"""
Tux Assistant - Distribution Detection

Detects the Linux distribution and family for package management.

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
"""

import os
import shutil
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class DistroFamily(Enum):
    """Linux distribution families based on package manager."""
    ARCH = "arch"
    DEBIAN = "debian"
    FEDORA = "fedora"
    RHEL = "rhel"
    OPENSUSE = "opensuse"
    UNKNOWN = "unknown"


# Map distro IDs to their family
DISTRO_FAMILY_MAP = {
    DistroFamily.ARCH: [
        'arch', 'manjaro', 'cachyos', 'endeavouros', 'garuda', 'artix',
        'arcolinux', 'archcraft', 'rebornos', 'bluestar', 'startde'
    ],
    DistroFamily.DEBIAN: [
        'debian', 'ubuntu', 'linuxmint', 'pop', 'elementary', 'zorin',
        'kali', 'parrot', 'mx', 'antix', 'lmde', 'devuan', 'pureos',
        'neon', 'kubuntu', 'xubuntu', 'lubuntu', 'ubuntumate',
        'siduction', 'forky',  # Debian Sid/Testing derivatives
        'tuxedo', 'tuxedoos', 'kubuntufocus'  # Ubuntu derivatives
    ],
    DistroFamily.FEDORA: [
        'fedora', 'nobara', 'ultramarine', 'risi', 'qubes'
    ],
    DistroFamily.RHEL: [
        'rhel', 'centos', 'rocky', 'alma', 'almalinux', 'ol', 'oracle',
        'eurolinux', 'scientific'
    ],
    DistroFamily.OPENSUSE: [
        'opensuse', 'opensuse-leap', 'opensuse-tumbleweed', 'suse', 'sles',
        'geckolinux'
    ],
}


@dataclass
class DistroInfo:
    """Information about the detected distribution."""
    id: str
    name: str
    version: str
    family: DistroFamily
    package_manager: str
    install_cmd: list[str]
    search_cmd: list[str]
    update_cmd: list[str]
    
    @property
    def is_arch_based(self) -> bool:
        return self.family == DistroFamily.ARCH
    
    @property
    def is_debian_based(self) -> bool:
        return self.family == DistroFamily.DEBIAN
    
    @property
    def is_fedora_based(self) -> bool:
        return self.family == DistroFamily.FEDORA
    
    @property
    def is_rhel_based(self) -> bool:
        return self.family == DistroFamily.RHEL
    
    @property
    def is_opensuse_based(self) -> bool:
        return self.family == DistroFamily.OPENSUSE


def parse_os_release() -> dict[str, str]:
    """Parse /etc/os-release into a dictionary."""
    data = {}
    os_release_paths = ['/etc/os-release', '/usr/lib/os-release']
    
    for path in os_release_paths:
        if os.path.exists(path):
            with open(path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        key, value = line.split('=', 1)
                        # Remove quotes from value
                        value = value.strip('"\'')
                        data[key] = value
            break
    
    return data


def detect_family(distro_id: str) -> DistroFamily:
    """Determine the distribution family from the distro ID."""
    distro_id_lower = distro_id.lower()
    
    for family, members in DISTRO_FAMILY_MAP.items():
        if distro_id_lower in members:
            return family
    
    # Try partial matching for derivatives
    for family, members in DISTRO_FAMILY_MAP.items():
        for member in members:
            if member in distro_id_lower or distro_id_lower in member:
                return family
    
    return DistroFamily.UNKNOWN


def get_package_manager_info(family: DistroFamily) -> tuple[str, list[str], list[str], list[str]]:
    """Get package manager commands for a distribution family."""
    
    if family == DistroFamily.ARCH:
        return (
            'pacman',
            ['sudo', 'pacman', '-S', '--needed', '--noconfirm'],
            ['pacman', '-Ss'],
            ['sudo', 'pacman', '-Syu', '--noconfirm']
        )
    
    elif family == DistroFamily.DEBIAN:
        return (
            'apt',
            ['sudo', 'apt', 'install', '-y'],
            ['apt', 'search'],
            ['sudo', 'apt', 'update', '&&', 'sudo', 'apt', 'upgrade', '-y']
        )
    
    elif family == DistroFamily.FEDORA:
        return (
            'dnf',
            ['sudo', 'dnf', 'install', '-y'],
            ['dnf', 'search'],
            ['sudo', 'dnf', 'upgrade', '-y']
        )
    
    elif family == DistroFamily.RHEL:
        # Check if dnf is available, otherwise use yum
        if shutil.which('dnf'):
            return (
                'dnf',
                ['sudo', 'dnf', 'install', '-y'],
                ['dnf', 'search'],
                ['sudo', 'dnf', 'upgrade', '-y']
            )
        else:
            return (
                'yum',
                ['sudo', 'yum', 'install', '-y'],
                ['yum', 'search'],
                ['sudo', 'yum', 'upgrade', '-y']
            )
    
    elif family == DistroFamily.OPENSUSE:
        return (
            'zypper',
            ['sudo', 'zypper', 'install', '-y'],
            ['zypper', 'search'],
            ['sudo', 'zypper', 'update', '-y']
        )
    
    else:
        return ('unknown', [], [], [])


def detect_aur_helper() -> Optional[str]:
    """Detect installed AUR helper on Arch-based systems."""
    aur_helpers = ['paru', 'yay', 'pikaur', 'trizen', 'aurman']
    
    for helper in aur_helpers:
        if shutil.which(helper):
            return helper
    
    return None


def detect() -> DistroInfo:
    """Detect the current Linux distribution and return full info."""
    os_release = parse_os_release()
    
    distro_id = os_release.get('ID', 'unknown')
    distro_name = os_release.get('NAME', 'Unknown Linux')
    distro_version = os_release.get('VERSION_ID', os_release.get('VERSION', 'unknown'))
    
    family = detect_family(distro_id)
    pkg_mgr, install_cmd, search_cmd, update_cmd = get_package_manager_info(family)
    
    return DistroInfo(
        id=distro_id,
        name=distro_name,
        version=distro_version,
        family=family,
        package_manager=pkg_mgr,
        install_cmd=install_cmd,
        search_cmd=search_cmd,
        update_cmd=update_cmd
    )


# Cached instance
_distro_info: Optional[DistroInfo] = None


def get_distro() -> DistroInfo:
    """Get cached distro info (detects once, reuses after)."""
    global _distro_info
    if _distro_info is None:
        _distro_info = detect()
    return _distro_info


# Convenience functions
def get_family() -> DistroFamily:
    """Get just the distro family."""
    return get_distro().family


def get_install_command() -> list[str]:
    """Get the package install command for this distro."""
    return get_distro().install_cmd.copy()


def get_search_command() -> list[str]:
    """Get the package search command for this distro."""
    return get_distro().search_cmd.copy()
