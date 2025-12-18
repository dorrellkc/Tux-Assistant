"""
Tux Assistant - Main GTK4 Application

The main application class using GTK4 and libadwaita.
Dynamically discovers and loads modules from the modules directory.

Copyright (c) 2025 Christopher Dorrell. Licensed under GPL-3.0.
"""

import sys
import os
import gi
import sqlite3
import threading
import urllib.request
import json
from datetime import datetime, timedelta

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GLib, Gdk, GdkPixbuf, GObject

# Try to import WebKit for global Claude AI panel
WEBKIT_AVAILABLE = False
try:
    gi.require_version('WebKit', '6.0')
    from gi.repository import WebKit
    WEBKIT_AVAILABLE = True
except (ValueError, ImportError):
    try:
        gi.require_version('WebKit2', '5.0')
        from gi.repository import WebKit2 as WebKit
        WEBKIT_AVAILABLE = True
    except (ValueError, ImportError):
        pass  # WebKit not available

from . import __version__, __app_name__, __app_id__
from .core import get_distro, get_desktop
from .modules import ModuleRegistry, ModuleCategory, create_icon_simple

# Weather widget (feature flag - set to False to disable)
ENABLE_WEATHER_WIDGET = True


APP_ID = __app_id__
APP_VERSION = __version__

# CSS for larger, more readable UI
APP_CSS = """
/* Base font size increase - affects everything */
window {
    font-size: 11pt;
}

/* Larger titles in preference groups */
.title {
    font-size: 12pt;
    font-weight: bold;
}

/* Row titles slightly larger */
row > box > box > label.title {
    font-size: 11pt;
}

/* Row subtitles readable */
row > box > box > label.subtitle {
    font-size: 10pt;
}

/* Regular text buttons more readable - but not checkboxes */
button.text-button,
button.suggested-action,
button.destructive-action,
button.flat {
    font-size: 11pt;
    min-height: 36px;
}

/* Large pill buttons (like Create ISO) */
button.pill {
    min-height: 42px;
    padding: 10px 24px;
    font-size: 12pt;
}

/* Action rows taller for easier clicking */
row.activatable {
    min-height: 60px;
}

/* Preference group titles */
preferencesgroup > label {
    font-size: 13pt;
    font-weight: bold;
}

/* Status page titles */
statuspage > box > label.title {
    font-size: 18pt;
}

/* Status page descriptions */
statuspage > box > label.description {
    font-size: 11pt;
}

/* Entry rows */
entry, .entry {
    font-size: 11pt;
    min-height: 36px;
}

/* Combo rows */
comborow > box {
    min-height: 40px;
}

/* Switch rows */
switchrow {
    min-height: 56px;
}

/* Card content padding */
.card {
    padding: 4px;
}

/* Terminal/output text */
textview {
    font-size: 10pt;
}

/* Navigation/header bar */
headerbar {
    min-height: 48px;
}

headerbar > windowtitle > .title {
    font-size: 13pt;
    font-weight: bold;
}

/* Labels in content areas */
label {
    font-size: 11pt;
}

/* Dim labels slightly smaller but still readable */
label.dim-label {
    font-size: 10pt;
}

/* Link buttons */
linkbutton > label {
    font-size: 11pt;
}

/* Message dialogs */
messagedialog .heading {
    font-size: 14pt;
}

messagedialog .body {
    font-size: 11pt;
}

/* TuxFetch sidebar styles */
.tux-sidebar {
    background-color: @window_bg_color;
    border-left: 1px solid alpha(@borders, 0.5);
}

.tux-sidebar-scrollable {
    background-color: darker(@window_bg_color);
}

.tux-fetch-sidebar {
    background-color: transparent;
}

.tux-fetch-sidebar label {
    font-size: 10pt;
}

.tux-fetch-sidebar .dim-label {
    opacity: 0.7;
}

.sidebar-separator {
    margin-top: 8px;
    margin-bottom: 0px;
}

.tux-fetch-bar {
    min-height: 4px;
    border-radius: 2px;
}

.tux-fetch-bar trough {
    min-height: 4px;
    background-color: alpha(@borders, 0.3);
}

.tux-fetch-bar progress {
    min-height: 4px;
    background-color: @accent_bg_color;
}

/* Tux Tunes sidebar button */
.tux-tunes-sidebar-btn {
    padding: 12px 16px;
    border-radius: 12px;
    background: linear-gradient(135deg, alpha(@accent_bg_color, 0.2), alpha(@accent_bg_color, 0.1));
    border: 1px solid alpha(@accent_bg_color, 0.3);
}

.tux-tunes-sidebar-btn:hover {
    background: linear-gradient(135deg, alpha(@accent_bg_color, 0.3), alpha(@accent_bg_color, 0.2));
}

.tux-tunes-icon {
    font-size: 24pt;
}

.tux-tunes-title {
    font-size: 11pt;
    font-weight: bold;
}

.tux-tunes-subtitle {
    font-size: 9pt;
}

/* Global Claude AI panel */
.claude-global-panel {
    background-color: @card_bg_color;
    border-left: 1px solid alpha(@borders, 0.5);
}

.claude-toggle-btn {
    min-width: 36px;
    min-height: 36px;
}

.claude-toggle-btn.active {
    background-color: alpha(@accent_bg_color, 0.3);
}
"""


class TuxAssistantApp(Adw.Application):
    """Main application class."""
    
    def __init__(self):
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.HANDLES_OPEN
        )
        
        self.window = None
        self._pending_urls = []  # URLs to open after window is ready
        
        # Connect signals
        self.connect('activate', self.on_activate)
        self.connect('startup', self.on_startup)
        self.connect('open', self.on_open)
    
    def on_startup(self, app):
        """Called when the application starts."""
        # Register bundled icons with GTK icon theme
        self._register_bundled_icons()
        
        # Discover and register all modules
        ModuleRegistry.discover_modules()
        
        # Load custom CSS for larger UI
        self.load_css()
        
        # Set up actions
        self.create_actions()
        
        # Audio dependency check disabled - uncomment to re-enable:
        # GLib.idle_add(self._check_audio_dependencies)
    
    def _register_bundled_icons(self):
        """Register bundled icons with GTK's icon theme.
        
        This creates a proper icon theme structure at runtime so GTK can find
        our bundled icons even if they weren't installed to the system theme.
        """
        # Find the bundled icons directory
        icon_dirs = [
            # Installed to /opt (most common)
            '/opt/tux-assistant/assets/icons',
            # Running from source
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'assets', 'icons'),
            # Installed to /usr/share
            '/usr/share/tux-assistant/assets/icons',
            # Local install
            os.path.expanduser('~/.local/share/tux-assistant/assets/icons'),
        ]
        
        bundled_dir = None
        for icon_dir in icon_dirs:
            if os.path.isdir(icon_dir):
                bundled_dir = icon_dir
                break
        
        if not bundled_dir:
            return
        
        # Create a runtime icon theme directory structure
        runtime_theme_dir = os.path.expanduser('~/.local/share/icons/tux-runtime')
        scalable_dir = os.path.join(runtime_theme_dir, 'scalable', 'actions')
        
        try:
            os.makedirs(scalable_dir, exist_ok=True)
            
            # Create index.theme file
            index_path = os.path.join(runtime_theme_dir, 'index.theme')
            if not os.path.exists(index_path):
                with open(index_path, 'w') as f:
                    f.write("""[Icon Theme]
Name=Tux Runtime
Comment=Runtime icons for Tux Assistant
Inherits=hicolor
Directories=scalable/actions

[scalable/actions]
Size=16
MinSize=8
MaxSize=512
Type=Scalable
""")
            
            # Symlink all bundled icons to the runtime theme
            for icon_file in os.listdir(bundled_dir):
                if icon_file.endswith('.svg'):
                    src = os.path.join(bundled_dir, icon_file)
                    dst = os.path.join(scalable_dir, icon_file)
                    if not os.path.exists(dst):
                        try:
                            os.symlink(src, dst)
                        except OSError:
                            # Fall back to copy if symlink fails
                            import shutil
                            shutil.copy2(src, dst)
            
            # Add to icon theme search path
            icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
            icon_theme.add_search_path(os.path.expanduser('~/.local/share/icons'))
            
            # Also add hicolor as fallback (should already be there but ensure it)
            for path in ['/usr/share/icons', os.path.expanduser('~/.local/share/icons')]:
                if os.path.isdir(path):
                    icon_theme.add_search_path(path)
                    
        except Exception as e:
            # Non-fatal - icons will fall back to direct file loading
            pass
    
    def load_css(self):
        """Load custom CSS for improved readability."""
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(APP_CSS.encode())
        
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            css_provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )
    
    def on_activate(self, app):
        """Called when the application is activated."""
        if not self.window:
            self.window = TuxAssistantWindow(application=self)
        
        self.window.present()
        
        # Open any pending URLs after a brief delay (let browser initialize)
        if self._pending_urls:
            GLib.timeout_add(500, self._open_pending_urls)
    
    def on_open(self, app, files, n_files, hint):
        """Handle files/URLs passed to the application."""
        for gfile in files:
            uri = gfile.get_uri()
            # Check if it's a web URL
            if uri.startswith('http://') or uri.startswith('https://'):
                self._pending_urls.append(uri)
        
        # Activate the window (will also open pending URLs)
        self.activate()
    
    def _open_pending_urls(self):
        """Open pending URLs in the browser."""
        if self.window and self._pending_urls:
            for url in self._pending_urls:
                try:
                    if hasattr(self.window, '_browser_new_tab'):
                        # Show browser if needed
                        if hasattr(self.window, '_show_browser_docked'):
                            self.window._show_browser_docked()
                        self.window._browser_new_tab(url)
                except Exception as e:
                    print(f"Error opening URL {url}: {e}")
            self._pending_urls.clear()
        return False  # Don't repeat
    
    def create_actions(self):
        """Create application actions."""
        # Quit action
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", self.on_quit)
        self.add_action(quit_action)
        self.set_accels_for_action("app.quit", ["<Control>q"])
        
        # About action
        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self.on_about)
        self.add_action(about_action)
    
    def on_quit(self, action, param):
        """Handle quit action."""
        self.quit()
    
    def on_about(self, action, param):
        """Show about dialog."""
        distro = get_distro()
        desktop = get_desktop()
        
        # Count registered modules
        all_modules = ModuleRegistry.get_all_modules()
        
        # Calculate total lines of code
        module_stats = [
            ("Desktop Enhancements", "~3,900 lines"),
            ("Software Center", "~2,600 lines"),
            ("Networking", "~2,500 lines"),
            ("Setup Tools", "~900 lines"),
            ("Core Framework", "~600 lines"),
        ]
        
        about = Adw.AboutWindow(
            transient_for=self.window,
            application_name=__app_name__,
            application_icon="preferences-system",
            version=APP_VERSION,
            developer_name="Christopher Dorrell",
            copyright="© 2025 Christopher Dorrell",
            license_type=Gtk.License.CUSTOM,
            license="GPL-3.0",
            comments="A comprehensive GTK4/Libadwaita system configuration and management application for Linux.\n\nSupports Arch, Fedora, Debian/Ubuntu, openSUSE and derivatives.",
            website="https://github.com/dorrelkc/tux-assistant",
            issue_url="https://github.com/dorrelkc/tux-assistant/issues",
            debug_info=f"Version: {APP_VERSION}\n"
                      f"Distribution: {distro.name} ({distro.family.value})\n"
                      f"Desktop: {desktop.display_name} ({desktop.session_type})\n"
                      f"Package Manager: {distro.package_manager}\n"
                      f"Loaded Modules: {len(all_modules)}\n"
                      f"Total Code: ~10,500 lines",
            debug_info_filename="tux-assistant-debug.txt"
        )
        
        about.add_credit_section(
            "System Information",
            [
                f"Distribution: {distro.name}",
                f"Desktop: {desktop.display_name}",
                f"Display Server: {desktop.session_type.upper()}"
            ]
        )
        
        # List loaded modules
        if all_modules:
            about.add_credit_section(
                "Loaded Modules",
                [m.name for m in all_modules]
            )
        
        about.present()
    
    def _check_audio_dependencies(self):
        """Check and install audio analysis dependencies if missing."""
        import subprocess
        import threading
        
        # Check which modules are missing
        missing = []
        for module in ['numpy', 'scipy', 'librosa', 'pydub']:
            try:
                __import__(module)
            except ImportError:
                missing.append(module)
        
        if not missing:
            return False  # All good
        
        print(f"Tux Assistant: Missing audio deps: {missing}")
        
        def do_install():
            from .core import get_distro
            distro = get_distro()
            family = distro.family.value
            
            # System packages available in repos
            sys_pkg_map = {
                'arch': {'numpy': 'python-numpy', 'scipy': 'python-scipy'},
                'debian': {'numpy': 'python3-numpy', 'scipy': 'python3-scipy'},
                'fedora': {'numpy': 'python3-numpy', 'scipy': 'python3-scipy'},
                'opensuse': {'numpy': 'python3-numpy', 'scipy': 'python3-scipy'},
            }
            
            # Pip package for pip itself
            pip_pkg_map = {
                'arch': 'python-pip',
                'debian': 'python3-pip',
                'fedora': 'python3-pip',
                'opensuse': 'python3-pip',
            }
            
            # Package manager commands
            pkg_cmds = {
                'arch': ['pkexec', 'pacman', '-S', '--noconfirm', '--needed'],
                'debian': ['pkexec', 'apt-get', 'install', '-y'],
                'fedora': ['pkexec', 'dnf', 'install', '-y'],
                'opensuse': ['pkexec', 'zypper', 'install', '-y'],
            }
            
            pkg_cmd = pkg_cmds.get(family)
            sys_packages = sys_pkg_map.get(family, {})
            pip_pkg = pip_pkg_map.get(family)
            
            if not pkg_cmd:
                print(f"Tux Assistant: Unknown distro family {family}")
                return
            
            # Step 1: Install system packages (numpy, scipy)
            sys_to_install = []
            for mod in ['numpy', 'scipy']:
                if mod in missing and mod in sys_packages:
                    sys_to_install.append(sys_packages[mod])
            
            if sys_to_install:
                print(f"Tux Assistant: Installing system packages: {sys_to_install}")
                try:
                    result = subprocess.run(
                        pkg_cmd + sys_to_install,
                        capture_output=True, text=True, timeout=300
                    )
                    if result.returncode == 0:
                        print(f"Tux Assistant: Installed {sys_to_install}")
                    else:
                        print(f"Tux Assistant: Failed: {result.stderr[:150]}")
                except Exception as e:
                    print(f"Tux Assistant: Error: {e}")
            
            # Step 2: Install pip if we need pydub or librosa
            pip_needed = [m for m in missing if m in ['pydub', 'librosa']]
            if pip_needed and pip_pkg:
                print(f"Tux Assistant: Installing {pip_pkg}")
                try:
                    subprocess.run(pkg_cmd + [pip_pkg], capture_output=True, timeout=120)
                except:
                    pass
            
            # Step 3: Install pydub and librosa via pip
            for pkg in pip_needed:
                print(f"Tux Assistant: Installing {pkg} via pip")
                try:
                    result = subprocess.run(
                        [sys.executable, '-m', 'pip', 'install', '--user', '--break-system-packages', pkg],
                        capture_output=True, text=True, timeout=300
                    )
                    if result.returncode == 0:
                        print(f"Tux Assistant: Installed {pkg}")
                    else:
                        # Fallback without flag
                        result = subprocess.run(
                            [sys.executable, '-m', 'pip', 'install', '--user', pkg],
                            capture_output=True, text=True, timeout=300
                        )
                        if result.returncode == 0:
                            print(f"Tux Assistant: Installed {pkg}")
                        else:
                            print(f"Tux Assistant: Failed to install {pkg}: {result.stderr[:150]}")
                except Exception as e:
                    print(f"Tux Assistant: Error installing {pkg}: {e}")
            
            print("Tux Assistant: Audio dependency check complete")
        
        # Run in thread
        thread = threading.Thread(target=do_install)
        thread.start()
        
        return False


