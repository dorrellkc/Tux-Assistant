"""
Tux Assistant - Media Server Setup Module

Plex, Jellyfin, and Emby installation and drive configuration.
Makes external drives accessible to media server services.

"You will move it double quick time!" - Gunnery Sergeant Hartman

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

import os
import re
import subprocess
import threading
import json
import tempfile
from pathlib import Path
from gi.repository import Gtk, Adw, GLib, Gio
from typing import Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from ..core import get_distro, DistroFamily
from .registry import register_module, ModuleCategory


# =============================================================================
# Data Models
# =============================================================================

class MediaServer(Enum):
    """Supported media servers."""
    PLEX = "plex"
    JELLYFIN = "jellyfin"
    EMBY = "emby"


@dataclass
class MediaServerInfo:
    """Information about a media server."""
    id: MediaServer
    name: str
    description: str
    icon: str
    service_name: str
    user: str
    group: str
    packages: dict  # family -> packages
    repo_setup: dict  # family -> commands to add repo
    web_port: int
    

# Media server definitions
MEDIA_SERVERS = {
    MediaServer.PLEX: MediaServerInfo(
        id=MediaServer.PLEX,
        name="Plex Media Server",
        description="Popular media server with apps for all devices",
        icon="video-display-symbolic",
        service_name="plexmediaserver",
        user="plex",
        group="plex",
        web_port=32400,
        packages={
            'arch': ['plex-media-server'],  # AUR
            'debian': ['plexmediaserver'],
            'fedora': ['plexmediaserver'],
            'opensuse': ['plexmediaserver'],
        },
        repo_setup={
            'debian': [
                'curl https://downloads.plex.tv/plex-keys/PlexSign.key | gpg --dearmor | sudo tee /usr/share/keyrings/plex-archive-keyring.gpg >/dev/null',
                'echo "deb [signed-by=/usr/share/keyrings/plex-archive-keyring.gpg] https://downloads.plex.tv/repo/deb public main" | sudo tee /etc/apt/sources.list.d/plexmediaserver.list',
                'sudo apt update',
            ],
            'fedora': [
                'sudo dnf install -y https://downloads.plex.tv/plex-media-server-new/1.40.0.7998-c29d4c0c8/redhat/plexmediaserver-1.40.0.7998-c29d4c0c8.x86_64.rpm',
            ],
            'opensuse': [
                'sudo rpm --import https://downloads.plex.tv/plex-keys/PlexSign.key',
                'sudo zypper addrepo https://downloads.plex.tv/repo/rpm/x86_64/ plex',
            ],
        }
    ),
    MediaServer.JELLYFIN: MediaServerInfo(
        id=MediaServer.JELLYFIN,
        name="Jellyfin",
        description="Free and open-source media server (no account needed)",
        icon="video-display-symbolic",
        service_name="jellyfin",
        user="jellyfin",
        group="jellyfin",
        web_port=8096,
        packages={
            'arch': ['jellyfin-server', 'jellyfin-web'],
            'debian': ['jellyfin'],
            'fedora': ['jellyfin'],
            'opensuse': ['jellyfin'],
        },
        repo_setup={
            'debian': [
                'curl -fsSL https://repo.jellyfin.org/ubuntu/jellyfin_team.gpg.key | gpg --dearmor | sudo tee /usr/share/keyrings/jellyfin-archive-keyring.gpg >/dev/null',
                'echo "deb [signed-by=/usr/share/keyrings/jellyfin-archive-keyring.gpg] https://repo.jellyfin.org/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/jellyfin.list',
                'sudo apt update',
            ],
            'fedora': [
                'sudo dnf install -y https://repo.jellyfin.org/releases/server/fedora/stable/server/jellyfin-server-latest.fc$(rpm -E %fedora).x86_64.rpm',
                'sudo dnf install -y https://repo.jellyfin.org/releases/server/fedora/stable/web/jellyfin-web-latest.noarch.rpm',
            ],
        }
    ),
    MediaServer.EMBY: MediaServerInfo(
        id=MediaServer.EMBY,
        name="Emby Server",
        description="Media server with premium features available",
        icon="video-display-symbolic",
        service_name="emby-server",
        user="emby",
        group="emby",
        web_port=8096,
        packages={
            'arch': ['emby-server'],  # AUR
            'debian': ['emby-server'],
            'fedora': ['emby-server'],
            'opensuse': ['emby-server'],
        },
        repo_setup={
            'debian': [
                'wget -qO- https://emby.media/emby-server-deb.gpg | sudo gpg --dearmor -o /usr/share/keyrings/emby-server.gpg',
                'echo "deb [signed-by=/usr/share/keyrings/emby-server.gpg] https://deb.emby.media stable main" | sudo tee /etc/apt/sources.list.d/emby-server.list',
                'sudo apt update',
            ],
        }
    ),
}


@dataclass
class DriveInfo:
    """Information about a detected drive."""
    device: str  # /dev/sdb1
    label: str  # "Seagate 4TB"
    uuid: str  # UUID for fstab
    fstype: str  # ext4, ntfs, etc.
    size: str  # "4T"
    mountpoint: str  # Current mount point or empty
    model: str  # Drive model
    
    @property
    def display_name(self) -> str:
        """Get display name for UI."""
        if self.label:
            return f"{self.label} ({self.size})"
        return f"{self.model or self.device} ({self.size})"
    
    @property
    def is_mounted(self) -> bool:
        return bool(self.mountpoint)


# =============================================================================
# Drive Detection
# =============================================================================

def detect_drives() -> list[DriveInfo]:
    """Detect all available drives suitable for media storage."""
    drives = []
    
    try:
        # Use lsblk to get drive info
        result = subprocess.run(
            ['lsblk', '-o', 'NAME,LABEL,UUID,FSTYPE,SIZE,MOUNTPOINT,MODEL,TYPE', 
             '-J', '-p'],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode != 0:
            return drives
        
        data = json.loads(result.stdout)
        
        for device in data.get('blockdevices', []):
            # Process partitions
            for part in device.get('children', []):
                if part.get('type') != 'part':
                    continue
                
                # Skip if no filesystem
                fstype = part.get('fstype', '')
                if not fstype or fstype in ['swap', 'linux_raid_member']:
                    continue
                
                # Skip small partitions (< 10GB) - likely system partitions
                size_str = part.get('size', '0')
                if _parse_size_gb(size_str) < 10:
                    continue
                
                # Skip root and boot partitions
                mountpoint = part.get('mountpoint', '') or ''
                if mountpoint in ['/', '/boot', '/boot/efi', '/home']:
                    continue
                
                drives.append(DriveInfo(
                    device=part.get('name', ''),
                    label=part.get('label', '') or '',
                    uuid=part.get('uuid', '') or '',
                    fstype=fstype,
                    size=size_str,
                    mountpoint=mountpoint,
                    model=device.get('model', '') or part.get('label', '') or ''
                ))
        
        # Also check for whole drives without partition tables (some external drives)
        for device in data.get('blockdevices', []):
            if device.get('type') == 'disk' and not device.get('children'):
                fstype = device.get('fstype', '')
                if fstype and fstype not in ['swap']:
                    size_str = device.get('size', '0')
                    if _parse_size_gb(size_str) >= 10:
                        drives.append(DriveInfo(
                            device=device.get('name', ''),
                            label=device.get('label', '') or '',
                            uuid=device.get('uuid', '') or '',
                            fstype=fstype,
                            size=size_str,
                            mountpoint=device.get('mountpoint', '') or '',
                            model=device.get('model', '') or ''
                        ))
    
    except Exception as e:
        print(f"Error detecting drives: {e}")
    
    return drives


def _parse_size_gb(size_str: str) -> float:
    """Parse size string to GB."""
    try:
        size_str = size_str.upper().strip()
        if size_str.endswith('T'):
            return float(size_str[:-1]) * 1024
        elif size_str.endswith('G'):
            return float(size_str[:-1])
        elif size_str.endswith('M'):
            return float(size_str[:-1]) / 1024
        return 0
    except:
        return 0


def get_username() -> str:
    """Get current username."""
    return os.environ.get('SUDO_USER') or os.environ.get('USER') or 'user'


def detect_installed_media_server() -> Optional[MediaServer]:
    """Detect which media server is installed, if any."""
    for server_type, info in MEDIA_SERVERS.items():
        # Check if service exists
        result = subprocess.run(
            ['systemctl', 'list-unit-files', f'{info.service_name}.service'],
            capture_output=True, text=True
        )
        if info.service_name in result.stdout:
            return server_type
    return None


# =============================================================================
# Main Module Page
# =============================================================================

@register_module(
    id="media_server",
    name="Media Server",
    description="Plex, Jellyfin, Emby setup and drive configuration",
    icon="video-display-symbolic",
    category=ModuleCategory.SERVER,
    order=51
)
class MediaServerPage(Adw.NavigationPage):
    """Media server setup module main page."""
    
    def __init__(self, window):
        super().__init__(title="Media Server")
        
        self.window = window
        self.distro = get_distro()
        self.installed_server = detect_installed_media_server()
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the module UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header
        header = Adw.HeaderBar()
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
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        clamp.set_child(content_box)
        
        # Hero section
        status_page = Adw.StatusPage()
        status_page.set_icon_name("video-display-symbolic")
        status_page.set_title("Media Server Setup")
        
        if self.installed_server:
            server_name = MEDIA_SERVERS[self.installed_server].name
            status_page.set_description(f"{server_name} is installed.\nConfigure drives or manage your server.")
        else:
            status_page.set_description(
                "Set up your own media streaming server.\n"
                "Stream movies and TV to all your devices."
            )
        content_box.append(status_page)
        
        # Install section (if no server installed)
        if not self.installed_server:
            install_group = Adw.PreferencesGroup()
            install_group.set_title("Install Media Server")
            install_group.set_description("Choose a media server to install")
            content_box.append(install_group)
            
            for server_type, info in MEDIA_SERVERS.items():
                row = Adw.ActionRow()
                row.set_title(info.name)
                row.set_subtitle(info.description)
                row.set_activatable(True)
                row.add_prefix(Gtk.Image.new_from_icon_name(info.icon))
                row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
                row.connect("activated", self._on_install_server, server_type)
                install_group.add(row)
        
        # Drive configuration section
        drive_group = Adw.PreferencesGroup()
        drive_group.set_title("Configure Drives")
        drive_group.set_description("Make drives accessible to your media server")
        content_box.append(drive_group)
        
        # Configure new drive
        config_row = Adw.ActionRow()
        config_row.set_title("Configure Drive for Media Server")
        config_row.set_subtitle("Set up permissions for external/secondary drives")
        config_row.set_activatable(True)
        config_row.add_prefix(Gtk.Image.new_from_icon_name("drive-harddisk-symbolic"))
        config_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        config_row.connect("activated", self._on_configure_drive)
        drive_group.add(config_row)
        
        # Configure specific folder
        folder_row = Adw.ActionRow()
        folder_row.set_title("Configure Media Folder")
        folder_row.set_subtitle("Set permissions on a specific folder recursively")
        folder_row.set_activatable(True)
        folder_row.add_prefix(Gtk.Image.new_from_icon_name("folder-symbolic"))
        folder_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        folder_row.connect("activated", self._on_configure_folder)
        drive_group.add(folder_row)
        
        # Server management (if installed)
        if self.installed_server:
            manage_group = Adw.PreferencesGroup()
            manage_group.set_title("Manage Server")
            content_box.append(manage_group)
            
            info = MEDIA_SERVERS[self.installed_server]
            
            # Service status
            status_row = Adw.ActionRow()
            status_row.set_title("Service Status")
            
            # Check if running
            is_running = self._is_service_running(info.service_name)
            if is_running:
                status_label = Gtk.Label(label="Running")
                status_label.add_css_class("success")
            else:
                status_label = Gtk.Label(label="Stopped")
                status_label.add_css_class("error")
            status_row.add_suffix(status_label)
            
            manage_group.add(status_row)
            
            # Start/Stop button
            action_row = Adw.ActionRow()
            if is_running:
                action_row.set_title("Stop Server")
                action_row.set_subtitle(f"Stop {info.name}")
            else:
                action_row.set_title("Start Server")
                action_row.set_subtitle(f"Start {info.name}")
            action_row.set_activatable(True)
            action_row.connect("activated", self._on_toggle_service)
            manage_group.add(action_row)
            
            # Open web interface
            web_row = Adw.ActionRow()
            web_row.set_title("Open Web Interface")
            web_row.set_subtitle(f"http://localhost:{info.web_port}")
            web_row.set_activatable(True)
            web_row.add_suffix(Gtk.Image.new_from_icon_name("web-browser-symbolic"))
            web_row.connect("activated", self._on_open_web)
            manage_group.add(web_row)
    
    def _is_service_running(self, service_name: str) -> bool:
        """Check if a service is running."""
        try:
            result = subprocess.run(
                ['systemctl', 'is-active', service_name],
                capture_output=True, text=True
            )
            return result.stdout.strip() == 'active'
        except:
            return False
    
    def _on_install_server(self, row, server_type: MediaServer):
        """Start server installation."""
        dialog = InstallServerDialog(self.window, self.distro, server_type)
        dialog.present(self.window)
    
    def _on_configure_drive(self, row):
        """Open drive configuration dialog."""
        dialog = ConfigureDriveDialog(self.window, self.distro, self.installed_server)
        dialog.present(self.window)
    
    def _on_configure_folder(self, row):
        """Open folder configuration dialog."""
        dialog = ConfigureFolderDialog(self.window, self.distro, self.installed_server)
        dialog.present(self.window)
    
    def _on_toggle_service(self, row):
        """Start or stop the media server service."""
        if not self.installed_server:
            return
        
        info = MEDIA_SERVERS[self.installed_server]
        is_running = self._is_service_running(info.service_name)
        
        action = "stop" if is_running else "start"
        
        # Run via pkexec
        try:
            subprocess.run(
                ['pkexec', 'systemctl', action, info.service_name],
                check=True
            )
            self.window.show_toast(f"Server {action}ed successfully")
            # Refresh the page
            self._build_ui()
        except:
            self.window.show_toast(f"Failed to {action} server")
    
    def _on_open_web(self, row):
        """Open the web interface."""
        if not self.installed_server:
            return
        
        info = MEDIA_SERVERS[self.installed_server]
        url = f"http://localhost:{info.web_port}"
        
        Gtk.show_uri(self.window, url, 0)


# =============================================================================
# Install Server Dialog
# =============================================================================

class InstallServerDialog(Adw.Dialog):
    """Dialog for installing a media server."""
    
    def __init__(self, window, distro, server_type: MediaServer):
        super().__init__()
        
        self.window = window
        self.distro = distro
        self.server_type = server_type
        self.info = MEDIA_SERVERS[server_type]
        
        self.set_title(f"Install {self.info.name}")
        self.set_content_width(500)
        self.set_content_height(400)
        
        self._build_ui()
    
    def _build_ui(self):
        """Build dialog UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        toolbar_view.add_top_bar(header)
        
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_btn)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)
        toolbar_view.set_content(content)
        
        # Info
        status = Adw.StatusPage()
        status.set_icon_name(self.info.icon)
        status.set_title(f"Install {self.info.name}")
        status.set_description(self.info.description)
        content.append(status)
        
        # What will be done
        info_group = Adw.PreferencesGroup()
        info_group.set_title("Installation Steps")
        content.append(info_group)
        
        steps = [
            ("Add repository", "Configure official package source"),
            ("Install packages", "Download and install server"),
            ("Enable service", "Start on boot automatically"),
            ("Start server", "Begin running immediately"),
        ]
        
        for title, subtitle in steps:
            row = Adw.ActionRow()
            row.set_title(title)
            row.set_subtitle(subtitle)
            row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
            info_group.add(row)
        
        # Install button
        install_btn = Gtk.Button(label="Install")
        install_btn.add_css_class("suggested-action")
        install_btn.add_css_class("pill")
        install_btn.set_halign(Gtk.Align.CENTER)
        install_btn.connect("clicked", self._on_install)
        content.append(install_btn)
    
    def _on_install(self, button):
        """Start installation."""
        self.close()
        
        # Create installation plan
        plan = self._create_plan()
        
        # Show progress dialog
        progress = InstallProgressDialog(self.window, plan, self.info)
        progress.present(self.window)
    
    def _create_plan(self) -> dict:
        """Create installation plan."""
        family = self.distro.family.value
        
        return {
            'type': 'media_server_install',
            'server': self.server_type.value,
            'family': family,
            'packages': self.info.packages.get(family, []),
            'repo_setup': self.info.repo_setup.get(family, []),
            'service_name': self.info.service_name,
        }


