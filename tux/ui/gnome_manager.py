#!/usr/bin/env python3
"""
GNOME Enhancements Manager - GTK GUI

A graphical tool for managing GNOME Shell extensions and tweaks.
Integrates with extensions.gnome.org API and gsettings.
"""

import gi
import json
import subprocess
import threading
import urllib.request
import urllib.parse
from typing import Optional, Callable

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, GLib, Gio, Pango


# =============================================================================
# Constants
# =============================================================================

EXTENSIONS_API_URL = "https://extensions.gnome.org/extension-query/"
EXTENSION_INFO_URL = "https://extensions.gnome.org/extension-info/"

# Popular/recommended extensions with their UUIDs
POPULAR_EXTENSIONS = [
    {
        "uuid": "dash-to-dock@micxgx.gmail.com",
        "name": "Dash to Dock",
        "description": "A dock for GNOME Shell (like macOS)",
        "pk": 307
    },
    {
        "uuid": "blur-my-shell@aunetx",
        "name": "Blur My Shell",
        "description": "Add blur effect to different parts of the Shell",
        "pk": 3193
    },
    {
        "uuid": "appindicatorsupport@rgcjonas.gmail.com",
        "name": "AppIndicator Support",
        "description": "Adds AppIndicator/tray icon support",
        "pk": 615
    },
    {
        "uuid": "caffeine@pataber.gmail.com",
        "name": "Caffeine",
        "description": "Disable screensaver and suspend",
        "pk": 517
    },
    {
        "uuid": "just-perfection-desktop@just-perfection",
        "name": "Just Perfection",
        "description": "Customize GNOME Shell behavior",
        "pk": 3843
    },
    {
        "uuid": "gsconnect@andyholmes.github.io",
        "name": "GSConnect",
        "description": "KDE Connect for GNOME (phone integration)",
        "pk": 1319
    },
    {
        "uuid": "Vitals@CoreCoding.com",
        "name": "Vitals",
        "description": "System monitor (CPU, RAM, temp, etc.)",
        "pk": 1460
    },
    {
        "uuid": "arcmenu@arcmenu.com",
        "name": "ArcMenu",
        "description": "Application menu for GNOME Shell",
        "pk": 3628
    },
    {
        "uuid": "clipboard-indicator@tudmotu.com",
        "name": "Clipboard Indicator",
        "description": "Clipboard manager for GNOME Shell",
        "pk": 779
    },
    {
        "uuid": "user-theme@gnome-shell-extensions.gcampax.github.com",
        "name": "User Themes",
        "description": "Load shell themes from user directory",
        "pk": 19
    },
]

# Common tweaks with their gsettings paths
TWEAKS_SETTINGS = {
    "window_buttons": {
        "schema": "org.gnome.desktop.wm.preferences",
        "key": "button-layout",
        "type": "string",
        "options": {
            "Right (default)": "appmenu:minimize,maximize,close",
            "Left (macOS style)": "close,minimize,maximize:appmenu",
            "Minimal (close only)": "appmenu:close",
        }
    },
    "show_weekday": {
        "schema": "org.gnome.desktop.interface",
        "key": "clock-show-weekday",
        "type": "bool",
        "label": "Show weekday in clock"
    },
    "show_seconds": {
        "schema": "org.gnome.desktop.interface",
        "key": "clock-show-seconds",
        "type": "bool",
        "label": "Show seconds in clock"
    },
    "show_battery_percentage": {
        "schema": "org.gnome.desktop.interface",
        "key": "show-battery-percentage",
        "type": "bool",
        "label": "Show battery percentage"
    },
    "hot_corners": {
        "schema": "org.gnome.desktop.interface",
        "key": "enable-hot-corners",
        "type": "bool",
        "label": "Enable hot corners"
    },
    "animations": {
        "schema": "org.gnome.desktop.interface",
        "key": "enable-animations",
        "type": "bool",
        "label": "Enable animations"
    },
    "night_light": {
        "schema": "org.gnome.settings-daemon.plugins.color",
        "key": "night-light-enabled",
        "type": "bool",
        "label": "Enable Night Light"
    },
    "mouse_natural_scroll": {
        "schema": "org.gnome.desktop.peripherals.mouse",
        "key": "natural-scroll",
        "type": "bool",
        "label": "Mouse natural scrolling"
    },
    "touchpad_tap_to_click": {
        "schema": "org.gnome.desktop.peripherals.touchpad",
        "key": "tap-to-click",
        "type": "bool",
        "label": "Tap to click"
    },
    "touchpad_natural_scroll": {
        "schema": "org.gnome.desktop.peripherals.touchpad",
        "key": "natural-scroll",
        "type": "bool",
        "label": "Touchpad natural scrolling"
    },
}