class TuxAssistantWindow(Adw.ApplicationWindow):
    """Main application window."""
    
    CONFIG_DIR = GLib.get_user_config_dir() + "/tux-assistant"
    CONFIG_FILE = CONFIG_DIR + "/window.conf"
    BOOKMARKS_FILE = CONFIG_DIR + "/bookmarks.json"
    HISTORY_DB = CONFIG_DIR + "/history.db"
    UPDATE_CHECK_FILE = CONFIG_DIR + "/update_check.json"
    GITHUB_RELEASES_URL = "https://api.github.com/repos/dorrellkc/Tux-Assistant/releases/latest"
    
    # History limits - designed for daily use over years
    HISTORY_MAX_SIZE_MB = 200  # Maximum database size
    HISTORY_MAX_ENTRIES = 500000  # Maximum entries
    HISTORY_CLEANUP_PERCENT = 20  # Delete this % when limit hit
    
    # Privacy blocklists - common ad and tracker domains
    AD_DOMAINS = {
        # Google Ads
        'doubleclick.net', 'googlesyndication.com', 'googleadservices.com',
        'googleads.g.doubleclick.net', 'pagead2.googlesyndication.com',
        'adservice.google.com', 'ads.google.com', 'tpc.googlesyndication.com',
        # Facebook/Meta
        'facebook.com/tr', 'connect.facebook.net', 'an.facebook.com',
        # Amazon
        'amazon-adsystem.com', 'aax.amazon-adsystem.com', 'z-na.amazon-adsystem.com',
        # Major ad networks
        'adsserver.com', 'adnxs.com', 'adsrvr.org', 'adtech.de',
        'advertising.com', 'adform.net', 'adroll.com', 'adfox.ru',
        'criteo.com', 'criteo.net', 'outbrain.com', 'outbrainimg.com',
        'taboola.com', 'taboola.net', 'mgid.com', 'revcontent.com',
        'pubmatic.com', 'rubiconproject.com', 'openx.net', 'contextweb.com',
        'bidswitch.net', 'casalemedia.com', 'media.net', 'medianet.com',
        'yieldmo.com', 'teads.tv', 'sharethrough.com', 'smartadserver.com',
        'moatads.com', 'adsafeprotected.com', 'doubleverify.com',
        'serving-sys.com', 'eyeota.net', 'liadm.com', 'rlcdn.com',
        'bluekai.com', 'krxd.net', 'exelator.com', 'demdex.net',
        'adzerk.net', 'adcolony.com', 'unity3d.com/ads', 'unityads.unity3d.com',
        'mopub.com', 'applovin.com', 'vungle.com', 'chartboost.com',
        # Tech/Dev site ad networks
        'carbonads.com', 'carbonads.net', 'srv.carbonads.net', 'cdn.carbonads.com',
        'buysellads.com', 'buysellads.net', 's3.buysellads.com',
        'adthrive.com', 'ads.adthrive.com',
        'mediavine.com', 'scripts.mediavine.com',
        'ezoic.net', 'ezoic.com', 'go.ezoic.net',
        'jeeng.com', 'sdk.jeeng.com',
        'ethicalads.io',
    }
    
    TRACKER_DOMAINS = {
        # Google Analytics/Tags
        'google-analytics.com', 'analytics.google.com', 'ssl.google-analytics.com',
        'googletagmanager.com', 'googletagservices.com', 'googlesyndication.com',
        # Facebook
        'facebook.net', 'pixel.facebook.com', 'connect.facebook.net',
        # Analytics platforms
        'hotjar.com', 'static.hotjar.com', 'mixpanel.com', 'api.mixpanel.com',
        'segment.io', 'segment.com', 'api.segment.io', 'cdn.segment.com',
        'amplitude.com', 'api.amplitude.com', 'heapanalytics.com',
        'fullstory.com', 'rs.fullstory.com', 'mouseflow.com', 'crazyegg.com',
        'luckyorange.com', 'clarity.ms', 'clicktale.net',
        # A/B Testing
        'optimizely.com', 'cdn.optimizely.com', 'abtasty.com', 'vwo.com',
        # Error tracking
        'newrelic.com', 'nr-data.net', 'sentry.io', 'bugsnag.com',
        'rollbar.com', 'loggly.com', 'track.js',
        # Chat/Support widgets
        'intercom.io', 'widget.intercom.io', 'drift.com', 'js.driftt.com',
        'crisp.chat', 'client.crisp.chat', 'zopim.com', 'tawk.to',
        'freshchat.com', 'wchat.freshchat.com',
        # Marketing automation
        'hubspot.com', 'hs-analytics.net', 'hsforms.com', 'js.hs-analytics.net',
        'marketo.com', 'munchkin.marketo.net', 'pardot.com', 'pi.pardot.com',
        # Audience measurement
        'scorecardresearch.com', 'quantserve.com', 'pixel.quantserve.com',
        'chartbeat.com', 'static.chartbeat.com', 'comscore.com', 'sb.scorecardresearch.com',
        'imrworldwide.com', 'Nielsen.com', 'secure-us.imrworldwide.com',
        # Other trackers
        'branch.io', 'app.link', 'adjust.com', 'app.adjust.com',
        'appsflyer.com', 'kochava.com', 'singular.net',
    }
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.set_title("Tux Assistant")
        
        # Load saved window size or use defaults
        width, height, maximized = self._load_window_size()
        self.set_default_size(width, height)
        if maximized:
            self.maximize()
        
        # Connect to size/state change signals to save on change
        self.connect("notify::default-width", self._on_size_changed)
        self.connect("notify::default-height", self._on_size_changed)
        self.connect("notify::maximized", self._on_state_changed)
        
        # Detect system info
        self.distro = get_distro()
        self.desktop = get_desktop()
        
        # Initialize bookmarks and folders
        self.bookmarks = []
        self.bookmark_folders = []  # List of folder names
        self._load_bookmarks()
        
        # Initialize downloads list
        self.downloads = []  # List of {download, destination, progress, status}
        
        # Initialize privacy settings
        browser_settings = self._load_browser_settings()
        self.force_https = browser_settings.get('force_https', True)
        self.block_ads = browser_settings.get('block_ads', True)
        self.block_trackers = browser_settings.get('block_trackers', True)
        self.pages_protected = 0  # Track protected pages this session
        
        # SponsorBlock settings
        self.sponsorblock_enabled = browser_settings.get('sponsorblock_enabled', True)
        self.sponsorblock_categories = browser_settings.get('sponsorblock_categories', 
            'sponsor,selfpromo,interaction,intro,outro')  # Default categories to skip
        print(f"[SponsorBlock] Initialized: enabled={self.sponsorblock_enabled}, categories={self.sponsorblock_categories}")
        
        # Read Aloud (TTS) settings
        self.tts_voice = browser_settings.get('tts_voice', 'en-US-ChristopherNeural')
        self.tts_rate = browser_settings.get('tts_rate', '+0%')  # -50% to +100%
        self.tts_process = None  # Track running TTS process
        self.tts_playing = False  # Track if TTS is actively playing/generating
        self.tts_audio_file = None  # Track temp audio file
        print(f"[TTS] Initialized: voice={self.tts_voice}, rate={self.tts_rate}")
        
        # Initialize content filter store for ad blocking
        self.content_filter_store = None
        self.content_filters = []  # List of compiled filters
        self._init_content_filters()
        
        # Initialize history database
        self._init_history_db()
        
        # Build UI
        self.build_ui()
        
        # Check for updates (non-blocking)
        self._check_for_updates()
        
        # Window-level keyboard handler for F11 (fullscreen)
        window_key_controller = Gtk.EventControllerKey()
        window_key_controller.connect("key-pressed", self._on_window_key_pressed)
        self.add_controller(window_key_controller)
    
    def _on_window_key_pressed(self, controller, keyval, keycode, state):
        """Handle window-level keyboard shortcuts."""
        # F11: Toggle fullscreen
        if keyval == Gdk.KEY_F11:
            self._toggle_fullscreen()
            return True
        
        return False
    
    def _get_available_icon(self, icon_names: list, fallback: str) -> str:
        """Find first available icon from a list of candidates.
        
        Args:
            icon_names: List of icon names to try in order
            fallback: Icon name to use if none found
            
        Returns:
            First available icon name, or fallback
        """
        icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        
        for icon_name in icon_names:
            if icon_theme.has_icon(icon_name):
                return icon_name
        
        return fallback
    
    def _load_window_size(self) -> tuple[int, int, bool]:
        """Load saved window size from config file."""
        import os
        
        default_width, default_height = 1280, 850  # Wider to show TuxFetch panel
        maximized = False
        
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if '=' in line:
                            key, value = line.split('=', 1)
                            if key == 'width':
                                default_width = max(800, min(3000, int(value)))
                            elif key == 'height':
                                default_height = max(600, min(2000, int(value)))
                            elif key == 'maximized':
                                maximized = value.lower() == 'true'
        except Exception:
            pass  # Use defaults on any error
        
        return default_width, default_height, maximized
    
    def _save_window_size(self):
        """Save current window size to config file."""
        import os
        
        try:
            # Create config directory if needed
            os.makedirs(self.CONFIG_DIR, exist_ok=True)
            
            # Get current size (only if not maximized)
            width = self.get_width()
            height = self.get_height()
            maximized = self.is_maximized()
            
            # Don't save tiny sizes (probably minimized or hidden)
            if width < 100 or height < 100:
                return
            
            with open(self.CONFIG_FILE, 'w') as f:
                f.write(f"width={width}\n")
                f.write(f"height={height}\n")
                f.write(f"maximized={str(maximized).lower()}\n")
        except Exception:
            pass  # Silently fail - not critical
    
    def _on_size_changed(self, widget, param):
        """Handle window size change."""
        # Don't save while maximized (we want to remember the unmaximized size)
        if not self.is_maximized():
            self._save_window_size()
    
    def _on_state_changed(self, widget, param):
        """Handle window state change (maximized/unmaximized)."""
        self._save_window_size()
    
    def _load_bookmarks(self):
        """Load bookmarks and folders from JSON file."""
        import json
        import os
        
        try:
            if os.path.exists(self.BOOKMARKS_FILE):
                with open(self.BOOKMARKS_FILE, 'r') as f:
                    data = json.load(f)
                    
                # Handle both old format (list) and new format (dict with folders)
                if isinstance(data, list):
                    # Old format - just bookmarks list
                    self.bookmarks = data
                    self.bookmark_folders = []
                elif isinstance(data, dict):
                    # New format with folders
                    self.bookmarks = data.get('bookmarks', [])
                    self.bookmark_folders = data.get('folders', [])
                else:
                    self.bookmarks = []
                    self.bookmark_folders = []
        except Exception:
            self.bookmarks = []
            self.bookmark_folders = []
    
    def _save_bookmarks(self):
        """Save bookmarks and folders to JSON file."""
        import json
        import os
        
        try:
            os.makedirs(self.CONFIG_DIR, exist_ok=True)
            data = {
                'bookmarks': self.bookmarks,
                'folders': self.bookmark_folders
            }
            with open(self.BOOKMARKS_FILE, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to save bookmarks: {e}")
    
    # ==================== History Database Methods ====================
    
    def _init_history_db(self):
        """Initialize the history SQLite database."""
        try:
            os.makedirs(self.CONFIG_DIR, exist_ok=True)
            
            conn = sqlite3.connect(self.HISTORY_DB)
            cursor = conn.cursor()
            
            # Create history table with frecency support
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT NOT NULL UNIQUE,
                    title TEXT,
                    visit_count INTEGER DEFAULT 1,
                    last_visit REAL NOT NULL,
                    first_visit REAL NOT NULL,
                    frecency INTEGER DEFAULT 0
                )
            ''')
            
            # Indexes for fast queries
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_url ON history(url)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_last_visit ON history(last_visit DESC)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_frecency ON history(frecency DESC)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_history_title ON history(title)')
            
            conn.commit()
            conn.close()
            
            # Check if maintenance needed (in background)
            threading.Thread(target=self._check_history_maintenance, daemon=True).start()
            
        except Exception as e:
            print(f"Failed to initialize history database: {e}")
    
    def _record_history(self, url, title=None):
        """Record a page visit to history with frecency update."""
        if not url or url.startswith('about:') or url.startswith('data:'):
            return
        
        import time
        now = time.time()
        
        try:
            conn = sqlite3.connect(self.HISTORY_DB)
            cursor = conn.cursor()
            
            # Check if URL exists
            cursor.execute('SELECT id, visit_count, first_visit FROM history WHERE url = ?', (url,))
            existing = cursor.fetchone()
            
            if existing:
                # Update existing entry
                entry_id, visit_count, first_visit = existing
                new_count = visit_count + 1
                frecency = self._calculate_frecency(new_count, now, first_visit)
                
                cursor.execute('''
                    UPDATE history 
                    SET title = COALESCE(?, title),
                        visit_count = ?,
                        last_visit = ?,
                        frecency = ?
                    WHERE id = ?
                ''', (title, new_count, now, frecency, entry_id))
            else:
                # Insert new entry
                frecency = self._calculate_frecency(1, now, now)
                cursor.execute('''
                    INSERT INTO history (url, title, visit_count, last_visit, first_visit, frecency)
                    VALUES (?, ?, 1, ?, ?, ?)
                ''', (url, title or url, now, now, frecency))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            print(f"Failed to record history: {e}")
    
    def _calculate_frecency(self, visit_count, last_visit, first_visit):
        """
        Calculate frecency score (frequency × recency).
        Higher score = more relevant for autocomplete.
        
        Formula inspired by Firefox:
        - Recent visits worth more
        - Frequent visits compound
        - Decay over time
        """
        import time
        now = time.time()
        
        # Time buckets (in seconds)
        HOUR = 3600
        DAY = 86400
        WEEK = 604800
        MONTH = 2592000
        
        # Age of last visit
        age = now - last_visit
        
        # Recency weight (more recent = higher)
        if age < HOUR:
            recency_weight = 100
        elif age < DAY:
            recency_weight = 70
        elif age < WEEK:
            recency_weight = 50
        elif age < MONTH:
            recency_weight = 30
        else:
            recency_weight = 10
        
        # Frequency bonus (caps at reasonable level)
        frequency_bonus = min(visit_count * 10, 200)
        
        # Combined score
        return recency_weight + frequency_bonus
    
    def _get_history(self, limit=50, offset=0, search=None, time_filter=None):
        """
        Get history entries.
        
        Args:
            limit: Maximum entries to return
            offset: Pagination offset
            search: Search term for URL/title
            time_filter: 'today', 'yesterday', 'week', 'month', or None for all
        
        Returns:
            List of dicts: [{url, title, visit_count, last_visit, frecency}, ...]
        """
        import time
        
        try:
            conn = sqlite3.connect(self.HISTORY_DB)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = 'SELECT url, title, visit_count, last_visit, frecency FROM history'
            params = []
            conditions = []
            
            # Time filter
            if time_filter:
                now = time.time()
                today_start = now - (now % 86400)  # Start of today (UTC)
                
                if time_filter == 'today':
                    conditions.append('last_visit >= ?')
                    params.append(today_start)
                elif time_filter == 'yesterday':
                    conditions.append('last_visit >= ? AND last_visit < ?')
                    params.extend([today_start - 86400, today_start])
                elif time_filter == 'week':
                    conditions.append('last_visit >= ?')
                    params.append(now - 604800)
                elif time_filter == 'month':
                    conditions.append('last_visit >= ?')
                    params.append(now - 2592000)
            
            # Search filter
            if search:
                conditions.append('(url LIKE ? OR title LIKE ?)')
                search_term = f'%{search}%'
                params.extend([search_term, search_term])
            
            if conditions:
                query += ' WHERE ' + ' AND '.join(conditions)
            
            query += ' ORDER BY last_visit DESC LIMIT ? OFFSET ?'
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            results = [dict(row) for row in cursor.fetchall()]
            
            conn.close()
            return results
            
        except Exception as e:
            print(f"Failed to get history: {e}")
            return []
    
    def _get_history_suggestions(self, query, limit=8):
        """Get history suggestions for URL autocomplete, ranked by frecency."""
        if not query or len(query) < 2:
            return []
        
        try:
            conn = sqlite3.connect(self.HISTORY_DB)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Search by URL or title, order by frecency
            search_term = f'%{query}%'
            cursor.execute('''
                SELECT url, title, frecency 
                FROM history 
                WHERE url LIKE ? OR title LIKE ?
                ORDER BY frecency DESC
                LIMIT ?
            ''', (search_term, search_term, limit))
            
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return results
            
        except Exception as e:
            print(f"Failed to get history suggestions: {e}")
            return []
    
    def _get_history_count(self):
        """Get total number of history entries."""
        try:
            conn = sqlite3.connect(self.HISTORY_DB)
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM history')
            count = cursor.fetchone()[0]
            conn.close()
            return count
        except:
            return 0
    
    def _delete_history_entry(self, url):
        """Delete a single history entry."""
        try:
            conn = sqlite3.connect(self.HISTORY_DB)
            cursor = conn.cursor()
            cursor.execute('DELETE FROM history WHERE url = ?', (url,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Failed to delete history entry: {e}")
            return False
    
    def _delete_history_entries(self, urls):
        """Delete multiple history entries."""
        try:
            conn = sqlite3.connect(self.HISTORY_DB)
            cursor = conn.cursor()
            cursor.executemany('DELETE FROM history WHERE url = ?', [(url,) for url in urls])
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Failed to delete history entries: {e}")
            return False
    
    def _clear_history(self, time_range='all'):
        """
        Clear history for a time range.
        
        Args:
            time_range: 'hour', 'today', 'all'
        """
        import time
        
        try:
            conn = sqlite3.connect(self.HISTORY_DB)
            cursor = conn.cursor()
            
            if time_range == 'all':
                cursor.execute('DELETE FROM history')
            elif time_range == 'hour':
                cutoff = time.time() - 3600
                cursor.execute('DELETE FROM history WHERE last_visit >= ?', (cutoff,))
            elif time_range == 'today':
                now = time.time()
                today_start = now - (now % 86400)
                cursor.execute('DELETE FROM history WHERE last_visit >= ?', (today_start,))
            
            conn.commit()
            conn.close()
            
            # VACUUM in background to reclaim space
            threading.Thread(target=self._vacuum_history_db, daemon=True).start()
            
            return True
        except Exception as e:
            print(f"Failed to clear history: {e}")
            return False
    
    def _check_history_maintenance(self):
        """Check if history database needs maintenance (size/entry limits)."""
        try:
            # Check file size
            if os.path.exists(self.HISTORY_DB):
                size_mb = os.path.getsize(self.HISTORY_DB) / (1024 * 1024)
                if size_mb > self.HISTORY_MAX_SIZE_MB:
                    print(f"History DB size ({size_mb:.1f}MB) exceeds limit, cleaning...")
                    self._cleanup_old_history()
                    return
            
            # Check entry count
            count = self._get_history_count()
            if count > self.HISTORY_MAX_ENTRIES:
                print(f"History entries ({count}) exceeds limit, cleaning...")
                self._cleanup_old_history()
                
        except Exception as e:
            print(f"History maintenance check failed: {e}")
    
    def _cleanup_old_history(self):
        """Delete oldest entries to stay within limits."""
        try:
            conn = sqlite3.connect(self.HISTORY_DB)
            cursor = conn.cursor()
            
            # Get count
            cursor.execute('SELECT COUNT(*) FROM history')
            count = cursor.fetchone()[0]
            
            # Delete oldest 20%
            delete_count = int(count * self.HISTORY_CLEANUP_PERCENT / 100)
            if delete_count > 0:
                cursor.execute('''
                    DELETE FROM history WHERE id IN (
                        SELECT id FROM history ORDER BY last_visit ASC LIMIT ?
                    )
                ''', (delete_count,))
                conn.commit()
                print(f"Cleaned up {delete_count} old history entries")
            
            conn.close()
            
            # VACUUM to reclaim space
            self._vacuum_history_db()
            
        except Exception as e:
            print(f"History cleanup failed: {e}")
    
    def _vacuum_history_db(self):
        """Reclaim space in history database (run in background thread)."""
        try:
            conn = sqlite3.connect(self.HISTORY_DB)
            conn.execute('VACUUM')
            conn.close()
        except Exception as e:
            print(f"History VACUUM failed: {e}")
    
    # ==================== End History Methods ====================
    
    def _load_browser_settings(self):
        """Load browser settings from config file."""
        import os
        
        settings = {
            'bookmarks_bar_visible': True,
            'zoom_level': 1.0,
            'force_https': True,
            'block_ads': True,
            'block_trackers': True,
            'homepage': 'https://duckduckgo.com',
            'search_engine': 'DuckDuckGo',
            'default_zoom': 1.0,
            'sponsorblock_enabled': True,
            'sponsorblock_categories': 'sponsor,selfpromo,interaction,intro,outro',
            'tts_voice': 'en-US-ChristopherNeural',
            'tts_rate': '+0%'
        }
        
        try:
            pref_file = os.path.join(self.CONFIG_DIR, 'browser.conf')
            if os.path.exists(pref_file):
                with open(pref_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if '=' in line:
                            key, value = line.split('=', 1)
                            if key == 'bookmarks_bar_visible':
                                settings['bookmarks_bar_visible'] = value.lower() == 'true'
                            elif key == 'zoom_level':
                                settings['zoom_level'] = float(value)
                            elif key == 'force_https':
                                settings['force_https'] = value.lower() == 'true'
                            elif key == 'block_ads':
                                settings['block_ads'] = value.lower() == 'true'
                            elif key == 'block_trackers':
                                settings['block_trackers'] = value.lower() == 'true'
                            elif key == 'homepage':
                                settings['homepage'] = value
                            elif key == 'search_engine':
                                settings['search_engine'] = value
                            elif key == 'default_zoom':
                                settings['default_zoom'] = float(value)
                            elif key == 'sponsorblock_enabled':
                                settings['sponsorblock_enabled'] = value.lower() == 'true'
                            elif key == 'sponsorblock_categories':
                                settings['sponsorblock_categories'] = value
                            elif key == 'tts_voice':
                                settings['tts_voice'] = value
                            elif key == 'tts_rate':
                                settings['tts_rate'] = value
        except:
            pass
        return settings
    
    def _save_browser_settings(self, **kwargs):
        """Save browser settings to config file."""
        import os
        
        # Load existing settings first
        settings = self._load_browser_settings()
        settings.update(kwargs)
        
        try:
            os.makedirs(self.CONFIG_DIR, exist_ok=True)
            pref_file = os.path.join(self.CONFIG_DIR, 'browser.conf')
            with open(pref_file, 'w') as f:
                for key, value in settings.items():
                    if isinstance(value, bool):
                        f.write(f"{key}={'true' if value else 'false'}\n")
                    else:
                        f.write(f"{key}={value}\n")
        except:
            pass
    
    def _load_bookmarks_bar_visible(self):
        """Load bookmarks bar visibility preference."""
        return self._load_browser_settings()['bookmarks_bar_visible']
    
    def _save_bookmarks_bar_visible(self, visible):
        """Save bookmarks bar visibility preference."""
        self._save_browser_settings(bookmarks_bar_visible=visible)
    
    def _load_zoom_level(self):
        """Load saved zoom level."""
        return self._load_browser_settings()['zoom_level']
    
    def _save_zoom_level(self, level):
        """Save zoom level."""
        self._save_browser_settings(zoom_level=level)
    
    def _on_bookmarks_bar_toggle(self, switch, param):
        """Handle bookmarks bar visibility toggle."""
        visible = switch.get_active()
        if hasattr(self, 'bookmarks_bar_container'):
            self.bookmarks_bar_container.set_visible(visible)
        self._save_bookmarks_bar_visible(visible)
    
    def _on_width_changed_for_panel(self, widget, param):
        """Show/hide TuxFetch panel based on window width."""
        if hasattr(self, 'tux_fetch_panel'):
            width = self.get_width()
            # Hide panel on narrow windows (< 900px)
            if width < 900:
                self.tux_fetch_panel.set_visible(False)
            else:
                self.tux_fetch_panel.set_visible(True)
    
    def build_ui(self):
        """Build the main user interface."""
        import os
        
        # Main layout
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(self.main_box)
        
        # Header bar
        header = Adw.HeaderBar()
        
        # Version label on the left
        version_label = Gtk.Label()
        version_label.set_markup(f"<small>v{APP_VERSION}</small>")
        version_label.add_css_class("dim-label")
        header.pack_start(version_label)
        
        # Getting Started button
        getting_started_btn = Gtk.Button(label="Getting Started")
        getting_started_btn.set_tooltip_text("Quick guide to using Tux Assistant")
        getting_started_btn.connect("clicked", self._show_getting_started)
        header.pack_start(getting_started_btn)
        
        # Install to System button (only show if running portable)
        if self._is_running_portable() and not self._is_installed():
            install_btn = Gtk.Button(label="Install to System")
            install_btn.add_css_class("suggested-action")
            install_btn.set_tooltip_text("Install Tux Assistant permanently")
            install_btn.connect("clicked", self._on_install_to_system)
            header.pack_start(install_btn)
        
        # Menu button on the right
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("tux-open-menu-symbolic")
        menu_button.set_menu_model(self.create_menu())
        header.pack_end(menu_button)
        
        # Update indicator button (hidden by default, shows when update available)
        self.update_button = Gtk.MenuButton()
        self.update_button.set_icon_name("tux-software-update-available-symbolic")
        self.update_button.set_tooltip_text("Update available!")
        self.update_button.add_css_class("suggested-action")
        self.update_button.set_visible(False)
        self._setup_update_popover()
        header.pack_end(self.update_button)
        
        # Weather widget (before other toggle buttons)
        if ENABLE_WEATHER_WIDGET:
            try:
                from .ui.weather_widget import WeatherWidget
                self.weather_widget = WeatherWidget(self)
                header.pack_end(self.weather_widget)
            except Exception as e:
                print(f"Weather widget failed to load: {e}")
        
        # Claude AI toggle button (only if WebKit available)
        if WEBKIT_AVAILABLE:
            # Browser toggle button
            self.browser_toggle_btn = Gtk.ToggleButton()
            # Use our bundled icon - guaranteed to exist on all systems
            self.browser_toggle_btn.set_icon_name("tux-browser")
            self.browser_toggle_btn.set_tooltip_text("Toggle Web Browser")
            self.browser_toggle_btn.add_css_class("claude-toggle-btn")
            self.browser_toggle_btn.connect("toggled", self._on_browser_toggle)
            header.pack_end(self.browser_toggle_btn)
            
            # Claude AI toggle button
            self.claude_toggle_btn = Gtk.ToggleButton()
            self.claude_toggle_btn.set_icon_name("tux-user-available-symbolic")
            self.claude_toggle_btn.set_tooltip_text("Toggle Claude AI Assistant")
            self.claude_toggle_btn.add_css_class("claude-toggle-btn")
            self.claude_toggle_btn.connect("toggled", self._on_claude_toggle)
            header.pack_end(self.claude_toggle_btn)
        
        # Tux Tunes button (always available)
        tux_tunes_btn = Gtk.Button()
        tux_tunes_btn.set_icon_name("tux-audio-headphones-symbolic")
        tux_tunes_btn.set_tooltip_text("Launch Tux Tunes - Internet Radio")
        tux_tunes_btn.add_css_class("claude-toggle-btn")
        tux_tunes_btn.connect("clicked", self._on_tux_tunes_clicked)
        header.pack_end(tux_tunes_btn)
        
        self.main_box.append(header)
        
        # Toast overlay for notifications
        self.toast_overlay = Adw.ToastOverlay()
        self.main_box.append(self.toast_overlay)
        
        # Main content paned (navigation on left, Claude panel on right)
        self.main_paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.main_paned.set_shrink_start_child(False)
        self.main_paned.set_shrink_end_child(False)
        self.main_paned.set_resize_start_child(True)
        self.main_paned.set_resize_end_child(False)
        self.toast_overlay.set_child(self.main_paned)
        
        # Navigation view for page switching (left side)
        self.navigation_view = Adw.NavigationView()
        self.main_paned.set_start_child(self.navigation_view)
        
        # Claude AI panel (right side, initially hidden)
        self.claude_panel = None
        self.claude_panel_visible = False
        self.claude_is_docked = False
        self.claude_window = None
        
        # Browser panel (right side, initially hidden)
        self.browser_panel = None
        self.browser_panel_visible = False
        self.browser_is_docked = False
        self.browser_window = None
        
        # Track which panel is currently docked
        self.docked_panel = None  # 'claude', 'browser', or None
        
        if WEBKIT_AVAILABLE:
            self._build_global_claude_panel()
            # Browser panel built lazily when first opened
        
        # Create main page
        main_page = self.create_main_page()
        self.navigation_view.add(main_page)
    
    def _is_running_portable(self) -> bool:
        """Check if running from portable/temporary location."""
        import os
        return os.environ.get('TUX_ASSISTANT_PORTABLE', '') == '1'
    
    def _is_installed(self) -> bool:
        """Check if Tux Assistant is installed to system."""
        import os
        return os.path.exists('/opt/tux-assistant/tux-assistant.py')
    
    def _build_global_claude_panel(self):
        """Build the global Claude AI panel (hidden by default)."""
        # Create panel container
        self.claude_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.claude_panel.set_size_request(400, -1)
        self.claude_panel.add_css_class("claude-global-panel")
        
        # Panel header
        panel_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        panel_header.set_margin_top(12)
        panel_header.set_margin_bottom(8)
        panel_header.set_margin_start(12)
        panel_header.set_margin_end(12)
        self.claude_panel.append(panel_header)
        
        # Title with icon
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title_box.set_hexpand(True)
        
        icon_label = Gtk.Label(label="🤖")
        title_box.append(icon_label)
        
        title_label = Gtk.Label(label="Claude AI")
        title_label.add_css_class("title")
        title_box.append(title_label)
        
        panel_header.append(title_box)
        
        # External browser button
        external_btn = Gtk.Button.new_from_icon_name("tux-web-browser-symbolic")
        external_btn.set_tooltip_text("Open in external browser")
        external_btn.connect("clicked", self._on_claude_external)
        panel_header.append(external_btn)
        
        # Navigation toolbar
        nav_toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        nav_toolbar.set_margin_start(12)
        nav_toolbar.set_margin_end(12)
        nav_toolbar.set_margin_bottom(8)
        self.claude_panel.append(nav_toolbar)
        
        # Back button
        back_btn = Gtk.Button.new_from_icon_name("tux-go-previous-symbolic")
        back_btn.set_tooltip_text("Go back")
        back_btn.connect("clicked", lambda b: self.claude_webview.go_back() if hasattr(self, 'claude_webview') else None)
        nav_toolbar.append(back_btn)
        
        # Forward button
        forward_btn = Gtk.Button.new_from_icon_name("tux-go-next-symbolic")
        forward_btn.set_tooltip_text("Go forward")
        forward_btn.connect("clicked", lambda b: self.claude_webview.go_forward() if hasattr(self, 'claude_webview') else None)
        nav_toolbar.append(forward_btn)
        
        # Reload button
        reload_btn = Gtk.Button.new_from_icon_name("tux-view-refresh-symbolic")
        reload_btn.set_tooltip_text("Reload")
        reload_btn.connect("clicked", lambda b: self.claude_webview.reload() if hasattr(self, 'claude_webview') else None)
        nav_toolbar.append(reload_btn)
        
        # Home button
        home_btn = Gtk.Button.new_from_icon_name("tux-go-home-symbolic")
        home_btn.set_tooltip_text("Go to Claude.ai")
        home_btn.connect("clicked", lambda b: self.claude_webview.load_uri("https://claude.ai") if hasattr(self, 'claude_webview') else None)
        nav_toolbar.append(home_btn)
        
        # Create WebView
        self.claude_network_session = None
        try:
            if hasattr(WebKit, 'NetworkSession'):
                data_dir = os.path.join(GLib.get_user_data_dir(), 'tux-assistant', 'webview')
                cache_dir = os.path.join(GLib.get_user_cache_dir(), 'tux-assistant', 'webview')
                os.makedirs(data_dir, exist_ok=True)
                os.makedirs(cache_dir, exist_ok=True)
                
                self.claude_network_session = WebKit.NetworkSession.new(data_dir, cache_dir)
                
                cookie_manager = self.claude_network_session.get_cookie_manager()
                cookie_manager.set_accept_policy(WebKit.CookieAcceptPolicy.ALWAYS)
                cookie_manager.set_persistent_storage(
                    os.path.join(data_dir, 'cookies.sqlite'),
                    WebKit.CookiePersistentStorage.SQLITE
                )
                
                self.claude_webview = WebKit.WebView(network_session=self.claude_network_session)
                
                # Set up download handling
                self.claude_network_session.connect('download-started', self._on_claude_download_started)
            else:
                self.claude_webview = WebKit.WebView()
                try:
                    context = self.claude_webview.get_context()
                    context.connect('download-started', self._on_claude_download_started)
                except:
                    pass
        except Exception as e:
            print(f"WebKit setup error: {e}")
            self.claude_webview = WebKit.WebView()
        
        self.claude_webview.set_vexpand(True)
        self.claude_webview.set_hexpand(True)
        
        # Configure settings
        settings = self.claude_webview.get_settings()
        settings.set_enable_javascript(True)
        settings.set_javascript_can_open_windows_automatically(False)
        
        for method, value in [
            ('set_enable_html5_database', True),
            ('set_enable_html5_local_storage', True),
            ('set_enable_page_cache', True),
            ('set_enable_smooth_scrolling', True),
            ('set_enable_webgl', True),
            ('set_enable_media', True),
            ('set_enable_mediasource', True),
            ('set_enable_encrypted_media', True),
        ]:
            try:
                getattr(settings, method)(value)
            except:
                pass
        
        try:
            settings.set_hardware_acceleration_policy(WebKit.HardwareAccelerationPolicy.ALWAYS)
        except:
            pass
        
        # GNOME Web-style user agent (passes Cloudflare!)
        settings.set_user_agent(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
        )
        
        # Handle external links - open in default browser
        self.claude_webview.connect("decide-policy", self._on_webview_decide_policy)
        
        # Handle links that try to open new windows
        self.claude_webview.connect("create", self._on_browser_create_window)
        
        # Frame around webview
        webview_frame = Gtk.Frame()
        webview_frame.set_margin_start(12)
        webview_frame.set_margin_end(12)
        webview_frame.set_margin_bottom(12)
        webview_frame.set_child(self.claude_webview)
        webview_frame.set_vexpand(True)
        self.claude_panel.append(webview_frame)
        
        # Don't add to paned yet - starts hidden
        self.claude_panel_visible = False
    
    def _on_claude_toggle(self, button):
        """Toggle Claude AI panel visibility."""
        if not hasattr(self, 'claude_panel') or self.claude_panel is None:
            return
        
        if button.get_active():
            # Show Claude
            button.add_css_class("active")
            
            # Load Claude if not already loaded
            uri = self.claude_webview.get_uri()
            if not uri or uri == "about:blank":
                self.claude_webview.load_uri("https://claude.ai")
            
            # Check if browser is using the side panel
            if self.docked_panel == 'browser':
                # Browser has the panel - open Claude as floating window
                self._show_claude_floating()
            else:
                # Panel is free - dock Claude
                self._show_claude_docked()
        else:
            # Hide Claude
            button.remove_css_class("active")
            
            if self.claude_is_docked:
                self.main_paned.set_end_child(None)
                self.docked_panel = None
                self.claude_is_docked = False
            
            if self.claude_window:
                self.claude_window.close()
                self.claude_window = None
            
            self.claude_panel_visible = False
    
    def _on_webview_decide_policy(self, webview, decision, decision_type):
        """Handle navigation policy - open external links in default browser."""
        if decision_type == WebKit.PolicyDecisionType.NAVIGATION_ACTION:
            nav_action = decision.get_navigation_action()
            request = nav_action.get_request()
            uri = request.get_uri()
            
            if uri:
                # Allow claude.ai navigation within webview
                if 'claude.ai' in uri or uri.startswith('about:'):
                    decision.use()
                    return False
                
                # Open external links in default browser
                try:
                    import subprocess
                    subprocess.Popen(['xdg-open', uri])
                    decision.ignore()
                    return True
                except Exception as e:
                    print(f"Failed to open external link: {e}")
                    decision.use()
                    return False
        
        decision.use()
        return False
    
    def _show_claude_docked(self):
        """Show Claude in the docked panel."""
        # Make sure it's in the panel
        if self.claude_panel.get_parent():
            self.claude_panel.get_parent().remove(self.claude_panel)
        
        self.main_paned.set_end_child(self.claude_panel)
        self.docked_panel = 'claude'
        self.claude_is_docked = True
        self.claude_panel_visible = True
    
    def _show_claude_floating(self):
        """Show Claude in a floating window."""
        if self.claude_window:
            self.claude_window.present()
            return
        
        # Remove from panel if docked
        if self.claude_panel.get_parent():
            self.claude_panel.get_parent().remove(self.claude_panel)
        
        # Create floating window
        self.claude_window = Gtk.Window()
        self.claude_window.set_title("Claude AI")
        self.claude_window.set_default_size(500, 700)
        self.claude_window.set_modal(False)
        self.claude_window.set_decorated(True)
        self.claude_window.set_child(self.claude_panel)
        self.claude_window.connect("close-request", self._on_claude_window_close)
        self.claude_window.present()
        
        self.claude_is_docked = False
        self.claude_panel_visible = True
    
    def _on_claude_window_close(self, window):
        """Handle Claude floating window close."""
        # Remove panel from window before closing
        window.set_child(None)
        self.claude_window = None
        self.claude_is_docked = False
        self.claude_panel_visible = False
        
        # Untoggle the button
        if hasattr(self, 'claude_toggle_btn'):
            self.claude_toggle_btn.set_active(False)
        
        return False  # Allow close
    
    def _on_claude_external(self, button):
        """Open Claude in external browser."""
        Gtk.show_uri(None, "https://claude.ai", Gdk.CURRENT_TIME)
    
    def _build_global_browser_panel(self):
        """Build the global web browser panel."""
        # Create panel container
        self.browser_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.browser_panel.set_size_request(400, -1)
        self.browser_panel.add_css_class("claude-global-panel")
        
        # Panel header
        self.browser_home_url = self._load_browser_settings().get('homepage', 'https://duckduckgo.com')
        self.browser_panel_visible = False
        
        # Panel header
        panel_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        panel_header.set_margin_top(12)
        panel_header.set_margin_bottom(8)
        panel_header.set_margin_start(12)
        panel_header.set_margin_end(12)
        self.browser_panel.append(panel_header)
        
        # Title with icon
        title_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        title_box.set_hexpand(True)
        
        icon_label = Gtk.Label(label="🌐")
        title_box.append(icon_label)
        
        title_label = Gtk.Label(label="Tux Browser")
        title_label.add_css_class("title")
        title_box.append(title_label)
        
        panel_header.append(title_box)
        
        # Pop-out button
        popout_btn = Gtk.Button.new_from_icon_name("tux-window-new-symbolic")
        popout_btn.set_tooltip_text("Pop out to window")
        popout_btn.connect("clicked", self._on_browser_popout)
        panel_header.append(popout_btn)
        
        # Navigation toolbar with URL bar
        nav_toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        nav_toolbar.set_margin_start(12)
        nav_toolbar.set_margin_end(12)
        nav_toolbar.set_margin_bottom(4)
        self.browser_panel.append(nav_toolbar)
        
        # Back button
        back_btn = Gtk.Button.new_from_icon_name("tux-go-previous-symbolic")
        back_btn.set_tooltip_text("Go back")
        back_btn.connect("clicked", lambda b: self._get_current_browser_webview().go_back() if self._get_current_browser_webview() else None)
        nav_toolbar.append(back_btn)
        
        # Forward button
        forward_btn = Gtk.Button.new_from_icon_name("tux-go-next-symbolic")
        forward_btn.set_tooltip_text("Go forward")
        forward_btn.connect("clicked", lambda b: self._get_current_browser_webview().go_forward() if self._get_current_browser_webview() else None)
        nav_toolbar.append(forward_btn)
        
        # Reload button
        reload_btn = Gtk.Button.new_from_icon_name("tux-view-refresh-symbolic")
        reload_btn.set_tooltip_text("Reload")
        reload_btn.connect("clicked", lambda b: self._get_current_browser_webview().reload() if self._get_current_browser_webview() else None)
        nav_toolbar.append(reload_btn)
        
        # Home button
        home_btn = Gtk.Button.new_from_icon_name("tux-go-home-symbolic")
        home_btn.set_tooltip_text("Go to home page")
        home_btn.connect("clicked", self._on_browser_home)
        nav_toolbar.append(home_btn)
        
        # URL bar with autocomplete
        self.browser_url_entry = Gtk.Entry()
        self.browser_url_entry.set_hexpand(True)
        self.browser_url_entry.set_placeholder_text("Enter URL or search...")
        self.browser_url_entry.connect("activate", self._on_browser_url_activate)
        self.browser_url_entry.connect("changed", self._on_url_entry_changed)
        nav_toolbar.append(self.browser_url_entry)
        
        # Autocomplete popover and controllers created lazily
        self.url_autocomplete_popover = None
        self.url_autocomplete_list = None
        self._autocomplete_active = False
        self._url_controllers_added = False
        
        # Go button
        go_btn = Gtk.Button.new_from_icon_name("tux-go-next-symbolic")
        go_btn.set_tooltip_text("Go")
        go_btn.connect("clicked", lambda b: self._on_browser_url_activate(self.browser_url_entry))
        nav_toolbar.append(go_btn)
        
        # Bookmark star button (add/remove current page)
        self.bookmark_star_btn = Gtk.Button.new_from_icon_name("tux-non-starred-symbolic")
        self.bookmark_star_btn.set_tooltip_text("Add bookmark (Ctrl+D)")
        self.bookmark_star_btn.connect("clicked", self._on_bookmark_toggle)
        nav_toolbar.append(self.bookmark_star_btn)
        
        # Bookmarks menu button
        bookmarks_btn = Gtk.MenuButton()
        bookmarks_btn.set_icon_name("tux-user-bookmarks-symbolic")
        bookmarks_btn.set_tooltip_text("Bookmarks")
        
        # Create popover for bookmarks list
        self.bookmarks_popover = Gtk.Popover()
        self.bookmarks_popover.set_size_request(350, -1)
        self.bookmarks_popover.set_autohide(True)
        self.bookmarks_popover.connect("show", lambda p: self._on_bookmarks_popover_show())
        bookmarks_btn.set_popover(self.bookmarks_popover)
        
        # Main container for popover content
        popover_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        popover_box.set_margin_top(8)
        popover_box.set_margin_bottom(8)
        popover_box.set_margin_start(8)
        popover_box.set_margin_end(8)
        self.bookmarks_popover.set_child(popover_box)
        
        # Search bar and sort in a row
        search_sort_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        popover_box.append(search_sort_box)
        
        # Search bar
        self.bookmarks_search_entry = Gtk.SearchEntry()
        self.bookmarks_search_entry.set_placeholder_text("Search bookmarks...")
        self.bookmarks_search_entry.set_hexpand(True)
        self.bookmarks_search_entry.connect("search-changed", self._on_bookmarks_search_changed)
        search_sort_box.append(self.bookmarks_search_entry)
        
        # Sort dropdown
        sort_model = Gtk.StringList.new(["Default", "Name A-Z", "Name Z-A", "Recent"])
        self.bookmarks_sort_dropdown = Gtk.DropDown(model=sort_model)
        self.bookmarks_sort_dropdown.set_tooltip_text("Sort bookmarks")
        self.bookmarks_sort_dropdown.connect("notify::selected", self._on_bookmarks_sort_changed)
        search_sort_box.append(self.bookmarks_sort_dropdown)
        
        # Bookmarks list box inside scrolled window
        bookmarks_scroll = Gtk.ScrolledWindow()
        bookmarks_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        bookmarks_scroll.set_max_content_height(300)
        bookmarks_scroll.set_propagate_natural_height(True)
        popover_box.append(bookmarks_scroll)
        
        self.bookmarks_list_box = Gtk.ListBox()
        self.bookmarks_list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.bookmarks_list_box.add_css_class("boxed-list")
        bookmarks_scroll.set_child(self.bookmarks_list_box)
        
        # Separator
        popover_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        
        # Add / New Folder / Separator buttons
        buttons_box1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons_box1.set_homogeneous(True)
        popover_box.append(buttons_box1)
        
        add_btn = Gtk.Button(label="Add")
        add_btn.set_icon_name("tux-list-add-symbolic")
        add_btn.connect("clicked", self._on_bookmark_add_manual)
        buttons_box1.append(add_btn)
        
        new_folder_btn = Gtk.Button(label="Folder")
        new_folder_btn.set_icon_name("tux-folder-new-symbolic")
        new_folder_btn.connect("clicked", self._on_bookmark_new_folder)
        buttons_box1.append(new_folder_btn)
        
        separator_btn = Gtk.Button(label="Separator")
        separator_btn.set_icon_name("tux-view-more-horizontal-symbolic")
        separator_btn.connect("clicked", self._on_bookmark_add_separator)
        buttons_box1.append(separator_btn)
        
        # Import / Export buttons
        buttons_box2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        buttons_box2.set_homogeneous(True)
        popover_box.append(buttons_box2)
        
        import_btn = Gtk.Button(label="Import")
        import_btn.set_icon_name("tux-document-open-symbolic")
        import_btn.connect("clicked", self._on_bookmarks_import)
        buttons_box2.append(import_btn)
        
        export_btn = Gtk.Button(label="Export")
        export_btn.set_icon_name("tux-document-save-symbolic")
        export_btn.connect("clicked", self._on_bookmarks_export)
        buttons_box2.append(export_btn)
        
        # Manage button - opens full bookmark manager window
        manage_btn = Gtk.Button(label="Manage...")
        manage_btn.set_icon_name("tux-applications-system-symbolic")
        manage_btn.connect("clicked", self._show_bookmark_manager)
        popover_box.append(manage_btn)
        
        # Clear All button
        clear_btn = Gtk.Button(label="Clear All")
        clear_btn.set_icon_name("tux-user-trash-symbolic")
        clear_btn.add_css_class("destructive-action")
        clear_btn.connect("clicked", self._on_bookmarks_clear_all)
        popover_box.append(clear_btn)
        
        # Show Bookmarks Bar toggle
        bar_toggle_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bar_toggle_box.set_margin_top(4)
        popover_box.append(bar_toggle_box)
        
        bar_label = Gtk.Label(label="Show Bookmarks Bar")
        bar_label.set_hexpand(True)
        bar_label.set_xalign(0)
        bar_toggle_box.append(bar_label)
        
        self.bookmarks_bar_switch = Gtk.Switch()
        self.bookmarks_bar_switch.set_active(self._load_bookmarks_bar_visible())
        self.bookmarks_bar_switch.connect("notify::active", self._on_bookmarks_bar_toggle)
        bar_toggle_box.append(self.bookmarks_bar_switch)
        
        nav_toolbar.append(bookmarks_btn)
        
        # History menu button
        history_btn = Gtk.MenuButton()
        history_btn.set_icon_name("tux-document-open-recent-symbolic")
        history_btn.set_tooltip_text("History")
        
        # Create popover for history
        self.history_popover = Gtk.Popover()
        self.history_popover.set_size_request(400, -1)
        self.history_popover.set_autohide(True)
        self.history_popover.connect("show", lambda p: self._on_history_popover_show())
        history_btn.set_popover(self.history_popover)
        
        # History popover content
        history_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        history_box.set_margin_top(8)
        history_box.set_margin_bottom(8)
        history_box.set_margin_start(8)
        history_box.set_margin_end(8)
        self.history_popover.set_child(history_box)
        
        # Search bar
        self.history_search_entry = Gtk.SearchEntry()
        self.history_search_entry.set_placeholder_text("Search history...")
        self.history_search_entry.connect("search-changed", self._on_history_search_changed)
        history_box.append(self.history_search_entry)
        
        # History list
        history_scroll = Gtk.ScrolledWindow()
        history_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        history_scroll.set_max_content_height(350)
        history_scroll.set_propagate_natural_height(True)
        history_box.append(history_scroll)
        
        self.history_list_box = Gtk.ListBox()
        self.history_list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.history_list_box.add_css_class("boxed-list")
        history_scroll.set_child(self.history_list_box)
        
        # Separator
        history_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        
        # Bottom buttons
        history_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        history_box.append(history_actions)
        
        # Show All History
        show_all_btn = Gtk.Button(label="Show All History")
        show_all_btn.set_icon_name("tux-view-list-symbolic")
        show_all_btn.connect("clicked", self._show_history_window)
        show_all_btn.set_hexpand(True)
        history_actions.append(show_all_btn)
        
        # Clear History button (opens dialog)
        clear_btn = Gtk.Button(label="Clear")
        clear_btn.set_icon_name("tux-edit-clear-symbolic")
        clear_btn.connect("clicked", self._show_clear_history_dialog)
        history_actions.append(clear_btn)
        
        nav_toolbar.append(history_btn)
        
        # Downloads menu button
        downloads_btn = Gtk.MenuButton()
        downloads_btn.set_icon_name("tux-folder-download-symbolic")
        downloads_btn.set_tooltip_text("Downloads")
        
        # Create popover for downloads
        self.downloads_popover = Gtk.Popover()
        self.downloads_popover.set_size_request(400, -1)
        self.downloads_popover.set_autohide(True)
        downloads_btn.set_popover(self.downloads_popover)
        
        # Downloads popover content
        downloads_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        downloads_box.set_margin_top(8)
        downloads_box.set_margin_bottom(8)
        downloads_box.set_margin_start(8)
        downloads_box.set_margin_end(8)
        self.downloads_popover.set_child(downloads_box)
        
        # Downloads list
        downloads_scroll = Gtk.ScrolledWindow()
        downloads_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        downloads_scroll.set_max_content_height(350)
        downloads_scroll.set_propagate_natural_height(True)
        downloads_box.append(downloads_scroll)
        
        self.downloads_list_box = Gtk.ListBox()
        self.downloads_list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self.downloads_list_box.add_css_class("boxed-list")
        downloads_scroll.set_child(self.downloads_list_box)
        
        # Empty state label
        self.downloads_empty_label = Gtk.Label(label="No downloads yet")
        self.downloads_empty_label.add_css_class("dim-label")
        self.downloads_list_box.append(self.downloads_empty_label)
        
        # Bottom buttons
        downloads_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        downloads_box.append(downloads_actions)
        
        # Open Downloads folder
        open_folder_btn = Gtk.Button(label="Open Downloads Folder")
        open_folder_btn.set_icon_name("tux-folder-open-symbolic")
        open_folder_btn.connect("clicked", self._open_downloads_folder)
        open_folder_btn.set_hexpand(True)
        downloads_actions.append(open_folder_btn)
        
        # Clear completed
        clear_downloads_btn = Gtk.Button(label="Clear")
        clear_downloads_btn.set_icon_name("tux-edit-clear-symbolic")
        clear_downloads_btn.set_tooltip_text("Clear completed downloads")
        clear_downloads_btn.connect("clicked", self._clear_completed_downloads)
        downloads_actions.append(clear_downloads_btn)
        
        nav_toolbar.append(downloads_btn)
        
        # Privacy shield button
        privacy_btn = Gtk.MenuButton()
        privacy_btn.set_icon_name("tux-security-high-symbolic")
        privacy_btn.set_tooltip_text("Privacy Shield")
        
        # Privacy popover
        self.privacy_popover = Gtk.Popover()
        self.privacy_popover.set_autohide(True)
        privacy_btn.set_popover(self.privacy_popover)
        
        privacy_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        privacy_box.set_margin_top(12)
        privacy_box.set_margin_bottom(12)
        privacy_box.set_margin_start(12)
        privacy_box.set_margin_end(12)
        self.privacy_popover.set_child(privacy_box)
        
        # Pages protected count label
        self.blocked_label = Gtk.Label(label="🛡️ Protection active")
        self.blocked_label.set_xalign(0)
        self.blocked_label.add_css_class("heading")
        privacy_box.append(self.blocked_label)
        
        privacy_box.append(Gtk.Separator())
        
        # Force HTTPS toggle
        https_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        https_label = Gtk.Label(label="Force HTTPS")
        https_label.set_hexpand(True)
        https_label.set_xalign(0)
        https_row.append(https_label)
        self.https_switch = Gtk.Switch()
        self.https_switch.set_active(self.force_https)
        self.https_switch.connect("notify::active", self._on_https_toggled)
        https_row.append(self.https_switch)
        privacy_box.append(https_row)
        
        # Block ads toggle
        ads_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        ads_label = Gtk.Label(label="Block Ads")
        ads_label.set_hexpand(True)
        ads_label.set_xalign(0)
        ads_row.append(ads_label)
        self.ads_switch = Gtk.Switch()
        self.ads_switch.set_active(self.block_ads)
        self.ads_switch.connect("notify::active", self._on_ads_toggled)
        ads_row.append(self.ads_switch)
        privacy_box.append(ads_row)
        
        # Block trackers toggle
        trackers_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        trackers_label = Gtk.Label(label="Block Trackers")
        trackers_label.set_hexpand(True)
        trackers_label.set_xalign(0)
        trackers_row.append(trackers_label)
        self.trackers_switch = Gtk.Switch()
        self.trackers_switch.set_active(self.block_trackers)
        self.trackers_switch.connect("notify::active", self._on_trackers_toggled)
        trackers_row.append(self.trackers_switch)
        privacy_box.append(trackers_row)
        
        # SponsorBlock toggle
        sponsorblock_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        sponsorblock_label = Gtk.Label(label="SponsorBlock (YouTube)")
        sponsorblock_label.set_hexpand(True)
        sponsorblock_label.set_xalign(0)
        sponsorblock_row.append(sponsorblock_label)
        self.sponsorblock_switch = Gtk.Switch()
        self.sponsorblock_switch.set_active(self.sponsorblock_enabled)
        self.sponsorblock_switch.connect("notify::active", self._on_sponsorblock_toggled)
        sponsorblock_row.append(self.sponsorblock_switch)
        privacy_box.append(sponsorblock_row)
        
        nav_toolbar.append(privacy_btn)
        
        # Settings button
        settings_btn = Gtk.MenuButton()
        settings_btn.set_icon_name("tux-emblem-system-symbolic")
        settings_btn.set_tooltip_text("Browser Settings")
        
        # Create settings popover
        self.settings_popover = Gtk.Popover()
        self.settings_popover.set_autohide(True)
        settings_btn.set_popover(self.settings_popover)
        
        # Wrap in scrolled window for long content
        settings_scroll = Gtk.ScrolledWindow()
        settings_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        settings_scroll.set_max_content_height(450)
        settings_scroll.set_propagate_natural_height(True)
        self.settings_popover.set_child(settings_scroll)
        
        settings_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        settings_box.set_margin_top(12)
        settings_box.set_margin_bottom(12)
        settings_box.set_margin_start(12)
        settings_box.set_margin_end(12)
        settings_scroll.set_child(settings_box)
        
        # Title
        settings_title = Gtk.Label(label="Browser Settings")
        settings_title.add_css_class("title-3")
        settings_box.append(settings_title)
        
        settings_box.append(Gtk.Separator())
        
        # === General Section ===
        general_label = Gtk.Label(label="General")
        general_label.add_css_class("heading")
        general_label.set_xalign(0)
        settings_box.append(general_label)
        
        # Homepage
        homepage_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        homepage_label = Gtk.Label(label="Homepage")
        homepage_label.set_xalign(0)
        homepage_label.set_hexpand(True)
        homepage_row.append(homepage_label)
        self.homepage_entry = Gtk.Entry()
        self.homepage_entry.set_width_chars(20)
        self.homepage_entry.set_text(self._load_browser_settings().get('homepage', 'https://duckduckgo.com'))
        self.homepage_entry.connect("changed", self._on_homepage_changed)
        homepage_row.append(self.homepage_entry)
        settings_box.append(homepage_row)
        
        # Search Engine
        search_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        search_label = Gtk.Label(label="Search Engine")
        search_label.set_xalign(0)
        search_label.set_hexpand(True)
        search_row.append(search_label)
        
        self.search_engine_dropdown = Gtk.DropDown()
        search_engines = Gtk.StringList.new(["DuckDuckGo", "Google", "Bing", "Startpage", "Brave"])
        self.search_engine_dropdown.set_model(search_engines)
        
        # Set current selection
        current_engine = self._load_browser_settings().get('search_engine', 'DuckDuckGo')
        engine_map = {"DuckDuckGo": 0, "Google": 1, "Bing": 2, "Startpage": 3, "Brave": 4}
        self.search_engine_dropdown.set_selected(engine_map.get(current_engine, 0))
        self.search_engine_dropdown.connect("notify::selected", self._on_search_engine_changed)
        search_row.append(self.search_engine_dropdown)
        settings_box.append(search_row)
        
        # Default Zoom
        zoom_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        zoom_label = Gtk.Label(label="Default Zoom")
        zoom_label.set_xalign(0)
        zoom_label.set_hexpand(True)
        zoom_row.append(zoom_label)
        
        self.zoom_dropdown = Gtk.DropDown()
        zoom_levels = Gtk.StringList.new(["50%", "75%", "100%", "125%", "150%", "175%", "200%"])
        self.zoom_dropdown.set_model(zoom_levels)
        
        # Set current zoom
        current_zoom = self._load_browser_settings().get('default_zoom', 1.0)
        zoom_map = {0.5: 0, 0.75: 1, 1.0: 2, 1.25: 3, 1.5: 4, 1.75: 5, 2.0: 6}
        self.zoom_dropdown.set_selected(zoom_map.get(current_zoom, 2))
        self.zoom_dropdown.connect("notify::selected", self._on_default_zoom_changed)
        zoom_row.append(self.zoom_dropdown)
        settings_box.append(zoom_row)
        
        settings_box.append(Gtk.Separator())
        
        # === Read Aloud Section ===
        tts_label = Gtk.Label(label="Read Aloud")
        tts_label.add_css_class("heading")
        tts_label.set_xalign(0)
        settings_box.append(tts_label)
        
        # Voice selection
        voice_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        voice_label = Gtk.Label(label="Voice")
        voice_label.set_xalign(0)
        voice_label.set_hexpand(True)
        voice_row.append(voice_label)
        
        self.tts_voice_dropdown = Gtk.DropDown()
        # US English voices - mix of male/female
        tts_voices = Gtk.StringList.new([
            "Christopher (Male)",
            "Guy (Male)", 
            "Eric (Male)",
            "Roger (Male)",
            "Jenny (Female)",
            "Aria (Female)",
            "Michelle (Female)",
            "Ana (Female, Child)"
        ])
        self.tts_voice_dropdown.set_model(tts_voices)
        
        # Voice name mapping
        self.tts_voice_map = {
            0: 'en-US-ChristopherNeural',
            1: 'en-US-GuyNeural',
            2: 'en-US-EricNeural', 
            3: 'en-US-RogerNeural',
            4: 'en-US-JennyNeural',
            5: 'en-US-AriaNeural',
            6: 'en-US-MichelleNeural',
            7: 'en-US-AnaNeural'
        }
        self.tts_voice_reverse_map = {v: k for k, v in self.tts_voice_map.items()}
        
        # Set current voice
        current_voice = self._load_browser_settings().get('tts_voice', 'en-US-ChristopherNeural')
        self.tts_voice_dropdown.set_selected(self.tts_voice_reverse_map.get(current_voice, 0))
        self.tts_voice_dropdown.connect("notify::selected", self._on_tts_voice_changed)
        voice_row.append(self.tts_voice_dropdown)
        settings_box.append(voice_row)
        
        # Speed selection
        speed_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        speed_label = Gtk.Label(label="Speed")
        speed_label.set_xalign(0)
        speed_label.set_hexpand(True)
        speed_row.append(speed_label)
        
        self.tts_speed_dropdown = Gtk.DropDown()
        tts_speeds = Gtk.StringList.new(["Slower", "Normal", "Faster", "Fast"])
        self.tts_speed_dropdown.set_model(tts_speeds)
        
        self.tts_speed_map = {0: '-25%', 1: '+0%', 2: '+25%', 3: '+50%'}
        self.tts_speed_reverse_map = {v: k for k, v in self.tts_speed_map.items()}
        
        current_rate = self._load_browser_settings().get('tts_rate', '+0%')
        self.tts_speed_dropdown.set_selected(self.tts_speed_reverse_map.get(current_rate, 1))
        self.tts_speed_dropdown.connect("notify::selected", self._on_tts_speed_changed)
        speed_row.append(self.tts_speed_dropdown)
        settings_box.append(speed_row)
        
        # Test button
        test_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        test_btn = Gtk.Button(label="Test Voice")
        test_btn.set_icon_name("tux-audio-speakers-symbolic")
        test_btn.connect("clicked", self._on_tts_test_clicked)
        test_row.append(test_btn)
        
        self.tts_stop_btn = Gtk.Button(label="Stop")
        self.tts_stop_btn.set_icon_name("tux-media-playback-stop-symbolic")
        self.tts_stop_btn.connect("clicked", self._on_tts_stop_clicked)
        self.tts_stop_btn.set_sensitive(False)
        test_row.append(self.tts_stop_btn)
        settings_box.append(test_row)
        
        # Hint label
        tts_hint = Gtk.Label(label="Select text, then Ctrl+Shift+R to read aloud")
        tts_hint.add_css_class("dim-label")
        tts_hint.set_xalign(0)
        settings_box.append(tts_hint)
        
        settings_box.append(Gtk.Separator())
        
        # === Data Management Section ===
        data_label = Gtk.Label(label="Clear Browsing Data")
        data_label.add_css_class("heading")
        data_label.set_xalign(0)
        settings_box.append(data_label)
        
        # Clear buttons in a flow box
        clear_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        settings_box.append(clear_box)
        
        # Clear History
        clear_history_btn = Gtk.Button(label="Clear History")
        clear_history_btn.set_icon_name("tux-edit-clear-history-symbolic")
        clear_history_btn.connect("clicked", self._on_clear_history_clicked)
        clear_box.append(clear_history_btn)
        
        # Clear Cookies
        clear_cookies_btn = Gtk.Button(label="Clear Cookies")
        clear_cookies_btn.set_icon_name("tux-cookie-symbolic")
        clear_cookies_btn.connect("clicked", self._on_clear_cookies_clicked)
        clear_box.append(clear_cookies_btn)
        
        # Clear Cache
        clear_cache_btn = Gtk.Button(label="Clear Cache")
        clear_cache_btn.set_icon_name("tux-folder-templates-symbolic")
        clear_cache_btn.connect("clicked", self._on_clear_cache_clicked)
        clear_box.append(clear_cache_btn)
        
        # Clear All
        clear_all_btn = Gtk.Button(label="Clear All Data")
        clear_all_btn.set_icon_name("tux-edit-clear-all-symbolic")
        clear_all_btn.add_css_class("destructive-action")
        clear_all_btn.connect("clicked", self._on_clear_all_clicked)
        clear_box.append(clear_all_btn)
        
        settings_box.append(Gtk.Separator())
        
        # === Default Browser Section ===
        default_label = Gtk.Label(label="System Integration")
        default_label.add_css_class("heading")
        default_label.set_xalign(0)
        settings_box.append(default_label)
        
        # Status label
        self.default_browser_status = Gtk.Label()
        self.default_browser_status.set_xalign(0)
        self.default_browser_status.add_css_class("dim-label")
        self._update_default_browser_status()
        settings_box.append(self.default_browser_status)
        
        # Set as default button
        set_default_btn = Gtk.Button(label="Set as Default Browser")
        set_default_btn.set_icon_name("tux-web-browser-symbolic")
        set_default_btn.connect("clicked", self._on_set_default_browser_clicked)
        settings_box.append(set_default_btn)
        
        # Hint
        default_hint = Gtk.Label(label="External links will open in Tux Browser")
        default_hint.add_css_class("dim-label")
        default_hint.set_xalign(0)
        settings_box.append(default_hint)
        
        # Read Article button (TTS)
        self.read_article_btn = Gtk.Button.new_from_icon_name("tux-audio-speakers-symbolic")
        self.read_article_btn.set_tooltip_text("Read article aloud")
        self.read_article_btn.connect("clicked", self._on_read_article_clicked)
        nav_toolbar.append(self.read_article_btn)
        
        # Stop Reading button (TTS) - initially hidden
        self.stop_reading_btn = Gtk.Button.new_from_icon_name("tux-media-playback-stop-symbolic")
        self.stop_reading_btn.set_tooltip_text("Stop reading")
        self.stop_reading_btn.add_css_class("destructive-action")
        self.stop_reading_btn.connect("clicked", self._on_stop_reading_clicked)
        self.stop_reading_btn.set_visible(False)
        nav_toolbar.append(self.stop_reading_btn)
        
        # Reader Mode toggle button
        self.reader_mode_btn = Gtk.ToggleButton()
        self.reader_mode_btn.set_icon_name("tux-document-page-setup-symbolic")
        self.reader_mode_btn.set_tooltip_text("Reader Mode - distraction-free reading")
        self.reader_mode_btn.connect("toggled", self._on_reader_mode_toggled)
        nav_toolbar.append(self.reader_mode_btn)
        
        # Track reader mode state
        self._reader_mode_active = False
        
        nav_toolbar.append(settings_btn)
        
        # New tab button
        new_tab_btn = Gtk.Button.new_from_icon_name("tab-new-symbolic")
        new_tab_btn.set_tooltip_text("New tab (Ctrl+T)")
        new_tab_btn.connect("clicked", lambda b: self._browser_new_tab())
        nav_toolbar.append(new_tab_btn)
        
        # Expand/collapse browser (hide/show sidebar)
        self.browser_expand_btn = Gtk.Button.new_from_icon_name("tux-view-fullscreen-symbolic")
        self.browser_expand_btn.set_tooltip_text("Expand browser (hide sidebar)")
        self.browser_expand_btn.connect("clicked", self._on_browser_expand_toggle)
        nav_toolbar.append(self.browser_expand_btn)
        self.browser_expanded = False
        
        # Bookmarks bar (like Firefox/Chrome) - in scrollable container
        self.bookmarks_bar_container = Gtk.ScrolledWindow()
        self.bookmarks_bar_container.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self.bookmarks_bar_container.set_margin_start(12)
        self.bookmarks_bar_container.set_margin_end(12)
        self.bookmarks_bar_container.set_margin_bottom(4)
        self.bookmarks_bar_container.set_max_content_width(600)
        self.bookmarks_bar_container.set_propagate_natural_width(True)
        self.browser_panel.append(self.bookmarks_bar_container)
        
        self.bookmarks_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self.bookmarks_bar.add_css_class("toolbar")
        self.bookmarks_bar_container.set_child(self.bookmarks_bar)
        
        # Apply saved visibility preference
        self.bookmarks_bar_container.set_visible(self._load_bookmarks_bar_visible())
        
        # Populate bookmarks bar
        self._refresh_bookmarks_bar()
        
        # Set up network session (shared by all tabs)
        self.browser_network_session = None
        try:
            if hasattr(WebKit, 'NetworkSession'):
                data_dir = os.path.join(GLib.get_user_data_dir(), 'tux-assistant', 'webview')
                cache_dir = os.path.join(GLib.get_user_cache_dir(), 'tux-assistant', 'webview')
                os.makedirs(data_dir, exist_ok=True)
                os.makedirs(cache_dir, exist_ok=True)
                
                self.browser_network_session = WebKit.NetworkSession.new(data_dir, cache_dir)
                
                cookie_manager = self.browser_network_session.get_cookie_manager()
                cookie_manager.set_accept_policy(WebKit.CookieAcceptPolicy.ALWAYS)
                cookie_manager.set_persistent_storage(
                    os.path.join(data_dir, 'cookies.sqlite'),
                    WebKit.CookiePersistentStorage.SQLITE
                )
                
                self.browser_network_session.connect('download-started', self._on_browser_download_started)
        except Exception as e:
            print(f"Browser network session error: {e}")
        
        # Tab bar container
        tab_bar_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        tab_bar_box.set_margin_start(12)
        tab_bar_box.set_margin_end(12)
        tab_bar_box.set_margin_bottom(4)
        self.browser_panel.append(tab_bar_box)
        
        # Create TabView (holds the tab pages)
        self.browser_tab_view = Adw.TabView()
        self.browser_tab_view.set_vexpand(True)
        self.browser_tab_view.set_hexpand(True)
        
        # Create TabBar (the visual tab strip)
        self.browser_tab_bar = Adw.TabBar()
        self.browser_tab_bar.set_view(self.browser_tab_view)
        self.browser_tab_bar.set_autohide(False)
        self.browser_tab_bar.set_expand_tabs(False)
        self.browser_tab_bar.set_hexpand(True)
        tab_bar_box.append(self.browser_tab_bar)
        
        # Connect tab signals
        self.browser_tab_view.connect("notify::selected-page", self._on_browser_tab_changed)
        self.browser_tab_view.connect("close-page", self._on_browser_tab_close)
        
        # Frame around tab view
        webview_frame = Gtk.Frame()
        webview_frame.set_margin_start(12)
        webview_frame.set_margin_end(12)
        webview_frame.set_margin_bottom(12)
        webview_frame.set_child(self.browser_tab_view)
        webview_frame.set_vexpand(True)
        self.browser_panel.append(webview_frame)
        
        # Find bar (hidden by default)
        self.find_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.find_bar.set_margin_start(12)
        self.find_bar.set_margin_end(12)
        self.find_bar.set_margin_bottom(8)
        self.find_bar.add_css_class("toolbar")
        self.find_bar.set_visible(False)
        
        find_label = Gtk.Label(label="Find:")
        self.find_bar.append(find_label)
        
        self.find_entry = Gtk.Entry()
        self.find_entry.set_placeholder_text("Search in page...")
        self.find_entry.set_hexpand(True)
        self.find_entry.connect("changed", self._on_find_text_changed)
        self.find_entry.connect("activate", self._on_find_next)
        self.find_bar.append(self.find_entry)
        
        # Match count label
        self.find_match_label = Gtk.Label(label="")
        self.find_match_label.add_css_class("dim-label")
        self.find_bar.append(self.find_match_label)
        
        # Previous button
        prev_btn = Gtk.Button.new_from_icon_name("tux-go-up-symbolic")
        prev_btn.set_tooltip_text("Previous match (Shift+Enter)")
        prev_btn.connect("clicked", self._on_find_prev)
        self.find_bar.append(prev_btn)
        
        # Next button
        next_btn = Gtk.Button.new_from_icon_name("tux-go-down-symbolic")
        next_btn.set_tooltip_text("Next match (Enter)")
        next_btn.connect("clicked", self._on_find_next)
        self.find_bar.append(next_btn)
        
        # Close button
        close_btn = Gtk.Button.new_from_icon_name("tux-window-close-symbolic")
        close_btn.set_tooltip_text("Close (Escape)")
        close_btn.connect("clicked", lambda b: self._hide_find_bar())
        self.find_bar.append(close_btn)
        
        # Handle Shift+Enter for previous
        find_key_controller = Gtk.EventControllerKey()
        find_key_controller.connect("key-pressed", self._on_find_key_pressed)
        self.find_entry.add_controller(find_key_controller)
        
        self.browser_panel.append(self.find_bar)
        
        # Add keyboard shortcuts
        self._setup_browser_keyboard_shortcuts()
        
        # Create first tab
        self._browser_new_tab(self.browser_home_url)
    
    def _setup_browser_keyboard_shortcuts(self):
        """Set up keyboard shortcuts for the browser."""
        # Use CAPTURE phase to intercept before WebView gets the event
        controller = Gtk.EventControllerKey()
        controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
        controller.connect("key-pressed", self._on_browser_key_pressed)
        self.browser_panel.add_controller(controller)
    
    def _on_browser_key_pressed(self, controller, keyval, keycode, state):
        """Handle browser keyboard shortcuts."""
        ctrl = state & Gdk.ModifierType.CONTROL_MASK
        shift = state & Gdk.ModifierType.SHIFT_MASK
        
        if ctrl:
            if keyval == Gdk.KEY_t or keyval == Gdk.KEY_T:
                # Ctrl+T: New tab
                self._browser_new_tab()
                return True
            elif keyval == Gdk.KEY_w or keyval == Gdk.KEY_W:
                # Ctrl+W: Close current tab
                self._browser_close_current_tab()
                return True
            elif keyval == Gdk.KEY_l or keyval == Gdk.KEY_L:
                # Ctrl+L: Focus URL bar
                self.browser_url_entry.grab_focus()
                self.browser_url_entry.select_region(0, -1)
                return True
            elif keyval == Gdk.KEY_Tab:
                if shift:
                    # Ctrl+Shift+Tab: Previous tab
                    self._browser_prev_tab()
                else:
                    # Ctrl+Tab: Next tab
                    self._browser_next_tab()
                return True
            elif keyval == Gdk.KEY_r or keyval == Gdk.KEY_R:
                if shift:
                    # Ctrl+Shift+R: Read selection aloud
                    webview = self._get_current_browser_webview()
                    if webview:
                        self._read_selection_aloud(webview)
                    return True
                else:
                    # Ctrl+R: Reload
                    webview = self._get_current_browser_webview()
                    if webview:
                        webview.reload()
                    return True
            elif keyval == Gdk.KEY_d or keyval == Gdk.KEY_D:
                # Ctrl+D: Bookmark current page
                self._on_bookmark_toggle(None)
                return True
            elif keyval == Gdk.KEY_f or keyval == Gdk.KEY_F:
                # Ctrl+F: Find in page
                self._show_find_bar()
                return True
            elif keyval == Gdk.KEY_plus or keyval == Gdk.KEY_equal or keyval == Gdk.KEY_KP_Add:
                # Ctrl++: Zoom in
                self._browser_zoom_in()
                return True
            elif keyval == Gdk.KEY_minus or keyval == Gdk.KEY_KP_Subtract:
                # Ctrl+-: Zoom out
                self._browser_zoom_out()
                return True
            elif keyval == Gdk.KEY_0 or keyval == Gdk.KEY_KP_0:
                # Ctrl+0: Reset zoom
                self._browser_zoom_reset()
                return True
            elif keyval == Gdk.KEY_p or keyval == Gdk.KEY_P:
                # Ctrl+P: Print page
                self._browser_print()
                return True
        
        # Escape to close find bar
        if keyval == Gdk.KEY_Escape:
            # Stop TTS playback first
            if self.tts_process:
                self._stop_read_aloud()
                return True
            if hasattr(self, 'find_bar') and self.find_bar.get_visible():
                self._hide_find_bar()
                return True
            # Also exit fullscreen with Escape
            if self.is_fullscreen():
                self.unfullscreen()
                return True
        
        # F10: Toggle browser expand (hide/show sidebar)
        if keyval == Gdk.KEY_F10:
            if hasattr(self, 'browser_expand_btn'):
                self._on_browser_expand_toggle(self.browser_expand_btn)
            return True
        
        # F11: Toggle fullscreen (also handled at window level, but just in case)
        if keyval == Gdk.KEY_F11:
            self._toggle_fullscreen()
            return True
        
        return False
    
    def _browser_zoom_in(self):
        """Zoom in the current webview."""
        webview = self._get_current_browser_webview()
        if webview:
            current = webview.get_zoom_level()
            new_zoom = min(current + 0.1, 3.0)  # Max 300%
            self._apply_zoom_to_all_tabs(new_zoom)
            self._save_zoom_level(new_zoom)
            self._show_zoom_toast(new_zoom)
    
    def _browser_zoom_out(self):
        """Zoom out the current webview."""
        webview = self._get_current_browser_webview()
        if webview:
            current = webview.get_zoom_level()
            new_zoom = max(current - 0.1, 0.3)  # Min 30%
            self._apply_zoom_to_all_tabs(new_zoom)
            self._save_zoom_level(new_zoom)
            self._show_zoom_toast(new_zoom)
    
    def _browser_zoom_reset(self):
        """Reset zoom to 100%."""
        webview = self._get_current_browser_webview()
        if webview:
            self._apply_zoom_to_all_tabs(1.0)
            self._save_zoom_level(1.0)
            self.show_toast("Zoom: 100%")
    
    def _apply_zoom_to_all_tabs(self, zoom_level):
        """Apply zoom level to all open tabs."""
        if not hasattr(self, 'browser_tab_view'):
            return
        for i in range(self.browser_tab_view.get_n_pages()):
            page = self.browser_tab_view.get_nth_page(i)
            if page:
                wv = page.get_child()
                if wv:
                    wv.set_zoom_level(zoom_level)
    
    def _show_zoom_toast(self, level):
        """Show current zoom level."""
        percent = int(level * 100)
        self.show_toast(f"Zoom: {percent}%")
    
    def _show_find_bar(self):
        """Show the find bar and focus the entry."""
        if not hasattr(self, 'find_bar'):
            return
        self.find_bar.set_visible(True)
        self.find_entry.grab_focus()
        self.find_entry.select_region(0, -1)
    
    def _toggle_fullscreen(self):
        """Toggle fullscreen mode."""
        if self.is_fullscreen():
            self.unfullscreen()
        else:
            self.fullscreen()
    
    def _browser_print(self):
        """Print the current page."""
        webview = self._get_current_browser_webview()
        if webview:
            try:
                # WebKit 6.0 / WebKit2 5.0 API
                print_operation = WebKit.PrintOperation.new(webview)
                print_operation.run_dialog(self)
            except Exception as e:
                print(f"Print error: {e}")
                self.show_toast("Print not available")
    
    def _hide_find_bar(self):
        """Hide the find bar and clear search."""
        if not hasattr(self, 'find_bar'):
            return
        self.find_bar.set_visible(False)
        self.find_match_label.set_text("")
        # Clear the search highlighting
        webview = self._get_current_browser_webview()
        if webview:
            find_controller = webview.get_find_controller()
            find_controller.search_finish()
            # Return focus to webview so keyboard shortcuts work
            webview.grab_focus()
    
    def _on_find_text_changed(self, entry):
        """Handle find text changes - search as you type."""
        text = entry.get_text()
        webview = self._get_current_browser_webview()
        if not webview:
            return
        
        find_controller = webview.get_find_controller()
        
        if not text:
            find_controller.search_finish()
            self.find_match_label.set_text("")
            return
        
        # Connect to match count updates (only once)
        if not hasattr(self, '_find_handler_connected'):
            find_controller.connect("counted-matches", self._on_find_match_count)
            find_controller.connect("found-text", self._on_find_found)
            find_controller.connect("failed-to-find-text", self._on_find_failed)
            self._find_handler_connected = True
        
        # Search with options
        find_controller.search(
            text,
            WebKit.FindOptions.CASE_INSENSITIVE | WebKit.FindOptions.WRAP_AROUND,
            100  # Max matches to count
        )
    
    def _on_find_match_count(self, find_controller, match_count):
        """Update match count display."""
        if match_count == 0:
            self.find_match_label.set_text("No matches")
        elif match_count == 1:
            self.find_match_label.set_text("1 match")
        else:
            self.find_match_label.set_text(f"{match_count} matches")
    
    def _on_find_found(self, find_controller, match_count):
        """Called when text is found."""
        # Update styling to indicate success
        self.find_entry.remove_css_class("error")
    
    def _on_find_failed(self, find_controller):
        """Called when text is not found."""
        self.find_match_label.set_text("No matches")
        self.find_entry.add_css_class("error")
    
    def _on_find_next(self, *args):
        """Find next match."""
        webview = self._get_current_browser_webview()
        if webview and self.find_entry.get_text():
            find_controller = webview.get_find_controller()
            find_controller.search_next()
    
    def _on_find_prev(self, *args):
        """Find previous match."""
        webview = self._get_current_browser_webview()
        if webview and self.find_entry.get_text():
            find_controller = webview.get_find_controller()
            find_controller.search_previous()
    
    def _on_find_key_pressed(self, controller, keyval, keycode, state):
        """Handle special keys in find entry."""
        shift = state & Gdk.ModifierType.SHIFT_MASK
        
        if keyval == Gdk.KEY_Return or keyval == Gdk.KEY_KP_Enter:
            if shift:
                self._on_find_prev()
            else:
                self._on_find_next()
            return True
        elif keyval == Gdk.KEY_Escape:
            self._hide_find_bar()
            return True
        
        return False

    def _create_browser_webview(self):
        """Create a new WebView with proper settings."""
        try:
            if self.browser_network_session:
                webview = WebKit.WebView(network_session=self.browser_network_session)
            else:
                webview = WebKit.WebView()
                try:
                    context = webview.get_context()
                    context.connect('download-started', self._on_browser_download_started)
                except:
                    pass
        except Exception as e:
            print(f"WebView creation error: {e}")
            webview = WebKit.WebView()
        
        webview.set_vexpand(True)
        webview.set_hexpand(True)
        
        # Apply ad-hiding CSS if blocking is enabled
        if self.block_ads:
            self._apply_ad_blocking_css(webview)
        
        # Configure settings
        settings = webview.get_settings()
        settings.set_enable_javascript(True)
        settings.set_javascript_can_open_windows_automatically(False)
        
        for method, value in [
            ('set_enable_html5_database', True),
            ('set_enable_html5_local_storage', True),
            ('set_enable_page_cache', True),
            ('set_enable_smooth_scrolling', True),
            ('set_enable_webgl', True),
            ('set_enable_media', True),
        ]:
            try:
                getattr(settings, method)(value)
            except:
                pass
        
        try:
            settings.set_hardware_acceleration_policy(WebKit.HardwareAccelerationPolicy.ALWAYS)
        except:
            pass
        
        # Standard browser user agent
        settings.set_user_agent(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
        )
        
        # Apply saved zoom level
        try:
            zoom = self._load_zoom_level()
            webview.set_zoom_level(zoom)
        except:
            pass
        
        # Connect signals
        webview.connect("load-changed", self._on_browser_load_changed)
        webview.connect("create", self._on_browser_create_window)
        webview.connect("notify::title", self._on_browser_title_changed)
        webview.connect("decide-policy", self._on_browser_decide_policy)
        webview.connect("context-menu", self._on_browser_context_menu)
        
        # Capture JavaScript console output for debugging
        try:
            # Try the WebKit2GTK 4.1+ API
            if hasattr(webview, 'get_inspector'):
                settings = webview.get_settings()
                if hasattr(settings, 'set_enable_write_console_messages_to_stdout'):
                    settings.set_enable_write_console_messages_to_stdout(True)
                    print("[Browser] Console output enabled")
        except Exception as e:
            print(f"[Browser] Console capture setup failed: {e}")
        
        # Close bookmarks popover when clicking on webview
        click_controller = Gtk.GestureClick()
        click_controller.connect("pressed", self._on_webview_clicked)
        webview.add_controller(click_controller)
        
        # Ctrl+scroll for zoom
        scroll_controller = Gtk.EventControllerScroll()
        scroll_controller.set_flags(Gtk.EventControllerScrollFlags.VERTICAL)
        scroll_controller.connect("scroll", self._on_webview_scroll)
        webview.add_controller(scroll_controller)
        
        return webview
    
    def _on_webview_clicked(self, gesture, n_press, x, y):
        """Close popovers when webview is clicked."""
        if hasattr(self, 'bookmarks_popover') and self.bookmarks_popover.is_visible():
            self.bookmarks_popover.popdown()
        if self.url_autocomplete_popover and self.url_autocomplete_popover.is_visible():
            self.url_autocomplete_popover.popdown()
    
    def _on_webview_scroll(self, controller, dx, dy):
        """Handle Ctrl+scroll for zoom with throttling."""
        # Check if Ctrl is held
        state = controller.get_current_event_state()
        if not (state & Gdk.ModifierType.CONTROL_MASK):
            return False  # Let normal scroll happen
        
        # Throttle: only zoom every 100ms to prevent jitter
        import time
        now = time.time()
        if hasattr(self, '_last_zoom_time') and (now - self._last_zoom_time) < 0.1:
            return True  # Consume but don't process
        self._last_zoom_time = now
        
        webview = self._get_current_browser_webview()
        if webview:
            current = webview.get_zoom_level()
            if dy < 0:  # Scroll up = zoom in
                new_zoom = min(current + 0.1, 3.0)
            else:  # Scroll down = zoom out
                new_zoom = max(current - 0.1, 0.3)
            self._apply_zoom_to_all_tabs(new_zoom)
            self._save_zoom_level(new_zoom)
        return True  # Consume the event
    
    def _browser_new_tab(self, url=None):
        """Create a new browser tab."""
        if not hasattr(self, 'browser_tab_view'):
            return
        
        webview = self._create_browser_webview()
        
        # Add to tab view
        page = self.browser_tab_view.append(webview)
        page.set_title("New Tab")
        
        # Select the new tab
        self.browser_tab_view.set_selected_page(page)
        
        # Load URL
        if url:
            webview.load_uri(url)
        else:
            webview.load_uri(self.browser_home_url)
        
        return page
    
    def _browser_close_current_tab(self):
        """Close the current browser tab."""
        if not hasattr(self, 'browser_tab_view'):
            return
        
        # Don't close if it's the last tab
        if self.browser_tab_view.get_n_pages() <= 1:
            return
        
        page = self.browser_tab_view.get_selected_page()
        if page:
            self.browser_tab_view.close_page(page)
    
    def _browser_next_tab(self):
        """Switch to next tab."""
        if not hasattr(self, 'browser_tab_view'):
            return
        
        n_pages = self.browser_tab_view.get_n_pages()
        if n_pages <= 1:
            return
        
        current = self.browser_tab_view.get_selected_page()
        current_pos = self.browser_tab_view.get_page_position(current)
        next_pos = (current_pos + 1) % n_pages
        next_page = self.browser_tab_view.get_nth_page(next_pos)
        self.browser_tab_view.set_selected_page(next_page)
    
    def _browser_prev_tab(self):
        """Switch to previous tab."""
        if not hasattr(self, 'browser_tab_view'):
            return
        
        n_pages = self.browser_tab_view.get_n_pages()
        if n_pages <= 1:
            return
        
        current = self.browser_tab_view.get_selected_page()
        current_pos = self.browser_tab_view.get_page_position(current)
        prev_pos = (current_pos - 1) % n_pages
        prev_page = self.browser_tab_view.get_nth_page(prev_pos)
        self.browser_tab_view.set_selected_page(prev_page)
    
    def _get_current_browser_webview(self):
        """Get the WebView from the currently selected tab."""
        if not hasattr(self, 'browser_tab_view'):
            return None
        
        page = self.browser_tab_view.get_selected_page()
        if page:
            return page.get_child()
        return None
    
    def _on_browser_tab_changed(self, tab_view, param):
        """Handle tab selection change."""
        webview = self._get_current_browser_webview()
        if webview:
            uri = webview.get_uri()
            if uri and hasattr(self, 'browser_url_entry'):
                if hasattr(self, '_autocomplete_active'):
                    self._autocomplete_active = True
                self.browser_url_entry.set_text(uri)
                if hasattr(self, '_autocomplete_active'):
                    self._autocomplete_active = False
            # Update bookmark star for current URL
            self._update_bookmark_star()
    
    def _on_browser_tab_close(self, tab_view, page):
        """Handle tab close request."""
        # If this is the last tab, close the browser panel instead
        if tab_view.get_n_pages() <= 1:
            tab_view.close_page_finish(page, False)  # Deny the tab close
            # Close the browser panel entirely
            self._close_browser_panel()
            return True
        
        tab_view.close_page_finish(page, True)  # Confirm close
        return True
    
    def _close_browser_panel(self):
        """Close the browser panel and return to main view."""
        # Update toggle button state (block handler to prevent recursion)
        if hasattr(self, 'browser_toggle_btn') and self.browser_toggle_btn.get_active():
            self.browser_toggle_btn.handler_block_by_func(self._on_browser_toggle)
            self.browser_toggle_btn.set_active(False)
            self.browser_toggle_btn.remove_css_class("active")
            self.browser_toggle_btn.handler_unblock_by_func(self._on_browser_toggle)
        
        # Remove browser panel from UI
        if self.browser_is_docked:
            self.main_paned.set_end_child(None)
            self.docked_panel = None
            self.browser_is_docked = False
        
        if self.browser_window:
            self.browser_window.close()
            self.browser_window = None
        
        self.browser_panel_visible = False
        
        # Reset browser panel so it gets rebuilt fresh next time
        self.browser_panel = None
        
        # Restore sidebar if it was hidden
        if hasattr(self, 'browser_expanded') and self.browser_expanded:
            self.browser_expanded = False
            self.navigation_view.set_visible(True)
            if hasattr(self, 'browser_expand_btn'):
                self.browser_expand_btn.set_icon_name("tux-view-fullscreen-symbolic")
                self.browser_expand_btn.set_tooltip_text("Expand browser (hide sidebar)")
    
    def _on_browser_title_changed(self, webview, param):
        """Update tab title when page title changes."""
        if not hasattr(self, 'browser_tab_view'):
            return
        
        title = webview.get_title()
        if title:
            # Find the page for this webview
            for i in range(self.browser_tab_view.get_n_pages()):
                page = self.browser_tab_view.get_nth_page(i)
                if page.get_child() == webview:
                    # Truncate long titles
                    if len(title) > 25:
                        title = title[:22] + "..."
                    page.set_title(title)
                    break
    
    def _on_browser_toggle(self, button):
        """Toggle browser panel visibility."""
        # Build browser panel lazily on first use
        if not hasattr(self, 'browser_panel') or self.browser_panel is None:
            if WEBKIT_AVAILABLE:
                self._build_global_browser_panel()
            else:
                return
        
        if button.get_active():
            # Show browser
            button.add_css_class("active")
            
            # Ensure there's at least one tab
            webview = self._get_current_browser_webview()
            if webview:
                uri = webview.get_uri()
                if not uri or uri == "about:blank":
                    webview.load_uri(self.browser_home_url)
            
            # Check if Claude is using the side panel
            if self.docked_panel == 'claude':
                # Claude has the panel - open browser as floating window
                self._show_browser_floating()
            else:
                # Panel is free - dock browser
                self._show_browser_docked()
        else:
            # Hide browser
            button.remove_css_class("active")
            
            # Restore sidebar if it was hidden
            if hasattr(self, 'browser_expanded') and self.browser_expanded:
                self.browser_expanded = False
                self.navigation_view.set_visible(True)
                if hasattr(self, 'browser_expand_btn'):
                    self.browser_expand_btn.set_icon_name("tux-view-fullscreen-symbolic")
                    self.browser_expand_btn.set_tooltip_text("Expand browser (hide sidebar)")
            
            if self.browser_is_docked:
                self.main_paned.set_end_child(None)
                self.docked_panel = None
                self.browser_is_docked = False
            
            if self.browser_window:
                self.browser_window.close()
                self.browser_window = None
            
            self.browser_panel_visible = False
    
    def _show_browser_docked(self):
        """Show browser in the docked panel."""
        if self.browser_panel.get_parent():
            self.browser_panel.get_parent().remove(self.browser_panel)
        
        self.main_paned.set_end_child(self.browser_panel)
        self.docked_panel = 'browser'
        self.browser_is_docked = True
        self.browser_panel_visible = True
        
        # Sync toggle button state (block handler to prevent recursion)
        if hasattr(self, 'browser_toggle_btn') and not self.browser_toggle_btn.get_active():
            self.browser_toggle_btn.handler_block_by_func(self._on_browser_toggle)
            self.browser_toggle_btn.set_active(True)
            self.browser_toggle_btn.add_css_class("active")
            self.browser_toggle_btn.handler_unblock_by_func(self._on_browser_toggle)
        
        # Give browser most of the space - leave ~250px for navigation
        # This makes the browser the star of the show
        GLib.idle_add(lambda: self.main_paned.set_position(250))
    
    def _show_browser_floating(self):
        """Show browser in a floating window."""
        if self.browser_window:
            self.browser_window.present()
            return
        
        if self.browser_panel.get_parent():
            self.browser_panel.get_parent().remove(self.browser_panel)
        
        self.browser_window = Gtk.Window()
        self.browser_window.set_title("Web Browser")
        self.browser_window.set_default_size(800, 600)
        self.browser_window.set_modal(False)
        self.browser_window.set_decorated(True)
        self.browser_window.set_child(self.browser_panel)
        self.browser_window.connect("close-request", self._on_browser_window_close)
        self.browser_window.present()
        
        self.browser_is_docked = False
        self.browser_panel_visible = True
    
    def _on_browser_window_close(self, window):
        """Handle browser floating window close."""
        window.set_child(None)
        self.browser_window = None
        self.browser_is_docked = False
        self.browser_panel_visible = False
        
        if hasattr(self, 'browser_toggle_btn'):
            self.browser_toggle_btn.set_active(False)
        
        return False
    
    def _on_browser_popout(self, button):
        """Pop out browser to floating window."""
        if self.browser_is_docked:
            self.main_paned.set_end_child(None)
            self.docked_panel = None
            self.browser_is_docked = False
            self._show_browser_floating()
    
    def _on_browser_home(self, button):
        """Navigate to home page."""
        webview = self._get_current_browser_webview()
        if webview:
            webview.load_uri(self.browser_home_url)
    
    def _on_browser_expand_toggle(self, button):
        """Toggle browser expanded view (hide/show sidebar)."""
        self.browser_expanded = not self.browser_expanded
        
        if self.browser_expanded:
            # Hide the sidebar (navigation view)
            self.navigation_view.set_visible(False)
            self.browser_expand_btn.set_icon_name("tux-view-restore-symbolic")
            self.browser_expand_btn.set_tooltip_text("Restore sidebar")
        else:
            # Show the sidebar
            self.navigation_view.set_visible(True)
            self.browser_expand_btn.set_icon_name("tux-view-fullscreen-symbolic")
            self.browser_expand_btn.set_tooltip_text("Expand browser (hide sidebar)")
    
    def _on_browser_url_activate(self, entry):
        """Handle URL entry activation."""
        text = entry.get_text().strip()
        if not text:
            return
        
        # Check if it's a URL or a search
        if '.' in text and ' ' not in text:
            # Looks like a URL
            if not text.startswith('http://') and not text.startswith('https://'):
                text = 'https://' + text
            url = text
        else:
            # Search with configured search engine
            url = self._get_search_url(text)
        
        webview = self._get_current_browser_webview()
        if webview:
            webview.load_uri(url)
        
        # Hide autocomplete
        if self.url_autocomplete_popover:
            self.url_autocomplete_popover.popdown()
    
    def _create_url_autocomplete_popover(self):
        """Create the URL autocomplete popover (called lazily after window is realized)."""
        self.url_autocomplete_popover = Gtk.Popover()
        self.url_autocomplete_popover.set_parent(self.browser_url_entry)
        self.url_autocomplete_popover.set_position(Gtk.PositionType.BOTTOM)
        self.url_autocomplete_popover.set_autohide(False)  # We control visibility
        self.url_autocomplete_popover.set_size_request(400, -1)
        
        autocomplete_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.url_autocomplete_popover.set_child(autocomplete_box)
        
        autocomplete_scroll = Gtk.ScrolledWindow()
        autocomplete_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        autocomplete_scroll.set_max_content_height(250)
        autocomplete_scroll.set_propagate_natural_height(True)
        autocomplete_box.append(autocomplete_scroll)
        
        self.url_autocomplete_list = Gtk.ListBox()
        self.url_autocomplete_list.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.url_autocomplete_list.add_css_class("boxed-list")
        self.url_autocomplete_list.connect("row-activated", self._on_autocomplete_activated)
        autocomplete_scroll.set_child(self.url_autocomplete_list)
        
        # Add controllers now that window is realized
        if not self._url_controllers_added:
            url_key_controller = Gtk.EventControllerKey()
            url_key_controller.connect("key-pressed", self._on_url_key_pressed)
            self.browser_url_entry.add_controller(url_key_controller)
            
            focus_controller = Gtk.EventControllerFocus()
            focus_controller.connect("leave", self._on_url_focus_leave)
            self.browser_url_entry.add_controller(focus_controller)
            
            self._url_controllers_added = True
    
    def _on_url_entry_changed(self, entry):
        """Show autocomplete suggestions as user types."""
        if getattr(self, '_autocomplete_active', False):
            return  # Avoid loops when we set text programmatically
        
        text = entry.get_text().strip()
        
        # Need at least 2 characters
        if len(text) < 2:
            if self.url_autocomplete_popover:
                self.url_autocomplete_popover.popdown()
            return
        
        # Create popover lazily (first time)
        if not self.url_autocomplete_popover:
            self._create_url_autocomplete_popover()
        
        # Get suggestions from history (frecency-ranked)
        suggestions = self._get_history_suggestions(text, limit=6)
        
        # Also get matching bookmarks
        bookmark_matches = []
        for bm in self.bookmarks:
            if bm.get('type') == 'separator':
                continue
            if (text.lower() in bm.get('title', '').lower() or 
                text.lower() in bm.get('url', '').lower()):
                bookmark_matches.append({
                    'url': bm['url'],
                    'title': bm.get('title', bm['url']),
                    'is_bookmark': True
                })
                if len(bookmark_matches) >= 3:
                    break
        
        # Clear existing suggestions
        while True:
            child = self.url_autocomplete_list.get_first_child()
            if child is None:
                break
            self.url_autocomplete_list.remove(child)
        
        # Combine: bookmarks first, then history
        all_suggestions = []
        seen_urls = set()
        
        for bm in bookmark_matches:
            if bm['url'] not in seen_urls:
                all_suggestions.append(bm)
                seen_urls.add(bm['url'])
        
        for h in suggestions:
            if h['url'] not in seen_urls:
                h['is_bookmark'] = False
                all_suggestions.append(h)
                seen_urls.add(h['url'])
        
        if not all_suggestions:
            self.url_autocomplete_popover.popdown()
            return
        
        # Build suggestion rows
        for suggestion in all_suggestions[:8]:
            row = self._create_autocomplete_row(suggestion)
            self.url_autocomplete_list.append(row)
        
        # Show the popover
        self.url_autocomplete_popover.popup()
    
    def _create_autocomplete_row(self, suggestion):
        """Create a row for autocomplete dropdown."""
        row = Adw.ActionRow()
        row.set_title(suggestion.get('title', suggestion['url']))
        row.set_activatable(True)
        
        # Truncate URL
        url = suggestion['url']
        display_url = url[:50] + '...' if len(url) > 50 else url
        row.set_subtitle(display_url)
        
        row.autocomplete_url = url
        
        # Icon - bookmark or history
        if suggestion.get('is_bookmark'):
            icon = Gtk.Image.new_from_icon_name("tux-user-bookmarks-symbolic")
        else:
            icon = Gtk.Image.new_from_icon_name("tux-document-open-recent-symbolic")
        row.add_prefix(icon)
        
        # Add click gesture for reliable clicking
        click = Gtk.GestureClick()
        click.connect("pressed", lambda g, n, x, y, u=url: self._on_autocomplete_row_clicked(u))
        row.add_controller(click)
        
        return row
    
    def _on_autocomplete_row_clicked(self, url):
        """Handle click on autocomplete row."""
        # Hide popover FIRST
        if self.url_autocomplete_popover:
            self.url_autocomplete_popover.popdown()
        
        # Update entry without triggering autocomplete
        self._autocomplete_active = True
        self.browser_url_entry.set_text(url)
        self._autocomplete_active = False
        
        # Navigate
        webview = self._get_current_browser_webview()
        if webview:
            webview.load_uri(url)
    
    def _on_autocomplete_activated(self, listbox, row):
        """Navigate to selected autocomplete suggestion (keyboard)."""
        # row is ListBoxRow, get_child() is our ActionRow
        action_row = row.get_child()
        if action_row and hasattr(action_row, 'autocomplete_url'):
            url = action_row.autocomplete_url
            
            # Update entry without triggering autocomplete
            self._autocomplete_active = True
            self.browser_url_entry.set_text(url)
            self._autocomplete_active = False
            
            # Hide popover
            self.url_autocomplete_popover.popdown()
            
            # Navigate
            webview = self._get_current_browser_webview()
            if webview:
                webview.load_uri(url)
    
    def _on_url_key_pressed(self, controller, keyval, keycode, state):
        """Handle keyboard navigation in URL autocomplete."""
        if not self.url_autocomplete_popover or not self.url_autocomplete_popover.is_visible():
            return False
        
        # Escape - hide autocomplete
        if keyval == Gdk.KEY_Escape:
            self.url_autocomplete_popover.popdown()
            return True
        
        # Down arrow - move to list
        if keyval == Gdk.KEY_Down:
            first_row = self.url_autocomplete_list.get_row_at_index(0)
            if first_row:
                self.url_autocomplete_list.select_row(first_row)
                first_row.grab_focus()
            return True
        
        # Up arrow - select last item
        if keyval == Gdk.KEY_Up:
            # Count rows
            i = 0
            while self.url_autocomplete_list.get_row_at_index(i):
                i += 1
            if i > 0:
                last_row = self.url_autocomplete_list.get_row_at_index(i - 1)
                if last_row:
                    self.url_autocomplete_list.select_row(last_row)
                    last_row.grab_focus()
            return True
        
        return False
    
    def _on_url_focus_leave(self, controller):
        """Hide autocomplete when URL entry loses focus."""
        # Small delay to allow clicking on suggestions
        GLib.timeout_add(150, self._maybe_hide_autocomplete)
    
    def _maybe_hide_autocomplete(self):
        """Hide autocomplete if focus isn't in the list."""
        if self.url_autocomplete_popover:
            # Check if focus went to the autocomplete list
            focus = self.get_focus()
            if focus and hasattr(focus, 'get_parent'):
                parent = focus.get_parent()
                while parent:
                    if parent == self.url_autocomplete_list:
                        return False  # Focus is in list, don't hide
                    parent = parent.get_parent() if hasattr(parent, 'get_parent') else None
            
            self.url_autocomplete_popover.popdown()
        return False  # Don't repeat
    
    def _on_bookmark_toggle(self, button):
        """Add or remove current page from bookmarks."""
        webview = self._get_current_browser_webview()
        if not webview:
            return
        
        url = webview.get_uri()
        title = webview.get_title() or url
        
        if not url or url == "about:blank":
            return
        
        # Check if already bookmarked
        existing = None
        for i, bm in enumerate(self.bookmarks):
            if bm.get('url') == url:
                existing = i
                break
        
        if existing is not None:
            # Remove bookmark
            del self.bookmarks[existing]
            self.show_toast("Bookmark removed")
        else:
            # Add bookmark
            import time
            self.bookmarks.append({
                'url': url,
                'title': title,
                'added': int(time.time())
            })
            self.show_toast("Bookmark added")
        
        self._save_bookmarks()
        self._update_bookmark_star()
        self._refresh_bookmarks_list()
        self._refresh_bookmarks_bar()
    
    def _get_bookmark_favicon(self, url):
        """Get favicon image for a bookmark URL."""
        from urllib.parse import urlparse
        import os
        
        # Default icon
        icon = Gtk.Image.new_from_icon_name("tux-web-browser-symbolic")
        icon.set_pixel_size(24)
        
        if not url:
            return icon
        
        try:
            # Extract domain from URL
            parsed = urlparse(url)
            domain = parsed.netloc
            if not domain:
                return icon
            
            # Check favicon cache
            cache_dir = os.path.join(GLib.get_user_cache_dir(), 'tux-assistant', 'favicons')
            os.makedirs(cache_dir, exist_ok=True)
            
            cache_file = os.path.join(cache_dir, f"{domain}.ico")
            
            if os.path.exists(cache_file):
                # Load from cache
                try:
                    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(cache_file, 24, 24, True)
                    icon = Gtk.Image.new_from_pixbuf(pixbuf)
                except:
                    pass
            else:
                # Queue async favicon fetch (don't block UI)
                GLib.idle_add(self._fetch_favicon_async, domain, cache_file)
        except:
            pass
        
        return icon
    
    def _fetch_favicon_async(self, domain, cache_file):
        """Fetch favicon in background."""
        import urllib.request
        import os
        
        try:
            # Use DuckDuckGo's favicon service
            favicon_url = f"https://icons.duckduckgo.com/ip3/{domain}.ico"
            
            # Fetch with timeout
            urllib.request.urlretrieve(favicon_url, cache_file)
        except:
            pass
        
        return False  # Don't repeat
    
    def _update_bookmark_star(self):
        """Update bookmark star icon based on current URL."""
        if not hasattr(self, 'bookmark_star_btn'):
            return
        
        webview = self._get_current_browser_webview()
        if not webview:
            return
        
        url = webview.get_uri()
        is_bookmarked = any(bm.get('url') == url for bm in self.bookmarks)
        
        if is_bookmarked:
            self.bookmark_star_btn.set_icon_name("tux-starred-symbolic")
            self.bookmark_star_btn.set_tooltip_text("Remove bookmark (Ctrl+D)")
        else:
            self.bookmark_star_btn.set_icon_name("tux-non-starred-symbolic")
            self.bookmark_star_btn.set_tooltip_text("Add bookmark (Ctrl+D)")
    
    def _on_bookmarks_popover_show(self):
        """Handle bookmarks popover showing."""
        # Clear search and refresh list
        if hasattr(self, 'bookmarks_search_entry'):
            self.bookmarks_search_entry.set_text("")
        self._refresh_bookmarks_list()
    
    def _on_bookmarks_search_changed(self, entry):
        """Filter bookmarks based on search text."""
        self._refresh_bookmarks_list(entry.get_text())
    
    def _on_bookmarks_sort_changed(self, dropdown, param):
        """Handle sort option change."""
        search_text = ""
        if hasattr(self, 'bookmarks_search_entry'):
            search_text = self.bookmarks_search_entry.get_text()
        self._refresh_bookmarks_list(search_text)
    
    # ==================== History Panel Methods ====================
    
    def _on_history_popover_show(self):
        """Handle history popover showing."""
        if hasattr(self, 'history_search_entry'):
            self.history_search_entry.set_text("")
        self._refresh_history_list()
    
    def _on_history_search_changed(self, entry):
        """Filter history based on search text."""
        self._refresh_history_list(entry.get_text())
    
    def _refresh_history_list(self, search_filter=""):
        """Rebuild the history list in the popover."""
        import time
        from datetime import datetime
        
        if not hasattr(self, 'history_list_box'):
            return
        
        # Clear existing
        while True:
            child = self.history_list_box.get_first_child()
            if child is None:
                break
            self.history_list_box.remove(child)
        
        # Get history entries
        search = search_filter.strip() if search_filter else None
        entries = self._get_history(limit=100, search=search)
        
        if not entries:
            empty = Adw.ActionRow()
            empty.set_title("No history" if not search else "No matches found")
            empty.add_css_class("dim-label")
            self.history_list_box.append(empty)
            return
        
        # Group by time
        now = time.time()
        today_start = now - (now % 86400)
        yesterday_start = today_start - 86400
        week_start = now - 604800
        
        current_section = None
        
        for entry in entries:
            last_visit = entry['last_visit']
            
            # Determine section
            if last_visit >= today_start:
                section = "Today"
            elif last_visit >= yesterday_start:
                section = "Yesterday"
            elif last_visit >= week_start:
                section = "This Week"
            else:
                section = "Older"
            
            # Add section header if new section
            if section != current_section and not search_filter:
                current_section = section
                header = Adw.ActionRow()
                header.set_title(section)
                header.add_css_class("dim-label")
                header.set_activatable(False)
                header.set_selectable(False)
                self.history_list_box.append(header)
            
            # Create history row
            row = self._create_history_row(entry)
            self.history_list_box.append(row)
    
    def _create_history_row(self, entry):
        """Create a row for history list."""
        import time
        from datetime import datetime
        
        row = Adw.ActionRow()
        row.set_title(entry.get('title', entry['url']))
        
        # Format time nicely
        visit_time = entry['last_visit']
        dt = datetime.fromtimestamp(visit_time)
        now = time.time()
        
        if now - visit_time < 86400:  # Today
            time_str = dt.strftime("%H:%M")
        else:
            time_str = dt.strftime("%b %d")
        
        # Escape ampersands for markup
        display_url = entry['url'][:60].replace('&', '&amp;')
        row.set_subtitle(f"{time_str} • {display_url}{'...' if len(entry['url']) > 60 else ''}")
        row.set_tooltip_text(entry['url'])
        
        # Make clickable
        row.set_activatable(True)
        row.history_url = entry['url']
        row.connect("activated", self._on_history_activated)
        
        # Favicon
        favicon = self._get_bookmark_favicon(entry['url'])
        row.add_prefix(favicon)
        
        # Delete button
        delete_btn = Gtk.Button.new_from_icon_name("tux-edit-delete-symbolic")
        delete_btn.add_css_class("flat")
        delete_btn.set_valign(Gtk.Align.CENTER)
        delete_btn.set_tooltip_text("Remove from history")
        delete_btn.history_url = entry['url']
        delete_btn.connect("clicked", self._on_history_delete_entry)
        row.add_suffix(delete_btn)
        
        return row
    
    def _on_history_activated(self, row):
        """Navigate to history entry."""
        url = getattr(row, 'history_url', None)
        if url and hasattr(self, 'history_popover'):
            self.history_popover.popdown()
            webview = self._get_current_browser_webview()
            if webview:
                webview.load_uri(url)
    
    def _on_history_delete_entry(self, button):
        """Delete single history entry."""
        url = getattr(button, 'history_url', None)
        if url:
            self._delete_history_entry(url)
            # Refresh list
            search = ""
            if hasattr(self, 'history_search_entry'):
                search = self.history_search_entry.get_text()
            self._refresh_history_list(search)
    
    def _clear_history_action(self, time_range):
        """Clear history with confirmation."""
        if hasattr(self, 'history_popover'):
            self.history_popover.popdown()
        
        if time_range == 'all':
            count = self._get_history_count()
            dialog = Adw.MessageDialog(
                transient_for=self,
                heading="Clear All History?",
                body=f"This will permanently delete {count} history entries."
            )
            dialog.add_response("cancel", "Cancel")
            dialog.add_response("clear", "Clear All")
            dialog.set_response_appearance("clear", Adw.ResponseAppearance.DESTRUCTIVE)
            dialog.set_default_response("cancel")
            dialog.set_close_response("cancel")
            
            def on_response(d, response):
                if response == "clear":
                    self._clear_history(time_range)
                    self.show_toast("History cleared")
            
            dialog.connect("response", on_response)
            dialog.present()
        else:
            # For hour/today, just do it
            self._clear_history(time_range)
            label = "Last hour" if time_range == "hour" else "Today's history"
            self.show_toast(f"{label} cleared")
    
    def _show_clear_history_dialog(self, button=None):
        """Show dialog to choose what history to clear."""
        if hasattr(self, 'history_popover'):
            self.history_popover.popdown()
        
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Clear History",
            body="Choose what to clear:"
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("hour", "Last Hour")
        dialog.add_response("today", "Today")
        dialog.add_response("all", "All Time")
        dialog.set_response_appearance("all", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        
        def on_response(d, response):
            if response in ('hour', 'today', 'all'):
                self._clear_history(response)
                if response == 'all':
                    self.show_toast("All history cleared")
                elif response == 'hour':
                    self.show_toast("Last hour cleared")
                else:
                    self.show_toast("Today's history cleared")
                # Refresh panel if open
                if hasattr(self, 'history_search_entry'):
                    self._refresh_history_list(self.history_search_entry.get_text())
        
        dialog.connect("response", on_response)
        dialog.present()
    
    def _show_history_window(self, button=None):
        """Show full history window."""
        if hasattr(self, 'history_popover'):
            self.history_popover.popdown()
        
        # Track current filters
        self.hw_search_filter = ""
        self.hw_time_filter = None
        
        # Create the window
        self.history_window = Adw.Window()
        self.history_window.set_title("History")
        self.history_window.set_default_size(700, 550)
        self.history_window.set_transient_for(self)
        self.history_window.set_modal(False)
        
        # Main layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.history_window.set_content(main_box)
        
        # Header bar
        header = Adw.HeaderBar()
        main_box.append(header)
        
        # Time filter dropdown on left
        time_options = ["All Time", "Today", "Yesterday", "This Week", "This Month"]
        time_model = Gtk.StringList.new(time_options)
        self.hw_time_dropdown = Gtk.DropDown(model=time_model)
        self.hw_time_dropdown.set_tooltip_text("Filter by time")
        self.hw_time_dropdown.connect("notify::selected", self._on_hw_time_filter_changed)
        header.pack_start(self.hw_time_dropdown)
        
        # Search entry as title
        self.hw_search = Gtk.SearchEntry()
        self.hw_search.set_placeholder_text("Search history...")
        self.hw_search.set_hexpand(True)
        self.hw_search.connect("search-changed", self._on_hw_search_changed)
        header.set_title_widget(self.hw_search)
        
        # Entry count label on right
        self.hw_count_label = Gtk.Label()
        self.hw_count_label.add_css_class("dim-label")
        header.pack_end(self.hw_count_label)
        
        # Scrolled window for history list
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        main_box.append(scroll)
        
        # ListBox with multi-select
        self.hw_list = Gtk.ListBox()
        self.hw_list.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.hw_list.add_css_class("boxed-list")
        self.hw_list.set_margin_start(12)
        self.hw_list.set_margin_end(12)
        self.hw_list.set_margin_top(12)
        self.hw_list.set_margin_bottom(12)
        scroll.set_child(self.hw_list)
        
        # Bottom toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        toolbar.set_margin_start(12)
        toolbar.set_margin_end(12)
        toolbar.set_margin_bottom(12)
        toolbar.set_margin_top(8)
        main_box.append(toolbar)
        
        # Delete Selected button
        delete_btn = Gtk.Button(label="Delete Selected")
        delete_btn.set_icon_name("tux-edit-delete-symbolic")
        delete_btn.add_css_class("destructive-action")
        delete_btn.connect("clicked", self._on_hw_delete_selected)
        toolbar.append(delete_btn)
        
        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        toolbar.append(spacer)
        
        # Clear All button
        clear_all_btn = Gtk.Button(label="Clear All History")
        clear_all_btn.set_icon_name("tux-edit-clear-all-symbolic")
        clear_all_btn.add_css_class("destructive-action")
        clear_all_btn.connect("clicked", self._on_hw_clear_all)
        toolbar.append(clear_all_btn)
        
        # Keyboard shortcuts
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_hw_key_pressed)
        self.history_window.add_controller(key_controller)
        
        # Populate the list
        self._refresh_hw_list()
        
        # Show the window
        self.history_window.present()
    
    def _refresh_hw_list(self):
        """Refresh the history window list."""
        import time
        from datetime import datetime
        
        # Clear existing
        while True:
            child = self.hw_list.get_first_child()
            if child is None:
                break
            self.hw_list.remove(child)
        
        # Map dropdown selection to time filter
        time_map = {
            0: None,        # All Time
            1: 'today',
            2: 'yesterday', 
            3: 'week',
            4: 'month'
        }
        
        time_filter = time_map.get(self.hw_time_dropdown.get_selected(), None)
        search = self.hw_search.get_text().strip() if hasattr(self, 'hw_search') else None
        search = search if search else None
        
        # Get entries
        entries = self._get_history(limit=500, search=search, time_filter=time_filter)
        
        # Update count label
        total_count = self._get_history_count()
        if search or time_filter:
            self.hw_count_label.set_text(f"{len(entries)} of {total_count}")
        else:
            self.hw_count_label.set_text(f"{total_count} entries")
        
        if not entries:
            empty = Adw.ActionRow()
            if search:
                empty.set_title("No matches found")
            elif time_filter:
                empty.set_title("No history for this time period")
            else:
                empty.set_title("No browsing history")
            empty.add_css_class("dim-label")
            empty.set_activatable(False)
            empty.set_selectable(False)
            self.hw_list.append(empty)
            return
        
        # Group by date
        now = time.time()
        today_start = now - (now % 86400)
        yesterday_start = today_start - 86400
        week_start = now - 604800
        month_start = now - 2592000
        
        current_section = None
        
        for entry in entries:
            last_visit = entry['last_visit']
            
            # Determine section
            if last_visit >= today_start:
                section = "Today"
            elif last_visit >= yesterday_start:
                section = "Yesterday"
            elif last_visit >= week_start:
                section = "This Week"
            elif last_visit >= month_start:
                section = "This Month"
            else:
                # Format as month/year for older entries
                dt = datetime.fromtimestamp(last_visit)
                section = dt.strftime("%B %Y")
            
            # Add section header if new section (only when not searching)
            if section != current_section and not search:
                current_section = section
                header = Adw.ActionRow()
                header.set_title(section)
                header.add_css_class("dim-label")
                header.set_activatable(False)
                header.set_selectable(False)
                self.hw_list.append(header)
            
            # Create history row
            row = self._create_hw_row(entry)
            self.hw_list.append(row)
    
    def _create_hw_row(self, entry):
        """Create a row for history window list."""
        import time
        from datetime import datetime
        
        row = Adw.ActionRow()
        row.set_title(entry.get('title', entry['url']))
        
        # Format timestamp
        visit_time = entry['last_visit']
        dt = datetime.fromtimestamp(visit_time)
        now = time.time()
        
        if now - visit_time < 86400:
            time_str = dt.strftime("%H:%M")
        else:
            time_str = dt.strftime("%b %d, %H:%M")
        
        # Truncate URL for display
        url = entry['url']
        display_url = url[:70] + '...' if len(url) > 70 else url
        display_url = display_url.replace('&', '&amp;')  # Escape for markup
        
        row.set_subtitle(f"{time_str} • {display_url}")
        row.set_tooltip_text(url)
        
        # Store data
        row.history_url = url
        
        # Favicon
        favicon = self._get_bookmark_favicon(url)
        row.add_prefix(favicon)
        
        # Visit button (to navigate)
        visit_btn = Gtk.Button.new_from_icon_name("tux-go-jump-symbolic")
        visit_btn.add_css_class("flat")
        visit_btn.set_valign(Gtk.Align.CENTER)
        visit_btn.set_tooltip_text("Visit this page")
        visit_btn.history_url = url
        visit_btn.connect("clicked", self._on_hw_visit_clicked)
        row.add_suffix(visit_btn)
        
        return row
    
    def _on_hw_search_changed(self, entry):
        """Handle search in history window."""
        self._refresh_hw_list()
    
    def _on_hw_time_filter_changed(self, dropdown, param):
        """Handle time filter change."""
        self._refresh_hw_list()
    
    def _on_hw_visit_clicked(self, button):
        """Navigate to history entry from window."""
        url = getattr(button, 'history_url', None)
        if url:
            self.history_window.close()
            webview = self._get_current_browser_webview()
            if webview:
                webview.load_uri(url)
    
    def _on_hw_delete_selected(self, button):
        """Delete selected history entries."""
        selected_rows = self.hw_list.get_selected_rows()
        
        # Filter to only rows with history_url (not headers)
        urls_to_delete = []
        for row in selected_rows:
            # Get the actual child widget (ActionRow)
            child = row.get_child()
            if child and hasattr(child, 'history_url'):
                urls_to_delete.append(child.history_url)
        
        if not urls_to_delete:
            self.show_toast("No history entries selected")
            return
        
        # Delete them
        self._delete_history_entries(urls_to_delete)
        
        # Refresh
        self._refresh_hw_list()
        
        # Also refresh panel if open
        if hasattr(self, 'history_search_entry'):
            self._refresh_history_list(self.history_search_entry.get_text())
        
        self.show_toast(f"Deleted {len(urls_to_delete)} entr{'y' if len(urls_to_delete) == 1 else 'ies'}")
    
    def _on_hw_clear_all(self, button):
        """Clear all history from window."""
        count = self._get_history_count()
        
        dialog = Adw.MessageDialog(
            transient_for=self.history_window,
            heading="Clear All History?",
            body=f"This will permanently delete all {count} history entries."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("clear", "Clear All")
        dialog.set_response_appearance("clear", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        
        def on_response(d, response):
            if response == "clear":
                self._clear_history('all')
                self._refresh_hw_list()
                self.show_toast("All history cleared")
        
        dialog.connect("response", on_response)
        dialog.present()
    
    def _on_hw_key_pressed(self, controller, keyval, keycode, state):
        """Handle keyboard shortcuts in history window."""
        # Delete key - delete selected
        if keyval == Gdk.KEY_Delete:
            self._on_hw_delete_selected(None)
            return True
        
        # Escape - close window
        if keyval == Gdk.KEY_Escape:
            self.history_window.close()
            return True
        
        # Ctrl+A - select all
        if keyval == Gdk.KEY_a and state & Gdk.ModifierType.CONTROL_MASK:
            self.hw_list.select_all()
            return True
        
        # Ctrl+F - focus search
        if keyval == Gdk.KEY_f and state & Gdk.ModifierType.CONTROL_MASK:
            self.hw_search.grab_focus()
            return True
        
        return False
    
    # ==================== End History Panel Methods ====================
    
    def _refresh_bookmarks_list(self, search_filter=""):
        """Rebuild the bookmarks list in the popover."""
        if not hasattr(self, 'bookmarks_list_box'):
            return
        
        # Clear existing items
        while True:
            child = self.bookmarks_list_box.get_first_child()
            if child is None:
                break
            self.bookmarks_list_box.remove(child)
        
        # Filter bookmarks if search text provided
        search_filter = search_filter.lower().strip()
        if search_filter:
            filtered = [bm for bm in self.bookmarks 
                       if search_filter in bm.get('title', '').lower() 
                       or search_filter in bm.get('url', '').lower()]
        else:
            filtered = list(self.bookmarks)  # Copy to avoid mutating original
        
        # Apply sorting
        if hasattr(self, 'bookmarks_sort_dropdown'):
            sort_index = self.bookmarks_sort_dropdown.get_selected()
            if sort_index == 1:  # Name A-Z
                filtered.sort(key=lambda bm: bm.get('title', '').lower())
            elif sort_index == 2:  # Name Z-A
                filtered.sort(key=lambda bm: bm.get('title', '').lower(), reverse=True)
            elif sort_index == 3:  # Recent (by added timestamp, newest first)
                filtered.sort(key=lambda bm: bm.get('added', 0), reverse=True)
            # sort_index == 0 is Default (original order)
        
        if not filtered:
            # Show empty/no results message
            if search_filter:
                empty_label = Gtk.Label(label="No matching bookmarks")
            else:
                empty_label = Gtk.Label(label="No bookmarks yet")
            empty_label.add_css_class("dim-label")
            empty_label.set_margin_top(20)
            empty_label.set_margin_bottom(20)
            self.bookmarks_list_box.append(empty_label)
            return
        
        # Group bookmarks by folder
        unfiled = [bm for bm in filtered if not bm.get('folder')]
        
        # Add ALL folders (even empty ones)
        for folder_name in self.bookmark_folders:
            folder_bookmarks = [bm for bm in filtered if bm.get('folder') == folder_name]
            
            # Folder header box with expander and delete button
            folder_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            folder_header.set_margin_top(4)
            folder_header.set_margin_bottom(4)
            
            # Add drop target to folder header
            drop_target = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.MOVE)
            drop_target.set_preload(True)
            drop_target.folder_name = folder_name
            drop_target.connect("accept", self._on_drop_accept)
            drop_target.connect("drop", self._on_bookmark_drop_to_folder)
            drop_target.connect("enter", self._on_drop_enter)
            drop_target.connect("leave", self._on_drop_leave)
            folder_header.add_controller(drop_target)
            
            # Expander takes most space
            expander = Gtk.Expander(label=f"📁 {folder_name} ({len(folder_bookmarks)})")
            expander.set_expanded(True)
            expander.set_hexpand(True)
            folder_header.append(expander)
            
            # Delete folder button
            delete_folder_btn = Gtk.Button.new_from_icon_name("tux-edit-delete-symbolic")
            delete_folder_btn.add_css_class("flat")
            delete_folder_btn.set_tooltip_text(f"Delete folder '{folder_name}'")
            delete_folder_btn.set_valign(Gtk.Align.CENTER)
            delete_folder_btn.folder_name = folder_name
            delete_folder_btn.connect("clicked", self._on_delete_folder)
            folder_header.append(delete_folder_btn)
            
            self.bookmarks_list_box.append(folder_header)
            
            if folder_bookmarks:
                folder_list = Gtk.ListBox()
                folder_list.set_selection_mode(Gtk.SelectionMode.NONE)
                folder_list.add_css_class("boxed-list")
                folder_list.set_margin_start(16)  # Indent under folder
                
                for bm in folder_bookmarks:
                    row = self._create_bookmark_row(bm)
                    folder_list.append(row)
                
                # Link list visibility to expander
                expander.folder_list = folder_list
                expander.connect("notify::expanded", self._on_folder_expander_toggled)
                
                self.bookmarks_list_box.append(folder_list)
            else:
                # Empty folder message
                empty_msg = Gtk.Label(label="(empty)")
                empty_msg.add_css_class("dim-label")
                empty_msg.set_margin_start(24)
                empty_msg.set_xalign(0)
                expander.empty_label = empty_msg
                expander.connect("notify::expanded", self._on_folder_expander_toggled)
                self.bookmarks_list_box.append(empty_msg)
        
        # Add unfiled section (always show if there are folders, for drop target)
        if self.bookmark_folders:
            # Unfiled header with drop target
            unfiled_header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            unfiled_header.set_margin_top(8)
            unfiled_header.set_margin_bottom(4)
            
            unfiled_label = Gtk.Label(label="Unfiled" if unfiled else "Unfiled (drop here)")
            unfiled_label.add_css_class("dim-label")
            unfiled_label.set_xalign(0)
            unfiled_label.set_hexpand(True)
            unfiled_header.append(unfiled_label)
            
            # Add drop target to unfiled section
            drop_target = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.MOVE)
            drop_target.set_preload(True)
            drop_target.folder_name = None  # None means unfiled
            drop_target.connect("accept", self._on_drop_accept)
            drop_target.connect("drop", self._on_bookmark_drop_to_folder)
            drop_target.connect("enter", self._on_drop_enter)
            drop_target.connect("leave", self._on_drop_leave)
            unfiled_header.add_controller(drop_target)
            
            self.bookmarks_list_box.append(unfiled_header)
        
        # Add unfiled bookmarks
        for bm in unfiled:
            row = self._create_bookmark_row(bm)
            self.bookmarks_list_box.append(row)
    
    def _on_folder_expander_toggled(self, expander, param):
        """Show/hide folder contents when expander is toggled."""
        expanded = expander.get_expanded()
        if hasattr(expander, 'folder_list'):
            expander.folder_list.set_visible(expanded)
        if hasattr(expander, 'empty_label'):
            expander.empty_label.set_visible(expanded)
    
    def _on_delete_folder(self, button):
        """Delete a folder (move bookmarks to unfiled)."""
        folder_name = getattr(button, 'folder_name', None)
        if not folder_name:
            return
        
        # Count bookmarks in folder
        folder_bookmarks = [bm for bm in self.bookmarks if bm.get('folder') == folder_name]
        
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=f"Delete '{folder_name}'?",
            body=f"This folder contains {len(folder_bookmarks)} bookmark(s). They will be moved to Unfiled."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        
        dialog.folder_name = folder_name
        dialog.connect("response", self._on_delete_folder_response)
        dialog.present()
    
    def _on_delete_folder_response(self, dialog, response):
        """Handle delete folder confirmation."""
        if response == "delete":
            folder_name = dialog.folder_name
            
            # Remove folder assignment from bookmarks
            for bm in self.bookmarks:
                if bm.get('folder') == folder_name:
                    del bm['folder']
            
            # Remove folder from list
            if folder_name in self.bookmark_folders:
                self.bookmark_folders.remove(folder_name)
            
            self._save_bookmarks()
            self._refresh_bookmarks_list()
            self._refresh_bookmarks_bar()
            self.show_toast(f"Folder '{folder_name}' deleted")
    
    def _create_bookmark_row(self, bm):
        """Create a bookmark row for the list."""
        # Check if this is a separator
        if bm.get('type') == 'separator':
            return self._create_separator_row(bm)
        
        row = Adw.ActionRow()
        row.set_title(bm.get('title', 'Untitled'))
        row.set_subtitle(bm.get('url', ''))
        row.set_activatable(True)
        row.set_tooltip_text(bm.get('url', ''))
        
        # Drag handle as first prefix
        drag_handle = Gtk.Image.new_from_icon_name("tux-list-drag-handle-symbolic")
        drag_handle.add_css_class("dim-label")
        row.add_prefix(drag_handle)
        
        # Favicon prefix
        favicon = self._get_bookmark_favicon(bm.get('url', ''))
        row.add_prefix(favicon)
        
        # Store bookmark data for drag/drop and handlers
        row.bookmark_url = bm.get('url')
        row.bookmark_data = bm
        row.connect("activated", self._on_bookmark_activated)
        
        # Add drag source
        drag_source = Gtk.DragSource()
        drag_source.set_actions(Gdk.DragAction.MOVE)
        drag_source.connect("prepare", self._on_bookmark_drag_prepare)
        drag_source.connect("drag-begin", self._on_bookmark_drag_begin)
        drag_source.connect("drag-end", self._on_drag_end)
        row.add_controller(drag_source)
        
        # Add drop target for reordering
        drop_target = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.MOVE)
        drop_target.set_preload(True)
        drop_target.target_bookmark = bm
        drop_target.connect("accept", self._on_drop_accept)
        drop_target.connect("drop", self._on_unified_drop)
        drop_target.connect("enter", self._on_drop_enter)
        drop_target.connect("leave", self._on_drop_leave)
        row.add_controller(drop_target)
        
        # Edit button
        edit_btn = Gtk.Button.new_from_icon_name("tux-document-edit-symbolic")
        edit_btn.set_valign(Gtk.Align.CENTER)
        edit_btn.add_css_class("flat")
        edit_btn.set_tooltip_text("Edit bookmark")
        edit_btn.bookmark_url = bm.get('url')
        edit_btn.bookmark_title = bm.get('title', '')
        edit_btn.bookmark_folder = bm.get('folder')
        edit_btn.connect("clicked", self._on_bookmark_edit)
        row.add_suffix(edit_btn)
        
        # Delete button
        delete_btn = Gtk.Button.new_from_icon_name("tux-edit-delete-symbolic")
        delete_btn.set_valign(Gtk.Align.CENTER)
        delete_btn.add_css_class("flat")
        delete_btn.set_tooltip_text("Remove bookmark")
        delete_btn.bookmark_url = bm.get('url')
        delete_btn.connect("clicked", self._on_bookmark_delete)
        row.add_suffix(delete_btn)
        
        return row
    
    def _create_separator_row(self, bm):
        """Create a separator row for the list."""
        # Use ActionRow for consistent styling and hit area
        row = Adw.ActionRow()
        row.set_title("──────────────")
        row.set_subtitle("Separator")
        row.add_css_class("dim-label")
        
        # Drag handle as first prefix
        drag_handle = Gtk.Image.new_from_icon_name("tux-list-drag-handle-symbolic")
        drag_handle.add_css_class("dim-label")
        row.add_prefix(drag_handle)
        
        # Delete button
        delete_btn = Gtk.Button.new_from_icon_name("tux-edit-delete-symbolic")
        delete_btn.set_valign(Gtk.Align.CENTER)
        delete_btn.add_css_class("flat")
        delete_btn.set_tooltip_text("Remove separator")
        delete_btn.separator_data = bm
        delete_btn.connect("clicked", self._on_separator_delete)
        row.add_suffix(delete_btn)
        
        # Store separator data for drag
        row.bookmark_data = bm
        row.is_separator = True
        
        # Add drag source for reordering
        drag_source = Gtk.DragSource()
        drag_source.set_actions(Gdk.DragAction.MOVE)
        drag_source.connect("prepare", self._on_separator_drag_prepare)
        drag_source.connect("drag-begin", self._on_separator_drag_begin)
        drag_source.connect("drag-end", self._on_drag_end)
        row.add_controller(drag_source)
        
        # Add drop target so items can be dropped ON this separator
        drop_target = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.MOVE)
        drop_target.set_preload(True)
        drop_target.separator_data = bm
        drop_target.target_bookmark = bm  # For unified handler
        drop_target.connect("accept", self._on_drop_accept)
        drop_target.connect("drop", self._on_unified_drop)
        drop_target.connect("enter", self._on_drop_enter)
        drop_target.connect("leave", self._on_drop_leave)
        row.add_controller(drop_target)
        
        return row
    
    def _on_separator_delete(self, button):
        """Delete a separator."""
        sep_data = getattr(button, 'separator_data', None)
        if sep_data and sep_data in self.bookmarks:
            self.bookmarks.remove(sep_data)
            self._save_bookmarks()
            self._refresh_bookmarks_list()
            self._refresh_bookmarks_bar()
            self.show_toast("Separator removed")
    
    def _on_separator_drag_prepare(self, source, x, y):
        """Prepare separator for drag."""
        try:
            widget = source.get_widget()
            sep_data = getattr(widget, 'bookmark_data', None)
            if sep_data:
                # Use a unique identifier for separator
                self._dragging_bookmark_url = f"__separator__{id(sep_data)}"
                self._dragging_separator = sep_data
                # Use typed value that matches drop target expectation
                value = GObject.Value(GObject.TYPE_STRING, "separator")
                content = Gdk.ContentProvider.new_for_value(value)
                return content
        except Exception as e:
            print(f"Separator drag prepare error: {e}")
        return None
    
    def _on_separator_drag_begin(self, source, drag):
        """Set drag icon for separator."""
        try:
            icon = Gtk.DragIcon.get_for_drag(drag)
            label = Gtk.Label(label="── Separator ──")
            label.add_css_class("card")
            label.set_margin_top(8)
            label.set_margin_bottom(8)
            label.set_margin_start(8)
            label.set_margin_end(8)
            icon.set_child(label)
        except Exception as e:
            print(f"Separator drag begin error: {e}")
    
    def _on_separator_drop(self, drop_target, value, x, y):
        """Handle item dropped on a separator - insert at separator's position."""
        try:
            url = getattr(self, '_dragging_bookmark_url', None)
            dragged_sep = getattr(self, '_dragging_separator', None)
            target_sep = getattr(drop_target, 'separator_data', None)
            
            
            if not target_sep:
                return False
            
            # Find what we're dragging
            dragged_item = None
            if dragged_sep and dragged_sep in self.bookmarks:
                dragged_item = dragged_sep
            elif url:
                for bm in self.bookmarks:
                    if bm.get('url') == url:
                        dragged_item = bm
                        break
            
            if not dragged_item:
                return False
            
            if dragged_item == target_sep:
                return False
            
            # Find target separator's position
            try:
                target_idx = self.bookmarks.index(target_sep)
            except ValueError:
                return False
            
            # Remove dragged item from current position
            self.bookmarks.remove(dragged_item)
            
            # Remove folder (moving to unfiled)
            if 'folder' in dragged_item:
                del dragged_item['folder']
            
            # Recalculate target index after removal
            try:
                target_idx = self.bookmarks.index(target_sep)
            except ValueError:
                target_idx = len(self.bookmarks)
            
            # Insert at target position
            self.bookmarks.insert(target_idx, dragged_item)
            
            self._save_bookmarks()
            self._refresh_bookmarks_list()
            self._refresh_bookmarks_bar()
            self.show_toast("Reordered")
            return True
            
        except Exception as e:
            print(f"Separator drop error: {e}")
        return False
    
    def _on_unified_drop(self, drop_target, value, x, y):
        """Unified handler for dropping bookmarks or separators on any target."""
        try:
            url = getattr(self, '_dragging_bookmark_url', None)
            dragged_sep = getattr(self, '_dragging_separator', None)
            target_bm = getattr(drop_target, 'target_bookmark', None)
            target_index = getattr(drop_target, 'target_index', 0)
            
            
            if not target_bm:
                return False
            
            # Find what we're dragging
            dragged_item = None
            if dragged_sep and dragged_sep in self.bookmarks:
                dragged_item = dragged_sep
            elif url:
                for bm in self.bookmarks:
                    if bm.get('url') == url:
                        dragged_item = bm
                        break
            
            if not dragged_item:
                return False
            
            if dragged_item == target_bm:
                return False
            
            # Find target's position
            try:
                target_idx = self.bookmarks.index(target_bm)
            except ValueError:
                return False
            
            # Remove dragged item
            self.bookmarks.remove(dragged_item)
            
            # Remove folder assignment
            if 'folder' in dragged_item:
                del dragged_item['folder']
            
            # Recalculate target index after removal
            try:
                target_idx = self.bookmarks.index(target_bm)
            except ValueError:
                target_idx = len(self.bookmarks)
            
            # Insert at target position
            self.bookmarks.insert(target_idx, dragged_item)
            
            self._save_bookmarks()
            self._refresh_bookmarks_list()
            self._refresh_bookmarks_bar()
            self.show_toast("Reordered")
            return True
            
        except Exception as e:
            print(f"Unified drop error: {e}")
        return False
    
    def _on_bookmark_drag_prepare(self, source, x, y):
        """Prepare bookmark data for drag."""
        try:
            row = source.get_widget()
            url = getattr(row, 'bookmark_url', '')
            if url:
                # Store dragged bookmark URL in instance for drop handler
                self._dragging_bookmark_url = url
                # Use GLib.Bytes for reliable transfer
                value = GObject.Value(GObject.TYPE_STRING, url)
                content = Gdk.ContentProvider.new_for_value(value)
                return content
        except Exception as e:
            print(f"Drag prepare error: {e}")
        return None
    
    def _on_bookmark_drag_begin(self, source, drag):
        """Set drag icon when drag begins."""
        try:
            row = source.get_widget()
            title = row.get_title() or "Bookmark"
            # Use a simple icon for drag
            icon = Gtk.DragIcon.get_for_drag(drag)
            label = Gtk.Label(label=f"📑 {title[:20]}")
            label.add_css_class("card")
            label.set_margin_top(8)
            label.set_margin_bottom(8)
            label.set_margin_start(8)
            label.set_margin_end(8)
            icon.set_child(label)
        except Exception as e:
            print(f"Drag begin error: {e}")
    
    def _on_drag_end(self, source, drag, delete_data):
        """Clean up after drag ends."""
        self._dragging_bookmark_url = None
        self._dragging_separator = None
    
    def _on_bar_bookmark_drag_prepare(self, source, x, y):
        """Prepare bookmark data for drag from toolbar."""
        try:
            btn = source.get_widget()
            url = getattr(btn, 'bookmark_url', '')
            if url:
                self._dragging_bookmark_url = url
                value = GObject.Value(GObject.TYPE_STRING, url)
                content = Gdk.ContentProvider.new_for_value(value)
                return content
        except Exception as e:
            print(f"Bar drag prepare error: {e}")
        return None
    
    def _on_bar_bookmark_drag_begin(self, source, drag):
        """Set drag icon when drag begins from toolbar."""
        try:
            btn = source.get_widget()
            title = getattr(btn, 'bookmark_title', 'Bookmark')
            icon = Gtk.DragIcon.get_for_drag(drag)
            label = Gtk.Label(label=f"📑 {title[:20]}")
            label.add_css_class("card")
            label.set_margin_top(8)
            label.set_margin_bottom(8)
            label.set_margin_start(8)
            label.set_margin_end(8)
            icon.set_child(label)
        except Exception as e:
            print(f"Bar drag begin error: {e}")
    
    def _on_popover_drag_prepare(self, source, x, y):
        """Prepare bookmark data for drag from popover."""
        try:
            row = source.get_widget()
            url = getattr(row, 'bookmark_url', '')
            if url:
                self._dragging_bookmark_url = url
                value = GObject.Value(GObject.TYPE_STRING, url)
                content = Gdk.ContentProvider.new_for_value(value)
                return content
        except Exception as e:
            print(f"Popover drag prepare error: {e}")
        return None
    
    def _on_popover_drag_begin(self, source, drag):
        """Set drag icon and close popover when drag begins."""
        try:
            row = source.get_widget()
            title = getattr(row, 'bookmark_title', None) or row.get_title() or "Bookmark"
            
            # Close the popover so it doesn't interfere
            popover = getattr(source, 'popover', None)
            if popover:
                popover.popdown()
            
            # Set drag icon
            icon = Gtk.DragIcon.get_for_drag(drag)
            label = Gtk.Label(label=f"📑 {title[:20]}")
            label.add_css_class("card")
            label.set_margin_top(8)
            label.set_margin_bottom(8)
            label.set_margin_start(8)
            label.set_margin_end(8)
            icon.set_child(label)
        except Exception as e:
            print(f"Popover drag begin error: {e}")
    
    def _on_popover_drag_end(self, source, drag, delete_data):
        """Clean up after popover drag ends."""
        self._dragging_bookmark_url = None
    
    def _on_drop_enter(self, drop_target, x, y):
        """Highlight drop target when drag enters."""
        try:
            widget = drop_target.get_widget()
            widget.add_css_class("suggested-action")
            folder_name = getattr(drop_target, 'folder_name', None)
            sep_data = getattr(drop_target, 'separator_data', None)
            target_index = getattr(drop_target, 'target_index', None)
        except Exception as e:
            pass
        return Gdk.DragAction.MOVE
    
    def _on_drop_accept(self, drop_target, drop):
        """Accept all drops - we handle filtering in drop handler."""
        return True
    
    def _on_drop_leave(self, drop_target):
        """Remove highlight when drag leaves."""
        try:
            widget = drop_target.get_widget()
            widget.remove_css_class("suggested-action")
        except:
            pass
    
    def _on_bookmark_drop_to_folder(self, drop_target, value, x, y):
        """Handle bookmark dropped on folder."""
        try:
            # Get URL from instance variable (more reliable than DnD value)
            url = getattr(self, '_dragging_bookmark_url', None)
            target_folder = getattr(drop_target, 'folder_name', None)
            if not url:
                return False
            
            # Find the bookmark
            for bm in self.bookmarks:
                if bm.get('url') == url:
                    current_folder = bm.get('folder')
                    
                    # Don't do anything if dropping on same folder
                    if current_folder == target_folder:
                        return False
                    
                    # Update folder
                    if target_folder:
                        bm['folder'] = target_folder
                        self.show_toast(f"Moved to {target_folder}")
                    else:
                        if 'folder' in bm:
                            del bm['folder']
                        self.show_toast("Moved to Unfiled")
                    
                    self._save_bookmarks()
                    self._refresh_bookmarks_list()
                    self._refresh_bookmarks_bar()
                    return True
        except Exception as e:
            print(f"Drop error: {e}")
        
        return False
    
    def _on_bookmark_reorder_drop(self, drop_target, value, x, y):
        """Handle bookmark or separator dropped for reordering in toolbar."""
        try:
            url = getattr(self, '_dragging_bookmark_url', None)
            separator = getattr(self, '_dragging_separator', None)
            target_index = getattr(drop_target, 'target_index', 0)
            
            
            if not url and not separator:
                return False
            
            # Find the dragged item
            dragged_bm = None
            
            # Check if we're dragging a separator
            if separator and separator in self.bookmarks:
                dragged_bm = separator
            elif url:
                # Find by URL (regular bookmark)
                for bm in self.bookmarks:
                    if bm.get('url') == url:
                        dragged_bm = bm
                        break
            
            if dragged_bm is None:
                return False
            
            # Check if already at target position (only for unfiled)
            if not dragged_bm.get('folder'):
                unfiled = [bm for bm in self.bookmarks if not bm.get('folder')]
                try:
                    current_idx = unfiled.index(dragged_bm)
                    if current_idx == target_index:
                        return False
                except ValueError:
                    pass
            
            # Remove from current position
            self.bookmarks.remove(dragged_bm)
            
            # Remove folder assignment (moving to unfiled/toolbar)
            if 'folder' in dragged_bm:
                del dragged_bm['folder']
            
            # Find insertion point in main list
            # Count unfiled bookmarks before target_index to find real position
            unfiled_count = 0
            insert_pos = 0
            for i, bm in enumerate(self.bookmarks):
                if not bm.get('folder'):
                    if unfiled_count == target_index:
                        insert_pos = i
                        break
                    unfiled_count += 1
                insert_pos = i + 1
            
            self.bookmarks.insert(insert_pos, dragged_bm)
            
            self._save_bookmarks()
            self._refresh_bookmarks_list()
            self._refresh_bookmarks_bar()
            self.show_toast("Reordered")
            return True
            
        except Exception as e:
            print(f"Reorder drop error: {e}")
        
        return False
    
    def _refresh_bookmarks_bar(self):
        """Rebuild the bookmarks bar with bookmark buttons and folder menus."""
        if not hasattr(self, 'bookmarks_bar'):
            return
        
        # Clear existing buttons
        while True:
            child = self.bookmarks_bar.get_first_child()
            if child is None:
                break
            self.bookmarks_bar.remove(child)
        
        # Add drop target to the bar itself (for dropping to unfiled)
        # Note: We don't add a drop target to the bar itself anymore
        # Each child widget (buttons, separators) has its own drop target
        # This prevents the bar from intercepting drops meant for children
        
        if not self.bookmarks and not self.bookmark_folders:
            # Show hint when empty
            hint = Gtk.Label(label="Bookmarks will appear here (drag here to add)")
            hint.add_css_class("dim-label")
            self.bookmarks_bar.append(hint)
            return
        
        items_added = 0
        max_items = 12
        
        # Add folders as dropdown menus first
        for folder_name in self.bookmark_folders:
            if items_added >= max_items:
                break
            
            folder_bookmarks = [bm for bm in self.bookmarks if bm.get('folder') == folder_name]
            
            # Create menu button for folder
            menu_btn = Gtk.MenuButton()
            menu_btn.add_css_class("flat")
            menu_btn.set_label(f"📁 {folder_name}")
            menu_btn.set_tooltip_text(f"{len(folder_bookmarks)} bookmarks - drop to add")
            
            # Add drop target to folder button
            folder_drop = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.MOVE)
            folder_drop.set_preload(True)
            folder_drop.folder_name = folder_name
            folder_drop.connect("accept", self._on_drop_accept)
            folder_drop.connect("drop", self._on_bookmark_drop_to_folder)
            folder_drop.connect("enter", self._on_drop_enter)
            folder_drop.connect("leave", self._on_drop_leave)
            menu_btn.add_controller(folder_drop)
            
            # Create popover with folder contents
            popover = Gtk.Popover()
            popover.set_autohide(False)  # Disable autohide so drag works
            
            if folder_bookmarks:
                folder_list = Gtk.ListBox()
                folder_list.set_selection_mode(Gtk.SelectionMode.NONE)
                folder_list.add_css_class("boxed-list")
                
                for bm in folder_bookmarks:
                    row = Adw.ActionRow()
                    title = bm.get('title', 'Untitled')
                    if len(title) > 30:
                        title = title[:27] + "..."
                    row.set_title(title)
                    row.set_activatable(True)
                    row.bookmark_url = bm.get('url')
                    row.bookmark_title = bm.get('title', 'Untitled')
                    row.folder_popover = popover
                    row.connect("activated", self._on_folder_bookmark_clicked)
                    
                    # Add drag source to folder popover row
                    drag_source = Gtk.DragSource()
                    drag_source.set_actions(Gdk.DragAction.MOVE)
                    drag_source.connect("prepare", self._on_popover_drag_prepare)
                    drag_source.connect("drag-begin", self._on_popover_drag_begin)
                    drag_source.connect("drag-end", self._on_popover_drag_end)
                    drag_source.popover = popover  # Store reference
                    row.add_controller(drag_source)
                    
                    folder_list.append(row)
                
                popover.set_child(folder_list)
            else:
                empty_label = Gtk.Label(label="Empty folder")
                empty_label.add_css_class("dim-label")
                empty_label.set_margin_top(12)
                empty_label.set_margin_bottom(12)
                empty_label.set_margin_start(12)
                empty_label.set_margin_end(12)
                popover.set_child(empty_label)
            
            menu_btn.set_popover(popover)
            self.bookmarks_bar.append(menu_btn)
            items_added += 1
        
        # Add unfiled bookmarks and separators
        unfiled = [bm for bm in self.bookmarks if not bm.get('folder')]
        bar_index = 0  # Track position for reordering
        for bm in unfiled:
            if items_added >= max_items:
                break
            
            # Check if this is a separator
            if bm.get('type') == 'separator':
                # Use a button with separator appearance for proper hit area
                sep_btn = Gtk.Button()
                sep_btn.add_css_class("flat")
                sep_btn.set_label("│")  # Vertical bar character
                sep_btn.set_sensitive(True)
                sep_btn.set_can_focus(False)
                sep_btn.set_tooltip_text("Separator (drag to reorder)")
                
                # Store separator data for drag
                sep_btn.bookmark_data = bm
                sep_btn.is_separator = True
                sep_btn.bookmark_index = bar_index
                
                # Add drag source
                drag_source = Gtk.DragSource()
                drag_source.set_actions(Gdk.DragAction.MOVE)
                drag_source.connect("prepare", self._on_separator_drag_prepare)
                drag_source.connect("drag-begin", self._on_separator_drag_begin)
                drag_source.connect("drag-end", self._on_drag_end)
                sep_btn.add_controller(drag_source)
                
                # Add drop target for reordering - use unified handler
                drop_target = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.MOVE)
                drop_target.set_preload(True)
                drop_target.separator_data = bm
                drop_target.target_index = bar_index
                drop_target.target_bookmark = bm  # Store for unified handler
                drop_target.connect("accept", self._on_drop_accept)
                drop_target.connect("drop", self._on_unified_drop)
                drop_target.connect("enter", self._on_drop_enter)
                drop_target.connect("leave", self._on_drop_leave)
                sep_btn.add_controller(drop_target)
                
                self.bookmarks_bar.append(sep_btn)
                items_added += 1
                bar_index += 1
                continue
            
            btn = Gtk.Button()
            btn.add_css_class("flat")
            
            # Shorten title for button
            title = bm.get('title', 'Untitled')
            if len(title) > 20:
                title = title[:17] + "..."
            btn.set_label(title)
            btn.set_tooltip_text(bm.get('url', '') + " (drag to reorder)")
            
            btn.bookmark_url = bm.get('url')
            btn.bookmark_title = bm.get('title', 'Untitled')
            btn.bookmark_index = bar_index  # Track position for reordering
            btn.bookmark_data = bm  # Store full data for drop handler
            btn.connect("clicked", self._on_bookmarks_bar_clicked)
            
            # Add drag source to toolbar button
            drag_source = Gtk.DragSource()
            drag_source.set_actions(Gdk.DragAction.MOVE)
            drag_source.connect("prepare", self._on_bar_bookmark_drag_prepare)
            drag_source.connect("drag-begin", self._on_bar_bookmark_drag_begin)
            drag_source.connect("drag-end", self._on_drag_end)
            btn.add_controller(drag_source)
            
            # Add drop target for reordering - use unified handler
            drop_target = Gtk.DropTarget.new(GObject.TYPE_STRING, Gdk.DragAction.MOVE)
            drop_target.set_preload(True)
            drop_target.target_index = bar_index
            drop_target.target_bookmark = bm  # Store bookmark data
            drop_target.connect("accept", self._on_drop_accept)
            drop_target.connect("drop", self._on_unified_drop)
            drop_target.connect("enter", self._on_drop_enter)
            drop_target.connect("leave", self._on_drop_leave)
            btn.add_controller(drop_target)
            
            self.bookmarks_bar.append(btn)
            items_added += 1
            bar_index += 1
        
        # Show "more" indicator if there are more items
        total_items = len(self.bookmark_folders) + len(unfiled)
        if total_items > max_items:
            more_label = Gtk.Label(label=f"+{total_items - max_items} more")
            more_label.add_css_class("dim-label")
            self.bookmarks_bar.append(more_label)
    
    def _on_folder_bookmark_clicked(self, row):
        """Navigate to bookmark clicked in folder popover."""
        url = getattr(row, 'bookmark_url', None)
        popover = getattr(row, 'folder_popover', None)
        if url:
            webview = self._get_current_browser_webview()
            if webview:
                webview.load_uri(url)
        if popover:
            popover.popdown()
    
    def _on_bookmarks_bar_clicked(self, button):
        """Navigate to bookmark clicked in bar."""
        url = getattr(button, 'bookmark_url', None)
        if url:
            webview = self._get_current_browser_webview()
            if webview:
                webview.load_uri(url)
    
    def _on_bookmark_activated(self, row):
        """Navigate to clicked bookmark."""
        url = getattr(row, 'bookmark_url', None)
        if url:
            webview = self._get_current_browser_webview()
            if webview:
                webview.load_uri(url)
            self.bookmarks_popover.popdown()
    
    def _on_bookmark_delete(self, button):
        """Delete a bookmark."""
        url = getattr(button, 'bookmark_url', None)
        if url:
            self.bookmarks = [bm for bm in self.bookmarks if bm.get('url') != url]
            self._save_bookmarks()
            self._refresh_bookmarks_list()
            self._refresh_bookmarks_bar()
            self._update_bookmark_star()
            self.show_toast("Bookmark removed")
    
    def _on_bookmark_new_folder(self, button):
        """Show dialog to create a new folder."""
        self.bookmarks_popover.popdown()
        
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="New Folder",
            body="Enter folder name:"
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("create", "Create")
        dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("create")
        dialog.set_close_response("cancel")
        
        # Folder name entry
        name_entry = Gtk.Entry()
        name_entry.set_placeholder_text("Folder name")
        name_entry.set_margin_top(12)
        name_entry.set_margin_bottom(12)
        name_entry.set_margin_start(12)
        name_entry.set_margin_end(12)
        
        dialog.set_extra_child(name_entry)
        dialog.name_entry = name_entry
        
        dialog.connect("response", self._on_bookmark_new_folder_response)
        dialog.present()
    
    def _on_bookmark_new_folder_response(self, dialog, response):
        """Handle new folder dialog response."""
        if response == "create":
            name = dialog.name_entry.get_text().strip()
            
            if not name:
                self.show_toast("Folder name is required")
                return
            
            if name in self.bookmark_folders:
                self.show_toast("Folder already exists")
                return
            
            self.bookmark_folders.append(name)
            self._save_bookmarks()
            self._refresh_bookmarks_list()
            self.show_toast(f"Folder '{name}' created")
    
    def _on_bookmark_add_separator(self, button):
        """Add a separator to bookmarks."""
        import time
        separator = {
            'type': 'separator',
            'added': int(time.time())
        }
        self.bookmarks.append(separator)
        self._save_bookmarks()
        self._refresh_bookmarks_list()
        self._refresh_bookmarks_bar()
        self.show_toast("Separator added")
    
    def _on_bookmark_add_manual(self, button):
        """Show dialog to manually add a bookmark."""
        self.bookmarks_popover.popdown()
        
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Add Bookmark",
            body="Enter the bookmark details:"
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("add", "Add")
        dialog.set_response_appearance("add", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("add")
        dialog.set_close_response("cancel")
        
        # Create input fields
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_margin_top(12)
        content_box.set_margin_bottom(12)
        content_box.set_margin_start(12)
        content_box.set_margin_end(12)
        
        # Title entry
        title_entry = Gtk.Entry()
        title_entry.set_placeholder_text("Title")
        content_box.append(title_entry)
        
        # URL entry
        url_entry = Gtk.Entry()
        url_entry.set_placeholder_text("https://example.com")
        content_box.append(url_entry)
        
        # Folder dropdown
        folder_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        folder_label = Gtk.Label(label="Folder:")
        folder_box.append(folder_label)
        
        folder_options = ["(None)"] + self.bookmark_folders
        folder_model = Gtk.StringList.new(folder_options)
        folder_dropdown = Gtk.DropDown(model=folder_model)
        folder_dropdown.set_hexpand(True)
        folder_box.append(folder_dropdown)
        content_box.append(folder_box)
        
        dialog.set_extra_child(content_box)
        
        # Store references for response handler
        dialog.title_entry = title_entry
        dialog.url_entry = url_entry
        dialog.folder_dropdown = folder_dropdown
        dialog.folder_options = folder_options
        
        dialog.connect("response", self._on_bookmark_add_response)
        dialog.present()
    
    def _on_bookmark_add_response(self, dialog, response):
        """Handle add bookmark dialog response."""
        if response == "add":
            title = dialog.title_entry.get_text().strip()
            url = dialog.url_entry.get_text().strip()
            
            # Get selected folder
            folder = None
            if hasattr(dialog, 'folder_dropdown'):
                folder_idx = dialog.folder_dropdown.get_selected()
                if folder_idx > 0:  # 0 is "(None)"
                    folder = dialog.folder_options[folder_idx]
            
            if not url:
                self.show_toast("URL is required")
                return
            
            # Add https if missing
            if url and not url.startswith('http://') and not url.startswith('https://'):
                url = 'https://' + url
            
            if not title:
                title = url
            
            # Check for duplicates
            if any(bm.get('url') == url for bm in self.bookmarks):
                self.show_toast("Bookmark already exists")
                return
            
            import time
            bookmark = {
                'url': url,
                'title': title,
                'added': int(time.time())
            }
            if folder:
                bookmark['folder'] = folder
            
            self.bookmarks.append(bookmark)
            self._save_bookmarks()
            self._refresh_bookmarks_list()
            self._refresh_bookmarks_bar()
            self.show_toast("Bookmark added")
    
    def _on_bookmark_edit(self, button):
        """Show dialog to edit a bookmark."""
        url = getattr(button, 'bookmark_url', None)
        title = getattr(button, 'bookmark_title', '')
        folder = getattr(button, 'bookmark_folder', None)
        
        if not url:
            return
        
        self.bookmarks_popover.popdown()
        
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Edit Bookmark",
            body="Modify the bookmark details:"
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("save", "Save")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("save")
        dialog.set_close_response("cancel")
        
        # Create input fields
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content_box.set_margin_top(12)
        content_box.set_margin_bottom(12)
        content_box.set_margin_start(12)
        content_box.set_margin_end(12)
        
        # Title entry (pre-filled)
        title_entry = Gtk.Entry()
        title_entry.set_placeholder_text("Title")
        title_entry.set_text(title)
        content_box.append(title_entry)
        
        # URL entry (pre-filled)
        url_entry = Gtk.Entry()
        url_entry.set_placeholder_text("https://example.com")
        url_entry.set_text(url)
        content_box.append(url_entry)
        
        # Folder dropdown
        folder_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        folder_label = Gtk.Label(label="Folder:")
        folder_box.append(folder_label)
        
        folder_options = ["(None)"] + self.bookmark_folders
        folder_model = Gtk.StringList.new(folder_options)
        folder_dropdown = Gtk.DropDown(model=folder_model)
        folder_dropdown.set_hexpand(True)
        
        # Select current folder
        if folder and folder in folder_options:
            folder_dropdown.set_selected(folder_options.index(folder))
        
        folder_box.append(folder_dropdown)
        content_box.append(folder_box)
        
        dialog.set_extra_child(content_box)
        
        # Store references for response handler
        dialog.title_entry = title_entry
        dialog.url_entry = url_entry
        dialog.original_url = url
        dialog.folder_dropdown = folder_dropdown
        dialog.folder_options = folder_options
        
        dialog.connect("response", self._on_bookmark_edit_response)
        dialog.present()
    
    def _on_bookmark_edit_response(self, dialog, response):
        """Handle edit bookmark dialog response."""
        if response == "save":
            new_title = dialog.title_entry.get_text().strip()
            new_url = dialog.url_entry.get_text().strip()
            original_url = dialog.original_url
            
            # Get selected folder
            new_folder = None
            if hasattr(dialog, 'folder_dropdown'):
                folder_idx = dialog.folder_dropdown.get_selected()
                if folder_idx > 0:  # 0 is "(None)"
                    new_folder = dialog.folder_options[folder_idx]
            
            if not new_url:
                self.show_toast("URL is required")
                return
            
            # Add https if missing
            if new_url and not new_url.startswith('http://') and not new_url.startswith('https://'):
                new_url = 'https://' + new_url
            
            if not new_title:
                new_title = new_url
            
            # Check for duplicates (if URL changed)
            if new_url != original_url and any(bm.get('url') == new_url for bm in self.bookmarks):
                self.show_toast("Bookmark with that URL already exists")
                return
            
            # Update the bookmark
            for bm in self.bookmarks:
                if bm.get('url') == original_url:
                    bm['url'] = new_url
                    bm['title'] = new_title
                    if new_folder:
                        bm['folder'] = new_folder
                    elif 'folder' in bm:
                        del bm['folder']  # Remove folder if set to (None)
                    break
            
            self._save_bookmarks()
            self._refresh_bookmarks_list()
            self._refresh_bookmarks_bar()
            self._update_bookmark_star()
            self.show_toast("Bookmark updated")
    
    def _on_bookmarks_import(self, button):
        """Import bookmarks from HTML file (Firefox/Chrome format)."""
        self.bookmarks_popover.popdown()
        
        dialog = Gtk.FileDialog()
        dialog.set_title("Import Bookmarks")
        
        # Filter for HTML files
        filter_html = Gtk.FileFilter()
        filter_html.set_name("HTML Bookmark Files")
        filter_html.add_mime_type("text/html")
        filter_html.add_pattern("*.html")
        filter_html.add_pattern("*.htm")
        
        filter_all = Gtk.FileFilter()
        filter_all.set_name("All Files")
        filter_all.add_pattern("*")
        
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_html)
        filters.append(filter_all)
        dialog.set_filters(filters)
        dialog.set_default_filter(filter_html)
        
        dialog.open(self, None, self._on_bookmarks_import_response)
    
    def _on_bookmarks_import_response(self, dialog, result):
        """Handle import file selection."""
        import re
        
        try:
            file = dialog.open_finish(result)
            if not file:
                return
            
            filepath = file.get_path()
            
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Parse Netscape bookmark format: <A HREF="url"...>Title</A>
            pattern = r'<A\s+HREF="([^"]+)"[^>]*>([^<]+)</A>'
            matches = re.findall(pattern, content, re.IGNORECASE)
            
            if not matches:
                self.show_toast("No bookmarks found in file")
                return
            
            # Get existing URLs to avoid duplicates
            existing_urls = {bm.get('url') for bm in self.bookmarks}
            
            import time
            now = int(time.time())
            imported = 0
            for url, title in matches:
                if url not in existing_urls:
                    self.bookmarks.append({
                        'url': url,
                        'title': title.strip(),
                        'added': now
                    })
                    existing_urls.add(url)
                    imported += 1
            
            if imported > 0:
                self._save_bookmarks()
                self._refresh_bookmarks_list()
                self._refresh_bookmarks_bar()
                self.show_toast(f"Imported {imported} bookmarks")
            else:
                self.show_toast("All bookmarks already exist")
                
        except Exception as e:
            print(f"Import error: {e}")
            self.show_toast("Failed to import bookmarks")
    
    def _on_bookmarks_export(self, button):
        """Export bookmarks to HTML file (Firefox/Chrome compatible)."""
        self.bookmarks_popover.popdown()
        
        if not self.bookmarks:
            self.show_toast("No bookmarks to export")
            return
        
        dialog = Gtk.FileDialog()
        dialog.set_title("Export Bookmarks")
        dialog.set_initial_name("bookmarks.html")
        
        dialog.save(self, None, self._on_bookmarks_export_response)
    
    def _on_bookmarks_export_response(self, dialog, result):
        """Handle export file selection."""
        from html import escape
        from datetime import datetime
        
        try:
            file = dialog.save_finish(result)
            if not file:
                return
            
            filepath = file.get_path()
            
            # Ensure .html extension
            if not filepath.lower().endswith('.html') and not filepath.lower().endswith('.htm'):
                filepath += '.html'
            
            # Generate Netscape bookmark format (compatible with all browsers)
            timestamp = int(datetime.now().timestamp())
            
            html = '''<!DOCTYPE NETSCAPE-Bookmark-file-1>
