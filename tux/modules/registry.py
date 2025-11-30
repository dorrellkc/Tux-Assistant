"""
Module Registry - Dynamic module discovery and management

This module provides a registry system that automatically discovers
and loads modules from the modules directory. Modules can be added
or removed by simply adding/removing their folders.

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable, Type
import importlib
import os


class ModuleCategory(Enum):
    """Categories for organizing modules in the UI."""
    SETUP = "Setup and Configuration"
    DEVELOPER = "Developer Tools"
    NETWORK = "Network and Sharing"
    SERVER = "Server and Cloud"
    MEDIA = "Media and Entertainment"
    SYSTEM = "System Tools"


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
