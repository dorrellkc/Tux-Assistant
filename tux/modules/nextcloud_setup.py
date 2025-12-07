"""
Tux Assistant - Nextcloud Server Setup Module

Self-hosted Nextcloud server with:
- Apache + PHP + MariaDB + Redis
- Let's Encrypt SSL
- DuckDNS dynamic DNS
- Desktop client integration

Makes Grandpa cool with his own cloud. ☁️

Copyright (c) 2025 Christopher Dorrell. Licensed under GPL-3.0.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

import os
import sys
import subprocess
import threading
import json
import tempfile
from gi.repository import Gtk, Adw, GLib, Gio
from typing import Optional, Callable
from dataclasses import dataclass

from ..core import get_distro, DistroFamily
from .registry import register_module, ModuleCategory


# =============================================================================
# Configuration
# =============================================================================

NEXTCLOUD_VERSION = "29.0.0"  # Latest stable as of writing
NEXTCLOUD_DOWNLOAD_URL = f"https://download.nextcloud.com/server/releases/nextcloud-{NEXTCLOUD_VERSION}.tar.bz2"

# Package requirements per distro family
PACKAGES = {
    DistroFamily.ARCH: {
        'webserver': ['apache'],
        'php': [
            'php', 'php-apache', 'php-gd', 'php-intl', 'php-sodium',
            'php-apcu', 'php-redis', 'php-imagick'
        ],
        'database': ['mariadb'],
        'cache': ['redis'],
        'tools': ['certbot', 'certbot-apache', 'wget', 'unzip'],
        'ddns': ['ddclient'],
    },
    DistroFamily.DEBIAN: {
        'webserver': ['apache2', 'libapache2-mod-php'],
        'php': [
            'php', 'php-gd', 'php-mysql', 'php-curl', 'php-mbstring',
            'php-intl', 'php-gmp', 'php-bcmath', 'php-xml', 'php-zip',
            'php-apcu', 'php-redis', 'php-imagick', 'php-ldap'
        ],
        'database': ['mariadb-server', 'mariadb-client'],
        'cache': ['redis-server'],
        'tools': ['certbot', 'python3-certbot-apache', 'wget', 'unzip', 'bzip2'],
        'ddns': ['ddclient'],
    },
    DistroFamily.FEDORA: {
        'webserver': ['httpd', 'mod_ssl'],
        'php': [
            'php', 'php-gd', 'php-mysqlnd', 'php-curl', 'php-mbstring',
            'php-intl', 'php-gmp', 'php-bcmath', 'php-xml', 'php-zip',
            'php-pecl-apcu', 'php-pecl-redis5', 'php-pecl-imagick', 'php-ldap',
            'php-opcache', 'php-json', 'php-sodium'
        ],
        'database': ['mariadb-server', 'mariadb'],
        'cache': ['redis'],
        'tools': ['certbot', 'python3-certbot-apache', 'wget', 'unzip', 'bzip2'],
        'ddns': ['ddclient'],
    },
    DistroFamily.OPENSUSE: {
        'webserver': ['apache2', 'apache2-mod_php8'],
        'php': [
            'php8', 'php8-gd', 'php8-mysql', 'php8-curl', 'php8-mbstring',
            'php8-intl', 'php8-gmp', 'php8-bcmath', 'php8-xmlreader', 'php8-zip',
            'php8-APCu', 'php8-redis', 'php8-imagick', 'php8-ldap',
            'php8-opcache', 'php8-sodium'
        ],
        'database': ['mariadb', 'mariadb-client'],
        'cache': ['redis'],
        'tools': ['certbot', 'wget', 'unzip', 'bzip2'],
        'ddns': ['ddclient'],
    },
}

# Service names per distro
SERVICES = {
    DistroFamily.ARCH: {
        'webserver': 'httpd',
        'database': 'mariadb',
        'cache': 'redis',
    },
    DistroFamily.DEBIAN: {
        'webserver': 'apache2',
        'database': 'mariadb',
        'cache': 'redis-server',
    },
    DistroFamily.FEDORA: {
        'webserver': 'httpd',
        'database': 'mariadb',
        'cache': 'redis',
    },
    DistroFamily.OPENSUSE: {
        'webserver': 'apache2',
        'database': 'mariadb',
        'cache': 'redis',
    },
}

# Apache config paths
APACHE_PATHS = {
    DistroFamily.ARCH: {
        'conf_dir': '/etc/httpd/conf/extra',
        'sites_enabled': '/etc/httpd/conf/extra',
        'main_conf': '/etc/httpd/conf/httpd.conf',
        'php_conf': '/etc/httpd/conf/extra/php_module.conf',
    },
    DistroFamily.DEBIAN: {
        'conf_dir': '/etc/apache2/sites-available',
        'sites_enabled': '/etc/apache2/sites-enabled',
        'main_conf': '/etc/apache2/apache2.conf',
        'php_conf': None,  # Handled by libapache2-mod-php
    },
    DistroFamily.FEDORA: {
        'conf_dir': '/etc/httpd/conf.d',
        'sites_enabled': '/etc/httpd/conf.d',
        'main_conf': '/etc/httpd/conf/httpd.conf',
        'php_conf': '/etc/httpd/conf.d/php.conf',
    },
    DistroFamily.OPENSUSE: {
        'conf_dir': '/etc/apache2/vhosts.d',
        'sites_enabled': '/etc/apache2/vhosts.d',
        'main_conf': '/etc/apache2/httpd.conf',
        'php_conf': None,
    },
}


@dataclass
class NextcloudConfig:
    """Configuration for Nextcloud installation."""
    admin_user: str
    admin_pass: str
    data_dir: str
    duckdns_subdomain: str
    duckdns_token: str
    db_name: str = "nextcloud"
    db_user: str = "nextcloud"
    db_pass: str = ""  # Will be generated
    install_dir: str = "/var/www/nextcloud"
    
    @property
    def domain(self) -> str:
        return f"{self.duckdns_subdomain}.duckdns.org"
    
    def generate_db_password(self):
        """Generate a secure random database password."""
        import secrets
        self.db_pass = secrets.token_urlsafe(24)


# =============================================================================
# Nextcloud Setup Wizard UI
# =============================================================================

class NextcloudSetupWizard(Adw.Dialog):
    """Setup wizard for Nextcloud server installation."""
    
    def __init__(self, window, on_complete: Callable[[NextcloudConfig], None]):
        super().__init__()
        
        self.window = window
        self.on_complete = on_complete
        self.distro = get_distro()
        
        self.set_title("Nextcloud Server Setup")
        self.set_content_width(550)
        self.set_content_height(600)
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the wizard UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        toolbar_view.add_top_bar(header)
        
        # Cancel button
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_btn)
        
        # Main scrollable content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        toolbar_view.set_content(scrolled)
        
        # Content box
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        content_box.set_margin_top(24)
        content_box.set_margin_bottom(24)
        content_box.set_margin_start(24)
        content_box.set_margin_end(24)
        scrolled.set_child(content_box)
        
        # Welcome banner
        welcome = Adw.StatusPage()
        welcome.set_icon_name("network-server-symbolic")
        welcome.set_title("Set Up Your Personal Cloud")
        welcome.set_description("Replace Google Drive with your own Nextcloud server.\nJust fill in a few details and we'll handle the rest.")
        content_box.append(welcome)
        
        # Admin Account Group
        admin_group = Adw.PreferencesGroup()
        admin_group.set_title("Administrator Account")
        admin_group.set_description("Create your Nextcloud admin login")
        content_box.append(admin_group)
        
        # Admin username
        self.admin_user_row = Adw.EntryRow()
        self.admin_user_row.set_title("Username")
        self.admin_user_row.set_text("admin")
        admin_group.add(self.admin_user_row)
        
        # Admin password
        self.admin_pass_row = Adw.PasswordEntryRow()
        self.admin_pass_row.set_title("Password")
        admin_group.add(self.admin_pass_row)
        
        # Confirm password
        self.admin_pass_confirm_row = Adw.PasswordEntryRow()
        self.admin_pass_confirm_row.set_title("Confirm Password")
        admin_group.add(self.admin_pass_confirm_row)
        
        # Storage Group
        storage_group = Adw.PreferencesGroup()
        storage_group.set_title("Data Storage")
        storage_group.set_description("Where should your files be stored?")
        content_box.append(storage_group)
        
        # Data directory
        data_row = Adw.ActionRow()
        data_row.set_title("Storage Location")
        data_row.set_subtitle("/var/nextcloud-data")
        
        self.data_dir_entry = Gtk.Entry()
        self.data_dir_entry.set_text("/var/nextcloud-data")
        self.data_dir_entry.set_hexpand(True)
        self.data_dir_entry.set_valign(Gtk.Align.CENTER)
        data_row.add_suffix(self.data_dir_entry)
        
        browse_btn = Gtk.Button(icon_name="folder-open-symbolic")
        browse_btn.set_valign(Gtk.Align.CENTER)
        browse_btn.set_tooltip_text("Browse for folder")
        browse_btn.connect("clicked", self._on_browse_clicked)
        data_row.add_suffix(browse_btn)
        
        storage_group.add(data_row)
        
        # Internet Access Group
        internet_group = Adw.PreferencesGroup()
        internet_group.set_title("Internet Access (DuckDNS)")
        internet_group.set_description("Free dynamic DNS so you can access your cloud from anywhere")
        content_box.append(internet_group)
        
        # Help link
        duckdns_help_row = Adw.ActionRow()
        duckdns_help_row.set_title("Need a DuckDNS account?")
        duckdns_help_row.set_subtitle("It's free and takes 30 seconds")
        duckdns_help_row.set_activatable(True)
        duckdns_help_row.connect("activated", self._on_duckdns_help)
        
        link_icon = Gtk.Image.new_from_icon_name("web-browser-symbolic")
        duckdns_help_row.add_suffix(link_icon)
        internet_group.add(duckdns_help_row)
        
        # DuckDNS subdomain
        subdomain_row = Adw.EntryRow()
        subdomain_row.set_title("Your Subdomain")
        self.subdomain_entry = subdomain_row
        internet_group.add(subdomain_row)
        
        # Show full domain preview
        domain_preview = Adw.ActionRow()
        domain_preview.set_title("Your Cloud Address")
        self.domain_label = Gtk.Label(label="[subdomain].duckdns.org")
        self.domain_label.add_css_class("dim-label")
        domain_preview.add_suffix(self.domain_label)
        internet_group.add(domain_preview)
        
        # Update preview when subdomain changes
        self.subdomain_entry.connect("changed", self._on_subdomain_changed)
        
        # DuckDNS token
        self.token_row = Adw.PasswordEntryRow()
        self.token_row.set_title("DuckDNS Token")
        internet_group.add(self.token_row)
        
        # What will be installed
        info_group = Adw.PreferencesGroup()
        info_group.set_title("What Will Be Installed")
        content_box.append(info_group)
        
        components = [
            ("Apache Web Server", "Serves your Nextcloud"),
            ("PHP 8.x", "Powers Nextcloud"),
            ("MariaDB", "Stores your data"),
            ("Redis", "Speeds things up"),
            ("Let's Encrypt SSL", "Encrypts your connection"),
            ("DuckDNS Client", "Updates your IP automatically"),
            ("Nextcloud Desktop Client", "Sync files from your desktop"),
        ]
        
        for name, desc in components:
            row = Adw.ActionRow()
            row.set_title(name)
            row.set_subtitle(desc)
            row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
            info_group.add(row)
        
        # Install button
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(24)
        content_box.append(button_box)
        
        self.install_btn = Gtk.Button(label="Install Nextcloud Server")
        self.install_btn.add_css_class("suggested-action")
        self.install_btn.add_css_class("pill")
        self.install_btn.connect("clicked", self._on_install_clicked)
        button_box.append(self.install_btn)
        
        # Validation message
        self.validation_label = Gtk.Label()
        self.validation_label.add_css_class("error")
        self.validation_label.set_visible(False)
        content_box.append(self.validation_label)
    
    def _on_subdomain_changed(self, entry):
        """Update domain preview when subdomain changes."""
        subdomain = entry.get_text().strip()
        if subdomain:
            self.domain_label.set_text(f"{subdomain}.duckdns.org")
        else:
            self.domain_label.set_text("[subdomain].duckdns.org")
    
    def _on_browse_clicked(self, button):
        """Open folder chooser for data directory."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Data Storage Location")
        
        # We need to select folders
        dialog.select_folder(self.window, None, self._on_folder_selected)
    
    def _on_folder_selected(self, dialog, result):
        """Handle folder selection."""
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                self.data_dir_entry.set_text(folder.get_path())
        except GLib.Error:
            pass  # User cancelled
    
    def _on_duckdns_help(self, row):
        """Open DuckDNS website."""
        Gtk.show_uri(None, "https://www.duckdns.org/", 0)
    
    def _validate(self) -> tuple[bool, str]:
        """Validate all inputs."""
        # Check admin username
        admin_user = self.admin_user_row.get_text().strip()
        if not admin_user:
            return False, "Please enter an admin username"
        if len(admin_user) < 3:
            return False, "Username must be at least 3 characters"
        
        # Check admin password
        admin_pass = self.admin_pass_row.get_text()
        admin_pass_confirm = self.admin_pass_confirm_row.get_text()
        
        if not admin_pass:
            return False, "Please enter an admin password"
        if len(admin_pass) < 8:
            return False, "Password must be at least 8 characters"
        if admin_pass != admin_pass_confirm:
            return False, "Passwords do not match"
        
        # Check data directory
        data_dir = self.data_dir_entry.get_text().strip()
        if not data_dir:
            return False, "Please specify a data storage location"
        if not data_dir.startswith('/'):
            return False, "Data directory must be an absolute path"
        
        # Check DuckDNS
        subdomain = self.subdomain_entry.get_text().strip()
        if not subdomain:
            return False, "Please enter your DuckDNS subdomain"
        if not subdomain.replace('-', '').replace('_', '').isalnum():
            return False, "Subdomain can only contain letters, numbers, - and _"
        
        token = self.token_row.get_text().strip()
        if not token:
            return False, "Please enter your DuckDNS token"
        
        return True, ""
    
    def _on_install_clicked(self, button):
        """Validate and start installation."""
        valid, message = self._validate()
        
        if not valid:
            self.validation_label.set_text(message)
            self.validation_label.set_visible(True)
            return
        
        self.validation_label.set_visible(False)
        
        # Create config
        config = NextcloudConfig(
            admin_user=self.admin_user_row.get_text().strip(),
            admin_pass=self.admin_pass_row.get_text(),
            data_dir=self.data_dir_entry.get_text().strip(),
            duckdns_subdomain=self.subdomain_entry.get_text().strip(),
            duckdns_token=self.token_row.get_text().strip(),
        )
        config.generate_db_password()
        
        # Close wizard and start installation
        self.close()
        
        if self.on_complete:
            self.on_complete(config)