<!-- This is an automatically generated file.
     It will be read and overwritten.
     DO NOT EDIT! -->
<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
<TITLE>Bookmarks</TITLE>
<H1>Bookmarks</H1>
<DL><p>
    <DT><H3 ADD_DATE="{timestamp}" LAST_MODIFIED="{timestamp}">Tux Assistant Bookmarks</H3>
    <DL><p>
'''.format(timestamp=timestamp)
            
            for bm in self.bookmarks:
                title = escape(bm.get('title', 'Untitled'))
                url = escape(bm.get('url', ''))
                html += f'        <DT><A HREF="{url}" ADD_DATE="{timestamp}">{title}</A>\n'
            
            html += '''    </DL><p>
</DL><p>
'''
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html)
            
            self.show_toast(f"Exported {len(self.bookmarks)} bookmarks")
            
        except Exception as e:
            print(f"Export error: {e}")
            self.show_toast("Failed to export bookmarks")
    
    def _on_bookmarks_clear_all(self, button):
        """Clear all bookmarks with confirmation."""
        self.bookmarks_popover.popdown()
        
        if not self.bookmarks:
            self.show_toast("No bookmarks to clear")
            return
        
        # Create confirmation dialog
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Clear All Bookmarks?",
            body=f"This will delete all {len(self.bookmarks)} bookmarks. This cannot be undone."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("clear", "Clear All")
        dialog.set_response_appearance("clear", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        dialog.connect("response", self._on_bookmarks_clear_response)
        dialog.present()
    
    def _on_bookmarks_clear_response(self, dialog, response):
        """Handle clear all confirmation response."""
        if response == "clear":
            count = len(self.bookmarks)
            folder_count = len(self.bookmark_folders)
            self.bookmarks = []
            self.bookmark_folders = []
            self._save_bookmarks()
            self._refresh_bookmarks_list()
            self._refresh_bookmarks_bar()
            self._update_bookmark_star()
            msg = f"Cleared {count} bookmarks"
            if folder_count:
                msg += f" and {folder_count} folders"
            self.show_toast(msg)
    
    def _get_all_tags(self):
        """Get all unique tags from all bookmarks."""
        tags = set()
        for bm in self.bookmarks:
            for tag in bm.get('tags', []):
                tags.add(tag)
        return sorted(tags)
    
    def _create_tag_chip(self, tag, removable=False, on_remove=None, on_click=None):
        """Create a tag chip widget."""
        chip = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        chip.add_css_class("card")
        chip.set_margin_top(2)
        chip.set_margin_bottom(2)
        
        if on_click:
            # Make it a button
            btn = Gtk.Button()
            btn.add_css_class("flat")
            btn.add_css_class("pill")
            btn.set_child(chip)
            btn.tag_name = tag
            btn.connect("clicked", on_click)
            container = btn
        else:
            container = chip
        
        label = Gtk.Label(label=tag)
        label.set_margin_start(8)
        label.set_margin_end(4 if removable else 8)
        label.set_margin_top(2)
        label.set_margin_bottom(2)
        chip.append(label)
        
        if removable and on_remove:
            remove_btn = Gtk.Button.new_from_icon_name("tux-window-close-symbolic")
            remove_btn.add_css_class("flat")
            remove_btn.add_css_class("circular")
            remove_btn.set_valign(Gtk.Align.CENTER)
            remove_btn.tag_name = tag
            remove_btn.connect("clicked", on_remove)
            chip.append(remove_btn)
        
        return container
    
    def _show_bookmark_manager(self, button=None):
        """Show the full bookmark manager window."""
        if hasattr(self, 'bookmarks_popover'):
            self.bookmarks_popover.popdown()
        
        # Track current tag filter
        self.bm_tag_filter = None
        
        # Create the manager window
        self.bm_window = Adw.Window()
        self.bm_window.set_title("Bookmark Manager")
        self.bm_window.set_default_size(650, 550)
        self.bm_window.set_transient_for(self)
        self.bm_window.set_modal(False)
        
        # Main layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.bm_window.set_content(main_box)
        
        # Header bar with search and tag filter
        header = Adw.HeaderBar()
        main_box.append(header)
        
        # Search entry 
        self.bm_search = Gtk.SearchEntry()
        self.bm_search.set_placeholder_text("Search bookmarks...")
        self.bm_search.set_hexpand(True)
        self.bm_search.connect("search-changed", self._on_bm_search_changed)
        header.set_title_widget(self.bm_search)
        
        # Tag filter dropdown in header
        all_tags = self._get_all_tags()
        tag_options = ["All Tags"] + all_tags
        tag_model = Gtk.StringList.new(tag_options)
        self.bm_tag_dropdown = Gtk.DropDown(model=tag_model)
        self.bm_tag_dropdown.set_tooltip_text("Filter by tag")
        self.bm_tag_dropdown.connect("notify::selected", self._on_bm_tag_filter_changed)
        header.pack_start(self.bm_tag_dropdown)
        
        # Tag management button in header
        tags_btn = Gtk.Button.new_from_icon_name("tag-symbolic")
        tags_btn.set_tooltip_text("Manage tags")
        tags_btn.connect("clicked", self._show_tag_manager)
        header.pack_end(tags_btn)
        
        # Scrolled window for bookmark list
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        main_box.append(scroll)
        
        # ListBox with multi-select
        self.bm_list = Gtk.ListBox()
        self.bm_list.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.bm_list.add_css_class("boxed-list")
        self.bm_list.set_margin_start(12)
        self.bm_list.set_margin_end(12)
        self.bm_list.set_margin_top(12)
        self.bm_list.set_margin_bottom(12)
        scroll.set_child(self.bm_list)
        
        # Bottom toolbar
        toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        toolbar.set_margin_start(12)
        toolbar.set_margin_end(12)
        toolbar.set_margin_bottom(12)
        toolbar.set_margin_top(8)
        main_box.append(toolbar)
        
        # Delete Selected button
        delete_btn = Gtk.Button(label="Delete Selected")
        delete_btn.set_icon_name("tux-edit-delete-symbolic")
        delete_btn.add_css_class("destructive-action")
        delete_btn.connect("clicked", self._on_bm_delete_selected)
        toolbar.append(delete_btn)
        
        # Move to Folder dropdown
        move_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        toolbar.append(move_box)
        
        move_label = Gtk.Label(label="Move to:")
        move_box.append(move_label)
        
        # Build folder dropdown
        folder_options = ["(Unfiled)"] + self.bookmark_folders
        folder_model = Gtk.StringList.new(folder_options)
        self.bm_folder_dropdown = Gtk.DropDown(model=folder_model)
        self.bm_folder_dropdown.set_tooltip_text("Move selected to folder")
        self.bm_folder_dropdown.connect("notify::selected", self._on_bm_move_to_folder)
        move_box.append(self.bm_folder_dropdown)
        
        # Spacer
        spacer = Gtk.Box()
        spacer.set_hexpand(True)
        toolbar.append(spacer)
        
        # New Folder button
        new_folder_btn = Gtk.Button(label="New Folder")
        new_folder_btn.set_icon_name("tux-folder-new-symbolic")
        new_folder_btn.connect("clicked", self._on_bm_new_folder)
        toolbar.append(new_folder_btn)
        
        # Export button
        export_btn = Gtk.Button(label="Export")
        export_btn.set_icon_name("tux-document-save-symbolic")
        export_btn.connect("clicked", self._on_bookmarks_export)
        toolbar.append(export_btn)
        
        # Keyboard shortcuts
        key_controller = Gtk.EventControllerKey()
        key_controller.connect("key-pressed", self._on_bm_key_pressed)
        self.bm_window.add_controller(key_controller)
        
        # Populate the list
        self._refresh_bm_list()
        
        # Show the window
        self.bm_window.present()
    
    def _refresh_bm_list(self, search_filter=""):
        """Refresh the bookmark manager list."""
        # Clear existing
        while True:
            child = self.bm_list.get_first_child()
            if child is None:
                break
            self.bm_list.remove(child)
        
        search_filter = search_filter.lower().strip()
        tag_filter = getattr(self, 'bm_tag_filter', None)
        
        # Filter bookmarks
        filtered = []
        for bm in self.bookmarks:
            if bm.get('type') == 'separator':
                continue
            
            # Tag filter
            if tag_filter:
                if tag_filter not in bm.get('tags', []):
                    continue
            
            # Search filter
            if search_filter:
                if not (search_filter in bm.get('title', '').lower() or 
                        search_filter in bm.get('url', '').lower() or
                        any(search_filter in tag.lower() for tag in bm.get('tags', []))):
                    continue
            
            filtered.append(bm)
        
        if search_filter or tag_filter:
            # When filtering, show flat list
            for bm in filtered:
                row = self._create_bm_row(bm)
                self.bm_list.append(row)
        else:
            # Show organized by folder
            unfiled = [bm for bm in filtered if not bm.get('folder')]
            
            # Add folders
            for folder_name in self.bookmark_folders:
                folder_bookmarks = [bm for bm in filtered if bm.get('folder') == folder_name]
                
                # Folder header
                folder_row = Adw.ActionRow()
                folder_row.set_title(f"📁 {folder_name}")
                folder_row.set_subtitle(f"{len(folder_bookmarks)} bookmark{'s' if len(folder_bookmarks) != 1 else ''}")
                folder_row.add_css_class("dim-label")
                folder_row.set_activatable(False)
                folder_row.set_selectable(False)
                self.bm_list.append(folder_row)
                
                # Bookmarks in this folder
                for bm in folder_bookmarks:
                    row = self._create_bm_row(bm, indent=True)
                    self.bm_list.append(row)
            
            # Unfiled section
            if self.bookmark_folders and unfiled:
                unfiled_header = Adw.ActionRow()
                unfiled_header.set_title("Unfiled")
                unfiled_header.set_subtitle(f"{len(unfiled)} bookmark{'s' if len(unfiled) != 1 else ''}")
                unfiled_header.add_css_class("dim-label")
                unfiled_header.set_activatable(False)
                unfiled_header.set_selectable(False)
                self.bm_list.append(unfiled_header)
            
            # Add unfiled bookmarks
            for bm in unfiled:
                row = self._create_bm_row(bm)
                self.bm_list.append(row)
        
        # Show empty message if needed
        if not self.bm_list.get_first_child():
            empty = Adw.ActionRow()
            if tag_filter:
                empty.set_title(f"No bookmarks with tag '{tag_filter}'")
            elif search_filter:
                empty.set_title("No matches found")
            else:
                empty.set_title("No bookmarks")
            empty.add_css_class("dim-label")
            empty.set_activatable(False)
            empty.set_selectable(False)
            self.bm_list.append(empty)
    
    def _create_bm_row(self, bm, indent=False):
        """Create a row for the bookmark manager list."""
        row = Adw.ActionRow()
        row.set_title(bm.get('title', 'Untitled'))
        row.set_subtitle(bm.get('url', ''))
        row.set_tooltip_text(bm.get('url', ''))
        
        # Store reference to bookmark data
        row.bookmark_data = bm
        
        # Favicon
        favicon = self._get_bookmark_favicon(bm.get('url', ''))
        row.add_prefix(favicon)
        
        # Indent if in folder
        if indent:
            row.set_margin_start(24)
        
        # Tags display - show as chips
        tags = bm.get('tags', [])
        if tags:
            tags_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            tags_box.set_margin_end(8)
            for tag in tags[:3]:  # Show max 3 tags inline
                tag_label = Gtk.Label(label=tag)
                tag_label.add_css_class("dim-label")
                tag_label.set_margin_start(4)
                tag_label.set_margin_end(4)
                tags_box.append(tag_label)
            if len(tags) > 3:
                more_label = Gtk.Label(label=f"+{len(tags) - 3}")
                more_label.add_css_class("dim-label")
                tags_box.append(more_label)
            row.add_suffix(tags_box)
        
        # Folder indicator
        if bm.get('folder'):
            folder_label = Gtk.Label(label=f"📁 {bm.get('folder')}")
            folder_label.add_css_class("dim-label")
            folder_label.set_margin_end(8)
            row.add_suffix(folder_label)
        
        # Edit button
        edit_btn = Gtk.Button.new_from_icon_name("tux-document-edit-symbolic")
        edit_btn.set_valign(Gtk.Align.CENTER)
        edit_btn.add_css_class("flat")
        edit_btn.set_tooltip_text("Edit bookmark")
        edit_btn.bookmark_url = bm.get('url')
        edit_btn.bookmark_title = bm.get('title', '')
        edit_btn.bookmark_folder = bm.get('folder')
        edit_btn.bookmark_tags = bm.get('tags', [])
        edit_btn.connect("clicked", self._on_bm_edit_clicked)
        row.add_suffix(edit_btn)
        
        return row
    
    def _on_bm_tag_filter_changed(self, dropdown, param):
        """Handle tag filter dropdown change."""
        selected = dropdown.get_selected()
        if selected == 0:
            self.bm_tag_filter = None
        else:
            all_tags = self._get_all_tags()
            if selected - 1 < len(all_tags):
                self.bm_tag_filter = all_tags[selected - 1]
            else:
                self.bm_tag_filter = None
        
        self._refresh_bm_list(self.bm_search.get_text() if hasattr(self, 'bm_search') else "")
    
    def _on_bm_search_changed(self, entry):
        """Handle search in bookmark manager."""
        self._refresh_bm_list(entry.get_text())
    
    def _on_bm_delete_selected(self, button):
        """Delete selected bookmarks."""
        selected_rows = self.bm_list.get_selected_rows()
        if not selected_rows:
            self.show_toast("No bookmarks selected")
            return
        
        # Get URLs of selected bookmarks
        urls_to_delete = []
        for row in selected_rows:
            if hasattr(row, 'bookmark_data'):
                url = row.bookmark_data.get('url')
                if url:
                    urls_to_delete.append(url)
        
        if not urls_to_delete:
            self.show_toast("No bookmarks selected")
            return
        
        # Delete them
        self.bookmarks = [bm for bm in self.bookmarks if bm.get('url') not in urls_to_delete]
        self._save_bookmarks()
        self._refresh_bm_list(self.bm_search.get_text() if hasattr(self, 'bm_search') else "")
        self._refresh_bookmarks_list()
        self._refresh_bookmarks_bar()
        self._update_bookmark_star()
        self.show_toast(f"Deleted {len(urls_to_delete)} bookmark{'s' if len(urls_to_delete) != 1 else ''}")
    
    def _on_bm_move_to_folder(self, dropdown, param):
        """Move selected bookmarks to folder."""
        selected_rows = self.bm_list.get_selected_rows()
        if not selected_rows:
            return
        
        selected_index = dropdown.get_selected()
        if selected_index == 0:
            target_folder = None  # Unfiled
        else:
            target_folder = self.bookmark_folders[selected_index - 1]
        
        moved_count = 0
        for row in selected_rows:
            if hasattr(row, 'bookmark_data'):
                bm = row.bookmark_data
                if bm.get('type') != 'separator':
                    # Find and update the bookmark in main list
                    for bookmark in self.bookmarks:
                        if bookmark.get('url') == bm.get('url'):
                            if target_folder:
                                bookmark['folder'] = target_folder
                            elif 'folder' in bookmark:
                                del bookmark['folder']
                            moved_count += 1
                            break
        
        if moved_count > 0:
            self._save_bookmarks()
            self._refresh_bm_list(self.bm_search.get_text() if hasattr(self, 'bm_search') else "")
            self._refresh_bookmarks_list()
            self._refresh_bookmarks_bar()
            folder_name = target_folder if target_folder else "Unfiled"
            self.show_toast(f"Moved {moved_count} bookmark{'s' if moved_count != 1 else ''} to {folder_name}")
        
        # Reset dropdown to first item
        dropdown.set_selected(0)
    
    def _on_bm_new_folder(self, button):
        """Create a new folder from bookmark manager."""
        dialog = Adw.MessageDialog(
            transient_for=self.bm_window,
            heading="New Folder",
            body="Enter folder name:"
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("create", "Create")
        dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("create")
        dialog.set_close_response("cancel")
        
        # Add entry
        entry = Gtk.Entry()
        entry.set_placeholder_text("Folder name")
        entry.set_margin_start(24)
        entry.set_margin_end(24)
        dialog.set_extra_child(entry)
        
        def on_response(d, response):
            if response == "create":
                name = entry.get_text().strip()
                if not name:
                    self.show_toast("Folder name cannot be empty")
                    return
                if name in self.bookmark_folders:
                    self.show_toast(f"Folder '{name}' already exists")
                    return
                
                self.bookmark_folders.append(name)
                self._save_bookmarks()
                self._refresh_bm_list()
                self._refresh_bookmarks_list()
                
                # Update the folder dropdown in manager
                folder_options = ["(Unfiled)"] + self.bookmark_folders
                folder_model = Gtk.StringList.new(folder_options)
                self.bm_folder_dropdown.set_model(folder_model)
                
                self.show_toast(f"Created folder '{name}'")
        
        dialog.connect("response", on_response)
        dialog.present()
    
    def _on_bm_edit_clicked(self, button):
        """Edit bookmark from manager window."""
        url = getattr(button, 'bookmark_url', None)
        title = getattr(button, 'bookmark_title', '')
        folder = getattr(button, 'bookmark_folder', None)
        current_tags = list(getattr(button, 'bookmark_tags', []))
        
        if not url:
            return
        
        dialog = Adw.MessageDialog(
            transient_for=self.bm_window,
            heading="Edit Bookmark",
            body="Modify the bookmark details:"
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("save", "Save")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("save")
        dialog.set_close_response("cancel")
        
        # Form
        form_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        form_box.set_margin_start(24)
        form_box.set_margin_end(24)
        
        title_entry = Gtk.Entry()
        title_entry.set_text(title)
        title_entry.set_placeholder_text("Title")
        form_box.append(title_entry)
        
        url_entry = Gtk.Entry()
        url_entry.set_text(url)
        url_entry.set_placeholder_text("URL")
        form_box.append(url_entry)
        
        # Folder dropdown
        folder_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        folder_label = Gtk.Label(label="Folder:")
        folder_box.append(folder_label)
        
        folder_options = ["(None)"] + self.bookmark_folders
        folder_model = Gtk.StringList.new(folder_options)
        folder_dropdown = Gtk.DropDown(model=folder_model)
        
        # Set current folder
        if folder and folder in self.bookmark_folders:
            folder_dropdown.set_selected(self.bookmark_folders.index(folder) + 1)
        
        folder_box.append(folder_dropdown)
        form_box.append(folder_box)
        
        # Tags section
        tags_section = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        tags_section.set_margin_top(8)
        form_box.append(tags_section)
        
        tags_label = Gtk.Label(label="Tags:")
        tags_label.set_xalign(0)
        tags_section.append(tags_label)
        
        # Current tags display
        tags_display = Gtk.FlowBox()
        tags_display.set_selection_mode(Gtk.SelectionMode.NONE)
        tags_display.set_homogeneous(False)
        tags_display.set_max_children_per_line(10)
        tags_section.append(tags_display)
        
        # Store tags in a mutable list for the dialog
        edit_tags = list(current_tags)
        
        def refresh_tags_display():
            # Clear
            while True:
                child = tags_display.get_first_child()
                if child is None:
                    break
                tags_display.remove(child)
            # Add current tags
            for tag in edit_tags:
                chip_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
                chip_label = Gtk.Label(label=tag)
                chip_label.set_margin_start(6)
                chip_label.set_margin_end(2)
                chip_box.append(chip_label)
                
                remove_btn = Gtk.Button.new_from_icon_name("tux-window-close-symbolic")
                remove_btn.add_css_class("flat")
                remove_btn.add_css_class("circular")
                remove_btn.set_valign(Gtk.Align.CENTER)
                remove_btn.tag_name = tag
                def on_remove(btn):
                    t = btn.tag_name
                    if t in edit_tags:
                        edit_tags.remove(t)
                        refresh_tags_display()
                remove_btn.connect("clicked", on_remove)
                chip_box.append(remove_btn)
                
                chip_box.add_css_class("card")
                tags_display.append(chip_box)
            
            if not edit_tags:
                no_tags = Gtk.Label(label="No tags")
                no_tags.add_css_class("dim-label")
                tags_display.append(no_tags)
        
        refresh_tags_display()
        
        # Add tag entry with autocomplete suggestions
        add_tag_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        tags_section.append(add_tag_box)
        
        tag_entry = Gtk.Entry()
        tag_entry.set_placeholder_text("Add tag (Enter to add)")
        tag_entry.set_hexpand(True)
        add_tag_box.append(tag_entry)
        
        add_tag_btn = Gtk.Button.new_from_icon_name("tux-list-add-symbolic")
        add_tag_btn.set_tooltip_text("Add tag")
        add_tag_box.append(add_tag_btn)
        
        def add_tag_from_entry():
            new_tag = tag_entry.get_text().strip().lower()
            if new_tag and new_tag not in edit_tags:
                edit_tags.append(new_tag)
                refresh_tags_display()
                tag_entry.set_text("")
        
        add_tag_btn.connect("clicked", lambda b: add_tag_from_entry())
        tag_entry.connect("activate", lambda e: add_tag_from_entry())
        
        # Suggestions from existing tags
        all_tags = self._get_all_tags()
        if all_tags:
            suggest_label = Gtk.Label(label="Suggestions:")
            suggest_label.set_xalign(0)
            suggest_label.add_css_class("dim-label")
            suggest_label.set_margin_top(4)
            tags_section.append(suggest_label)
            
            suggest_box = Gtk.FlowBox()
            suggest_box.set_selection_mode(Gtk.SelectionMode.NONE)
            suggest_box.set_max_children_per_line(10)
            tags_section.append(suggest_box)
            
            for tag in all_tags[:10]:  # Show max 10 suggestions
                if tag not in edit_tags:
                    suggest_btn = Gtk.Button(label=tag)
                    suggest_btn.add_css_class("flat")
                    suggest_btn.add_css_class("pill")
                    suggest_btn.tag_name = tag
                    def on_suggest(btn):
                        t = btn.tag_name
                        if t not in edit_tags:
                            edit_tags.append(t)
                            refresh_tags_display()
                            # Hide used suggestion
                            btn.set_visible(False)
                    suggest_btn.connect("clicked", on_suggest)
                    suggest_box.append(suggest_btn)
        
        dialog.set_extra_child(form_box)
        
        original_url = url
        
        def on_response(d, response):
            if response == "save":
                new_title = title_entry.get_text().strip()
                new_url = url_entry.get_text().strip()
                
                if not new_url:
                    self.show_toast("URL cannot be empty")
                    return
                
                folder_idx = folder_dropdown.get_selected()
                new_folder = self.bookmark_folders[folder_idx - 1] if folder_idx > 0 else None
                
                # Check for duplicate URL
                if new_url != original_url and any(bm.get('url') == new_url for bm in self.bookmarks):
                    self.show_toast("A bookmark with that URL already exists")
                    return
                
                # Update the bookmark
                for bm in self.bookmarks:
                    if bm.get('url') == original_url:
                        bm['url'] = new_url
                        bm['title'] = new_title if new_title else new_url
                        if new_folder:
                            bm['folder'] = new_folder
                        elif 'folder' in bm:
                            del bm['folder']
                        # Update tags
                        if edit_tags:
                            bm['tags'] = edit_tags
                        elif 'tags' in bm:
                            del bm['tags']
                        break
                
                self._save_bookmarks()
                self._refresh_bm_list(self.bm_search.get_text() if hasattr(self, 'bm_search') else "")
                self._refresh_bookmarks_list()
                self._refresh_bookmarks_bar()
                self._update_bookmark_star()
                
                # Update tag filter dropdown
                self._update_bm_tag_dropdown()
                
                self.show_toast("Bookmark updated")
        
        dialog.connect("response", on_response)
        dialog.present()
    
    def _update_bm_tag_dropdown(self):
        """Update the tag filter dropdown in bookmark manager."""
        if hasattr(self, 'bm_tag_dropdown'):
            all_tags = self._get_all_tags()
            tag_options = ["All Tags"] + all_tags
            tag_model = Gtk.StringList.new(tag_options)
            self.bm_tag_dropdown.set_model(tag_model)
    
    def _show_tag_manager(self, button):
        """Show tag management dialog."""
        all_tags = self._get_all_tags()
        
        dialog = Adw.MessageDialog(
            transient_for=self.bm_window,
            heading="Manage Tags",
            body=f"{len(all_tags)} tag{'s' if len(all_tags) != 1 else ''} in use"
        )
        dialog.add_response("close", "Close")
        dialog.set_default_response("close")
        dialog.set_close_response("close")
        
        if not all_tags:
            dialog.set_body("No tags in use yet. Add tags when editing bookmarks.")
            dialog.present()
            return
        
        # List of tags with counts and actions
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        content.set_margin_start(24)
        content.set_margin_end(24)
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_max_content_height(300)
        scroll.set_propagate_natural_height(True)
        content.append(scroll)
        
        tag_list = Gtk.ListBox()
        tag_list.add_css_class("boxed-list")
        tag_list.set_selection_mode(Gtk.SelectionMode.NONE)
        scroll.set_child(tag_list)
        
        for tag in all_tags:
            # Count bookmarks with this tag
            count = sum(1 for bm in self.bookmarks if tag in bm.get('tags', []))
            
            row = Adw.ActionRow()
            row.set_title(tag)
            row.set_subtitle(f"{count} bookmark{'s' if count != 1 else ''}")
            
            # Rename button
            rename_btn = Gtk.Button.new_from_icon_name("tux-document-edit-symbolic")
            rename_btn.add_css_class("flat")
            rename_btn.set_valign(Gtk.Align.CENTER)
            rename_btn.set_tooltip_text("Rename tag")
            rename_btn.tag_name = tag
            rename_btn.connect("clicked", lambda b: self._rename_tag(b.tag_name, dialog))
            row.add_suffix(rename_btn)
            
            # Delete button
            delete_btn = Gtk.Button.new_from_icon_name("tux-edit-delete-symbolic")
            delete_btn.add_css_class("flat")
            delete_btn.set_valign(Gtk.Align.CENTER)
            delete_btn.set_tooltip_text("Delete tag from all bookmarks")
            delete_btn.tag_name = tag
            delete_btn.connect("clicked", lambda b: self._delete_tag(b.tag_name, dialog))
            row.add_suffix(delete_btn)
            
            tag_list.append(row)
        
        dialog.set_extra_child(content)
        dialog.present()
    
    def _rename_tag(self, old_name, parent_dialog):
        """Rename a tag across all bookmarks."""
        dialog = Adw.MessageDialog(
            transient_for=self.bm_window,
            heading=f"Rename Tag '{old_name}'",
            body="Enter new name:"
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("rename", "Rename")
        dialog.set_response_appearance("rename", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("rename")
        dialog.set_close_response("cancel")
        
        entry = Gtk.Entry()
        entry.set_text(old_name)
        entry.set_margin_start(24)
        entry.set_margin_end(24)
        dialog.set_extra_child(entry)
        
        def on_response(d, response):
            if response == "rename":
                new_name = entry.get_text().strip().lower()
                if not new_name:
                    self.show_toast("Tag name cannot be empty")
                    return
                if new_name == old_name:
                    return
                
                # Update all bookmarks
                count = 0
                for bm in self.bookmarks:
                    tags = bm.get('tags', [])
                    if old_name in tags:
                        tags.remove(old_name)
                        if new_name not in tags:
                            tags.append(new_name)
                        bm['tags'] = tags
                        count += 1
                
                self._save_bookmarks()
                self._refresh_bm_list(self.bm_search.get_text() if hasattr(self, 'bm_search') else "")
                self._update_bm_tag_dropdown()
                self.show_toast(f"Renamed tag in {count} bookmark{'s' if count != 1 else ''}")
                parent_dialog.close()
        
        dialog.connect("response", on_response)
        dialog.present()
    
    def _delete_tag(self, tag_name, parent_dialog):
        """Delete a tag from all bookmarks."""
        count = sum(1 for bm in self.bookmarks if tag_name in bm.get('tags', []))
        
        dialog = Adw.MessageDialog(
            transient_for=self.bm_window,
            heading=f"Delete Tag '{tag_name}'?",
            body=f"This will remove the tag from {count} bookmark{'s' if count != 1 else ''}."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.set_close_response("cancel")
        
        def on_response(d, response):
            if response == "delete":
                for bm in self.bookmarks:
                    tags = bm.get('tags', [])
                    if tag_name in tags:
                        tags.remove(tag_name)
                        if tags:
                            bm['tags'] = tags
                        elif 'tags' in bm:
                            del bm['tags']
                
                self._save_bookmarks()
                self._refresh_bm_list(self.bm_search.get_text() if hasattr(self, 'bm_search') else "")
                self._update_bm_tag_dropdown()
                self.show_toast(f"Deleted tag '{tag_name}'")
                parent_dialog.close()
        
        dialog.connect("response", on_response)
        dialog.present()
    
    def _on_bm_key_pressed(self, controller, keyval, keycode, state):
        """Handle keyboard shortcuts in bookmark manager."""
        # Delete key - delete selected
        if keyval == Gdk.KEY_Delete:
            self._on_bm_delete_selected(None)
            return True
        
        # Escape - close window
        if keyval == Gdk.KEY_Escape:
            self.bm_window.close()
            return True
        
        # Ctrl+A - select all
        if keyval == Gdk.KEY_a and state & Gdk.ModifierType.CONTROL_MASK:
            self.bm_list.select_all()
            return True
        
        # Ctrl+F - focus search
        if keyval == Gdk.KEY_f and state & Gdk.ModifierType.CONTROL_MASK:
            self.bm_search.grab_focus()
            return True
        
        return False
    
    def _on_browser_decide_policy(self, webview, decision, decision_type):
        """Handle policy decisions for downloads, HTTPS upgrade, and blocking."""
        
        # Handle navigation actions (links, typed URLs)
        if decision_type == WebKit.PolicyDecisionType.NAVIGATION_ACTION:
            nav_action = decision.get_navigation_action()
            request = nav_action.get_request()
            uri = request.get_uri()
            
            if uri:
                # Check for blocked domains (ads/trackers)
                if self._should_block_uri(uri):
                    decision.ignore()
                    return True
                
                # Upgrade HTTP to HTTPS
                if self.force_https and uri.startswith('http://'):
                    # Skip localhost and local network
                    if not any(x in uri for x in ['localhost', '127.0.0.1', '192.168.', '10.', '172.16.']):
                        https_uri = 'https://' + uri[7:]
                        decision.ignore()
                        webview.load_uri(https_uri)
                        return True
        
        # Handle response decisions (downloads, subresources)
        if decision_type == WebKit.PolicyDecisionType.RESPONSE:
            response = decision.get_response()
            if response:
                uri = response.get_uri()
                
                # Block ad/tracker resources
                if uri and self._should_block_uri(uri):
                    decision.ignore()
                    return True
                
                # Check if this should be downloaded
                if decision.is_mime_type_supported() == False:
                    decision.download()
                    return True
        
        decision.use()
        return False
    
    def _should_block_uri(self, uri):
        """Check if a URI should be blocked based on privacy settings."""
        if not uri:
            return False
        
        try:
            # Extract domain from URI
            from urllib.parse import urlparse
            parsed = urlparse(uri)
            domain = parsed.netloc.lower()
            
            # Remove www. prefix for matching
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Check against blocklists
            if self.block_ads:
                for ad_domain in self.AD_DOMAINS:
                    if ad_domain in domain or domain.endswith('.' + ad_domain):
                        return True
            
            if self.block_trackers:
                for tracker_domain in self.TRACKER_DOMAINS:
                    if tracker_domain in domain or domain.endswith('.' + tracker_domain):
                        return True
        except:
            pass
        
        return False
    
    def _on_https_toggled(self, switch, pspec):
        """Handle HTTPS toggle."""
        self.force_https = switch.get_active()
        self._save_browser_settings(force_https=self.force_https)
    
    def _on_ads_toggled(self, switch, pspec):
        """Handle ads blocking toggle."""
        self.block_ads = switch.get_active()
        self._save_browser_settings(block_ads=self.block_ads)
    
    def _on_trackers_toggled(self, switch, pspec):
        """Handle tracker blocking toggle."""
        self.block_trackers = switch.get_active()
        self._save_browser_settings(block_trackers=self.block_trackers)
    
    def _on_sponsorblock_toggled(self, switch, pspec):
        """Handle SponsorBlock toggle."""
        self.sponsorblock_enabled = switch.get_active()
        self._save_browser_settings(sponsorblock_enabled=self.sponsorblock_enabled)
    
    def _on_homepage_changed(self, entry):
        """Handle homepage change."""
        homepage = entry.get_text().strip()
        if homepage:
            self._save_browser_settings(homepage=homepage)
            # Also update the instance variable
            self.browser_home_url = homepage
    
    def _on_search_engine_changed(self, dropdown, pspec):
        """Handle search engine change."""
        engines = ["DuckDuckGo", "Google", "Bing", "Startpage", "Brave"]
        selected = dropdown.get_selected()
        if 0 <= selected < len(engines):
            self._save_browser_settings(search_engine=engines[selected])
    
    def _on_default_zoom_changed(self, dropdown, pspec):
        """Handle default zoom change."""
        zoom_values = [0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
        selected = dropdown.get_selected()
        if 0 <= selected < len(zoom_values):
            zoom = zoom_values[selected]
            self._save_browser_settings(default_zoom=zoom)
            # Apply to all current tabs
            self._apply_zoom_to_all_tabs(zoom)
            self._save_zoom_level(zoom)
    
    def _on_tts_voice_changed(self, dropdown, pspec):
        """Handle TTS voice change."""
        selected = dropdown.get_selected()
        if selected in self.tts_voice_map:
            self.tts_voice = self.tts_voice_map[selected]
            self._save_browser_settings(tts_voice=self.tts_voice)
            print(f"[TTS] Voice changed to: {self.tts_voice}")
    
    def _on_tts_speed_changed(self, dropdown, pspec):
        """Handle TTS speed change."""
        selected = dropdown.get_selected()
        if selected in self.tts_speed_map:
            self.tts_rate = self.tts_speed_map[selected]
            self._save_browser_settings(tts_rate=self.tts_rate)
            print(f"[TTS] Speed changed to: {self.tts_rate}")
    
    def _on_tts_test_clicked(self, button):
        """Test the TTS voice."""
        test_text = "Hello! This is a test of the Read Aloud feature in Tux Assistant. How does this voice sound to you?"
        self._read_aloud(test_text)
    
    def _on_tts_stop_clicked(self, button):
        """Stop TTS playback."""
        self._stop_read_aloud()
    
    def _read_aloud(self, text):
        """Read text aloud using edge-tts with chunking and caching."""
        import subprocess
        import tempfile
        import shutil
        import hashlib
        import threading
        
        # Stop any existing playback
        self._stop_read_aloud()
        
        # Check if edge-tts is available
        if not shutil.which('edge-tts'):
            self._show_toast("edge-tts not found. Install with: pip install edge-tts")
            return
        
        # Check for audio player
        player = None
        for p in ['mpv', 'ffplay', 'vlc', 'paplay']:
            if shutil.which(p):
                player = p
                break
        
        if not player:
            self._show_toast("No audio player found. Install mpv or vlc.")
            return
        
        # Setup cache directory
        cache_dir = os.path.join(self.CONFIG_DIR, 'tts_cache')
        os.makedirs(cache_dir, exist_ok=True)
        
        # Update UI - show stop button, hide play button
        if hasattr(self, 'tts_stop_btn'):
            self.tts_stop_btn.set_sensitive(True)
        if hasattr(self, 'stop_reading_btn'):
            self.stop_reading_btn.set_visible(True)
        if hasattr(self, 'read_article_btn'):
            self.read_article_btn.set_visible(False)
        
        # Track state for this playback session
        self.tts_playing = True
        self.tts_audio_file = "playing"  # Marker that we're active
        
        def get_cache_path(chunk_text):
            """Generate cache path for a text chunk."""
            cache_key = f"{self.tts_voice}_{self.tts_rate}_{chunk_text}"
            cache_hash = hashlib.md5(cache_key.encode()).hexdigest()
            return os.path.join(cache_dir, f"{cache_hash}.mp3")
        
        def generate_chunk(chunk_text, output_path):
            """Generate audio for a single chunk."""
            cmd = [
                'edge-tts',
                '--voice', self.tts_voice,
                '--rate', self.tts_rate,
                '--text', chunk_text,
                '--write-media', output_path
            ]
            result = subprocess.run(cmd, capture_output=True, timeout=120)
            return result.returncode == 0
        
        def play_audio(audio_path):
            """Play an audio file and wait for completion."""
            if player == 'mpv':
                play_cmd = ['mpv', '--no-video', '--really-quiet', audio_path]
            elif player == 'ffplay':
                play_cmd = ['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', audio_path]
            elif player == 'vlc':
                play_cmd = ['vlc', '--intf', 'dummy', '--play-and-exit', audio_path]
            else:
                play_cmd = ['paplay', audio_path]
            
            self.tts_process = subprocess.Popen(play_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.tts_process.wait()
            self.tts_process = None
        
        def split_into_chunks(full_text, max_chunk_size=1500):
            """Split text into chunks at sentence boundaries."""
            chunks = []
            
            # Split by paragraphs first
            paragraphs = full_text.split('\n\n')
            current_chunk = ""
            
            for para in paragraphs:
                para = para.strip()
                if not para:
                    continue
                
                # If adding this paragraph exceeds limit, save current and start new
                if len(current_chunk) + len(para) > max_chunk_size and current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = para
                else:
                    current_chunk += " " + para if current_chunk else para
            
            # Don't forget the last chunk
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            
            # If we only have one big chunk, try splitting by sentences
            if len(chunks) == 1 and len(chunks[0]) > max_chunk_size:
                text = chunks[0]
                chunks = []
                sentences = []
                
                # Simple sentence splitting
                import re
                sentence_endings = re.split(r'(?<=[.!?])\s+', text)
                current_chunk = ""
                
                for sentence in sentence_endings:
                    if len(current_chunk) + len(sentence) > max_chunk_size and current_chunk:
                        chunks.append(current_chunk.strip())
                        current_chunk = sentence
                    else:
                        current_chunk += " " + sentence if current_chunk else sentence
                
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
            
            return chunks if chunks else [full_text]
        
        def stream_and_play():
            """Generate and play chunks in a streaming fashion."""
            try:
                chunks = split_into_chunks(text)
                total_chunks = len(chunks)
                
                if total_chunks == 1:
                    GLib.idle_add(self._show_toast, "Generating audio...")
                else:
                    GLib.idle_add(self._show_toast, f"Reading {total_chunks} sections...")
                
                for i, chunk in enumerate(chunks):
                    # Check if we should stop
                    if not self.tts_playing:
                        return
                    
                    cache_path = get_cache_path(chunk)
                    
                    # Check cache first
                    if os.path.exists(cache_path):
                        # Cache hit - play immediately
                        if total_chunks > 1:
                            GLib.idle_add(self._show_toast, f"Playing {i+1}/{total_chunks} (cached)")
                    else:
                        # Cache miss - generate
                        if total_chunks > 1:
                            GLib.idle_add(self._show_toast, f"Generating {i+1}/{total_chunks}...")
                        else:
                            GLib.idle_add(self._show_toast, "Generating...")
                        
                        # Generate to temp file first, then move to cache
                        temp_path = cache_path + ".tmp"
                        if not generate_chunk(chunk, temp_path):
                            GLib.idle_add(self._show_toast, "TTS generation failed")
                            return
                        
                        # Check again if we should stop
                        if not self.tts_playing:
                            try:
                                os.remove(temp_path)
                            except:
                                pass
                            return
                        
                        # Move to cache
                        try:
                            shutil.move(temp_path, cache_path)
                        except:
                            cache_path = temp_path  # Use temp if move fails
                        
                        if total_chunks == 1:
                            GLib.idle_add(self._show_toast, "Playing...")
                    
                    # Play this chunk
                    if not self.tts_playing:
                        return
                    
                    play_audio(cache_path)
                    
            except subprocess.TimeoutExpired:
                GLib.idle_add(self._show_toast, "TTS generation timed out")
            except Exception as e:
                GLib.idle_add(self._show_toast, f"TTS error: {str(e)[:50]}")
            finally:
                self.tts_playing = False
                GLib.idle_add(self._tts_playback_finished)
        
        # Run in background thread
        thread = threading.Thread(target=stream_and_play, daemon=True)
        thread.start()
    
    def _stop_read_aloud(self):
        """Stop current TTS playback."""
        import signal
        import os as os_module
        
        # Signal to stop streaming
        self.tts_playing = False
        
        if self.tts_process:
            try:
                # Try SIGKILL for immediate stop
                self.tts_process.kill()
                try:
                    self.tts_process.wait(timeout=1)
                except:
                    pass
            except:
                pass
            finally:
                self.tts_process = None
        
        if self.tts_audio_file:
            try:
                if os_module.path.exists(self.tts_audio_file):
                    os_module.remove(self.tts_audio_file)
                self.tts_audio_file = None
            except:
                pass
        
        # Update UI
        if hasattr(self, 'tts_stop_btn'):
            self.tts_stop_btn.set_sensitive(False)
        if hasattr(self, 'stop_reading_btn'):
            self.stop_reading_btn.set_visible(False)
        if hasattr(self, 'read_article_btn'):
            self.read_article_btn.set_visible(True)
    
    def _on_stop_reading_clicked(self, button):
        """Handle stop reading button click."""
        self._stop_read_aloud()
        self._show_toast("Reading stopped")
    
    def _on_reader_mode_toggled(self, button):
        """Toggle reader mode for distraction-free reading."""
        webview = self._get_current_browser_webview()
        if not webview:
            button.set_active(False)
            return
        
        self._reader_mode_active = button.get_active()
        
        if self._reader_mode_active:
            # Activate reader mode
            self._enable_reader_mode(webview)
        else:
            # Deactivate reader mode - reload page to restore
            webview.reload()
    
    def _enable_reader_mode(self, webview):
        """Extract article content and display in reader mode."""
        # JavaScript to extract article content and apply reader styling
        reader_js = '''
        (function() {
            // Try to find main article content
            var article = document.querySelector('article') || 
                          document.querySelector('[role="main"]') ||
                          document.querySelector('.post-content') ||
                          document.querySelector('.article-content') ||
                          document.querySelector('.entry-content') ||
                          document.querySelector('.content') ||
                          document.querySelector('main');
            
            // Get title
            var title = document.querySelector('h1') || document.querySelector('title');
            var titleText = title ? title.textContent : document.title;
            
            // Get article text
            var content = '';
            if (article) {
                content = article.innerHTML;
            } else {
                // Fallback: get all paragraphs
                var paragraphs = document.querySelectorAll('p');
                for (var i = 0; i < paragraphs.length; i++) {
                    if (paragraphs[i].textContent.length > 50) {
                        content += '<p>' + paragraphs[i].textContent + '</p>';
                    }
                }
            }
            
            if (!content || content.length < 100) {
                alert('Could not extract article content from this page.');
                return false;
            }
            
            // Create reader mode overlay
            var readerCSS = `
                body.tux-reader-mode {
                    background: #fefefe !important;
                    color: #333 !important;
                }
                @media (prefers-color-scheme: dark) {
                    body.tux-reader-mode {
                        background: #1a1a2e !important;
                        color: #e8e8e8 !important;
                    }
                    body.tux-reader-mode .tux-reader-container {
                        background: #1a1a2e !important;
                    }
                }
                .tux-reader-container {
                    max-width: 700px !important;
                    margin: 0 auto !important;
                    padding: 40px 20px !important;
                    font-family: Georgia, 'Times New Roman', serif !important;
                    font-size: 20px !important;
                    line-height: 1.8 !important;
                    background: #fefefe !important;
                }
                .tux-reader-container h1 {
                    font-size: 32px !important;
                    margin-bottom: 30px !important;
                    line-height: 1.3 !important;
                    font-weight: bold !important;
                }
                .tux-reader-container p {
                    margin-bottom: 1.5em !important;
                }
                .tux-reader-container img {
                    max-width: 100% !important;
                    height: auto !important;
                    margin: 20px 0 !important;
                }
                .tux-reader-container a {
                    color: #0066cc !important;
                }
                .tux-reader-hidden {
                    display: none !important;
                }
            `;
            
            // Add style
            var style = document.createElement('style');
            style.id = 'tux-reader-style';
            style.textContent = readerCSS;
            document.head.appendChild(style);
            
            // Hide original content
            document.body.classList.add('tux-reader-mode');
            var children = document.body.children;
            for (var i = 0; i < children.length; i++) {
                if (!children[i].classList.contains('tux-reader-container')) {
                    children[i].classList.add('tux-reader-hidden');
                }
            }
            
            // Create reader container
            var container = document.createElement('div');
            container.className = 'tux-reader-container';
            container.innerHTML = '<h1>' + titleText + '</h1>' + content;
            document.body.appendChild(container);
            
            // Scroll to top
            window.scrollTo(0, 0);
            
            return true;
        })();
        '''
        
        webview.evaluate_javascript(reader_js, -1, None, None, None, None, None)
    
    def _tts_playback_finished(self):
        """Called when TTS playback finishes."""
        self.tts_process = None
        self.tts_playing = False
        self.tts_audio_file = None
        
        if hasattr(self, 'tts_stop_btn'):
            self.tts_stop_btn.set_sensitive(False)
        if hasattr(self, 'stop_reading_btn'):
            self.stop_reading_btn.set_visible(False)
        if hasattr(self, 'read_article_btn'):
            self.read_article_btn.set_visible(True)
    
    def _on_browser_context_menu(self, webview, context_menu, event, hit_test_result=None):
        """Handle browser context menu to add Read Aloud option."""
        try:
            # Add separator before our items
            context_menu.append(WebKit.ContextMenuItem.new_separator())
            
            # Create a simple action for Read Aloud
            # Use Gtk.Action approach that works with WebKit context menus
            read_action = Gio.SimpleAction.new("tux-read-aloud", None)
            read_action.connect("activate", lambda a, p: self._read_selection_aloud(webview))
            
            # Register the action with the application
            app = self.get_application()
            if app:
                app.add_action(read_action)
            
            # Try the new WebKit 4.1+ API first
            try:
                # For WebKit2GTK 4.1+, use the GAction approach
                read_item = WebKit.ContextMenuItem.new_from_gaction(
                    read_action,
                    "🔊 Read Selection Aloud",
                    None
                )
                context_menu.append(read_item)
            except:
                # Fallback: Create with stock action and modify
                pass
            
            # Add Stop option if currently playing
            if self.tts_process:
                stop_action = Gio.SimpleAction.new("tux-stop-reading", None)
                stop_action.connect("activate", lambda a, p: self._stop_read_aloud())
                if app:
                    app.add_action(stop_action)
                
                try:
                    stop_item = WebKit.ContextMenuItem.new_from_gaction(
                        stop_action,
                        "⏹️ Stop Reading",
                        None
                    )
                    context_menu.append(stop_item)
                except:
                    pass
                    
        except Exception as e:
            print(f"[TTS] Context menu error: {e}")
        
        return False  # Don't block the menu
    
    def _read_selection_aloud(self, webview):
        """Get selected text from webview and read it aloud."""
        js_code = "window.getSelection().toString();"
        
        def on_js_result(source_object, result, user_data=None):
            try:
                js_result = source_object.evaluate_javascript_finish(result)
                if js_result:
                    text = None
                    if hasattr(js_result, 'to_string'):
                        text = js_result.to_string()
                    elif hasattr(js_result, 'is_string') and js_result.is_string():
                        text = js_result.to_string()
                    elif hasattr(js_result, 'get_string'):
                        text = js_result.get_string()
                    
                    if text and text.strip():
                        self._read_aloud(text.strip())
                    else:
                        self._show_toast("No text selected")
                else:
                    self._show_toast("No text selected")
            except Exception as e:
                print(f"[TTS] Error: {e}")
                self._show_toast("Could not get selected text")
        
        try:
            if hasattr(webview, 'evaluate_javascript'):
                webview.evaluate_javascript(js_code, -1, None, None, None, on_js_result)
            elif hasattr(webview, 'run_javascript'):
                webview.run_javascript(js_code, None, on_js_result, None)
        except Exception as e:
            print(f"[TTS] JavaScript execution failed: {e}")

    def _on_read_article_clicked(self, button):
        """Handle read article button click."""
        webview = self._get_current_browser_webview()
        if webview:
            self._read_article_aloud(webview)
        else:
            self._show_toast("No page loaded")

    def _read_article_aloud(self, webview):
        """Extract main article content from page and read it aloud."""
        # JavaScript to extract article content
        # Priority: <article>, common article classes, element with most <p> text
        js_code = """
        (function() {
            // Helper to get text content, stripping scripts/styles
            function getCleanText(el) {
                if (!el) return '';
                var clone = el.cloneNode(true);
                // Remove scripts, styles, nav, footer, aside, ads
                var remove = clone.querySelectorAll('script, style, nav, footer, aside, .ad, .ads, .advertisement, .social-share, .comments, .related-posts, [role="complementary"], [role="navigation"]');
                remove.forEach(function(r) { r.remove(); });
                return clone.textContent.trim().replace(/\\s+/g, ' ');
            }
            
            // Try <article> element first
            var article = document.querySelector('article');
            if (article) {
                var text = getCleanText(article);
                if (text.length > 200) return text;
            }
            
            // Try common article content selectors
            var selectors = [
                '.article-body', '.article-content', '.post-content', '.entry-content',
                '.story-body', '.story-content', '.content-body', '.main-content',
                '[itemprop="articleBody"]', '[role="article"]', '.post-body',
                '.article__body', '.article__content', '#article-body', '#story-body'
            ];
            
            for (var i = 0; i < selectors.length; i++) {
                var el = document.querySelector(selectors[i]);
                if (el) {
                    var text = getCleanText(el);
                    if (text.length > 200) return text;
                }
            }
            
            // Fallback: find element with most paragraph text
            var main = document.querySelector('main') || document.body;
            var paragraphs = main.querySelectorAll('p');
            var texts = [];
            paragraphs.forEach(function(p) {
                var t = p.textContent.trim();
                if (t.length > 50) texts.push(t);
            });
            
            if (texts.length > 0) {
                return texts.join(' ');
            }
            
            return '';
        })();
        """
        
        def on_js_result(source_object, result, user_data=None):
            try:
                js_result = source_object.evaluate_javascript_finish(result)
                if js_result:
                    text = None
                    if hasattr(js_result, 'to_string'):
                        text = js_result.to_string()
                    elif hasattr(js_result, 'is_string') and js_result.is_string():
                        text = js_result.to_string()
                    elif hasattr(js_result, 'get_string'):
                        text = js_result.get_string()
                    
                    if text and text.strip() and len(text.strip()) > 50:
                        # Limit to reasonable length (avoid reading entire page)
                        article_text = text.strip()
                        if len(article_text) > 15000:
                            article_text = article_text[:15000] + "... Article truncated."
                        self._show_toast(f"Reading article ({len(article_text)} chars)")
                        self._read_aloud(article_text)
                    else:
                        self._show_toast("Could not find article content")
                else:
                    self._show_toast("Could not find article content")
            except Exception as e:
                print(f"[TTS] Article extraction error: {e}")
                self._show_toast("Could not extract article")
        
        try:
            if hasattr(webview, 'evaluate_javascript'):
                webview.evaluate_javascript(js_code, -1, None, None, None, on_js_result)
            elif hasattr(webview, 'run_javascript'):
                webview.run_javascript(js_code, None, on_js_result, None)
        except Exception as e:
            print(f"[TTS] JavaScript execution failed: {e}")

    def _on_clear_history_clicked(self, button):
        """Clear browsing history."""
        try:
            history_db = os.path.join(self.CONFIG_DIR, 'browser_history.db')
            if os.path.exists(history_db):
                import sqlite3
                conn = sqlite3.connect(history_db)
                conn.execute("DELETE FROM history")
                conn.commit()
                conn.close()
            self._show_toast("History cleared")
        except Exception as e:
            self._show_toast(f"Failed to clear history: {e}")
    
    def _on_clear_cookies_clicked(self, button):
        """Clear browser cookies."""
        try:
            if self.browser_network_session:
                cookie_manager = self.browser_network_session.get_cookie_manager()
                # Clear all cookies
                data_dir = os.path.join(GLib.get_user_data_dir(), 'tux-assistant', 'webview')
                cookie_file = os.path.join(data_dir, 'cookies.sqlite')
                if os.path.exists(cookie_file):
                    os.remove(cookie_file)
                self._show_toast("Cookies cleared (restart browser to take effect)")
            else:
                self._show_toast("Cookie manager not available")
        except Exception as e:
            self._show_toast(f"Failed to clear cookies: {e}")
    
    def _on_clear_cache_clicked(self, button):
        """Clear browser cache."""
        try:
            cache_dir = os.path.join(GLib.get_user_cache_dir(), 'tux-assistant', 'webview')
            if os.path.exists(cache_dir):
                import shutil
                shutil.rmtree(cache_dir)
                os.makedirs(cache_dir, exist_ok=True)
            self._show_toast("Cache cleared")
        except Exception as e:
            self._show_toast(f"Failed to clear cache: {e}")
    
    def _on_clear_all_clicked(self, button):
        """Clear all browsing data."""
        # Create confirmation dialog
        dialog = Adw.MessageDialog.new(
            self,
            "Clear All Browsing Data?",
            "This will clear history, cookies, and cache. This cannot be undone."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("clear", "Clear All")
        dialog.set_response_appearance("clear", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.connect("response", self._on_clear_all_confirmed)
        dialog.present()
    
    def _on_clear_all_confirmed(self, dialog, response):
        """Handle clear all confirmation."""
        if response == "clear":
            # Clear history
            try:
                history_db = os.path.join(self.CONFIG_DIR, 'browser_history.db')
                if os.path.exists(history_db):
                    import sqlite3
                    conn = sqlite3.connect(history_db)
                    conn.execute("DELETE FROM history")
                    conn.commit()
                    conn.close()
            except:
                pass
            
            # Clear cookies
            try:
                data_dir = os.path.join(GLib.get_user_data_dir(), 'tux-assistant', 'webview')
                cookie_file = os.path.join(data_dir, 'cookies.sqlite')
                if os.path.exists(cookie_file):
                    os.remove(cookie_file)
            except:
                pass
            
            # Clear cache
            try:
                cache_dir = os.path.join(GLib.get_user_cache_dir(), 'tux-assistant', 'webview')
                if os.path.exists(cache_dir):
                    import shutil
                    shutil.rmtree(cache_dir)
                    os.makedirs(cache_dir, exist_ok=True)
            except:
                pass
            
            self._show_toast("All browsing data cleared")
    
    def _update_default_browser_status(self):
        """Update the default browser status label."""
        try:
            result = subprocess.run(
                ['xdg-settings', 'get', 'default-web-browser'],
                capture_output=True, text=True, timeout=5
            )
            current = result.stdout.strip()
            
            if 'tuxassistant' in current.lower() or 'tux-assistant' in current.lower():
                if hasattr(self, 'default_browser_status'):
                    self.default_browser_status.set_label("✓ Tux Browser is your default browser")
                    self.default_browser_status.remove_css_class("dim-label")
                    self.default_browser_status.add_css_class("success")
            else:
                if hasattr(self, 'default_browser_status'):
                    self.default_browser_status.set_label(f"Current: {current or 'Unknown'}")
                    self.default_browser_status.remove_css_class("success")
                    self.default_browser_status.add_css_class("dim-label")
        except Exception as e:
            if hasattr(self, 'default_browser_status'):
                self.default_browser_status.set_label("Could not detect default browser")
    
    def _on_set_default_browser_clicked(self, button):
        """Set Tux Assistant as the default web browser."""
        try:
            # The desktop file should be installed at standard locations
            desktop_file = "com.tuxassistant.app.desktop"
            
            # Try to set as default browser using xdg-settings
            result = subprocess.run(
                ['xdg-settings', 'set', 'default-web-browser', desktop_file],
                capture_output=True, text=True, timeout=10
            )
            
            if result.returncode == 0:
                self._show_toast("Tux Browser set as default!")
                self._update_default_browser_status()
            else:
                # Try alternative: xdg-mime for http/https
                subprocess.run([
                    'xdg-mime', 'default', desktop_file, 
                    'x-scheme-handler/http', 'x-scheme-handler/https'
                ], timeout=10)
                
                self._show_toast("Tux Browser set as default!")
                self._update_default_browser_status()
                
        except subprocess.TimeoutExpired:
            self._show_toast("Setting default browser timed out")
        except FileNotFoundError:
            self._show_toast("xdg-settings not found - install xdg-utils")
        except Exception as e:
            self._show_toast(f"Error: {str(e)[:50]}")
    
    def _show_toast(self, message):
        """Show a toast notification."""
        if hasattr(self, 'toast_overlay'):
            toast = Adw.Toast.new(message)
            toast.set_timeout(3)
            self.toast_overlay.add_toast(toast)
        else:
            print(f"[Toast] {message}")
    
    # =========================================================================
    # Update Checker
    # =========================================================================
    
    def _setup_update_popover(self):
        """Setup the update notification popover."""
        self.update_popover = Gtk.Popover()
        self.update_popover.set_autohide(True)
        
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        box.set_margin_top(12)
        box.set_margin_bottom(12)
        box.set_margin_start(12)
        box.set_margin_end(12)
        
        # Title
        self.update_title = Gtk.Label()
        self.update_title.set_markup("<b>Update Available!</b>")
        self.update_title.set_halign(Gtk.Align.START)
        box.append(self.update_title)
        
        # Version info
        self.update_version_label = Gtk.Label()
        self.update_version_label.set_halign(Gtk.Align.START)
        self.update_version_label.add_css_class("dim-label")
        box.append(self.update_version_label)
        
        # Changelog preview (scrollable)
        scroll = Gtk.ScrolledWindow()
        scroll.set_min_content_height(100)
        scroll.set_max_content_height(200)
        scroll.set_min_content_width(300)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        self.update_changelog = Gtk.Label()
        self.update_changelog.set_wrap(True)
        self.update_changelog.set_wrap_mode(2)  # WORD_CHAR
        self.update_changelog.set_halign(Gtk.Align.START)
        self.update_changelog.set_valign(Gtk.Align.START)
        self.update_changelog.set_selectable(True)
        scroll.set_child(self.update_changelog)
        box.append(scroll)
        
        # Download button
        download_btn = Gtk.Button(label="View on GitHub")
        download_btn.add_css_class("suggested-action")
        download_btn.connect("clicked", self._on_update_download_clicked)
        box.append(download_btn)
        
        self.update_popover.set_child(box)
        self.update_button.set_popover(self.update_popover)
        
        # Store release URL for download button
        self.update_release_url = None
    
    def _check_for_updates(self):
        """Check GitHub for updates (runs in background thread)."""
        def do_check():
            try:
                # Check if we should skip (checked in last 24 hours)
                if os.path.exists(self.UPDATE_CHECK_FILE):
                    try:
                        with open(self.UPDATE_CHECK_FILE, 'r') as f:
                            cached = json.load(f)
                        last_check = datetime.fromisoformat(cached.get('last_check', '2000-01-01'))
                        if datetime.now() - last_check < timedelta(hours=24):
                            # Use cached result if update was available
                            if cached.get('update_available'):
                                GLib.idle_add(
                                    self._show_update_available,
                                    cached.get('latest_version', ''),
                                    cached.get('changelog', ''),
                                    cached.get('release_url', '')
                                )
                            return
                    except (json.JSONDecodeError, ValueError):
                        pass  # Invalid cache, check anyway
                
                # Fetch latest release from GitHub
                req = urllib.request.Request(
                    self.GITHUB_RELEASES_URL,
                    headers={'User-Agent': f'Tux-Assistant/{APP_VERSION}'}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode('utf-8'))
                
                latest_version = data.get('tag_name', '').lstrip('v')
                changelog = data.get('body', '')[:500]  # Limit changelog length
                release_url = data.get('html_url', '')
                
                # Compare versions
                current = APP_VERSION.lstrip('v')
                update_available = self._compare_versions(latest_version, current) > 0
                
                # Cache the result
                os.makedirs(self.CONFIG_DIR, exist_ok=True)
                with open(self.UPDATE_CHECK_FILE, 'w') as f:
                    json.dump({
                        'last_check': datetime.now().isoformat(),
                        'latest_version': latest_version,
                        'update_available': update_available,
                        'changelog': changelog,
                        'release_url': release_url
                    }, f)
                
                # Show update if available
                if update_available:
                    GLib.idle_add(
                        self._show_update_available,
                        latest_version,
                        changelog,
                        release_url
                    )
                else:
                    print(f"[Update] Current version {current} is up to date")
                    
            except Exception as e:
                print(f"[Update] Check failed: {e}")
        
        # Run in background thread
        thread = threading.Thread(target=do_check, daemon=True)
        thread.start()
    
    def _compare_versions(self, v1, v2):
        """Compare two version strings. Returns: 1 if v1>v2, -1 if v1<v2, 0 if equal."""
        try:
            def parse_version(v):
                # Handle versions like "0.9.203" or "v0.9.203"
                v = v.lstrip('v')
                parts = []
                for part in v.split('.'):
                    # Handle parts like "203-beta" -> just take the number
                    num = ''.join(c for c in part if c.isdigit())
                    parts.append(int(num) if num else 0)
                return parts
            
            p1, p2 = parse_version(v1), parse_version(v2)
            
            # Pad to same length
            while len(p1) < len(p2): p1.append(0)
            while len(p2) < len(p1): p2.append(0)
            
            for a, b in zip(p1, p2):
                if a > b: return 1
                if a < b: return -1
            return 0
        except Exception:
            return 0  # On error, assume equal
    
    def _show_update_available(self, version, changelog, release_url):
        """Show the update indicator (called from main thread)."""
        self.update_version_label.set_text(f"v{APP_VERSION} → v{version}")
        
        # Clean up changelog for display
        if changelog:
            # Take first ~300 chars, try to end at sentence
            preview = changelog[:300]
            if len(changelog) > 300:
                # Try to end at a period or newline
                last_break = max(preview.rfind('.'), preview.rfind('\n'))
                if last_break > 100:
                    preview = preview[:last_break + 1]
                preview += "..."
            self.update_changelog.set_text(preview)
        else:
            self.update_changelog.set_text("See GitHub for details.")
        
        self.update_release_url = release_url
        self.update_button.set_visible(True)
        print(f"[Update] Version {version} available!")
    
    def _on_update_download_clicked(self, button):
        """Open the GitHub release page."""
        self.update_popover.popdown()
        if self.update_release_url:
            try:
                Gio.AppInfo.launch_default_for_uri(self.update_release_url, None)
            except Exception as e:
                self._show_toast(f"Couldn't open browser: {e}")
    
    def _update_blocked_count(self):
        """Update the protection status label."""
        if hasattr(self, 'blocked_label'):
            if self.pages_protected > 0:
                self.blocked_label.set_label(f"🛡️ {self.pages_protected} pages protected")
            else:
                self.blocked_label.set_label("🛡️ Protection active")
    
    def _init_content_filters(self):
        """Initialize WebKit content filter store for ad blocking."""
        try:
            # Check if UserContentFilterStore is available
            if not hasattr(WebKit, 'UserContentFilterStore'):
                print("[Privacy] UserContentFilterStore not available, using fallback")
                return
            
            # Create filter store directory
            filter_dir = os.path.join(self.CONFIG_DIR, 'filters')
            os.makedirs(filter_dir, exist_ok=True)
            
            # Create the filter store
            self.content_filter_store = WebKit.UserContentFilterStore.new(filter_dir)
            
            # Load or create our filter
            self._load_or_create_filters()
            
        except Exception as e:
            print(f"[Privacy] Failed to init content filters: {e}")
    
    def _load_or_create_filters(self):
        """Load existing filters or create new ones."""
        if not self.content_filter_store:
            return
        
        # Check if we have a cached filter
        filter_file = os.path.join(self.CONFIG_DIR, 'filters', 'easylist.json')
        
        if not os.path.exists(filter_file):
            # Create our filter rules
            self._create_filter_rules(filter_file)
        
        # Load the filter
        try:
            self.content_filter_store.load(
                'tux-adblock',
                None,  # cancellable
                self._on_filter_loaded
            )
        except Exception as e:
            print(f"[Privacy] Filter load failed, saving new: {e}")
            self._save_and_load_filter(filter_file)
    
    def _create_filter_rules(self, filter_file):
        """Create WebKit content blocker rules in JSON format."""
        # WebKit Content Blocker format (same as Safari)
        # This is a curated list based on EasyList patterns
        rules = [
            # Block common ad domains
            {"trigger": {"url-filter": ".*doubleclick\\.net"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*googlesyndication\\.com"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*googleadservices\\.com"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*google-analytics\\.com"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*googletagmanager\\.com"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*amazon-adsystem\\.com"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*facebook\\.net.*tr"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*facebook\\.com/tr"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*adnxs\\.com"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*adsrvr\\.org"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*criteo\\.(com|net)"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*taboola\\.com"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*outbrain\\.com"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*pubmatic\\.com"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*rubiconproject\\.com"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*openx\\.net"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*hotjar\\.com"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*mixpanel\\.com"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*segment\\.io"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*amplitude\\.com"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*quantserve\\.com"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*scorecardresearch\\.com"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*moatads\\.com"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*adsafeprotected\\.com"}, "action": {"type": "block"}},
            
            # Block ad URLs by pattern
            {"trigger": {"url-filter": ".*/ads/"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*/ad/"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*\\.ad\\."}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*/pagead/"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*/adserver"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*/adclick"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*/aclk\\?"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*banner.*\\.gif"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*banner.*\\.jpg"}, "action": {"type": "block"}},
            {"trigger": {"url-filter": ".*banner.*\\.png"}, "action": {"type": "block"}},
            
            # CSS hiding rules
            {"trigger": {"url-filter": ".*"}, "action": {"type": "css-display-none", "selector": ".adsbygoogle, .ad-container, .ad-wrapper, .ad-slot, .ad-banner, .ad-unit"}},
            {"trigger": {"url-filter": ".*"}, "action": {"type": "css-display-none", "selector": "[id*='div-gpt-ad'], [class*='gpt-ad'], .taboola, .outbrain, .OUTBRAIN"}},
            {"trigger": {"url-filter": ".*"}, "action": {"type": "css-display-none", "selector": "[class*='banner-ad'], [class*='ad-banner'], [class*='leaderboard-ad']"}},
            {"trigger": {"url-filter": ".*"}, "action": {"type": "css-display-none", "selector": "ins.adsbygoogle, amp-ad, amp-embed, amp-sticky-ad"}},
        ]
        
        import json
        with open(filter_file, 'w') as f:
            json.dump(rules, f)
        
        print(f"[Privacy] Created {len(rules)} filter rules")
    
    def _save_and_load_filter(self, filter_file):
        """Save filter to store and load it."""
        if not self.content_filter_store or not os.path.exists(filter_file):
            return
        
        try:
            with open(filter_file, 'r') as f:
                rules_json = f.read()
            
            # Save to the filter store
            self.content_filter_store.save(
                'tux-adblock',
                GLib.Bytes.new(rules_json.encode('utf-8')),
                None,  # cancellable
                self._on_filter_saved
            )
        except Exception as e:
            print(f"[Privacy] Failed to save filter: {e}")
    
    def _on_filter_saved(self, store, result):
        """Called when filter is saved."""
        try:
            content_filter = store.save_finish(result)
            self.content_filters.append(content_filter)
            print("[Privacy] Content filter saved and ready")
        except Exception as e:
            print(f"[Privacy] Filter save failed: {e}")
    
    def _on_filter_loaded(self, store, result):
        """Called when filter is loaded."""
        try:
            content_filter = store.load_finish(result)
            self.content_filters.append(content_filter)
            print("[Privacy] Content filter loaded")
        except Exception as e:
            # Filter doesn't exist yet, create it
            filter_file = os.path.join(self.CONFIG_DIR, 'filters', 'easylist.json')
            if not os.path.exists(filter_file):
                self._create_filter_rules(filter_file)
            self._save_and_load_filter(filter_file)
    
    def _apply_ad_blocking_css(self, webview):
        """Apply CSS to hide common ad elements."""
        try:
            content_manager = webview.get_user_content_manager()
            
            # Conservative ad-hiding CSS - only target definite ad patterns
            ad_hide_css = """
            /* Definite ad containers */
            .ad-container, .ad-wrapper, .ad-slot, .ad-unit,
            .ad-banner, .ad-box, .ad-placeholder, .ad-frame,
            .adsbygoogle, .ads-container, .ad-leaderboard,
            .banner-ad, .sidebar-ad,
            
            /* Google Ads */
            ins.adsbygoogle, [data-ad-slot], [data-google-query-id],
            amp-ad, amp-embed, amp-sticky-ad,
            iframe[src*="doubleclick"], iframe[src*="googlesyndication"],
            iframe[src*="amazon-adsystem"],
            
            /* Common banner ad patterns */
            [class*="banner-ad"], [class*="ad-banner"], [id*="banner-ad"],
            [class*="leaderboard"], [class*="top-banner"], [class*="header-ad"],
            [class*="rectangle-ad"], [class*="skyscraper"],
            
            /* Specific ad networks */
            .taboola, .outbrain, #taboola-below, .OUTBRAIN,
            [id*="div-gpt-ad"], [class*="gpt-ad"],
            
            /* Common WordPress ad plugins */
            .wp-ad, .wpa, .adrotate, .advanced-ads,
            
            /* Sponsored content containers */
            .sponsored, .sponsored-content, .sponsored-post,
            .promoted, .promoted-content, .native-ad,
            .carbon-wrap, .carbonads, #carbonads,
            .bsa-cpc, .buysellads, [id*="bsa-zone"],
            [class*="adthrive"], [class*="mediavine"], [id*="ezoic"],
            
            /* Cookie banners (specific patterns) */
            .cc-banner, .cookie-banner, .cookie-notice,
            #onetrust-banner-sdk, .onetrust-pc-dark-filter
            
            { display: none !important; visibility: hidden !important; height: 0 !important; overflow: hidden !important; }
            """
            
            user_style = WebKit.UserStyleSheet.new(
                ad_hide_css,
                WebKit.UserContentInjectedFrames.ALL_FRAMES,
                WebKit.UserStyleLevel.USER,
                None,  # allowlist
                None   # blocklist
            )
            content_manager.add_style_sheet(user_style)
        except Exception as e:
            print(f"Failed to apply ad-blocking CSS: {e}")
    
    def _on_browser_load_changed(self, webview, event):
        """Update URL bar when page loads and record history."""
        if event == WebKit.LoadEvent.COMMITTED:
            uri = webview.get_uri()
            if uri and hasattr(self, 'browser_url_entry'):
                if hasattr(self, '_autocomplete_active'):
                    self._autocomplete_active = True
                self.browser_url_entry.set_text(uri)
                if hasattr(self, '_autocomplete_active'):
                    self._autocomplete_active = False
            # Update bookmark star for current URL
            self._update_bookmark_star()
        
        # Record to history when page finishes loading (has title)
        elif event == WebKit.LoadEvent.FINISHED:
            uri = webview.get_uri()
            title = webview.get_title()
            if uri:
                self._record_history(uri, title)
            
            # Inject ad-hiding JavaScript after page loads
            if self.block_ads:
                self._inject_ad_hiding_js(webview)
            
            # Inject SponsorBlock for ALL YouTube pages (handles SPA navigation internally)
            if self.sponsorblock_enabled and uri and 'youtube.com' in uri:
                print(f"[SponsorBlock] YouTube page detected, injecting monitor script")
                self._inject_sponsorblock_monitor(webview)
    
    def _inject_ad_hiding_js(self, webview):
        """Inject JavaScript to hide ads after page load."""
        js_code = """
        (function() {
            console.log('[Tux] Ad hiding script running...');
            
            // Conservative selectors - only definite ad patterns
            const adSelectors = [
                // Definite ad containers
                '.ad-container', '.ad-wrapper', '.ad-slot', '.ad-unit',
                '.ad-banner', '.ad-box', '.ad-placeholder',
                '.adsbygoogle', '.ads-container', '.ad-leaderboard',
                '.banner-ad', '.sidebar-ad',
                
                // Banner ad patterns
                '[class*="banner-ad"]', '[class*="ad-banner"]', '[id*="banner-ad"]',
                '[class*="leaderboard"]', '[class*="top-banner"]', '[class*="header-ad"]',
                '[class*="rectangle-ad"]', '[class*="skyscraper"]',
                
                // Google/Network ads
                'ins.adsbygoogle', '[data-ad-slot]', '[data-google-query-id]',
                '[id*="div-gpt-ad"]', '[class*="gpt-ad"]',
                
                // WordPress ad plugins
                '.wp-ad', '.wpa', '.adrotate', '.advanced-ads',
                
                // Specific networks
                '.taboola', '.OUTBRAIN', '.outbrain', '#taboola-below',
                
                // Cookie banners
                '.cc-banner', '.cookie-banner', '.cookie-notice',
                '#onetrust-banner-sdk'
            ];
            
            let hiddenCount = 0;
            
            function hideAds() {
                adSelectors.forEach(selector => {
                    try {
                        document.querySelectorAll(selector).forEach(el => {
                            if (el.style.display !== 'none') {
                                el.style.display = 'none';
                                el.style.visibility = 'hidden';
                                el.style.height = '0';
                                el.style.overflow = 'hidden';
                                hiddenCount++;
                            }
                        });
                    } catch(e) {}
                });
                
                // Hide iframes from ad networks
                document.querySelectorAll('iframe').forEach(iframe => {
                    const src = iframe.src || '';
                    if (src.includes('doubleclick') || src.includes('googlesyndication') ||
                        src.includes('amazon-adsystem') || src.includes('taboola') || 
                        src.includes('outbrain') || src.includes('ad.') ||
                        src.includes('/ads/') || src.includes('adserver')) {
                        if (iframe.style.display !== 'none') {
                            iframe.style.display = 'none';
                            hiddenCount++;
                        }
                    }
                });
                
                // Hide banner-sized images (common ad dimensions)
                // Standard IAB ad sizes: 728x90, 300x250, 336x280, 160x600, 320x50, 468x60
                document.querySelectorAll('img').forEach(img => {
                    const w = img.naturalWidth || img.width;
                    const h = img.naturalHeight || img.height;
                    const src = (img.src || '').toLowerCase();
                    
                    // Check for banner dimensions
                    const isBannerSize = (
                        (w === 728 && h === 90) ||   // Leaderboard
                        (w === 300 && h === 250) ||  // Medium Rectangle
                        (w === 336 && h === 280) ||  // Large Rectangle
                        (w === 160 && h === 600) ||  // Wide Skyscraper
                        (w === 320 && h === 50) ||   // Mobile Leaderboard
                        (w === 468 && h === 60) ||   // Full Banner
                        (w === 970 && h === 90) ||   // Large Leaderboard
                        (w === 970 && h === 250) ||  // Billboard
                        (w === 300 && h === 600) ||  // Half Page
                        (w >= 700 && h >= 80 && h <= 100 && w/h > 6) // Wide banners
                    );
                    
                    // Check for ad keywords in image source
                    const hasAdKeyword = (
                        src.includes('banner') || src.includes('/ad/') ||
                        src.includes('/ads/') || src.includes('advert') ||
                        src.includes('sponsor') || src.includes('promo') ||
                        src.includes('affiliate') || src.includes('click.')
                    );
                    
                    if (isBannerSize || hasAdKeyword) {
                        // Also check parent - if it's a link, hide the link
                        const parent = img.closest('a') || img.parentElement;
                        if (parent && parent.style.display !== 'none') {
                            parent.style.display = 'none';
                            hiddenCount++;
                        } else if (img.style.display !== 'none') {
                            img.style.display = 'none';
                            hiddenCount++;
                        }
                    }
                });
                
                // Hide links with affiliate/tracking patterns containing images
                document.querySelectorAll('a').forEach(link => {
                    const href = (link.href || '').toLowerCase();
                    const hasImage = link.querySelector('img');
                    
                    if (hasImage && link.style.display !== 'none') {
                        // Common affiliate/ad link patterns
                        const isAdLink = (
                            href.includes('doubleclick') ||
                            href.includes('googlesyndication') ||
                            href.includes('googleadservices') ||
                            href.includes('/aclk') ||
                            href.includes('pagead') ||
                            href.includes('amazon-adsystem') ||
                            href.includes('affiliate') ||
                            href.includes('shareasale') ||
                            href.includes('awin1.com') ||
                            href.includes('prf.hn') ||
                            href.includes('anrdoezrs') ||
                            href.includes('tkqlhce') ||
                            href.includes('jdoqocy') ||
                            href.includes('dpbolvw') ||
                            href.includes('kqzyfj') ||
                            href.includes('commission') ||
                            href.includes('partnerize') ||
                            href.includes('impact.com') ||
                            (href.includes('click') && href.includes('track'))
                        );
                        
                        if (isAdLink) {
                            link.style.display = 'none';
                            hiddenCount++;
                        }
                    }
                });
                
                if (hiddenCount > 0) {
                    console.log('[Tux] Hidden ' + hiddenCount + ' ad elements');
                }
            }
            
            // Run immediately and after delays for lazy content
            hideAds();
            setTimeout(hideAds, 1000);
            setTimeout(hideAds, 3000);
            
            // Observe DOM for new ads
            const observer = new MutationObserver(function() {
                setTimeout(hideAds, 100);
            });
            if (document.body) {
                observer.observe(document.body, { childList: true, subtree: true });
            }
        })();
        """
        try:
            # Try newer API first, fall back to older
            if hasattr(webview, 'evaluate_javascript'):
                webview.evaluate_javascript(js_code, -1, None, None, None, None, None)
            elif hasattr(webview, 'run_javascript'):
                webview.run_javascript(js_code, None, None, None)
            
            # Update pages protected count
            self.pages_protected += 1
            self._update_blocked_count()
        except Exception as e:
            print(f"JS injection failed: {e}")
    
    def _inject_sponsorblock_monitor(self, webview):
        """Inject self-contained SponsorBlock monitor for YouTube."""
        
        categories = self.sponsorblock_categories
        
        js_code = f"""
        (function() {{
            // Prevent multiple injections
            if (window._tuxSponsorBlockMonitor) {{
                console.log('[Tux SponsorBlock] Already running');
                return;
            }}
            window._tuxSponsorBlockMonitor = true;
            
            console.log('[Tux SponsorBlock] Monitor script starting...');
            
            // ============================================
            // YOUTUBE AD AUTO-SKIP (based on community research)
            // ============================================
            let adSkipAttempts = 0;
            let wasInAd = false;
            
            function isAdPlaying() {{
                return document.querySelector('.ad-showing') !== null ||
                       document.querySelector('.ad-interrupting') !== null ||
                       document.querySelector('.ytp-ad-player-overlay') !== null;
            }}
            
            function trySkipAd() {{
                // Skip button selectors (YouTube changes these - updated Dec 2024)
                const skipSelectors = [
                    '.ytp-skip-ad-button',
                    '.ytp-ad-skip-button', 
                    '.ytp-ad-skip-button-modern',
                    '.ytp-ad-skip-button-text',
                    'button.ytp-ad-skip-button',
                    '.ytp-ad-skip-button-slot button',
                    '.videoAdUiSkipButton',
                    'button[aria-label^="Skip ad"]',
                    'button[aria-label^="Skip Ad"]'
                ];
                
                for (const selector of skipSelectors) {{
                    const skipBtn = document.querySelector(selector);
                    if (skipBtn && skipBtn.offsetParent !== null) {{
                        console.log('[Tux AdSkip] Found skip button: ' + selector);
                        skipBtn.click();
                        
                        return true;
                    }}
                }}
                return false;
            }}
            
            function trySeekPastAd() {{
                // For unskippable ads - seek to end
                const video = document.querySelector('video');
                if (video && isAdPlaying() && video.duration && isFinite(video.duration)) {{
                    // Only for short ads (< 2 minutes)
                    if (video.duration < 120) {{
                        try {{
                            // Seek to just before end (0.1 seconds)
                            video.currentTime = video.duration - 0.1;
                            console.log('[Tux AdSkip] Seeked to end of ad');
                            return true;
                        }} catch(e) {{
                            console.log('[Tux AdSkip] Seek failed: ' + e);
                        }}
                    }}
                }}
                return false;
            }}
            
            function closeOverlayAds() {{
                // Close overlay/banner ads
                const closeSelectors = [
                    '.ytp-ad-overlay-close-button',
                    '.ytp-ad-overlay-close-container',
                    '[class*="ad-overlay-close"]'
                ];
                
                closeSelectors.forEach(selector => {{
                    const btn = document.querySelector(selector);
                    if (btn && btn.offsetParent !== null) {{
                        try {{ 
                            btn.click(); 
                            console.log('[Tux AdSkip] Closed overlay ad');
                        }} catch(e) {{}}
                    }}
                }});
            }}
            
            function handleAds() {{
                const inAd = isAdPlaying();
                
                if (inAd) {{
                    adSkipAttempts++;
                    
                    if (adSkipAttempts <= 3) {{
                    }}
                    
                    // Try methods in order:
                    // 1. Click skip button (if available)
                    if (!trySkipAd()) {{
                        // 2. Try seeking to end (for unskippable)
                        if (adSkipAttempts > 2) {{
                            trySeekPastAd();
                        }}
                    }}
                    
                    // 3. Always try to close overlays
                    closeOverlayAds();
                    
                    wasInAd = true;
                }} else {{
                    if (wasInAd) {{
                        console.log('[Tux AdSkip] Ad finished');
                        wasInAd = false;
                    }}
                    adSkipAttempts = 0;
                }}
            }}
            
            // Check for ads frequently (every 300ms)
            setInterval(handleAds, 300);
            
            // Also use MutationObserver for instant detection
            const adObserver = new MutationObserver(handleAds);
            const player = document.querySelector('#movie_player');
            if (player) {{
                adObserver.observe(player, {{ 
                    attributes: true, 
                    attributeFilter: ['class'],
                    subtree: true 
                }});
            }}
            
            // ============================================
            // SPONSORBLOCK (in-video sponsor skipping)
            // ============================================
            const CATEGORIES = '{categories}'.split(',').map(c => c.trim());
            let currentVideoId = null;
            let segments = [];
            let skippedSegments = new Set();
            let videoElement = null;
            let lastUrl = location.href;
            
            function isWatchPage() {{
                return location.href.includes('/watch') || location.href.includes('youtu.be/');
            }}
            
            function getVideoId() {{
                if (!isWatchPage()) return null;
                
                const urlMatch = location.href.match(/[?&]v=([a-zA-Z0-9_-]{{11}})/);
                if (urlMatch) return urlMatch[1];
                
                const shortMatch = location.href.match(/youtu\\.be\\/([a-zA-Z0-9_-]{{11}})/);
                if (shortMatch) return shortMatch[1];
                
                const shortsMatch = location.href.match(/\\/shorts\\/([a-zA-Z0-9_-]{{11}})/);
                if (shortsMatch) return shortsMatch[1];
                
                return null;
            }}
            
            async function fetchSegments(videoId) {{
                const categoryParams = CATEGORIES.map(c => 'category=' + c).join('&');
                const url = 'https://sponsor.ajay.app/api/skipSegments?videoID=' + videoId + '&' + categoryParams;
                
                
                try {{
                    const response = await fetch(url);
                    if (response.status === 404) {{
                        return [];
                    }}
                    if (!response.ok) {{
                        return [];
                    }}
                    const data = await response.json();
                    return data;
                }} catch (e) {{
                    return [];
                }}
            }}
            
            function formatTime(seconds) {{
                const mins = Math.floor(seconds / 60);
                const secs = Math.floor(seconds % 60);
                return mins + ':' + secs.toString().padStart(2, '0');
            }}
            
            function showSkipNotification(category, duration) {{
                let notification = document.getElementById('tux-sponsorblock-notification');
                if (!notification) {{
                    notification = document.createElement('div');
                    notification.id = 'tux-sponsorblock-notification';
                    notification.style.cssText = `
                        position: fixed;
                        bottom: 80px;
                        right: 20px;
                        background: rgba(0, 0, 0, 0.9);
                        color: #00d400;
                        padding: 12px 20px;
                        border-radius: 8px;
                        font-family: -apple-system, BlinkMacSystemFont, 'Roboto', sans-serif;
                        font-size: 14px;
                        font-weight: 500;
                        z-index: 999999;
                        transition: opacity 0.3s;
                    `;
                    document.body.appendChild(notification);
                }}
                
                const names = {{
                    'sponsor': 'Sponsor',
                    'selfpromo': 'Self-Promo', 
                    'interaction': 'Interaction',
                    'intro': 'Intro',
                    'outro': 'Outro',
                    'preview': 'Preview',
                    'filler': 'Filler'
                }};
                
                notification.textContent = '🛡️ Skipped ' + (names[category] || category) + ' (' + Math.round(duration) + 's)';
                notification.style.opacity = '1';
                
                setTimeout(() => {{ notification.style.opacity = '0'; }}, 3000);
            }}
            
            function checkAndSkip() {{
                // Don't skip during YouTube ads
                if (isAdPlaying()) return;
                if (!videoElement || !segments.length) return;
                
                const currentTime = videoElement.currentTime;
                
                // Log position every 10 seconds
                const timeKey = Math.floor(currentTime / 10);
                if (timeKey !== window._sbLastTimeKey && segments.length > 0) {{
                    window._sbLastTimeKey = timeKey;
                    const seg = segments[0];
                }}
                
                for (const segment of segments) {{
                    const start = segment.segment[0];
                    const end = segment.segment[1];
                    const uuid = segment.UUID;
                    
                    if (currentTime >= start && currentTime < end - 0.5) {{
                        if (!skippedSegments.has(uuid)) {{
                            console.log('[Tux SponsorBlock] SKIPPING ' + segment.category + ' from ' + formatTime(start) + ' to ' + formatTime(end));
                            videoElement.currentTime = end;
                            skippedSegments.add(uuid);
                            showSkipNotification(segment.category, end - start);
                            return;
                        }}
                    }}
                }}
            }}
            
            async function checkForVideo() {{
                if (!isWatchPage()) {{
                    return;
                }}
                
                const videoId = getVideoId();
                if (!videoId) {{
                    return;
                }}
                
                const video = document.querySelector('#movie_player video') || 
                              document.querySelector('video.html5-main-video') ||
                              document.querySelector('video');
                
                if (video && video !== videoElement) {{
                    console.log('[Tux SponsorBlock] Found video element');
                    videoElement = video;
                    video.addEventListener('timeupdate', checkAndSkip);
                }}
                
                if (videoId && videoId !== currentVideoId) {{
                    console.log('[Tux SponsorBlock] New video: ' + videoId);
                    currentVideoId = videoId;
                    skippedSegments.clear();
                    window._sbLastTimeKey = -1;
                    
                    segments = await fetchSegments(videoId);
                    
                    if (segments.length > 0) {{
                        let info = '';
                        segments.forEach(s => {{
                            info += s.category + ' ' + formatTime(s.segment[0]) + '-' + formatTime(s.segment[1]) + ' ';
                        }});
                    }}
                }}
            }}
            
            function checkNavigation() {{
                if (location.href !== lastUrl) {{
                    console.log('[Tux SponsorBlock] Navigation detected');
                    lastUrl = location.href;
                    currentVideoId = null;
                    videoElement = null;
                    skippedSegments.clear();
                    setTimeout(checkForVideo, 300);
                }}
            }}
            
            setInterval(checkForVideo, 2000);
            setInterval(checkNavigation, 500);
            setTimeout(checkForVideo, 1000);
            
            document.addEventListener('yt-navigate-finish', () => {{
                console.log('[Tux SponsorBlock] yt-navigate-finish event');
                currentVideoId = null;
                videoElement = null;
                setTimeout(checkForVideo, 500);
            }});
            
            new MutationObserver(checkNavigation).observe(document.body, {{
                childList: true, 
                subtree: true
            }});
            
        }})();
        """
        
        try:
            if hasattr(webview, 'evaluate_javascript'):
                webview.evaluate_javascript(js_code, -1, None, None, None, None, None)
            elif hasattr(webview, 'run_javascript'):
                webview.run_javascript(js_code, None, None, None)
            print("[SponsorBlock] Monitor script injected")
        except Exception as e:
            print(f"[SponsorBlock] Injection failed: {e}")
    
    def _on_browser_create_window(self, webview, navigation_action):
        """Handle links that try to open new windows - open in default browser."""
        request = navigation_action.get_request()
        uri = request.get_uri()
        
        if uri:
            try:
                import subprocess
                subprocess.Popen(['xdg-open', uri])
            except Exception as e:
                print(f"Failed to open link: {e}")
        
        return None  # Don't create new window in webview
    
    def _on_browser_download_started(self, session_or_context, download):
        """Handle download from browser."""
        download.connect('decide-destination', self._on_browser_download_decide_destination)
        download.connect('finished', self._on_browser_download_finished)
        download.connect('failed', self._on_browser_download_failed)
        download.connect('received-data', self._on_browser_download_progress)
        
        # Track this download
        download_info = {
            'download': download,
            'destination': None,
            'filename': 'Downloading...',
            'progress': 0.0,
            'status': 'downloading'
        }
        self.downloads.insert(0, download_info)  # Add to front
        self._update_downloads_ui()
    
    def _on_browser_download_decide_destination(self, download, suggested_filename):
        """Decide where to save browser download."""
        downloads_dir = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
        if not downloads_dir:
            downloads_dir = os.path.expanduser("~/Downloads")
        
        filename = suggested_filename if suggested_filename else "download"
        filename = "".join(c for c in filename if c.isalnum() or c in '._- ()')
        if not filename:
            filename = "download"
        
        destination = os.path.join(downloads_dir, filename)
        
        base, ext = os.path.splitext(destination)
        counter = 1
        while os.path.exists(destination):
            destination = f"{base}_{counter}{ext}"
            counter += 1
        
        download.set_destination(destination)
        
        # Update tracking info
        for d in self.downloads:
            if d['download'] == download:
                d['destination'] = destination
                d['filename'] = os.path.basename(destination)
                break
        self._update_downloads_ui()
        
        self.show_toast(f"Downloading: {os.path.basename(destination)}")
        return True
    
    def _on_browser_download_finished(self, download):
        """Handle browser download completion."""
        destination = download.get_destination()
        filename = os.path.basename(destination) if destination else "file"
        
        # Update tracking info
        for d in self.downloads:
            if d['download'] == download:
                d['status'] = 'completed'
                d['progress'] = 1.0
                break
        self._update_downloads_ui()
        
        self.show_toast(f"Downloaded: {filename}")
    
    def _on_browser_download_failed(self, download, error):
        """Handle browser download failure."""
        # Update tracking info
        for d in self.downloads:
            if d['download'] == download:
                d['status'] = 'failed'
                break
        self._update_downloads_ui()
        
        self.show_toast("Download failed")
    
    def _on_browser_download_progress(self, download, data_length):
        """Handle download progress update."""
        try:
            response = download.get_response()
            if response:
                total = response.get_content_length()
                received = download.get_received_data_length()
                if total > 0:
                    progress = received / total
                    for d in self.downloads:
                        if d['download'] == download:
                            d['progress'] = progress
                            break
                    # Don't update UI on every chunk - too slow
                    # UI updates on finish/fail
        except:
            pass
    
    def _update_downloads_ui(self):
        """Update the downloads list UI."""
        if not hasattr(self, 'downloads_list_box'):
            return
        
        # Clear existing items
        while True:
            child = self.downloads_list_box.get_first_child()
            if child:
                self.downloads_list_box.remove(child)
            else:
                break
        
        if not self.downloads:
            # Show empty state
            empty_label = Gtk.Label(label="No downloads yet")
            empty_label.add_css_class("dim-label")
            empty_label.set_margin_top(20)
            empty_label.set_margin_bottom(20)
            self.downloads_list_box.append(empty_label)
            return
        
        # Add download items
        for d in self.downloads[:20]:  # Show max 20
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
            row.set_margin_top(8)
            row.set_margin_bottom(8)
            row.set_margin_start(8)
            row.set_margin_end(8)
            
            # Icon based on status
            if d['status'] == 'completed':
                icon = Gtk.Image.new_from_icon_name("tux-emblem-ok-symbolic")
                icon.add_css_class("success")
            elif d['status'] == 'failed':
                icon = Gtk.Image.new_from_icon_name("tux-dialog-error-symbolic")
                icon.add_css_class("error")
            else:
                icon = Gtk.Image.new_from_icon_name("tux-folder-download-symbolic")
            row.append(icon)
            
            # Filename and status
            info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2)
            info_box.set_hexpand(True)
            
            filename_label = Gtk.Label(label=d['filename'])
            filename_label.set_xalign(0)
            filename_label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
            filename_label.set_max_width_chars(35)
            info_box.append(filename_label)
            
            if d['status'] == 'downloading':
                progress_bar = Gtk.ProgressBar()
                progress_bar.set_fraction(d['progress'])
                info_box.append(progress_bar)
            elif d['status'] == 'failed':
                status_label = Gtk.Label(label="Failed")
                status_label.set_xalign(0)
                status_label.add_css_class("dim-label")
                status_label.add_css_class("error")
                info_box.append(status_label)
            
            row.append(info_box)
            
            # Open file button (only for completed)
            if d['status'] == 'completed' and d['destination']:
                # Open containing folder button
                folder_btn = Gtk.Button.new_from_icon_name("tux-folder-symbolic")
                folder_btn.set_tooltip_text("Open containing folder")
                folder_btn.add_css_class("flat")
                dest = d['destination']
                folder_btn.connect("clicked", lambda b, f=dest: self._open_containing_folder(f))
                row.append(folder_btn)
                
                # Open file button
                open_btn = Gtk.Button.new_from_icon_name("tux-media-playback-start-symbolic")
                open_btn.set_tooltip_text("Open file")
                open_btn.add_css_class("flat")
                open_btn.connect("clicked", lambda b, f=dest: self._open_file(f))
                row.append(open_btn)
            
            self.downloads_list_box.append(row)
    
    def _open_downloads_folder(self, button=None):
        """Open the downloads folder in file manager."""
        downloads_dir = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
        if not downloads_dir:
            downloads_dir = os.path.expanduser("~/Downloads")
        
        import subprocess
        subprocess.Popen(["xdg-open", downloads_dir])
    
    def _open_file(self, filepath):
        """Open a file with default application."""
        try:
            Gtk.FileLauncher.new(Gio.File.new_for_path(filepath)).launch(self, None, None, None)
        except:
            import subprocess
            subprocess.Popen(["xdg-open", filepath])
    
    def _open_containing_folder(self, filepath):
        """Open the folder containing a file."""
        import subprocess
        folder = os.path.dirname(filepath)
        subprocess.Popen(["xdg-open", folder])
    
    def _clear_completed_downloads(self, button=None):
        """Clear completed and failed downloads from list."""
        self.downloads = [d for d in self.downloads if d['status'] == 'downloading']
        self._update_downloads_ui()
    
    def _on_claude_download_started(self, session_or_context, download):
        """Handle download requests from Claude webview."""
        download.connect('decide-destination', self._on_claude_download_decide_destination)
        download.connect('finished', self._on_claude_download_finished)
        download.connect('failed', self._on_claude_download_failed)
    
    def _on_claude_download_decide_destination(self, download, suggested_filename):
        """Decide where to save Claude download."""
        downloads_dir = GLib.get_user_special_dir(GLib.UserDirectory.DIRECTORY_DOWNLOAD)
        if not downloads_dir:
            downloads_dir = os.path.expanduser("~/Downloads")
        
        filename = None
        
        if suggested_filename and suggested_filename.strip():
            clean_name = suggested_filename.strip()
            if clean_name.lower() not in ('download', 'download file', 'file', 'blob'):
                filename = clean_name
        
        if not filename:
            try:
                response = download.get_response()
                if response:
                    resp_filename = response.get_suggested_filename()
                    if resp_filename and resp_filename.strip():
                        clean_name = resp_filename.strip()
                        if clean_name.lower() not in ('download', 'download file', 'file', 'blob'):
                            filename = clean_name
            except:
                pass
        
        if not filename:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = ""
            try:
                response = download.get_response()
                if response:
                    mime_type = response.get_mime_type()
                    if mime_type:
                        mime_to_ext = {
                            'application/zip': '.zip',
                            'text/plain': '.txt',
                            'text/html': '.html',
                            'application/json': '.json',
                            'text/markdown': '.md',
                            'application/pdf': '.pdf',
                            'image/png': '.png',
                            'text/x-python': '.py',
                        }
                        ext = mime_to_ext.get(mime_type, '')
            except:
                pass
            filename = f"claude_download_{timestamp}{ext}"
        
        filename = "".join(c for c in filename if c.isalnum() or c in '._- ()')
        if not filename:
            filename = "download"
        
        destination = os.path.join(downloads_dir, filename)
        
        base, ext = os.path.splitext(destination)
        counter = 1
        while os.path.exists(destination):
            destination = f"{base}_{counter}{ext}"
            counter += 1
        
        download.set_destination(destination)
        self.show_toast(f"Downloading: {os.path.basename(destination)}")
        return True
    
    def _on_claude_download_finished(self, download):
        """Handle Claude download completion."""
        destination = download.get_destination()
        filename = os.path.basename(destination) if destination else "file"
        self.show_toast(f"Downloaded: {filename}")
    
    def _on_claude_download_failed(self, download, error):
        """Handle Claude download failure."""
        self.show_toast("Download failed")
    
    def _on_install_to_system(self, button):
        """Handle Install to System button click."""
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Install Tux Assistant",
            body=(
                "This will install Tux Assistant to your system:\n\n"
                "• Application files → /opt/tux-assistant/\n"
                "• Desktop shortcut → Applications menu\n\n"
                "You'll need to enter your administrator password."
            )
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("install", "Install")
        dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("install")
        dialog.set_close_response("cancel")
        
        dialog.connect("response", self._on_install_response)
        dialog.present()
    
    def _on_install_response(self, dialog, response):
        """Handle install dialog response."""
        if response != "install":
            return
        
        import os
        import subprocess
        
        # Get the source directory (where we're running from)
        run_file = os.environ.get('TUX_ASSISTANT_RUN_FILE', '')
        
        if not run_file or not os.path.exists(run_file):
            self.show_toast("Could not locate installation source")
            return
        
        # Create install script
        install_script = f'''#!/bin/bash
