"""
Tux Assistant - System Maintenance Module

System cleanup, updates, startup apps, and storage management.

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

import os
import subprocess
import threading
from gi.repository import Gtk, Adw, GLib, Gio
from typing import Optional, List, Tuple
from dataclasses import dataclass

from ..core import get_distro, DistroFamily

from .registry import register_module, ModuleCategory


# =============================================================================
# Cleanup Utilities
# =============================================================================

@dataclass
class CleanupItem:
    """A cleanable item with size info."""
    name: str
    description: str
    size_bytes: int
    cleanup_func: str  # Method name to call for cleanup
    icon: str = "user-trash-symbolic"


def get_human_size(size_bytes: int) -> str:
    """Convert bytes to human readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def get_dir_size(path: str) -> int:
    """Get total size of a directory in bytes."""
    total = 0
    try:
        if os.path.isfile(path):
            return os.path.getsize(path)
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                try:
                    total += os.path.getsize(filepath)
                except (OSError, FileNotFoundError):
                    pass
    except (OSError, PermissionError):
        pass
    return total


def get_package_cache_size(family: DistroFamily) -> int:
    """Get size of package manager cache."""
    cache_paths = {
        DistroFamily.ARCH: "/var/cache/pacman/pkg",
        DistroFamily.DEBIAN: "/var/cache/apt/archives",
        DistroFamily.FEDORA: "/var/cache/dnf",
        DistroFamily.OPENSUSE: "/var/cache/zypp/packages",
    }
    path = cache_paths.get(family)
    if path and os.path.exists(path):
        return get_dir_size(path)
    return 0


def get_journal_size() -> int:
    """Get size of systemd journal logs."""
    journal_path = "/var/log/journal"
    if os.path.exists(journal_path):
        return get_dir_size(journal_path)
    return 0


def get_trash_size() -> int:
    """Get size of user's trash."""
    trash_path = os.path.expanduser("~/.local/share/Trash")
    if os.path.exists(trash_path):
        return get_dir_size(trash_path)
    return 0


def get_thumbnail_cache_size() -> int:
    """Get size of thumbnail cache."""
    thumb_path = os.path.expanduser("~/.cache/thumbnails")
    if os.path.exists(thumb_path):
        return get_dir_size(thumb_path)
    return 0


def get_user_cache_size() -> int:
    """Get size of user cache directory (excluding thumbnails)."""
    cache_path = os.path.expanduser("~/.cache")
    thumb_path = os.path.expanduser("~/.cache/thumbnails")
    
    total = get_dir_size(cache_path)
    # Subtract thumbnails since we count those separately
    total -= get_dir_size(thumb_path)
    return max(0, total)


