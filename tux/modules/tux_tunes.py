"""
Tux Tunes - Tux Assistant Module

Internet radio player with smart recording.
Listen to 50,000+ stations while you work!

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
"""

import os
import subprocess
import threading

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib

from ..core import get_distro, DistroFamily
from .registry import register_module, ModuleCategory


# Desktop file content for standalone app
DESKTOP_FILE = """[Desktop Entry]
Name=Tux Tunes
Comment=Internet Radio Player with Smart Recording
Exec=python3 {exec_path}
Icon=audio-x-generic
Terminal=false
Type=Application
Categories=Audio;Music;Player;GTK;
Keywords=radio;internet;streaming;music;recording;
StartupNotify=true
"""


# Required packages by distro family
# Base GStreamer packages
GSTREAMER_PACKAGES = {
    DistroFamily.ARCH: ['gstreamer', 'gst-plugins-base', 'gst-plugins-good', 
                        'gst-plugins-bad', 'gst-plugins-ugly', 'python-gobject'],
    DistroFamily.DEBIAN: ['gstreamer1.0-plugins-base', 'gstreamer1.0-plugins-good', 
                          'gstreamer1.0-plugins-bad', 'gstreamer1.0-plugins-ugly',
                          'python3-gi', 'gir1.2-gst-plugins-base-1.0'],
    DistroFamily.FEDORA: ['gstreamer1-plugins-base', 'gstreamer1-plugins-good', 
                          'gstreamer1-plugins-bad-free', 'gstreamer1-plugins-ugly-free',
                          'python3-gobject'],
    DistroFamily.OPENSUSE: ['gstreamer-plugins-base', 'gstreamer-plugins-good', 
                        'gstreamer-plugins-bad', 'gstreamer-plugins-ugly',
                        'python3-gobject'],
}

# Audio analysis packages (for smart recording)
AUDIO_ANALYSIS_PACKAGES = {
    DistroFamily.ARCH: ['python-numpy', 'python-scipy', 'python-pydub', 'ffmpeg', 'python-pip'],
    DistroFamily.DEBIAN: ['python3-numpy', 'python3-scipy', 'python3-pydub', 'ffmpeg', 'python3-pip'],
    DistroFamily.FEDORA: ['python3-numpy', 'python3-scipy', 'python3-pydub', 'ffmpeg', 'python3-pip'],
    DistroFamily.OPENSUSE: ['python3-numpy', 'python3-scipy', 'python3-pydub', 'ffmpeg', 'python3-pip'],
}

# Python packages that need pip install (not in repos)
PIP_PACKAGES = ['librosa']

# Combined for backwards compatibility
REQUIRED_PACKAGES = {
    family: GSTREAMER_PACKAGES.get(family, []) + AUDIO_ANALYSIS_PACKAGES.get(family, [])
    for family in DistroFamily
}


def check_gstreamer_installed() -> bool:
    """Check if GStreamer is available."""
    try:
        gi.require_version('Gst', '1.0')
        from gi.repository import Gst
        Gst.init(None)
        return True
    except Exception:
        return False


def check_audio_analysis_installed() -> dict:
    """Check if audio analysis libraries are available."""
    results = {
        'numpy': False,
        'scipy': False,
        'librosa': False,
        'pydub': False,
    }
    
    try:
        import numpy
        results['numpy'] = True
    except ImportError:
        pass
    
    try:
        import scipy
        results['scipy'] = True
    except ImportError:
        pass
    
    try:
        import librosa
        results['librosa'] = True
    except ImportError:
        pass
    
    try:
        from pydub import AudioSegment
        results['pydub'] = True
    except ImportError:
        pass
    
    return results


def check_all_deps() -> dict:
    """Check all dependencies."""
    audio_deps = check_audio_analysis_installed()
    return {
        'gstreamer': check_gstreamer_installed(),
        'audio_analysis': audio_deps,
        'audio_analysis_ready': all(audio_deps.values()),
        'basic_ready': check_gstreamer_installed(),
        'full_ready': check_gstreamer_installed() and all(audio_deps.values()),
    }


def get_tux_tunes_path() -> str:
    """Get path to tux-tunes.py launcher."""
    # Try various locations
    possible_paths = [
        # Installed location
        "/opt/tux-assistant/tux/apps/tux_tunes/tux-tunes.py",
        # Development location (relative to this file)
        os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                     'apps', 'tux_tunes', 'tux-tunes.py'),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return possible_paths[0]  # Default to installed location


