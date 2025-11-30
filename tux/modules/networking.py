"""
Tux Assistant - Networking Module

Comprehensive networking tools including:
- Network discovery and browsing
- Samba server configuration
- Active Directory / Domain join
- Firewall management

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

import os
import subprocess
import threading
import json
import tempfile
from gi.repository import Gtk, Adw, GLib, Gio
from dataclasses import dataclass
from typing import Optional
from enum import Enum

from ..core import get_distro, get_desktop, DistroFamily
from .registry import register_module, ModuleCategory
from ..ui.fun_facts import RotatingFunFactWidget


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class NetworkHost:
    """A discovered network host."""
    ip: str
    hostname: str
    mac: Optional[str] = None
    services: list[str] = None
    
    def __post_init__(self):
        if self.services is None:
            self.services = []


@dataclass 
class SambaShare:
    """A Samba share configuration."""
    name: str
    path: str
    comment: str = ""
    browseable: bool = True
    writable: bool = True
    guest_ok: bool = False
    valid_users: str = ""


class FirewallBackend(Enum):
    """Firewall backends."""
    FIREWALLD = "firewalld"
    UFW = "ufw"
    IPTABLES = "iptables"
    NONE = "none"


# =============================================================================
# Helper Functions
# =============================================================================

def get_firewall_backend() -> FirewallBackend:
    """Detect which firewall backend is available."""
    import shutil
    
    if shutil.which('firewall-cmd'):
        # Check if firewalld is running
        result = subprocess.run(
            ['systemctl', 'is-active', 'firewalld'],
            capture_output=True, text=True
        )
        if result.stdout.strip() == 'active':
            return FirewallBackend.FIREWALLD
    
    if shutil.which('ufw'):
        result = subprocess.run(
            ['ufw', 'status'],
            capture_output=True, text=True
        )
        if 'active' in result.stdout.lower():
            return FirewallBackend.UFW
    
    if shutil.which('iptables'):
        return FirewallBackend.IPTABLES
    
    return FirewallBackend.NONE


def get_local_ip() -> str:
    """Get the local IP address."""
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"


def get_hostname() -> str:
    """Get the system hostname."""
    import socket
    return socket.gethostname()


# =============================================================================
# Network Discovery
# =============================================================================

class ScanType(Enum):
    """Types of network scans."""
    QUICK = "quick"  # SMB-only, fast
    FULL = "full"    # All hosts, slower


class NetworkScanner:
    """Scans the local network for hosts and services."""
    
    def __init__(self):
        self.distro = get_distro()
    
    def get_network_range(self) -> str:
        """Get the local network range (e.g., 192.168.1.0/24)."""
        ip = get_local_ip()
        parts = ip.split('.')
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
    
    def resolve_hostname(self, ip: str) -> str:
        """Resolve IP to hostname via reverse DNS."""
        import socket
        try:
            hostname, _, _ = socket.gethostbyaddr(ip)
            return hostname
        except:
            return ""
    
    def scan_for_shares(self, scan_type: ScanType, callback, progress_callback=None) -> list[NetworkHost]:
        """
        Scan the network for hosts with shares.
        
        Args:
            scan_type: QUICK (SMB only) or FULL (all hosts)
            callback: Function to call with status updates (str)
            progress_callback: Function for detailed progress (current, total, found, phase)
        
        Returns:
            List of NetworkHost objects
        """
        import shutil
        
        network = self.get_network_range()
        hosts = []
        
        if scan_type == ScanType.QUICK:
            # Quick scan: Only find hosts with SMB (port 445) open
            hosts = self._scan_smb_hosts(network, callback, progress_callback)
        else:
            # Full scan: Find all hosts, then check for shares
            hosts = self._scan_all_hosts(network, callback, progress_callback)
        
        # For each host, resolve hostname and detect shares
        callback(f"Checking {len(hosts)} host(s) for shares...")
        
        for i, host in enumerate(hosts):
            callback(f"Checking {host.ip}...")
            if progress_callback:
                progress_callback(i + 1, len(hosts), len([h for h in hosts if h.services]), "shares")
            
            # Resolve hostname if not already known
            if not host.hostname or host.hostname == host.ip:
                resolved = self.resolve_hostname(host.ip)
                if resolved:
                    host.hostname = resolved
            
            # Detect SMB shares
            shares = self._get_share_list(host.ip)
            host.services = shares
        
        return hosts
    
    def _scan_smb_hosts(self, network: str, callback, progress_callback=None) -> list[NetworkHost]:
        """Quick scan: Find only hosts with SMB port open."""
        import shutil
        
        hosts = []
        
        if shutil.which('nmap'):
            callback("Quick scan: Finding SMB shares (port 445)...")
            if progress_callback:
                progress_callback(0, 1, 0, "nmap")  # nmap doesn't give per-IP progress
            try:
                # Scan only port 445 (SMB), only show open ports
                result = subprocess.run(
                    ['nmap', '-p', '445', '--open', '-oG', '-', network],
                    capture_output=True, text=True, timeout=30
                )
                
                for line in result.stdout.split('\n'):
                    if 'Host:' in line and '445/open' in line:
                        parts = line.split()
                        ip = parts[1]
                        hostname = ""
                        
                        # Extract hostname if present
                        if '(' in line and ')' in line:
                            start = line.index('(') + 1
                            end = line.index(')')
                            hostname = line[start:end]
                        
                        hosts.append(NetworkHost(ip=ip, hostname=hostname or ip))
                        callback(f"Found SMB host: {hostname or ip} ({ip})")
            
            except subprocess.TimeoutExpired:
                callback("Scan timed out")
            except Exception as e:
                callback(f"Error: {e}")
        else:
            # Fallback: Check common IPs for SMB
            callback("Quick scan: Checking for SMB shares (no nmap)...")
            base = '.'.join(network.split('.')[:3])
            total_ips = 254
            
            for i in range(1, 255):
                ip = f"{base}.{i}"
                if progress_callback:
                    progress_callback(i, total_ips, len(hosts), "smb_scan")
                if self._check_smb_port(ip):
                    hosts.append(NetworkHost(ip=ip, hostname=ip))
                    callback(f"Found SMB host: {ip}")
        
        return hosts
    
    def _check_smb_port(self, ip: str) -> bool:
        """Check if SMB port 445 is open on a host."""
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        try:
            result = sock.connect_ex((ip, 445))
            return result == 0
        except:
            return False
        finally:
            sock.close()
    
    def _scan_all_hosts(self, network: str, callback, progress_callback=None) -> list[NetworkHost]:
        """Full scan: Find all hosts on network."""
        import shutil
        
        hosts = []
        
        # Try nmap first
        if shutil.which('nmap'):
            callback("Full scan: Discovering all network devices...")
            if progress_callback:
                progress_callback(0, 1, 0, "nmap")  # nmap doesn't give per-IP progress
            try:
                result = subprocess.run(
                    ['nmap', '-sn', network, '-oG', '-'],
                    capture_output=True, text=True, timeout=60
                )
                
                for line in result.stdout.split('\n'):
                    if 'Host:' in line and 'Status: Up' in line:
                        parts = line.split()
                        ip = parts[1]
                        hostname = ""
                        
                        if '(' in line and ')' in line:
                            start = line.index('(') + 1
                            end = line.index(')')
                            hostname = line[start:end]
                        
                        hosts.append(NetworkHost(ip=ip, hostname=hostname or ip))
                        callback(f"Found: {hostname or ip} ({ip})")
            
            except subprocess.TimeoutExpired:
                callback("Scan timed out")
            except Exception as e:
                callback(f"Error: {e}")
        
        # Fallback to ARP table + ping sweep (no root needed)
        # arp-scan requires sudo which breaks our pkexec model
        else:
            callback("Full scan: Using ping sweep (this may take a while)...")
            base = '.'.join(network.split('.')[:3])
            total_ips = 254
            
            # First, try to read existing ARP cache for quick wins
            try:
                arp_result = subprocess.run(
                    ['arp', '-n'],
                    capture_output=True, text=True, timeout=5
                )
                for line in arp_result.stdout.split('\n'):
                    parts = line.split()
                    if len(parts) >= 3 and parts[0].count('.') == 3:
                        ip = parts[0]
                        mac = parts[2] if parts[2] != '(incomplete)' else ""
                        if mac:
                            hosts.append(NetworkHost(ip=ip, hostname=ip, mac=mac))
                            callback(f"Found (ARP cache): {ip}")
            except:
                pass
            
            # Then ping sweep for anything not in cache
            found_ips = {h.ip for h in hosts}
            for i in range(1, 255):
                ip = f"{base}.{i}"
                if progress_callback:
                    progress_callback(i, total_ips, len(hosts), "ping_sweep")
                if ip in found_ips:
                    continue
                try:
                    result = subprocess.run(
                        ['ping', '-c', '1', '-W', '1', ip],
                        capture_output=True, timeout=2
                    )
                    if result.returncode == 0:
                        hosts.append(NetworkHost(ip=ip, hostname=ip))
                        callback(f"Found: {ip}")
                except:
                    pass
        
        return hosts
    
    def _get_share_list(self, ip: str) -> list[str]:
        """Get list of SMB shares on a host (quick, no auth)."""
        import shutil
        
        shares = []
        
        if not shutil.which('smbclient'):
            return shares
        
        try:
            result = subprocess.run(
                ['smbclient', '-L', ip, '-N', '-g'],  # -g for parseable output
                capture_output=True, text=True, timeout=5
            )
            
            for line in result.stdout.split('\n'):
                # Format: Disk|ShareName|Comment
                if line.startswith('Disk|'):
                    parts = line.split('|')
                    if len(parts) >= 2:
                        share_name = parts[1]
                        # Skip system shares
                        if not share_name.endswith('$'):
                            shares.append(share_name)
        except:
            pass
        
        return shares
    
    def discover_smb_shares(self, host: str, callback) -> list[str]:
        """Discover SMB shares on a host (detailed, for UI)."""
        import shutil
        shares = []
        
        if not shutil.which('smbclient'):
            callback("smbclient not installed")
            return shares
        
        callback(f"Discovering shares on {host}...")
        
        try:
            result = subprocess.run(
                ['smbclient', '-L', host, '-N'],
                capture_output=True, text=True, timeout=10
            )
            
            in_shares = False
            for line in result.stdout.split('\n'):
                if 'Sharename' in line:
                    in_shares = True
                    continue
                if in_shares and line.strip().startswith('---'):
                    continue
                if in_shares and line.strip():
                    parts = line.split()
                    if parts and not parts[0].startswith('IPC') and not parts[0].endswith('$'):
                        shares.append(parts[0])
                        callback(f"  Share: {parts[0]}")
        
        except Exception as e:
            callback(f"Error: {e}")
        
        return shares


# =============================================================================
# Samba Configuration
# =============================================================================

class SambaManager:
    """Manages Samba server configuration."""
    
    SMB_CONF = "/etc/samba/smb.conf"
    
    def __init__(self):
        self.distro = get_distro()
    
    def get_samba_packages(self) -> list[str]:
        """Get required Samba packages for this distro."""
        packages = {
            DistroFamily.ARCH: ["samba", "smbclient", "cifs-utils"],
            DistroFamily.DEBIAN: ["samba", "smbclient", "cifs-utils"],
            DistroFamily.FEDORA: ["samba", "samba-client", "cifs-utils"],
            DistroFamily.OPENSUSE: ["samba", "samba-client", "cifs-utils"],
        }
        return packages.get(self.distro.family, ["samba", "smbclient"])
    
    def get_samba_service(self) -> str:
        """Get the Samba service name for this distro."""
        if self.distro.family == DistroFamily.DEBIAN:
            return "smbd"
        return "smb"
    
    def is_installed(self) -> bool:
        """Check if Samba is installed."""
        import shutil
        return shutil.which('smbd') is not None
    
    def is_running(self) -> bool:
        """Check if Samba service is running."""
        service = self.get_samba_service()
        result = subprocess.run(
            ['systemctl', 'is-active', service],
            capture_output=True, text=True
        )
        return result.stdout.strip() == 'active'
    
    def get_workgroup(self) -> str:
        """Get current workgroup from smb.conf."""
        try:
            with open(self.SMB_CONF, 'r') as f:
                for line in f:
                    if line.strip().lower().startswith('workgroup'):
                        return line.split('=')[1].strip()
        except:
            pass
        return "WORKGROUP"
    
    def get_shares(self) -> list[SambaShare]:
        """Parse existing shares from smb.conf."""
        shares = []
        try:
            with open(self.SMB_CONF, 'r') as f:
                content = f.read()
            
            import re
            # Find all share sections (excluding global, homes, printers)
            pattern = r'\[([^\]]+)\]([^\[]*)'
            matches = re.findall(pattern, content)
            
            for name, config in matches:
                name = name.strip()
                if name.lower() in ('global', 'homes', 'printers', 'print$'):
                    continue
                
                share = SambaShare(name=name, path="")
                
                for line in config.split('\n'):
                    line = line.strip()
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip().lower()
                        value = value.strip()
                        
                        if key == 'path':
                            share.path = value
                        elif key == 'comment':
                            share.comment = value
                        elif key == 'browseable':
                            share.browseable = value.lower() in ('yes', 'true', '1')
                        elif key in ('writable', 'writeable', 'write ok'):
                            share.writable = value.lower() in ('yes', 'true', '1')
                        elif key == 'guest ok':
                            share.guest_ok = value.lower() in ('yes', 'true', '1')
                        elif key == 'valid users':
                            share.valid_users = value
                
                if share.path:
                    shares.append(share)
        
        except Exception as e:
            # Log silently - caller can handle empty list
            # Avoid print() to stdout in production
            pass
        
        return shares
    
    def generate_share_config(self, share: SambaShare) -> str:
        """Generate smb.conf section for a share."""
        config = f"""
[{share.name}]
    path = {share.path}
    comment = {share.comment or share.name}
    browseable = {"yes" if share.browseable else "no"}
    writable = {"yes" if share.writable else "no"}
    guest ok = {"yes" if share.guest_ok else "no"}
