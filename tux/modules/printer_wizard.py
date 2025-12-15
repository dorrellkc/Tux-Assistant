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
        result = subprocess.run(['which', 'lpinfo'], capture_output=True)
        return result.returncode == 0
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
    
    try:
        # Use lpinfo to find USB devices
        result = subprocess.run(
            ['lpinfo', '-v'],
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
                    ['lpinfo', '--device-id', uri],
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
    
    # Method 1: CUPS lpinfo network discovery
    try:
        result = subprocess.run(
            ['lpinfo', '-v'],
            capture_output=True, text=True,
            timeout=10
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
            # Quick browse for IPP printers
            result = subprocess.run(
                ['avahi-browse', '-t', '-r', '-p', '_ipp._tcp'],
                capture_output=True, text=True,
                timeout=5
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
    
    return printers


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
# Printer Wizard Page
# =============================================================================

@register_module(
    id="printer_wizard",
    name="Printer Wizard",
    description="Detect and set up printers",
    icon="printer-symbolic",
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
        self.refresh_btn.set_icon_name("view-refresh-symbolic")
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
        self.printers_placeholder.add_prefix(Gtk.Image.new_from_icon_name("printer-symbolic"))
        
        scan_btn = Gtk.Button(label="Scan")
        scan_btn.add_css_class("suggested-action")
        scan_btn.set_valign(Gtk.Align.CENTER)
        scan_btn.connect("clicked", self._on_scan_clicked)
        self.printers_placeholder.add_suffix(scan_btn)
        
        self.printers_group.add(self.printers_placeholder)
        
        self.printer_rows = [self.printers_placeholder]
    
    def _build_help_section(self):
        """Build the help section."""
        help_group = Adw.PreferencesGroup()
        help_group.set_title("Printer Setup Help")
        self.content_box.append(help_group)
        
        # HP printers
        hp_row = Adw.ActionRow()
        hp_row.set_title("HP Printers")
        hp_row.set_subtitle("Usually work great with HPLIP")
        hp_row.add_prefix(Gtk.Image.new_from_icon_name("object-select-symbolic"))
        help_group.add(hp_row)
        
        # Brother printers
        brother_row = Adw.ActionRow()
        brother_row.set_title("Brother Printers")
        brother_row.set_subtitle("May require downloading drivers from Brother")
        brother_row.add_prefix(Gtk.Image.new_from_icon_name("dialog-warning-symbolic"))
        help_group.add(brother_row)
        
        # Other printers
        other_row = Adw.ActionRow()
        other_row.set_title("Other Brands")
        other_row.set_subtitle("Canon, Epson - check manufacturer website for Linux drivers")
        other_row.add_prefix(Gtk.Image.new_from_icon_name("help-about-symbolic"))
        help_group.add(other_row)
        
        # Manual setup
        manual_row = Adw.ActionRow()
        manual_row.set_title("Manual Setup")
        manual_row.set_subtitle("Open CUPS web interface for advanced configuration")
        manual_row.add_prefix(Gtk.Image.new_from_icon_name("emblem-system-symbolic"))
        
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
            self.status_row.add_prefix(Gtk.Image.new_from_icon_name("dialog-error-symbolic"))
            
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
            self.status_row.add_prefix(Gtk.Image.new_from_icon_name("dialog-warning-symbolic"))
            
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
            self.status_row.add_prefix(Gtk.Image.new_from_icon_name("object-select-symbolic"))
            
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
            row.add_prefix(Gtk.Image.new_from_icon_name("printer-symbolic"))
            
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
            usb_header.add_prefix(Gtk.Image.new_from_icon_name("media-removable-symbolic"))
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
            net_header.add_prefix(Gtk.Image.new_from_icon_name("network-workgroup-symbolic"))
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
        """Set up a Brother printer."""
        # Phase 3 - For now, guide to Brother website
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Brother Printer Setup",
            body=f"Brother printers require drivers from Brother's website.\n\nPrinter: {printer.display_name}\n\nWould you like to open the Brother driver download page?"
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("open", "Open Brother Support")
        dialog.set_response_appearance("open", Adw.ResponseAppearance.SUGGESTED)
        dialog.connect("response", self._on_brother_response, printer)
        dialog.present()
    
    def _on_brother_response(self, dialog, response, printer):
        """Handle Brother dialog response."""
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
