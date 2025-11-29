"""
Tux Assistant - Fun Facts Module

Entertainment and education while you wait!
Displays rotating facts about Tux Assistant, Linux myths/facts,
distro unity, and fun Linux history.

"Well done, not medium rare" - Christopher

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

import random
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum
from gi.repository import Gtk, Adw, GLib, Pango


# =============================================================================
# Data Models
# =============================================================================

class FactCategory(Enum):
    """Categories of fun facts."""
    APP_FEATURE = "app_feature"
    LINUX_MYTH = "linux_myth"
    DISTRO_UNITY = "distro_unity"
    LINUX_FUN = "linux_fun"
    LINUX_HISTORY = "linux_history"
    TUX_TIPS = "tux_tips"


@dataclass
class FunFact:
    """A single fun fact."""
    category: FactCategory
    content: str
    title: Optional[str] = None
    myth: Optional[str] = None  # For myth-busting facts
    module: Optional[str] = None  # Related module name
    icon: str = "💡"


# =============================================================================
# Facts Database
# =============================================================================

# App Features - What Tux Assistant can do
APP_FEATURE_FACTS = [
    FunFact(
        category=FactCategory.APP_FEATURE,
        title="Media Server Setup",
        content="Tux Assistant can set up Plex, Jellyfin, or Emby media servers and automatically configure your drives with the right permissions!",
        module="media_server",
        icon="🎬"
    ),
    FunFact(
        category=FactCategory.APP_FEATURE,
        title="Desktop Customization",
        content="Customize your desktop with themes, icons, extensions, and tweaks for GNOME, KDE, XFCE, Cinnamon, and MATE - all from one place!",
        module="desktop_enhancements",
        icon="🎨"
    ),
    FunFact(
        category=FactCategory.APP_FEATURE,
        title="Self-Hosted Cloud",
        content="Replace Google Drive with your own Nextcloud server! Tux Assistant handles the entire setup including SSL certificates and dynamic DNS.",
        module="nextcloud_setup",
        icon="☁️"
    ),
    FunFact(
        category=FactCategory.APP_FEATURE,
        title="Network File Sharing",
        content="Set up Samba shares to easily share files between Linux, Windows, and Mac computers on your network.",
        module="networking",
        icon="🔗"
    ),
    FunFact(
        category=FactCategory.APP_FEATURE,
        title="Software Made Easy",
        content="Install popular apps like browsers, media players, office suites, and development tools with just a few clicks!",
        module="software_center",
        icon="📦"
    ),
    FunFact(
        category=FactCategory.APP_FEATURE,
        title="Multi-Distro Support",
        content="Tux Assistant works on Arch, Debian, Ubuntu, Fedora, openSUSE, and dozens of their derivatives!",
        icon="🐧"
    ),
    FunFact(
        category=FactCategory.APP_FEATURE,
        title="Package Source Management",
        content="Enable Flatpak, Snap, AUR helpers, RPM Fusion, and other repositories without touching config files.",
        module="package_sources",
        icon="📚"
    ),
    FunFact(
        category=FactCategory.APP_FEATURE,
        title="System Setup Tools",
        content="Configure system settings, manage services, and set up your Linux system just the way you like it.",
        module="setup_tools",
        icon="🔧"
    ),
    FunFact(
        category=FactCategory.APP_FEATURE,
        title="ISO Creator",
        content="Create custom bootable ISOs to back up your system or create your own Linux distribution!",
        module="iso_creator",
        icon="💿"
    ),
    FunFact(
        category=FactCategory.APP_FEATURE,
        title="QR Code Sharing",
        content="When you set up a Samba share, Tux Assistant can generate a QR code for easy mobile device connection!",
        module="networking",
        icon="📱"
    ),
    FunFact(
        category=FactCategory.APP_FEATURE,
        title="Automatic Drive Detection",
        content="The Media Server module automatically detects your external drives and sets up permissions for your media server.",
        module="media_server",
        icon="💾"
    ),
    FunFact(
        category=FactCategory.APP_FEATURE,
        title="Five Desktop Environments",
        content="GNOME, KDE Plasma, XFCE, Cinnamon, and MATE all get full customization support with desktop-specific tweaks!",
        module="desktop_enhancements",
        icon="🖥️"
    ),
]

# Linux Myths vs Facts
LINUX_MYTH_FACTS = [
    FunFact(
        category=FactCategory.LINUX_MYTH,
        myth="Linux is only for programmers and hackers",
        content="Modern distros like Linux Mint, Pop!_OS, and Zorin OS are designed for everyday users. If you can use Windows, you can use Linux!",
        icon="🔓"
    ),
    FunFact(
        category=FactCategory.LINUX_MYTH,
        myth="You need to use the terminal for everything",
        content="Most tasks have GUI tools now. Apps like Tux Assistant exist specifically to avoid terminal commands. The terminal is powerful but optional!",
        icon="🖱️"
    ),
    FunFact(
        category=FactCategory.LINUX_MYTH,
        myth="Linux can't run games",
        content="Steam's Proton compatibility layer lets you play thousands of Windows games on Linux. The Steam Deck runs Linux and it's a gaming powerhouse!",
        icon="🎮"
    ),
    FunFact(
        category=FactCategory.LINUX_MYTH,
        myth="Linux has no software",
        content="LibreOffice, GIMP, Firefox, Chrome, Spotify, Discord, VS Code, OBS Studio, VLC... most apps you need are available and often free!",
        icon="📱"
    ),
    FunFact(
        category=FactCategory.LINUX_MYTH,
        myth="Linux is hard to install",
        content="Modern Linux installers are often easier than Windows! Many distros can be installed in under 15 minutes with just a few clicks.",
        icon="⚡"
    ),
    FunFact(
        category=FactCategory.LINUX_MYTH,
        myth="You can't use Microsoft Office on Linux",
        content="Microsoft Office works through the web browser, and LibreOffice handles most Office documents perfectly. Wine can even run the desktop apps!",
        icon="📄"
    ),
    FunFact(
        category=FactCategory.LINUX_MYTH,
        myth="Linux doesn't support hardware",
        content="Linux supports more hardware than ever! Most devices work out of the box. Even NVIDIA has started releasing open-source drivers.",
        icon="🔌"
    ),
    FunFact(
        category=FactCategory.LINUX_MYTH,
        myth="Linux is just for servers",
        content="While Linux dominates servers, it's also great for desktops! It's fast, secure, doesn't spy on you, and runs great on older hardware.",
        icon="💻"
    ),
    FunFact(
        category=FactCategory.LINUX_MYTH,
        myth="All Linux distros are the same",
        content="Distros differ in package managers, release cycles, default apps, and philosophies. That's why tools like Tux Assistant help bridge the gaps!",
        icon="🌈"
    ),
    FunFact(
        category=FactCategory.LINUX_MYTH,
        myth="Linux updates break everything",
        content="Rolling releases like Arch are stable when you update regularly. LTS releases like Ubuntu are rock-solid for years. Pick what suits you!",
        icon="🔄"
    ),
    FunFact(
        category=FactCategory.LINUX_MYTH,
        myth="You need to compile everything from source",
        content="Package managers handle installation for you. It's usually just one command or click - easier than hunting for .exe files online!",
        icon="📦"
    ),
    FunFact(
        category=FactCategory.LINUX_MYTH,
        myth="Linux has an ugly interface",
        content="Modern desktops like KDE Plasma and GNOME are beautiful! With themes and customization, Linux can look better than Windows or macOS.",
        icon="✨"
    ),
]

# Distro Unity Facts
DISTRO_UNITY_FACTS = [
    FunFact(
        category=FactCategory.DISTRO_UNITY,
        content="Arch, Debian, Fedora, openSUSE - different families, same Tux Assistant experience. One tool for all your Linux needs!",
        icon="🤝"
    ),
    FunFact(
        category=FactCategory.DISTRO_UNITY,
        content="Whether you use pacman, apt, dnf, or zypper - Tux Assistant speaks your package manager's language fluently.",
        icon="🗣️"
    ),
    FunFact(
        category=FactCategory.DISTRO_UNITY,
        content="GNOME, KDE, XFCE, Cinnamon, MATE - five desktop environments, one unified experience with Tux Assistant.",
        icon="🖥️"
    ),
    FunFact(
        category=FactCategory.DISTRO_UNITY,
        content="One app, many distros. That's the Tux Assistant promise. Your skills transfer between distributions!",
        icon="🐧"
    ),
    FunFact(
        category=FactCategory.DISTRO_UNITY,
        content="Linux Mint, Pop!_OS, Manjaro, EndeavourOS - whatever derivative you choose, Tux Assistant has you covered.",
        icon="🛡️"
    ),
    FunFact(
        category=FactCategory.DISTRO_UNITY,
        content="The Linux community is stronger together. Tux Assistant helps unite users across all distributions.",
        icon="💪"
    ),
    FunFact(
        category=FactCategory.DISTRO_UNITY,
        content="Switching distros? Your Tux Assistant knowledge comes with you. Same interface, same features, new home.",
        icon="🏠"
    ),
    FunFact(
        category=FactCategory.DISTRO_UNITY,
        content="From Ubuntu newbies to Arch veterans - Tux Assistant adapts to your distro while keeping things consistent.",
        icon="🎯"
    ),
]

# Fun Linux History Facts
LINUX_HISTORY_FACTS = [
    FunFact(
        category=FactCategory.LINUX_HISTORY,
        content="Linus Torvalds created Linux in 1991 as a hobby project. He famously said it would 'never be big and professional.'",
        icon="📜"
    ),
    FunFact(
        category=FactCategory.LINUX_HISTORY,
        content="The name 'Linux' was chosen by Ari Lemmke, the FTP server admin who hosted it. Linus wanted to call it 'Freax'!",
        icon="😄"
    ),
    FunFact(
        category=FactCategory.LINUX_HISTORY,
        content="Tux the penguin became the Linux mascot because Linus Torvalds was reportedly bitten by a penguin at a zoo in Australia!",
        icon="🐧"
    ),
    FunFact(
        category=FactCategory.LINUX_HISTORY,
        content="The first Linux kernel was just 10,000 lines of code. Today's kernel has over 30 million lines!",
        icon="📈"
    ),
    FunFact(
        category=FactCategory.LINUX_HISTORY,
        content="Linux was announced on August 25, 1991, with Linus's famous Usenet post: 'I'm doing a (free) operating system (just a hobby, won't be big and professional).'",
        icon="📅"
    ),
    FunFact(
        category=FactCategory.LINUX_HISTORY,
        content="The first graphical Linux distribution was Yggdrasil Linux, released in December 1992.",
        icon="🖼️"
    ),
    FunFact(
        category=FactCategory.LINUX_HISTORY,
        content="Red Hat was founded in 1993 and became the first billion-dollar open-source company.",
        icon="🎩"
    ),
    FunFact(
        category=FactCategory.LINUX_HISTORY,
        content="Ubuntu launched in 2004 with the mission to make Linux accessible to everyone. Its name means 'humanity to others' in Zulu.",
        icon="🌍"
    ),
    FunFact(
        category=FactCategory.LINUX_HISTORY,
        content="Debian, named after founder Ian Murdock and his wife Debra, has been continuously developed since 1993.",
        icon="💎"
    ),
]

# General Linux Fun Facts
LINUX_FUN_FACTS = [
    FunFact(
        category=FactCategory.LINUX_FUN,
        content="Android, Chrome OS, and most web servers run on Linux. You probably use Linux every day without knowing it!",
        icon="📱"
    ),
    FunFact(
        category=FactCategory.LINUX_FUN,
        content="The International Space Station runs on Linux. It's literally out of this world reliable!",
        icon="🚀"
    ),
    FunFact(
        category=FactCategory.LINUX_FUN,
        content="100% of the world's top 500 supercomputers run Linux. When you need serious power, you need Linux.",
        icon="🖥️"
    ),
    FunFact(
        category=FactCategory.LINUX_FUN,
        content="The Large Hadron Collider at CERN runs on Linux. It helps discover particles like the Higgs boson!",
        icon="⚛️"
    ),
    FunFact(
        category=FactCategory.LINUX_FUN,
        content="Every Tesla car runs Linux. Your next road trip might be powered by the penguin!",
        icon="🚗"
    ),
    FunFact(
        category=FactCategory.LINUX_FUN,
        content="NASA's Ingenuity helicopter on Mars runs Linux. The penguin has conquered another planet!",
        icon="🚁"
    ),
    FunFact(
        category=FactCategory.LINUX_FUN,
        content="The New York Stock Exchange runs on Linux. Trillions of dollars flow through systems powered by the penguin!",
        icon="📊"
    ),
    FunFact(
        category=FactCategory.LINUX_FUN,
        content="Google, Facebook, Amazon, and Netflix all run on Linux servers. The internet runs on Linux!",
        icon="🌐"
    ),
    FunFact(
        category=FactCategory.LINUX_FUN,
        content="The steam locomotive emoji was added to Unicode partly because of Steam's support for Linux gaming! 🚂",
        icon="🎮"
    ),
    FunFact(
        category=FactCategory.LINUX_FUN,
        content="Linux can run on almost anything - from supercomputers to smart refrigerators to tiny microcontrollers!",
        icon="🔬"
    ),
    FunFact(
        category=FactCategory.LINUX_FUN,
        content="The Linux kernel receives contributions from thousands of developers at companies like Google, Microsoft, and Intel.",
        icon="👥"
    ),
    FunFact(
        category=FactCategory.LINUX_FUN,
        content="Microsoft loves Linux! They contribute to the kernel, run Linux in Azure, and even ship WSL with Windows.",
        icon="💙"
    ),
    FunFact(
        category=FactCategory.LINUX_FUN,
        content="There are over 600 active Linux distributions. That's a lot of choice - or freedom, as we like to call it!",
        icon="🌈"
    ),
    FunFact(
        category=FactCategory.LINUX_FUN,
        content="Linux is completely free and open source. You can read, modify, and share the entire operating system!",
        icon="🆓"
    ),
]

# Tux Assistant Tips
TUX_TIPS_FACTS = [
    FunFact(
        category=FactCategory.TUX_TIPS,
        title="Tip",
        content="You can run 'tux-assistant' from any terminal to launch the app quickly!",
        icon="💡"
    ),
    FunFact(
        category=FactCategory.TUX_TIPS,
        title="Tip",
        content="Tux Assistant automatically detects your distro and desktop environment on startup.",
        icon="💡"
    ),
    FunFact(
        category=FactCategory.TUX_TIPS,
        title="Tip",
        content="All changes requiring admin privileges will prompt for your password - nothing happens without your approval!",
        icon="🔐"
    ),
    FunFact(
        category=FactCategory.TUX_TIPS,
        title="Tip",
        content="Having issues? Try running from terminal to see detailed error messages.",
        icon="🔍"
    ),
    FunFact(
        category=FactCategory.TUX_TIPS,
        title="Tip",
        content="Tux Assistant respects your privacy - no telemetry, no tracking, no data collection. Ever.",
        icon="🛡️"
    ),
    FunFact(
        category=FactCategory.TUX_TIPS,
        title="Tip",
        content="To uninstall Tux Assistant, run 'sudo ./install.sh --uninstall' from the original directory.",
        icon="📝"
    ),
]


# =============================================================================
# Facts Manager
# =============================================================================

class FunFactsManager:
    """Manages the fun facts database and rotation."""
    
    def __init__(self):
        self._all_facts: List[FunFact] = []
        self._shown_facts: set = set()
        self._load_facts()
    
    def _load_facts(self):
        """Load all facts from built-in database and user file."""
        # Load built-in facts
        self._all_facts = (
            APP_FEATURE_FACTS +
            LINUX_MYTH_FACTS +
            DISTRO_UNITY_FACTS +
            LINUX_HISTORY_FACTS +
            LINUX_FUN_FACTS +
            TUX_TIPS_FACTS
        )
        
        # Try to load user-added facts
        user_facts_path = Path.home() / ".config" / "tux-assistant" / "fun_facts.json"
        if user_facts_path.exists():
            try:
                with open(user_facts_path, 'r') as f:
                    user_data = json.load(f)
                    for fact_data in user_data.get('facts', []):
                        self._all_facts.append(FunFact(
                            category=FactCategory(fact_data.get('category', 'linux_fun')),
                            content=fact_data.get('content', ''),
                            title=fact_data.get('title'),
                            myth=fact_data.get('myth'),
                            icon=fact_data.get('icon', '💡')
                        ))
            except Exception:
                pass  # Silently ignore user facts errors
    
    def get_random_fact(self, category: Optional[FactCategory] = None) -> FunFact:
        """Get a random fact, avoiding recently shown ones."""
        # Filter by category if specified
        if category:
            available = [f for f in self._all_facts if f.category == category]
        else:
            available = self._all_facts.copy()
        
        # Filter out recently shown
        unshown = [f for f in available if id(f) not in self._shown_facts]
        
        # Reset if we've shown everything
        if not unshown:
            self._shown_facts.clear()
            unshown = available
        
        # Pick a random fact
        fact = random.choice(unshown)
        self._shown_facts.add(id(fact))
        
        return fact
    
    def get_fact_count(self) -> int:
        """Get total number of facts."""
        return len(self._all_facts)
    
    def get_category_count(self, category: FactCategory) -> int:
        """Get number of facts in a category."""
        return len([f for f in self._all_facts if f.category == category])


# =============================================================================
# GTK Widgets
# =============================================================================

class FunFactBox(Gtk.Box):
    """A widget that displays a single fun fact."""
    
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        
        self.add_css_class("card")
        self.set_margin_top(12)
        self.set_margin_bottom(12)
        self.set_margin_start(12)
        self.set_margin_end(12)
        
        # Inner padding
        inner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        inner.set_margin_top(16)
        inner.set_margin_bottom(16)
        inner.set_margin_start(16)
        inner.set_margin_end(16)
        self.append(inner)
        
        # Header with icon and title
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        inner.append(header)
        
        self.icon_label = Gtk.Label()
        self.icon_label.add_css_class("title-2")
        header.append(self.icon_label)
        
        self.title_label = Gtk.Label()
        self.title_label.add_css_class("title-4")
        self.title_label.set_halign(Gtk.Align.START)
        header.append(self.title_label)
        
        # Myth label (for myth-busting facts)
        self.myth_label = Gtk.Label()
        self.myth_label.add_css_class("dim-label")
        self.myth_label.set_wrap(True)
        self.myth_label.set_xalign(0)
        self.myth_label.set_visible(False)
        inner.append(self.myth_label)
        
        # Main content
        self.content_label = Gtk.Label()
        self.content_label.set_wrap(True)
        self.content_label.set_xalign(0)
        self.content_label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        inner.append(self.content_label)
    
    def set_fact(self, fact: FunFact):
        """Display a fact in the widget."""
        self.icon_label.set_text(fact.icon)
        
        # Set title
        if fact.title:
            self.title_label.set_text(fact.title)
        elif fact.myth:
            self.title_label.set_text("Myth Busted!")
        elif fact.category == FactCategory.DISTRO_UNITY:
            self.title_label.set_text("Distro Unity")
        elif fact.category == FactCategory.LINUX_HISTORY:
            self.title_label.set_text("Linux History")
        elif fact.category == FactCategory.LINUX_FUN:
            self.title_label.set_text("Did You Know?")
        else:
            self.title_label.set_text("Did You Know?")
        
        # Show myth if present
        if fact.myth:
            self.myth_label.set_text(f"❌ MYTH: \"{fact.myth}\"")
            self.myth_label.set_visible(True)
            self.content_label.set_text(f"✅ FACT: {fact.content}")
        else:
            self.myth_label.set_visible(False)
            self.content_label.set_text(fact.content)


class RotatingFunFactWidget(Gtk.Box):
    """
    A widget that displays rotating fun facts.
    Use this in any long-running operation dialog.
    """
    
    def __init__(self, rotation_interval: int = 8000):
        """
        Initialize the rotating facts widget.
        
        Args:
            rotation_interval: Time in milliseconds between fact changes (default 8 seconds)
        """
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        
        self.manager = FunFactsManager()
        self.rotation_interval = rotation_interval
        self._timer_id: Optional[int] = None
        
        # Create the fact display box
        self.fact_box = FunFactBox()
        self.append(self.fact_box)
        
        # Show first fact immediately
        self._show_next_fact()
        
        # Connect to map/unmap signals to start/stop rotation
        self.connect("map", self._on_map)
        self.connect("unmap", self._on_unmap)
    
    def _on_map(self, widget):
        """Start rotation when widget becomes visible."""
        self.start_rotation()
    
    def _on_unmap(self, widget):
        """Stop rotation when widget is hidden."""
        self.stop_rotation()
    
    def _show_next_fact(self):
        """Display the next random fact."""
        fact = self.manager.get_random_fact()
        self.fact_box.set_fact(fact)
    
    def start_rotation(self):
        """Start rotating facts."""
        if self._timer_id is None:
            self._timer_id = GLib.timeout_add(self.rotation_interval, self._on_timer)
    
    def stop_rotation(self):
        """Stop rotating facts."""
        if self._timer_id is not None:
            GLib.source_remove(self._timer_id)
            self._timer_id = None
    
    def _on_timer(self) -> bool:
        """Timer callback to rotate facts."""
        self._show_next_fact()
        return True  # Keep timer running


class LongOperationDialog(Adw.Dialog):
    """
    A dialog for long-running operations with progress and fun facts.
    Use this for network scans, large file operations, etc.
    """
    
    def __init__(
        self,
        title: str = "Working...",
        description: str = "This may take several minutes. Please be patient!",
        show_progress: bool = True,
        cancelable: bool = True
    ):
        super().__init__()
        
        self.set_title(title)
        self.set_content_width(500)
        self.set_content_height(400)
        self.set_can_close(cancelable)
        
        self._cancelled = False
        self._on_cancel_callback = None
        
        self._build_ui(title, description, show_progress, cancelable)
    
    def _build_ui(self, title: str, description: str, show_progress: bool, cancelable: bool):
        """Build the dialog UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        toolbar_view.add_top_bar(header)
        
        # Main content
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_top(20)
        content.set_margin_bottom(20)
        content.set_margin_start(20)
        content.set_margin_end(20)
        toolbar_view.set_content(content)
        
        # Title
        title_label = Gtk.Label(label=title)
        title_label.add_css_class("title-2")
        content.append(title_label)
        
        # Description
        desc_label = Gtk.Label(label=description)
        desc_label.add_css_class("dim-label")
        desc_label.set_wrap(True)
        content.append(desc_label)
        
        # Progress bar
        if show_progress:
            self.progress_bar = Gtk.ProgressBar()
            self.progress_bar.set_show_text(True)
            self.progress_bar.set_margin_top(8)
            content.append(self.progress_bar)
            
            # Start pulsing
            self._pulse_timer = GLib.timeout_add(100, self._pulse_progress)
        else:
            self.progress_bar = None
            self._pulse_timer = None
        
        # Status label
        self.status_label = Gtk.Label(label="Starting...")
        self.status_label.add_css_class("caption")
        self.status_label.set_margin_top(4)
        content.append(self.status_label)
        
        # Fun facts widget
        self.fun_facts = RotatingFunFactWidget(rotation_interval=8000)
        self.fun_facts.set_vexpand(True)
        content.append(self.fun_facts)
        
        # Cancel button
        if cancelable:
            cancel_btn = Gtk.Button(label="Cancel")
            cancel_btn.add_css_class("pill")
            cancel_btn.set_halign(Gtk.Align.CENTER)
            cancel_btn.connect("clicked", self._on_cancel_clicked)
            content.append(cancel_btn)
            self.cancel_button = cancel_btn
    
    def _pulse_progress(self) -> bool:
        """Pulse the progress bar."""
        if self.progress_bar:
            self.progress_bar.pulse()
        return True
    
    def _on_cancel_clicked(self, button):
        """Handle cancel button click."""
        self._cancelled = True
        if self._on_cancel_callback:
            self._on_cancel_callback()
        self.close()
    
    def set_on_cancel(self, callback):
        """Set callback for cancel button."""
        self._on_cancel_callback = callback
    
    def is_cancelled(self) -> bool:
        """Check if operation was cancelled."""
        return self._cancelled
    
    def set_progress(self, fraction: float, text: Optional[str] = None):
        """Set progress bar value (0.0 to 1.0)."""
        if self.progress_bar:
            # Stop pulsing if we're setting actual progress
            if self._pulse_timer and fraction > 0:
                GLib.source_remove(self._pulse_timer)
                self._pulse_timer = None
            
            self.progress_bar.set_fraction(fraction)
            if text:
                self.progress_bar.set_text(text)
    
    def set_status(self, status: str):
        """Set status text."""
        self.status_label.set_text(status)
    
    def complete(self, message: str = "Complete!"):
        """Mark operation as complete."""
        self.fun_facts.stop_rotation()
        
        if self._pulse_timer:
            GLib.source_remove(self._pulse_timer)
            self._pulse_timer = None
        
        if self.progress_bar:
            self.progress_bar.set_fraction(1.0)
            self.progress_bar.set_text(message)
        
        self.status_label.set_text(message)
        self.set_can_close(True)
        
        if hasattr(self, 'cancel_button'):
            self.cancel_button.set_label("Close")


# =============================================================================
# Convenience Functions
# =============================================================================

def get_random_fact() -> FunFact:
    """Get a random fun fact (convenience function)."""
    manager = FunFactsManager()
    return manager.get_random_fact()


def create_waiting_dialog(
    title: str = "Please Wait",
    description: str = "This operation may take several minutes. Enjoy some fun facts while you wait!",
    cancelable: bool = True
) -> LongOperationDialog:
    """
    Create a waiting dialog with fun facts.
    
    Args:
        title: Dialog title
        description: Description text
        cancelable: Whether user can cancel
    
    Returns:
        LongOperationDialog instance
    """
    return LongOperationDialog(
        title=title,
        description=description,
        show_progress=True,
        cancelable=cancelable
    )