"""
        if share.valid_users:
            config += f"    valid users = {share.valid_users}\n"
        
        return config
    
    def create_install_plan(self) -> dict:
        """Create an installation plan for Samba setup."""
        service = self.get_samba_service()
        
        return {
            "tasks": [
                {
                    "type": "install",
                    "name": "Install Samba packages",
                    "packages": self.get_samba_packages()
                },
                {
                    "type": "command",
                    "name": "Enable Samba service",
                    "command": f"systemctl enable --now {service}"
                },
                {
                    "type": "command",
                    "name": "Enable NetBIOS service", 
                    "command": "systemctl enable --now nmb || systemctl enable --now nmbd || true"
                }
            ]
        }
    
    def create_share_plan(self, share: SambaShare) -> dict:
        """Create a plan to add a new share."""
        config = self.generate_share_config(share)
        service = self.get_samba_service()
        
        # Escape the config for shell
        escaped_config = config.replace("'", "'\\''")
        escaped_name = share.name.replace("'", "'\\''")
        
        return {
            "tasks": [
                {
                    "type": "command",
                    "name": "Backup smb.conf (if exists)",
                    "command": "[ -f /etc/samba/smb.conf ] && cp /etc/samba/smb.conf /etc/samba/smb.conf.bak-$(date +%Y%m%d-%H%M%S) || echo 'No existing config to backup (fresh install)'"
                },
                {
                    "type": "command",
                    "name": "Ensure smb.conf exists",
                    "command": "[ -f /etc/samba/smb.conf ] || echo '[global]' > /etc/samba/smb.conf"
                },
                {
                    "type": "command",
                    "name": f"Check for existing [{share.name}] section",
                    "command": f"! grep -q '^\\[{escaped_name}\\]' /etc/samba/smb.conf || (echo 'ERROR: Share [{share.name}] already exists in smb.conf' && exit 1)"
                },
                {
                    "type": "command",
                    "name": f"Create directory {share.path}",
                    "command": f"mkdir -p '{share.path}'"
                },
                {
                    "type": "command",
                    "name": "Set directory permissions",
                    "command": f"chmod 0775 '{share.path}'"
                },
                {
                    "type": "command",
                    "name": "Add share to smb.conf",
                    "command": f"echo '{escaped_config}' >> /etc/samba/smb.conf"
                },
                {
                    "type": "command",
                    "name": "Test configuration",
                    "command": "testparm -s"
                },
                {
                    "type": "command",
                    "name": "Restart Samba",
                    "command": f"systemctl restart {service}"
                }
            ]
        }
    
    def create_delete_share_plan(self, share_name: str) -> dict:
        """Create a plan to remove a share from smb.conf."""
        service = self.get_samba_service()
        escaped_name = share_name.replace("'", "'\\''").replace("[", "\\[").replace("]", "\\]")
        
        # Use sed to remove the share section
        # This removes from [share_name] to the next section or EOF
        return {
            "tasks": [
                {
                    "type": "command",
                    "name": "Backup smb.conf",
                    "command": "[ -f /etc/samba/smb.conf ] && cp /etc/samba/smb.conf /etc/samba/smb.conf.bak-$(date +%Y%m%d-%H%M%S) || echo 'No config to backup'"
                },
                {
                    "type": "command",
                    "name": f"Remove share [{share_name}]",
                    "command": f"sed -i '/^\\[{escaped_name}\\]/,/^\\[/{{/^\\[{escaped_name}\\]/d;/^\\[/!d}}' /etc/samba/smb.conf"
                },
                {
                    "type": "command",
                    "name": "Clean up empty lines",
                    "command": "sed -i '/^$/N;/^\\n$/d' /etc/samba/smb.conf"
                },
                {
                    "type": "command",
                    "name": "Test configuration",
                    "command": "testparm -s"
                },
                {
                    "type": "command",
                    "name": "Restart Samba",
                    "command": f"systemctl restart {service}"
                }
            ]
        }
    
    def create_modify_share_plan(self, old_name: str, share: SambaShare) -> dict:
        """Create a plan to modify an existing share."""
        service = self.get_samba_service()
        config = self.generate_share_config(share)
        escaped_config = config.replace("'", "'\\''")
        escaped_old = old_name.replace("'", "'\\''").replace("[", "\\[").replace("]", "\\]")
        
        return {
            "tasks": [
                {
                    "type": "command",
                    "name": "Backup smb.conf",
                    "command": "[ -f /etc/samba/smb.conf ] && cp /etc/samba/smb.conf /etc/samba/smb.conf.bak-$(date +%Y%m%d-%H%M%S) || echo 'No config to backup'"
                },
                {
                    "type": "command",
                    "name": f"Remove old share [{old_name}]",
                    "command": f"sed -i '/^\\[{escaped_old}\\]/,/^\\[/{{/^\\[{escaped_old}\\]/d;/^\\[/!d}}' /etc/samba/smb.conf"
                },
                {
                    "type": "command",
                    "name": f"Add updated share [{share.name}]",
                    "command": f"echo '{escaped_config}' >> /etc/samba/smb.conf"
                },
                {
                    "type": "command",
                    "name": "Test configuration",
                    "command": "testparm -s"
                },
                {
                    "type": "command",
                    "name": "Restart Samba",
                    "command": f"systemctl restart {service}"
                }
            ]
        }


# =============================================================================
# Active Directory / Domain Join
# =============================================================================

class ADManager:
    """Manages Active Directory integration."""
    
    def __init__(self):
        self.distro = get_distro()
    
    def get_ad_packages(self) -> list[str]:
        """Get packages needed for AD join."""
        base = {
            DistroFamily.ARCH: [
                "samba", "sssd", "krb5", "realmd", "oddjob", "smbclient"
            ],
            DistroFamily.DEBIAN: [
                "samba", "sssd", "sssd-tools", "krb5-user", "realmd", 
                "oddjob", "oddjob-mkhomedir", "adcli", "smbclient",
                "libnss-sss", "libpam-sss"
            ],
            DistroFamily.FEDORA: [
                "samba", "samba-common-tools", "sssd", "sssd-ad", 
                "krb5-workstation", "realmd", "oddjob", "oddjob-mkhomedir",
                "adcli", "samba-client"
            ],
            DistroFamily.OPENSUSE: [
                "samba", "sssd", "sssd-ad", "krb5-client", "adcli", "samba-client"
            ],
        }
        return base.get(self.distro.family, [])
    
    def is_domain_joined(self) -> tuple[bool, str]:
        """Check if system is joined to a domain. Returns (joined, domain_name)."""
        import shutil
        
        if not shutil.which('realm'):
            return False, ""
        
        try:
            result = subprocess.run(
                ['realm', 'list'],
                capture_output=True, text=True, timeout=10
            )
            
            if result.stdout.strip():
                # Parse domain name from output
                for line in result.stdout.split('\n'):
                    if line and not line.startswith(' '):
                        return True, line.strip()
        except:
            pass
        
        return False, ""
    
    def discover_domain(self, domain: str) -> dict:
        """Discover information about a domain."""
        import shutil
        
        info = {
            "domain": domain,
            "realm": "",
            "domain_controllers": [],
            "client_software": "",
            "server_software": "",
        }
        
        if not shutil.which('realm'):
            return info
        
        try:
            result = subprocess.run(
                ['realm', 'discover', domain],
                capture_output=True, text=True, timeout=30
            )
            
            for line in result.stdout.split('\n'):
                line = line.strip()
                if line.startswith('realm-name:'):
                    info['realm'] = line.split(':', 1)[1].strip()
                elif line.startswith('domain-name:'):
                    info['domain'] = line.split(':', 1)[1].strip()
                elif line.startswith('client-software:'):
                    info['client_software'] = line.split(':', 1)[1].strip()
                elif line.startswith('server-software:'):
                    info['server_software'] = line.split(':', 1)[1].strip()
        
        except Exception as e:
            # Silently fail - domain discovery is optional
            # Avoid print() to stdout in production
            pass
        
        return info
    
    def create_join_plan(self, domain: str, admin_user: str, admin_pass: str, 
                         computer_ou: str = "") -> dict:
        """Create a plan to join an AD domain."""
        packages = self.get_ad_packages()
        
        # Escape single quotes in password for shell safety
        safe_pass = admin_pass.replace("'", "'\\''")
        safe_user = admin_user.replace("'", "'\\''")
        safe_domain = domain.replace("'", "'\\''")
        
        # Build realm join command using stdin redirect (more secure than echo in ps output)
        # The password goes through stdin, not visible in process list
        if computer_ou:
            safe_ou = computer_ou.replace("'", "'\\''")
            join_cmd = f"realm join -U '{safe_user}' --computer-ou='{safe_ou}' '{safe_domain}' <<< '{safe_pass}'"
        else:
            join_cmd = f"realm join -U '{safe_user}' '{safe_domain}' <<< '{safe_pass}'"
        
        tasks = [
            {
                "type": "install",
                "name": "Install AD/Kerberos packages",
                "packages": packages
            },
            {
                "type": "command",
                "name": f"Join domain {domain}",
                "command": join_cmd
            },
            {
                "type": "command",
                "name": "Enable SSSD",
                "command": "systemctl enable --now sssd"
            },
            {
                "type": "command",
                "name": "Enable home directory creation",
                "command": "authselect select sssd with-mkhomedir --force || pam-auth-update --enable mkhomedir || true"
            }
        ]
        
        return {"tasks": tasks}
    
    def create_leave_plan(self, domain: str, admin_user: str, admin_pass: str) -> dict:
        """Create a plan to leave an AD domain."""
        safe_pass = admin_pass.replace("'", "'\\''")
        safe_user = admin_user.replace("'", "'\\''")
        safe_domain = domain.replace("'", "'\\''")
        
        leave_cmd = f"realm leave -U '{safe_user}' '{safe_domain}' <<< '{safe_pass}'"
        
        return {
            "tasks": [
                {
                    "type": "command",
                    "name": f"Leave domain {domain}",
                    "command": leave_cmd
                },
                {
                    "type": "command",
                    "name": "Stop SSSD",
                    "command": "systemctl disable --now sssd || true"
                }
            ]
        }


# =============================================================================
# Firewall Management
# =============================================================================

class FirewallManager:
    """Manages firewall rules."""
    
    COMMON_SERVICES = {
        "ssh": {"port": "22/tcp", "desc": "SSH remote access"},
        "http": {"port": "80/tcp", "desc": "Web server (HTTP)"},
        "https": {"port": "443/tcp", "desc": "Web server (HTTPS)"},
        "samba": {"port": "137-139/tcp,445/tcp", "desc": "Windows file sharing"},
        "nfs": {"port": "2049/tcp", "desc": "NFS file sharing"},
        "vnc": {"port": "5900-5910/tcp", "desc": "VNC remote desktop"},
        "rdp": {"port": "3389/tcp", "desc": "RDP remote desktop"},
        "mysql": {"port": "3306/tcp", "desc": "MySQL database"},
        "postgresql": {"port": "5432/tcp", "desc": "PostgreSQL database"},
        "dns": {"port": "53/tcp,53/udp", "desc": "DNS server"},
        "dhcp": {"port": "67-68/udp", "desc": "DHCP server"},
        "ftp": {"port": "21/tcp", "desc": "FTP file transfer"},
        "smtp": {"port": "25/tcp", "desc": "Email (SMTP)"},
        "imap": {"port": "143/tcp,993/tcp", "desc": "Email (IMAP)"},
        "cups": {"port": "631/tcp", "desc": "Printing (CUPS)"},
        "mdns": {"port": "5353/udp", "desc": "Multicast DNS (Avahi)"},
        "syncthing": {"port": "22000/tcp,21027/udp", "desc": "Syncthing"},
        "plex": {"port": "32400/tcp", "desc": "Plex Media Server"},
        "minecraft": {"port": "25565/tcp", "desc": "Minecraft server"},
    }
    
    def __init__(self):
        self.backend = get_firewall_backend()
        self.distro = get_distro()
    
    def get_status(self) -> tuple[bool, str]:
        """Get firewall status. Returns (active, backend_name)."""
        if self.backend == FirewallBackend.NONE:
            return False, "none"
        return True, self.backend.value
    
    def get_open_ports(self) -> list[str]:
        """Get list of currently open ports/services."""
        ports = []
        
        if self.backend == FirewallBackend.FIREWALLD:
            try:
                result = subprocess.run(
                    ['firewall-cmd', '--list-all'],
                    capture_output=True, text=True
                )
                for line in result.stdout.split('\n'):
                    if line.strip().startswith('services:'):
                        services = line.split(':', 1)[1].strip().split()
                        ports.extend(services)
                    elif line.strip().startswith('ports:'):
                        port_list = line.split(':', 1)[1].strip().split()
                        ports.extend(port_list)
            except:
                pass
        
        elif self.backend == FirewallBackend.UFW:
            try:
                result = subprocess.run(
                    ['ufw', 'status', 'verbose'],
                    capture_output=True, text=True
                )
                for line in result.stdout.split('\n'):
                    if 'ALLOW' in line:
                        parts = line.split()
                        if parts:
                            ports.append(parts[0])
            except:
                pass
        
        return ports
    
    def create_open_port_command(self, service_or_port: str) -> str:
        """Create command to open a port/service."""
        if self.backend == FirewallBackend.FIREWALLD:
            # Check if it's a known service name
            if service_or_port in self.COMMON_SERVICES:
                return f"firewall-cmd --permanent --add-service={service_or_port} && firewall-cmd --reload"
            else:
                return f"firewall-cmd --permanent --add-port={service_or_port} && firewall-cmd --reload"
        
        elif self.backend == FirewallBackend.UFW:
            # UFW uses different syntax
            if '/' in service_or_port:
                port, proto = service_or_port.split('/')
                return f"ufw allow {port}/{proto}"
            else:
                return f"ufw allow {service_or_port}"
        
        return f"# No firewall backend detected for: {service_or_port}"
    
    def create_close_port_command(self, service_or_port: str) -> str:
        """Create command to close a port/service."""
        if self.backend == FirewallBackend.FIREWALLD:
            if service_or_port in self.COMMON_SERVICES:
                return f"firewall-cmd --permanent --remove-service={service_or_port} && firewall-cmd --reload"
            else:
                return f"firewall-cmd --permanent --remove-port={service_or_port} && firewall-cmd --reload"
        
        elif self.backend == FirewallBackend.UFW:
            if '/' in service_or_port:
                port, proto = service_or_port.split('/')
                return f"ufw delete allow {port}/{proto}"
            else:
                return f"ufw delete allow {service_or_port}"
        
        return f"# No firewall backend detected for: {service_or_port}"


# =============================================================================
# Networking Module UI - Split into Simple and Advanced
# =============================================================================

@register_module(
    id="networking_simple",
    name="Networking",
    description="WiFi, file sharing, hotspot, and speed test",
    icon="network-wireless-symbolic",
    category=ModuleCategory.NETWORK,
    order=10
)
class SimpleNetworkingPage(Adw.NavigationPage):
    """Simple networking tools for everyday users."""
    
    def __init__(self, window: 'LinuxToolkitWindow'):
        super().__init__(title="Networking")
        
        self.window = window
        self.distro = get_distro()
        
        # Managers (shared)
        self.samba = SambaManager()
        self.scanner = NetworkScanner()
        
        self.build_ui()
    
    def build_ui(self):
        """Build the networking UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        
        refresh_btn = Gtk.Button()
        refresh_btn.set_icon_name("view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh status")
        refresh_btn.connect("clicked", self.on_refresh)
        header.pack_end(refresh_btn)
        
        toolbar_view.add_top_bar(header)
        
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled.set_vexpand(True)
        toolbar_view.set_content(self.scrolled)
        
        self._build_content()
    
    def _build_content(self):
        """Build simple networking content."""
        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_margin_top(20)
        clamp.set_margin_bottom(20)
        clamp.set_margin_start(20)
        clamp.set_margin_end(20)
        self.scrolled.set_child(clamp)
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        clamp.set_child(content_box)
        
        # Simple status (just IP and connection)
        content_box.append(self._create_simple_status())
        
        # WiFi section
        content_box.append(self._create_wifi_section())
        
        # Quick file sharing
        content_box.append(self._create_quick_share_section())
        
        # Find shared folders
        content_box.append(self._create_find_shares_section())
        
        # Network tools (hotspot, speed test)
        content_box.append(self._create_network_tools_section())
    
    def _create_simple_status(self) -> Gtk.Widget:
        """Create simple status section."""
        group = Adw.PreferencesGroup()
        group.set_title("Network Status")
        
        # Connection status
        ip = get_local_ip()
        status_row = Adw.ActionRow()
        status_row.set_title("Connection")
        if ip and ip != "127.0.0.1":
            status_row.set_subtitle(f"Connected ({ip})")
            status_row.add_prefix(Gtk.Image.new_from_icon_name("network-wired-symbolic"))
        else:
            status_row.set_subtitle("Not connected")
            status_row.add_prefix(Gtk.Image.new_from_icon_name("network-offline-symbolic"))
        group.add(status_row)
        
        # WiFi status
        wifi_status = self._get_wifi_status()
        wifi_row = Adw.ActionRow()
        wifi_row.set_title("WiFi")
        if wifi_status['connected']:
            wifi_row.set_subtitle(f"Connected to {wifi_status['ssid']}")
            wifi_row.add_prefix(Gtk.Image.new_from_icon_name("network-wireless-signal-excellent-symbolic"))
        elif wifi_status['enabled']:
            wifi_row.set_subtitle("Enabled but not connected")
            wifi_row.add_prefix(Gtk.Image.new_from_icon_name("network-wireless-offline-symbolic"))
        else:
            wifi_row.set_subtitle("Disabled")
            wifi_row.add_prefix(Gtk.Image.new_from_icon_name("network-wireless-disabled-symbolic"))
        group.add(wifi_row)
        
        return group
    
    def _create_wifi_section(self) -> Gtk.Widget:
        """Create WiFi management section."""
        group = Adw.PreferencesGroup()
        group.set_title("WiFi")
        group.set_description("Wireless network management")
        
        has_nmcli = subprocess.run(['which', 'nmcli'], capture_output=True).returncode == 0
        
        if not has_nmcli:
            info_row = Adw.ActionRow()
            info_row.set_title("NetworkManager Not Found")
            info_row.set_subtitle("WiFi management requires NetworkManager")
            info_row.add_prefix(Gtk.Image.new_from_icon_name("dialog-warning-symbolic"))
            group.add(info_row)
            return group
        
        # WiFi settings link
        settings_row = Adw.ActionRow()
        settings_row.set_title("WiFi Settings")
        settings_row.set_subtitle("Connect to networks, manage saved connections")
        settings_row.add_prefix(Gtk.Image.new_from_icon_name("network-wireless-symbolic"))
        settings_row.set_activatable(True)
        settings_row.connect("activated", self._on_open_wifi_settings)
        settings_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        group.add(settings_row)
        
        # Connect to hidden network
        hidden_row = Adw.ActionRow()
        hidden_row.set_title("Connect to Hidden Network")
        hidden_row.set_subtitle("Join a network that doesn't broadcast its name")
        hidden_row.add_prefix(Gtk.Image.new_from_icon_name("network-wireless-acquiring-symbolic"))
        hidden_row.set_activatable(True)
        hidden_row.connect("activated", self._on_connect_hidden_network)
        hidden_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        group.add(hidden_row)
        
        return group
    
    def _create_quick_share_section(self) -> Gtk.Widget:
        """Create quick file sharing section."""
        group = Adw.PreferencesGroup()
        group.set_title("Share Files")
        group.set_description("Share folders with other computers on your network")
        
        if not self.samba.is_installed():
            # Offer to install
            install_row = Adw.ActionRow()
            install_row.set_title("File Sharing Not Installed")
            install_row.set_subtitle("Install Samba to share files with other computers")
            install_row.add_prefix(Gtk.Image.new_from_icon_name("folder-remote-symbolic"))
            
            install_btn = Gtk.Button(label="Install")
            install_btn.set_valign(Gtk.Align.CENTER)
            install_btn.add_css_class("suggested-action")
            install_btn.connect("clicked", self.on_install_samba)
            install_row.add_suffix(install_btn)
            
            group.add(install_row)
        else:
            # Quick share button
            share_row = Adw.ActionRow()
            share_row.set_title("Share a Folder")
            share_row.set_subtitle("Quickly share a folder on your network")
            share_row.add_prefix(Gtk.Image.new_from_icon_name("folder-publicshare-symbolic"))
            share_row.set_activatable(True)
            share_row.connect("activated", self.on_quick_share)
            share_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            group.add(share_row)
            
            # Status
            if self.samba.is_running():
                shares = self.samba.get_shares()
                if shares:
                    status_row = Adw.ActionRow()
                    status_row.set_title("Currently Sharing")
                    status_row.set_subtitle(f"{len(shares)} folder(s) shared")
                    status_row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
                    group.add(status_row)
        
        return group
    
    def _create_find_shares_section(self) -> Gtk.Widget:
        """Create section to find shared folders."""
        group = Adw.PreferencesGroup()
        group.set_title("Find Shared Folders")
        group.set_description("Browse shared folders on your network")
        
        # Quick scan
        scan_row = Adw.ActionRow()
        scan_row.set_title("Scan for Shared Folders")
        scan_row.set_subtitle("Find computers sharing files on your network")
        scan_row.add_prefix(Gtk.Image.new_from_icon_name("folder-remote-symbolic"))
        scan_row.set_activatable(True)
        scan_row.connect("activated", self.on_quick_scan)
        scan_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        group.add(scan_row)
        
        # Browse network
        browse_row = Adw.ActionRow()
        browse_row.set_title("Browse Network")
        browse_row.set_subtitle("Open network location in file manager")
        browse_row.add_prefix(Gtk.Image.new_from_icon_name("network-workgroup-symbolic"))
        browse_row.set_activatable(True)
        browse_row.connect("activated", self.on_browse_network)
        browse_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        group.add(browse_row)
        
        return group
    
    def _create_network_tools_section(self) -> Gtk.Widget:
        """Create network tools section."""
        group = Adw.PreferencesGroup()
        group.set_title("Network Tools")
        
        # WiFi Hotspot
        hotspot_row = Adw.ActionRow()
        hotspot_row.set_title("Create WiFi Hotspot")
        hotspot_row.set_subtitle("Share your internet connection wirelessly")
        hotspot_row.add_prefix(Gtk.Image.new_from_icon_name("network-wireless-hotspot-symbolic"))
        hotspot_row.set_activatable(True)
        hotspot_row.connect("activated", self._on_create_hotspot)
        hotspot_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        group.add(hotspot_row)
        
        # Speed test
        speed_row = Adw.ActionRow()
        speed_row.set_title("Speed Test")
        speed_row.set_subtitle("Test your internet connection speed")
        speed_row.add_prefix(Gtk.Image.new_from_icon_name("utilities-system-monitor-symbolic"))
        speed_row.set_activatable(True)
        speed_row.connect("activated", self._on_run_speedtest)
        speed_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        group.add(speed_row)
        
        # Network settings
        settings_row = Adw.ActionRow()
        settings_row.set_title("Network Settings")
        settings_row.set_subtitle("Open system network configuration")
        settings_row.add_prefix(Gtk.Image.new_from_icon_name("preferences-system-network-symbolic"))
        settings_row.set_activatable(True)
        settings_row.connect("activated", self._on_open_network_settings)
        settings_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        group.add(settings_row)
        
        return group
    
    def on_refresh(self, button):
        """Refresh the status."""
        self._build_content()
        self.window.show_toast("Status refreshed")
    
    def _get_wifi_status(self) -> dict:
        """Get current WiFi status."""
        status = {'enabled': False, 'connected': False, 'ssid': ''}
        
        try:
            result = subprocess.run(['nmcli', 'radio', 'wifi'], capture_output=True, text=True)
            status['enabled'] = result.stdout.strip() == 'enabled'
            
            if status['enabled']:
                result = subprocess.run(
                    ['nmcli', '-t', '-f', 'ACTIVE,SSID', 'dev', 'wifi'],
                    capture_output=True, text=True
                )
                for line in result.stdout.strip().split('\n'):
                    if line.startswith('yes:'):
                        status['connected'] = True
                        status['ssid'] = line.split(':', 1)[1] if ':' in line else ''
                        break
        except Exception:
            pass
        
        return status
    
    # Event handlers (reuse from original)
    def _on_open_wifi_settings(self, row):
        tools = [['gnome-control-center', 'wifi'], ['nm-connection-editor'], 
                 ['systemsettings', 'kcm_networkmanagement']]
        for tool in tools:
            try:
                if subprocess.run(['which', tool[0]], capture_output=True).returncode == 0:
                    subprocess.Popen(tool)
                    return
            except Exception:
                continue
        self.window.show_toast("Could not open WiFi settings")
    
    def _on_connect_hidden_network(self, row):
        dialog = Adw.MessageDialog(transient_for=self.window, heading="Connect to Hidden Network",
                                    body="Enter the network name (SSID) and password.")
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        
        ssid_group = Adw.PreferencesGroup()
        ssid_entry = Adw.EntryRow()
        ssid_entry.set_title("Network Name (SSID)")
        ssid_group.add(ssid_entry)
        content.append(ssid_group)
        
        pass_group = Adw.PreferencesGroup()
        pass_entry = Adw.PasswordEntryRow()
        pass_entry.set_title("Password")
        pass_group.add(pass_entry)
        content.append(pass_group)
        
        dialog.set_extra_child(content)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("connect", "Connect")
        dialog.set_response_appearance("connect", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_hidden_response, ssid_entry, pass_entry)
        dialog.present()
    
    def _on_hidden_response(self, dialog, response, ssid_entry, pass_entry):
        if response != "connect":
            return
        ssid = ssid_entry.get_text().strip()
        password = pass_entry.get_text()
        if not ssid:
            self.window.show_toast("Please enter a network name")
            return
        try:
            result = subprocess.run(['nmcli', 'device', 'wifi', 'connect', ssid, 
                                    'password', password, 'hidden', 'yes'],
                                   capture_output=True, text=True)
            if result.returncode == 0:
                self.window.show_toast(f"Connected to {ssid}")
            else:
                self.window.show_toast(f"Failed: {result.stderr.strip()}")
        except Exception as e:
            self.window.show_toast(f"Error: {str(e)}")
    
    def on_install_samba(self, button):
        dialog = Adw.MessageDialog(transient_for=self.window, heading="Install File Sharing",
                                    body="This will install Samba for sharing files on your network.")
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("install", "Install")
        dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_install_samba_response)
        dialog.present()
    
    def _on_install_samba_response(self, dialog, response):
        if response == "install":
            plan = self.samba.create_install_plan()
            self._execute_plan(plan, "Installing File Sharing")
    
    def on_quick_share(self, row):
        dialog = QuickShareDialog(self.window, self.samba, self._execute_plan)
        dialog.present()
    
    def on_quick_scan(self, row):
        page = NetworkScanPage(self.window, self.scanner, ScanType.QUICK)
        self.window.navigation_view.push(page)
    
    def on_browse_network(self, row):
        subprocess.Popen(['xdg-open', 'smb://'])
    
    def _on_create_hotspot(self, row):
        # Check if hotspot running
        try:
            result = subprocess.run(['nmcli', '-t', '-f', 'NAME,TYPE', 'connection', 'show', '--active'],
                                   capture_output=True, text=True)
            for line in result.stdout.strip().split('\n'):
                if 'Hotspot' in line:
                    dialog = Adw.MessageDialog(transient_for=self.window, heading="Hotspot Active",
                                                body="Would you like to stop it?")
                    dialog.add_response("cancel", "Cancel")
                    dialog.add_response("stop", "Stop Hotspot")
                    dialog.set_response_appearance("stop", Adw.ResponseAppearance.DESTRUCTIVE)
                    dialog.connect("response", lambda d, r: subprocess.run(['nmcli', 'connection', 'down', 'Hotspot']) if r == "stop" else None)
                    dialog.present()
                    return
        except Exception:
            pass
        
        dialog = Adw.MessageDialog(transient_for=self.window, heading="Create WiFi Hotspot", body="")
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        
        name_group = Adw.PreferencesGroup()
        name_entry = Adw.EntryRow()
        name_entry.set_title("Hotspot Name")
        name_entry.set_text(f"{os.uname().nodename}-hotspot")
        name_group.add(name_entry)
        content.append(name_group)
        
        pass_group = Adw.PreferencesGroup()
        pass_entry = Adw.PasswordEntryRow()
        pass_entry.set_title("Password (min 8 characters)")
        pass_group.add(pass_entry)
        content.append(pass_group)
        
        dialog.set_extra_child(content)
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("create", "Create")
        dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_hotspot_response, name_entry, pass_entry)
        dialog.present()
    
    def _on_hotspot_response(self, dialog, response, name_entry, pass_entry):
        if response != "create":
            return
        name = name_entry.get_text().strip()
        password = pass_entry.get_text()
        if not name or len(password) < 8:
            self.window.show_toast("Name required and password must be 8+ characters")
            return
        try:
            result = subprocess.run(['nmcli', 'device', 'wifi', 'hotspot', 'ssid', name, 'password', password],
                                   capture_output=True, text=True)
            self.window.show_toast(f"Hotspot '{name}' created!" if result.returncode == 0 else f"Failed: {result.stderr.strip()}")
        except Exception as e:
            self.window.show_toast(f"Error: {str(e)}")
    
    def _on_run_speedtest(self, row):
        if subprocess.run(['which', 'speedtest-cli'], capture_output=True).returncode != 0:
            dialog = Adw.MessageDialog(transient_for=self.window, heading="Speed Test Required",
                                        body="speedtest-cli is needed.")
            dialog.add_response("cancel", "Cancel")
            dialog.add_response("install", "Install")
            dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
            dialog.connect("response", self._on_install_speedtest)
            dialog.present()
            return
        self._run_in_terminal('echo "Speed Test"; echo ""; speedtest-cli; echo ""; read -p "Press Enter..."')
    
    def _on_install_speedtest(self, dialog, response):
        if response == "install":
            plan = {
                "tasks": [
                    {"type": "install", "name": "Install speedtest-cli", "packages": ["speedtest-cli"]}
                ]
            }
            self._execute_plan(plan, "Installing Speed Test")
    
    def _on_open_network_settings(self, row):
        tools = [['gnome-control-center', 'network'], ['nm-connection-editor'],
                 ['systemsettings', 'kcm_networkmanagement']]
        for tool in tools:
            try:
                if subprocess.run(['which', tool[0]], capture_output=True).returncode == 0:
                    subprocess.Popen(tool)
                    return
            except Exception:
                continue
        self.window.show_toast("Could not open network settings")
    
    def _run_in_terminal(self, script: str):
        terminals = [('konsole', ['konsole', '-e', 'bash', '-c', script]),
                     ('gnome-terminal', ['gnome-terminal', '--', 'bash', '-c', script]),
                     ('xfce4-terminal', ['xfce4-terminal', '-e', f'bash -c \'{script}\''])]
        for name, cmd in terminals:
            if subprocess.run(['which', name], capture_output=True).returncode == 0:
                subprocess.Popen(cmd)
                return
    
    def _execute_plan(self, plan: dict, title: str):
        dialog = PlanExecutionDialog(self.window, plan, title, self.distro)
        dialog.present()


