"""
Tux Assistant - Placeholder Modules

These are placeholder registrations for modules that are not yet implemented.
They will show "Coming soon!" when clicked.

To implement a module:
1. Create a new file (e.g., desktop_enhancements.py)
2. Use the @register_module decorator on your NavigationPage class
3. Remove the corresponding entry from this file

Copyright (c) 2025 Christopher Dorrell. Licensed under GPL-3.0.
"""
from .registry import ModuleRegistry, ModuleInfo, ModuleCategory

# System Snapshots - disabled for now; ISO Creator replaces this functionality.
# If you add a dedicated snapshots backend (e.g. Timeshift/Snapper),
# re-enable or re-register a proper page_class here.
# ModuleRegistry.register(ModuleInfo(
#     id="system_snapshots",
#     name="System Snapshots",
#     description="Create and restore system snapshots",
#     icon="drive-harddisk-symbolic",
#     category=ModuleCategory.SYSTEM,
#     order=10,
#     page_class=None,
# ))

# ISO Creator is now implemented in iso_creator.py
