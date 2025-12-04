"""
Developer Tools Module

Front-page category providing developer-focused utilities like
Git project management, repository cloning, SSH key management,
and Developer Kit export/import for portable dev setups.

Copyright (c) 2025 Christopher Dorrell. Licensed under GPL-3.0.
"""

import os
import subprocess
import threading
import json
import shutil
import stat
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, Gio, GLib, Gdk

from ..core import get_distro, DistroFamily
from .registry import register_module, ModuleCategory


# Config file for saved projects
CONFIG_DIR = os.path.join(GLib.get_user_config_dir(), 'tux-assistant')
PROJECTS_FILE = os.path.join(CONFIG_DIR, 'git_projects.json')

# Common directories to scan for git repos
SCAN_DIRECTORIES = [
    '~/Development',
    '~/Projects', 
    '~/src',
    '~/repos',
    '~/Code',
    '~/workspace',
]

# Developer Kit manifest filename
DEV_KIT_MANIFEST = 'developer_kit.json'


@dataclass
class GitProject:
    """Information about a git project."""
    path: str
    name: str
    remote_url: str
    branch: str
    has_changes: bool
    ahead: int  # commits ahead of remote
    behind: int  # commits behind remote
    last_commit: str
    

def check_ssh_keys_exist() -> tuple[bool, str, str, str]:
    """Check if SSH keys exist. Returns (exists, key_type, private_path, public_path)."""
    ssh_dir = os.path.expanduser("~/.ssh")
    key_types = ['id_ed25519', 'id_rsa', 'id_ecdsa']
    
    for key_type in key_types:
        private_key = os.path.join(ssh_dir, key_type)
        public_key = os.path.join(ssh_dir, f"{key_type}.pub")
        if os.path.exists(private_key) and os.path.exists(public_key):
            return True, key_type, private_key, public_key
    
    return False, "", "", ""


def check_git_config() -> tuple[bool, str, str]:
    """Check if git config has name and email set."""
    try:
        name_result = subprocess.run(
            ['git', 'config', '--global', 'user.name'],
            capture_output=True, text=True
        )
        email_result = subprocess.run(
            ['git', 'config', '--global', 'user.email'],
            capture_output=True, text=True
        )
        name = name_result.stdout.strip()
        email = email_result.stdout.strip()
        configured = bool(name and email)
        return configured, name, email
    except Exception:
        return False, "", ""


def is_git_repo(path: str) -> bool:
    """Check if a path is a git repository."""
    git_dir = os.path.join(path, '.git')
    return os.path.isdir(git_dir)


def get_git_info(path: str) -> Optional[GitProject]:
    """Get detailed git information for a repository."""
    if not is_git_repo(path):
        return None
    
    try:
        # Get remote URL
        remote_result = subprocess.run(
            ['git', '-C', path, 'remote', 'get-url', 'origin'],
            capture_output=True, text=True
        )
        remote_url = remote_result.stdout.strip() if remote_result.returncode == 0 else ""
        
        # Get current branch
        branch_result = subprocess.run(
            ['git', '-C', path, 'branch', '--show-current'],
            capture_output=True, text=True
        )
        branch = branch_result.stdout.strip() or "detached"
        
        # Check for uncommitted changes
        status_result = subprocess.run(
            ['git', '-C', path, 'status', '--porcelain'],
            capture_output=True, text=True
        )
        has_changes = bool(status_result.stdout.strip())
        
        # Get ahead/behind count (if remote tracking exists)
        ahead, behind = 0, 0
        try:
            rev_result = subprocess.run(
                ['git', '-C', path, 'rev-list', '--left-right', '--count', f'HEAD...origin/{branch}'],
                capture_output=True, text=True, timeout=5
            )
            if rev_result.returncode == 0:
                parts = rev_result.stdout.strip().split()
                if len(parts) == 2:
                    ahead, behind = int(parts[0]), int(parts[1])
        except Exception:
            pass
        
        # Get last commit message
        log_result = subprocess.run(
            ['git', '-C', path, 'log', '-1', '--format=%s'],
            capture_output=True, text=True
        )
        last_commit = log_result.stdout.strip()[:50] if log_result.returncode == 0 else ""
        
        return GitProject(
            path=path,
            name=os.path.basename(path),
            remote_url=remote_url,
            branch=branch,
            has_changes=has_changes,
            ahead=ahead,
            behind=behind,
            last_commit=last_commit
        )
    except Exception as e:
        return None


def scan_for_git_repos() -> List[str]:
    """Scan common directories for git repositories."""
    found_repos = []
    
    for scan_dir in SCAN_DIRECTORIES:
        expanded = os.path.expanduser(scan_dir)
        if not os.path.isdir(expanded):
            continue
        
        # Check immediate subdirectories
        try:
            for item in os.listdir(expanded):
                item_path = os.path.join(expanded, item)
                if os.path.isdir(item_path) and is_git_repo(item_path):
                    found_repos.append(item_path)
        except PermissionError:
            continue
    
    return sorted(set(found_repos))


def get_scanned_directories_status() -> List[tuple[str, bool]]:
    """Get list of scan directories and whether they exist."""
    results = []
    for scan_dir in SCAN_DIRECTORIES:
        expanded = os.path.expanduser(scan_dir)
        exists = os.path.isdir(expanded)
        results.append((scan_dir, exists))
    return results


def load_saved_projects() -> List[str]:
    """Load saved project paths from config."""
    try:
        if os.path.exists(PROJECTS_FILE):
            with open(PROJECTS_FILE, 'r') as f:
                data = json.load(f)
                return data.get('projects', [])
    except Exception:
        pass
    return []


def save_projects(paths: List[str]):
    """Save project paths to config."""
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(PROJECTS_FILE, 'w') as f:
            json.dump({'projects': paths}, f, indent=2)
    except Exception as e:
        print(f"Failed to save projects: {e}")