@register_module(
    id="networking_advanced",
    name="Advanced Networking",
    description="VPN, Active Directory, firewall, and advanced sharing",
    icon="network-server-symbolic",
    category=ModuleCategory.NETWORK,
    order=15
)
class NetworkingPage(Adw.NavigationPage):
    """Advanced networking tools page."""
    
    def __init__(self, window: 'LinuxToolkitWindow'):
        super().__init__(title="Advanced Networking")
        
        self.window = window
        self.distro = get_distro()
        
        # Managers
        self.samba = SambaManager()
        self.ad = ADManager()
        self.firewall = FirewallManager()
        self.scanner = NetworkScanner()
        
        self.build_ui()
    
    def build_ui(self):
        """Build the networking UI."""
        # Main container with header
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header (NavigationView handles back button automatically)
        header = Adw.HeaderBar()
        
        # Refresh button
        refresh_btn = Gtk.Button()
        refresh_btn.set_icon_name("view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh status")
        refresh_btn.connect("clicked", self.on_refresh)
        header.pack_end(refresh_btn)
        
        toolbar_view.add_top_bar(header)
        
        # Scrollable content
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled.set_vexpand(True)
        toolbar_view.set_content(self.scrolled)
        
        # Build the content
        self._build_content()
    
    def _build_content(self):
        """Build/rebuild the scrollable content."""
        # Content
        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_margin_top(20)
        clamp.set_margin_bottom(20)
        clamp.set_margin_start(20)
        clamp.set_margin_end(20)
        self.scrolled.set_child(clamp)
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        clamp.set_child(content_box)
        
        # Status banner
        content_box.append(self._create_status_banner())
        
        # Samba section (Quick Share first for easy access)
        content_box.append(self._create_samba_section())
        
        # Network Discovery section
        content_box.append(self._create_discovery_section())
        
        # Active Directory section
        content_box.append(self._create_ad_section())
        
        # Firewall section
        content_box.append(self._create_firewall_section())
        
        # WiFi section
        content_box.append(self._create_wifi_section())
        
        # VPN section
        content_box.append(self._create_vpn_section())
        
        # Tools section (Hotspot, Speed Test, etc.)
        content_box.append(self._create_network_tools_section())
    
    def on_refresh(self, button):
        """Refresh the status by rebuilding content."""
        self._build_content()
        self.window.show_toast("Status refreshed")
    
    def _create_status_banner(self) -> Gtk.Widget:
        """Create status info banner."""
        group = Adw.PreferencesGroup()
        group.set_title("Network Status")
        
        # Local IP
        ip_row = Adw.ActionRow()
        ip_row.set_title("Local IP Address")
        ip_row.set_subtitle(get_local_ip())
        ip_row.add_prefix(Gtk.Image.new_from_icon_name("network-wired-symbolic"))
        group.add(ip_row)
        
        # Hostname
        host_row = Adw.ActionRow()
        host_row.set_title("Hostname")
        host_row.set_subtitle(get_hostname())
        host_row.add_prefix(Gtk.Image.new_from_icon_name("computer-symbolic"))
        group.add(host_row)
        
        # Samba status
        samba_row = Adw.ActionRow()
        samba_row.set_title("Samba Server")
        if self.samba.is_installed():
            if self.samba.is_running():
                samba_row.set_subtitle(f"Running (Workgroup: {self.samba.get_workgroup()})")
                status_icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
                status_icon.add_css_class("success")
            else:
                samba_row.set_subtitle("Installed but not running")
                status_icon = Gtk.Image.new_from_icon_name("emblem-important-symbolic")
                status_icon.add_css_class("warning")
        else:
            samba_row.set_subtitle("Not installed")
            status_icon = Gtk.Image.new_from_icon_name("emblem-important-symbolic")
        samba_row.add_prefix(Gtk.Image.new_from_icon_name("network-server-symbolic"))
        samba_row.add_suffix(status_icon)
        group.add(samba_row)
        
        # Domain status
        joined, domain = self.ad.is_domain_joined()
        domain_row = Adw.ActionRow()
        domain_row.set_title("Active Directory")
        if joined:
            domain_row.set_subtitle(f"Joined to {domain}")
            status_icon = Gtk.Image.new_from_icon_name("emblem-ok-symbolic")
            status_icon.add_css_class("success")
        else:
            domain_row.set_subtitle("Not joined to a domain")
            status_icon = Gtk.Image.new_from_icon_name("list-remove-symbolic")
        domain_row.add_prefix(Gtk.Image.new_from_icon_name("system-users-symbolic"))
        domain_row.add_suffix(status_icon)
        group.add(domain_row)
        
        # Firewall status
        fw_active, fw_backend = self.firewall.get_status()
        fw_row = Adw.ActionRow()
        fw_row.set_title("Firewall")
        if fw_active:
            fw_row.set_subtitle(f"Active ({fw_backend})")
            status_icon = Gtk.Image.new_from_icon_name("security-high-symbolic")
            status_icon.add_css_class("success")
        else:
            fw_row.set_subtitle("Not active or not installed")
            status_icon = Gtk.Image.new_from_icon_name("security-low-symbolic")
            status_icon.add_css_class("warning")
        fw_row.add_prefix(Gtk.Image.new_from_icon_name("preferences-system-firewall-symbolic"))
        fw_row.add_suffix(status_icon)
        group.add(fw_row)
        
        return group
    
    def _create_discovery_section(self) -> Gtk.Widget:
        """Create network discovery section."""
        group = Adw.PreferencesGroup()
        group.set_title("Network Discovery")
        group.set_description("Find shared folders and devices on your network")
        
        # Quick scan (SMB only) - DEFAULT
        quick_row = Adw.ActionRow()
        quick_row.set_title("Find Shared Folders")
        quick_row.set_subtitle("Quick scan for SMB/Windows shares (recommended)")
        quick_row.set_activatable(True)
        quick_row.add_prefix(Gtk.Image.new_from_icon_name("folder-remote-symbolic"))
        quick_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        quick_row.connect("activated", self.on_quick_scan)
        group.add(quick_row)
        
        # Full network scan
        full_row = Adw.ActionRow()
        full_row.set_title("Full Network Scan")
        full_row.set_subtitle("Find all devices on network (slower)")
        full_row.set_activatable(True)
        full_row.add_prefix(Gtk.Image.new_from_icon_name("network-workgroup-symbolic"))
        full_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        full_row.connect("activated", self.on_full_scan)
        group.add(full_row)
        
        # Browse network (opens file manager)
        browse_row = Adw.ActionRow()
        browse_row.set_title("Browse Network")
        browse_row.set_subtitle("Open network location in file manager")
        browse_row.set_activatable(True)
        browse_row.add_prefix(Gtk.Image.new_from_icon_name("system-file-manager-symbolic"))
        browse_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        browse_row.connect("activated", self.on_browse_network)
        group.add(browse_row)
        
        return group
    
    def _create_samba_section(self) -> Gtk.Widget:
        """Create Samba configuration section."""
        group = Adw.PreferencesGroup()
        group.set_title("File Sharing (Samba)")
        group.set_description("Share folders with Windows and other devices")
        
        if not self.samba.is_installed():
            # Install Samba
            install_row = Adw.ActionRow()
            install_row.set_title("Install Samba Server")
            install_row.set_subtitle("Set up file sharing on this computer")
            install_row.set_activatable(True)
            install_row.add_prefix(Gtk.Image.new_from_icon_name("system-software-install-symbolic"))
            install_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            install_row.connect("activated", self.on_install_samba)
            group.add(install_row)
        else:
            # Quick share
            quick_row = Adw.ActionRow()
            quick_row.set_title("Quick Share")
            quick_row.set_subtitle("Quickly share a folder on the network")
            quick_row.set_activatable(True)
            quick_row.add_prefix(Gtk.Image.new_from_icon_name("folder-new-symbolic"))
            quick_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            quick_row.connect("activated", self.on_quick_share)
            group.add(quick_row)
            
            # Manage shares
            manage_row = Adw.ActionRow()
            manage_row.set_title("Manage Shares")
            shares = self.samba.get_shares()
            manage_row.set_subtitle(f"{len(shares)} share(s) configured")
            manage_row.set_activatable(True)
            manage_row.add_prefix(Gtk.Image.new_from_icon_name("folder-symbolic"))
            manage_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            manage_row.connect("activated", self.on_manage_shares)
            group.add(manage_row)
            
            # Add Samba user
            user_row = Adw.ActionRow()
            user_row.set_title("Samba Users")
            user_row.set_subtitle("Manage Samba user accounts")
            user_row.set_activatable(True)
            user_row.add_prefix(Gtk.Image.new_from_icon_name("system-users-symbolic"))
            user_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            user_row.connect("activated", self.on_samba_users)
            group.add(user_row)
        
        return group
    
    def _create_ad_section(self) -> Gtk.Widget:
        """Create Active Directory section."""
        group = Adw.PreferencesGroup()
        group.set_title("Active Directory")
        group.set_description("Join Windows domains and use AD authentication")
        
        joined, domain = self.ad.is_domain_joined()
        
        if joined:
            # Show domain info
            info_row = Adw.ActionRow()
            info_row.set_title(f"Joined to {domain}")
            info_row.set_subtitle("Domain users can log in to this system")
            info_row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
            group.add(info_row)
            
            # Leave domain
            leave_row = Adw.ActionRow()
            leave_row.set_title("Leave Domain")
            leave_row.set_subtitle("Disconnect from Active Directory")
            leave_row.set_activatable(True)
            leave_row.add_prefix(Gtk.Image.new_from_icon_name("list-remove-symbolic"))
            leave_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            leave_row.connect("activated", self.on_leave_domain)
            group.add(leave_row)
        else:
            # Join domain
            join_row = Adw.ActionRow()
            join_row.set_title("Join Domain")
            join_row.set_subtitle("Connect to an Active Directory domain")
            join_row.set_activatable(True)
            join_row.add_prefix(Gtk.Image.new_from_icon_name("list-add-symbolic"))
            join_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            join_row.connect("activated", self.on_join_domain)
            group.add(join_row)
        
        return group
    
    def _create_firewall_section(self) -> Gtk.Widget:
        """Create firewall management section."""
        group = Adw.PreferencesGroup()
        group.set_title("Firewall")
        group.set_description("Manage network access rules")
        
        fw_active, fw_backend = self.firewall.get_status()
        
        if not fw_active:
            # No firewall
            info_row = Adw.ActionRow()
            info_row.set_title("No Active Firewall")
            info_row.set_subtitle("Consider enabling firewalld or ufw for security")
            info_row.add_prefix(Gtk.Image.new_from_icon_name("dialog-warning-symbolic"))
            group.add(info_row)
        else:
            # Open ports
            ports_row = Adw.ActionRow()
            ports_row.set_title("Open Ports")
            open_ports = self.firewall.get_open_ports()
            ports_row.set_subtitle(f"{len(open_ports)} port(s)/service(s) open")
            ports_row.set_activatable(True)
            ports_row.add_prefix(Gtk.Image.new_from_icon_name("network-transmit-receive-symbolic"))
            ports_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            ports_row.connect("activated", self.on_manage_ports)
            group.add(ports_row)
            
            # Quick open common services
            quick_row = Adw.ActionRow()
            quick_row.set_title("Quick Open Service")
            quick_row.set_subtitle("Open ports for common services")
            quick_row.set_activatable(True)
            quick_row.add_prefix(Gtk.Image.new_from_icon_name("list-add-symbolic"))
            quick_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            quick_row.connect("activated", self.on_quick_open_port)
            group.add(quick_row)
        
        return group
    
    def _create_wifi_section(self) -> Gtk.Widget:
        """Create WiFi management section."""
        group = Adw.PreferencesGroup()
        group.set_title("WiFi")
        group.set_description("Wireless network management")
        
        # Check if nmcli is available
        has_nmcli = subprocess.run(['which', 'nmcli'], capture_output=True).returncode == 0
        
        if not has_nmcli:
            info_row = Adw.ActionRow()
            info_row.set_title("NetworkManager Not Found")
            info_row.set_subtitle("WiFi management requires NetworkManager")
            info_row.add_prefix(Gtk.Image.new_from_icon_name("dialog-warning-symbolic"))
            group.add(info_row)
            return group
        
        # Current WiFi status
        wifi_status = self._get_wifi_status()
        
        status_row = Adw.ActionRow()
        status_row.set_title("WiFi Status")
        if wifi_status['enabled']:
            if wifi_status['connected']:
                status_row.set_subtitle(f"Connected to {wifi_status['ssid']}")
                status_row.add_prefix(Gtk.Image.new_from_icon_name("network-wireless-signal-excellent-symbolic"))
            else:
                status_row.set_subtitle("Enabled but not connected")
                status_row.add_prefix(Gtk.Image.new_from_icon_name("network-wireless-offline-symbolic"))
        else:
            status_row.set_subtitle("WiFi is disabled")
            status_row.add_prefix(Gtk.Image.new_from_icon_name("network-wireless-disabled-symbolic"))
        group.add(status_row)
        
        # WiFi settings link
        settings_row = Adw.ActionRow()
        settings_row.set_title("WiFi Settings")
        settings_row.set_subtitle("Connect to networks, manage saved connections")
        settings_row.add_prefix(Gtk.Image.new_from_icon_name("preferences-system-network-symbolic"))
        settings_row.set_activatable(True)
        settings_row.connect("activated", self._on_open_wifi_settings)
        settings_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        group.add(settings_row)
        
        # Connect to hidden network
        hidden_row = Adw.ActionRow()
        hidden_row.set_title("Connect to Hidden Network")
        hidden_row.set_subtitle("Join a network that doesn't broadcast its name")
        hidden_row.add_prefix(Gtk.Image.new_from_icon_name("network-wireless-acquiring-symbolic"))
        hidden_row.set_activatable(True)
        hidden_row.connect("activated", self._on_connect_hidden_network)
        hidden_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        group.add(hidden_row)
        
        return group
    
    def _create_vpn_section(self) -> Gtk.Widget:
        """Create VPN section."""
        group = Adw.PreferencesGroup()
        group.set_title("VPN")
        group.set_description("Virtual Private Network connections")
        
        # Check for VPN tools
        has_nmcli = subprocess.run(['which', 'nmcli'], capture_output=True).returncode == 0
        
        # Current VPN status
        vpn_connected = False
        vpn_name = ""
        if has_nmcli:
            try:
                result = subprocess.run(
                    ['nmcli', '-t', '-f', 'TYPE,NAME,STATE', 'connection', 'show', '--active'],
                    capture_output=True, text=True
                )
                for line in result.stdout.strip().split('\n'):
                    if line and 'vpn' in line.lower():
                        parts = line.split(':')
                        if len(parts) >= 2:
                            vpn_connected = True
                            vpn_name = parts[1]
                            break
            except Exception:
                pass
        
        # Status row
        status_row = Adw.ActionRow()
        status_row.set_title("VPN Status")
        if vpn_connected:
            status_row.set_subtitle(f"Connected: {vpn_name}")
            status_row.add_prefix(Gtk.Image.new_from_icon_name("network-vpn-symbolic"))
        else:
            status_row.set_subtitle("Not connected")
            status_row.add_prefix(Gtk.Image.new_from_icon_name("network-vpn-disconnected-symbolic"))
        group.add(status_row)
        
        # Import OpenVPN config
        openvpn_row = Adw.ActionRow()
        openvpn_row.set_title("Import OpenVPN Config")
        openvpn_row.set_subtitle("Import a .ovpn configuration file")
        openvpn_row.add_prefix(Gtk.Image.new_from_icon_name("document-open-symbolic"))
        openvpn_row.set_activatable(True)
        openvpn_row.connect("activated", self._on_import_openvpn)
        openvpn_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        group.add(openvpn_row)
        
        # Import WireGuard config
        wireguard_row = Adw.ActionRow()
        wireguard_row.set_title("Import WireGuard Config")
        wireguard_row.set_subtitle("Import a .conf WireGuard configuration")
        wireguard_row.add_prefix(Gtk.Image.new_from_icon_name("document-open-symbolic"))
        wireguard_row.set_activatable(True)
        wireguard_row.connect("activated", self._on_import_wireguard)
        wireguard_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        group.add(wireguard_row)
        
        # VPN settings
        settings_row = Adw.ActionRow()
        settings_row.set_title("VPN Settings")
        settings_row.set_subtitle("Manage VPN connections")
        settings_row.add_prefix(Gtk.Image.new_from_icon_name("preferences-system-network-symbolic"))
        settings_row.set_activatable(True)
        settings_row.connect("activated", self._on_open_vpn_settings)
        settings_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        group.add(settings_row)
        
        return group
    
    def _create_network_tools_section(self) -> Gtk.Widget:
        """Create network tools section."""
        group = Adw.PreferencesGroup()
        group.set_title("Network Tools")
        group.set_description("Utilities for network management")
        
        # WiFi Hotspot
        hotspot_row = Adw.ActionRow()
        hotspot_row.set_title("Create WiFi Hotspot")
        hotspot_row.set_subtitle("Share your internet connection wirelessly")
        hotspot_row.add_prefix(Gtk.Image.new_from_icon_name("network-wireless-hotspot-symbolic"))
        hotspot_row.set_activatable(True)
        hotspot_row.connect("activated", self._on_create_hotspot)
        hotspot_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        group.add(hotspot_row)
        
        # Speed test
        speed_row = Adw.ActionRow()
        speed_row.set_title("Speed Test")
        speed_row.set_subtitle("Test your internet connection speed")
        speed_row.add_prefix(Gtk.Image.new_from_icon_name("utilities-system-monitor-symbolic"))
        speed_row.set_activatable(True)
        speed_row.connect("activated", self._on_run_speedtest)
        speed_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        group.add(speed_row)
        
        # Hosts file editor
        hosts_row = Adw.ActionRow()
        hosts_row.set_title("Edit Hosts File")
        hosts_row.set_subtitle("Manage local hostname mappings")
        hosts_row.add_prefix(Gtk.Image.new_from_icon_name("text-x-generic-symbolic"))
        hosts_row.set_activatable(True)
        hosts_row.connect("activated", self._on_edit_hosts)
        hosts_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        group.add(hosts_row)
        
        # Network settings
        settings_row = Adw.ActionRow()
        settings_row.set_title("Network Settings")
        settings_row.set_subtitle("Open system network configuration")
        settings_row.add_prefix(Gtk.Image.new_from_icon_name("preferences-system-network-symbolic"))
        settings_row.set_activatable(True)
        settings_row.connect("activated", self._on_open_network_settings)
        settings_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        group.add(settings_row)
        
        return group
    
    def _get_wifi_status(self) -> dict:
        """Get current WiFi status."""
        status = {'enabled': False, 'connected': False, 'ssid': ''}
        
        try:
            # Check if WiFi is enabled
            result = subprocess.run(
                ['nmcli', 'radio', 'wifi'],
                capture_output=True, text=True
            )
            status['enabled'] = result.stdout.strip() == 'enabled'
            
            if status['enabled']:
                # Check if connected
                result = subprocess.run(
                    ['nmcli', '-t', '-f', 'ACTIVE,SSID', 'dev', 'wifi'],
                    capture_output=True, text=True
                )
                for line in result.stdout.strip().split('\n'):
                    if line.startswith('yes:'):
                        status['connected'] = True
                        status['ssid'] = line.split(':', 1)[1] if ':' in line else ''
                        break
        except Exception:
            pass
        
        return status
    
    # -------------------------------------------------------------------------
    # Event Handlers
    # -------------------------------------------------------------------------
    
    def on_quick_scan(self, row):
        """Start quick SMB scan."""
        page = NetworkScanPage(self.window, self.scanner, ScanType.QUICK)
        self.window.navigation_view.push(page)
    
    def on_full_scan(self, row):
        """Start full network scan."""
        page = NetworkScanPage(self.window, self.scanner, ScanType.FULL)
        self.window.navigation_view.push(page)
    
    def on_browse_network(self, row):
        """Open network location in file manager."""
        subprocess.Popen(['xdg-open', 'smb://'])
    
    def on_install_samba(self, row):
        """Install Samba server."""
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Install Samba Server",
            body="This will install Samba and enable file sharing.\n\nPackages: " + 
                 ", ".join(self.samba.get_samba_packages())
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("install", "Install")
        dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_install_samba_response)
        dialog.present()
    
    def _on_install_samba_response(self, dialog, response):
        """Handle Samba install response."""
        if response == "install":
            plan = self.samba.create_install_plan()
            self._execute_plan(plan, "Installing Samba")
    
    def on_quick_share(self, row):
        """Show quick share dialog."""
        dialog = QuickShareDialog(self.window, self.samba, self._execute_plan)
        dialog.present()
    
    def on_manage_shares(self, row):
        """Show share management page."""
        page = ManageSharesPage(self.window, self.samba, self._execute_plan)
        self.window.navigation_view.push(page)
    
    def on_samba_users(self, row):
        """Show Samba user management."""
        dialog = SambaUserDialog(self.window)
        dialog.present()
    
    def on_join_domain(self, row):
        """Show domain join dialog."""
        dialog = DomainJoinDialog(self.window, self.ad, self._execute_plan)
        dialog.present()
    
    def on_leave_domain(self, row):
        """Leave the current domain."""
        joined, domain = self.ad.is_domain_joined()
        
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Leave Domain",
            body=f"Are you sure you want to leave {domain}?\n\n"
                 "Domain users will no longer be able to log in."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("leave", "Leave Domain")
        dialog.set_response_appearance("leave", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_leave_domain_response, domain)
        dialog.present()
    
    def _on_leave_domain_response(self, dialog, response, domain):
        """Handle leave domain response."""
        if response == "leave":
            # Show a clear "not implemented" message instead of a TODO
            message = (
                "Leaving an Active Directory domain from Tux Assistant is "
                "not yet implemented.\n\n"
                "For now, please use your distribution's domain tools to "
                "leave the domain:\n\n"
                "• Arch: realm leave\n"
                "• Fedora/RHEL: realm leave or adcli delete-computer\n"
                "• Debian/Ubuntu: realm leave\n"
                "• OpenSUSE: yast2 auth-client"
            )
            dlg = Adw.MessageDialog(
                transient_for=self.window,
                heading="Leave Domain",
                body=message
            )
            dlg.add_response("ok", "OK")
            dlg.set_default_response("ok")
            dlg.present()
    
    def on_manage_ports(self, row):
        """Show port management page."""
        page = FirewallPage(self.window, self.firewall)
        self.window.navigation_view.push(page)
    
    def on_quick_open_port(self, row):
        """Show quick open port dialog."""
        dialog = QuickOpenPortDialog(self.window, self.firewall, self._execute_plan)
        dialog.present()
    
    # -------------------------------------------------------------------------
    # WiFi, VPN, and Tools Handlers
    # -------------------------------------------------------------------------
    
    def _on_open_wifi_settings(self, row):
        """Open system WiFi settings."""
        tools = [
            ['gnome-control-center', 'wifi'],
            ['nm-connection-editor'],
            ['systemsettings', 'kcm_networkmanagement'],
            ['connman-gtk'],
        ]
        
        for tool in tools:
            try:
                result = subprocess.run(['which', tool[0]], capture_output=True)
                if result.returncode == 0:
                    subprocess.Popen(tool)
                    return
            except Exception:
                continue
        
        self.window.show_toast("Could not open WiFi settings")
    
    def _on_connect_hidden_network(self, row):
        """Show dialog to connect to hidden network."""
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Connect to Hidden Network",
            body="Enter the network name (SSID) and password."
        )
        
        # Add entry fields
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        
        ssid_group = Adw.PreferencesGroup()
        ssid_entry = Adw.EntryRow()
        ssid_entry.set_title("Network Name (SSID)")
        ssid_group.add(ssid_entry)
        content.append(ssid_group)
        
        pass_group = Adw.PreferencesGroup()
        pass_entry = Adw.PasswordEntryRow()
        pass_entry.set_title("Password")
        pass_group.add(pass_entry)
        content.append(pass_group)
        
        dialog.set_extra_child(content)
        
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("connect", "Connect")
        dialog.set_response_appearance("connect", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_hidden_network_response, ssid_entry, pass_entry)
        dialog.present()
    
    def _on_hidden_network_response(self, dialog, response, ssid_entry, pass_entry):
        """Handle hidden network connection."""
        if response != "connect":
            return
        
        ssid = ssid_entry.get_text().strip()
        password = pass_entry.get_text()
        
        if not ssid:
            self.window.show_toast("Please enter a network name")
            return
        
        # Use nmcli to connect
        try:
            cmd = ['nmcli', 'device', 'wifi', 'connect', ssid, 'password', password, 'hidden', 'yes']
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.window.show_toast(f"Connected to {ssid}")
            else:
                self.window.show_toast(f"Failed to connect: {result.stderr.strip()}")
        except Exception as e:
            self.window.show_toast(f"Error: {str(e)}")
    
    def _on_import_openvpn(self, row):
        """Import OpenVPN configuration file."""
        # Check if OpenVPN plugin is installed
        has_plugin = subprocess.run(
            ['which', 'nmcli'], capture_output=True
        ).returncode == 0
        
        if not has_plugin:
            self.window.show_toast("NetworkManager OpenVPN plugin required")
            return
        
        dialog = Gtk.FileDialog()
        dialog.set_title("Select OpenVPN Configuration")
        
        # Filter for .ovpn files
        filter_ovpn = Gtk.FileFilter()
        filter_ovpn.set_name("OpenVPN files (*.ovpn)")
        filter_ovpn.add_pattern("*.ovpn")
        
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_ovpn)
        dialog.set_filters(filters)
        
        dialog.open(self.window, None, self._on_openvpn_file_selected)
    
    def _on_openvpn_file_selected(self, dialog, result):
        """Handle OpenVPN file selection."""
        try:
            file = dialog.open_finish(result)
            if file:
                path = file.get_path()
                
                # Import using nmcli
                result = subprocess.run(
                    ['nmcli', 'connection', 'import', 'type', 'openvpn', 'file', path],
                    capture_output=True, text=True
                )
                
                if result.returncode == 0:
                    self.window.show_toast("OpenVPN config imported successfully")
                else:
                    # Check if plugin is missing
                    if 'plugin' in result.stderr.lower():
                        self._offer_install_openvpn_plugin()
                    else:
                        self.window.show_toast(f"Import failed: {result.stderr.strip()}")
        except Exception:
            pass
    
    def _offer_install_openvpn_plugin(self):
        """Offer to install OpenVPN NetworkManager plugin."""
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="OpenVPN Plugin Required",
            body="The NetworkManager OpenVPN plugin is needed to import this configuration."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("install", "Install Plugin")
        dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_install_openvpn_plugin)
        dialog.present()
    
    def _on_install_openvpn_plugin(self, dialog, response):
        """Install OpenVPN plugin."""
        if response != "install":
            return
        
        packages = {
            DistroFamily.ARCH: "networkmanager-openvpn",
            DistroFamily.DEBIAN: "network-manager-openvpn-gnome",
            DistroFamily.FEDORA: "NetworkManager-openvpn-gnome",
            DistroFamily.OPENSUSE: "NetworkManager-openvpn",
        }
        
        pkg = packages.get(self.distro.family, "")
        if not pkg:
            self.window.show_toast("Package not found for your distribution")
            return
        
        plan = {
            "tasks": [
                {"type": "install", "name": "Install OpenVPN Plugin", "packages": [pkg]}
            ]
        }
        self._execute_plan(plan, "Installing OpenVPN Plugin")
    
    def _on_import_wireguard(self, row):
        """Import WireGuard configuration file."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Select WireGuard Configuration")
        
        # Filter for .conf files
        filter_conf = Gtk.FileFilter()
        filter_conf.set_name("WireGuard files (*.conf)")
        filter_conf.add_pattern("*.conf")
        
        filters = Gio.ListStore.new(Gtk.FileFilter)
        filters.append(filter_conf)
        dialog.set_filters(filters)
        
        dialog.open(self.window, None, self._on_wireguard_file_selected)
    
    def _on_wireguard_file_selected(self, dialog, result):
        """Handle WireGuard file selection."""
        try:
            file = dialog.open_finish(result)
            if file:
                path = file.get_path()
                
                # Import using nmcli
                result = subprocess.run(
                    ['nmcli', 'connection', 'import', 'type', 'wireguard', 'file', path],
                    capture_output=True, text=True
                )
                
                if result.returncode == 0:
                    self.window.show_toast("WireGuard config imported successfully")
                else:
                    if 'plugin' in result.stderr.lower() or 'wireguard' in result.stderr.lower():
                        self._offer_install_wireguard()
                    else:
                        self.window.show_toast(f"Import failed: {result.stderr.strip()}")
        except Exception:
            pass
    
    def _offer_install_wireguard(self):
        """Offer to install WireGuard."""
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="WireGuard Required",
            body="WireGuard tools are needed to use this configuration."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("install", "Install WireGuard")
        dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_install_wireguard)
        dialog.present()
    
    def _on_install_wireguard(self, dialog, response):
        """Install WireGuard."""
        if response != "install":
            return
        
        packages = {
            DistroFamily.ARCH: "wireguard-tools",
            DistroFamily.DEBIAN: "wireguard",
            DistroFamily.FEDORA: "wireguard-tools",
            DistroFamily.OPENSUSE: "wireguard-tools",
        }
        
        pkg = packages.get(self.distro.family, "wireguard-tools")
        
        plan = {
            "tasks": [
                {"type": "install", "name": "Install WireGuard", "packages": [pkg]}
            ]
        }
        self._execute_plan(plan, "Installing WireGuard")
    
    def _on_open_vpn_settings(self, row):
        """Open VPN settings."""
        tools = [
            ['gnome-control-center', 'network'],
            ['nm-connection-editor'],
            ['systemsettings', 'kcm_networkmanagement'],
        ]
        
        for tool in tools:
            try:
                result = subprocess.run(['which', tool[0]], capture_output=True)
                if result.returncode == 0:
                    subprocess.Popen(tool)
                    return
            except Exception:
                continue
        
        self.window.show_toast("Could not open VPN settings")
    
    def _on_create_hotspot(self, row):
        """Create WiFi hotspot."""
        # Check if already running a hotspot
        try:
            result = subprocess.run(
                ['nmcli', '-t', '-f', 'NAME,TYPE', 'connection', 'show', '--active'],
                capture_output=True, text=True
            )
            for line in result.stdout.strip().split('\n'):
                if 'Hotspot' in line:
                    # Hotspot is running, offer to stop
                    dialog = Adw.MessageDialog(
                        transient_for=self.window,
                        heading="Hotspot Active",
                        body="A WiFi hotspot is currently running. Would you like to stop it?"
                    )
                    dialog.add_response("cancel", "Cancel")
                    dialog.add_response("stop", "Stop Hotspot")
                    dialog.set_response_appearance("stop", Adw.ResponseAppearance.DESTRUCTIVE)
                    dialog.connect("response", self._on_stop_hotspot)
                    dialog.present()
                    return
        except Exception:
            pass
        
        # Show hotspot creation dialog
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Create WiFi Hotspot",
            body="Share your internet connection wirelessly."
        )
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        content.set_margin_top(12)
        content.set_margin_bottom(12)
        content.set_margin_start(12)
        content.set_margin_end(12)
        
        name_group = Adw.PreferencesGroup()
        name_entry = Adw.EntryRow()
        name_entry.set_title("Hotspot Name")
        name_entry.set_text(f"{os.uname().nodename}-hotspot")
        name_group.add(name_entry)
        content.append(name_group)
        
        pass_group = Adw.PreferencesGroup()
        pass_entry = Adw.PasswordEntryRow()
        pass_entry.set_title("Password (min 8 characters)")
        pass_group.add(pass_entry)
        content.append(pass_group)
        
        dialog.set_extra_child(content)
        
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("create", "Create Hotspot")
        dialog.set_response_appearance("create", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_create_hotspot_response, name_entry, pass_entry)
        dialog.present()
    
    def _on_create_hotspot_response(self, dialog, response, name_entry, pass_entry):
        """Handle hotspot creation."""
        if response != "create":
            return
        
        name = name_entry.get_text().strip()
        password = pass_entry.get_text()
        
        if not name:
            self.window.show_toast("Please enter a hotspot name")
            return
        
        if len(password) < 8:
            self.window.show_toast("Password must be at least 8 characters")
            return
        
        # Create hotspot using nmcli
        try:
            result = subprocess.run(
                ['nmcli', 'device', 'wifi', 'hotspot', 'ssid', name, 'password', password],
                capture_output=True, text=True
            )
            
            if result.returncode == 0:
                self.window.show_toast(f"Hotspot '{name}' created!")
            else:
                self.window.show_toast(f"Failed: {result.stderr.strip()}")
        except Exception as e:
            self.window.show_toast(f"Error: {str(e)}")
    
    def _on_stop_hotspot(self, dialog, response):
        """Stop the hotspot."""
        if response != "stop":
            return
        
        try:
            subprocess.run(['nmcli', 'connection', 'down', 'Hotspot'], capture_output=True)
            self.window.show_toast("Hotspot stopped")
        except Exception:
            self.window.show_toast("Could not stop hotspot")
    
    def _on_run_speedtest(self, row):
        """Run internet speed test."""
        # Check if speedtest-cli is installed
        has_speedtest = subprocess.run(['which', 'speedtest-cli'], capture_output=True).returncode == 0
        
        if not has_speedtest:
            dialog = Adw.MessageDialog(
                transient_for=self.window,
                heading="Speed Test Tool Required",
                body="speedtest-cli is needed to run speed tests."
            )
            dialog.add_response("cancel", "Cancel")
            dialog.add_response("install", "Install speedtest-cli")
            dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
            dialog.connect("response", self._on_install_speedtest)
            dialog.present()
            return
        
        # Run speed test in terminal
        script = '''echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Internet Speed Test"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
speedtest-cli
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Press Enter to close..."
read'''
        
        self._run_in_terminal(script)
    
    def _on_install_speedtest(self, dialog, response):
        """Install speedtest-cli."""
        if response != "install":
            return
        
        packages = {
            DistroFamily.ARCH: "speedtest-cli",
            DistroFamily.DEBIAN: "speedtest-cli",
            DistroFamily.FEDORA: "speedtest-cli",
            DistroFamily.OPENSUSE: "speedtest-cli",
        }
        
        pkg = packages.get(self.distro.family, "speedtest-cli")
        
        plan = {
            "tasks": [
                {"type": "install", "name": "Install speedtest-cli", "packages": [pkg]}
            ]
        }
        self._execute_plan(plan, "Installing Speed Test")
    
    def _on_edit_hosts(self, row):
        """Edit the hosts file."""
        # Try to open with a graphical editor
        editors = [
            ['pkexec', 'gedit', '/etc/hosts'],
            ['pkexec', 'kate', '/etc/hosts'],
            ['pkexec', 'xed', '/etc/hosts'],
            ['pkexec', 'mousepad', '/etc/hosts'],
            ['pkexec', 'nano', '/etc/hosts'],  # Will need terminal
        ]
        
        for editor in editors[:-1]:  # Skip nano for now
            try:
                if subprocess.run(['which', editor[1]], capture_output=True).returncode == 0:
                    subprocess.Popen(editor)
                    return
            except Exception:
                continue
        
        # Fallback to terminal with nano
        script = '''echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  Editing /etc/hosts"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Use Ctrl+O to save, Ctrl+X to exit"
echo ""
sudo nano /etc/hosts'''
        
        self._run_in_terminal(script)
    
    def _on_open_network_settings(self, row):
        """Open system network settings."""
        tools = [
            ['gnome-control-center', 'network'],
            ['nm-connection-editor'],
            ['systemsettings', 'kcm_networkmanagement'],
            ['connman-gtk'],
        ]
        
        for tool in tools:
            try:
                result = subprocess.run(['which', tool[0]], capture_output=True)
                if result.returncode == 0:
                    subprocess.Popen(tool)
                    return
            except Exception:
                continue
        
        self.window.show_toast("Could not open network settings")
    
    def _run_in_terminal(self, script: str):
        """Run a script in a terminal window."""
        terminals = [
            ('konsole', ['konsole', '-e', 'bash', '-c', script]),
            ('gnome-terminal', ['gnome-terminal', '--', 'bash', '-c', script]),
            ('xfce4-terminal', ['xfce4-terminal', '-e', f'bash -c \'{script}\'']),
            ('tilix', ['tilix', '-e', f'bash -c "{script}"']),
            ('alacritty', ['alacritty', '-e', 'bash', '-c', script]),
            ('kitty', ['kitty', 'bash', '-c', script]),
        ]
        
        for term_name, term_cmd in terminals:
            try:
                if subprocess.run(['which', term_name], capture_output=True).returncode == 0:
                    subprocess.Popen(term_cmd)
                    return
            except Exception:
                continue
        
        self.window.show_toast("Could not find terminal emulator")
    
    def _execute_plan(self, plan: dict, title: str):
        """Execute a plan using tux-helper."""
        dialog = PlanExecutionDialog(self.window, plan, title, self.distro)
        dialog.present()


# =============================================================================
# Sub-pages and Dialogs
# =============================================================================

class NetworkScanPage(Adw.NavigationPage):
    """Page showing network scan results."""
    
    def __init__(self, window, scanner: NetworkScanner, scan_type: ScanType):
        title = "Find Shared Folders" if scan_type == ScanType.QUICK else "Network Scan"
        super().__init__(title=title)
        
        self.window = window
        self.scanner = scanner
        self.scan_type = scan_type
        self.hosts = []
        
        self.build_ui()
        GLib.timeout_add(100, self.start_scan)
    
    def build_ui(self):
        """Build the scan UI."""
        import time
        self.scan_start_time = time.time()
        
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        toolbar_view.add_top_bar(header)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        toolbar_view.set_content(scrolled)
        
        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_margin_top(20)
        clamp.set_margin_bottom(20)
        clamp.set_margin_start(20)
        clamp.set_margin_end(20)
        scrolled.set_child(clamp)
        
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        clamp.set_child(self.content_box)
        
        # Scan type indicator
        type_label = Gtk.Label()
        if self.scan_type == ScanType.QUICK:
            type_label.set_markup("<small>Quick Scan: Finding devices with shared folders</small>")
        else:
            type_label.set_markup("<small>Full Scan: Finding all network devices</small>")
        type_label.add_css_class("dim-label")
        type_label.set_halign(Gtk.Align.START)
        self.content_box.append(type_label)
        
        # Progress section
        progress_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        progress_box.set_valign(Gtk.Align.CENTER)
        self.content_box.append(progress_box)
        
        # Spinner and status in a row
        spinner_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        spinner_row.set_halign(Gtk.Align.CENTER)
        progress_box.append(spinner_row)
        
        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(32, 32)
        self.spinner.start()
        spinner_row.append(self.spinner)
        
        # Status label
        self.status_label = Gtk.Label(label="Starting scan...")
        self.status_label.add_css_class("title-4")
        spinner_row.append(self.status_label)
        
        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        self.progress_bar.set_margin_top(10)
        self.progress_bar.set_margin_start(40)
        self.progress_bar.set_margin_end(40)
        progress_box.append(self.progress_bar)
        
        # Stats row: Elapsed | Addresses checked | Devices found | ETA
        self.stats_label = Gtk.Label()
        self.stats_label.set_markup("<small>Elapsed: 0:00 | Checked: 0 of 254 | Found: 0 devices</small>")
        self.stats_label.add_css_class("dim-label")
        self.stats_label.set_margin_top(5)
        progress_box.append(self.stats_label)
        
        # Patience message
        patience_label = Gtk.Label()
        patience_label.set_markup("<small><i>This may take several minutes. Please be patient!</i></small>")
        patience_label.add_css_class("dim-label")
        patience_label.set_margin_top(8)
        progress_box.append(patience_label)
        self.patience_label = patience_label
        
        # Fun facts widget - entertainment while scanning!
        self.fun_facts = RotatingFunFactWidget(rotation_interval=8000)
        self.fun_facts.set_margin_top(20)
        self.content_box.append(self.fun_facts)
        
        # Results group (hidden initially)
        self.results_group = Adw.PreferencesGroup()
        self.results_group.set_visible(False)
        self.content_box.append(self.results_group)
        
        # Track progress state
        self.last_progress_time = time.time()
        self.progress_times = []  # Track time per IP for ETA
    
    def start_scan(self):
        """Start the network scan."""
        thread = threading.Thread(target=self._do_scan, daemon=True)
        thread.start()
        return False
    
    def _do_scan(self):
        """Run the scan."""
        import time
        
        def update_status(msg):
            GLib.idle_add(self._update_status, msg)
        
        def update_progress(current, total, found, phase):
            GLib.idle_add(self._update_progress, current, total, found, phase)
        
        self.hosts = self.scanner.scan_for_shares(self.scan_type, update_status, update_progress)
        GLib.idle_add(self._show_results)
    
    def _update_status(self, message):
        """Update status label."""
        self.status_label.set_label(message)
    
    def _update_progress(self, current, total, found, phase):
        """Update progress bar and stats."""
        import time
        
        now = time.time()
        elapsed = now - self.scan_start_time
        
        # Calculate progress fraction
        if total > 0:
            fraction = current / total
            self.progress_bar.set_fraction(fraction)
            pct = int(fraction * 100)
            self.progress_bar.set_text(f"{pct}%")
        else:
            # Pulse if we don't know total
            self.progress_bar.pulse()
        
        # Track time per IP for ETA calculation
        if current > 0:
            time_since_last = now - self.last_progress_time
            self.progress_times.append(time_since_last)
            # Keep only last 20 samples for rolling average
            if len(self.progress_times) > 20:
                self.progress_times.pop(0)
        self.last_progress_time = now
        
        # Calculate ETA
        eta_str = ""
        if current > 0 and total > 0 and current < total:
            avg_time = sum(self.progress_times) / len(self.progress_times) if self.progress_times else 0
            remaining = total - current
            eta_seconds = remaining * avg_time
            if eta_seconds > 0:
                eta_min = int(eta_seconds // 60)
                eta_sec = int(eta_seconds % 60)
                eta_str = f" | ETA: ~{eta_min}:{eta_sec:02d}"
        
        # Format elapsed time
        elapsed_min = int(elapsed // 60)
        elapsed_sec = int(elapsed % 60)
        elapsed_str = f"{elapsed_min}:{elapsed_sec:02d}"
        
        # Phase-specific text
        if phase == "nmap":
            phase_text = "Running nmap scan"
        elif phase == "ping_sweep":
            phase_text = f"Checked: {current} of {total}"
        elif phase == "smb_scan":
            phase_text = f"Checked: {current} of {total}"
        elif phase == "shares":
            phase_text = f"Checking shares: {current} of {total}"
        else:
            phase_text = f"Checked: {current} of {total}"
        
        # Update stats label
        stats = f"<small>Elapsed: {elapsed_str} | {phase_text} | Found: {found} device(s){eta_str}</small>"
        self.stats_label.set_markup(stats)
    
    def _show_results(self):
        """Show scan results."""
        self.spinner.stop()
        self.spinner.set_visible(False)
        self.patience_label.set_visible(False)
        self.progress_bar.set_visible(False)
        self.stats_label.set_visible(False)
        
        # Stop and hide fun facts
        self.fun_facts.stop_rotation()
        self.fun_facts.set_visible(False)
        
        if not self.hosts:
            if self.scan_type == ScanType.QUICK:
                self.status_label.set_label("No shared folders found on the network")
            else:
                self.status_label.set_label("No devices found")
            return
        
        # Count hosts with shares
        hosts_with_shares = sum(1 for h in self.hosts if h.services)
        total_shares = sum(len(h.services) for h in self.hosts)
        
        if self.scan_type == ScanType.QUICK:
            self.status_label.set_label(f"Found {len(self.hosts)} device(s) with {total_shares} share(s)")
        else:
            self.status_label.set_label(f"Found {len(self.hosts)} device(s) ({hosts_with_shares} with shares)")
        
        # Sort: hosts with shares first, then by hostname
        self.hosts.sort(key=lambda h: (0 if h.services else 1, h.hostname.lower()))
        
        self.results_group.set_title("Devices Found")
        self.results_group.set_visible(True)
        
        for host in self.hosts:
            row = Adw.ActionRow()
            
            # Title: hostname or IP
            display_name = host.hostname if host.hostname and host.hostname != host.ip else host.ip
            row.set_title(display_name)
            
            # Subtitle: IP (and MAC if available)
            subtitle = host.ip
            if host.hostname and host.hostname != host.ip:
                subtitle = host.ip
            if host.mac:
                subtitle += f"  •  {host.mac}"
            row.set_subtitle(subtitle)
            
            # Icon based on shares
            if host.services:
                row.add_prefix(Gtk.Image.new_from_icon_name("folder-remote-symbolic"))
            else:
                row.add_prefix(Gtk.Image.new_from_icon_name("computer-symbolic"))
            
            # Share count badge
            if host.services:
                share_count = len(host.services)
                share_label = Gtk.Label()
                share_label.set_markup(f"<small>{share_count} share{'s' if share_count != 1 else ''}</small>")
                share_label.add_css_class("success")
                share_label.set_valign(Gtk.Align.CENTER)
                row.add_suffix(share_label)
                
                # Tooltip with share names
                share_list = ", ".join(host.services[:5])
                if len(host.services) > 5:
                    share_list += f" (+{len(host.services) - 5} more)"
                row.set_tooltip_text(f"Shares: {share_list}")
            else:
                no_share_label = Gtk.Label()
                no_share_label.set_markup("<small>No shares</small>")
                no_share_label.add_css_class("dim-label")
                no_share_label.set_valign(Gtk.Align.CENTER)
                row.add_suffix(no_share_label)
            
            # Browse button
            browse_btn = Gtk.Button()
            browse_btn.set_icon_name("go-next-symbolic")
            browse_btn.set_valign(Gtk.Align.CENTER)
            browse_btn.set_tooltip_text("Browse shares")
            browse_btn.connect("clicked", self._on_browse_host, host.ip)
            row.add_suffix(browse_btn)
            
            self.results_group.add(row)
    
    def _on_browse_host(self, button, ip):
        """Browse a host's shares."""
        subprocess.Popen(['xdg-open', f'smb://{ip}/'])


