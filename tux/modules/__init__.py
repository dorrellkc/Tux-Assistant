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
from . import system_maintenance
from . import backup_restore
from . import gaming
from . import hardware_manager
from . import desktop_enhancements
from . import software_center
from . import networking
from . import setup_tools
from . import developer_tools

from . import tux_tunes
from . import help_learning
from . import placeholders  # placeholder registrations (if any remain)

__all__ = [
    'ModuleRegistry',
    'ModuleInfo',
    'ModuleCategory',
    'register_module',
]