set -e

# Create destination directory
mkdir -p /opt/tux-assistant

# Extract the .run file to get fresh copy
TEMP_DIR=$(mktemp -d)
PAYLOAD_LINE=$(awk '/^__PAYLOAD_BELOW__$/{{print NR + 1; exit 0;}}' "{run_file}")
tail -n +$PAYLOAD_LINE "{run_file}" | tar -xzf - -C "$TEMP_DIR"

# Copy files
cp -r "$TEMP_DIR/tux-assistant/"* /opt/tux-assistant/

# Clean up
rm -rf "$TEMP_DIR"

# Install tux-helper for privileged operations
cp /opt/tux-assistant/tux-helper /usr/bin/tux-helper
chmod +x /usr/bin/tux-helper

# Install icons to standard location for GNOME compatibility
mkdir -p /usr/share/icons/hicolor/scalable/apps
cp /opt/tux-assistant/assets/icon.svg /usr/share/icons/hicolor/scalable/apps/tux-assistant.svg
cp /opt/tux-assistant/assets/tux-tunes.svg /usr/share/icons/hicolor/scalable/apps/tux-tunes.svg

# Create Tux Assistant desktop file
cat > /usr/share/applications/com.tuxassistant.app.desktop << 'EOF'
[Desktop Entry]
Version=1.1
Type=Application
Name=Tux Assistant
GenericName=System Setup Tool
Comment=Linux system configuration tool
Exec=/usr/bin/python3 /opt/tux-assistant/tux-assistant.py
Icon=tux-assistant
Terminal=false
Categories=System;Settings;Utility;
Keywords=setup;install;configure;linux;
StartupNotify=true
StartupWMClass=com.tuxassistant.app
EOF

