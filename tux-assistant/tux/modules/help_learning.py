"""
Tux Assistant - Help and Learning Module

Interactive tutorials, troubleshooter, and guided help for Linux beginners.

Copyright (c) 2025 Christopher Dorrell. Licensed under GPL-3.0.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio

import subprocess
import os
from dataclasses import dataclass
from typing import Optional, Callable
from enum import Enum

from ..modules.registry import register_module, ModuleCategory
from ..core.distro import get_distro, DistroFamily


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class Tutorial:
    """A step-by-step tutorial."""
    id: str
    title: str
    description: str
    icon: str
    steps: list[dict]  # Each step: {title, content, action_label?, action_func?}
    category: str


@dataclass  
class TroubleshootItem:
    """A troubleshooting topic."""
    id: str
    title: str
    description: str
    icon: str
    checks: list[dict]  # Each check: {name, check_func, fix_label?, fix_func?, info?}


@dataclass
class QuickTask:
    """A common task shortcut."""
    id: str
    title: str  # "I want to..."
    icon: str
    action: str  # Module to open or action to take
    description: str


# =============================================================================
# Tutorial Content
# =============================================================================

TUTORIALS = [
    Tutorial(
        id="terminal_basics",
        title="Terminal Basics",
        description="Learn to use the command line - it's not as scary as it looks!",
        icon="utilities-terminal-symbolic",
        category="basics",
        steps=[
            {
                "title": "What is the Terminal?",
                "content": """The terminal (also called command line or console) is a text-based way to talk to your computer.

Think of it like texting your computer instead of clicking buttons. Many tasks are actually FASTER in the terminal once you learn the basics!

Don't worry - you can't break your computer by typing wrong commands. The worst that usually happens is an error message."""
            },
            {
                "title": "Opening the Terminal",
                "content": """There are several ways to open a terminal:

• Press Ctrl + Alt + T (works on most systems)
• Search for "Terminal" in your app menu
• Right-click on your desktop and select "Open Terminal"

Try opening a terminal now!""",
                "action_label": "Open Terminal",
                "action_id": "open_terminal"
            },
            {
                "title": "Your First Commands",
                "content": """Try typing these commands (press Enter after each):

pwd - Shows where you are (Print Working Directory)
ls - Lists files in the current folder
cd Desktop - Moves to your Desktop folder
cd .. - Goes back up one folder

These commands are safe and just show you information."""
            },
            {
                "title": "Getting Help",
                "content": """Almost every command has built-in help:

command --help - Shows help for that command
man command - Opens the full manual (press 'q' to exit)

For example, try: ls --help

The Linux community is also very helpful - searching "how to [task] linux terminal" usually gives great results!"""
            },
            {
                "title": "Essential Commands",
                "content": """Here are the most useful commands:

FILE OPERATIONS:
• cp file1 file2 - Copy a file
• mv file1 file2 - Move/rename a file
• rm file - Delete a file (careful!)
• mkdir folder - Create a folder

VIEWING FILES:
• cat file - Show file contents
• less file - View file with scrolling (q to quit)
• head file - Show first 10 lines
• tail file - Show last 10 lines

SEARCHING:
• find . -name "*.txt" - Find files by name
• grep "word" file - Search inside files"""
            },
            {
                "title": "You're Ready!",
                "content": """Congratulations! You now know the terminal basics.

Remember:
• Tab key auto-completes commands and filenames
• Up arrow recalls previous commands
• Ctrl+C cancels a running command
• Ctrl+L clears the screen

The more you practice, the more natural it becomes. Many Linux users actually prefer the terminal for everyday tasks!"""
            }
        ]
    ),
    Tutorial(
        id="software_install",
        title="Installing Software",
        description="Learn the different ways to install apps on Linux",
        icon="system-software-install-symbolic",
        category="basics",
        steps=[
            {
                "title": "Software on Linux",
                "content": """Linux handles software differently than Windows:

Instead of downloading .exe files from websites, Linux uses PACKAGE MANAGERS - like an app store that's built into your system.

This is actually MORE secure because:
• All software comes from trusted sources
• Updates happen automatically
• No hunting for downloads on sketchy websites"""
            },
            {
                "title": "Your Package Manager",
                "content": """Your system uses a package manager based on your distribution:

• Arch/Manjaro: pacman
• Ubuntu/Debian/Mint: apt  
• Fedora: dnf
• openSUSE: zypper

