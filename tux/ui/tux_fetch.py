"""
Tux Fetch - System Information Display

A fastfetch-style system info panel for Tux Assistant.
Displays distro, hardware, and system stats with ASCII art.

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Pango

import os
import subprocess
import platform
from datetime import datetime
from typing import Optional


# =============================================================================
# ASCII Art Logos (Simplified versions for GUI display)
# =============================================================================

DISTRO_LOGOS = {
    'arch': """
      /\\
     /  \\
    /\\   \\
   /  ..  \\
  /  '  '  \\
 / ..'  '.. \\
/_____/\\_____\\
""",
    'manjaro': """
 ██████████████
 ██████████████
 ██████  ██████
 ██████  ██████
 ██████  ██████
 ██████  ██████
 ██████  ██████
""",
    'endeavouros': """
      /\\
     /  \\
    / /\\ \\
   / /  \\ \\
  / /    \\ \\
 / / _____\\ \\
/_/  \\______\\
""",
    'cachyos': """
      /\\
     /  \\
    /    \\
   /  /\\  \\
  /  /  \\  \\
 /  /    \\  \\
/__/______\\__\\
""",
    'debian': """
   _____
  /  __ \\
 |  /    |
 |  \\___-
 -_
   --_
""",
    'ubuntu': """
         _
     ---(_)
 _/  ---  \\
(_) |   |
  \\  --- _/
     ---(_)
""",
    'linuxmint': """
 ___________
|_          \\
  | | _____ |
  | | | | | |
  | | | | | |
  | \\_____| |
  \\_________/
""",
    'fedora': """
      _____
     /   __)\\
     |  /  \\ \\
  ___|  |__/ /
 / (_    _) /
/ /  |  | \\ \\
\\_)  |  |  \\_)
     |__|
""",
    'opensuse': """
  _______
__|   __ \\
     / .\\  \\
     \\__/ |
   _______|
   \\_______
__________/
""",
    'pop': """
 ______
\\      \\
 \\  O   \\
 /       /
/   O   /
\\______/
""",
    'generic': """
    .--.
   |o_o |
   |:_/ |
  //   \\ \\
 (|     | )
