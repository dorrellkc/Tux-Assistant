"""
Module Registry - Dynamic module discovery and management

This module provides a registry system that automatically discovers
and loads modules from the modules directory. Modules can be added
or removed by simply adding/removing their folders.

Copyright (c) 2025 Christopher Dorrell. Licensed under GPL-3.0.
"""

import gi
gi.require_version('Gtk', '4.0')

from gi.repository import Gtk, Gio
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Type
import importlib
import os


# =============================================================================
# Icon Utilities - Cross-DE, Cross-Distro Icon Loading
# =============================================================================

def _get_bundled_icons_dir() -> Optional[str]:
    """Get the path to bundled icons directory."""
    # Try multiple locations
    candidates = [
        # Running from source
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'assets', 'icons'),
        # Installed to /opt
        '/opt/tux-assistant/assets/icons',
        # Installed to /usr/share
        '/usr/share/tux-assistant/assets/icons',
        # Local install
        os.path.expanduser('~/.local/share/tux-assistant/assets/icons'),
    ]
    
    for path in candidates:
        if os.path.isdir(path):
            return path
    return None


def get_icon_path(icon_name: str) -> Optional[str]:
    """
    Get the full path to a bundled icon file.
    
    Args:
        icon_name: Icon name (with or without tux- prefix, with or without .svg)
    
    Returns:
        Full path to the icon file, or None if not found
    """
    icons_dir = _get_bundled_icons_dir()
    if not icons_dir:
        return None
    
    # Normalize the icon name
    name = icon_name
    if not name.endswith('.svg'):
        name = name + '.svg'
    
    # Try with tux- prefix
    if not name.startswith('tux-'):
        tux_path = os.path.join(icons_dir, 'tux-' + name)
        if os.path.exists(tux_path):
            return tux_path
    
    # Try as-is
    direct_path = os.path.join(icons_dir, name)
    if os.path.exists(direct_path):
        return direct_path
    
    return None


def create_icon(icon_name: str, size: int = 16, fallback: str = "application-x-executable-symbolic") -> Gtk.Image:
    """
    Create a Gtk.Image using GTK's icon theme system.
    
    Uses new_from_icon_name() first which properly handles symbolic icon
    coloring for light/dark mode. Falls back to direct file loading for
    development/source installs where theme may not be registered.
    
    Args:
        icon_name: The icon name to load
        size: Icon size in pixels (default 16)
        fallback: Fallback icon name if primary not found
    
    Returns:
        Gtk.Image widget with the icon
    """
    # Normalize to use tux- prefix for our bundled icons
    if not icon_name.startswith('tux-'):
        icon_name = f'tux-{icon_name}'
    
    # Method 1: Use GTK icon theme (handles symbolic coloring for light/dark mode)
    # Our tux-icons theme is registered at app startup
    image = Gtk.Image.new_from_icon_name(icon_name)
    image.set_pixel_size(size)
    return image


def create_icon_simple(icon_name: str, size: int = 16) -> Gtk.Image:
    """
    Create a Gtk.Image using GTK's icon theme system.
    
    Uses new_from_icon_name() which properly handles symbolic icon
    coloring for light/dark mode. Our tux-icons theme is registered
    at app startup.
    
    Args:
        icon_name: The icon name (with or without tux- prefix)
        size: Icon size in pixels (default 16)
    
    Returns:
        Gtk.Image widget with the icon
    """
    # Normalize icon name to use tux- prefix
    if not icon_name.startswith('tux-'):
        icon_name = f'tux-{icon_name}'
    
    # Use GTK icon theme (handles symbolic coloring for light/dark mode)
    image = Gtk.Image.new_from_icon_name(icon_name)
    image.set_pixel_size(size)
    return image


class ModuleCategory(Enum):
    """Categories for organizing modules in the UI."""
    SETUP = "Setup and Configuration"
    MEDIA = "Media and Entertainment"
    NETWORK = "Network and Sharing"
    SYSTEM = "System and Maintenance"
    SERVER = "Server and Cloud"
    DEVELOPER = "Developer Tools"


