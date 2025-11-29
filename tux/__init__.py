"""
Tux Assistant

A comprehensive GTK4/Libadwaita system configuration and management 
application for Linux distributions.

Supports: Arch, Fedora, Debian/Ubuntu, openSUSE and derivatives.

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
"""

__version__ = "5.0.0"
__version_info__ = (5, 0, 0)
__author__ = "Christopher Dorrell"
__email__ = "dorrellkc@gmail.com"
__app_name__ = "Tux Assistant"
__app_id__ = "com.tuxassistant.app"

from .app import TuxAssistantApp, main

__all__ = ['TuxAssistantApp', 'main', '__version__', '__version_info__', '__app_name__']
