"""
Tux Assistant

A comprehensive GTK4/Libadwaita system configuration and management 
application for Linux distributions.

Supports: Arch, Fedora, Debian/Ubuntu, openSUSE and derivatives.

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
"""

import os

# Read version from VERSION file
_version_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'VERSION')
try:
    with open(_version_file, 'r') as f:
        __version__ = f.read().strip()
except Exception:
    __version__ = "0.0.0"

# Parse version info
_version_parts = __version__.split('.')
__version_info__ = tuple(int(x) for x in _version_parts[:3]) if len(_version_parts) >= 3 else (0, 0, 0)

__author__ = "Christopher Dorrell"
__email__ = "dorrellkc@gmail.com"
__app_name__ = "Tux Assistant"
__app_id__ = "com.tuxassistant.app"

from .app import TuxAssistantApp, main

__all__ = ['TuxAssistantApp', 'main', '__version__', '__version_info__', '__app_name__']
