"""
Tux Assistant - Gaming Module

Simple gaming setup: install Steam, Lutris, and gaming utilities.
Keeps it simple - installs the tools, lets them do their job.

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

import os
import subprocess
import threading
from gi.repository import Gtk, Adw, GLib
from typing import Optional, Tuple
from dataclasses import dataclass

from ..core import get_distro, DistroFamily

from .registry import register_module, ModuleCategory


# =============================================================================
# Gaming App Definitions
# =============================================================================

@dataclass
class GamingApp:
    """A gaming-related application."""
    id: str
    name: str
    description: str
    icon: str
    check_command: str  # Command to check if installed
    packages: dict  # DistroFamily -> package name(s)
    flatpak: Optional[str] = None  # Flatpak app ID as fallback
    website: Optional[str] = None


GAMING_APPS = [
    GamingApp(
        id="steam",
        name="Steam",
        description="The largest PC gaming platform. Includes Proton for Windows games.",
        icon="applications-games-symbolic",
        check_command="steam",
        packages={
            DistroFamily.ARCH: "steam",
            DistroFamily.DEBIAN: "steam",
            DistroFamily.FEDORA: "steam",
            DistroFamily.OPENSUSE: "steam",
        },
        flatpak="com.valvesoftware.Steam",
        website="https://store.steampowered.com/about/",
    ),
    GamingApp(
        id="lutris",
        name="Lutris",
        description="Game manager for GOG, Epic, Origin, and more. Great for non-Steam games.",
        icon="applications-games-symbolic",
        check_command="lutris",
        packages={
            DistroFamily.ARCH: "lutris",
            DistroFamily.DEBIAN: "lutris",
            DistroFamily.FEDORA: "lutris",
            DistroFamily.OPENSUSE: "lutris",
        },
        flatpak="net.lutris.Lutris",
        website="https://lutris.net/",
    ),
    GamingApp(
        id="heroic",
        name="Heroic Games Launcher",
        description="Open source launcher for Epic Games Store and GOG.",
        icon="applications-games-symbolic",
        check_command="heroic",
        packages={
            DistroFamily.ARCH: "heroic-games-launcher-bin",  # AUR
        },
        flatpak="com.heroicgameslauncher.hgl",
        website="https://heroicgameslauncher.com/",
    ),
    GamingApp(
        id="bottles",
        name="Bottles",
        description="Run Windows software and games easily. User-friendly Wine manager.",
        icon="applications-games-symbolic",
        check_command="bottles",
        packages={
            DistroFamily.ARCH: "bottles",
        },
        flatpak="com.usebottles.bottles",
        website="https://usebottles.com/",
    ),
]

GAMING_UTILITIES = [
    GamingApp(
        id="gamemode",
        name="GameMode",
        description="Optimizes your system for gaming. Used automatically by Steam and Lutris.",
        icon="utilities-system-monitor-symbolic",
        check_command="gamemoded",
        packages={
            DistroFamily.ARCH: "gamemode lib32-gamemode",
            DistroFamily.DEBIAN: "gamemode",
            DistroFamily.FEDORA: "gamemode",
            DistroFamily.OPENSUSE: "gamemode",
        },
    ),
    GamingApp(
        id="mangohud",
        name="MangoHud",
        description="Shows FPS, CPU/GPU stats overlay in games. Like MSI Afterburner.",
        icon="utilities-system-monitor-symbolic",
        check_command="mangohud",
        packages={
            DistroFamily.ARCH: "mangohud lib32-mangohud",
            DistroFamily.DEBIAN: "mangohud",
            DistroFamily.FEDORA: "mangohud",
            DistroFamily.OPENSUSE: "mangohud",
        },
        flatpak="org.freedesktop.Platform.VulkanLayer.MangoHud",
    ),
    GamingApp(
        id="protonup",
        name="ProtonUp-Qt",
        description="Easily install and manage Proton-GE and Wine-GE versions.",
        icon="system-software-update-symbolic",
        check_command="protonup-qt",
        packages={
            DistroFamily.ARCH: "protonup-qt",
        },
        flatpak="net.davidotek.pupgui2",
        website="https://davidotek.github.io/protonup-qt/",
    ),
]

CONTROLLER_PACKAGES = {
    "xbox": GamingApp(
        id="xbox",
        name="Xbox Controller Support",
        description="Support for Xbox One/Series controllers (usually built-in to kernel).",
        icon="input-gaming-symbolic",
        check_command="xboxdrv",
        packages={
            DistroFamily.ARCH: "xboxdrv",
            DistroFamily.DEBIAN: "xboxdrv",
            DistroFamily.FEDORA: "xboxdrv",
            DistroFamily.OPENSUSE: "xboxdrv",  # Requires hardware repo
        },
    ),
    "ps": GamingApp(
        id="ps",
        name="PlayStation Controller Support",
        description="Support for DualShock 4 controllers. DualSense (PS5) works out of the box.",
        icon="input-gaming-symbolic",
        check_command="ds4drv",
        packages={
            DistroFamily.ARCH: "ds4drv",  # AUR
            DistroFamily.DEBIAN: "ds4drv",
            # Fedora/openSUSE: Use pip install ds4drv or kernel support
        },
        flatpak=None,  # No flatpak available
        website="https://github.com/chrippa/ds4drv",
    ),
}


# =============================================================================
# Utility Functions
# =============================================================================

def check_app_installed(app: GamingApp) -> bool:
    """Check if an app is installed."""
    try:
        result = subprocess.run(
            ['which', app.check_command],
            capture_output=True
        )
        if result.returncode == 0:
            return True
        
        # Also check flatpak
        if app.flatpak:
            result = subprocess.run(
                ['flatpak', 'list', '--app', '--columns=application'],
                capture_output=True, text=True
            )
            if app.flatpak in result.stdout:
                return True
        
        return False
    except Exception:
        return False


def check_flatpak_available() -> bool:
    """Check if flatpak is installed."""
    try:
        result = subprocess.run(['which', 'flatpak'], capture_output=True)
        return result.returncode == 0
    except Exception:
        return False


def check_32bit_support(family: DistroFamily) -> Tuple[bool, str]:
    """Check if 32-bit library support is enabled (required for most games)."""
    try:
        if family == DistroFamily.ARCH:
            # Check if multilib is enabled
            with open('/etc/pacman.conf', 'r') as f:
                content = f.read()
                if '[multilib]' in content:
                    # Check it's not commented out
                    lines = content.split('\n')
                    for i, line in enumerate(lines):
                        if line.strip() == '[multilib]':
                            return True, "Multilib enabled"
            return False, "Enable [multilib] in /etc/pacman.conf"
        
        elif family == DistroFamily.DEBIAN:
            result = subprocess.run(
                ['dpkg', '--print-foreign-architectures'],
                capture_output=True, text=True
            )
            if 'i386' in result.stdout:
                return True, "i386 architecture enabled"
            return False, "Run: sudo dpkg --add-architecture i386"
        
        elif family == DistroFamily.FEDORA:
            # Fedora handles this automatically
            return True, "32-bit support available"
        
        elif family == DistroFamily.OPENSUSE:
            return True, "32-bit support available"
        
    except Exception as e:
        return False, str(e)
    
    return True, "Unknown"


# =============================================================================
# Gaming Page
# =============================================================================

@register_module(
    id="gaming",
    name="Gaming",
    description="Steam, Lutris, and gaming utilities",
    icon="applications-games-symbolic",
    category=ModuleCategory.SYSTEM,
    order=10
)
class GamingPage(Adw.NavigationPage):
    """Gaming setup module page."""
    
    def __init__(self, window):
        super().__init__(title="Gaming")
        
        self.window = window
        self.distro = get_distro()
        self.has_flatpak = check_flatpak_available()
        
        self._build_ui()
        self._refresh_status()
    
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
        refresh_btn.connect("clicked", lambda b: self._refresh_status())
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
        self._build_status_section()
        self._build_platforms_section()
        self._build_utilities_section()
        self._build_controllers_section()
        self._build_tips_section()
    
    def _build_status_section(self):
        """Build the gaming readiness status section."""
        self.status_group = Adw.PreferencesGroup()
        self.status_group.set_title("Gaming Readiness")
        self.status_group.set_description("Your system's gaming compatibility")
        self.content_box.append(self.status_group)
        
        # 32-bit support row
        self.lib32_row = Adw.ActionRow()
        self.lib32_row.set_title("32-bit Support")
        self.lib32_row.set_subtitle("Checking...")
        self.lib32_row.add_prefix(Gtk.Image.new_from_icon_name("application-x-executable-symbolic"))
        self.status_group.add(self.lib32_row)
        
        # Vulkan row
        self.vulkan_row = Adw.ActionRow()
        self.vulkan_row.set_title("Vulkan Support")
        self.vulkan_row.set_subtitle("Checking...")
        self.vulkan_row.add_prefix(Gtk.Image.new_from_icon_name("video-display-symbolic"))
        self.status_group.add(self.vulkan_row)
    
    def _build_platforms_section(self):
        """Build the gaming platforms section."""
        self.platforms_group = Adw.PreferencesGroup()
        self.platforms_group.set_title("Gaming Platforms")
        self.platforms_group.set_description("Install game launchers and stores")
        self.content_box.append(self.platforms_group)
        
        self.platform_rows = {}
        
        for app in GAMING_APPS:
            row = self._create_app_row(app)
            self.platforms_group.add(row)
            self.platform_rows[app.id] = row
    
    def _build_utilities_section(self):
        """Build the gaming utilities section."""
        self.utils_group = Adw.PreferencesGroup()
        self.utils_group.set_title("Gaming Utilities")
        self.utils_group.set_description("Performance tools and helpers")
        self.content_box.append(self.utils_group)
        
        self.utility_rows = {}
        
        for app in GAMING_UTILITIES:
            row = self._create_app_row(app)
            self.utils_group.add(row)
            self.utility_rows[app.id] = row
    
    def _build_controllers_section(self):
        """Build the controller support section."""
        self.controller_group = Adw.PreferencesGroup()
        self.controller_group.set_title("Controller Support")
        self.controller_group.set_description("Most controllers work out of the box via USB or Bluetooth")
        self.content_box.append(self.controller_group)
        
        # Info row
        info_row = Adw.ActionRow()
        info_row.set_title("Controllers")
        info_row.set_subtitle("Xbox and PlayStation controllers usually work automatically. Just plug in or pair via Bluetooth.")
        info_row.add_prefix(Gtk.Image.new_from_icon_name("input-gaming-symbolic"))
        self.controller_group.add(info_row)
    
    def _build_tips_section(self):
        """Build the tips section."""
        tips_group = Adw.PreferencesGroup()
        tips_group.set_title("Quick Tips")
        self.content_box.append(tips_group)
        
        tips = [
            ("Steam + Proton", "Enable Steam Play in Steam settings to run Windows games. It just works for most games."),
            ("Check ProtonDB", "Visit protondb.com to see how well specific games run on Linux."),
            ("Lutris", "Use Lutris for non-Steam games. It has install scripts for many games."),
            ("Performance", "Install GameMode - Steam and Lutris use it automatically for better performance."),
        ]
        
        for title, subtitle in tips:
            row = Adw.ActionRow()
            row.set_title(title)
            row.set_subtitle(subtitle)
            row.add_prefix(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
            tips_group.add(row)
        
        # ProtonDB link
        protondb_row = Adw.ActionRow()
        protondb_row.set_title("ProtonDB")
        protondb_row.set_subtitle("Check game compatibility at protondb.com")
        protondb_row.add_prefix(Gtk.Image.new_from_icon_name("web-browser-symbolic"))
        protondb_row.set_activatable(True)
        protondb_row.connect("activated", self._on_open_protondb)
        protondb_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        tips_group.add(protondb_row)
    
    def _create_app_row(self, app: GamingApp) -> Adw.ActionRow:
        """Create a row for a gaming app."""
        row = Adw.ActionRow()
        row.set_title(app.name)
        row.set_subtitle(app.description)
        row.add_prefix(Gtk.Image.new_from_icon_name(app.icon))
        
        # Status label
        status_label = Gtk.Label(label="Checking...")
        status_label.add_css_class("dim-label")
        row.add_suffix(status_label)
        
        # Store reference for updates
        row.status_label = status_label
        row.app = app
        
        # Install button (hidden initially)
        install_btn = Gtk.Button(label="Install")
        install_btn.set_valign(Gtk.Align.CENTER)
        install_btn.connect("clicked", self._on_install_app, app, row)
        install_btn.set_visible(False)
        row.add_suffix(install_btn)
        row.install_btn = install_btn
        
        # Launch button (hidden initially)
        launch_btn = Gtk.Button()
        launch_btn.set_icon_name("media-playback-start-symbolic")
        launch_btn.set_tooltip_text(f"Launch {app.name}")
        launch_btn.set_valign(Gtk.Align.CENTER)
        launch_btn.connect("clicked", self._on_launch_app, app)
        launch_btn.set_visible(False)
        row.add_suffix(launch_btn)
        row.launch_btn = launch_btn
        
        return row
    
    def _refresh_status(self):
        """Refresh all status indicators."""
        def check():
            # Check 32-bit support
            lib32_ok, lib32_msg = check_32bit_support(self.distro.family)
            
            # Check Vulkan
            vulkan_ok = self._check_vulkan()
            
            # Check app statuses
            app_status = {}
            for app in GAMING_APPS + GAMING_UTILITIES:
                app_status[app.id] = check_app_installed(app)
            
            GLib.idle_add(self._update_status, lib32_ok, lib32_msg, vulkan_ok, app_status)
        
        threading.Thread(target=check, daemon=True).start()
    
    def _check_vulkan(self) -> bool:
        """Check if Vulkan is available."""
        try:
            result = subprocess.run(
                ['vulkaninfo', '--summary'],
                capture_output=True, text=True
            )
            return result.returncode == 0 and 'GPU' in result.stdout
        except Exception:
            # vulkaninfo might not be installed
            # Check if vulkan libraries exist
            try:
                result = subprocess.run(
                    ['ldconfig', '-p'],
                    capture_output=True, text=True
                )
                return 'libvulkan' in result.stdout
            except Exception:
                return False
    
    def _update_status(self, lib32_ok: bool, lib32_msg: str, vulkan_ok: bool, app_status: dict):
        """Update status displays."""
        # 32-bit status
        if lib32_ok:
            self.lib32_row.set_subtitle(f"✓ {lib32_msg}")
        else:
            self.lib32_row.set_subtitle(f"⚠ {lib32_msg}")
        
        # Vulkan status
        if vulkan_ok:
            self.vulkan_row.set_subtitle("✓ Vulkan is available")
        else:
            self.vulkan_row.set_subtitle("⚠ Install Vulkan drivers for best performance")
        
        # App statuses
        all_rows = {**self.platform_rows, **self.utility_rows}
        for app_id, installed in app_status.items():
            if app_id in all_rows:
                row = all_rows[app_id]
                if installed:
                    row.status_label.set_label("Installed")
                    row.install_btn.set_visible(False)
                    row.launch_btn.set_visible(True)
                else:
                    row.status_label.set_label("")
                    row.install_btn.set_visible(True)
                    row.launch_btn.set_visible(False)
    
    def _on_install_app(self, button, app: GamingApp, row):
        """Install a gaming app."""
        button.set_sensitive(False)
        button.set_label("Installing...")
        
        # Get package name for this distro
        package = app.packages.get(self.distro.family)
        
        if not package and app.flatpak and self.has_flatpak:
            # Use flatpak as fallback
            self._install_via_flatpak(app, row)
            return
        
        if not package:
            self.window.show_toast(f"{app.name} not available for {self.distro.name}")
            button.set_sensitive(True)
            button.set_label("Install")
            return
        
        # Build install command
        if self.distro.family == DistroFamily.ARCH:
            # Check if it's an AUR package
            if '-bin' in package or '-git' in package:
                # Try yay or paru
                aur_helper = self._get_aur_helper()
                if aur_helper:
                    cmd = f"{aur_helper} -S --noconfirm {package}"
                else:
                    self.window.show_toast(f"{app.name} requires an AUR helper (yay/paru)")
                    button.set_sensitive(True)
                    button.set_label("Install")
                    return
            else:
                cmd = f"sudo pacman -S --noconfirm {package}"
        elif self.distro.family == DistroFamily.DEBIAN:
            cmd = f"sudo apt install -y {package}"
        elif self.distro.family == DistroFamily.FEDORA:
            cmd = f"sudo dnf install -y {package}"
        elif self.distro.family == DistroFamily.OPENSUSE:
            cmd = f"sudo zypper install -y {package}"
        else:
            self.window.show_toast(f"Unsupported distribution")
            button.set_sensitive(True)
            button.set_label("Install")
            return
        
        # Run in terminal
        self._run_install_command(cmd, app.name, row)
    
    def _install_via_flatpak(self, app: GamingApp, row):
        """Install an app via Flatpak."""
        cmd = f"flatpak install -y flathub {app.flatpak}"
        self._run_install_command(cmd, app.name, row)
    
    def _run_install_command(self, cmd: str, app_name: str, row):
        """Run an install command in terminal."""
        script = f'''echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Installing {app_name}..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
{cmd}
echo ""
echo "✓ Installation complete!"
echo ""
echo "Press Enter to close..."
read'''
        
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
                    self.window.show_toast(f"Installing {app_name}...")
                    
                    # Refresh status after delay
                    GLib.timeout_add(5000, self._refresh_status)
                    return
            except Exception:
                continue
        
        self.window.show_toast("Could not find terminal emulator")
        row.install_btn.set_sensitive(True)
        row.install_btn.set_label("Install")
    
    def _get_aur_helper(self) -> Optional[str]:
        """Get available AUR helper."""
        for helper in ['yay', 'paru', 'pikaur', 'trizen']:
            try:
                if subprocess.run(['which', helper], capture_output=True).returncode == 0:
                    return helper
            except Exception:
                pass
        return None
    
    def _on_launch_app(self, button, app: GamingApp):
        """Launch a gaming app."""
        try:
            subprocess.Popen([app.check_command])
        except Exception as e:
            self.window.show_toast(f"Could not launch {app.name}")
    
    def _on_open_protondb(self, row):
        """Open ProtonDB website."""
        try:
            subprocess.Popen(['xdg-open', 'https://www.protondb.com/'])
        except Exception:
            self.window.show_toast("Could not open browser")
