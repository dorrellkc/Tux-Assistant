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
