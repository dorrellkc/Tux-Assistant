"""
Tux Assistant - Core Module

Core functionality for distro detection, desktop detection,
command execution, and package management.

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
"""

from .distro import (
    DistroFamily,
    DistroInfo,
    get_distro,
    get_family,
    get_install_command,
    detect_aur_helper
)

from .desktop import (
    DesktopEnv,
    DisplayServer,
    DesktopInfo,
    get_desktop,
    get_desktop_env,
    is_kde,
    is_gnome,
    is_xfce,
    is_wayland,
    is_x11
)

from .commands import (
    CommandStatus,
    CommandResult,
    run,
    run_sudo,
    run_with_callback,
    command_exists,
    check_sudo_access
)

from .packages import (
    Package,
    InstallResult,
    PackageManager,
    get_package_manager
)

__all__ = [
    # Distro
    'DistroFamily', 'DistroInfo', 'get_distro', 'get_family',
    'get_install_command', 'detect_aur_helper',
    # Desktop
    'DesktopEnv', 'DisplayServer', 'DesktopInfo', 'get_desktop',
    'get_desktop_env', 'is_kde', 'is_gnome', 'is_xfce', 'is_wayland', 'is_x11',
    # Commands
    'CommandStatus', 'CommandResult', 'run', 'run_sudo',
    'run_with_callback', 'command_exists', 'check_sudo_access',
    # Packages
    'Package', 'InstallResult', 'PackageManager', 'get_package_manager'
]