Tux Assistant handles this automatically - you don't need to remember which one you have!""",
            },
            {
                "title": "Graphical Software Centers",
                "content": """The easiest way to install software is through graphical tools:

• GNOME Software (Ubuntu, Fedora)
• Discover (KDE/Plasma)
• Pamac (Manjaro)
• Software Center in Tux Assistant

These work just like phone app stores - search, click install, done!""",
                "action_label": "Open Software Center",
                "action_id": "open_software_center"
            },
            {
                "title": "Flatpak - Universal Apps",
                "content": """Flatpak is a newer way to install apps that works on ANY Linux distribution.

Benefits:
• Apps are sandboxed (more secure)
• Always get the latest version
• Works the same everywhere

Flathub.org has thousands of Flatpak apps. Tux Assistant can install Flatpak support for you if needed."""
            },
            {
                "title": "Installing from Terminal",
                "content": """Sometimes it's faster to install via terminal:

Arch: sudo pacman -S firefox
Ubuntu: sudo apt install firefox
Fedora: sudo dnf install firefox
openSUSE: sudo zypper install firefox

The 'sudo' means "run as administrator" - you'll enter your password.

Tux Assistant handles all this for you automatically!"""
            }
        ]
    ),
    Tutorial(
        id="file_management",
        title="Files &amp; Folders",
        description="Navigate your files like a pro",
        icon="system-file-manager-symbolic",
        category="basics",
        steps=[
            {
                "title": "Linux File Structure",
                "content": """Linux organizes files differently than Windows:

/ (root) - The top of everything (like C:\\ on Windows)
/home/username - Your personal files (like C:\\Users\\You)
/etc - System settings
/usr - Installed programs
/tmp - Temporary files

Your home folder is where you'll spend most of your time!"""
            },
            {
                "title": "Your Home Folder",
                "content": """Your home folder (/home/yourname) contains:

• Desktop - Your desktop files
• Documents - Your documents
• Downloads - Downloaded files
• Pictures - Your images
• Music - Your music
• Videos - Your videos

This is similar to Windows! The file manager shows these by default.""",
                "action_label": "Open File Manager",
                "action_id": "open_files"
            },
            {
                "title": "Hidden Files",
                "content": """Files starting with a dot (.) are hidden by default.

Examples:
• .config - App settings
• .local - App data
• .bashrc - Terminal settings

To see hidden files:
• In file manager: Press Ctrl+H
• In terminal: ls -a

These are hidden to reduce clutter, not for security."""
            },
            {
                "title": "Permissions",
                "content": """Linux has a permission system for files:

• Read (r) - Can view the file
• Write (w) - Can modify the file  
• Execute (x) - Can run the file (for programs)

If you can't access a file, it's usually a permission issue.

Most files in your home folder you have full access to. System files require administrator (sudo) access."""
            }
        ]
    ),
    Tutorial(
        id="updates_security",
        title="Updates &amp; Security",
        description="Keep your system safe and up-to-date",
        icon="system-software-update-symbolic",
        category="basics",
        steps=[
            {
                "title": "Why Updates Matter",
                "content": """Updates are important for:

• Security fixes - Patch vulnerabilities
• Bug fixes - Fix problems
• New features - Get improvements

Linux makes updates easy - everything updates together, not each app separately like Windows!"""
            },
            {
                "title": "Updating Your System",
                "content": """You can update through:

1. Tux Assistant → System Maintenance → Updates
2. Your system's Software Center
3. Terminal (for advanced users)

We recommend updating at least once a week, or whenever you see the notification.""",
                "action_label": "Check for Updates",
                "action_id": "open_updates"
            },
            {
                "title": "Linux Security",
                "content": """Good news: Linux is inherently more secure than Windows!

Why Linux is secure:
• No .exe files from random websites
• Software comes from trusted repositories
• Strong permission system
• Open source = many eyes reviewing code
• Smaller target (fewer viruses written for Linux)

You generally DON'T need antivirus on Linux for personal use."""
            },
            {
                "title": "Best Practices",
                "content": """Stay safe with these habits:

✓ Keep your system updated
✓ Only install from trusted sources
✓ Use strong passwords
✓ Don't run random scripts from the internet
✓ Back up important files regularly

Tux Assistant's Backup module makes backups easy!"""
            }
        ]
    ),
]

# =============================================================================
# Troubleshooter Content
# =============================================================================

