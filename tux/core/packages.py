"""
Tux Assistant - Package Manager

Unified package management across distributions.

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
"""

import json
import os
from dataclasses import dataclass
from typing import Callable, Optional
from pathlib import Path

from . import distro
from . import commands


@dataclass
class Package:
    """A package with optional distro-specific names."""
    name: str
    description: str = ""
    # Distro-specific package names (if different from default)
    arch_name: Optional[str] = None
    debian_name: Optional[str] = None
    fedora_name: Optional[str] = None
    opensuse_name: Optional[str] = None
    # Flatpak alternative
    flatpak_id: Optional[str] = None
    # Whether this needs AUR on Arch
    aur_only: bool = False
    
    def get_name_for_distro(self, family: distro.DistroFamily) -> Optional[str]:
        """Get the package name for a specific distro family."""
        if family == distro.DistroFamily.ARCH:
            return self.arch_name or self.name
        elif family == distro.DistroFamily.DEBIAN:
            return self.debian_name or self.name
        elif family == distro.DistroFamily.FEDORA:
            return self.fedora_name or self.name
        elif family == distro.DistroFamily.RHEL:
            return self.fedora_name or self.name  # RHEL uses same names as Fedora mostly
        elif family == distro.DistroFamily.OPENSUSE:
            return self.opensuse_name or self.name
        else:
            return self.name


@dataclass
class InstallResult:
    """Result of a package installation."""
    success: bool
    packages_installed: list[str]
    packages_failed: list[str]
    output: str
    error: str


