"""
Tux Assistant - Printer Wizard Module

Smart printer detection, driver installation, and setup wizard.
Handles USB and network printers across all major Linux distributions.

The goal: Make printing on Linux as easy as it should be.

Copyright (c) 2025 Christopher Dorrell. Licensed under GPL-3.0.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

import os
import re
import subprocess
import threading
from gi.repository import Gtk, Adw, GLib, Gio
from typing import Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum

from ..core import get_distro, DistroFamily

from .registry import register_module, ModuleCategory


# =============================================================================
# Data Classes
# =============================================================================

class PrinterConnectionType(Enum):
    """How the printer is connected."""
    USB = "usb"
    NETWORK = "network"
    UNKNOWN = "unknown"


class PrinterBrand(Enum):
    """Known printer brands with special handling."""
    HP = "hp"
    BROTHER = "brother"
    CANON = "canon"
    EPSON = "epson"
    SAMSUNG = "samsung"
    LEXMARK = "lexmark"
    XEROX = "xerox"
    RICOH = "ricoh"
    KYOCERA = "kyocera"
    GENERIC = "generic"


@dataclass
class DiscoveredPrinter:
    """Information about a discovered printer."""
    uri: str                          # CUPS URI (e.g., usb://HP/LaserJet)
    name: str                         # Human-readable name
    make: str                         # Manufacturer
    model: str                        # Model name
    connection_type: PrinterConnectionType
    brand: PrinterBrand
    is_configured: bool               # Already set up in CUPS?
    device_id: str                    # IEEE 1284 device ID if available
    location: str                     # Network location or USB port
    
    @property
    def display_name(self) -> str:
        """Get a clean display name."""
        if self.make and self.model:
            return f"{self.make} {self.model}"
        elif self.name:
            return self.name
        return self.uri


# =============================================================================
# Detection Utilities
# =============================================================================

def check_cups_installed() -> bool:
    """Check if CUPS is installed."""
    try:
        # Method 1: Check for lpinfo in PATH
        result = subprocess.run(['which', 'lpinfo'], capture_output=True)
        if result.returncode == 0:
            return True
        
        # Method 2: Check common locations for CUPS binaries
        cups_paths = [
            '/usr/sbin/cupsd',
            '/usr/bin/lpstat',
            '/usr/sbin/lpinfo',
            '/usr/bin/lp',
        ]
        for path in cups_paths:
            if os.path.exists(path):
                return True
        
        # Method 3: Check if cups service unit exists
        result = subprocess.run(
            ['systemctl', 'list-unit-files', 'cups.service'],
            capture_output=True, text=True
        )
        if 'cups.service' in result.stdout:
            return True
        
        return False
    except Exception:
        return False


def check_cups_running() -> bool:
    """Check if CUPS service is running."""
    try:
        result = subprocess.run(
            ['systemctl', 'is-active', 'cups'],
            capture_output=True, text=True
        )
        return result.stdout.strip() == "active"
    except Exception:
        return False


def find_lpinfo() -> Optional[str]:
    """Find the lpinfo command path.
    
    On some distros (openSUSE, etc.) /usr/sbin is not in PATH,
    so we need to check common locations explicitly.
    
    Returns: Full path to lpinfo, or None if not found.
    """
    # Method 1: Check if in PATH
    result = subprocess.run(['which', 'lpinfo'], capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    
    # Method 2: Check common locations
    lpinfo_paths = [
        '/usr/sbin/lpinfo',
        '/usr/bin/lpinfo',
        '/sbin/lpinfo',
    ]
    for path in lpinfo_paths:
        if os.path.exists(path):
            return path
    
    return None


def get_cups_status() -> Tuple[bool, bool, str]:
    """
    Get CUPS status.
    Returns: (installed, running, message)
    """
    installed = check_cups_installed()
    if not installed:
        return False, False, "CUPS not installed"
    
    running = check_cups_running()
    if not running:
        return True, False, "CUPS service not running"
    
    return True, True, "CUPS ready"


def detect_brand(make: str, model: str, uri: str) -> PrinterBrand:
    """Detect printer brand from available information."""
    text = f"{make} {model} {uri}".lower()
    
    if "hp" in text or "hewlett" in text:
        return PrinterBrand.HP
    elif "brother" in text:
        return PrinterBrand.BROTHER
    elif "canon" in text:
        return PrinterBrand.CANON
    elif "epson" in text:
        return PrinterBrand.EPSON
    elif "samsung" in text:
        return PrinterBrand.SAMSUNG
    elif "lexmark" in text:
        return PrinterBrand.LEXMARK
    elif "xerox" in text:
        return PrinterBrand.XEROX
    elif "ricoh" in text:
        return PrinterBrand.RICOH
    elif "kyocera" in text:
        return PrinterBrand.KYOCERA
    
    return PrinterBrand.GENERIC


def parse_device_id(device_id: str) -> Tuple[str, str]:
    """Parse IEEE 1284 device ID string for make/model."""
    make = ""
    model = ""
    
    # Device ID format: KEY:VALUE;KEY:VALUE;...
    for part in device_id.split(';'):
        if ':' in part:
            key, value = part.split(':', 1)
            key = key.strip().upper()
            value = value.strip()
            
            if key in ('MFG', 'MANUFACTURER'):
                make = value
            elif key in ('MDL', 'MODEL'):
                model = value
    
    return make, model


def discover_usb_printers() -> List[DiscoveredPrinter]:
    """Discover USB-connected printers."""
    printers = []
    
    # Find lpinfo command (may be in /usr/sbin on some distros)
    lpinfo_cmd = find_lpinfo()
    if not lpinfo_cmd:
        return printers
    
    try:
        # Use lpinfo to find USB devices
        result = subprocess.run(
            [lpinfo_cmd, '-v'],
            capture_output=True, text=True
        )
        
        if result.returncode != 0:
            return printers
        
        for line in result.stdout.strip().split('\n'):
            if not line:
                continue
            
            # Format: "direct usb://HP/LaserJet%201018?serial=..."
            parts = line.split(None, 1)
            if len(parts) < 2:
                continue
            
            backend_type, uri = parts
            
            # Only USB devices
            if not uri.startswith('usb://'):
                continue
            
            # Parse USB URI: usb://MAKE/MODEL?serial=XXX
            uri_clean = uri.replace('usb://', '')
            make = ""
            model = ""
            
            if '/' in uri_clean:
                make = uri_clean.split('/')[0]
                model_part = uri_clean.split('/')[1]
                # Remove query string
                model = model_part.split('?')[0]
                # URL decode
                model = model.replace('%20', ' ')
            
            # Try to get more info from device ID
            device_id = ""
            try:
                id_result = subprocess.run(
                    [lpinfo_cmd, '--device-id', uri],
                    capture_output=True, text=True,
                    timeout=5
                )
                if id_result.returncode == 0:
                    device_id = id_result.stdout.strip()
                    if device_id:
                        parsed_make, parsed_model = parse_device_id(device_id)
                        if parsed_make:
                            make = parsed_make
                        if parsed_model:
                            model = parsed_model
            except Exception:
                pass
            
            brand = detect_brand(make, model, uri)
            
            printers.append(DiscoveredPrinter(
                uri=uri,
                name=f"{make} {model}".strip() or "USB Printer",
                make=make,
                model=model,
                connection_type=PrinterConnectionType.USB,
                brand=brand,
                is_configured=False,  # Will check later
                device_id=device_id,
                location="USB"
            ))
    
    except Exception as e:
        print(f"Error discovering USB printers: {e}")
    
    return printers


def discover_network_printers() -> List[DiscoveredPrinter]:
    """Discover network printers via various methods."""
    printers = []
    seen_uris = set()
    
    # Find lpinfo command (may be in /usr/sbin on some distros)
    lpinfo_cmd = find_lpinfo()
    
    # Method 1: CUPS lpinfo network discovery (increased timeout)
    if lpinfo_cmd:
        try:
            result = subprocess.run(
                [lpinfo_cmd, '-v'],
                capture_output=True, text=True,
                timeout=30  # Increased from 10 to 30 seconds
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if not line:
                        continue
                    
                    parts = line.split(None, 1)
                    if len(parts) < 2:
                        continue
                    
                    backend_type, uri = parts
                    
                    # Network protocols
                    if any(uri.startswith(proto) for proto in ['socket://', 'ipp://', 'ipps://', 'lpd://', 'dnssd://']):
                        if uri in seen_uris:
                            continue
                        seen_uris.add(uri)
                        
                        # Parse network URI for make/model
                        make = ""
                        model = ""
                        location = ""
                        
                        # Extract hostname/IP
                        if '://' in uri:
                            location = uri.split('://')[1].split('/')[0].split(':')[0]
                        
                        # dnssd URIs often have make/model encoded
                        if uri.startswith('dnssd://'):
                            # dnssd://MAKE%20MODEL._ipp._tcp.local/...
                            name_part = uri.replace('dnssd://', '').split('.')[0]
                            name_part = name_part.replace('%20', ' ')
                            parts = name_part.split(' ', 1)
                            if len(parts) >= 1:
                                make = parts[0]
                            if len(parts) >= 2:
                                model = parts[1]
                        
                        brand = detect_brand(make, model, uri)
                        
                        printers.append(DiscoveredPrinter(
                            uri=uri,
                            name=f"{make} {model}".strip() or f"Network Printer ({location})",
                            make=make,
                            model=model,
                            connection_type=PrinterConnectionType.NETWORK,
                            brand=brand,
                            is_configured=False,
                            device_id="",
                            location=location
                        ))
        
        except subprocess.TimeoutExpired:
            print("Network printer discovery timed out")
        except Exception as e:
            print(f"Error with lpinfo network discovery: {e}")
    
    # Method 2: Avahi/mDNS discovery (if available)
    try:
        result = subprocess.run(['which', 'avahi-browse'], capture_output=True)
        if result.returncode == 0:
            # Quick browse for IPP printers (increased timeout)
            result = subprocess.run(
                ['avahi-browse', '-t', '-r', '-p', '_ipp._tcp'],
                capture_output=True, text=True,
                timeout=15  # Increased from 5 to 15 seconds
            )
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if not line or not line.startswith('='):
                        continue
                    
                    # Parse avahi-browse parseable output
                    # =;interface;protocol;name;type;domain;hostname;address;port;txt
                    parts = line.split(';')
                    if len(parts) >= 8:
                        name = parts[3]
                        hostname = parts[6]
                        address = parts[7]
                        port = parts[8] if len(parts) > 8 else "631"
                        
                        uri = f"ipp://{address}:{port}/ipp/print"
                        
                        if uri not in seen_uris:
                            seen_uris.add(uri)
                            
                            # Try to parse make/model from name
                            make = ""
                            model = ""
                            name_parts = name.split(' ', 1)
                            if len(name_parts) >= 1:
                                make = name_parts[0]
                            if len(name_parts) >= 2:
                                model = name_parts[1]
                            
                            brand = detect_brand(make, model, uri)
                            
                            printers.append(DiscoveredPrinter(
                                uri=uri,
                                name=name or f"Network Printer ({address})",
                                make=make,
                                model=model,
                                connection_type=PrinterConnectionType.NETWORK,
                                brand=brand,
                                is_configured=False,
                                device_id="",
                                location=address
                            ))
    
    except subprocess.TimeoutExpired:
        print("Avahi discovery timed out")
    except Exception as e:
        print(f"Error with Avahi discovery: {e}")
    
    # Method 3: SNMP discovery for older printers (if snmpwalk available)
    try:
        result = subprocess.run(['which', 'snmpwalk'], capture_output=True)
        if result.returncode == 0:
            # Get local network range
            local_ips = _get_local_network_ranges()
            
            for network in local_ips[:2]:  # Limit to first 2 networks to avoid long scans
                try:
                    # Use nmap for SNMP printer discovery if available
                    nmap_result = subprocess.run(['which', 'nmap'], capture_output=True)
                    if nmap_result.returncode == 0:
                        # Quick scan for port 9100 (raw printing) and 631 (IPP)
                        scan_result = subprocess.run(
                            ['nmap', '-p', '9100,631', '--open', '-oG', '-', network],
                            capture_output=True, text=True,
                            timeout=30
                        )
                        
                        if scan_result.returncode == 0:
                            for line in scan_result.stdout.split('\n'):
                                if 'open' in line and 'Host:' in line:
                                    # Extract IP: "Host: 192.168.1.50 ()"
                                    parts = line.split()
                                    for i, part in enumerate(parts):
                                        if part == 'Host:' and i + 1 < len(parts):
                                            ip = parts[i + 1]
                                            if ip and ip not in seen_uris:
                                                # Determine which port is open
                                                if '9100/open' in line:
                                                    uri = f"socket://{ip}:9100"
                                                else:
                                                    uri = f"ipp://{ip}:631/ipp/print"
                                                
                                                if uri not in seen_uris:
                                                    seen_uris.add(uri)
                                                    printers.append(DiscoveredPrinter(
                                                        uri=uri,
                                                        name=f"Network Printer ({ip})",
                                                        make="",
                                                        model="",
                                                        connection_type=PrinterConnectionType.NETWORK,
                                                        brand=PrinterBrand.GENERIC,
                                                        is_configured=False,
                                                        device_id="",
                                                        location=ip
                                                    ))
                except subprocess.TimeoutExpired:
                    print(f"Network scan timed out for {network}")
                except Exception as e:
                    print(f"Error scanning network {network}: {e}")
    except Exception as e:
        print(f"Error with SNMP/nmap discovery: {e}")
    
    return printers


def _get_local_network_ranges() -> List[str]:
    """Get local network CIDR ranges for scanning."""
    networks = []
    
    try:
        # Use ip command to get network info
        result = subprocess.run(
            ['ip', '-4', 'addr', 'show'],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            for line in result.stdout.split('\n'):
                if 'inet ' in line and '127.0.0.1' not in line:
                    # Extract CIDR: "inet 192.168.1.100/24 brd..."
                    parts = line.strip().split()
                    for i, part in enumerate(parts):
                        if part == 'inet' and i + 1 < len(parts):
                            cidr = parts[i + 1]
                            # Convert to network range (e.g., 192.168.1.0/24)
                            if '/' in cidr:
                                ip, mask = cidr.split('/')
                                ip_parts = ip.split('.')
                                if len(ip_parts) == 4:
                                    # Simple /24 assumption for scanning
                                    network = f"{ip_parts[0]}.{ip_parts[1]}.{ip_parts[2]}.0/24"
                                    if network not in networks:
                                        networks.append(network)
    except Exception as e:
        print(f"Error getting network ranges: {e}")
    
    return networks


def probe_printer_at_ip(ip_address: str) -> Optional[DiscoveredPrinter]:
    """Probe a specific IP address for a printer.
    
    Tries common printer ports and protocols to detect a printer.
    Returns a DiscoveredPrinter if found, None otherwise.
    """
    import socket
    
    # Ports to check: 9100 (raw/JetDirect), 631 (IPP), 515 (LPD)
    ports_to_check = [
        (9100, 'socket', 'Raw/JetDirect'),
        (631, 'ipp', 'IPP'),
        (515, 'lpd', 'LPD'),
    ]
    
    for port, protocol, desc in ports_to_check:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)  # 3 second timeout per port
            result = sock.connect_ex((ip_address, port))
            sock.close()
            
            if result == 0:  # Port is open
                # Build URI based on protocol
                if protocol == 'socket':
                    uri = f"socket://{ip_address}:{port}"
                elif protocol == 'ipp':
                    uri = f"ipp://{ip_address}:{port}/ipp/print"
                elif protocol == 'lpd':
                    uri = f"lpd://{ip_address}/lp"
                else:
                    continue
                
                # Try to get more info via SNMP if available
                make, model = _snmp_get_printer_info(ip_address)
                brand = detect_brand(make, model, uri)
                
                return DiscoveredPrinter(
                    uri=uri,
                    name=f"{make} {model}".strip() or f"Printer at {ip_address}",
                    make=make,
                    model=model,
                    connection_type=PrinterConnectionType.NETWORK,
                    brand=brand,
                    is_configured=False,
                    device_id="",
                    location=ip_address
                )
        except Exception:
            continue
    
    return None


def _snmp_get_printer_info(ip_address: str) -> Tuple[str, str]:
    """Try to get printer make/model via SNMP.
    
    Returns (make, model) tuple, empty strings if not available.
    """
    make = ""
    model = ""
    
    try:
        # Check if snmpget is available
        result = subprocess.run(['which', 'snmpget'], capture_output=True)
        if result.returncode != 0:
            return make, model
        
        # Standard Printer MIB OIDs
        # hrDeviceDescr.1 - Device description
        oid = "1.3.6.1.2.1.25.3.2.1.3.1"
        
        result = subprocess.run(
            ['snmpget', '-v1', '-c', 'public', '-t', '2', ip_address, oid],
            capture_output=True, text=True,
            timeout=5
        )
        
        if result.returncode == 0 and 'STRING:' in result.stdout:
            # Parse: "SNMPv2-SMI::...hrDeviceDescr.1 = STRING: HP LaserJet Pro MFP"
            desc = result.stdout.split('STRING:')[-1].strip().strip('"')
            
            # Try to extract make and model
            desc_lower = desc.lower()
            if 'hp' in desc_lower or 'hewlett' in desc_lower:
                make = "HP"
                model = desc.replace('HP', '').replace('Hewlett-Packard', '').strip()
            elif 'brother' in desc_lower:
                make = "Brother"
                model = desc.replace('Brother', '').strip()
            elif 'canon' in desc_lower:
                make = "Canon"
                model = desc.replace('Canon', '').strip()
            elif 'epson' in desc_lower:
                make = "Epson"
                model = desc.replace('Epson', '').replace('EPSON', '').strip()
            else:
                # Use full description as model
                model = desc
    except Exception:
        pass
    
    return make, model


def get_configured_printers() -> List[str]:
    """Get list of already-configured printer URIs."""
    configured = []
    
    try:
        result = subprocess.run(
            ['lpstat', '-v'],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                # Format: "device for PRINTER_NAME: URI"
                if ': ' in line:
                    uri = line.split(': ', 1)[1].strip()
                    configured.append(uri)
    
    except Exception:
        pass
    
    return configured


def discover_all_printers() -> List[DiscoveredPrinter]:
    """Discover all printers (USB and network)."""
    usb_printers = discover_usb_printers()
    network_printers = discover_network_printers()
    
    all_printers = usb_printers + network_printers
    
    # Mark configured printers
    configured_uris = get_configured_printers()
    for printer in all_printers:
        printer.is_configured = printer.uri in configured_uris
    
    return all_printers


# =============================================================================
# Package Conversion Utilities
# =============================================================================

def extract_package_name(filepath: str) -> str:
    """Extract the base package name from a .deb or .rpm file.
    
    Brother naming examples:
        brother-mfc-l2710dw-lpr-1.0.0-1.i386.deb → brother-mfc-l2710dw-lpr
        brlaser-6-2.fc40.x86_64.rpm → brlaser
    
    Returns the package name portion without version/arch.
    """
    filename = os.path.basename(filepath)
    
    # Remove extension
    if filename.endswith('.deb'):
        name = filename[:-4]
    elif filename.endswith('.rpm'):
        name = filename[:-4]
    else:
        return filename
    
    # For .deb files: name_version_arch or name-version-release.arch
    # For Brother: brother-model-component-version-release.arch
    
    # Try to find version pattern (numbers with dots/dashes)
    # Pattern: split on common version indicators
    import re
    
    # Match version patterns like: -1.0.0, _1.0.0, -6-2, etc.
    # We want everything BEFORE the version
    version_patterns = [
        r'[-_](\d+\.)+\d+[-_]',     # -1.0.0- or _1.0.0_
        r'[-_](\d+\.)+\d+$',         # ends with -1.0.0 (after removing arch)
        r'[-_]\d+[-_]\d+[-_]',       # -6-2- (Fedora style)
        r'[-_]\d+[-_]\d+\.',         # -6-2. (before arch)
    ]
    
    # First, try to remove arch suffix
    arch_patterns = [r'\.x86_64', r'\.i386', r'\.i686', r'\.amd64', r'\.arm64', r'\.aarch64', r'\.noarch']
    for arch in arch_patterns:
        name = re.sub(arch + r'$', '', name, flags=re.IGNORECASE)
    
    # Now find where version starts
    for pattern in version_patterns:
        match = re.search(pattern, name)
        if match:
            return name[:match.start()]
    
    # Fallback: try splitting on underscore (Debian convention)
    if '_' in name:
        return name.split('_')[0]
    
    # Last resort: return as-is but truncated at first digit sequence
    match = re.search(r'[-_]\d', name)
    if match:
        return name[:match.start()]
    
    return name


def get_conversion_script_debtap(deb_path: str, work_dir: str) -> str:
    """Generate a robust debtap conversion script.
    
    Uses isolated directory and tracks actual output files.
    """
    filename = os.path.basename(deb_path)
    pkg_name = extract_package_name(deb_path)
    
    return f'''
# ─── Converting: {filename} ───
CONVERT_DIR="{work_dir}"
mkdir -p "$CONVERT_DIR"
cd "$CONVERT_DIR"

# Record existing pkg files before conversion
ls *.pkg.tar* 2>/dev/null | sort > /tmp/before_convert_$$.txt || touch /tmp/before_convert_$$.txt

echo "Converting {filename} with debtap..."
debtap -q "{deb_path}"
DEBTAP_EXIT=$?

if [ $DEBTAP_EXIT -ne 0 ]; then
    echo "⚠ debtap conversion failed (exit code: $DEBTAP_EXIT)"
    echo "  You may need to run 'sudo debtap -u' first"
else
    # Find NEW pkg files (created by this conversion)
    ls *.pkg.tar* 2>/dev/null | sort > /tmp/after_convert_$$.txt || touch /tmp/after_convert_$$.txt
    NEW_PKGS=$(comm -13 /tmp/before_convert_$$.txt /tmp/after_convert_$$.txt)
    
    if [ -z "$NEW_PKGS" ]; then
        # Fallback: look for package matching our name
        NEW_PKGS=$(ls -t {pkg_name}*.pkg.tar* 2>/dev/null | head -1)
    fi
    
    if [ -n "$NEW_PKGS" ]; then
        for pkg in $NEW_PKGS; do
            echo "Installing: $pkg"
            sudo pacman -U --noconfirm "$pkg"
        done
    else
        echo "⚠ No converted package found for {filename}"
        echo "  The .deb may have converted but with an unexpected name."
        echo "  Check {work_dir} for .pkg.tar.* files"
    fi
fi

rm -f /tmp/before_convert_$$.txt /tmp/after_convert_$$.txt
'''


def get_conversion_script_alien_to_rpm(deb_path: str, work_dir: str) -> str:
    """Generate a robust alien .deb→.rpm conversion script."""
    filename = os.path.basename(deb_path)
    pkg_name = extract_package_name(deb_path)
    
    return f'''
# ─── Converting: {filename} ───
CONVERT_DIR="{work_dir}"
mkdir -p "$CONVERT_DIR"
cd "$CONVERT_DIR"

# Record existing rpm files before conversion
ls *.rpm 2>/dev/null | sort > /tmp/before_convert_$$.txt || touch /tmp/before_convert_$$.txt

echo "Converting {filename} with alien..."
sudo alien -r --scripts "{deb_path}"
ALIEN_EXIT=$?

if [ $ALIEN_EXIT -ne 0 ]; then
    echo "⚠ alien conversion failed (exit code: $ALIEN_EXIT)"
else
    # Find NEW rpm files
    ls *.rpm 2>/dev/null | sort > /tmp/after_convert_$$.txt || touch /tmp/after_convert_$$.txt
    NEW_RPMS=$(comm -13 /tmp/before_convert_$$.txt /tmp/after_convert_$$.txt)
    
    if [ -z "$NEW_RPMS" ]; then
        # Fallback: look for package matching our name
        NEW_RPMS=$(ls -t {pkg_name}*.rpm 2>/dev/null | head -1)
    fi
    
    if [ -n "$NEW_RPMS" ]; then
        for rpm in $NEW_RPMS; do
            echo "Installing: $rpm"
            sudo rpm -ivh --nodeps "$rpm"
        done
    else
        echo "⚠ No converted package found for {filename}"
    fi
fi

rm -f /tmp/before_convert_$$.txt /tmp/after_convert_$$.txt
'''


def get_conversion_script_alien_to_deb(rpm_path: str, work_dir: str) -> str:
    """Generate a robust alien .rpm→.deb conversion script."""
    filename = os.path.basename(rpm_path)
    pkg_name = extract_package_name(rpm_path)
    
    return f'''
# ─── Converting: {filename} ───
CONVERT_DIR="{work_dir}"
mkdir -p "$CONVERT_DIR"
cd "$CONVERT_DIR"

# Record existing deb files before conversion
ls *.deb 2>/dev/null | sort > /tmp/before_convert_$$.txt || touch /tmp/before_convert_$$.txt

echo "Converting {filename} with alien..."
sudo alien -d --scripts "{rpm_path}"
ALIEN_EXIT=$?

if [ $ALIEN_EXIT -ne 0 ]; then
    echo "⚠ alien conversion failed (exit code: $ALIEN_EXIT)"
else
    # Find NEW deb files
    ls *.deb 2>/dev/null | sort > /tmp/after_convert_$$.txt || touch /tmp/after_convert_$$.txt
    NEW_DEBS=$(comm -13 /tmp/before_convert_$$.txt /tmp/after_convert_$$.txt)
    
    if [ -z "$NEW_DEBS" ]; then
        # Fallback: look for package matching our name
        NEW_DEBS=$(ls -t {pkg_name}*.deb 2>/dev/null | head -1)
    fi
    
    if [ -n "$NEW_DEBS" ]; then
        for deb in $NEW_DEBS; do
            echo "Installing: $deb"
            sudo dpkg -i --force-all "$deb"
        done
        sudo apt-get install -f -y 2>/dev/null || true
    else
        echo "⚠ No converted package found for {filename}"
    fi
fi

rm -f /tmp/before_convert_$$.txt /tmp/after_convert_$$.txt
'''


# =============================================================================
# Brother Printer Setup Utilities
# =============================================================================

def normalize_brother_model(model: str) -> str:
    """Normalize Brother model name for driver search.
    
    Brother's installer expects lowercase model names like 'mfc-l2710dw'.
    """
    if not model:
        return ""
    
    # Remove common prefixes/suffixes and normalize
    model = model.lower().strip()
    model = model.replace('brother ', '')
    model = model.replace(' series', '')
    model = model.replace('_', '-')
    
    # Remove spaces around dashes
    model = re.sub(r'\s*-\s*', '-', model)
    # Replace remaining spaces with nothing (some models have no dash)
    model = model.replace(' ', '')
    
    return model


def check_aur_brother_package(model: str) -> Optional[str]:
    """Check if an AUR package exists for this Brother printer.
    
    Returns package name if found, None otherwise.
    """
    normalized = normalize_brother_model(model)
    if not normalized:
        return None
    
    # Common AUR package patterns for Brother
    patterns = [
        f"brother-{normalized}",
        f"brother-{normalized}-lpr",
        f"brother-{normalized}-cups",
        f"{normalized}-lpr",
    ]
    
    # Check if yay or paru is available
    aur_helper = None
    for helper in ['yay', 'paru']:
        result = subprocess.run(['which', helper], capture_output=True)
        if result.returncode == 0:
            aur_helper = helper
            break
    
    if not aur_helper:
        return None
    
    # Search AUR for each pattern
    for pattern in patterns:
        try:
            result = subprocess.run(
                [aur_helper, '-Ss', pattern],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0 and pattern in result.stdout:
                # Verify exact package exists
                for line in result.stdout.split('\n'):
                    if line.startswith('aur/') and pattern in line:
                        # Extract package name
                        pkg_name = line.split()[0].replace('aur/', '')
                        return pkg_name
        except Exception:
            continue
    
    return None


def check_debtap_installed() -> bool:
    """Check if debtap is installed (for Arch .deb conversion)."""
    result = subprocess.run(['which', 'debtap'], capture_output=True)
    return result.returncode == 0


def check_32bit_libs_installed() -> bool:
    """Check if 32-bit libraries are installed (needed for some Brother drivers)."""
    # Check for lib32-glibc on Arch or equivalent
    result = subprocess.run(
        ['pacman', '-Q', 'lib32-glibc'],
        capture_output=True
    )
    return result.returncode == 0


def get_brother_installer_url() -> str:
    """Get the URL for Brother's Linux driver install tool."""
    return "https://download.brother.com/welcome/dlf006893/linux-brprinter-installer-2.2.4-1.gz"