# Create Tux Tunes desktop file
cat > /usr/share/applications/com.tuxassistant.tuxtunes.desktop << 'EOF'
[Desktop Entry]
Version=1.1
Type=Application
Name=Tux Tunes
GenericName=Internet Radio
Comment=Listen to internet radio stations with smart recording
Exec=/usr/bin/python3 /opt/tux-assistant/tux/apps/tux_tunes/tux-tunes.py
Icon=tux-tunes
Terminal=false
Categories=Audio;Music;Player;
Keywords=radio;internet;streaming;music;recording;
StartupNotify=true
StartupWMClass=com.tuxassistant.tuxtunes
EOF

# Remove old desktop files if exist
rm -f /usr/share/applications/tux-assistant.desktop 2>/dev/null || true
rm -f /usr/share/applications/tux-tunes.desktop 2>/dev/null || true

# Update icon cache and desktop database
gtk-update-icon-cache /usr/share/icons/hicolor/ 2>/dev/null || true
update-desktop-database /usr/share/applications/ 2>/dev/null || true

# Create symlink for easy CLI access
ln -sf /opt/tux-assistant/tux-assistant.py /usr/local/bin/tux-assistant 2>/dev/null || true

echo "Installation complete!"
'''
        
        # Write script to temp file
        script_path = '/tmp/tux-install.sh'
        with open(script_path, 'w') as f:
            f.write(install_script)
        os.chmod(script_path, 0o755)
        
        # Run with pkexec
        try:
            result = subprocess.run(
                ['pkexec', 'bash', script_path],
                capture_output=True, text=True, timeout=60
            )
            
            if result.returncode == 0:
                success_dialog = Adw.MessageDialog(
                    transient_for=self,
                    heading="Installation Complete! 🎉",
                    body=(
                        "Tux Assistant has been installed successfully!\n\n"
                        "You can now find it in your applications menu.\n\n"
                        "You may close this portable instance."
                    )
                )
                success_dialog.add_response("ok", "OK")
                success_dialog.present()
            else:
                self.show_toast(f"Installation failed: {result.stderr[:100]}")
        except subprocess.TimeoutExpired:
            self.show_toast("Installation timed out")
        except Exception as e:
            self.show_toast(f"Installation error: {str(e)[:50]}")
        finally:
            # Clean up script
            if os.path.exists(script_path):
                os.remove(script_path)
    
    def create_menu(self) -> Gio.Menu:
        """Create the application menu."""
        menu = Gio.Menu()
        menu.append("About Tux Assistant", "app.about")
        menu.append("Quit", "app.quit")
        return menu
    
    def _show_getting_started(self, button):
        """Show the Getting Started guide dialog."""
        dialog = Adw.Dialog()
        dialog.set_title("Getting Started")
        dialog.set_content_width(550)
        dialog.set_content_height(500)
        
        toolbar_view = Adw.ToolbarView()
        dialog.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        
        close_btn = Gtk.Button(label="Got it!")
        close_btn.add_css_class("suggested-action")
        close_btn.connect("clicked", lambda b: dialog.close())
        header.pack_end(close_btn)
        
        toolbar_view.add_top_bar(header)
        
        # Scrollable content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        toolbar_view.set_content(scrolled)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_top(20)
        content.set_margin_bottom(20)
        content.set_margin_start(20)
        content.set_margin_end(20)
        scrolled.set_child(content)
        
        # Welcome
        welcome = Gtk.Label()
        welcome.set_markup(
            "<b>Welcome to Tux Assistant</b>\n\n"
            "A system configuration tool that handles the terminal stuff for you."
        )
        welcome.set_halign(Gtk.Align.START)
        welcome.set_wrap(True)
        content.append(welcome)
        
        # Main sections
        sections = Gtk.Label()
        sections.set_markup(
            "<b>Main Sections</b>\n\n"
            
            "<b>System Information</b>\n"
            "Shows your distro, desktop, and hardware. "
            "Install hardinfo2 for detailed specs.\n\n"
            
            "<b>Setup Tools</b>\n"
            "First-time setup: codecs, drivers, common apps. "
            "Start here if you just installed Linux.\n\n"
            
            "<b>Software Center</b>\n"
            "Install apps by category. Browsers, editors, games, etc.\n\n"
            
            "<b>Developer Tools</b>\n"
            "Git management with push/pull buttons. SSH key setup. "
            "Click 'How to Update' for the full workflow guide.\n\n"
            
            "<b>Networking</b>\n"
            "File sharing, Samba, network discovery, Active Directory.\n\n"
            
            "<b>Server and Cloud</b>\n"
            "Set up Nextcloud or media servers (Plex, Jellyfin, Emby).\n\n"
            
            "<b>Tux Tunes</b>\n"
            "Internet radio player with smart song recording."
        )
        sections.set_halign(Gtk.Align.START)
        sections.set_wrap(True)
        content.append(sections)
        
        # How it works
        how = Gtk.Label()
        how.set_markup(
            "<b>How Things Work</b>\n\n"
            "• Click rows to expand or see options\n"
            "• Buttons perform actions\n"
            "• Toast notifications show status at the bottom\n"
            "• Terminal windows open when you need to enter passwords\n\n"
            "You always see what's happening. No hidden magic."
        )
        how.set_halign(Gtk.Align.START)
        how.set_wrap(True)
        content.append(how)
        
        # Docs link
        docs = Gtk.Label()
        docs.set_markup(
            "<b>Full Documentation</b>\n\n"
            "Check the <tt>docs/</tt> folder in the project, or visit:\n"
            "https://github.com/dorrellkc/tux-assistant"
        )
        docs.set_halign(Gtk.Align.START)
        docs.set_wrap(True)
        content.append(docs)
        
        dialog.present(self)
    
    def create_main_page(self) -> Adw.NavigationPage:
        """Create the main navigation page with dynamically discovered modules."""
        
        page = Adw.NavigationPage(title="Tux Assistant")
        
        # Main horizontal layout: modules on left, sidebar on right
        main_hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        page.set_child(main_hbox)
        
        # LEFT SIDE: Scrollable modules list
        left_scrolled = Gtk.ScrolledWindow()
        left_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        left_scrolled.set_vexpand(True)
        left_scrolled.set_hexpand(True)
        main_hbox.append(left_scrolled)
        
        # Content box with clamp for max width
        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_margin_top(24)
        clamp.set_margin_bottom(24)
        clamp.set_margin_start(24)
        clamp.set_margin_end(24)
        left_scrolled.set_child(clamp)
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        clamp.set_child(content_box)
        
        # Search bar (at the top)
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        search_box.set_margin_top(8)
        search_box.set_margin_bottom(8)
        
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search Tux Assistant...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect("activate", self._on_search_activated)
        self.search_entry.connect("search-changed", self._on_search_changed)
        search_box.append(self.search_entry)
        
        content_box.append(search_box)
        
        # System info banner (compact version for left side)
        info_banner = self.create_system_info_banner()
        content_box.append(info_banner)
        
        # Search results container (hidden by default)
        self.search_results_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.search_results_box.set_visible(False)
        content_box.append(self.search_results_box)
        
        # Module content box (will be hidden during search)
        self.modules_content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content_box.append(self.modules_content_box)
        
        # Dynamically create module groups based on registered modules
        for category in ModuleRegistry.get_categories():
            modules = ModuleRegistry.get_modules_by_category(category)
            
            if modules:
                group = self.create_module_group_from_registry(category.value, modules)
                self.modules_content_box.append(group)
        
        # "I'm Done" section at the bottom
        done_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        done_box.set_margin_top(30)
        done_box.set_halign(Gtk.Align.CENTER)
        content_box.append(done_box)
        
        # Separator
        separator = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        separator.set_margin_bottom(10)
        done_box.append(separator)
        
        # Done button
        done_btn = Gtk.Button(label="✈️  I'm Done!")
        done_btn.add_css_class("pill")
        done_btn.add_css_class("suggested-action")
        done_btn.connect("clicked", self.on_done_clicked)
        done_box.append(done_btn)
        
        # Subtle hint text
        hint_label = Gtk.Label()
        hint_label.set_markup("<small>Click when you're finished to close the toolkit</small>")
        hint_label.add_css_class("dim-label")
        done_box.append(hint_label)
        
        # SIDEBAR DISABLED - Tux Tunes moved to header bar
        # Keeping code for potential future use
        """
        # RIGHT SIDE: Sidebar with Tux Tunes launcher
        sidebar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        sidebar_box.set_size_request(300, -1)  # Fixed width
        sidebar_box.add_css_class("tux-sidebar")
        main_hbox.append(sidebar_box)
        
        # TOP: Tux Tunes launcher button
        tux_tunes_btn = Gtk.Button()
        tux_tunes_btn.add_css_class("tux-tunes-sidebar-btn")
        tux_tunes_btn.set_margin_top(12)
        tux_tunes_btn.set_margin_start(12)
        tux_tunes_btn.set_margin_end(12)
        tux_tunes_btn.connect("clicked", self._on_tux_tunes_clicked)
        
        # Button content
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        btn_box.set_halign(Gtk.Align.CENTER)
        tux_tunes_btn.set_child(btn_box)
        
        btn_icon = Gtk.Label(label="🎵")
        btn_icon.add_css_class("tux-tunes-icon")
        btn_box.append(btn_icon)
        
        btn_label_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        btn_box.append(btn_label_box)
        
        btn_title = Gtk.Label(label="Tux Tunes")
        btn_title.add_css_class("tux-tunes-title")
        btn_title.set_halign(Gtk.Align.START)
        btn_label_box.append(btn_title)
        
        btn_subtitle = Gtk.Label(label="Internet radio & recording")
        btn_subtitle.add_css_class("dim-label")
        btn_subtitle.add_css_class("tux-tunes-subtitle")
        btn_subtitle.set_halign(Gtk.Align.START)
        btn_label_box.append(btn_subtitle)
        
        sidebar_box.append(tux_tunes_btn)
        
        # Separator between fixed and scrollable
        sidebar_sep = Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL)
        sidebar_sep.add_css_class("sidebar-separator")
        sidebar_box.append(sidebar_sep)
        
        # BOTTOM: Scrollable area for future modules
        sidebar_scrolled = Gtk.ScrolledWindow()
        sidebar_scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sidebar_scrolled.set_vexpand(True)
        sidebar_scrolled.add_css_class("tux-sidebar-scrollable")
        sidebar_box.append(sidebar_scrolled)
        
        # Container for future sidebar widgets
        self.sidebar_content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.sidebar_content.set_margin_top(12)
        self.sidebar_content.set_margin_bottom(12)
        self.sidebar_content.set_margin_start(12)
        self.sidebar_content.set_margin_end(12)
        sidebar_scrolled.set_child(self.sidebar_content)
        
        # Placeholder text for now
        placeholder = Gtk.Label()
        placeholder.set_markup("<small><i>More widgets coming soon...</i></small>")
        placeholder.add_css_class("dim-label")
        placeholder.set_valign(Gtk.Align.START)
        self.sidebar_content.append(placeholder)
        
        # Store reference to hide on small windows
        self.tux_fetch_panel = sidebar_box
        
        # Connect to window size changes to show/hide panel
        self.connect("notify::default-width", self._on_width_changed_for_panel)
        """
        
        return page
    
    def on_done_clicked(self, button):
        """Show goodbye dialog and close the app."""
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading="Thanks for Flying with Tux Assistant! ✈️",
            body=(
                "Thank you for using the Tux Assistant.\n\n"
                "Please return your tray tables to the upright position.\n\n"
                "We hope it has been beneficial and you enjoyed the ride!"
            )
        )
        dialog.add_response("stay", "Wait, Go Back")
        dialog.add_response("exit", "Exit")
        dialog.set_response_appearance("exit", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("exit")
        dialog.set_close_response("stay")
        
        dialog.connect("response", self._on_done_response)
        dialog.present()
    
    def _on_done_response(self, dialog, response):
        """Handle goodbye dialog response."""
        if response == "exit":
            self.get_application().quit()
    
    def _on_tux_tunes_clicked(self, button):
        """Launch Tux Tunes application with self-healing and clear error messages."""
        import subprocess
        import os
        import stat
        
        # Try to find Tux Tunes
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tux_tunes_script = os.path.join(app_dir, 'tux', 'apps', 'tux_tunes', 'tux-tunes.py')
        
        if not os.path.exists(tux_tunes_script):
            dialog = Adw.MessageDialog(
                transient_for=self,
                heading="Tux Tunes Not Found",
                body="Could not locate the Tux Tunes application.\n\nTry reinstalling Tux Assistant."
            )
            dialog.add_response("ok", "OK")
            dialog.present()
            return
        
        # Check and fix execute permission if needed (self-healing)
        if not os.access(tux_tunes_script, os.X_OK):
            try:
                # Try to fix it ourselves first
                os.chmod(tux_tunes_script, os.stat(tux_tunes_script).st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            except PermissionError:
                # Need elevated privileges - use pkexec
                try:
                    subprocess.run(['pkexec', 'chmod', '+x', tux_tunes_script], check=True)
                except Exception:
                    pass  # We'll try launching anyway since we use python3
        
        # Launch with error capture (don't hide errors!)
        try:
            # Use a pipe to capture any immediate startup errors
            process = subprocess.Popen(
                ['python3', tux_tunes_script],
                start_new_session=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Give it a moment to fail if it's going to
            import time
            time.sleep(0.3)
            
            # Check if it died immediately
            if process.poll() is not None:
                # Process ended - get the error
                _, stderr = process.communicate(timeout=1)
                error_msg = stderr.decode('utf-8', errors='replace').strip()
                
                # Parse common errors into user-friendly messages
                if 'No module named' in error_msg:
                    module = error_msg.split("No module named")[-1].strip().strip("'\"")
                    friendly_msg = f"Missing Python module: {module}\n\nInstall it with your package manager."
                elif 'Gst' in error_msg or 'GStreamer' in error_msg:
                    friendly_msg = "GStreamer is not installed.\n\nInstall: gstreamer, gst-plugins-base, gst-plugins-good"
                elif 'Gtk' in error_msg or 'gi.repository' in error_msg:
                    friendly_msg = "GTK libraries not found.\n\nInstall: python-gobject, gtk4, libadwaita"
                else:
                    # Show raw error but truncated
                    friendly_msg = error_msg[:200] if error_msg else "Unknown error - check terminal for details"
                
                dialog = Adw.MessageDialog(
                    transient_for=self,
                    heading="Tux Tunes Failed to Start",
                    body=friendly_msg
                )
                dialog.add_response("ok", "OK")
                dialog.present()
            # else: it's running! Success, no message needed
                
        except Exception as e:
            dialog = Adw.MessageDialog(
                transient_for=self,
                heading="Failed to Launch Tux Tunes",
                body=f"Error: {str(e)}\n\nTry running from terminal:\npython3 {tux_tunes_script}"
            )
            dialog.add_response("ok", "OK")
            dialog.present()
    
    def create_system_info_banner(self) -> Gtk.Widget:
        """Create a banner showing system information."""
        from .core import get_hardware_info, check_hardinfo2_available
        
        banner = Adw.PreferencesGroup()
        banner.set_title("System Information")
        
        # Distro row
        distro_row = Adw.ActionRow()
        distro_row.set_title("Distribution")
        distro_row.set_subtitle(f"{self.distro.name} ({self.distro.family.value})")
        distro_row.add_prefix(Gtk.Image.new_from_icon_name("tux-computer-symbolic"))
        banner.add(distro_row)
        
        # Desktop row
        desktop_row = Adw.ActionRow()
        desktop_row.set_title("Desktop Environment")
        desktop_row.set_subtitle(f"{self.desktop.display_name} ({self.desktop.session_type})")
        desktop_row.add_prefix(Gtk.Image.new_from_icon_name("tux-video-display-symbolic"))
        banner.add(desktop_row)
        
        # Package manager row
        pkg_row = Adw.ActionRow()
        pkg_row.set_title("Package Manager")
        pkg_row.set_subtitle(self.distro.package_manager)
        pkg_row.add_prefix(Gtk.Image.new_from_icon_name("tux-package-x-generic-symbolic"))
        banner.add(pkg_row)
        
        # Hardware info row
        hardware = get_hardware_info()
        hw_row = Adw.ActionRow()
        hw_row.set_title("Hardware")
        
        # Build hardware summary
        hw_parts = []
        if hardware.cpu_model and hardware.cpu_model != "Unknown CPU":
            # Shorten CPU model name
            cpu_short = hardware.cpu_model.split('@')[0].strip()
            if len(cpu_short) > 40:
                cpu_short = cpu_short[:37] + "..."
            hw_parts.append(cpu_short)
        if hardware.ram_total_gb > 0:
            hw_parts.append(f"{hardware.ram_total_gb}GB RAM")
        
        hw_subtitle = " • ".join(hw_parts) if hw_parts else "Click for details"
        hw_row.set_subtitle(hw_subtitle)
        hw_row.add_prefix(Gtk.Image.new_from_icon_name("tux-computer-symbolic"))
        
        # Add button based on hardinfo2 availability
        if hardware.hardinfo2_available:
            # Launch hardinfo2 button
            launch_btn = Gtk.Button()
            launch_btn.set_icon_name("tux-go-next-symbolic")
            launch_btn.set_valign(Gtk.Align.CENTER)
            launch_btn.add_css_class("flat")
            launch_btn.set_tooltip_text("Open hardinfo2 for detailed hardware info")
            launch_btn.connect("clicked", self._on_launch_hardinfo2)
            hw_row.add_suffix(launch_btn)
            hw_row.set_activatable(True)
            hw_row.connect("activated", lambda r: self._on_launch_hardinfo2(None))
        else:
            # Install button
            install_btn = Gtk.Button(label="Install hardinfo2 (Recommended)")
            install_btn.add_css_class("suggested-action")
            install_btn.set_valign(Gtk.Align.CENTER)
            install_btn.connect("clicked", self._on_install_hardinfo2)
            hw_row.add_suffix(install_btn)
        
        banner.add(hw_row)
        
        # Store reference for refresh
        self.hw_row = hw_row
        
        # System Fetch row (fastfetch)
        fetch_row = Adw.ActionRow()
        fetch_row.set_title("System Fetch")
        fetch_row.set_subtitle("Show detailed system info in terminal (fastfetch)")
        fetch_row.add_prefix(Gtk.Image.new_from_icon_name("tux-utilities-terminal-symbolic"))
        fetch_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
        fetch_row.set_activatable(True)
        fetch_row.connect("activated", self._on_fastfetch_clicked)
        banner.add(fetch_row)
        
        return banner
    
    def _on_launch_hardinfo2(self, button):
        """Launch hardinfo2."""
        from .core import launch_hardinfo2
        if not launch_hardinfo2():
            self.show_toast("Failed to launch hardinfo2")
    
    def _on_install_hardinfo2(self, button):
        """Install hardinfo2 via terminal so user can see progress and enter passwords."""
        from .core import detect_aur_helper, DistroFamily
        import subprocess
        
        # Build the install script based on distro
        if self.distro.family == DistroFamily.ARCH:
            aur_helper = detect_aur_helper()
            if aur_helper:
                install_script = f'''echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Installing hardinfo2..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
{aur_helper} -S hardinfo2
echo ""
if command -v hardinfo2 &> /dev/null; then
    echo "✓ hardinfo2 installed successfully!"