# =============================================================================
# Helper Functions
# =============================================================================

def get_gnome_shell_version() -> Optional[str]:
    """Get the current GNOME Shell version."""
    try:
        result = subprocess.run(
            ['gnome-shell', '--version'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            # "GNOME Shell 45.1" -> "45"
            version = result.stdout.strip().split()[-1]
            major = version.split('.')[0]
            return major
    except:
        pass
    return None


def get_installed_extensions() -> dict:
    """Get list of installed extensions with their enabled status."""
    extensions = {}
    try:
        # Get all installed extensions
        result = subprocess.run(
            ['gnome-extensions', 'list'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            for uuid in result.stdout.strip().split('\n'):
                if uuid:
                    extensions[uuid] = {"installed": True, "enabled": False}
        
        # Check which are enabled
        result = subprocess.run(
            ['gnome-extensions', 'list', '--enabled'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            for uuid in result.stdout.strip().split('\n'):
                if uuid and uuid in extensions:
                    extensions[uuid]["enabled"] = True
    except Exception as e:
        print(f"Error getting extensions: {e}")
    
    return extensions


def install_extension(uuid: str, callback: Callable = None) -> bool:
    """Install an extension by UUID using gnome-extensions."""
    try:
        # Try to install via gnome-extensions install (GNOME 40+)
        result = subprocess.run(
            ['gnome-extensions', 'install', uuid],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            if callback:
                GLib.idle_add(callback, True, f"Installed {uuid}")
            return True
        else:
            if callback:
                GLib.idle_add(callback, False, result.stderr)
            return False
    except Exception as e:
        if callback:
            GLib.idle_add(callback, False, str(e))
        return False


def enable_extension(uuid: str) -> bool:
    """Enable an extension."""
    try:
        result = subprocess.run(
            ['gnome-extensions', 'enable', uuid],
            capture_output=True
        )
        return result.returncode == 0
    except:
        return False


def disable_extension(uuid: str) -> bool:
    """Disable an extension."""
    try:
        result = subprocess.run(
            ['gnome-extensions', 'disable', uuid],
            capture_output=True
        )
        return result.returncode == 0
    except:
        return False


def uninstall_extension(uuid: str) -> bool:
    """Uninstall an extension."""
    try:
        result = subprocess.run(
            ['gnome-extensions', 'uninstall', uuid],
            capture_output=True
        )
        return result.returncode == 0
    except:
        return False


def get_gsetting(schema: str, key: str) -> Optional[str]:
    """Get a gsettings value."""
    try:
        result = subprocess.run(
            ['gsettings', 'get', schema, key],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    return None


def set_gsetting(schema: str, key: str, value: str) -> bool:
    """Set a gsettings value."""
    try:
        result = subprocess.run(
            ['gsettings', 'set', schema, key, value],
            capture_output=True
        )
        return result.returncode == 0
    except:
        return False


def search_extensions(query: str, shell_version: str = None) -> list:
    """Search for extensions on extensions.gnome.org."""
    try:
        params = {
            'search': query,
            'n_per_page': 20,
        }
        if shell_version:
            params['shell_version'] = shell_version
        
        url = EXTENSIONS_API_URL + "?" + urllib.parse.urlencode(params)
        
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'LinuxToolkit/4.5')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            return data.get('extensions', [])
    except Exception as e:
        print(f"Search error: {e}")
        return []


# =============================================================================
# GTK Widgets
# =============================================================================

class ExtensionRow(Gtk.Box):
    """A row widget for displaying an extension."""
    
    def __init__(self, ext_data: dict, installed: bool = False, enabled: bool = False,
                 on_install: Callable = None, on_toggle: Callable = None,
                 on_uninstall: Callable = None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        
        self.uuid = ext_data.get('uuid', '')
        self.ext_data = ext_data
        self.installed = installed
        self.enabled = enabled
        self.on_install = on_install
        self.on_toggle = on_toggle
        self.on_uninstall = on_uninstall
        
        # Info section
        info_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        info_box.set_hexpand(True)
        
        name_label = Gtk.Label(label=ext_data.get('name', self.uuid))
        name_label.set_halign(Gtk.Align.START)
        name_label.add_css_class('heading')
        name_label.set_markup(f"<b>{ext_data.get('name', self.uuid)}</b>")
        info_box.append(name_label)
        
        desc = ext_data.get('description', '')[:100]
        if len(ext_data.get('description', '')) > 100:
            desc += '...'
        desc_label = Gtk.Label(label=desc)
        desc_label.set_halign(Gtk.Align.START)
        desc_label.add_css_class('dim-label')
        desc_label.set_wrap(True)
        desc_label.set_max_width_chars(60)
        info_box.append(desc_label)
        
        self.append(info_box)
        
        # Action buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        button_box.set_valign(Gtk.Align.CENTER)
        
        if installed:
            # Enable/Disable toggle
            self.toggle_btn = Gtk.Switch()
            self.toggle_btn.set_active(enabled)
            self.toggle_btn.set_valign(Gtk.Align.CENTER)
            self.toggle_btn.connect('state-set', self._on_toggle)
            button_box.append(self.toggle_btn)
            
            # Uninstall button
            uninstall_btn = Gtk.Button(label="Remove")
            uninstall_btn.add_css_class('destructive-action')
            uninstall_btn.connect('clicked', self._on_uninstall)
            button_box.append(uninstall_btn)
        else:
            # Install button
            self.install_btn = Gtk.Button(label="Install")
            self.install_btn.add_css_class('suggested-action')
            self.install_btn.connect('clicked', self._on_install)
            button_box.append(self.install_btn)
        
        self.append(button_box)
    
    def _on_install(self, button):
        button.set_sensitive(False)
        button.set_label("Installing...")
        if self.on_install:
            self.on_install(self.uuid, self.ext_data)
    
    def _on_toggle(self, switch, state):
        if self.on_toggle:
            self.on_toggle(self.uuid, state)
        return False
    
    def _on_uninstall(self, button):
        if self.on_uninstall:
            self.on_uninstall(self.uuid)


class TweakRow(Gtk.Box):
    """A row widget for a tweak setting."""
    
    def __init__(self, key: str, config: dict, on_change: Callable = None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        self.set_margin_start(12)
        self.set_margin_end(12)
        self.set_margin_top(8)
        self.set_margin_bottom(8)
        
        self.key = key
        self.config = config
        self.on_change = on_change
        
        # Label
        label = Gtk.Label(label=config.get('label', key))
        label.set_halign(Gtk.Align.START)
        label.set_hexpand(True)
        self.append(label)
        
        # Get current value
        current = get_gsetting(config['schema'], config['key'])
        
        if config['type'] == 'bool':
            # Toggle switch
            self.widget = Gtk.Switch()
            self.widget.set_valign(Gtk.Align.CENTER)
            if current:
                self.widget.set_active(current.lower() == 'true')
            self.widget.connect('state-set', self._on_bool_change)
        
        elif config['type'] == 'string' and 'options' in config:
            # Dropdown
            self.widget = Gtk.DropDown()
            options = list(config['options'].keys())
            string_list = Gtk.StringList()
            for opt in options:
                string_list.append(opt)
            self.widget.set_model(string_list)
            
            # Set current selection
            if current:
                current_clean = current.strip("'")
                for i, (name, val) in enumerate(config['options'].items()):
                    if val == current_clean:
                        self.widget.set_selected(i)
                        break
            
            self.widget.connect('notify::selected', self._on_dropdown_change)
        
        self.append(self.widget)
    
    def _on_bool_change(self, switch, state):
        value = 'true' if state else 'false'
        set_gsetting(self.config['schema'], self.config['key'], value)
        if self.on_change:
            self.on_change(self.key, state)
        return False
    
    def _on_dropdown_change(self, dropdown, param):
        selected = dropdown.get_selected()
        options = list(self.config['options'].values())
        if selected < len(options):
            value = f"'{options[selected]}'"
            set_gsetting(self.config['schema'], self.config['key'], value)
            if self.on_change:
                self.on_change(self.key, options[selected])


# =============================================================================
# Main Window
# =============================================================================

class GnomeManagerWindow(Adw.ApplicationWindow):
    """Main window for GNOME Enhancements Manager."""
    
    def __init__(self, app):
        super().__init__(application=app)
        self.set_title("GNOME Enhancements - Tux Assistant")
        self.set_default_size(800, 600)
        
        self.shell_version = get_gnome_shell_version()
        self.installed_extensions = get_installed_extensions()
        
        # Main layout
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        # Header bar
        header = Adw.HeaderBar()
        header.set_title_widget(Gtk.Label(label="GNOME Enhancements"))
        main_box.append(header)
        
        # Tab view
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        
        # Stack switcher
        switcher = Gtk.StackSwitcher()
        switcher.set_stack(self.stack)
        switcher.set_halign(Gtk.Align.CENTER)
        switcher.set_margin_top(12)
        switcher.set_margin_bottom(12)
        main_box.append(switcher)
        
        # Extensions page
        extensions_page = self._create_extensions_page()
        self.stack.add_titled(extensions_page, "extensions", "Extensions")
        
        # Tweaks page
        tweaks_page = self._create_tweaks_page()
        self.stack.add_titled(tweaks_page, "tweaks", "Tweaks")
        
        # Installed page
        installed_page = self._create_installed_page()
        self.stack.add_titled(installed_page, "installed", "Installed")
        
        main_box.append(self.stack)
        
        # Status bar
        self.status_label = Gtk.Label()
        self.status_label.set_margin_start(12)
        self.status_label.set_margin_end(12)
        self.status_label.set_margin_bottom(8)
        self.status_label.add_css_class('dim-label')
        if self.shell_version:
            self.status_label.set_text(f"GNOME Shell {self.shell_version} • {len(self.installed_extensions)} extensions installed")
        main_box.append(self.status_label)
        
        self.set_content(main_box)
    
    def _create_extensions_page(self) -> Gtk.Widget:
        """Create the extensions browser page."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_margin_start(24)
        page.set_margin_end(24)
        page.set_margin_top(12)
        page.set_margin_bottom(12)
        
        # Search box
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search extensions...")
        self.search_entry.set_hexpand(True)
        self.search_entry.connect('activate', self._on_search)
        search_box.append(self.search_entry)
        
        search_btn = Gtk.Button(label="Search")
        search_btn.add_css_class('suggested-action')
        search_btn.connect('clicked', self._on_search)
        search_box.append(search_btn)
        
        page.append(search_box)
        
        # Popular extensions section
        popular_label = Gtk.Label()
        popular_label.set_markup("<b>Popular Extensions</b>")
        popular_label.set_halign(Gtk.Align.START)
        popular_label.set_margin_top(12)
        page.append(popular_label)
        
        # Scrollable list
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        self.extensions_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        
        # Add popular extensions
        for ext in POPULAR_EXTENSIONS:
            installed = ext['uuid'] in self.installed_extensions
            enabled = self.installed_extensions.get(ext['uuid'], {}).get('enabled', False)
            row = ExtensionRow(
                ext,
                installed=installed,
                enabled=enabled,
                on_install=self._on_extension_install,
                on_toggle=self._on_extension_toggle,
                on_uninstall=self._on_extension_uninstall
            )
            self.extensions_list.append(row)
        
        scroll.set_child(self.extensions_list)
        page.append(scroll)
        
        return page
    
    def _create_tweaks_page(self) -> Gtk.Widget:
        """Create the tweaks settings page."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        page.set_margin_start(24)
        page.set_margin_end(24)
        page.set_margin_top(12)
        page.set_margin_bottom(12)
        
        # Section: Window Controls
        window_label = Gtk.Label()
        window_label.set_markup("<b>Window Controls</b>")
        window_label.set_halign(Gtk.Align.START)
        page.append(window_label)
        
        window_frame = Gtk.Frame()
        window_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        window_box.append(TweakRow("window_buttons", TWEAKS_SETTINGS["window_buttons"]))
        window_frame.set_child(window_box)
        page.append(window_frame)
        
        # Section: Top Bar
        topbar_label = Gtk.Label()
        topbar_label.set_markup("<b>Top Bar</b>")
        topbar_label.set_halign(Gtk.Align.START)
        topbar_label.set_margin_top(12)
        page.append(topbar_label)
        
        topbar_frame = Gtk.Frame()
        topbar_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        topbar_box.append(TweakRow("show_weekday", TWEAKS_SETTINGS["show_weekday"]))
        topbar_box.append(TweakRow("show_seconds", TWEAKS_SETTINGS["show_seconds"]))
        topbar_box.append(TweakRow("show_battery_percentage", TWEAKS_SETTINGS["show_battery_percentage"]))
        topbar_frame.set_child(topbar_box)
        page.append(topbar_frame)
        
        # Section: Behavior
        behavior_label = Gtk.Label()
        behavior_label.set_markup("<b>Behavior</b>")
        behavior_label.set_halign(Gtk.Align.START)
        behavior_label.set_margin_top(12)
        page.append(behavior_label)
        
        behavior_frame = Gtk.Frame()
        behavior_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        behavior_box.append(TweakRow("hot_corners", TWEAKS_SETTINGS["hot_corners"]))
        behavior_box.append(TweakRow("animations", TWEAKS_SETTINGS["animations"]))
        behavior_box.append(TweakRow("night_light", TWEAKS_SETTINGS["night_light"]))
        behavior_frame.set_child(behavior_box)
        page.append(behavior_frame)
        
        # Section: Input
        input_label = Gtk.Label()
        input_label.set_markup("<b>Mouse & Touchpad</b>")
        input_label.set_halign(Gtk.Align.START)
        input_label.set_margin_top(12)
        page.append(input_label)
        
        input_frame = Gtk.Frame()
        input_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        input_box.append(TweakRow("touchpad_tap_to_click", TWEAKS_SETTINGS["touchpad_tap_to_click"]))
        input_box.append(TweakRow("touchpad_natural_scroll", TWEAKS_SETTINGS["touchpad_natural_scroll"]))
        input_box.append(TweakRow("mouse_natural_scroll", TWEAKS_SETTINGS["mouse_natural_scroll"]))
        input_frame.set_child(input_box)
        page.append(input_frame)
        
        # Spacer
        spacer = Gtk.Box()
        spacer.set_vexpand(True)
        page.append(spacer)
        
        return page
    
    def _create_installed_page(self) -> Gtk.Widget:
        """Create the installed extensions management page."""
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        page.set_margin_start(24)
        page.set_margin_end(24)
        page.set_margin_top(12)
        page.set_margin_bottom(12)
        
        # Header with refresh button
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        
        installed_label = Gtk.Label()
        installed_label.set_markup(f"<b>Installed Extensions ({len(self.installed_extensions)})</b>")
        installed_label.set_halign(Gtk.Align.START)
        installed_label.set_hexpand(True)
        header_box.append(installed_label)
        
        refresh_btn = Gtk.Button(label="Refresh")
        refresh_btn.connect('clicked', self._on_refresh_installed)
        header_box.append(refresh_btn)
        
        page.append(header_box)
        
        # Scrollable list
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        
        self.installed_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self._populate_installed_list()
        
        scroll.set_child(self.installed_list)
        page.append(scroll)
        
        return page
    
    def _populate_installed_list(self):
        """Populate the installed extensions list."""
        # Clear existing
        while child := self.installed_list.get_first_child():
            self.installed_list.remove(child)
        
        if not self.installed_extensions:
            empty_label = Gtk.Label(label="No extensions installed")
            empty_label.add_css_class('dim-label')
            self.installed_list.append(empty_label)
            return
        
        for uuid, status in self.installed_extensions.items():
            ext_data = {'uuid': uuid, 'name': uuid.split('@')[0], 'description': uuid}
            # Check if it's a popular one we know about
            for pop in POPULAR_EXTENSIONS:
                if pop['uuid'] == uuid:
                    ext_data = pop
                    break
            
            row = ExtensionRow(
                ext_data,
                installed=True,
                enabled=status.get('enabled', False),
                on_toggle=self._on_extension_toggle,
                on_uninstall=self._on_extension_uninstall
            )
            self.installed_list.append(row)
    
    def _on_search(self, widget):
        """Handle extension search."""
        query = self.search_entry.get_text().strip()
        if not query:
            return
        
        self.status_label.set_text(f"Searching for '{query}'...")
        
        # Run search in background thread
        def do_search():
            results = search_extensions(query, self.shell_version)
            GLib.idle_add(self._update_search_results, results)
        
        thread = threading.Thread(target=do_search)
        thread.daemon = True
        thread.start()
    
    def _update_search_results(self, results):
        """Update the extensions list with search results."""
        # Clear current list
        while child := self.extensions_list.get_first_child():
            self.extensions_list.remove(child)
        
        if not results:
            empty_label = Gtk.Label(label="No extensions found")
            empty_label.add_css_class('dim-label')
            self.extensions_list.append(empty_label)
            self.status_label.set_text("No results found")
            return
        
        for ext in results:
            uuid = ext.get('uuid', '')
            installed = uuid in self.installed_extensions
            enabled = self.installed_extensions.get(uuid, {}).get('enabled', False)
            
            row = ExtensionRow(
                ext,
                installed=installed,
                enabled=enabled,
                on_install=self._on_extension_install,
                on_toggle=self._on_extension_toggle,
                on_uninstall=self._on_extension_uninstall
            )
            self.extensions_list.append(row)
        
        self.status_label.set_text(f"Found {len(results)} extensions")
    
    def _on_extension_install(self, uuid: str, ext_data: dict):
        """Handle extension installation."""
        self.status_label.set_text(f"Installing {ext_data.get('name', uuid)}...")
        
        def do_install():
            # Try using gnome-extensions-cli if available, otherwise use D-Bus
            success = False
            
            # First try: gnome-extensions install (GNOME 40+)
            try:
                # We need the extension package number for the API
                pk = ext_data.get('pk')
                if pk:
                    # Download from extensions.gnome.org
                    shell_ver = self.shell_version or "45"
                    url = f"https://extensions.gnome.org/extension-info/?pk={pk}&shell_version={shell_ver}"
                    
                    req = urllib.request.Request(url)
                    req.add_header('User-Agent', 'LinuxToolkit/4.5')
                    
                    with urllib.request.urlopen(req, timeout=10) as response:
                        info = json.loads(response.read().decode())
                        download_url = info.get('download_url')
                        
                        if download_url:
                            # Download the zip
                            full_url = f"https://extensions.gnome.org{download_url}"
                            
                            import tempfile
                            import os
                            
                            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
                                tmp_path = tmp.name
                                urllib.request.urlretrieve(full_url, tmp_path)
                            
                            # Install using gnome-extensions
                            result = subprocess.run(
                                ['gnome-extensions', 'install', '--force', tmp_path],
                                capture_output=True,
                                text=True
                            )
                            
                            os.unlink(tmp_path)
                            
                            if result.returncode == 0:
                                success = True
                                # Enable the extension
                                subprocess.run(['gnome-extensions', 'enable', uuid], capture_output=True)
            except Exception as e:
                print(f"Install error: {e}")
            
            GLib.idle_add(self._on_install_complete, uuid, success)
        
        thread = threading.Thread(target=do_install)
        thread.daemon = True
        thread.start()
    
    def _on_install_complete(self, uuid: str, success: bool):
        """Handle installation completion."""
        if success:
            self.status_label.set_text(f"Installed {uuid}! You may need to log out for changes to take effect.")
            self.installed_extensions[uuid] = {"installed": True, "enabled": True}
            self._populate_installed_list()
        else:
            self.status_label.set_text(f"Failed to install {uuid}")
    
    def _on_extension_toggle(self, uuid: str, enabled: bool):
        """Handle extension enable/disable."""
        if enabled:
            success = enable_extension(uuid)
            action = "Enabled"
        else:
            success = disable_extension(uuid)
            action = "Disabled"
        
        if success:
            self.status_label.set_text(f"{action} {uuid}")
            if uuid in self.installed_extensions:
                self.installed_extensions[uuid]['enabled'] = enabled
        else:
            self.status_label.set_text(f"Failed to {action.lower()} {uuid}")
    
    def _on_extension_uninstall(self, uuid: str):
        """Handle extension uninstallation."""
        if uninstall_extension(uuid):
            self.status_label.set_text(f"Uninstalled {uuid}")
            if uuid in self.installed_extensions:
                del self.installed_extensions[uuid]
            self._populate_installed_list()
        else:
            self.status_label.set_text(f"Failed to uninstall {uuid}")
    
    def _on_refresh_installed(self, button):
        """Refresh the installed extensions list."""
        self.installed_extensions = get_installed_extensions()
        self._populate_installed_list()
        self.status_label.set_text(f"Refreshed - {len(self.installed_extensions)} extensions installed")


# =============================================================================
# Application
# =============================================================================

class GnomeManagerApp(Adw.Application):
    """GTK Application for GNOME Enhancements Manager."""
    
    def __init__(self):
        super().__init__(
            application_id='com.linuxtoolkit.gnome-manager',
            flags=Gio.ApplicationFlags.FLAGS_NONE
        )
    
    def do_activate(self):
        """Handle application activation."""
        win = GnomeManagerWindow(self)
        win.present()


def launch_gnome_manager():
    """Launch the GNOME Manager GUI."""
    app = GnomeManagerApp()
    app.run(None)


# =============================================================================
# Main
# =============================================================================

if __name__ == '__main__':
    launch_gnome_manager()