class BrotherSetupDialog(Adw.Dialog):
    """Dialog for setting up Brother printers with automatic driver installation."""
    
    def __init__(self, parent: Gtk.Window, printer: 'DiscoveredPrinter', distro):
        super().__init__()
        
        self.parent_window = parent
        self.printer = printer
        self.distro = distro
        self.model_name = normalize_brother_model(printer.model)
        self.aur_package = None
        self.install_method = None  # 'installer', 'aur', 'manual'
        
        self.set_title("Brother Printer Setup")
        self.set_content_width(550)
        self.set_content_height(500)
        
        self._build_ui()
        self._check_options()
    
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
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        toolbar_view.set_content(scrolled)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        content.set_margin_top(20)
        content.set_margin_bottom(20)
        content.set_margin_start(20)
        content.set_margin_end(20)
        scrolled.set_child(content)
        
        # Printer Info
        info_group = Adw.PreferencesGroup()
        info_group.set_title("Detected Printer")
        content.append(info_group)
        
        info_row = Adw.ActionRow()
        info_row.set_title(self.printer.display_name)
        info_row.set_subtitle(f"Model: {self.model_name or 'Unknown'}")
        info_row.add_prefix(Gtk.Image.new_from_icon_name("tux-printer-symbolic"))
        info_group.add(info_row)
        
        # Model entry (if not detected)
        if not self.model_name:
            model_row = Adw.EntryRow()
            model_row.set_title("Enter Model Number")
            model_row.set_text("")
            model_row.connect("changed", self._on_model_changed)
            info_group.add(model_row)
            self.model_entry = model_row
        else:
            self.model_entry = None
        
        # Installation Options
        self.options_group = Adw.PreferencesGroup()
        self.options_group.set_title("Installation Method")
        self.options_group.set_description("Checking available options...")
        content.append(self.options_group)
        
        # Placeholder while checking
        self.checking_row = Adw.ActionRow()
        self.checking_row.set_title("Checking installation options...")
        spinner = Gtk.Spinner()
        spinner.start()
        self.checking_row.add_prefix(spinner)
        self.options_group.add(self.checking_row)
        
        # Progress section (hidden initially)
        self.progress_group = Adw.PreferencesGroup()
        self.progress_group.set_title("Installation Progress")
        self.progress_group.set_visible(False)
        content.append(self.progress_group)
        
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_margin_start(12)
        self.progress_bar.set_margin_end(12)
        self.progress_bar.set_margin_top(8)
        self.progress_bar.set_margin_bottom(8)
        
        progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        progress_box.append(self.progress_bar)
        self.progress_group.add(progress_box)
        
        # Output view
        self.output_frame = Gtk.Frame()
        self.output_frame.set_margin_top(8)
        self.output_frame.set_visible(False)
        content.append(self.output_frame)
        
        output_scroll = Gtk.ScrolledWindow()
        output_scroll.set_min_content_height(150)
        output_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.output_frame.set_child(output_scroll)
        
        self.output_view = Gtk.TextView()
        self.output_view.set_editable(False)
        self.output_view.set_monospace(True)
        self.output_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.output_view.set_left_margin(8)
        self.output_view.set_right_margin(8)
        self.output_view.set_top_margin(8)
        self.output_view.set_bottom_margin(8)
        self.output_buffer = self.output_view.get_buffer()
        output_scroll.set_child(self.output_view)
    
    def _on_model_changed(self, entry):
        """Handle model entry change."""
        self.model_name = normalize_brother_model(entry.get_text())
        # Re-check options with new model
        self._check_options()
    
    def _check_options(self):
        """Check available installation options in background."""
        def check():
            options = []
            
            # Option 1: AUR package (Arch only)
            if self.distro.family == DistroFamily.ARCH and self.model_name:
                self.aur_package = check_aur_brother_package(self.model_name)
                if self.aur_package:
                    options.append(('aur', self.aur_package))
            
            # Option 2: Brother installer (all distros, but needs conversion on Arch)
            if self.distro.family != DistroFamily.ARCH:
                # Native support via rpm/deb
                options.append(('installer', 'Brother Driver Install Tool'))
            else:
                # Arch needs debtap
                if check_debtap_installed():
                    options.append(('installer_arch', 'Brother Installer (via debtap)'))
                else:
                    options.append(('installer_arch_needs_debtap', 'Brother Installer (requires debtap)'))
            
            # Option 3: Manual always available
            options.append(('manual', 'Manual Installation'))
            
            GLib.idle_add(self._show_options, options)
        
        threading.Thread(target=check, daemon=True).start()
    
    def _show_options(self, options):
        """Show available installation options."""
        # Remove checking placeholder
        self.options_group.remove(self.checking_row)
        self.options_group.set_description("Choose how to install the driver")
        
        for opt_id, opt_name in options:
            row = Adw.ActionRow()
            
            if opt_id == 'aur':
                row.set_title("Install from AUR")
                row.set_subtitle(f"Package: {opt_name}")
                row.add_prefix(Gtk.Image.new_from_icon_name("tux-emblem-ok-symbolic"))
                
                btn = Gtk.Button(label="Install")
                btn.add_css_class("suggested-action")
                btn.set_valign(Gtk.Align.CENTER)
                btn.connect("clicked", self._on_install_aur)
                row.add_suffix(btn)
                
            elif opt_id == 'installer':
                row.set_title("Automatic Installation")
                row.set_subtitle("Download and run Brother's official installer")
                row.add_prefix(Gtk.Image.new_from_icon_name("tux-emblem-ok-symbolic"))
                
                btn = Gtk.Button(label="Install")
                btn.add_css_class("suggested-action")
                btn.set_valign(Gtk.Align.CENTER)
                btn.connect("clicked", self._on_install_auto)
                row.add_suffix(btn)
                
            elif opt_id == 'installer_arch':
                row.set_title("Automatic Installation")
                row.set_subtitle("Download Brother drivers and convert with debtap")
                row.add_prefix(Gtk.Image.new_from_icon_name("tux-emblem-ok-symbolic"))
                
                btn = Gtk.Button(label="Install")
                btn.add_css_class("suggested-action")
                btn.set_valign(Gtk.Align.CENTER)
                btn.connect("clicked", self._on_install_arch_convert)
                row.add_suffix(btn)
                
            elif opt_id == 'installer_arch_needs_debtap':
                row.set_title("Automatic Installation")
                row.set_subtitle("Requires debtap (will be installed)")
                row.add_prefix(Gtk.Image.new_from_icon_name("tux-dialog-warning-symbolic"))
                
                btn = Gtk.Button(label="Install")
                btn.set_valign(Gtk.Align.CENTER)
                btn.connect("clicked", self._on_install_arch_with_debtap)
                row.add_suffix(btn)
                
            elif opt_id == 'manual':
                row.set_title("Manual Installation")
                row.set_subtitle("Open Brother support website or drag-drop driver files")
                row.add_prefix(Gtk.Image.new_from_icon_name("tux-help-browser-symbolic"))
                
                web_btn = Gtk.Button(label="Website")
                web_btn.set_valign(Gtk.Align.CENTER)
                web_btn.connect("clicked", self._on_open_brother_website)
                row.add_suffix(web_btn)
                
                drop_btn = Gtk.Button(label="Drop Files")
                drop_btn.set_valign(Gtk.Align.CENTER)
                drop_btn.connect("clicked", self._on_manual_drop)
                row.add_suffix(drop_btn)
            
            self.options_group.add(row)
        
        # Add 32-bit library warning for Arch
        if self.distro.family == DistroFamily.ARCH and not check_32bit_libs_installed():
            warn_row = Adw.ActionRow()
            warn_row.set_title("32-bit Libraries")
            warn_row.set_subtitle("Some Brother drivers need lib32-glibc (will install if needed)")
            warn_row.add_prefix(Gtk.Image.new_from_icon_name("tux-dialog-information-symbolic"))
            self.options_group.add(warn_row)
    
    def _append_output(self, text: str):
        """Append text to output view."""
        end_iter = self.output_buffer.get_end_iter()
        self.output_buffer.insert(end_iter, text + "\n")
        # Auto-scroll
        mark = self.output_buffer.create_mark(None, self.output_buffer.get_end_iter(), False)
        self.output_view.scroll_mark_onscreen(mark)
        self.output_buffer.delete_mark(mark)
    
    def _show_progress(self):
        """Show progress UI."""
        self.progress_group.set_visible(True)
        self.output_frame.set_visible(True)
        self.options_group.set_visible(False)
    
    def _on_install_aur(self, button):
        """Install Brother driver from AUR."""
        if not self.aur_package:
            return
        
        self._show_progress()
        self.progress_bar.set_text("Installing from AUR...")
        
        # Run in terminal for AUR helper interaction
        script = f'''echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Installing Brother Printer Driver from AUR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Package: {self.aur_package}"
echo ""

# Check for AUR helper
if command -v yay &> /dev/null; then
    yay -S --noconfirm {self.aur_package}
elif command -v paru &> /dev/null; then
    paru -S --noconfirm {self.aur_package}
else
    echo "Error: No AUR helper found (yay or paru required)"
    exit 1
fi

echo ""
echo "Restarting CUPS..."
sudo systemctl restart cups

echo ""
echo "✓ Installation complete!"
echo ""
echo "Your Brother printer should now be available."
echo "You may need to add it via CUPS (http://localhost:631)"
echo ""
read -p "Press Enter to close..."
'''
        self._run_in_terminal(script)
        self._append_output(f"Installing {self.aur_package} from AUR...")
        self.progress_bar.set_fraction(1.0)
        self.progress_bar.set_text("Check terminal window")
    
    def _on_install_auto(self, button):
        """Automatic installation using Brother's installer (non-Arch)."""
        if not self.model_name:
            self._append_output("Error: Please enter a model number")
            return
        
        self._show_progress()
        self.progress_bar.set_text("Downloading Brother installer...")
        
        # Build the installation script
        if self.distro.family == DistroFamily.OPENSUSE:
            prereq = "echo 'Installing 32-bit libraries...'\nsudo zypper install -y glibc-32bit"
        elif self.distro.family == DistroFamily.FEDORA:
            prereq = "echo 'Installing 32-bit libraries...'\nsudo dnf install -y glibc.i686"
        elif self.distro.family == DistroFamily.DEBIAN:
            prereq = "echo 'Enabling 32-bit architecture...'\nsudo dpkg --add-architecture i386\nsudo apt update\nsudo apt install -y libc6:i386"
        else:
            prereq = ""
        
        script = f'''echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Brother Printer Driver Installation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Printer Model: {self.model_name}"
echo ""

# Prerequisites
{prereq}

# Download Brother installer
echo ""
echo "Downloading Brother Driver Install Tool..."
cd /tmp
wget -q --show-progress -O linux-brprinter-installer.gz "{get_brother_installer_url()}"

if [ ! -f linux-brprinter-installer.gz ]; then
    echo "Error: Download failed"
    exit 1
fi

echo "Extracting..."
gunzip -f linux-brprinter-installer.gz
chmod +x linux-brprinter-installer*

echo ""
echo "Running Brother installer..."
echo "Please follow the prompts below."
echo ""

sudo bash linux-brprinter-installer* {self.model_name}

echo ""
echo "Restarting CUPS..."
sudo systemctl restart cups

echo ""
echo "✓ Installation complete!"
echo ""
read -p "Press Enter to close..."
'''
        self._run_in_terminal(script)
        self._append_output("Running Brother installer in terminal...")
        self.progress_bar.set_fraction(1.0)
        self.progress_bar.set_text("Follow prompts in terminal")
    
    def _on_install_arch_convert(self, button):
        """Install on Arch using debtap conversion."""
        if not self.model_name:
            self._append_output("Error: Please enter a model number")
            return
        
        self._show_progress()
        self.progress_bar.set_text("Preparing Arch installation...")
        
        # Brother typically downloads files to these locations
        # We'll search comprehensively and convert each found .deb
        script = f'''echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Brother Printer Driver (Arch Linux)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Printer Model: {self.model_name}"
echo ""

# Install 32-bit libraries if needed
if ! pacman -Q lib32-glibc &> /dev/null; then
    echo "Installing 32-bit libraries..."
    sudo pacman -S --noconfirm lib32-glibc
fi

# Update debtap database if needed
if [ ! -f /var/cache/debtap/packages* ]; then
    echo ""
    echo "Updating debtap database (first run, may take a minute)..."
    sudo debtap -u
fi

# Create isolated work directory for conversions
WORK_DIR="/tmp/brother-convert-$$"
mkdir -p "$WORK_DIR"
cd "$WORK_DIR"

# Download Brother installer
echo ""
echo "Downloading Brother Driver Install Tool..."
wget -q --show-progress -O linux-brprinter-installer.gz "{get_brother_installer_url()}"

if [ ! -f linux-brprinter-installer.gz ]; then
    echo "Error: Download failed"
    exit 1
fi

gunzip -f linux-brprinter-installer.gz
chmod +x linux-brprinter-installer*

# Run Brother installer
echo ""
echo "Running Brother installer..."
echo "The installer will download driver packages."
echo ""
sudo bash linux-brprinter-installer* {self.model_name}

# Now find and convert all Brother .deb files
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Searching for downloaded packages..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Brother downloads to various locations - search comprehensively
SEARCH_PATHS="/var/spool/lpd /tmp /opt/brother /usr/local /var/tmp"
FOUND_DEBS=""

for search_dir in $SEARCH_PATHS; do
    if [ -d "$search_dir" ]; then
        DEBS=$(find "$search_dir" -name "*.deb" -type f 2>/dev/null | grep -i brother || true)
        if [ -n "$DEBS" ]; then
            FOUND_DEBS="$FOUND_DEBS $DEBS"
        fi
    fi
done

# Also check for model-specific packages
MODEL_DEBS=$(find /tmp /var -name "*{self.model_name}*.deb" -type f 2>/dev/null || true)
FOUND_DEBS="$FOUND_DEBS $MODEL_DEBS"

# Remove duplicates and empty entries
FOUND_DEBS=$(echo "$FOUND_DEBS" | tr ' ' '\\n' | sort -u | grep -v '^$')

if [ -z "$FOUND_DEBS" ]; then
    echo "⚠ No Brother .deb packages found"
    echo ""
    echo "The installer may have:"
    echo "  1. Used a different package format"
    echo "  2. Installed drivers directly"
    echo "  3. Downloaded to an unexpected location"
    echo ""
    echo "Check if printing works. If not, download .deb files"
    echo "manually from Brother's website and use the Manual Install option."
else
    echo "Found packages:"
    echo "$FOUND_DEBS" | while read deb; do
        echo "  → $(basename "$deb")"
    done
    echo ""
    
    # Convert each .deb file
    for deb in $FOUND_DEBS; do
        if [ -f "$deb" ]; then
            DEB_NAME=$(basename "$deb")
            PKG_BASE=$(echo "$DEB_NAME" | sed 's/_.*//; s/-[0-9].*$//')
            
            echo ""
            echo "Converting: $DEB_NAME"
            echo "─────────────────────────────────────────"
            
            # Track files before conversion
            ls "$WORK_DIR"/*.pkg.tar* 2>/dev/null | sort > /tmp/before_$$.txt || touch /tmp/before_$$.txt
            
            # Run debtap in work directory
            cd "$WORK_DIR"
            debtap -q "$deb"
            DEBTAP_EXIT=$?
            
            if [ $DEBTAP_EXIT -ne 0 ]; then
                echo "⚠ debtap failed for $DEB_NAME (exit: $DEBTAP_EXIT)"
                continue
            fi
            
            # Find NEW package files
            ls "$WORK_DIR"/*.pkg.tar* 2>/dev/null | sort > /tmp/after_$$.txt || touch /tmp/after_$$.txt
            NEW_PKG=$(comm -13 /tmp/before_$$.txt /tmp/after_$$.txt | head -1)
            
            # Fallback: find by package base name
            if [ -z "$NEW_PKG" ]; then
                NEW_PKG=$(ls -t "$WORK_DIR"/$PKG_BASE*.pkg.tar* 2>/dev/null | head -1)
            fi
            
            # Last resort: newest pkg file
            if [ -z "$NEW_PKG" ]; then
                NEW_PKG=$(ls -t "$WORK_DIR"/*.pkg.tar* 2>/dev/null | head -1)
            fi
            
            if [ -n "$NEW_PKG" ] && [ -f "$NEW_PKG" ]; then
                echo "Installing: $(basename "$NEW_PKG")"
                sudo pacman -U --noconfirm "$NEW_PKG"
            else
                echo "⚠ Could not find converted package for $DEB_NAME"
            fi
            
            rm -f /tmp/before_$$.txt /tmp/after_$$.txt
        fi
    done
fi

echo ""
echo "Restarting CUPS..."
sudo systemctl restart cups

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Installation Complete"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Work directory: $WORK_DIR"
echo "(Contains converted packages - safe to delete)"
echo ""
echo "If printing doesn't work:"
echo "  1. Open CUPS: http://localhost:631"
echo "  2. Add printer manually"
echo "  3. Select Brother driver from list"
echo ""
read -p "Press Enter to close..."
'''
        self._run_in_terminal(script)
        self._append_output("Running installation in terminal...")
        self.progress_bar.set_fraction(1.0)
        self.progress_bar.set_text("Follow terminal prompts")
    
    def _on_install_arch_with_debtap(self, button):
        """Install debtap first, then proceed with conversion."""
        self._show_progress()
        self.progress_bar.set_text("Installing debtap...")
        
        script = f'''echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Installing debtap (Arch package converter)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check for AUR helper
if command -v yay &> /dev/null; then
    yay -S --noconfirm debtap
elif command -v paru &> /dev/null; then
    paru -S --noconfirm debtap
else
    echo "Error: No AUR helper found"
    echo "Please install yay or paru first"
    read -p "Press Enter to close..."
    exit 1
fi

echo ""
echo "Initializing debtap database..."
sudo debtap -u

echo ""
echo "✓ debtap installed!"
echo ""
echo "Now you can use the Automatic Installation option."
echo ""
read -p "Press Enter to close..."
'''
        self._run_in_terminal(script)
        self._append_output("Installing debtap - restart wizard after completion")
    
    def _on_open_brother_website(self, button):
        """Open Brother support website."""
        url = "https://support.brother.com/g/b/productsearch.aspx?c=us&lang=en&content=dl"
        try:
            subprocess.Popen(['xdg-open', url])
            self._append_output(f"Opened: {url}")
        except Exception:
            self._append_output("Could not open browser")
    
    def _on_manual_drop(self, button):
        """Open manual driver installation dialog."""
        dialog = ManualDriverDialog(self.parent_window, self.distro)
        dialog.present()
        self.close()
    
    def _run_in_terminal(self, script: str):
        """Run a script in a terminal window."""
        terminals = [
            ('ptyxis', ['ptyxis', '--', 'bash', '-c', script]),
            ('konsole', ['konsole', '-e', 'bash', '-c', script]),
            ('gnome-terminal', ['gnome-terminal', '--', 'bash', '-c', script]),
            ('xfce4-terminal', ['xfce4-terminal', '-e', f'bash -c \'{script}\'']),
            ('tilix', ['tilix', '-e', f'bash -c "{script}"']),
            ('alacritty', ['alacritty', '-e', 'bash', '-c', script]),
            ('kitty', ['kitty', 'bash', '-c', script]),
            ('xterm', ['xterm', '-e', f'bash -c "{script}"']),
        ]
        
        for term_name, term_cmd in terminals:
            try:
                if subprocess.run(['which', term_name], capture_output=True).returncode == 0:
                    subprocess.Popen(term_cmd)
                    return
            except Exception:
                continue