else
    echo "✗ Installation failed"
fi
echo ""
echo "Press Enter to close..."
read'''
            else:
                # Need to install yay first
                install_script = '''echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Installing yay (AUR helper) first..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
sudo pacman -S --needed --noconfirm base-devel git
cd /tmp
rm -rf yay
git clone https://aur.archlinux.org/yay.git
cd yay
makepkg -si
cd ..
rm -rf yay
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Now installing hardinfo2..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
yay -S hardinfo2
echo ""
if command -v hardinfo2 &> /dev/null; then
    echo "✓ hardinfo2 installed successfully!"
else
    echo "✗ Installation failed"
fi
echo ""
echo "Press Enter to close..."
read'''
        elif self.distro.family == DistroFamily.DEBIAN:
            install_script = '''echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Installing hardinfo2..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
sudo apt-get install -y hardinfo2
echo ""
if command -v hardinfo2 &> /dev/null; then
    echo "✓ hardinfo2 installed successfully!"
else
    echo "✗ Installation failed - may need backports enabled"
fi
echo ""
echo "Press Enter to close..."
read'''
        elif self.distro.family == DistroFamily.FEDORA:
            install_script = '''echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Installing hardinfo2..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
sudo dnf install -y hardinfo2
echo ""
if command -v hardinfo2 &> /dev/null; then
    echo "✓ hardinfo2 installed successfully!"