@register_module(
    id="developer_tools",
    name="Developer Tools",
    description="Git manager, SSH keys, and development utilities",
    icon="utilities-terminal-symbolic",
    category=ModuleCategory.DEVELOPER,
    order=40  # Power user tier
)
class DeveloperToolsPage(Adw.NavigationPage):
    """Developer tools page."""
    
    def __init__(self, parent_window):
        super().__init__(title="Developer Tools")
        
        self.window = parent_window
        self.distro = get_distro()
        self.projects: List[str] = []
        self.project_rows: dict = {}  # path -> row widget
        
        self.build_ui()
        self._load_projects()
    
    def build_ui(self):
        """Build the page UI."""
        # Use ToolbarView for proper header
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header bar (NavigationView handles back button automatically)
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)
        
        # Scrollable content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_hexpand(True)
        toolbar_view.set_content(scrolled)
        
        # Content box with clamp
        clamp = Adw.Clamp()
        clamp.set_maximum_size(850)
        clamp.set_margin_top(24)
        clamp.set_margin_bottom(24)
        clamp.set_margin_start(24)
        clamp.set_margin_end(24)
        scrolled.set_child(clamp)
        
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        clamp.set_child(self.content_box)
        
        # Header
        header_label = Gtk.Label()
        header_label.set_markup(
            "<big><b>Developer Tools</b></big>\n"
            "<small>Git project management and development utilities</small>"
        )
        header_label.set_halign(Gtk.Align.START)
        self.content_box.append(header_label)
        
        # Prerequisites check
        self._build_prerequisites_section(self.content_box)
        
        # Tux Assistant Dev section (only shows if in TA repo)
        self._build_tux_assistant_dev_section(self.content_box)
        
        # Git Projects section
        self._build_git_projects_section(self.content_box)
        
        # Developer Kit section
        self._build_developer_kit_section(self.content_box)
        
        # Other Git Tools
        self._build_other_git_tools(self.content_box)
    
    def _build_prerequisites_section(self, content_box):
        """Build the prerequisites check section."""
        prereq_group = Adw.PreferencesGroup()
        prereq_group.set_title("Prerequisites")
        prereq_group.set_description("Required setup for Git operations")
        content_box.append(prereq_group)
        
        # SSH Keys status
        ssh_exists, key_type, _, _ = check_ssh_keys_exist()
        ssh_row = Adw.ActionRow()
        ssh_row.set_title("SSH Keys")
        
        if ssh_exists:
            ssh_row.set_subtitle(f"✓ Found {key_type} keys")
            ssh_row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
        else:
            ssh_row.set_subtitle("✗ No SSH keys found - required for Git push/pull")
            ssh_row.add_prefix(Gtk.Image.new_from_icon_name("dialog-warning-symbolic"))
            
            setup_btn = Gtk.Button(label="Setup Keys")
            setup_btn.add_css_class("suggested-action")
            setup_btn.set_valign(Gtk.Align.CENTER)
            setup_btn.connect("clicked", self._on_restore_ssh_clicked)
            ssh_row.add_suffix(setup_btn)
        
        prereq_group.add(ssh_row)
        self.ssh_row = ssh_row
        
        # Git config status
        git_configured, name, email = check_git_config()
        config_row = Adw.ActionRow()
        config_row.set_title("Git Identity")
        
        if git_configured:
            # Don't use < > as they're interpreted as markup
            config_row.set_subtitle(f"✓ {name} ({email})")
            config_row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
        else:
            config_row.set_subtitle("✗ Name and email not configured")
            config_row.add_prefix(Gtk.Image.new_from_icon_name("dialog-warning-symbolic"))
            
            setup_btn = Gtk.Button(label="Configure")
            setup_btn.add_css_class("suggested-action")
            setup_btn.set_valign(Gtk.Align.CENTER)
            setup_btn.connect("clicked", self._on_configure_git_identity)
            config_row.add_suffix(setup_btn)
        
        prereq_group.add(config_row)
        self.config_row = config_row
        self.prereq_group = prereq_group
    
    def _refresh_prereq_section(self):
        """Refresh the git identity row after configuration."""
        git_configured, name, email = check_git_config()
        if git_configured and hasattr(self, 'config_row'):
            # Update the subtitle to show configured
            self.config_row.set_subtitle(f"✓ {name} ({email})")
            # Note: The button and icon will remain but that's OK for now
    
    def _build_tux_assistant_dev_section(self, content_box):
        """Build the Tux Assistant development section (only if in TA repo)."""
        # Check if we're in the Tux Assistant repo
        ta_repo_path = self._find_tux_assistant_repo()
        if not ta_repo_path:
            return  # Don't show section if not found
        
        self.ta_repo_path = ta_repo_path
        
        # Create the section
        ta_group = Adw.PreferencesGroup()
        ta_group.set_title("🐧 Tux Assistant Development")
        ta_group.set_description(f"Repo: {ta_repo_path}")
        content_box.append(ta_group)
        
        # SSH Key unlock row (FIRST - do this before any git operations)
        ssh_row = Adw.ActionRow()
        ssh_row.set_title("SSH Key")
        
        # Check if SSH agent is running and key is loaded
        ssh_status = self._check_ssh_agent_status()
        ssh_row.set_subtitle(ssh_status)
        
        if "Unlocked" in ssh_status:
            ssh_row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
        else:
            ssh_row.add_prefix(Gtk.Image.new_from_icon_name("dialog-password-symbolic"))
        
        unlock_btn = Gtk.Button(label="Unlock SSH Key")
        unlock_btn.add_css_class("suggested-action")
        unlock_btn.set_tooltip_text("Opens terminal to enter your SSH passphrase")
        unlock_btn.set_valign(Gtk.Align.CENTER)
        unlock_btn.connect("clicked", self._on_unlock_ssh_key)
        ssh_row.add_suffix(unlock_btn)
        
        ta_group.add(ssh_row)
        self.ta_ssh_row = ssh_row
        
        # Current branch status
        branch_row = Adw.ActionRow()
        branch_row.set_title("Current Branch")
        branch = self._get_ta_branch()
        has_changes = self._ta_has_changes()
        
        status_text = branch
        if has_changes:
            status_text += " (has uncommitted changes)"
        branch_row.set_subtitle(status_text)
        
        if branch == "main":
            branch_row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
        else:
            branch_row.add_prefix(Gtk.Image.new_from_icon_name("dialog-warning-symbolic"))
        
        ta_group.add(branch_row)
        self.ta_branch_row = branch_row
        
        # Main branch operations
        dev_row = Adw.ActionRow()
        dev_row.set_title("Main Branch")
        dev_row.set_subtitle("Pull latest changes or push your work")
        
        pull_dev_btn = Gtk.Button(label="Pull")
        pull_dev_btn.set_tooltip_text("git pull origin main")
        pull_dev_btn.set_valign(Gtk.Align.CENTER)
        pull_dev_btn.connect("clicked", self._on_ta_pull_dev)
        dev_row.add_suffix(pull_dev_btn)
        
        push_dev_btn = Gtk.Button(label="Push")
        push_dev_btn.add_css_class("suggested-action")
        push_dev_btn.set_tooltip_text("Commit and push changes to main branch")
        push_dev_btn.set_valign(Gtk.Align.CENTER)
        push_dev_btn.connect("clicked", self._on_ta_push_dev)
        dev_row.add_suffix(push_dev_btn)
        
        ta_group.add(dev_row)
        
        # Build and release row
        release_row = Adw.ActionRow()
        release_row.set_title("Build &amp; Release")
        release_row.set_subtitle("Build .run file and create GitHub Release")
        
        build_btn = Gtk.Button(label="Build .run Only")
        build_btn.set_tooltip_text("Run build-run.sh to create .run file")
        build_btn.set_valign(Gtk.Align.CENTER)
        build_btn.connect("clicked", self._on_ta_build_run)
        release_row.add_suffix(build_btn)
        
        release_btn = Gtk.Button(label="Create GitHub Release")
        release_btn.add_css_class("suggested-action")
        release_btn.set_tooltip_text("Build .run and upload to GitHub Releases")
        release_btn.set_valign(Gtk.Align.CENTER)
        release_btn.connect("clicked", self._on_github_release)
        release_row.add_suffix(release_btn)
        
        ta_group.add(release_row)
        
        # GitHub PAT setup row
        pat_row = Adw.ActionRow()
        pat_row.set_title("GitHub Token")
        
        # Check if PAT is stored
        pat_status = "Configured ✓" if self._get_github_pat() else "Not set"
        pat_row.set_subtitle(pat_status)
        
        if self._get_github_pat():
            pat_row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
        else:
            pat_row.add_prefix(Gtk.Image.new_from_icon_name("dialog-password-symbolic"))
        
        setup_pat_btn = Gtk.Button(label="Setup Token")
        setup_pat_btn.set_tooltip_text("Configure GitHub Personal Access Token")
        setup_pat_btn.set_valign(Gtk.Align.CENTER)
        setup_pat_btn.connect("clicked", self._on_setup_github_pat)
        pat_row.add_suffix(setup_pat_btn)
        
        ta_group.add(pat_row)
        self.pat_row = pat_row
        
        # Refresh button
        refresh_row = Adw.ActionRow()
        refresh_row.set_title("Refresh Status")
        refresh_row.set_subtitle("Check branch and changes status")
        
        refresh_btn = Gtk.Button(label="Refresh")
        refresh_btn.set_valign(Gtk.Align.CENTER)
        refresh_btn.connect("clicked", self._on_ta_refresh_status)
        refresh_row.add_suffix(refresh_btn)
        
        ta_group.add(refresh_row)
        
        # Setup &amp; Help row
        help_row = Adw.ActionRow()
        help_row.set_title("Setup &amp; Help")
        help_row.set_subtitle("Learn how to use the Git workflow")
        help_row.add_prefix(Gtk.Image.new_from_icon_name("help-about-symbolic"))
        
        help_btn = Gtk.Button(label="Open Guide")
        help_btn.set_valign(Gtk.Align.CENTER)
        help_btn.connect("clicked", self._on_show_git_help)
        help_row.add_suffix(help_btn)
        
        ta_group.add(help_row)
    
    def _get_ssh_env(self) -> dict:
        """Get environment with SSH agent variables loaded."""
        env = os.environ.copy()
        agent_info = os.path.expanduser("~/.ssh/agent-info")
        
        if os.path.exists(agent_info):
            try:
                with open(agent_info, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith('export '):
                            # Parse: export SSH_AUTH_SOCK=/tmp/ssh-xxx/agent.123
                            parts = line[7:].split('=', 1)
                            if len(parts) == 2:
                                env[parts[0]] = parts[1]
            except Exception:
                pass
        
        return env
    
    def _find_tux_assistant_repo(self) -> Optional[str]:
        """Find the Tux Assistant repo on the system."""
        # Check common locations
        possible_paths = [
            os.path.expanduser("~/Development/Tux-Assistant"),
            os.path.expanduser("~/Development/tux-assistant"),
            os.path.expanduser("~/Projects/Tux-Assistant"),
            os.path.expanduser("~/Projects/tux-assistant"),
            os.path.expanduser("~/tux-assistant"),
            os.path.expanduser("~/Tux-Assistant"),
        ]
        
        for path in possible_paths:
            if os.path.isdir(path) and os.path.isdir(os.path.join(path, '.git')):
                # Verify it's actually Tux Assistant by checking for key files
                if os.path.exists(os.path.join(path, 'tux', 'app.py')):
                    return path
        
        return None
    
    def _get_ta_branch(self) -> str:
        """Get current branch of Tux Assistant repo."""
        try:
            result = subprocess.run(
                ['git', 'branch', '--show-current'],
                cwd=self.ta_repo_path,
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() or "unknown"
        except:
            return "unknown"
    
    def _ta_has_changes(self) -> bool:
        """Check if Tux Assistant repo has uncommitted changes."""
        try:
            result = subprocess.run(
                ['git', 'status', '--porcelain'],
                cwd=self.ta_repo_path,
                capture_output=True, text=True, timeout=5
            )
            return bool(result.stdout.strip())
        except:
            return False
    
    def _check_ssh_agent_status(self) -> str:
        """Check if SSH agent is running and has keys loaded."""
        try:
            # First try to load SSH agent info from our saved file
            ssh_env = self._get_ssh_env()
            
            # Check if keys are loaded using the loaded environment
            result = subprocess.run(
                ['ssh-add', '-l'],
                capture_output=True, text=True, timeout=5,
                env=ssh_env
            )
            
            if result.returncode == 0 and result.stdout.strip():
                # Keys are loaded
                lines = result.stdout.strip().split('\n')
                return f"Unlocked ✓ ({len(lines)} key{'s' if len(lines) > 1 else ''} loaded)"
            elif "no identities" in result.stderr.lower() or result.returncode == 1:
                return "Locked - click Unlock to enter passphrase"
            else:
                return "Agent not running - click Unlock"
        except Exception as e:
            return "Agent not running - click Unlock"
    
    def _on_unlock_ssh_key(self, button):
        """Open terminal to unlock SSH key with passphrase."""
        # Find the SSH key
        ssh_dir = os.path.expanduser("~/.ssh")
        key_file = None
        
        for key_name in ['id_ed25519', 'id_rsa', 'id_ecdsa']:
            key_path = os.path.join(ssh_dir, key_name)
            if os.path.exists(key_path):
                key_file = key_path
                break
        
        if not key_file:
            self.window.show_toast("No SSH key found in ~/.ssh/")
            return
        
        agent_info_file = os.path.expanduser("~/.ssh/agent-info")
        
        # Create a script that starts ssh-agent if needed and adds the key
        unlock_script = f'''#!/bin/bash
echo "════════════════════════════════════════════════════"
echo "  🔐 SSH Key Unlock"
echo "════════════════════════════════════════════════════"
echo ""

AGENT_INFO="{agent_info_file}"

# Check if we have existing agent info and if it's still valid
if [ -f "$AGENT_INFO" ]; then
    source "$AGENT_INFO" 2>/dev/null
    if ssh-add -l &>/dev/null; then
        echo "SSH agent already running and accessible."
    else
        # Agent info exists but agent is dead, start new one
        echo "Starting new SSH agent..."
        eval "$(ssh-agent -s)" > /dev/null
        echo "export SSH_AUTH_SOCK=$SSH_AUTH_SOCK" > "$AGENT_INFO"
        echo "export SSH_AGENT_PID=$SSH_AGENT_PID" >> "$AGENT_INFO"
    fi
else
    # No agent info file, start fresh
    echo "Starting SSH agent..."
    eval "$(ssh-agent -s)" > /dev/null
    echo "export SSH_AUTH_SOCK=$SSH_AUTH_SOCK" > "$AGENT_INFO"
    echo "export SSH_AGENT_PID=$SSH_AGENT_PID" >> "$AGENT_INFO"
fi

echo ""
echo "Adding SSH key: {key_file}"
echo "Enter your passphrase when prompted:"
echo ""

ssh-add {key_file}

if [ $? -eq 0 ]; then
    echo ""
    echo "════════════════════════════════════════════════════"
    echo "  ✓ SSH key unlocked successfully!"
    echo "  You can now use Push/Pull without passphrase prompts"
    echo "════════════════════════════════════════════════════"
else
    echo ""
    echo "════════════════════════════════════════════════════"
    echo "  ✗ Failed to unlock SSH key"
    echo "════════════════════════════════════════════════════"
fi

echo ""
read -p "Press Enter to close this window..."
'''
        
        # Write script to temp file
        script_path = '/tmp/tux-ssh-unlock.sh'
        with open(script_path, 'w') as f:
            f.write(unlock_script)
        os.chmod(script_path, 0o755)
        
        # Find and launch terminal
        terminals = [
            ('kgx', ['kgx', '-e', 'bash', script_path]),  # GNOME Console (Fedora)
            ('ptyxis', ['ptyxis', '-e', 'bash', script_path]),  # New GNOME Terminal
            ('gnome-terminal', ['gnome-terminal', '--', 'bash', script_path]),
            ('konsole', ['konsole', '-e', 'bash', script_path]),
            ('xfce4-terminal', ['xfce4-terminal', '-e', f'bash {script_path}']),
            ('tilix', ['tilix', '-e', f'bash {script_path}']),
            ('alacritty', ['alacritty', '-e', 'bash', script_path]),
            ('kitty', ['kitty', 'bash', script_path]),
            ('xterm', ['xterm', '-e', f'bash {script_path}']),
        ]
        
        for term_name, term_cmd in terminals:
            try:
                if subprocess.run(['which', term_name], capture_output=True).returncode == 0:
                    subprocess.Popen(term_cmd)
                    self.window.show_toast(f"Opening terminal to unlock SSH key...")
                    
                    # Schedule a status refresh after a few seconds
                    GLib.timeout_add_seconds(3, self._refresh_ssh_status)
                    return
            except Exception:
                continue
        
        self.window.show_toast("Could not find a terminal emulator")
    
    def _refresh_ssh_status(self):
        """Refresh the SSH status display."""
        if hasattr(self, 'ta_ssh_row'):
            ssh_status = self._check_ssh_agent_status()
            self.ta_ssh_row.set_subtitle(ssh_status)
            
            # Update icon
            child = self.ta_ssh_row.get_first_child()
            while child:
                if isinstance(child, Gtk.Image):
                    self.ta_ssh_row.remove(child)
                    break
                child = child.get_next_sibling()
            
            if "Unlocked" in ssh_status:
                self.ta_ssh_row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
            else:
                self.ta_ssh_row.add_prefix(Gtk.Image.new_from_icon_name("dialog-password-symbolic"))
        
        return False  # Don't repeat
    
    def _on_ta_refresh_status(self, button):
        """Refresh the Tux Assistant status display."""
        branch = self._get_ta_branch()
        has_changes = self._ta_has_changes()
        
        status_text = branch
        if has_changes:
            status_text += " (has uncommitted changes)"
        
        self.ta_branch_row.set_subtitle(status_text)
        
        # Update icon
        # Remove old prefix
        child = self.ta_branch_row.get_first_child()
        while child:
            if isinstance(child, Gtk.Image):
                self.ta_branch_row.remove(child)
                break
            child = child.get_next_sibling()
        
        if branch == "main":
            self.ta_branch_row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
        else:
            self.ta_branch_row.add_prefix(Gtk.Image.new_from_icon_name("dialog-warning-symbolic"))
        
        # Also refresh SSH status
        self._refresh_ssh_status()
        
        self.window.show_toast("Status refreshed")
    
    def _on_show_git_help(self, button):
        """Show the Git workflow help dialog."""
        help_text = """<b>🚀 Quick Start - Update Workflow</b>

1. Download the new .zip file to ~/Downloads/
2. Open Tux Assistant → Developer Tools
3. Click <b>Unlock SSH Key</b> → enter passphrase
4. Go to <b>Other Git Tools</b> → <b>Update Project from ZIP</b>
5. Click <b>Push</b> button
6. Click <b>Create GitHub Release</b>

Done! Release is now on GitHub Releases page (not in repo).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🔑 First-Time Setup</b>

<b>GitHub Token (required for releases):</b>
1. Go to github.com/settings/tokens
2. Generate new token (classic)
3. Check "repo" scope
4. Copy the token
5. Click "Setup Token" in Tux Assistant
6. Paste and save

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🔧 Troubleshooting</b>

<b>Push failed / ssh_askpass error:</b>
• Did you click "Unlock SSH Key" first?
• If it still fails, run this in terminal:
  <tt>eval $(ssh-agent) &amp;&amp; ssh-add</tt>
• Then try Push again

<b>"Release already exists" error:</b>
• Bump the VERSION file first
• Or delete the existing release on GitHub

<b>GitHub API error 401:</b>
• Token expired or invalid
• Generate a new token and update it

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>💻 Manual Terminal Commands</b>

If GUI isn't working, use this full command:

<tt>cd ~/Development/Tux-Assistant &amp;&amp; \\
rm -rf /tmp/tux-assistant &amp;&amp; \\
unzip ~/Downloads/tux-assistant-vX.X.X-source.zip -d /tmp/ &amp;&amp; \\
cp -r /tmp/tux-assistant/* . &amp;&amp; \\
git add . &amp;&amp; git commit -m "vX.X.X" &amp;&amp; git push</tt>

Then use the Create GitHub Release button, or manually via gh CLI."""

        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Git Workflow Guide",
            body=""
        )
        
        # Create scrollable content for long help text
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(400)
        scroll.set_min_content_width(500)
        
        label = Gtk.Label()
        label.set_markup(help_text)
        label.set_wrap(True)
        label.set_xalign(0)
        label.set_margin_start(12)
        label.set_margin_end(12)
        label.set_margin_top(12)
        label.set_margin_bottom(12)
        label.set_selectable(True)
        
        scroll.set_child(label)
        dialog.set_extra_child(scroll)
        
        dialog.add_response("close", "Got it!")
        dialog.set_response_appearance("close", Adw.ResponseAppearance.SUGGESTED)
        dialog.present()
    
    def _on_ta_pull_dev(self, button):
        """Pull latest changes from main branch."""
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Pull Main Branch",
            body="This will pull the latest changes from origin/main.\n\nAny uncommitted changes may cause conflicts."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("pull", "Pull")
        dialog.set_response_appearance("pull", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._do_ta_pull_dev)
        dialog.present()
    
    def _do_ta_pull_dev(self, dialog, response):
        """Execute the pull operation."""
        if response != "pull":
            return
        
        def do_pull():
            try:
                # Pull from main
                result = subprocess.run(
                    ['git', 'pull', 'origin', 'main'],
                    cwd=self.ta_repo_path,
                    capture_output=True, text=True, timeout=60
                )
                
                if result.returncode == 0:
                    GLib.idle_add(self.window.show_toast, "Successfully pulled main branch")
                    GLib.idle_add(self._on_ta_refresh_status, None)
                else:
                    GLib.idle_add(self.window.show_toast, f"Pull failed: {result.stderr[:50]}")
            except Exception as e:
                GLib.idle_add(self.window.show_toast, f"Error: {str(e)[:50]}")
        
        threading.Thread(target=do_pull, daemon=True).start()
        self.window.show_toast("Pulling main branch...")
    
    def _on_ta_push_dev(self, button):
        """Push changes to main branch with commit message dialog."""
        # Check if there are changes
        if not self._ta_has_changes():
            self.window.show_toast("No changes to commit")
            return
        
        # Show commit message dialog
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Push to Main Branch",
            body="Enter a commit message for your changes:"
        )
        
        # Add entry for commit message
        entry = Gtk.Entry()
        entry.set_placeholder_text("Describe your changes...")
        entry.set_margin_start(20)
        entry.set_margin_end(20)
        entry.set_margin_top(10)
        dialog.set_extra_child(entry)
        
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("push", "Commit & Push")
        dialog.set_response_appearance("push", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._do_ta_push_dev, entry)
        dialog.present()
        
        # Focus the entry
        entry.grab_focus()
    
    def _do_ta_push_dev(self, dialog, response, entry):
        """Execute the push operation."""
        if response != "push":
            return
        
        commit_msg = entry.get_text().strip()
        if not commit_msg:
            commit_msg = "Update from Tux Assistant"
        
        def do_push():
            try:
                # Get SSH environment
                ssh_env = self._get_ssh_env()
                
                # Add all changes
                subprocess.run(
                    ['git', 'add', '.'],
                    cwd=self.ta_repo_path,
                    capture_output=True, text=True, timeout=30,
                    env=ssh_env
                )
                
                # Commit
                result1 = subprocess.run(
                    ['git', 'commit', '-m', commit_msg],
                    cwd=self.ta_repo_path,
                    capture_output=True, text=True, timeout=30,
                    env=ssh_env
                )
                
                # Push to main with SSH env
                result2 = subprocess.run(
                    ['git', 'push', 'origin', 'main'],
                    cwd=self.ta_repo_path,
                    capture_output=True, text=True, timeout=60,
                    env=ssh_env
                )
                
                if result2.returncode == 0:
                    GLib.idle_add(self.window.show_toast, "Successfully pushed to main branch")
                    GLib.idle_add(self._on_ta_refresh_status, None)
                else:
                    GLib.idle_add(self.window.show_toast, f"Push failed: {result2.stderr[:50]}")
            except Exception as e:
                GLib.idle_add(self.window.show_toast, f"Error: {str(e)[:50]}")
        
        threading.Thread(target=do_push, daemon=True).start()
        self.window.show_toast("Committing and pushing...")
    
    def _on_ta_build_run(self, button):
        """Build the .run file."""
        build_script = os.path.join(self.ta_repo_path, 'scripts', 'build-run.sh')
        
        if not os.path.exists(build_script):
            self.window.show_toast("Build script not found: scripts/build-run.sh")
            return
        
        def do_build():
            try:
                result = subprocess.run(
                    ['bash', build_script],
                    cwd=self.ta_repo_path,
                    capture_output=True, text=True, timeout=120
                )
                
                if result.returncode == 0:
                    # Find the version
                    version_file = os.path.join(self.ta_repo_path, 'VERSION')
                    version = "unknown"
                    if os.path.exists(version_file):
                        with open(version_file, 'r') as f:
                            version = f.read().strip()
                    GLib.idle_add(self.window.show_toast, f"Built Tux-Assistant-v{version}.run")
                else:
                    GLib.idle_add(self.window.show_toast, f"Build failed: {result.stderr[:50]}")
            except Exception as e:
                GLib.idle_add(self.window.show_toast, f"Error: {str(e)[:50]}")
        
        threading.Thread(target=do_build, daemon=True).start()
        self.window.show_toast("Building .run file...")
    
    def _on_ta_release(self, button):
        """Build and push to main branch."""
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Build &amp; Release",
            body=(
                "This will:\n\n"
                "1. Build the .run file\n"
                "2. Copy .run to releases/\n"
                "3. Commit and push to main\n\n"
                "Make sure changes are committed first!"
            )
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("release", "Build &amp; Release")
        dialog.set_response_appearance("release", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._do_ta_release)
        dialog.present()
    
    def _do_ta_release(self, dialog, response):
        """Execute the full release process."""
        if response != "release":
            return
        
        def do_release():
            try:
                # Get SSH environment for all git operations
                ssh_env = self._get_ssh_env()
                
                # 1. Build
                build_script = os.path.join(self.ta_repo_path, 'scripts', 'build-run.sh')
                result = subprocess.run(
                    ['bash', build_script],
                    cwd=self.ta_repo_path,
                    capture_output=True, text=True, timeout=120
                )
                
                if result.returncode != 0:
                    GLib.idle_add(self.window.show_toast, "Build failed")
                    return
                
                # Get version
                version_file = os.path.join(self.ta_repo_path, 'VERSION')
                with open(version_file, 'r') as f:
                    version = f.read().strip()
                
                run_file = os.path.join(self.ta_repo_path, 'dist', f'Tux-Assistant-v{version}.run')
                
                if not os.path.exists(run_file):
                    GLib.idle_add(self.window.show_toast, ".run file not found after build")
                    return
                
                # 2. Copy .run to releases
                releases_dir = os.path.join(self.ta_repo_path, 'releases')
                os.makedirs(releases_dir, exist_ok=True)
                
                dest_file = os.path.join(releases_dir, f'Tux-Assistant-v{version}.run')
                shutil.copy2(run_file, dest_file)
                
                # 3. Commit and push to main
                subprocess.run(['git', 'add', '.'], cwd=self.ta_repo_path, timeout=30, env=ssh_env)
                subprocess.run(
                    ['git', 'commit', '-m', f'Release v{version}'],
                    cwd=self.ta_repo_path, timeout=30, env=ssh_env
                )
                subprocess.run(
                    ['git', 'push', 'origin', 'main'],
                    cwd=self.ta_repo_path, env=ssh_env, timeout=60
                )
                
                GLib.idle_add(self.window.show_toast, f"Released v{version} to main!")
                GLib.idle_add(self._on_ta_refresh_status, None)
                
            except Exception as e:
                GLib.idle_add(self.window.show_toast, f"Release error: {str(e)[:50]}")
        
        threading.Thread(target=do_release, daemon=True).start()
        self.window.show_toast("Starting release process...")
    
    def _get_github_pat(self):
        """Get GitHub PAT from config file."""
        pat_file = os.path.join(CONFIG_DIR, '.github_pat')
        if os.path.exists(pat_file):
            try:
                with open(pat_file, 'r') as f:
                    return f.read().strip()
            except:
                pass
        return None
    
    def _save_github_pat(self, pat):
        """Save GitHub PAT to config file."""
        os.makedirs(CONFIG_DIR, exist_ok=True)
        pat_file = os.path.join(CONFIG_DIR, '.github_pat')
        with open(pat_file, 'w') as f:
            f.write(pat)
        os.chmod(pat_file, 0o600)  # Read/write only for owner
    
    def _on_setup_github_pat(self, button):
        """Show dialog to setup GitHub PAT."""
        dialog = Adw.AlertDialog()
        dialog.set_heading("GitHub Personal Access Token")
        dialog.set_body(
            "Enter your GitHub PAT with 'repo' scope.\n\n"
            "Create one at: github.com/settings/tokens\n"
            "Required scope: repo (Full control)"
        )
        
        # Entry for PAT
        entry = Gtk.Entry()
        entry.set_visibility(False)  # Hide like password
        entry.set_placeholder_text("ghp_xxxxxxxxxxxxxxxxxxxx")
        current_pat = self._get_github_pat()
        if current_pat:
            entry.set_text(current_pat)
        entry.set_margin_top(12)
        entry.set_margin_start(12)
        entry.set_margin_end(12)
        dialog.set_extra_child(entry)
        
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("save", "Save Token")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        
        def on_response(d, response):
            if response == "save":
                pat = entry.get_text().strip()
                if pat:
                    self._save_github_pat(pat)
                    self.window.show_toast("GitHub token saved!")
                    # Update UI
                    if hasattr(self, 'pat_row'):
                        self.pat_row.set_subtitle("Configured ✓")
        
        dialog.connect("response", on_response)
        dialog.present(self.window)
    
    def _on_github_release(self, button):
        """Create a GitHub Release with the .run file."""
        pat = self._get_github_pat()
        if not pat:
            self.window.show_toast("Set up GitHub Token first!")
            return
        
        # Confirm dialog
        dialog = Adw.AlertDialog()
        dialog.set_heading("Create GitHub Release")
        
        # Get version
        version_file = os.path.join(self.ta_repo_path, 'VERSION')
        with open(version_file, 'r') as f:
            version = f.read().strip()
        
        dialog.set_body(f"This will:\n\n1. Build Tux-Assistant-v{version}.run\n2. Create GitHub Release v{version}\n3. Upload .run as release asset\n\nContinue?")
        
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("release", "Create Release")
        dialog.set_response_appearance("release", Adw.ResponseAppearance.SUGGESTED)
        
        dialog.connect("response", self._do_github_release)
        dialog.present(self.window)
    
    def _do_github_release(self, dialog, response):
        """Execute GitHub Release creation."""
        if response != "release":
            return
        
        def do_release():
            try:
                import urllib.request
                import urllib.error
                
                pat = self._get_github_pat()
                
                # 1. Build
                GLib.idle_add(self.window.show_toast, "Building .run file...")
                build_script = os.path.join(self.ta_repo_path, 'scripts', 'build-run.sh')
                result = subprocess.run(
                    ['bash', build_script],
                    cwd=self.ta_repo_path,
                    capture_output=True, text=True, timeout=120
                )
                
                if result.returncode != 0:
                    GLib.idle_add(self.window.show_toast, "Build failed!")
                    return
                
                # Get version
                version_file = os.path.join(self.ta_repo_path, 'VERSION')
                with open(version_file, 'r') as f:
                    version = f.read().strip()
                
                run_file = os.path.join(self.ta_repo_path, 'dist', f'Tux-Assistant-v{version}.run')
                
                if not os.path.exists(run_file):
                    GLib.idle_add(self.window.show_toast, ".run file not found!")
                    return
                
                # 2. Create GitHub Release
                GLib.idle_add(self.window.show_toast, "Creating GitHub release...")
                
                # Get repo info from remote
                result = subprocess.run(
                    ['git', 'remote', 'get-url', 'origin'],
                    cwd=self.ta_repo_path,
                    capture_output=True, text=True
                )
                remote_url = result.stdout.strip()
                
                # Parse owner/repo from URL
                # Handle: git@github.com:owner/repo.git or https://github.com/owner/repo.git
                if 'github.com:' in remote_url:
                    repo_path = remote_url.split('github.com:')[1].replace('.git', '')
                elif 'github.com/' in remote_url:
                    repo_path = remote_url.split('github.com/')[1].replace('.git', '')
                else:
                    GLib.idle_add(self.window.show_toast, "Could not parse GitHub repo URL")
                    return
                
                owner, repo = repo_path.split('/')
                
                # Create release via API
                release_data = json.dumps({
                    "tag_name": f"v{version}",
                    "name": f"Tux Assistant v{version}",
                    "body": f"## Tux Assistant v{version}\n\nDownload `Tux-Assistant-v{version}.run` below and run:\n```bash\nchmod +x Tux-Assistant-v{version}.run\n./Tux-Assistant-v{version}.run\n```",
                    "draft": False,
                    "prerelease": False
                }).encode('utf-8')
                
                req = urllib.request.Request(
                    f"https://api.github.com/repos/{owner}/{repo}/releases",
                    data=release_data,
                    headers={
                        'Authorization': f'Bearer {pat}',
                        'Accept': 'application/vnd.github+json',
                        'Content-Type': 'application/json',
                        'X-GitHub-Api-Version': '2022-11-28'
                    },
                    method='POST'
                )
                
                try:
                    with urllib.request.urlopen(req) as resp:
                        release_info = json.loads(resp.read().decode('utf-8'))
                        upload_url = release_info['upload_url'].replace('{?name,label}', '')
                except urllib.error.HTTPError as e:
                    error_body = e.read().decode('utf-8')
                    if 'already_exists' in error_body:
                        GLib.idle_add(self.window.show_toast, f"Release v{version} already exists!")
                    else:
                        GLib.idle_add(self.window.show_toast, f"GitHub API error: {e.code}")
                    return
                
                # 3. Upload .run file as asset
                GLib.idle_add(self.window.show_toast, "Uploading .run file...")
                
                filename = f'Tux-Assistant-v{version}.run'
                with open(run_file, 'rb') as f:
                    file_data = f.read()
                
                upload_req = urllib.request.Request(
                    f"{upload_url}?name={filename}",
                    data=file_data,
                    headers={
                        'Authorization': f'Bearer {pat}',
                        'Accept': 'application/vnd.github+json',
                        'Content-Type': 'application/octet-stream',
                        'X-GitHub-Api-Version': '2022-11-28'
                    },
                    method='POST'
                )
                
                try:
                    with urllib.request.urlopen(upload_req) as resp:
                        pass  # Success
                except urllib.error.HTTPError as e:
                    GLib.idle_add(self.window.show_toast, f"Upload failed: {e.code}")
                    return
                
                GLib.idle_add(self.window.show_toast, f"🎉 Released v{version} to GitHub!")
                
            except Exception as e:
                GLib.idle_add(self.window.show_toast, f"Release error: {str(e)[:50]}")
        
        threading.Thread(target=do_release, daemon=True).start()
        self.window.show_toast("Starting GitHub release...")
    
    def _build_git_projects_section(self, content_box):
        """Build the git projects management section."""
        # Projects header with action buttons
        projects_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        projects_header.set_margin_top(10)
        content_box.append(projects_header)
        
        projects_label = Gtk.Label()
        projects_label.set_markup("<b>Git Projects</b>")
        projects_label.set_halign(Gtk.Align.START)
        projects_label.set_hexpand(True)
        projects_header.append(projects_label)
        
        # Help button - shows workflow guide
        help_btn = Gtk.Button(label="How to Update")
        help_btn.set_tooltip_text("Show the update workflow")
        help_btn.connect("clicked", self._show_update_workflow_help)
        projects_header.append(help_btn)
        
        # Scan button
        self.scan_btn = Gtk.Button()
        self.scan_btn.set_icon_name("folder-saved-search-symbolic")
        self.scan_btn.set_tooltip_text("Scan for Git projects")
        self.scan_btn.add_css_class("flat")
        self.scan_btn.connect("clicked", self._on_scan_projects)
        projects_header.append(self.scan_btn)
        
        # Add manually button
        add_btn = Gtk.Button()
        add_btn.set_icon_name("list-add-symbolic")
        add_btn.set_tooltip_text("Add project manually (Advanced)")
        add_btn.add_css_class("flat")
        add_btn.connect("clicked", self._on_add_project_manually)
        projects_header.append(add_btn)
        
        # Refresh button
        refresh_btn = Gtk.Button()
        refresh_btn.set_icon_name("view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh project status")
        refresh_btn.add_css_class("flat")
        refresh_btn.connect("clicked", self._on_refresh_projects)
        projects_header.append(refresh_btn)
        
        # Projects list
        self.projects_group = Adw.PreferencesGroup()
        self.projects_group.set_description("Manage your Git repositories with one-click push and pull")
        content_box.append(self.projects_group)
        
        # Empty state container (will be populated dynamically)
        self.empty_state_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        self.empty_state_box.set_margin_top(20)
        self.empty_state_box.set_margin_bottom(20)
        self._build_empty_state()
        self.projects_group.add(self.empty_state_box)
    
    def _build_empty_state(self):
        """Build the empty state guidance UI."""
        # Clear existing content
        while self.empty_state_box.get_first_child():
            self.empty_state_box.remove(self.empty_state_box.get_first_child())
        
        # Title
        title_label = Gtk.Label()
        title_label.set_markup("<b>No Git Projects Found</b>")
        title_label.set_halign(Gtk.Align.CENTER)
        self.empty_state_box.append(title_label)
        
        # Show scanned directories status
        dir_status = get_scanned_directories_status()
        scanned_label = Gtk.Label()
        status_lines = []
        for dir_path, exists in dir_status[:4]:  # Show first 4
            icon = "✓" if exists else "✗"
            status_lines.append(f"  {icon} {dir_path}")
        
        scanned_label.set_markup(
            "<small>Scanned locations:\n" + 
            "\n".join(status_lines) +
            "</small>"
        )
        scanned_label.add_css_class("dim-label")
        scanned_label.set_halign(Gtk.Align.CENTER)
        self.empty_state_box.append(scanned_label)
        
        # Action label
        action_label = Gtk.Label()
        action_label.set_markup("<small>What would you like to do?</small>")
        action_label.set_margin_top(10)
        self.empty_state_box.append(action_label)
        
        # Action buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        button_box.set_halign(Gtk.Align.CENTER)
        self.empty_state_box.append(button_box)
        
        # Clone a repository button
        clone_btn = Gtk.Button()
        clone_btn_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        clone_btn_content.append(Gtk.Image.new_from_icon_name("folder-download-symbolic"))
        clone_btn_content.append(Gtk.Label(label="Clone a Repository"))
        clone_btn.set_child(clone_btn_content)
        clone_btn.add_css_class("suggested-action")
        clone_btn.add_css_class("pill")
        clone_btn.connect("clicked", lambda b: self._on_clone_repo_clicked(None))
        button_box.append(clone_btn)
        
        # Create ~/Development button (only if it doesn't exist)
        dev_folder = os.path.expanduser("~/Development")
        if not os.path.isdir(dev_folder):
            create_btn = Gtk.Button()
            create_btn_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            create_btn_content.append(Gtk.Image.new_from_icon_name("folder-new-symbolic"))
            create_btn_content.append(Gtk.Label(label="Create ~/Development Folder"))
            create_btn.set_child(create_btn_content)
            create_btn.connect("clicked", self._on_create_dev_folder)
            button_box.append(create_btn)
        
        # Import Developer Kit button (if keys missing)
        ssh_exists, _, _, _ = check_ssh_keys_exist()
        if not ssh_exists:
            import_btn = Gtk.Button()
            import_btn_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            import_btn_content.append(Gtk.Image.new_from_icon_name("document-open-symbolic"))
            import_btn_content.append(Gtk.Label(label="Import Developer Kit"))
            import_btn.set_child(import_btn_content)
            import_btn.connect("clicked", self._on_import_dev_kit)
            button_box.append(import_btn)
        
        # Add manually button
        manual_btn = Gtk.Button()
        manual_btn_content = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        manual_btn_content.append(Gtk.Image.new_from_icon_name("list-add-symbolic"))
        manual_btn_content.append(Gtk.Label(label="Add Manually (Advanced)"))
        manual_btn.set_child(manual_btn_content)
        manual_btn.add_css_class("flat")
        manual_btn.connect("clicked", self._on_add_project_manually)
        button_box.append(manual_btn)
    
    def _build_developer_kit_section(self, content_box):
        """Build the Developer Kit export/import section."""
        kit_group = Adw.PreferencesGroup()
        kit_group.set_title("Developer Kit")
        kit_group.set_description("Export your dev setup to USB, import on fresh installs")
        content_box.append(kit_group)
        
        # Export row
        export_row = Adw.ActionRow()
        export_row.set_title("Export Developer Kit")
        export_row.set_subtitle("Save SSH keys, Git identity, and project list to a folder")
        export_row.add_prefix(Gtk.Image.new_from_icon_name("drive-removable-media-symbolic"))
        
        export_btn = Gtk.Button(label="Export")
        export_btn.set_valign(Gtk.Align.CENTER)
        export_btn.connect("clicked", self._on_export_dev_kit)
        export_row.add_suffix(export_btn)
        export_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        export_row.set_activatable(True)
        export_row.connect("activated", lambda r: self._on_export_dev_kit(None))
        kit_group.add(export_row)
        
        # Import row
        import_row = Adw.ActionRow()
        import_row.set_title("Import Developer Kit")
        import_row.set_subtitle("Restore your dev setup from a previous export")
        import_row.add_prefix(Gtk.Image.new_from_icon_name("document-open-symbolic"))
        
        import_btn = Gtk.Button(label="Import")
        import_btn.set_valign(Gtk.Align.CENTER)
        import_btn.connect("clicked", self._on_import_dev_kit)
        import_row.add_suffix(import_btn)
        import_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        import_row.set_activatable(True)
        import_row.connect("activated", lambda r: self._on_import_dev_kit(None))
        kit_group.add(import_row)
    
    def _build_other_git_tools(self, content_box):
        """Build other git tools section."""
        git_group = Adw.PreferencesGroup()
        git_group.set_title("Other Git Tools")
        content_box.append(git_group)
        
        # Update from ZIP
        update_row = Adw.ActionRow()
        update_row.set_title("Update Project from ZIP")
        update_row.set_subtitle("Safely update a git project from a downloaded ZIP file")
        update_row.add_prefix(Gtk.Image.new_from_icon_name("package-x-generic-symbolic"))
        update_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        update_row.set_activatable(True)
        update_row.connect("activated", self._on_update_from_zip_clicked)
        git_group.add(update_row)
        
        # Clone Git Repository
        clone_row = Adw.ActionRow()
        clone_row.set_title("Clone Git Repository")
        clone_row.set_subtitle("Download a new project from GitHub, GitLab, etc.")
        clone_row.add_prefix(Gtk.Image.new_from_icon_name("folder-download-symbolic"))
        clone_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        clone_row.set_activatable(True)
        clone_row.connect("activated", self._on_clone_repo_clicked)
        git_group.add(clone_row)
        
        # Restore SSH Keys
        ssh_row = Adw.ActionRow()
        ssh_row.set_title("Restore SSH Keys")
        ssh_row.set_subtitle("Drag and drop your backed up SSH keys")
        ssh_row.add_prefix(Gtk.Image.new_from_icon_name("channel-secure-symbolic"))
        ssh_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        ssh_row.set_activatable(True)
        ssh_row.connect("activated", self._on_restore_ssh_clicked)
        git_group.add(ssh_row)
    
    def _load_projects(self):
        """Load saved projects and display them."""
        self.projects = load_saved_projects()
        self._refresh_project_list()
    
    def _refresh_project_list(self):
        """Refresh the project list display."""
        # Clear existing project rows
        for path, row in list(self.project_rows.items()):
            self.projects_group.remove(row)
        self.project_rows.clear()
        
        # Filter to only valid repos
        valid_projects = [p for p in self.projects if is_git_repo(p)]
        
        if valid_projects:
            self.empty_state_box.set_visible(False)
            
            for path in valid_projects:
                row = self._create_project_row(path)
                if row:
                    self.projects_group.add(row)
                    self.project_rows[path] = row
        else:
            self._build_empty_state()  # Rebuild to reflect current state
            self.empty_state_box.set_visible(True)
        
        # Save cleaned up list
        if valid_projects != self.projects:
            self.projects = valid_projects
            save_projects(self.projects)
    
    def _create_project_row(self, path: str) -> Optional[Adw.ExpanderRow]:
        """Create an expander row for a git project."""
        info = get_git_info(path)
        if not info:
            return None
        
        # Main row
        row = Adw.ExpanderRow()
        row.set_title(info.name)
        
        # Build subtitle with status
        status_parts = []
        status_parts.append(f"📁 {info.branch}")
        
        if info.has_changes:
            status_parts.append("📝 Changes")
        if info.ahead > 0:
            status_parts.append(f"⬆️ {info.ahead} ahead")
        if info.behind > 0:
            status_parts.append(f"⬇️ {info.behind} behind")
        
        if not info.has_changes and info.ahead == 0 and info.behind == 0:
            status_parts.append("✓ Up to date")
        
        row.set_subtitle(" • ".join(status_parts))
        
        # Icon based on status
        if info.has_changes or info.ahead > 0:
            row.add_prefix(Gtk.Image.new_from_icon_name("document-modified-symbolic"))
        elif info.behind > 0:
            row.add_prefix(Gtk.Image.new_from_icon_name("emblem-synchronizing-symbolic"))
        else:
            row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
        
        # Quick action buttons (in the row itself)
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        button_box.set_valign(Gtk.Align.CENTER)
        
        # Pull button with label
        pull_btn = Gtk.Button()
        pull_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        pull_box.append(Gtk.Image.new_from_icon_name("go-down-symbolic"))
        pull_box.append(Gtk.Label(label="Pull"))
        pull_btn.set_child(pull_box)
        pull_btn.set_tooltip_text("Pull latest changes from remote")
        pull_btn.connect("clicked", lambda b: self._on_pull_project(path, row))
        button_box.append(pull_btn)
        
        # Push button with label
        push_btn = Gtk.Button()
        push_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        push_box.append(Gtk.Image.new_from_icon_name("go-up-symbolic"))
        push_box.append(Gtk.Label(label="Push"))
        push_btn.set_child(push_box)
        push_btn.set_tooltip_text("Push your changes to remote")
        if not info.has_changes and info.ahead == 0:
            push_btn.set_sensitive(False)
            push_btn.set_tooltip_text("Nothing to push")
        push_btn.connect("clicked", lambda b: self._on_push_project(path, row))
        button_box.append(push_btn)
        
        row.add_suffix(button_box)
        
        # Expanded content - details
        details_row = Adw.ActionRow()
        details_row.set_title("Path")
        details_row.set_subtitle(path)
        row.add_row(details_row)
        
        if info.remote_url:
            remote_row = Adw.ActionRow()
            remote_row.set_title("Remote")
            # Shorten URL for display
            display_url = info.remote_url
            if len(display_url) > 50:
                display_url = display_url[:47] + "..."
            remote_row.set_subtitle(display_url)
            row.add_row(remote_row)
        
        if info.last_commit:
            commit_row = Adw.ActionRow()
            commit_row.set_title("Last Commit")
            commit_row.set_subtitle(info.last_commit)
            row.add_row(commit_row)
        
        # Action buttons row
        actions_row = Adw.ActionRow()
        actions_row.set_title("Actions")
        
        action_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        action_box.set_valign(Gtk.Align.CENTER)
        
        # Install to System (if install.sh exists)
        install_script = os.path.join(path, 'install.sh')
        if os.path.exists(install_script):
            install_btn = Gtk.Button(label="Install to System")
            install_btn.add_css_class("suggested-action")
            install_btn.set_tooltip_text("Run install.sh to update system installation")
            install_btn.connect("clicked", lambda b: self._install_to_system(path))
            action_box.append(install_btn)
        
        # Open in file manager
        open_btn = Gtk.Button(label="Open Folder")
        open_btn.connect("clicked", lambda b: self._open_in_file_manager(path))
        action_box.append(open_btn)
        
        # Open terminal here
        term_btn = Gtk.Button(label="Terminal")
        term_btn.connect("clicked", lambda b: self._open_terminal(path))
        action_box.append(term_btn)
        
        # Remove from list
        remove_btn = Gtk.Button()
        remove_btn.set_icon_name("user-trash-symbolic")
        remove_btn.set_tooltip_text("Remove from list")
        remove_btn.add_css_class("flat")
        remove_btn.connect("clicked", lambda b: self._on_remove_project(path))
        action_box.append(remove_btn)
        
        actions_row.add_suffix(action_box)
        row.add_row(actions_row)
        
        # Store info reference
        row.git_info = info
        
        return row
    
    def _on_scan_projects(self, button):
        """Scan for git projects."""
        button.set_sensitive(False)
        
        def scan_thread():
            found = scan_for_git_repos()
            GLib.idle_add(self._on_scan_complete, found, button)
        
        threading.Thread(target=scan_thread, daemon=True).start()
    
    def _on_scan_complete(self, found: List[str], button):
        """Handle scan completion."""
        button.set_sensitive(True)
        
        # Merge with existing
        new_projects = set(self.projects) | set(found)
        self.projects = sorted(new_projects)
        save_projects(self.projects)
        self._refresh_project_list()
        
        new_count = len(found) - len(set(found) & set(self.projects))
        if found:
            self.window.show_toast(f"Found {len(found)} git repositories")
        else:
            # Show helpful message since empty state will guide them
            self.window.show_toast("No git repositories found - see options below")
    
    def _on_create_dev_folder(self, button):
        """Create the ~/Development folder."""
        dev_folder = os.path.expanduser("~/Development")
        try:
            os.makedirs(dev_folder, exist_ok=True)
            self.window.show_toast("Created ~/Development - ready to clone projects!")
            self._refresh_project_list()  # Rebuild empty state
        except Exception as e:
            self.window.show_toast(f"Failed to create folder: {e}")
    
    def _on_add_project_manually(self, button):
        """Show dialog to add project manually."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Git Project Folder")
        
        # Start in Development folder if it exists
        dev_folder = os.path.expanduser("~/Development")
        if os.path.isdir(dev_folder):
            dialog.set_initial_folder(Gio.File.new_for_path(dev_folder))
        
        dialog.select_folder(self.window, None, self._on_folder_selected)
    
    def _on_folder_selected(self, dialog, result):
        """Handle folder selection."""
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                path = folder.get_path()
                
                if not is_git_repo(path):
                    self.window.show_toast("Not a git repository")
                    return
                
                if path not in self.projects:
                    self.projects.append(path)
                    save_projects(self.projects)
                    self._refresh_project_list()
                    self.window.show_toast(f"Added {os.path.basename(path)}")
                else:
                    self.window.show_toast("Project already in list")
        except Exception as e:
            pass  # User cancelled
    
    def _on_refresh_projects(self, button):
        """Refresh all project statuses."""
        button.set_sensitive(False)
        
        def refresh_thread():
            GLib.idle_add(self._on_refresh_complete, button)
        
        threading.Thread(target=refresh_thread, daemon=True).start()
    
    def _on_refresh_complete(self, button):
        """Handle refresh completion."""
        self._refresh_project_list()
        button.set_sensitive(True)
        self.window.show_toast("Projects refreshed")
    
    def _on_remove_project(self, path: str):
        """Remove a project from the list."""
        if path in self.projects:
            self.projects.remove(path)
            save_projects(self.projects)
            self._refresh_project_list()
            self.window.show_toast("Removed from list")
    
    def _on_pull_project(self, path: str, row):
        """Pull latest changes for a project."""
        # Check prerequisites
        ssh_exists, _, _, _ = check_ssh_keys_exist()
        if not ssh_exists:
            self.window.show_toast("SSH keys required - set up keys first")
            return
        
        self._pull_via_terminal(path)
    
    def _pull_via_terminal(self, path: str):
        """Open terminal to run git pull (allows passphrase entry)."""
        project_name = os.path.basename(path)
        agent_info = os.path.expanduser("~/.ssh/agent-info")
        
        # Create a script that pulls and waits for user to see result
        pull_script = f'''# Load SSH agent if available
if [ -f "{agent_info}" ]; then
    source "{agent_info}" 2>/dev/null
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Pulling {project_name}..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
cd "{path}"
if git pull; then
    echo ""
    echo "✓ Pull successful!"
else
    echo ""
    echo "✗ Pull failed"
fi
echo ""
echo "Press Enter to close..."
read'''
        
        # Find available terminal
        terminals = [
            ('kgx', ['kgx', '-e', 'bash', '-c', pull_script]),  # GNOME Console (Fedora)
            ('ptyxis', ['ptyxis', '-e', 'bash', '-c', pull_script]),  # New GNOME Terminal
            ('konsole', ['konsole', '-e', 'bash', '-c', pull_script]),
            ('gnome-terminal', ['gnome-terminal', '--', 'bash', '-c', pull_script]),
            ('xfce4-terminal', ['xfce4-terminal', '-e', f'bash -c \'{pull_script}\'']),
            ('tilix', ['tilix', '-e', f'bash -c "{pull_script}"']),
            ('alacritty', ['alacritty', '-e', 'bash', '-c', pull_script]),
            ('kitty', ['kitty', 'bash', '-c', pull_script]),
            ('xterm', ['xterm', '-e', 'bash', '-c', pull_script]),
        ]
        
        for term_name, term_cmd in terminals:
            try:
                if subprocess.run(['which', term_name], capture_output=True).returncode == 0:
                    subprocess.Popen(term_cmd)
                    self.window.show_toast(f"Terminal opened - enter passphrase if prompted")
                    
                    # Refresh after a delay to catch the pull result
                    GLib.timeout_add(3000, self._refresh_project_list)
                    return
            except Exception:
                continue
        
        self.window.show_toast("Could not find terminal emulator")
    
    def _on_push_project(self, path: str, row):
        """Push changes for a project."""
        # Check prerequisites
        ssh_exists, _, _, _ = check_ssh_keys_exist()
        if not ssh_exists:
            self.window.show_toast("SSH keys required - set up keys first")
            return
        
        info = get_git_info(path)
        if not info:
            self.window.show_toast("Could not read project info")
            return
        
        # Show commit message dialog if there are changes
        if info.has_changes:
            dialog = CommitPushDialog(self.window, path, info, self._on_commit_push_complete)
            dialog.present(self.window)
        elif info.ahead > 0:
            # Just push existing commits
            self._do_push(path)
        else:
            self.window.show_toast("Nothing to push")
    
    def _on_commit_push_complete(self, path: str, message: str):
        """Handle commit/push dialog completion."""
        self._do_commit_and_push(path, message)
    
    def _do_commit_and_push(self, path: str, message: str):
        """Commit all changes and push using terminal for passphrase."""
        # Stage and commit first (these don't need passphrase)
        try:
            subprocess.run(['git', '-C', path, 'add', '-A'], check=True)
            subprocess.run(
                ['git', '-C', path, 'commit', '-m', message],
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError as e:
            self.window.show_toast(f"Commit failed: {e}")
            return
        
        # Now push via terminal so user can enter passphrase
        self._push_via_terminal(path)
    
    def _do_push(self, path: str):
        """Push existing commits via terminal."""
        self._push_via_terminal(path)
    
    def _push_via_terminal(self, path: str):
        """Open terminal to run git push (allows passphrase entry)."""
        project_name = os.path.basename(path)
        agent_info = os.path.expanduser("~/.ssh/agent-info")
        
        # Create a script that pushes and waits for user to see result
        push_script = f'''# Load SSH agent if available
if [ -f "{agent_info}" ]; then
    source "{agent_info}" 2>/dev/null
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Pushing {project_name}..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
cd "{path}"
if git push; then
    echo ""
    echo "✓ Push successful!"
else
    echo ""
    echo "✗ Push failed"
fi
echo ""
echo "Press Enter to close..."
read'''
        
        # Find available terminal
        terminals = [
            ('kgx', ['kgx', '-e', 'bash', '-c', push_script]),  # GNOME Console (Fedora)
            ('ptyxis', ['ptyxis', '-e', 'bash', '-c', push_script]),  # New GNOME Terminal
            ('konsole', ['konsole', '-e', 'bash', '-c', push_script]),
            ('gnome-terminal', ['gnome-terminal', '--', 'bash', '-c', push_script]),
            ('xfce4-terminal', ['xfce4-terminal', '-e', f'bash -c \'{push_script}\'']),
            ('tilix', ['tilix', '-e', f'bash -c "{push_script}"']),
            ('alacritty', ['alacritty', '-e', 'bash', '-c', push_script]),
            ('kitty', ['kitty', 'bash', '-c', push_script]),
            ('xterm', ['xterm', '-e', 'bash', '-c', push_script]),
        ]
        
        for term_name, term_cmd in terminals:
            try:
                if subprocess.run(['which', term_name], capture_output=True).returncode == 0:
                    subprocess.Popen(term_cmd)
                    self.window.show_toast(f"Terminal opened - enter passphrase if prompted")
                    
                    # Refresh after a delay to catch the push result
                    GLib.timeout_add(3000, self._refresh_project_list)
                    return
            except Exception:
                continue
        
        self.window.show_toast("Could not find terminal emulator")
    
    def _on_git_operation_complete(self, success: bool, message: str, path: str):
        """Handle git operation completion."""
        self.window.show_toast(message)
        if success:
            self._refresh_project_list()
    
    def _open_in_file_manager(self, path: str):
        """Open project folder in file manager."""
        try:
            subprocess.Popen(['xdg-open', path])
        except Exception:
            self.window.show_toast("Could not open file manager")
    
    def _open_terminal(self, path: str):
        """Open terminal in project folder."""
        terminals = ['kgx', 'ptyxis', 'gnome-terminal', 'konsole', 'xfce4-terminal', 'tilix', 'alacritty', 'kitty', 'xterm']
        
        for term in terminals:
            try:
                if subprocess.run(['which', term], capture_output=True).returncode == 0:
                    if term == 'gnome-terminal':
                        subprocess.Popen([term, '--working-directory', path])
                    elif term == 'konsole':
                        subprocess.Popen([term, '--workdir', path])
                    elif term in ('kgx', 'ptyxis'):
                        subprocess.Popen([term], cwd=path)
                    else:
                        subprocess.Popen([term], cwd=path)
                    return
            except Exception:
                continue
        
        self.window.show_toast("Could not find terminal emulator")
    
    def _install_to_system(self, path: str):
        """Run install.sh to update the system installation."""
        project_name = os.path.basename(path)
        install_script = os.path.join(path, 'install.sh')
        
        if not os.path.exists(install_script):
            self.window.show_toast("No install.sh found in project")
            return
        
        # Run install via terminal
        install_cmd = f'''echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Installing {project_name} to System..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
cd "{path}"
sudo bash install.sh
echo ""
echo "✓ Installation complete!"
echo ""
echo "Restart the app from your menu to use the new version."
echo ""
echo "Press Enter to close..."
read'''
        
        terminals = [
            ('kgx', ['kgx', '-e', 'bash', '-c', install_cmd]),  # GNOME Console (Fedora)
            ('ptyxis', ['ptyxis', '-e', 'bash', '-c', install_cmd]),  # New GNOME Terminal
            ('konsole', ['konsole', '-e', 'bash', '-c', install_cmd]),
            ('gnome-terminal', ['gnome-terminal', '--', 'bash', '-c', install_cmd]),
            ('xfce4-terminal', ['xfce4-terminal', '-e', f'bash -c \'{install_cmd}\'']),
            ('tilix', ['tilix', '-e', f'bash -c "{install_cmd}"']),
            ('alacritty', ['alacritty', '-e', 'bash', '-c', install_cmd]),
            ('kitty', ['kitty', 'bash', '-c', install_cmd]),
            ('xterm', ['xterm', '-e', 'bash', '-c', install_cmd]),
        ]
        
        for term_name, term_cmd in terminals:
            try:
                if subprocess.run(['which', term_name], capture_output=True).returncode == 0:
                    subprocess.Popen(term_cmd)
                    self.window.show_toast("Terminal opened - enter sudo password")
                    return
            except Exception:
                continue
        
        self.window.show_toast("Could not find terminal emulator")
    
    def _on_configure_git_identity(self, button):
        """Show dialog to configure git identity."""
        dialog = GitIdentityDialog(self.window, self._on_identity_configured)
        dialog.present(self.window)
    
    def _on_identity_configured(self, name, email):
        """Handle identity configuration success."""
        self.window.show_toast("Git identity configured!")
        # Refresh the prerequisites section to show the green checkmark
        self._refresh_prereq_section()
    
    def _on_clone_repo_clicked(self, row):
        """Show git clone dialog."""
        from .setup_tools import GitCloneDialog
        dialog = GitCloneDialog(self.window, self.distro)
        dialog.present(self.window)
    
    def _on_restore_ssh_clicked(self, button_or_row):
        """Show SSH key restore dialog."""
        from .setup_tools import SSHKeyRestoreDialog
        dialog = SSHKeyRestoreDialog(self.window, self.distro)
        dialog.present(self.window)
    
    def _on_update_from_zip_clicked(self, row):
        """Show dialog to update a project from a ZIP file."""
        dialog = UpdateFromZipDialog(self.window, self.projects, self._on_update_from_zip_complete)
        dialog.present(self.window)
    
    def _on_update_from_zip_complete(self):
        """Handle update from ZIP completion."""
        self._refresh_project_list()
        self.window.show_toast("Project updated! Review changes and push when ready.")
    
    # ==================== Developer Kit Export/Import ====================
    
    def _show_update_workflow_help(self, button):
        """Show a dialog explaining the update workflow."""
        dialog = Adw.Dialog()
        dialog.set_title("How to Update Your Project")
        dialog.set_content_width(500)
        dialog.set_content_height(450)
        
        toolbar_view = Adw.ToolbarView()
        dialog.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        
        close_btn = Gtk.Button(label="Got it!")
        close_btn.add_css_class("suggested-action")
        close_btn.connect("clicked", lambda b: dialog.close())
        header.pack_end(close_btn)
        
        toolbar_view.add_top_bar(header)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_top(20)
        content.set_margin_bottom(20)
        content.set_margin_start(20)
        content.set_margin_end(20)
        toolbar_view.set_content(content)
        
        # Workflow steps
        help_text = Gtk.Label()
        help_text.set_markup(
            "<b>Updating from a Downloaded ZIP</b>\n\n"
            
            "<b>Step 1: Update Files</b>\n"
            "• Scroll down to 'Other Git Tools'\n"
            "• Click 'Update Project from ZIP'\n"
            "• Select your downloaded ZIP file\n"
            "• Select your project and click 'Update Project'\n"
            "• Click '← Back to Push'\n\n"
            
            "<b>Step 2: Push to Git</b>\n"
            "• Find your project in Git Projects\n"
            "• Click the 'Push' button\n"
            "• Enter your SSH passphrase in the terminal\n"
            "• Press Enter to close terminal\n\n"
            
            "<b>Step 3: Install to System</b>\n"
            "• Click the arrow on your project to expand it\n"
            "• Click 'Install to System' button\n"
            "• Enter your sudo password\n"
            "• Press Enter to close terminal\n\n"
            
            "<b>Step 4: Restart</b>\n"
            "• Close the app\n"
            "• Relaunch from your app menu\n"
            "• You're now running the new version!"
        )
        help_text.set_halign(Gtk.Align.START)
        help_text.set_wrap(True)
        content.append(help_text)
        
        dialog.present(self.window)

    def _on_export_dev_kit(self, button):
        """Export Developer Kit to a folder."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Export Location")
        dialog.set_initial_name("developer_kit")
        
        # Default to home directory
        dialog.set_initial_folder(Gio.File.new_for_path(os.path.expanduser("~")))
        
        dialog.select_folder(self.window, None, self._on_export_folder_selected)
    
    def _on_export_folder_selected(self, dialog, result):
        """Handle export folder selection."""
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                parent_path = folder.get_path()
                kit_path = os.path.join(parent_path, f"developer_kit_{datetime.now().strftime('%Y%m%d')}")
                self._do_export_dev_kit(kit_path)
        except Exception as e:
            if "dismissed" not in str(e).lower():
                self.window.show_toast(f"Export cancelled")
    
    def _do_export_dev_kit(self, kit_path: str):
        """Perform the Developer Kit export."""
        try:
            os.makedirs(kit_path, exist_ok=True)
            
            results = []
            manifest = {
                'version': 1,
                'created': datetime.now().isoformat(),
                'contents': []
            }
            
            # Export SSH keys
            ssh_exists, key_type, private_path, public_path = check_ssh_keys_exist()
            if ssh_exists:
                ssh_dir = os.path.join(kit_path, 'ssh_keys')
                os.makedirs(ssh_dir, exist_ok=True)
                
                # Copy keys
                shutil.copy2(private_path, os.path.join(ssh_dir, os.path.basename(private_path)))
                shutil.copy2(public_path, os.path.join(ssh_dir, os.path.basename(public_path)))
                
                manifest['contents'].append('ssh_keys')
                results.append(f"✓ SSH keys ({key_type})")
            else:
                results.append("✗ No SSH keys to export")
            
            # Export Git config
            git_configured, name, email = check_git_config()
            if git_configured:
                git_config = {'name': name, 'email': email}
                with open(os.path.join(kit_path, 'git_config.json'), 'w') as f:
                    json.dump(git_config, f, indent=2)
                manifest['contents'].append('git_config')
                results.append(f"✓ Git identity ({name})")
            else:
                results.append("✗ No Git identity to export")
            
            # Export project list (just the remote URLs, not local paths)
            if self.projects:
                project_remotes = []
                for path in self.projects:
                    info = get_git_info(path)
                    if info and info.remote_url:
                        project_remotes.append({
                            'name': info.name,
                            'remote_url': info.remote_url
                        })
                
                if project_remotes:
                    with open(os.path.join(kit_path, 'projects.json'), 'w') as f:
                        json.dump({'projects': project_remotes}, f, indent=2)
                    manifest['contents'].append('projects')
                    results.append(f"✓ Project list ({len(project_remotes)} repos)")
            
            # Write manifest
            with open(os.path.join(kit_path, DEV_KIT_MANIFEST), 'w') as f:
                json.dump(manifest, f, indent=2)
            
            # Show result dialog
            result_dialog = Adw.AlertDialog(
                heading="Developer Kit Exported!",
                body=f"Saved to:\n{kit_path}\n\n" + "\n".join(results) + 
                     "\n\n⚠️ Keep this safe - contains your SSH keys!"
            )
            result_dialog.add_response("ok", "OK")
            result_dialog.present(self.window)
            
        except Exception as e:
            self.window.show_toast(f"Export failed: {e}")
    
    def _on_import_dev_kit(self, button):
        """Import Developer Kit from a folder."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Developer Kit Folder")
        
        dialog.select_folder(self.window, None, self._on_import_folder_selected)
    
    def _on_import_folder_selected(self, dialog, result):
        """Handle import folder selection."""
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                kit_path = folder.get_path()
                self._do_import_dev_kit(kit_path)
        except Exception as e:
            if "dismissed" not in str(e).lower():
                self.window.show_toast(f"Import cancelled")
    
    def _do_import_dev_kit(self, kit_path: str):
        """Perform the Developer Kit import."""
        # Check for manifest
        manifest_path = os.path.join(kit_path, DEV_KIT_MANIFEST)
        if not os.path.exists(manifest_path):
            self.window.show_toast("Not a valid Developer Kit folder")
            return
        
        try:
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            results = []
            
            # Import SSH keys
            ssh_dir = os.path.join(kit_path, 'ssh_keys')
            if 'ssh_keys' in manifest.get('contents', []) and os.path.isdir(ssh_dir):
                dest_ssh_dir = os.path.expanduser("~/.ssh")
                os.makedirs(dest_ssh_dir, exist_ok=True)
                os.chmod(dest_ssh_dir, stat.S_IRWXU)  # 700
                
                for key_file in os.listdir(ssh_dir):
                    src = os.path.join(ssh_dir, key_file)
                    dst = os.path.join(dest_ssh_dir, key_file)
                    
                    # Don't overwrite existing keys without confirmation
                    if os.path.exists(dst):
                        results.append(f"⚠️ Skipped {key_file} (already exists)")
                        continue
                    
                    shutil.copy2(src, dst)
                    
                    # Set proper permissions
                    if key_file.endswith('.pub'):
                        os.chmod(dst, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)  # 644
                    else:
                        os.chmod(dst, stat.S_IRUSR | stat.S_IWUSR)  # 600
                    
                    results.append(f"✓ Imported {key_file}")
            
            # Import Git config
            git_config_path = os.path.join(kit_path, 'git_config.json')
            if 'git_config' in manifest.get('contents', []) and os.path.exists(git_config_path):
                with open(git_config_path, 'r') as f:
                    git_config = json.load(f)
                
                if git_config.get('name'):
                    subprocess.run(['git', 'config', '--global', 'user.name', git_config['name']], check=True)
                if git_config.get('email'):
                    subprocess.run(['git', 'config', '--global', 'user.email', git_config['email']], check=True)
                
                results.append(f"✓ Git identity: {git_config.get('name', 'Unknown')}")
            
            # Show project list (user can clone from here)
            projects_path = os.path.join(kit_path, 'projects.json')
            imported_projects = []
            if 'projects' in manifest.get('contents', []) and os.path.exists(projects_path):
                with open(projects_path, 'r') as f:
                    projects_data = json.load(f)
                
                imported_projects = projects_data.get('projects', [])
                project_count = len(imported_projects)
                results.append(f"✓ Found {project_count} project(s) to clone")
            
            # Show result dialog with next steps
            result_dialog = Adw.AlertDialog(
                heading="Developer Kit Imported!",
                body="\n".join(results) + "\n\n📋 Next Steps:\n1. Unlock your SSH key\n2. Clone your repositories"
            )
            result_dialog.add_response("close", "Close")
            result_dialog.add_response("unlock", "Unlock SSH Key")
            result_dialog.set_response_appearance("unlock", Adw.ResponseAppearance.SUGGESTED)
            result_dialog.set_default_response("unlock")
            
            # Store projects for cloning
            self._imported_projects = imported_projects
            
            result_dialog.connect("response", self._on_import_dialog_response)
            result_dialog.present(self.window)
            
            # Refresh the UI
            self._refresh_project_list()
            
        except Exception as e:
            self.window.show_toast(f"Import failed: {e}")
    
    def _on_import_dialog_response(self, dialog, response):
        """Handle import dialog response."""
        if response == "unlock":
            # Trigger SSH unlock, then show clone dialog
            self._unlock_and_clone()
    
    def _unlock_and_clone(self):
        """Unlock SSH key and then offer to clone projects."""
        # Check for SSH key
        ssh_key_path = os.path.expanduser("~/.ssh/id_ed25519")
        if not os.path.exists(ssh_key_path):
            ssh_key_path = os.path.expanduser("~/.ssh/id_rsa")
        
        if not os.path.exists(ssh_key_path):
            self.window.show_toast("No SSH key found")
            return
        
        # Create dialog for passphrase
        passphrase_dialog = Adw.AlertDialog(
            heading="Unlock SSH Key",
            body="Enter your SSH key passphrase to unlock and clone repositories:"
        )
        
        # Add password entry
        entry = Gtk.PasswordEntry()
        entry.set_show_peek_icon(True)
        entry.set_margin_top(12)
        entry.set_margin_start(12)
        entry.set_margin_end(12)
        passphrase_dialog.set_extra_child(entry)
        
        passphrase_dialog.add_response("cancel", "Cancel")
        passphrase_dialog.add_response("unlock", "Unlock & Clone")
        passphrase_dialog.set_response_appearance("unlock", Adw.ResponseAppearance.SUGGESTED)
        passphrase_dialog.set_default_response("unlock")
        
        # Store entry reference
        self._passphrase_entry = entry
        
        passphrase_dialog.connect("response", self._on_unlock_clone_response)
        passphrase_dialog.present(self.window)
    
    def _on_unlock_clone_response(self, dialog, response):
        """Handle unlock and clone response."""
        if response != "unlock":
            return
        
        passphrase = self._passphrase_entry.get_text()
        
        # Find SSH key
        ssh_key_path = os.path.expanduser("~/.ssh/id_ed25519")
        if not os.path.exists(ssh_key_path):
            ssh_key_path = os.path.expanduser("~/.ssh/id_rsa")
        
        # Run ssh-add in terminal with the passphrase
        def do_unlock():
            try:
                import subprocess
                import os
                
                # Start ssh-agent and get its output
                agent_result = subprocess.run(
                    ['ssh-agent', '-s'],
                    capture_output=True,
                    text=True
                )
                
                # Parse SSH_AUTH_SOCK and SSH_AGENT_PID
                env = os.environ.copy()
                for line in agent_result.stdout.split('\n'):
                    if 'SSH_AUTH_SOCK' in line:
                        sock = line.split('=')[1].split(';')[0]
                        env['SSH_AUTH_SOCK'] = sock
                    elif 'SSH_AGENT_PID' in line:
                        pid = line.split('=')[1].split(';')[0]
                        env['SSH_AGENT_PID'] = pid
                
                # Save agent info for later
                agent_info_path = os.path.expanduser("~/.ssh/agent-info")
                with open(agent_info_path, 'w') as f:
                    f.write(f"SSH_AUTH_SOCK={env.get('SSH_AUTH_SOCK', '')}\n")
                    f.write(f"SSH_AGENT_PID={env.get('SSH_AGENT_PID', '')}\n")
                
                # Add key using expect-like approach
                add_proc = subprocess.Popen(
                    ['ssh-add', ssh_key_path],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    text=True
                )
                stdout, stderr = add_proc.communicate(input=passphrase + '\n', timeout=10)
                
                if add_proc.returncode == 0:
                    # Add GitHub to known hosts
                    subprocess.run(
                        ['ssh-keyscan', '-t', 'ed25519', 'github.com'],
                        stdout=open(os.path.expanduser('~/.ssh/known_hosts'), 'a'),
                        stderr=subprocess.DEVNULL,
                        env=env
                    )
                    
                    GLib.idle_add(self._ssh_unlocked_success, env)
                else:
                    GLib.idle_add(lambda: self.window.show_toast("Failed to unlock SSH key"))
                    
            except Exception as e:
                GLib.idle_add(lambda: self.window.show_toast(f"Error: {e}"))
        
        threading.Thread(target=do_unlock, daemon=True).start()
    
    def _ssh_unlocked_success(self, env):
        """SSH unlocked successfully, now offer to clone."""
        self.window.show_toast("SSH key unlocked!")
        
        # Store env for cloning
        self._ssh_env = env
        
        # Check if we have projects to clone
        if hasattr(self, '_imported_projects') and self._imported_projects:
            # Show clone dialog
            self._show_clone_projects_dialog()
        else:
            # Just refresh
            self._refresh_prereq_section()
    
    def _show_clone_projects_dialog(self):
        """Show dialog to clone imported projects."""
        projects = self._imported_projects
        
        # Create dialog
        clone_dialog = Adw.AlertDialog(
            heading="Clone Projects?",
            body=f"Found {len(projects)} project(s) from your Developer Kit:\n\n" +
                 "\n".join([f"• {p.get('name', 'Unknown')}" for p in projects[:5]]) +
                 ("\n..." if len(projects) > 5 else "") +
                 "\n\nClone them now?"
        )
        
        clone_dialog.add_response("cancel", "Later")
        clone_dialog.add_response("clone", "Clone All")
        clone_dialog.set_response_appearance("clone", Adw.ResponseAppearance.SUGGESTED)
        
        clone_dialog.connect("response", self._on_clone_projects_response)
        clone_dialog.present(self.window)
    
    def _on_clone_projects_response(self, dialog, response):
        """Handle clone projects response."""
        if response != "clone":
            return
        
        # Create ~/Development if needed
        dev_dir = os.path.expanduser("~/Development")
        os.makedirs(dev_dir, exist_ok=True)
        
        # Clone each project
        def do_clone():
            cloned = 0
            failed = 0
            
            env = getattr(self, '_ssh_env', os.environ.copy())
            # Also load from agent-info file
            agent_info = os.path.expanduser("~/.ssh/agent-info")
            if os.path.exists(agent_info):
                with open(agent_info, 'r') as f:
                    for line in f:
                        if '=' in line:
                            key, val = line.strip().split('=', 1)
                            env[key] = val
            
            for project in self._imported_projects:
                name = project.get('name', '')
                url = project.get('remote_url', '')
                
                if not url:
                    continue
                
                dest = os.path.join(dev_dir, name)
                
                if os.path.exists(dest):
                    # Already exists, skip
                    continue
                
                try:
                    result = subprocess.run(
                        ['git', 'clone', url, dest],
                        capture_output=True,
                        text=True,
                        env=env,
                        timeout=120
                    )
                    if result.returncode == 0:
                        cloned += 1
                    else:
                        failed += 1
                except:
                    failed += 1
            
            GLib.idle_add(lambda: self._clone_complete(cloned, failed))
        
        self.window.show_toast("Cloning projects...")
        threading.Thread(target=do_clone, daemon=True).start()
    
    def _clone_complete(self, cloned, failed):
        """Clone operation complete."""
        if failed == 0:
            self.window.show_toast(f"✓ Cloned {cloned} project(s)!")
        else:
            self.window.show_toast(f"Cloned {cloned}, failed {failed}")
        
        # Refresh project list
        self._refresh_project_list()


class CommitPushDialog(Adw.Dialog):
    """Dialog for entering commit message before pushing."""
    
    def __init__(self, parent, path: str, info: GitProject, on_commit_callback=None):
        super().__init__()
        
        self.project_path = path
        self.info = info
        self.on_commit_callback = on_commit_callback
        
        self.set_title(f"Push {info.name}")
        self.set_content_width(450)
        self.set_content_height(300)
        
        self._build_ui()
    
    def _build_ui(self):
        """Build dialog UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_btn)
        
        push_btn = Gtk.Button(label="Commit & Push")
        push_btn.add_css_class("suggested-action")
        push_btn.connect("clicked", self._on_push)
        header.pack_end(push_btn)
        self.push_btn = push_btn
        
        toolbar_view.add_top_bar(header)
        
        # Content
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_top(20)
        content.set_margin_bottom(20)
        content.set_margin_start(20)
        content.set_margin_end(20)
        toolbar_view.set_content(content)
        
        # Info
        info_label = Gtk.Label()
        info_label.set_markup(
            f"<b>{self.info.name}</b> on <tt>{self.info.branch}</tt>\n"
            f"<small>You have uncommitted changes to push.</small>"
        )
        info_label.set_halign(Gtk.Align.START)
        content.append(info_label)
        
        # Commit message
        msg_group = Adw.PreferencesGroup()
        msg_group.set_title("Commit Message")
        content.append(msg_group)
        
        self.message_entry = Adw.EntryRow()
        self.message_entry.set_title("Message")
        self.message_entry.set_text("Update")
        self.message_entry.connect("changed", self._validate)
        msg_group.add(self.message_entry)
        
        # Hint
        hint = Gtk.Label()
        hint.set_markup("<small>Tip: Use a descriptive message like 'v5.7.1: Fix bug in login'</small>")
        hint.add_css_class("dim-label")
        hint.set_halign(Gtk.Align.START)
        content.append(hint)
    
    def _validate(self, entry):
        """Validate commit message."""
        message = self.message_entry.get_text().strip()
        self.push_btn.set_sensitive(bool(message))
    
    def _on_push(self, button):
        """Handle push button."""
        if self.on_commit_callback:
            message = self.get_commit_message()
            self.on_commit_callback(self.project_path, message)
        self.close()
    
    def get_commit_message(self) -> str:
        """Get the commit message."""
        return self.message_entry.get_text().strip()