class QuickShareDialog(Adw.Dialog):
    """Dialog for quickly sharing a folder."""
    
    def __init__(self, window, samba: SambaManager, execute_callback):
        super().__init__()
        
        self.window = window
        self.samba = samba
        self.execute_callback = execute_callback
        self.selected_path = None
        
        self.set_title("Quick Share")
        self.set_content_width(450)
        self.set_content_height(400)
        
        self.build_ui()
    
    def build_ui(self):
        """Build dialog UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_btn)
        
        self.share_btn = Gtk.Button(label="Share")
        self.share_btn.add_css_class("suggested-action")
        self.share_btn.set_sensitive(False)
        self.share_btn.connect("clicked", self.on_share)
        header.pack_end(self.share_btn)
        
        toolbar_view.add_top_bar(header)
        
        # Content
        clamp = Adw.Clamp()
        clamp.set_maximum_size(400)
        clamp.set_margin_top(20)
        clamp.set_margin_bottom(20)
        clamp.set_margin_start(20)
        clamp.set_margin_end(20)
        toolbar_view.set_content(clamp)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        clamp.set_child(content)
        
        group = Adw.PreferencesGroup()
        content.append(group)
        
        # Folder selection
        folder_row = Adw.ActionRow()
        folder_row.set_title("Folder")
        folder_row.set_subtitle("No folder selected")
        folder_row.set_activatable(True)
        folder_row.add_prefix(Gtk.Image.new_from_icon_name("folder-symbolic"))
        folder_row.add_suffix(Gtk.Image.new_from_icon_name("folder-open-symbolic"))
        folder_row.connect("activated", self.on_select_folder)
        self.folder_row = folder_row
        group.add(folder_row)
        
        # Share name
        name_row = Adw.EntryRow()
        name_row.set_title("Share Name")
        name_row.connect("changed", self.on_name_changed)
        self.name_row = name_row
        group.add(name_row)
        
        # Options
        options_group = Adw.PreferencesGroup()
        options_group.set_title("Options")
        content.append(options_group)
        
        # Writable
        self.writable_switch = Adw.SwitchRow()
        self.writable_switch.set_title("Writable")
        self.writable_switch.set_subtitle("Allow users to modify files")
        self.writable_switch.set_active(True)
        options_group.add(self.writable_switch)
        
        # Guest access
        self.guest_switch = Adw.SwitchRow()
        self.guest_switch.set_title("Guest Access")
        self.guest_switch.set_subtitle("Allow access without password")
        self.guest_switch.set_active(False)
        self.guest_switch.connect("notify::active", self.on_guest_toggled)
        options_group.add(self.guest_switch)
        
        # Password section (shown when guest access is OFF)
        self.password_group = Adw.PreferencesGroup()
        self.password_group.set_title("Samba Password")
        self.password_group.set_description("Set a password to access this share")
        content.append(self.password_group)
        
        # Password entry
        self.password_row = Adw.PasswordEntryRow()
        self.password_row.set_title("Password")
        self.password_row.connect("changed", self.on_password_changed)
        self.password_group.add(self.password_row)
        
        # Confirm password
        self.confirm_row = Adw.PasswordEntryRow()
        self.confirm_row.set_title("Confirm Password")
        self.confirm_row.connect("changed", self.on_password_changed)
        self.password_group.add(self.confirm_row)
        
        # Password match indicator
        self.password_status = Gtk.Label()
        self.password_status.set_halign(Gtk.Align.START)
        self.password_status.add_css_class("dim-label")
        self.password_status.set_margin_start(12)
        self.password_group.add(self.password_status)
    
    def on_guest_toggled(self, switch, param):
        """Show/hide password fields based on guest access toggle."""
        guest_enabled = switch.get_active()
        self.password_group.set_visible(not guest_enabled)
        self._update_share_button()
    
    def on_select_folder(self, row):
        """Open folder chooser."""
        dialog = Gtk.FileDialog()
        dialog.set_title("Select Folder to Share")
        dialog.select_folder(self.window, None, self._on_folder_selected)
    
    def _on_folder_selected(self, dialog, result):
        """Handle folder selection."""
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                self.selected_path = folder.get_path()
                self.folder_row.set_subtitle(self.selected_path)
                
                # Auto-fill share name from folder name
                if not self.name_row.get_text():
                    name = os.path.basename(self.selected_path)
                    self.name_row.set_text(name)
                
                self._update_share_button()
        except:
            pass
    
    def on_name_changed(self, row):
        """Handle share name change."""
        self._update_share_button()
    
    def on_password_changed(self, row):
        """Handle password field changes."""
        password = self.password_row.get_text()
        confirm = self.confirm_row.get_text()
        
        if not password:
            self.password_status.set_text("")
        elif password != confirm:
            self.password_status.set_markup("<span color='#e74c3c'>⚠ Passwords do not match</span>")
        elif len(password) < 4:
            self.password_status.set_markup("<span color='#f39c12'>⚠ Password is too short</span>")
        else:
            self.password_status.set_markup("<span color='#27ae60'>✓ Passwords match</span>")
        
        self._update_share_button()
    
    def _update_share_button(self):
        """Update share button sensitivity."""
        has_path = self.selected_path is not None
        has_name = len(self.name_row.get_text().strip()) > 0
        
        # Check password if guest access is off
        if not self.guest_switch.get_active():
            password = self.password_row.get_text()
            confirm = self.confirm_row.get_text()
            has_valid_password = password and password == confirm and len(password) >= 4
        else:
            has_valid_password = True
        
        self.share_btn.set_sensitive(has_path and has_name and has_valid_password)
    
    def on_share(self, button):
        """Create the share."""
        share = SambaShare(
            name=self.name_row.get_text().strip(),
            path=self.selected_path,
            writable=self.writable_switch.get_active(),
            guest_ok=self.guest_switch.get_active()
        )
        
        plan = self.samba.create_share_plan(share)
        
        # If not guest access, add smbpasswd setup to plan
        if not self.guest_switch.get_active():
            password = self.password_row.get_text()
            username = os.environ.get('USER') or os.environ.get('SUDO_USER') or 'user'
            
            # Escape password for shell (handle special chars)
            escaped_password = password.replace("'", "'\\''")
            
            # Add smbpasswd command to plan tasks
            plan['tasks'].append({
                "type": "command",
                "name": f"Set Samba password for {username}",
                "command": f"(echo '{escaped_password}'; echo '{escaped_password}') | smbpasswd -a -s {username}"
            })
        
        self.close()
        self.execute_callback(plan, f"Creating share '{share.name}'")


class ManageSharesPage(Adw.NavigationPage):
    """Page for managing existing Samba shares."""
    
    def __init__(self, window, samba: SambaManager, execute_callback):
        super().__init__(title="Manage Shares")
        
        self.window = window
        self.samba = samba
        self.execute_callback = execute_callback
        
        self.build_ui()
    
    def build_ui(self):
        """Build page UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        
        # Add share button
        add_btn = Gtk.Button()
        add_btn.set_icon_name("list-add-symbolic")
        add_btn.set_tooltip_text("Add new share")
        add_btn.connect("clicked", self.on_add_share)
        header.pack_end(add_btn)
        
        # Refresh button
        refresh_btn = Gtk.Button()
        refresh_btn.set_icon_name("view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh share list")
        refresh_btn.connect("clicked", lambda b: self.refresh_shares())
        header.pack_end(refresh_btn)
        
        toolbar_view.add_top_bar(header)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        toolbar_view.set_content(scrolled)
        
        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_margin_top(20)
        clamp.set_margin_bottom(20)
        clamp.set_margin_start(20)
        clamp.set_margin_end(20)
        scrolled.set_child(clamp)
        
        self.content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        clamp.set_child(self.content)
        
        self.refresh_shares()
    
    def refresh_shares(self):
        """Refresh the list of shares."""
        # Clear existing content
        while self.content.get_first_child():
            self.content.remove(self.content.get_first_child())
        
        shares = self.samba.get_shares()
        
        if not shares:
            # No shares - show empty state
            empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            empty_box.set_valign(Gtk.Align.CENTER)
            empty_box.set_vexpand(True)
            
            icon = Gtk.Image.new_from_icon_name("folder-remote-symbolic")
            icon.set_pixel_size(64)
            icon.add_css_class("dim-label")
            empty_box.append(icon)
            
            label = Gtk.Label(label="No Shares Configured")
            label.add_css_class("title-2")
            empty_box.append(label)
            
            sublabel = Gtk.Label(label="Create a share to make folders accessible over the network")
            sublabel.add_css_class("dim-label")
            empty_box.append(sublabel)
            
            add_btn = Gtk.Button(label="Create Share")
            add_btn.add_css_class("suggested-action")
            add_btn.add_css_class("pill")
            add_btn.set_halign(Gtk.Align.CENTER)
            add_btn.set_margin_top(20)
            add_btn.connect("clicked", self.on_add_share)
            empty_box.append(add_btn)
            
            self.content.append(empty_box)
            return
        
        # Show shares
        group = Adw.PreferencesGroup()
        group.set_title(f"Active Shares ({len(shares)})")
        group.set_description("/etc/samba/smb.conf")
        self.content.append(group)
        
        for share in shares:
            row = Adw.ExpanderRow()
            row.set_title(share.name)
            row.set_subtitle(share.path)
            row.set_icon_name("folder-remote-symbolic")
            
            # Properties display
            props_row = Adw.ActionRow()
            
            # Build properties string
            props = []
            if share.writable:
                props.append("Writable")
            else:
                props.append("Read-only")
            if share.guest_ok:
                props.append("Guest OK")
            if share.valid_users:
                props.append(f"Users: {share.valid_users}")
            
            props_row.set_title("Properties")
            props_row.set_subtitle(" • ".join(props) if props else "Default settings")
            row.add_row(props_row)
            
            # Comment if present
            if share.comment:
                comment_row = Adw.ActionRow()
                comment_row.set_title("Comment")
                comment_row.set_subtitle(share.comment)
                row.add_row(comment_row)
            
            # Action buttons row
            actions_row = Adw.ActionRow()
            actions_row.set_title("Actions")
            
            edit_btn = Gtk.Button()
            edit_btn.set_icon_name("document-edit-symbolic")
            edit_btn.set_tooltip_text("Edit share")
            edit_btn.set_valign(Gtk.Align.CENTER)
            edit_btn.add_css_class("flat")
            edit_btn.connect("clicked", self.on_edit_share, share)
            actions_row.add_suffix(edit_btn)
            
            delete_btn = Gtk.Button()
            delete_btn.set_icon_name("user-trash-symbolic")
            delete_btn.set_tooltip_text("Delete share")
            delete_btn.set_valign(Gtk.Align.CENTER)
            delete_btn.add_css_class("flat")
            delete_btn.add_css_class("error")
            delete_btn.connect("clicked", self.on_delete_share, share)
            actions_row.add_suffix(delete_btn)
            
            row.add_row(actions_row)
            
            group.add(row)
        
        # Info section
        info_group = Adw.PreferencesGroup()
        info_group.set_title("Information")
        self.content.append(info_group)
        
        # Workgroup info
        workgroup = self.samba.get_workgroup()
        workgroup_row = Adw.ActionRow()
        workgroup_row.set_title("Workgroup")
        workgroup_row.set_subtitle(workgroup)
        workgroup_row.add_prefix(Gtk.Image.new_from_icon_name("network-workgroup-symbolic"))
        info_group.add(workgroup_row)
        
        # Service status
        status = "Running" if self.samba.is_running() else "Stopped"
        status_row = Adw.ActionRow()
        status_row.set_title("Samba Service")
        status_row.set_subtitle(status)
        status_row.add_prefix(Gtk.Image.new_from_icon_name(
            "emblem-ok-symbolic" if self.samba.is_running() else "dialog-warning-symbolic"
        ))
        info_group.add(status_row)
    
    def on_add_share(self, button):
        """Show add share dialog."""
        dialog = QuickShareDialog(self.window, self.samba, self._on_share_action)
        dialog.present()
    
    def _on_share_action(self, plan, title):
        """Execute share action and refresh."""
        self.execute_callback(plan, title)
        # Refresh after a delay to allow operation to complete
        GLib.timeout_add(1000, self.refresh_shares)
    
    def on_edit_share(self, button, share: SambaShare):
        """Show edit share dialog."""
        dialog = EditShareDialog(self.window, self.samba, share, self._on_share_action)
        dialog.present()
    
    def on_delete_share(self, button, share: SambaShare):
        """Confirm and delete share."""
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading=f"Delete Share '{share.name}'?",
            body=f"This will remove the share from smb.conf.\n"
                 f"The folder at {share.path} will not be deleted."
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("delete", "Delete")
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.connect("response", self._on_delete_response, share)
        dialog.present()
    
    def _on_delete_response(self, dialog, response, share: SambaShare):
        """Handle delete confirmation."""
        if response == "delete":
            plan = self.samba.create_delete_share_plan(share.name)
            self._on_share_action(plan, f"Deleting share '{share.name}'")


