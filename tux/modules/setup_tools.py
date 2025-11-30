"""
Tux Assistant - Setup Tools Module

Post-installation setup: codecs, drivers, repositories, and system configuration.

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

import sys
from gi.repository import Gtk, Adw, GLib, Pango
from typing import Callable, Optional
from dataclasses import dataclass
from enum import Enum

from ..core import (
    get_distro, get_desktop, get_package_manager,
    DistroFamily, DesktopEnv,
    run_sudo, run_with_callback, CommandResult
)

from .package_sources import (
    get_alternative_source, get_source_type_description,
    get_source_enable_info, SourceType, PackageSource,
    verify_source_exists, get_preferred_source, get_all_sources_for_package,
    get_source_preferences, set_source_preference
)


class SetupCategory(Enum):
    """Categories of setup tasks."""
    DISTRO = "distro"
    CODECS = "codecs"
    DRIVERS = "drivers"
    REPOS = "repos"
    DESKTOP = "desktop"


@dataclass
class SetupTask:
    """A setup task that can be run."""
    id: str
    name: str
    description: str
    category: SetupCategory
    packages: dict[DistroFamily, list[str]]  # Family -> package list (wishlist)
    commands: dict[DistroFamily, list[list[str]]] = None  # Family -> list of commands
    desktop_specific: Optional[DesktopEnv] = None  # If only for specific DE
    requires_reboot: bool = False
    special_handler: Optional[str] = None  # Handler ID for special post-install setup
    
    def get_packages_for_distro(self, family: DistroFamily) -> list[str]:
        """Get packages for a specific distro family (wishlist - not filtered)."""
        return self.packages.get(family, self.packages.get(DistroFamily.UNKNOWN, []))
    
    def get_commands_for_distro(self, family: DistroFamily) -> list[list[str]]:
        """Get extra commands for a specific distro family."""
        if self.commands is None:
            return []
        return self.commands.get(family, [])


# =============================================================================
# Dynamic Package Availability Checking
# =============================================================================

import subprocess
import json as json_module

# Cache for package availability to avoid repeated checks
_package_availability_cache: dict[str, bool] = {}
_cache_initialized: bool = False


def check_package_available(package: str, family: str) -> bool:
    """Check if a single package is available in the system's repos."""
    cache_key = f"{family}:{package}"
    
    if cache_key in _package_availability_cache:
        return _package_availability_cache[cache_key]
    
    available = False
    try:
        if family == 'debian':
            result = subprocess.run(
                ['apt-cache', 'show', package],
                capture_output=True, text=True, timeout=10
            )
            available = result.returncode == 0 and 'Package:' in result.stdout
        elif family == 'arch':
            result = subprocess.run(
                ['pacman', '-Si', package],
                capture_output=True, text=True, timeout=10
            )
            available = result.returncode == 0
        elif family == 'fedora':
            result = subprocess.run(
                ['dnf', 'info', package],
                capture_output=True, text=True, timeout=15
            )
            available = result.returncode == 0 and 'Name' in result.stdout
        elif family == 'opensuse':
            result = subprocess.run(
                ['zypper', 'info', package],
                capture_output=True, text=True, timeout=15
            )
            available = result.returncode == 0 and 'Name' in result.stdout
        else:
            # Unknown family - assume available
            available = True
    except Exception:
        available = False
    
    _package_availability_cache[cache_key] = available
    return available


def filter_available_packages(packages: list[str], family: str) -> list[str]:
    """Filter a package list to only include packages that are actually available."""
    return [pkg for pkg in packages if check_package_available(pkg, family)]


def get_available_packages_for_task(task: 'SetupTask', family: DistroFamily) -> list[str]:
    """Get only the available packages for a task on the current system."""
    wishlist = task.get_packages_for_distro(family)
    family_str = family.value if hasattr(family, 'value') else str(family)
    return filter_available_packages(wishlist, family_str)


def clear_package_cache():
    """Clear the package availability cache (useful after enabling new repos)."""
    global _package_availability_cache
    _package_availability_cache = {}


# =============================================================================
# Setup Task Definitions
# =============================================================================

MULTIMEDIA_CODECS = SetupTask(
    id="multimedia_codecs",
    name="Multimedia Codecs",
    description="Audio/video codecs including DVD playback (repos auto-enabled)",
    category=SetupCategory.CODECS,
    packages={
        DistroFamily.ARCH: [
            "ffmpeg", "gstreamer", "gst-plugins-base", "gst-plugins-good",
            "gst-plugins-bad", "gst-plugins-ugly", "gst-libav",
            "libdvdcss", "libdvdread", "libdvdnav"
        ],
        DistroFamily.DEBIAN: [
            # Core codecs from official repos
            "ffmpeg", "gstreamer1.0-plugins-base", "gstreamer1.0-plugins-good",
            "gstreamer1.0-plugins-bad", "gstreamer1.0-plugins-ugly",
            "gstreamer1.0-libav", "libavcodec-extra",
            # DVD support - libdvd-pkg downloads/compiles libdvdcss (requires contrib - auto-enabled)
            "libdvd-pkg", "libdvdread8", "libdvdnav4"
        ],
        DistroFamily.FEDORA: [
            # Full codec support - requires RPM Fusion repos
            "ffmpeg", "ffmpeg-libs",
            "gstreamer1-plugins-base", "gstreamer1-plugins-good",
            "gstreamer1-plugins-good-extras",
            "gstreamer1-plugins-bad-free", "gstreamer1-plugins-bad-freeworld",
            "gstreamer1-plugins-ugly",
            "gstreamer1-plugin-openh264", "mozilla-openh264",
            "gstreamer1-libav",
            "libdvdcss"
        ],
        DistroFamily.OPENSUSE: [
            # Full codec support - requires Packman repos
            "ffmpeg", "gstreamer-plugins-base", "gstreamer-plugins-good",
            "gstreamer-plugins-bad", "gstreamer-plugins-ugly",
            "gstreamer-plugins-libav",
            "libdvdcss2"
        ],
    },
    commands={
        DistroFamily.DEBIAN: [
            # Configure libdvd-pkg to download and compile libdvdcss
            ["sudo", "dpkg-reconfigure", "-f", "noninteractive", "libdvd-pkg"]
        ]
    }
)

FIRMWARE_AND_DRIVERS = SetupTask(
    id="firmware_drivers",
    name="Firmware and Drivers",
    description="System firmware and hardware drivers",
    category=SetupCategory.DRIVERS,
    packages={
        DistroFamily.ARCH: [
            "linux-firmware", "fwupd", "sof-firmware"
        ],
        DistroFamily.DEBIAN: [
            "firmware-linux", "firmware-linux-nonfree", "fwupd"
        ],
        DistroFamily.FEDORA: [
            "linux-firmware", "fwupd"
        ],
        DistroFamily.OPENSUSE: [
            "kernel-firmware", "fwupd"
        ],
    }
)

INTEL_GRAPHICS = SetupTask(
    id="intel_graphics",
    name="Intel Graphics",
    description="Intel GPU drivers and Vulkan support",
    category=SetupCategory.DRIVERS,
    packages={
        DistroFamily.ARCH: [
            "mesa", "intel-media-driver", "vulkan-intel", "lib32-mesa", "lib32-vulkan-intel"
        ],
        DistroFamily.DEBIAN: [
            "mesa-vulkan-drivers", "intel-media-va-driver"
        ],
        DistroFamily.FEDORA: [
            "mesa-vulkan-drivers", "intel-media-driver"
        ],
        DistroFamily.OPENSUSE: [
            "Mesa-vulkan-drivers", "intel-media-driver"
        ],
    }
)

AMD_GRAPHICS = SetupTask(
    id="amd_graphics",
    name="AMD Graphics (Open Source)",
    description="AMD GPU open source drivers with Vulkan support - recommended for most users",
    category=SetupCategory.DRIVERS,
    packages={
        DistroFamily.ARCH: [
            "mesa", "vulkan-radeon", "lib32-mesa", "lib32-vulkan-radeon",
            "libva-mesa-driver", "lib32-libva-mesa-driver"
        ],
        DistroFamily.DEBIAN: [
            "mesa-vulkan-drivers", "libdrm-amdgpu1", "xserver-xorg-video-amdgpu"
        ],
        DistroFamily.FEDORA: [
            "mesa-vulkan-drivers", "xorg-x11-drv-amdgpu"
        ],
        DistroFamily.OPENSUSE: [
            "Mesa-vulkan-drivers", "xf86-video-amdgpu"
        ],
    }
)

AMD_PRO_GRAPHICS = SetupTask(
    id="amd_pro_graphics",
    name="AMD PRO Graphics",
    description="AMD PRO drivers for Radeon Pro/Workstation GPUs - OpenCL, Vulkan Pro, AMF encoding",
    category=SetupCategory.DRIVERS,
    packages={
        # Note: AMD PRO requires downloading from AMD and using amdgpu-install
        # These are placeholder packages that work alongside the installer
        DistroFamily.ARCH: [
            "mesa", "vulkan-radeon", "lib32-mesa", "lib32-vulkan-radeon",
            "libva-mesa-driver", "rocm-opencl-runtime"
        ],
        DistroFamily.DEBIAN: [
            "mesa-vulkan-drivers", "libdrm-amdgpu1", "xserver-xorg-video-amdgpu"
        ],
        DistroFamily.FEDORA: [
            "mesa-vulkan-drivers", "xorg-x11-drv-amdgpu"
        ],
    },
    requires_reboot=True
)

# NVIDIA driver options - from newest to legacy
NVIDIA_LATEST = SetupTask(
    id="nvidia_latest",
    name="NVIDIA Latest (580.x)",
    description="Latest production driver - RTX 40/30/20 series, GTX 16/10 series, Quadro",
    category=SetupCategory.DRIVERS,
    packages={
        DistroFamily.ARCH: [
            "nvidia", "nvidia-utils", "lib32-nvidia-utils", "nvidia-settings"
        ],
        DistroFamily.DEBIAN: [
            "nvidia-driver", "nvidia-settings"
        ],
        DistroFamily.FEDORA: [
            "akmod-nvidia", "xorg-x11-drv-nvidia", "xorg-x11-drv-nvidia-cuda"
        ],
        DistroFamily.OPENSUSE: [
            "nvidia-video-G06", "nvidia-gl-G06"
        ],
    },
    requires_reboot=True
)

NVIDIA_550 = SetupTask(
    id="nvidia_550",
    name="NVIDIA 550.x (Stable LTS)",
    description="Stable long-term support driver - Maxwell, Pascal, Volta, Turing, Ampere, Ada",
    category=SetupCategory.DRIVERS,
    packages={
        DistroFamily.ARCH: [
            "nvidia-550xx", "nvidia-550xx-utils", "lib32-nvidia-550xx-utils", "nvidia-settings"
        ],
        DistroFamily.DEBIAN: [
            "nvidia-driver-550", "nvidia-settings"
        ],
        DistroFamily.FEDORA: [
            "akmod-nvidia", "xorg-x11-drv-nvidia", "xorg-x11-drv-nvidia-cuda"
        ],
    },
    requires_reboot=True
)

NVIDIA_535 = SetupTask(
    id="nvidia_535",
    name="NVIDIA 535.x (Legacy LTS)",
    description="Legacy LTS driver - older Maxwell, Pascal, Volta, Turing, Ampere",
    category=SetupCategory.DRIVERS,
    packages={
        DistroFamily.ARCH: [
            "nvidia-535xx", "nvidia-535xx-utils", "lib32-nvidia-535xx-utils", "nvidia-settings"
        ],
        DistroFamily.DEBIAN: [
            "nvidia-driver-535", "nvidia-settings"
        ],
    },
    requires_reboot=True
)

NVIDIA_470_LEGACY = SetupTask(
    id="nvidia_470",
    name="NVIDIA 470.x (Legacy)",
    description="Legacy driver for Kepler GPUs (GTX 600/700 series) - End of support Sep 2024",
    category=SetupCategory.DRIVERS,
    packages={
        DistroFamily.ARCH: [
            "nvidia-470xx-dkms", "nvidia-470xx-utils", "lib32-nvidia-470xx-utils", "nvidia-settings"
        ],
        DistroFamily.DEBIAN: [
            "nvidia-legacy-470xx-driver", "nvidia-settings"
        ],
    },
    requires_reboot=True
)

NVIDIA_390_LEGACY = SetupTask(
    id="nvidia_390",
    name="NVIDIA 390.x (Very Old Legacy)",
    description="Very old legacy driver for Fermi GPUs (GTX 400/500 series) - security updates only",
    category=SetupCategory.DRIVERS,
    packages={
        DistroFamily.ARCH: [
            "nvidia-390xx-dkms", "nvidia-390xx-utils", "lib32-nvidia-390xx-utils"
        ],
        DistroFamily.DEBIAN: [
            "nvidia-legacy-390xx-driver"
        ],
    },
    requires_reboot=True
)

NVIDIA_OPEN = SetupTask(
    id="nvidia_open",
    name="NVIDIA Open Kernel (Experimental)",
    description="Open source kernel modules - RTX 20 series and newer, Turing+ architecture",
    category=SetupCategory.DRIVERS,
    packages={
        DistroFamily.ARCH: [
            "nvidia-open", "nvidia-utils", "lib32-nvidia-utils", "nvidia-settings"
        ],
        DistroFamily.FEDORA: [
            "akmod-nvidia", "xorg-x11-drv-nvidia"
        ],
    },
    requires_reboot=True
)

PRINTING_SUPPORT = SetupTask(
    id="printing",
    name="Printing Support",
    description="CUPS printing system and common drivers",
    category=SetupCategory.DISTRO,
    packages={
        DistroFamily.ARCH: [
            "cups", "cups-pdf", "system-config-printer",
            "gutenprint", "hplip"
        ],
        DistroFamily.DEBIAN: [
            # cups-pdf not available in Debian 13+
            "cups", "system-config-printer",
            "printer-driver-gutenprint", "hplip"
        ],
        DistroFamily.FEDORA: [
            "cups", "cups-pdf", "system-config-printer",
            "gutenprint", "hplip"
        ],
        DistroFamily.OPENSUSE: [
            "cups", "cups-pdf", "system-config-printer",
            "gutenprint", "hplip"
        ],
    }
)

BLUETOOTH_SUPPORT = SetupTask(
    id="bluetooth",
    name="Bluetooth Support",
    description="Bluetooth drivers and management tools",
    category=SetupCategory.DISTRO,
    packages={
        DistroFamily.ARCH: [
            "bluez", "bluez-utils", "blueman"
        ],
        DistroFamily.DEBIAN: [
            "bluez", "bluez-tools", "blueman"
        ],
        DistroFamily.FEDORA: [
            "bluez", "bluez-tools", "blueman"
        ],
        DistroFamily.OPENSUSE: [
            "bluez", "bluez-tools", "blueman"
        ],
    }
)

