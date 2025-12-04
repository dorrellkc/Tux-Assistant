"""
Tux Assistant - Main GTK4 Application

The main application class using GTK4 and libadwaita.
Dynamically discovers and loads modules from the modules directory.

Copyright (c) 2025 Christopher Dorrell. Licensed under GPL-3.0.
"""

import sys
import os
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GLib, Gdk

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
from .modules import ModuleRegistry, ModuleCategory


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
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS
        )
        
        self.window = None
        
        # Connect signals
        self.connect('activate', self.on_activate)
        self.connect('startup', self.on_startup)
    
    def on_startup(self, app):
        """Called when the application starts."""
        # Discover and register all modules
        ModuleRegistry.discover_modules()
        
        # Load custom CSS for larger UI
        self.load_css()
        
        # Set up actions
        self.create_actions()
        
        # Audio dependency check disabled - uncomment to re-enable:
        # GLib.idle_add(self._check_audio_dependencies)
    
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
        
        # Build UI
        self.build_ui()
    
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
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_menu_model(self.create_menu())
        header.pack_end(menu_button)
        
        # Claude AI toggle button (only if WebKit available)
        if WEBKIT_AVAILABLE:
            # Browser toggle button
            self.browser_toggle_btn = Gtk.ToggleButton()
            self.browser_toggle_btn.set_icon_name("web-browser-symbolic")
            self.browser_toggle_btn.set_tooltip_text("Toggle Web Browser")
            self.browser_toggle_btn.add_css_class("claude-toggle-btn")
            self.browser_toggle_btn.connect("toggled", self._on_browser_toggle)
            header.pack_end(self.browser_toggle_btn)
            
            # Claude AI toggle button
            self.claude_toggle_btn = Gtk.ToggleButton()
            self.claude_toggle_btn.set_icon_name("user-available-symbolic")
            self.claude_toggle_btn.set_tooltip_text("Toggle Claude AI Assistant")
            self.claude_toggle_btn.add_css_class("claude-toggle-btn")
            self.claude_toggle_btn.connect("toggled", self._on_claude_toggle)
            header.pack_end(self.claude_toggle_btn)
        
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
            self._build_global_browser_panel()
        
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
        external_btn = Gtk.Button.new_from_icon_name("web-browser-symbolic")
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
        back_btn = Gtk.Button.new_from_icon_name("go-previous-symbolic")
        back_btn.set_tooltip_text("Go back")
        back_btn.connect("clicked", lambda b: self.claude_webview.go_back() if hasattr(self, 'claude_webview') else None)
        nav_toolbar.append(back_btn)
        
        # Forward button
        forward_btn = Gtk.Button.new_from_icon_name("go-next-symbolic")
        forward_btn.set_tooltip_text("Go forward")
        forward_btn.connect("clicked", lambda b: self.claude_webview.go_forward() if hasattr(self, 'claude_webview') else None)
        nav_toolbar.append(forward_btn)
        
        # Reload button
        reload_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        reload_btn.set_tooltip_text("Reload")
        reload_btn.connect("clicked", lambda b: self.claude_webview.reload() if hasattr(self, 'claude_webview') else None)
        nav_toolbar.append(reload_btn)
        
        # Home button
        home_btn = Gtk.Button.new_from_icon_name("go-home-symbolic")
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
        
        title_label = Gtk.Label(label="Web Browser")
        title_label.add_css_class("title")
        title_box.append(title_label)
        
        panel_header.append(title_box)
        
        # Pop-out button
        popout_btn = Gtk.Button.new_from_icon_name("window-new-symbolic")
        popout_btn.set_tooltip_text("Pop out to window")
        popout_btn.connect("clicked", self._on_browser_popout)
        panel_header.append(popout_btn)
        
        # URL bar
        url_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        url_box.set_margin_start(12)
        url_box.set_margin_end(12)
        url_box.set_margin_bottom(8)
        self.browser_panel.append(url_box)
        
        self.browser_url_entry = Gtk.Entry()
        self.browser_url_entry.set_hexpand(True)
        self.browser_url_entry.set_placeholder_text("Enter URL or search...")
        self.browser_url_entry.connect("activate", self._on_browser_url_activate)
        url_box.append(self.browser_url_entry)
        
        go_btn = Gtk.Button.new_from_icon_name("go-next-symbolic")
        go_btn.set_tooltip_text("Go")
        go_btn.connect("clicked", lambda b: self._on_browser_url_activate(self.browser_url_entry))
        url_box.append(go_btn)
        
        # Navigation toolbar
        nav_toolbar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        nav_toolbar.set_margin_start(12)
        nav_toolbar.set_margin_end(12)
        nav_toolbar.set_margin_bottom(8)
        self.browser_panel.append(nav_toolbar)
        
        # Back button
        back_btn = Gtk.Button.new_from_icon_name("go-previous-symbolic")
        back_btn.set_tooltip_text("Go back")
        back_btn.connect("clicked", lambda b: self.browser_webview.go_back() if hasattr(self, 'browser_webview') else None)
        nav_toolbar.append(back_btn)
        
        # Forward button
        forward_btn = Gtk.Button.new_from_icon_name("go-next-symbolic")
        forward_btn.set_tooltip_text("Go forward")
        forward_btn.connect("clicked", lambda b: self.browser_webview.go_forward() if hasattr(self, 'browser_webview') else None)
        nav_toolbar.append(forward_btn)
        
        # Reload button
        reload_btn = Gtk.Button.new_from_icon_name("view-refresh-symbolic")
        reload_btn.set_tooltip_text("Reload")
        reload_btn.connect("clicked", lambda b: self.browser_webview.reload() if hasattr(self, 'browser_webview') else None)
        nav_toolbar.append(reload_btn)
        
        # Home button
        home_btn = Gtk.Button.new_from_icon_name("go-home-symbolic")
        home_btn.set_tooltip_text("Go to home page")
        home_btn.connect("clicked", self._on_browser_home)
        nav_toolbar.append(home_btn)
        
        # Create WebView (shares same cookie storage as Claude)
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
                
                self.browser_webview = WebKit.WebView(network_session=self.browser_network_session)
                self.browser_network_session.connect('download-started', self._on_browser_download_started)
            else:
                self.browser_webview = WebKit.WebView()
                try:
                    context = self.browser_webview.get_context()
                    context.connect('download-started', self._on_browser_download_started)
                except:
                    pass
        except Exception as e:
            print(f"Browser WebKit setup error: {e}")
            self.browser_webview = WebKit.WebView()
        
        self.browser_webview.set_vexpand(True)
        self.browser_webview.set_hexpand(True)
        
        # Update URL bar when page loads
        self.browser_webview.connect("load-changed", self._on_browser_load_changed)
        
        # Configure settings
        settings = self.browser_webview.get_settings()
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
        
        # Handle links that try to open new windows - open in default browser
        self.browser_webview.connect("create", self._on_browser_create_window)
        
        # Frame around webview
        webview_frame = Gtk.Frame()
        webview_frame.set_margin_start(12)
        webview_frame.set_margin_end(12)
        webview_frame.set_margin_bottom(12)
        webview_frame.set_child(self.browser_webview)
        webview_frame.set_vexpand(True)
        self.browser_panel.append(webview_frame)
        
        self.browser_panel_visible = False
        self.browser_home_url = "https://duckduckgo.com"
    
    def _on_browser_toggle(self, button):
        """Toggle browser panel visibility."""
        if not hasattr(self, 'browser_panel') or self.browser_panel is None:
            return
        
        if button.get_active():
            # Show browser
            button.add_css_class("active")
            
            # Load home page if not already loaded
            uri = self.browser_webview.get_uri()
            if not uri or uri == "about:blank":
                self.browser_webview.load_uri(self.browser_home_url)
            
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
        if hasattr(self, 'browser_webview'):
            self.browser_webview.load_uri(self.browser_home_url)
    
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
            # Search with DuckDuckGo
            from urllib.parse import quote
            url = f"https://duckduckgo.com/?q={quote(text)}"
        
        self.browser_webview.load_uri(url)
    
    def _on_browser_load_changed(self, webview, event):
        """Update URL bar when page loads."""
        if event == WebKit.LoadEvent.COMMITTED:
            uri = webview.get_uri()
            if uri and hasattr(self, 'browser_url_entry'):
                self.browser_url_entry.set_text(uri)
    
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
        self.show_toast(f"Downloading: {os.path.basename(destination)}")
        return True
    
    def _on_browser_download_finished(self, download):
        """Handle browser download completion."""
        destination = download.get_destination()
        filename = os.path.basename(destination) if destination else "file"
        self.show_toast(f"Downloaded: {filename}")
    
    def _on_browser_download_failed(self, download, error):
        """Handle browser download failure."""
        self.show_toast("Download failed")
    
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
        from .core import get_hardware_info
        from .ui.tux_fetch import TuxFetchSidebar
        
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
        
        # System info banner (compact version for left side)
        info_banner = self.create_system_info_banner()
        content_box.append(info_banner)
        
        # Dynamically create module groups based on registered modules
        for category in ModuleRegistry.get_categories():
            modules = ModuleRegistry.get_modules_by_category(category)
            
            if modules:
                group = self.create_module_group_from_registry(category.value, modules)
                content_box.append(group)
        
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
        
        # RIGHT SIDE: Sidebar with Tux Tunes launcher, fixed TuxFetch, scrollable area below
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
        
        # MIDDLE: Fixed TuxFetch panel
        hardware = get_hardware_info()
        tux_fetch = TuxFetchSidebar(self.distro, self.desktop, hardware)
        sidebar_box.append(tux_fetch)
        
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
        
        return page
        done_box.append(hint_label)
        
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
        """Launch Tux Tunes application."""
        import subprocess
        import os
        
        # Try to find and launch Tux Tunes
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        tux_tunes_script = os.path.join(app_dir, 'tux', 'apps', 'tux_tunes', 'tux-tunes.py')
        
        if os.path.exists(tux_tunes_script):
            try:
                subprocess.Popen(['python3', tux_tunes_script], 
                               start_new_session=True,
                               stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL)
            except Exception as e:
                # Show error toast
                toast = Adw.Toast(title=f"Failed to launch Tux Tunes: {e}")
                toast.set_timeout(3)
                # Find toast overlay if available
                pass
        else:
            # Show not found message
            dialog = Adw.MessageDialog(
                transient_for=self,
                heading="Tux Tunes Not Found",
                body="Could not locate the Tux Tunes application."
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
        distro_row.add_prefix(Gtk.Image.new_from_icon_name("computer-symbolic"))
        banner.add(distro_row)
        
        # Desktop row
        desktop_row = Adw.ActionRow()
        desktop_row.set_title("Desktop Environment")
        desktop_row.set_subtitle(f"{self.desktop.display_name} ({self.desktop.session_type})")
        desktop_row.add_prefix(Gtk.Image.new_from_icon_name("video-display-symbolic"))
        banner.add(desktop_row)
        
        # Package manager row
        pkg_row = Adw.ActionRow()
        pkg_row.set_title("Package Manager")
        pkg_row.set_subtitle(self.distro.package_manager)
        pkg_row.add_prefix(Gtk.Image.new_from_icon_name("package-x-generic-symbolic"))
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
        hw_row.add_prefix(Gtk.Image.new_from_icon_name("computer-symbolic"))
        
        # Add button based on hardinfo2 availability
        if hardware.hardinfo2_available:
            # Launch hardinfo2 button
            launch_btn = Gtk.Button()
            launch_btn.set_icon_name("go-next-symbolic")
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
            launch_btn.set_icon_name("go-next-symbolic")
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
            row.add_prefix(Gtk.Image.new_from_icon_name(module_info.icon))
            row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            
            # Connect click handler
            row.connect("activated", self.on_module_clicked, module_info)
            group.add(row)
        
        return group
    
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