# =============================================================================
# Installation Progress Dialog
# =============================================================================

class NextcloudInstallDialog(Adw.Dialog):
    """Dialog showing Nextcloud installation progress."""
    
    def __init__(self, window, config: NextcloudConfig):
        super().__init__()
        
        self.window = window
        self.config = config
        self.distro = get_distro()
        self.cancelled = False
        self.success = False
        
        self.set_title("Installing Nextcloud")
        self.set_content_width(600)
        self.set_content_height(500)
        
        self._build_ui()
        self._start_installation()
    
    def _build_ui(self):
        """Build the dialog UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        toolbar_view.add_top_bar(header)
        
        # Cancel button
        self.cancel_btn = Gtk.Button(label="Cancel")
        self.cancel_btn.connect("clicked", self._on_cancel)
        header.pack_start(self.cancel_btn)
        
        # Close button (hidden initially)
        self.close_btn = Gtk.Button(label="Close")
        self.close_btn.connect("clicked", lambda b: self.close())
        self.close_btn.set_visible(False)
        header.pack_end(self.close_btn)
        
        # Content
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content_box.set_margin_top(24)
        content_box.set_margin_bottom(24)
        content_box.set_margin_start(24)
        content_box.set_margin_end(24)
        toolbar_view.set_content(content_box)
        
        # Status label
        self.status_label = Gtk.Label()
        self.status_label.set_markup("<b>Preparing installation...</b>")
        self.status_label.set_halign(Gtk.Align.START)
        content_box.append(self.status_label)
        
        # Current task label
        self.task_label = Gtk.Label()
        self.task_label.add_css_class("dim-label")
        self.task_label.set_halign(Gtk.Align.START)
        content_box.append(self.task_label)
        
        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        content_box.append(self.progress_bar)
        
        # Step list
        steps_group = Adw.PreferencesGroup()
        steps_group.set_title("Installation Steps")
        content_box.append(steps_group)
        
        self.steps = [
            ("packages", "Installing packages", "package-x-generic-symbolic"),
            ("database", "Setting up database", "drive-harddisk-symbolic"),
            ("download", "Downloading Nextcloud", "folder-download-symbolic"),
            ("configure", "Configuring Nextcloud", "emblem-system-symbolic"),
            ("apache", "Configuring web server", "network-server-symbolic"),
            ("ssl", "Setting up SSL certificate", "channel-secure-symbolic"),
            ("duckdns", "Configuring DuckDNS", "network-wireless-symbolic"),
            ("finalize", "Finalizing setup", "emblem-ok-symbolic"),
        ]
        
        self.step_rows = {}
        for step_id, step_name, icon in self.steps:
            row = Adw.ActionRow()
            row.set_title(step_name)
            
            # Status icon
            status_icon = Gtk.Image.new_from_icon_name("content-loading-symbolic")
            status_icon.add_css_class("dim-label")
            row.add_prefix(status_icon)
            
            # Step icon
            row.add_suffix(Gtk.Image.new_from_icon_name(icon))
            
            self.step_rows[step_id] = {'row': row, 'icon': status_icon}
            steps_group.add(row)
        
        # Output view (collapsed by default)
        expander = Gtk.Expander(label="Show Details")
        content_box.append(expander)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_min_content_height(150)
        expander.set_child(scrolled)
        
        self.output_view = Gtk.TextView()
        self.output_view.set_editable(False)
        self.output_view.set_cursor_visible(False)
        self.output_view.set_monospace(True)
        self.output_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        scrolled.set_child(self.output_view)
        
        self.output_buffer = self.output_view.get_buffer()
    
    def _append_output(self, text: str):
        """Append text to output view."""
        end_iter = self.output_buffer.get_end_iter()
        self.output_buffer.insert(end_iter, text + "\n")
    
    def _update_step(self, step_id: str, status: str):
        """Update a step's status icon."""
        if step_id in self.step_rows:
            icon = self.step_rows[step_id]['icon']
            icon.remove_css_class("dim-label")
            icon.remove_css_class("accent")
            icon.remove_css_class("success")
            icon.remove_css_class("error")
            
            if status == 'running':
                icon.set_from_icon_name("emblem-synchronizing-symbolic")
                icon.add_css_class("accent")
            elif status == 'success':
                icon.set_from_icon_name("emblem-ok-symbolic")
                icon.add_css_class("success")
            elif status == 'error':
                icon.set_from_icon_name("dialog-error-symbolic")
                icon.add_css_class("error")
    
    def _update_progress(self, step_num: int, message: str):
        """Update progress bar and status."""
        progress = step_num / len(self.steps)
        self.progress_bar.set_fraction(progress)
        self.progress_bar.set_text(f"{step_num}/{len(self.steps)}")
        self.task_label.set_text(message)
    
    def _start_installation(self):
        """Start the installation in a background thread."""
        thread = threading.Thread(target=self._run_installation, daemon=True)
        thread.start()
    
    def _run_installation(self):
        """Run the installation process."""
        try:
            # Create installation plan
            plan = self._create_installation_plan()
            
            # Write plan to temp file
            plan_file = tempfile.NamedTemporaryFile(
                mode='w', suffix='.json', prefix='nextcloud-plan-', delete=False
            )
            json.dump(plan, plan_file)
            plan_file.close()
            
            GLib.idle_add(self._append_output, f"Installation plan created: {plan_file.name}")
            
            # Find tux-helper
            helper_path = self._find_helper()
            if not helper_path:
                GLib.idle_add(self._append_output, "Error: tux-helper not found!")
                GLib.idle_add(self._installation_failed, "tux-helper not found")
                return
            
            # Ensure helper is executable
            try:
                os.chmod(helper_path, 0o755)
            except:
                pass
            
            # Execute with pkexec
            import shutil
            use_pkexec = shutil.which('pkexec') is not None
            
            if use_pkexec:
                cmd = ['pkexec', helper_path, '--nextcloud-install', plan_file.name]
            else:
                cmd = ['sudo', helper_path, '--nextcloud-install', plan_file.name]
            
            GLib.idle_add(self.status_label.set_markup, "<b>Installing... (authentication required)</b>")
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            current_step = 0
            for line in process.stdout:
                if self.cancelled:
                    process.terminate()
                    break
                
                line = line.strip()
                if not line:
                    continue
                
                GLib.idle_add(self._append_output, line)
                
                # Parse status messages from helper
                if line.startswith('[NC:'):
                    self._parse_status_line(line)
            
            process.wait()
            
            # Clean up plan file
            try:
                os.unlink(plan_file.name)
            except:
                pass
            
            if process.returncode == 0:
                GLib.idle_add(self._installation_complete)
            else:
                GLib.idle_add(self._installation_failed, f"Installation failed (exit code {process.returncode})")
        
        except Exception as e:
            GLib.idle_add(self._append_output, f"Error: {str(e)}")
            GLib.idle_add(self._installation_failed, str(e))
    
    def _parse_status_line(self, line: str):
        """Parse status messages from tux-helper."""
        try:
            # Format: [NC:STEP:STATUS] message
            # e.g., [NC:packages:running] Installing packages...
            end_bracket = line.index(']')
            parts = line[4:end_bracket].split(':')
            
            if len(parts) >= 2:
                step_id = parts[0]
                status = parts[1]
                message = line[end_bracket + 2:] if len(line) > end_bracket + 2 else ""
                
                GLib.idle_add(self._update_step, step_id, status)
                
                if status == 'running':
                    step_num = next((i for i, (sid, _, _) in enumerate(self.steps) if sid == step_id), 0) + 1
                    GLib.idle_add(self._update_progress, step_num, message)
        except:
            pass
    
    def _create_installation_plan(self) -> dict:
        """Create the installation plan for tux-helper."""
        family = self.distro.family
        
        return {
            'type': 'nextcloud_install',
            'family': family.value,
            'config': {
                'admin_user': self.config.admin_user,
                'admin_pass': self.config.admin_pass,
                'data_dir': self.config.data_dir,
                'install_dir': self.config.install_dir,
                'db_name': self.config.db_name,
                'db_user': self.config.db_user,
                'db_pass': self.config.db_pass,
                'domain': self.config.domain,
                'duckdns_subdomain': self.config.duckdns_subdomain,
                'duckdns_token': self.config.duckdns_token,
            },
            'packages': PACKAGES.get(family, {}),
            'services': SERVICES.get(family, {}),
            'apache_paths': APACHE_PATHS.get(family, {}),
            'nextcloud_url': NEXTCLOUD_DOWNLOAD_URL,
        }
    
    def _find_helper(self) -> Optional[str]:
        """Find tux-helper executable."""
        helper_paths = [
            '/usr/bin/tux-helper',
            '/usr/local/bin/tux-helper',
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'tux-helper'),
        ]
        
        for path in helper_paths:
            if os.path.exists(path):
                return path
        return None
    
    def _installation_complete(self):
        """Handle successful installation."""
        self.success = True
        self.progress_bar.set_fraction(1.0)
        self.progress_bar.set_text("Complete!")
        
        self.status_label.set_markup("<b>✓ Nextcloud installed successfully!</b>")
        self.task_label.set_text(f"Access your cloud at: https://{self.config.domain}")
        
        # Mark all steps as complete
        for step_id in self.step_rows:
            self._update_step(step_id, 'success')
        
        self.cancel_btn.set_visible(False)
        self.close_btn.set_visible(True)
        
        self._append_output("")
        self._append_output("=" * 50)
        self._append_output("INSTALLATION COMPLETE!")
        self._append_output("=" * 50)
        self._append_output(f"")
        self._append_output(f"Your Nextcloud is now running at:")
        self._append_output(f"  https://{self.config.domain}")
        self._append_output(f"")
        self._append_output(f"Admin Login:")
        self._append_output(f"  Username: {self.config.admin_user}")
        self._append_output(f"  Password: (the one you entered)")
        self._append_output(f"")
        self._append_output(f"Data stored in: {self.config.data_dir}")
    
    def _installation_failed(self, error: str):
        """Handle failed installation."""
        self.status_label.set_markup(f"<b>✗ Installation failed</b>")
        self.task_label.set_text(error)
        
        self.cancel_btn.set_visible(False)
        self.close_btn.set_visible(True)
    
    def _on_cancel(self, button):
        """Handle cancel button."""
        self.cancelled = True
        button.set_sensitive(False)
        self.task_label.set_text("Cancelling...")