TROUBLESHOOT_ITEMS = [
    TroubleshootItem(
        id="no_sound",
        title="No Sound",
        description="Audio not working? Let's fix it.",
        icon="audio-volume-muted-symbolic",
        checks=[
            {
                "name": "Check if audio is muted",
                "info": "Look for a mute icon in your system tray, or press the mute key on your keyboard.",
                "check_id": "check_muted"
            },
            {
                "name": "Check volume level",
                "info": "Make sure volume isn't set to 0%.",
                "action_label": "Open Sound Settings",
                "action_id": "open_sound_settings"
            },
            {
                "name": "Check output device",
                "info": "Make sure the correct speakers/headphones are selected.",
                "action_label": "Open Hardware Manager",
                "action_id": "open_hardware_audio"
            },
            {
                "name": "Restart PulseAudio/PipeWire",
                "info": "Sometimes the audio service needs a restart.",
                "action_label": "Restart Audio",
                "action_id": "restart_audio"
            },
            {
                "name": "Check if speakers are connected",
                "info": "For external speakers, make sure they're plugged in and turned on.",
            }
        ]
    ),
    TroubleshootItem(
        id="no_wifi",
        title="WiFi Not Working",
        description="Can't connect to WiFi? Let's diagnose.",
        icon="network-wireless-offline-symbolic",
        checks=[
            {
                "name": "Check if WiFi is enabled",
                "info": "Look for airplane mode or a WiFi toggle switch.",
                "action_label": "Open WiFi Settings",
                "action_id": "open_wifi_settings"
            },
            {
                "name": "Check if you're in range",
                "info": "Make sure you're close enough to your router.",
            },
            {
                "name": "Verify password",
                "info": "WiFi passwords are case-sensitive. Try forgetting the network and reconnecting.",
            },
            {
                "name": "Restart NetworkManager",
                "info": "This often fixes connection issues.",
                "action_label": "Restart Network",
                "action_id": "restart_network"
            },
            {
                "name": "Check for WiFi driver",
                "info": "Some WiFi cards need additional drivers.",
                "action_label": "Check Drivers",
                "action_id": "check_drivers"
            }
        ]
    ),
    TroubleshootItem(
        id="no_print",
        title="Printer Not Working",
        description="Can't print? Let's troubleshoot.",
        icon="printer-error-symbolic",
        checks=[
            {
                "name": "Check if printer is on and connected",
                "info": "Make sure the printer is powered on and connected via USB or network.",
            },
            {
                "name": "Check if CUPS is running",
                "info": "CUPS is the printing system. It needs to be running.",
                "action_label": "Open Hardware Manager",
                "action_id": "open_hardware_printers"
            },
            {
                "name": "Check print queue",
                "info": "Jobs might be stuck in the queue.",
                "action_label": "Open Print Queue",
                "action_id": "open_print_queue"
            },
            {
                "name": "Reinstall printer",
                "info": "Sometimes removing and re-adding the printer fixes issues.",
                "action_label": "Configure Printers",
                "action_id": "configure_printers"
            }
        ]
    ),
    TroubleshootItem(
        id="slow_system",
        title="System Running Slow",
        description="Computer feeling sluggish? Let's speed it up.",
        icon="utilities-system-monitor-symbolic",
        checks=[
            {
                "name": "Check what's using resources",
                "info": "Open System Monitor to see what programs are using CPU/RAM.",
                "action_label": "Open System Monitor",
                "action_id": "open_system_monitor"
            },
            {
                "name": "Check disk space",
                "info": "Low disk space can cause slowdowns.",
                "action_label": "Open System Maintenance",
                "action_id": "open_maintenance"
            },
            {
                "name": "Check startup programs",
                "info": "Too many programs starting at boot slows things down.",
                "action_label": "Manage Startup Apps",
                "action_id": "open_startup"
            },
            {
                "name": "Clean up system",
                "info": "Clear caches and temporary files.",
                "action_label": "Run Cleanup",
                "action_id": "run_cleanup"
            },
            {
                "name": "Restart your computer",
                "info": "When in doubt, restart! It clears temporary issues.",
            }
        ]
    ),
    TroubleshootItem(
        id="app_crash",
        title="App Keeps Crashing",
        description="Application crashing or freezing?",
        icon="dialog-error-symbolic",
        checks=[
            {
                "name": "Update the application",
                "info": "Crashes are often fixed in newer versions.",
                "action_label": "Check Updates",
                "action_id": "open_updates"
            },
            {
                "name": "Try reinstalling",
                "info": "A fresh install can fix corrupted files.",
            },
            {
                "name": "Check for enough RAM",
                "info": "The app might need more memory than available.",
                "action_label": "Check Resources",
                "action_id": "open_system_monitor"
            },
            {
                "name": "Look for error messages",
                "info": "Run the app from terminal to see error output.",
                "action_label": "Open Terminal",
                "action_id": "open_terminal"
            },
            {
                "name": "Try Flatpak version",
                "info": "Flatpak apps are sandboxed and may be more stable.",
            }
        ]
    ),
    TroubleshootItem(
        id="bluetooth_issues",
        title="Bluetooth Problems",
        description="Bluetooth device not connecting?",
        icon="bluetooth-disabled-symbolic",
        checks=[
            {
                "name": "Check if Bluetooth is enabled",
                "info": "Make sure Bluetooth is turned on in your system.",
                "action_label": "Open Hardware Manager",
                "action_id": "open_hardware_bluetooth"
            },
            {
                "name": "Put device in pairing mode",
                "info": "The Bluetooth device needs to be discoverable. Check its manual.",
            },
            {
                "name": "Remove and re-pair",
                "info": "Try removing the device and pairing again from scratch.",
            },
            {
                "name": "Restart Bluetooth service",
                "info": "This can fix connection issues.",
                "action_label": "Restart Bluetooth",
                "action_id": "restart_bluetooth"
            },
            {
                "name": "Check distance",
                "info": "Bluetooth typically works within 30 feet (10 meters).",
            }
        ]
    ),
]

