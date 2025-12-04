"""
Tux Assistant - Hardware Manager Module

Printers, Bluetooth, Displays, and Audio management.
Provides friendly interfaces to system hardware settings.

Copyright (c) 2025 Christopher Dorrell. Licensed under GPL-3.0.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

import os
import subprocess
import threading
from gi.repository import Gtk, Adw, GLib, Gio
from typing import Optional, List, Tuple
from dataclasses import dataclass

from ..core import get_distro, DistroFamily

from .registry import register_module, ModuleCategory


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class PrinterInfo:
    """Information about a printer."""
    name: str
    description: str
    location: str
    is_default: bool
    is_accepting: bool
    state: str


@dataclass
class BluetoothDevice:
    """Information about a Bluetooth device."""
    address: str
    name: str
    paired: bool
    connected: bool
    device_type: str


@dataclass 
class AudioDevice:
    """Information about an audio device."""
    id: str
    name: str
    description: str
    is_default: bool
    device_type: str  # "sink" (output) or "source" (input)


@dataclass
class DisplayInfo:
    """Information about a display."""
    name: str
    resolution: str
    refresh_rate: str
    is_primary: bool
    position: str


# =============================================================================
# Printer Utilities
# =============================================================================

def get_printers() -> List[PrinterInfo]:
    """Get list of configured printers."""
    printers = []
    
    try:
        # Use lpstat to get printer info
        result = subprocess.run(
            ['lpstat', '-p', '-d'],
            capture_output=True, text=True
        )
        
        if result.returncode != 0:
            return printers
        
        default_printer = ""
        lines = result.stdout.strip().split('\n')
        
        for line in lines:
            if line.startswith('system default destination:'):
                default_printer = line.split(':')[1].strip()
            elif line.startswith('printer '):
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[1]
                    state = "idle"
                    if "disabled" in line.lower():
                        state = "disabled"
                    elif "printing" in line.lower():
                        state = "printing"
                    
                    printers.append(PrinterInfo(
                        name=name,
                        description="",
                        location="",
                        is_default=(name == default_printer),
                        is_accepting=("disabled" not in line.lower()),
                        state=state
                    ))
        
    except Exception:
        pass
    
    return printers


def check_cups_status() -> Tuple[str, str]:
    """Check CUPS status.
    Returns: (status, issue_type)
    issue_type: "ok", "not_installed", "service_stopped"
    """
    try:
        # Check if CUPS is installed
        result = subprocess.run(['which', 'lpstat'], capture_output=True)
        if result.returncode != 0:
            # Also check for cups package
            result = subprocess.run(['which', 'cupsd'], capture_output=True)
            if result.returncode != 0:
                return "CUPS not installed", "not_installed"
        
        # Check if CUPS service is running
        result = subprocess.run(
            ['systemctl', 'is-active', 'cups'],
            capture_output=True, text=True
        )
        if result.stdout.strip() == "active":
            return "Printer service running", "ok"
        else:
            return "Printer service not running", "service_stopped"
    except Exception:
        return "Could not check printer status", "error"


def check_cups_running() -> bool:
    """Check if CUPS service is running (legacy helper)."""
    _, issue_type = check_cups_status()
    return issue_type == "ok"


# =============================================================================
# Bluetooth Utilities
# =============================================================================

def check_bluetooth_available() -> Tuple[bool, str, str]:
    """Check if Bluetooth is available and get status.
    Returns: (available, status_message, issue_type)
    issue_type: "ok", "no_tools", "service_stopped", "no_adapter", "powered_off"
    """
    try:
        # Check if bluetoothctl exists
        result = subprocess.run(['which', 'bluetoothctl'], capture_output=True)
        if result.returncode != 0:
            return False, "Bluetooth tools not installed", "no_tools"
        
        # Check if Bluetooth service is running
        result = subprocess.run(
            ['systemctl', 'is-active', 'bluetooth'],
            capture_output=True, text=True
        )
        if result.stdout.strip() != "active":
            return False, "Bluetooth service not running", "service_stopped"
        
        # Check if controller exists
        result = subprocess.run(
            ['bluetoothctl', 'show'],
            capture_output=True, text=True
        )
        if "No default controller" in result.stdout or result.returncode != 0:
            return False, "No Bluetooth adapter found", "no_adapter"
        
        # Check if powered on
        if "Powered: yes" in result.stdout:
            return True, "Bluetooth is on", "ok"
        else:
            return True, "Bluetooth is off", "powered_off"
        
    except Exception as e:
        return False, str(e), "error"


def get_bluetooth_devices() -> List[BluetoothDevice]:
    """Get list of paired and nearby Bluetooth devices."""
    devices = []
    
    try:
        # Get paired devices
        result = subprocess.run(
            ['bluetoothctl', 'devices', 'Paired'],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            for line in result.stdout.strip().split('\n'):
                if line.startswith('Device '):
                    parts = line.split(' ', 2)
                    if len(parts) >= 3:
                        address = parts[1]
                        name = parts[2]
                        
                        # Check if connected
                        info_result = subprocess.run(
                            ['bluetoothctl', 'info', address],
                            capture_output=True, text=True
                        )
                        connected = "Connected: yes" in info_result.stdout
                        
                        devices.append(BluetoothDevice(
                            address=address,
                            name=name,
                            paired=True,
                            connected=connected,
                            device_type="unknown"
                        ))
        
    except Exception:
        pass
    
    return devices


def toggle_bluetooth_power(on: bool) -> bool:
    """Turn Bluetooth on or off."""
    try:
        cmd = "power on" if on else "power off"
        result = subprocess.run(
            ['bluetoothctl', cmd],
            capture_output=True, text=True,
            input=""
        )
        return result.returncode == 0
    except Exception:
        return False


# =============================================================================
# Audio Utilities
# =============================================================================

def get_audio_backend() -> str:
    """Detect if using PipeWire or PulseAudio."""
    try:
        result = subprocess.run(
            ['pactl', 'info'],
            capture_output=True, text=True
        )
        if 'PipeWire' in result.stdout:
            return 'pipewire'
        return 'pulseaudio'
    except Exception:
        return 'unknown'


def get_audio_outputs() -> List[AudioDevice]:
    """Get list of audio output devices (sinks)."""
    devices = []
    
    try:
        result = subprocess.run(
            ['pactl', 'list', 'sinks', 'short'],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            # Get default sink
            default_result = subprocess.run(
                ['pactl', 'get-default-sink'],
                capture_output=True, text=True
            )
            default_sink = default_result.stdout.strip()
            
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        sink_id = parts[0]
                        sink_name = parts[1]
                        
                        # Get friendly description
                        desc_result = subprocess.run(
                            ['pactl', 'list', 'sinks'],
                            capture_output=True, text=True
                        )
                        description = sink_name
                        
                        # Parse description from full output
                        in_sink = False
                        for desc_line in desc_result.stdout.split('\n'):
                            if f"Name: {sink_name}" in desc_line:
                                in_sink = True
                            elif in_sink and "Description:" in desc_line:
                                description = desc_line.split(':', 1)[1].strip()
                                break
                            elif in_sink and desc_line.startswith("Sink #"):
                                break
                        
                        devices.append(AudioDevice(
                            id=sink_id,
                            name=sink_name,
                            description=description,
                            is_default=(sink_name == default_sink),
                            device_type="sink"
                        ))
        
    except Exception:
        pass
    
    return devices


def get_audio_inputs() -> List[AudioDevice]:
    """Get list of audio input devices (sources)."""
    devices = []
    
    try:
        result = subprocess.run(
            ['pactl', 'list', 'sources', 'short'],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            # Get default source
            default_result = subprocess.run(
                ['pactl', 'get-default-source'],
                capture_output=True, text=True
            )
            default_source = default_result.stdout.strip()
            
            for line in result.stdout.strip().split('\n'):
                if line:
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        source_id = parts[0]
                        source_name = parts[1]
                        
                        # Skip monitor sources (they echo output)
                        if '.monitor' in source_name:
                            continue
                        
                        # Get friendly description
                        desc_result = subprocess.run(
                            ['pactl', 'list', 'sources'],
                            capture_output=True, text=True
                        )
                        description = source_name
                        
                        in_source = False
                        for desc_line in desc_result.stdout.split('\n'):
                            if f"Name: {source_name}" in desc_line:
                                in_source = True
                            elif in_source and "Description:" in desc_line:
                                description = desc_line.split(':', 1)[1].strip()
                                break
                            elif in_source and desc_line.startswith("Source #"):
                                break
                        
                        devices.append(AudioDevice(
                            id=source_id,
                            name=source_name,
                            description=description,
                            is_default=(source_name == default_source),
                            device_type="source"
                        ))
        
    except Exception:
        pass
    
    return devices


def set_default_audio_device(device: AudioDevice) -> bool:
    """Set the default audio device."""
    try:
        if device.device_type == "sink":
            cmd = ['pactl', 'set-default-sink', device.name]
        else:
            cmd = ['pactl', 'set-default-source', device.name]
        
        result = subprocess.run(cmd, capture_output=True)
        return result.returncode == 0
    except Exception:
        return False


# =============================================================================
# Display Utilities
# =============================================================================

def get_displays() -> List[DisplayInfo]:
    """Get list of connected displays."""
    displays = []
    
    try:
        result = subprocess.run(
            ['xrandr', '--query'],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            current_display = None
            
            for line in result.stdout.split('\n'):
                # Display line: "HDMI-1 connected primary 1920x1080+0+0"
                if ' connected' in line:
                    parts = line.split()
                    name = parts[0]
                    is_primary = 'primary' in line
                    
                    # Extract resolution and position
                    resolution = ""
                    position = ""
                    for part in parts:
                        if 'x' in part and '+' in part:
                            res_pos = part.split('+')
                            resolution = res_pos[0]
                            if len(res_pos) >= 3:
                                position = f"+{res_pos[1]}+{res_pos[2]}"
                            break
                    
                    current_display = DisplayInfo(
                        name=name,
                        resolution=resolution,
                        refresh_rate="",
                        is_primary=is_primary,
                        position=position
                    )
                    displays.append(current_display)
                
                # Resolution line with refresh rate: "   1920x1080     60.00*+"
                elif current_display and line.strip() and '*' in line:
                    parts = line.split()
                    for part in parts:
                        if '*' in part:
                            current_display.refresh_rate = part.replace('*', '').replace('+', '') + " Hz"
                            break
        
    except Exception:
        pass
    
    return displays


# =============================================================================
# Hardware Manager Page
# =============================================================================

@register_module(
    id="hardware_manager",
    name="Hardware Manager",
    description="Printers, Bluetooth, displays, audio",
    icon="computer-symbolic",
    category=ModuleCategory.SYSTEM,
    order=11  # Windows refugee essential
)
class HardwareManagerPage(Adw.NavigationPage):
    """Hardware management module page."""
    
    def __init__(self, window):
        super().__init__(title="Hardware Manager")
        
        self.window = window
        self.distro = get_distro()
        
        self._build_ui()
        self._refresh_all()
    
    def _build_ui(self):
        """Build the page UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header
        header = Adw.HeaderBar()
        
        # Refresh button
        refresh_btn = Gtk.Button()
        refresh_btn.set_icon_name("view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh")
        refresh_btn.connect("clicked", lambda b: self._refresh_all())
        header.pack_end(refresh_btn)
        
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
        
        # Build sections
        self._build_printers_section()
        self._build_bluetooth_section()
        self._build_audio_section()
        self._build_displays_section()
    
    def _build_printers_section(self):
        """Build the printers section."""
        self.printers_group = Adw.PreferencesGroup()
        self.printers_group.set_title("Printers")
        self.printers_group.set_description("Manage printers and print queues")
        self.content_box.append(self.printers_group)
        
        # Placeholder row
        self.printers_placeholder = Adw.ActionRow()
        self.printers_placeholder.set_title("Loading...")
        self.printers_group.add(self.printers_placeholder)
        
        # Track rows for cleanup
        self.printer_rows = [self.printers_placeholder]
    
    def _build_bluetooth_section(self):
        """Build the Bluetooth section."""
        self.bluetooth_group = Adw.PreferencesGroup()
        self.bluetooth_group.set_title("Bluetooth")
        self.bluetooth_group.set_description("Pair and manage Bluetooth devices")
        self.content_box.append(self.bluetooth_group)
        
        # We'll rebuild this dynamically based on state
        self.bt_rows = []
    
    def _rebuild_bluetooth_ui(self, available: bool, status: str, issue_type: str, devices: List[BluetoothDevice]):
        """Completely rebuild Bluetooth UI based on current state."""
        # Clear all existing rows
        for row in self.bt_rows:
            self.bluetooth_group.remove(row)
        self.bt_rows.clear()
        
        if issue_type == "no_tools":
            # No Bluetooth tools installed
            row = Adw.ActionRow()
            row.set_title("Bluetooth Tools Not Installed")
            row.set_subtitle("Install Bluetooth support to use wireless devices")
            row.add_prefix(Gtk.Image.new_from_icon_name("dialog-warning-symbolic"))
            
            install_btn = Gtk.Button(label="Install Bluetooth")
            install_btn.set_valign(Gtk.Align.CENTER)
            install_btn.add_css_class("suggested-action")
            install_btn.connect("clicked", self._on_install_bluetooth_tools)
            row.add_suffix(install_btn)
            
            self.bluetooth_group.add(row)
            self.bt_rows.append(row)
            
        elif issue_type == "service_stopped":
            # Service not running
            row = Adw.ActionRow()
            row.set_title("Bluetooth Service Stopped")
            row.set_subtitle("Start the Bluetooth service to use wireless devices")
            row.add_prefix(Gtk.Image.new_from_icon_name("bluetooth-disabled-symbolic"))
            
            start_btn = Gtk.Button(label="Start Service")
            start_btn.set_valign(Gtk.Align.CENTER)
            start_btn.add_css_class("suggested-action")
            start_btn.connect("clicked", self._on_start_bluetooth_service)
            row.add_suffix(start_btn)
            
            self.bluetooth_group.add(row)
            self.bt_rows.append(row)
            
        elif issue_type == "no_adapter":
            # No Bluetooth hardware
            row = Adw.ActionRow()
            row.set_title("No Bluetooth Adapter")
            row.set_subtitle("No Bluetooth hardware detected on this computer")
            row.add_prefix(Gtk.Image.new_from_icon_name("bluetooth-disabled-symbolic"))
            
            self.bluetooth_group.add(row)
            self.bt_rows.append(row)
            
        elif issue_type == "powered_off":
            # Service running but Bluetooth is off
            row = Adw.ActionRow()
            row.set_title("Bluetooth Disabled")
            row.set_subtitle("Enable Bluetooth to connect wireless devices")
            row.add_prefix(Gtk.Image.new_from_icon_name("bluetooth-disabled-symbolic"))
            
            enable_btn = Gtk.Button(label="Enable Bluetooth")
            enable_btn.set_valign(Gtk.Align.CENTER)
            enable_btn.add_css_class("suggested-action")
            enable_btn.connect("clicked", self._on_enable_bluetooth)
            row.add_suffix(enable_btn)
            
            self.bluetooth_group.add(row)
            self.bt_rows.append(row)
            
        else:
            # Bluetooth is on and working!
            # Status row with disable option
            status_row = Adw.ActionRow()
            status_row.set_title("Bluetooth Enabled")
            status_row.set_subtitle("Ready to connect devices")
            status_row.add_prefix(Gtk.Image.new_from_icon_name("bluetooth-active-symbolic"))
            
            disable_btn = Gtk.Button(label="Disable")
            disable_btn.set_valign(Gtk.Align.CENTER)
            disable_btn.connect("clicked", self._on_disable_bluetooth)
            status_row.add_suffix(disable_btn)
            
            self.bluetooth_group.add(status_row)
            self.bt_rows.append(status_row)
            
            # Paired devices expander
            devices_expander = Adw.ExpanderRow()
            devices_expander.set_title("Paired Devices")
            
            if devices:
                devices_expander.set_subtitle(f"{len(devices)} device(s)")
                
                for device in devices:
                    dev_row = Adw.ActionRow()
                    dev_row.set_title(device.name)
                    
                    status_text = "Connected" if device.connected else "Paired"
                    dev_row.set_subtitle(f"{device.address} • {status_text}")
                    
                    icon = "bluetooth-active-symbolic" if device.connected else "bluetooth-symbolic"
                    dev_row.add_prefix(Gtk.Image.new_from_icon_name(icon))
                    
                    devices_expander.add_row(dev_row)
            else:
                devices_expander.set_subtitle("No paired devices")
            
            self.bluetooth_group.add(devices_expander)
            self.bt_rows.append(devices_expander)
            
            # Bluetooth settings row
            settings_row = Adw.ActionRow()
            settings_row.set_title("Bluetooth Settings")
            settings_row.set_subtitle("Pair new devices and manage connections")
            settings_row.add_prefix(Gtk.Image.new_from_icon_name("preferences-system-symbolic"))
            settings_row.set_activatable(True)
            settings_row.connect("activated", self._on_open_bluetooth_settings)
            settings_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            
            self.bluetooth_group.add(settings_row)
            self.bt_rows.append(settings_row)
    
    def _build_audio_section(self):
        """Build the audio section."""
        self.audio_group = Adw.PreferencesGroup()
        self.audio_group.set_title("Audio")
        self.audio_group.set_description("Manage audio input and output devices")
        self.content_box.append(self.audio_group)
        
        # Output devices
        self.audio_output_expander = Adw.ExpanderRow()
        self.audio_output_expander.set_title("Output Device")
        self.audio_output_expander.set_subtitle("Loading...")
        self.audio_output_expander.add_prefix(Gtk.Image.new_from_icon_name("audio-speakers-symbolic"))
        self.audio_group.add(self.audio_output_expander)
        
        # Input devices
        self.audio_input_expander = Adw.ExpanderRow()
        self.audio_input_expander.set_title("Input Device")
        self.audio_input_expander.set_subtitle("Loading...")
        self.audio_input_expander.add_prefix(Gtk.Image.new_from_icon_name("audio-input-microphone-symbolic"))
        self.audio_group.add(self.audio_input_expander)
        
        # Volume control row
        volume_row = Adw.ActionRow()
        volume_row.set_title("Volume Settings")
        volume_row.set_subtitle("Open system sound settings")
        volume_row.add_prefix(Gtk.Image.new_from_icon_name("multimedia-volume-control-symbolic"))
        volume_row.set_activatable(True)
        volume_row.connect("activated", self._on_open_sound_settings)
        volume_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        self.audio_group.add(volume_row)
        
        self.audio_output_rows = []
        self.audio_input_rows = []
    
    def _build_displays_section(self):
        """Build the displays section."""
        self.displays_group = Adw.PreferencesGroup()
        self.displays_group.set_title("Displays")
        self.displays_group.set_description("Monitor configuration and settings")
        self.content_box.append(self.displays_group)
        
        # Placeholder
        self.displays_placeholder = Adw.ActionRow()
        self.displays_placeholder.set_title("Loading...")
        self.displays_group.add(self.displays_placeholder)
        
        self.display_rows = [self.displays_placeholder]
    
    def _refresh_all(self):
        """Refresh all hardware information."""
        self._refresh_printers()
        self._refresh_bluetooth()
        self._refresh_audio()
        self._refresh_displays()
    
    def _refresh_printers(self):
        """Refresh printer list."""
        def load():
            status, issue_type = check_cups_status()
            printers = get_printers() if issue_type == "ok" else []
            GLib.idle_add(self._update_printers, status, issue_type, printers)
        
        threading.Thread(target=load, daemon=True).start()
    
    def _update_printers(self, status: str, issue_type: str, printers: List[PrinterInfo]):
        """Update printers UI."""
        # Clear existing rows
        for row in self.printer_rows:
            self.printers_group.remove(row)
        self.printer_rows.clear()
        
        if issue_type == "not_installed":
            # CUPS not installed
            row = Adw.ActionRow()
            row.set_title("Printer Support Not Installed")
            row.set_subtitle("Install CUPS to use printers")
            row.add_prefix(Gtk.Image.new_from_icon_name("dialog-warning-symbolic"))
            
            install_btn = Gtk.Button(label="Install CUPS")
            install_btn.set_valign(Gtk.Align.CENTER)
            install_btn.add_css_class("suggested-action")
            install_btn.connect("clicked", self._on_install_cups)
            row.add_suffix(install_btn)
            
            self.printers_group.add(row)
            self.printer_rows.append(row)
            return
        
        if issue_type == "service_stopped":
            # CUPS installed but not running
            row = Adw.ActionRow()
            row.set_title("Printer Service Stopped")
            row.set_subtitle("Start the printer service to manage printers")
            row.add_prefix(Gtk.Image.new_from_icon_name("printer-symbolic"))
            
            start_btn = Gtk.Button(label="Start Service")
            start_btn.set_valign(Gtk.Align.CENTER)
            start_btn.add_css_class("suggested-action")
            start_btn.connect("clicked", self._on_start_cups)
            row.add_suffix(start_btn)
            
            self.printers_group.add(row)
            self.printer_rows.append(row)
            return
        
        # CUPS is running - show printers
        if not printers:
            row = Adw.ActionRow()
            row.set_title("No Printers Configured")
            row.set_subtitle("Add a printer to get started")
            row.add_prefix(Gtk.Image.new_from_icon_name("printer-symbolic"))
            
            add_btn = Gtk.Button(label="Add Printer")
            add_btn.set_valign(Gtk.Align.CENTER)
            add_btn.add_css_class("suggested-action")
            add_btn.connect("clicked", self._on_add_printer)
            row.add_suffix(add_btn)
            
            self.printers_group.add(row)
            self.printer_rows.append(row)
        else:
            for printer in printers:
                row = Adw.ActionRow()
                
                title = printer.name
                if printer.is_default:
                    title += " (Default)"
                row.set_title(title)
                row.set_subtitle(f"Status: {printer.state}")
                row.add_prefix(Gtk.Image.new_from_icon_name("printer-symbolic"))
                
                self.printers_group.add(row)
                self.printer_rows.append(row)
            
            # Add printer button
            add_row = Adw.ActionRow()
            add_row.set_title("Add Printer")
            add_row.set_subtitle("Configure a new printer")
            add_row.add_prefix(Gtk.Image.new_from_icon_name("list-add-symbolic"))
            add_row.set_activatable(True)
            add_row.connect("activated", lambda r: self._on_add_printer(None))
            add_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            
            self.printers_group.add(add_row)
            self.printer_rows.append(add_row)
    
    def _refresh_bluetooth(self):
        """Refresh Bluetooth status."""
        def load():
            available, status, issue_type = check_bluetooth_available()
            devices = get_bluetooth_devices() if available else []
            GLib.idle_add(self._update_bluetooth, available, status, issue_type, devices)
        
        threading.Thread(target=load, daemon=True).start()
    
    def _update_bluetooth(self, available: bool, status: str, issue_type: str, devices: List[BluetoothDevice]):
        """Update Bluetooth UI."""
        self._rebuild_bluetooth_ui(available, status, issue_type, devices)
    
    def _refresh_audio(self):
        """Refresh audio devices."""
        def load():
            outputs = get_audio_outputs()
            inputs = get_audio_inputs()
            GLib.idle_add(self._update_audio, outputs, inputs)
        
        threading.Thread(target=load, daemon=True).start()
    
    def _update_audio(self, outputs: List[AudioDevice], inputs: List[AudioDevice]):
        """Update audio UI."""
        # Clear existing rows
        for row in self.audio_output_rows:
            self.audio_output_expander.remove(row)
        self.audio_output_rows.clear()
        
        for row in self.audio_input_rows:
            self.audio_input_expander.remove(row)
        self.audio_input_rows.clear()
        
        # Output devices
        default_output = None
        for device in outputs:
            if device.is_default:
                default_output = device.description
            
            row = Adw.ActionRow()
            row.set_title(device.description)
            
            if device.is_default:
                row.set_subtitle("Default")
                row.add_prefix(Gtk.Image.new_from_icon_name("emblem-default-symbolic"))
            else:
                btn = Gtk.Button(label="Set Default")
                btn.set_valign(Gtk.Align.CENTER)
                btn.connect("clicked", self._on_set_default_audio, device)
                row.add_suffix(btn)
            
            self.audio_output_expander.add_row(row)
            self.audio_output_rows.append(row)
        
        self.audio_output_expander.set_subtitle(default_output or "No output devices")
        
        # Input devices
        default_input = None
        for device in inputs:
            if device.is_default:
                default_input = device.description
            
            row = Adw.ActionRow()
            row.set_title(device.description)
            
            if device.is_default:
                row.set_subtitle("Default")
                row.add_prefix(Gtk.Image.new_from_icon_name("emblem-default-symbolic"))
            else:
                btn = Gtk.Button(label="Set Default")
                btn.set_valign(Gtk.Align.CENTER)
                btn.connect("clicked", self._on_set_default_audio, device)
                row.add_suffix(btn)
            
            self.audio_input_expander.add_row(row)
            self.audio_input_rows.append(row)
        
        self.audio_input_expander.set_subtitle(default_input or "No input devices")
    
    def _refresh_displays(self):
        """Refresh display information."""
        def load():
            displays = get_displays()
            GLib.idle_add(self._update_displays, displays)
        
        threading.Thread(target=load, daemon=True).start()
    
    def _update_displays(self, displays: List[DisplayInfo]):
        """Update displays UI."""
        # Clear existing rows
        for row in self.display_rows:
            self.displays_group.remove(row)
        self.display_rows.clear()
        
        if not displays:
            row = Adw.ActionRow()
            row.set_title("No Displays Detected")
            row.set_subtitle("Could not query display information")
            self.displays_group.add(row)
            self.display_rows.append(row)
        else:
            for display in displays:
                row = Adw.ActionRow()
                
                title = display.name
                if display.is_primary:
                    title += " (Primary)"
                row.set_title(title)
                
                subtitle_parts = []
                if display.resolution:
                    subtitle_parts.append(display.resolution)
                if display.refresh_rate:
                    subtitle_parts.append(display.refresh_rate)
                row.set_subtitle(" @ ".join(subtitle_parts) if subtitle_parts else "Unknown resolution")
                
                row.add_prefix(Gtk.Image.new_from_icon_name("video-display-symbolic"))
                
                self.displays_group.add(row)
                self.display_rows.append(row)
        
        # Display settings button
        settings_row = Adw.ActionRow()
        settings_row.set_title("Display Settings")
        settings_row.set_subtitle("Resolution, arrangement, night light")
        settings_row.add_prefix(Gtk.Image.new_from_icon_name("preferences-desktop-display-symbolic"))
        settings_row.set_activatable(True)
        settings_row.connect("activated", self._on_open_display_settings)
        settings_row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
        
        self.displays_group.add(settings_row)
        self.display_rows.append(settings_row)
    
    # =========================================================================
    # Action Handlers
    # =========================================================================
    
    def _on_start_cups(self, button):
        """Start CUPS service."""
        try:
            subprocess.Popen(['pkexec', 'systemctl', 'start', 'cups'])
            self.window.show_toast("Starting printer service...")
            GLib.timeout_add(2000, self._refresh_printers)
        except Exception:
            self.window.show_toast("Could not start printer service")
    
    def _on_install_cups(self, button):
        """Install CUPS printer support."""
        packages = {
            DistroFamily.ARCH: "cups cups-pdf system-config-printer",
            DistroFamily.DEBIAN: "cups cups-pdf system-config-printer",
            DistroFamily.FEDORA: "cups cups-pdf system-config-printer",
            DistroFamily.OPENSUSE: "cups cups-pdf system-config-printer",
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
        self.window.show_toast("Installing printer support...")
        GLib.timeout_add(5000, self._refresh_printers)
    
    def _on_add_printer(self, button):
        """Open printer configuration."""
        # Try different printer config tools
        tools = [
            ['system-config-printer'],
            ['gnome-control-center', 'printers'],
            ['kde-config-printer'],
            ['xdg-open', 'http://localhost:631/admin'],
        ]
        
        for tool in tools:
            try:
                result = subprocess.run(['which', tool[0]], capture_output=True)
                if result.returncode == 0:
                    subprocess.Popen(tool)
                    return
            except Exception:
                continue
        
        # Fallback to CUPS web interface
        try:
            subprocess.Popen(['xdg-open', 'http://localhost:631/admin'])
        except Exception:
            self.window.show_toast("Could not open printer settings")
    
    def _on_install_bluetooth_tools(self, button):
        """Install Bluetooth tools."""
        packages = {
            DistroFamily.ARCH: "bluez bluez-utils",
            DistroFamily.DEBIAN: "bluez bluetooth",
            DistroFamily.FEDORA: "bluez bluez-tools",
            DistroFamily.OPENSUSE: "bluez",
        }
        
        pkg = packages.get(self.distro.family, "bluez")
        
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
echo "  Installing Bluetooth Tools..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
{cmd}
echo ""
echo "Enabling Bluetooth service..."
sudo systemctl enable bluetooth
sudo systemctl start bluetooth
echo ""
echo "✓ Installation complete!"
echo ""
echo "Press Enter to close..."
read'''
        
        self._run_in_terminal(script)
        self.window.show_toast("Installing Bluetooth tools...")
        GLib.timeout_add(5000, self._refresh_bluetooth)
    
    def _on_start_bluetooth_service(self, button):
        """Start the Bluetooth service."""
        try:
            subprocess.Popen(['pkexec', 'systemctl', 'start', 'bluetooth'])
            self.window.show_toast("Starting Bluetooth service...")
            GLib.timeout_add(2000, self._refresh_bluetooth)
        except Exception:
            self.window.show_toast("Could not start Bluetooth service")
    
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
    
    def _on_enable_bluetooth(self, button):
        """Enable Bluetooth."""
        success = toggle_bluetooth_power(True)
        if success:
            self.window.show_toast("Bluetooth enabled")
            GLib.timeout_add(1000, self._refresh_bluetooth)
        else:
            self.window.show_toast("Could not enable Bluetooth")
    
    def _on_disable_bluetooth(self, button):
        """Disable Bluetooth."""
        success = toggle_bluetooth_power(False)
        if success:
            self.window.show_toast("Bluetooth disabled")
            GLib.timeout_add(1000, self._refresh_bluetooth)
        else:
            self.window.show_toast("Could not disable Bluetooth")
    
    def _on_open_bluetooth_settings(self, row):
        """Open system Bluetooth settings."""
        tools = [
            ('gnome-control-center', ['gnome-control-center', 'bluetooth']),
            ('blueman-manager', ['blueman-manager']),
            ('bluedevil-wizard', ['bluedevil-wizard']),
            ('systemsettings', ['systemsettings', 'kcm_bluetooth']),
        ]
        
        for tool_name, tool_cmd in tools:
            try:
                result = subprocess.run(['which', tool_name], capture_output=True)
                if result.returncode == 0:
                    subprocess.Popen(tool_cmd)
                    return
            except Exception:
                continue
        
        # No Bluetooth manager found - offer to install one
        self._show_install_bluetooth_manager_dialog()
    
    def _show_install_bluetooth_manager_dialog(self):
        """Show dialog to install a Bluetooth manager."""
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="No Bluetooth Manager Found",
            body="Would you like to install one?"
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("blueman", "Blueman (Recommended)")
        dialog.set_response_appearance("blueman", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("blueman")
        dialog.connect("response", self._on_install_bluetooth_manager_response)
        dialog.present()
    
    def _on_install_bluetooth_manager_response(self, dialog, response):
        """Handle Bluetooth manager install response."""
        if response == "cancel":
            return
        
        packages = {
            DistroFamily.ARCH: "blueman",
            DistroFamily.DEBIAN: "blueman",
            DistroFamily.FEDORA: "blueman",
            DistroFamily.OPENSUSE: "blueman",
        }
        
        pkg = packages.get(self.distro.family, "blueman")
        
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
echo "  Installing Blueman..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
{cmd}
echo ""
echo "✓ Installation complete!"
echo ""
echo "You can now use 'blueman-manager' for Bluetooth settings."
echo ""
echo "Press Enter to close..."
read'''
        
        self._run_in_terminal(script)
        self.window.show_toast("Installing Blueman...")
    
    def _on_set_default_audio(self, button, device: AudioDevice):
        """Set default audio device."""
        success = set_default_audio_device(device)
        if success:
            self.window.show_toast(f"Default set to: {device.description}")
            self._refresh_audio()
        else:
            self.window.show_toast("Could not change audio device")
    
    def _on_open_sound_settings(self, row):
        """Open system sound settings."""
        tools = [
            ['gnome-control-center', 'sound'],
            ['pavucontrol'],
            ['systemsettings', 'kcm_pulseaudio'],
            ['xfce4-mixer'],
        ]
        
        for tool in tools:
            try:
                result = subprocess.run(['which', tool[0]], capture_output=True)
                if result.returncode == 0:
                    subprocess.Popen(tool)
                    return
            except Exception:
                continue
        
        self.window.show_toast("Could not open sound settings")
    
    def _on_open_display_settings(self, row):
        """Open system display settings."""
        tools = [
            ['gnome-control-center', 'display'],
            ['arandr'],
            ['systemsettings', 'kcm_kscreen'],
            ['lxrandr'],
            ['xfce4-display-settings'],
        ]
        
        for tool in tools:
            try:
                result = subprocess.run(['which', tool[0]], capture_output=True)
                if result.returncode == 0:
                    subprocess.Popen(tool)
                    return
            except Exception:
                continue
        
        self.window.show_toast("Could not open display settings")