class EditShareDialog(Adw.Dialog):
    """Dialog for editing an existing share."""
    
    def __init__(self, window, samba: SambaManager, share: SambaShare, execute_callback):
        super().__init__()
        
        self.window = window
        self.samba = samba
        self.share = share
        self.original_name = share.name
        self.execute_callback = execute_callback
        
        self.set_title(f"Edit Share: {share.name}")
        self.set_content_width(450)
        self.set_content_height(450)
        
        self.build_ui()
    
    def build_ui(self):
        """Build dialog UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_btn)
        
        save_btn = Gtk.Button(label="Save")
        save_btn.add_css_class("suggested-action")
        save_btn.connect("clicked", self.on_save)
        header.pack_end(save_btn)
        
        toolbar_view.add_top_bar(header)
        
        # Content
        clamp = Adw.Clamp()
        clamp.set_maximum_size(400)
        clamp.set_margin_top(20)
        clamp.set_margin_bottom(20)
        clamp.set_margin_start(20)
        clamp.set_margin_end(20)
        toolbar_view.set_content(clamp)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        clamp.set_child(content)
        
        group = Adw.PreferencesGroup()
        content.append(group)
        
        # Share name
        self.name_row = Adw.EntryRow()
        self.name_row.set_title("Share Name")
        self.name_row.set_text(self.share.name)
        group.add(self.name_row)
        
        # Path (read-only display)
        path_row = Adw.ActionRow()
        path_row.set_title("Path")
        path_row.set_subtitle(self.share.path)
        path_row.add_prefix(Gtk.Image.new_from_icon_name("folder-symbolic"))
        group.add(path_row)
        
        # Comment
        self.comment_row = Adw.EntryRow()
        self.comment_row.set_title("Comment")
        self.comment_row.set_text(self.share.comment or "")
        group.add(self.comment_row)
        
        # Options
        options_group = Adw.PreferencesGroup()
        options_group.set_title("Options")
        content.append(options_group)
        
        # Browseable
        self.browseable_switch = Adw.SwitchRow()
        self.browseable_switch.set_title("Browseable")
        self.browseable_switch.set_subtitle("Show in network browser")
        self.browseable_switch.set_active(self.share.browseable)
        options_group.add(self.browseable_switch)
        
        # Writable
        self.writable_switch = Adw.SwitchRow()
        self.writable_switch.set_title("Writable")
        self.writable_switch.set_subtitle("Allow users to modify files")
        self.writable_switch.set_active(self.share.writable)
        options_group.add(self.writable_switch)
        
        # Guest access
        self.guest_switch = Adw.SwitchRow()
        self.guest_switch.set_title("Guest Access")
        self.guest_switch.set_subtitle("Allow access without password")
        self.guest_switch.set_active(self.share.guest_ok)
        options_group.add(self.guest_switch)
        
        # Valid users
        access_group = Adw.PreferencesGroup()
        access_group.set_title("Access Control")
        content.append(access_group)
        
        self.users_row = Adw.EntryRow()
        self.users_row.set_title("Valid Users")
        self.users_row.set_text(self.share.valid_users or "")
        access_group.add(self.users_row)
        
        users_hint = Gtk.Label()
        users_hint.set_markup("<small>Comma-separated list (e.g. user1, @group1). Leave empty for all users.</small>")
        users_hint.add_css_class("dim-label")
        users_hint.set_halign(Gtk.Align.START)
        users_hint.set_margin_start(15)
        access_group.add(users_hint)
    
    def on_save(self, button):
        """Save changes to the share."""
        updated_share = SambaShare(
            name=self.name_row.get_text().strip() or self.share.name,
            path=self.share.path,
            comment=self.comment_row.get_text().strip(),
            browseable=self.browseable_switch.get_active(),
            writable=self.writable_switch.get_active(),
            guest_ok=self.guest_switch.get_active(),
            valid_users=self.users_row.get_text().strip()
        )
        
        plan = self.samba.create_modify_share_plan(self.original_name, updated_share)
        self.close()
        self.execute_callback(plan, f"Updating share '{updated_share.name}'")


class SambaUserDialog(Adw.Dialog):
    """Dialog for managing Samba users."""
    
    def __init__(self, window):
        super().__init__()
        
        self.window = window
        
        self.set_title("Add Samba User")
        self.set_content_width(400)
        self.set_content_height(300)
        
        self.build_ui()
    
    def build_ui(self):
        """Build dialog UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_btn)
        
        self.add_btn = Gtk.Button(label="Add User")
        self.add_btn.add_css_class("suggested-action")
        self.add_btn.set_sensitive(False)
        self.add_btn.connect("clicked", self.on_add_user)
        header.pack_end(self.add_btn)
        
        toolbar_view.add_top_bar(header)
        
        # Content
        clamp = Adw.Clamp()
        clamp.set_maximum_size(350)
        clamp.set_margin_top(20)
        clamp.set_margin_bottom(20)
        clamp.set_margin_start(20)
        clamp.set_margin_end(20)
        toolbar_view.set_content(clamp)
        
        group = Adw.PreferencesGroup()
        group.set_description("Add an existing system user to Samba")
        clamp.set_child(group)
        
        # Username
        self.user_row = Adw.EntryRow()
        self.user_row.set_title("Username")
        self.user_row.connect("changed", self._on_changed)
        group.add(self.user_row)
        
        # Password
        self.pass_row = Adw.PasswordEntryRow()
        self.pass_row.set_title("Samba Password")
        self.pass_row.connect("changed", self._on_changed)
        group.add(self.pass_row)
        
        # Confirm password
        self.confirm_row = Adw.PasswordEntryRow()
        self.confirm_row.set_title("Confirm Password")
        self.confirm_row.connect("changed", self._on_changed)
        group.add(self.confirm_row)
    
    def _on_changed(self, row):
        """Update button state."""
        username = self.user_row.get_text().strip()
        password = self.pass_row.get_text()
        confirm = self.confirm_row.get_text()
        
        valid = len(username) > 0 and len(password) >= 4 and password == confirm
        self.add_btn.set_sensitive(valid)
    
    def on_add_user(self, button):
        """Add the Samba user."""
        username = self.user_row.get_text().strip()
        password = self.pass_row.get_text()
        
        # Run smbpasswd
        self.close()
        
        # Execute via tux-helper
        plan = {
            "tasks": [
                {
                    "type": "command",
                    "name": f"Add Samba user {username}",
                    "command": f"(echo '{password}'; echo '{password}') | smbpasswd -a -s {username}"
                }
            ]
        }
        
        dialog = PlanExecutionDialog(self.window, plan, f"Adding Samba user {username}", get_distro())
        dialog.present()


