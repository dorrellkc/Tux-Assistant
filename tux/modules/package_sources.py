"""
Tux Assistant - Alternative Package Sources Database

Defines where to find packages that aren't in base repositories.
Covers: COPR (Fedora), PPA (Debian/Ubuntu), AUR (Arch), OBS (OpenSUSE), Flatpak (universal)

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class SourceType(Enum):
    """Type of alternative package source."""
    COPR = "copr"           # Fedora COPR
    PPA = "ppa"             # Ubuntu/Debian PPA  
    AUR = "aur"             # Arch User Repository
    OBS = "obs"             # OpenSUSE Build Service
    FLATPAK = "flatpak"     # Flatpak (universal)
    RPMFUSION = "rpmfusion" # RPM Fusion (Fedora)
    PACKMAN = "packman"     # Packman (OpenSUSE)


@dataclass
class PackageSource:
    """Information about an alternative package source."""
    source_type: SourceType
    repo_id: str                        # e.g., "decathorpe/elementary-stable" or Flatpak ID
    package_name: Optional[str] = None  # If different from the base package name
    note: Optional[str] = None          # Additional info for user
    requires_helper: bool = False       # If True, requires AUR helper like yay/paru


# =============================================================================
# Alternative Package Sources Database
# =============================================================================
# Format: package_name -> { distro_family -> PackageSource }
# 
# This is a "living document" - update monthly or as needed when repos change.
# Last updated: 2025-11-28

ALTERNATIVE_SOURCES: dict[str, dict[str, PackageSource]] = {
    
    # =========================================================================
    # Media Applications
    # =========================================================================
    
    "shortwave": {
        # Internet radio app - not in base repos for most distros
        "fedora": PackageSource(
            SourceType.COPR, 
            "decathorpe/elementary-apps",
            note="Elementary apps COPR"
        ),
        "arch": PackageSource(
            SourceType.AUR,
            "shortwave",
            requires_helper=True,
            note="Requires yay or paru"
        ),
        "opensuse": PackageSource(
            SourceType.FLATPAK,
            "de.haeckerfelix.Shortwave",
            note="Available via Flathub"
        ),
        # Debian has it in repos - no alternative needed
    },
    
    "cozy": {
        # Audiobook player
        "fedora": PackageSource(
            SourceType.FLATPAK,
            "com.github.geigi.cozy", 
            note="Available via Flathub"
        ),
        "arch": PackageSource(
            SourceType.AUR,
            "cozy-audiobooks",
            requires_helper=True,
            note="Requires yay or paru"
        ),
        "opensuse": PackageSource(
            SourceType.FLATPAK,
            "com.github.geigi.cozy",
            note="Available via Flathub"
        ),
        # Debian has it in repos
    },
    
    "foliate": {
        # E-book reader
        "fedora": PackageSource(
            SourceType.FLATPAK,
            "com.github.johnfactotum.Foliate",
            note="Available via Flathub"
        ),
        "arch": PackageSource(
            SourceType.AUR,
            "foliate",
            requires_helper=True,
            note="Requires yay or paru"
        ),
        # Debian and OpenSUSE have it in repos
    },
    
    "spotify-client": {
        # Spotify desktop client
        "debian": PackageSource(
            SourceType.PPA,
            "spotify/stable",
            package_name="spotify-client",
            note="Official Spotify repository"
        ),
        "fedora": PackageSource(
            SourceType.FLATPAK,
            "com.spotify.Client",
            note="Available via Flathub"
        ),
        "arch": PackageSource(
            SourceType.AUR,
            "spotify",
            requires_helper=True,
            note="Requires yay or paru"
        ),
        "opensuse": PackageSource(
            SourceType.FLATPAK,
            "com.spotify.Client",
            note="Available via Flathub"
        ),
    },
    
    # =========================================================================
    # Browsers
    # =========================================================================
    
    "google-chrome-stable": {
        "debian": PackageSource(
            SourceType.PPA,
            "google/chrome",
            note="Official Google Chrome repository"
        ),
        "fedora": PackageSource(
            SourceType.COPR,
            "AmatCoder/chromium-browser",
            package_name="chromium-browser",
            note="Chromium (open source alternative)"
        ),
        "arch": PackageSource(
            SourceType.AUR,
            "google-chrome",
            requires_helper=True,
            note="Requires yay or paru"
        ),
    },
    
    "brave-browser": {
        "debian": PackageSource(
            SourceType.PPA,
            "brave/brave-browser",
            note="Official Brave repository"
        ),
        "fedora": PackageSource(
            SourceType.FLATPAK,
            "com.brave.Browser",
            note="Available via Flathub"
        ),
        "arch": PackageSource(
            SourceType.AUR,
            "brave-bin",
            requires_helper=True,
            note="Requires yay or paru"
        ),
        "opensuse": PackageSource(
            SourceType.FLATPAK,
            "com.brave.Browser",
            note="Available via Flathub"
        ),
    },
    
    # =========================================================================
    # Development Tools
    # =========================================================================
    
    "visual-studio-code-bin": {
        "arch": PackageSource(
            SourceType.AUR,
            "visual-studio-code-bin",
            requires_helper=True,
            note="Requires yay or paru"
        ),
    },
    
    "code": {
        # VSCode on Debian/Fedora
        "debian": PackageSource(
            SourceType.PPA,
            "microsoft/vscode",
            note="Official Microsoft VSCode repository"
        ),
        "fedora": PackageSource(
            SourceType.COPR,
            "taw/vscode",
            note="Community COPR"
        ),
    },
    
    "sublime-text": {
        "debian": PackageSource(
            SourceType.PPA,
            "sublimehq/sublime-text",
            note="Official Sublime Text repository"
        ),
        "arch": PackageSource(
            SourceType.AUR,
            "sublime-text-4",
            requires_helper=True,
            note="Requires yay or paru"
        ),
        "fedora": PackageSource(
            SourceType.FLATPAK,
            "com.sublimetext.three",
            note="Available via Flathub"
        ),
    },
    
    # =========================================================================
    # Communication
    # =========================================================================
    
    "discord": {
        "debian": PackageSource(
            SourceType.FLATPAK,
            "com.discordapp.Discord",
            note="Available via Flathub"
        ),
        "fedora": PackageSource(
            SourceType.FLATPAK,
            "com.discordapp.Discord",
            note="Available via Flathub"
        ),
        "arch": PackageSource(
            SourceType.AUR,
            "discord",
            requires_helper=True,
            note="Requires yay or paru"
        ),
        "opensuse": PackageSource(
            SourceType.FLATPAK,
            "com.discordapp.Discord",
            note="Available via Flathub"
        ),
    },
    
    "slack-desktop": {
        "debian": PackageSource(
            SourceType.FLATPAK,
            "com.slack.Slack",
            note="Available via Flathub"
        ),
        "fedora": PackageSource(
            SourceType.FLATPAK,
            "com.slack.Slack",
            note="Available via Flathub"
        ),
        "arch": PackageSource(
            SourceType.AUR,
            "slack-desktop",
            requires_helper=True,
            note="Requires yay or paru"
        ),
        "opensuse": PackageSource(
            SourceType.FLATPAK,
            "com.slack.Slack",
            note="Available via Flathub"
        ),
    },
    
    "zoom": {
        "debian": PackageSource(
            SourceType.FLATPAK,
            "us.zoom.Zoom",
            note="Available via Flathub"
        ),
        "fedora": PackageSource(
            SourceType.FLATPAK,
            "us.zoom.Zoom",
            note="Available via Flathub"
        ),
        "arch": PackageSource(
            SourceType.AUR,
            "zoom",
            requires_helper=True,
            note="Requires yay or paru"
        ),
        "opensuse": PackageSource(
            SourceType.FLATPAK,
            "us.zoom.Zoom",
            note="Available via Flathub"
        ),
    },
    
    # =========================================================================
    # Gaming
    # =========================================================================
    
    "steam": {
        "debian": PackageSource(
            SourceType.PPA,
            "valve/steam",
            note="Requires enabling non-free repos"
        ),
        # Fedora, Arch, OpenSUSE have it in repos (with RPM Fusion for Fedora)
    },
    
    "lutris": {
        # Most distros have this, but not all
        "opensuse": PackageSource(
            SourceType.OBS,
            "games",
            note="Available via games OBS repo"
        ),
    },
    
    # =========================================================================
    # System Tools
    # =========================================================================
    
    "timeshift": {
        "fedora": PackageSource(
            SourceType.COPR,
            "fif/timeshift",
            note="System backup/restore"
        ),
        "arch": PackageSource(
            SourceType.AUR,
            "timeshift",
            requires_helper=True,
            note="Requires yay or paru"
        ),
        # Debian/Ubuntu have it in repos
    },
    
    "stacer": {
        # System optimizer
        "debian": PackageSource(
            SourceType.PPA,
            "oguzhaninan/stacer",
            note="System optimizer"
        ),
        "fedora": PackageSource(
            SourceType.COPR,
            "oguzhaninan/stacer",
            note="System optimizer"
        ),
        "arch": PackageSource(
            SourceType.AUR,
            "stacer",
            requires_helper=True,
            note="Requires yay or paru"
        ),
    },
    
    "btop": {
        # Might not be in older Debian repos
        "debian": PackageSource(
            SourceType.FLATPAK,
            "io.github.aristocratos.btop",
            note="Available via Flathub if not in repos"
        ),
    },
    
    # =========================================================================
    # Multimedia Codecs (special handling - usually auto-enabled)
    # =========================================================================
    
    "libdvdcss": {
        # DVD decryption - requires special repos
        "fedora": PackageSource(
            SourceType.RPMFUSION,
            "rpmfusion-free",
            note="Requires RPM Fusion Free"
        ),
    },
    
    "ffmpeg": {
        # Full ffmpeg with all codecs
        "fedora": PackageSource(
            SourceType.RPMFUSION,
            "rpmfusion-free",
            note="Requires RPM Fusion Free"
        ),
        "opensuse": PackageSource(
            SourceType.PACKMAN,
            "packman",
            note="Requires Packman repository"
        ),
    },
    
    "gstreamer1-plugins-ugly": {
        "fedora": PackageSource(
            SourceType.RPMFUSION,
            "rpmfusion-free",
            note="Requires RPM Fusion Free"
        ),
    },
    
    "gstreamer1-plugins-bad-freeworld": {
        "fedora": PackageSource(
            SourceType.RPMFUSION,
            "rpmfusion-free",
            note="Requires RPM Fusion Free"
        ),
    },
}


def get_alternative_source(package: str, family: str) -> Optional[PackageSource]:
    """Get alternative source for a package on a given distro family.
    
    Args:
        package: Package name
        family: Distro family (arch, debian, fedora, opensuse)
    
    Returns:
        PackageSource if alternative exists, None otherwise
    """
    if package in ALTERNATIVE_SOURCES:
        return ALTERNATIVE_SOURCES[package].get(family)
    return None


def get_all_alternatives_for_family(family: str) -> dict[str, PackageSource]:
    """Get all packages that have alternative sources for a distro family.
    
    Args:
        family: Distro family
        
    Returns:
        Dict of package_name -> PackageSource
    """
    result = {}
    for pkg, sources in ALTERNATIVE_SOURCES.items():
        if family in sources:
            result[pkg] = sources[family]
    return result


def get_source_type_description(source_type: SourceType) -> str:
    """Get human-readable description for a source type."""
    descriptions = {
        SourceType.COPR: "Fedora COPR Repository",
        SourceType.PPA: "Personal Package Archive (PPA)",
        SourceType.AUR: "Arch User Repository (AUR)",
        SourceType.OBS: "OpenSUSE Build Service",
        SourceType.FLATPAK: "Flatpak (Flathub)",
        SourceType.RPMFUSION: "RPM Fusion",
        SourceType.PACKMAN: "Packman Repository",
    }
    return descriptions.get(source_type, source_type.value)


def get_source_enable_info(source: PackageSource) -> dict:
    """Get information about how to enable a source.
    
    Returns dict with:
        - command: CLI command to enable (if applicable)
        - requires_root: Whether it needs sudo/root
        - requires_helper: Whether it needs AUR helper
        - description: Human-readable steps
    """
    info = {
        "command": None,
        "requires_root": True,
        "requires_helper": source.requires_helper,
        "description": "",
    }
    
    if source.source_type == SourceType.COPR:
        info["command"] = f"dnf copr enable -y {source.repo_id}"
        info["description"] = f"Enable COPR: {source.repo_id}"
        
    elif source.source_type == SourceType.PPA:
        info["command"] = f"add-apt-repository -y ppa:{source.repo_id}"
        info["description"] = f"Add PPA: ppa:{source.repo_id}"
        
    elif source.source_type == SourceType.AUR:
        info["requires_root"] = False
        info["requires_helper"] = True
        pkg_name = source.package_name or source.repo_id
        info["command"] = f"yay -S --noconfirm {pkg_name}"  # Or paru
        info["description"] = f"Install from AUR: {pkg_name}"
        
    elif source.source_type == SourceType.FLATPAK:
        info["requires_root"] = False  # User can install flatpaks
        info["command"] = f"flatpak install -y flathub {source.repo_id}"
        info["description"] = f"Install Flatpak: {source.repo_id}"
        
    elif source.source_type == SourceType.RPMFUSION:
        # RPM Fusion is auto-handled by tux-helper, but provide info anyway
        info["description"] = "RPM Fusion (auto-enabled by toolkit)"
        
    elif source.source_type == SourceType.PACKMAN:
        # Packman is auto-handled by tux-helper
        info["description"] = "Packman (auto-enabled by toolkit)"
        
    elif source.source_type == SourceType.OBS:
        info["description"] = f"OpenSUSE Build Service: {source.repo_id}"
    
    return info


# =============================================================================
# Source Verification
# =============================================================================

import subprocess
import shutil

# Cache for verification results
_verification_cache: dict[str, bool] = {}


def verify_source_exists(source: PackageSource, family: str) -> tuple[bool, str]:
    """Verify that an alternative source actually exists/is accessible.
    
    Args:
        source: The PackageSource to verify
        family: Distro family string
        
    Returns:
        Tuple of (exists: bool, message: str)
    """
    cache_key = f"{source.source_type.value}:{source.repo_id}"
    
    if cache_key in _verification_cache:
        return _verification_cache[cache_key], "Cached result"
    
    exists = False
    message = "Unknown"
    
    try:
        if source.source_type == SourceType.FLATPAK:
            # Check if the Flatpak exists on Flathub
            exists, message = _verify_flatpak(source.repo_id)
            
        elif source.source_type == SourceType.AUR:
            # Check if AUR package exists
            exists, message = _verify_aur(source.repo_id)
            
        elif source.source_type == SourceType.COPR:
            # Check if COPR repo exists
            exists, message = _verify_copr(source.repo_id)
            
        elif source.source_type == SourceType.PPA:
            # PPAs are harder to verify without adding them
            # We'll assume they exist if in our database
            exists = True
            message = "PPA in database (not verified)"
            
        elif source.source_type in [SourceType.RPMFUSION, SourceType.PACKMAN]:
            # These are well-known repos, always exist
            exists = True
            message = "Standard repository"
            
        elif source.source_type == SourceType.OBS:
            # OBS repos - assume valid if in database
            exists = True
            message = "OBS repo in database"
        
    except Exception as e:
        exists = False
        message = f"Verification error: {str(e)}"
    
    _verification_cache[cache_key] = exists
    return exists, message


def _verify_flatpak(app_id: str) -> tuple[bool, str]:
    """Verify a Flatpak app exists on Flathub."""
    if not shutil.which('flatpak'):
        return True, "Flatpak not installed (assumed valid)"
    
    try:
        # Search for the app on flathub
        result = subprocess.run(
            ['flatpak', 'search', '--columns=application', app_id],
            capture_output=True, text=True, timeout=30
        )
        
        if app_id in result.stdout:
            return True, "Found on Flathub"
        else:
            return False, "Not found on Flathub"
            
    except subprocess.TimeoutExpired:
        return True, "Verification timeout (assumed valid)"
    except Exception as e:
        return True, f"Could not verify: {e}"


def _verify_aur(pkg_name: str) -> tuple[bool, str]:
    """Verify an AUR package exists."""
    try:
        # Query AUR RPC
        import urllib.request
        import json
        
        url = f"https://aur.archlinux.org/rpc/v5/info/{pkg_name}"
        
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            
            if data.get('resultcount', 0) > 0:
                return True, "Found in AUR"
            else:
                return False, "Not found in AUR"
                
    except Exception as e:
        return True, f"Could not verify AUR: {e}"


def _verify_copr(repo_id: str) -> tuple[bool, str]:
    """Verify a COPR repository exists."""
    try:
        import urllib.request
        
        # COPR API endpoint
        user, project = repo_id.split('/', 1) if '/' in repo_id else (repo_id, '')
        url = f"https://copr.fedorainfracloud.org/api_3/project?ownername={user}&projectname={project}"
        
        with urllib.request.urlopen(url, timeout=10) as response:
            if response.status == 200:
                return True, "COPR project found"
            else:
                return False, "COPR project not found"
                
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False, "COPR project not found"
        return True, f"Could not verify COPR: {e}"
    except Exception as e:
        return True, f"Could not verify COPR: {e}"


def clear_verification_cache():
    """Clear the source verification cache."""
    global _verification_cache
    _verification_cache = {}


# =============================================================================
# User Source Preferences
# =============================================================================

import os
import json

# Default preference order (can be customized by user)
DEFAULT_SOURCE_PREFERENCE = [
    SourceType.FLATPAK,    # Universal, sandboxed, safe
    SourceType.AUR,        # Native packages (Arch)
    SourceType.COPR,       # Native packages (Fedora)
    SourceType.PPA,        # Native packages (Debian/Ubuntu)
    SourceType.OBS,        # Native packages (OpenSUSE)
    SourceType.RPMFUSION,  # Standard repo (Fedora)
    SourceType.PACKMAN,    # Standard repo (OpenSUSE)
]

_user_preferences: dict = None
_preferences_file = os.path.expanduser("~/.config/tux-assistant/source-preferences.json")


def _load_preferences():
    """Load user preferences from file."""
    global _user_preferences
    
    if _user_preferences is not None:
        return
    
    _user_preferences = {
        "source_order": [s.value for s in DEFAULT_SOURCE_PREFERENCE],
        "prefer_flatpak": True,  # If True, always prefer Flatpak when available
        "prefer_native": False,  # If True, prefer native packages over Flatpak
    }
    
    try:
        if os.path.exists(_preferences_file):
            with open(_preferences_file, 'r') as f:
                saved = json.load(f)
                _user_preferences.update(saved)
    except Exception:
        pass  # Use defaults on error


def _save_preferences():
    """Save user preferences to file."""
    if _user_preferences is None:
        return
    
    try:
        os.makedirs(os.path.dirname(_preferences_file), exist_ok=True)
        with open(_preferences_file, 'w') as f:
            json.dump(_user_preferences, f, indent=2)
    except Exception:
        pass  # Best effort


def get_preferred_source(package: str, family: str) -> Optional[PackageSource]:
    """Get the preferred alternative source for a package based on user preferences.
    
    If multiple sources are available for a package, returns the one that
    matches user's preference order.
    
    Args:
        package: Package name
        family: Distro family string
        
    Returns:
        Best matching PackageSource or None
    """
    _load_preferences()
    
    if package not in ALTERNATIVE_SOURCES:
        return None
    
    sources_for_pkg = ALTERNATIVE_SOURCES[package]
    
    if family not in sources_for_pkg:
        # Check if Flatpak is available (universal)
        if 'flatpak' in sources_for_pkg:
            # Any family can use Flatpak
            pass
        else:
            return None
    
    # Get all available sources for this package/family combo
    available_sources = []
    
    # Direct family match
    if family in sources_for_pkg:
        available_sources.append(sources_for_pkg[family])
    
    # Flatpak is available on any distro (if defined)
    for fam, src in sources_for_pkg.items():
        if src.source_type == SourceType.FLATPAK and src not in available_sources:
            available_sources.append(src)
    
    if not available_sources:
        return None
    
    if len(available_sources) == 1:
        return available_sources[0]
    
    # Sort by user preference
    source_order = _user_preferences.get("source_order", [s.value for s in DEFAULT_SOURCE_PREFERENCE])
    
    def sort_key(src):
        try:
            return source_order.index(src.source_type.value)
        except ValueError:
            return 999  # Unknown types go last
    
    available_sources.sort(key=sort_key)
    
    # Apply prefer_flatpak / prefer_native overrides
    if _user_preferences.get("prefer_flatpak", True):
        for src in available_sources:
            if src.source_type == SourceType.FLATPAK:
                return src
    
    if _user_preferences.get("prefer_native", False):
        for src in available_sources:
            if src.source_type != SourceType.FLATPAK:
                return src
    
    return available_sources[0]


def get_all_sources_for_package(package: str, family: str) -> list[PackageSource]:
    """Get all available alternative sources for a package, sorted by preference.
    
    Args:
        package: Package name
        family: Distro family string
        
    Returns:
        List of PackageSource objects, sorted by user preference
    """
    _load_preferences()
    
    if package not in ALTERNATIVE_SOURCES:
        return []
    
    sources_for_pkg = ALTERNATIVE_SOURCES[package]
    available_sources = []
    
    # Direct family match
    if family in sources_for_pkg:
        available_sources.append(sources_for_pkg[family])
    
    # Flatpak works on any distro
    for fam, src in sources_for_pkg.items():
        if src.source_type == SourceType.FLATPAK and src not in available_sources:
            available_sources.append(src)
    
    # Sort by preference
    source_order = _user_preferences.get("source_order", [s.value for s in DEFAULT_SOURCE_PREFERENCE])
    
    def sort_key(src):
        try:
            return source_order.index(src.source_type.value)
        except ValueError:
            return 999
    
    available_sources.sort(key=sort_key)
    return available_sources


def set_source_preference(prefer_flatpak: bool = None, prefer_native: bool = None, 
                          source_order: list[str] = None):
    """Set user source preferences.
    
    Args:
        prefer_flatpak: If True, always prefer Flatpak when available
        prefer_native: If True, prefer native packages (AUR/COPR/PPA) over Flatpak
        source_order: List of source type strings in preferred order
    """
    _load_preferences()
    
    if prefer_flatpak is not None:
        _user_preferences["prefer_flatpak"] = prefer_flatpak
        if prefer_flatpak:
            _user_preferences["prefer_native"] = False
            
    if prefer_native is not None:
        _user_preferences["prefer_native"] = prefer_native
        if prefer_native:
            _user_preferences["prefer_flatpak"] = False
            
    if source_order is not None:
        _user_preferences["source_order"] = source_order
    
    _save_preferences()


def get_source_preferences() -> dict:
    """Get current source preferences.
    
    Returns:
        Dict with prefer_flatpak, prefer_native, source_order
    """
    _load_preferences()
    return _user_preferences.copy()
