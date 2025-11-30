"""
Tux Assistant - Backup & Restore Module

Simple file backup and Timeshift integration.
Keeps it simple - backup folders to external drive, manage snapshots.

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

import os
import subprocess
import threading
import json
from datetime import datetime
from gi.repository import Gtk, Adw, GLib, Gio
from typing import Optional, List
from dataclasses import dataclass
from pathlib import Path

from ..core import get_distro, DistroFamily

from .registry import register_module, ModuleCategory


# =============================================================================
# Backup Utilities
# =============================================================================

@dataclass
class BackupLocation:
    """A backup destination."""
    name: str
    path: str
    mount_point: str
    device: str
    size_total: int
    size_free: int
    location_type: str  # "internal", "external", "network", "custom"


def get_human_size(size_bytes: int) -> str:
    """Convert bytes to human readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def get_backup_destinations() -> List[BackupLocation]:
    """Get available backup destinations (all usable drives)."""
    destinations = []
    seen_mounts = set()
    
    try:
        # Use lsblk to find mounted drives
        result = subprocess.run(
            ['lsblk', '-J', '-o', 'NAME,SIZE,MOUNTPOINT,FSTYPE,HOTPLUG,RM,TYPE'],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            data = json.loads(result.stdout)
            
            for device in data.get('blockdevices', []):
                _process_device(device, destinations, seen_mounts)
                
                # Check children (partitions)
                for child in device.get('children', []):
                    _process_device(child, destinations, seen_mounts, parent=device.get('name', ''))
    
    except Exception:
        pass
    
    # Check common mount points for anything we missed
    common_mounts = ['/mnt', '/media', '/run/media']
    for mount_base in common_mounts:
        if os.path.exists(mount_base):
            try:
                # Check subdirectories (user mounts often in /run/media/username/)
                for name in os.listdir(mount_base):
                    path = os.path.join(mount_base, name)
                    _check_mount_path(path, destinations, seen_mounts)
                    
                    # Check one level deeper for /run/media/user/drive
                    if os.path.isdir(path):
                        try:
                            for subname in os.listdir(path):
                                subpath = os.path.join(path, subname)
                                _check_mount_path(subpath, destinations, seen_mounts)
                        except Exception:
                            pass
            except Exception:
                pass
    
    # Check for network mounts
    _find_network_mounts(destinations, seen_mounts)
    
    return destinations


def _process_device(device: dict, destinations: List[BackupLocation], seen_mounts: set, parent: str = ""):
    """Process a device from lsblk output."""
    mount = device.get('mountpoint')
    
    # Skip if not mounted
    if not mount or mount in seen_mounts:
        return
    
    # Skip system mounts
    skip_mounts = ['/', '/boot', '/boot/efi', '/home', '[SWAP]', '/var', '/tmp', '/usr']
    if mount in skip_mounts:
        return
    
    # Skip if no filesystem
    if not device.get('fstype'):
        return
    
    is_removable = device.get('rm', False) or device.get('hotplug', False)
    
    try:
        statvfs = os.statvfs(mount)
        total = statvfs.f_blocks * statvfs.f_frsize
        free = statvfs.f_bavail * statvfs.f_frsize
        
        if total > 0:
            name = os.path.basename(mount) or device.get('name', 'Drive')
            loc_type = "external" if is_removable else "internal"
            
            destinations.append(BackupLocation(
                name=name,
                path=mount,
                mount_point=mount,
                device=f"/dev/{device.get('name', '')}",
                size_total=total,
                size_free=free,
                location_type=loc_type
            ))
            seen_mounts.add(mount)
    except Exception:
        pass


def _check_mount_path(path: str, destinations: List[BackupLocation], seen_mounts: set):
    """Check if a path is a valid mount point and add it."""
    if path in seen_mounts:
        return
    
    if not os.path.ismount(path):
        return
    
    try:
        statvfs = os.statvfs(path)
        total = statvfs.f_blocks * statvfs.f_frsize
        free = statvfs.f_bavail * statvfs.f_frsize
        
        if total > 0:
            name = os.path.basename(path) or "Drive"
            destinations.append(BackupLocation(
                name=name,
                path=path,
                mount_point=path,
                device="",
                size_total=total,
                size_free=free,
                location_type="external"
            ))
            seen_mounts.add(path)
    except Exception:
        pass


def _find_network_mounts(destinations: List[BackupLocation], seen_mounts: set):
    """Find network mounts (CIFS/NFS)."""
    try:
        with open('/proc/mounts', 'r') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 3:
                    device, mount, fstype = parts[0], parts[1], parts[2]
                    
                    # Skip if already seen
                    if mount in seen_mounts:
                        continue
                    
                    # Check for network filesystems
                    if fstype in ['cifs', 'nfs', 'nfs4', 'smbfs']:
                        try:
                            statvfs = os.statvfs(mount)
                            total = statvfs.f_blocks * statvfs.f_frsize
                            free = statvfs.f_bavail * statvfs.f_frsize
                            
                            if total > 0:
                                # Extract share name from device
                                name = os.path.basename(mount) or device.split('/')[-1] or "Network Drive"
                                
                                destinations.append(BackupLocation(
                                    name=f"🌐 {name}",
                                    path=mount,
                                    mount_point=mount,
                                    device=device,
                                    size_total=total,
                                    size_free=free,
                                    location_type="network"
                                ))
                                seen_mounts.add(mount)
                        except Exception:
                            pass
    except Exception:
        pass


def check_timeshift_installed() -> bool:
    """Check if Timeshift is installed."""
    try:
        result = subprocess.run(['which', 'timeshift'], capture_output=True)
        return result.returncode == 0
    except Exception:
        return False


def check_rsync_installed() -> bool:
    """Check if rsync is installed."""
    try:
        result = subprocess.run(['which', 'rsync'], capture_output=True)
        return result.returncode == 0
    except Exception:
        return False


def get_timeshift_snapshots() -> List[dict]:
    """Get list of Timeshift snapshots."""
    snapshots = []
    
    try:
        result = subprocess.run(
            ['pkexec', 'timeshift', '--list'],
            capture_output=True, text=True
        )
        
        if result.returncode != 0:
            return snapshots
        
        # Parse output - it's a table format
        lines = result.stdout.strip().split('\n')
        in_table = False
        
        for line in lines:
            if '---' in line:
                in_table = True
                continue
            
            if in_table and line.strip():
                parts = line.split()
                if len(parts) >= 3:
                    snapshots.append({
                        'name': parts[0],
                        'date': ' '.join(parts[1:3]) if len(parts) > 2 else parts[1],
                        'tags': parts[3] if len(parts) > 3 else '',
                    })
    
    except Exception:
        pass
    
    return snapshots


# =============================================================================
# Default Backup Folders
# =============================================================================

DEFAULT_BACKUP_FOLDERS = [
    ("Documents", os.path.expanduser("~/Documents")),
    ("Pictures", os.path.expanduser("~/Pictures")),
    ("Music", os.path.expanduser("~/Music")),
    ("Videos", os.path.expanduser("~/Videos")),
    ("Desktop", os.path.expanduser("~/Desktop")),
]


# =============================================================================
# Backup & Restore Page
# =============================================================================

@register_module(
    id="backup_restore",
    name="Backup & Restore",
    description="File backup and system snapshots",
    icon="drive-harddisk-symbolic",
    category=ModuleCategory.SYSTEM,
    order=15
)
class BackupRestorePage(Adw.NavigationPage):
    """Backup and restore module page."""
    
    def __init__(self, window):
        super().__init__(title="Backup & Restore")
        
        self.window = window
        self.distro = get_distro()
        self.has_timeshift = check_timeshift_installed()
        self.destinations = []
        self.selected_destination = None
        self.selected_folders = set()
        
        self._build_ui()
        self._refresh_destinations()
    
    def _build_ui(self):
        """Build the page UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header
        header = Adw.HeaderBar()
        
        # Refresh button
        refresh_btn = Gtk.Button()
        refresh_btn.set_icon_name("view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh")
        refresh_btn.connect("clicked", lambda b: self._refresh_destinations())
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
        self._build_file_backup_section()
        self._build_timeshift_section()
        self._build_tips_section()
    
    def _build_file_backup_section(self):
        """Build the file backup section."""
        self.backup_group = Adw.PreferencesGroup()
        self.backup_group.set_title("File Backup")
        self.backup_group.set_description("Back up your personal files to any drive or network location")
        self.content_box.append(self.backup_group)
        
        # Destination selector
        self.dest_row = Adw.ComboRow()
        self.dest_row.set_title("Backup Destination")
        self.dest_row.set_subtitle("Select a destination")
        self.dest_row.add_prefix(Gtk.Image.new_from_icon_name("drive-harddisk-symbolic"))
        
        # Model for destinations
        self.dest_model = Gtk.StringList()
        self.dest_row.set_model(self.dest_model)
        self.dest_row.connect("notify::selected", self._on_destination_changed)
        
        self.backup_group.add(self.dest_row)
        
        # Additional destination options
        dest_options_row = Adw.ActionRow()
        dest_options_row.set_title("More Options")
        dest_options_row.set_subtitle("Browse for folder or connect to network share")
        dest_options_row.add_prefix(Gtk.Image.new_from_icon_name("list-add-symbolic"))
        
        # Browse button
        browse_btn = Gtk.Button(label="Browse...")
        browse_btn.set_valign(Gtk.Align.CENTER)
        browse_btn.set_tooltip_text("Select any folder as backup destination")
        browse_btn.connect("clicked", self._on_browse_destination)
        dest_options_row.add_suffix(browse_btn)
        
        # Network button
        network_btn = Gtk.Button(label="Network...")
        network_btn.set_valign(Gtk.Align.CENTER)
        network_btn.set_tooltip_text("Connect to a network share (Samba/NFS)")
        network_btn.connect("clicked", self._on_connect_network)
        dest_options_row.add_suffix(network_btn)
        
        self.backup_group.add(dest_options_row)
        
        # Folders to backup
        self.folders_expander = Adw.ExpanderRow()
        self.folders_expander.set_title("Folders to Backup")
        self.folders_expander.set_subtitle("Select which folders to include")
        self.folders_expander.add_prefix(Gtk.Image.new_from_icon_name("folder-symbolic"))
        self.backup_group.add(self.folders_expander)
        
        # Add default folder checkboxes
        self.folder_checks = {}
        for name, path in DEFAULT_BACKUP_FOLDERS:
            if os.path.exists(path):
                row = Adw.ActionRow()
                row.set_title(name)
                row.set_subtitle(path)
                
                check = Gtk.CheckButton()
                check.set_active(True)
                check.set_valign(Gtk.Align.CENTER)
                check.connect("toggled", self._on_folder_toggled, path)
                row.add_suffix(check)
                row.set_activatable_widget(check)
                
                self.folders_expander.add_row(row)
                self.folder_checks[path] = check
                self.selected_folders.add(path)
        
        # Custom folder button
        add_folder_row = Adw.ActionRow()
        add_folder_row.set_title("Add Custom Folder")
        add_folder_row.set_subtitle("Browse for additional folders")
        
        add_btn = Gtk.Button()
        add_btn.set_icon_name("list-add-symbolic")
        add_btn.set_valign(Gtk.Align.CENTER)
        add_btn.connect("clicked", self._on_add_custom_folder)
        add_folder_row.add_suffix(add_btn)
        
        self.folders_expander.add_row(add_folder_row)
        
        # Backup button
        backup_row = Adw.ActionRow()
        backup_row.set_activatable(False)
        
        self.backup_btn = Gtk.Button(label="Start Backup")
        self.backup_btn.add_css_class("suggested-action")
        self.backup_btn.set_valign(Gtk.Align.CENTER)
        self.backup_btn.connect("clicked", self._on_start_backup)
        self.backup_btn.set_sensitive(False)
        backup_row.add_suffix(self.backup_btn)
        
        self.backup_group.add(backup_row)
    
    def _build_timeshift_section(self):
        """Build the Timeshift system snapshots section."""
        self.timeshift_group = Adw.PreferencesGroup()
        self.timeshift_group.set_title("System Snapshots")
        self.timeshift_group.set_description("Create and restore system snapshots with Timeshift")
        self.content_box.append(self.timeshift_group)
        
        if not self.has_timeshift:
            # Offer to install
            install_row = Adw.ActionRow()
            install_row.set_title("Timeshift Not Installed")
            install_row.set_subtitle("Install Timeshift to create system snapshots")
            install_row.add_prefix(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
            
            install_btn = Gtk.Button(label="Install")
            install_btn.set_valign(Gtk.Align.CENTER)
            install_btn.connect("clicked", self._on_install_timeshift)
            install_row.add_suffix(install_btn)
            
            self.timeshift_group.add(install_row)
        else:
            # Create snapshot row
            create_row = Adw.ActionRow()
            create_row.set_title("Create Snapshot")
            create_row.set_subtitle("Take a snapshot of your current system state")
            create_row.add_prefix(Gtk.Image.new_from_icon_name("list-add-symbolic"))
            
            create_btn = Gtk.Button(label="Create")
            create_btn.set_valign(Gtk.Align.CENTER)
            create_btn.add_css_class("suggested-action")
            create_btn.connect("clicked", self._on_create_snapshot)
            create_row.add_suffix(create_btn)
            
            self.timeshift_group.add(create_row)
            
            # Open Timeshift row
            open_row = Adw.ActionRow()
            open_row.set_title("Open Timeshift")
            open_row.set_subtitle("Manage snapshots, restore, and configure settings")
            open_row.add_prefix(Gtk.Image.new_from_icon_name("applications-system-symbolic"))
            
            open_btn = Gtk.Button(label="Open")
            open_btn.set_valign(Gtk.Align.CENTER)
            open_btn.connect("clicked", self._on_open_timeshift)
            open_row.add_suffix(open_btn)
            
            self.timeshift_group.add(open_row)
    
    def _build_tips_section(self):
        """Build the tips section."""
        tips_group = Adw.PreferencesGroup()
        tips_group.set_title("Backup Tips")
        self.content_box.append(tips_group)
        
        tips = [
            ("3-2-1 Rule", "Keep 3 copies on 2 different media with 1 offsite"),
            ("Regular Backups", "Back up weekly at minimum, daily for important work"),
            ("Test Restores", "Occasionally verify your backups can actually be restored"),
            ("System vs Files", "Timeshift = system recovery, File Backup = your personal data"),
        ]
        
        for title, subtitle in tips:
            row = Adw.ActionRow()
            row.set_title(title)
            row.set_subtitle(subtitle)
            row.add_prefix(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
            tips_group.add(row)
    
    def _refresh_destinations(self):
        """Refresh available backup destinations."""
        def load():
            destinations = get_backup_destinations()
            GLib.idle_add(self._update_destinations, destinations)
        
        threading.Thread(target=load, daemon=True).start()
    
    def _update_destinations(self, destinations: List[BackupLocation]):
        """Update destination dropdown."""
        self.destinations = destinations
        
        # Clear existing
        while self.dest_model.get_n_items() > 0:
            self.dest_model.remove(0)
        
        if not destinations:
            self.dest_model.append("No drives found - use Browse or Network")
            self.dest_row.set_subtitle("Use options below to select a destination")
            self.backup_btn.set_sensitive(False)
            self.selected_destination = None
        else:
            for dest in destinations:
                # Add type indicator
                type_icons = {
                    "internal": "💾",
                    "external": "🔌",
                    "network": "🌐",
                    "custom": "📁"
                }
                icon = type_icons.get(dest.location_type, "📁")
                label = f"{icon} {dest.name} ({get_human_size(dest.size_free)} free)"
                self.dest_model.append(label)
            
            self.dest_row.set_selected(0)
            self.selected_destination = destinations[0]
            self.backup_btn.set_sensitive(True)
            type_label = destinations[0].location_type.capitalize()
            self.dest_row.set_subtitle(f"{type_label}: {destinations[0].path}")
    
    def _on_destination_changed(self, row, param):
        """Handle destination selection change."""
        idx = row.get_selected()
        if idx < len(self.destinations):
            self.selected_destination = self.destinations[idx]
            type_label = self.selected_destination.location_type.capitalize()
            self.dest_row.set_subtitle(f"{type_label}: {self.selected_destination.path}")
            self.backup_btn.set_sensitive(True)
        else:
            self.selected_destination = None
            self.backup_btn.set_sensitive(False)
    
    def _on_folder_toggled(self, check, path):
        """Handle folder checkbox toggle."""
        if check.get_active():
            self.selected_folders.add(path)
        else:
            self.selected_folders.discard(path)
    
    def _on_browse_destination(self, button):
        """Browse for a custom backup destination folder."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Backup Destination Folder")
        
        # Start in /mnt or home
        start_path = "/mnt" if os.path.exists("/mnt") else os.path.expanduser("~")
        dialog.set_initial_folder(Gio.File.new_for_path(start_path))
        
        dialog.select_folder(self.window, None, self._on_browse_destination_selected)
    
    def _on_browse_destination_selected(self, dialog, result):
        """Handle custom destination folder selection."""
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                path = folder.get_path()
                
                # Check if writable
                if not os.access(path, os.W_OK):
                    self.window.show_toast("Cannot write to this location")
                    return
                
                # Get size info
                try:
                    statvfs = os.statvfs(path)
                    total = statvfs.f_blocks * statvfs.f_frsize
                    free = statvfs.f_bavail * statvfs.f_frsize
                except Exception:
                    total = 0
                    free = 0
                
                # Add as custom destination
                name = os.path.basename(path) or "Custom Location"
                custom_dest = BackupLocation(
                    name=name,
                    path=path,
                    mount_point=path,
                    device="",
                    size_total=total,
                    size_free=free,
                    location_type="custom"
                )
                
                # Add to list if not already there
                if not any(d.path == path for d in self.destinations):
                    self.destinations.append(custom_dest)
                    label = f"📁 {name} ({get_human_size(free)} free)"
                    self.dest_model.append(label)
                
                # Select it
                for i, dest in enumerate(self.destinations):
                    if dest.path == path:
                        self.dest_row.set_selected(i)
                        break
                
                self.window.show_toast(f"Added: {name}")
        except Exception as e:
            self.window.show_toast(f"Error: {str(e)}")
    
    def _on_connect_network(self, button):
        """Show network share connection dialog."""
        dialog = Adw.Dialog()
        dialog.set_title("Connect to Network Share")
        dialog.set_content_width(450)
        dialog.set_content_height(400)
        
        toolbar_view = Adw.ToolbarView()
        dialog.set_child(toolbar_view)
        
        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: dialog.close())
        header.pack_start(cancel_btn)
        
        connect_btn = Gtk.Button(label="Connect")
        connect_btn.add_css_class("suggested-action")
        header.pack_end(connect_btn)
        
        toolbar_view.add_top_bar(header)
        
        # Content
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)
        toolbar_view.set_content(content)
        
        # Instructions
        instructions = Gtk.Label(label="Connect to a Samba (Windows) or NFS share")
        instructions.add_css_class("dim-label")
        content.append(instructions)
        
        # Form
        form_group = Adw.PreferencesGroup()
        content.append(form_group)
        
        # Share type
        type_row = Adw.ComboRow()
        type_row.set_title("Share Type")
        type_model = Gtk.StringList()
        type_model.append("Samba (Windows Share)")
        type_model.append("NFS")
        type_row.set_model(type_model)
        form_group.add(type_row)
        
        # Server address
        server_row = Adw.EntryRow()
        server_row.set_title("Server Address")
        server_row.set_text("")
        form_group.add(server_row)
        
        # Share name
        share_row = Adw.EntryRow()
        share_row.set_title("Share Name")
        share_row.set_text("")
        form_group.add(share_row)
        
        # Username (for Samba)
        user_row = Adw.EntryRow()
        user_row.set_title("Username (optional)")
        user_row.set_text("")
        form_group.add(user_row)
        
        # Password (for Samba)
        pass_row = Adw.PasswordEntryRow()
        pass_row.set_title("Password (optional)")
        form_group.add(pass_row)
        
        # Mount point
        mount_row = Adw.EntryRow()
        mount_row.set_title("Mount Point")
        mount_row.set_text("/mnt/backup")
        form_group.add(mount_row)
        
        # Example
        example = Gtk.Label(label="Example: Server: 192.168.1.100, Share: backups")
        example.add_css_class("dim-label")
        example.set_margin_top(8)
        content.append(example)
        
        # Connect handler
        connect_btn.connect("clicked", self._on_network_connect_clicked, dialog,
                          type_row, server_row, share_row, user_row, pass_row, mount_row)
        
        dialog.present(self.window)
    
    def _on_network_connect_clicked(self, button, dialog, type_row, server_row, 
                                     share_row, user_row, pass_row, mount_row):
        """Handle network share connection."""
        share_type = type_row.get_selected()  # 0 = Samba, 1 = NFS
        server = server_row.get_text().strip()
        share = share_row.get_text().strip()
        username = user_row.get_text().strip()
        password = pass_row.get_text()
        mount_point = mount_row.get_text().strip()
        
        # Validate
        if not server:
            self.window.show_toast("Enter a server address")
            return
        if not share:
            self.window.show_toast("Enter a share name")
            return
        if not mount_point:
            self.window.show_toast("Enter a mount point")
            return
        
        # Build mount command
        if share_type == 0:  # Samba
            if username and password:
                creds = f"username={username},password={password}"
            elif username:
                creds = f"username={username}"
            else:
                creds = "guest"
            
            cmd = f"sudo mkdir -p {mount_point} && sudo mount -t cifs //{server}/{share} {mount_point} -o {creds}"
        else:  # NFS
            cmd = f"sudo mkdir -p {mount_point} && sudo mount -t nfs {server}:/{share} {mount_point}"
        
        script = f'''echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Connecting to Network Share..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
{cmd}
if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Connected successfully!"
else
    echo ""
    echo "✗ Connection failed. Check your settings."
fi
echo ""
echo "Press Enter to close..."
read'''
        
        self._run_in_terminal(script)
        dialog.close()
        self.window.show_toast("Connecting to network share...")
        
        # Refresh destinations after delay
        GLib.timeout_add(3000, self._refresh_destinations)
    
    def _on_add_custom_folder(self, button):
        """Add a custom folder to backup."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Folder to Backup")
        
        # Start in home directory
        home = Gio.File.new_for_path(os.path.expanduser("~"))
        dialog.set_initial_folder(home)
        
        dialog.select_folder(self.window, None, self._on_custom_folder_selected)
    
    def _on_custom_folder_selected(self, dialog, result):
        """Handle custom folder selection."""
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                path = folder.get_path()
                
                # Check if already added
                if path in self.folder_checks:
                    self.window.show_toast("Folder already in list")
                    return
                
                # Add new row
                name = os.path.basename(path)
                row = Adw.ActionRow()
                row.set_title(name)
                row.set_subtitle(path)
                
                check = Gtk.CheckButton()
                check.set_active(True)
                check.set_valign(Gtk.Align.CENTER)
                check.connect("toggled", self._on_folder_toggled, path)
                row.add_suffix(check)
                row.set_activatable_widget(check)
                
                # Insert before "Add Custom Folder" row
                self.folders_expander.add_row(row)
                self.folder_checks[path] = check
                self.selected_folders.add(path)
                
                self.window.show_toast(f"Added: {name}")
        except Exception:
            pass
    
    def _on_start_backup(self, button):
        """Start the backup process."""
        if not self.selected_destination:
            self.window.show_toast("No destination selected")
            return
        
        if not self.selected_folders:
            self.window.show_toast("No folders selected")
            return
        
        # Check if rsync is installed
        if not check_rsync_installed():
            self._show_install_rsync_dialog()
            return
        
        # Confirm backup
        folder_count = len(self.selected_folders)
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Start Backup?",
            body=f"Back up {folder_count} folder{'s' if folder_count != 1 else ''} to {self.selected_destination.name}?"
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("backup", "Start Backup")
        dialog.set_response_appearance("backup", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("backup")
        dialog.connect("response", self._on_backup_confirmed)
        dialog.present()
    
    def _on_backup_confirmed(self, dialog, response):
        """Handle backup confirmation."""
        if response != "backup":
            return
        
        # Create backup directory with timestamp
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        hostname = os.uname().nodename
        backup_dir = os.path.join(
            self.selected_destination.path,
            "TuxBackup",
            f"{hostname}_{timestamp}"
        )
        
        # Build rsync commands for each folder
        rsync_commands = []
        for folder in self.selected_folders:
            folder_name = os.path.basename(folder)
            dest_path = os.path.join(backup_dir, folder_name)
            rsync_commands.append(f'rsync -av --progress "{folder}/" "{dest_path}/"')
        
        rsync_script = '\n'.join(rsync_commands)
        
        script = f'''echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Tux Assistant Backup"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Destination: {backup_dir}"
echo ""

# Create backup directory
mkdir -p "{backup_dir}"

# Run backups
{rsync_script}

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✓ Backup complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Press Enter to close..."
read'''
        
        self._run_in_terminal(script)
        self.window.show_toast("Backup started...")
    
    def _show_install_rsync_dialog(self):
        """Show dialog to install rsync."""
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="rsync Not Installed",
            body="rsync is required for file backup. Would you like to install it?"
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("install", "Install rsync")
        dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("install")
        dialog.connect("response", self._on_install_rsync_response)
        dialog.present()
    
    def _on_install_rsync_response(self, dialog, response):
        """Handle rsync installation response."""
        if response != "install":
            return
        
        packages = {
            DistroFamily.ARCH: "rsync",
            DistroFamily.DEBIAN: "rsync",
            DistroFamily.FEDORA: "rsync",
            DistroFamily.OPENSUSE: "rsync",
        }
        
        pkg = packages.get(self.distro.family)
        if not pkg:
            self.window.show_toast("rsync not available for this distribution")
            return
        
        if self.distro.family == DistroFamily.ARCH:
            cmd = f"sudo pacman -S --noconfirm {pkg}"
        elif self.distro.family == DistroFamily.DEBIAN:
            cmd = f"sudo apt install -y {pkg}"
        elif self.distro.family == DistroFamily.FEDORA:
            cmd = f"sudo dnf install -y {pkg}"
        elif self.distro.family == DistroFamily.OPENSUSE:
            cmd = f"sudo zypper install -y {pkg}"
        else:
            return
        
        script = f'''echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Installing rsync..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
{cmd}
echo ""
echo "✓ Installation complete!"
echo ""
echo "Press Enter to close..."
read'''
        
        self._run_in_terminal(script)
        self.window.show_toast("Installing rsync...")
    
    def _on_install_timeshift(self, button):
        """Install Timeshift."""
        packages = {
            DistroFamily.ARCH: "timeshift",
            DistroFamily.DEBIAN: "timeshift",
            DistroFamily.FEDORA: "timeshift",
            DistroFamily.OPENSUSE: "timeshift",
        }
        
        pkg = packages.get(self.distro.family)
        if not pkg:
            self.window.show_toast("Timeshift not available for this distribution")
            return
        
        if self.distro.family == DistroFamily.ARCH:
            cmd = f"sudo pacman -S --noconfirm {pkg}"
        elif self.distro.family == DistroFamily.DEBIAN:
            cmd = f"sudo apt install -y {pkg}"
        elif self.distro.family == DistroFamily.FEDORA:
            cmd = f"sudo dnf install -y {pkg}"
        elif self.distro.family == DistroFamily.OPENSUSE:
            # openSUSE needs the Archiving:Backup repo for Timeshift
            # Note: openSUSE also has snapper pre-installed for BTRFS
            cmd = '''# Adding Archiving:Backup repository for Timeshift
sudo zypper addrepo -f https://download.opensuse.org/repositories/Archiving:Backup/openSUSE_Tumbleweed/Archiving:Backup.repo 2>/dev/null || true
sudo zypper --gpg-auto-import-keys refresh
sudo zypper install -y timeshift'''
        else:
            return
        
        # Special note for openSUSE about snapper
        extra_note = ""
        if self.distro.family == DistroFamily.OPENSUSE:
            extra_note = '''
echo ""
echo "Note: openSUSE also includes 'snapper' for BTRFS snapshots."
echo "You can use YaST → Filesystem Snapshots for snapper management."'''
        
        script = f'''echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Installing Timeshift..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
{cmd}
echo ""
echo "✓ Installation complete!"{extra_note}
echo ""
echo "Press Enter to close..."
read'''
        
        self._run_in_terminal(script)
        self.window.show_toast("Installing Timeshift...")
        
        # Refresh after delay
        GLib.timeout_add(5000, self._check_timeshift_installed)
    
    def _check_timeshift_installed(self):
        """Check if Timeshift was installed and rebuild UI."""
        self.has_timeshift = check_timeshift_installed()
        if self.has_timeshift:
            # Rebuild the timeshift section
            self.content_box.remove(self.timeshift_group)
            self._build_timeshift_section()
            # Move tips to end
            tips = self.content_box.get_last_child()
            if tips:
                self.content_box.reorder_child_after(self.timeshift_group, self.backup_group)
        return False  # Don't repeat
    
    def _on_create_snapshot(self, button):
        """Create a Timeshift snapshot."""
        script = '''echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Creating System Snapshot..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
sudo timeshift --create --comments "Manual snapshot from Tux Assistant"
echo ""
echo "✓ Snapshot created!"
echo ""
echo "Press Enter to close..."
read'''
        
        self._run_in_terminal(script)
        self.window.show_toast("Creating snapshot...")
    
    def _on_open_timeshift(self, button):
        """Open Timeshift GUI."""
        try:
            subprocess.Popen(['pkexec', 'timeshift-gtk'])
        except Exception:
            # Try without pkexec
            try:
                subprocess.Popen(['timeshift-gtk'])
            except Exception:
                self.window.show_toast("Could not open Timeshift")
    
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
