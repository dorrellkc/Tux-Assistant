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
        """Build the simplified Tux Assistant development section."""
        # Check if we're in the Tux Assistant repo
        ta_repo_path = self._find_tux_assistant_repo()
        if not ta_repo_path:
            return  # Don't show section if not found
        
        self.ta_repo_path = ta_repo_path
        
        # Get current status
        version = self._get_ta_version()
        branch = self._get_ta_branch()
        ssh_status = self._check_ssh_agent_status()
        ssh_ok = "Unlocked" in ssh_status
        
        # Create the section
        ta_group = Adw.PreferencesGroup()
        ta_group.set_title("🐧 Tux Assistant Development")
        content_box.append(ta_group)
        
        # Status row - shows version, branch, SSH
        status_row = Adw.ActionRow()
        status_row.set_title(f"Version {version}")
        
        status_parts = [f"Branch: {branch}"]
        status_parts.append(f"SSH: {'✓ Ready' if ssh_ok else '🔒 Locked'}")
        status_row.set_subtitle(" • ".join(status_parts))
        
        if ssh_ok:
            status_row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
        else:
            status_row.add_prefix(Gtk.Image.new_from_icon_name("dialog-password-symbolic"))
        
        # Unlock SSH button (only show if locked)
        if not ssh_ok:
            unlock_btn = Gtk.Button(label="Unlock SSH")
            unlock_btn.add_css_class("suggested-action")
            unlock_btn.set_tooltip_text("Required before publishing")
            unlock_btn.set_valign(Gtk.Align.CENTER)
            unlock_btn.connect("clicked", self._on_unlock_ssh_key)
            status_row.add_suffix(unlock_btn)
        
        # Refresh button
        refresh_btn = Gtk.Button()
        refresh_btn.set_icon_name("view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh status")
        refresh_btn.add_css_class("flat")
        refresh_btn.set_valign(Gtk.Align.CENTER)
        refresh_btn.connect("clicked", self._on_ta_refresh_status)
        status_row.add_suffix(refresh_btn)
        
        ta_group.add(status_row)
        self.ta_status_row = status_row
        self.ta_ssh_row = status_row  # For compatibility with refresh
        self.ta_branch_row = status_row  # For compatibility with refresh
        
        # Dev Sync row - shows GitHub/AUR sync status
        sync_row = Adw.ActionRow()
        sync_row.set_title("🔄 Dev Sync")
        
        # Get sync status
        sync_status = self._get_sync_status()
        sync_row.set_subtitle(sync_status['message'])
        
        if sync_status['state'] == 'in_sync':
            sync_row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
        elif sync_status['state'] == 'repo_outdated':
            sync_row.add_prefix(Gtk.Image.new_from_icon_name("dialog-warning-symbolic"))
            sync_btn = Gtk.Button(label="Sync Repo")
            sync_btn.add_css_class("destructive-action")
            sync_btn.set_tooltip_text("Copy installed version to repo")
            sync_btn.set_valign(Gtk.Align.CENTER)
            sync_btn.connect("clicked", self._on_sync_repo_from_installed)
            sync_row.add_suffix(sync_btn)
        elif sync_status['state'] == 'behind':
            sync_row.add_prefix(Gtk.Image.new_from_icon_name("software-update-available-symbolic"))
            pull_btn = Gtk.Button(label="Pull")
            pull_btn.add_css_class("suggested-action")
            pull_btn.set_tooltip_text("Pull latest from GitHub")
            pull_btn.set_valign(Gtk.Align.CENTER)
            pull_btn.connect("clicked", self._on_ta_pull_dev)
            sync_row.add_suffix(pull_btn)
        elif sync_status['state'] == 'ahead':
            sync_row.add_prefix(Gtk.Image.new_from_icon_name("send-to-symbolic"))
            push_btn = Gtk.Button(label="Push")
            push_btn.add_css_class("suggested-action")
            push_btn.set_tooltip_text("Push to GitHub")
            push_btn.set_valign(Gtk.Align.CENTER)
            push_btn.connect("clicked", self._on_ta_push_dev)
            sync_row.add_suffix(push_btn)
        elif sync_status['state'] == 'aur_behind':
            sync_row.add_prefix(Gtk.Image.new_from_icon_name("software-update-available-symbolic"))
            aur_btn = Gtk.Button(label="Update AUR")
            aur_btn.add_css_class("suggested-action")
            aur_btn.set_tooltip_text("Publish to AUR")
            aur_btn.set_valign(Gtk.Align.CENTER)
            aur_btn.connect("clicked", self._on_publish_to_aur)
            sync_row.add_suffix(aur_btn)
        elif sync_status['state'] == 'dirty':
            sync_row.add_prefix(Gtk.Image.new_from_icon_name("document-edit-symbolic"))
        else:
            sync_row.add_prefix(Gtk.Image.new_from_icon_name("dialog-question-symbolic"))
        
        ta_group.add(sync_row)
        self.sync_row = sync_row
        
        # Install from ZIP row
        install_row = Adw.ActionRow()
        install_row.set_title("📥 Install from ZIP")
        install_row.set_subtitle("Extract source from Claude and install locally")
        install_row.add_prefix(Gtk.Image.new_from_icon_name("package-x-generic-symbolic"))
        
        install_btn = Gtk.Button(label="Choose ZIP & Install")
        install_btn.add_css_class("suggested-action")
        install_btn.set_tooltip_text("Select ZIP file, extract, and run install.sh")
        install_btn.set_valign(Gtk.Align.CENTER)
        install_btn.connect("clicked", self._on_install_from_zip)
        install_row.add_suffix(install_btn)
        
        ta_group.add(install_row)
        
        # Publish Release row
        publish_row = Adw.ActionRow()
        publish_row.set_title("🚀 Publish Release")
        publish_row.set_subtitle("Commit → Push → Build .run → Create GitHub Release")
        publish_row.add_prefix(Gtk.Image.new_from_icon_name("send-to-symbolic"))
        
        publish_btn = Gtk.Button(label=f"Publish v{version}")
        publish_btn.add_css_class("destructive-action")
        publish_btn.set_tooltip_text("Full release workflow in one click")
        publish_btn.set_valign(Gtk.Align.CENTER)
        publish_btn.connect("clicked", self._on_full_publish_release)
        publish_row.add_suffix(publish_btn)
        
        ta_group.add(publish_row)
        
        # Publish to AUR row
        aur_row = Adw.ActionRow()
        aur_row.set_title("📦 Publish to AUR")
        aur_row.set_subtitle("Generate PKGBUILD and push to Arch User Repository")
        aur_row.add_prefix(Gtk.Image.new_from_icon_name("software-update-available-symbolic"))
        
        aur_btn = Gtk.Button(label=f"Publish v{version} to AUR")
        aur_btn.add_css_class("suggested-action")
        aur_btn.set_tooltip_text("Create/update AUR package")
        aur_btn.set_valign(Gtk.Align.CENTER)
        aur_btn.connect("clicked", self._on_publish_to_aur)
        aur_row.add_suffix(aur_btn)
        
        ta_group.add(aur_row)
        
        # ═══ Build for Debian/Ubuntu ═══
        deb_group = Adw.PreferencesGroup()
        deb_group.set_title("📦 Build for Debian/Ubuntu")
        deb_group.set_description("Create .deb package for apt-based distributions")
        content_box.append(deb_group)
        
        deb_row = Adw.ActionRow()
        deb_row.set_title("Debian Package (.deb)")
        deb_row.set_subtitle("Works with: Debian, Ubuntu, Linux Mint, Pop!_OS")
        deb_row.add_prefix(Gtk.Image.new_from_icon_name("package-x-generic-symbolic"))
        
        deb_btn = Gtk.Button(label=f"Build v{version} .deb")
        deb_btn.add_css_class("suggested-action")
        deb_btn.set_valign(Gtk.Align.CENTER)
        deb_btn.connect("clicked", lambda b: self._on_build_package("deb"))
        deb_row.add_suffix(deb_btn)
        
        deb_group.add(deb_row)
        
        # ═══ Build for Fedora ═══
        fedora_group = Adw.PreferencesGroup()
        fedora_group.set_title("📦 Build for Fedora")
        fedora_group.set_description("Create .rpm package for Fedora")
        content_box.append(fedora_group)
        
        fedora_row = Adw.ActionRow()
        fedora_row.set_title("Fedora Package (.rpm)")
        fedora_row.set_subtitle("Works with: Fedora, RHEL, CentOS, Rocky Linux")
        fedora_row.add_prefix(Gtk.Image.new_from_icon_name("package-x-generic-symbolic"))
        
        fedora_btn = Gtk.Button(label=f"Build v{version} .rpm")
        fedora_btn.add_css_class("suggested-action")
        fedora_btn.set_valign(Gtk.Align.CENTER)
        fedora_btn.connect("clicked", lambda b: self._on_build_package("fedora"))
        fedora_row.add_suffix(fedora_btn)
        
        fedora_group.add(fedora_row)
        
        # ═══ Build for openSUSE ═══
        suse_group = Adw.PreferencesGroup()
        suse_group.set_title("📦 Build for openSUSE")
        suse_group.set_description("Create .rpm package for openSUSE")
        content_box.append(suse_group)
        
        suse_row = Adw.ActionRow()
        suse_row.set_title("openSUSE Package (.rpm)")
        suse_row.set_subtitle("Works with: openSUSE Tumbleweed, Leap")
        suse_row.add_prefix(Gtk.Image.new_from_icon_name("package-x-generic-symbolic"))
        
        suse_btn = Gtk.Button(label=f"Build v{version} .rpm")
        suse_btn.add_css_class("suggested-action")
        suse_btn.set_valign(Gtk.Align.CENTER)
        suse_btn.connect("clicked", lambda b: self._on_build_package("suse"))
        suse_row.add_suffix(suse_btn)
        
        suse_group.add(suse_row)
        
        # ═══ Build All Packages ═══
        build_all_group = Adw.PreferencesGroup()
        build_all_group.set_title("📦 Build All Release Packages")
        build_all_group.set_description("Create all packages in one go for distribution")
        content_box.append(build_all_group)
        
        build_all_row = Adw.ActionRow()
        build_all_row.set_title("Build Complete Release")
        build_all_row.set_subtitle(".run + .deb + Fedora .rpm + openSUSE .rpm")
        build_all_row.add_prefix(Gtk.Image.new_from_icon_name("folder-download-symbolic"))
        
        build_all_btn = Gtk.Button(label=f"Build All v{version}")
        build_all_btn.add_css_class("suggested-action")
        build_all_btn.set_valign(Gtk.Align.CENTER)
        build_all_btn.connect("clicked", self._on_build_all_packages)
        build_all_row.add_suffix(build_all_btn)
        
        build_all_group.add(build_all_row)
        
        build_all_info = Adw.ActionRow()
        build_all_info.set_title("Output Location")
        build_all_info.set_subtitle(f"~/Tux-Assistant-Releases/v{version}/")
        build_all_info.add_prefix(Gtk.Image.new_from_icon_name("folder-symbolic"))
        build_all_group.add(build_all_info)
        
        # ═══ Publish Full Release ═══
        full_release_group = Adw.PreferencesGroup()
        full_release_group.set_title("🚀 Publish Full Release")
        full_release_group.set_description("Push to GitHub and upload all packages as release assets")
        content_box.append(full_release_group)
        
        full_release_row = Adw.ActionRow()
        full_release_row.set_title("Publish Complete Release")
        full_release_row.set_subtitle("Commit → Push → Build All → Create GitHub Release")
        full_release_row.add_prefix(Gtk.Image.new_from_icon_name("send-to-symbolic"))
        
        full_release_btn = Gtk.Button(label=f"Publish v{version}")
        full_release_btn.add_css_class("destructive-action")
        full_release_btn.set_valign(Gtk.Align.CENTER)
        full_release_btn.connect("clicked", self._on_full_release_all)
        full_release_row.add_suffix(full_release_btn)
        
        full_release_group.add(full_release_row)
        
        # Help link (small, at bottom)
        help_row = Adw.ActionRow()
        help_row.set_title("Need help?")
        help_row.set_subtitle("View the Git workflow guide")
        help_row.add_prefix(Gtk.Image.new_from_icon_name("help-about-symbolic"))
        help_row.set_activatable(True)
        help_row.connect("activated", self._on_show_git_help)
        
        chevron = Gtk.Image.new_from_icon_name("go-next-symbolic")
        chevron.add_css_class("dim-label")
        help_row.add_suffix(chevron)
        
        ta_group.add(help_row)
    
    def _get_ta_version(self) -> str:
        """Get current version from VERSION file."""
        try:
            version_file = os.path.join(self.ta_repo_path, 'VERSION')
            with open(version_file, 'r') as f:
                return f.read().strip()
        except:
            return "unknown"
    
    def _on_install_from_zip(self, button):
        """Open file picker and install from ZIP."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Tux Assistant Source ZIP")
        
        # Filter for ZIP files
        filter_zip = Gtk.FileFilter()
        filter_zip.set_name("ZIP files")
        filter_zip.add_pattern("*.zip")
        filter_zip.add_pattern("tux-assistant*.zip")
        
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_zip)
        dialog.set_filters(filters)
        dialog.set_default_filter(filter_zip)
        
        # Start in Downloads folder
        downloads = os.path.expanduser("~/Downloads")
        if os.path.exists(downloads):
            dialog.set_initial_folder(Gio.File.new_for_path(downloads))
        
        dialog.open(self.window, None, self._on_zip_selected)
    
    def _on_zip_selected(self, dialog, result):
        """Handle ZIP file selection."""
        try:
            file = dialog.open_finish(result)
            if file:
                zip_path = file.get_path()
                self._do_install_from_zip(zip_path)
        except GLib.Error as e:
            if e.code != Gtk.DialogError.DISMISSED:
                self.window.show_toast(f"Error: {e.message}")
    
    def _do_install_from_zip(self, zip_path: str):
        """Extract ZIP and install."""
        self.window.show_toast("Installing from ZIP...")
        
        def do_install():
            try:
                import zipfile
                import shutil
                
                # 1. Clean /tmp/tux-assistant
                tmp_dir = "/tmp/tux-assistant"
                if os.path.exists(tmp_dir):
                    shutil.rmtree(tmp_dir)
                
                # 2. Extract ZIP to /tmp
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall("/tmp")
                
                # Check if extraction created the folder
                if not os.path.exists(tmp_dir):
                    GLib.idle_add(self.window.show_toast, "ZIP doesn't contain tux-assistant folder")
                    return
                
                # 3. Copy to repo
                for item in os.listdir(tmp_dir):
                    src = os.path.join(tmp_dir, item)
                    dst = os.path.join(self.ta_repo_path, item)
                    if os.path.isdir(src):
                        if os.path.exists(dst):
                            shutil.rmtree(dst)
                        shutil.copytree(src, dst)
                    else:
                        shutil.copy2(src, dst)
                
                # 4. Run install.sh
                install_script = os.path.join(self.ta_repo_path, 'install.sh')
                if os.path.exists(install_script):
                    result = subprocess.run(
                        ['pkexec', 'bash', install_script],
                        cwd=self.ta_repo_path,
                        capture_output=True,
                        text=True,
                        timeout=120
                    )
                    
                    if result.returncode == 0:
                        # Get new version
                        version = self._get_ta_version()
                        GLib.idle_add(self.window.show_toast, f"✅ Installed v{version}!")
                        GLib.idle_add(self._on_ta_refresh_status, None)
                    else:
                        GLib.idle_add(self.window.show_toast, "Install failed - check terminal")
                else:
                    GLib.idle_add(self.window.show_toast, "install.sh not found")
                    
            except Exception as e:
                GLib.idle_add(self.window.show_toast, f"Error: {str(e)[:50]}")
        
        threading.Thread(target=do_install, daemon=True).start()
    
    def _on_full_publish_release(self, button):
        """Full publish workflow: commit, push, build, gh release."""
        # Check SSH first
        ssh_status = self._check_ssh_agent_status()
        if "Unlocked" not in ssh_status:
            self.window.show_toast("Please unlock SSH key first")
            return
        
        # Check if gh is installed
        gh_check = subprocess.run(['which', 'gh'], capture_output=True)
        if gh_check.returncode != 0:
            dialog = Adw.AlertDialog()
            dialog.set_heading("GitHub CLI Required")
            dialog.set_body(
                "Install 'gh' to publish releases:\n\n"
                "Fedora: sudo dnf install gh\n"
                "Arch: sudo pacman -S github-cli\n"
                "Ubuntu: sudo apt install gh\n\n"
                "Then run: gh auth login"
            )
            dialog.add_response("ok", "OK")
            dialog.present(self.window)
            return
        
        # Get version
        version = self._get_ta_version()
        
        # Prompt for commit message
        dialog = Adw.AlertDialog()
        dialog.set_heading(f"Publish v{version} to GitHub?")
        dialog.set_body("This will:\n• Commit all changes\n• Push to GitHub\n• Build .run installer\n• Create GitHub Release")
        
        # Add entry for commit message
        entry = Gtk.Entry()
        entry.set_text(f"v{version}")
        entry.set_placeholder_text("Commit message")
        entry.set_margin_top(12)
        entry.set_margin_start(12)
        entry.set_margin_end(12)
        dialog.set_extra_child(entry)
        
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("publish", "Publish")
        dialog.set_response_appearance("publish", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("publish")
        
        dialog.connect("response", self._do_full_publish, entry, version)
        dialog.present(self.window)
    
    def _do_full_publish(self, dialog, response, entry, version):
        """Execute the full publish workflow."""
        if response != "publish":
            return
        
        commit_msg = entry.get_text().strip() or f"v{version}"
        self.window.show_toast("Publishing release...")
        
        def do_publish():
            try:
                ssh_env = self._get_ssh_env()
                
                # 1. Git add and commit
                subprocess.run(['git', 'add', '.'], cwd=self.ta_repo_path, timeout=30)
                
                commit_result = subprocess.run(
                    ['git', 'commit', '-m', commit_msg],
                    cwd=self.ta_repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                # Check if there was nothing to commit (that's OK)
                if commit_result.returncode != 0 and "nothing to commit" not in commit_result.stdout:
                    if "nothing to commit" not in commit_result.stderr:
                        GLib.idle_add(self.window.show_toast, "Commit failed")
                        return
                
                # 2. Git push
                GLib.idle_add(self.window.show_toast, "Pushing to GitHub...")
                push_result = subprocess.run(
                    ['git', 'push', 'origin', 'main'],
                    cwd=self.ta_repo_path,
                    env=ssh_env,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if push_result.returncode != 0:
                    error = push_result.stderr[:50] if push_result.stderr else "Unknown error"
                    GLib.idle_add(self.window.show_toast, f"Push failed: {error}")
                    return
                
                # 3. Build .run
                GLib.idle_add(self.window.show_toast, "Building .run installer...")
                build_script = os.path.join(self.ta_repo_path, 'scripts', 'build-run.sh')
                
                # Make sure it's executable
                os.chmod(build_script, 0o755)
                
                build_result = subprocess.run(
                    ['bash', build_script],
                    cwd=self.ta_repo_path,
                    capture_output=True,
                    text=True,
                    timeout=180
                )
                
                if build_result.returncode != 0:
                    GLib.idle_add(self.window.show_toast, "Build failed")
                    return
                
                # 4. Find the .run file
                run_file = os.path.join(self.ta_repo_path, 'dist', f'Tux-Assistant-v{version}.run')
                if not os.path.exists(run_file):
                    GLib.idle_add(self.window.show_toast, f".run file not found: {run_file}")
                    return
                
                # 5. Create GitHub release
                GLib.idle_add(self.window.show_toast, "Creating GitHub release...")
                release_result = subprocess.run(
                    [
                        'gh', 'release', 'create', f'v{version}',
                        run_file,
                        '--title', f'Tux Assistant v{version}',
                        '--notes', f'{commit_msg}\n\nDownload the .run file and run:\nchmod +x Tux-Assistant-v{version}.run && ./Tux-Assistant-v{version}.run'
                    ],
                    cwd=self.ta_repo_path,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    env=ssh_env
                )
                
                if release_result.returncode == 0:
                    GLib.idle_add(self.window.show_toast, f"🎉 Published v{version} to GitHub!")
                    GLib.idle_add(self._on_ta_refresh_status, None)
                else:
                    error = release_result.stderr[:50] if release_result.stderr else "Unknown error"
                    GLib.idle_add(self.window.show_toast, f"Release failed: {error}")
                    
            except Exception as e:
                GLib.idle_add(self.window.show_toast, f"Error: {str(e)[:50]}")
        
        threading.Thread(target=do_publish, daemon=True).start()
        
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
    
    def _on_publish_to_aur(self, button):
        """Handle AUR publish button click."""
        version = self._get_ta_version()
        
        # Check SSH first
        ssh_status = self._check_ssh_agent_status()
        if "Unlocked" not in ssh_status:
            self.window.show_toast("⚠️ Unlock SSH key first!")
            return
        
        # Check if GitHub release exists (we need the tarball)
        check_result = subprocess.run(
            ['gh', 'release', 'view', f'v{version}'],
            cwd=self.ta_repo_path,
            capture_output=True, text=True, timeout=30
        )
        
        if check_result.returncode != 0:
            self.window.show_toast(f"⚠️ GitHub release v{version} not found. Publish to GitHub first!")
            return
        
        # Show confirmation dialog
        dialog = Adw.AlertDialog()
        dialog.set_heading(f"Publish v{version} to AUR?")
        dialog.set_body(
            "This will:\n\n"
            "• Download source tarball from GitHub\n"
            "• Generate PKGBUILD and .SRCINFO\n"
            "• Push to AUR (ssh://aur@aur.archlinux.org/tux-assistant.git)\n\n"
            "Make sure you have:\n"
            "• AUR account at aur.archlinux.org\n"
            "• SSH key added to AUR account"
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("publish", "Publish to AUR")
        dialog.set_response_appearance("publish", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._do_aur_publish, version)
        dialog.present(self.window)
    
    def _generate_pkgbuild(self, version: str, sha256sum: str) -> str:
        """Generate PKGBUILD content."""
        return f'''# Maintainer: Christopher Dorrell <dorrellkc@gmail.com>
pkgname=tux-assistant
pkgver={version}
pkgrel=1
pkgdesc="GTK4/Libadwaita Linux system configuration tool - simplifies post-installation setup"
arch=('any')
url="https://github.com/dorrellkc/Tux-Assistant"
license=('GPL-3.0-or-later')
depends=(
    'python'
    'python-gobject'
    'gtk4'
    'libadwaita'
    'python-requests'
    'polkit'
    'python-dbus'
    'webkit2gtk-4.1'
    'gstreamer'
    'gst-plugins-base'
    'gst-plugins-good'
    'hicolor-icon-theme'
)
optdepends=(
    'speedtest-cli: for network speed tests'
    'samba: for network file sharing'
    'gnome-shell: for GNOME extension management'
    'gst-plugins-ugly: for additional audio format support'
    'gst-plugins-bad: for additional audio format support'
)
install=tux-assistant.install
source=("$pkgname-$pkgver.tar.gz::https://github.com/dorrellkc/Tux-Assistant/archive/refs/tags/v$pkgver.tar.gz"
        "tux-assistant.install")
sha256sums=('{sha256sum}'
            'SKIP')

package() {{
    cd "$srcdir/Tux-Assistant-$pkgver"
    
    # Install to /opt/tux-assistant
    install -dm755 "$pkgdir/opt/tux-assistant"
    cp -r tux "$pkgdir/opt/tux-assistant/"
    cp -r assets "$pkgdir/opt/tux-assistant/"
    cp -r data "$pkgdir/opt/tux-assistant/"
    cp -r scripts "$pkgdir/opt/tux-assistant/"
    install -Dm755 tux-assistant.py "$pkgdir/opt/tux-assistant/"
    install -Dm755 tux-helper "$pkgdir/opt/tux-assistant/"
    install -Dm644 VERSION "$pkgdir/opt/tux-assistant/"
    
    # Install Tux Assistant launcher script
    install -dm755 "$pkgdir/usr/bin"
    echo '#!/bin/bash' > "$pkgdir/usr/bin/tux-assistant"
    echo 'cd /opt/tux-assistant && python tux-assistant.py "$@"' >> "$pkgdir/usr/bin/tux-assistant"
    chmod 755 "$pkgdir/usr/bin/tux-assistant"
    
    # Install Tux Tunes launcher script
    echo '#!/bin/bash' > "$pkgdir/usr/bin/tux-tunes"
    echo 'python /opt/tux-assistant/tux/apps/tux_tunes/tux-tunes.py "$@"' >> "$pkgdir/usr/bin/tux-tunes"
    chmod 755 "$pkgdir/usr/bin/tux-tunes"
    
    # Install tux-helper to /usr/bin
    install -Dm755 tux-helper "$pkgdir/usr/bin/tux-helper"
    
    # Install desktop files
    install -Dm644 data/com.tuxassistant.app.desktop "$pkgdir/usr/share/applications/com.tuxassistant.app.desktop"
    install -Dm644 data/com.tuxassistant.tuxtunes.desktop "$pkgdir/usr/share/applications/com.tuxassistant.tuxtunes.desktop"
    
    # Install icons
    install -Dm644 assets/icon.svg "$pkgdir/usr/share/icons/hicolor/scalable/apps/tux-assistant.svg"
    install -Dm644 assets/tux-tunes.svg "$pkgdir/usr/share/icons/hicolor/scalable/apps/tux-tunes.svg"
    
    # Install polkit policy
    install -Dm644 data/com.tuxassistant.helper.policy "$pkgdir/usr/share/polkit-1/actions/com.tuxassistant.helper.policy"
}}
'''
    
    def _generate_srcinfo(self, version: str, sha256sum: str) -> str:
        """Generate .SRCINFO content."""
        return f'''pkgbase = tux-assistant
\tpkgdesc = GTK4/Libadwaita Linux system configuration tool - simplifies post-installation setup
\tpkgver = {version}
\tpkgrel = 1
\turl = https://github.com/dorrellkc/Tux-Assistant
\tarch = any
\tlicense = GPL-3.0-or-later
\tinstall = tux-assistant.install
\tdepends = python
\tdepends = python-gobject
\tdepends = gtk4
\tdepends = libadwaita
\tdepends = python-requests
\tdepends = polkit
\tdepends = python-dbus
\tdepends = webkit2gtk-4.1
\tdepends = gstreamer
\tdepends = gst-plugins-base
\tdepends = gst-plugins-good
\tdepends = hicolor-icon-theme
\toptdepends = speedtest-cli: for network speed tests
\toptdepends = samba: for network file sharing
\toptdepends = gnome-shell: for GNOME extension management
\toptdepends = gst-plugins-ugly: for additional audio format support
\toptdepends = gst-plugins-bad: for additional audio format support
\tsource = tux-assistant-{version}.tar.gz::https://github.com/dorrellkc/Tux-Assistant/archive/refs/tags/v{version}.tar.gz
\tsource = tux-assistant.install
\tsha256sums = {sha256sum}
\tsha256sums = SKIP

pkgname = tux-assistant
'''
    
    def _generate_install_hook(self) -> str:
        """Generate tux-assistant.install hook file for icon cache updates."""
        return '''# tux-assistant.install - Post-install hooks for Tux Assistant

post_install() {
    # Update icon cache
    if [ -x /usr/bin/gtk-update-icon-cache ]; then
        gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor
    fi
    
    # Update desktop database
    if [ -x /usr/bin/update-desktop-database ]; then
        update-desktop-database -q /usr/share/applications
    fi
}

post_upgrade() {
    post_install
}

post_remove() {
    post_install
}
'''
    
    def _generate_metainfo_tux_assistant(self, version: str) -> str:
        """Generate AppStream metainfo for Tux Assistant."""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>com.tuxassistant.app</id>
  <name>Tux Assistant</name>
  <summary>Linux system configuration and setup tool</summary>
  <metadata_license>CC0-1.0</metadata_license>
  <project_license>GPL-3.0-or-later</project_license>
  <developer id="com.tuxassistant">
    <name>Christopher Dorrell</name>
  </developer>
  <description>
    <p>
      Tux Assistant is a comprehensive GTK4/Libadwaita system configuration 
      and management application for Linux. It simplifies post-installation 
      setup, software installation, system maintenance, and configuration 
      across multiple distributions.
    </p>
    <p>Features include:</p>
    <ul>
      <li>System setup wizards and configuration tools</li>
      <li>Software center with curated applications</li>
      <li>Gaming setup (Steam, Lutris, gaming utilities)</li>
      <li>Desktop enhancements and theming</li>
      <li>Network configuration and sharing</li>
      <li>Hardware management</li>
      <li>System maintenance and cleanup</li>
    </ul>
  </description>
  <launchable type="desktop-id">com.tuxassistant.app.desktop</launchable>
  <url type="homepage">https://github.com/dorrellkc/Tux-Assistant</url>
  <url type="bugtracker">https://github.com/dorrellkc/Tux-Assistant/issues</url>
  <provides>
    <binary>tux-assistant</binary>
  </provides>
  <requires>
    <display_length compare="ge">768</display_length>
  </requires>
  <supports>
    <control>pointing</control>
    <control>keyboard</control>
    <control>touch</control>
  </supports>
  <categories>
    <category>System</category>
    <category>Settings</category>
    <category>Utility</category>
  </categories>
  <keywords>
    <keyword>linux</keyword>
    <keyword>setup</keyword>
    <keyword>configuration</keyword>
    <keyword>system</keyword>
    <keyword>install</keyword>
  </keywords>
  <releases>
    <release version="{version}" date="{datetime.now().strftime('%Y-%m-%d')}">
      <description>
        <p>Latest release of Tux Assistant</p>
      </description>
    </release>
  </releases>
  <content_rating type="oars-1.1" />
</component>
'''
    
    def _generate_metainfo_tux_tunes(self, version: str) -> str:
        """Generate AppStream metainfo for Tux Tunes."""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<component type="desktop-application">
  <id>com.tuxassistant.tuxtunes</id>
  <name>Tux Tunes</name>
  <summary>Internet radio player with smart recording</summary>
  <metadata_license>CC0-1.0</metadata_license>
  <project_license>GPL-3.0-or-later</project_license>
  <developer id="com.tuxassistant">
    <name>Christopher Dorrell</name>
  </developer>
  <description>
    <p>
      Tux Tunes is a modern internet radio player built with GTK4 and 
      Libadwaita. Listen to thousands of radio stations from around the 
      world with a beautiful, native Linux interface.
    </p>
    <p>Features include:</p>
    <ul>
      <li>Browse and search internet radio stations</li>
      <li>Smart recording with automatic song detection</li>
      <li>Station favorites and history</li>
      <li>Audio visualization</li>
      <li>Clean, modern interface</li>
    </ul>
  </description>
  <launchable type="desktop-id">com.tuxassistant.tuxtunes.desktop</launchable>
  <url type="homepage">https://github.com/dorrellkc/Tux-Assistant</url>
  <url type="bugtracker">https://github.com/dorrellkc/Tux-Assistant/issues</url>
  <provides>
    <binary>tux-tunes</binary>
  </provides>
  <requires>
    <display_length compare="ge">600</display_length>
  </requires>
  <supports>
    <control>pointing</control>
    <control>keyboard</control>
    <control>touch</control>
  </supports>
  <categories>
    <category>AudioVideo</category>
    <category>Audio</category>
    <category>Music</category>
    <category>Player</category>
  </categories>
  <keywords>
    <keyword>radio</keyword>
    <keyword>internet</keyword>
    <keyword>streaming</keyword>
    <keyword>music</keyword>
    <keyword>recording</keyword>
  </keywords>
  <releases>
    <release version="{version}" date="{datetime.now().strftime('%Y-%m-%d')}">
      <description>
        <p>Latest release of Tux Tunes</p>
      </description>
    </release>
  </releases>
  <content_rating type="oars-1.1" />
</component>
'''
    
    def _generate_post_install_script(self) -> str:
        """Generate post-install script for DEB/RPM packages."""
        return '''#!/bin/bash
# Post-install script for Tux Assistant

# Update icon cache
if [ -x /usr/bin/gtk-update-icon-cache ]; then
    gtk-update-icon-cache -q -t -f /usr/share/icons/hicolor 2>/dev/null || true
fi

# Update desktop database
if [ -x /usr/bin/update-desktop-database ]; then
    update-desktop-database -q /usr/share/applications 2>/dev/null || true
fi

# Make launchers executable (just in case)
chmod +x /usr/local/bin/tux-assistant 2>/dev/null || true
chmod +x /usr/local/bin/tux-tunes 2>/dev/null || true
chmod +x /usr/bin/tux-helper 2>/dev/null || true

exit 0
'''
    
    def _do_aur_publish(self, dialog, response, version):
        """Execute AUR publish workflow."""
        if response != "publish":
            return
        
        self.window.show_toast("Preparing AUR package...")
        
        def do_aur_publish():
            try:
                import shutil
                ssh_env = self._get_ssh_env()
                cache_dir = os.path.expanduser("~/.cache/tux-assistant")
                aur_repo = os.path.join(cache_dir, "aur-repo")
                
                # Create cache dir
                os.makedirs(cache_dir, exist_ok=True)
                
                # 1. Download source tarball and calculate sha256
                GLib.idle_add(self.window.show_toast, "Downloading source tarball...")
                tarball_url = f"https://github.com/dorrellkc/Tux-Assistant/archive/refs/tags/v{version}.tar.gz"
                tarball_path = os.path.join(cache_dir, f"tux-assistant-{version}.tar.gz")
                
                # Download with curl
                dl_result = subprocess.run(
                    ['curl', '-L', '-o', tarball_path, tarball_url],
                    capture_output=True, text=True, timeout=120
                )
                
                if dl_result.returncode != 0 or not os.path.exists(tarball_path):
                    GLib.idle_add(self.window.show_toast, "Failed to download tarball")
                    return
                
                # Calculate sha256
                sha_result = subprocess.run(
                    ['sha256sum', tarball_path],
                    capture_output=True, text=True, timeout=30
                )
                
                if sha_result.returncode != 0:
                    GLib.idle_add(self.window.show_toast, "Failed to calculate sha256")
                    return
                
                sha256sum = sha_result.stdout.split()[0]
                
                # 2. Clone or pull AUR repo
                GLib.idle_add(self.window.show_toast, "Syncing AUR repo...")
                
                if os.path.isdir(aur_repo) and os.path.isdir(os.path.join(aur_repo, '.git')):
                    # Pull existing repo - ensure we're on master branch (AUR uses master)
                    subprocess.run(['git', 'checkout', 'master'], cwd=aur_repo, capture_output=True, timeout=10)
                    # Reset any local changes and pull fresh
                    subprocess.run(['git', 'reset', '--hard', 'HEAD'], cwd=aur_repo, capture_output=True, timeout=10)
                    pull_result = subprocess.run(
                        ['git', 'pull', '--rebase', 'origin', 'master'],
                        cwd=aur_repo,
                        env=ssh_env,
                        capture_output=True, text=True, timeout=60
                    )
                    if pull_result.returncode != 0:
                        # Pull failed - delete and re-clone
                        shutil.rmtree(aur_repo)
                        subprocess.run(
                            ['git', 'clone', 'ssh://aur@aur.archlinux.org/tux-assistant.git', 'aur-repo'],
                            cwd=cache_dir,
                            env=ssh_env,
                            capture_output=True, text=True, timeout=60
                        )
                else:
                    # Remove any broken repo dir
                    if os.path.exists(aur_repo):
                        shutil.rmtree(aur_repo)
                    
                    # Clone fresh
                    clone_result = subprocess.run(
                        ['git', 'clone', 'ssh://aur@aur.archlinux.org/tux-assistant.git', 'aur-repo'],
                        cwd=cache_dir,
                        env=ssh_env,
                        capture_output=True, text=True, timeout=60
                    )
                    
                    if clone_result.returncode != 0:
                        GLib.idle_add(self.window.show_toast, f"Clone failed: {clone_result.stderr[:60]}")
                        return
                
                # 3. Generate PKGBUILD, .SRCINFO, and install hook
                GLib.idle_add(self.window.show_toast, "Generating PKGBUILD...")
                
                pkgbuild_content = self._generate_pkgbuild(version, sha256sum)
                srcinfo_content = self._generate_srcinfo(version, sha256sum)
                install_hook_content = self._generate_install_hook()
                
                with open(os.path.join(aur_repo, 'PKGBUILD'), 'w') as f:
                    f.write(pkgbuild_content)
                
                with open(os.path.join(aur_repo, '.SRCINFO'), 'w') as f:
                    f.write(srcinfo_content)
                
                with open(os.path.join(aur_repo, 'tux-assistant.install'), 'w') as f:
                    f.write(install_hook_content)
                
                # 4. Commit and push
                GLib.idle_add(self.window.show_toast, "Pushing to AUR...")
                
                subprocess.run(['git', 'add', 'PKGBUILD', '.SRCINFO', 'tux-assistant.install'], cwd=aur_repo, timeout=10)
                
                commit_result = subprocess.run(
                    ['git', 'commit', '-m', f'Update to v{version}'],
                    cwd=aur_repo,
                    capture_output=True, text=True, timeout=30
                )
                
                # Get current branch name
                branch_result = subprocess.run(
                    ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                    cwd=aur_repo, capture_output=True, text=True, timeout=10
                )
                current_branch = branch_result.stdout.strip() or 'master'
                
                # Push to the current branch (AUR uses master)
                push_result = subprocess.run(
                    ['git', 'push', '-u', 'origin', current_branch],
                    cwd=aur_repo,
                    env=ssh_env,
                    capture_output=True, text=True, timeout=60
                )
                
                if push_result.returncode == 0 or "Everything up-to-date" in push_result.stderr:
                    GLib.idle_add(self.window.show_toast, f"🎉 Published v{version} to AUR!")
                else:
                    error = push_result.stderr[:80] if push_result.stderr else push_result.stdout[:80]
                    GLib.idle_add(self.window.show_toast, f"AUR push failed: {error}")
                    
                # Cleanup tarball
                try:
                    os.remove(tarball_path)
                except:
                    pass
                    
            except Exception as e:
                GLib.idle_add(self.window.show_toast, f"Error: {str(e)[:50]}")
        
        threading.Thread(target=do_aur_publish, daemon=True).start()
    
    def _on_build_package(self, pkg_type: str):
        """Handle package build button click."""
        version = self._get_ta_version()
        
        # Determine package info based on type
        pkg_info = {
            "deb": {
                "name": "Debian/Ubuntu",
                "ext": "deb",
                "filename": f"tux-assistant_{version}_amd64.deb",
                "deps": "python3, python3-gi, gir1.2-gtk-4.0, libadwaita-1-0, gir1.2-adw-1, gstreamer1.0-tools, gir1.2-gst-plugins-base-1.0, gstreamer1.0-plugins-good"
            },
            "fedora": {
                "name": "Fedora",
                "ext": "rpm",
                "filename": f"tux-assistant-{version}-1.fc.x86_64.rpm",
                "deps": "python3, python3-gobject, gtk4, libadwaita, gstreamer1, gstreamer1-plugins-base, gstreamer1-plugins-good"
            },
            "suse": {
                "name": "openSUSE",
                "ext": "rpm",
                "filename": f"tux-assistant-{version}-1.suse.x86_64.rpm",
                "deps": "python3, python3-gobject, gtk4, typelib-1_0-Gtk-4_0, libadwaita, typelib-1_0-Adw-1, gstreamer, gstreamer-plugins-base, gstreamer-plugins-good"
            }
        }
        
        info = pkg_info.get(pkg_type)
        if not info:
            self.window.show_toast("Unknown package type")
            return
        
        # Show confirmation dialog
        dialog = Adw.AlertDialog()
        dialog.set_heading(f"Build {info['name']} Package?")
        dialog.set_body(
            f"This will create:\n"
            f"  • {info['filename']}\n\n"
            f"Output folder:\n"
            f"  ~/Tux-Assistant-Packages/\n\n"
            f"Requires: fpm (Ruby gem)\n"
            f"Will be installed automatically if missing."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("build", f"Build .{info['ext']}")
        dialog.set_response_appearance("build", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("build")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._do_build_package, pkg_type, info, version)
        dialog.present(self.window)
    
    def _do_build_package(self, dialog, response, pkg_type: str, info: dict, version: str):
        """Execute package build."""
        if response != "build":
            return
        
        self.window.show_toast(f"Building {info['name']} package...")
        
        def do_build():
            try:
                import shutil
                import glob
                
                # Output directory
                output_dir = os.path.expanduser("~/Tux-Assistant-Packages")
                os.makedirs(output_dir, exist_ok=True)
                
                # Staging directory
                staging_dir = "/tmp/tux-assistant-pkg-staging"
                if os.path.exists(staging_dir):
                    shutil.rmtree(staging_dir)
                os.makedirs(staging_dir)
                
                # ===== STEP 1: Detect distro and install system dependencies =====
                GLib.idle_add(self.window.show_toast, "Checking system dependencies...")
                
                def detect_distro():
                    """Detect the Linux distribution."""
                    try:
                        with open("/etc/os-release") as f:
                            content = f.read().lower()
                            if "arch" in content or "endeavour" in content or "manjaro" in content:
                                return "arch"
                            elif "fedora" in content or "rhel" in content or "centos" in content or "rocky" in content:
                                return "fedora"
                            elif "opensuse" in content or "suse" in content:
                                return "suse"
                            elif "ubuntu" in content or "debian" in content or "mint" in content or "pop" in content:
                                return "debian"
                    except:
                        pass
                    # Fallback: check for package managers
                    if os.path.exists("/usr/bin/pacman"):
                        return "arch"
                    elif os.path.exists("/usr/bin/dnf"):
                        return "fedora"
                    elif os.path.exists("/usr/bin/zypper"):
                        return "suse"
                    elif os.path.exists("/usr/bin/apt"):
                        return "debian"
                    return "unknown"
                
                distro = detect_distro()
                
                # Define required packages per distro
                # For deb: need ar (binutils)
                # For rpm: need rpmbuild (rpm-build)
                required_packages = {
                    "arch": {
                        "ruby": "ruby",
                        "ar": "binutils",
                        "rpmbuild": "rpm-tools",
                    },
                    "fedora": {
                        "ruby": "ruby",
                        "ar": "binutils",
                        "rpmbuild": "rpm-build",
                    },
                    "suse": {
                        "ruby": "ruby",
                        "ar": "binutils",
                        "rpmbuild": "rpm-build",
                    },
                    "debian": {
                        "ruby": "ruby",
                        "ar": "binutils",
                        "rpmbuild": "rpm",
                    },
                }
                
                pkg_install_cmds = {
                    "arch": ["sudo", "pacman", "-S", "--noconfirm", "--needed"],
                    "fedora": ["sudo", "dnf", "install", "-y"],
                    "suse": ["sudo", "zypper", "--non-interactive", "install"],
                    "debian": ["sudo", "apt", "install", "-y"],
                }
                
                # Determine which tools we need based on package type
                tools_needed = ["ruby"]  # Always need ruby for fpm
                if info["ext"] == "deb":
                    tools_needed.append("ar")
                elif info["ext"] == "rpm":
                    tools_needed.append("rpmbuild")
                
                # Check which tools are missing
                missing_packages = []
                for tool in tools_needed:
                    result = subprocess.run(["which", tool], capture_output=True)
                    if result.returncode != 0:
                        if distro in required_packages and tool in required_packages[distro]:
                            missing_packages.append(required_packages[distro][tool])
                        else:
                            # Fallback package names
                            fallback = {"ruby": "ruby", "ar": "binutils", "rpmbuild": "rpm-build"}
                            if tool in fallback:
                                missing_packages.append(fallback[tool])
                
                # Install missing system packages
                if missing_packages and distro != "unknown":
                    GLib.idle_add(self.window.show_toast, f"Installing: {', '.join(missing_packages)}...")
                    install_cmd = pkg_install_cmds[distro] + missing_packages
                    result = subprocess.run(install_cmd, capture_output=True, text=True, timeout=300)
                    if result.returncode != 0:
                        GLib.idle_add(self._show_pkg_install_error, missing_packages, distro)
                        return
                elif missing_packages and distro == "unknown":
                    GLib.idle_add(self.window.show_toast, f"Please install: {', '.join(missing_packages)}")
                    return
                
                # ===== STEP 2: Find or install fpm =====
                GLib.idle_add(self.window.show_toast, "Checking for fpm...")
                
                def find_fpm():
                    """Find fpm executable."""
                    # Method 1: Check if fpm is in PATH
                    try:
                        result = subprocess.run(["which", "fpm"], capture_output=True, text=True, timeout=5)
                        if result.returncode == 0 and result.stdout.strip():
                            return result.stdout.strip()
                    except:
                        pass
                    
                    # Method 2: Ask Ruby directly where gems are installed
                    try:
                        gem_user = subprocess.run(
                            ["ruby", "-e", "puts Gem.user_dir"],
                            capture_output=True, text=True, timeout=10
                        )
                        if gem_user.returncode == 0 and gem_user.stdout.strip():
                            gem_dir = gem_user.stdout.strip()
                            # Check direct bin path
                            fpm_candidate = os.path.join(gem_dir, "bin", "fpm")
                            if os.path.isfile(fpm_candidate):
                                return fpm_candidate
                            # Check inside gems/fpm-*/bin/ (user install pattern)
                            import glob
                            fpm_glob = os.path.join(gem_dir, "gems", "fpm-*", "bin", "fpm")
                            matches = glob.glob(fpm_glob)
                            if matches:
                                return matches[0]
                    except:
                        pass
                    
                    # Method 3: Check gem environment gempath
                    try:
                        gem_env = subprocess.run(
                            ["gem", "environment", "gempath"],
                            capture_output=True, text=True, timeout=10
                        )
                        if gem_env.returncode == 0 and gem_env.stdout.strip():
                            import glob
                            for path in gem_env.stdout.strip().split(":"):
                                # Direct bin
                                candidate = os.path.join(path, "bin", "fpm")
                                if os.path.isfile(candidate):
                                    return candidate
                                # Inside gems folder
                                fpm_glob = os.path.join(path, "gems", "fpm-*", "bin", "fpm")
                                matches = glob.glob(fpm_glob)
                                if matches:
                                    return matches[0]
                    except:
                        pass
                    
                    # Method 4: Brute force check common locations
                    import glob
                    home = os.path.expanduser("~")
                    for ruby_ver in ["3.4.0", "3.3.0", "3.2.0", "3.1.0", "3.0.0", "2.7.0"]:
                        for base in [".local/share/gem/ruby", ".gem/ruby", ".gems/ruby"]:
                            # Direct bin path
                            candidate = os.path.join(home, base, ruby_ver, "bin", "fpm")
                            if os.path.isfile(candidate):
                                return candidate
                            # Inside gems subfolder
                            fpm_glob = os.path.join(home, base, ruby_ver, "gems", "fpm-*", "bin", "fpm")
                            matches = glob.glob(fpm_glob)
                            if matches:
                                return matches[0]
                    
                    return None
                
                fpm_path = find_fpm()
                
                if not fpm_path:
                    GLib.idle_add(self.window.show_toast, "Installing fpm (this may take a minute)...")
                    # Check for ruby
                    ruby_check = subprocess.run(["which", "ruby"], capture_output=True)
                    if ruby_check.returncode != 0:
                        GLib.idle_add(self.window.show_toast, "Error: Ruby not installed. Install with: sudo pacman -S ruby")
                        return
                    # Install fpm gem
                    result = subprocess.run(
                        ["gem", "install", "--user-install", "fpm"],
                        capture_output=True, text=True, timeout=300
                    )
                    if result.returncode != 0:
                        GLib.idle_add(self.window.show_toast, f"Failed to install fpm: {result.stderr[:50]}")
                        return
                    # Find fpm after install
                    fpm_path = find_fpm()
                    if not fpm_path:
                        # Last resort - get the path directly from gem and USE it
                        try:
                            import glob
                            gem_user = subprocess.run(
                                ["ruby", "-e", "puts Gem.user_dir"],
                                capture_output=True, text=True, timeout=10
                            )
                            gem_dir = gem_user.stdout.strip()
                            # Try direct bin
                            fpm_candidate = os.path.join(gem_dir, "bin", "fpm")
                            if os.path.isfile(fpm_candidate):
                                fpm_path = fpm_candidate
                            else:
                                # Try gems/fpm-*/bin/fpm
                                fpm_glob = os.path.join(gem_dir, "gems", "fpm-*", "bin", "fpm")
                                matches = glob.glob(fpm_glob)
                                if matches:
                                    fpm_path = matches[0]
                                else:
                                    GLib.idle_add(self._show_fpm_path_dialog, gem_dir)
                                    return
                        except:
                            GLib.idle_add(self._show_fpm_error_dialog)
                            return
                
                GLib.idle_add(self.window.show_toast, "Preparing package structure...")
                
                # Create directory structure
                opt_dir = os.path.join(staging_dir, "opt", "tux-assistant")
                bin_dir = os.path.join(staging_dir, "usr", "local", "bin")
                helper_dir = os.path.join(staging_dir, "usr", "bin")
                desktop_dir = os.path.join(staging_dir, "usr", "share", "applications")
                polkit_dir = os.path.join(staging_dir, "usr", "share", "polkit-1", "actions")
                metainfo_dir = os.path.join(staging_dir, "usr", "share", "metainfo")
                icon_base = os.path.join(staging_dir, "usr", "share", "icons", "hicolor")
                
                for d in [opt_dir, bin_dir, helper_dir, desktop_dir, polkit_dir, metainfo_dir]:
                    os.makedirs(d, exist_ok=True)
                
                # Copy application files to /opt/tux-assistant
                src_dir = self.ta_repo_path
                
                # Verify source files exist
                required_files = [
                    os.path.join(src_dir, "tux"),
                    os.path.join(src_dir, "assets"),
                    os.path.join(src_dir, "tux-assistant.py"),
                    os.path.join(src_dir, "tux-helper"),
                    os.path.join(src_dir, "VERSION"),
                    os.path.join(src_dir, "data", "com.tuxassistant.app.desktop"),
                ]
                for rf in required_files:
                    if not os.path.exists(rf):
                        GLib.idle_add(self.window.show_toast, f"Missing: {os.path.basename(rf)}")
                        return
                
                shutil.copytree(os.path.join(src_dir, "tux"), os.path.join(opt_dir, "tux"))
                shutil.copytree(os.path.join(src_dir, "assets"), os.path.join(opt_dir, "assets"))
                shutil.copy2(os.path.join(src_dir, "tux-assistant.py"), opt_dir)
                shutil.copy2(os.path.join(src_dir, "tux-helper"), opt_dir)
                shutil.copy2(os.path.join(src_dir, "VERSION"), opt_dir)
                
                # Make key Python files executable
                tux_tunes_py = os.path.join(opt_dir, "tux", "apps", "tux_tunes", "tux-tunes.py")
                if os.path.exists(tux_tunes_py):
                    os.chmod(tux_tunes_py, 0o755)
                os.chmod(os.path.join(opt_dir, "tux-assistant.py"), 0o755)
                os.chmod(os.path.join(opt_dir, "tux-helper"), 0o755)
                
                # Create launcher scripts
                tux_launcher = os.path.join(bin_dir, "tux-assistant")
                with open(tux_launcher, "w") as f:
                    f.write("#!/bin/bash\npython3 /opt/tux-assistant/tux-assistant.py \"$@\"\n")
                os.chmod(tux_launcher, 0o755)
                
                tunes_launcher = os.path.join(bin_dir, "tux-tunes")
                with open(tunes_launcher, "w") as f:
                    f.write("#!/bin/bash\npython3 /opt/tux-assistant/tux/apps/tux_tunes/tux-tunes.py \"$@\"\n")
                os.chmod(tunes_launcher, 0o755)
                
                # Create helper symlink target (will be /usr/bin/tux-helper -> /opt/tux-assistant/tux-helper)
                helper_link = os.path.join(helper_dir, "tux-helper")
                # Create a wrapper script instead of symlink for packaging
                with open(helper_link, "w") as f:
                    f.write("#!/bin/bash\nexec /opt/tux-assistant/tux-helper \"$@\"\n")
                os.chmod(helper_link, 0o755)
                
                # Copy desktop files
                shutil.copy2(os.path.join(src_dir, "data", "com.tuxassistant.app.desktop"), desktop_dir)
                shutil.copy2(os.path.join(src_dir, "data", "com.tuxassistant.tuxtunes.desktop"), desktop_dir)
                
                # Copy polkit policy
                shutil.copy2(os.path.join(src_dir, "data", "com.tuxassistant.helper.policy"), polkit_dir)
                
                # Generate and write AppStream metainfo files
                with open(os.path.join(metainfo_dir, "com.tuxassistant.app.metainfo.xml"), "w") as f:
                    f.write(self._generate_metainfo_tux_assistant(version))
                with open(os.path.join(metainfo_dir, "com.tuxassistant.tuxtunes.metainfo.xml"), "w") as f:
                    f.write(self._generate_metainfo_tux_tunes(version))
                
                # Create post-install script
                post_install_script = os.path.join(staging_dir, "post-install.sh")
                with open(post_install_script, "w") as f:
                    f.write(self._generate_post_install_script())
                os.chmod(post_install_script, 0o755)
                
                # Install icons at multiple sizes
                icon_svg = os.path.join(src_dir, "assets", "icon.svg")
                tunes_svg = os.path.join(src_dir, "assets", "tux-tunes.svg")
                
                for size in ["16x16", "24x24", "32x32", "48x48", "64x64", "128x128", "256x256", "scalable"]:
                    if size == "scalable":
                        icon_dir = os.path.join(icon_base, size, "apps")
                    else:
                        icon_dir = os.path.join(icon_base, size, "apps")
                    os.makedirs(icon_dir, exist_ok=True)
                    shutil.copy2(icon_svg, os.path.join(icon_dir, "tux-assistant.svg"))
                    shutil.copy2(tunes_svg, os.path.join(icon_dir, "tux-tunes.svg"))
                
                GLib.idle_add(self.window.show_toast, f"Running fpm for {info['name']}...")
                
                # Build fpm command
                output_file = os.path.join(output_dir, info["filename"])
                
                # Remove existing file if present
                if os.path.exists(output_file):
                    os.remove(output_file)
                
                fpm_cmd = [
                    fpm_path,
                    "-s", "dir",
                    "-t", info["ext"],
                    "-n", "tux-assistant",
                    "-v", version,
                    "--description", "GTK4/Libadwaita Linux system configuration tool",
                    "--url", "https://github.com/dorrellkc/Tux-Assistant",
                    "--maintainer", "Christopher Dorrell <dorrellkc@gmail.com>",
                    "--license", "All Rights Reserved",
                    "-a", "x86_64",
                    "-p", output_file,
                    "-C", staging_dir,
                    "--after-install", post_install_script,
                    "--exclude", "post-install.sh",
                ]
                
                # Add dependencies
                for dep in info["deps"].split(", "):
                    fpm_cmd.extend(["-d", dep.strip()])
                
                # Add iteration/release for RPM
                if info["ext"] == "rpm":
                    if pkg_type == "fedora":
                        fpm_cmd.extend(["--iteration", "1.fc"])
                    else:
                        fpm_cmd.extend(["--iteration", "1.suse"])
                
                # Add the content
                fpm_cmd.append(".")
                
                result = subprocess.run(
                    fpm_cmd,
                    capture_output=True, text=True, timeout=120
                )
                
                if result.returncode != 0:
                    error_msg = result.stderr[:100] if result.stderr else result.stdout[:100]
                    GLib.idle_add(self.window.show_toast, f"fpm error: {error_msg}")
                    return
                
                # Verify the file was created
                if os.path.exists(output_file):
                    GLib.idle_add(self.window.show_toast, f"🎉 Built {info['filename']}!")
                    # Open file manager to output directory
                    GLib.idle_add(self._open_package_folder, output_dir)
                else:
                    GLib.idle_add(self.window.show_toast, "Package file not found after build")
                
                # Cleanup staging
                shutil.rmtree(staging_dir, ignore_errors=True)
                
            except FileNotFoundError as e:
                GLib.idle_add(self.window.show_toast, f"File not found: {e.filename}")
            except Exception as e:
                import traceback
                print(f"Package build error: {traceback.format_exc()}")
                GLib.idle_add(self.window.show_toast, f"Error: {type(e).__name__}: {str(e)[:40]}")
        
        threading.Thread(target=do_build, daemon=True).start()
    
    def _open_package_folder(self, folder_path: str):
        """Open file manager to the package folder."""
        try:
            subprocess.Popen(["xdg-open", folder_path])
        except Exception:
            pass  # Silently fail if can't open folder
    
    # =========================================================================
    # Build All Packages
    # =========================================================================
    
    def _on_build_all_packages(self, button):
        """Handle Build All Packages button click."""
        version = self._get_ta_version()
        
        dialog = Adw.AlertDialog()
        dialog.set_heading(f"Build All v{version} Packages?")
        dialog.set_body(
            "This will create:\n\n"
            f"  • Tux-Assistant-v{version}.run\n"
            f"  • tux-assistant_{version}_amd64.deb\n"
            f"  • tux-assistant-{version}-1.fc.x86_64.rpm\n"
            f"  • tux-assistant-{version}-1.suse.x86_64.rpm\n\n"
            f"Output: ~/Tux-Assistant-Releases/v{version}/\n\n"
            "This may take a few minutes."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("build", "Build All")
        dialog.set_response_appearance("build", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("build")
        dialog.connect("response", self._do_build_all_packages, version)
        dialog.present(self.window)
    
    def _do_build_all_packages(self, dialog, response, version):
        """Execute building all packages."""
        if response != "build":
            return
        
        self.window.show_toast("Building all packages...")
        
        def do_build_all():
            try:
                import shutil
                import glob
                
                # Create release directory
                release_dir = os.path.expanduser(f"~/Tux-Assistant-Releases/v{version}")
                os.makedirs(release_dir, exist_ok=True)
                
                # Track success
                built = []
                failed = []
                
                # ═══ 1. Build .run ═══
                GLib.idle_add(self.window.show_toast, "Building .run installer...")
                build_script = os.path.join(self.ta_repo_path, 'scripts', 'build-run.sh')
                
                if os.path.exists(build_script):
                    os.chmod(build_script, 0o755)
                    result = subprocess.run(
                        ['bash', build_script],
                        cwd=self.ta_repo_path,
                        capture_output=True, text=True, timeout=180
                    )
                    
                    run_file = os.path.join(self.ta_repo_path, 'dist', f'Tux-Assistant-v{version}.run')
                    if result.returncode == 0 and os.path.exists(run_file):
                        shutil.copy2(run_file, release_dir)
                        built.append(".run")
                    else:
                        failed.append(".run")
                else:
                    failed.append(".run (script missing)")
                
                # ═══ 2. Build DEB and RPMs using fpm ═══
                pkg_configs = [
                    {
                        "type": "deb",
                        "name": "Debian/Ubuntu",
                        "ext": "deb",
                        "filename": f"tux-assistant_{version}_amd64.deb",
                        "deps": "python3, python3-gi, gir1.2-gtk-4.0, libadwaita-1-0, gir1.2-adw-1, gstreamer1.0-tools, gir1.2-gst-plugins-base-1.0, gstreamer1.0-plugins-good",
                        "iteration": None
                    },
                    {
                        "type": "fedora",
                        "name": "Fedora",
                        "ext": "rpm",
                        "filename": f"tux-assistant-{version}-1.fc.x86_64.rpm",
                        "deps": "python3, python3-gobject, gtk4, libadwaita, gstreamer1, gstreamer1-plugins-base, gstreamer1-plugins-good",
                        "iteration": "1.fc"
                    },
                    {
                        "type": "suse",
                        "name": "openSUSE",
                        "ext": "rpm",
                        "filename": f"tux-assistant-{version}-1.suse.x86_64.rpm",
                        "deps": "python3, python3-gobject, gtk4, typelib-1_0-Gtk-4_0, libadwaita, typelib-1_0-Adw-1, gstreamer, gstreamer-plugins-base, gstreamer-plugins-good",
                        "iteration": "1.suse"
                    }
                ]
                
                # Find fpm
                fpm_path = self._find_fpm_path()
                if not fpm_path:
                    GLib.idle_add(self.window.show_toast, "Installing fpm...")
                    subprocess.run(['gem', 'install', '--user-install', 'fpm'], 
                                   capture_output=True, timeout=120)
                    fpm_path = self._find_fpm_path()
                
                if not fpm_path:
                    GLib.idle_add(self.window.show_toast, "fpm not found - DEB/RPM skipped")
                    failed.extend([".deb", "Fedora .rpm", "openSUSE .rpm"])
                else:
                    # Build each package type
                    for pkg in pkg_configs:
                        GLib.idle_add(self.window.show_toast, f"Building {pkg['name']} package...")
                        
                        success = self._build_single_package(
                            fpm_path, version, release_dir, pkg
                        )
                        
                        if success:
                            built.append(f".{pkg['ext']} ({pkg['type']})")
                        else:
                            failed.append(f".{pkg['ext']} ({pkg['type']})")
                
                # Report results
                if built:
                    GLib.idle_add(self.window.show_toast, f"🎉 Built: {', '.join(built)}")
                    GLib.idle_add(self._open_package_folder, release_dir)
                
                if failed:
                    GLib.idle_add(self.window.show_toast, f"Failed: {', '.join(failed)}")
                    
            except Exception as e:
                import traceback
                print(f"Build all error: {traceback.format_exc()}")
                GLib.idle_add(self.window.show_toast, f"Error: {str(e)[:50]}")
        
        threading.Thread(target=do_build_all, daemon=True).start()
    
    def _find_fpm_path(self) -> str:
        """Find fpm executable."""
        import glob
        
        # Check PATH
        result = subprocess.run(['which', 'fpm'], capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        
        # Check gem user dir
        try:
            gem_result = subprocess.run(
                ['ruby', '-e', 'puts Gem.user_dir'],
                capture_output=True, text=True, timeout=10
            )
            if gem_result.returncode == 0:
                gem_dir = gem_result.stdout.strip()
                bin_dir = os.path.join(gem_dir, 'bin')
                
                # Check for fpm directly
                fpm_path = os.path.join(bin_dir, 'fpm')
                if os.path.isfile(fpm_path):
                    return fpm_path
                
                # Check for fpm.ruby* (openSUSE naming)
                fpm_ruby_matches = glob.glob(os.path.join(bin_dir, 'fpm.ruby*'))
                if fpm_ruby_matches:
                    fpm_ruby_path = fpm_ruby_matches[0]
                    # Create symlink in ~/.local/bin for convenience
                    local_bin = os.path.expanduser("~/.local/bin")
                    os.makedirs(local_bin, exist_ok=True)
                    symlink_path = os.path.join(local_bin, 'fpm')
                    if not os.path.exists(symlink_path):
                        try:
                            os.symlink(fpm_ruby_path, symlink_path)
                        except:
                            pass
                    return fpm_ruby_path
                
                # Try glob in gems folder
                matches = glob.glob(os.path.join(gem_dir, 'gems', 'fpm-*', 'bin', 'fpm'))
                if matches:
                    return matches[0]
        except:
            pass
        
        return ""
    
    def _build_single_package(self, fpm_path: str, version: str, output_dir: str, pkg: dict) -> bool:
        """Build a single package type. Returns True on success."""
        try:
            import shutil
            import tempfile
            
            staging_dir = tempfile.mkdtemp(prefix=f"tux-{pkg['type']}-")
            
            # Create directory structure
            opt_dir = os.path.join(staging_dir, "opt", "tux-assistant")
            bin_dir = os.path.join(staging_dir, "usr", "local", "bin")
            helper_dir = os.path.join(staging_dir, "usr", "bin")
            desktop_dir = os.path.join(staging_dir, "usr", "share", "applications")
            polkit_dir = os.path.join(staging_dir, "usr", "share", "polkit-1", "actions")
            metainfo_dir = os.path.join(staging_dir, "usr", "share", "metainfo")
            icon_base = os.path.join(staging_dir, "usr", "share", "icons", "hicolor")
            
            for d in [opt_dir, bin_dir, helper_dir, desktop_dir, polkit_dir, metainfo_dir]:
                os.makedirs(d, exist_ok=True)
            
            src_dir = self.ta_repo_path
            
            # Copy app files
            shutil.copytree(os.path.join(src_dir, "tux"), os.path.join(opt_dir, "tux"))
            shutil.copytree(os.path.join(src_dir, "assets"), os.path.join(opt_dir, "assets"))
            shutil.copy2(os.path.join(src_dir, "tux-assistant.py"), opt_dir)
            shutil.copy2(os.path.join(src_dir, "tux-helper"), opt_dir)
            shutil.copy2(os.path.join(src_dir, "VERSION"), opt_dir)
            
            # Make executables
            os.chmod(os.path.join(opt_dir, "tux-assistant.py"), 0o755)
            os.chmod(os.path.join(opt_dir, "tux-helper"), 0o755)
            tux_tunes = os.path.join(opt_dir, "tux", "apps", "tux_tunes", "tux-tunes.py")
            if os.path.exists(tux_tunes):
                os.chmod(tux_tunes, 0o755)
            
            # Create launchers
            with open(os.path.join(bin_dir, "tux-assistant"), "w") as f:
                f.write("#!/bin/bash\npython3 /opt/tux-assistant/tux-assistant.py \"$@\"\n")
            os.chmod(os.path.join(bin_dir, "tux-assistant"), 0o755)
            
            with open(os.path.join(bin_dir, "tux-tunes"), "w") as f:
                f.write("#!/bin/bash\npython3 /opt/tux-assistant/tux/apps/tux_tunes/tux-tunes.py \"$@\"\n")
            os.chmod(os.path.join(bin_dir, "tux-tunes"), 0o755)
            
            with open(os.path.join(helper_dir, "tux-helper"), "w") as f:
                f.write("#!/bin/bash\nexec /opt/tux-assistant/tux-helper \"$@\"\n")
            os.chmod(os.path.join(helper_dir, "tux-helper"), 0o755)
            
            # Copy desktop files
            shutil.copy2(os.path.join(src_dir, "data", "com.tuxassistant.app.desktop"), desktop_dir)
            shutil.copy2(os.path.join(src_dir, "data", "com.tuxassistant.tuxtunes.desktop"), desktop_dir)
            
            # Copy polkit
            shutil.copy2(os.path.join(src_dir, "data", "com.tuxassistant.helper.policy"), polkit_dir)
            
            # Generate metainfo
            with open(os.path.join(metainfo_dir, "com.tuxassistant.app.metainfo.xml"), "w") as f:
                f.write(self._generate_metainfo_tux_assistant(version))
            with open(os.path.join(metainfo_dir, "com.tuxassistant.tuxtunes.metainfo.xml"), "w") as f:
                f.write(self._generate_metainfo_tux_tunes(version))
            
            # Create post-install script
            post_install = os.path.join(staging_dir, "post-install.sh")
            with open(post_install, "w") as f:
                f.write(self._generate_post_install_script())
            os.chmod(post_install, 0o755)
            
            # Copy icons
            icon_svg = os.path.join(src_dir, "assets", "icon.svg")
            tunes_svg = os.path.join(src_dir, "assets", "tux-tunes.svg")
            for size in ["16x16", "24x24", "32x32", "48x48", "64x64", "128x128", "256x256", "scalable"]:
                icon_dir = os.path.join(icon_base, size, "apps")
                os.makedirs(icon_dir, exist_ok=True)
                shutil.copy2(icon_svg, os.path.join(icon_dir, "tux-assistant.svg"))
                shutil.copy2(tunes_svg, os.path.join(icon_dir, "tux-tunes.svg"))
            
            # Build with fpm
            output_file = os.path.join(output_dir, pkg["filename"])
            if os.path.exists(output_file):
                os.remove(output_file)
            
            fpm_cmd = [
                fpm_path,
                "-s", "dir",
                "-t", pkg["ext"],
                "-n", "tux-assistant",
                "-v", version,
                "--description", "GTK4/Libadwaita Linux system configuration tool",
                "--url", "https://github.com/dorrellkc/Tux-Assistant",
                "--maintainer", "Christopher Dorrell <dorrellkc@gmail.com>",
                "--license", "All Rights Reserved",
                "-a", "x86_64",
                "-p", output_file,
                "-C", staging_dir,
                "--after-install", post_install,
                "--exclude", "post-install.sh",
            ]
            
            for dep in pkg["deps"].split(", "):
                fpm_cmd.extend(["-d", dep.strip()])
            
            if pkg["iteration"]:
                fpm_cmd.extend(["--iteration", pkg["iteration"]])
            
            fpm_cmd.append(".")
            
            result = subprocess.run(fpm_cmd, capture_output=True, text=True, timeout=120)
            
            shutil.rmtree(staging_dir, ignore_errors=True)
            
            return result.returncode == 0 and os.path.exists(output_file)
            
        except Exception as e:
            print(f"Build {pkg['type']} failed: {e}")
            return False
    
    # =========================================================================
    # Publish Full Release (with all packages)
    # =========================================================================
    
    def _on_full_release_all(self, button):
        """Handle Publish Full Release button click."""
        # Check SSH first
        ssh_status = self._check_ssh_agent_status()
        if "Unlocked" not in ssh_status:
            self.window.show_toast("Please unlock SSH key first")
            return
        
        # Check gh CLI
        gh_check = subprocess.run(['which', 'gh'], capture_output=True)
        if gh_check.returncode != 0:
            dialog = Adw.AlertDialog()
            dialog.set_heading("GitHub CLI Required")
            dialog.set_body(
                "Install 'gh' and authenticate:\n\n"
                "Fedora: sudo dnf install gh\n"
                "Arch: sudo pacman -S github-cli\n\n"
                "Then run: gh auth login"
            )
            dialog.add_response("ok", "OK")
            dialog.present(self.window)
            return
        
        version = self._get_ta_version()
        
        dialog = Adw.AlertDialog()
        dialog.set_heading(f"Publish Full v{version} Release?")
        dialog.set_body(
            "This will:\n\n"
            "1. Commit all changes to GitHub\n"
            "2. Push to main branch\n"
            "3. Build ALL packages (.run, .deb, 2x .rpm)\n"
            "4. Create GitHub Release with all assets\n\n"
            "⚠️ This publishes to the world!"
        )
        
        entry = Gtk.Entry()
        entry.set_text(f"Release v{version}")
        entry.set_placeholder_text("Commit/release message")
        entry.set_margin_top(12)
        entry.set_margin_start(12)
        entry.set_margin_end(12)
        dialog.set_extra_child(entry)
        
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("publish", "Publish Everything")
        dialog.set_response_appearance("publish", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        
        dialog.connect("response", self._do_full_release_all, entry, version)
        dialog.present(self.window)
    
    def _do_full_release_all(self, dialog, response, entry, version):
        """Execute the full release workflow with all packages."""
        if response != "publish":
            return
        
        commit_msg = entry.get_text().strip() or f"Release v{version}"
        self.window.show_toast("Starting full release...")
        
        def do_full_release():
            try:
                import shutil
                ssh_env = self._get_ssh_env()
                release_dir = os.path.expanduser(f"~/Tux-Assistant-Releases/v{version}")
                os.makedirs(release_dir, exist_ok=True)
                
                # ═══ 1. Git commit ═══
                GLib.idle_add(self.window.show_toast, "Committing changes...")
                subprocess.run(['git', 'add', '.'], cwd=self.ta_repo_path, timeout=30)
                commit_result = subprocess.run(
                    ['git', 'commit', '-m', commit_msg],
                    cwd=self.ta_repo_path, capture_output=True, text=True, timeout=30
                )
                # OK if nothing to commit
                
                # ═══ 2. Git push ═══
                GLib.idle_add(self.window.show_toast, "Pushing to GitHub...")
                push_result = subprocess.run(
                    ['git', 'push', 'origin', 'main'],
                    cwd=self.ta_repo_path, env=ssh_env,
                    capture_output=True, text=True, timeout=60
                )
                if push_result.returncode != 0:
                    GLib.idle_add(self.window.show_toast, f"Push failed: {push_result.stderr[:50]}")
                    return
                
                # ═══ 3. Build .run ═══
                GLib.idle_add(self.window.show_toast, "Building .run installer...")
                build_script = os.path.join(self.ta_repo_path, 'scripts', 'build-run.sh')
                if os.path.exists(build_script):
                    os.chmod(build_script, 0o755)
                    subprocess.run(['bash', build_script], cwd=self.ta_repo_path,
                                   capture_output=True, timeout=180)
                    run_file = os.path.join(self.ta_repo_path, 'dist', f'Tux-Assistant-v{version}.run')
                    if os.path.exists(run_file):
                        shutil.copy2(run_file, release_dir)
                
                # ═══ 4. Build DEB and RPMs ═══
                fpm_path = self._find_fpm_path()
                if fpm_path:
                    pkg_configs = [
                        {"type": "deb", "name": "DEB", "ext": "deb",
                         "filename": f"tux-assistant_{version}_amd64.deb",
                         "deps": "python3, python3-gi, gir1.2-gtk-4.0, libadwaita-1-0, gir1.2-adw-1, gstreamer1.0-tools, gir1.2-gst-plugins-base-1.0, gstreamer1.0-plugins-good",
                         "iteration": None},
                        {"type": "fedora", "name": "Fedora RPM", "ext": "rpm",
                         "filename": f"tux-assistant-{version}-1.fc.x86_64.rpm",
                         "deps": "python3, python3-gobject, gtk4, libadwaita, gstreamer1, gstreamer1-plugins-base, gstreamer1-plugins-good",
                         "iteration": "1.fc"},
                        {"type": "suse", "name": "openSUSE RPM", "ext": "rpm",
                         "filename": f"tux-assistant-{version}-1.suse.x86_64.rpm",
                         "deps": "python3, python3-gobject, gtk4, typelib-1_0-Gtk-4_0, libadwaita, typelib-1_0-Adw-1, gstreamer, gstreamer-plugins-base, gstreamer-plugins-good",
                         "iteration": "1.suse"}
                    ]
                    
                    for pkg in pkg_configs:
                        GLib.idle_add(self.window.show_toast, f"Building {pkg['name']}...")
                        self._build_single_package(fpm_path, version, release_dir, pkg)
                
                # ═══ 5. Create GitHub Release ═══
                GLib.idle_add(self.window.show_toast, "Creating GitHub Release...")
                
                # Gather all built files
                release_files = []
                for f in os.listdir(release_dir):
                    filepath = os.path.join(release_dir, f)
                    if os.path.isfile(filepath):
                        release_files.append(filepath)
                
                if not release_files:
                    GLib.idle_add(self.window.show_toast, "No packages built!")
                    return
                
                # Build release notes
                file_list = "\n".join([f"- {os.path.basename(f)}" for f in release_files])
                release_notes = f"{commit_msg}\n\n**Downloads:**\n{file_list}\n\n" \
                               f"**Install .run:**\n```\nchmod +x Tux-Assistant-v{version}.run\n" \
                               f"./Tux-Assistant-v{version}.run\n```"
                
                # Create release with all files
                gh_cmd = [
                    'gh', 'release', 'create', f'v{version}',
                    '--title', f'Tux Assistant v{version}',
                    '--notes', release_notes
                ] + release_files
                
                release_result = subprocess.run(
                    gh_cmd, cwd=self.ta_repo_path, env=ssh_env,
                    capture_output=True, text=True, timeout=300
                )
                
                if release_result.returncode == 0:
                    GLib.idle_add(self.window.show_toast, f"🎉 Published v{version} with {len(release_files)} files!")
                    GLib.idle_add(self._open_package_folder, release_dir)
                else:
                    error = release_result.stderr[:80] if release_result.stderr else "Unknown error"
                    GLib.idle_add(self.window.show_toast, f"Release failed: {error}")
                    
            except Exception as e:
                import traceback
                print(f"Full release error: {traceback.format_exc()}")
                GLib.idle_add(self.window.show_toast, f"Error: {str(e)[:50]}")
        
        threading.Thread(target=do_full_release, daemon=True).start()
    
    def _show_fpm_path_dialog(self, gem_bin_dir: str):
        """Show dialog with fpm PATH instructions."""
        dialog = Adw.AlertDialog()
        dialog.set_heading("fpm Not in PATH")
        dialog.set_body(
            f"fpm was installed but isn't in your PATH.\n\n"
            f"Add this to your ~/.bashrc or ~/.zshrc:\n\n"
            f"export PATH=\"{gem_bin_dir}:$PATH\"\n\n"
            f"Then restart your terminal or run:\n"
            f"source ~/.bashrc"
        )
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.present(self.window)
    
    def _show_fpm_error_dialog(self):
        """Show dialog when fpm can't be found."""
        dialog = Adw.AlertDialog()
        dialog.set_heading("fpm Not Found")
        dialog.set_body(
            "fpm was installed but couldn't be located.\n\n"
            "Try running in terminal:\n"
            "  gem environment\n\n"
            "Look for 'EXECUTABLE DIRECTORY' and add it to your PATH."
        )
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.present(self.window)
    
    def _show_pkg_install_error(self, packages: list, distro: str):
        """Show dialog when system package installation fails."""
        install_cmds = {
            "arch": f"sudo pacman -S {' '.join(packages)}",
            "fedora": f"sudo dnf install {' '.join(packages)}",
            "suse": f"sudo zypper install {' '.join(packages)}",
            "debian": f"sudo apt install {' '.join(packages)}",
        }
        cmd = install_cmds.get(distro, f"Install: {', '.join(packages)}")
        
        dialog = Adw.AlertDialog()
        dialog.set_heading("Dependencies Required")
        dialog.set_body(
            f"Failed to install required packages.\n\n"
            f"Please run manually in terminal:\n\n"
            f"{cmd}\n\n"
            f"Then try building again."
        )
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.present(self.window)
    
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
    
    def _get_sync_status(self) -> dict:
        """Check sync status between installed version, local repo, GitHub, and AUR."""
        result = {
            'state': 'unknown',
            'message': 'Checking...',
            'installed_ver': '',
            'local_ver': '',
            'github_ver': '',
            'aur_ver': ''
        }
        
        try:
            # Get installed version (what's actually running)
            installed_ver_file = "/opt/tux-assistant/VERSION"
            installed_ver = ''
            if os.path.exists(installed_ver_file):
                with open(installed_ver_file, 'r') as f:
                    installed_ver = f.read().strip()
            result['installed_ver'] = installed_ver
            
            # Get repo version
            local_ver = self._get_ta_version()
            result['local_ver'] = local_ver
            
            # Check if installed version differs from repo version
            if installed_ver and local_ver and installed_ver != local_ver:
                result['state'] = 'repo_outdated'
                result['message'] = f"Installed v{installed_ver} • Repo has v{local_ver} - sync needed"
                return result
            
            # Check for uncommitted changes first
            if self._ta_has_changes():
                result['state'] = 'dirty'
                result['message'] = f"v{local_ver} • Uncommitted changes"
                return result
            
            # Fetch from remote (quick, no pull)
            subprocess.run(
                ['git', 'fetch', '--tags', '-q'],
                cwd=self.ta_repo_path,
                capture_output=True, text=True, timeout=15
            )
            
            # Get local and remote commit hashes
            local_result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=self.ta_repo_path,
                capture_output=True, text=True, timeout=5
            )
            local_commit = local_result.stdout.strip()[:7] if local_result.returncode == 0 else ''
            
            remote_result = subprocess.run(
                ['git', 'rev-parse', 'origin/main'],
                cwd=self.ta_repo_path,
                capture_output=True, text=True, timeout=5
            )
            remote_commit = remote_result.stdout.strip()[:7] if remote_result.returncode == 0 else ''
            
            # Check ahead/behind
            if local_commit and remote_commit and local_commit != remote_commit:
                # Check if local is behind
                merge_base = subprocess.run(
                    ['git', 'merge-base', '--is-ancestor', 'HEAD', 'origin/main'],
                    cwd=self.ta_repo_path,
                    capture_output=True, text=True, timeout=5
                )
                if merge_base.returncode == 0:
                    result['state'] = 'behind'
                    result['message'] = f"v{local_ver} • Behind GitHub - pull available"
                    return result
                else:
                    result['state'] = 'ahead'
                    result['message'] = f"v{local_ver} • Ahead of GitHub - push needed"
                    return result
            
            # Check AUR version
            aur_dir = os.path.expanduser("~/Development/tux-assistant-aur")
            pkgbuild = os.path.join(aur_dir, "PKGBUILD")
            if os.path.exists(pkgbuild):
                with open(pkgbuild, 'r') as f:
                    for line in f:
                        if line.startswith('pkgver='):
                            aur_ver = line.split('=')[1].strip()
                            result['aur_ver'] = aur_ver
                            if aur_ver != local_ver:
                                result['state'] = 'aur_behind'
                                result['message'] = f"v{local_ver} • AUR needs update (has v{aur_ver})"
                                return result
                            break
            
            # All in sync
            result['state'] = 'in_sync'
            result['message'] = f"v{local_ver} • GitHub ✓ • AUR ✓"
            return result
            
        except Exception as e:
            result['message'] = f"Error checking status: {str(e)[:30]}"
            return result
    
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
            ('ptyxis', ['ptyxis', '-e', 'bash', script_path]),  # Fedora 43+ default
            ('kgx', ['kgx', '-e', 'bash', script_path]),  # GNOME Console
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
        if not hasattr(self, 'ta_status_row'):
            return
        
        version = self._get_ta_version()
        branch = self._get_ta_branch()
        ssh_status = self._check_ssh_agent_status()
        ssh_ok = "Unlocked" in ssh_status
        
        # Update title with version
        self.ta_status_row.set_title(f"Version {version}")
        
        # Update subtitle with status
        status_parts = [f"Branch: {branch}"]
        status_parts.append(f"SSH: {'✓ Ready' if ssh_ok else '🔒 Locked'}")
        self.ta_status_row.set_subtitle(" • ".join(status_parts))
        
        # Update icon
        child = self.ta_status_row.get_first_child()
        while child:
            if isinstance(child, Gtk.Image):
                self.ta_status_row.remove(child)
                break
            child = child.get_next_sibling()
        
        if ssh_ok:
            self.ta_status_row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
        else:
            self.ta_status_row.add_prefix(Gtk.Image.new_from_icon_name("dialog-password-symbolic"))
        
        # Update sync row if it exists
        if hasattr(self, 'sync_row'):
            sync_status = self._get_sync_status()
            self.sync_row.set_subtitle(sync_status['message'])
        
        if button:  # Only show toast if manually refreshed
            self.window.show_toast("Status refreshed")
    
    def _on_show_git_help(self, button):
        """Show the Git workflow help dialog."""
        help_text = """<b>🚀 Quick Start - 2 Button Workflow</b>

<b>Step 1: Install from ZIP</b>
• Download .zip from Claude to ~/Downloads/
• Click <b>Choose ZIP &amp; Install</b>
• Select the ZIP file
• Wait for installation to complete

<b>Step 2: Publish Release</b>
• Click <b>Unlock SSH</b> (if locked)
• Click <b>Publish vX.X.X</b>
• Enter commit message (or use default)
• Wait for GitHub release to complete

That's it! 🎉

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>🔧 Troubleshooting</b>

<b>Push failed / ssh_askpass error:</b>
• Click "Unlock SSH" button first
• If it still fails, run in terminal:
  <tt>eval $(ssh-agent) &amp;&amp; ssh-add</tt>

<b>"gh: command not found":</b>
• Install GitHub CLI:
  Fedora: <tt>sudo dnf install gh</tt>
  Arch: <tt>sudo pacman -S github-cli</tt>
  Ubuntu: <tt>sudo apt install gh</tt>
• Then run: <tt>gh auth login</tt>

<b>Build fails:</b>
• Check you have all dependencies
• Try running manually in terminal

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>💻 Manual Terminal Commands</b>

<b>Install from ZIP:</b>
<tt>rm -rf /tmp/tux-assistant &amp;&amp; \\
unzip ~/Downloads/tux-assistant-vX.X.X-source.zip -d /tmp/ &amp;&amp; \\
cd ~/Development/Tux-Assistant &amp;&amp; \\
cp -r /tmp/tux-assistant/* . &amp;&amp; \\
sudo ./install.sh</tt>

<b>Publish Release:</b>
<tt>cd ~/Development/Tux-Assistant &amp;&amp; \\
git add . &amp;&amp; git commit -m "vX.X.X" &amp;&amp; git push &amp;&amp; \\
./scripts/build-run.sh &amp;&amp; \\
gh release create vX.X.X dist/Tux-Assistant-vX.X.X.run \\
--title "Tux Assistant vX.X.X" --notes "Release notes"</tt>

Replace X.X.X with your version number."""

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
    
    def _on_sync_repo_from_installed(self, button):
        """Sync repo from installed version (copy from /opt/tux-assistant)."""
        installed_ver = ''
        installed_ver_file = "/opt/tux-assistant/VERSION"
        if os.path.exists(installed_ver_file):
            with open(installed_ver_file, 'r') as f:
                installed_ver = f.read().strip()
        
        repo_ver = self._get_ta_version()
        
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Sync Repo from Installed",
            body=f"This will copy the installed version (v{installed_ver}) to your repo, overwriting the current repo version (v{repo_ver}).\n\nThis ensures your repo matches what's installed."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("sync", "Sync Repo")
        dialog.set_response_appearance("sync", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._do_sync_repo_from_installed)
        dialog.present()
    
    def _do_sync_repo_from_installed(self, dialog, response):
        """Execute the repo sync from installed version."""
        if response != "sync":
            return
        
        def do_sync():
            try:
                import shutil
                
                installed_dir = "/opt/tux-assistant"
                repo_dir = self.ta_repo_path
                
                if not os.path.exists(installed_dir):
                    GLib.idle_add(self.window.show_toast, "Installed directory not found")
                    return
                
                # Files/folders to copy (excluding .git and other dev files)
                items_to_copy = [
                    'tux', 'data', 'assets', 'docs', 'scripts', 'screenshots',
                    'install.sh', 'tux-assistant.py', 'tux-helper', 'VERSION',
                    'README.md', 'README-public.md', 'LICENSE', 'CHANGELOG.md',
                    'TODO.md', 'GIT-COMMANDS.txt', 'setup-branches.sh',
                    'tux-assistant.install'
                ]
                
                for item in items_to_copy:
                    src = os.path.join(installed_dir, item)
                    dst = os.path.join(repo_dir, item)
                    
                    if os.path.exists(src):
                        if os.path.isdir(src):
                            if os.path.exists(dst):
                                shutil.rmtree(dst)
                            shutil.copytree(src, dst)
                        else:
                            shutil.copy2(src, dst)
                
                GLib.idle_add(self.window.show_toast, "Repo synced from installed version")
                GLib.idle_add(self._on_ta_refresh_status, None)
                
            except Exception as e:
                GLib.idle_add(self.window.show_toast, f"Sync failed: {str(e)[:50]}")
        
        threading.Thread(target=do_sync, daemon=True).start()
        self.window.show_toast("Syncing repo from installed...")
    
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
    
    def _on_github_release(self, button):
        """Create a GitHub release with the current version."""
        if not self.ta_repo_path:
            self.window.show_toast("Tux Assistant repo not found")
            return
        
        # Check if gh is installed
        gh_check = subprocess.run(['which', 'gh'], capture_output=True)
        if gh_check.returncode != 0:
            dialog = Adw.AlertDialog()
            dialog.set_heading("GitHub CLI Not Installed")
            dialog.set_body(
                "The 'gh' command is required for GitHub releases.\n\n"
                "Install it with:\n"
                "• Fedora: sudo dnf install gh\n"
                "• Arch: sudo pacman -S github-cli\n"
                "• Ubuntu: sudo apt install gh\n\n"
                "Then run: gh auth login"
            )
            dialog.add_response("ok", "OK")
            dialog.present(self.window)
            return
        
        # Get version
        try:
            version_file = os.path.join(self.ta_repo_path, 'VERSION')
            with open(version_file, 'r') as f:
                version = f.read().strip()
        except:
            self.window.show_toast("Could not read VERSION file")
            return
        
        run_file = os.path.join(self.ta_repo_path, 'releases', f'Tux-Assistant-v{version}.run')
        
        if not os.path.exists(run_file):
            self.window.show_toast(f"Release file not found: Tux-Assistant-v{version}.run")
            return
        
        # Confirm dialog
        dialog = Adw.AlertDialog()
        dialog.set_heading(f"Create GitHub Release v{version}?")
        dialog.set_body(
            f"This will:\n"
            f"• Create tag v{version}\n"
            f"• Upload Tux-Assistant-v{version}.run\n"
            f"• Publish as latest release"
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("release", "Publish")
        dialog.set_response_appearance("release", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._do_github_release, version, run_file)
        dialog.present(self.window)
    
    def _do_github_release(self, dialog, response, version: str, run_file: str):
        """Execute the GitHub release."""
        if response != "release":
            return
        
        def do_release():
            try:
                ssh_env = self._get_ssh_env()
                
                # Create the release
                result = subprocess.run(
                    [
                        'gh', 'release', 'create', f'v{version}',
                        run_file,
                        '--title', f'Tux Assistant v{version}',
                        '--notes', f'Tux Assistant v{version} release.\n\nDownload the .run file and run: chmod +x Tux-Assistant-v{version}.run && ./Tux-Assistant-v{version}.run'
                    ],
                    cwd=self.ta_repo_path,
                    capture_output=True,
                    text=True,
                    timeout=120,
                    env=ssh_env
                )
                
                if result.returncode == 0:
                    GLib.idle_add(self.window.show_toast, f"GitHub Release v{version} created! 🎉")
                else:
                    error = result.stderr[:100] if result.stderr else "Unknown error"
                    GLib.idle_add(self.window.show_toast, f"Release failed: {error}")
                    
            except Exception as e:
                GLib.idle_add(self.window.show_toast, f"Error: {str(e)[:50]}")
        
        threading.Thread(target=do_release, daemon=True).start()
        self.window.show_toast("Creating GitHub release...")
    
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
            ('ptyxis', ['ptyxis', '-e', 'bash', '-c', pull_script]),  # Fedora 43+ default
            ('kgx', ['kgx', '-e', 'bash', '-c', pull_script]),  # GNOME Console
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
            ('ptyxis', ['ptyxis', '-e', 'bash', '-c', push_script]),  # Fedora 43+ default
            ('kgx', ['kgx', '-e', 'bash', '-c', push_script]),  # GNOME Console
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
        terminals = ['ptyxis', 'kgx', 'gnome-terminal', 'konsole', 'xfce4-terminal', 'tilix', 'alacritty', 'kitty', 'xterm']
        
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
    
    def _install_build_dependencies(self) -> str:
        """Install all build dependencies for package building."""
        import glob
        
        results = []
        
        # Detect distro
        distro = "unknown"
        try:
            with open("/etc/os-release") as f:
                content = f.read().lower()
                if "arch" in content or "endeavour" in content or "manjaro" in content or "cachyos" in content:
                    distro = "arch"
                elif "fedora" in content or "rhel" in content or "centos" in content or "rocky" in content:
                    distro = "fedora"
                elif "opensuse" in content or "suse" in content:
                    distro = "suse"
                elif "ubuntu" in content or "debian" in content or "mint" in content or "pop" in content:
                    distro = "debian"
        except:
            pass
        
        # Define packages needed per distro
        pkg_map = {
            "arch": {
                "install_cmd": ["sudo", "pacman", "-S", "--noconfirm", "--needed"],
                "packages": ["ruby", "binutils", "rpm-tools", "fakeroot"]
            },
            "fedora": {
                "install_cmd": ["sudo", "dnf", "install", "-y"],
                "packages": ["ruby", "ruby-devel", "binutils", "rpm-build", "gcc", "make"]
            },
            "suse": {
                "install_cmd": ["sudo", "zypper", "--non-interactive", "install"],
                "packages": ["ruby", "ruby-devel", "binutils", "rpm-build", "fakeroot", "gcc", "make"]
            },
            "debian": {
                "install_cmd": ["sudo", "apt", "install", "-y"],
                "packages": ["ruby", "ruby-dev", "binutils", "rpm", "fakeroot", "build-essential"]
            }
        }
        
        if distro == "unknown":
            return "⚠️ Unknown distro - install ruby, binutils, rpm-build manually"
        
        # Install system packages
        try:
            config = pkg_map[distro]
            cmd = config["install_cmd"] + config["packages"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            if result.returncode == 0:
                results.append("✓ System build tools installed")
            else:
                results.append(f"⚠️ Some packages may have failed")
        except Exception as e:
            results.append(f"⚠️ Package install error: {str(e)[:50]}")
        
        # Install fpm gem
        try:
            # Check if fpm already exists
            fpm_path = self._find_fpm_path()
            if not fpm_path:
                result = subprocess.run(
                    ["gem", "install", "--user-install", "fpm"],
                    capture_output=True, text=True, timeout=300
                )
                if result.returncode == 0:
                    results.append("✓ FPM gem installed")
                    
                    # Handle openSUSE/newer Ruby naming (fpm.ruby*)
                    gem_result = subprocess.run(
                        ['ruby', '-e', 'puts Gem.user_dir'],
                        capture_output=True, text=True, timeout=10
                    )
                    if gem_result.returncode == 0:
                        gem_dir = gem_result.stdout.strip()
                        bin_dir = os.path.join(gem_dir, 'bin')
                        fpm_ruby_matches = glob.glob(os.path.join(bin_dir, 'fpm.ruby*'))
                        if fpm_ruby_matches:
                            fpm_ruby_path = fpm_ruby_matches[0]
                            local_bin = os.path.expanduser("~/.local/bin")
                            os.makedirs(local_bin, exist_ok=True)
                            symlink_path = os.path.join(local_bin, 'fpm')
                            if not os.path.exists(symlink_path):
                                try:
                                    os.symlink(fpm_ruby_path, symlink_path)
                                    results.append("✓ FPM symlink created")
                                except:
                                    pass
                else:
                    results.append(f"⚠️ FPM install failed")
            else:
                results.append("✓ FPM already installed")
        except Exception as e:
            results.append(f"⚠️ FPM error: {str(e)[:50]}")
        
        # Ensure ~/.local/bin is in PATH hint
        local_bin = os.path.expanduser("~/.local/bin")
        path_env = os.environ.get("PATH", "")
        if local_bin not in path_env:
            results.append(f"ℹ️ Add to PATH: {local_bin}")
        
        return "\\n".join(results) if results else "✓ Build dependencies ready"
    
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
            
            # Install build dependencies first
            self.window.show_toast("Installing build dependencies...")
            build_result = self._install_build_dependencies()
            if build_result:
                results.append(build_result)
            
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
