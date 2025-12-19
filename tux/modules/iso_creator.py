"""
Tux Assistant - ISO Creator Module

Beautiful GTK4/Adwaita GUI wrapper for penguins-eggs.
Creates bootable live ISOs from your running system.

Powered by penguins-eggs - https://penguins-eggs.net
A professional and universal remastering tool by Piero Proietti

Features:
- One-click ISO creation from your running system
- Clone mode (with user data) or clean mode (without user data)
- Encrypted clone for secure backups
- Compression level options
- Calamares/Krill installer integration

Supported distributions (via penguins-eggs):
- Fedora, AlmaLinux, Rocky Linux
- Arch, Manjaro, EndeavourOS, Garuda
- Debian, Ubuntu, Linux Mint, Pop!_OS
- OpenSUSE, and many more derivatives

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

import os
import subprocess
import threading
import shutil
import pwd
import re
from pathlib import Path
from gi.repository import Gtk, Adw, GLib, Gio, Pango
from dataclasses import dataclass
from typing import Optional, Callable, List, Tuple
from enum import Enum

from ..core import get_distro, get_desktop, DistroFamily
from .registry import register_module, ModuleCategory


# =============================================================================
# Configuration Classes
# =============================================================================

class SnapshotMode(Enum):
    """Snapshot modes supported by penguins-eggs."""
    CLEAN = ("clean", "Clean ISO", "Remove all user data - perfect for distribution")
    CLONE = ("clone", "Clone", "Include user data unencrypted in the ISO")
    CRYPTED = ("cryptedclone", "Encrypted Clone", "Include user data encrypted (LUKS)")
    
    def __init__(self, flag: str, label: str, desc: str):
        self.flag = flag
        self.label = label
        self.desc = desc


class CompressionMode(Enum):
    """Compression options for penguins-eggs."""
    FAST = ("", "Fast (zstd)", "Quick compression, good for testing")
    PENDRIVE = ("--pendrive", "Pendrive Optimized", "zstd level 15 - optimized for USB")
    STANDARD = ("--standard", "Standard (xz)", "Better compression, takes longer")
    MAX = ("--max", "Maximum (xz-bcj)", "Best compression, slowest")
    
    def __init__(self, flag: str, label: str, desc: str):
        self.flag = flag
        self.label = label
        self.desc = desc


@dataclass
class EggsStatus:
    """Status information about penguins-eggs installation."""
    installed: bool = False
    version: str = ""
    configured: bool = False
    calamares_installed: bool = False


# =============================================================================
# Utility Functions  
# =============================================================================

def check_eggs_installed() -> EggsStatus:
    """Check if penguins-eggs is installed and configured."""
    status = EggsStatus()
    
    # Check if eggs command exists
    if not shutil.which('eggs'):
        return status
    
    status.installed = True
    
    # Get version
    try:
        result = subprocess.run(
            ['eggs', 'version'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            # Parse version from output like "penguins-eggs/25.9.18 linux-x64..."
            for line in result.stdout.split('\n'):
                if 'penguins-eggs' in line:
                    parts = line.split('/')
                    if len(parts) >= 2:
                        version_part = parts[1].split()[0]
                        status.version = version_part
                    break
    except:
        pass
    
    # Check if configured by running eggs status
    # If it runs without error and shows output, it's likely configured
    try:
        result = subprocess.run(
            ['eggs', 'status'],
            capture_output=True, text=True, timeout=10
        )
        # If eggs status runs successfully and produces output, consider it configured
        # Check for common indicators of proper configuration
        output_lower = result.stdout.lower()
        if result.returncode == 0:
            # Check for positive indicators
            if any(indicator in output_lower for indicator in [
                'eggs', 'kernel', 'initrd', 'live', 'distro', 
                'configuration', 'calamares', 'krill'
            ]):
                status.configured = True
            # Also consider configured if no errors and some output
            elif len(result.stdout.strip()) > 50:
                status.configured = True
        
        status.calamares_installed = 'calamares' in output_lower
    except:
        # If we can't check status, assume configured if installed
        status.configured = True
    
    return status


def get_real_user() -> Tuple[str, str]:
    """Get the real user (not root) and their home directory."""
    real_user = os.environ.get('SUDO_USER', os.environ.get('USER', 'root'))
    try:
        home = pwd.getpwnam(real_user).pw_dir
    except KeyError:
        home = os.path.expanduser('~')
    return real_user, home


# =============================================================================
# GTK4/Adwaita GUI
# =============================================================================

# TODO: ISO Creator is not ready for v1.0 - suppressed until fully working
# @register_module(
#     id="iso_creator",
#     name="ISO Creator", 
#     description="Create bootable ISO images from your system",
#     icon="media-optical-symbolic",
#     category=ModuleCategory.SYSTEM,
#     order=52  # Specialized tier
# )
class ISOCreatorPage(Adw.NavigationPage):
    """Main ISO Creator page - GUI for penguins-eggs."""
    
    def __init__(self, window):
        super().__init__(title="ISO Creator")
        
        self.window = window
        self.distro = get_distro()
        self.eggs_status = check_eggs_installed()
        self.process = None
        self.output_buffer = []
        self.pending_commands = []
        self.installation_failed = False
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the user interface."""
        # Main container
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header bar
        header = Adw.HeaderBar()
        
        # Refresh button
        refresh_btn = Gtk.Button(icon_name="view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh status")
        refresh_btn.connect("clicked", self._on_refresh_clicked)
        header.pack_end(refresh_btn)
        
        toolbar_view.add_top_bar(header)
        
        # Stack for different views
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        toolbar_view.set_content(self.stack)
        
        # Build different pages
        self._build_not_installed_page()
        self._build_setup_choice_page()
        self._build_guided_page()
        self._build_main_page()
        self._build_progress_page()
        
        # Show appropriate page
        self._update_view()
    
    def _build_not_installed_page(self):
        """Build the 'eggs not installed' page with one-click install."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        status = Adw.StatusPage()
        status.set_icon_name("media-optical-symbolic")
        status.set_title("Install penguins-eggs")
        status.set_description(
            "ISO Creator needs penguins-eggs to create bootable images.\n"
            "Click below to install it automatically."
        )
        
        # Content box
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content_box.set_halign(Gtk.Align.CENTER)
        content_box.set_margin_top(16)
        
        # Info card
        info_frame = Gtk.Frame()
        info_frame.add_css_class("card")
        
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        info_box.set_margin_top(16)
        info_box.set_margin_bottom(16)
        info_box.set_margin_start(16)
        info_box.set_margin_end(16)
        
        # What is penguins-eggs
        info_title = Gtk.Label(label="<b>What is penguins-eggs?</b>")
        info_title.set_use_markup(True)
        info_title.set_halign(Gtk.Align.START)
        info_box.append(info_title)
        
        features = [
            "• Create bootable live ISOs from your running system",
            "• Include or exclude user data (clone/clean modes)",
            "• Encrypted backups with LUKS",
            "• Calamares installer integration",
            f"• Full support for {self.distro.name}"
        ]
        for feature in features:
            feat_label = Gtk.Label(label=feature)
            feat_label.set_halign(Gtk.Align.START)
            feat_label.add_css_class("dim-label")
            info_box.append(feat_label)
        
        info_frame.set_child(info_box)
        content_box.append(info_frame)
        
        # Install button
        self.install_button = Gtk.Button(label="Install penguins-eggs")
        self.install_button.add_css_class("suggested-action")
        self.install_button.add_css_class("pill")
        self.install_button.set_halign(Gtk.Align.CENTER)
        self.install_button.connect("clicked", self._on_install_eggs_clicked)
        content_box.append(self.install_button)
        
        # Installation method info
        method_label = Gtk.Label()
        method_label.set_markup(f"<small>Will install via: {self._get_install_method_description()}</small>")
        method_label.add_css_class("dim-label")
        content_box.append(method_label)
        
        # Links
        links_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        links_box.set_halign(Gtk.Align.CENTER)
        links_box.set_margin_top(16)
        
        eggs_link = Gtk.LinkButton.new_with_label(
            "https://penguins-eggs.net",
            "Learn more about penguins-eggs"
        )
        links_box.append(eggs_link)
        
        content_box.append(links_box)
        
        status.set_child(content_box)
        page.append(status)
        
        self.stack.add_named(page, "not_installed")
    
    def _build_setup_choice_page(self):
        """Build the setup choice page - Learn First vs Quick Start."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        status = Adw.StatusPage()
        status.set_icon_name("emblem-system-symbolic")
        status.set_title("Configure penguins-eggs")
        status.set_description(
            "penguins-eggs is installed! Choose how you'd like to proceed."
        )
        
        # Content box
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        content_box.set_halign(Gtk.Align.CENTER)
        content_box.set_margin_top(16)
        
        # Two-column layout for choices
        choices_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=24)
        choices_box.set_halign(Gtk.Align.CENTER)
        
        # === LEARN FIRST (Guided Tour) ===
        learn_frame = Gtk.Frame()
        learn_frame.add_css_class("card")
        
        learn_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        learn_box.set_margin_top(20)
        learn_box.set_margin_bottom(20)
        learn_box.set_margin_start(20)
        learn_box.set_margin_end(20)
        learn_box.set_size_request(280, -1)
        
        learn_icon = Gtk.Image.new_from_icon_name("tux-help-browser-symbolic")
        learn_icon.set_pixel_size(48)
        learn_box.append(learn_icon)
        
        learn_title = Gtk.Label(label="<b>🎓 Learn First</b>")
        learn_title.set_use_markup(True)
        learn_box.append(learn_title)
        
        learn_subtitle = Gtk.Label(label="Explore features before setup")
        learn_subtitle.add_css_class("dim-label")
        learn_box.append(learn_subtitle)
        
        learn_desc = Gtk.Label(
            label="Take a guided tour of all\n"
                  "penguins-eggs capabilities.\n"
                  "Learn what each option does."
        )
        learn_desc.set_justify(Gtk.Justification.CENTER)
        learn_desc.add_css_class("dim-label")
        learn_box.append(learn_desc)
        
        learn_features = Gtk.Label(
            label="<small>• ISO creation modes\n"
                  "• Compression options\n"
                  "• Advanced features\n"
                  "• Then auto-configure</small>"
        )
        learn_features.set_use_markup(True)
        learn_features.set_justify(Gtk.Justification.CENTER)
        learn_box.append(learn_features)
        
        learn_button = Gtk.Button(label="Take the Tour")
        learn_button.add_css_class("suggested-action")
        learn_button.connect("clicked", self._on_learn_clicked)
        learn_box.append(learn_button)
        
        learn_frame.set_child(learn_box)
        choices_box.append(learn_frame)
        
        # === QUICK START (Dad) ===
        quick_frame = Gtk.Frame()
        quick_frame.add_css_class("card")
        
        quick_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        quick_box.set_margin_top(20)
        quick_box.set_margin_bottom(20)
        quick_box.set_margin_start(20)
        quick_box.set_margin_end(20)
        quick_box.set_size_request(280, -1)
        
        quick_icon = Gtk.Image.new_from_icon_name("tux-media-playback-start-symbolic")
        quick_icon.set_pixel_size(48)
        quick_box.append(quick_icon)
        
        quick_title = Gtk.Label(label="<b>⚡ Quick Start</b>")
        quick_title.set_use_markup(True)
        quick_box.append(quick_title)
        
        quick_subtitle = Gtk.Label(label="Configure with defaults")
        quick_subtitle.add_css_class("dim-label")
        quick_box.append(quick_subtitle)
        
        quick_desc = Gtk.Label(
            label="Skip the tour and configure\n"
                  "with sensible defaults.\n"
                  "Start creating ISOs now."
        )
        quick_desc.set_justify(Gtk.Justification.CENTER)
        quick_desc.add_css_class("dim-label")
        quick_box.append(quick_desc)
        
        quick_features = Gtk.Label(
            label="<small>• One-click setup\n"
                  "• Default configuration\n"
                  "• Ready in seconds\n"
                  "• Recommended</small>"
        )
        quick_features.set_use_markup(True)
        quick_features.set_justify(Gtk.Justification.CENTER)
        quick_box.append(quick_features)
        
        quick_button = Gtk.Button(label="Quick Start")
        quick_button.add_css_class("suggested-action")
        quick_button.connect("clicked", self._on_dad_clicked)
        quick_box.append(quick_button)
        
        quick_frame.set_child(quick_box)
        choices_box.append(quick_frame)
        
        content_box.append(choices_box)
        
        # Skip option for already configured
        skip_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        skip_box.set_halign(Gtk.Align.CENTER)
        skip_box.set_margin_top(16)
        
        skip_label = Gtk.Label(label="Already configured?")
        skip_label.add_css_class("dim-label")
        skip_box.append(skip_label)
        
        skip_button = Gtk.Button(label="Skip to ISO Creator")
        skip_button.add_css_class("flat")
        skip_button.connect("clicked", self._on_skip_setup_clicked)
        skip_box.append(skip_button)
        
        content_box.append(skip_box)
        
        status.set_child(content_box)
        page.append(status)
        
        self.stack.add_named(page, "setup_choice")
    
    def _build_guided_page(self):
        """Build the integrated guided tour page (replaces terminal-based mom)."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        # Scrollable content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)
        
        # Header
        header_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        header_box.set_halign(Gtk.Align.CENTER)
        header_box.set_margin_bottom(16)
        
        header_icon = Gtk.Image.new_from_icon_name("tux-help-browser-symbolic")
        header_icon.set_pixel_size(64)
        header_box.append(header_icon)
        
        header_title = Gtk.Label(label="<b><big>penguins-eggs Guide</big></b>")
        header_title.set_use_markup(True)
        header_box.append(header_title)
        
        header_desc = Gtk.Label(
            label="Learn what penguins-eggs can do before creating your first ISO"
        )
        header_desc.add_css_class("dim-label")
        header_box.append(header_desc)
        
        content.append(header_box)
        
        # === SECTION 1: What is penguins-eggs? ===
        self._add_guide_section(
            content,
            "🥚 What is penguins-eggs?",
            "penguins-eggs is a powerful tool that creates bootable live ISO images from your "
            "running Linux system. Think of it as taking a snapshot of your entire system that "
            "you can boot from USB, share with others, or use for backup and recovery.",
            [
                ("Created by", "Piero Proietti"),
                ("Website", "penguins-eggs.net"),
                ("Supported", "Arch, Debian, Fedora, Ubuntu, and many more"),
            ]
        )
        
        # === SECTION 2: Snapshot Modes ===
        self._add_guide_section(
            content,
            "📸 Snapshot Modes",
            "Choose what to include in your ISO:",
            [
                ("Clean ISO", "Removes all user data - perfect for creating a distributable Linux distro"),
                ("Clone", "Includes your user data unencrypted - great for personal backups"),
                ("Encrypted Clone", "Includes user data encrypted with LUKS - secure backups"),
            ]
        )
        
        # === SECTION 3: Compression Options ===
        self._add_guide_section(
            content,
            "📦 Compression Options",
            "Balance between ISO size and creation speed:",
            [
                ("Fast (zstd)", "Quick compression, larger file - good for testing"),
                ("Pendrive", "Optimized for USB drives with zstd level 15"),
                ("Standard (xz)", "Better compression, takes longer"),
                ("Maximum (xz-bcj)", "Best compression, slowest - for final releases"),
            ]
        )
        
        # === SECTION 4: Advanced Features ===
        self._add_guide_section(
            content,
            "🔧 Advanced Features",
            "Additional capabilities you can explore:",
            [
                ("Calamares", "Graphical installer for your live ISO"),
                ("Krill", "Text-based installer for servers and minimal systems"),
                ("Yolk", "Include packages for offline installation"),
                ("Wardrobe", "Apply pre-configured desktop themes and setups"),
                ("Cuckoo", "Set up PXE boot server to install over network"),
            ]
        )
        
        # === SECTION 5: Typical Workflow ===
        self._add_guide_section(
            content,
            "🚀 Typical Workflow",
            "How most users create an ISO:",
            [
                ("Step 1", "Configure your system exactly how you want it"),
                ("Step 2", "Run eggs produce to create the ISO"),
                ("Step 3", "Write the ISO to USB with tools like Ventoy or dd"),
                ("Step 4", "Boot from USB and optionally install with Calamares"),
            ]
        )
        
        # === SECTION 6: Output Location ===
        _, home = get_real_user()
        self._add_guide_section(
            content,
            "📁 Where ISOs are Saved",
            f"Your created ISOs will be saved to:",
            [
                ("Location", f"{home}/eggs/"),
                ("Format", "ISO 9660 bootable image"),
                ("Live user", "Default login is 'live' with password 'evolution'"),
            ]
        )
        
        # Ready to continue button
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(24)
        
        back_button = Gtk.Button(label="Back")
        back_button.connect("clicked", lambda b: self.stack.set_visible_child_name("setup_choice"))
        button_box.append(back_button)
        
        continue_button = Gtk.Button(label="Configure & Continue")
        continue_button.add_css_class("suggested-action")
        continue_button.add_css_class("pill")
        continue_button.connect("clicked", self._on_dad_clicked)
        button_box.append(continue_button)
        
        content.append(button_box)
        
        # Attribution
        attr_label = Gtk.Label()
        attr_label.set_markup(
            "<small>penguins-eggs by Piero Proietti • "
            "<a href='https://penguins-eggs.net'>penguins-eggs.net</a></small>"
        )
        attr_label.set_margin_top(16)
        content.append(attr_label)
        
        scrolled.set_child(content)
        page.append(scrolled)
        
        self.stack.add_named(page, "guided")
    
    def _add_guide_section(self, parent: Gtk.Box, title: str, description: str, 
                           items: List[Tuple[str, str]]):
        """Add an expandable section to the guide."""
        # Section frame
        frame = Gtk.Frame()
        frame.add_css_class("card")
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(16)
        box.set_margin_bottom(16)
        box.set_margin_start(16)
        box.set_margin_end(16)
        
        # Title
        title_label = Gtk.Label(label=f"<b>{title}</b>")
        title_label.set_use_markup(True)
        title_label.set_halign(Gtk.Align.START)
        box.append(title_label)
        
        # Description
        desc_label = Gtk.Label(label=description)
        desc_label.set_halign(Gtk.Align.START)
        desc_label.set_wrap(True)
        desc_label.set_xalign(0)
        desc_label.add_css_class("dim-label")
        box.append(desc_label)
        
        # Items
        if items:
            items_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            items_box.set_margin_top(8)
            
            for key, value in items:
                item_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                
                key_label = Gtk.Label(label=f"<b>{key}:</b>")
                key_label.set_use_markup(True)
                key_label.set_halign(Gtk.Align.START)
                key_label.set_size_request(140, -1)
                item_box.append(key_label)
                
                value_label = Gtk.Label(label=value)
                value_label.set_halign(Gtk.Align.START)
                value_label.set_wrap(True)
                value_label.set_xalign(0)
                value_label.set_hexpand(True)
                item_box.append(value_label)
                
                items_box.append(item_box)
            
            box.append(items_box)
        
        frame.set_child(box)
        parent.append(frame)
    
    def _on_learn_clicked(self, button):
        """Show the integrated guided tour."""
        self.stack.set_visible_child_name("guided")
    
    def _on_dad_clicked(self, button):
        """Run eggs dad -d for quick automatic configuration."""
        self._run_dad_configuration()
    
    def _run_dad_configuration(self):
        """Run eggs dad -d to configure with defaults."""
        self.stack.set_visible_child_name("progress")
        self.progress_label.set_markup("<b>Configuring penguins-eggs...</b>")
        
        # Clear output
        buffer = self.output_view.get_buffer()
        buffer.set_text("")
        
        # Show cancel, hide done
        self.cancel_button.set_visible(True)
        self.done_button.set_visible(False)
        
        cmd = ['sudo', 'eggs', 'dad', '-d', '--nointeractive']
        self._append_output(f"$ {' '.join(cmd)}\n\n")
        
        thread = threading.Thread(target=self._execute_dad_configuration, args=(cmd,))
        thread.daemon = True
        thread.start()
    
    def _execute_dad_configuration(self, cmd: List[str]):
        """Execute eggs dad configuration."""
        try:
            if cmd[0] == 'sudo' and shutil.which('pkexec'):
                cmd = ['pkexec'] + cmd[1:]
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            for line in iter(self.process.stdout.readline, ''):
                if not line:
                    break
                GLib.idle_add(self._append_output, line)
            
            self.process.wait()
            
            # Refresh status and show completion
            self.eggs_status = check_eggs_installed()
            GLib.idle_add(self._on_dad_complete)
            
        except Exception as e:
            GLib.idle_add(self._append_output, f"\n[ERROR] Configuration failed: {str(e)}\n")
            GLib.idle_add(self._on_command_complete, False)
    
    def _on_dad_complete(self):
        """Handle successful dad configuration."""
        self.cancel_button.set_visible(False)
        self.done_button.set_visible(True)
        self.done_button.set_label("Continue to ISO Creator")
        
        self.progress_label.set_markup("<b>✓ penguins-eggs configured!</b>")
        self._append_output("\n=== Configuration complete! Click 'Continue' to create ISOs. ===\n")
    
    def _on_skip_setup_clicked(self, button):
        """Skip setup and go directly to ISO creator."""
        self.eggs_status = check_eggs_installed()
        self.stack.set_visible_child_name("main")
    
    def _get_install_method_description(self) -> str:
        """Get human-readable description of install method for current distro."""
        if self.distro.family == DistroFamily.ARCH:
            if self.distro.id == 'manjaro':
                return "Manjaro Community Repository (pamac)"
            return "Chaotic-AUR repository"
        elif self.distro.family == DistroFamily.DEBIAN:
            return "penguins-eggs PPA repository"
        elif self.distro.family == DistroFamily.FEDORA:
            return "penguins-eggs RPM repository"
        elif self.distro.family == DistroFamily.OPENSUSE:
            return "penguins-eggs RPM repository"
        else:
            return "fresh-eggs universal installer"
    
    def _on_install_eggs_clicked(self, button):
        """Handle install button click - start automatic installation."""
        self._install_penguins_eggs()
    
    def _install_penguins_eggs(self):
        """Install penguins-eggs automatically based on distro."""
        # Build installation commands based on distro family
        commands = self._get_installation_commands()
        
        if not commands:
            self._show_error_dialog(
                "Unsupported Distribution",
                f"Automatic installation is not available for {self.distro.name}.\n"
                "Please visit https://penguins-eggs.net for manual installation instructions."
            )
            return
        
        # Switch to progress view and run installation
        self._run_installation_sequence(commands, "Installing penguins-eggs...")
    
    def _get_installation_commands(self) -> List[List[str]]:
        """Get the installation commands for the current distribution."""
        commands = []
        
        if self.distro.family == DistroFamily.ARCH:
            if self.distro.id == 'manjaro':
                # Manjaro has it in community repo
                commands = [
                    ['pamac', 'install', '--no-confirm', 'penguins-eggs']
                ]
            else:
                # Arch/EndeavourOS/Garuda - use chaotic-aur or yay
                if shutil.which('yay'):
                    commands = [
                        ['yay', '-S', '--noconfirm', 'penguins-eggs']
                    ]
                elif shutil.which('paru'):
                    commands = [
                        ['paru', '-S', '--noconfirm', 'penguins-eggs']
                    ]
                else:
                    # Install via chaotic-aur setup
                    commands = [
                        ['sudo', 'pacman-key', '--recv-key', '3056513887B78AEB', '--keyserver', 'keyserver.ubuntu.com'],
                        ['sudo', 'pacman-key', '--lsign-key', '3056513887B78AEB'],
                        ['sudo', 'pacman', '-U', '--noconfirm', 
                         'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-keyring.pkg.tar.zst',
                         'https://cdn-mirror.chaotic.cx/chaotic-aur/chaotic-mirrorlist.pkg.tar.zst'],
                        ['sudo', 'bash', '-c', 
                         'echo -e "\\n[chaotic-aur]\\nInclude = /etc/pacman.d/chaotic-mirrorlist" >> /etc/pacman.conf'],
                        ['sudo', 'pacman', '-Sy', '--noconfirm', 'penguins-eggs']
                    ]
        
        elif self.distro.family == DistroFamily.DEBIAN:
            # Debian/Ubuntu/Mint - add PPA and install
            commands = [
                ['sudo', 'bash', '-c',
                 'curl -fsSL https://pieroproietti.github.io/penguins-eggs-ppa/KEY.gpg | '
                 'gpg --dearmor -o /etc/apt/trusted.gpg.d/penguins-eggs.gpg'],
                ['sudo', 'bash', '-c',
                 'echo "deb [arch=$(dpkg --print-architecture)] '
                 'https://pieroproietti.github.io/penguins-eggs-ppa ./" > '
                 '/etc/apt/sources.list.d/penguins-eggs.list'],
                ['sudo', 'apt', 'update'],
                ['sudo', 'apt', 'install', '-y', 'penguins-eggs']
            ]
        
        elif self.distro.family == DistroFamily.FEDORA:
            # Fedora - use the eggs repo
            commands = [
                ['sudo', 'bash', '-c',
                 'curl -fsSL https://penguins-eggs.net/repos/fedora/penguins-eggs.repo -o '
                 '/etc/yum.repos.d/penguins-eggs.repo'],
                ['sudo', 'dnf', 'install', '-y', 'penguins-eggs']
            ]
        
        elif self.distro.family == DistroFamily.RHEL:
            # RHEL/AlmaLinux/Rocky
            commands = [
                ['sudo', 'bash', '-c',
                 'curl -fsSL https://penguins-eggs.net/repos/el9/penguins-eggs.repo -o '
                 '/etc/yum.repos.d/penguins-eggs.repo'],
                ['sudo', 'dnf', 'install', '-y', 'penguins-eggs']
            ]
        
        elif self.distro.family == DistroFamily.OPENSUSE:
            # OpenSUSE
            commands = [
                ['sudo', 'bash', '-c',
                 'curl -fsSL https://penguins-eggs.net/repos/opensuse/penguins-eggs.repo -o '
                 '/etc/zypp/repos.d/penguins-eggs.repo'],
                ['sudo', 'zypper', '--non-interactive', 'install', 'penguins-eggs']
            ]
        
        return commands
    
    def _run_installation_sequence(self, commands: List[List[str]], title: str):
        """Run a sequence of installation commands."""
        self.stack.set_visible_child_name("progress")
        self.progress_label.set_markup(f"<b>{title}</b>")
        
        # Clear output
        buffer = self.output_view.get_buffer()
        buffer.set_text("")
        
        # Show cancel, hide done
        self.cancel_button.set_visible(True)
        self.done_button.set_visible(False)
        
        # Store commands for sequential execution
        self.pending_commands = commands.copy()
        self.installation_failed = False
        
        # Start first command
        self._run_next_installation_command()
    
    def _run_next_installation_command(self):
        """Run the next command in the installation sequence."""
        if not self.pending_commands or self.installation_failed:
            # All done or failed
            if not self.installation_failed:
                # Installation complete - now configure eggs
                GLib.idle_add(self._configure_eggs_after_install)
            return
        
        cmd = self.pending_commands.pop(0)
        self._append_output(f"\n$ {' '.join(cmd)}\n")
        
        thread = threading.Thread(target=self._execute_installation_command, args=(cmd,))
        thread.daemon = True
        thread.start()
    
    def _execute_installation_command(self, cmd: List[str]):
        """Execute a single installation command."""
        try:
            # Use pkexec for commands that need sudo
            if cmd[0] == 'sudo' and shutil.which('pkexec'):
                cmd = ['pkexec'] + cmd[1:]
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            for line in iter(self.process.stdout.readline, ''):
                if not line:
                    break
                GLib.idle_add(self._append_output, line)
            
            self.process.wait()
            
            if self.process.returncode != 0:
                self.installation_failed = True
                GLib.idle_add(self._append_output, f"\n[ERROR] Command failed with code {self.process.returncode}\n")
                GLib.idle_add(self._on_command_complete, False)
            else:
                # Run next command
                GLib.idle_add(self._run_next_installation_command)
                
        except Exception as e:
            self.installation_failed = True
            GLib.idle_add(self._append_output, f"\n[ERROR] {str(e)}\n")
            GLib.idle_add(self._on_command_complete, False)
    
    def _configure_eggs_after_install(self):
        """Show setup choice page after successful installation."""
        self._append_output("\n=== Installation complete! ===\n")
        self._append_output("Proceeding to configuration options...\n")
        
        # Refresh status
        self.eggs_status = check_eggs_installed()
        
        # Show the setup choice page
        GLib.timeout_add(1500, self._show_setup_choice)
    
    def _show_setup_choice(self):
        """Switch to setup choice page."""
        self.stack.set_visible_child_name("setup_choice")
        return False  # Don't repeat
    
    def _show_error_dialog(self, title: str, message: str):
        """Show an error dialog."""
        dialog = Adw.MessageDialog(
            transient_for=self.get_root(),
            heading=title,
            body=message
        )
        dialog.add_response("ok", "OK")
        dialog.present()
    
    def _build_main_page(self):
        """Build the main configuration page."""
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)
        scrolled.set_child(content)
        
        # Status banner
        self._build_status_section(content)
        
        # Snapshot mode selection
        self._build_mode_section(content)
        
        # Compression options
        self._build_compression_section(content)
        
        # Additional options
        self._build_options_section(content)
        
        # Action buttons
        self._build_action_buttons(content)
        
        self.stack.add_named(scrolled, "main")
    
    def _build_status_section(self, content: Gtk.Box):
        """Build status information section."""
        group = Adw.PreferencesGroup()
        group.set_title("System Status")
        content.append(group)
        
        # Distribution
        row = Adw.ActionRow()
        row.set_title("Distribution")
        row.set_subtitle(f"{self.distro.name}")
        row.add_prefix(Gtk.Image.new_from_icon_name("tux-computer-symbolic"))
        group.add(row)
        
        # penguins-eggs version
        self.eggs_version_row = Adw.ActionRow()
        self.eggs_version_row.set_title("penguins-eggs")
        self.eggs_version_row.add_prefix(Gtk.Image.new_from_icon_name("tux-application-x-executable-symbolic"))
        self._update_eggs_version_row()
        group.add(self.eggs_version_row)
        
        # Disk space
        try:
            stat = os.statvfs('/')
            free_gb = (stat.f_bavail * stat.f_frsize) // (1024**3)
            total_gb = (stat.f_blocks * stat.f_frsize) // (1024**3)
            
            row = Adw.ActionRow()
            row.set_title("Disk Space")
            row.set_subtitle(f"{free_gb} GB free of {total_gb} GB")
            row.add_prefix(Gtk.Image.new_from_icon_name("tux-drive-harddisk-symbolic"))
            
            # Warning if low space
            if free_gb < 20:
                warning = Gtk.Image.new_from_icon_name("tux-dialog-warning-symbolic")
                warning.add_css_class("warning")
                row.add_suffix(warning)
            
            group.add(row)
        except:
            pass
        
        # Output location
        _, home = get_real_user()
        row = Adw.ActionRow()
        row.set_title("Output Location")
        row.set_subtitle(f"{home}/eggs")
        row.add_prefix(Gtk.Image.new_from_icon_name("tux-folder-symbolic"))
        group.add(row)
    
    def _update_eggs_version_row(self):
        """Update the eggs version row with current status."""
        # Remove any existing suffix widgets first (prevents duplicate buttons)
        while True:
            # Get the first suffix and remove it, repeat until none left
            # ActionRow doesn't have a direct "clear suffixes" so we work around
            try:
                # This is a bit hacky but necessary - we store and manage our own button
                if hasattr(self, '_config_btn') and self._config_btn:
                    self.eggs_version_row.remove(self._config_btn)
                    self._config_btn = None
            except:
                pass
            break
        
        if self.eggs_status.installed:
            version_text = f"v{self.eggs_status.version}" if self.eggs_status.version else "Installed"
            if self.eggs_status.configured:
                version_text += " (configured)"
            else:
                version_text += " (needs configuration)"
            self.eggs_version_row.set_subtitle(version_text)
            
            # Add configure button if needed
            if not self.eggs_status.configured:
                self._config_btn = Gtk.Button(label="Configure")
                self._config_btn.set_valign(Gtk.Align.CENTER)
                self._config_btn.add_css_class("suggested-action")
                self._config_btn.connect("clicked", self._on_configure_eggs)
                self.eggs_version_row.add_suffix(self._config_btn)
        else:
            self.eggs_version_row.set_subtitle("Not installed")
    
    def _build_mode_section(self, content: Gtk.Box):
        """Build snapshot mode selection."""
        group = Adw.PreferencesGroup()
        group.set_title("Snapshot Mode")
        group.set_description("Choose what to include in your ISO")
        content.append(group)
        
        self.mode_row = Adw.ComboRow()
        self.mode_row.set_title("Mode")
        
        model = Gtk.StringList()
        for mode in SnapshotMode:
            model.append(f"{mode.label} - {mode.desc}")
        
        self.mode_row.set_model(model)
        self.mode_row.set_selected(0)  # Clean by default
        group.add(self.mode_row)
        
        # Info about modes
        info_row = Adw.ActionRow()
        info_row.set_title("About Modes")
        info_row.set_subtitle(
            "Clean: Perfect for sharing. Clone: Personal backup. "
            "Encrypted: Secure backup with LUKS encryption."
        )
        info_row.add_prefix(Gtk.Image.new_from_icon_name("tux-dialog-information-symbolic"))
        group.add(info_row)
    
    def _build_compression_section(self, content: Gtk.Box):
        """Build compression options."""
        group = Adw.PreferencesGroup()
        group.set_title("Compression")
        content.append(group)
        
        self.compression_row = Adw.ComboRow()
        self.compression_row.set_title("Compression Level")
        
        model = Gtk.StringList()
        for comp in CompressionMode:
            model.append(f"{comp.label}")
        
        self.compression_row.set_model(model)
        self.compression_row.set_selected(0)  # Fast by default
        self.compression_row.connect("notify::selected", self._on_compression_changed)
        group.add(self.compression_row)
        
        self.compression_desc = Adw.ActionRow()
        self.compression_desc.set_title("Description")
        self.compression_desc.set_subtitle(list(CompressionMode)[0].desc)
        group.add(self.compression_desc)
    
    def _on_compression_changed(self, row, param):
        """Update compression description when selection changes."""
        selected = row.get_selected()
        mode = list(CompressionMode)[selected]
        self.compression_desc.set_subtitle(mode.desc)
    
    def _build_options_section(self, content: Gtk.Box):
        """Build additional options."""
        group = Adw.PreferencesGroup()
        group.set_title("Options")
        content.append(group)
        
        # Custom basename
        self.basename_row = Adw.EntryRow()
        self.basename_row.set_title("ISO Name (optional)")
        self.basename_row.set_text("")
        group.add(self.basename_row)
        
        # Verbose output
        self.verbose_row = Adw.SwitchRow()
        self.verbose_row.set_title("Verbose Output")
        self.verbose_row.set_subtitle("Show detailed progress information")
        self.verbose_row.set_active(True)
        group.add(self.verbose_row)
        
        # Yolk (offline install capability)
        self.yolk_row = Adw.SwitchRow()
        self.yolk_row.set_title("Enable Offline Install")
        self.yolk_row.set_subtitle("Include packages for installation without internet (yolk)")
        self.yolk_row.set_active(False)
        group.add(self.yolk_row)
    
    def _build_action_buttons(self, content: Gtk.Box):
        """Build action buttons."""
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(24)
        content.append(button_box)
        
        # Tools button
        tools_btn = Gtk.Button(label="Tools")
        tools_btn.connect("clicked", self._on_tools_clicked)
        button_box.append(tools_btn)
        
        # Main create button
        self.create_button = Gtk.Button(label="Create ISO")
        self.create_button.add_css_class("suggested-action")
        self.create_button.add_css_class("pill")
        self.create_button.connect("clicked", self._on_create_clicked)
        button_box.append(self.create_button)
        
        # Attribution
        attr_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        attr_box.set_halign(Gtk.Align.CENTER)
        attr_box.set_margin_top(24)
        
        attr_label = Gtk.Label(label="Powered by")
        attr_label.add_css_class("dim-label")
        attr_box.append(attr_label)
        
        eggs_link = Gtk.LinkButton.new_with_label(
            "https://penguins-eggs.net",
            "penguins-eggs"
        )
        attr_box.append(eggs_link)
        
        by_label = Gtk.Label(label="by Piero Proietti")
        by_label.add_css_class("dim-label")
        attr_box.append(by_label)
        
        content.append(attr_box)
    
    def _build_progress_page(self):
        """Build the progress/terminal page."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        page.set_margin_top(16)
        page.set_margin_bottom(16)
        page.set_margin_start(16)
        page.set_margin_end(16)
        
        # Progress header
        self.progress_label = Gtk.Label(label="<b>Creating ISO...</b>")
        self.progress_label.set_use_markup(True)
        self.progress_label.set_halign(Gtk.Align.START)
        page.append(self.progress_label)
        
        # Terminal output
        terminal_frame = Gtk.Frame()
        terminal_frame.add_css_class("card")
        terminal_frame.set_vexpand(True)
        
        # Use a text view for output (VTE may not be available)
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        
        self.output_view = Gtk.TextView()
        self.output_view.set_editable(False)
        self.output_view.set_monospace(True)
        self.output_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.output_view.set_margin_top(8)
        self.output_view.set_margin_bottom(8)
        self.output_view.set_margin_start(8)
        self.output_view.set_margin_end(8)
        
        scrolled.set_child(self.output_view)
        terminal_frame.set_child(scrolled)
        page.append(terminal_frame)
        
        # Progress buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        btn_box.set_halign(Gtk.Align.CENTER)
        btn_box.set_margin_top(16)
        
        self.cancel_button = Gtk.Button(label="Cancel")
        self.cancel_button.add_css_class("destructive-action")
        self.cancel_button.connect("clicked", self._on_cancel_clicked)
        btn_box.append(self.cancel_button)
        
        self.done_button = Gtk.Button(label="Done")
        self.done_button.add_css_class("suggested-action")
        self.done_button.connect("clicked", self._on_done_clicked)
        self.done_button.set_visible(False)
        btn_box.append(self.done_button)
        
        page.append(btn_box)
        
        self.stack.add_named(page, "progress")
    
    def _update_view(self):
        """Update which view is shown based on eggs status."""
        if not self.eggs_status.installed:
            self.stack.set_visible_child_name("not_installed")
        elif not self.eggs_status.configured:
            # Installed but not configured - show setup choice
            self.stack.set_visible_child_name("setup_choice")
        else:
            self.stack.set_visible_child_name("main")

        # Enable create button only when eggs is installed and configured
        if hasattr(self, "create_button") and self.create_button is not None:
            can_create = self.eggs_status.installed and self.eggs_status.configured
            self.create_button.set_sensitive(can_create)

    # =========================================================================

    # Event Handlers
    # =========================================================================
    
    def _on_refresh_clicked(self, button):
        """Refresh eggs status."""
        self.eggs_status = check_eggs_installed()
        self._update_eggs_version_row()
        self._update_view()
    
    def _on_configure_eggs(self, button):
        """Show setup choice page for configuration."""
        self.stack.set_visible_child_name("setup_choice")
    
    def _on_tools_clicked(self, button):
        """Show tools menu."""
        popover = Gtk.Popover()
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_margin_top(8)
        box.set_margin_bottom(8)
        box.set_margin_start(8)
        box.set_margin_end(8)
        
        # Clean old ISOs
        clean_btn = Gtk.Button(label="Clean Old ISOs")
        clean_btn.add_css_class("flat")
        clean_btn.connect("clicked", lambda b: self._run_eggs_tool('kill'))
        box.append(clean_btn)
        
        # System clean
        sys_clean_btn = Gtk.Button(label="Clean System Cache")
        sys_clean_btn.add_css_class("flat")
        sys_clean_btn.connect("clicked", lambda b: self._run_eggs_tool('tools clean'))
        box.append(sys_clean_btn)
        
        # Calamares
        calam_btn = Gtk.Button(label="Install Calamares")
        calam_btn.add_css_class("flat")
        calam_btn.connect("clicked", lambda b: self._run_eggs_tool('calamares --install'))
        box.append(calam_btn)
        
        # Status
        status_btn = Gtk.Button(label="Show Status")
        status_btn.add_css_class("flat")
        status_btn.connect("clicked", lambda b: self._run_eggs_tool('status'))
        box.append(status_btn)
        
        popover.set_child(box)
        popover.set_parent(button)
        popover.popup()
    
    def _run_eggs_tool(self, tool_cmd: str):
        """Run an eggs tool command."""
        cmd = ['sudo', 'eggs'] + tool_cmd.split()
        self._run_eggs_command(cmd, f"Running: eggs {tool_cmd}")
    
    def _on_create_clicked(self, button):
        """Start ISO creation."""
        # Check disk space first
        try:
            stat = os.statvfs('/')
            free_gb = (stat.f_bavail * stat.f_frsize) // (1024**3)
            if free_gb < 15:
                dialog = Adw.MessageDialog(
                    transient_for=self.get_root(),
                    heading="Low Disk Space",
                    body=f"Only {free_gb} GB free. ISO creation may fail.\nAt least 15 GB recommended."
                )
                dialog.add_response("cancel", "Cancel")
                dialog.add_response("continue", "Continue Anyway")
                dialog.set_default_response("cancel")
                dialog.set_close_response("cancel")
                dialog.connect("response", self._on_disk_space_response)
                dialog.present()
                return
        except:
            pass  # Continue if we can't check
        
        self._start_iso_creation()
    
    def _on_disk_space_response(self, dialog, response):
        """Handle disk space warning response."""
        if response == "continue":
            self._start_iso_creation()
    
    def _start_iso_creation(self):
        """Actually start the ISO creation process."""
        # Build command
        cmd = ['sudo', 'eggs', 'produce', '--nointeractive']
        
        # Add mode flag
        mode_idx = self.mode_row.get_selected()
        mode = list(SnapshotMode)[mode_idx]
        if mode.flag != "clean":
            cmd.append(f'--{mode.flag}')
        
        # Add compression
        comp_idx = self.compression_row.get_selected()
        comp = list(CompressionMode)[comp_idx]
        if comp.flag:
            cmd.append(comp.flag)
        
        # Add basename if specified (sanitized to prevent injection)
        basename = re.sub(r'[^A-Za-z0-9._-]', '', self.basename_row.get_text().strip())
        if basename:
            cmd.extend(['--basename', basename])
        
        # Add verbose
        if self.verbose_row.get_active():
            cmd.append('--verbose')
        
        # Add yolk
        if self.yolk_row.get_active():
            cmd.append('--yolk')
        
        self._run_eggs_command(cmd, "Creating ISO image...")
    
    def _run_eggs_command(self, cmd: List[str], title: str):
        """Run an eggs command with output display."""
        # Switch to progress view
        self.stack.set_visible_child_name("progress")
        self.progress_label.set_markup(f"<b>{title}</b>")
        
        # Clear output
        buffer = self.output_view.get_buffer()
        buffer.set_text("")
        
        # Show cancel, hide done
        self.cancel_button.set_visible(True)
        self.done_button.set_visible(False)
        
        # Start command in thread
        self.process = None
        thread = threading.Thread(target=self._execute_command, args=(cmd,))
        thread.daemon = True
        thread.start()
    
    def _execute_command(self, cmd: List[str]):
        """Execute command and capture output."""
        try:
            # Use pkexec for GUI sudo if available
            if cmd[0] == 'sudo' and shutil.which('pkexec'):
                cmd = ['pkexec'] + cmd[1:]
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            for line in iter(self.process.stdout.readline, ''):
                if not line:
                    break
                GLib.idle_add(self._append_output, line)
            
            self.process.wait()
            
            success = self.process.returncode == 0
            GLib.idle_add(self._on_command_complete, success)
            
        except Exception as e:
            GLib.idle_add(self._append_output, f"\nError: {str(e)}\n")
            GLib.idle_add(self._on_command_complete, False)
    
    def _append_output(self, text: str):
        """Append text to output view."""
        buffer = self.output_view.get_buffer()
        end_iter = buffer.get_end_iter()
        buffer.insert(end_iter, text)
        
        # Auto-scroll to bottom
        mark = buffer.create_mark(None, buffer.get_end_iter(), False)
        self.output_view.scroll_mark_onscreen(mark)
        buffer.delete_mark(mark)
    
    def _on_command_complete(self, success: bool):
        """Handle command completion."""
        self.cancel_button.set_visible(False)
        self.done_button.set_visible(True)
        self.done_button.set_label("Done")  # Reset label
        
        if success:
            self.progress_label.set_markup("<b>✓ Complete!</b>")
            self._append_output("\n\n=== ISO creation completed successfully! ===\n")
            
            # Show location
            _, home = get_real_user()
            self._append_output(f"Output location: {home}/eggs/\n")
        else:
            self.progress_label.set_markup("<b>✗ Failed</b>")
            self._append_output("\n\n=== Process failed. See output above for details. ===\n")
    
    def _on_cancel_clicked(self, button):
        """Cancel running process."""
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self._append_output("\n\n=== Process cancelled by user ===\n")
        
        self._on_command_complete(False)
    
    def _on_done_clicked(self, button):
        """Return to main view."""
        # Refresh status in case something changed
        self.eggs_status = check_eggs_installed()
        self._update_eggs_version_row()
        self._update_view()
