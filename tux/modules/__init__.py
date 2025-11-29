# Tux Assistant Modules
# Modules auto-register when imported via the registry system

from .registry import (
    ModuleRegistry,
    ModuleInfo,
    ModuleCategory,
    register_module,
)

# Explicit imports so all modules are guaranteed to be loaded when
# the application starts. This avoids relying solely on implicit
# discovery and ensures @register_module decorators are executed.
from . import desktop_enhancements
from . import software_center
from . import networking
from . import setup_tools
from . import iso_creator
from . import tux_tunes
from . import placeholders  # placeholder registrations (if any remain)

__all__ = [
    'ModuleRegistry',
    'ModuleInfo',
    'ModuleCategory',
    'register_module',
]
