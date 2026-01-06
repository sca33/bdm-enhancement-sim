"""Item type modules for BDM Enhancement Simulator.

This package contains all item type implementations. Each item type
is a separate subpackage that registers itself with the ItemTypeRegistry.

Import this module to auto-register all available item types.
"""

# Import all item type modules to trigger registration
from . import awakening
from . import totem
from . import rune
from . import relic
from . import accessory