else
    echo "✗ Installation failed"
fi
echo ""
echo "Press Enter to close..."
read'''
        elif self.distro.family == DistroFamily.OPENSUSE:
            install_script = '''echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Installing hardinfo2..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
sudo zypper install -y hardinfo2
echo ""
if command -v hardinfo2 &> /dev/null; then
    echo "✓ hardinfo2 installed successfully!"
else
    echo "✗ Installation failed"
fi
echo ""
echo "Press Enter to close..."
read'''
        else:
            self.show_toast("Unsupported distribution")
            return
        
        # Write script to temp file (avoids quoting issues with multi-line scripts)
        import tempfile
        script_file = tempfile.NamedTemporaryFile(mode='w', suffix='.sh', delete=False)
        script_file.write("#!/bin/bash\n")
        script_file.write(install_script)
        script_file.write(f"\nrm -f {script_file.name}\n")  # Self-cleanup
        script_file.close()
        os.chmod(script_file.name, 0o755)
        
        # Terminal commands using the script file
        terminals = [
            ('konsole', ['konsole', '-e', script_file.name]),
            ('ptyxis', ['ptyxis', '-e', 'bash', script_file.name]),  # Fedora 41+
            ('kgx', ['kgx', '-e', 'bash', script_file.name]),  # GNOME Console
            ('gnome-console', ['gnome-console', '-e', 'bash', script_file.name]),
            ('gnome-terminal', ['gnome-terminal', '--', script_file.name]),
            ('xfce4-terminal', ['xfce4-terminal', '-e', script_file.name]),
            ('mate-terminal', ['mate-terminal', '-e', script_file.name]),
            ('qterminal', ['qterminal', '-e', script_file.name]),
            ('lxterminal', ['lxterminal', '-e', script_file.name]),
            ('tilix', ['tilix', '-e', script_file.name]),
            ('terminator', ['terminator', '-e', script_file.name]),
            ('alacritty', ['alacritty', '-e', script_file.name]),
            ('kitty', ['kitty', script_file.name]),
            ('foot', ['foot', script_file.name]),
            ('wezterm', ['wezterm', 'start', '--', script_file.name]),
            ('sakura', ['sakura', '-e', script_file.name]),
            ('urxvt', ['urxvt', '-e', script_file.name]),
            ('st', ['st', '-e', script_file.name]),
            ('xterm', ['xterm', '-e', script_file.name]),
        ]
        
        for term_name, term_cmd in terminals:
            try:
                if subprocess.run(['which', term_name], capture_output=True).returncode == 0:
                    subprocess.Popen(term_cmd)
                    self.show_toast("Terminal opened - follow the prompts to install")
                    
                    # Check for completion after a delay and update UI
                    GLib.timeout_add(5000, self._check_hardinfo2_installed, button)
                    return
            except Exception:
                continue
        
        # Cleanup if no terminal found
        os.unlink(script_file.name)
        self.show_toast("Could not find terminal emulator - please install one (gnome-console, konsole, xterm, etc.)")
    
    def _check_hardinfo2_installed(self, button):
        """Check if hardinfo2 was installed and update UI."""
        from .core import check_hardinfo2_available
        
        if check_hardinfo2_available():
            # Replace button with launch button
            button.get_parent().remove(button)
            
            launch_btn = Gtk.Button()
            launch_btn.set_icon_name("tux-go-next-symbolic")
            launch_btn.set_valign(Gtk.Align.CENTER)
            launch_btn.add_css_class("flat")
            launch_btn.set_tooltip_text("Open hardinfo2 for detailed hardware info")
            launch_btn.connect("clicked", self._on_launch_hardinfo2)
            self.hw_row.add_suffix(launch_btn)
            self.hw_row.set_activatable(True)
            self.hw_row.connect("activated", lambda r: self._on_launch_hardinfo2(None))
            self.show_toast("hardinfo2 ready!")
            return False  # Stop checking
        
        # Keep checking for a bit (up to 60 seconds)
        return True
    
    def _on_fastfetch_clicked(self, row):
        """Launch fastfetch in the user's terminal."""
        import shutil
        import subprocess
        import os
        
        # Check if fastfetch is installed
        if not shutil.which('fastfetch'):
            self.show_toast("fastfetch not installed - install it with your package manager")
            return
        
        # Create script (same approach as developer_tools.py)
        script_content = '''#!/bin/bash