class GitIdentityDialog(Adw.Dialog):
    """Dialog for configuring git identity."""
    
    def __init__(self, parent, on_success_callback=None):
        super().__init__()
        
        self.window = parent
        self.on_success_callback = on_success_callback
        
        self.set_title("Configure Git Identity")
        self.set_content_width(400)
        self.set_content_height(250)
        
        self._build_ui()
    
    def _build_ui(self):
        """Build dialog UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_btn)
        
        save_btn = Gtk.Button(label="Save")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self._on_save)
        header.pack_end(save_btn)
        self.save_btn = save_btn
        
        toolbar_view.add_top_bar(header)
        
        # Content
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_top(20)
        content.set_margin_bottom(20)
        content.set_margin_start(20)
        content.set_margin_end(20)
        toolbar_view.set_content(content)
        
        # Identity group
        group = Adw.PreferencesGroup()
        group.set_title("Git Identity")
        group.set_description("Used for commit author information")
        content.append(group)
        
        # Get current values
        _, current_name, current_email = check_git_config()
        
        self.name_entry = Adw.EntryRow()
        self.name_entry.set_title("Name")
        self.name_entry.set_text(current_name or "")
        group.add(self.name_entry)
        
        self.email_entry = Adw.EntryRow()
        self.email_entry.set_title("Email")
        self.email_entry.set_text(current_email or "")
        group.add(self.email_entry)
    
    def _on_save(self, button):
        """Save git identity."""
        name = self.name_entry.get_text().strip()
        email = self.email_entry.get_text().strip()
        
        try:
            if name:
                subprocess.run(['git', 'config', '--global', 'user.name', name], check=True)
            if email:
                subprocess.run(['git', 'config', '--global', 'user.email', email], check=True)
            
            self.close()
            if self.on_success_callback:
                self.on_success_callback(name, email)
        except Exception as e:
            print(f"Failed to set git config: {e}")
            if self.window:
                self.window.show_toast(f"Failed to configure git: {e}")


class UpdateFromZipDialog(Adw.Dialog):
    """Dialog for updating a git project from a downloaded ZIP file."""
    
    def __init__(self, parent, projects: List[str], on_complete_callback=None):
        super().__init__()
        
        self.parent_window = parent
        self.projects = projects
        self.on_complete_callback = on_complete_callback
        self.selected_project = None
        self.selected_zip = None
        
        self.set_title("Update Project from ZIP")
        self.set_content_width(550)
        self.set_content_height(500)
        
        self._build_ui()
    
    def _build_ui(self):
        """Build dialog UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        self.header = header  # Save reference for later
        
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_btn)
        
        self.update_btn = Gtk.Button(label="Update Project")
        self.update_btn.add_css_class("suggested-action")
        self.update_btn.set_sensitive(False)
        self.update_btn.connect("clicked", self._on_update_clicked)
        header.pack_end(self.update_btn)
        
        toolbar_view.add_top_bar(header)
        
        # Content
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content.set_margin_top(20)
        content.set_margin_bottom(20)
        content.set_margin_start(20)
        content.set_margin_end(20)
        toolbar_view.set_content(content)
        
        # Instructions
        info_label = Gtk.Label()
        info_label.set_markup(
            "<b>Update a Git project from a ZIP file</b>\n"
            "<small>This safely updates your project while preserving git history.\n"
            "Your .git folder stays intact - just the source files are replaced.</small>"
        )
        info_label.set_halign(Gtk.Align.START)
        info_label.set_wrap(True)
        content.append(info_label)
        
        # Step 1: Select ZIP file
        zip_group = Adw.PreferencesGroup()
        zip_group.set_title("Step 1: Select ZIP File")
        content.append(zip_group)
        
        self.zip_row = Adw.ActionRow()
        self.zip_row.set_title("ZIP File")
        self.zip_row.set_subtitle("No file selected")
        self.zip_row.add_prefix(Gtk.Image.new_from_icon_name("package-x-generic-symbolic"))
        
        browse_btn = Gtk.Button(label="Browse")
        browse_btn.set_valign(Gtk.Align.CENTER)
        browse_btn.connect("clicked", self._on_browse_zip)
        self.zip_row.add_suffix(browse_btn)
        zip_group.add(self.zip_row)
        
        # Step 2: Select target project
        project_group = Adw.PreferencesGroup()
        project_group.set_title("Step 2: Select Target Project")
        content.append(project_group)
        
        if self.projects:
            for project_path in self.projects:
                project_name = os.path.basename(project_path)
                row = Adw.ActionRow()
                row.set_title(project_name)
                row.set_subtitle(project_path)
                row.add_prefix(Gtk.Image.new_from_icon_name("folder-symbolic"))
                
                # Radio-style selection
                check = Gtk.CheckButton()
                check.set_valign(Gtk.Align.CENTER)
                check.connect("toggled", self._on_project_selected, project_path)
                
                # Group the checkbuttons
                if hasattr(self, 'first_check'):
                    check.set_group(self.first_check)
                else:
                    self.first_check = check
                
                row.add_suffix(check)
                row.set_activatable(True)
                row.connect("activated", lambda r, c=check: c.set_active(True))
                project_group.add(row)
        else:
            empty_row = Adw.ActionRow()
            empty_row.set_title("No projects found")
            empty_row.set_subtitle("Add projects via Scan or Add Manually first")
            project_group.add(empty_row)
        
        # Status area
        self.status_group = Adw.PreferencesGroup()
        self.status_group.set_title("Status")
        self.status_group.set_visible(False)
        content.append(self.status_group)
        
        self.status_label = Gtk.Label()
        self.status_label.set_wrap(True)
        self.status_label.set_halign(Gtk.Align.START)
        self.status_group.add(self.status_label)
    
    def _on_browse_zip(self, button):
        """Browse for ZIP file."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Select ZIP File")
        
        # Filter for ZIP files
        filter_zip = Gtk.FileFilter()
        filter_zip.set_name("ZIP Archives")
        filter_zip.add_pattern("*.zip")
        
        filter_list = Gio.ListStore.new(Gtk.FileFilter)
        filter_list.append(filter_zip)
        dialog.set_filters(filter_list)
        dialog.set_default_filter(filter_zip)
        
        # Start in Downloads
        downloads = os.path.expanduser("~/Downloads")
        if os.path.isdir(downloads):
            dialog.set_initial_folder(Gio.File.new_for_path(downloads))
        
        dialog.open(self.parent_window, None, self._on_zip_selected)
    
    def _on_zip_selected(self, dialog, result):
        """Handle ZIP file selection."""
        try:
            file = dialog.open_finish(result)
            if file:
                self.selected_zip = file.get_path()
                self.zip_row.set_subtitle(os.path.basename(self.selected_zip))
                self._validate()
        except Exception:
            pass  # User cancelled
    
    def _on_project_selected(self, check, project_path):
        """Handle project selection."""
        if check.get_active():
            self.selected_project = project_path
            self._validate()
    
    def _validate(self):
        """Check if we can proceed."""
        valid = self.selected_zip and self.selected_project
        self.update_btn.set_sensitive(valid)
    
    def _on_update_clicked(self, button):
        """Perform the update."""
        if not self.selected_zip or not self.selected_project:
            return
        
        button.set_sensitive(False)
        button.set_label("Updating...")
        self.status_group.set_visible(True)
        self.status_label.set_text("Starting update...")
        
        # Run in thread
        def update_thread():
            try:
                results = self._do_update()
                GLib.idle_add(self._on_update_complete, True, results)
            except Exception as e:
                GLib.idle_add(self._on_update_complete, False, str(e))
        
        threading.Thread(target=update_thread, daemon=True).start()
    
    def _do_update(self) -> str:
        """Perform the actual update. Returns status message."""
        import zipfile
        import tempfile
        
        results = []
        project_path = self.selected_project
        zip_path = self.selected_zip
        
        # Verify .git exists
        git_dir = os.path.join(project_path, '.git')
        if not os.path.isdir(git_dir):
            raise Exception("Not a git repository - .git folder not found!")
        
        results.append("✓ Verified .git folder exists")
        
        # Create temp directory for extraction
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extract ZIP
            GLib.idle_add(lambda: self.status_label.set_text("Extracting ZIP..."))
            
            with zipfile.ZipFile(zip_path, 'r') as zf:
                zf.extractall(temp_dir)
            
            results.append("✓ Extracted ZIP file")
            
            # Find the source directory (handle nested folder in ZIP)
            extracted_items = os.listdir(temp_dir)
            if len(extracted_items) == 1 and os.path.isdir(os.path.join(temp_dir, extracted_items[0])):
                source_dir = os.path.join(temp_dir, extracted_items[0])
            else:
                source_dir = temp_dir
            
            results.append(f"✓ Found source: {os.path.basename(source_dir)}")
            
            # Get list of items to preserve
            preserve = ['.git']
            
            # Get list of items to remove (everything except .git)
            GLib.idle_add(lambda: self.status_label.set_text("Removing old files..."))
            
            for item in os.listdir(project_path):
                if item not in preserve:
                    item_path = os.path.join(project_path, item)
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
            
            results.append("✓ Removed old files (preserved .git)")
            
            # Copy new files
            GLib.idle_add(lambda: self.status_label.set_text("Copying new files..."))
            
            for item in os.listdir(source_dir):
                src = os.path.join(source_dir, item)
                dst = os.path.join(project_path, item)
                
                if os.path.isdir(src):
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)
            
            results.append("✓ Copied new files")
        
        # Fix execute permissions on scripts
        GLib.idle_add(lambda: self.status_label.set_text("Setting permissions..."))
        
        executable_files = ['install.sh', 'tux-helper', 'tux-assistant.py']
        for exe_file in executable_files:
            exe_path = os.path.join(project_path, exe_file)
            if os.path.exists(exe_path):
                os.chmod(exe_path, 0o755)
        
        results.append("✓ Fixed execute permissions")
        
        # Check git status
        result = subprocess.run(
            ['git', '-C', project_path, 'status', '--porcelain'],
            capture_output=True, text=True
        )
        
        changed_files = len(result.stdout.strip().split('\n')) if result.stdout.strip() else 0
        results.append(f"✓ Git sees {changed_files} changed files")
        
        return "\n".join(results)
    
    def _on_update_complete(self, success: bool, message: str):
        """Handle update completion."""
        self.update_btn.set_label("Update Project")
        
        if success:
            self.status_label.set_markup(
                f"<b>Update Complete!</b>\n\n{message}\n\n"
                "<small><b>Next steps:</b>\n"
                "1. Click '← Back to Push' below\n"
                "2. Click the Push button on your project\n"
                "3. Expand the project row and click 'Install to System'</small>"
            )
            
            # Change Update button to "Back to Push"
            self.update_btn.set_label("← Back to Push")
            self.update_btn.set_sensitive(True)
            self.update_btn.disconnect_by_func(self._on_update_clicked)
            self.update_btn.connect("clicked", lambda b: self.close())
            
            if self.on_complete_callback:
                self.on_complete_callback()
        else:
            self.status_label.set_markup(f"<b>Update Failed</b>\n\n{message}")
            self.update_btn.set_sensitive(True)
