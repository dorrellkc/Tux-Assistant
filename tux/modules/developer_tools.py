"""
Developer Tools Module

Front-page category providing developer-focused utilities like
Git project management, repository cloning, SSH key management,
and Developer Kit export/import for portable dev setups.

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
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
    order=10
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
        # Scrollable content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        self.set_child(scrolled)
        
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
            config_row.set_subtitle(f"✓ {name} <{email}>")
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
        ssh_row.set_subtitle("Drag & drop your backed up SSH keys")
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
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        button_box.set_valign(Gtk.Align.CENTER)
        
        # Pull button
        pull_btn = Gtk.Button()
        pull_btn.set_icon_name("go-down-symbolic")
        pull_btn.set_tooltip_text("Pull latest changes")
        pull_btn.add_css_class("flat")
        pull_btn.connect("clicked", lambda b: self._on_pull_project(path, row))
        button_box.append(pull_btn)
        
        # Push button
        push_btn = Gtk.Button()
        push_btn.set_icon_name("go-up-symbolic")
        push_btn.set_tooltip_text("Push changes")
        push_btn.add_css_class("flat")
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
        
        self.window.show_toast("Pulling...")
        
        def pull_thread():
            try:
                result = subprocess.run(
                    ['git', '-C', path, 'pull'],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                success = result.returncode == 0
                message = "Pull complete!" if success else f"Pull failed: {result.stderr[:100]}"
                GLib.idle_add(self._on_git_operation_complete, success, message, path)
            except subprocess.TimeoutExpired:
                GLib.idle_add(self._on_git_operation_complete, False, "Pull timed out", path)
            except Exception as e:
                GLib.idle_add(self._on_git_operation_complete, False, str(e), path)
        
        threading.Thread(target=pull_thread, daemon=True).start()
    
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
            dialog = CommitPushDialog(self.window, path, info)
            dialog.connect("response", self._on_commit_push_response)
            dialog.present(self.window)
        elif info.ahead > 0:
            # Just push existing commits
            self._do_push(path)
        else:
            self.window.show_toast("Nothing to push")
    
    def _on_commit_push_response(self, dialog, response):
        """Handle commit/push dialog response."""
        if response == "push":
            path = dialog.project_path
            message = dialog.get_commit_message()
            self._do_commit_and_push(path, message)
    
    def _do_commit_and_push(self, path: str, message: str):
        """Commit all changes and push."""
        self.window.show_toast("Committing and pushing...")
        
        def push_thread():
            try:
                # Stage all changes
                subprocess.run(['git', '-C', path, 'add', '-A'], check=True)
                
                # Commit
                subprocess.run(
                    ['git', '-C', path, 'commit', '-m', message],
                    check=True,
                    capture_output=True
                )
                
                # Push
                result = subprocess.run(
                    ['git', '-C', path, 'push'],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                success = result.returncode == 0
                msg = "Pushed successfully!" if success else f"Push failed: {result.stderr[:100]}"
                GLib.idle_add(self._on_git_operation_complete, success, msg, path)
                
            except subprocess.CalledProcessError as e:
                GLib.idle_add(self._on_git_operation_complete, False, f"Git error: {e}", path)
            except Exception as e:
                GLib.idle_add(self._on_git_operation_complete, False, str(e), path)
        
        threading.Thread(target=push_thread, daemon=True).start()
    
    def _do_push(self, path: str):
        """Push existing commits."""
        self.window.show_toast("Pushing...")
        
        def push_thread():
            try:
                result = subprocess.run(
                    ['git', '-C', path, 'push'],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                success = result.returncode == 0
                msg = "Pushed successfully!" if success else f"Push failed: {result.stderr[:100]}"
                GLib.idle_add(self._on_git_operation_complete, success, msg, path)
            except Exception as e:
                GLib.idle_add(self._on_git_operation_complete, False, str(e), path)
        
        threading.Thread(target=push_thread, daemon=True).start()
    
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
        terminals = ['gnome-terminal', 'konsole', 'xfce4-terminal', 'tilix', 'alacritty', 'kitty']
        
        for term in terminals:
            try:
                if subprocess.run(['which', term], capture_output=True).returncode == 0:
                    if term == 'gnome-terminal':
                        subprocess.Popen([term, '--working-directory', path])
                    elif term == 'konsole':
                        subprocess.Popen([term, '--workdir', path])
                    else:
                        subprocess.Popen([term], cwd=path)
                    return
            except Exception:
                continue
        
        self.window.show_toast("Could not find terminal emulator")
    
    def _on_configure_git_identity(self, button):
        """Show dialog to configure git identity."""
        dialog = GitIdentityDialog(self.window)
        dialog.connect("response", self._on_identity_configured)
        dialog.present(self.window)
    
    def _on_identity_configured(self, dialog, response):
        """Handle identity configuration response."""
        if response == "save":
            self.window.show_toast("Git identity configured!")
    
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
    
    # ==================== Developer Kit Export/Import ====================
    
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
            if 'projects' in manifest.get('contents', []) and os.path.exists(projects_path):
                with open(projects_path, 'r') as f:
                    projects_data = json.load(f)
                
                project_count = len(projects_data.get('projects', []))
                results.append(f"✓ Found {project_count} project(s) to clone")
                
                # TODO: Offer to clone these projects
            
            # Show result dialog
            result_dialog = Adw.AlertDialog(
                heading="Developer Kit Imported!",
                body="\n".join(results) + "\n\nYou may need to restart the app to see updated status."
            )
            result_dialog.add_response("ok", "OK")
            result_dialog.present(self.window)
            
            # Refresh the UI
            self._refresh_project_list()
            
        except Exception as e:
            self.window.show_toast(f"Import failed: {e}")


class CommitPushDialog(Adw.Dialog):
    """Dialog for entering commit message before pushing."""
    
    def __init__(self, parent, path: str, info: GitProject):
        super().__init__()
        
        self.project_path = path
        self.info = info
        
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
        self.emit("response", "push")
        self.close()
    
    def get_commit_message(self) -> str:
        """Get the commit message."""
        return self.message_entry.get_text().strip()


class GitIdentityDialog(Adw.Dialog):
    """Dialog for configuring git identity."""
    
    def __init__(self, parent):
        super().__init__()
        
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
            
            self.emit("response", "save")
            self.close()
        except Exception as e:
            print(f"Failed to set git config: {e}")