# =============================================================================
# Quick Tasks ("I want to...")
# =============================================================================

QUICK_TASKS = [
    QuickTask("play_dvd", "Play a DVD", "media-optical-dvd-symbolic", "software_center:media", 
              "Install VLC or other media player with DVD support"),
    QuickTask("connect_wifi", "Connect to WiFi", "network-wireless-symbolic", "networking_simple",
              "Open WiFi settings to connect to a network"),
    QuickTask("print_doc", "Print a document", "printer-symbolic", "hardware_manager",
              "Set up and configure printers"),
    QuickTask("install_app", "Install an application", "system-software-install-symbolic", "software_center",
              "Browse and install software"),
    QuickTask("play_games", "Play games", "applications-games-symbolic", "gaming",
              "Set up Steam, Lutris, and gaming tools"),
    QuickTask("backup_files", "Back up my files", "drive-harddisk-symbolic", "backup_restore",
              "Create backups of important files"),
    QuickTask("share_files", "Share files on network", "folder-publicshare-symbolic", "networking_simple",
              "Set up file sharing with other computers"),
    QuickTask("customize_look", "Customize my desktop", "preferences-desktop-wallpaper-symbolic", "desktop_enhancements",
              "Themes, icons, fonts, and more"),
    QuickTask("update_system", "Update my system", "system-software-update-symbolic", "system_maintenance",
              "Check for and install updates"),
    QuickTask("fix_sound", "Fix audio problems", "audio-volume-muted-symbolic", "troubleshoot_no_sound",
              "Troubleshoot sound issues"),
]


# =============================================================================
# Help and Learning Module
# =============================================================================