ARCHIVE_SUPPORT = SetupTask(
    id="archives",
    name="Archive Support",
    description="Support for ZIP, RAR, 7z, and other archives",
    category=SetupCategory.DISTRO,
    packages={
        DistroFamily.ARCH: [
            "unzip", "unrar", "p7zip", "lzip", "lzop"
        ],
        DistroFamily.DEBIAN: [
            # unrar requires non-free - auto-enabled by helper
            "unzip", "unrar", "p7zip-full", "lzip", "lzop"
        ],
        DistroFamily.FEDORA: [
            "unzip", "unrar", "p7zip", "lzip", "lzop"
        ],
        DistroFamily.OPENSUSE: [
            "unzip", "unrar", "p7zip", "lzip", "lzop"
        ],
    }
)

FONTS = SetupTask(
    id="fonts",
    name="Additional Fonts",
    description="Microsoft fonts, Noto, and other font families",
    category=SetupCategory.DISTRO,
    packages={
        DistroFamily.ARCH: [
            "ttf-dejavu", "ttf-liberation", "noto-fonts", "noto-fonts-emoji",
            "ttf-roboto", "ttf-fira-code"
        ],
        DistroFamily.DEBIAN: [
            # ttf-mscorefonts-installer requires contrib - auto-enabled by helper
            "fonts-dejavu", "fonts-liberation", "fonts-noto", "fonts-noto-color-emoji",
            "fonts-roboto", "fonts-firacode", "ttf-mscorefonts-installer"
        ],
        DistroFamily.FEDORA: [
            "dejavu-fonts-all", "liberation-fonts", "google-noto-fonts-common",
            "google-noto-emoji-fonts", "google-roboto-fonts", "fira-code-fonts"
        ],
        DistroFamily.OPENSUSE: [
            "dejavu-fonts", "liberation-fonts", "noto-fonts",
            "google-roboto-fonts", "fira-code-fonts"
        ],
    }
)

EMOJI_SUPPORT = SetupTask(
    id="emoji_support",
    name="Emoji Support",
    description="Emoji picker with Super+. keyboard shortcut",
    category=SetupCategory.DISTRO,
    packages={
        DistroFamily.ARCH: [
            "gnome-characters", "noto-fonts-emoji"
        ],
        DistroFamily.DEBIAN: [
            "gnome-characters", "fonts-noto-color-emoji"
        ],
        DistroFamily.FEDORA: [
            "gnome-characters", "google-noto-emoji-color-fonts"
        ],
        DistroFamily.OPENSUSE: [
            "gnome-characters", "noto-coloremoji-fonts"
        ],
    },
    # Special command to set up keyboard shortcut
    special_handler="emoji_keyboard"
)

XFCE_ENHANCEMENTS = SetupTask(
    id="xfce_enhancements",
    name="XFCE Enhancements",
    description="Super key for Whisker Menu + Thunar Open/Edit as Root + Share folders",
    category=SetupCategory.DESKTOP,
    desktop_specific=DesktopEnv.XFCE,
    packages={
        DistroFamily.ARCH: [
            "xcape", "xfce4-whiskermenu-plugin", "mousepad", "samba"
        ],
        DistroFamily.DEBIAN: [
            "xcape", "xfce4-whiskermenu-plugin", "mousepad", "samba"
        ],
        DistroFamily.FEDORA: [
            "xcape", "xfce4-whiskermenu-plugin", "mousepad", "samba"
        ],
        DistroFamily.OPENSUSE: [
            "xcape", "xfce4-whiskermenu-plugin", "mousepad", "samba"
        ],
    },
    special_handler="xfce_enhancements"
)

KDE_ENHANCEMENTS = SetupTask(
    id="kde_enhancements",
    name="KDE Online Accounts & Extras",
    description="Fix Google/online account integration + media apps",
    category=SetupCategory.DESKTOP,
    desktop_specific=DesktopEnv.KDE,
    packages={
        # Universal wishlist - dynamic filtering will only show what's available
        DistroFamily.ARCH: [
            "kaccounts-integration", "kaccounts-providers", "kio-gdrive",
            "ktorrent", "shortwave", "foliate", "cozy", "vlc", "mpv"
        ],
        DistroFamily.DEBIAN: [
            "kaccounts-integration", "kaccounts-providers", "kio-gdrive",
            "ktorrent", "shortwave", "foliate", "cozy", "vlc", "mpv"
        ],
        DistroFamily.FEDORA: [
            "kaccounts-integration", "kaccounts-providers", "kio-gdrive",
            "ktorrent", "shortwave", "foliate", "cozy", "vlc", "mpv"
        ],
        DistroFamily.OPENSUSE: [
            "kaccounts-integration", "kaccounts-providers", "kio-gdrive",
            "ktorrent", "shortwave", "foliate", "cozy", "vlc", "mpv"
        ],
    },
    special_handler="kde_enhancements"
)

GNOME_ENHANCEMENTS = SetupTask(
    id="gnome_enhancements",
    name="GNOME Extensions & Tweaks Manager",
    description="GUI tool to browse/install extensions and customize GNOME settings",
    category=SetupCategory.DESKTOP,
    desktop_specific=DesktopEnv.GNOME,
    packages={
        DistroFamily.ARCH: [
            "gnome-tweaks", "gnome-shell-extensions", "dconf-editor",
            "python-gobject", "libadwaita"
        ],
        DistroFamily.DEBIAN: [
            "gnome-tweaks", "gnome-shell-extensions", "dconf-editor",
            "python3-gi", "gir1.2-adw-1", "gir1.2-gtk-4.0"
        ],
        DistroFamily.FEDORA: [
            "gnome-tweaks", "gnome-extensions-app", "dconf-editor",
            "python3-gobject", "libadwaita"
        ],
        DistroFamily.OPENSUSE: [
            "gnome-tweaks", "gnome-shell-extensions", "dconf-editor",
            "python3-gobject", "libadwaita", "typelib-1_0-Adw-1"
        ],
    },
    special_handler="gnome_enhancements"
)

ESSENTIAL_TOOLS = SetupTask(
    id="essential_tools",
    name="Essential Tools",
    description="Common utilities: git, curl, htop, fastfetch, etc.",
    category=SetupCategory.DISTRO,
    packages={
        DistroFamily.ARCH: [
            "git", "curl", "wget", "htop", "btop", "neofetch", "fastfetch",
            "vim", "nano", "rsync", "tree", "bat", "fd", "ripgrep"
        ],
        DistroFamily.DEBIAN: [
            # neofetch removed in Debian 13+, use fastfetch
            "git", "curl", "wget", "htop", "fastfetch",
            "vim", "nano", "rsync", "tree", "bat", "fd-find", "ripgrep"
        ],
        DistroFamily.FEDORA: [
            "git", "curl", "wget", "htop", "btop", "neofetch", "fastfetch",
            "vim-enhanced", "nano", "rsync", "tree", "bat", "fd-find", "ripgrep"
        ],
        DistroFamily.OPENSUSE: [
            "git", "curl", "wget", "htop", "fastfetch",
            "vim", "nano", "rsync", "tree", "bat", "fd", "ripgrep"
        ],
    }
)

# NOTE: RPM Fusion and Packman repos are now AUTOMATICALLY enabled by tux-helper
# when installing packages that need them. No manual task needed!

# Flatpak setup
FLATPAK_SETUP = SetupTask(
    id="flatpak",
    name="Flatpak and Flathub",
    description="Install Flatpak and add Flathub repository",
    category=SetupCategory.REPOS,
    packages={
        DistroFamily.ARCH: ["flatpak"],
        DistroFamily.DEBIAN: ["flatpak", "gnome-software-plugin-flatpak"],
        DistroFamily.FEDORA: ["flatpak"],
        DistroFamily.OPENSUSE: ["flatpak"],
    },
    commands={
        DistroFamily.ARCH: [
            ["flatpak", "remote-add", "--if-not-exists", "flathub", 
             "https://dl.flathub.org/repo/flathub.flatpakrepo"]
        ],
        DistroFamily.DEBIAN: [
            ["flatpak", "remote-add", "--if-not-exists", "flathub",
             "https://dl.flathub.org/repo/flathub.flatpakrepo"]
        ],
        DistroFamily.FEDORA: [
            ["flatpak", "remote-add", "--if-not-exists", "flathub",
             "https://dl.flathub.org/repo/flathub.flatpakrepo"]
        ],
        DistroFamily.OPENSUSE: [
            ["flatpak", "remote-add", "--if-not-exists", "flathub",
             "https://dl.flathub.org/repo/flathub.flatpakrepo"]
        ],
    }
)

# =============================================================================
# Virtualization
# =============================================================================

VIRTUALBOX = SetupTask(
    id="virtualbox",
    name="VirtualBox",
    description="Oracle VirtualBox with user added to vboxusers group",
    category=SetupCategory.DISTRO,
    packages={
        DistroFamily.ARCH: [
            "virtualbox", "virtualbox-host-modules-arch", "virtualbox-guest-iso"
        ],
        DistroFamily.DEBIAN: [
            "virtualbox", "virtualbox-ext-pack", "virtualbox-guest-additions-iso"
        ],
        DistroFamily.FEDORA: [
            # Fedora needs RPM Fusion for VirtualBox - auto-enabled!
            "VirtualBox", "akmod-VirtualBox", "virtualbox-guest-additions"
        ],
        DistroFamily.OPENSUSE: [
            "virtualbox", "virtualbox-host-source", "virtualbox-guest-tools"
        ],
    },
    special_handler="virtualbox_setup",
    requires_reboot=True
)

VIRT_MANAGER = SetupTask(
    id="virt_manager",
    name="Virt-Manager (QEMU/KVM)",
    description="Full virtualization with QEMU/KVM, libvirt, and virt-manager GUI",
    category=SetupCategory.DISTRO,
    packages={
        DistroFamily.ARCH: [
            "qemu-full", "libvirt", "virt-manager", "virt-viewer",
            "dnsmasq", "bridge-utils", "openbsd-netcat", "edk2-ovmf"
        ],
        DistroFamily.DEBIAN: [
            "qemu-system", "qemu-utils", "libvirt-daemon-system", "libvirt-clients",
            "virt-manager", "virt-viewer", "virtinst",
            "dnsmasq-base", "bridge-utils", "ovmf"
        ],
        DistroFamily.FEDORA: [
            "qemu-kvm", "libvirt", "virt-manager", "virt-viewer", "virt-install",
            "dnsmasq", "bridge-utils", "edk2-ovmf"
        ],
        DistroFamily.OPENSUSE: [
            "qemu-kvm", "libvirt", "virt-manager", "virt-viewer", "virt-install",
            "dnsmasq", "bridge-utils", "qemu-ovmf-x86_64"
        ],
    },
    special_handler="virtmanager_setup",
    requires_reboot=True
)

# Snap removal (Ubuntu-only)
SNAP_REMOVAL = SetupTask(
    id="snap_removal",
    name="Remove Snap Completely",
    description="Remove all snaps and snapd, block future installation (Ubuntu only)",
    category=SetupCategory.DISTRO,
    packages={
        DistroFamily.DEBIAN: [],  # No packages to install - this removes things
    },
    special_handler="snap_removal",
    requires_reboot=True
)


# All available tasks
ALL_TASKS = [
    ESSENTIAL_TOOLS,
    MULTIMEDIA_CODECS,
    ARCHIVE_SUPPORT,
    FONTS,
    EMOJI_SUPPORT,
    XFCE_ENHANCEMENTS,
    KDE_ENHANCEMENTS,
    GNOME_ENHANCEMENTS,
    FIRMWARE_AND_DRIVERS,
    INTEL_GRAPHICS,
    AMD_GRAPHICS,
    AMD_PRO_GRAPHICS,
    NVIDIA_LATEST,
    NVIDIA_550,
    NVIDIA_535,
    NVIDIA_470_LEGACY,
    NVIDIA_390_LEGACY,
    NVIDIA_OPEN,
    PRINTING_SUPPORT,
    BLUETOOTH_SUPPORT,
    FLATPAK_SETUP,
    VIRTUALBOX,
    VIRT_MANAGER,
    SNAP_REMOVAL,
    # NOTE: RPM Fusion and Packman are now auto-enabled when needed - no manual tasks!
]


def get_tasks_for_distro(family: DistroFamily, desktop_env: Optional[DesktopEnv] = None) -> list[SetupTask]:
    """Get tasks that are applicable for a distro family and desktop environment.
    
    Args:
        family: The distro family to filter for
        desktop_env: Optional desktop environment to filter for. If None, desktop-specific
                     tasks will be excluded unless explicitly requested.
    """
    tasks = []
    for task in ALL_TASKS:
        # Check if task has packages or commands for this family
        has_packages = family in task.packages and len(task.packages[family]) > 0
        has_commands = task.commands and family in task.commands and len(task.commands[family]) > 0
        
        if has_packages or has_commands:
            # Check desktop-specific filter
            if task.desktop_specific is not None:
                # Task is for a specific desktop - only include if we match
                if desktop_env is None or task.desktop_specific != desktop_env:
                    continue  # Skip this task
            
            tasks.append(task)
    
    return tasks


# =============================================================================
# GPU Detection
# =============================================================================

import subprocess
import re
from dataclasses import dataclass as gpu_dataclass


@gpu_dataclass
class DetectedGPU:
    """Information about a detected GPU."""
    vendor: str  # 'nvidia', 'amd', 'intel', 'unknown'
    name: str
    pci_id: str
    recommended_driver: str
    driver_notes: str