class DomainJoinDialog(Adw.Dialog):
    """Dialog for joining an AD domain."""
    
    def __init__(self, window, ad: ADManager, execute_callback):
        super().__init__()
        
        self.window = window
        self.ad = ad
        self.execute_callback = execute_callback
        
        self.set_title("Join Domain")
        self.set_content_width(450)
        self.set_content_height(450)
        
        self.build_ui()
    
    def build_ui(self):
        """Build dialog UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_btn)
        
        self.join_btn = Gtk.Button(label="Join")
        self.join_btn.add_css_class("suggested-action")
        self.join_btn.set_sensitive(False)
        self.join_btn.connect("clicked", self.on_join)
        header.pack_end(self.join_btn)
        
        toolbar_view.add_top_bar(header)
        
        # Content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        toolbar_view.set_content(scrolled)
        
        clamp = Adw.Clamp()
        clamp.set_maximum_size(400)
        clamp.set_margin_top(20)
        clamp.set_margin_bottom(20)
        clamp.set_margin_start(20)
        clamp.set_margin_end(20)
        scrolled.set_child(clamp)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        clamp.set_child(content)
        
        # Domain info
        domain_group = Adw.PreferencesGroup()
        domain_group.set_title("Domain")
        content.append(domain_group)
        
        self.domain_row = Adw.EntryRow()
        self.domain_row.set_title("Domain Name")
        self.domain_row.connect("changed", self._on_changed)
        domain_group.add(self.domain_row)
        
        # Credentials
        cred_group = Adw.PreferencesGroup()
        cred_group.set_title("Administrator Credentials")
        content.append(cred_group)
        
        self.user_row = Adw.EntryRow()
        self.user_row.set_title("Username")
        self.user_row.set_text("Administrator")
        self.user_row.connect("changed", self._on_changed)
        cred_group.add(self.user_row)
        
        self.pass_row = Adw.PasswordEntryRow()
        self.pass_row.set_title("Password")
        self.pass_row.connect("changed", self._on_changed)
        cred_group.add(self.pass_row)
        
        # Advanced options (collapsed)
        advanced_group = Adw.PreferencesGroup()
        advanced_group.set_title("Advanced Options")
        content.append(advanced_group)
        
        self.ou_row = Adw.EntryRow()
        self.ou_row.set_title("Computer OU (optional)")
        advanced_group.add(self.ou_row)
    
    def _on_changed(self, row):
        """Update button state."""
        domain = self.domain_row.get_text().strip()
        username = self.user_row.get_text().strip()
        password = self.pass_row.get_text()
        
        valid = len(domain) > 0 and len(username) > 0 and len(password) > 0
        self.join_btn.set_sensitive(valid)
    
    def on_join(self, button):
        """Join the domain."""
        domain = self.domain_row.get_text().strip()
        username = self.user_row.get_text().strip()
        password = self.pass_row.get_text()
        ou = self.ou_row.get_text().strip()
        
        plan = self.ad.create_join_plan(domain, username, password, ou)
        self.close()
        self.execute_callback(plan, f"Joining domain {domain}")


class QuickOpenPortDialog(Adw.Dialog):
    """Dialog for quickly opening firewall ports."""
    
    def __init__(self, window, firewall: FirewallManager, execute_callback):
        super().__init__()
        
        self.window = window
        self.firewall = firewall
        self.execute_callback = execute_callback
        self.selected_service = None
        
        self.set_title("Open Firewall Port")
        self.set_content_width(400)
        self.set_content_height(500)
        
        self.build_ui()
    
    def build_ui(self):
        """Build dialog UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        
        cancel_btn = Gtk.Button(label="Cancel")
        cancel_btn.connect("clicked", lambda b: self.close())
        header.pack_start(cancel_btn)
        
        self.open_btn = Gtk.Button(label="Open Port")
        self.open_btn.add_css_class("suggested-action")
        self.open_btn.set_sensitive(False)
        self.open_btn.connect("clicked", self.on_open)
        header.pack_end(self.open_btn)
        
        toolbar_view.add_top_bar(header)
        
        # Content
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        toolbar_view.set_content(scrolled)
        
        clamp = Adw.Clamp()
        clamp.set_maximum_size(350)
        clamp.set_margin_top(20)
        clamp.set_margin_bottom(20)
        clamp.set_margin_start(20)
        clamp.set_margin_end(20)
        scrolled.set_child(clamp)
        
        group = Adw.PreferencesGroup()
        group.set_title("Select Service")
        clamp.set_child(group)
        
        # List common services
        for service, info in self.firewall.COMMON_SERVICES.items():
            row = Adw.ActionRow()
            row.set_title(service.upper())
            row.set_subtitle(f"{info['desc']} ({info['port']})")
            row.set_activatable(True)
            
            check = Gtk.CheckButton()
            check.set_valign(Gtk.Align.CENTER)
            check.connect("toggled", self._on_service_toggled, service)
            row.add_prefix(check)
            row.set_activatable_widget(check)
            
            group.add(row)
    
    def _on_service_toggled(self, check, service):
        """Handle service selection."""
        if check.get_active():
            self.selected_service = service
            self.open_btn.set_sensitive(True)
        else:
            if self.selected_service == service:
                self.selected_service = None
                self.open_btn.set_sensitive(False)
    
    def on_open(self, button):
        """Open the selected port."""
        if not self.selected_service:
            return
        
        cmd = self.firewall.create_open_port_command(self.selected_service)
        plan = {
            "tasks": [
                {
                    "type": "command",
                    "name": f"Open {self.selected_service}",
                    "command": cmd
                }
            ]
        }
        
        self.close()
        self.execute_callback(plan, f"Opening {self.selected_service}")