@register_module(
    id="help_learning",
    name="Help and Learning",
    description="Tutorials, troubleshooting, and guided help",
    icon="help-browser-symbolic",
    category=ModuleCategory.SYSTEM,
    order=2  # Second - help for new users
)
class HelpLearningPage(Adw.NavigationPage):
    """Help and learning center for Linux beginners."""
    
    def __init__(self, window: 'LinuxToolkitWindow'):
        super().__init__(title="Help and Learning")
        
        self.window = window
        self.distro = get_distro()
        
        self.build_ui()
    
    def build_ui(self):
        """Build the help UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        toolbar_view.set_content(scrolled)
        
        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_margin_top(20)
        clamp.set_margin_bottom(20)
        clamp.set_margin_start(20)
        clamp.set_margin_end(20)
        scrolled.set_child(clamp)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        clamp.set_child(content)
        
        # Welcome banner
        content.append(self._create_welcome_section())
        
        # Quick Tasks - "I want to..."
        content.append(self._create_quick_tasks_section())
        
        # Troubleshooter
        content.append(self._create_troubleshooter_section())
        
        # Tutorials
        content.append(self._create_tutorials_section())
        
        # Linux Basics
        content.append(self._create_basics_section())
    
    def _create_welcome_section(self) -> Gtk.Widget:
        """Create welcome banner."""
        group = Adw.PreferencesGroup()
        group.set_title("Welcome to Linux!")
        group.set_description("Don't worry, we'll help you figure things out. Linux is different from Windows, but once you get the hang of it, you might never go back!")
        
        return group
    
    def _create_quick_tasks_section(self) -> Gtk.Widget:
        """Create 'I want to...' quick tasks section."""
        group = Adw.PreferencesGroup()
        group.set_title("I Want To...")
        group.set_description("Quick shortcuts to common tasks")
        
        for task in QUICK_TASKS[:6]:  # Show first 6
            row = Adw.ActionRow()
            row.set_title(task.title)
            row.set_subtitle(task.description)
            row.add_prefix(Gtk.Image.new_from_icon_name(task.icon))
            row.set_activatable(True)
            row.connect("activated", self._on_quick_task, task)
            row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            group.add(row)
        
        # Show more button
        more_row = Adw.ActionRow()
        more_row.set_title("More tasks...")
        more_row.set_activatable(True)
        more_row.connect("activated", self._on_show_all_tasks)
        more_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        group.add(more_row)
        
        return group
    
    def _create_troubleshooter_section(self) -> Gtk.Widget:
        """Create troubleshooter section."""
        group = Adw.PreferencesGroup()
        group.set_title("Troubleshooter")
        group.set_description("Having a problem? Let's fix it together.")
        
        for item in TROUBLESHOOT_ITEMS:
            row = Adw.ActionRow()
            row.set_title(item.title)
            row.set_subtitle(item.description)
            row.add_prefix(Gtk.Image.new_from_icon_name(item.icon))
            row.set_activatable(True)
            row.connect("activated", self._on_troubleshoot, item)
            row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            group.add(row)
        
        return group
    
    def _create_tutorials_section(self) -> Gtk.Widget:
        """Create tutorials section."""
        group = Adw.PreferencesGroup()
        group.set_title("Learn Linux")
        group.set_description("Step-by-step tutorials for beginners")
        
        for tutorial in TUTORIALS:
            row = Adw.ActionRow()
            row.set_title(tutorial.title)
            row.set_subtitle(tutorial.description)
            row.add_prefix(Gtk.Image.new_from_icon_name(tutorial.icon))
            row.set_activatable(True)
            row.connect("activated", self._on_tutorial, tutorial)
            row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            group.add(row)
        
        return group
    
    def _create_basics_section(self) -> Gtk.Widget:
        """Create Linux basics quick reference."""
        group = Adw.PreferencesGroup()
        group.set_title("Quick Reference")
        group.set_description("Handy shortcuts and tips")
        
        # Keyboard shortcuts
        shortcuts_row = Adw.ExpanderRow()
        shortcuts_row.set_title("Keyboard Shortcuts")
        shortcuts_row.set_subtitle("Essential shortcuts to know")
        shortcuts_row.add_prefix(Gtk.Image.new_from_icon_name("input-keyboard-symbolic"))
        
        shortcuts = [
            ("Ctrl + C", "Copy / Cancel command in terminal"),
            ("Ctrl + V", "Paste"),
            ("Ctrl + Z", "Undo"),
            ("Ctrl + Alt + T", "Open terminal"),
            ("Super (Windows key)", "Open app menu"),
            ("Alt + Tab", "Switch windows"),
            ("Alt + F4", "Close window"),
            ("Ctrl + Alt + Delete", "Log out / System menu"),
            ("Print Screen", "Take screenshot"),
        ]
        
        for key, desc in shortcuts:
            shortcut_row = Adw.ActionRow()
            shortcut_row.set_title(key)
            shortcut_row.set_subtitle(desc)
            shortcuts_row.add_row(shortcut_row)
        
        group.add(shortcuts_row)
        
        # Terminology
        terms_row = Adw.ExpanderRow()
        terms_row.set_title("Linux Terminology")
        terms_row.set_subtitle("What do these words mean?")
        terms_row.add_prefix(Gtk.Image.new_from_icon_name("accessories-dictionary-symbolic"))
        
        terms = [
            ("Distribution (Distro)", "A version of Linux, like Ubuntu, Fedora, or Arch"),
            ("Package", "A piece of software, ready to install"),
            ("Repository (Repo)", "A library of packages you can install from"),
            ("Terminal / Console", "Text-based interface for running commands"),
            ("Root", "The administrator account (like Admin on Windows)"),
            ("sudo", "Run a command as administrator"),
            ("Desktop Environment", "The look and feel (GNOME, KDE, XFCE)"),
            ("Home folder", "Your personal files (/home/username)"),
        ]
        
        for term, definition in terms:
            term_row = Adw.ActionRow()
            term_row.set_title(term)
            term_row.set_subtitle(definition)
            terms_row.add_row(term_row)
        
        group.add(terms_row)
        
        # Get help online
        help_row = Adw.ActionRow()
        help_row.set_title("Get Help Online")
        help_row.set_subtitle("Forums, wikis, and communities")
        help_row.add_prefix(Gtk.Image.new_from_icon_name("web-browser-symbolic"))
        help_row.set_activatable(True)
        help_row.connect("activated", self._on_online_help)
        help_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        group.add(help_row)
        
        return group
    
    # -------------------------------------------------------------------------
    # Event Handlers
    # -------------------------------------------------------------------------
    
    def _on_quick_task(self, row, task: QuickTask):
        """Handle quick task selection."""
        print(f"[Help] Quick task clicked: {task.title} -> {task.action}")
        if task.action.startswith("troubleshoot_"):
            # It's a troubleshoot item
            item_id = task.action.replace("troubleshoot_", "")
            for item in TROUBLESHOOT_ITEMS:
                if item.id == item_id:
                    self._show_troubleshooter(item)
                    return
        elif ":" in task.action:
            # Deep link: module:subcategory (e.g., software_center:media)
            self._navigate_deep(task.action)
        else:
            # It's a module - navigate to it
            self._navigate_to_module(task.action)
    
    def _on_show_all_tasks(self, row):
        """Show all quick tasks."""
        page = AllTasksPage(self.window, self)
        self.window.navigation_view.push(page)
    
    def _on_troubleshoot(self, row, item: TroubleshootItem):
        """Open troubleshooter for an item."""
        self._show_troubleshooter(item)
    
    def _show_troubleshooter(self, item: TroubleshootItem):
        """Show troubleshooter page."""
        page = TroubleshooterPage(self.window, item, self)
        self.window.navigation_view.push(page)
    
    def _on_tutorial(self, row, tutorial: Tutorial):
        """Open a tutorial."""
        page = TutorialPage(self.window, tutorial, self)
        self.window.navigation_view.push(page)
    
    def _on_online_help(self, row):
        """Show online help resources."""
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Online Help Resources",
            body="Here are some great places to get help:"
        )
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        
        resources = [
            ("Ask Ubuntu", "https://askubuntu.com"),
            ("Arch Wiki", "https://wiki.archlinux.org"),
            ("Linux Questions", "https://www.linuxquestions.org"),
            ("Reddit r/linux4noobs", "https://reddit.com/r/linux4noobs"),
            ("Stack Overflow", "https://stackoverflow.com"),
        ]
        
        for name, url in resources:
            btn = Gtk.Button(label=name)
            btn.connect("clicked", lambda b, u=url: subprocess.Popen(['xdg-open', u]))
            content.append(btn)
        
        dialog.set_extra_child(content)
        dialog.add_response("close", "Close")
        dialog.present()
    
    def _navigate_to_module(self, module_id: str):
        """Navigate to a module."""
        from ..modules.registry import ModuleRegistry
        
        modules = ModuleRegistry.get_all_modules()
        for mod in modules:
            if mod.id == module_id:
                try:
                    page = mod.page_class(self.window)
                    self.window.navigation_view.push(page)
                except Exception as e:
                    print(f"[Help] Error loading module '{module_id}': {e}")
                    self.window.show_toast(f"Error loading module: {e}")
                return
        
        print(f"[Help] Module '{module_id}' not found in registry")
        self.window.show_toast(f"Module '{module_id}' not found")
    
    def _navigate_deep(self, action: str):
        """Navigate to a module and then to a specific subcategory.
        
        Format: module_id:category_id (e.g., software_center:media)
        """
        parts = action.split(":", 1)
        if len(parts) != 2:
            self._navigate_to_module(action)
            return
        
        module_id, category_id = parts
        
        # Handle software_center deep links
        if module_id == "software_center":
            try:
                from .software_center import build_catalog, CategoryPage
                from ..core.distro import get_distro
                
                # Find the category
                catalog = build_catalog()
                category = None
                for cat in catalog:
                    if cat.id == category_id:
                        category = cat
                        break
                
                if category:
                    # Navigate directly to the category page
                    distro = get_distro()
                    page = CategoryPage(self.window, category, distro)
                    self.window.navigation_view.push(page)
                else:
                    print(f"[Help] Category '{category_id}' not found in software center")
                    self._navigate_to_module(module_id)
            except Exception as e:
                print(f"[Help] Error navigating to {action}: {e}")
                self._navigate_to_module(module_id)
        else:
            # For other modules, just navigate to the module
            self._navigate_to_module(module_id)
    
    def execute_action(self, action_id: str):
        """Execute a tutorial/troubleshooter action."""
        actions = {
            "open_terminal": lambda: subprocess.Popen(['x-terminal-emulator']) if subprocess.run(['which', 'x-terminal-emulator'], capture_output=True).returncode == 0 else subprocess.Popen(['gnome-terminal']) if subprocess.run(['which', 'gnome-terminal'], capture_output=True).returncode == 0 else subprocess.Popen(['konsole']),
            "open_files": lambda: subprocess.Popen(['xdg-open', os.path.expanduser('~')]),
            "open_software_center": lambda: self._navigate_to_module("software_center"),
            "open_updates": lambda: self._navigate_to_module("system_maintenance"),
            "open_sound_settings": lambda: self._open_settings("sound"),
            "open_wifi_settings": lambda: self._open_settings("wifi"),
            "open_system_monitor": lambda: self._open_system_monitor(),
            "open_maintenance": lambda: self._navigate_to_module("system_maintenance"),
            "open_startup": lambda: self._navigate_to_module("system_maintenance"),
            "open_hardware_audio": lambda: self._navigate_to_module("hardware_manager"),
            "open_hardware_printers": lambda: self._navigate_to_module("hardware_manager"),
            "open_hardware_bluetooth": lambda: self._navigate_to_module("hardware_manager"),
            "open_print_queue": lambda: subprocess.Popen(['system-config-printer']),
            "configure_printers": lambda: subprocess.Popen(['system-config-printer']),
            "restart_audio": lambda: self._restart_audio(),
            "restart_network": lambda: self._restart_network(),
            "restart_bluetooth": lambda: self._restart_bluetooth(),
            "check_drivers": lambda: self._navigate_to_module("setup_tools"),
            "run_cleanup": lambda: self._navigate_to_module("system_maintenance"),
        }
        
        if action_id in actions:
            try:
                actions[action_id]()
            except Exception as e:
                self.window.show_toast(f"Error: {str(e)}")
        else:
            self.window.show_toast(f"Unknown action: {action_id}")
    
    def _open_settings(self, section: str):
        """Open system settings."""
        try:
            subprocess.Popen(['gnome-control-center', section])
        except:
            try:
                subprocess.Popen(['systemsettings5'])
            except:
                self.window.show_toast("Could not open settings")
    
    def _open_system_monitor(self):
        """Open system monitor."""
        monitors = ['gnome-system-monitor', 'ksysguard', 'xfce4-taskmanager', 'htop']
        for mon in monitors:
            if subprocess.run(['which', mon], capture_output=True).returncode == 0:
                if mon == 'htop':
                    subprocess.Popen(['x-terminal-emulator', '-e', 'htop'])
                else:
                    subprocess.Popen([mon])
                return
        self.window.show_toast("No system monitor found")
    
    def _restart_audio(self):
        """Restart audio service."""
        # Try PipeWire first, then PulseAudio
        try:
            subprocess.run(['systemctl', '--user', 'restart', 'pipewire'], capture_output=True)
            subprocess.run(['systemctl', '--user', 'restart', 'pipewire-pulse'], capture_output=True)
            self.window.show_toast("Audio service restarted")
        except:
            try:
                subprocess.run(['pulseaudio', '-k'], capture_output=True)
                subprocess.run(['pulseaudio', '--start'], capture_output=True)
                self.window.show_toast("PulseAudio restarted")
            except:
                self.window.show_toast("Could not restart audio")
    
    def _restart_network(self):
        """Restart network service."""
        try:
            subprocess.run(['sudo', 'systemctl', 'restart', 'NetworkManager'], capture_output=True)
            self.window.show_toast("Network service restarted")
        except:
            self.window.show_toast("Could not restart network")
    
    def _restart_bluetooth(self):
        """Restart Bluetooth service."""
        try:
            subprocess.run(['sudo', 'systemctl', 'restart', 'bluetooth'], capture_output=True)
            self.window.show_toast("Bluetooth service restarted")
        except:
            self.window.show_toast("Could not restart Bluetooth")


# =============================================================================
# Sub-Pages
# =============================================================================

class TutorialPage(Adw.NavigationPage):
    """Page for displaying a tutorial."""
    
    def __init__(self, window, tutorial: Tutorial, help_page: HelpLearningPage):
        super().__init__(title=tutorial.title)
        
        self.window = window
        self.tutorial = tutorial
        self.help_page = help_page
        self.current_step = 0
        
        self.build_ui()
    
    def build_ui(self):
        """Build tutorial UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)
        
        # Main content
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        self.content_box.set_margin_top(20)
        self.content_box.set_margin_bottom(20)
        self.content_box.set_margin_start(20)
        self.content_box.set_margin_end(20)
        
        clamp = Adw.Clamp()
        clamp.set_maximum_size(700)
        clamp.set_child(self.content_box)
        
        toolbar_view.set_content(clamp)
        
        self._show_step(0)
    
    def _show_step(self, step_num: int):
        """Show a tutorial step."""
        # Clear previous content
        while child := self.content_box.get_first_child():
            self.content_box.remove(child)
        
        if step_num >= len(self.tutorial.steps):
            return
        
        step = self.tutorial.steps[step_num]
        self.current_step = step_num
        
        # Progress indicator
        progress_label = Gtk.Label()
        progress_label.set_markup(f"<small>Step {step_num + 1} of {len(self.tutorial.steps)}</small>")
        progress_label.add_css_class("dim-label")
        self.content_box.append(progress_label)
        
        # Progress bar
        progress = Gtk.ProgressBar()
        progress.set_fraction((step_num + 1) / len(self.tutorial.steps))
        self.content_box.append(progress)
        
        # Step title
        title_label = Gtk.Label()
        title_label.set_markup(f"<big><b>{step['title']}</b></big>")
        title_label.set_halign(Gtk.Align.START)
        title_label.set_margin_top(10)
        self.content_box.append(title_label)
        
        # Step content
        content_label = Gtk.Label()
        content_label.set_text(step['content'])
        content_label.set_wrap(True)
        content_label.set_halign(Gtk.Align.START)
        content_label.set_valign(Gtk.Align.START)
        content_label.set_vexpand(True)
        self.content_box.append(content_label)
        
        # Action button (if any)
        if 'action_label' in step:
            action_btn = Gtk.Button(label=step['action_label'])
            action_btn.add_css_class("suggested-action")
            action_btn.connect("clicked", lambda b: self.help_page.execute_action(step.get('action_id', '')))
            self.content_box.append(action_btn)
        
        # Navigation buttons
        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        nav_box.set_halign(Gtk.Align.END)
        nav_box.set_margin_top(20)
        
        if step_num > 0:
            prev_btn = Gtk.Button(label="Previous")
            prev_btn.connect("clicked", lambda b: self._show_step(step_num - 1))
            nav_box.append(prev_btn)
        
        if step_num < len(self.tutorial.steps) - 1:
            next_btn = Gtk.Button(label="Next")
            next_btn.add_css_class("suggested-action")
            next_btn.connect("clicked", lambda b: self._show_step(step_num + 1))
            nav_box.append(next_btn)
        else:
            done_btn = Gtk.Button(label="Done!")
            done_btn.add_css_class("suggested-action")
            done_btn.connect("clicked", lambda b: self.window.navigation_view.pop())
            nav_box.append(done_btn)
        
        self.content_box.append(nav_box)


