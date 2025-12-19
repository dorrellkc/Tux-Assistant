"""
Hardware Detection Module

Provides basic hardware information from /proc and system commands.
Falls back gracefully when detailed tools like hardinfo2 aren't available.

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
"""

import os
import subprocess
import shutil
from dataclasses import dataclass
from typing import Optional


@dataclass
class HardwareInfo:
    """Basic hardware information."""
    cpu_model: str
    cpu_cores: int
    cpu_threads: int
    ram_total_gb: float
    gpu_model: str
    disk_info: str
    hardinfo2_available: bool


def get_cpu_info() -> tuple[str, int, int]:
    """Get CPU model, cores, and threads from /proc/cpuinfo and lscpu."""
    model = "Unknown CPU"
    cores = 0
    threads = 0
    
    try:
        # Get model from /proc/cpuinfo
        with open('/proc/cpuinfo', 'r') as f:
            for line in f:
                if line.startswith('model name'):
                    model = line.split(':')[1].strip()
                    break
        
        # Get cores/threads from lscpu (more reliable)
        result = subprocess.run(
            ['lscpu'], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if line.startswith('CPU(s):'):
                    threads = int(line.split(':')[1].strip())
                elif line.startswith('Core(s) per socket:'):
                    cores_per_socket = int(line.split(':')[1].strip())
                elif line.startswith('Socket(s):'):
                    sockets = int(line.split(':')[1].strip())
            
            if 'cores_per_socket' in dir() and 'sockets' in dir():
                cores = cores_per_socket * sockets
            else:
                cores = threads  # Fallback
                
    except Exception:
        pass
    
    return model, cores, threads


def get_ram_info() -> float:
    """Get total RAM in GB from /proc/meminfo."""
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if line.startswith('MemTotal:'):
                    # Value is in kB
                    kb = int(line.split()[1])
                    return round(kb / 1024 / 1024, 1)
    except Exception:
        pass
    return 0.0


def get_gpu_info() -> str:
    """Get GPU model from lspci."""
    try:
        result = subprocess.run(
            ['lspci'], 
            capture_output=True, 
            text=True, 
            timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'VGA' in line or '3D controller' in line:
                    # Extract the model part after the colon
                    parts = line.split(': ')
                    if len(parts) >= 2:
                        return parts[1].strip()
    except Exception:
        pass
    return "Unknown GPU"


def get_disk_info() -> str:
    """Get basic disk info."""
    try:
        result = subprocess.run(
            ['lsblk', '-d', '-o', 'NAME,SIZE,TYPE', '--noheadings'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            disks = []
            for line in result.stdout.strip().split('\n'):
                parts = line.split()
                if len(parts) >= 2 and parts[-1] == 'disk':
                    disks.append(f"{parts[0]}: {parts[1]}")
            if disks:
                return ", ".join(disks[:3])  # Limit to 3 disks
    except Exception:
        pass
    return "Unknown"


def check_hardinfo2_available() -> bool:
    """Check if hardinfo2 is installed."""
    return shutil.which('hardinfo2') is not None


def get_hardware_info() -> HardwareInfo:
    """Get all hardware information."""
    cpu_model, cpu_cores, cpu_threads = get_cpu_info()
    
    return HardwareInfo(
        cpu_model=cpu_model,
        cpu_cores=cpu_cores,
        cpu_threads=cpu_threads,
        ram_total_gb=get_ram_info(),
        gpu_model=get_gpu_info(),
        disk_info=get_disk_info(),
        hardinfo2_available=check_hardinfo2_available()
    )


def get_hardinfo2_package_name(distro_family: str) -> str:
    """Get the package name for hardinfo2 based on distro family."""
    # All distros use 'hardinfo2' as the package name
    return 'hardinfo2'


def is_aur_package(distro_family: str) -> bool:
    """Check if hardinfo2 needs AUR on this distro."""
    return distro_family.lower() in ('arch',)


def launch_hardinfo2() -> bool:
    """Launch hardinfo2 GUI."""
    try:
        subprocess.Popen(['hardinfo2'], start_new_session=True)
        return True
    except Exception:
        return False