def get_orphaned_packages(family: DistroFamily) -> Tuple[int, List[str]]:
    """Get count and list of orphaned packages."""
    try:
        if family == DistroFamily.ARCH:
            result = subprocess.run(
                ['pacman', '-Qdtq'],
                capture_output=True, text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                packages = result.stdout.strip().split('\n')
                return len(packages), packages
        elif family == DistroFamily.DEBIAN:
            result = subprocess.run(
                ['deborphan'],
                capture_output=True, text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                packages = result.stdout.strip().split('\n')
                return len(packages), packages
        # Fedora and openSUSE handle this differently
    except Exception:
        pass
    return 0, []


# =============================================================================
# Update Utilities  
# =============================================================================

def check_updates_available(family: DistroFamily) -> Tuple[bool, int, str]:
    """Check if updates are available. Returns (has_updates, count, details)."""
    try:
        if family == DistroFamily.ARCH:
            result = subprocess.run(
                ['checkupdates'],
                capture_output=True, text=True
            )
            if result.returncode == 0 and result.stdout.strip():
                updates = result.stdout.strip().split('\n')
                return True, len(updates), result.stdout.strip()
            return False, 0, ""
            
        elif family == DistroFamily.DEBIAN:
            # Update cache first (might need sudo, so just check)
            subprocess.run(['apt', 'update'], capture_output=True)
            result = subprocess.run(
                ['apt', 'list', '--upgradable'],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                lines = [l for l in result.stdout.strip().split('\n') 
                        if l and 'Listing...' not in l]
                if lines:
                    return True, len(lines), '\n'.join(lines)
            return False, 0, ""
            
        elif family == DistroFamily.FEDORA:
            result = subprocess.run(
                ['dnf', 'check-update', '-q'],
                capture_output=True, text=True
            )
            # dnf returns 100 if updates available, 0 if none
            if result.returncode == 100 and result.stdout.strip():
                updates = [l for l in result.stdout.strip().split('\n') if l.strip()]
                return True, len(updates), result.stdout.strip()
            return False, 0, ""
            
        elif family == DistroFamily.OPENSUSE:
            result = subprocess.run(
                ['zypper', 'list-updates'],
                capture_output=True, text=True
            )
            if result.returncode == 0 and 'No updates found' not in result.stdout:
                lines = result.stdout.strip().split('\n')
                # Skip header lines
                updates = [l for l in lines if '|' in l and 'Name' not in l]
                if updates:
                    return True, len(updates), '\n'.join(updates)
            return False, 0, ""
            
    except Exception as e:
        return False, 0, str(e)
    
    return False, 0, ""


# =============================================================================
# Startup Apps Utilities
# =============================================================================

@dataclass
class StartupApp:
    """A startup application entry."""
    name: str
    exec_cmd: str
    enabled: bool
    desktop_file: str
    icon: Optional[str] = None
    comment: Optional[str] = None


def get_autostart_apps() -> List[StartupApp]:
    """Get list of autostart applications."""
    apps = []
    
    # User autostart directory
    user_autostart = os.path.expanduser("~/.config/autostart")
    
    # System autostart directories
    system_autostart = [
        "/etc/xdg/autostart",
    ]
    
    seen_names = set()
    
    # Check user directory first (takes precedence)
    if os.path.exists(user_autostart):
        for filename in os.listdir(user_autostart):
            if filename.endswith('.desktop'):
                filepath = os.path.join(user_autostart, filename)
                app = parse_desktop_file(filepath)
                if app:
                    seen_names.add(filename)
                    apps.append(app)
    
    # Check system directories
    for sys_dir in system_autostart:
        if os.path.exists(sys_dir):
            for filename in os.listdir(sys_dir):
                if filename.endswith('.desktop') and filename not in seen_names:
                    filepath = os.path.join(sys_dir, filename)
                    app = parse_desktop_file(filepath)
                    if app:
                        seen_names.add(filename)
                        apps.append(app)
    
    return sorted(apps, key=lambda a: a.name.lower())


def parse_desktop_file(filepath: str) -> Optional[StartupApp]:
    """Parse a .desktop file into a StartupApp."""
    try:
        name = None
        exec_cmd = None
        icon = None
        comment = None
        hidden = False
        
        with open(filepath, 'r') as f:
            for line in f:
                line = line.strip()
                if line.startswith('Name='):
                    name = line[5:]
                elif line.startswith('Exec='):
                    exec_cmd = line[5:]
                elif line.startswith('Icon='):
                    icon = line[5:]
                elif line.startswith('Comment='):
                    comment = line[8:]
                elif line.startswith('Hidden='):
                    hidden = line[7:].lower() == 'true'
                elif line.startswith('X-GNOME-Autostart-enabled='):
                    hidden = line[26:].lower() == 'false'
        
        if name and exec_cmd:
            return StartupApp(
                name=name,
                exec_cmd=exec_cmd,
                enabled=not hidden,
                desktop_file=filepath,
                icon=icon,
                comment=comment
            )
    except Exception:
        pass
    return None


def toggle_autostart_app(app: StartupApp, enable: bool) -> bool:
    """Enable or disable an autostart app."""
    user_autostart = os.path.expanduser("~/.config/autostart")
    os.makedirs(user_autostart, exist_ok=True)
    
    filename = os.path.basename(app.desktop_file)
    user_file = os.path.join(user_autostart, filename)
    
    try:
        # If it's a system file, copy to user dir first
        if not app.desktop_file.startswith(user_autostart):
            with open(app.desktop_file, 'r') as f:
                content = f.read()
            with open(user_file, 'w') as f:
                f.write(content)
            app.desktop_file = user_file
        
        # Read current content
        with open(app.desktop_file, 'r') as f:
            lines = f.readlines()
        
        # Update or add the enabled line
        found = False
        new_lines = []
        for line in lines:
            if line.startswith('Hidden=') or line.startswith('X-GNOME-Autostart-enabled='):
                found = True
                if enable:
                    new_lines.append('X-GNOME-Autostart-enabled=true\n')
                else:
                    new_lines.append('X-GNOME-Autostart-enabled=false\n')
            else:
                new_lines.append(line)
        
        if not found:
            # Add before the last line or at end
            if enable:
                new_lines.append('X-GNOME-Autostart-enabled=true\n')
            else:
                new_lines.append('X-GNOME-Autostart-enabled=false\n')
        
        with open(app.desktop_file, 'w') as f:
            f.writelines(new_lines)
        
        return True
    except Exception:
        return False


# =============================================================================
# System Maintenance Page
# =============================================================================

@register_module(
    name="System Maintenance",
    description="Cleanup, updates, startup apps, storage",
    icon="applications-system-symbolic",
    category=ModuleCategory.SYSTEM,
    order=5
)
class SystemMaintenancePage(Adw.NavigationPage):
    """System maintenance module page."""
    
    def __init__(self, window):
        super().__init__(title="System Maintenance")
        
        self.window = window
        self.distro = get_distro()
        
        # Cache for sizes
        self.cleanup_sizes = {}
        self.updates_info = (False, 0, "")
        self.startup_apps = []
        
        self._build_ui()
        self._refresh_all()
    
    def _build_ui(self):
        """Build the page UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header (NavigationView handles back button automatically)
        header = Adw.HeaderBar()
        
        # Refresh button
        refresh_btn = Gtk.Button()
        refresh_btn.set_icon_name("view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh")
        refresh_btn.connect("clicked", lambda b: self._refresh_all())
        header.pack_end(refresh_btn)
        
        toolbar_view.add_top_bar(header)
        
        # Scrollable content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        toolbar_view.set_content(scrolled)
        
        # Content with clamp
        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_margin_top(24)
        clamp.set_margin_bottom(24)
        clamp.set_margin_start(24)
        clamp.set_margin_end(24)
        scrolled.set_child(clamp)
        
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        clamp.set_child(self.content_box)
        
        # Build sections
        self._build_cleanup_section()
        self._build_updates_section()
        self._build_startup_section()
        self._build_storage_section()
    
    def _build_cleanup_section(self):
        """Build the system cleanup section."""
        self.cleanup_group = Adw.PreferencesGroup()
        self.cleanup_group.set_title("System Cleanup")
        self.cleanup_group.set_description("Free up disk space by removing unnecessary files")
        self.content_box.append(self.cleanup_group)
        
        # Package cache row
        self.pkg_cache_row = Adw.ActionRow()
        self.pkg_cache_row.set_title("Package Cache")
        self.pkg_cache_row.set_subtitle("Cached package downloads")
        self.pkg_cache_row.add_prefix(Gtk.Image.new_from_icon_name("package-x-generic-symbolic"))
        
        self.pkg_cache_size = Gtk.Label(label="Calculating...")
        self.pkg_cache_size.add_css_class("dim-label")
        self.pkg_cache_row.add_suffix(self.pkg_cache_size)
        
        pkg_clean_btn = Gtk.Button(label="Clean")
        pkg_clean_btn.set_valign(Gtk.Align.CENTER)
        pkg_clean_btn.connect("clicked", self._on_clean_package_cache)
        self.pkg_cache_row.add_suffix(pkg_clean_btn)
        self.cleanup_group.add(self.pkg_cache_row)
        
        # User cache row
        self.user_cache_row = Adw.ActionRow()
        self.user_cache_row.set_title("Application Cache")
        self.user_cache_row.set_subtitle("Cached data from applications")
        self.user_cache_row.add_prefix(Gtk.Image.new_from_icon_name("folder-symbolic"))
        
        self.user_cache_size = Gtk.Label(label="Calculating...")
        self.user_cache_size.add_css_class("dim-label")
        self.user_cache_row.add_suffix(self.user_cache_size)
        
        user_clean_btn = Gtk.Button(label="Clean")
        user_clean_btn.set_valign(Gtk.Align.CENTER)
        user_clean_btn.connect("clicked", self._on_clean_user_cache)
        self.user_cache_row.add_suffix(user_clean_btn)
        self.cleanup_group.add(self.user_cache_row)
        
        # Thumbnails row
        self.thumb_row = Adw.ActionRow()
        self.thumb_row.set_title("Thumbnail Cache")
        self.thumb_row.set_subtitle("Cached image previews")
        self.thumb_row.add_prefix(Gtk.Image.new_from_icon_name("image-x-generic-symbolic"))
        
        self.thumb_size = Gtk.Label(label="Calculating...")
        self.thumb_size.add_css_class("dim-label")
        self.thumb_row.add_suffix(self.thumb_size)
        
        thumb_clean_btn = Gtk.Button(label="Clean")
        thumb_clean_btn.set_valign(Gtk.Align.CENTER)
        thumb_clean_btn.connect("clicked", self._on_clean_thumbnails)
        self.thumb_row.add_suffix(thumb_clean_btn)
        self.cleanup_group.add(self.thumb_row)
        
        # Journal logs row
        self.journal_row = Adw.ActionRow()
        self.journal_row.set_title("System Logs")
        self.journal_row.set_subtitle("Old journal logs (keeps last 7 days)")
        self.journal_row.add_prefix(Gtk.Image.new_from_icon_name("text-x-generic-symbolic"))
        
        self.journal_size = Gtk.Label(label="Calculating...")
        self.journal_size.add_css_class("dim-label")
        self.journal_row.add_suffix(self.journal_size)
        
        journal_clean_btn = Gtk.Button(label="Clean")
        journal_clean_btn.set_valign(Gtk.Align.CENTER)
        journal_clean_btn.connect("clicked", self._on_clean_journal)
        self.journal_row.add_suffix(journal_clean_btn)
        self.cleanup_group.add(self.journal_row)
        
        # Trash row
        self.trash_row = Adw.ActionRow()
        self.trash_row.set_title("Trash")
        self.trash_row.set_subtitle("Deleted files waiting to be removed")
        self.trash_row.add_prefix(Gtk.Image.new_from_icon_name("user-trash-full-symbolic"))
        
        self.trash_size = Gtk.Label(label="Calculating...")
        self.trash_size.add_css_class("dim-label")
        self.trash_row.add_suffix(self.trash_size)
        
        trash_clean_btn = Gtk.Button(label="Empty")
        trash_clean_btn.set_valign(Gtk.Align.CENTER)
        trash_clean_btn.connect("clicked", self._on_empty_trash)
        self.trash_row.add_suffix(trash_clean_btn)
        self.cleanup_group.add(self.trash_row)
        
        # Clean All button
        clean_all_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        clean_all_box.set_halign(Gtk.Align.END)
        clean_all_box.set_margin_top(8)
        
        self.clean_all_btn = Gtk.Button(label="Clean All")
        self.clean_all_btn.add_css_class("suggested-action")
        self.clean_all_btn.connect("clicked", self._on_clean_all)
        clean_all_box.append(self.clean_all_btn)
        
        # Add to group via a row
        clean_all_row = Adw.ActionRow()
        clean_all_row.set_activatable(False)
        clean_all_row.add_suffix(self.clean_all_btn)
        self.cleanup_group.add(clean_all_row)
    
    def _build_updates_section(self):
        """Build the system updates section."""
        self.updates_group = Adw.PreferencesGroup()
        self.updates_group.set_title("System Updates")
        self.updates_group.set_description("Keep your system up to date")
        self.content_box.append(self.updates_group)
        
        # Update status row
        self.update_row = Adw.ActionRow()
        self.update_row.set_title("Available Updates")
        self.update_row.set_subtitle("Checking...")
        self.update_row.add_prefix(Gtk.Image.new_from_icon_name("software-update-available-symbolic"))
        
        self.update_count = Gtk.Label(label="...")
        self.update_count.add_css_class("dim-label")
        self.update_row.add_suffix(self.update_count)
        
        self.update_btn = Gtk.Button(label="Update")
        self.update_btn.set_valign(Gtk.Align.CENTER)
        self.update_btn.add_css_class("suggested-action")
        self.update_btn.connect("clicked", self._on_run_updates)
        self.update_btn.set_sensitive(False)
        self.update_row.add_suffix(self.update_btn)
        
        self.updates_group.add(self.update_row)
    
    def _build_startup_section(self):
        """Build the startup apps section."""
        self.startup_group = Adw.PreferencesGroup()
        self.startup_group.set_title("Startup Applications")
        self.startup_group.set_description("Apps that run when you log in")
        self.content_box.append(self.startup_group)
        
        # Placeholder - will be populated by _refresh_startup_apps
        self.startup_placeholder = Adw.ActionRow()
        self.startup_placeholder.set_title("Loading...")
        self.startup_group.add(self.startup_placeholder)
    
    def _build_storage_section(self):
        """Build the storage overview section."""
        self.storage_group = Adw.PreferencesGroup()
        self.storage_group.set_title("Storage")
        self.storage_group.set_description("Disk usage overview")
        self.content_box.append(self.storage_group)
        
        # Disk usage row
        self.disk_row = Adw.ActionRow()
        self.disk_row.set_title("Disk Usage")
        self.disk_row.set_subtitle("Analyzing...")
        self.disk_row.add_prefix(Gtk.Image.new_from_icon_name("drive-harddisk-symbolic"))
        
        disk_btn = Gtk.Button(label="Analyze")
        disk_btn.set_valign(Gtk.Align.CENTER)
        disk_btn.connect("clicked", self._on_analyze_storage)
        self.disk_row.add_suffix(disk_btn)
        
        self.storage_group.add(self.disk_row)
    
    def _refresh_all(self):
        """Refresh all sections."""
        self._refresh_cleanup_sizes()
        self._refresh_updates()
        self._refresh_startup_apps()
        self._refresh_storage()
    
    def _refresh_cleanup_sizes(self):
        """Refresh cleanup section sizes in background."""
        def calculate():
            sizes = {
                'pkg_cache': get_package_cache_size(self.distro.family),
                'user_cache': get_user_cache_size(),
                'thumbnails': get_thumbnail_cache_size(),
                'journal': get_journal_size(),
                'trash': get_trash_size(),
            }
            GLib.idle_add(self._update_cleanup_sizes, sizes)
        
        threading.Thread(target=calculate, daemon=True).start()
    
    def _update_cleanup_sizes(self, sizes: dict):
        """Update cleanup size labels."""
        self.cleanup_sizes = sizes
        
        self.pkg_cache_size.set_label(get_human_size(sizes['pkg_cache']))
        self.user_cache_size.set_label(get_human_size(sizes['user_cache']))
        self.thumb_size.set_label(get_human_size(sizes['thumbnails']))
        self.journal_size.set_label(get_human_size(sizes['journal']))
        self.trash_size.set_label(get_human_size(sizes['trash']))
        
        total = sum(sizes.values())
        self.clean_all_btn.set_label(f"Clean All ({get_human_size(total)})")
    
    def _refresh_updates(self):
        """Check for updates in background."""
        def check():
            info = check_updates_available(self.distro.family)
            GLib.idle_add(self._update_updates_status, info)
        
        threading.Thread(target=check, daemon=True).start()
    
    def _update_updates_status(self, info: Tuple[bool, int, str]):
        """Update the updates section."""
        has_updates, count, details = info
        self.updates_info = info
        
        if has_updates:
            self.update_row.set_subtitle(f"{count} update{'s' if count != 1 else ''} available")
            self.update_count.set_label(str(count))
            self.update_btn.set_sensitive(True)
            self.update_row.set_icon_name("software-update-available-symbolic")
        else:
            self.update_row.set_subtitle("Your system is up to date")
            self.update_count.set_label("✓")
            self.update_btn.set_sensitive(False)
    
    def _refresh_startup_apps(self):
        """Refresh startup apps list."""
        def load():
            apps = get_autostart_apps()
            GLib.idle_add(self._update_startup_apps, apps)
        
        threading.Thread(target=load, daemon=True).start()
    
    def _update_startup_apps(self, apps: List[StartupApp]):
        """Update startup apps UI."""
        self.startup_apps = apps
        
        # Clear existing rows
        while True:
            row = self.startup_group.get_first_child()
            if row:
                self.startup_group.remove(row)
            else:
                break
        
        if not apps:
            empty_row = Adw.ActionRow()
            empty_row.set_title("No startup applications")
            empty_row.set_subtitle("Apps added here will run when you log in")
            self.startup_group.add(empty_row)
            return
        
        for app in apps:
            row = Adw.ActionRow()
            row.set_title(app.name)
            row.set_subtitle(app.comment or app.exec_cmd)
            
            # Icon
            if app.icon:
                row.add_prefix(Gtk.Image.new_from_icon_name(app.icon))
            else:
                row.add_prefix(Gtk.Image.new_from_icon_name("application-x-executable-symbolic"))
            
            # Toggle switch
            switch = Gtk.Switch()
            switch.set_active(app.enabled)
            switch.set_valign(Gtk.Align.CENTER)
            switch.connect("state-set", self._on_startup_toggled, app)
            row.add_suffix(switch)
            
            self.startup_group.add(row)
    
    def _refresh_storage(self):
        """Refresh storage info."""
        def check():
            try:
                # Get root filesystem usage
                statvfs = os.statvfs('/')
                total = statvfs.f_blocks * statvfs.f_frsize
                free = statvfs.f_bavail * statvfs.f_frsize
                used = total - free
                percent = (used / total) * 100
                
                GLib.idle_add(
                    self._update_storage_info,
                    used, total, percent
                )
            except Exception:
                pass
        
        threading.Thread(target=check, daemon=True).start()
    
    def _update_storage_info(self, used: int, total: int, percent: float):
        """Update storage display."""
        self.disk_row.set_subtitle(
            f"{get_human_size(used)} used of {get_human_size(total)} ({percent:.1f}%)"
        )
    
    # =========================================================================
    # Cleanup Actions
    # =========================================================================
    
    def _on_clean_package_cache(self, button):
        """Clean package manager cache."""
        commands = {
            DistroFamily.ARCH: "sudo paccache -rk1 && sudo paccache -ruk0",
            DistroFamily.DEBIAN: "sudo apt-get clean",
            DistroFamily.FEDORA: "sudo dnf clean all",
            DistroFamily.OPENSUSE: "sudo zypper clean --all",
        }
        cmd = commands.get(self.distro.family)
        if cmd:
            self._run_cleanup_command(cmd, "Package cache cleaned!")
    
    def _on_clean_user_cache(self, button):
        """Clean user application cache."""
        # Be careful - only clean safe directories
        cache_path = os.path.expanduser("~/.cache")
        
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Clean Application Cache?",
            body="This will remove cached data from applications.\nSome apps may run slower temporarily while they rebuild their cache."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("clean", "Clean")
        dialog.set_response_appearance("clean", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.connect("response", self._on_user_cache_confirm)
        dialog.present()
    
    def _on_user_cache_confirm(self, dialog, response):
        """Handle user cache clean confirmation."""
        if response == "clean":
            # Clean specific safe cache directories
            safe_dirs = [
                "~/.cache/mesa_shader_cache",
                "~/.cache/fontconfig",
                "~/.cache/pip",
                "~/.cache/yarn",
                "~/.cache/npm",
            ]
            for d in safe_dirs:
                path = os.path.expanduser(d)
                if os.path.exists(path):
                    try:
                        subprocess.run(['rm', '-rf', path])
                    except Exception:
                        pass
            
            self.window.show_toast("Application cache cleaned!")
            self._refresh_cleanup_sizes()
    
    def _on_clean_thumbnails(self, button):
        """Clean thumbnail cache."""
        thumb_path = os.path.expanduser("~/.cache/thumbnails")
        if os.path.exists(thumb_path):
            try:
                subprocess.run(['rm', '-rf', thumb_path])
                os.makedirs(thumb_path, exist_ok=True)
                self.window.show_toast("Thumbnail cache cleared!")
                self._refresh_cleanup_sizes()
            except Exception as e:
                self.window.show_toast(f"Error: {e}")
    
    def _on_clean_journal(self, button):
        """Clean old journal logs."""
        self._run_cleanup_command(
            "sudo journalctl --vacuum-time=7d",
            "Old logs cleaned! (Kept last 7 days)"
        )
    
    def _on_empty_trash(self, button):
        """Empty the trash."""
        trash_path = os.path.expanduser("~/.local/share/Trash")
        
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Empty Trash?",
            body="This will permanently delete all items in the trash.\nThis cannot be undone."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("empty", "Empty Trash")
        dialog.set_response_appearance("empty", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.connect("response", self._on_empty_trash_confirm, trash_path)
        dialog.present()
    
    def _on_empty_trash_confirm(self, dialog, response, trash_path):
        """Handle trash empty confirmation."""
        if response == "empty":
            try:
                # Remove trash contents
                files_dir = os.path.join(trash_path, "files")
                info_dir = os.path.join(trash_path, "info")
                
                if os.path.exists(files_dir):
                    subprocess.run(['rm', '-rf', files_dir])
                    os.makedirs(files_dir, exist_ok=True)
                if os.path.exists(info_dir):
                    subprocess.run(['rm', '-rf', info_dir])
                    os.makedirs(info_dir, exist_ok=True)
                
                self.window.show_toast("Trash emptied!")
                self._refresh_cleanup_sizes()
            except Exception as e:
                self.window.show_toast(f"Error: {e}")
    
    def _on_clean_all(self, button):
        """Clean all cleanable items."""
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Clean Everything?",
            body="This will clean:\n• Package cache\n• Thumbnail cache\n• Old system logs\n• Trash\n\nContinue?"
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("clean", "Clean All")
        dialog.set_response_appearance("clean", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("clean")
        dialog.connect("response", self._on_clean_all_confirm)
        dialog.present()
    
    def _on_clean_all_confirm(self, dialog, response):
        """Handle clean all confirmation."""
        if response == "clean":
            # Do the cleaning
            self._on_clean_thumbnails(None)
            self._on_clean_journal(None)
            # Empty trash without confirmation since we already asked
            trash_path = os.path.expanduser("~/.local/share/Trash")
            try:
                files_dir = os.path.join(trash_path, "files")
                info_dir = os.path.join(trash_path, "info")
                if os.path.exists(files_dir):
                    subprocess.run(['rm', '-rf', files_dir])
                    os.makedirs(files_dir, exist_ok=True)
                if os.path.exists(info_dir):
                    subprocess.run(['rm', '-rf', info_dir])
                    os.makedirs(info_dir, exist_ok=True)
            except Exception:
                pass
            
            # Package cache last (needs sudo)
            self._on_clean_package_cache(None)
    
    def _run_cleanup_command(self, command: str, success_message: str):
        """Run a cleanup command in terminal."""
        script = f'''echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  System Cleanup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
{command}
echo ""
echo "✓ Done!"
echo ""
echo "Press Enter to close..."
read'''
        
        self._run_in_terminal(script)
        
        # Refresh after delay
        GLib.timeout_add(2000, self._refresh_cleanup_sizes)
    
    # =========================================================================
    # Update Actions
    # =========================================================================
    
    def _on_run_updates(self, button):
        """Run system updates."""
        commands = {
            DistroFamily.ARCH: "sudo pacman -Syu",
            DistroFamily.DEBIAN: "sudo apt update && sudo apt upgrade",
            DistroFamily.FEDORA: "sudo dnf upgrade",
            DistroFamily.OPENSUSE: "sudo zypper update",
        }
        cmd = commands.get(self.distro.family, "echo 'Unknown distribution'")
        
        script = f'''echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  System Update"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
{cmd}
echo ""
echo "✓ Update complete!"
echo ""
echo "Press Enter to close..."
read'''
        
        self._run_in_terminal(script)
        
        # Refresh after delay
        GLib.timeout_add(5000, self._refresh_updates)
    
    # =========================================================================
    # Startup App Actions
    # =========================================================================
    
    def _on_startup_toggled(self, switch, state, app: StartupApp):
        """Handle startup app toggle."""
        success = toggle_autostart_app(app, state)
        if success:
            app.enabled = state
            self.window.show_toast(
                f"{app.name} {'enabled' if state else 'disabled'} at startup"
            )
        else:
            # Revert switch
            switch.set_active(not state)
            self.window.show_toast(f"Failed to update {app.name}")
        return True
    
    # =========================================================================
    # Storage Actions
    # =========================================================================
    
    def _on_analyze_storage(self, button):
        """Open disk usage analyzer."""
        # Try to open a disk analyzer
        analyzers = [
            'baobab',           # GNOME Disk Usage Analyzer
            'filelight',        # KDE
            'qdirstat',         # Qt-based
            'ncdu',             # Terminal-based
        ]
        
        for analyzer in analyzers:
            try:
                result = subprocess.run(['which', analyzer], capture_output=True)
                if result.returncode == 0:
                    subprocess.Popen([analyzer])
                    return
            except Exception:
                continue
        
        # If no analyzer found, offer to install one
        self.window.show_toast("No disk analyzer found. Install 'baobab' or 'filelight'.")
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def _run_in_terminal(self, script: str):
        """Run a script in a terminal window."""
        terminals = [
            ('konsole', ['konsole', '-e', 'bash', '-c', script]),
            ('gnome-terminal', ['gnome-terminal', '--', 'bash', '-c', script]),
            ('xfce4-terminal', ['xfce4-terminal', '-e', f'bash -c \'{script}\'']),
            ('tilix', ['tilix', '-e', f'bash -c "{script}"']),
            ('alacritty', ['alacritty', '-e', 'bash', '-c', script]),
            ('kitty', ['kitty', 'bash', '-c', script]),
        ]
        
        for term_name, term_cmd in terminals:
            try:
                if subprocess.run(['which', term_name], capture_output=True).returncode == 0:
                    subprocess.Popen(term_cmd)
                    return
            except Exception:
                continue
        
        self.window.show_toast("Could not find terminal emulator")