# =============================================================================
# Main Module Page
# =============================================================================

@register_module(
    id="nextcloud_setup",
    name="Nextcloud Server",
    description="Set up your own personal cloud server",
    icon="network-server-symbolic",
    category=ModuleCategory.SERVER,
    order=51  # Specialized tier
)
class NextcloudSetupPage(Adw.NavigationPage):
    """Nextcloud setup module main page."""
    
    def __init__(self, window):
        super().__init__(title="Nextcloud Server")
        
        self.window = window
        self.distro = get_distro()
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the module UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header (NavigationView handles back button automatically)
        header = Adw.HeaderBar()
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
        clamp.set_margin_start(24)
        clamp.set_margin_end(24)
        scrolled.set_child(clamp)
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        clamp.set_child(content_box)
        
        # Hero section
        status_page = Adw.StatusPage()
        status_page.set_icon_name("network-server-symbolic")
        status_page.set_title("Your Personal Cloud")
        status_page.set_description(
            "Replace Google Drive with Nextcloud - your files, your server, your control.\n"
            "Access from anywhere with automatic dynamic DNS."
        )
        content_box.append(status_page)
        
        # Features
        features_group = Adw.PreferencesGroup()
        features_group.set_title("What You Get")
        content_box.append(features_group)
        
        features = [
            ("folder-symbolic", "File Sync", "Sync files across all your devices"),
            ("x-office-calendar-symbolic", "Calendar & Contacts", "Replace Google Calendar (optional apps)"),
            ("channel-secure-symbolic", "Secure Connection", "Automatic HTTPS with Let's Encrypt"),
            ("network-wireless-symbolic", "Access Anywhere", "DuckDNS handles your changing IP"),
            ("computer-symbolic", "Desktop Integration", "Nextcloud client pre-configured"),
        ]
        
        for icon, title, subtitle in features:
            row = Adw.ActionRow()
            row.set_title(title)
            row.set_subtitle(subtitle)
            row.add_prefix(Gtk.Image.new_from_icon_name(icon))
            features_group.add(row)
        
        # Requirements
        req_group = Adw.PreferencesGroup()
        req_group.set_title("What You Need")
        content_box.append(req_group)
        
        requirements = [
            ("emblem-ok-symbolic", "A DuckDNS account", "Free - takes 30 seconds to create"),
            ("emblem-ok-symbolic", "Storage space", "For your files - local drive or mounted storage"),
            ("emblem-ok-symbolic", "Open ports", "Ports 80 and 443 on your router"),
        ]
        
        for icon, title, subtitle in requirements:
            row = Adw.ActionRow()
            row.set_title(title)
            row.set_subtitle(subtitle)
            row.add_prefix(Gtk.Image.new_from_icon_name(icon))
            req_group.add(row)
        
        # Actions
        action_group = Adw.PreferencesGroup()
        content_box.append(action_group)
        
        # Setup button
        setup_row = Adw.ActionRow()
        setup_row.set_title("Set Up Nextcloud Server")
        setup_row.set_subtitle("Install and configure everything automatically")
        setup_row.add_prefix(Gtk.Image.new_from_icon_name("emblem-system-symbolic"))
        setup_row.set_activatable(True)
        setup_row.connect("activated", self._on_setup_clicked)
        
        go_icon = Gtk.Image.new_from_icon_name("go-next-symbolic")
        setup_row.add_suffix(go_icon)
        
        action_group.add(setup_row)
        
        # Install client only
        client_row = Adw.ActionRow()
        client_row.set_title("Install Desktop Client Only")
        client_row.set_subtitle("Connect to an existing Nextcloud server")
        client_row.add_prefix(Gtk.Image.new_from_icon_name("folder-remote-symbolic"))
        client_row.set_activatable(True)
        client_row.connect("activated", self._on_client_only_clicked)
        
        client_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        action_group.add(client_row)
    
    def _on_setup_clicked(self, row):
        """Open the setup wizard."""
        wizard = NextcloudSetupWizard(
            self.window,
            on_complete=self._start_installation
        )
        wizard.present(self.window)
    
    def _start_installation(self, config: NextcloudConfig):
        """Start the installation with the provided config."""
        dialog = NextcloudInstallDialog(self.window, config)
        dialog.present(self.window)
    
    def _on_client_only_clicked(self, row):
        """Install just the Nextcloud desktop client."""
        # TODO: Implement client-only installation
        # For now, show a message
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Install Desktop Client",
            body="This will install the Nextcloud desktop client.\n\nYou can then connect it to any Nextcloud server."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("install", "Install Client")
        dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_client_install_response)
        dialog.present()
    
    def _on_client_install_response(self, dialog, response):
        """Handle client install dialog response."""
        if response == "install":
            self._install_client_only()
    
    def _install_client_only(self):
        """Install just the Nextcloud client."""
        family = self.distro.family
        
        if family == DistroFamily.ARCH:
            pkg = "nextcloud-client"
        elif family == DistroFamily.DEBIAN:
            pkg = "nextcloud-desktop"
        elif family == DistroFamily.FEDORA:
            pkg = "nextcloud-client"
        elif family == DistroFamily.OPENSUSE:
            pkg = "nextcloud-desktop"
        else:
            self.window.show_toast("Unsupported distribution")
            return
        
        # Use tux-helper to install
        # For simplicity, we'll just show the command for now
        self.window.show_toast(f"Installing {pkg}...")
        
        # TODO: Actually run the installation