@register_module(
    id="tux_tunes",
    name="Tux Tunes",
    description="Internet radio with smart song recording",
    icon="audio-x-generic-symbolic",
    category=ModuleCategory.MEDIA,
    order=60
)
class TuxTunesPage(Adw.NavigationPage):
    """Tux Tunes radio player module page."""
    
    def __init__(self, window):
        super().__init__(title="Tux Tunes")
        
        self.window = window
        self.distro = get_distro()
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the page UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        toolbar_view.add_top_bar(header)
        
        # Scrollable content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        toolbar_view.set_content(scrolled)
        
        # Content with clamp
        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_margin_top(24)
        clamp.set_margin_bottom(24)
        clamp.set_margin_start(16)
        clamp.set_margin_end(16)
        scrolled.set_child(clamp)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        clamp.set_child(content)
        
        # Title section (simpler than StatusPage which has rendering issues)
        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        title_box.set_halign(Gtk.Align.CENTER)
        title_box.set_margin_bottom(16)
        
        icon = Gtk.Image.new_from_icon_name("audio-x-generic-symbolic")
        icon.set_pixel_size(64)
        icon.add_css_class("dim-label")
        title_box.append(icon)
        
        title_label = Gtk.Label(label="Tux Tunes")
        title_label.add_css_class("title-1")
        title_box.append(title_label)
        
        desc_label = Gtk.Label(label="Internet radio player with smart recording.\nListen to 50,000+ stations and capture complete songs!")
        desc_label.add_css_class("dim-label")
        desc_label.set_justify(Gtk.Justification.CENTER)
        title_box.append(desc_label)
        
        content.append(title_box)
        
        # Check dependencies
        deps = check_all_deps()
        gstreamer_ok = deps['gstreamer']
        audio_ok = deps['audio_analysis_ready']
        
        # Status group
        status_group = Adw.PreferencesGroup()
        status_group.set_title("Status")
        content.append(status_group)
        
        # GStreamer status
        if gstreamer_ok:
            gst_row = Adw.ActionRow()
            gst_row.set_title("GStreamer Ready")
            gst_row.set_subtitle("Audio playback available")
            gst_row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
            status_group.add(gst_row)
        else:
            gst_row = Adw.ActionRow()
            gst_row.set_title("GStreamer Needed")
            gst_row.set_subtitle("Required for audio playback")
            gst_row.add_prefix(Gtk.Image.new_from_icon_name("dialog-warning-symbolic"))
            status_group.add(gst_row)
        
        # Audio analysis status
        if audio_ok:
            audio_row = Adw.ActionRow()
            audio_row.set_title("Smart Recording Ready")
            audio_row.set_subtitle("Audio analysis libraries installed")
            audio_row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
            status_group.add(audio_row)
        else:
            missing = [k for k, v in deps['audio_analysis'].items() if not v]
            audio_row = Adw.ActionRow()
            audio_row.set_title("Smart Recording Limited")
            audio_row.set_subtitle(f"Missing: {', '.join(missing)}")
            audio_row.add_prefix(Gtk.Image.new_from_icon_name("dialog-information-symbolic"))
            status_group.add(audio_row)
        
        # Install buttons if needed
        if not gstreamer_ok or not audio_ok:
            install_row = Adw.ActionRow()
            install_row.set_title("Install All Dependencies")
            install_row.set_subtitle("Install GStreamer and audio analysis libraries")
            install_row.set_activatable(True)
            install_row.add_prefix(Gtk.Image.new_from_icon_name("system-software-install-symbolic"))
            install_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            install_row.connect("activated", self._on_install_deps)
            status_group.add(install_row)
        
        # Features group
        features_group = Adw.PreferencesGroup()
        features_group.set_title("Features")
        content.append(features_group)
        
        features = [
            ("folder-music-symbolic", "50,000+ Stations", "Access radio-browser.info database"),
            ("media-record-symbolic", "Smart Recording", "Captures full songs with pre/post buffering"),
            ("starred-symbolic", "Favorites Library", "Save your favorite stations"),
            ("system-search-symbolic", "Search & Browse", "Find stations by name or genre"),
            ("list-add-symbolic", "Custom Stations", "Add your own stream URLs"),
        ]
        
        for icon, title, subtitle in features:
            row = Adw.ActionRow()
            row.set_title(title)
            row.set_subtitle(subtitle)
            row.add_prefix(Gtk.Image.new_from_icon_name(icon))
            features_group.add(row)
        
        # Actions group
        actions_group = Adw.PreferencesGroup()
        actions_group.set_title("Actions")
        content.append(actions_group)
        
        # Launch button
        launch_row = Adw.ActionRow()
        launch_row.set_title("Launch Tux Tunes")
        if not gstreamer_ok:
            launch_row.set_subtitle("Install GStreamer first")
            launch_row.set_activatable(False)
        elif not audio_ok:
            launch_row.set_subtitle("Basic mode (install full deps for smart recording)")
            launch_row.set_activatable(True)
            launch_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        else:
            launch_row.set_subtitle("Full features ready")
            launch_row.set_activatable(True)
            launch_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        launch_row.add_prefix(Gtk.Image.new_from_icon_name("media-playback-start-symbolic"))
        launch_row.connect("activated", self._on_launch)
        actions_group.add(launch_row)
        
        # Create shortcut row
        shortcut_row = Adw.ActionRow()
        shortcut_row.set_title("Create Desktop Shortcut")
        shortcut_row.set_subtitle("Add Tux Tunes to your applications menu")
        shortcut_row.set_activatable(True)
        shortcut_row.add_prefix(Gtk.Image.new_from_icon_name("application-x-executable-symbolic"))
        shortcut_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        shortcut_row.connect("activated", self._on_create_shortcut)
        actions_group.add(shortcut_row)
        
        # Info group
        info_group = Adw.PreferencesGroup()
        info_group.set_description(
            "Tux Tunes uses radio-browser.info, a free community-driven "
            "database of internet radio stations. The smart recording feature "
            "uses pre-buffering to capture the beginning of songs that would "
            "otherwise be cut off - fixing a common problem with other radio apps!"
        )
        content.append(info_group)
    
    def _on_install_deps(self, row):
        """Install required dependencies."""
        # Get system packages for this distro
        gst_packages = GSTREAMER_PACKAGES.get(self.distro.family, GSTREAMER_PACKAGES[DistroFamily.DEBIAN])
        audio_packages = AUDIO_ANALYSIS_PACKAGES.get(self.distro.family, AUDIO_ANALYSIS_PACKAGES[DistroFamily.DEBIAN])
        all_packages = gst_packages + audio_packages
        
        tasks = []
        
        # Build system package install command
        if self.distro.family == DistroFamily.ARCH:
            cmd = f"pacman -S --needed --noconfirm {' '.join(all_packages)}"
        elif self.distro.family == DistroFamily.DEBIAN:
            cmd = f"apt-get install -y {' '.join(all_packages)}"
        elif self.distro.family == DistroFamily.FEDORA:
            cmd = f"dnf install -y {' '.join(all_packages)}"
        elif self.distro.family == DistroFamily.SUSE:
            cmd = f"zypper install -y {' '.join(all_packages)}"
        else:
            self.window.show_toast("Unsupported distribution")
            return
        
        tasks.append({
            "type": "command",
            "name": "Install system packages",
            "command": cmd
        })
        
        # Add pip packages (librosa isn't in most distro repos)
        if PIP_PACKAGES:
            # Use pip for Arch, pip3 for others
            if self.distro.family == DistroFamily.ARCH:
                pip_cmd = f"pip install --break-system-packages {' '.join(PIP_PACKAGES)}"
            else:
                pip_cmd = f"pip3 install --break-system-packages {' '.join(PIP_PACKAGES)}"
            tasks.append({
                "type": "command",
                "name": "Install Python packages (pip)",
                "command": pip_cmd
            })
        
        # Execute with pkexec
        plan = {"tasks": tasks}
        
        # Import here to avoid circular import
        from .networking import PlanExecutionDialog
        dialog = PlanExecutionDialog(self.window, plan, "Installing Dependencies", self.distro)
        
        # Connect to closed signal to refresh the page
        dialog.connect("closed", self._on_install_dialog_closed)
        
        dialog.present(self.window)
    
    def _on_install_dialog_closed(self, dialog):
        """Handle install dialog closed - refresh the page."""
        # Give a moment for imports to settle
        GLib.timeout_add(500, self._refresh_page)
    
    def _refresh_page(self):
        """Rebuild the page UI to reflect new dependency state."""
        # Remove old content
        old_child = self.get_child()
        if old_child:
            self.set_child(None)
        
        # Rebuild UI
        self._build_ui()
        
        # Show toast
        deps = check_all_deps()
        if deps['full_ready']:
            self.window.show_toast("All dependencies installed! ✓")
        elif deps['basic_ready']:
            self.window.show_toast("Basic playback ready. Some features still missing.")
        
        return False  # Don't repeat
    
    def _on_launch(self, row):
        """Launch Tux Tunes."""
        tux_tunes_path = get_tux_tunes_path()
        
        if not os.path.exists(tux_tunes_path):
            self.window.show_toast(f"Not found: {tux_tunes_path}")
            return
        
        try:
            # Launch with visible output for debugging
            process = subprocess.Popen(
                ['python3', tux_tunes_path],
                start_new_session=True,
            )
            self.window.show_toast("Launching Tux Tunes...")
        except Exception as e:
            self.window.show_toast(f"Failed to launch: {e}")
    
    def _on_create_shortcut(self, row):
        """Create desktop shortcut."""
        tux_tunes_path = get_tux_tunes_path()
        
        # Create desktop file
        desktop_content = DESKTOP_FILE.format(exec_path=tux_tunes_path)
        
        # Ensure directory exists
        apps_dir = os.path.expanduser("~/.local/share/applications")
        os.makedirs(apps_dir, exist_ok=True)
        
        desktop_path = os.path.join(apps_dir, "tux-tunes.desktop")
        
        try:
            with open(desktop_path, 'w') as f:
                f.write(desktop_content)
            
            # Make executable
            os.chmod(desktop_path, 0o755)
            
            self.window.show_toast("Desktop shortcut created! Check your app menu.")
        except Exception as e:
            self.window.show_toast(f"Failed to create shortcut: {e}")