class TroubleshooterPage(Adw.NavigationPage):
    """Page for troubleshooting a specific issue."""
    
    def __init__(self, window, item: TroubleshootItem, help_page: HelpLearningPage):
        super().__init__(title=item.title)
        
        self.window = window
        self.item = item
        self.help_page = help_page
        
        self.build_ui()
    
    def build_ui(self):
        """Build troubleshooter UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        toolbar_view.set_content(scrolled)
        
        clamp = Adw.Clamp()
        clamp.set_maximum_size(700)
        clamp.set_margin_top(20)
        clamp.set_margin_bottom(20)
        clamp.set_margin_start(20)
        clamp.set_margin_end(20)
        scrolled.set_child(clamp)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        clamp.set_child(content)
        
        # Header
        header_label = Gtk.Label()
        header_label.set_markup(f"<big>Let's troubleshoot: <b>{self.item.title}</b></big>")
        header_label.set_halign(Gtk.Align.START)
        content.append(header_label)
        
        desc_label = Gtk.Label()
        desc_label.set_text("Go through these checks one by one. Often the first few will solve the problem!")
        desc_label.set_wrap(True)
        desc_label.set_halign(Gtk.Align.START)
        desc_label.add_css_class("dim-label")
        content.append(desc_label)
        
        # Checks
        group = Adw.PreferencesGroup()
        group.set_title("Troubleshooting Steps")
        
        for i, check in enumerate(self.item.checks):
            row = Adw.ExpanderRow()
            row.set_title(f"{i + 1}. {check['name']}")
            row.add_prefix(Gtk.Image.new_from_icon_name("checkbox-symbolic"))
            
            # Info row
            info_row = Adw.ActionRow()
            info_row.set_title(check.get('info', ''))
            info_row.set_title_lines(5)
            row.add_row(info_row)
            
            # Action button if present
            if 'action_label' in check:
                action_row = Adw.ActionRow()
                action_btn = Gtk.Button(label=check['action_label'])
                action_btn.set_valign(Gtk.Align.CENTER)
                action_btn.add_css_class("suggested-action")
                action_btn.connect("clicked", lambda b, aid=check.get('action_id', ''): self.help_page.execute_action(aid))
                action_row.add_suffix(action_btn)
                row.add_row(action_row)
            
            group.add(row)
        
        content.append(group)
        
        # Still not working?
        still_group = Adw.PreferencesGroup()
        still_group.set_title("Still Not Working?")
        
        search_row = Adw.ActionRow()
        search_row.set_title("Search online for help")
        search_row.set_subtitle(f"Search: '{self.item.title} linux fix'")
        search_row.add_prefix(Gtk.Image.new_from_icon_name("web-browser-symbolic"))
        search_row.set_activatable(True)
        search_row.connect("activated", self._on_search_online)
        search_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        still_group.add(search_row)
        
        content.append(still_group)
    
    def _on_search_online(self, row):
        """Search online for help."""
        query = f"{self.item.title} linux fix".replace(" ", "+")
        subprocess.Popen(['xdg-open', f'https://duckduckgo.com/?q={query}'])


class AllTasksPage(Adw.NavigationPage):
    """Page showing all quick tasks."""
    
    def __init__(self, window, help_page: HelpLearningPage):
        super().__init__(title="All Tasks")
        
        self.window = window
        self.help_page = help_page
        
        self.build_ui()
    
    def build_ui(self):
        """Build UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        toolbar_view.set_content(scrolled)
        
        clamp = Adw.Clamp()
        clamp.set_maximum_size(700)
        clamp.set_margin_top(20)
        clamp.set_margin_bottom(20)
        clamp.set_margin_start(20)
        clamp.set_margin_end(20)
        scrolled.set_child(clamp)
        
        group = Adw.PreferencesGroup()
        group.set_title("I Want To...")
        group.set_description("Select what you want to do")
        
        for task in QUICK_TASKS:
            row = Adw.ActionRow()
            row.set_title(task.title)
            row.set_subtitle(task.description)
            row.add_prefix(Gtk.Image.new_from_icon_name(task.icon))
            row.set_activatable(True)
            row.connect("activated", lambda r, t=task: self._on_task(t))
            row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            group.add(row)
        
        clamp.set_child(group)
    
    def _on_task(self, task: QuickTask):
        """Handle task selection."""
        self.help_page._on_quick_task(None, task)