@dataclass
class ModuleInfo:
    """Information about a registered module."""
    id: str
    name: str
    description: str
    icon: str
    category: ModuleCategory
    page_class: Optional[Type] = None  # The NavigationPage class for this module
    enabled: bool = True
    order: int = 100  # Lower numbers appear first
    
    # Optional: Callable that returns dynamic description based on system state
    description_func: Optional[Callable] = None
    
    def get_description(self, **kwargs) -> str:
        """Get description, optionally dynamic based on system state."""
        if self.description_func:
            return self.description_func(**kwargs)
        return self.description


class ModuleRegistry:
    """
    Central registry for all toolkit modules.
    
    Modules register themselves when imported, allowing for
    dynamic discovery and easy addition/removal of features.
    """
    
    _instance = None
    _modules: dict[str, ModuleInfo] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._modules = {}
        return cls._instance
    
    @classmethod
    def register(cls, module_info: ModuleInfo):
        """Register a module with the registry."""
        registry = cls()
        registry._modules[module_info.id] = module_info
    
    @classmethod
    def unregister(cls, module_id: str):
        """Unregister a module."""
        registry = cls()
        if module_id in registry._modules:
            del registry._modules[module_id]
    
    @classmethod
    def get_module(cls, module_id: str) -> Optional[ModuleInfo]:
        """Get a specific module by ID."""
        registry = cls()
        return registry._modules.get(module_id)
    
    @classmethod
    def get_modules_by_category(cls, category: ModuleCategory) -> list[ModuleInfo]:
        """Get all modules in a category, sorted by order."""
        registry = cls()
        modules = [
            m for m in registry._modules.values()
            if m.category == category and m.enabled
        ]
        return sorted(modules, key=lambda m: m.order)
    
    @classmethod
    def get_all_modules(cls) -> list[ModuleInfo]:
        """Get all registered modules, sorted by category and order."""
        registry = cls()
        return sorted(
            registry._modules.values(),
            key=lambda m: (m.category.value, m.order)
        )
    
    @classmethod
    def get_categories(cls) -> list[ModuleCategory]:
        """Get all categories that have at least one enabled module."""
        registry = cls()
        categories = set()
        for module in registry._modules.values():
            if module.enabled:
                categories.add(module.category)
        
        # Return in defined order
        return [c for c in ModuleCategory if c in categories]
    
    @classmethod
    def discover_modules(cls):
        """
        Discover and import all modules in the modules directory.
        
        Each module should have a register() function or register
        itself on import.
        """
        modules_dir = os.path.dirname(os.path.abspath(__file__))
        
        for item in os.listdir(modules_dir):
            # Skip private files and non-Python files
            if item.startswith('_') or item.startswith('.'):
                continue
            
            # Skip the registry itself and __pycache__
            if item in ('registry.py', '__pycache__', '__init__.py'):
                continue
            
            # Handle both .py files and directories
            if item.endswith('.py'):
                module_name = item[:-3]
            elif os.path.isdir(os.path.join(modules_dir, item)):
                module_name = item
            else:
                continue
            
            try:
                # Import the module - it should register itself
                importlib.import_module(f'.{module_name}', package='tux.modules')
            except Exception as e:
                import traceback
                print(f"Warning: Failed to load module '{module_name}': {e}")
                traceback.print_exc()


# Convenience decorator for registering modules
def register_module(
    id: str,
    name: str,
    description: str,
    icon: str,
    category: ModuleCategory,
    order: int = 100,
    enabled: bool = True,
    description_func: Optional[Callable] = None
):
    """
    Decorator to register a NavigationPage class as a module.
    
    Usage:
        @register_module(
            id="my_module",
            name="My Module",
            description="Does something cool",
            icon="cool-icon-symbolic",
            category=ModuleCategory.SETUP
        )
        class MyModulePage(Adw.NavigationPage):
            ...
    """
    def decorator(cls):
        module_info = ModuleInfo(
            id=id,
            name=name,
            description=description,
            icon=icon,
            category=category,
            page_class=cls,
            order=order,
            enabled=enabled,
            description_func=description_func
        )
        ModuleRegistry.register(module_info)
        return cls
    return decorator
