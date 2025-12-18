#!/usr/bin/env python3
"""
Tux Assistant - Main Entry Point

A comprehensive system configuration and automation toolkit for Linux.

Copyright (c) 2025 Christopher Dorrell. Licensed under GPL-3.0.

Usage:
    ./tux.py          # Launch GUI
    ./tux.py --help   # Show help
    ./tux.py --version # Show version
"""

import sys
import os

# Add the script directory to path for imports
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.insert(0, script_dir)


def check_dependencies():
    """Check if required dependencies are installed."""
    missing = []
    
    try:
        import gi
        gi.require_version('Gtk', '4.0')
        gi.require_version('Adw', '1')
        from gi.repository import Gtk, Adw
    except (ImportError, ValueError) as e:
        missing.append(f"GTK4/libadwaita: {e}")
    
    if missing:
        print("Missing dependencies:")
        for dep in missing:
            print(f"  - {dep}")
        print("\nInstall with:")
        print("  Arch:   sudo pacman -S gtk4 libadwaita python-gobject")
        print("  Fedora: sudo dnf install gtk4 libadwaita python3-gobject")
        print("  Debian: sudo apt install libgtk-4-1 libadwaita-1-0 python3-gi gir1.2-gtk-4.0 gir1.2-adw-1")
        sys.exit(1)


def main():
    """Main entry point."""
    # Handle --help and --version before loading GTK
    if len(sys.argv) > 1:
        if sys.argv[1] in ('--help', '-h'):
            print(__doc__)
            print("Options:")
            print("  --help, -h      Show this help message")
            print("  --version, -v   Show version information")
            print("  --check         Check system and dependencies")
            print("  --browser [URL] Launch Tux Browser (Firefox)")
            sys.exit(0)
        
        elif sys.argv[1] in ('--version', '-v'):
            from tux import __version__
            print(f"Tux Assistant v{__version__}")
            sys.exit(0)
        
        elif sys.argv[1] == '--check':
            check_dependencies()
            
            from tux.core import get_distro, get_desktop
            
            distro = get_distro()
            desktop = get_desktop()
            
            print("System Check")
            print("=" * 40)
            print(f"Distribution:    {distro.name}")
            print(f"Family:          {distro.family.value}")
            print(f"Package Manager: {distro.package_manager}")
            print(f"Desktop:         {desktop.display_name}")
            print(f"Display Server:  {desktop.session_type}")
            print("=" * 40)
            print("All checks passed!")
            sys.exit(0)
        
        elif sys.argv[1] == '--browser':
            # Launch Tux Browser directly (Firefox with managed profile)
            import subprocess
            
            profile_dir = os.path.expanduser("~/.config/tux-assistant/firefox-profile")
            os.makedirs(profile_dir, exist_ok=True)
            
            # Create user.js if it doesn't exist
            user_js_path = os.path.join(profile_dir, "user.js")
            if not os.path.exists(user_js_path):
                user_js_content = '''// Tux Browser - Firefox Profile Preferences
user_pref("browser.startup.homepage", "https://start.duckduckgo.com");
user_pref("privacy.trackingprotection.enabled", true);
user_pref("dom.security.https_only_mode", true);
user_pref("toolkit.telemetry.enabled", false);
user_pref("extensions.pocket.enabled", false);
user_pref("browser.shell.checkDefaultBrowser", false);
'''
                with open(user_js_path, 'w') as f:
                    f.write(user_js_content)
            
            # Find Firefox
            firefox = None
            for name in ['firefox', 'firefox-esr', 'firefox-bin']:
                result = subprocess.run(['which', name], capture_output=True, text=True)
                if result.returncode == 0:
                    firefox = result.stdout.strip()
                    break
            
            if not firefox:
                print("Error: Firefox not found. Please install Firefox.")
                sys.exit(1)
            
            # Build command - no --class, let Firefox use its default identity
            # This ensures GNOME/KDE match it to firefox.desktop for proper icon
            cmd = [firefox, '--profile', profile_dir]
            
            # Add URL if provided
            if len(sys.argv) > 2:
                cmd.append(sys.argv[2])
            
            # Launch Firefox
            subprocess.Popen(cmd, start_new_session=True)
            sys.exit(0)
    
    # Check dependencies before launching
    check_dependencies()
    
    # Launch the application
    from tux import main as app_main
    sys.exit(app_main())


if __name__ == "__main__":
    main()