class PackageManager:
    """Unified package manager interface."""
    
    def __init__(self):
        self.distro_info = distro.get_distro()
        self.family = self.distro_info.family
        self._aur_helper = None
    
    @property
    def aur_helper(self) -> Optional[str]:
        """Get the AUR helper (Arch only)."""
        if self._aur_helper is None and self.family == distro.DistroFamily.ARCH:
            self._aur_helper = distro.detect_aur_helper()
        return self._aur_helper
    
    def is_installed(self, package: str) -> bool:
        """Check if a package is installed."""
        if self.family == distro.DistroFamily.ARCH:
            result = commands.run(['pacman', '-Q', package], capture_output=True)
            return result.success
        
        elif self.family == distro.DistroFamily.DEBIAN:
            result = commands.run(['dpkg', '-s', package], capture_output=True)
            return result.success
        
        elif self.family in (distro.DistroFamily.FEDORA, distro.DistroFamily.RHEL):
            result = commands.run(['rpm', '-q', package], capture_output=True)
            return result.success
        
        elif self.family == distro.DistroFamily.OPENSUSE:
            result = commands.run(['rpm', '-q', package], capture_output=True)
            return result.success
        
        return False
    
    def search(self, query: str) -> list[tuple[str, str]]:
        """
        Search for packages matching a query.
        
        Returns:
            List of (package_name, description) tuples
        """
        results = []
        
        if self.family == distro.DistroFamily.ARCH:
            result = commands.run(['pacman', '-Ss', query], capture_output=True)
            if result.success:
                lines = result.stdout.strip().split('\n')
                i = 0
                while i < len(lines):
                    if '/' in lines[i]:
                        parts = lines[i].split('/')
                        if len(parts) >= 2:
                            name_version = parts[1].split()[0]
                            desc = lines[i + 1].strip() if i + 1 < len(lines) else ''
                            results.append((name_version, desc))
                    i += 2
        
        elif self.family == distro.DistroFamily.DEBIAN:
            result = commands.run(['apt-cache', 'search', query], capture_output=True)
            if result.success:
                for line in result.stdout.strip().split('\n'):
                    if ' - ' in line:
                        name, desc = line.split(' - ', 1)
                        results.append((name.strip(), desc.strip()))
        
        elif self.family in (distro.DistroFamily.FEDORA, distro.DistroFamily.RHEL):
            result = commands.run(['dnf', 'search', query], capture_output=True)
            if result.success:
                for line in result.stdout.strip().split('\n'):
                    if ' : ' in line:
                        name, desc = line.split(' : ', 1)
                        results.append((name.strip(), desc.strip()))
        
        elif self.family == distro.DistroFamily.OPENSUSE:
            result = commands.run(['zypper', 'search', query], capture_output=True)
            if result.success:
                for line in result.stdout.strip().split('\n'):
                    if '|' in line:
                        parts = line.split('|')
                        if len(parts) >= 3:
                            name = parts[1].strip()
                            desc = parts[2].strip() if len(parts) > 2 else ''
                            if name and not name.startswith('-'):
                                results.append((name, desc))
        
        return results
    
    def install(
        self,
        packages: list[str],
        on_output: Optional[Callable[[str], None]] = None
    ) -> InstallResult:
        """
        Install one or more packages.
        
        Args:
            packages: List of package names to install
            on_output: Optional callback for real-time output
        
        Returns:
            InstallResult with success status and details
        """
        if not packages:
            return InstallResult(
                success=True,
                packages_installed=[],
                packages_failed=[],
                output='',
                error=''
            )
        
        # Build install command
        cmd = self.distro_info.install_cmd.copy()
        cmd.extend(packages)
        
        # Run installation
        if on_output:
            # Use callback-based execution for real-time output
            result_holder = [None]
            
            def on_complete(result):
                result_holder[0] = result
            
            thread = commands.run_with_callback(
                cmd,
                on_stdout=on_output,
                on_stderr=on_output,
                on_complete=on_complete
            )
            thread.join()  # Wait for completion
            result = result_holder[0]
        else:
            result = commands.run(cmd, timeout=600)  # 10 minute timeout
        
        if result is None:
            return InstallResult(
                success=False,
                packages_installed=[],
                packages_failed=packages,
                output='',
                error='Installation failed - no result'
            )
        
        # Determine which packages succeeded/failed
        installed = []
        failed = []
        
        for pkg in packages:
            if self.is_installed(pkg):
                installed.append(pkg)
            else:
                failed.append(pkg)
        
        return InstallResult(
            success=result.success and len(failed) == 0,
            packages_installed=installed,
            packages_failed=failed,
            output=result.stdout,
            error=result.stderr
        )
    
    def install_aur(
        self,
        packages: list[str],
        on_output: Optional[Callable[[str], None]] = None
    ) -> InstallResult:
        """
        Install packages from AUR (Arch only).
        
        Args:
            packages: List of AUR package names
            on_output: Optional callback for real-time output
        
        Returns:
            InstallResult
        """
        if self.family != distro.DistroFamily.ARCH:
            return InstallResult(
                success=False,
                packages_installed=[],
                packages_failed=packages,
                output='',
                error='AUR is only available on Arch-based systems'
            )
        
        if not self.aur_helper:
            return InstallResult(
                success=False,
                packages_installed=[],
                packages_failed=packages,
                output='',
                error='No AUR helper found. Install yay or paru first.'
            )
        
        # Build AUR helper command
        cmd = [self.aur_helper, '-S', '--needed', '--noconfirm'] + packages
        
        if on_output:
            result_holder = [None]
            
            def on_complete(result):
                result_holder[0] = result
            
            thread = commands.run_with_callback(
                cmd,
                on_stdout=on_output,
                on_stderr=on_output,
                on_complete=on_complete
            )
            thread.join()
            result = result_holder[0]
        else:
            result = commands.run(cmd, timeout=1200)  # 20 minute timeout for AUR
        
        if result is None:
            return InstallResult(
                success=False,
                packages_installed=[],
                packages_failed=packages,
                output='',
                error='AUR installation failed - no result'
            )
        
        # Check results
        installed = []
        failed = []
        
        for pkg in packages:
            if self.is_installed(pkg):
                installed.append(pkg)
            else:
                failed.append(pkg)
        
        return InstallResult(
            success=result.success and len(failed) == 0,
            packages_installed=installed,
            packages_failed=failed,
            output=result.stdout,
            error=result.stderr
        )
    
    def update(self, on_output: Optional[Callable[[str], None]] = None) -> commands.CommandResult:
        """Update package database."""
        if self.family == distro.DistroFamily.ARCH:
            cmd = ['sudo', 'pacman', '-Sy']
        elif self.family == distro.DistroFamily.DEBIAN:
            cmd = ['sudo', 'apt', 'update']
        elif self.family in (distro.DistroFamily.FEDORA, distro.DistroFamily.RHEL):
            cmd = ['sudo', 'dnf', 'check-update']
        elif self.family == distro.DistroFamily.OPENSUSE:
            cmd = ['sudo', 'zypper', 'refresh']
        else:
            return commands.CommandResult(
                status=commands.CommandStatus.FAILED,
                return_code=-1,
                stdout='',
                stderr='Unknown distribution family',
                command=[]
            )
        
        if on_output:
            result_holder = [None]
            
            def on_complete(result):
                result_holder[0] = result
            
            thread = commands.run_with_callback(
                cmd,
                on_stdout=on_output,
                on_stderr=on_output,
                on_complete=on_complete
            )
            thread.join()
            return result_holder[0]
        else:
            return commands.run(cmd, timeout=300)
    
    def upgrade(self, on_output: Optional[Callable[[str], None]] = None) -> commands.CommandResult:
        """Upgrade all packages."""
        if self.family == distro.DistroFamily.ARCH:
            cmd = ['sudo', 'pacman', '-Syu', '--noconfirm']
        elif self.family == distro.DistroFamily.DEBIAN:
            cmd = ['sudo', 'apt', 'upgrade', '-y']
        elif self.family in (distro.DistroFamily.FEDORA, distro.DistroFamily.RHEL):
            cmd = ['sudo', 'dnf', 'upgrade', '-y']
        elif self.family == distro.DistroFamily.OPENSUSE:
            cmd = ['sudo', 'zypper', 'update', '-y']
        else:
            return commands.CommandResult(
                status=commands.CommandStatus.FAILED,
                return_code=-1,
                stdout='',
                stderr='Unknown distribution family',
                command=[]
            )
        
        if on_output:
            result_holder = [None]
            
            def on_complete(result):
                result_holder[0] = result
            
            thread = commands.run_with_callback(
                cmd,
                on_stdout=on_output,
                on_stderr=on_output,
                on_complete=on_complete
            )
            thread.join()
            return result_holder[0]
        else:
            return commands.run(cmd, timeout=1800)  # 30 minutes


# Singleton instance
_package_manager: Optional[PackageManager] = None


def get_package_manager() -> PackageManager:
    """Get the package manager instance."""
    global _package_manager
    if _package_manager is None:
        _package_manager = PackageManager()
    return _package_manager