class ManualDriverDialog(Adw.Dialog):
    """Dialog for manually installing printer drivers via drag-drop."""
    
    def __init__(self, parent: Gtk.Window, distro):
        super().__init__()
        
        self.parent_window = parent
        self.distro = distro
        self.dropped_files = []
        
        self.set_title("Manual Driver Installation")
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
        
        self.install_btn = Gtk.Button(label="Install")
        self.install_btn.add_css_class("suggested-action")
        self.install_btn.set_sensitive(False)
        self.install_btn.connect("clicked", self._on_install)
        header.pack_end(self.install_btn)
        
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
            "<b>Drag and drop printer driver files here</b>\n"
            "<small>Supports .deb, .rpm, and source tarballs (.tar.gz)</small>"
        )
        info_label.set_halign(Gtk.Align.CENTER)
        info_label.set_justify(Gtk.Justification.CENTER)
        content.append(info_label)
        
        # Drop zone
        self.drop_zone = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        self.drop_zone.set_size_request(-1, 180)
        self.drop_zone.set_valign(Gtk.Align.CENTER)
        self.drop_zone.set_halign(Gtk.Align.CENTER)
        self.drop_zone.add_css_class("card")
        self.drop_zone.set_vexpand(True)
        self.drop_zone.set_hexpand(True)
        
        drop_frame = Gtk.Frame()
        drop_frame.set_child(self.drop_zone)
        content.append(drop_frame)
        
        # Drop icon
        self.drop_icon = Gtk.Image.new_from_icon_name("tux-folder-download-symbolic")
        self.drop_icon.set_pixel_size(48)
        self.drop_icon.add_css_class("dim-label")
        self.drop_zone.append(self.drop_icon)
        
        # Drop label
        self.drop_label = Gtk.Label(label="Drop .deb, .rpm, or .tar.gz files here")
        self.drop_label.add_css_class("dim-label")
        self.drop_zone.append(self.drop_label)
        
        # Files list
        self.files_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.files_list.set_visible(False)
        content.append(self.files_list)
        
        # Setup drag-drop
        drop_target = Gtk.DropTarget.new(Gio.File, Gdk.DragAction.COPY)
        drop_target.connect("drop", self._on_drop)
        drop_target.connect("accept", self._on_accept)
        drop_frame.add_controller(drop_target)
        
        # Distro info
        distro_label = Gtk.Label()
        if self.distro.family == DistroFamily.ARCH:
            distro_label.set_markup("<small>ℹ️ .deb files will be converted with debtap</small>")
        elif self.distro.family == DistroFamily.FEDORA or self.distro.family == DistroFamily.OPENSUSE:
            distro_label.set_markup("<small>ℹ️ .deb files will be converted with alien</small>")
        else:
            distro_label.set_markup("<small>ℹ️ Native .deb installation</small>")
        distro_label.add_css_class("dim-label")
        content.append(distro_label)
    
    def _on_accept(self, drop_target, drop):
        """Check if we accept the drop."""
        return True
    
    def _on_drop(self, drop_target, value, x, y):
        """Handle dropped file."""
        if isinstance(value, Gio.File):
            path = value.get_path()
            if path:
                # Check file type
                if path.endswith(('.deb', '.rpm', '.tar.gz', '.tgz', '.tar.xz', '.tar.bz2')):
                    self.dropped_files.append(path)
                    self._update_files_display()
                    return True
        return False
    
    def _update_files_display(self):
        """Update the display of dropped files."""
        # Clear old entries
        child = self.files_list.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            self.files_list.remove(child)
            child = next_child
        
        if self.dropped_files:
            self.files_list.set_visible(True)
            self.drop_label.set_text(f"{len(self.dropped_files)} file(s) ready")
            self.install_btn.set_sensitive(True)
            
            for f in self.dropped_files:
                row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
                
                icon = Gtk.Image.new_from_icon_name("tux-package-x-generic-symbolic")
                row.append(icon)
                
                label = Gtk.Label(label=os.path.basename(f))
                label.set_hexpand(True)
                label.set_halign(Gtk.Align.START)
                row.append(label)
                
                remove_btn = Gtk.Button.new_from_icon_name("tux-edit-delete-symbolic")
                remove_btn.add_css_class("flat")
                remove_btn.connect("clicked", self._on_remove_file, f)
                row.append(remove_btn)
                
                self.files_list.append(row)
        else:
            self.files_list.set_visible(False)
            self.drop_label.set_text("Drop .deb, .rpm, or .tar.gz files here")
            self.install_btn.set_sensitive(False)
    
    def _on_remove_file(self, button, filepath):
        """Remove a file from the list."""
        if filepath in self.dropped_files:
            self.dropped_files.remove(filepath)
            self._update_files_display()
    
    def _on_install(self, button):
        """Install the dropped driver files."""
        if not self.dropped_files:
            return
        
        # Create unique work directory for conversions
        import time
        work_dir = f"/tmp/tux-driver-convert-{int(time.time())}"
        
        # Build installation script based on distro and file types
        script_parts = [
            'echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"',
            'echo "  Installing Printer Driver(s)"',
            'echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"',
            'echo ""',
            f'WORK_DIR="{work_dir}"',
            'mkdir -p "$WORK_DIR"',
            '',
        ]
        
        for f in self.dropped_files:
            filename = os.path.basename(f)
            script_parts.append(f'echo "Processing: {filename}"')
            script_parts.append('')
            
            if f.endswith('.deb'):
                if self.distro.family == DistroFamily.DEBIAN:
                    # Native .deb installation
                    script_parts.append(f'sudo dpkg -i --force-all "{f}"')
                    script_parts.append('sudo apt-get install -f -y')
                elif self.distro.family == DistroFamily.ARCH:
                    # Convert with debtap - use robust helper
                    script_parts.append(get_conversion_script_debtap(f, work_dir))
                else:
                    # Fedora/openSUSE - convert with alien
                    script_parts.append(get_conversion_script_alien_to_rpm(f, work_dir))
                    
            elif f.endswith('.rpm'):
                if self.distro.family in (DistroFamily.FEDORA, DistroFamily.OPENSUSE):
                    # Native .rpm installation
                    script_parts.append(f'sudo rpm -ivh --nodeps "{f}"')
                elif self.distro.family == DistroFamily.ARCH:
                    # Arch can extract but not directly install rpm
                    # Use rpmextract or fakeroot approach
                    script_parts.append(f'echo "⚠ Direct .rpm installation on Arch is limited"')
                    script_parts.append(f'echo "  Consider downloading the .deb version instead"')
                    script_parts.append(f'echo "  Or search AUR for this driver"')
                    script_parts.append(f'')
                    script_parts.append(f'# Attempting basic extraction...')
                    script_parts.append(f'cd "$WORK_DIR"')
                    script_parts.append(f'rpm2cpio "{f}" | cpio -idmv')
                    script_parts.append(f'if [ -d opt ]; then sudo cp -r opt/* /opt/ 2>/dev/null; fi')
                    script_parts.append(f'if [ -d usr ]; then sudo cp -r usr/* /usr/ 2>/dev/null; fi')
                else:
                    # Debian - convert with alien
                    script_parts.append(get_conversion_script_alien_to_deb(f, work_dir))
                    
            elif f.endswith(('.tar.gz', '.tgz', '.tar.xz', '.tar.bz2')):
                # Source tarball - try to build
                script_parts.append(f'echo "Extracting source archive..."')
                script_parts.append(f'BUILD_DIR="$WORK_DIR/source-build"')
                script_parts.append(f'mkdir -p "$BUILD_DIR"')
                script_parts.append(f'cd "$BUILD_DIR"')
                script_parts.append(f'tar xf "{f}"')
                script_parts.append(f'')
                script_parts.append(f'# Find the extracted directory')
                script_parts.append(f'EXTRACTED=$(find . -maxdepth 1 -type d ! -name "." | head -1)')
                script_parts.append(f'if [ -n "$EXTRACTED" ]; then cd "$EXTRACTED"; fi')
                script_parts.append(f'')
                script_parts.append(f'# Detect and run build system')
                script_parts.append(f'if [ -f configure ]; then')
                script_parts.append(f'    echo "Detected: autotools"')
                script_parts.append(f'    ./configure && make && sudo make install')
                script_parts.append(f'elif [ -f CMakeLists.txt ]; then')
                script_parts.append(f'    echo "Detected: cmake"')
                script_parts.append(f'    mkdir -p build && cd build && cmake .. && make && sudo make install')
                script_parts.append(f'elif [ -f meson.build ]; then')
                script_parts.append(f'    echo "Detected: meson"')
                script_parts.append(f'    meson setup build && ninja -C build && sudo ninja -C build install')
                script_parts.append(f'elif [ -f install.sh ]; then')
                script_parts.append(f'    echo "Running install.sh..."')
                script_parts.append(f'    sudo bash install.sh')
                script_parts.append(f'elif [ -f Makefile ]; then')
                script_parts.append(f'    echo "Detected: Makefile"')
                script_parts.append(f'    make && sudo make install')
                script_parts.append(f'else')
                script_parts.append(f'    echo "⚠ Unknown build system - manual installation required"')
                script_parts.append(f'    echo "  Contents extracted to: $BUILD_DIR"')
                script_parts.append(f'fi')
            
            script_parts.append('')
            script_parts.append('echo ""')
        
        script_parts.extend([
            '',
            'echo "Restarting CUPS..."',
            'sudo systemctl restart cups',
            '',
            'echo ""',
            'echo "✓ Installation complete!"',
            'echo ""',
            f'echo "Work directory: {work_dir}"',
            'echo "(You can delete this after verifying installation)"',
            'echo ""',
            'read -p "Press Enter to close..."',
        ])
        
        script = '\n'.join(script_parts)
        self._run_in_terminal(script)
        self.close()
    
    def _run_in_terminal(self, script: str):
        """Run a script in a terminal window."""
        terminals = [
            ('ptyxis', ['ptyxis', '--', 'bash', '-c', script]),
            ('konsole', ['konsole', '-e', 'bash', '-c', script]),
            ('gnome-terminal', ['gnome-terminal', '--', 'bash', '-c', script]),
            ('xfce4-terminal', ['xfce4-terminal', '-e', f'bash -c \'{script}\'']),
            ('tilix', ['tilix', '-e', f'bash -c "{script}"']),
            ('alacritty', ['alacritty', '-e', 'bash', '-c', script]),
            ('kitty', ['kitty', 'bash', '-c', script]),
            ('xterm', ['xterm', '-e', f'bash -c "{script}"']),
        ]
        
        for term_name, term_cmd in terminals:
            try:
                if subprocess.run(['which', term_name], capture_output=True).returncode == 0:
                    subprocess.Popen(term_cmd)
                    return
            except Exception:
                continue