fastfetch
echo
read -p "Press Enter to close..."
'''
        
        # Write script to fixed temp path (like developer_tools.py does)
        script_path = '/tmp/tux-fastfetch.sh'
        with open(script_path, 'w') as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)
        
        # Find and launch terminal - EXACT copy from developer_tools.py
        terminals = [
            ('ptyxis', ['ptyxis', '-e', 'bash', script_path]),  # Fedora 43+ default
            ('kgx', ['kgx', '-e', 'bash', script_path]),  # GNOME Console
            ('gnome-terminal', ['gnome-terminal', '--', 'bash', script_path]),
            ('konsole', ['konsole', '-e', 'bash', script_path]),
            ('xfce4-terminal', ['xfce4-terminal', '-e', f'bash {script_path}']),
            ('tilix', ['tilix', '-e', f'bash {script_path}']),
            ('alacritty', ['alacritty', '-e', 'bash', script_path]),
            ('kitty', ['kitty', 'bash', script_path]),
            ('xterm', ['xterm', '-e', f'bash {script_path}']),
        ]
        
        for term_name, term_cmd in terminals:
            try:
                if subprocess.run(['which', term_name], capture_output=True).returncode == 0:
                    subprocess.Popen(term_cmd)
                    return
            except Exception:
                continue
        
        self.show_toast("No supported terminal found")
    
    def create_module_group_from_registry(self, title: str, modules: list) -> Gtk.Widget:
        """
        Create a group of module buttons from registry modules.
        
        Args:
            title: Group title (category name)
            modules: List of ModuleInfo objects
        """
        group = Adw.PreferencesGroup()
        group.set_title(title)
        
        for module_info in modules:
            row = Adw.ActionRow()
            row.set_title(module_info.name)
            
            # Get description (may be dynamic)
            description = module_info.get_description(
                desktop=self.desktop,
                distro=self.distro
            )
            row.set_subtitle(description)
            
            row.set_activatable(True)
            row.add_prefix(create_icon_simple(module_info.icon))
            row.add_suffix(create_icon_simple("tux-go-next-symbolic"))
            
            # Connect click handler
            row.connect("activated", self.on_module_clicked, module_info)
            group.add(row)
        
        return group
    
    # =========================================================================
    # Search Functionality
    # =========================================================================
    
    def _build_search_index(self) -> list:
        """Build searchable index from all modules."""
        search_items = []
        
        for category in ModuleRegistry.get_categories():
            modules = ModuleRegistry.get_modules_by_category(category)
            for mod in modules:
                # Add module with keywords
                keywords = [
                    mod.name.lower(),
                    mod.id.lower(),
                    mod.description.lower() if mod.description else "",
                    category.value.lower(),
                ]
                
                # Add common search terms for each module
                module_keywords = {
                    "gaming": ["steam", "lutris", "proton", "wine", "games", "play"],
                    "software_center": ["install", "apps", "software", "packages", "flatpak", "snap"],
                    "system_maintenance": ["update", "clean", "cache", "startup", "services"],
                    "networking_simple": ["wifi", "network", "internet", "connection", "vpn", "samba"],
                    "hardware_manager": ["printer", "bluetooth", "drivers", "sound", "audio"],
                    "desktop_enhancements": ["theme", "icon", "font", "wallpaper", "gnome", "kde", "extensions"],
                    "backup_restore": ["backup", "restore", "timeshift", "snapshot"],
                    "setup_tools": ["codecs", "drivers", "nvidia", "setup"],
                    "media_server": ["plex", "jellyfin", "media", "server", "dvd"],
                    "developer_tools": ["git", "ssh", "code", "programming", "aur", "deb", "rpm"],
                    "help_learning": ["help", "tutorial", "learn", "troubleshoot", "guide"],
                    "repo_management": ["repository", "repo", "ppa", "copr", "packman", "multilib"],
                }
                
                if mod.id in module_keywords:
                    keywords.extend(module_keywords[mod.id])
                
                search_items.append({
                    "module": mod,
                    "keywords": " ".join(keywords),
                    "name": mod.name,
                    "description": mod.description or "",
                    "icon": mod.icon,
                })
        
        return search_items
    
    def _on_search_changed(self, entry):
        """Handle search text changes - show/hide results."""
        query = entry.get_text().strip().lower()
        
        if not query:
            # Clear search, show modules
            self.search_results_box.set_visible(False)
            self.modules_content_box.set_visible(True)
            # Clear old results
            while child := self.search_results_box.get_first_child():
                self.search_results_box.remove(child)
            return
        
        # Show search results, hide modules
        self.search_results_box.set_visible(True)
        self.modules_content_box.set_visible(False)
        
        # Clear old results
        while child := self.search_results_box.get_first_child():
            self.search_results_box.remove(child)
        
        # Search
        search_index = self._build_search_index()
        matches = []
        
        for item in search_index:
            if query in item["keywords"]:
                matches.append(item)
        
        if matches:
            results_group = Adw.PreferencesGroup()
            results_group.set_title(f"Results for \"{entry.get_text().strip()}\"")
            
            for match in matches[:10]:  # Limit to 10 results
                row = Adw.ActionRow()
                row.set_title(match["name"])
                row.set_subtitle(match["description"])
                row.set_activatable(True)
                row.add_prefix(Gtk.Image.new_from_icon_name(match["icon"]))
                row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
                row.connect("activated", self.on_module_clicked, match["module"])
                results_group.add(row)
            
            self.search_results_box.append(results_group)
        else:
            # No results - show web search option
            no_results = Adw.PreferencesGroup()
            no_results.set_title("No matching features found")
            no_results.set_description(f"Press Enter to search the web for \"{entry.get_text().strip()}\"")
            
            web_row = Adw.ActionRow()
            web_row.set_title("Search DuckDuckGo")
            web_row.set_subtitle(f"Search the web for: {entry.get_text().strip()}")
            web_row.set_activatable(True)
            web_row.add_prefix(Gtk.Image.new_from_icon_name("tux-web-browser-symbolic"))
            web_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
            web_row.connect("activated", lambda r: self._do_web_search(entry.get_text().strip()))
            no_results.add(web_row)
            
            self.search_results_box.append(no_results)
    
    def _on_search_activated(self, entry):
        """Handle Enter key in search - navigate to first result or web search."""
        query = entry.get_text().strip().lower()
        
        if not query:
            return
        
        # Check for matches
        search_index = self._build_search_index()
        matches = [item for item in search_index if query in item["keywords"]]
        
        if matches:
            # Navigate to first match
            mod = matches[0]["module"]
            if mod.page_class:
                page = mod.page_class(self)
                self.navigation_view.push(page)
                entry.set_text("")
                self.search_results_box.set_visible(False)
                self.modules_content_box.set_visible(True)
        else:
            # No matches - do web search
            self._do_web_search(entry.get_text().strip())
    
    def _get_search_url(self, query):
        """Get search URL based on configured search engine."""
        import urllib.parse
        
        search_engine = self._load_browser_settings().get('search_engine', 'DuckDuckGo')
        encoded_query = urllib.parse.quote(query)
        
        search_urls = {
            'DuckDuckGo': f"https://duckduckgo.com/?q={encoded_query}",
            'Google': f"https://www.google.com/search?q={encoded_query}",
            'Bing': f"https://www.bing.com/search?q={encoded_query}",
            'Startpage': f"https://www.startpage.com/search?q={encoded_query}",
            'Brave': f"https://search.brave.com/search?q={encoded_query}"
        }
        
        return search_urls.get(search_engine, search_urls['DuckDuckGo'])
    
    def _do_web_search(self, query: str):
        """Open web search in internal browser."""
        search_url = self._get_search_url(query + ' linux')
        
        if WEBKIT_AVAILABLE and hasattr(self, 'browser_panel') and self.browser_panel is not None:
            # Use internal browser
            if not self.browser_panel_visible:
                self.browser_toggle_btn.set_active(True)
            
            # Load search URL
            webview = self._get_current_browser_webview()
            if webview:
                webview.load_uri(search_url)
            
            self.show_toast(f"Searching: {query}")
        else:
            # Fallback to external browser
            import subprocess
            subprocess.Popen(['xdg-open', search_url])
            self.show_toast(f"Opening search in browser...")
        
        # Clear search
        self.search_entry.set_text("")
        self.search_results_box.set_visible(False)
        self.modules_content_box.set_visible(True)
    
    def show_toast(self, message: str, timeout: int = 3):
        """Show a toast notification."""
        toast = Adw.Toast(title=message)
        toast.set_timeout(timeout)
        self.toast_overlay.add_toast(toast)
    
    def on_module_clicked(self, row, module_info):
        """Handle module click - navigate to module page."""
        if module_info.page_class:
            # Create an instance of the module's page class
            page = module_info.page_class(self)
            self.navigation_view.push(page)
        else:
            # Module exists but has no page yet
            self.show_toast(f"{module_info.name} - Coming soon!")


def main():
    """Main entry point."""
    app = TuxAssistantApp()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