def detect_gpus() -> list[DetectedGPU]:
    """Detect GPUs in the system using lspci."""
    gpus = []
    
    try:
        # Run lspci to find VGA and 3D controllers
        result = subprocess.run(
            ['lspci', '-nn'],
            capture_output=True, text=True, timeout=10
        )
        
        if result.returncode != 0:
            return gpus
        
        for line in result.stdout.splitlines():
            # Look for VGA compatible controller or 3D controller
            if 'VGA compatible controller' in line or '3D controller' in line:
                # Extract device info
                # Format: XX:XX.X VGA compatible controller: Vendor Device [VVVV:DDDD]
                
                # Get PCI ID
                pci_match = re.search(r'\[([0-9a-fA-F]{4}):([0-9a-fA-F]{4})\]', line)
                pci_id = f"{pci_match.group(1)}:{pci_match.group(2)}" if pci_match else ""
                
                # Determine vendor and get device name
                name_part = line.split(': ', 1)[-1] if ': ' in line else line
                name = re.sub(r'\s*\[[0-9a-fA-F:]+\]', '', name_part).strip()
                
                vendor = 'unknown'
                recommended = ''
                notes = ''
                
                if 'NVIDIA' in line.upper():
                    vendor = 'nvidia'
                    # Determine recommended driver based on GPU generation
                    if any(x in name.upper() for x in ['RTX 40', 'RTX 50', 'RTX 30', 'RTX 20', 'GTX 16']):
                        recommended = 'nvidia_latest'
                        notes = 'Latest driver recommended (RTX/GTX 16+ series)'
                    elif any(x in name.upper() for x in ['GTX 10', 'GTX 9', 'TITAN X', 'QUADRO P', 'QUADRO M']):
                        recommended = 'nvidia_550'
                        notes = 'Stable 550.x LTS driver recommended (Maxwell/Pascal)'
                    elif any(x in name.upper() for x in ['GTX 7', 'GTX 6', 'QUADRO K']):
                        recommended = 'nvidia_470'
                        notes = 'Legacy 470.x driver for Kepler GPUs'
                    elif any(x in name.upper() for x in ['GTX 5', 'GTX 4', 'QUADRO 4000', 'QUADRO 5000', 'QUADRO 6000']):
                        recommended = 'nvidia_390'
                        notes = 'Very old legacy 390.x driver for Fermi GPUs'
                    else:
                        recommended = 'nvidia_latest'
                        notes = 'Try latest driver first'
                        
                elif 'AMD' in line.upper() or 'ATI' in line.upper() or 'RADEON' in line.upper():
                    vendor = 'amd'
                    if any(x in name.upper() for x in ['PRO', 'FIREPRO', 'RADEON PRO', 'W5', 'W6', 'W7']):
                        recommended = 'amd_pro_graphics'
                        notes = 'Workstation GPU - AMD PRO drivers available'
                    else:
                        recommended = 'amd_graphics'
                        notes = 'Open source Mesa drivers recommended'
                        
                elif 'INTEL' in line.upper():
                    vendor = 'intel'
                    recommended = 'intel_graphics'
                    notes = 'Intel open source drivers'
                
                gpus.append(DetectedGPU(
                    vendor=vendor,
                    name=name,
                    pci_id=pci_id,
                    recommended_driver=recommended,
                    driver_notes=notes
                ))
    
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    
    return gpus


# =============================================================================
# Setup Tools Page UI
# =============================================================================

from .registry import register_module, ModuleCategory
from typing import Callable
import os
import tempfile


class TaskDetailPage(Adw.NavigationPage):
    """Detail page showing what packages a task will install."""
    
    def __init__(self, task: SetupTask, distro_family: DistroFamily, 
                 is_queued: bool, on_queue_changed: Callable[[str, bool], None],
                 window=None):
        super().__init__(title=task.name)
        
        self.task = task
        self.distro_family = distro_family
        self.is_queued = is_queued
        self.on_queue_changed = on_queue_changed
        self.window = window  # Reference to main window for toasts
        self.available_packages = []  # Will be populated after checking
        self.unavailable_packages = []
        self.pkg_group = None  # Reference for updating
        self.alt_sources_group = None  # Group for alternative sources
        self.content_box = None  # Reference to content box for adding alt sources
        
        self._build_ui()
        
        # Start package availability check in background
        self._check_packages_async()
    
    def _check_packages_async(self):
        """Check package availability in background thread."""
        import threading
        
        def check_packages():
            wishlist = self.task.get_packages_for_distro(self.distro_family)
            family_str = self.distro_family.value if hasattr(self.distro_family, 'value') else str(self.distro_family)
            total = len(wishlist)
            
            available = []
            unavailable = []
            for i, pkg in enumerate(wishlist, 1):
                # Update progress on UI thread
                GLib.idle_add(self._update_check_progress, i, total, pkg)
                
                if check_package_available(pkg, family_str):
                    available.append(pkg)
                else:
                    unavailable.append(pkg)
            
            # Update UI on main thread
            GLib.idle_add(self._update_packages_ui, available, unavailable)
        
        thread = threading.Thread(target=check_packages, daemon=True)
        thread.start()
    
    def _update_check_progress(self, current: int, total: int, pkg_name: str):
        """Update the spinner row with progress info."""
        if self.pkg_group:
            # Find the spinner row and update its title
            child = self.pkg_group.get_first_child()
            while child:
                if isinstance(child, Adw.ActionRow) and child.get_title().startswith("Checking"):
                    child.set_title(f"Checking package {current}/{total}: {pkg_name}")
                    break
                child = child.get_next_sibling()
        return False
    
    def _update_packages_ui(self, available: list, unavailable: list):
        """Update the packages UI after availability check."""
        self.available_packages = available
        self.unavailable_packages = unavailable
        family_str = self.distro_family.value if hasattr(self.distro_family, 'value') else str(self.distro_family)
        
        if self.pkg_group:
            # Clear all existing ActionRows (including spinner row)
            rows_to_remove = []
            child = self.pkg_group.get_first_child()
            while child:
                if isinstance(child, Adw.ActionRow):
                    rows_to_remove.append(child)
                child = child.get_next_sibling()
            
            for row in rows_to_remove:
                self.pkg_group.remove(row)
            
            # Update title
            if available:
                self.pkg_group.set_title(f"Packages to Install ({len(available)})")
                self.pkg_group.set_description("These packages are available in your enabled repositories")
            else:
                self.pkg_group.set_title("No Packages Available")
                self.pkg_group.set_description("None of the desired packages are available in your repositories")
            
            # Add available packages
            for pkg in available:
                pkg_row = Adw.ActionRow()
                pkg_row.set_title(pkg)
                pkg_row.add_prefix(Gtk.Image.new_from_icon_name("package-x-generic-symbolic"))
                check_icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
                check_icon.add_css_class("success")
                pkg_row.add_suffix(check_icon)
                self.pkg_group.add(pkg_row)
            
            # Show unavailable packages (greyed out) - but only ones without alternatives
            # We'll show ones with alternatives in a separate section
            pkgs_with_alternatives = []
            pkgs_without_alternatives = []
            
            for pkg in unavailable:
                # Use get_preferred_source to respect user preferences
                alt_source = get_preferred_source(pkg, family_str)
                if alt_source:
                    # Get all available sources for this package
                    all_sources = get_all_sources_for_package(pkg, family_str)
                    pkgs_with_alternatives.append((pkg, alt_source, all_sources))
                else:
                    pkgs_without_alternatives.append(pkg)
            
            # Show packages without any alternative
            for pkg in pkgs_without_alternatives:
                pkg_row = Adw.ActionRow()
                pkg_row.set_title(pkg)
                pkg_row.set_subtitle("Not available - no known alternative source")
                pkg_row.add_css_class("dim-label")
                pkg_row.add_prefix(Gtk.Image.new_from_icon_name("package-x-generic-symbolic"))
                x_icon = Gtk.Image.new_from_icon_name("window-close-symbolic")
                x_icon.add_css_class("error")
                pkg_row.add_suffix(x_icon)
                self.pkg_group.add(pkg_row)
        
            # Create alternative sources section if we have any
            if pkgs_with_alternatives:
                self._create_alternative_sources_section(pkgs_with_alternatives)
        
        return False  # Don't repeat
    
    def _create_alternative_sources_section(self, pkgs_with_alternatives: list):
        """Create UI section for packages available from alternative sources.
        
        Args:
            pkgs_with_alternatives: List of tuples (pkg, preferred_source, all_sources)
        """
        # Remove existing alt sources group if present
        if self.alt_sources_group and self.content_box:
            self.content_box.remove(self.alt_sources_group)
        
        # Normalize to (pkg, source) for batch operations - use preferred source
        self.pkgs_with_alternatives = [(pkg, src) for pkg, src, _ in pkgs_with_alternatives]
        self.alt_source_buttons = {}  # pkg -> button reference
        
        family_str = self.distro_family.value if hasattr(self.distro_family, 'value') else str(self.distro_family)
        
        self.alt_sources_group = Adw.PreferencesGroup()
        self.alt_sources_group.set_title(f"📦 Available from Alternative Sources ({len(pkgs_with_alternatives)})")
        
        # Get current preferences for description
        prefs = get_source_preferences()
        if prefs.get("prefer_flatpak"):
            pref_desc = "Preferring Flatpak (sandboxed)"
        elif prefs.get("prefer_native"):
            pref_desc = "Preferring native packages"
        else:
            pref_desc = "Using default preference order"
        self.alt_sources_group.set_description(f"{pref_desc} • Click ⚙ to change")
        
        # Add preference toggle row
        pref_row = Adw.ActionRow()
        pref_row.set_title("Source Preference")
        pref_row.set_subtitle("Choose between sandboxed Flatpak or native packages")
        pref_row.add_prefix(Gtk.Image.new_from_icon_name("emblem-system-symbolic"))
        
        # Flatpak preference button
        flatpak_btn = Gtk.ToggleButton(label="Flatpak")
        flatpak_btn.set_valign(Gtk.Align.CENTER)
        flatpak_btn.set_active(prefs.get("prefer_flatpak", True))
        flatpak_btn.set_tooltip_text("Prefer sandboxed Flatpak apps")
        
        # Native preference button
        native_btn = Gtk.ToggleButton(label="Native")
        native_btn.set_valign(Gtk.Align.CENTER)
        native_btn.set_active(prefs.get("prefer_native", False))
        native_btn.set_tooltip_text("Prefer native packages (AUR/COPR/PPA)")
        
        # Link them
        flatpak_btn.connect("toggled", self._on_pref_flatpak_toggled, native_btn)
        native_btn.connect("toggled", self._on_pref_native_toggled, flatpak_btn)
        
        pref_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        pref_box.append(flatpak_btn)
        pref_box.append(native_btn)
        pref_row.add_suffix(pref_box)
        
        self.alt_sources_group.add(pref_row)
        
        # Add "Install All" button if more than one package
        if len(pkgs_with_alternatives) > 1:
            install_all_row = Adw.ActionRow()
            install_all_row.set_title("Install All from Alternative Sources")
            install_all_row.set_subtitle(f"Enable required repos and install all {len(pkgs_with_alternatives)} packages")
            install_all_row.add_prefix(Gtk.Image.new_from_icon_name("emblem-synchronizing-symbolic"))
            
            self.install_all_btn = Gtk.Button(label="Install All")
            self.install_all_btn.set_valign(Gtk.Align.CENTER)
            self.install_all_btn.add_css_class("suggested-action")
            self.install_all_btn.connect("clicked", self._on_install_all_clicked)
            install_all_row.add_suffix(self.install_all_btn)
            
            self.alt_sources_group.add(install_all_row)
        
        for pkg, source, all_sources in pkgs_with_alternatives:
            row = Adw.ActionRow()
            row.set_title(pkg)
            
            # Build subtitle with source info
            source_desc = get_source_type_description(source.source_type)
            subtitle = f"Via {source_desc}"
            if source.note:
                subtitle += f" • {source.note}"
            
            # Show if multiple sources available
            if len(all_sources) > 1:
                other_types = [s.source_type.value for s in all_sources if s != source]
                subtitle += f" (also: {', '.join(other_types)})"
            
            row.set_subtitle(subtitle)
            
            # Source type icon with verification status
            icon_name = self._get_source_icon(source.source_type)
            prefix_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
            prefix_box.append(Gtk.Image.new_from_icon_name(icon_name))
            
            # Verify source in background (non-blocking - just show indicator if cached)
            verified, _ = verify_source_exists(source, family_str)
            if not verified:
                warn_icon = Gtk.Image.new_from_icon_name("dialog-warning-symbolic")
                warn_icon.set_tooltip_text("Source could not be verified - may not exist")
                warn_icon.add_css_class("warning")
                prefix_box.append(warn_icon)
            
            row.add_prefix(prefix_box)
            
            # Install button
            enable_btn = Gtk.Button(label="Install")
            enable_btn.set_valign(Gtk.Align.CENTER)
            enable_btn.add_css_class("flat")
            enable_btn.connect("clicked", self._on_enable_source_clicked, pkg, source)
            row.add_suffix(enable_btn)
            
            # Store button reference
            self.alt_source_buttons[pkg] = enable_btn
            
            self.alt_sources_group.add(row)
        
        # Insert after the packages group
        if self.content_box and self.pkg_group:
            self.content_box.append(self.alt_sources_group)
            self.content_box.reorder_child_after(self.alt_sources_group, self.pkg_group)
    
    def _on_pref_flatpak_toggled(self, button, native_btn):
        """Handle Flatpak preference toggle."""
        if button.get_active():
            native_btn.set_active(False)
            set_source_preference(prefer_flatpak=True)
        elif not native_btn.get_active():
            # At least one should be active, or neither (default order)
            set_source_preference(prefer_flatpak=False, prefer_native=False)
        
        # Refresh the list with new preferences
        self._check_packages_async()
    
    def _on_pref_native_toggled(self, button, flatpak_btn):
        """Handle Native preference toggle."""
        if button.get_active():
            flatpak_btn.set_active(False)
            set_source_preference(prefer_native=True)
        elif not flatpak_btn.get_active():
            set_source_preference(prefer_flatpak=False, prefer_native=False)
        
        # Refresh the list with new preferences
        self._check_packages_async()
    
    def _on_install_all_clicked(self, button):
        """Handle Install All button - batch install from alternative sources."""
        if not hasattr(self, 'pkgs_with_alternatives') or not self.pkgs_with_alternatives:
            return
        
        # Disable the button
        button.set_sensitive(False)
        button.set_label("Installing...")
        
        # Disable individual buttons too
        for pkg, btn in self.alt_source_buttons.items():
            btn.set_sensitive(False)
        
        # Get parent window
        window = self.get_root()
        
        # Create batch install dialog
        dialog = BatchAlternativeInstallDialog(
            window=window,
            packages_with_sources=self.pkgs_with_alternatives,
            distro_family=self.distro_family,
            on_complete=self._on_batch_install_complete
        )
        dialog.present()
    
    def _on_batch_install_complete(self, successful_packages: list, failed_packages: list):
        """Handle completion of batch alternative source installation."""
        # Clear cache and refresh
        clear_package_cache()
        
        # Update buttons for successful packages
        for pkg in successful_packages:
            if pkg in self.alt_source_buttons:
                btn = self.alt_source_buttons[pkg]
                btn.set_label("✓")
                btn.remove_css_class("flat")
                btn.add_css_class("success")
        
        # Re-enable buttons for failed packages
        for pkg in failed_packages:
            if pkg in self.alt_source_buttons:
                btn = self.alt_source_buttons[pkg]
                btn.set_sensitive(True)
                btn.set_label("Retry")
        
        # Update install all button
        if hasattr(self, 'install_all_btn'):
            if failed_packages:
                self.install_all_btn.set_sensitive(True)
                self.install_all_btn.set_label(f"Retry Failed ({len(failed_packages)})")
            else:
                self.install_all_btn.set_label("✓ All Installed")
                self.install_all_btn.remove_css_class("suggested-action")
                self.install_all_btn.add_css_class("success")
        
        # Re-check packages to update main UI
        self._check_packages_async()
        
        # Show toast
        if self.window and hasattr(self.window, 'show_toast'):
            if failed_packages:
                self.window.show_toast(f"Installed {len(successful_packages)}, {len(failed_packages)} failed")
            else:
                self.window.show_toast(f"Successfully installed {len(successful_packages)} packages")
    
    def _get_source_icon(self, source_type: SourceType) -> str:
        """Get icon name for a source type."""
        icons = {
            SourceType.COPR: "application-x-addon-symbolic",
            SourceType.PPA: "application-x-addon-symbolic", 
            SourceType.AUR: "system-software-install-symbolic",
            SourceType.OBS: "application-x-addon-symbolic",
            SourceType.FLATPAK: "system-software-install-symbolic",
            SourceType.RPMFUSION: "application-x-addon-symbolic",
            SourceType.PACKMAN: "application-x-addon-symbolic",
        }
        return icons.get(source_type, "package-x-generic-symbolic")
    
    def _on_enable_source_clicked(self, button, package: str, source: PackageSource):
        """Handle Enable & Install button click."""
        # Disable button to prevent double-click
        button.set_sensitive(False)
        button.set_label("Installing...")
        
        # Get parent window for dialog
        window = self.get_root()
        
        # Create and show installation dialog
        dialog = AlternativeSourceInstallDialog(
            window=window,
            package=package,
            source=source,
            distro_family=self.distro_family,
            on_complete=lambda success: self._on_alt_install_complete(success, button, package)
        )
        dialog.present()
    
    def _on_alt_install_complete(self, success: bool, button: Gtk.Button, package: str):
        """Handle completion of alternative source installation."""
        if success:
            # Clear package cache and re-check
            clear_package_cache()
            
            # Update button to show success
            button.set_label("✓ Installed")
            button.remove_css_class("suggested-action")
            button.add_css_class("success")
            
            # Re-run package check to update the UI
            self._check_packages_async()
            
            # Show toast if we have window reference
            if self.window and hasattr(self.window, 'show_toast'):
                self.window.show_toast(f"Successfully installed {package}")
        else:
            # Re-enable button on failure
            button.set_sensitive(True)
            button.set_label("Retry")
    
    def _build_ui(self):
        """Build the detail page UI."""
        # Main container
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header bar
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
        
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        clamp.set_child(self.content_box)
        
        # Task info header
        info_group = Adw.PreferencesGroup()
        info_group.set_title("About This Task")
        info_group.set_description(self.task.description)
        self.content_box.append(info_group)
        
        # Description row
        desc_row = Adw.ActionRow()
        desc_row.set_title("Category")
        desc_row.set_subtitle(self.task.category.value.title())
        desc_row.add_prefix(Gtk.Image.new_from_icon_name("folder-symbolic"))
        info_group.add(desc_row)
        
        # Reboot indicator
        if self.task.requires_reboot:
            reboot_row = Adw.ActionRow()
            reboot_row.set_title("Requires Reboot")
            reboot_row.set_subtitle("System restart needed after installation")
            reboot_row.add_prefix(Gtk.Image.new_from_icon_name("system-reboot-symbolic"))
            info_group.add(reboot_row)
        
        # Packages section - show loading initially
        wishlist = self.task.get_packages_for_distro(self.distro_family)
        if wishlist:
            self.pkg_group = Adw.PreferencesGroup()
            self.pkg_group.set_title("Checking Package Availability...")
            self.pkg_group.set_description("Scanning your enabled repositories")
            self.content_box.append(self.pkg_group)
            
            # Show spinner while checking
            spinner_row = Adw.ActionRow()
            spinner_row.set_title("Checking packages...")
            spinner = Gtk.Spinner()
            spinner.start()
            spinner_row.add_prefix(spinner)
            self.pkg_group.add(spinner_row)
        
        # Commands section (if any)
        commands = self.task.get_commands_for_distro(self.distro_family)
        if commands:
            cmd_group = Adw.PreferencesGroup()
            cmd_group.set_title("Additional Commands")
            cmd_group.set_description("These commands will also be run during installation")
            self.content_box.append(cmd_group)
            
            for cmd in commands:
                cmd_str = ' '.join(cmd)
                # Remove sudo prefix for display
                if cmd_str.startswith('sudo '):
                    cmd_str = cmd_str[5:]
                
                cmd_row = Adw.ActionRow()
                cmd_row.set_title(cmd_str)
                cmd_row.add_prefix(Gtk.Image.new_from_icon_name("utilities-terminal-symbolic"))
                cmd_group.add(cmd_row)
        
        # Action buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(24)
        self.content_box.append(button_box)
        
        # Queue toggle button
        self.queue_button = Gtk.Button()
        self._update_queue_button()
        self.queue_button.connect("clicked", self._on_queue_clicked)
        button_box.append(self.queue_button)
        
        # Status label
        self.status_label = Gtk.Label()
        self.status_label.add_css_class("dim-label")
        self._update_status_label()
        self.content_box.append(self.status_label)
    
    def _update_queue_button(self):
        """Update queue button appearance based on state."""
        if self.is_queued:
            self.queue_button.set_label("Remove from Queue")
            self.queue_button.remove_css_class("suggested-action")
            self.queue_button.add_css_class("destructive-action")
        else:
            self.queue_button.set_label("Add to Install Queue")
            self.queue_button.remove_css_class("destructive-action")
            self.queue_button.add_css_class("suggested-action")
    
    def _update_status_label(self):
        """Update status label."""
        if self.is_queued:
            self.status_label.set_text("✓ This task is queued for installation")
        else:
            self.status_label.set_text("Click the button above to add to your install queue")
    
    def _on_queue_clicked(self, button):
        """Handle queue button click."""
        self.is_queued = not self.is_queued
        self._update_queue_button()
        self._update_status_label()
        
        # Notify parent
        if self.on_queue_changed:
            self.on_queue_changed(self.task.id, self.is_queued)