class FirewallPage(Adw.NavigationPage):
    """Page showing current firewall rules."""
    
    def __init__(self, window, firewall: FirewallManager):
        super().__init__(title="Firewall Rules")
        
        self.window = window
        self.firewall = firewall
        
        self.build_ui()
    
    def build_ui(self):
        """Build the firewall page."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        toolbar_view.add_top_bar(header)
        
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        toolbar_view.set_content(scrolled)
        
        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_margin_top(20)
        clamp.set_margin_bottom(20)
        clamp.set_margin_start(20)
        clamp.set_margin_end(20)
        scrolled.set_child(clamp)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        clamp.set_child(content)
        
        # Status
        active, backend = self.firewall.get_status()
        status_label = Gtk.Label()
        status_label.set_markup(f"<b>Firewall Backend:</b> {backend}")
        status_label.set_halign(Gtk.Align.START)
        content.append(status_label)
        
        # Open ports
        group = Adw.PreferencesGroup()
        group.set_title("Open Ports / Services")
        content.append(group)
        
        open_ports = self.firewall.get_open_ports()
        
        if not open_ports:
            row = Adw.ActionRow()
            row.set_title("No ports open")
            row.set_subtitle("System is fully locked down")
            group.add(row)
        else:
            for port in open_ports:
                row = Adw.ActionRow()
                row.set_title(port)
                
                # Check if it's a known service
                if port in self.firewall.COMMON_SERVICES:
                    info = self.firewall.COMMON_SERVICES[port]
                    row.set_subtitle(info['desc'])
                
                row.add_prefix(Gtk.Image.new_from_icon_name("network-transmit-symbolic"))
                group.add(row)


class PlanExecutionDialog(Adw.Dialog):
    """Dialog that executes a plan and shows progress."""
    
    def __init__(self, window, plan: dict, title: str, distro):
        super().__init__()
        
        self.window = window
        self.plan = plan
        self.distro = distro
        
        self.set_title(title)
        self.set_content_width(600)
        self.set_content_height(400)
        
        self.build_ui()
        GLib.timeout_add(100, self.start_execution)
    
    def build_ui(self):
        """Build dialog UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        
        self.close_btn = Gtk.Button(label="Close")
        self.close_btn.set_sensitive(False)
        self.close_btn.connect("clicked", lambda b: self.close())
        header.pack_end(self.close_btn)
        
        toolbar_view.add_top_bar(header)
        
        # Content
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        box.set_margin_top(20)
        box.set_margin_bottom(20)
        box.set_margin_start(20)
        box.set_margin_end(20)
        toolbar_view.set_content(box)
        
        # Status
        self.status_label = Gtk.Label(label="Starting...")
        self.status_label.set_halign(Gtk.Align.START)
        box.append(self.status_label)
        
        # Progress bar
        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(True)
        box.append(self.progress)
        
        # Log output
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_vexpand(True)
        scrolled.set_min_content_height(200)
        box.append(scrolled)
        
        self.log_view = Gtk.TextView()
        self.log_view.set_editable(False)
        self.log_view.set_monospace(True)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        scrolled.set_child(self.log_view)
        
        self.log_buffer = self.log_view.get_buffer()
    
    def start_execution(self):
        """Start executing the plan."""
        thread = threading.Thread(target=self._execute, daemon=True)
        thread.start()
        return False
    
    def _execute(self):
        """Execute the plan via tux-helper."""
        import tempfile
        import subprocess
        
        # Write plan to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.plan, f)
            plan_file = f.name
        
        try:
            # Run tux-helper
            cmd = ['pkexec', '/usr/bin/tux-helper', 
                   '--execute-plan', plan_file,
                   '--family', self.distro.family.value]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            tasks = self.plan.get('tasks', [])
            total = len(tasks)
            
            for line in process.stdout:
                line = line.rstrip()
                
                # Parse status messages
                if '[Tux Assistant:' in line:
                    if 'PROGRESS' in line:
                        # Extract progress
                        try:
                            parts = line.split(']', 1)[1].strip()
                            current, rest = parts.split('/', 1)
                            current = int(current)
                            fraction = current / total if total > 0 else 0
                            GLib.idle_add(self._update_progress, fraction, parts)
                        except:
                            pass
                    elif 'COMPLETE' in line:
                        GLib.idle_add(self._on_complete, "Complete")
                    elif 'ERROR' in line:
                        msg = line.split(']', 1)[1].strip() if ']' in line else line
                        GLib.idle_add(self._append_log, f"ERROR: {msg}\n")
                else:
                    GLib.idle_add(self._append_log, line + "\n")
            
            process.wait()
            
            if process.returncode == 0:
                GLib.idle_add(self._on_complete, "Complete")
            else:
                GLib.idle_add(self._on_complete, "Failed")
        
        except Exception as e:
            GLib.idle_add(self._on_complete, f"Error: {e}")
        
        finally:
            os.unlink(plan_file)
    
    def _update_progress(self, fraction, text):
        """Update progress bar."""
        self.progress.set_fraction(fraction)
        self.progress.set_text(text)
        self.status_label.set_label(f"Running: {text}")
    
    def _append_log(self, text):
        """Append text to log."""
        end = self.log_buffer.get_end_iter()
        self.log_buffer.insert(end, text)
        
        # Scroll to bottom
        mark = self.log_buffer.get_insert()
        self.log_view.scroll_to_mark(mark, 0.0, True, 0.0, 1.0)
    
    def _on_complete(self, status):
        """Handle completion."""
        self.status_label.set_label(status)
        self.progress.set_fraction(1.0)
        self.close_btn.set_sensitive(True)


# Remove the placeholder registration for networking since we have the real one now
