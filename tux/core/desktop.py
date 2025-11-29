"""
Tux Assistant - Desktop Environment Detection

Detects the current desktop environment and display server.

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
"""

import os
import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DesktopEnv(Enum):
    """Known desktop environments."""
    KDE = "kde"
    GNOME = "gnome"
    XFCE = "xfce"
    CINNAMON = "cinnamon"
    MATE = "mate"
    LXQT = "lxqt"
    LXDE = "lxde"
    BUDGIE = "budgie"
    DEEPIN = "deepin"
    PANTHEON = "pantheon"
    ENLIGHTENMENT = "enlightenment"
    I3 = "i3"
    SWAY = "sway"
    HYPRLAND = "hyprland"
    UNKNOWN = "unknown"


class DisplayServer(Enum):
    """Display server types."""
    X11 = "x11"
    WAYLAND = "wayland"
    UNKNOWN = "unknown"


# Desktop environment detection patterns
DE_DETECTION = {
    DesktopEnv.KDE: {
        'env_values': ['KDE', 'plasma', 'KDE-plasma'],
        'processes': ['plasmashell', 'kwin', 'kwin_x11', 'kwin_wayland'],
        'display_name': 'KDE Plasma'
    },
    DesktopEnv.GNOME: {
        'env_values': ['GNOME', 'GNOME-Classic', 'gnome', 'ubuntu:GNOME'],
        'processes': ['gnome-shell', 'gnome-session'],
        'display_name': 'GNOME'
    },
    DesktopEnv.XFCE: {
        'env_values': ['XFCE', 'xfce'],
        'processes': ['xfce4-session', 'xfdesktop', 'xfce4-panel'],
        'display_name': 'XFCE'
    },
    DesktopEnv.CINNAMON: {
        'env_values': ['X-Cinnamon', 'Cinnamon'],
        'processes': ['cinnamon', 'cinnamon-session'],
        'display_name': 'Cinnamon'
    },
    DesktopEnv.MATE: {
        'env_values': ['MATE'],
        'processes': ['mate-session', 'mate-panel'],
        'display_name': 'MATE'
    },
    DesktopEnv.LXQT: {
        'env_values': ['LXQt'],
        'processes': ['lxqt-session', 'lxqt-panel'],
        'display_name': 'LXQt'
    },
    DesktopEnv.LXDE: {
        'env_values': ['LXDE'],
        'processes': ['lxsession', 'lxpanel'],
        'display_name': 'LXDE'
    },
    DesktopEnv.BUDGIE: {
        'env_values': ['Budgie', 'budgie-desktop', 'Budgie:GNOME'],
        'processes': ['budgie-panel', 'budgie-wm'],
        'display_name': 'Budgie'
    },
    DesktopEnv.DEEPIN: {
        'env_values': ['Deepin', 'DDE'],
        'processes': ['dde-desktop', 'dde-dock'],
        'display_name': 'Deepin'
    },
    DesktopEnv.PANTHEON: {
        'env_values': ['Pantheon'],
        'processes': ['gala', 'wingpanel'],
        'display_name': 'Pantheon'
    },
    DesktopEnv.I3: {
        'env_values': ['i3'],
        'processes': ['i3'],
        'display_name': 'i3'
    },
    DesktopEnv.SWAY: {
        'env_values': ['sway'],
        'processes': ['sway'],
        'display_name': 'Sway'
    },
    DesktopEnv.HYPRLAND: {
        'env_values': ['Hyprland'],
        'processes': ['Hyprland'],
        'display_name': 'Hyprland'
    },
}


@dataclass
class DesktopInfo:
    """Information about the detected desktop environment."""
    desktop_env: DesktopEnv
    display_name: str
    display_server: DisplayServer
    session_type: str
    is_wayland: bool
    is_x11: bool
    
    @property
    def is_detected(self) -> bool:
        """Returns True if a desktop environment was detected."""
        return self.desktop_env != DesktopEnv.UNKNOWN


def get_running_processes() -> set[str]:
    """Get a set of currently running process names."""
    processes = set()
    try:
        result = subprocess.run(
            ['ps', '-A', '-o', 'comm='],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            processes = set(result.stdout.strip().split('\n'))
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return processes


def detect_display_server() -> tuple[DisplayServer, str]:
    """Detect the display server (X11 or Wayland)."""
    session_type = os.environ.get('XDG_SESSION_TYPE', '').lower()
    wayland_display = os.environ.get('WAYLAND_DISPLAY', '')
    display = os.environ.get('DISPLAY', '')
    
    if session_type == 'wayland' or wayland_display:
        return DisplayServer.WAYLAND, 'wayland'
    elif session_type == 'x11' or display:
        return DisplayServer.X11, 'x11'
    else:
        return DisplayServer.UNKNOWN, 'unknown'


def detect_from_environment() -> Optional[DesktopEnv]:
    """Try to detect desktop environment from environment variables."""
    # Check various environment variables
    env_vars = [
        'XDG_CURRENT_DESKTOP',
        'XDG_SESSION_DESKTOP', 
        'DESKTOP_SESSION',
        'GDMSESSION'
    ]
    
    for var in env_vars:
        value = os.environ.get(var, '')
        if value:
            # Check against known patterns
            for de, info in DE_DETECTION.items():
                for pattern in info['env_values']:
                    if pattern.lower() in value.lower():
                        return de
    
    return None


def detect_from_processes() -> Optional[DesktopEnv]:
    """Try to detect desktop environment from running processes."""
    running = get_running_processes()
    
    for de, info in DE_DETECTION.items():
        for process in info['processes']:
            if process in running:
                return de
    
    return None


def detect() -> DesktopInfo:
    """Detect the current desktop environment and display server."""
    # Try environment detection first (more reliable)
    desktop_env = detect_from_environment()
    
    # Fall back to process detection
    if desktop_env is None:
        desktop_env = detect_from_processes()
    
    # Still nothing? Unknown
    if desktop_env is None:
        desktop_env = DesktopEnv.UNKNOWN
    
    # Get display name
    if desktop_env in DE_DETECTION:
        display_name = DE_DETECTION[desktop_env]['display_name']
    else:
        display_name = 'Unknown'
    
    # Detect display server
    display_server, session_type = detect_display_server()
    
    return DesktopInfo(
        desktop_env=desktop_env,
        display_name=display_name,
        display_server=display_server,
        session_type=session_type,
        is_wayland=display_server == DisplayServer.WAYLAND,
        is_x11=display_server == DisplayServer.X11
    )


# Cached instance
_desktop_info: Optional[DesktopInfo] = None


def get_desktop() -> DesktopInfo:
    """Get cached desktop info (detects once, reuses after)."""
    global _desktop_info
    if _desktop_info is None:
        _desktop_info = detect()
    return _desktop_info


# Convenience functions
def get_desktop_env() -> DesktopEnv:
    """Get just the desktop environment."""
    return get_desktop().desktop_env


def is_kde() -> bool:
    """Check if running KDE."""
    return get_desktop_env() == DesktopEnv.KDE


def is_gnome() -> bool:
    """Check if running GNOME."""
    return get_desktop_env() == DesktopEnv.GNOME


def is_xfce() -> bool:
    """Check if running XFCE."""
    return get_desktop_env() == DesktopEnv.XFCE


def is_wayland() -> bool:
    """Check if running on Wayland."""
    return get_desktop().is_wayland


def is_x11() -> bool:
    """Check if running on X11."""
    return get_desktop().is_x11