# Import Gdk for drag-drop
try:
    gi.require_version('Gdk', '4.0')
    from gi.repository import Gdk
except Exception:
    Gdk = None


# =============================================================================
# Printer Wizard Page
# =============================================================================

@register_module(
    id="printer_wizard",
    name="Printer Wizard",
    description="Detect and set up printers",
    icon="tux-printer-symbolic",
    category=ModuleCategory.SYSTEM,
    order=12
)
class PrinterWizardPage(Adw.NavigationPage):
    """Printer setup wizard page."""
    
    def __init__(self, window):
        super().__init__(title="Printer Wizard")
        
        self.window = window
        self.distro = get_distro()
        self.discovered_printers: List[DiscoveredPrinter] = []
        self.is_scanning = False
        
        self._build_ui()
        self._check_prerequisites()
    
    def _build_ui(self):
        """Build the page UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header
        header = Adw.HeaderBar()
        
        # Refresh button
        self.refresh_btn = Gtk.Button()
        self.refresh_btn.set_icon_name("tux-view-refresh-symbolic")
        self.refresh_btn.set_tooltip_text("Scan for Printers")
        self.refresh_btn.connect("clicked", self._on_scan_clicked)
        header.pack_end(self.refresh_btn)
        
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
        
        # Status section
        self._build_status_section()
        
        # Discovered printers section
        self._build_printers_section()
        
        # Help section
        self._build_help_section()
    
    def _build_status_section(self):
        """Build the CUPS status section."""
        self.status_group = Adw.PreferencesGroup()
        self.status_group.set_title("Printer Service")
        self.status_group.set_description("CUPS print system status")
        self.content_box.append(self.status_group)
        
        self.status_row = Adw.ActionRow()
        self.status_row.set_title("Checking...")
        self.status_group.add(self.status_row)
    
    def _build_printers_section(self):
        """Build the discovered printers section."""
        self.printers_group = Adw.PreferencesGroup()
        self.printers_group.set_title("Discovered Printers")
        self.printers_group.set_description("USB and network printers found on your system")
        self.content_box.append(self.printers_group)
        
        # Placeholder with Scan button
        self.printers_placeholder = Adw.ActionRow()
        self.printers_placeholder.set_title("No printers found yet")
        self.printers_placeholder.set_subtitle("Click Scan to search for USB and network printers")
        self.printers_placeholder.add_prefix(Gtk.Image.new_from_icon_name("tux-printer-symbolic"))
        
        scan_btn = Gtk.Button(label="Scan")
        scan_btn.add_css_class("suggested-action")
        scan_btn.set_valign(Gtk.Align.CENTER)
        scan_btn.connect("clicked", self._on_scan_clicked)
        self.printers_placeholder.add_suffix(scan_btn)
        
        self.printers_group.add(self.printers_placeholder)
        
        self.printer_rows = [self.printers_placeholder]
    
    def _build_help_section(self):
        """Build the help section."""
        # Manual IP entry section
        manual_group = Adw.PreferencesGroup()
        manual_group.set_title("Add Printer by IP Address")
        manual_group.set_description("For printers that aren't discovered automatically")
        self.content_box.append(manual_group)
        
        # IP entry row
        self.ip_entry_row = Adw.EntryRow()
        self.ip_entry_row.set_title("Printer IP Address")
        self.ip_entry_row.set_text("")
        self.ip_entry_row.set_input_purpose(Gtk.InputPurpose.NUMBER)
        
        # Add button to probe the IP
        probe_btn = Gtk.Button(label="Find")
        probe_btn.add_css_class("suggested-action")
        probe_btn.set_valign(Gtk.Align.CENTER)
        probe_btn.connect("clicked", self._on_probe_ip)
        self.ip_entry_row.add_suffix(probe_btn)
        
        manual_group.add(self.ip_entry_row)
        
        # Status row for IP probe results (hidden initially)
        self.ip_status_row = Adw.ActionRow()
        self.ip_status_row.set_visible(False)
        manual_group.add(self.ip_status_row)
        
        # Help section
        help_group = Adw.PreferencesGroup()
        help_group.set_title("Printer Setup Help")
        self.content_box.append(help_group)
        
        # HP printers
        hp_row = Adw.ActionRow()
        hp_row.set_title("HP Printers")
        hp_row.set_subtitle("Usually work great with HPLIP")
        hp_row.add_prefix(Gtk.Image.new_from_icon_name("tux-object-select-symbolic"))
        help_group.add(hp_row)
        
        # Brother printers
        brother_row = Adw.ActionRow()
        brother_row.set_title("Brother Printers")
        brother_row.set_subtitle("May require downloading drivers from Brother")
        brother_row.add_prefix(Gtk.Image.new_from_icon_name("tux-dialog-warning-symbolic"))
        help_group.add(brother_row)
        
        # Other printers
        other_row = Adw.ActionRow()
        other_row.set_title("Other Brands")
        other_row.set_subtitle("Canon, Epson - check manufacturer website for Linux drivers")
        other_row.add_prefix(Gtk.Image.new_from_icon_name("tux-help-about-symbolic"))
        help_group.add(other_row)
        
        # Manual setup
        manual_row = Adw.ActionRow()
        manual_row.set_title("Manual Setup")
        manual_row.set_subtitle("Open CUPS web interface for advanced configuration")
        manual_row.add_prefix(Gtk.Image.new_from_icon_name("tux-emblem-system-symbolic"))
        
        cups_btn = Gtk.Button(label="Open CUPS")
        cups_btn.set_valign(Gtk.Align.CENTER)
        cups_btn.connect("clicked", self._on_open_cups)
        manual_row.add_suffix(cups_btn)
        
        help_group.add(manual_row)
    
    def _check_prerequisites(self):
        """Check CUPS status and update UI."""
        def check():
            installed, running, message = get_cups_status()
            GLib.idle_add(self._update_status, installed, running, message)
        
        threading.Thread(target=check, daemon=True).start()
    
    def _update_status(self, installed: bool, running: bool, message: str):
        """Update the status section based on CUPS state."""
        # Remove old status row
        self.status_group.remove(self.status_row)
        
        if not installed:
            # CUPS not installed
            self.status_row = Adw.ActionRow()
            self.status_row.set_title("Printer Support Not Installed")
            self.status_row.set_subtitle("Install CUPS to enable printing")
            self.status_row.add_prefix(Gtk.Image.new_from_icon_name("tux-dialog-error-symbolic"))
            
            install_btn = Gtk.Button(label="Install CUPS")
            install_btn.set_valign(Gtk.Align.CENTER)
            install_btn.add_css_class("suggested-action")
            install_btn.connect("clicked", self._on_install_cups)
            self.status_row.add_suffix(install_btn)
            
            self.refresh_btn.set_sensitive(False)
            
        elif not running:
            # CUPS installed but not running
            self.status_row = Adw.ActionRow()
            self.status_row.set_title("Printer Service Stopped")
            self.status_row.set_subtitle("Start CUPS to detect and use printers")
            self.status_row.add_prefix(Gtk.Image.new_from_icon_name("tux-dialog-warning-symbolic"))
            
            start_btn = Gtk.Button(label="Start Service")
            start_btn.set_valign(Gtk.Align.CENTER)
            start_btn.add_css_class("suggested-action")
            start_btn.connect("clicked", self._on_start_cups)
            self.status_row.add_suffix(start_btn)
            
            self.refresh_btn.set_sensitive(False)
            
        else:
            # CUPS ready
            self.status_row = Adw.ActionRow()
            self.status_row.set_title("Printer Service Running")
            self.status_row.set_subtitle("Ready to detect and configure printers")
            self.status_row.add_prefix(Gtk.Image.new_from_icon_name("tux-object-select-symbolic"))
            
            self.refresh_btn.set_sensitive(True)
        
        self.status_group.add(self.status_row)
    
    def _on_scan_clicked(self, button):
        """Start scanning for printers."""
        if self.is_scanning:
            return
        
        self.is_scanning = True
        self.refresh_btn.set_sensitive(False)
        
        # Clear existing rows
        for row in self.printer_rows:
            self.printers_group.remove(row)
        self.printer_rows.clear()
        
        # Show scanning indicator
        scanning_row = Adw.ActionRow()
        scanning_row.set_title("Scanning for printers...")
        scanning_row.set_subtitle("Checking USB and network connections")
        
        spinner = Gtk.Spinner()
        spinner.start()
        scanning_row.add_prefix(spinner)
        
        self.printers_group.add(scanning_row)
        self.printer_rows.append(scanning_row)
        
        # Start discovery in background
        def discover():
            printers = discover_all_printers()
            GLib.idle_add(self._update_printers, printers)
        
        threading.Thread(target=discover, daemon=True).start()
    
    def _update_printers(self, printers: List[DiscoveredPrinter]):
        """Update the printers list."""
        self.is_scanning = False
        self.refresh_btn.set_sensitive(True)
        self.discovered_printers = printers
        
        # Clear existing rows
        for row in self.printer_rows:
            self.printers_group.remove(row)
        self.printer_rows.clear()
        
        if not printers:
            # No printers found
            row = Adw.ActionRow()
            row.set_title("No Printers Found")
            row.set_subtitle("Make sure your printer is connected and powered on")
            row.add_prefix(Gtk.Image.new_from_icon_name("tux-printer-symbolic"))
            
            self.printers_group.add(row)
            self.printer_rows.append(row)
            return
        
        # Group by connection type
        usb_printers = [p for p in printers if p.connection_type == PrinterConnectionType.USB]
        network_printers = [p for p in printers if p.connection_type == PrinterConnectionType.NETWORK]
        
        # USB printers
        if usb_printers:
            usb_header = Adw.ActionRow()
            usb_header.set_title(f"USB Printers ({len(usb_printers)})")
            usb_header.add_prefix(Gtk.Image.new_from_icon_name("tux-media-removable-symbolic"))
            self.printers_group.add(usb_header)
            self.printer_rows.append(usb_header)
            
            for printer in usb_printers:
                row = self._create_printer_row(printer)
                self.printers_group.add(row)
                self.printer_rows.append(row)
        
        # Network printers
        if network_printers:
            net_header = Adw.ActionRow()
            net_header.set_title(f"Network Printers ({len(network_printers)})")
            net_header.add_prefix(Gtk.Image.new_from_icon_name("tux-network-workgroup-symbolic"))
            self.printers_group.add(net_header)
            self.printer_rows.append(net_header)
            
            for printer in network_printers:
                row = self._create_printer_row(printer)
                self.printers_group.add(row)
                self.printer_rows.append(row)
    
    def _create_printer_row(self, printer: DiscoveredPrinter) -> Adw.ActionRow:
        """Create a row for a discovered printer."""
        row = Adw.ActionRow()
        row.set_title(printer.display_name)
        
        # Build subtitle
        subtitle_parts = []
        if printer.brand != PrinterBrand.GENERIC:
            subtitle_parts.append(printer.brand.value.upper())
        if printer.location:
            subtitle_parts.append(printer.location)
        if printer.is_configured:
            subtitle_parts.append("✓ Configured")
        
        row.set_subtitle(" • ".join(subtitle_parts) if subtitle_parts else printer.uri)
        
        # Icon based on brand
        icon = "printer-symbolic"
        row.add_prefix(Gtk.Image.new_from_icon_name(icon))
        
        if printer.is_configured:
            # Already set up
            configured_label = Gtk.Label(label="Configured")
            configured_label.add_css_class("dim-label")
            configured_label.set_valign(Gtk.Align.CENTER)
            row.add_suffix(configured_label)
        else:
            # Setup button
            setup_btn = Gtk.Button(label="Set Up")
            setup_btn.set_valign(Gtk.Align.CENTER)
            setup_btn.add_css_class("suggested-action")
            setup_btn.connect("clicked", self._on_setup_printer, printer)
            row.add_suffix(setup_btn)
        
        return row
    
    def _on_setup_printer(self, button, printer: DiscoveredPrinter):
        """Handle printer setup button click."""
        # For now, show what we would do
        # This is where Phase 2/3 will add brand-specific logic
        
        if printer.brand == PrinterBrand.HP:
            self._setup_hp_printer(printer)
        elif printer.brand == PrinterBrand.BROTHER:
            self._setup_brother_printer(printer)
        else:
            self._setup_generic_printer(printer)
    
    def _setup_hp_printer(self, printer: DiscoveredPrinter):
        """Set up an HP printer using HPLIP."""
        # Check if hplip is installed
        result = subprocess.run(['which', 'hp-setup'], capture_output=True)
        
        if result.returncode != 0:
            # Need to install HPLIP first
            dialog = Adw.MessageDialog(
                transient_for=self.window,
                heading="Install HP Printer Drivers",
                body=f"To set up your {printer.display_name}, we need to install HPLIP (HP Linux Imaging and Printing).\n\nWould you like to install it now?"
            )
            dialog.add_response("cancel", "Cancel")
            dialog.add_response("install", "Install HPLIP")
            dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
            dialog.connect("response", self._on_hplip_install_response, printer)
            dialog.present()
        else:
            # HPLIP installed, run setup
            self._run_hp_setup(printer)
    
    def _on_hplip_install_response(self, dialog, response, printer):
        """Handle HPLIP install dialog response."""
        if response != "install":
            return
        
        packages = {
            DistroFamily.ARCH: "hplip",
            DistroFamily.DEBIAN: "hplip hplip-gui",
            DistroFamily.FEDORA: "hplip hplip-gui",
            DistroFamily.OPENSUSE: "hplip hplip-scan",
        }
        
        pkg = packages.get(self.distro.family, "hplip")
        
        if self.distro.family == DistroFamily.ARCH:
            cmd = f"sudo pacman -S --noconfirm {pkg}"
        elif self.distro.family == DistroFamily.DEBIAN:
            cmd = f"sudo apt install -y {pkg}"
        elif self.distro.family == DistroFamily.FEDORA:
            cmd = f"sudo dnf install -y {pkg}"
        elif self.distro.family == DistroFamily.OPENSUSE:
            cmd = f"sudo zypper install -y {pkg}"
        else:
            self.window.show_toast("Unsupported distribution")
            return
        
        script = f'''echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Installing HP Printer Drivers (HPLIP)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
{cmd}
echo ""
echo "✓ Installation complete!"
echo ""
echo "Now running HP printer setup..."
echo ""
hp-setup
echo ""
echo "Press Enter to close..."
read'''
        
        self._run_in_terminal(script)
        self.window.show_toast("Installing HP drivers...")
    
    def _run_hp_setup(self, printer: DiscoveredPrinter):
        """Run HP printer setup."""
        try:
            subprocess.Popen(['hp-setup'])
            self.window.show_toast("Opening HP printer setup...")
        except Exception:
            self.window.show_toast("Could not start HP setup")
    
    def _setup_brother_printer(self, printer: DiscoveredPrinter):
        """Set up a Brother printer using the enhanced wizard."""
        dialog = BrotherSetupDialog(self.window, printer, self.distro)
        dialog.present()
    
    def _on_brother_response(self, dialog, response, printer):
        """Handle Brother dialog response - legacy, kept for compatibility."""
        if response == "open":
            try:
                subprocess.Popen(['xdg-open', 'https://support.brother.com/g/b/productsearch.aspx?c=us&lang=en&content=dl'])
            except Exception:
                self.window.show_toast("Could not open browser")
    
    def _setup_generic_printer(self, printer: DiscoveredPrinter):
        """Set up a generic printer using CUPS."""
        # Use system-config-printer or CUPS web interface
        tools = [
            ['system-config-printer'],
            ['gnome-control-center', 'printers'],
        ]
        
        for tool in tools:
            try:
                result = subprocess.run(['which', tool[0]], capture_output=True)
                if result.returncode == 0:
                    subprocess.Popen(tool)
                    self.window.show_toast("Opening printer settings...")
                    return
            except Exception:
                continue
        
        # Fallback to CUPS web
        try:
            subprocess.Popen(['xdg-open', 'http://localhost:631/admin'])
            self.window.show_toast("Opening CUPS web interface...")
        except Exception:
            self.window.show_toast("Could not open printer settings")
    
    def _on_install_cups(self, button):
        """Install CUPS."""
        packages = {
            DistroFamily.ARCH: "cups cups-pdf",
            DistroFamily.DEBIAN: "cups cups-pdf",
            DistroFamily.FEDORA: "cups cups-pdf",
            DistroFamily.OPENSUSE: "cups cups-pdf",
        }
        
        pkg = packages.get(self.distro.family, "cups")
        
        if self.distro.family == DistroFamily.ARCH:
            cmd = f"sudo pacman -S --noconfirm {pkg}"
        elif self.distro.family == DistroFamily.DEBIAN:
            cmd = f"sudo apt install -y {pkg}"
        elif self.distro.family == DistroFamily.FEDORA:
            cmd = f"sudo dnf install -y {pkg}"
        elif self.distro.family == DistroFamily.OPENSUSE:
            cmd = f"sudo zypper install -y {pkg}"
        else:
            self.window.show_toast("Unsupported distribution")
            return
        
        script = f'''echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Installing Printer Support (CUPS)..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
{cmd}
echo ""
echo "Enabling printer service..."
sudo systemctl enable cups
sudo systemctl start cups
echo ""
echo "✓ Installation complete!"
echo ""
echo "Press Enter to close..."
read'''
        
        self._run_in_terminal(script)
        self.window.show_toast("Installing CUPS...")
        GLib.timeout_add(5000, self._check_prerequisites)
    
    def _on_start_cups(self, button):
        """Start CUPS service."""
        try:
            subprocess.Popen(['pkexec', 'systemctl', 'start', 'cups'])
            self.window.show_toast("Starting printer service...")
            GLib.timeout_add(2000, self._check_prerequisites)
        except Exception:
            self.window.show_toast("Could not start printer service")
    
    def _on_probe_ip(self, button):
        """Probe an IP address for a printer."""
        ip_address = self.ip_entry_row.get_text().strip()
        
        if not ip_address:
            self.window.show_toast("Please enter an IP address")
            return
        
        # Basic IP validation
        import re
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if not re.match(ip_pattern, ip_address):
            self.window.show_toast("Invalid IP address format")
            return
        
        # Validate each octet is 0-255
        octets = ip_address.split('.')
        for octet in octets:
            if int(octet) > 255:
                self.window.show_toast("Invalid IP address")
                return
        
        # Show searching status
        self.ip_status_row.set_visible(True)
        self.ip_status_row.set_title("Searching...")
        self.ip_status_row.set_subtitle(f"Probing {ip_address} for printer services")
        
        # Remove any existing prefix/suffix
        while self.ip_status_row.get_first_child():
            child = self.ip_status_row.get_first_child()
            if hasattr(child, 'get_css_classes'):
                self.ip_status_row.remove(child)
                break
        
        spinner = Gtk.Spinner()
        spinner.start()
        self.ip_status_row.add_prefix(spinner)
        
        # Probe in background thread
        def probe():
            printer = probe_printer_at_ip(ip_address)
            GLib.idle_add(self._on_probe_complete, ip_address, printer)
        
        threading.Thread(target=probe, daemon=True).start()
    
    def _on_probe_complete(self, ip_address: str, printer: Optional[DiscoveredPrinter]):
        """Handle probe completion."""
        # Clear spinner
        child = self.ip_status_row.get_first_child()
        while child:
            next_child = child.get_next_sibling()
            # Check if it's a prefix (spinner)
            self.ip_status_row.remove(child)
            break
        
        if printer:
            # Found a printer!
            self.ip_status_row.set_title(f"✓ Found: {printer.display_name}")
            self.ip_status_row.set_subtitle(f"Protocol: {printer.uri.split('://')[0]} at {ip_address}")
            self.ip_status_row.add_prefix(Gtk.Image.new_from_icon_name("tux-emblem-ok-symbolic"))
            
            # Add setup button
            setup_btn = Gtk.Button(label="Set Up")
            setup_btn.add_css_class("suggested-action")
            setup_btn.set_valign(Gtk.Align.CENTER)
            setup_btn.connect("clicked", self._on_setup_printer, printer)
            self.ip_status_row.add_suffix(setup_btn)
            
            # Also add to discovered printers list
            self.discovered_printers.append(printer)
            
            self.window.show_toast(f"Found printer at {ip_address}")
        else:
            # No printer found
            self.ip_status_row.set_title("No printer found")
            self.ip_status_row.set_subtitle(f"No response from {ip_address} on printer ports (9100, 631, 515)")
            self.ip_status_row.add_prefix(Gtk.Image.new_from_icon_name("tux-dialog-warning-symbolic"))
            
            self.window.show_toast(f"No printer found at {ip_address}")
    
    def _on_open_cups(self, widget):
        """Open CUPS web interface."""
        url = "http://localhost:631"
        
        # Try actual browsers first, then xdg-open/gio as fallback
        # (xdg-open can exist but not work on some systems)
        methods = [
            ['firefox', url],
            ['google-chrome', url],
            ['chromium', url],
            ['chromium-browser', url],
            ['brave', url],
            ['vivaldi', url],
            ['epiphany', url],
            ['konqueror', url],
            ['xdg-open', url],
            ['gio', 'open', url],
        ]
        
        for cmd in methods:
            try:
                result = subprocess.run(['which', cmd[0]], capture_output=True)
                if result.returncode == 0:
                    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    self.window.show_toast("Opening CUPS web interface...")
                    return
            except Exception:
                continue
        
        self.window.show_toast("Could not open browser - try http://localhost:631 manually")
    
    def _run_in_terminal(self, script: str):
        """Run a script in a terminal window."""
        # Import from app.py's terminal detection or use local list
        terminals = [
            ('ptyxis', ['ptyxis', '--', 'bash', '-c', script]),
            ('konsole', ['konsole', '-e', 'bash', '-c', script]),
            ('gnome-terminal', ['gnome-terminal', '--', 'bash', '-c', script]),
            ('xfce4-terminal', ['xfce4-terminal', '-e', f'bash -c \'{script}\'']),
            ('tilix', ['tilix', '-e', f'bash -c "{script}"']),
            ('alacritty', ['alacritty', '-e', 'bash', '-c', script]),
            ('kitty', ['kitty', 'bash', '-c', script]),
            ('xterm', ['xterm', '-e', f'bash -c "{script}"']),
        ]
        
        for term_name, term_cmd in terminals:
            try:
                if subprocess.run(['which', term_name], capture_output=True).returncode == 0:
                    subprocess.Popen(term_cmd)
                    return
            except Exception:
                continue
        
        self.window.show_toast("Could not find terminal emulator")
