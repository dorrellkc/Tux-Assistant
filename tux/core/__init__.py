"""
Tux Assistant - Core Module

Core functionality for distro detection, desktop detection,
command execution, and package management.

Copyright (c) 2025 Christopher Dorrell. Licensed under GPL-3.0.
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
    check_sudo_access,
    get_terminal_commands,
    find_terminal,
    run_in_terminal
)

from .packages import (
    Package,
    InstallResult,
    PackageManager,
    get_package_manager
)

from .hardware import (
    HardwareInfo,
    get_hardware_info,
    get_hardinfo2_package_name,
    is_aur_package,
    launch_hardinfo2,
    check_hardinfo2_available
)

from .logger import (
    setup_logging,
    get_logger,
    is_debug_enabled
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
    'get_terminal_commands', 'find_terminal', 'run_in_terminal',
    # Packages
    'Package', 'InstallResult', 'PackageManager', 'get_package_manager',
    # Hardware
    'HardwareInfo', 'get_hardware_info', 'get_hardinfo2_package_name',
    'is_aur_package', 'launch_hardinfo2', 'check_hardinfo2_available',
    # Logging
    'setup_logging', 'get_logger', 'is_debug_enabled'
]