class InstallProgressDialog(Adw.Dialog):
    """Dialog showing installation progress."""
    
    def __init__(self, window, plan: dict, info: MediaServerInfo):
        super().__init__()
        
        self.window = window
        self.plan = plan
        self.info = info
        
        self.set_title(f"Installing {info.name}")
        self.set_content_width(500)
        self.set_content_height(350)
        self.set_can_close(False)
        
        self._build_ui()
        GLib.timeout_add(100, self._start_install)
    
    def _build_ui(self):
        """Build UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        toolbar_view.add_top_bar(header)
        
        self.close_btn = Gtk.Button(label="Close")
        self.close_btn.connect("clicked", lambda b: self.close())
        self.close_btn.set_visible(False)
        header.pack_end(self.close_btn)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)
        toolbar_view.set_content(content)
        
        self.status_label = Gtk.Label(label="Preparing installation...")
        self.status_label.add_css_class("title-3")
        content.append(self.status_label)
        
        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(True)
        content.append(self.progress)
        
        # Output view
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        content.append(scrolled)
        
        self.output_view = Gtk.TextView()
        self.output_view.set_editable(False)
        self.output_view.set_monospace(True)
        self.output_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        scrolled.set_child(self.output_view)
        
        self.output_buffer = self.output_view.get_buffer()
    
    def _append_output(self, text: str):
        """Append to output."""
        end = self.output_buffer.get_end_iter()
        self.output_buffer.insert(end, text + "\n")
    
    def _start_install(self):
        """Start installation in background."""
        thread = threading.Thread(target=self._run_install, daemon=True)
        thread.start()
        return False
    
    def _run_install(self):
        """Run the installation."""
        try:
            family = self.plan['family']
            
            # Step 1: Add repository
            GLib.idle_add(self.status_label.set_text, "Adding repository...")
            GLib.idle_add(self.progress.set_fraction, 0.1)
            
            for cmd in self.plan.get('repo_setup', []):
                GLib.idle_add(self._append_output, f"$ {cmd}")
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                if result.stdout:
                    GLib.idle_add(self._append_output, result.stdout)
                if result.returncode != 0 and result.stderr:
                    GLib.idle_add(self._append_output, f"Warning: {result.stderr}")
            
            # Step 2: Install packages
            GLib.idle_add(self.status_label.set_text, "Installing packages...")
            GLib.idle_add(self.progress.set_fraction, 0.3)
            
            packages = self.plan.get('packages', [])
            if packages:
                if family == 'arch':
                    cmd = ['sudo', 'pacman', '-S', '--noconfirm'] + packages
                elif family == 'debian':
                    cmd = ['sudo', 'apt', 'install', '-y'] + packages
                elif family == 'fedora':
                    cmd = ['sudo', 'dnf', 'install', '-y'] + packages
                elif family == 'opensuse':
                    cmd = ['sudo', 'zypper', 'install', '-y'] + packages
                else:
                    cmd = None
                
                if cmd:
                    GLib.idle_add(self._append_output, f"$ {' '.join(cmd)}")
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.stdout:
                        GLib.idle_add(self._append_output, result.stdout[-1000:])  # Last 1000 chars
            
            # Step 3: Enable service
            GLib.idle_add(self.status_label.set_text, "Enabling service...")
            GLib.idle_add(self.progress.set_fraction, 0.7)
            
            service = self.plan['service_name']
            subprocess.run(['sudo', 'systemctl', 'enable', service], capture_output=True)
            GLib.idle_add(self._append_output, f"Enabled {service}")
            
            # Step 4: Start service
            GLib.idle_add(self.status_label.set_text, "Starting service...")
            GLib.idle_add(self.progress.set_fraction, 0.9)
            
            subprocess.run(['sudo', 'systemctl', 'start', service], capture_output=True)
            GLib.idle_add(self._append_output, f"Started {service}")
            
            # Done
            GLib.idle_add(self.progress.set_fraction, 1.0)
            GLib.idle_add(self.status_label.set_text, "Installation complete!")
            GLib.idle_add(self._append_output, f"\n✓ {self.info.name} installed successfully!")
            GLib.idle_add(self._append_output, f"Access at: http://localhost:{self.info.web_port}")
            
        except Exception as e:
            GLib.idle_add(self.status_label.set_text, "Installation failed")
            GLib.idle_add(self._append_output, f"Error: {str(e)}")
        
        GLib.idle_add(self._finish)
    
    def _finish(self):
        """Show close button."""
        self.close_btn.set_visible(True)
        self.set_can_close(True)


# =============================================================================
# Configure Drive Dialog
# =============================================================================

class ConfigureDriveDialog(Adw.Dialog):
    """Dialog for configuring drives for media server access."""
    
    def __init__(self, window, distro, installed_server: Optional[MediaServer]):
        super().__init__()
        
        self.window = window
        self.distro = distro
        self.installed_server = installed_server
        self.drives = detect_drives()
        self.selected_drives: set[str] = set()
        self.selected_server = installed_server or MediaServer.PLEX
        
        self.set_title("Configure Drives")
        self.set_content_width(550)
        self.set_content_height(500)
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the dialog UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        toolbar_view.add_top_bar(header)
        
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_btn)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        toolbar_view.set_content(scrolled)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)
        scrolled.set_child(content)
        
        # Server selection (if none installed)
        if not self.installed_server:
            server_group = Adw.PreferencesGroup()
            server_group.set_title("Media Server")
            server_group.set_description("Which media server will access these drives?")
            content.append(server_group)
            
            self.server_combo = Adw.ComboRow()
            self.server_combo.set_title("Server")
            
            model = Gtk.StringList()
            for server in MediaServer:
                model.append(MEDIA_SERVERS[server].name)
            self.server_combo.set_model(model)
            self.server_combo.set_selected(0)
            self.server_combo.connect("notify::selected", self._on_server_changed)
            server_group.add(self.server_combo)
        
        # Drive selection
        drive_group = Adw.PreferencesGroup()
        drive_group.set_title("Select Drives")
        drive_group.set_description("Choose drives to make accessible")
        content.append(drive_group)
        
        if not self.drives:
            no_drives_row = Adw.ActionRow()
            no_drives_row.set_title("No external drives detected")
            no_drives_row.set_subtitle("Connect a drive and refresh")
            drive_group.add(no_drives_row)
        else:
            for drive in self.drives:
                row = Adw.ActionRow()
                row.set_title(drive.display_name)
                
                subtitle = f"{drive.device} • {drive.fstype}"
                if drive.mountpoint:
                    subtitle += f" • Mounted at {drive.mountpoint}"
                row.set_subtitle(subtitle)
                
                check = Gtk.CheckButton()
                check.connect("toggled", self._on_drive_toggled, drive.device)
                row.add_prefix(check)
                row.set_activatable_widget(check)
                
                drive_group.add(row)
        
        # What will be done
        info_group = Adw.PreferencesGroup()
        info_group.set_title("What This Does")
        content.append(info_group)
        
        steps = [
            "Add drive to /etc/fstab for automatic mounting",
            "Create mount point in /media/$USER/",
            "Set read permissions for media server user",
            "Configure ACL for media server group",
        ]
        
        for step in steps:
            row = Adw.ActionRow()
            row.set_title(step)
            row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
            info_group.add(row)
        
        # Configure button
        self.config_btn = Gtk.Button(label="Configure Selected Drives")
        self.config_btn.add_css_class("suggested-action")
        self.config_btn.add_css_class("pill")
        self.config_btn.set_halign(Gtk.Align.CENTER)
        self.config_btn.set_sensitive(False)
        self.config_btn.connect("clicked", self._on_configure)
        content.append(self.config_btn)
    
    def _on_server_changed(self, combo, pspec):
        """Handle server selection change."""
        idx = combo.get_selected()
        self.selected_server = list(MediaServer)[idx]
    
    def _on_drive_toggled(self, check, device):
        """Handle drive selection toggle."""
        if check.get_active():
            self.selected_drives.add(device)
        else:
            self.selected_drives.discard(device)
        
        self.config_btn.set_sensitive(len(self.selected_drives) > 0)
    
    def _on_configure(self, button):
        """Configure selected drives."""
        if not self.selected_drives:
            return
        
        self.close()
        
        # Get selected drive info
        drives = [d for d in self.drives if d.device in self.selected_drives]
        server_info = MEDIA_SERVERS[self.selected_server]
        
        # Show configuration progress
        dialog = DriveConfigProgressDialog(
            self.window, drives, server_info, get_username()
        )
        dialog.present(self.window)


class DriveConfigProgressDialog(Adw.Dialog):
    """Dialog showing drive configuration progress."""
    
    def __init__(self, window, drives: list[DriveInfo], server_info: MediaServerInfo, username: str):
        super().__init__()
        
        self.window = window
        self.drives = drives
        self.server_info = server_info
        self.username = username
        
        self.set_title("Configuring Drives")
        self.set_content_width(500)
        self.set_content_height(400)
        self.set_can_close(False)
        
        self._build_ui()
        GLib.timeout_add(100, self._start_config)
    
    def _build_ui(self):
        """Build UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        toolbar_view.add_top_bar(header)
        
        self.close_btn = Gtk.Button(label="Close")
        self.close_btn.connect("clicked", lambda b: self.close())
        self.close_btn.set_visible(False)
        header.pack_end(self.close_btn)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)
        toolbar_view.set_content(content)
        
        self.status_label = Gtk.Label(label="Preparing...")
        self.status_label.add_css_class("title-3")
        content.append(self.status_label)
        
        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(True)
        content.append(self.progress)
        
        # Output
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        content.append(scrolled)
        
        self.output_view = Gtk.TextView()
        self.output_view.set_editable(False)
        self.output_view.set_monospace(True)
        self.output_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        scrolled.set_child(self.output_view)
        
        self.output_buffer = self.output_view.get_buffer()
    
    def _append(self, text: str):
        """Append to output."""
        end = self.output_buffer.get_end_iter()
        self.output_buffer.insert(end, text + "\n")
    
    def _start_config(self):
        """Start configuration."""
        thread = threading.Thread(target=self._run_config, daemon=True)
        thread.start()
        return False
    
    def _run_config(self):
        """Run drive configuration."""
        try:
            total_steps = len(self.drives) * 4
            current_step = 0
            
            media_base = f"/media/{self.username}"
            server_group = self.server_info.group
            
            # Ensure base media directory exists with correct permissions
            GLib.idle_add(self.status_label.set_text, "Setting up media directory...")
            GLib.idle_add(self._append, f"Creating {media_base}")
            
            subprocess.run(['sudo', 'mkdir', '-p', media_base], capture_output=True)
            subprocess.run(['sudo', 'chmod', 'go+rx', media_base], capture_output=True)
            
            # Try to set ACL on base directory
            subprocess.run(['sudo', 'setfacl', '-m', f'g:{server_group}:rx', media_base], 
                          capture_output=True)
            
            for drive in self.drives:
                drive_label = drive.label or drive.device.split('/')[-1]
                mount_point = f"{media_base}/{drive_label}"
                
                # Step 1: Create mount point
                current_step += 1
                GLib.idle_add(self.progress.set_fraction, current_step / total_steps)
                GLib.idle_add(self.status_label.set_text, f"Creating mount point for {drive_label}...")
                GLib.idle_add(self._append, f"\n=== Configuring {drive.display_name} ===")
                GLib.idle_add(self._append, f"Mount point: {mount_point}")
                
                subprocess.run(['sudo', 'mkdir', '-p', mount_point], capture_output=True)
                
                # Step 2: Add to fstab (if not already there)
                current_step += 1
                GLib.idle_add(self.progress.set_fraction, current_step / total_steps)
                GLib.idle_add(self.status_label.set_text, f"Updating fstab...")
                
                if drive.uuid:
                    fstab_line = f"UUID={drive.uuid}  {mount_point}  {drive.fstype}  nosuid,nodev,nofail  0  2"
                    
                    # Check if already in fstab
                    with open('/etc/fstab', 'r') as f:
                        fstab_content = f.read()
                    
                    if drive.uuid not in fstab_content:
                        GLib.idle_add(self._append, f"Adding to /etc/fstab:")
                        GLib.idle_add(self._append, f"  {fstab_line}")
                        
                        subprocess.run(
                            ['sudo', 'bash', '-c', f'echo "{fstab_line}" >> /etc/fstab'],
                            capture_output=True
                        )
                    else:
                        GLib.idle_add(self._append, "Already in fstab, skipping")
                
                # Step 3: Mount the drive
                current_step += 1
                GLib.idle_add(self.progress.set_fraction, current_step / total_steps)
                GLib.idle_add(self.status_label.set_text, f"Mounting {drive_label}...")
                
                if not drive.is_mounted:
                    result = subprocess.run(['sudo', 'mount', mount_point], capture_output=True, text=True)
                    if result.returncode == 0:
                        GLib.idle_add(self._append, f"Mounted at {mount_point}")
                    else:
                        # Try mounting by device
                        subprocess.run(['sudo', 'mount', drive.device, mount_point], capture_output=True)
                        GLib.idle_add(self._append, f"Mounted {drive.device} at {mount_point}")
                else:
                    GLib.idle_add(self._append, f"Already mounted at {drive.mountpoint}")
                    mount_point = drive.mountpoint  # Use existing mount point
                
                # Step 4: Set permissions
                current_step += 1
                GLib.idle_add(self.progress.set_fraction, current_step / total_steps)
                GLib.idle_add(self.status_label.set_text, f"Setting permissions...")
                
                # Basic permissions
                subprocess.run(['sudo', 'chmod', 'go+rx', mount_point], capture_output=True)
                GLib.idle_add(self._append, f"chmod go+rx {mount_point}")
                
                # ACL for media server
                result = subprocess.run(
                    ['sudo', 'setfacl', '-m', f'g:{server_group}:rx', mount_point],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    GLib.idle_add(self._append, f"setfacl -m g:{server_group}:rx {mount_point}")
                else:
                    GLib.idle_add(self._append, f"Note: ACL not supported or {server_group} group doesn't exist yet")
                
                GLib.idle_add(self._append, f"✓ {drive_label} configured")
            
            # Done
            GLib.idle_add(self.progress.set_fraction, 1.0)
            GLib.idle_add(self.status_label.set_text, "Configuration complete!")
            GLib.idle_add(self._append, f"\n✓ All drives configured for {self.server_info.name}")
            GLib.idle_add(self._append, f"\nYou can now add these locations in your media server's library settings.")
            
        except Exception as e:
            GLib.idle_add(self.status_label.set_text, "Configuration failed")
            GLib.idle_add(self._append, f"Error: {str(e)}")
        
        GLib.idle_add(self._finish)
    
    def _finish(self):
        """Show close button."""
        self.close_btn.set_visible(True)
        self.set_can_close(True)


# =============================================================================
# Configure Folder Dialog
# =============================================================================

class ConfigureFolderDialog(Adw.Dialog):
    """Dialog for configuring a specific folder for media server access."""
    
    def __init__(self, window, distro, installed_server: Optional[MediaServer]):
        super().__init__()
        
        self.window = window
        self.distro = distro
        self.installed_server = installed_server
        self.selected_server = installed_server or MediaServer.PLEX
        self.selected_folder: Optional[str] = None
        
        self.set_title("Configure Media Folder")
        self.set_content_width(500)
        self.set_content_height(400)
        
        self._build_ui()
    
    def _build_ui(self):
        """Build UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        toolbar_view.add_top_bar(header)
        
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_btn)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)
        toolbar_view.set_content(content)
        
        # Description
        desc = Gtk.Label(
            label="Select a folder containing your media files.\n"
                  "Permissions will be set recursively so your media server can access all files."
        )
        desc.set_wrap(True)
        desc.add_css_class("dim-label")
        content.append(desc)
        
        # Server selection
        if not self.installed_server:
            server_group = Adw.PreferencesGroup()
            server_group.set_title("Media Server")
            content.append(server_group)
            
            self.server_combo = Adw.ComboRow()
            self.server_combo.set_title("Server")
            
            model = Gtk.StringList()
            for server in MediaServer:
                model.append(MEDIA_SERVERS[server].name)
            self.server_combo.set_model(model)
            self.server_combo.connect("notify::selected", self._on_server_changed)
            server_group.add(self.server_combo)
        
        # Folder selection
        folder_group = Adw.PreferencesGroup()
        folder_group.set_title("Media Folder")
        content.append(folder_group)
        
        folder_row = Adw.ActionRow()
        folder_row.set_title("Select Folder")
        folder_row.set_subtitle("No folder selected")
        folder_row.set_activatable(True)
        folder_row.add_suffix(Gtk.Image.new_from_icon_name("folder-open-symbolic"))
        folder_row.connect("activated", self._on_select_folder)
        self.folder_row = folder_row
        folder_group.add(folder_row)
        
        # Warning
        warning_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        warning_box.set_margin_top(12)
        warning_icon = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
        warning_icon.add_css_class("warning")
        warning_box.append(warning_icon)
        
        warning_label = Gtk.Label(
            label="This will run chmod recursively on all files in the folder."
        )
        warning_label.add_css_class("dim-label")
        warning_box.append(warning_label)
        content.append(warning_box)
        
        # Configure button
        self.config_btn = Gtk.Button(label="Set Permissions")
        self.config_btn.add_css_class("suggested-action")
        self.config_btn.add_css_class("pill")
        self.config_btn.set_halign(Gtk.Align.CENTER)
        self.config_btn.set_sensitive(False)
        self.config_btn.connect("clicked", self._on_configure)
        content.append(self.config_btn)
    
    def _on_server_changed(self, combo, pspec):
        """Handle server change."""
        idx = combo.get_selected()
        self.selected_server = list(MediaServer)[idx]
    
    def _on_select_folder(self, row):
        """Open folder chooser."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Media Folder")
        dialog.select_folder(self.window, None, self._on_folder_selected)
    
    def _on_folder_selected(self, dialog, result):
        """Handle folder selection."""
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                self.selected_folder = folder.get_path()
                self.folder_row.set_subtitle(self.selected_folder)
                self.config_btn.set_sensitive(True)
        except GLib.Error:
            pass
    
    def _on_configure(self, button):
        """Configure the folder."""
        if not self.selected_folder:
            return
        
        server_info = MEDIA_SERVERS[self.selected_server]
        
        # Show confirmation
        confirm = Adw.MessageDialog(
            transient_for=self.window,
            heading="Confirm Permissions Change",
            body=f"This will recursively set read permissions on:\n{self.selected_folder}\n\nFor: {server_info.name}"
        )
        confirm.add_response("cancel", "Cancel")
        confirm.add_response("apply", "Apply Permissions")
        confirm.set_response_appearance("apply", Adw.ResponseAppearance.SUGGESTED)
        confirm.connect("response", self._on_confirm_response, server_info)
        confirm.present()
    
    def _on_confirm_response(self, dialog, response, server_info):
        """Handle confirmation response."""
        if response != "apply":
            return
        
        self.close()
        
        # Run the permission changes
        folder = self.selected_folder
        group = server_info.group
        
        def run_permissions():
            try:
                # chmod -R +rwX (capital X = execute only on directories)
                subprocess.run(
                    ['sudo', 'chmod', '-R', '+rwX', folder],
                    capture_output=True, timeout=300
                )
                
                # Try to set ACL recursively
                subprocess.run(
                    ['sudo', 'setfacl', '-R', '-m', f'g:{group}:rx', folder],
                    capture_output=True, timeout=300
                )
                
                GLib.idle_add(self.window.show_toast, f"Permissions set on {folder}")
            except Exception as e:
                GLib.idle_add(self.window.show_toast, f"Error: {str(e)}")
        
        # Run in background
        thread = threading.Thread(target=run_permissions, daemon=True)
        thread.start()
        
        self.window.show_toast("Setting permissions... this may take a moment.")