# =============================================================================
# Alternative Source Installation Dialog
# =============================================================================

class AlternativeSourceInstallDialog(Adw.Dialog):
    """Dialog for enabling alternative repos and installing packages."""
    
    def __init__(self, window, package: str, source: PackageSource, 
                 distro_family: DistroFamily, on_complete: Callable[[bool], None]):
        super().__init__()
        
        self.package = package
        self.source = source
        self.distro_family = distro_family
        self.on_complete = on_complete
        self.cancelled = False
        
        self.set_title(f"Install {package}")
        self.set_content_width(500)
        self.set_content_height(400)
        
        self._build_ui()
        
        # Start installation in background
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
        self.close_btn.set_sensitive(False)
        self.close_btn.set_visible(False)
        header.pack_end(self.close_btn)
        
        # Main content
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content_box.set_margin_top(20)
        content_box.set_margin_bottom(20)
        content_box.set_margin_start(20)
        content_box.set_margin_end(20)
        toolbar_view.set_content(content_box)
        
        # Status
        self.status_label = Gtk.Label()
        self.status_label.set_markup(f"<b>Installing {self.package}</b>")
        self.status_label.set_halign(Gtk.Align.START)
        content_box.append(self.status_label)
        
        # Source info
        source_desc = get_source_type_description(self.source.source_type)
        info_label = Gtk.Label(label=f"Source: {source_desc}")
        info_label.add_css_class("dim-label")
        info_label.set_halign(Gtk.Align.START)
        content_box.append(info_label)
        
        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_text("Preparing...")
        self.progress_bar.pulse()
        content_box.append(self.progress_bar)
        
        # Output text view
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_min_content_height(200)
        content_box.append(scrolled)
        
        self.output_view = Gtk.TextView()
        self.output_view.set_editable(False)
        self.output_view.set_cursor_visible(False)
        self.output_view.set_monospace(True)
        self.output_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        scrolled.set_child(self.output_view)
        
        self.output_buffer = self.output_view.get_buffer()
    
    def _append_output(self, text: str, style: str = None):
        """Append text to output view."""
        end_iter = self.output_buffer.get_end_iter()
        self.output_buffer.insert(end_iter, text + "\n")
        
        # Scroll to bottom
        mark = self.output_buffer.get_insert()
        self.output_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)
    
    def _start_installation(self):
        """Start the installation process in a background thread."""
        import threading
        thread = threading.Thread(target=self._run_installation, daemon=True)
        thread.start()
    
    def _run_installation(self):
        """Run the installation (in background thread)."""
        import shutil
        
        family_str = self.distro_family.value if hasattr(self.distro_family, 'value') else str(self.distro_family)
        pkg_name = self.source.package_name or self.package
        
        try:
            if self.source.source_type == SourceType.FLATPAK:
                self._install_flatpak(pkg_name)
            elif self.source.source_type == SourceType.AUR:
                self._install_aur(pkg_name)
            elif self.source.source_type == SourceType.COPR:
                self._install_copr(pkg_name)
            elif self.source.source_type == SourceType.PPA:
                self._install_ppa(pkg_name)
            elif self.source.source_type == SourceType.RPMFUSION:
                self._install_rpmfusion(pkg_name)
            elif self.source.source_type == SourceType.PACKMAN:
                self._install_packman(pkg_name)
            else:
                GLib.idle_add(self._append_output, f"Unknown source type: {self.source.source_type}")
                GLib.idle_add(self._installation_complete, False)
                return
                
        except Exception as e:
            GLib.idle_add(self._append_output, f"Error: {str(e)}")
            GLib.idle_add(self._installation_complete, False)
    
    def _install_flatpak(self, flatpak_id: str):
        """Install a Flatpak package, setting up Flatpak/Flathub if needed."""
        GLib.idle_add(self._append_output, f"Installing Flatpak: {flatpak_id}")
        GLib.idle_add(self.progress_bar.set_text, "Checking Flatpak setup...")
        
        import shutil
        
        # Check if flatpak is installed
        if not shutil.which('flatpak'):
            GLib.idle_add(self._append_output, "Flatpak not installed - installing it first...")
            
            if not self._auto_install_flatpak():
                GLib.idle_add(self._append_output, "")
                GLib.idle_add(self._append_output, "Failed to install Flatpak automatically.")
                GLib.idle_add(self._append_output, "Please install Flatpak first using the 'Flatpak and Flathub' task")
                GLib.idle_add(self._installation_complete, False)
                return
            
            GLib.idle_add(self._append_output, "✓ Flatpak installed!")
        
        # Check if flathub is added (try both system and user)
        GLib.idle_add(self.progress_bar.set_text, "Checking Flathub repository...")
        result = subprocess.run(['flatpak', 'remotes', '--columns=name'], capture_output=True, text=True)
        
        if 'flathub' not in result.stdout.lower():
            GLib.idle_add(self._append_output, "Adding Flathub repository...")
            
            # Try user-level first (no root needed)
            add_result = subprocess.run([
                'flatpak', 'remote-add', '--if-not-exists', '--user',
                'flathub', 'https://dl.flathub.org/repo/flathub.flatpakrepo'
            ], capture_output=True, text=True)
            
            if add_result.returncode == 0:
                GLib.idle_add(self._append_output, "✓ Flathub added (user)")
            else:
                # Try system-level
                add_result = subprocess.run([
                    'flatpak', 'remote-add', '--if-not-exists',
                    'flathub', 'https://dl.flathub.org/repo/flathub.flatpakrepo'
                ], capture_output=True, text=True)
                
                if add_result.returncode == 0:
                    GLib.idle_add(self._append_output, "✓ Flathub added (system)")
                else:
                    GLib.idle_add(self._append_output, f"Warning: Could not add Flathub: {add_result.stderr}")
        
        GLib.idle_add(self.progress_bar.set_text, f"Installing {flatpak_id}...")
        GLib.idle_add(self._append_output, "")
        GLib.idle_add(self._append_output, f"Installing {flatpak_id} from Flathub...")
        
        # Install the flatpak (try user install first, no root needed)
        process = subprocess.Popen(
            ['flatpak', 'install', '-y', '--user', 'flathub', flatpak_id],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        for line in process.stdout:
            if self.cancelled:
                process.terminate()
                return
            line = line.strip()
            if line:
                GLib.idle_add(self._append_output, line)
        
        process.wait()
        
        # If user install failed, try system install
        if process.returncode != 0:
            GLib.idle_add(self._append_output, "")
            GLib.idle_add(self._append_output, "User install failed, trying system install...")
            
            process = subprocess.Popen(
                ['flatpak', 'install', '-y', 'flathub', flatpak_id],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            for line in process.stdout:
                if self.cancelled:
                    process.terminate()
                    return
                line = line.strip()
                if line:
                    GLib.idle_add(self._append_output, line)
            
            process.wait()
        
        success = process.returncode == 0
        GLib.idle_add(self._installation_complete, success)
    
    def _auto_install_flatpak(self) -> bool:
        """Automatically install Flatpak. Returns True on success."""
        family_str = self.distro_family.value if hasattr(self.distro_family, 'value') else str(self.distro_family)
        
        try:
            if family_str == 'arch':
                cmd = ['sudo', 'pacman', '-S', '--noconfirm', 'flatpak']
            elif family_str == 'debian':
                cmd = ['sudo', 'apt', 'install', '-y', 'flatpak']
            elif family_str == 'fedora':
                cmd = ['sudo', 'dnf', 'install', '-y', 'flatpak']
            elif family_str == 'opensuse':
                cmd = ['sudo', 'zypper', 'install', '-y', 'flatpak']
            else:
                return False
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
            return result.returncode == 0
            
        except Exception:
            return False
    
    def _install_aur(self, pkg_name: str):
        """Install an AUR package using yay or paru, auto-installing helper if needed."""
        import shutil
        
        # Find AUR helper
        aur_helper = None
        for helper in ['paru', 'yay', 'pikaur']:
            if shutil.which(helper):
                aur_helper = helper
                break
        
        if not aur_helper:
            GLib.idle_add(self._append_output, "No AUR helper found - installing yay automatically...")
            GLib.idle_add(self.progress_bar.set_text, "Installing yay AUR helper...")
            
            # Auto-install yay
            if self._auto_install_yay():
                aur_helper = 'yay'
                GLib.idle_add(self._append_output, "✓ yay installed successfully!")
                GLib.idle_add(self._append_output, "")
            else:
                GLib.idle_add(self._append_output, "")
                GLib.idle_add(self._append_output, "Failed to auto-install yay. Manual installation:")
                GLib.idle_add(self._append_output, "  sudo pacman -S --needed git base-devel")
                GLib.idle_add(self._append_output, "  git clone https://aur.archlinux.org/yay-bin.git")
                GLib.idle_add(self._append_output, "  cd yay-bin && makepkg -si")
                GLib.idle_add(self._installation_complete, False)
                return
        
        GLib.idle_add(self._append_output, f"Using {aur_helper} to install {pkg_name} from AUR...")
        GLib.idle_add(self.progress_bar.set_text, f"Installing via {aur_helper}...")
        
        # Run AUR helper (doesn't need root - it handles sudo itself)
        process = subprocess.Popen(
            [aur_helper, '-S', '--noconfirm', pkg_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )
        
        for line in process.stdout:
            if self.cancelled:
                process.terminate()
                return
            GLib.idle_add(self._append_output, line.strip())
        
        process.wait()
        
        success = process.returncode == 0
        GLib.idle_add(self._installation_complete, success)
    
    def _auto_install_yay(self) -> bool:
        """Automatically install yay AUR helper. Returns True on success."""
        import tempfile
        import shutil
        
        try:
            # First ensure base-devel and git are installed
            GLib.idle_add(self._append_output, "Installing prerequisites (git, base-devel)...")
            
            prereq_proc = subprocess.run(
                ['sudo', 'pacman', '-S', '--needed', '--noconfirm', 'git', 'base-devel'],
                capture_output=True, text=True, timeout=120
            )
            
            if prereq_proc.returncode != 0:
                GLib.idle_add(self._append_output, f"Failed to install prerequisites: {prereq_proc.stderr}")
                return False
            
            # Create temp directory for building
            with tempfile.TemporaryDirectory() as tmpdir:
                GLib.idle_add(self._append_output, "Cloning yay-bin from AUR...")
                
                # Clone yay-bin (prebuilt binary, faster)
                clone_proc = subprocess.run(
                    ['git', 'clone', 'https://aur.archlinux.org/yay-bin.git', f'{tmpdir}/yay-bin'],
                    capture_output=True, text=True, timeout=60
                )
                
                if clone_proc.returncode != 0:
                    GLib.idle_add(self._append_output, f"Failed to clone: {clone_proc.stderr}")
                    return False
                
                GLib.idle_add(self._append_output, "Building and installing yay...")
                
                # Build and install
                build_proc = subprocess.Popen(
                    ['makepkg', '-si', '--noconfirm'],
                    cwd=f'{tmpdir}/yay-bin',
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True
                )
                
                for line in build_proc.stdout:
                    GLib.idle_add(self._append_output, f"  {line.strip()}")
                
                build_proc.wait()
                
                if build_proc.returncode != 0:
                    return False
                
                # Verify installation
                if shutil.which('yay'):
                    return True
                    
            return False
            
        except Exception as e:
            GLib.idle_add(self._append_output, f"Error installing yay: {str(e)}")
            return False
    
    def _install_copr(self, pkg_name: str):
        """Enable a COPR repo and install package."""
        GLib.idle_add(self._append_output, f"Enabling COPR: {self.source.repo_id}")
        GLib.idle_add(self.progress_bar.set_text, "Enabling COPR repository...")
        
        # Use tux-helper for privileged operations
        self._run_with_helper('copr', self.source.repo_id, pkg_name)
    
    def _install_ppa(self, pkg_name: str):
        """Add a PPA and install package."""
        GLib.idle_add(self._append_output, f"Adding PPA: ppa:{self.source.repo_id}")
        GLib.idle_add(self.progress_bar.set_text, "Adding PPA repository...")
        
        # Use tux-helper for privileged operations
        self._run_with_helper('ppa', self.source.repo_id, pkg_name)
    
    def _install_rpmfusion(self, pkg_name: str):
        """Enable RPM Fusion and install package."""
        GLib.idle_add(self._append_output, "Enabling RPM Fusion repositories...")
        GLib.idle_add(self.progress_bar.set_text, "Enabling RPM Fusion...")
        
        # Use tux-helper for privileged operations
        self._run_with_helper('rpmfusion', '', pkg_name)
    
    def _install_packman(self, pkg_name: str):
        """Enable Packman and install package."""
        GLib.idle_add(self._append_output, "Enabling Packman repository...")
        GLib.idle_add(self.progress_bar.set_text, "Enabling Packman...")
        
        # Use tux-helper for privileged operations
        self._run_with_helper('packman', '', pkg_name)
    
    def _run_with_helper(self, source_type: str, repo_id: str, pkg_name: str):
        """Run installation using tux-helper with pkexec."""
        import shutil
        
        # Find tux-helper
        helper_paths = [
            '/usr/bin/tux-helper',
            '/usr/local/bin/tux-helper',
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'tux-helper'),
        ]
        
        helper_path = None
        for path in helper_paths:
            if os.path.exists(path):
                helper_path = path
                break
        
        if not helper_path:
            GLib.idle_add(self._append_output, "Error: tux-helper not found!")
            GLib.idle_add(self._installation_complete, False)
            return
        
        # Build command
        cmd_args = ['--enable-source', source_type]
        if repo_id:
            cmd_args.extend(['--repo-id', repo_id])
        cmd_args.extend(['--install-package', pkg_name])
        
        # Use pkexec for privilege escalation
        use_pkexec = shutil.which('pkexec') is not None
        
        if use_pkexec:
            cmd = ['pkexec', helper_path] + cmd_args
        else:
            cmd = ['sudo', helper_path] + cmd_args
        
        GLib.idle_add(self._append_output, f"Running: {' '.join(cmd)}")
        GLib.idle_add(self.progress_bar.set_text, "Installing (authentication required)...")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
            
            for line in process.stdout:
                if self.cancelled:
                    process.terminate()
                    return
                line = line.strip()
                if line:
                    GLib.idle_add(self._append_output, line)
            
            process.wait()
            
            success = process.returncode == 0
            GLib.idle_add(self._installation_complete, success)
            
        except Exception as e:
            GLib.idle_add(self._append_output, f"Error: {str(e)}")
            GLib.idle_add(self._installation_complete, False)
    
    def _installation_complete(self, success: bool):
        """Handle installation completion."""
        self.progress_bar.set_fraction(1.0 if success else 0.0)
        
        if success:
            self.progress_bar.set_text("Complete!")
            self.status_label.set_markup(f"<b>✓ Successfully installed {self.package}</b>")
            self._append_output("")
            self._append_output("=" * 40)
            self._append_output("Installation completed successfully!")
        else:
            self.progress_bar.set_text("Failed")
            self.status_label.set_markup(f"<b>✗ Failed to install {self.package}</b>")
            self._append_output("")
            self._append_output("=" * 40)
            self._append_output("Installation failed. Check the output above for details.")
        
        # Update buttons
        self.cancel_btn.set_visible(False)
        self.close_btn.set_visible(True)
        self.close_btn.set_sensitive(True)
        
        # Notify callback
        if self.on_complete:
            self.on_complete(success)
    
    def _on_cancel(self, button):
        """Handle cancel button."""
        self.cancelled = True
        self._append_output("Cancelling...")
        self.close()


# =============================================================================
# Batch Alternative Source Installation Dialog
# =============================================================================

class BatchAlternativeInstallDialog(Adw.Dialog):
    """Dialog for batch installing packages from alternative sources."""
    
    def __init__(self, window, packages_with_sources: list, 
                 distro_family: DistroFamily, on_complete: Callable[[list, list], None]):
        super().__init__()
        
        self.packages_with_sources = packages_with_sources  # [(pkg, source), ...]
        self.distro_family = distro_family
        self.on_complete = on_complete
        self.cancelled = False
        self.successful = []
        self.failed = []
        
        self.set_title(f"Installing {len(packages_with_sources)} Packages")
        self.set_content_width(550)
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
        
        # Close button
        self.close_btn = Gtk.Button(label="Close")
        self.close_btn.connect("clicked", lambda b: self.close())
        self.close_btn.set_sensitive(False)
        self.close_btn.set_visible(False)
        header.pack_end(self.close_btn)
        
        # Main content
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content_box.set_margin_top(20)
        content_box.set_margin_bottom(20)
        content_box.set_margin_start(20)
        content_box.set_margin_end(20)
        toolbar_view.set_content(content_box)
        
        # Status
        self.status_label = Gtk.Label()
        self.status_label.set_markup(f"<b>Installing {len(self.packages_with_sources)} packages from alternative sources</b>")
        self.status_label.set_halign(Gtk.Align.START)
        content_box.append(self.status_label)
        
        # Current package
        self.current_label = Gtk.Label(label="Preparing...")
        self.current_label.add_css_class("dim-label")
        self.current_label.set_halign(Gtk.Align.START)
        content_box.append(self.current_label)
        
        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_text("0 / " + str(len(self.packages_with_sources)))
        content_box.append(self.progress_bar)
        
        # Package list with status
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_min_content_height(150)
        content_box.append(scrolled)
        
        self.pkg_list = Gtk.ListBox()
        self.pkg_list.set_selection_mode(Gtk.SelectionMode.NONE)
        self.pkg_list.add_css_class("boxed-list")
        scrolled.set_child(self.pkg_list)
        
        # Create rows for each package
        self.pkg_rows = {}
        for pkg, source in self.packages_with_sources:
            row = Adw.ActionRow()
            row.set_title(pkg)
            row.set_subtitle(get_source_type_description(source.source_type))
            
            # Status icon (starts as pending)
            status_icon = Gtk.Image.new_from_icon_name("content-loading-symbolic")
            status_icon.add_css_class("dim-label")
            row.add_suffix(status_icon)
            
            self.pkg_rows[pkg] = {'row': row, 'icon': status_icon}
            self.pkg_list.append(row)
        
        # Output expander
        expander = Gtk.Expander(label="Show Details")
        content_box.append(expander)
        
        output_scrolled = Gtk.ScrolledWindow()
        output_scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        output_scrolled.set_min_content_height(100)
        expander.set_child(output_scrolled)
        
        self.output_view = Gtk.TextView()
        self.output_view.set_editable(False)
        self.output_view.set_cursor_visible(False)
        self.output_view.set_monospace(True)
        self.output_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        output_scrolled.set_child(self.output_view)
        
        self.output_buffer = self.output_view.get_buffer()
    
    def _append_output(self, text: str):
        """Append text to output view."""
        end_iter = self.output_buffer.get_end_iter()
        self.output_buffer.insert(end_iter, text + "\n")
    
    def _update_pkg_status(self, pkg: str, status: str):
        """Update a package row's status icon."""
        if pkg in self.pkg_rows:
            icon = self.pkg_rows[pkg]['icon']
            icon.remove_css_class("dim-label")
            
            if status == 'installing':
                icon.set_from_icon_name("emblem-synchronizing-symbolic")
                icon.add_css_class("accent")
            elif status == 'success':
                icon.remove_css_class("accent")
                icon.set_from_icon_name("emblem-ok-symbolic")
                icon.add_css_class("success")
            elif status == 'failed':
                icon.remove_css_class("accent")
                icon.set_from_icon_name("dialog-error-symbolic")
                icon.add_css_class("error")
    
    def _start_installation(self):
        """Start the batch installation in a background thread."""
        import threading
        thread = threading.Thread(target=self._run_batch_installation, daemon=True)
        thread.start()
    
    def _run_batch_installation(self):
        """Run the batch installation (in background thread)."""
        import shutil
        
        family_str = self.distro_family.value if hasattr(self.distro_family, 'value') else str(self.distro_family)
        total = len(self.packages_with_sources)
        
        # Group by source type to minimize repo enables
        # e.g., enable COPR once, then install all COPR packages
        by_source_type = {}
        for pkg, source in self.packages_with_sources:
            key = (source.source_type, source.repo_id if source.source_type in [SourceType.COPR, SourceType.PPA] else None)
            if key not in by_source_type:
                by_source_type[key] = []
            by_source_type[key].append((pkg, source))
        
        completed = 0
        
        for (source_type, repo_id), packages in by_source_type.items():
            if self.cancelled:
                break
            
            # Enable repo once for this group (if needed)
            if source_type in [SourceType.COPR, SourceType.PPA, SourceType.RPMFUSION, SourceType.PACKMAN]:
                GLib.idle_add(self._append_output, f"\n=== Enabling {source_type.value} ===")
                # The individual install methods handle repo enabling
            
            # Install each package in this group
            for pkg, source in packages:
                if self.cancelled:
                    break
                
                GLib.idle_add(self.current_label.set_text, f"Installing: {pkg}")
                GLib.idle_add(self._update_pkg_status, pkg, 'installing')
                GLib.idle_add(self._append_output, f"\n--- Installing {pkg} ---")
                
                success = self._install_single_package(pkg, source, family_str)
                
                if success:
                    self.successful.append(pkg)
                    GLib.idle_add(self._update_pkg_status, pkg, 'success')
                else:
                    self.failed.append(pkg)
                    GLib.idle_add(self._update_pkg_status, pkg, 'failed')
                
                completed += 1
                progress = completed / total
                GLib.idle_add(self.progress_bar.set_fraction, progress)
                GLib.idle_add(self.progress_bar.set_text, f"{completed} / {total}")
        
        GLib.idle_add(self._installation_complete)
    
    def _install_single_package(self, pkg: str, source: PackageSource, family_str: str) -> bool:
        """Install a single package. Returns True on success."""
        import shutil
        
        pkg_name = source.package_name or pkg
        
        try:
            if source.source_type == SourceType.FLATPAK:
                return self._do_flatpak_install(pkg_name)
            elif source.source_type == SourceType.AUR:
                return self._do_aur_install(pkg_name)
            elif source.source_type == SourceType.COPR:
                return self._do_copr_install(source.repo_id, pkg_name)
            elif source.source_type == SourceType.PPA:
                return self._do_ppa_install(source.repo_id, pkg_name)
            elif source.source_type == SourceType.RPMFUSION:
                return self._do_rpmfusion_install(pkg_name)
            elif source.source_type == SourceType.PACKMAN:
                return self._do_packman_install(pkg_name)
            else:
                GLib.idle_add(self._append_output, f"Unknown source type: {source.source_type}")
                return False
        except Exception as e:
            GLib.idle_add(self._append_output, f"Error: {str(e)}")
            return False
    
    def _do_flatpak_install(self, flatpak_id: str) -> bool:
        """Install a Flatpak package."""
        import shutil
        
        if not shutil.which('flatpak'):
            GLib.idle_add(self._append_output, "Flatpak not installed!")
            return False
        
        # Ensure flathub is added
        subprocess.run([
            'flatpak', 'remote-add', '--if-not-exists', '--user',
            'flathub', 'https://dl.flathub.org/repo/flathub.flatpakrepo'
        ], capture_output=True)
        
        result = subprocess.run(
            ['flatpak', 'install', '-y', '--user', 'flathub', flatpak_id],
            capture_output=True, text=True, timeout=300
        )
        
        if result.returncode != 0:
            # Try system install
            result = subprocess.run(
                ['flatpak', 'install', '-y', 'flathub', flatpak_id],
                capture_output=True, text=True, timeout=300
            )
        
        if result.stdout:
            GLib.idle_add(self._append_output, result.stdout[:500])
        
        return result.returncode == 0
    
    def _do_aur_install(self, pkg_name: str) -> bool:
        """Install an AUR package."""
        import shutil
        
        aur_helper = None
        for helper in ['paru', 'yay', 'pikaur']:
            if shutil.which(helper):
                aur_helper = helper
                break
        
        if not aur_helper:
            GLib.idle_add(self._append_output, "No AUR helper found!")
            return False
        
        result = subprocess.run(
            [aur_helper, '-S', '--noconfirm', pkg_name],
            capture_output=True, text=True, timeout=600
        )
        
        if result.stdout:
            GLib.idle_add(self._append_output, result.stdout[-500:])
        
        return result.returncode == 0
    
    def _do_copr_install(self, repo_id: str, pkg_name: str) -> bool:
        """Enable COPR and install package."""
        # Enable COPR
        subprocess.run(['sudo', 'dnf', 'copr', 'enable', '-y', repo_id],
                      capture_output=True, timeout=60)
        
        # Install package
        result = subprocess.run(
            ['sudo', 'dnf', 'install', '-y', pkg_name],
            capture_output=True, text=True, timeout=300
        )
        
        return result.returncode == 0
    
    def _do_ppa_install(self, repo_id: str, pkg_name: str) -> bool:
        """Add PPA and install package."""
        ppa = repo_id if repo_id.startswith('ppa:') else f'ppa:{repo_id}'
        
        # Add PPA
        subprocess.run(['sudo', 'add-apt-repository', '-y', ppa],
                      capture_output=True, timeout=60)
        subprocess.run(['sudo', 'apt', 'update'], capture_output=True, timeout=120)
        
        # Install package
        result = subprocess.run(
            ['sudo', 'apt', 'install', '-y', pkg_name],
            capture_output=True, text=True, timeout=300
        )
        
        return result.returncode == 0
    
    def _do_rpmfusion_install(self, pkg_name: str) -> bool:
        """Enable RPM Fusion and install package."""
        # RPM Fusion should already be enabled by tux-helper, just install
        result = subprocess.run(
            ['sudo', 'dnf', 'install', '-y', pkg_name],
            capture_output=True, text=True, timeout=300
        )
        
        return result.returncode == 0
    
    def _do_packman_install(self, pkg_name: str) -> bool:
        """Install from Packman."""
        result = subprocess.run(
            ['sudo', 'zypper', 'install', '-y', pkg_name],
            capture_output=True, text=True, timeout=300
        )
        
        return result.returncode == 0
    
    def _installation_complete(self):
        """Handle batch installation completion."""
        total = len(self.packages_with_sources)
        
        self.progress_bar.set_fraction(1.0)
        
        if self.cancelled:
            self.status_label.set_markup("<b>Installation cancelled</b>")
            self.progress_bar.set_text("Cancelled")
        elif self.failed:
            self.status_label.set_markup(f"<b>Completed: {len(self.successful)} succeeded, {len(self.failed)} failed</b>")
            self.progress_bar.set_text(f"{len(self.successful)}/{total} succeeded")
        else:
            self.status_label.set_markup(f"<b>✓ All {total} packages installed successfully!</b>")
            self.progress_bar.set_text("Complete!")
        
        self.current_label.set_text("")
        
        # Update buttons
        self.cancel_btn.set_visible(False)
        self.close_btn.set_visible(True)
        self.close_btn.set_sensitive(True)
        
        # Notify callback
        if self.on_complete:
            self.on_complete(self.successful, self.failed)
    
    def _on_cancel(self, button):
        """Handle cancel button."""
        self.cancelled = True
        self.current_label.set_text("Cancelling...")
        button.set_sensitive(False)


@register_module(
    id="setup_tools",
    name="Setup Tools",
    description="Complete system setup, codecs, drivers, and apps",
    icon="system-run-symbolic",
    category=ModuleCategory.SETUP,
    order=10
)
class SetupToolsPage(Adw.NavigationPage):
    """The Setup Tools page with task selection and execution."""
    
    def __init__(self, window: 'LinuxToolkitWindow'):
        super().__init__(title="Setup Tools")
        
        self.window = window
        self.distro = get_distro()
        self.desktop = get_desktop()
        self.pkg_manager = get_package_manager()
        
        # Track selected tasks
        self.selected_tasks: set[str] = set()
        
        self.build_ui()
    
    def build_ui(self):
        """Build the Setup Tools UI."""
        # Main container with header for back button
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header with back button only (no window controls)
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
        clamp.set_margin_top(20)
        clamp.set_margin_bottom(20)
        clamp.set_margin_start(20)
        clamp.set_margin_end(20)
        scrolled.set_child(clamp)
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        clamp.set_child(content_box)
        
        # Info banner
        info_banner = Adw.Banner()
        info_banner.set_title(f"Setup tools for {self.distro.name}")
        info_banner.set_revealed(True)
        content_box.append(info_banner)
        
        # Get applicable tasks for this distro and desktop environment
        desktop = get_desktop()
        tasks = get_tasks_for_distro(self.distro.family, desktop.desktop_env)
        
        # Group tasks by category
        categories = {}
        for task in tasks:
            cat = task.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(task)
        
        # Create category groups
        category_names = {
            SetupCategory.DISTRO: "System Essentials",
            SetupCategory.CODECS: "Multimedia",
            SetupCategory.DRIVERS: "Drivers",
            SetupCategory.REPOS: "Repositories",
            SetupCategory.DESKTOP: "Desktop",
        }
        
        # Detect GPUs and show recommendations before Drivers section
        detected_gpus = detect_gpus()
        if detected_gpus:
            gpu_group = Adw.PreferencesGroup()
            gpu_group.set_title("🔍 Detected Graphics Hardware")
            gpu_group.set_description("Your system's GPUs and recommended drivers - click for details")
            content_box.append(gpu_group)
            
            for gpu in detected_gpus:
                gpu_row = Adw.ActionRow()
                gpu_row.set_title(gpu.name)
                
                # Set subtitle with recommendation
                if gpu.recommended_driver:
                    gpu_row.set_subtitle(f"Recommended: {gpu.driver_notes}")
                else:
                    gpu_row.set_subtitle("Driver recommendation not available")
                
                # Vendor icon
                if gpu.vendor == 'nvidia':
                    gpu_row.add_prefix(Gtk.Image.new_from_icon_name("video-display-symbolic"))
                    vendor_badge = Gtk.Label(label="NVIDIA")
                    vendor_badge.add_css_class("success")
                elif gpu.vendor == 'amd':
                    gpu_row.add_prefix(Gtk.Image.new_from_icon_name("video-display-symbolic"))
                    vendor_badge = Gtk.Label(label="AMD")
                    vendor_badge.add_css_class("accent")
                elif gpu.vendor == 'intel':
                    gpu_row.add_prefix(Gtk.Image.new_from_icon_name("video-display-symbolic"))
                    vendor_badge = Gtk.Label(label="Intel")
                    vendor_badge.add_css_class("dim-label")
                else:
                    gpu_row.add_prefix(Gtk.Image.new_from_icon_name("video-display-symbolic"))
                    vendor_badge = Gtk.Label(label="Unknown")
                
                vendor_badge.set_valign(Gtk.Align.CENTER)
                gpu_row.add_suffix(vendor_badge)
                
                # Make row activatable to show details
                gpu_row.set_activatable(True)
                gpu_row.connect("activated", self._on_gpu_row_activated, gpu)
                
                # If we have a recommendation, add a "Select" button to auto-select
                if gpu.recommended_driver:
                    select_btn = Gtk.Button(label="Select")
                    select_btn.set_valign(Gtk.Align.CENTER)
                    select_btn.add_css_class("flat")
                    select_btn.connect("clicked", self._on_select_recommended_driver, gpu.recommended_driver)
                    gpu_row.add_suffix(select_btn)
                
                gpu_group.add(gpu_row)
        
        for category, cat_tasks in categories.items():
            group = self.create_task_group(
                category_names.get(category, category.value),
                cat_tasks
            )
            content_box.append(group)
        
        # Bottom action bar
        action_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        action_bar.set_halign(Gtk.Align.CENTER)
        action_bar.set_margin_top(20)
        content_box.append(action_bar)
        
        # Select All button
        select_all_btn = Gtk.Button(label="Select All")
        select_all_btn.connect("clicked", self.on_select_all)
        action_bar.append(select_all_btn)
        
        # Clear button
        clear_btn = Gtk.Button(label="Clear")
        clear_btn.connect("clicked", self.on_clear_selection)
        action_bar.append(clear_btn)
        
        # Install button
        self.install_btn = Gtk.Button(label="Install Selected")
        self.install_btn.add_css_class("suggested-action")
        self.install_btn.connect("clicked", self.on_install_clicked)
        self.install_btn.set_sensitive(False)
        action_bar.append(self.install_btn)
    
    def create_task_group(self, title: str, tasks: list[SetupTask]) -> Gtk.Widget:
        """Create a group of task checkboxes."""
        group = Adw.PreferencesGroup()
        group.set_title(title)
        
        # Store checkbox references for this group
        if not hasattr(self, 'task_checkboxes'):
            self.task_checkboxes = {}
        
        for task in tasks:
            row = Adw.ActionRow()
            row.set_title(task.name)
            row.set_subtitle(task.description)
            
            # Checkbox - clicking this queues the item
            checkbox = Gtk.CheckButton()
            checkbox.set_valign(Gtk.Align.CENTER)
            checkbox.connect("toggled", self.on_task_toggled, task.id)
            row.add_prefix(checkbox)
            
            # Store checkbox reference for later access
            self.task_checkboxes[task.id] = checkbox
            checkbox.task_id = task.id
            
            # Make row clickable to show details (NOT linked to checkbox)
            row.set_activatable(True)
            row.connect("activated", self.on_task_row_clicked, task)
            
            # Arrow to indicate clickable for details
            arrow = Gtk.Image.new_from_icon_name("go-next-symbolic")
            row.add_suffix(arrow)
            
            # Reboot indicator if needed
            if task.requires_reboot:
                reboot_icon = Gtk.Image.new_from_icon_name("system-reboot-symbolic")
                reboot_icon.set_tooltip_text("Requires reboot")
                row.add_suffix(reboot_icon)
            
            group.add(row)
        
        return group
    
    def on_task_row_clicked(self, row, task: SetupTask):
        """Show task detail page when row text is clicked."""
        detail_page = TaskDetailPage(
            task=task,
            distro_family=self.distro.family,
            is_queued=task.id in self.selected_tasks,
            on_queue_changed=self.on_detail_queue_changed,
            window=self.window
        )
        self.window.navigation_view.push(detail_page)
    
    def on_detail_queue_changed(self, task_id: str, queued: bool):
        """Handle queue change from detail page."""
        if queued:
            self.selected_tasks.add(task_id)
        else:
            self.selected_tasks.discard(task_id)
        
        # Update checkbox state
        if task_id in self.task_checkboxes:
            checkbox = self.task_checkboxes[task_id]
            # Block signal to prevent recursion
            checkbox.handler_block_by_func(self.on_task_toggled)
            checkbox.set_active(queued)
            checkbox.handler_unblock_by_func(self.on_task_toggled)
        
        # Update install button
        self._update_install_button()
    
    def on_task_toggled(self, checkbox: Gtk.CheckButton, task_id: str):
        """Handle task checkbox toggle."""
        if checkbox.get_active():
            self.selected_tasks.add(task_id)
        else:
            self.selected_tasks.discard(task_id)
        
        self._update_install_button()
    
    def _update_install_button(self):
        """Update the install button state and label."""
        count = len(self.selected_tasks)
        self.install_btn.set_sensitive(count > 0)
        if count > 0:
            self.install_btn.set_label(f"Install Selected ({count})")
        else:
            self.install_btn.set_label("Install Selected")
    
    def on_select_all(self, button):
        """Select all tasks."""
        for task_id, checkbox in self.task_checkboxes.items():
            checkbox.set_active(True)
    
    def on_clear_selection(self, button):
        """Clear all selections."""
        for task_id, checkbox in self.task_checkboxes.items():
            checkbox.set_active(False)
    
    def _on_select_recommended_driver(self, button, driver_id: str):
        """Select the recommended driver from GPU detection."""
        if driver_id in self.task_checkboxes:
            # First clear any other GPU driver selections to avoid conflicts
            gpu_driver_ids = [
                'nvidia_latest', 'nvidia_550', 'nvidia_535', 'nvidia_470', 'nvidia_390', 'nvidia_open',
                'amd_graphics', 'amd_pro_graphics', 'intel_graphics'
            ]
            for did in gpu_driver_ids:
                if did in self.task_checkboxes and did != driver_id:
                    self.task_checkboxes[did].set_active(False)
            
            # Select the recommended driver
            self.task_checkboxes[driver_id].set_active(True)
            self.window.show_toast("Selected recommended driver")
            
            # Show repo/driver hints for NVIDIA on some distros
            self._maybe_show_driver_repo_warning(driver_id)
        else:
            self.window.show_toast("Driver not available for your distribution")
    
    def _on_gpu_row_activated(self, row, gpu: DetectedGPU):
        """Show a details dialog for the selected GPU."""
        # Build details string
        lines = [
            f"🖥️  {gpu.name}",
            "",
        ]
        
        if gpu.pci_id:
            lines.append(f"PCI ID: {gpu.pci_id}")
        
        if gpu.vendor:
            lines.append(f"Vendor: {gpu.vendor.upper()}")
        
        if gpu.recommended_driver:
            lines.append("")
            lines.append("Recommended driver:")
            lines.append(f"  • {gpu.recommended_driver}")
            if gpu.driver_notes:
                lines.append(f"    ({gpu.driver_notes})")
        
        body = "\n".join(lines)
        
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="GPU Details",
            body=body or "No additional details available."
        )
        dialog.add_response("ok", "OK")
        dialog.set_default_response("ok")
        dialog.present()
    
    def _maybe_show_driver_repo_warning(self, driver_id: str):
        """Show a hint if the selected driver likely needs extra repos."""
        # Only care about NVIDIA drivers
        if not driver_id.startswith("nvidia_"):
            return
        
        message = None
        
        if self.distro.family == DistroFamily.FEDORA:
            message = (
                "On Fedora, NVIDIA drivers require RPM Fusion (nonfree). "
                "If installation fails, enable RPM Fusion first from the Repositories section."
            )
        elif self.distro.family == DistroFamily.DEBIAN:
            message = (
                "On Debian, NVIDIA drivers require non-free / contrib repositories. "
                "If installation fails, enable those repos in your sources.list first."
            )
        
        if message:
            # Show as a dialog since toasts might be too short for this info
            dialog = Adw.MessageDialog(
                transient_for=self.window,
                heading="NVIDIA Driver Notice",
                body=message
            )
            dialog.add_response("ok", "Got it")
            dialog.set_default_response("ok")
            dialog.present()
    
    def on_install_clicked(self, button):
        """Start installation of selected tasks."""
        if not self.selected_tasks:
            return
        
        # Get the actual task objects
        tasks_to_install = [
            task for task in ALL_TASKS 
            if task.id in self.selected_tasks
        ]
        
        # Count available packages (not wishlist)
        total_packages = 0
        family_str = self.distro.family.value if hasattr(self.distro.family, 'value') else str(self.distro.family)
        for task in tasks_to_install:
            wishlist = task.get_packages_for_distro(self.distro.family)
            available = filter_available_packages(wishlist, family_str)
            total_packages += len(available)
        
        # Check for reboot requirements
        needs_reboot = any(t.requires_reboot for t in tasks_to_install)
        reboot_warning = "\n\n⚠️ Some selections require a reboot after installation." if needs_reboot else ""
        
        # Build task list for confirmation
        task_list = "\n".join(f"  • {t.name}" for t in tasks_to_install)
        
        # Show confirmation dialog
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Confirm Installation",
            body=f"Install {len(tasks_to_install)} items (~{total_packages} packages)?\n\n{task_list}{reboot_warning}"
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("install", "Install")
        dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("install")
        dialog.set_close_response("cancel")
        
        dialog.connect("response", self._on_confirm_response, tasks_to_install)
        dialog.present()
    
    def _on_confirm_response(self, dialog, response, tasks_to_install):
        """Handle confirmation dialog response."""
        if response == "install":
            # Open installation dialog
            install_dialog = InstallationDialog(self.window, tasks_to_install, self.distro.family)
            install_dialog.present()


class SSHKeyRestoreDialog(Adw.Dialog):
    """Dialog for restoring SSH keys via drag and drop."""
    
    def __init__(self, parent, distro):
        super().__init__()
        
        self.parent_window = parent
        self.distro = distro
        self.private_key_data = None
        self.public_key_data = None
        self.private_key_name = None
        self.public_key_name = None
        
        self.set_title("Restore SSH Keys")
        self.set_content_width(550)
        self.set_content_height(550)
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the dialog UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_btn)
        
        toolbar_view.add_top_bar(header)
        
        # Content
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        content.set_margin_top(20)
        content.set_margin_bottom(20)
        content.set_margin_start(20)
        content.set_margin_end(20)
        toolbar_view.set_content(content)
        
        # Instructions
        info_label = Gtk.Label()
        info_label.set_markup(
            "<b>Drag and drop your SSH key files here</b>\n"
            "<small>Drop both <tt>id_ed25519</tt> (private) and <tt>id_ed25519.pub</tt> (public)</small>"
        )
        info_label.set_halign(Gtk.Align.CENTER)
        info_label.set_justify(Gtk.Justification.CENTER)
        content.append(info_label)
        
        # Drop zone
        self.drop_zone = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.drop_zone.set_size_request(-1, 150)
        self.drop_zone.set_valign(Gtk.Align.CENTER)
        self.drop_zone.set_halign(Gtk.Align.CENTER)
        self.drop_zone.add_css_class("card")
        self.drop_zone.set_margin_top(10)
        self.drop_zone.set_margin_bottom(10)
        
        # Make it expand to fill space
        drop_frame = Gtk.Frame()
        drop_frame.set_child(self.drop_zone)
        drop_frame.set_vexpand(True)
        content.append(drop_frame)
        
        # Drop zone content
        drop_icon = Gtk.Image.new_from_icon_name("document-send-symbolic")
        drop_icon.set_pixel_size(48)
        drop_icon.add_css_class("dim-label")
        self.drop_zone.append(drop_icon)
        
        self.drop_label = Gtk.Label(label="Drop SSH key files here")
        self.drop_label.add_css_class("dim-label")
        self.drop_zone.append(self.drop_label)
        
        # Status labels for each file
        self.status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.status_box.set_halign(Gtk.Align.CENTER)
        self.drop_zone.append(self.status_box)
        
        self.private_status = Gtk.Label()
        self.private_status.set_markup("<small>Private key: ❌ Not loaded</small>")
        self.status_box.append(self.private_status)
        
        self.public_status = Gtk.Label()
        self.public_status.set_markup("<small>Public key: ❌ Not loaded</small>")
        self.status_box.append(self.public_status)
        
        # Setup drag and drop
        drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
        drop_target.connect("drop", self._on_file_dropped)
        drop_target.connect("enter", self._on_drag_enter)
        drop_target.connect("leave", self._on_drag_leave)
        drop_frame.add_controller(drop_target)
        
        # Git identity section
        identity_group = Adw.PreferencesGroup()
        identity_group.set_title("Git Identity")
        identity_group.set_description("Set your name and email for commits")
        content.append(identity_group)
        
        self.name_entry = Adw.EntryRow()
        self.name_entry.set_title("Name")
        self.name_entry.set_text("Christopher Dorrell")
        identity_group.add(self.name_entry)
        
        self.email_entry = Adw.EntryRow()
        self.email_entry.set_title("Email")
        self.email_entry.set_text("dorrellkc@gmail.com")
        identity_group.add(self.email_entry)
        
        # Restore button
        self.restore_btn = Gtk.Button(label="Restore Keys & Setup Git")
        self.restore_btn.add_css_class("suggested-action")
        self.restore_btn.add_css_class("pill")
        self.restore_btn.set_sensitive(False)
        self.restore_btn.set_halign(Gtk.Align.CENTER)
        self.restore_btn.set_margin_top(10)
        self.restore_btn.connect("clicked", self._on_restore_clicked)
        content.append(self.restore_btn)
        
        # Result area (hidden initially)
        self.result_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.result_box.set_visible(False)
        self.result_box.set_margin_top(10)
        content.append(self.result_box)
        
        self.result_label = Gtk.Label()
        self.result_label.set_wrap(True)
        self.result_label.set_halign(Gtk.Align.CENTER)
        self.result_box.append(self.result_label)
    
    def _on_drag_enter(self, drop_target, x, y):
        """Handle drag enter."""
        self.drop_label.set_text("Release to drop files")
        return Gdk.DragAction.COPY
    
    def _on_drag_leave(self, drop_target):
        """Handle drag leave."""
        self.drop_label.set_text("Drop SSH key files here")
    
    def _on_file_dropped(self, drop_target, value, x, y):
        """Handle file drop."""
        if not isinstance(value, Gio.File):
            return False
        
        filepath = value.get_path()
        filename = value.get_basename()
        
        try:
            with open(filepath, 'r') as f:
                file_content = f.read()
            
            # Determine if it's private or public key
            if filename.endswith('.pub') or 'ssh-' in file_content[:20]:
                # Public key
                self.public_key_data = file_content
                self.public_key_name = filename
                self.public_status.set_markup(f"<small>Public key: ✅ {filename}</small>")
            elif 'PRIVATE KEY' in file_content or not filename.endswith('.pub'):
                # Private key
                self.private_key_data = file_content
                self.private_key_name = filename
                self.private_status.set_markup(f"<small>Private key: ✅ {filename}</small>")
            
            # Check if both keys are loaded
            if self.private_key_data and self.public_key_data:
                self.drop_label.set_text("Both keys loaded!")
                self.restore_btn.set_sensitive(True)
            else:
                self.drop_label.set_text("Drop the other key file")
            
            return True
            
        except Exception as e:
            self.drop_label.set_text(f"Error: {e}")
            return False
    
    def _on_restore_clicked(self, button):
        """Restore SSH keys and configure git."""
        import os
        import subprocess
        import stat
        
        button.set_sensitive(False)
        button.set_label("Restoring...")
        
        ssh_dir = os.path.expanduser("~/.ssh")
        results = []
        
        try:
            # Create .ssh directory if needed
            os.makedirs(ssh_dir, exist_ok=True)
            os.chmod(ssh_dir, stat.S_IRWXU)  # 700
            results.append("✅ Created ~/.ssh directory")
            
            # Write private key
            private_path = os.path.join(ssh_dir, self.private_key_name or "id_ed25519")
            with open(private_path, 'w') as f:
                f.write(self.private_key_data)
            os.chmod(private_path, stat.S_IRUSR | stat.S_IWUSR)  # 600
            results.append(f"✅ Saved private key")
            
            # Write public key
            public_path = os.path.join(ssh_dir, self.public_key_name or "id_ed25519.pub")
            with open(public_path, 'w') as f:
                f.write(self.public_key_data)
            os.chmod(public_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)  # 644
            results.append(f"✅ Saved public key")
            
            # Set git identity
            name = self.name_entry.get_text().strip()
            email = self.email_entry.get_text().strip()
            
            if name:
                subprocess.run(['git', 'config', '--global', 'user.name', name], check=True)
                results.append(f"✅ Set git name: {name}")
            
            if email:
                subprocess.run(['git', 'config', '--global', 'user.email', email], check=True)
                results.append(f"✅ Set git email: {email}")
            
            # Start ssh-agent and add key
            try:
                # Test GitHub connection
                result = subprocess.run(
                    ['ssh', '-T', '-o', 'StrictHostKeyChecking=no', 'git@github.com'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                # GitHub returns exit code 1 but with success message
                if 'successfully authenticated' in result.stderr.lower():
                    results.append("✅ GitHub connection verified!")
                elif 'permission denied' in result.stderr.lower():
                    results.append("⚠️ Key saved but GitHub test failed - check key is added to GitHub")
                else:
                    results.append("⚠️ Could not verify GitHub - try: ssh -T git@github.com")
            except subprocess.TimeoutExpired:
                results.append("⚠️ GitHub test timed out")
            except Exception as e:
                results.append(f"⚠️ GitHub test skipped: {e}")
            
            # Show success
            self.result_label.set_markup(
                "<b>SSH Keys Restored!</b>\n\n" + 
                "\n".join(results)
            )
            self.result_box.set_visible(True)
            button.set_label("Done!")
            button.remove_css_class("suggested-action")
            
        except Exception as e:
            self.result_label.set_markup(f"<b>Error</b>\n\n{e}")
            self.result_box.set_visible(True)
            button.set_label("Restore Keys & Setup Git")
            button.set_sensitive(True)


class GitCloneDialog(Adw.Dialog):
    """Dialog for cloning a git repository."""
    
    def __init__(self, parent, distro):
        super().__init__()
        
        self.parent_window = parent
        self.distro = distro
        
        self.set_title("Clone Git Repository")
        self.set_content_width(500)
        self.set_content_height(400)
        
        self._build_ui()
    
    def _build_ui(self):
        """Build the dialog UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_btn)
        
        self.clone_btn = Gtk.Button(label="Clone")
        self.clone_btn.add_css_class("suggested-action")
        self.clone_btn.set_sensitive(False)
        self.clone_btn.connect("clicked", self._on_clone_clicked)
        header.pack_end(self.clone_btn)
        
        toolbar_view.add_top_bar(header)
        
        # Content
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        content.set_margin_top(20)
        content.set_margin_bottom(20)
        content.set_margin_start(20)
        content.set_margin_end(20)
        toolbar_view.set_content(content)
        
        # Instructions
        info_label = Gtk.Label()
        info_label.set_markup(
            "<b>Enter the repository URL</b>\n"
            "<small>Example: https://github.com/username/repo-name.git</small>"
        )
        info_label.set_halign(Gtk.Align.START)
        content.append(info_label)
        
        # URL Entry
        url_group = Adw.PreferencesGroup()
        content.append(url_group)
        
        self.url_entry = Adw.EntryRow()
        self.url_entry.set_title("Repository URL")
        self.url_entry.connect("changed", self._on_url_changed)
        url_group.add(self.url_entry)
        
        # Destination folder
        dest_group = Adw.PreferencesGroup()
        dest_group.set_title("Destination")
        content.append(dest_group)
        
        self.dest_entry = Adw.EntryRow()
        self.dest_entry.set_title("Clone to folder")
        self.dest_entry.set_text("~/Development")
        dest_group.add(self.dest_entry)
        
        # Git check / install
        self.git_status = Adw.ActionRow()
        self.git_status.set_title("Git")
        self._check_git_installed()
        dest_group.add(self.git_status)
        
        # Output area (hidden initially)
        self.output_group = Adw.PreferencesGroup()
        self.output_group.set_title("Output")
        self.output_group.set_visible(False)
        content.append(self.output_group)
        
        self.output_label = Gtk.Label()
        self.output_label.set_halign(Gtk.Align.START)
        self.output_label.set_wrap(True)
        self.output_label.set_selectable(True)
        self.output_group.add(self.output_label)
    
    def _check_git_installed(self):
        """Check if git is installed."""
        import subprocess
        try:
            result = subprocess.run(['which', 'git'], capture_output=True, text=True)
            if result.returncode == 0:
                self.git_installed = True
                self.git_status.set_subtitle("Installed ✓")
                self.git_status.add_suffix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
            else:
                self._show_git_not_installed()
        except Exception:
            self._show_git_not_installed()
    
    def _show_git_not_installed(self):
        """Show git not installed state with install button."""
        self.git_installed = False
        self.git_status.set_subtitle("Not installed")
        
        install_btn = Gtk.Button(label="Install")
        install_btn.add_css_class("suggested-action")
        install_btn.connect("clicked", self._on_install_git)
        self.git_status.add_suffix(install_btn)
    
    def _on_install_git(self, button):
        """Install git."""
        import subprocess
        
        button.set_sensitive(False)
        button.set_label("Installing...")
        
        # Get install command for distro
        if self.distro.family == DistroFamily.ARCH:
            cmd = ["pkexec", "pacman", "-S", "--noconfirm", "git"]
        elif self.distro.family == DistroFamily.DEBIAN:
            cmd = ["pkexec", "apt-get", "install", "-y", "git"]
        elif self.distro.family == DistroFamily.FEDORA:
            cmd = ["pkexec", "dnf", "install", "-y", "git"]
        elif self.distro.family == DistroFamily.SUSE:
            cmd = ["pkexec", "zypper", "install", "-y", "git"]
        else:
            self.git_status.set_subtitle("Please install git manually")
            return
        
        def install_thread():
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                GLib.idle_add(self._on_git_install_complete, result.returncode == 0)
            except Exception as e:
                GLib.idle_add(self._on_git_install_complete, False)
        
        import threading
        threading.Thread(target=install_thread, daemon=True).start()
    
    def _on_git_install_complete(self, success):
        """Handle git installation complete."""
        # Remove the install button
        while self.git_status.get_last_child():
            child = self.git_status.get_last_child()
            if isinstance(child, Gtk.Button) or isinstance(child, Gtk.Image):
                self.git_status.remove(child)
            else:
                break
        
        if success:
            self.git_installed = True
            self.git_status.set_subtitle("Installed ✓")
            self.git_status.add_suffix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
            self._on_url_changed(self.url_entry)  # Re-check if clone button should enable
        else:
            self.git_status.set_subtitle("Installation failed")
            install_btn = Gtk.Button(label="Retry")
            install_btn.connect("clicked", self._on_install_git)
            self.git_status.add_suffix(install_btn)
    
    def _on_url_changed(self, entry):
        """Validate URL and enable/disable clone button."""
        url = entry.get_text().strip()
        valid = (
            url.startswith("https://") or url.startswith("git@")
        ) and len(url) > 10 and hasattr(self, 'git_installed') and self.git_installed
        
        self.clone_btn.set_sensitive(valid)
    
    def _on_clone_clicked(self, button):
        """Clone the repository."""
        import subprocess
        import os
        
        url = self.url_entry.get_text().strip()
        dest = os.path.expanduser(self.dest_entry.get_text().strip())
        
        # Extract repo name from URL
        repo_name = url.rstrip('/').split('/')[-1]
        if repo_name.endswith('.git'):
            repo_name = repo_name[:-4]
        
        full_dest = os.path.join(dest, repo_name)
        
        # Show output area
        self.output_group.set_visible(True)
        self.output_label.set_text(f"Cloning {url}...")
        self.clone_btn.set_sensitive(False)
        self.clone_btn.set_label("Cloning...")
        
        def clone_thread():
            try:
                # Create destination directory
                os.makedirs(dest, exist_ok=True)
                
                # Clone
                result = subprocess.run(
                    ['git', 'clone', url, full_dest],
                    capture_output=True,
                    text=True,
                    cwd=dest
                )
                
                if result.returncode == 0:
                    GLib.idle_add(self._on_clone_complete, True, full_dest, None)
                else:
                    error = result.stderr or result.stdout or "Unknown error"
                    GLib.idle_add(self._on_clone_complete, False, full_dest, error)
                    
            except Exception as e:
                GLib.idle_add(self._on_clone_complete, False, full_dest, str(e))
        
        import threading
        threading.Thread(target=clone_thread, daemon=True).start()
    
    def _on_clone_complete(self, success, path, error):
        """Handle clone completion."""
        if success:
            self.output_label.set_markup(
                f"<b>✓ Successfully cloned!</b>\n\n"
                f"Location: <tt>{path}</tt>\n\n"
                f"<small>You can close this dialog now.</small>"
            )
            self.clone_btn.set_label("Done")
            self.clone_btn.remove_css_class("suggested-action")
        else:
            self.output_label.set_markup(
                f"<b>✗ Clone failed</b>\n\n"
                f"<small>{error}</small>"
            )
            self.clone_btn.set_label("Clone")
            self.clone_btn.set_sensitive(True)


class InstallationDialog(Adw.Dialog):
    """Dialog showing installation progress."""
    
    def __init__(self, parent: Gtk.Window, tasks: list[SetupTask], family: DistroFamily):
        super().__init__()
        
        self.parent_window = parent
        self.tasks = tasks
        self.family = family
        self.pkg_manager = get_package_manager()
        self.current_task_index = 0
        self.cancelled = False
        self.install_thread = None
        
        # Track results
        self.successful_tasks = []
        self.failed_tasks = []
        self.needs_reboot = False
        
        self.set_title("Installing...")
        self.set_content_width(650)
        self.set_content_height(500)
        
        self.build_ui()
    
    def build_ui(self):
        """Build the installation dialog UI."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        box.set_margin_start(20)
        box.set_margin_end(20)
        self.set_child(box)
        
        # Status label
        self.status_label = Gtk.Label()
        self.status_label.set_markup("<b>Preparing installation...</b>")
        self.status_label.set_halign(Gtk.Align.START)
        box.append(self.status_label)
        
        # Current task label
        self.task_label = Gtk.Label()
        self.task_label.set_halign(Gtk.Align.START)
        self.task_label.add_css_class("dim-label")
        box.append(self.task_label)
        
        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        box.append(self.progress_bar)
        
        # Terminal output
        frame = Gtk.Frame()
        frame.set_vexpand(True)
        box.append(frame)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        frame.set_child(scrolled)
        
        self.output_view = Gtk.TextView()
        self.output_view.set_editable(False)
        self.output_view.set_monospace(True)
        self.output_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.output_view.set_left_margin(10)
        self.output_view.set_right_margin(10)
        self.output_view.set_top_margin(10)
        self.output_view.set_bottom_margin(10)
        self.output_buffer = self.output_view.get_buffer()
        scrolled.set_child(self.output_view)
        
        # Create text tags for colored output
        self.output_buffer.create_tag("success", foreground="#26a269")
        self.output_buffer.create_tag("error", foreground="#c01c28")
        self.output_buffer.create_tag("warning", foreground="#e5a50a")
        self.output_buffer.create_tag("info", foreground="#1c71d8")
        self.output_buffer.create_tag("header", weight=700)
        
        # Buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.END)
        box.append(button_box)
        
        self.cancel_btn = Gtk.Button(label="Cancel")
        self.cancel_btn.connect("clicked", self.on_cancel)
        button_box.append(self.cancel_btn)
        
        self.close_btn = Gtk.Button(label="Close")
        self.close_btn.add_css_class("suggested-action")
        self.close_btn.connect("clicked", self.on_close)
        self.close_btn.set_sensitive(False)
        button_box.append(self.close_btn)
        
        # Start installation after dialog is shown
        GLib.timeout_add(500, self.start_installation)
    
    def append_output(self, text: str, tag: str = None):
        """Append text to the output view, optionally with a tag."""
        end_iter = self.output_buffer.get_end_iter()
        if tag:
            self.output_buffer.insert_with_tags_by_name(end_iter, text + "\n", tag)
        else:
            self.output_buffer.insert(end_iter, text + "\n")
        
        # Auto-scroll to bottom
        GLib.idle_add(self._scroll_to_bottom)
    
    def _scroll_to_bottom(self):
        """Scroll output view to bottom."""
        mark = self.output_buffer.create_mark(None, self.output_buffer.get_end_iter(), False)
        self.output_view.scroll_mark_onscreen(mark)
        self.output_buffer.delete_mark(mark)
        return False
    
    def start_installation(self) -> bool:
        """Start the installation process in a background thread."""
        import threading
        
        self.append_output("=" * 50, "header")
        self.append_output("Tux Assistant - Installation", "header")
        self.append_output("=" * 50, "header")
        self.append_output(f"Tasks to install: {len(self.tasks)}", "info")
        self.append_output("")
        
        # Start installation in background thread
        self.install_thread = threading.Thread(target=self._run_installation, daemon=True)
        self.install_thread.start()
        
        return False  # Don't repeat timeout
    
    def _run_installation(self):
        """Run installation in background thread using tux-helper."""
        import subprocess
        import json
        import tempfile
        import os
        
        # Build the plan
        plan = {
            'tasks': []
        }
        
        for task in self.tasks:
            # Get wishlist and filter to only available packages
            wishlist = task.get_packages_for_distro(self.family)
            family_str = self.family.value if hasattr(self.family, 'value') else str(self.family)
            
            # Filter to available packages only
            packages = filter_available_packages(wishlist, family_str)
            
            # Report on unavailable packages
            unavailable = [p for p in wishlist if p not in packages]
            if unavailable:
                GLib.idle_add(
                    self.append_output, 
                    f"Note: Skipping unavailable packages: {', '.join(unavailable)}", 
                    "warning"
                )
            
            commands = task.get_commands_for_distro(self.family)
            
            # For most tasks: packages first, then commands (e.g., Flatpak needs to be installed before adding repos)
            # Exception: repo setup tasks (RPM Fusion, Packman) have only commands and should run first
            
            # If task has packages, install them first
            if packages:
                plan['tasks'].append({
                    'type': 'install',
                    'name': task.name,
                    'packages': packages
                })
            
            # Then run any setup commands (like adding Flathub after flatpak is installed)
            if commands:
                for cmd in commands:
                    # Convert command list to string, skip 'sudo' prefix
                    if cmd and cmd[0] == 'sudo':
                        cmd = cmd[1:]
                    cmd_str = ' '.join(cmd)
                    plan['tasks'].append({
                        'type': 'command',
                        'name': f"{task.name} (setup)",
                        'command': cmd_str
                    })
            
            # Run special handler if defined (e.g., emoji keyboard shortcut setup)
            if task.special_handler:
                plan['tasks'].append({
                    'type': 'special',
                    'name': f"{task.name} (configure)",
                    'app_id': task.special_handler
                })
        
        # Write plan to temp file
        plan_file = tempfile.NamedTemporaryFile(
            mode='w', 
            suffix='.json', 
            prefix='ltk-plan-',
            delete=False
        )
        json.dump(plan, plan_file)
        plan_file.close()
        
        GLib.idle_add(self.append_output, f"Plan created with {len(plan['tasks'])} task(s)", "info")
        GLib.idle_add(self.append_output, "")
        
        # Find tux-helper
        helper_paths = [
            '/usr/bin/tux-helper',
            '/usr/local/bin/tux-helper',
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'tux-helper'),
            os.path.join(os.path.dirname(sys.argv[0]), 'tux-helper'),
        ]
        
        helper_path = None
        for path in helper_paths:
            if os.path.exists(path):
                helper_path = path
                break
        
        if not helper_path:
            GLib.idle_add(self.append_output, "Error: tux-helper not found!", "error")
            GLib.idle_add(self.append_output, "Searched paths:", "error")
            for p in helper_paths:
                GLib.idle_add(self.append_output, f"  {p}", "error")
            GLib.idle_add(self._installation_complete)
            return
        
        GLib.idle_add(self.append_output, f"Using helper: {helper_path}", "info")
        GLib.idle_add(self.append_output, "Requesting authentication...", "info")
        GLib.idle_add(self.append_output, "")
        
        # Check if pkexec is available, otherwise fall back to sudo in terminal
        import shutil
        use_pkexec = shutil.which('pkexec') is not None
        
        if use_pkexec:
            # Run pkexec tux-helper --execute-plan <planfile>
            cmd = ['pkexec', helper_path, '--execute-plan', plan_file.name]
        else:
            # Fallback: try sudo directly (user will be prompted in terminal output)
            GLib.idle_add(self.append_output, "Note: pkexec not found, using sudo fallback", "warning")
            cmd = ['sudo', helper_path, '--execute-plan', plan_file.name]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            for line in process.stdout:
                if self.cancelled:
                    process.terminate()
                    break
                
                line = line.rstrip()
                if not line:
                    continue
                
                # Parse tux-helper status messages
                if line.startswith('[Tux Assistant:'):
                    # Extract status type and message
                    try:
                        end_bracket = line.index(']')
                        status_type = line[5:end_bracket].lower()
                        message = line[end_bracket + 2:]
                        
                        if status_type == 'success':
                            GLib.idle_add(self.append_output, f"✓ {message}", "success")
                            # Track successful task
                            for task in self.tasks:
                                if task.name in message:
                                    self.successful_tasks.append(task)
                                    if task.requires_reboot:
                                        self.needs_reboot = True
                                    break
                        elif status_type == 'error':
                            GLib.idle_add(self.append_output, f"✗ {message}", "error")
                        elif status_type == 'warning':
                            GLib.idle_add(self.append_output, f"⚠ {message}", "warning")
                        elif status_type == 'start':
                            GLib.idle_add(self.append_output, f"→ {message}", "info")
                        elif status_type == 'progress':
                            # Update progress bar
                            parts = message.split(' ', 1)
                            if '/' in parts[0]:
                                current, total = parts[0].split('/')
                                try:
                                    progress = int(current) / int(total)
                                    task_name = parts[1] if len(parts) > 1 else ""
                                    GLib.idle_add(self._update_progress_from_helper, progress, current, total, task_name)
                                except ValueError:
                                    pass
                        elif status_type == 'complete':
                            GLib.idle_add(self.append_output, f"● {message}", "info")
                        else:
                            GLib.idle_add(self.append_output, line)
                    except (ValueError, IndexError):
                        GLib.idle_add(self.append_output, line)
                else:
                    # Regular output
                    GLib.idle_add(self.append_output, line)
            
            process.wait()
            
            if process.returncode != 0 and not self.cancelled:
                GLib.idle_add(self.append_output, "", None)
                GLib.idle_add(self.append_output, f"Helper exited with code {process.returncode}", "warning")
        
        except FileNotFoundError:
            GLib.idle_add(self.append_output, "Error: Neither pkexec nor sudo found!", "error")
            GLib.idle_add(self.append_output, "Please install polkit (policykit-1 on Debian)", "error")
        except Exception as e:
            GLib.idle_add(self.append_output, f"Error: {str(e)}", "error")
        finally:
            # Clean up plan file
            try:
                os.unlink(plan_file.name)
            except:
                pass
        
        # Done
        GLib.idle_add(self._installation_complete)
    
    def _update_progress_from_helper(self, progress: float, current: str, total: str, task_name: str):
        """Update progress from helper output."""
        self.progress_bar.set_fraction(progress)
        self.progress_bar.set_text(f"{current}/{total}")
        if task_name:
            self.status_label.set_markup(f"<b>Installing: {task_name}</b>")
            self.task_label.set_text("")
    
    def _update_progress(self, task: SetupTask, progress: float, current: int, total: int):
        """Update progress UI (called from main thread)."""
        self.status_label.set_markup(f"<b>Installing: {task.name}</b>")
        self.task_label.set_text(task.description)
        self.progress_bar.set_fraction(progress)
        self.progress_bar.set_text(f"{current}/{total}")
    
    def _installation_complete(self):
        """Handle installation completion (called from main thread)."""
        self.progress_bar.set_fraction(1.0)
        
        if self.cancelled:
            self.status_label.set_markup("<b>Installation cancelled</b>")
            self.progress_bar.set_text("Cancelled")
        else:
            self.status_label.set_markup("<b>Installation complete!</b>")
            self.progress_bar.set_text("Done")
        
        self.task_label.set_text("")
        
        # Summary
        self.append_output("=" * 50, "header")
        self.append_output("Summary", "header")
        self.append_output("=" * 50, "header")
        
        if self.successful_tasks:
            self.append_output(f"✓ Successful: {len(self.successful_tasks)}", "success")
            for task in self.successful_tasks:
                self.append_output(f"  • {task.name}", "success")
        
        if self.failed_tasks:
            self.append_output(f"✗ Issues: {len(self.failed_tasks)}", "error")
            for task in self.failed_tasks:
                self.append_output(f"  • {task.name}", "error")
        
        if self.needs_reboot:
            self.append_output("")
            self.append_output("⚠ A reboot is recommended for some changes to take effect", "warning")
        
        self.cancel_btn.set_sensitive(False)
        self.close_btn.set_sensitive(True)
    
    def on_cancel(self, button):
        """Handle cancel button."""
        self.cancelled = True
        self.append_output("")
        self.append_output("⚠ Cancelling... (current operation will complete)", "warning")
        self.cancel_btn.set_sensitive(False)
    
    def on_close(self, button):
        """Handle close button."""
        self.close()
