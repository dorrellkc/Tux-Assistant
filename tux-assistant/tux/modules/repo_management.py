"""
Repo Management Module

Foundational module for managing distribution repositories.
This should be the FIRST thing users configure - everything else depends on proper repos.

Supports:
- Debian/Ubuntu: Backports, Universe, Multiverse
- Fedora: RPM Fusion (free + nonfree)
- openSUSE: Packman
- Arch: Multilib, AUR helpers

Copyright (c) 2025 Christopher Dorrell. Licensed under GPL-3.0.
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


# =============================================================================
# Repo Status Checking Functions
# =============================================================================

def check_debian_backports() -> bool:
    """Check if Debian backports is enabled."""
    try:
        result = subprocess.run(
            ['grep', '-r', 'backports', '/etc/apt/sources.list', '/etc/apt/sources.list.d/'],
            capture_output=True, text=True, timeout=5
        )
        # Check for uncommented backports line
        for line in result.stdout.splitlines():
            if 'backports' in line and not line.strip().startswith('#'):
                return True
        return False
    except:
        return False


def check_ubuntu_universe() -> bool:
    """Check if Ubuntu universe repo is enabled."""
    try:
        result = subprocess.run(
            ['apt-cache', 'policy'],
            capture_output=True, text=True, timeout=10
        )
        return 'universe' in result.stdout
    except:
        return False


def check_rpmfusion() -> tuple:
    """Check if RPM Fusion repos are enabled. Returns (free_enabled, nonfree_enabled)."""
    try:
        result = subprocess.run(['rpm', '-qa'], capture_output=True, text=True, timeout=10)
        packages = result.stdout.lower()
        free = 'rpmfusion-free-release' in packages
        nonfree = 'rpmfusion-nonfree-release' in packages
        return (free, nonfree)
    except:
        return (False, False)


def check_packman() -> bool:
    """Check if Packman repo is enabled on openSUSE."""
    try:
        result = subprocess.run(['zypper', 'lr'], capture_output=True, text=True, timeout=10)
        return 'packman' in result.stdout.lower()
    except:
        return False


def check_arch_multilib() -> bool:
    """Check if multilib repo is enabled on Arch."""
    try:
        with open('/etc/pacman.conf', 'r') as f:
            content = f.read()
        # Look for uncommented [multilib] section
        import re
        match = re.search(r'^\[multilib\]', content, re.MULTILINE)
        if match:
            # Check if the next non-empty line is not commented
            lines = content[match.end():].split('\n')
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                if line.startswith('#'):
                    return False
                if line.startswith('Include'):
                    return True
                break
        return False
    except:
        return False


def detect_aur_helper() -> str:
    """Detect which AUR helper is installed."""
    helpers = ['yay', 'paru', 'pikaur', 'trizen', 'aurman']
    for helper in helpers:
        try:
            result = subprocess.run(['which', helper], capture_output=True, timeout=5)
            if result.returncode == 0:
                return helper
        except:
            continue
    return ""


def get_debian_codename() -> str:
    """Get Debian/Ubuntu codename."""
    try:
        result = subprocess.run(
            ['lsb_release', '-cs'],
            capture_output=True, text=True, timeout=5
        )
        return result.stdout.strip()
    except:
        return ""


# =============================================================================
# Module Registration
# =============================================================================

@register_module(
    id="repo_management",
    name="Repository Management",
    description="Configure package repositories and sources",
    icon="drive-multidisk-symbolic",
    category=ModuleCategory.SETUP,
    order=1  # FIRST in Setup category - everything depends on this
)
class RepoManagementPage(Adw.NavigationPage):
    """Repository management module page."""
    
    def __init__(self, window):
        super().__init__()
        self.window = window
        self.distro = get_distro()
        
        self.set_title("Repository Management")
        self._build_ui()
    
    def _build_ui(self):
        """Build the repository management UI."""
        # Main container
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)
        
        # Scrollable content
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        toolbar_view.set_content(scroll)
        
        # Content box
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        content.set_margin_top(24)
        content.set_margin_bottom(24)
        content.set_margin_start(24)
        content.set_margin_end(24)
        scroll.set_child(content)
        
        # Intro
        intro_group = Adw.PreferencesGroup()
        intro_group.set_title("📦 Package Repositories")
        intro_group.set_description(
            "Configure additional repositories to access more software. "
            "This is the first step for a complete system setup."
        )
        content.append(intro_group)
        
        # Build distro-specific UI
        if self.distro.family == DistroFamily.DEBIAN:
            self._build_debian_ui(content)
        elif self.distro.family == DistroFamily.FEDORA:
            self._build_fedora_ui(content)
        elif self.distro.family == DistroFamily.OPENSUSE:
            self._build_opensuse_ui(content)
        elif self.distro.family == DistroFamily.ARCH:
            self._build_arch_ui(content)
        else:
            self._build_unsupported_ui(content)
        
        # Refresh button at bottom
        refresh_btn = Gtk.Button(label="Refresh Status")
        refresh_btn.add_css_class("pill")
        refresh_btn.set_halign(Gtk.Align.CENTER)
        refresh_btn.set_margin_top(12)
        refresh_btn.connect("clicked", self._on_refresh)
        content.append(refresh_btn)
    
    # =========================================================================
    # Debian/Ubuntu UI
    # =========================================================================
    
    def _build_debian_ui(self, content):
        """Build Debian/Ubuntu specific UI."""
        codename = get_debian_codename()
        is_ubuntu = 'ubuntu' in self.distro.name.lower()
        
        # Backports section
        backports_group = Adw.PreferencesGroup()
        backports_group.set_title("🔄 Backports Repository")
        backports_group.set_description(
            "Newer versions of packages from testing, rebuilt for stable. "
            "Recommended for newer hardware support and applications like hardinfo2."
        )
        content.append(backports_group)
        
        backports_enabled = check_debian_backports()
        
        backports_row = Adw.ActionRow()
        backports_row.set_title(f"{codename}-backports" if codename else "Backports")
        backports_row.add_prefix(Gtk.Image.new_from_icon_name("software-update-available-symbolic"))
        
        if backports_enabled:
            backports_row.set_subtitle("Newer packages from testing")
            status_label = Gtk.Label(label="✓ Enabled")
            status_label.add_css_class("success")
            status_label.set_valign(Gtk.Align.CENTER)
            backports_row.add_suffix(status_label)
        else:
            backports_row.set_subtitle("Not enabled - some packages may be unavailable")
            enable_btn = Gtk.Button(label="Enable")
            enable_btn.add_css_class("suggested-action")
            enable_btn.set_valign(Gtk.Align.CENTER)
            enable_btn.connect("clicked", self._enable_debian_backports, codename)
            backports_row.add_suffix(enable_btn)
        
        backports_group.add(backports_row)
        
        # Universe/Multiverse (Ubuntu only)
        if is_ubuntu:
            universe_group = Adw.PreferencesGroup()
            universe_group.set_title("🌌 Universe & Multiverse")
            universe_group.set_description(
                "Community-maintained and restricted packages. "
                "Required for many applications."
            )
            content.append(universe_group)
            
            universe_enabled = check_ubuntu_universe()
            
            universe_row = Adw.ActionRow()
            universe_row.set_title("Universe Repository")
            universe_row.add_prefix(Gtk.Image.new_from_icon_name("starred-symbolic"))
            
            if universe_enabled:
                universe_row.set_subtitle("Community-maintained packages")
                status_label = Gtk.Label(label="✓ Enabled")
                status_label.add_css_class("success")
                status_label.set_valign(Gtk.Align.CENTER)
                universe_row.add_suffix(status_label)
            else:
                universe_row.set_subtitle("Not enabled")
                enable_btn = Gtk.Button(label="Enable")
                enable_btn.add_css_class("suggested-action")
                enable_btn.set_valign(Gtk.Align.CENTER)
                enable_btn.connect("clicked", self._enable_ubuntu_universe)
                universe_row.add_suffix(enable_btn)
            
            universe_group.add(universe_row)
        
        # Custom repo section for Debian/Ubuntu
        self._build_custom_repo_section(content, "debian")
    
    def _enable_debian_backports(self, button, codename):
        """Enable Debian backports repository."""
        button.set_sensitive(False)
        button.set_label("Enabling...")
        
        def do_enable():
            try:
                # Create backports source file
                backports_line = f"deb http://deb.debian.org/debian {codename}-backports main contrib non-free"
                
                # Write to sources.list.d
                cmd = f'echo "{backports_line}" | sudo tee /etc/apt/sources.list.d/backports.list'
                
                result = subprocess.run(
                    ['pkexec', 'bash', '-c', cmd],
                    capture_output=True, text=True, timeout=30
                )
                
                if result.returncode == 0:
                    # Update apt cache
                    subprocess.run(
                        ['pkexec', 'apt-get', 'update'],
                        capture_output=True, timeout=120
                    )
                    GLib.idle_add(self._on_enable_success, button, "Backports enabled!")
                else:
                    GLib.idle_add(self._on_enable_failed, button, "Failed to enable backports")
            except Exception as e:
                GLib.idle_add(self._on_enable_failed, button, str(e))
        
        threading.Thread(target=do_enable, daemon=True).start()
    
    def _enable_ubuntu_universe(self, button):
        """Enable Ubuntu universe repository."""
        button.set_sensitive(False)
        button.set_label("Enabling...")
        
        def do_enable():
            try:
                result = subprocess.run(
                    ['pkexec', 'add-apt-repository', '-y', 'universe'],
                    capture_output=True, text=True, timeout=60
                )
                
                if result.returncode == 0:
                    subprocess.run(
                        ['pkexec', 'apt-get', 'update'],
                        capture_output=True, timeout=120
                    )
                    GLib.idle_add(self._on_enable_success, button, "Universe enabled!")
                else:
                    GLib.idle_add(self._on_enable_failed, button, "Failed to enable universe")
            except Exception as e:
                GLib.idle_add(self._on_enable_failed, button, str(e))
        
        threading.Thread(target=do_enable, daemon=True).start()
    
    # =========================================================================
    # Fedora UI
    # =========================================================================
    
    def _build_fedora_ui(self, content):
        """Build Fedora specific UI."""
        rpmfusion_group = Adw.PreferencesGroup()
        rpmfusion_group.set_title("🎬 RPM Fusion")
        rpmfusion_group.set_description(
            "Additional packages not included in Fedora due to licensing. "
            "Required for multimedia codecs, NVIDIA drivers, and many applications."
        )
        content.append(rpmfusion_group)
        
        free_enabled, nonfree_enabled = check_rpmfusion()
        print(f"[RepoMgmt] RPM Fusion check: free={free_enabled}, nonfree={nonfree_enabled}")
        
        # Free repo
        free_row = Adw.ActionRow()
        free_row.set_title("RPM Fusion Free")
        free_row.set_subtitle("Open source packages (FFmpeg, VLC, etc.)")
        
        if free_enabled:
            free_row.add_prefix(Gtk.Image.new_from_icon_name("object-select-symbolic"))
            status_label = Gtk.Label(label="✓ Enabled")
            status_label.add_css_class("success")
            status_label.set_valign(Gtk.Align.CENTER)
            free_row.add_suffix(status_label)
        else:
            free_row.add_prefix(Gtk.Image.new_from_icon_name("circle-outline-thick-symbolic"))
            btn = Gtk.Button(label="Enable")
            btn.add_css_class("suggested-action")
            btn.set_valign(Gtk.Align.CENTER)
            btn.connect("clicked", self._enable_rpmfusion, "free")
            free_row.add_suffix(btn)
        
        rpmfusion_group.add(free_row)
        
        # Nonfree repo
        nonfree_row = Adw.ActionRow()
        nonfree_row.set_title("RPM Fusion Nonfree")
        nonfree_row.set_subtitle("Proprietary packages (NVIDIA drivers, Steam, etc.)")
        
        if nonfree_enabled:
            nonfree_row.add_prefix(Gtk.Image.new_from_icon_name("object-select-symbolic"))
            status_label = Gtk.Label(label="✓ Enabled")
            status_label.add_css_class("success")
            status_label.set_valign(Gtk.Align.CENTER)
            nonfree_row.add_suffix(status_label)
        else:
            nonfree_row.add_prefix(Gtk.Image.new_from_icon_name("circle-outline-thick-symbolic"))
            btn = Gtk.Button(label="Enable")
            btn.add_css_class("suggested-action")
            btn.set_valign(Gtk.Align.CENTER)
            btn.connect("clicked", self._enable_rpmfusion, "nonfree")
            nonfree_row.add_suffix(btn)
        
        rpmfusion_group.add(nonfree_row)
        
        # Enable both button if neither enabled
        if not free_enabled or not nonfree_enabled:
            both_row = Adw.ActionRow()
            both_row.set_title("Enable Both")
            both_row.set_subtitle("Recommended for full codec and driver support")
            
            both_btn = Gtk.Button(label="Enable All")
            both_btn.add_css_class("suggested-action")
            both_btn.set_valign(Gtk.Align.CENTER)
            both_btn.connect("clicked", self._enable_rpmfusion, "both")
            both_row.add_suffix(both_btn)
            
            rpmfusion_group.add(both_row)
        
        # Custom repo section for Fedora
        self._build_custom_repo_section(content, "fedora")
    
    def _enable_rpmfusion(self, button, repo_type):
        """Enable RPM Fusion repository."""
        button.set_sensitive(False)
        button.set_label("Enabling...")
        
        def do_enable():
            try:
                # Get Fedora version
                fedora_ver = subprocess.run(
                    ['rpm', '-E', '%fedora'],
                    capture_output=True, text=True, timeout=5
                ).stdout.strip()
                
                urls = []
                if repo_type in ("free", "both"):
                    urls.append(f"https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-{fedora_ver}.noarch.rpm")
                if repo_type in ("nonfree", "both"):
                    urls.append(f"https://download1.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-{fedora_ver}.noarch.rpm")
                
                for url in urls:
                    result = subprocess.run(
                        ['pkexec', 'dnf', 'install', '-y', url],
                        capture_output=True, text=True, timeout=120
                    )
                    if result.returncode != 0:
                        GLib.idle_add(self._on_enable_failed, button, "Failed to enable RPM Fusion")
                        return
                
                GLib.idle_add(self._on_enable_success, button, "RPM Fusion enabled!")
            except Exception as e:
                GLib.idle_add(self._on_enable_failed, button, str(e))
        
        threading.Thread(target=do_enable, daemon=True).start()
    
    # =========================================================================
    # openSUSE UI
    # =========================================================================
    
    def _build_opensuse_ui(self, content):
        """Build openSUSE specific UI."""
        packman_group = Adw.PreferencesGroup()
        packman_group.set_title("📦 Packman Repository")
        packman_group.set_description(
            "Additional multimedia packages and codecs not included in openSUSE. "
            "Required for full video and audio playback support."
        )
        content.append(packman_group)
        
        packman_enabled = check_packman()
        
        packman_row = Adw.ActionRow()
        packman_row.set_title("Packman Essentials")
        packman_row.set_subtitle("Multimedia codecs and libraries")
        packman_row.add_prefix(Gtk.Image.new_from_icon_name("folder-music-symbolic"))
        
        if packman_enabled:
            status_label = Gtk.Label(label="✓ Enabled")
            status_label.add_css_class("success")
            status_label.set_valign(Gtk.Align.CENTER)
            packman_row.add_suffix(status_label)
        else:
            btn = Gtk.Button(label="Enable")
            btn.add_css_class("suggested-action")
            btn.set_valign(Gtk.Align.CENTER)
            btn.connect("clicked", self._enable_packman)
            packman_row.add_suffix(btn)
        
        packman_group.add(packman_row)
        
        # Custom repo section for openSUSE
        self._build_custom_repo_section(content, "opensuse")
    
    def _enable_packman(self, button):
        """Enable Packman repository on openSUSE."""
        button.set_sensitive(False)
        button.set_label("Enabling...")
        
        def do_enable():
            try:
                # Detect Tumbleweed vs Leap
                result = subprocess.run(
                    ['cat', '/etc/os-release'],
                    capture_output=True, text=True, timeout=5
                )
                
                if 'tumbleweed' in result.stdout.lower():
                    repo_url = "https://ftp.gwdg.de/pub/linux/misc/packman/suse/openSUSE_Tumbleweed/Essentials/"
                else:
                    # Leap - try to get version
                    import re
                    match = re.search(r'VERSION_ID="?(\d+\.\d+)"?', result.stdout)
                    if match:
                        version = match.group(1)
                        repo_url = f"https://ftp.gwdg.de/pub/linux/misc/packman/suse/openSUSE_Leap_{version}/Essentials/"
                    else:
                        repo_url = "https://ftp.gwdg.de/pub/linux/misc/packman/suse/openSUSE_Tumbleweed/Essentials/"
                
                # Add repo
                result = subprocess.run(
                    ['pkexec', 'zypper', 'ar', '-cfp', '90', repo_url, 'packman-essentials'],
                    capture_output=True, text=True, timeout=60
                )
                
                if result.returncode == 0 or 'already exists' in result.stderr:
                    # Refresh and switch packages
                    subprocess.run(
                        ['pkexec', 'zypper', '--gpg-auto-import-keys', 'refresh'],
                        capture_output=True, timeout=120
                    )
                    GLib.idle_add(self._on_enable_success, button, "Packman enabled!")
                else:
                    GLib.idle_add(self._on_enable_failed, button, "Failed to add Packman repo")
            except Exception as e:
                GLib.idle_add(self._on_enable_failed, button, str(e))
        
        threading.Thread(target=do_enable, daemon=True).start()
    
    # =========================================================================
    # Arch UI
    # =========================================================================
    
    def _build_arch_ui(self, content):
        """Build Arch Linux specific UI."""
        # Multilib section
        multilib_group = Adw.PreferencesGroup()
        multilib_group.set_title("🎮 Multilib Repository")
        multilib_group.set_description(
            "32-bit libraries required for Steam, Wine, and gaming. "
            "Essential for running Windows games and applications."
        )
        content.append(multilib_group)
        
        multilib_enabled = check_arch_multilib()
        
        multilib_row = Adw.ActionRow()
        multilib_row.set_title("multilib")
        multilib_row.set_subtitle("32-bit compatibility libraries")
        multilib_row.add_prefix(Gtk.Image.new_from_icon_name("application-x-executable-symbolic"))
        
        if multilib_enabled:
            status_label = Gtk.Label(label="✓ Enabled")
            status_label.add_css_class("success")
            status_label.set_valign(Gtk.Align.CENTER)
            multilib_row.add_suffix(status_label)
        else:
            btn = Gtk.Button(label="Enable")
            btn.add_css_class("suggested-action")
            btn.set_valign(Gtk.Align.CENTER)
            btn.connect("clicked", self._enable_multilib)
            multilib_row.add_suffix(btn)
        
        multilib_group.add(multilib_row)
        
        # AUR Helper section
        aur_group = Adw.PreferencesGroup()
        aur_group.set_title("📦 AUR Helper")
        aur_group.set_description(
            "Arch User Repository (AUR) contains community packages. "
            "An AUR helper makes installing and updating AUR packages easy."
        )
        content.append(aur_group)
        
        current_helper = detect_aur_helper()
        
        aur_row = Adw.ActionRow()
        aur_row.set_title("AUR Helper")
        aur_row.add_prefix(Gtk.Image.new_from_icon_name("system-software-install-symbolic"))
        
        if current_helper:
            aur_row.set_subtitle(f"{current_helper} installed")
            status_label = Gtk.Label(label="✓ Ready")
            status_label.add_css_class("success")
            status_label.set_valign(Gtk.Align.CENTER)
            aur_row.add_suffix(status_label)
        else:
            aur_row.set_subtitle("No AUR helper detected")
            btn = Gtk.Button(label="Install yay")
            btn.add_css_class("suggested-action")
            btn.set_valign(Gtk.Align.CENTER)
            btn.connect("clicked", self._install_yay)
            aur_row.add_suffix(btn)
        
        aur_group.add(aur_row)
        
        # Custom repo section for Arch
        self._build_custom_repo_section(content, "arch")
    
    def _enable_multilib(self, button):
        """Enable multilib repository on Arch."""
        button.set_sensitive(False)
        button.set_label("Enabling...")
        
        def do_enable():
            try:
                # Read current pacman.conf
                with open('/etc/pacman.conf', 'r') as f:
                    content = f.read()
                
                # Uncomment [multilib] section
                import re
                # Find commented multilib section and uncomment it
                new_content = re.sub(
                    r'#\[multilib\]\n#Include = /etc/pacman\.d/mirrorlist',
                    '[multilib]\nInclude = /etc/pacman.d/mirrorlist',
                    content
                )
                
                if new_content == content:
                    # Maybe it's formatted differently, try another pattern
                    new_content = re.sub(
                        r'#\[multilib\]',
                        '[multilib]',
                        content
                    )
                    new_content = re.sub(
                        r'#(Include = /etc/pacman\.d/mirrorlist)',
                        r'\1',
                        new_content,
                        count=1  # Only first occurrence after multilib
                    )
                
                # Write to temp file
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.conf', delete=False) as tmp:
                    tmp.write(new_content)
                    tmp_path = tmp.name
                
                # Copy with pkexec
                result = subprocess.run(
                    ['pkexec', 'cp', tmp_path, '/etc/pacman.conf'],
                    capture_output=True, text=True, timeout=30
                )
                
                os.unlink(tmp_path)
                
                if result.returncode == 0:
                    # Sync repos
                    subprocess.run(
                        ['pkexec', 'pacman', '-Sy'],
                        capture_output=True, timeout=120
                    )
                    GLib.idle_add(self._on_enable_success, button, "Multilib enabled!")
                else:
                    GLib.idle_add(self._on_enable_failed, button, "Failed to enable multilib")
            except Exception as e:
                GLib.idle_add(self._on_enable_failed, button, str(e))
        
        threading.Thread(target=do_enable, daemon=True).start()
    
    def _install_yay(self, button):
        """Install yay AUR helper."""
        button.set_sensitive(False)
        button.set_label("Installing...")
        
        def do_install():
            try:
                # Install base-devel and git
                subprocess.run(
                    ['pkexec', 'pacman', '-S', '--needed', '--noconfirm', 'base-devel', 'git'],
                    capture_output=True, timeout=120
                )
                
                # Clone and build yay
                import tempfile
                with tempfile.TemporaryDirectory() as tmpdir:
                    subprocess.run(
                        ['git', 'clone', 'https://aur.archlinux.org/yay.git', tmpdir],
                        capture_output=True, timeout=60
                    )
                    
                    result = subprocess.run(
                        ['makepkg', '-si', '--noconfirm'],
                        cwd=tmpdir,
                        capture_output=True, text=True, timeout=300
                    )
                    
                    if result.returncode == 0:
                        GLib.idle_add(self._on_enable_success, button, "yay installed!")
                    else:
                        GLib.idle_add(self._on_enable_failed, button, "Failed to build yay")
            except Exception as e:
                GLib.idle_add(self._on_enable_failed, button, str(e))
        
        threading.Thread(target=do_install, daemon=True).start()
    
    # =========================================================================
    # Unsupported/Generic UI
    # =========================================================================
    
    def _build_unsupported_ui(self, content):
        """Build UI for unsupported distros."""
        info_group = Adw.PreferencesGroup()
        info_group.set_title("ℹ️ Distribution Not Supported")
        info_group.set_description(
            f"Automatic repository management is not yet available for {self.distro.name}. "
            "Please configure repositories manually using your distribution's tools."
        )
        content.append(info_group)
    
    # =========================================================================
    # Custom Repository Section
    # =========================================================================
    
    def _build_custom_repo_section(self, content, distro_type: str):
        """Build the custom repository entry section."""
        custom_group = Adw.PreferencesGroup()
        custom_group.set_title("➕ Add Custom Repository")
        
        if distro_type == "debian":
            custom_group.set_description(
                "Add a PPA (Ubuntu) or custom APT repository line. "
                "Example: ppa:user/repo or deb http://example.com/repo stable main"
            )
            placeholder = "ppa:user/repo or deb http://..."
        elif distro_type == "fedora":
            custom_group.set_description(
                "Add a COPR repository. Example: user/project"
            )
            placeholder = "user/project (COPR)"
        elif distro_type == "opensuse":
            custom_group.set_description(
                "Add an OBS repository URL or zypper repo command."
            )
            placeholder = "https://download.opensuse.org/..."
        elif distro_type == "arch":
            custom_group.set_description(
                "Add a custom repository. This will be appended to pacman.conf."
            )
            placeholder = "Server = https://..."
        else:
            placeholder = "Repository URL or identifier"
        
        content.append(custom_group)
        
        # Entry row for repo input
        entry_row = Adw.EntryRow()
        entry_row.set_title("Repository")
        entry_row.set_text("")
        
        # Store reference for the button callback
        self._custom_repo_entry = entry_row
        self._custom_repo_distro = distro_type
        
        # Add button
        add_btn = Gtk.Button(label="Add")
        add_btn.add_css_class("suggested-action")
        add_btn.set_valign(Gtk.Align.CENTER)
        add_btn.connect("clicked", self._on_add_custom_repo)
        entry_row.add_suffix(add_btn)
        
        custom_group.add(entry_row)
        
        # Help text row
        help_row = Adw.ActionRow()
        help_row.set_title("Need help?")
        
        if distro_type == "debian":
            help_row.set_subtitle("PPAs require 'software-properties-common' package")
        elif distro_type == "fedora":
            help_row.set_subtitle("Find COPR repos at copr.fedorainfracloud.org")
        elif distro_type == "opensuse":
            help_row.set_subtitle("Find repos at software.opensuse.org")
        elif distro_type == "arch":
            help_row.set_subtitle("Custom repos need [reponame] section and Server line")
        
        help_row.add_prefix(Gtk.Image.new_from_icon_name("dialog-question-symbolic"))
        custom_group.add(help_row)
    
    def _on_add_custom_repo(self, button):
        """Handle adding a custom repository."""
        repo_input = self._custom_repo_entry.get_text().strip()
        
        if not repo_input:
            self.window.show_toast("Please enter a repository")
            return
        
        button.set_sensitive(False)
        button.set_label("Adding...")
        
        distro_type = self._custom_repo_distro
        
        def do_add():
            try:
                success = False
                
                if distro_type == "debian":
                    if repo_input.startswith("ppa:"):
                        # Add PPA
                        result = subprocess.run(
                            ['pkexec', 'add-apt-repository', '-y', repo_input],
                            capture_output=True, text=True, timeout=60
                        )
                        success = result.returncode == 0
                    else:
                        # Add custom deb line
                        filename = repo_input.split()[1].replace('http://', '').replace('https://', '').replace('/', '-')[:30]
                        result = subprocess.run(
                            ['pkexec', 'bash', '-c', f'echo "{repo_input}" > /etc/apt/sources.list.d/{filename}.list'],
                            capture_output=True, text=True, timeout=30
                        )
                        success = result.returncode == 0
                    
                    if success:
                        subprocess.run(['pkexec', 'apt-get', 'update'], capture_output=True, timeout=120)
                
                elif distro_type == "fedora":
                    # Add COPR repo
                    result = subprocess.run(
                        ['pkexec', 'dnf', 'copr', 'enable', '-y', repo_input],
                        capture_output=True, text=True, timeout=60
                    )
                    success = result.returncode == 0
                
                elif distro_type == "opensuse":
                    # Add zypper repo
                    result = subprocess.run(
                        ['pkexec', 'zypper', 'ar', '-f', repo_input, 'custom-repo'],
                        capture_output=True, text=True, timeout=60
                    )
                    success = result.returncode == 0 or 'already exists' in result.stderr
                    
                    if success:
                        subprocess.run(
                            ['pkexec', 'zypper', '--gpg-auto-import-keys', 'refresh'],
                            capture_output=True, timeout=120
                        )
                
                elif distro_type == "arch":
                    # This is more complex - user needs to provide full repo config
                    # For now, just show instructions
                    GLib.idle_add(self.window.show_toast, "For Arch, manually edit /etc/pacman.conf")
                    GLib.idle_add(button.set_label, "Add")
                    GLib.idle_add(button.set_sensitive, True)
                    return
                
                if success:
                    GLib.idle_add(self._on_enable_success, button, f"Repository added!")
                    GLib.idle_add(self._custom_repo_entry.set_text, "")
                else:
                    GLib.idle_add(self._on_enable_failed, button, "Failed to add repository")
                    
            except Exception as e:
                GLib.idle_add(self._on_enable_failed, button, str(e))
        
        threading.Thread(target=do_add, daemon=True).start()
    
    # =========================================================================
    # Common Callbacks
    # =========================================================================
    
    def _on_enable_success(self, button, message):
        """Handle successful enable."""
        button.set_label("✓ Done")
        button.set_sensitive(False)
        button.remove_css_class("suggested-action")
        button.add_css_class("success")
        self.window.show_toast(message)
    
    def _on_enable_failed(self, button, message):
        """Handle failed enable."""
        button.set_label("Retry")
        button.set_sensitive(True)
        self.window.show_toast(f"Error: {message[:50]}")
    
    def _on_refresh(self, button):
        """Refresh the page to update status."""
        # Rebuild the UI by navigating away and back
        self.window.show_toast("Refreshing...")
        # Simple approach: just recreate the page content
        parent = self.get_child()
        if parent:
            self.set_child(None)
        self._build_ui()