/'\\_   _/`\\
\\___)=(___/
"""
}


# =============================================================================
# System Information Gathering
# =============================================================================

def get_uptime() -> str:
    """Get system uptime."""
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
        
        days = int(uptime_seconds // 86400)
        hours = int((uptime_seconds % 86400) // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        parts.append(f"{minutes}m")
        
        return " ".join(parts)
    except:
        return "Unknown"


def get_shell() -> str:
    """Get current shell."""
    shell = os.environ.get('SHELL', '/bin/bash')
    return os.path.basename(shell)


def get_kernel() -> str:
    """Get kernel version."""
    try:
        return platform.release()
    except:
        return "Unknown"


def get_packages_count() -> str:
    """Get approximate package count."""
    try:
        # Try pacman first (Arch)
        result = subprocess.run(['pacman', '-Q'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            count = len(result.stdout.strip().split('\n'))
            return f"{count} (pacman)"
    except:
        pass
    
    try:
        # Try dpkg (Debian/Ubuntu)
        result = subprocess.run(['dpkg', '--list'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            # Count lines starting with 'ii' (installed)
            count = sum(1 for line in result.stdout.split('\n') if line.startswith('ii'))
            return f"{count} (dpkg)"
    except:
        pass
    
    try:
        # Try rpm (Fedora/RHEL)
        result = subprocess.run(['rpm', '-qa'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            count = len(result.stdout.strip().split('\n'))
            return f"{count} (rpm)"
    except:
        pass
    
    return "Unknown"


def get_resolution() -> str:
    """Get screen resolution."""
    try:
        result = subprocess.run(['xrandr', '--current'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if ' connected' in line and 'x' in line:
                    # Find resolution in format like "1920x1080"
                    parts = line.split()
                    for part in parts:
                        if 'x' in part and part[0].isdigit():
                            res = part.split('+')[0]  # Remove position info
                            return res
    except:
        pass
    
    # Try wlr-randr for Wayland
    try:
        result = subprocess.run(['wlr-randr'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'current' in line.lower() and 'x' in line:
                    parts = line.split()
                    for part in parts:
                        if 'x' in part and part[0].isdigit():
                            return part.split('@')[0]
    except:
        pass
    
    return "Unknown"


def get_memory_usage() -> tuple[float, float, float]:
    """Get RAM usage: (used_gb, total_gb, percent)."""
    try:
        with open('/proc/meminfo', 'r') as f:
            meminfo = {}
            for line in f:
                parts = line.split(':')
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = int(parts[1].strip().split()[0])  # Value in kB
                    meminfo[key] = value
        
        total = meminfo.get('MemTotal', 0)
        available = meminfo.get('MemAvailable', 0)
        used = total - available
        
        total_gb = round(total / 1024 / 1024, 1)
        used_gb = round(used / 1024 / 1024, 1)
        percent = round((used / total) * 100, 1) if total > 0 else 0
        
        return (used_gb, total_gb, percent)
    except:
        return (0, 0, 0)


def get_disk_usage() -> tuple[float, float, float]:
    """Get root disk usage: (used_gb, total_gb, percent)."""
    try:
        statvfs = os.statvfs('/')
        total = statvfs.f_frsize * statvfs.f_blocks
        free = statvfs.f_frsize * statvfs.f_bavail
        used = total - free
        
        total_gb = round(total / 1024 / 1024 / 1024, 1)
        used_gb = round(used / 1024 / 1024 / 1024, 1)
        percent = round((used / total) * 100, 1) if total > 0 else 0
        
        return (used_gb, total_gb, percent)
    except:
        return (0, 0, 0)


def get_cpu_usage() -> float:
    """Get current CPU usage percentage."""
    try:
        # Read /proc/stat twice with a small delay
        def read_cpu_stats():
            with open('/proc/stat', 'r') as f:
                line = f.readline()
                parts = line.split()[1:]  # Skip 'cpu' label
                return [int(x) for x in parts]
        
        stats1 = read_cpu_stats()
        # For instant reading, use a simpler approach
        idle = stats1[3]
        total = sum(stats1)
        
        # Return approximate based on idle time ratio
        return round(100 - (idle / total * 100), 1)
    except:
        return 0


def get_terminal() -> str:
    """Get terminal emulator name."""
    # Check common environment variables
    term = os.environ.get('TERM_PROGRAM', '')
    if term:
        return term
    
    term = os.environ.get('TERMINAL', '')
    if term:
        return os.path.basename(term)
    
    # Check parent process
    try:
        ppid = os.getppid()
        with open(f'/proc/{ppid}/comm', 'r') as f:
            return f.read().strip()
    except:
        pass
    
    return os.environ.get('TERM', 'unknown')


# =============================================================================
# TuxFetch Widget
# =============================================================================

class TuxFetchPanel(Gtk.Box):
    """A fastfetch-style system information panel."""
    
    def __init__(self, distro_info, desktop_info, hardware_info):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        self.distro = distro_info
        self.desktop = desktop_info
        self.hardware = hardware_info
        
        # Styling
        self.set_margin_top(16)
        self.set_margin_bottom(16)
        self.set_margin_start(16)
        self.set_margin_end(16)
        self.add_css_class("card")
        
        self.build_ui()
    
    def build_ui(self):
        """Build the fetch panel UI."""
        # Title
        title = Gtk.Label()
        title.set_markup("<b>System Info</b>")
        title.set_halign(Gtk.Align.START)
        title.set_margin_bottom(8)
        self.append(title)
        
        # Main content in horizontal layout: logo | info
        main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=16)
        self.append(main_box)
        
        # ASCII Logo
        logo_label = Gtk.Label()
        logo_label.set_markup(f"<tt>{self._get_logo()}</tt>")
        logo_label.set_halign(Gtk.Align.START)
        logo_label.set_valign(Gtk.Align.START)
        logo_label.add_css_class("monospace")
        main_box.append(logo_label)
        
        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        main_box.append(sep)
        
        # Info lines
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        info_box.set_hexpand(True)
        main_box.append(info_box)
        
        # Gather all info
        user = os.environ.get('USER', 'user')
        hostname = platform.node()
        
        # Add info lines
        info_lines = [
            ("", f"<b>{user}@{hostname}</b>"),
            ("", "─" * 20),
            ("OS", f"{self.distro.name}"),
            ("Kernel", get_kernel()),
            ("Uptime", get_uptime()),
            ("Packages", get_packages_count()),
            ("Shell", get_shell()),
            ("DE", f"{self.desktop.display_name}"),
            ("WM", self.desktop.session_type.upper()),
            ("Resolution", get_resolution()),
            ("Terminal", get_terminal()),
            ("", ""),  # Spacer
            ("CPU", self._format_cpu()),
            ("GPU", self._format_gpu()),
            ("Memory", self._format_memory()),
            ("Disk (/)", self._format_disk()),
        ]
        
        for label, value in info_lines:
            row = self._create_info_row(label, value)
            info_box.append(row)
        
        # Color palette at bottom
        palette = self._create_color_palette()
        palette.set_margin_top(8)
        self.append(palette)
    
    def _get_logo(self) -> str:
        """Get the ASCII logo for the current distro."""
        distro_id = self.distro.id.lower()
        
        # Check exact match first
        if distro_id in DISTRO_LOGOS:
            return DISTRO_LOGOS[distro_id]
        
        # Check family-based
        family = self.distro.family.value.lower()
        if family in DISTRO_LOGOS:
            return DISTRO_LOGOS[family]
        
        # Default to generic Tux
        return DISTRO_LOGOS['generic']
    
    def _create_info_row(self, label: str, value: str) -> Gtk.Widget:
        """Create a single info row."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        if label:
            label_widget = Gtk.Label()
            label_widget.set_markup(f"<b>{label}</b>")
            label_widget.set_halign(Gtk.Align.START)
            label_widget.set_size_request(80, -1)
            box.append(label_widget)
        
        value_widget = Gtk.Label()
        value_widget.set_markup(value)
        value_widget.set_halign(Gtk.Align.START)
        value_widget.set_ellipsize(Pango.EllipsizeMode.END)
        value_widget.set_hexpand(True)
        box.append(value_widget)
        
        return box
    
    def _format_cpu(self) -> str:
        """Format CPU info."""
        cpu = self.hardware.cpu_model
        if cpu == "Unknown CPU":
            return "Unknown"
        
        # Shorten common prefixes
        cpu = cpu.replace("Intel(R) Core(TM)", "Intel")
        cpu = cpu.replace("AMD Ryzen", "Ryzen")
        cpu = cpu.replace(" Processor", "")
        cpu = cpu.replace(" with Radeon Graphics", "")
        
        # Truncate if too long
        if len(cpu) > 35:
            cpu = cpu[:32] + "..."
        
        return cpu
    
    def _format_gpu(self) -> str:
        """Format GPU info."""
        gpu = self.hardware.gpu_model
        if gpu == "Unknown GPU":
            return "Unknown"
        
        # Shorten common prefixes
        gpu = gpu.replace("NVIDIA Corporation", "NVIDIA")
        gpu = gpu.replace("Advanced Micro Devices, Inc.", "AMD")
        gpu = gpu.replace("Intel Corporation", "Intel")
        gpu = gpu.replace("[", "").replace("]", "")
        
        # Truncate if too long
        if len(gpu) > 35:
            gpu = gpu[:32] + "..."
        
        return gpu
    
    def _format_memory(self) -> str:
        """Format memory usage."""
        used, total, percent = get_memory_usage()
        return f"{used}GB / {total}GB ({percent}%)"
    
    def _format_disk(self) -> str:
        """Format disk usage."""
        used, total, percent = get_disk_usage()
        return f"{used}GB / {total}GB ({percent}%)"
    
    def _create_color_palette(self) -> Gtk.Widget:
        """Create the terminal color palette display."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        box.set_halign(Gtk.Align.CENTER)
        
        # Standard terminal colors
        colors = [
            "#2e3436", "#cc0000", "#4e9a06", "#c4a000",
            "#3465a4", "#75507b", "#06989a", "#d3d7cf",
            "#555753", "#ef2929", "#8ae234", "#fce94f",
            "#729fcf", "#ad7fa8", "#34e2e2", "#eeeeec"
        ]
        
        for color in colors:
            block = Gtk.DrawingArea()
            block.set_size_request(16, 16)
            block.set_draw_func(self._draw_color_block, color)
            box.append(block)
        
        return box
    
    def _draw_color_block(self, area, cr, width, height, color):
        """Draw a colored block."""
        from gi.repository import Gdk
        rgba = Gdk.RGBA()
        rgba.parse(color)
        cr.set_source_rgba(rgba.red, rgba.green, rgba.blue, 1.0)
        cr.rectangle(0, 0, width, height)
        cr.fill()


class TuxFetchCompact(Gtk.Box):
    """A more compact version for smaller windows."""
    
    def __init__(self, distro_info, desktop_info, hardware_info):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        
        self.distro = distro_info
        self.desktop = desktop_info
        self.hardware = hardware_info
        
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.add_css_class("card")
        
        self.build_ui()
    
    def build_ui(self):
        """Build compact UI."""
        # Title with user@host
        user = os.environ.get('USER', 'user')
        hostname = platform.node()
        
        title = Gtk.Label()
        title.set_markup(f"<b>{user}@{hostname}</b>")
        title.set_halign(Gtk.Align.CENTER)
        self.append(title)
        
        sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        self.append(sep)
        
        # Key stats in a grid
        grid = Gtk.Grid()
        grid.set_row_spacing(4)
        grid.set_column_spacing(12)
        self.append(grid)
        
        stats = [
            ("OS", self.distro.name),
            ("DE", self.desktop.display_name),
            ("Kernel", get_kernel()),
            ("Uptime", get_uptime()),
        ]
        
        for i, (label, value) in enumerate(stats):
            lbl = Gtk.Label()
            lbl.set_markup(f"<b>{label}</b>")
            lbl.set_halign(Gtk.Align.END)
            grid.attach(lbl, 0, i, 1, 1)
            
            val = Gtk.Label(label=value)
            val.set_halign(Gtk.Align.START)
            val.set_ellipsize(Pango.EllipsizeMode.END)
            grid.attach(val, 1, i, 1, 1)
        
        # Memory bar
        used, total, percent = get_memory_usage()
        mem_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        mem_box.set_margin_top(8)
        self.append(mem_box)
        
        mem_label = Gtk.Label()
        mem_label.set_markup(f"<small>RAM: {used}GB / {total}GB</small>")
        mem_box.append(mem_label)
        
        mem_bar = Gtk.ProgressBar()
        mem_bar.set_fraction(percent / 100)
        mem_box.append(mem_bar)


class TuxFetchSidebar(Gtk.Box):
    """A fixed sidebar version that blends with the window chrome."""
    
    def __init__(self, distro_info, desktop_info, hardware_info):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        self.distro = distro_info
        self.desktop = desktop_info
        self.hardware = hardware_info
        
        # Style as sidebar - don't expand, stay at top
        self.add_css_class("tux-fetch-sidebar")
        self.set_vexpand(False)  # Don't expand - stay compact
        self.set_valign(Gtk.Align.START)  # Align to top
        
        self.build_ui()
    
    def build_ui(self):
        """Build the sidebar UI."""
        # Inner box with padding
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        inner.set_margin_top(16)
        inner.set_margin_bottom(16)
        inner.set_margin_start(12)
        inner.set_margin_end(12)
        self.append(inner)
        
        # ASCII Logo (compact)
        logo_label = Gtk.Label()
        logo_label.set_markup(f"<tt><small>{self._get_logo()}</small></tt>")
        logo_label.set_halign(Gtk.Align.CENTER)
        logo_label.add_css_class("dim-label")
        inner.append(logo_label)
        
        # User@hostname
        user = os.environ.get('USER', 'user')
        hostname = platform.node()
        
        user_label = Gtk.Label()
        user_label.set_markup(f"<b>{user}@{hostname}</b>")
        user_label.set_halign(Gtk.Align.CENTER)
        user_label.set_margin_top(8)
        inner.append(user_label)
        
        # Separator line
        sep_label = Gtk.Label()
        sep_label.set_markup("<small>────────────────────</small>")
        sep_label.add_css_class("dim-label")
        sep_label.set_halign(Gtk.Align.CENTER)
        inner.append(sep_label)
        
        # Info rows - comprehensive like fastfetch
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box.set_margin_top(4)
        inner.append(info_box)
        
        # System info
        info_lines = [
            ("OS", f"{self.distro.name} {platform.machine()}"),
            ("Host", self._get_host_model()),
            ("Kernel", get_kernel()),
            ("Uptime", get_uptime()),
            ("Pkgs", get_packages_count()),
            ("Shell", self._get_shell_with_version()),
        ]
        
        for label, value in info_lines:
            row = self._create_info_row(label, value)
            info_box.append(row)
        
        # Display/Desktop section
        info_box2 = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        info_box2.set_margin_top(6)
        inner.append(info_box2)
        
        display_lines = [
            ("Display", get_resolution()),
            ("DE", self._get_de_with_version()),
            ("WM", self._get_wm()),
            ("Theme", self._get_theme()),
            ("Icons", self._get_icons()),
            ("Terminal", self._get_terminal_with_version()),
        ]
        
        for label, value in display_lines:
            if value and value != "Unknown":
                row = self._create_info_row(label, value)
                info_box2.append(row)
        
        # Hardware section
        hw_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        hw_box.set_margin_top(6)
        inner.append(hw_box)
        
        hw_lines = [
            ("CPU", self._format_cpu_short()),
            ("GPU", self._format_gpu_short()),
        ]
        
        for label, value in hw_lines:
            row = self._create_info_row(label, value)
            hw_box.append(row)
        
        # Memory bar
        used, total, percent = get_memory_usage()
        mem_row = self._create_bar_row("Memory", f"{used}/{total}GB", percent)
        hw_box.append(mem_row)
        
        # Swap info
        swap_info = self._get_swap_info()
        if swap_info:
            swap_row = self._create_info_row("Swap", swap_info)
            hw_box.append(swap_row)
        
        # Disk bar
        used_d, total_d, percent_d = get_disk_usage()
        disk_row = self._create_bar_row("Disk (/)", f"{int(used_d)}/{int(total_d)}GB", percent_d)
        hw_box.append(disk_row)
        
        # Network/Battery section
        net_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        net_box.set_margin_top(6)
        inner.append(net_box)
        
        # Local IP
        local_ip = self._get_local_ip()
        if local_ip:
            ip_row = self._create_info_row("Local IP", local_ip)
            net_box.append(ip_row)
        
        # Battery (for laptops)
        battery_info = self._get_battery_info()
        if battery_info:
            bat_row = self._create_info_row("Battery", battery_info)
            net_box.append(bat_row)
        
        # Locale
        locale_info = self._get_locale()
        if locale_info:
            locale_row = self._create_info_row("Locale", locale_info)
            net_box.append(locale_row)
        
        # Color palette at very bottom
        palette = self._create_color_palette()
        palette.set_margin_top(12)
        palette.set_halign(Gtk.Align.CENTER)
        inner.append(palette)
    
    def _get_logo(self) -> str:
        """Get a compact ASCII logo matching fastfetch style."""
        distro_id = self.distro.id.lower()
        
        # More accurate logos matching fastfetch
        logos = {
            # EndeavourOS - curved mountain shape
            'endeavouros': """      /\\
     /  \\
    /`'.,\\
   /     ',
  /      ,`\\
 /   ,.`'   \\
/.,'`googarch\\""",
            
            # Arch - classic A shape  
            'arch': """       /\\
      /  \\
     /    \\
    /      \\
   /   /\\   \\
  /   /  \\   \\
 /   /    \\   \\
/___/      \\___\\""",
            
            # Manjaro - blocky M
            'manjaro': """██████████████████
██████████████████
████          ████
████ ████████ ████
████ ████████ ████
████ ████████ ████
████ ████████ ████
████ ████████ ████""",
            
            # CachyOS - arch derivative
            'cachyos': """      /\\
     /  \\
    /    \\
   / ___  \\
  / |   |  \\
 /  |___|   \\
/____________\\""",
            
            # Garuda - eagle/bird
            'garuda': """       _______
      /  ___  \\
     / /`   `\\ \\
    | | () () | |
     \\ \\  ^  / /
      \\ `---' /
       `-----'""",
            
            # Debian - swirl
            'debian': """    _____
   /  __ \\
  |  /    |
  |  \\___-
  -_
    --_""",
            
            # Ubuntu - circle of friends
            'ubuntu': """           _
       ---(_)
   _/  ---  \\
  (_) |   |
    \\  --- _/
       ---(_)""",
            
            # Linux Mint - leaf
            'linuxmint': """  ___________
 |_          \\
   | | _____ |
   | | | | | |
   | | | | | |
   | \\_____| |
   \\_________/""",
            
            # Pop!_OS
            'pop': """   ____________
  /  _______   \\
 / /        \\   \\
| |  ______  |  |
| | |__  __| |  |
 \\ \\   ||   /  /
  \\_\\  ||  /__/""",
            
            # Fedora - infinity
            'fedora': """        _____
       /   __)\\
       |  /  \\ \\
    ___|  |__/ /
   / (_    _)_/
  / /  |  |
  \\_)  |__|""",
            
            # openSUSE - gecko
            'opensuse': """    _______
  __|   __ \\
       / .\\ \\
       \\__/ |
     _______|
     \\_______
  __________/""",
            
            # Zorin
            'zorin': """   ________
  /  ____  \\
 |  |    |  |
 |  |    |  |
 |  |____|  |
 |    __    |
  \\__|  |__/""",
            
            # Generic Tux
            'generic': """    .---.
   /     \\
   \\.@-@./
   /`\\_/`\\
  //  _  \\\\
 | \\     / |
  \\|  |  |/
   |__|__|""",
        }
        
        # Check exact match first
        if distro_id in logos:
            return logos[distro_id]
        
        # Check for common derivatives
        if 'endeavour' in distro_id:
            return logos['endeavouros']
        if 'manjaro' in distro_id:
            return logos['manjaro']
        if 'cachyos' in distro_id or 'cachy' in distro_id:
            return logos['cachyos']
        if 'garuda' in distro_id:
            return logos['garuda']
        
        # Check family
        family = self.distro.family.value.lower()
        if family == 'arch':
            return logos['arch']
        if family == 'debian':
            return logos['debian']
        if family == 'fedora':
            return logos['fedora']
        if family == 'opensuse':
            return logos['opensuse']
        
        return logos['generic']
    
    def _create_info_row(self, label: str, value: str) -> Gtk.Widget:
        """Create a compact info row."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        
        lbl = Gtk.Label()
        lbl.set_markup(f"<small><b>{label}</b></small>")
        lbl.set_halign(Gtk.Align.START)
        lbl.set_size_request(50, -1)
        lbl.add_css_class("dim-label")
        box.append(lbl)
        
        val = Gtk.Label()
        val.set_markup(f"<small>{GLib.markup_escape_text(value)}</small>")
        val.set_halign(Gtk.Align.START)
        val.set_ellipsize(Pango.EllipsizeMode.END)
        val.set_hexpand(True)
        box.append(val)
        
        return box
    
    def _create_bar_row(self, label: str, text: str, percent: float) -> Gtk.Widget:
        """Create a row with a progress bar."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        box.set_margin_top(4)
        
        # Label row
        label_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        
        lbl = Gtk.Label()
        lbl.set_markup(f"<small><b>{label}</b></small>")
        lbl.set_halign(Gtk.Align.START)
        lbl.add_css_class("dim-label")
        label_box.append(lbl)
        
        val = Gtk.Label()
        val.set_markup(f"<small>{text}</small>")
        val.set_halign(Gtk.Align.END)
        val.set_hexpand(True)
        label_box.append(val)
        
        box.append(label_box)
        
        # Progress bar
        bar = Gtk.ProgressBar()
        bar.set_fraction(min(percent / 100, 1.0))
        bar.add_css_class("tux-fetch-bar")
        box.append(bar)
        
        return box
    
    def _format_cpu_short(self) -> str:
        """Get shortened CPU name."""
        cpu = self.hardware.cpu_model
        if cpu == "Unknown CPU":
            return "Unknown"
        
        # Extract key info
        cpu = cpu.replace("Intel(R) Core(TM)", "Intel")
        cpu = cpu.replace("Intel(R)", "Intel")
        cpu = cpu.replace("AMD Ryzen", "Ryzen")
        cpu = cpu.replace(" Processor", "")
        cpu = cpu.replace(" with Radeon Graphics", "")
        cpu = cpu.split('@')[0].strip()
        
        if len(cpu) > 22:
            cpu = cpu[:20] + "…"
        
        return cpu
    
    def _format_gpu_short(self) -> str:
        """Get shortened GPU name."""
        gpu = self.hardware.gpu_model
        if gpu == "Unknown GPU":
            return "Unknown"
        
        # Simplify
        gpu = gpu.replace("NVIDIA Corporation", "NVIDIA")
        gpu = gpu.replace("Advanced Micro Devices, Inc.", "AMD")
        gpu = gpu.replace("Intel Corporation", "Intel")
        gpu = gpu.replace("[", "").replace("]", "")
        
        if len(gpu) > 24:
            gpu = gpu[:22] + "…"
        
        return gpu
    
    def _get_host_model(self) -> str:
        """Get computer model name."""
        try:
            # Try DMI info
            paths = [
                '/sys/devices/virtual/dmi/id/product_name',
                '/sys/devices/virtual/dmi/id/product_family',
            ]
            for path in paths:
                if os.path.exists(path):
                    with open(path, 'r') as f:
                        model = f.read().strip()
                        if model and model.lower() not in ('to be filled', 'default string', 'system product name'):
                            return model[:28] if len(model) > 28 else model
        except:
            pass
        return "Unknown"
    
    def _get_shell_with_version(self) -> str:
        """Get shell name with version."""
        shell = get_shell()
        try:
            if shell == 'bash':
                result = subprocess.run(['bash', '--version'], capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    # Parse "GNU bash, version 5.2.15(1)-release"
                    line = result.stdout.split('\n')[0]
                    if 'version' in line:
                        version = line.split('version')[1].split()[0].split('(')[0]
                        return f"bash {version}"
            elif shell == 'zsh':
                result = subprocess.run(['zsh', '--version'], capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    parts = result.stdout.split()
                    if len(parts) >= 2:
                        return f"zsh {parts[1]}"
            elif shell == 'fish':
                result = subprocess.run(['fish', '--version'], capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    parts = result.stdout.split()
                    if len(parts) >= 3:
                        return f"fish {parts[2]}"
        except:
            pass
        return shell
    
    def _get_de_with_version(self) -> str:
        """Get DE with version if available."""
        de = self.desktop.display_name
        # Try to get version
        try:
            if 'plasma' in de.lower() or 'kde' in de.lower():
                result = subprocess.run(['plasmashell', '--version'], capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    version = result.stdout.strip().split()[-1]
                    return f"KDE Plasma {version}"
            elif 'gnome' in de.lower():
                result = subprocess.run(['gnome-shell', '--version'], capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    version = result.stdout.strip().split()[-1]
                    return f"GNOME {version}"
            elif 'xfce' in de.lower():
                result = subprocess.run(['xfce4-session', '--version'], capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'xfce4-session' in line:
                            version = line.split()[-1].strip('()')
                            return f"XFCE {version}"
        except:
            pass
        return de
    
    def _get_wm(self) -> str:
        """Get window manager."""
        # Check for specific WMs
        session_type = self.desktop.session_type.upper()
        
        try:
            # KWin
            if subprocess.run(['pgrep', '-x', 'kwin_wayland'], capture_output=True).returncode == 0:
                return "KWin (Wayland)"
            if subprocess.run(['pgrep', '-x', 'kwin_x11'], capture_output=True).returncode == 0:
                return "KWin (X11)"
            # Mutter (GNOME)
            if subprocess.run(['pgrep', '-x', 'mutter'], capture_output=True).returncode == 0:
                return "Mutter"
            # Others
            wms = ['sway', 'hyprland', 'i3', 'openbox', 'xfwm4', 'marco', 'metacity']
            for wm in wms:
                if subprocess.run(['pgrep', '-x', wm], capture_output=True).returncode == 0:
                    return wm.capitalize()
        except:
            pass
        
        return session_type
    
    def _get_theme(self) -> str:
        """Get GTK/Qt theme."""
        try:
            # Try GTK theme
            result = subprocess.run(['gsettings', 'get', 'org.gnome.desktop.interface', 'gtk-theme'], 
                                   capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                theme = result.stdout.strip().strip("'")
                return theme
        except:
            pass
        
        # Try reading from config
        try:
            gtk3_settings = os.path.expanduser('~/.config/gtk-3.0/settings.ini')
            if os.path.exists(gtk3_settings):
                with open(gtk3_settings, 'r') as f:
                    for line in f:
                        if line.startswith('gtk-theme-name'):
                            return line.split('=')[1].strip()
        except:
            pass
        
        return "Unknown"
    
    def _get_icons(self) -> str:
        """Get icon theme."""
        try:
            result = subprocess.run(['gsettings', 'get', 'org.gnome.desktop.interface', 'icon-theme'],
                                   capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                return result.stdout.strip().strip("'")
        except:
            pass
        return "Unknown"
    
    def _get_terminal_with_version(self) -> str:
        """Get terminal with version."""
        term = get_terminal()
        try:
            if term == 'konsole':
                result = subprocess.run(['konsole', '--version'], capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'konsole' in line.lower():
                            parts = line.split()
                            if len(parts) >= 2:
                                return f"konsole {parts[-1]}"
            elif term == 'gnome-terminal':
                result = subprocess.run(['gnome-terminal', '--version'], capture_output=True, text=True, timeout=2)
                if result.returncode == 0:
                    parts = result.stdout.split()
                    if len(parts) >= 4:
                        return f"gnome-terminal {parts[3]}"
        except:
            pass
        return term
    
    def _get_swap_info(self) -> str:
        """Get swap usage."""
        try:
            with open('/proc/meminfo', 'r') as f:
                swap_total = 0
                swap_free = 0
                for line in f:
                    if line.startswith('SwapTotal:'):
                        swap_total = int(line.split()[1])
                    elif line.startswith('SwapFree:'):
                        swap_free = int(line.split()[1])
                
                if swap_total > 0:
                    swap_used = swap_total - swap_free
                    used_gb = round(swap_used / 1024 / 1024, 2)
                    total_gb = round(swap_total / 1024 / 1024, 2)
                    percent = round((swap_used / swap_total) * 100, 0)
                    return f"{used_gb}/{total_gb}GB ({int(percent)}%)"
                else:
                    return "Disabled"
        except:
            pass
        return None
    
    def _get_local_ip(self) -> str:
        """Get local IP address."""
        try:
            # Get default interface IP
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            pass
        return None
    
    def _get_battery_info(self) -> str:
        """Get battery status for laptops."""
        try:
            bat_path = '/sys/class/power_supply/BAT0'
            if not os.path.exists(bat_path):
                bat_path = '/sys/class/power_supply/BAT1'
            if not os.path.exists(bat_path):
                return None  # No battery (desktop)
            
            # Read capacity
            with open(f'{bat_path}/capacity', 'r') as f:
                capacity = f.read().strip()
            
            # Read status
            with open(f'{bat_path}/status', 'r') as f:
                status = f.read().strip()
            
            status_map = {
                'Charging': '⚡',
                'Discharging': '🔋',
                'Full': '✓',
                'Not charging': '⏸'
            }
            icon = status_map.get(status, '')
            
            return f"{capacity}% {icon} [{status}]"
        except:
            pass
        return None
    
    def _get_locale(self) -> str:
        """Get system locale."""
        import locale
        try:
            loc = locale.getlocale()[0]
            if loc:
                return loc.replace('_', '-')
        except:
            pass
        
        # Fallback to env
        return os.environ.get('LANG', 'Unknown').split('.')[0]
    
    def _create_color_palette(self) -> Gtk.Widget:
        """Create small color blocks."""
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=1)
        
        colors = [
            "#2e3436", "#cc0000", "#4e9a06", "#c4a000",
            "#3465a4", "#75507b", "#06989a", "#d3d7cf",
        ]
        
        for color in colors:
            block = Gtk.DrawingArea()
            block.set_size_request(12, 12)
            block.set_draw_func(self._draw_color_block, color)
            box.append(block)
        
        return box
    
    def _draw_color_block(self, area, cr, width, height, color):
        """Draw a colored block."""
        from gi.repository import Gdk
        rgba = Gdk.RGBA()
        rgba.parse(color)
        cr.set_source_rgba(rgba.red, rgba.green, rgba.blue, 1.0)
        cr.rectangle(0, 0, width, height)
        cr.fill()
