#!/usr/bin/env python3
"""
Tux Tunes - Internet Radio Player
Standalone launcher script.

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
"""

import sys
import os

# Add tux-assistant root directory to path for imports
# This script is at: tux-assistant/tux/apps/tux_tunes/tux-tunes.py
# We need:          tux-assistant/
script_dir = os.path.dirname(os.path.abspath(__file__))  # tux_tunes/
apps_dir = os.path.dirname(script_dir)                    # apps/
tux_dir = os.path.dirname(apps_dir)                       # tux/
root_dir = os.path.dirname(tux_dir)                       # tux-assistant/

if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from tux.apps.tux_tunes.app import main

if __name__ == "__main__":
    sys.exit(main())
