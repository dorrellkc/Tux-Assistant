"""
Tux Fetch - System Information Display

Displays system information using fastfetch output.
Honors fastfetch by using their tool, not copying it.

Copyright (c) 2025 Christopher Dorrell. Licensed under GPL-3.0.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

import os
import subprocess
import platform
import re


class TuxFetchSidebar(Gtk.Box):
    """Display fastfetch output in a clean monochrome style."""
    
    def __init__(self, distro_info, desktop_info, hardware_info):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        self.distro = distro_info
        self.desktop = desktop_info
        self.hardware = hardware_info
        
        # Style as sidebar - don't expand, stay at top
        self.add_css_class("tux-fetch-sidebar")
        self.set_vexpand(False)
        self.set_valign(Gtk.Align.START)
        
        self.build_ui()
    
    def build_ui(self):
        """Build the UI with fastfetch output."""
        # Inner box with padding
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        inner.set_margin_top(12)
        inner.set_margin_bottom(12)
        inner.set_margin_start(8)
        inner.set_margin_end(8)
        self.append(inner)
        
        # Get fastfetch output
        fastfetch_output = self._get_fastfetch_output()
        
        # Display in monospace label
        output_label = Gtk.Label()
        output_label.set_markup(f"<tt><small>{GLib.markup_escape_text(fastfetch_output)}</small></tt>")
        output_label.set_halign(Gtk.Align.START)
        output_label.set_valign(Gtk.Align.START)
        output_label.set_selectable(True)  # Allow copying
        output_label.add_css_class("tux-fetch-output")
        inner.append(output_label)
    
    def _get_fastfetch_output(self) -> str:
        """Get fastfetch output, installing if necessary."""
        # Check if fastfetch is available
        if not self._is_fastfetch_installed():
            # Try to install it
            if not self._install_fastfetch():
                return self._get_fallback_output()
        
        try:
            # Run fastfetch with settings optimized for our sidebar width
            result = subprocess.run(
                ['fastfetch', '--logo-width', '12', '--logo-padding-top', '0',
                 '--logo-padding-left', '0', '--logo-padding-right', '1'],
                capture_output=True, text=True, timeout=5
            )
            
            if result.returncode == 0 and result.stdout.strip():
                # Strip ANSI color codes for clean monochrome output
                output = re.sub(r'\x1b\[[0-9;]*m', '', result.stdout)
                # Also strip any other escape sequences
                output = re.sub(r'\x1b\[[\?0-9;]*[a-zA-Z]', '', output)
                return output.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            pass
        
        return self._get_fallback_output()
    
    def _is_fastfetch_installed(self) -> bool:
        """Check if fastfetch is installed."""
        try:
            result = subprocess.run(['which', 'fastfetch'], 
                                   capture_output=True, text=True, timeout=2)
            return result.returncode == 0
        except Exception:
            return False
    
    def _install_fastfetch(self) -> bool:
        """Try to install fastfetch based on distro."""
        family = self.distro.family.value.lower()
        
        try:
            if family == 'arch':
                # Fastfetch is in official repos
                result = subprocess.run(
                    ['pkexec', 'pacman', '-S', '--noconfirm', 'fastfetch'],
                    capture_output=True, text=True, timeout=60
                )
                return result.returncode == 0
            elif family == 'debian':
                result = subprocess.run(
                    ['pkexec', 'apt', 'install', '-y', 'fastfetch'],
                    capture_output=True, text=True, timeout=120
                )
                return result.returncode == 0
            elif family == 'fedora':
                result = subprocess.run(
                    ['pkexec', 'dnf', 'install', '-y', 'fastfetch'],
                    capture_output=True, text=True, timeout=120
                )
                return result.returncode == 0
            elif family == 'opensuse':
                result = subprocess.run(
                    ['pkexec', 'zypper', 'install', '-y', 'fastfetch'],
                    capture_output=True, text=True, timeout=120
                )
                return result.returncode == 0
        except Exception:
            pass
        
        return False
    
    def _get_fallback_output(self) -> str:
        """Generate fallback output if fastfetch unavailable."""
        user = os.environ.get('USER', 'user')
        hostname = platform.node()
        
        lines = [
            f"{user}@{hostname}",
            "-" * (len(user) + len(hostname) + 1),
            f"OS: {self.distro.name}",
            f"Kernel: {platform.release()}",
            f"Uptime: {self._get_uptime()}",
            f"Shell: {self._get_shell()}",
            f"DE: {self.desktop.display_name}",
            "",
            f"CPU: {self.hardware.cpu_model[:35]}...",
            f"Memory: {self._format_memory()}",
            "",
            "(Install fastfetch for full info)",
        ]
        
        return "\n".join(lines)
    
    def _get_uptime(self) -> str:
        """Get system uptime."""
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.read().split()[0])
            
            days = int(uptime_seconds // 86400)
            hours = int((uptime_seconds % 86400) // 3600)
            minutes = int((uptime_seconds % 3600) // 60)
            
            if days > 0:
                return f"{days}d {hours}h {minutes}m"
            elif hours > 0:
                return f"{hours}h {minutes}m"
            else:
                return f"{minutes}m"
        except Exception:
            return "Unknown"
    
    def _get_shell(self) -> str:
        """Get current shell."""
        shell = os.environ.get('SHELL', '/bin/bash')
        return os.path.basename(shell)
    
    def _format_memory(self) -> str:
        """Format memory usage."""
        try:
            with open('/proc/meminfo', 'r') as f:
                meminfo = {}
                for line in f:
                    parts = line.split(':')
                    if len(parts) == 2:
                        key = parts[0].strip()
                        value = int(parts[1].strip().split()[0])
                        meminfo[key] = value
            
            total = meminfo.get('MemTotal', 0)
            available = meminfo.get('MemAvailable', 0)
            used = total - available
            
            total_gb = round(total / 1024 / 1024, 1)
            used_gb = round(used / 1024 / 1024, 1)
            
            return f"{used_gb}GB / {total_gb}GB"
        except Exception:
            return "Unknown"


# For backward compatibility
TuxFetchPanel = TuxFetchSidebar
TuxFetchCompact = TuxFetchSidebar
