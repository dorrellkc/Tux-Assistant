"""
Tux Assistant - Main GTK4 Application

The main application class using GTK4 and libadwaita.
Dynamically discovers and loads modules from the modules directory.

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
"""

import sys
import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Gtk, Adw, Gio, GLib, Gdk

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
            license="All Rights Reserved",
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
        
        default_width, default_height = 1100, 800
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
    
    def build_ui(self):
        """Build the main user interface."""
        # Main layout
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.set_content(self.main_box)
        
        # Header bar
        header = Adw.HeaderBar()
        
        # Menu button
        menu_button = Gtk.MenuButton()
        menu_button.set_icon_name("open-menu-symbolic")
        menu_button.set_menu_model(self.create_menu())
        header.pack_end(menu_button)
        
        self.main_box.append(header)
        
        # Toast overlay for notifications
        self.toast_overlay = Adw.ToastOverlay()
        self.main_box.append(self.toast_overlay)
        
        # Navigation view for page switching
        self.navigation_view = Adw.NavigationView()
        self.toast_overlay.set_child(self.navigation_view)
        
        # Create main page
        main_page = self.create_main_page()
        self.navigation_view.add(main_page)
    
    def create_menu(self) -> Gio.Menu:
        """Create the application menu."""
        menu = Gio.Menu()
        menu.append("About Tux Assistant", "app.about")
        menu.append("Quit", "app.quit")
        return menu
    
    def create_main_page(self) -> Adw.NavigationPage:
        """Create the main navigation page with dynamically discovered modules."""
        page = Adw.NavigationPage(title="Tux Assistant")
        
        # Scrollable content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        page.set_child(scrolled)
        
        # Content box with clamp for max width
        clamp = Adw.Clamp()
        clamp.set_maximum_size(950)  # Wider to use more of the larger window
        clamp.set_margin_top(24)
        clamp.set_margin_bottom(24)
        clamp.set_margin_start(24)
        clamp.set_margin_end(24)
        scrolled.set_child(clamp)
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        clamp.set_child(content_box)
        
        # System info banner
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
        """Install hardinfo2 with pre-wiring for AUR/repos if needed."""
        button.set_sensitive(False)
        button.set_label("Installing...")
        
        import threading
        
        def install_thread():
            from .core import run_sudo, detect_aur_helper, DistroFamily
            import subprocess
            
            success = False
            message = ""
            
            try:
                if self.distro.family == DistroFamily.ARCH:
                    # Need AUR helper for Arch
                    aur_helper = detect_aur_helper()
                    if aur_helper:
                        result = subprocess.run(
                            [aur_helper, '-S', '--noconfirm', 'hardinfo2'],
                            capture_output=True,
                            text=True
                        )
                        success = result.returncode == 0
                        message = "hardinfo2 installed!" if success else result.stderr
                    else:
                        # Install yay first
                        message = "Installing AUR helper (yay) first..."
                        GLib.idle_add(lambda: button.set_label(message))
                        
                        # Install base-devel and git if needed
                        subprocess.run(
                            ['pkexec', 'pacman', '-S', '--noconfirm', '--needed', 'base-devel', 'git'],
                            capture_output=True
                        )
                        
                        # Clone and build yay
                        import tempfile
                        import os
                        with tempfile.TemporaryDirectory() as tmpdir:
                            subprocess.run(
                                ['git', 'clone', 'https://aur.archlinux.org/yay.git', tmpdir],
                                capture_output=True
                            )
                            result = subprocess.run(
                                ['makepkg', '-si', '--noconfirm'],
                                cwd=tmpdir,
                                capture_output=True
                            )
                        
                        if subprocess.run(['which', 'yay'], capture_output=True).returncode == 0:
                            # Now install hardinfo2
                            result = subprocess.run(
                                ['yay', '-S', '--noconfirm', 'hardinfo2'],
                                capture_output=True,
                                text=True
                            )
                            success = result.returncode == 0
                            message = "hardinfo2 installed!" if success else result.stderr
                        else:
                            message = "Failed to install AUR helper"
                            
                elif self.distro.family == DistroFamily.DEBIAN:
                    result = subprocess.run(
                        ['pkexec', 'apt-get', 'install', '-y', 'hardinfo2'],
                        capture_output=True,
                        text=True
                    )
                    success = result.returncode == 0
                    if not success and 'Unable to locate' in result.stderr:
                        # Try enabling backports for Debian 12
                        message = "Enabling backports..."
                        GLib.idle_add(lambda: button.set_label(message))
                        # This would need backports setup - simplified for now
                        message = "hardinfo2 not available - may need backports enabled"
                    else:
                        message = "hardinfo2 installed!" if success else result.stderr
                        
                elif self.distro.family == DistroFamily.FEDORA:
                    result = subprocess.run(
                        ['pkexec', 'dnf', 'install', '-y', 'hardinfo2'],
                        capture_output=True,
                        text=True
                    )
                    success = result.returncode == 0
                    message = "hardinfo2 installed!" if success else result.stderr
                    
                elif self.distro.family == DistroFamily.SUSE:
                    result = subprocess.run(
                        ['pkexec', 'zypper', 'install', '-y', 'hardinfo2'],
                        capture_output=True,
                        text=True
                    )
                    success = result.returncode == 0
                    message = "hardinfo2 installed!" if success else result.stderr
                else:
                    message = "Unsupported distribution"
                    
            except Exception as e:
                message = str(e)
            
            GLib.idle_add(self._on_hardinfo2_install_complete, success, message, button)
        
        threading.Thread(target=install_thread, daemon=True).start()
    
    def _on_hardinfo2_install_complete(self, success, message, button):
        """Handle hardinfo2 installation completion."""
        from .core import check_hardinfo2_available
        
        if success and check_hardinfo2_available():
            self.show_toast("hardinfo2 installed! Infrastructure ready for future tools.")
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
        else:
            self.show_toast(f"Installation failed: {message}")
            button.set_label("Install hardinfo2 (Recommended)")
            button.set_sensitive(True)
    
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
