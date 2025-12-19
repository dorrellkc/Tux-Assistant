"""
Tux Assistant - Desktop Enhancements Module

Themes, extensions, widgets, and tweaks for GNOME, KDE, XFCE, Cinnamon, and MATE.

Copyright (c) 2025 Christopher Dorrell. Licensed under GPL-3.0.
"""

import subprocess
import threading
import json
import urllib.request
import urllib.parse
import tempfile
import os
import shutil
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Callable

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')
from gi.repository import Gtk, Adw, GLib, Gio

# Try to import WebKit for theme preview browser
try:
    gi.require_version('WebKit', '6.0')
    from gi.repository import WebKit
    HAS_WEBKIT = True
except Exception:
    try:
        gi.require_version('WebKit2', '5.0')
        from gi.repository import WebKit2 as WebKit
        HAS_WEBKIT = True
    except Exception:
        HAS_WEBKIT = False

from ..core import get_distro, get_desktop, DesktopEnv, DistroFamily
from .registry import register_module, ModuleCategory


# =============================================================================
# Data Models
# =============================================================================

class ThemeType(Enum):
    """Types of themes."""
    GTK = "gtk"
    ICON = "icon"
    CURSOR = "cursor"
    SHELL = "shell"  # GNOME Shell
    PLASMA = "plasma"  # KDE Global
    KVANTUM = "kvantum"  # Qt theming


@dataclass
class Theme:
    """A theme package."""
    id: str
    name: str
    theme_type: ThemeType
    description: str = ""
    packages: dict[str, list[str]] = field(default_factory=dict)  # family -> packages
    # For applying the theme
    gtk_theme: str = ""  # GTK theme name
    icon_theme: str = ""  # Icon theme name
    cursor_theme: str = ""  # Cursor theme name
    shell_theme: str = ""  # GNOME Shell theme
    plasma_theme: str = ""  # KDE Plasma theme
    kvantum_theme: str = ""  # Kvantum theme name
    # External URLs for manual installation
    gnome_look_url: str = ""  # gnome-look.org page
    github_url: str = ""  # GitHub repo for manual install
    kde_store_url: str = ""  # KDE Store page


@dataclass
class Extension:
    """A desktop extension/addon."""
    id: str
    name: str
    description: str
    desktop: DesktopEnv  # Which DE this is for
    # Installation
    packages: dict[str, list[str]] = field(default_factory=dict)
    extension_uuid: str = ""  # GNOME extension UUID
    kde_store_id: str = ""  # KDE Store ID
    # For GNOME extensions that can be enabled via gsettings
    gnome_extension_id: str = ""


@dataclass  
class Tweak:
    """A system tweak/setting."""
    id: str
    name: str
    description: str
    desktop: DesktopEnv  # Which DE this applies to
    # The actual tweak
    gsettings_schema: str = ""
    gsettings_key: str = ""
    gsettings_value: str = ""
    dconf_path: str = ""
    dconf_value: str = ""
    kconfig_file: str = ""
    kconfig_group: str = ""
    kconfig_key: str = ""
    kconfig_value: str = ""
    xfconf_channel: str = ""
    xfconf_property: str = ""
    xfconf_value: str = ""
    # For toggle tweaks
    is_toggle: bool = False
    enabled_value: str = ""
    disabled_value: str = ""


@dataclass
class Tool:
    """A desktop tool/utility."""
    id: str
    name: str
    description: str
    packages: dict[str, list[str]] = field(default_factory=dict)
    flatpak_id: str = ""  # Alternative flatpak
    desktop: Optional[DesktopEnv] = None  # None = universal


# =============================================================================
# Theme Definitions
# =============================================================================

GTK_THEMES = [
    Theme(
        id="adwaita",
        name="Adwaita",
        theme_type=ThemeType.GTK,
        description="GNOME's default modern theme",
        packages={
            'arch': ['gnome-themes-extra'],
            'fedora': ['gnome-themes-extra'],
            'debian': ['gnome-themes-extra'],
            'opensuse': ['gnome-themes-extras'],
        },
        gtk_theme="Adwaita"
    ),
    Theme(
        id="adwaita-dark",
        name="Adwaita Dark",
        theme_type=ThemeType.GTK,
        description="GNOME's default dark theme",
        packages={
            'arch': ['gnome-themes-extra'],
            'fedora': ['gnome-themes-extra'],
            'debian': ['gnome-themes-extra'],
            'opensuse': ['gnome-themes-extras'],
        },
        gtk_theme="Adwaita-dark"
    ),
    Theme(
        id="arc",
        name="Arc",
        theme_type=ThemeType.GTK,
        description="Flat theme with transparent elements",
        packages={
            'arch': ['arc-gtk-theme'],
            'fedora': ['arc-theme'],
            'debian': ['arc-theme'],
            'opensuse': ['arc-gtk-theme'],
        },
        gtk_theme="Arc"
    ),
    Theme(
        id="arc-dark",
        name="Arc Dark",
        theme_type=ThemeType.GTK,
        description="Arc theme - dark variant",
        packages={
            'arch': ['arc-gtk-theme'],
            'fedora': ['arc-theme'],
            'debian': ['arc-theme'],
            'opensuse': ['arc-gtk-theme'],
        },
        gtk_theme="Arc-Dark"
    ),
    Theme(
        id="arc-darker",
        name="Arc Darker",
        theme_type=ThemeType.GTK,
        description="Arc theme - darker variant",
        packages={
            'arch': ['arc-gtk-theme'],
            'fedora': ['arc-theme'],
            'debian': ['arc-theme'],
            'opensuse': ['arc-gtk-theme'],
        },
        gtk_theme="Arc-Darker"
    ),
    Theme(
        id="numix",
        name="Numix",
        theme_type=ThemeType.GTK,
        description="Modern flat theme from Numix Project",
        packages={
            'arch': ['numix-gtk-theme'],
            'fedora': ['numix-gtk-theme'],
            'debian': ['numix-gtk-theme'],
            'opensuse': ['numix-gtk-theme'],
        },
        gtk_theme="Numix"
    ),
    Theme(
        id="adapta",
        name="Adapta",
        theme_type=ThemeType.GTK,
        description="Material Design adaptive theme",
        packages={
            'arch': ['adapta-gtk-theme'],
            'fedora': ['adapta-gtk-theme'],
            'debian': ['adapta-gtk-theme'],
            'opensuse': ['adapta-gtk-theme'],
        },
        gtk_theme="Adapta"
    ),
    Theme(
        id="adapta-nokto",
        name="Adapta Nokto",
        theme_type=ThemeType.GTK,
        description="Adapta theme - dark variant",
        packages={
            'arch': ['adapta-gtk-theme'],
            'fedora': ['adapta-gtk-theme'],
            'debian': ['adapta-gtk-theme'],
            'opensuse': ['adapta-gtk-theme'],
        },
        gtk_theme="Adapta-Nokto"
    ),
    Theme(
        id="dracula",
        name="Dracula",
        theme_type=ThemeType.GTK,
        description="Dark theme based on Dracula color scheme",
        packages={
            'arch': ['dracula-gtk-theme'],  # AUR
            'fedora': [],  # Manual install from draculatheme.com/gtk
            'debian': [],
            'opensuse': [],
        },
        gtk_theme="Dracula",
        gnome_look_url="https://www.gnome-look.org/p/1687249",
        github_url="https://github.com/dracula/gtk"
    ),
    Theme(
        id="nordic",
        name="Nordic",
        theme_type=ThemeType.GTK,
        description="Nord color palette GTK theme",
        packages={
            'arch': ['nordic-theme'],  # AUR
            'fedora': [],  # Manual install from github.com/EliverLara/Nordic
            'debian': [],
            'opensuse': [],
        },
        gtk_theme="Nordic",
        gnome_look_url="https://www.gnome-look.org/p/1267246",
        github_url="https://github.com/EliverLara/Nordic"
    ),
    Theme(
        id="catppuccin-mocha",
        name="Catppuccin Mocha",
        theme_type=ThemeType.GTK,
        description="Soothing pastel dark theme",
        packages={
            'arch': ['catppuccin-gtk-theme-mocha'],  # AUR
            'fedora': [],  # Manual install from github.com/catppuccin/gtk
            'debian': [],
            'opensuse': [],
        },
        gtk_theme="Catppuccin-Mocha-Standard-Blue-Dark",
        gnome_look_url="https://www.gnome-look.org/p/1715554",
        github_url="https://github.com/catppuccin/gtk"
    ),
    Theme(
        id="materia",
        name="Materia",
        theme_type=ThemeType.GTK,
        description="Material Design theme for GTK",
        packages={
            'arch': ['materia-gtk-theme'],
            'fedora': ['materia-gtk-theme'],
            'debian': ['materia-gtk-theme'],
            'opensuse': ['materia-gtk-theme'],
        },
        gtk_theme="Materia"
    ),
    Theme(
        id="materia-dark",
        name="Materia Dark",
        theme_type=ThemeType.GTK,
        description="Material Design dark theme",
        packages={
            'arch': ['materia-gtk-theme'],
            'fedora': ['materia-gtk-theme'],
            'debian': ['materia-gtk-theme'],
            'opensuse': ['materia-gtk-theme'],
        },
        gtk_theme="Materia-dark"
    ),
    Theme(
        id="gruvbox",
        name="Gruvbox",
        theme_type=ThemeType.GTK,
        description="Retro groove color scheme",
        packages={
            'arch': ['gruvbox-dark-gtk'],  # AUR
            'fedora': [],  # Manual install from github.com/Fausto-Korpsvart/Gruvbox-GTK-Theme
            'debian': [],
            'opensuse': [],
        },
        gtk_theme="Gruvbox-Dark",
        gnome_look_url="https://www.gnome-look.org/p/1681313",
        github_url="https://github.com/Fausto-Korpsvart/Gruvbox-GTK-Theme"
    ),
    Theme(
        id="breeze",
        name="Breeze",
        theme_type=ThemeType.GTK,
        description="KDE's Breeze theme for GTK apps",
        packages={
            'arch': ['breeze-gtk'],
            'fedora': ['breeze-gtk'],
            'debian': ['breeze-gtk-theme'],
            'opensuse': ['breeze-gtk'],
        },
        gtk_theme="Breeze"
    ),
    Theme(
        id="breeze-dark",
        name="Breeze Dark",
        theme_type=ThemeType.GTK,
        description="KDE's Breeze dark theme for GTK apps",
        packages={
            'arch': ['breeze-gtk'],
            'fedora': ['breeze-gtk'],
            'debian': ['breeze-gtk-theme'],
            'opensuse': ['breeze-gtk'],
        },
        gtk_theme="Breeze-Dark"
    ),
]

ICON_THEMES = [
    Theme(
        id="papirus",
        name="Papirus",
        theme_type=ThemeType.ICON,
        description="Modern icon theme for Linux",
        packages={
            'arch': ['papirus-icon-theme'],
            'fedora': ['papirus-icon-theme'],
            'debian': ['papirus-icon-theme'],
            'opensuse': ['papirus-icon-theme'],
        },
        icon_theme="Papirus"
    ),
    Theme(
        id="papirus-dark",
        name="Papirus Dark",
        theme_type=ThemeType.ICON,
        description="Papirus icons - dark variant",
        packages={
            'arch': ['papirus-icon-theme'],
            'fedora': ['papirus-icon-theme'],
            'debian': ['papirus-icon-theme'],
            'opensuse': ['papirus-icon-theme'],
        },
        icon_theme="Papirus-Dark"
    ),
    Theme(
        id="tela",
        name="Tela",
        theme_type=ThemeType.ICON,
        description="Flat colorful icon theme",
        packages={
            'arch': ['tela-icon-theme'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        icon_theme="Tela",
        gnome_look_url="https://www.gnome-look.org/p/1279924",
        github_url="https://github.com/vinceliuice/Tela-icon-theme"
    ),
    Theme(
        id="tela-circle",
        name="Tela Circle",
        theme_type=ThemeType.ICON,
        description="Tela icons with circular folders",
        packages={
            'arch': ['tela-circle-icon-theme'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        icon_theme="Tela-circle",
        gnome_look_url="https://www.gnome-look.org/p/1359276",
        github_url="https://github.com/vinceliuice/Tela-circle-icon-theme"
    ),
    Theme(
        id="numix",
        name="Numix",
        theme_type=ThemeType.ICON,
        description="Official Numix icon theme",
        packages={
            'arch': ['numix-icon-theme'],
            'fedora': ['numix-icon-theme'],
            'debian': ['numix-icon-theme'],
            'opensuse': ['numix-icon-theme'],
        },
        icon_theme="Numix"
    ),
    Theme(
        id="numix-circle",
        name="Numix Circle",
        theme_type=ThemeType.ICON,
        description="Numix icons with circle style",
        packages={
            'arch': ['numix-icon-theme-circle'],
            'fedora': ['numix-icon-theme-circle'],
            'debian': ['numix-icon-theme-circle'],
            'opensuse': ['numix-icon-theme-circle'],
        },
        icon_theme="Numix-Circle"
    ),
    Theme(
        id="adwaita",
        name="Adwaita",
        theme_type=ThemeType.ICON,
        description="GNOME's default icon theme",
        packages={
            'arch': ['adwaita-icon-theme'],
            'fedora': ['adwaita-icon-theme'],
            'debian': ['adwaita-icon-theme'],
            'opensuse': ['adwaita-icon-theme'],
        },
        icon_theme="Adwaita"
    ),
    Theme(
        id="breeze",
        name="Breeze",
        theme_type=ThemeType.ICON,
        description="KDE's default icon theme",
        packages={
            'arch': ['breeze-icons'],
            'fedora': ['breeze-icon-theme'],
            'debian': ['breeze-icon-theme'],
            'opensuse': ['breeze-icons'],
        },
        icon_theme="breeze"
    ),
    Theme(
        id="la-capitaine",
        name="La Capitaine",
        theme_type=ThemeType.ICON,
        description="macOS-inspired icon theme",
        packages={
            'arch': ['la-capitaine-icon-theme'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        icon_theme="La-Capitaine",
        gnome_look_url="https://www.gnome-look.org/p/1148695",
        github_url="https://github.com/keeferrourke/la-capitaine-icon-theme"
    ),
]

CURSOR_THEMES = [
    Theme(
        id="bibata-modern",
        name="Bibata Modern",
        theme_type=ThemeType.CURSOR,
        description="Material-based cursor theme",
        packages={
            'arch': ['bibata-cursor-theme'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        cursor_theme="Bibata-Modern-Classic",
        gnome_look_url="https://www.gnome-look.org/p/1197198",
        github_url="https://github.com/ful1e5/Bibata_Cursor"
    ),
    Theme(
        id="bibata-original",
        name="Bibata Original",
        theme_type=ThemeType.CURSOR,
        description="Bibata with original style",
        packages={
            'arch': ['bibata-cursor-theme'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        cursor_theme="Bibata-Original-Classic"
    ),
    Theme(
        id="capitaine",
        name="Capitaine",
        theme_type=ThemeType.CURSOR,
        description="macOS-inspired cursor theme",
        packages={
            'arch': ['capitaine-cursors'],
            'fedora': ['la-capitaine-cursor-theme'],
            'debian': [],
            'opensuse': [],
        },
        cursor_theme="capitaine-cursors"
    ),
    Theme(
        id="adwaita",
        name="Adwaita",
        theme_type=ThemeType.CURSOR,
        description="GNOME's default cursor theme",
        packages={
            'arch': ['adwaita-icon-theme'],
            'fedora': ['adwaita-cursor-theme'],
            'debian': ['adwaita-icon-theme'],
            'opensuse': ['adwaita-icon-theme'],
        },
        cursor_theme="Adwaita"
    ),
    Theme(
        id="breeze",
        name="Breeze",
        theme_type=ThemeType.CURSOR,
        description="KDE's default cursor theme",
        packages={
            'arch': ['breeze'],
            'fedora': ['breeze-cursor-theme'],
            'debian': ['breeze-cursor-theme'],
            'opensuse': ['breeze5-cursors'],
        },
        cursor_theme="breeze_cursors"
    ),
]


# =============================================================================
# GNOME Extensions
# =============================================================================

GNOME_EXTENSIONS = [
    Extension(
        id="dash-to-dock",
        name="Dash to Dock",
        description="Transform the dash into a dock",
        desktop=DesktopEnv.GNOME,
        packages={
            'arch': ['gnome-shell-extension-dash-to-dock'],
            'fedora': ['gnome-shell-extension-dash-to-dock'],
            'debian': ['gnome-shell-extension-dash-to-dock'],
            'opensuse': ['gnome-shell-extension-dash-to-dock'],
        },
        extension_uuid="dash-to-dock@micxgx.gmail.com"
    ),
    Extension(
        id="dash-to-panel",
        name="Dash to Panel",
        description="Taskbar-style panel for GNOME",
        desktop=DesktopEnv.GNOME,
        packages={
            'arch': ['gnome-shell-extension-dash-to-panel'],
            'fedora': ['gnome-shell-extension-dash-to-panel'],
            'debian': ['gnome-shell-extension-dash-to-panel'],
            'opensuse': ['gnome-shell-extension-dash-to-panel'],
        },
        extension_uuid="dash-to-panel@jderose9.github.com"
    ),
    Extension(
        id="appindicator",
        name="AppIndicator/KStatusNotifier",
        description="Tray icons support for GNOME",
        desktop=DesktopEnv.GNOME,
        packages={
            'arch': ['gnome-shell-extension-appindicator'],
            'fedora': ['gnome-shell-extension-appindicator'],
            'debian': ['gnome-shell-extension-appindicator'],
            'opensuse': ['gnome-shell-extension-appindicator'],
        },
        extension_uuid="appindicatorsupport@rgcjonas.gmail.com"
    ),
    Extension(
        id="blur-my-shell",
        name="Blur My Shell",
        description="Add blur effects to GNOME Shell",
        desktop=DesktopEnv.GNOME,
        packages={
            'arch': ['gnome-shell-extension-blur-my-shell'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        extension_uuid="blur-my-shell@aunetx"
    ),
    Extension(
        id="caffeine",
        name="Caffeine",
        description="Disable screensaver and auto-suspend",
        desktop=DesktopEnv.GNOME,
        packages={
            'arch': ['gnome-shell-extension-caffeine'],
            'fedora': ['gnome-shell-extension-caffeine'],
            'debian': ['gnome-shell-extension-caffeine'],
            'opensuse': [],
        },
        extension_uuid="caffeine@patapon.info"
    ),
    Extension(
        id="gsconnect",
        name="GSConnect",
        description="KDE Connect for GNOME",
        desktop=DesktopEnv.GNOME,
        packages={
            'arch': ['gnome-shell-extension-gsconnect'],
            'fedora': ['gnome-shell-extension-gsconnect'],
            'debian': ['gnome-shell-extension-gsconnect'],
            'opensuse': ['gnome-shell-extension-gsconnect'],
        },
        extension_uuid="gsconnect@andyholmes.github.io"
    ),
    Extension(
        id="just-perfection",
        name="Just Perfection",
        description="Tweak GNOME Shell UI elements",
        desktop=DesktopEnv.GNOME,
        packages={
            'arch': ['gnome-shell-extension-just-perfection-desktop'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        extension_uuid="just-perfection-desktop@just-perfection"
    ),
    Extension(
        id="clipboard-indicator",
        name="Clipboard Indicator",
        description="Clipboard manager in top panel",
        desktop=DesktopEnv.GNOME,
        packages={
            'arch': ['gnome-shell-extension-clipboard-indicator'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        extension_uuid="clipboard-indicator@tudmotu.com"
    ),
    Extension(
        id="vitals",
        name="Vitals",
        description="System monitor in top panel",
        desktop=DesktopEnv.GNOME,
        packages={
            'arch': ['gnome-shell-extension-vitals'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        extension_uuid="Vitals@CoreCoding.com"
    ),
    Extension(
        id="arcmenu",
        name="ArcMenu",
        description="Application menu for GNOME",
        desktop=DesktopEnv.GNOME,
        packages={
            'arch': ['gnome-shell-extension-arcmenu'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        extension_uuid="arcmenu@arcmenu.com"
    ),
    Extension(
        id="pop-shell",
        name="Pop Shell",
        description="Tiling window manager extension",
        desktop=DesktopEnv.GNOME,
        packages={
            'arch': ['gnome-shell-extension-pop-shell'],
            'fedora': ['gnome-shell-extension-pop-shell'],
            'debian': [],
            'opensuse': [],
        },
        extension_uuid="pop-shell@system76.com"
    ),
]


# =============================================================================
# XFCE Plugins
# =============================================================================

XFCE_PLUGINS = [
    Extension(
        id="whisker-menu",
        name="Whisker Menu",
        description="Alternate application menu",
        desktop=DesktopEnv.XFCE,
        packages={
            'arch': ['xfce4-whiskermenu-plugin'],
            'fedora': ['xfce4-whiskermenu-plugin'],
            'debian': ['xfce4-whiskermenu-plugin'],
            'opensuse': ['xfce4-panel-plugin-whiskermenu'],
        }
    ),
    Extension(
        id="weather",
        name="Weather Plugin",
        description="Weather information in panel",
        desktop=DesktopEnv.XFCE,
        packages={
            'arch': ['xfce4-weather-plugin'],
            'fedora': ['xfce4-weather-plugin'],
            'debian': ['xfce4-weather-plugin'],
            'opensuse': ['xfce4-panel-plugin-weather'],
        }
    ),
    Extension(
        id="pulseaudio",
        name="PulseAudio Plugin",
        description="Audio control in panel",
        desktop=DesktopEnv.XFCE,
        packages={
            'arch': ['xfce4-pulseaudio-plugin'],
            'fedora': ['xfce4-pulseaudio-plugin'],
            'debian': ['xfce4-pulseaudio-plugin'],
            'opensuse': ['xfce4-panel-plugin-pulseaudio'],
        }
    ),
    Extension(
        id="docklike",
        name="Docklike Taskbar",
        description="Modern dock-style taskbar",
        desktop=DesktopEnv.XFCE,
        packages={
            'arch': ['xfce4-docklike-plugin'],
            'fedora': ['xfce4-docklike-plugin'],
            'debian': ['xfce4-docklike-plugin'],
            'opensuse': [],
        }
    ),
    Extension(
        id="systemload",
        name="System Load Monitor",
        description="CPU, memory, swap monitoring",
        desktop=DesktopEnv.XFCE,
        packages={
            'arch': ['xfce4-systemload-plugin'],
            'fedora': ['xfce4-systemload-plugin'],
            'debian': ['xfce4-systemload-plugin'],
            'opensuse': ['xfce4-panel-plugin-systemload'],
        }
    ),
    Extension(
        id="netload",
        name="Network Monitor",
        description="Network activity monitor",
        desktop=DesktopEnv.XFCE,
        packages={
            'arch': ['xfce4-netload-plugin'],
            'fedora': ['xfce4-netload-plugin'],
            'debian': ['xfce4-netload-plugin'],
            'opensuse': ['xfce4-panel-plugin-netload'],
        }
    ),
    Extension(
        id="clipman",
        name="Clipman",
        description="Clipboard manager",
        desktop=DesktopEnv.XFCE,
        packages={
            'arch': ['xfce4-clipman-plugin'],
            'fedora': ['xfce4-clipman-plugin'],
            'debian': ['xfce4-clipman-plugin'],
            'opensuse': ['xfce4-panel-plugin-clipman'],
        }
    ),
]


# =============================================================================
# KDE Plasma Widgets
# =============================================================================

KDE_WIDGETS = [
    Extension(
        id="kde-eventcalendar",
        name="Event Calendar",
        description="Calendar with Google/ICS integration",
        desktop=DesktopEnv.KDE,
        packages={
            'arch': ['plasma5-applets-eventcalendar'],
            'fedora': [],
            'debian': [],
            'opensuse': ['plasma5-applet-eventcalendar'],
        },
        kde_store_id="998901"
    ),
    Extension(
        id="kde-thermal-monitor",
        name="Thermal Monitor",
        description="CPU/GPU temperature monitoring",
        desktop=DesktopEnv.KDE,
        packages={
            'arch': ['plasma5-applets-thermal-monitor'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        kde_store_id="998917"
    ),
    Extension(
        id="kde-resources-monitor",
        name="Resources Monitor",
        description="CPU, RAM, and network monitor",
        desktop=DesktopEnv.KDE,
        packages={
            'arch': ['plasma5-applets-resources-monitor'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        kde_store_id="1527636"
    ),
    Extension(
        id="kde-window-title",
        name="Window Title",
        description="Show active window title in panel",
        desktop=DesktopEnv.KDE,
        packages={
            'arch': ['plasma5-applets-window-title'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        kde_store_id="1274218"
    ),
    Extension(
        id="kde-window-buttons",
        name="Window Buttons",
        description="Window controls in panel (like macOS)",
        desktop=DesktopEnv.KDE,
        packages={
            'arch': ['plasma5-applets-window-buttons'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        kde_store_id="1274218"
    ),
    Extension(
        id="kde-netspeed",
        name="Netspeed Widget",
        description="Network speed indicator",
        desktop=DesktopEnv.KDE,
        packages={
            'arch': ['plasma5-applets-netspeed'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        kde_store_id="998895"
    ),
    Extension(
        id="kde-simple-menu",
        name="Simple Menu",
        description="Clean, categorized app menu",
        desktop=DesktopEnv.KDE,
        packages={
            'arch': [],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        kde_store_id="1169537"
    ),
    Extension(
        id="kde-panel-spacer",
        name="Panel Spacer Extended",
        description="Flexible panel spacer with features",
        desktop=DesktopEnv.KDE,
        packages={
            'arch': [],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        kde_store_id="1361598"
    ),
]


# =============================================================================
# KDE Global Themes
# =============================================================================

KDE_GLOBAL_THEMES = [
    Theme(
        id="kde-breeze",
        name="Breeze",
        theme_type=ThemeType.PLASMA,
        description="KDE's default modern theme",
        packages={
            'arch': ['breeze'],
            'fedora': ['breeze-gtk'],
            'debian': ['breeze'],
            'opensuse': ['breeze5-style'],
        },
        plasma_theme="breeze"
    ),
    Theme(
        id="kde-breeze-dark",
        name="Breeze Dark",
        theme_type=ThemeType.PLASMA,
        description="KDE's dark variant",
        packages={
            'arch': ['breeze'],
            'fedora': ['breeze-gtk'],
            'debian': ['breeze'],
            'opensuse': ['breeze5-style'],
        },
        plasma_theme="breeze-dark"
    ),
    Theme(
        id="kde-oxygen",
        name="Oxygen",
        theme_type=ThemeType.PLASMA,
        description="Classic KDE theme",
        packages={
            'arch': ['oxygen'],
            'fedora': ['oxygen'],
            'debian': ['oxygen-icon-theme'],
            'opensuse': ['oxygen5-style'],
        },
        plasma_theme="oxygen"
    ),
    Theme(
        id="kde-nordic",
        name="Nordic",
        theme_type=ThemeType.PLASMA,
        description="Nord color scheme for KDE",
        packages={
            'arch': ['nordic-kde-git'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        plasma_theme="Nordic"
    ),
    Theme(
        id="kde-layan",
        name="Layan",
        theme_type=ThemeType.PLASMA,
        description="Flat material design theme",
        packages={
            'arch': ['layan-kde-git'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        plasma_theme="Layan"
    ),
    Theme(
        id="kde-sweet",
        name="Sweet",
        theme_type=ThemeType.PLASMA,
        description="Gradient dark theme",
        packages={
            'arch': ['sweet-kde-git'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        plasma_theme="Sweet"
    ),
    Theme(
        id="kde-orchis",
        name="Orchis",
        theme_type=ThemeType.PLASMA,
        description="Clean material design theme",
        packages={
            'arch': ['orchis-kde-theme-git'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        plasma_theme="Orchis"
    ),
]


# =============================================================================
# Kvantum Themes
# =============================================================================

KVANTUM_THEMES = [
    Theme(
        id="kvantum-adapta",
        name="Adapta",
        theme_type=ThemeType.KVANTUM,
        description="Material design Kvantum theme",
        packages={
            'arch': ['kvantum-theme-adapta'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        kvantum_theme="KvAdapta"
    ),
    Theme(
        id="kvantum-arc",
        name="Arc",
        theme_type=ThemeType.KVANTUM,
        description="Arc theme for Qt apps",
        packages={
            'arch': ['kvantum-theme-arc'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        kvantum_theme="KvArc"
    ),
    Theme(
        id="kvantum-materia",
        name="Materia",
        theme_type=ThemeType.KVANTUM,
        description="Materia for Qt apps",
        packages={
            'arch': ['kvantum-theme-materia'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        kvantum_theme="KvMateria"
    ),
    Theme(
        id="kvantum-nordic",
        name="Nordic",
        theme_type=ThemeType.KVANTUM,
        description="Nord theme for Qt apps",
        packages={
            'arch': ['kvantum-theme-nordic-git'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        kvantum_theme="Nordic"
    ),
    Theme(
        id="kvantum-sweet",
        name="Sweet",
        theme_type=ThemeType.KVANTUM,
        description="Sweet gradient theme for Qt",
        packages={
            'arch': ['kvantum-theme-sweet-git'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        kvantum_theme="Sweet"
    ),
    Theme(
        id="kvantum-catppuccin",
        name="Catppuccin",
        theme_type=ThemeType.KVANTUM,
        description="Catppuccin for Qt apps",
        packages={
            'arch': ['kvantum-theme-catppuccin-git'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        kvantum_theme="Catppuccin-Mocha-Blue"
    ),
]


# =============================================================================
# KWin Scripts
# =============================================================================

KWIN_SCRIPTS = [
    Extension(
        id="kwin-bismuth",
        name="Bismuth",
        description="Dynamic tiling extension for KDE",
        desktop=DesktopEnv.KDE,
        packages={
            'arch': ['kwin-bismuth'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        kde_store_id="1484226"
    ),
    Extension(
        id="kwin-krohnkite",
        name="Krohnkite",
        description="Dynamic tiling (legacy, Plasma 5)",
        desktop=DesktopEnv.KDE,
        packages={
            'arch': ['kwin-scripts-krohnkite'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        kde_store_id="1281790"
    ),
    Extension(
        id="kwin-forceblur",
        name="Force Blur",
        description="Force blur effect on windows",
        desktop=DesktopEnv.KDE,
        packages={
            'arch': ['kwin-scripts-forceblur'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        kde_store_id="1294604"
    ),
    Extension(
        id="kwin-geometry-change",
        name="Geometry Change",
        description="Animate window geometry changes",
        desktop=DesktopEnv.KDE,
        packages={
            'arch': [],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        kde_store_id="1370281"
    ),
    Extension(
        id="kwin-sticky-window-snapping",
        name="Sticky Window Snapping",
        description="Snap windows to each other",
        desktop=DesktopEnv.KDE,
        packages={
            'arch': [],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        kde_store_id="1112552"
    ),
]


# =============================================================================
# KDE Tweaks
# =============================================================================

KDE_TWEAKS = [
    Tweak(
        id="kde-single-click",
        name="Single Click to Open",
        description="Open files with single click",
        desktop=DesktopEnv.KDE,
        kconfig_file="~/.config/kdeglobals",
        kconfig_group="KDE",
        kconfig_key="SingleClick",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="kde-animations",
        name="Animations",
        description="Enable desktop animations",
        desktop=DesktopEnv.KDE,
        kconfig_file="~/.config/kwinrc",
        kconfig_group="Compositing",
        kconfig_key="AnimationSpeed",
        is_toggle=False,
        enabled_value="3",
        disabled_value="0"
    ),
    Tweak(
        id="kde-blur",
        name="Blur Effect",
        description="Enable blur behind windows",
        desktop=DesktopEnv.KDE,
        kconfig_file="~/.config/kwinrc",
        kconfig_group="Plugins",
        kconfig_key="blurEnabled",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="kde-wobbly",
        name="Wobbly Windows",
        description="Windows wobble when moved",
        desktop=DesktopEnv.KDE,
        kconfig_file="~/.config/kwinrc",
        kconfig_group="Plugins",
        kconfig_key="wobblywindowsEnabled",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="kde-magic-lamp",
        name="Magic Lamp Minimize",
        description="Genie effect when minimizing",
        desktop=DesktopEnv.KDE,
        kconfig_file="~/.config/kwinrc",
        kconfig_group="Plugins",
        kconfig_key="magiclampEnabled",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="kde-overview",
        name="Overview Effect",
        description="macOS-style window overview",
        desktop=DesktopEnv.KDE,
        kconfig_file="~/.config/kwinrc",
        kconfig_group="Plugins",
        kconfig_key="overviewEnabled",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="kde-cube",
        name="Desktop Cube",
        description="3D cube virtual desktop switcher",
        desktop=DesktopEnv.KDE,
        kconfig_file="~/.config/kwinrc",
        kconfig_group="Plugins",
        kconfig_key="cubeEnabled",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
]


# =============================================================================
# XFCE Tweaks (for xfconf-query)
# =============================================================================

XFCE_TWEAKS = [
    Tweak(
        id="xfce-compositing",
        name="Compositing",
        description="Enable window compositing",
        desktop=DesktopEnv.XFCE,
        xfconf_channel="xfwm4",
        xfconf_property="/general/use_compositing",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="xfce-shadows",
        name="Window Shadows",
        description="Show shadows under windows",
        desktop=DesktopEnv.XFCE,
        xfconf_channel="xfwm4",
        xfconf_property="/general/show_dock_shadow",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="xfce-box-move",
        name="Box Move/Resize",
        description="Show outline when moving windows",
        desktop=DesktopEnv.XFCE,
        xfconf_channel="xfwm4",
        xfconf_property="/general/box_move",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="xfce-cycle-preview",
        name="Alt-Tab Preview",
        description="Show window preview in Alt-Tab",
        desktop=DesktopEnv.XFCE,
        xfconf_channel="xfwm4",
        xfconf_property="/general/cycle_preview",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="xfce-wrap-windows",
        name="Wrap Windows on Screen Edge",
        description="Windows wrap to opposite edge",
        desktop=DesktopEnv.XFCE,
        xfconf_channel="xfwm4",
        xfconf_property="/general/wrap_windows",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="xfce-tile-on-drag",
        name="Tile on Drag to Edge",
        description="Snap windows when dragged to edge",
        desktop=DesktopEnv.XFCE,
        xfconf_channel="xfwm4",
        xfconf_property="/general/tile_on_move",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
]


# =============================================================================
# XFCE Compositor Tools
# =============================================================================

XFCE_COMPOSITOR_TOOLS = [
    Tool(
        id="picom",
        name="Picom",
        description="Modern X11 compositor (fork of compton)",
        packages={
            'arch': ['picom'],
            'fedora': ['picom'],
            'debian': ['picom'],
            'opensuse': ['picom'],
        },
        desktop=DesktopEnv.XFCE
    ),
    Tool(
        id="compton",
        name="Compton",
        description="Lightweight X11 compositor",
        packages={
            'arch': ['compton'],
            'fedora': ['compton'],
            'debian': ['compton'],
            'opensuse': ['compton'],
        },
        desktop=DesktopEnv.XFCE
    ),
    Tool(
        id="xfce4-settings",
        name="XFCE Settings Manager",
        description="XFCE settings (usually pre-installed)",
        packages={
            'arch': ['xfce4-settings'],
            'fedora': ['xfce4-settings'],
            'debian': ['xfce4-settings'],
            'opensuse': ['xfce4-settings'],
        },
        desktop=DesktopEnv.XFCE
    ),
]


# =============================================================================
# Cinnamon Applets (Panel Addons)
# =============================================================================

CINNAMON_APPLETS = [
    Extension(
        id="cinnamon-weather",
        name="Weather Applet",
        description="Weather information in panel",
        desktop=DesktopEnv.CINNAMON,
        packages={
            'arch': ['cinnamon'],  # Built-in, just need cinnamon
            'fedora': ['cinnamon'],
            'debian': ['cinnamon'],
            'opensuse': ['cinnamon'],
        }
    ),
    Extension(
        id="cinnamon-calendar",
        name="Calendar Applet",
        description="Calendar with events integration",
        desktop=DesktopEnv.CINNAMON,
        packages={
            'arch': ['cinnamon'],
            'fedora': ['cinnamon'],
            'debian': ['cinnamon'],
            'opensuse': ['cinnamon'],
        }
    ),
    Extension(
        id="cinnamon-removable-drives",
        name="Removable Drives",
        description="Quick access to USB drives and media",
        desktop=DesktopEnv.CINNAMON,
        packages={
            'arch': ['cinnamon'],
            'fedora': ['cinnamon'],
            'debian': ['cinnamon'],
            'opensuse': ['cinnamon'],
        }
    ),
    Extension(
        id="cinnamon-system-monitor",
        name="System Monitor",
        description="CPU, memory, and network monitor",
        desktop=DesktopEnv.CINNAMON,
        packages={
            'arch': ['cinnamon'],
            'fedora': ['cinnamon'],
            'debian': ['cinnamon'],
            'opensuse': ['cinnamon'],
        }
    ),
    Extension(
        id="cinnamon-workspace-switcher",
        name="Workspace Switcher",
        description="Visual workspace switcher in panel",
        desktop=DesktopEnv.CINNAMON,
        packages={
            'arch': ['cinnamon'],
            'fedora': ['cinnamon'],
            'debian': ['cinnamon'],
            'opensuse': ['cinnamon'],
        }
    ),
    Extension(
        id="cinnamon-timer",
        name="Timer Applet",
        description="Countdown timer and stopwatch",
        desktop=DesktopEnv.CINNAMON,
        packages={
            'arch': ['cinnamon'],
            'fedora': ['cinnamon'],
            'debian': ['cinnamon'],
            'opensuse': ['cinnamon'],
        }
    ),
]


# =============================================================================
# Cinnamon Spices (Extensions/Desklets/Themes)
# =============================================================================

CINNAMON_EXTENSIONS = [
    Extension(
        id="cinnamon-transparent-panels",
        name="Transparent Panels",
        description="Make panels transparent or semi-transparent",
        desktop=DesktopEnv.CINNAMON,
        packages={
            'arch': ['cinnamon'],
            'fedora': ['cinnamon'],
            'debian': ['cinnamon'],
            'opensuse': ['cinnamon'],
        }
    ),
    Extension(
        id="cinnamon-blur-overview",
        name="Blur Overview",
        description="Add blur effect to overview/expo",
        desktop=DesktopEnv.CINNAMON,
        packages={
            'arch': ['cinnamon'],
            'fedora': ['cinnamon'],
            'debian': ['cinnamon'],
            'opensuse': ['cinnamon'],
        }
    ),
    Extension(
        id="cinnamon-workspace-grid",
        name="Workspace Grid",
        description="Arrange workspaces in a grid",
        desktop=DesktopEnv.CINNAMON,
        packages={
            'arch': ['cinnamon'],
            'fedora': ['cinnamon'],
            'debian': ['cinnamon'],
            'opensuse': ['cinnamon'],
        }
    ),
    Extension(
        id="cinnamon-gTile",
        name="gTile",
        description="Window tiling and snapping",
        desktop=DesktopEnv.CINNAMON,
        packages={
            'arch': ['cinnamon'],
            'fedora': ['cinnamon'],
            'debian': ['cinnamon'],
            'opensuse': ['cinnamon'],
        }
    ),
]


# =============================================================================
# Cinnamon Tweaks (gsettings-based, similar to GNOME)
# =============================================================================

CINNAMON_TWEAKS = [
    Tweak(
        id="cinnamon-desktop-effects",
        name="Desktop Effects",
        description="Enable animations and effects",
        desktop=DesktopEnv.CINNAMON,
        gsettings_schema="org.cinnamon",
        gsettings_key="desktop-effects",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="cinnamon-startup-animation",
        name="Startup Animation",
        description="Show animation when Cinnamon starts",
        desktop=DesktopEnv.CINNAMON,
        gsettings_schema="org.cinnamon",
        gsettings_key="startup-animation",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="cinnamon-workspace-osd",
        name="Workspace OSD",
        description="Show workspace name on switch",
        desktop=DesktopEnv.CINNAMON,
        gsettings_schema="org.cinnamon",
        gsettings_key="workspace-osd-visible",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="cinnamon-panels-autohide",
        name="Panel Auto-hide",
        description="Automatically hide panels",
        desktop=DesktopEnv.CINNAMON,
        gsettings_schema="org.cinnamon",
        gsettings_key="panels-autohide",
        is_toggle=True,
        enabled_value="['1:true']",
        disabled_value="['1:false']"
    ),
    Tweak(
        id="cinnamon-hot-corner",
        name="Hot Corner",
        description="Enable hot corner for overview",
        desktop=DesktopEnv.CINNAMON,
        gsettings_schema="org.cinnamon",
        gsettings_key="overview-activation-mode",
        is_toggle=True,
        enabled_value="'corner'",
        disabled_value="'none'"
    ),
    Tweak(
        id="cinnamon-snap-osd",
        name="Snap OSD",
        description="Show OSD when snapping windows",
        desktop=DesktopEnv.CINNAMON,
        gsettings_schema="org.cinnamon.muffin",
        gsettings_key="tile-hud-threshold",
        is_toggle=True,
        enabled_value="25",
        disabled_value="0"
    ),
    Tweak(
        id="cinnamon-window-animations",
        name="Window Animations",
        description="Animate window open/close/minimize",
        desktop=DesktopEnv.CINNAMON,
        gsettings_schema="org.cinnamon",
        gsettings_key="desktop-effects-close",
        is_toggle=True,
        enabled_value="'traditional'",
        disabled_value="'none'"
    ),
    Tweak(
        id="cinnamon-show-desktop-icons",
        name="Show Desktop Icons",
        description="Display icons on desktop",
        desktop=DesktopEnv.CINNAMON,
        gsettings_schema="org.nemo.desktop",
        gsettings_key="show-desktop-icons",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="cinnamon-invert-scroll",
        name="Natural Scrolling",
        description="Reverse scroll direction (natural)",
        desktop=DesktopEnv.CINNAMON,
        gsettings_schema="org.cinnamon.desktop.peripherals.touchpad",
        gsettings_key="natural-scroll",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="cinnamon-edge-tiling",
        name="Edge Tiling",
        description="Snap windows when dragged to edge",
        desktop=DesktopEnv.CINNAMON,
        gsettings_schema="org.cinnamon.muffin",
        gsettings_key="edge-tiling",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
]


# =============================================================================
# Cinnamon Tools
# =============================================================================

CINNAMON_TOOLS = [
    Tool(
        id="cinnamon-settings",
        name="Cinnamon Settings",
        description="Cinnamon system settings (usually pre-installed)",
        packages={
            'arch': ['cinnamon-settings-daemon'],
            'fedora': ['cinnamon-settings-daemon'],
            'debian': ['cinnamon-settings-daemon'],
            'opensuse': ['cinnamon-settings-daemon'],
        },
        desktop=DesktopEnv.CINNAMON
    ),
    Tool(
        id="nemo",
        name="Nemo File Manager",
        description="Cinnamon's powerful file manager",
        packages={
            'arch': ['nemo', 'nemo-fileroller', 'nemo-preview'],
            'fedora': ['nemo', 'nemo-fileroller', 'nemo-preview'],
            'debian': ['nemo', 'nemo-fileroller', 'nemo-preview'],
            'opensuse': ['nemo', 'nemo-extension-fileroller', 'nemo-extension-preview'],
        },
        desktop=DesktopEnv.CINNAMON
    ),
    Tool(
        id="nemo-extensions",
        name="Nemo Extensions Pack",
        description="Additional Nemo plugins and features",
        packages={
            'arch': ['nemo-share', 'nemo-terminal', 'nemo-python'],
            'fedora': ['nemo-extensions'],
            'debian': ['nemo-gtkhash', 'nemo-compare', 'nemo-terminal'],
            'opensuse': ['nemo-extension-share', 'nemo-extension-terminal'],
        },
        desktop=DesktopEnv.CINNAMON
    ),
    Tool(
        id="cinnamon-screensaver",
        name="Cinnamon Screensaver",
        description="Lock screen and screensaver",
        packages={
            'arch': ['cinnamon-screensaver'],
            'fedora': ['cinnamon-screensaver'],
            'debian': ['cinnamon-screensaver'],
            'opensuse': ['cinnamon-screensaver'],
        },
        desktop=DesktopEnv.CINNAMON
    ),
    Tool(
        id="mint-themes",
        name="Mint Themes Collection",
        description="Linux Mint's beautiful theme collection",
        packages={
            'arch': ['mint-themes'],  # AUR
            'fedora': [],  # Manual install
            'debian': ['mint-themes', 'mint-y-icons'],
            'opensuse': [],  # Manual install
        },
        desktop=DesktopEnv.CINNAMON
    ),
    Tool(
        id="cinnamon-control-center",
        name="Control Center",
        description="Cinnamon Control Center for system settings",
        packages={
            'arch': ['cinnamon-control-center'],
            'fedora': ['cinnamon-control-center'],
            'debian': ['cinnamon-control-center'],
            'opensuse': ['cinnamon-control-center'],
        },
        desktop=DesktopEnv.CINNAMON
    ),
]


# =============================================================================
# MATE Panel Applets
# =============================================================================

MATE_APPLETS = [
    Extension(
        id="mate-sensors-applet",
        name="Sensors Applet",
        description="Hardware sensors monitoring",
        desktop=DesktopEnv.MATE,
        packages={
            'arch': ['mate-sensors-applet'],
            'fedora': ['mate-sensors-applet'],
            'debian': ['mate-sensors-applet'],
            'opensuse': ['mate-sensors-applet'],
        }
    ),
    Extension(
        id="mate-netspeed",
        name="Netspeed Applet",
        description="Network speed monitor in panel",
        desktop=DesktopEnv.MATE,
        packages={
            'arch': ['mate-netspeed'],
            'fedora': ['mate-netspeed'],
            'debian': ['mate-netspeed'],
            'opensuse': ['mate-netspeed'],
        }
    ),
    Extension(
        id="mate-applet-dock",
        name="Dock Applet",
        description="Application dock for MATE panel",
        desktop=DesktopEnv.MATE,
        packages={
            'arch': ['mate-applet-dock'],
            'fedora': ['mate-applet-dock'],
            'debian': ['mate-dock-applet'],
            'opensuse': ['mate-applet-dock'],
        }
    ),
    Extension(
        id="mate-applet-brisk-menu",
        name="Brisk Menu",
        description="Modern application menu for MATE",
        desktop=DesktopEnv.MATE,
        packages={
            'arch': ['brisk-menu'],
            'fedora': ['brisk-menu'],
            'debian': ['brisk-menu'],
            'opensuse': ['brisk-menu'],
        }
    ),
    Extension(
        id="mate-indicator-applet",
        name="Indicator Applet",
        description="Application indicators in panel",
        desktop=DesktopEnv.MATE,
        packages={
            'arch': ['mate-indicator-applet'],
            'fedora': ['mate-indicator-applet'],
            'debian': ['mate-indicator-applet'],
            'opensuse': ['mate-indicator-applet'],
        }
    ),
    Extension(
        id="mate-media",
        name="Media Applet",
        description="Volume control applet",
        desktop=DesktopEnv.MATE,
        packages={
            'arch': ['mate-media'],
            'fedora': ['mate-media'],
            'debian': ['mate-media'],
            'opensuse': ['mate-media'],
        }
    ),
]


# =============================================================================
# MATE Tweaks (gsettings-based via org.mate.*)
# =============================================================================

MATE_TWEAKS = [
    Tweak(
        id="mate-compositing",
        name="Compositing Manager",
        description="Enable window compositing effects",
        desktop=DesktopEnv.MATE,
        gsettings_schema="org.mate.Marco.general",
        gsettings_key="compositing-manager",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="mate-animations",
        name="Window Animations",
        description="Enable window animations",
        desktop=DesktopEnv.MATE,
        gsettings_schema="org.mate.Marco.general",
        gsettings_key="reduced-resources",
        is_toggle=True,
        enabled_value="false",  # Inverted - reduced resources = no animations
        disabled_value="true"
    ),
    Tweak(
        id="mate-show-desktop-icons",
        name="Show Desktop Icons",
        description="Display icons on desktop",
        desktop=DesktopEnv.MATE,
        gsettings_schema="org.mate.caja.desktop",
        gsettings_key="show-desktop-icons",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="mate-trash-icon",
        name="Show Trash on Desktop",
        description="Display trash icon on desktop",
        desktop=DesktopEnv.MATE,
        gsettings_schema="org.mate.caja.desktop",
        gsettings_key="trash-icon-visible",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="mate-home-icon",
        name="Show Home on Desktop",
        description="Display home folder on desktop",
        desktop=DesktopEnv.MATE,
        gsettings_schema="org.mate.caja.desktop",
        gsettings_key="home-icon-visible",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="mate-computer-icon",
        name="Show Computer on Desktop",
        description="Display computer icon on desktop",
        desktop=DesktopEnv.MATE,
        gsettings_schema="org.mate.caja.desktop",
        gsettings_key="computer-icon-visible",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="mate-center-new-windows",
        name="Center New Windows",
        description="Open new windows in center of screen",
        desktop=DesktopEnv.MATE,
        gsettings_schema="org.mate.Marco.general",
        gsettings_key="center-new-windows",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="mate-edge-tiling",
        name="Edge Tiling",
        description="Snap windows when dragged to edge",
        desktop=DesktopEnv.MATE,
        gsettings_schema="org.mate.Marco.general",
        gsettings_key="side-by-side-tiling",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="mate-show-hidden-files",
        name="Show Hidden Files",
        description="Show hidden files in Caja by default",
        desktop=DesktopEnv.MATE,
        gsettings_schema="org.mate.caja.preferences",
        gsettings_key="show-hidden-files",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="mate-thumbnails",
        name="Show Thumbnails",
        description="Show file thumbnails in Caja",
        desktop=DesktopEnv.MATE,
        gsettings_schema="org.mate.caja.preferences",
        gsettings_key="show-image-thumbnails",
        is_toggle=True,
        enabled_value="'always'",
        disabled_value="'never'"
    ),
]


# =============================================================================
# MATE Tools
# =============================================================================

MATE_TOOLS = [
    Tool(
        id="mate-tweak",
        name="MATE Tweak",
        description="Advanced MATE desktop customization",
        packages={
            'arch': ['mate-tweak'],
            'fedora': ['mate-tweak'],
            'debian': ['mate-tweak'],
            'opensuse': ['mate-tweak'],
        },
        desktop=DesktopEnv.MATE
    ),
    Tool(
        id="caja",
        name="Caja File Manager",
        description="MATE's file manager (usually pre-installed)",
        packages={
            'arch': ['caja', 'caja-extensions-common'],
            'fedora': ['caja', 'caja-extensions'],
            'debian': ['caja', 'caja-common'],
            'opensuse': ['caja', 'caja-extensions'],
        },
        desktop=DesktopEnv.MATE
    ),
    Tool(
        id="caja-extensions",
        name="Caja Extensions",
        description="Additional Caja plugins",
        packages={
            'arch': ['caja-share', 'caja-wallpaper', 'caja-xattr-tags', 'caja-open-terminal'],
            'fedora': ['caja-share', 'caja-image-converter', 'caja-open-terminal'],
            'debian': ['caja-share', 'caja-image-converter', 'caja-open-terminal', 'caja-wallpaper'],
            'opensuse': ['caja-extension-share', 'caja-extension-open-terminal'],
        },
        desktop=DesktopEnv.MATE
    ),
    Tool(
        id="pluma",
        name="Pluma Text Editor",
        description="MATE's text editor",
        packages={
            'arch': ['pluma'],
            'fedora': ['pluma'],
            'debian': ['pluma'],
            'opensuse': ['pluma'],
        },
        desktop=DesktopEnv.MATE
    ),
    Tool(
        id="atril",
        name="Atril Document Viewer",
        description="MATE's PDF and document viewer",
        packages={
            'arch': ['atril'],
            'fedora': ['atril'],
            'debian': ['atril'],
            'opensuse': ['atril'],
        },
        desktop=DesktopEnv.MATE
    ),
    Tool(
        id="engrampa",
        name="Engrampa Archive Manager",
        description="MATE's archive manager",
        packages={
            'arch': ['engrampa'],
            'fedora': ['engrampa'],
            'debian': ['engrampa'],
            'opensuse': ['engrampa'],
        },
        desktop=DesktopEnv.MATE
    ),
    Tool(
        id="eom",
        name="Eye of MATE",
        description="MATE's image viewer",
        packages={
            'arch': ['eom'],
            'fedora': ['eom'],
            'debian': ['eom'],
            'opensuse': ['eom'],
        },
        desktop=DesktopEnv.MATE
    ),
    Tool(
        id="mate-calc",
        name="MATE Calculator",
        description="Calculator application",
        packages={
            'arch': ['mate-calc'],
            'fedora': ['mate-calc'],
            'debian': ['mate-calc'],
            'opensuse': ['mate-calc'],
        },
        desktop=DesktopEnv.MATE
    ),
    Tool(
        id="mate-system-monitor",
        name="MATE System Monitor",
        description="System resource monitor",
        packages={
            'arch': ['mate-system-monitor'],
            'fedora': ['mate-system-monitor'],
            'debian': ['mate-system-monitor'],
            'opensuse': ['mate-system-monitor'],
        },
        desktop=DesktopEnv.MATE
    ),
]


# =============================================================================
# Theme Presets
# =============================================================================

@dataclass
class ThemePreset:
    """A complete theme preset combining GTK, icons, cursors."""
    id: str
    name: str
    description: str
    gtk_theme: str
    icon_theme: str
    cursor_theme: str
    shell_theme: str = ""  # GNOME Shell
    plasma_theme: str = ""  # KDE Global
    kvantum_theme: str = ""  # Qt apps
    wallpaper_hint: str = ""  # Suggested wallpaper style


THEME_PRESETS = [
    ThemePreset(
        id="preset-dark-modern",
        name="Dark Modern",
        description="Sleek dark theme with blue accents",
        gtk_theme="Adwaita-dark",
        icon_theme="Papirus-Dark",
        cursor_theme="Adwaita",
        shell_theme="",
        wallpaper_hint="Dark abstract or geometric"
    ),
    ThemePreset(
        id="preset-nordic",
        name="Nordic",
        description="Cool blue Nord color scheme",
        gtk_theme="Nordic",
        icon_theme="Papirus-Dark",
        cursor_theme="Bibata-Modern-Classic",
        shell_theme="Nordic",
        plasma_theme="Nordic",
        kvantum_theme="Nordic",
        wallpaper_hint="Mountains, snow, northern lights"
    ),
    ThemePreset(
        id="preset-dracula",
        name="Dracula",
        description="Popular purple dark theme",
        gtk_theme="Dracula",
        icon_theme="Papirus-Dark",
        cursor_theme="Bibata-Modern-Classic",
        wallpaper_hint="Dark purple or gothic"
    ),
    ThemePreset(
        id="preset-catppuccin",
        name="Catppuccin Mocha",
        description="Soothing pastel dark theme",
        gtk_theme="Catppuccin-Mocha-Standard-Blue-Dark",
        icon_theme="Papirus-Dark",
        cursor_theme="Bibata-Modern-Classic",
        kvantum_theme="Catppuccin-Mocha-Blue",
        wallpaper_hint="Cozy, warm colors"
    ),
    ThemePreset(
        id="preset-arc",
        name="Arc",
        description="Classic flat design",
        gtk_theme="Arc-Dark",
        icon_theme="Papirus-Dark",
        cursor_theme="Adwaita",
        kvantum_theme="KvArc",
        wallpaper_hint="Minimal geometric"
    ),
    ThemePreset(
        id="preset-material",
        name="Material Design",
        description="Google Material Design aesthetic",
        gtk_theme="Materia-dark",
        icon_theme="Papirus",
        cursor_theme="Adwaita",
        kvantum_theme="KvMateria",
        wallpaper_hint="Colorful gradients"
    ),
    ThemePreset(
        id="preset-macos-light",
        name="macOS Light",
        description="Approximate macOS Sonoma light look",
        gtk_theme="Adwaita",
        icon_theme="La-Capitaine",
        cursor_theme="capitaine-cursors",
        wallpaper_hint="Bright, colorful abstract"
    ),
    ThemePreset(
        id="preset-macos-dark",
        name="macOS Dark",
        description="Approximate macOS dark look",
        gtk_theme="Adwaita-dark",
        icon_theme="La-Capitaine",
        cursor_theme="capitaine-cursors",
        wallpaper_hint="Dark abstract"
    ),
    ThemePreset(
        id="preset-windows11",
        name="Windows 11 Style",
        description="Approximate Windows 11 aesthetic",
        gtk_theme="Adwaita",
        icon_theme="Papirus",
        cursor_theme="Adwaita",
        wallpaper_hint="Flowing abstract, blue tones"
    ),
    ThemePreset(
        id="preset-gruvbox",
        name="Gruvbox",
        description="Retro groove color scheme",
        gtk_theme="Gruvbox-Dark",
        icon_theme="Papirus-Dark",
        cursor_theme="Bibata-Modern-Classic",
        wallpaper_hint="Retro, warm earth tones"
    ),
]


# =============================================================================
# Universal Tools
# =============================================================================

UNIVERSAL_TOOLS = [
    Tool(
        id="gnome-tweaks",
        name="GNOME Tweaks",
        description="Advanced GNOME settings",
        packages={
            'arch': ['gnome-tweaks'],
            'fedora': ['gnome-tweaks'],
            'debian': ['gnome-tweaks'],
            'opensuse': ['gnome-tweaks'],
        },
        desktop=DesktopEnv.GNOME
    ),
    Tool(
        id="extension-manager",
        name="Extension Manager",
        description="Browse and install GNOME extensions",
        packages={
            'arch': ['extension-manager'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        flatpak_id="com.mattjakeman.ExtensionManager",
        desktop=DesktopEnv.GNOME
    ),
    Tool(
        id="dconf-editor",
        name="dconf Editor",
        description="Advanced GNOME settings editor",
        packages={
            'arch': ['dconf-editor'],
            'fedora': ['dconf-editor'],
            'debian': ['dconf-editor'],
            'opensuse': ['dconf-editor'],
        },
        desktop=DesktopEnv.GNOME
    ),
    Tool(
        id="kvantum",
        name="Kvantum Manager",
        description="Qt theme engine and manager",
        packages={
            'arch': ['kvantum'],
            'fedora': ['kvantum'],
            'debian': ['qt5-style-kvantum', 'qt5-style-kvantum-themes'],
            'opensuse': ['kvantum-manager'],
        },
        desktop=DesktopEnv.KDE
    ),
    Tool(
        id="lxappearance",
        name="LXAppearance",
        description="GTK theme switcher",
        packages={
            'arch': ['lxappearance'],
            'fedora': ['lxappearance'],
            'debian': ['lxappearance'],
            'opensuse': ['lxappearance'],
        },
    ),
    Tool(
        id="qt5ct",
        name="Qt5 Settings",
        description="Configure Qt5 appearance",
        packages={
            'arch': ['qt5ct'],
            'fedora': ['qt5ct'],
            'debian': ['qt5ct'],
            'opensuse': ['qt5ct'],
        },
    ),
    Tool(
        id="qt6ct",
        name="Qt6 Settings",
        description="Configure Qt6 appearance",
        packages={
            'arch': ['qt6ct'],
            'fedora': ['qt6ct'],
            'debian': [],
            'opensuse': ['qt6ct'],
        },
    ),
    Tool(
        id="flameshot",
        name="Flameshot",
        description="Powerful screenshot tool",
        packages={
            'arch': ['flameshot'],
            'fedora': ['flameshot'],
            'debian': ['flameshot'],
            'opensuse': ['flameshot'],
        },
    ),
    Tool(
        id="variety",
        name="Variety",
        description="Wallpaper changer",
        packages={
            'arch': ['variety'],
            'fedora': ['variety'],
            'debian': ['variety'],
            'opensuse': ['variety'],
        },
    ),
    Tool(
        id="conky",
        name="Conky",
        description="Desktop system monitor",
        packages={
            'arch': ['conky'],
            'fedora': ['conky'],
            'debian': ['conky-all'],
            'opensuse': ['conky'],
        },
    ),
    Tool(
        id="plank",
        name="Plank",
        description="Simple dock application",
        packages={
            'arch': ['plank'],
            'fedora': ['plank'],
            'debian': ['plank'],
            'opensuse': ['plank'],
        },
    ),
    Tool(
        id="ulauncher",
        name="Ulauncher",
        description="Application launcher",
        packages={
            'arch': ['ulauncher'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
        flatpak_id="io.ulauncher.Ulauncher"
    ),
    Tool(
        id="albert",
        name="Albert",
        description="Keyboard launcher",
        packages={
            'arch': ['albert'],
            'fedora': [],
            'debian': [],
            'opensuse': ['albert'],
        },
    ),
]

FONT_PACKAGES = [
    Tool(
        id="nerd-fonts",
        name="Nerd Fonts",
        description="Patched fonts with icons",
        packages={
            'arch': ['ttf-jetbrains-mono-nerd', 'ttf-firacode-nerd', 'ttf-hack-nerd'],
            'fedora': [],
            'debian': [],
            'opensuse': [],
        },
    ),
    Tool(
        id="fira-code",
        name="Fira Code",
        description="Monospace font with ligatures",
        packages={
            'arch': ['ttf-fira-code'],
            'fedora': ['fira-code-fonts'],
            'debian': ['fonts-firacode'],
            'opensuse': ['fira-code-fonts'],
        },
    ),
    Tool(
        id="jetbrains-mono",
        name="JetBrains Mono",
        description="Developer font by JetBrains",
        packages={
            'arch': ['ttf-jetbrains-mono'],
            'fedora': ['jetbrains-mono-fonts-all'],
            'debian': ['fonts-jetbrains-mono'],
            'opensuse': ['jetbrains-mono-fonts'],
        },
    ),
    Tool(
        id="inter",
        name="Inter",
        description="Modern UI font",
        packages={
            'arch': ['inter-font'],
            'fedora': ['inter-fonts'],
            'debian': ['fonts-inter'],
            'opensuse': ['inter-fonts'],
        },
    ),
    Tool(
        id="roboto",
        name="Roboto",
        description="Google's Roboto font family",
        packages={
            'arch': ['ttf-roboto'],
            'fedora': ['google-roboto-fonts'],
            'debian': ['fonts-roboto'],
            'opensuse': ['google-roboto-fonts'],
        },
    ),
    Tool(
        id="noto",
        name="Noto Fonts",
        description="Google's universal font family",
        packages={
            'arch': ['noto-fonts', 'noto-fonts-emoji'],
            'fedora': ['google-noto-fonts-common', 'google-noto-emoji-fonts'],
            'debian': ['fonts-noto', 'fonts-noto-color-emoji'],
            'opensuse': ['noto-fonts', 'noto-coloremoji-fonts'],
        },
    ),
    Tool(
        id="ubuntu-fonts",
        name="Ubuntu Fonts",
        description="Ubuntu font family",
        packages={
            'arch': ['ttf-ubuntu-font-family'],
            'fedora': [],
            'debian': ['fonts-ubuntu'],
            'opensuse': ['ubuntu-fonts'],
        },
    ),
]


# =============================================================================
# GNOME Tweaks (gsettings-based)
# =============================================================================

GNOME_TWEAKS = [
    # === Window Behavior ===
    Tweak(
        id="titlebar-buttons",
        name="Show Minimize/Maximize Buttons",
        description="Add min/max buttons to window titlebars",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.desktop.wm.preferences",
        gsettings_key="button-layout",
        gsettings_value="appmenu:minimize,maximize,close",
        is_toggle=True,
        enabled_value="appmenu:minimize,maximize,close",
        disabled_value="appmenu:close"
    ),
    Tweak(
        id="center-new-windows",
        name="Center New Windows",
        description="Open new windows in center of screen",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.mutter",
        gsettings_key="center-new-windows",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="edge-tiling",
        name="Edge Tiling",
        description="Tile windows when dragged to screen edges",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.mutter",
        gsettings_key="edge-tiling",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="attach-modal-dialogs",
        name="Attach Modal Dialogs",
        description="Attach dialog windows to their parent",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.mutter",
        gsettings_key="attach-modal-dialogs",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="focus-mode-click",
        name="Click to Focus",
        description="Windows require click to focus (vs hover)",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.desktop.wm.preferences",
        gsettings_key="focus-mode",
        is_toggle=True,
        enabled_value="click",
        disabled_value="sloppy"
    ),
    Tweak(
        id="raise-on-click",
        name="Raise Windows on Click",
        description="Clicking a window raises it to front",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.desktop.wm.preferences",
        gsettings_key="raise-on-click",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="resize-with-right-button",
        name="Resize with Right Button",
        description="Use right-click to resize windows",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.desktop.wm.preferences",
        gsettings_key="resize-with-right-button",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    # === Top Bar / Clock ===
    Tweak(
        id="show-weekday",
        name="Show Weekday in Clock",
        description="Display weekday in top panel clock",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.desktop.interface",
        gsettings_key="clock-show-weekday",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="show-date",
        name="Show Date in Clock",
        description="Display date in top panel clock",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.desktop.interface",
        gsettings_key="clock-show-date",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="clock-seconds",
        name="Show Seconds in Clock",
        description="Display seconds in top panel clock",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.desktop.interface",
        gsettings_key="clock-show-seconds",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="clock-24h",
        name="24-Hour Clock",
        description="Use 24-hour time format",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.desktop.interface",
        gsettings_key="clock-format",
        is_toggle=True,
        enabled_value="24h",
        disabled_value="12h"
    ),
    Tweak(
        id="show-battery-percentage",
        name="Show Battery Percentage",
        description="Display battery percentage in panel",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.desktop.interface",
        gsettings_key="show-battery-percentage",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    # === Appearance / Interface ===
    Tweak(
        id="dark-mode",
        name="Dark Mode",
        description="Enable system-wide dark mode",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.desktop.interface",
        gsettings_key="color-scheme",
        is_toggle=True,
        enabled_value="prefer-dark",
        disabled_value="default"
    ),
    Tweak(
        id="animations",
        name="Animations",
        description="Enable desktop animations",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.desktop.interface",
        gsettings_key="enable-animations",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="hot-corner",
        name="Hot Corner (Activities)",
        description="Enable hot corner for Activities view",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.desktop.interface",
        gsettings_key="enable-hot-corners",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    # === Input Devices ===
    Tweak(
        id="tap-to-click",
        name="Tap to Click",
        description="Enable touchpad tap to click",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.desktop.peripherals.touchpad",
        gsettings_key="tap-to-click",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="natural-scrolling",
        name="Natural Scrolling (Touchpad)",
        description="Reverse touchpad scroll direction",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.desktop.peripherals.touchpad",
        gsettings_key="natural-scroll",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="two-finger-scroll",
        name="Two-Finger Scrolling",
        description="Use two fingers to scroll on touchpad",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.desktop.peripherals.touchpad",
        gsettings_key="two-finger-scrolling-enabled",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="disable-touchpad-typing",
        name="Disable Touchpad While Typing",
        description="Prevent accidental touches while typing",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.desktop.peripherals.touchpad",
        gsettings_key="disable-while-typing",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="mouse-natural-scroll",
        name="Natural Scrolling (Mouse)",
        description="Reverse mouse scroll direction",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.desktop.peripherals.mouse",
        gsettings_key="natural-scroll",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="middle-click-paste",
        name="Middle-Click Paste",
        description="Paste with middle mouse button",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.desktop.interface",
        gsettings_key="gtk-enable-primary-paste",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    # === Workspaces ===
    Tweak(
        id="dynamic-workspaces",
        name="Dynamic Workspaces",
        description="Automatically add/remove workspaces",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.mutter",
        gsettings_key="dynamic-workspaces",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="workspaces-only-primary",
        name="Workspaces on Primary Display Only",
        description="Only primary monitor switches workspaces",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.mutter",
        gsettings_key="workspaces-only-on-primary",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    # === Sound ===
    Tweak(
        id="over-amplification",
        name="Over-Amplification",
        description="Allow volume above 100%",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.desktop.sound",
        gsettings_key="allow-volume-above-100-percent",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="event-sounds",
        name="System Sounds",
        description="Play sounds for system events",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.desktop.sound",
        gsettings_key="event-sounds",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    # === Power ===
    Tweak(
        id="suspend-on-lid-close",
        name="Suspend on Lid Close",
        description="Suspend laptop when lid is closed",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.settings-daemon.plugins.power",
        gsettings_key="lid-close-suspend-with-external-monitor",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="show-suspend-button",
        name="Show Suspend Button",
        description="Show suspend in power menu",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.desktop.lockdown",
        gsettings_key="disable-log-out",
        is_toggle=True,
        enabled_value="false",
        disabled_value="true"
    ),
    # === Privacy / Security ===
    Tweak(
        id="automatic-screen-lock",
        name="Automatic Screen Lock",
        description="Lock screen when idle",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.desktop.screensaver",
        gsettings_key="lock-enabled",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="show-full-name-login",
        name="Show Full Name at Login",
        description="Display full name instead of username",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.login-screen",
        gsettings_key="enable-fingerprint-authentication",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    # === Files / Nautilus ===
    Tweak(
        id="show-hidden-files",
        name="Show Hidden Files",
        description="Show hidden files in file manager",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gnome.nautilus.preferences",
        gsettings_key="show-hidden-files",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
    Tweak(
        id="sort-folders-first",
        name="Sort Folders Before Files",
        description="Show folders before files in file manager",
        desktop=DesktopEnv.GNOME,
        gsettings_schema="org.gtk.gtk4.settings.file-chooser",
        gsettings_key="sort-directories-first",
        is_toggle=True,
        enabled_value="true",
        disabled_value="false"
    ),
]


# =============================================================================
# Theme Manager
# =============================================================================

class ThemeManager:
    """Manages theme installation and application."""
    
    def __init__(self, distro, desktop):
        self.distro = distro
        self.desktop = desktop
    
    def get_current_gtk_theme(self) -> str:
        """Get the currently active GTK theme."""
        try:
            result = subprocess.run(
                ['gsettings', 'get', 'org.gnome.desktop.interface', 'gtk-theme'],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip().strip("'")
        except Exception:
            return ""
    
    def get_current_icon_theme(self) -> str:
        """Get the currently active icon theme."""
        try:
            result = subprocess.run(
                ['gsettings', 'get', 'org.gnome.desktop.interface', 'icon-theme'],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip().strip("'")
        except Exception:
            return ""
    
    def get_current_cursor_theme(self) -> str:
        """Get the currently active cursor theme."""
        try:
            result = subprocess.run(
                ['gsettings', 'get', 'org.gnome.desktop.interface', 'cursor-theme'],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip().strip("'")
        except Exception:
            return ""
    
    def apply_gtk_theme(self, theme_name: str) -> bool:
        """Apply a GTK theme."""
        try:
            if self.desktop.desktop_env == DesktopEnv.GNOME:
                subprocess.run(
                    ['gsettings', 'set', 'org.gnome.desktop.interface', 'gtk-theme', theme_name],
                    check=True, timeout=5
                )
            elif self.desktop.desktop_env == DesktopEnv.CINNAMON:
                subprocess.run(
                    ['gsettings', 'set', 'org.cinnamon.desktop.interface', 'gtk-theme', theme_name],
                    check=True, timeout=5
                )
            elif self.desktop.desktop_env == DesktopEnv.MATE:
                subprocess.run(
                    ['gsettings', 'set', 'org.mate.interface', 'gtk-theme', theme_name],
                    check=True, timeout=5
                )
            elif self.desktop.desktop_env == DesktopEnv.XFCE:
                # XFCE needs both GTK theme and window manager theme
                subprocess.run(
                    ['xfconf-query', '-c', 'xsettings', '-p', '/Net/ThemeName', '-s', theme_name],
                    check=True, timeout=5
                )
                # Also set the window manager (xfwm4) theme for window decorations
                subprocess.run(
                    ['xfconf-query', '-c', 'xfwm4', '-p', '/general/theme', '-s', theme_name],
                    timeout=5
                )
            elif self.desktop.desktop_env == DesktopEnv.KDE:
                # KDE: Set GTK theme via kde-gtk-config or plasma settings
                # Try plasma-apply-gtk3-config first (newer)
                for cmd in ['plasma-apply-gtk3-config', 'plasma-apply-gtk-config']:
                    try:
                        result = subprocess.run(
                            [cmd, '--gtk3-theme', theme_name],
                            capture_output=True, timeout=5
                        )
                        if result.returncode == 0:
                            return True
                    except FileNotFoundError:
                        continue
                # Fallback: directly write to settings
                for kwritecmd in ['kwriteconfig5', 'kwriteconfig6']:
                    try:
                        subprocess.run(
                            [kwritecmd, '--file', 'kdeglobals', '--group', 'General',
                             '--key', 'widgetStyle', theme_name],
                            timeout=5
                        )
                        return True
                    except FileNotFoundError:
                        continue
            return True
        except Exception:
            return False
    
    def apply_icon_theme(self, theme_name: str) -> bool:
        """Apply an icon theme."""
        try:
            if self.desktop.desktop_env == DesktopEnv.GNOME:
                subprocess.run(
                    ['gsettings', 'set', 'org.gnome.desktop.interface', 'icon-theme', theme_name],
                    check=True, timeout=5
                )
            elif self.desktop.desktop_env == DesktopEnv.CINNAMON:
                subprocess.run(
                    ['gsettings', 'set', 'org.cinnamon.desktop.interface', 'icon-theme', theme_name],
                    check=True, timeout=5
                )
            elif self.desktop.desktop_env == DesktopEnv.MATE:
                subprocess.run(
                    ['gsettings', 'set', 'org.mate.interface', 'icon-theme', theme_name],
                    check=True, timeout=5
                )
            elif self.desktop.desktop_env == DesktopEnv.XFCE:
                subprocess.run(
                    ['xfconf-query', '-c', 'xsettings', '-p', '/Net/IconThemeName', '-s', theme_name],
                    check=True, timeout=5
                )
            elif self.desktop.desktop_env == DesktopEnv.KDE:
                # KDE: plasma-apply-desktoptheme for icons
                try:
                    subprocess.run(
                        ['plasma-apply-icon-theme', theme_name],
                        check=True, timeout=5
                    )
                except FileNotFoundError:
                    # Fallback to kconfig
                    for kwritecmd in ['kwriteconfig5', 'kwriteconfig6']:
                        try:
                            subprocess.run(
                                [kwritecmd, '--file', 'kdeglobals', '--group', 'Icons',
                                 '--key', 'Theme', theme_name],
                                timeout=5
                            )
                            # Refresh KDE
                            subprocess.run(['kbuildsycoca5'], capture_output=True, timeout=10)
                            return True
                        except FileNotFoundError:
                            continue
            return True
        except Exception:
            return False
    
    def apply_cursor_theme(self, theme_name: str) -> bool:
        """Apply a cursor theme."""
        try:
            if self.desktop.desktop_env == DesktopEnv.GNOME:
                subprocess.run(
                    ['gsettings', 'set', 'org.gnome.desktop.interface', 'cursor-theme', theme_name],
                    check=True, timeout=5
                )
            elif self.desktop.desktop_env == DesktopEnv.CINNAMON:
                subprocess.run(
                    ['gsettings', 'set', 'org.cinnamon.desktop.interface', 'cursor-theme', theme_name],
                    check=True, timeout=5
                )
            elif self.desktop.desktop_env == DesktopEnv.MATE:
                subprocess.run(
                    ['gsettings', 'set', 'org.mate.peripherals-mouse', 'cursor-theme', theme_name],
                    check=True, timeout=5
                )
            elif self.desktop.desktop_env == DesktopEnv.XFCE:
                subprocess.run(
                    ['xfconf-query', '-c', 'xsettings', '-p', '/Gtk/CursorThemeName', '-s', theme_name],
                    check=True, timeout=5
                )
            elif self.desktop.desktop_env == DesktopEnv.KDE:
                # KDE cursor theme via plasma-apply-cursortheme
                subprocess.run(
                    ['plasma-apply-cursortheme', theme_name],
                    check=True, timeout=5
                )
            return True
        except Exception:
            return False
    
    def apply_plasma_theme(self, theme_name: str) -> bool:
        """Apply a KDE Plasma global theme."""
        try:
            # lookandfeeltool applies the full look-and-feel theme
            result = subprocess.run(
                ['lookandfeeltool', '-a', theme_name],
                capture_output=True, timeout=10
            )
            if result.returncode == 0:
                return True
            
            # Fallback: try plasma-apply-lookandfeel (newer KDE)
            result = subprocess.run(
                ['plasma-apply-lookandfeel', '-a', theme_name],
                capture_output=True, timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def apply_kvantum_theme(self, theme_name: str) -> bool:
        """Apply a Kvantum Qt theme."""
        import shutil
        
        if not shutil.which('kvantummanager'):
            return False
        
        try:
            subprocess.run(
                ['kvantummanager', '--set', theme_name],
                check=True, timeout=5
            )
            return True
        except Exception:
            return False
    
    def get_current_plasma_theme(self) -> str:
        """Get the current KDE Plasma theme."""
        try:
            # Read from kdeglobals
            result = subprocess.run(
                ['kreadconfig5', '--file', 'kdeglobals', '--group', 'KDE', '--key', 'LookAndFeelPackage'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            
            # Try kreadconfig6 for Plasma 6
            result = subprocess.run(
                ['kreadconfig6', '--file', 'kdeglobals', '--group', 'KDE', '--key', 'LookAndFeelPackage'],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip()
        except Exception:
            return ""
    
    def get_current_kvantum_theme(self) -> str:
        """Get the current Kvantum theme."""
        import os
        config_file = os.path.expanduser('~/.config/Kvantum/kvantum.kvconfig')
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    for line in f:
                        if line.startswith('theme='):
                            return line.split('=', 1)[1].strip()
        except Exception:
            pass
        return ""


# =============================================================================
# Tweak Manager
# =============================================================================

class TweakManager:
    """Manages system tweaks."""
    
    def __init__(self, desktop):
        self.desktop = desktop
    
    def is_tweak_enabled(self, tweak: Tweak) -> bool:
        """Check if a toggle tweak is enabled."""
        if not tweak.is_toggle:
            return False
        
        current = self.get_tweak_value(tweak)
        if current is None:
            return False
        
        return current.lower() == tweak.enabled_value.lower()
    
    def get_tweak_value(self, tweak: Tweak) -> Optional[str]:
        """Get the current value of a tweak."""
        # GNOME gsettings
        if tweak.gsettings_schema and tweak.gsettings_key:
            try:
                result = subprocess.run(
                    ['gsettings', 'get', tweak.gsettings_schema, tweak.gsettings_key],
                    capture_output=True, text=True, timeout=5
                )
                return result.stdout.strip().strip("'")
            except Exception:
                return None
        
        # KDE kconfig
        if tweak.kconfig_file and tweak.kconfig_key:
            try:
                import os
                config_file = os.path.expanduser(tweak.kconfig_file)
                # Try kreadconfig5 first, then kreadconfig6 for Plasma 6
                for cmd in ['kreadconfig5', 'kreadconfig6', 'kreadconfig']:
                    try:
                        result = subprocess.run(
                            [cmd, '--file', config_file, '--group', tweak.kconfig_group, 
                             '--key', tweak.kconfig_key],
                            capture_output=True, text=True, timeout=5
                        )
                        if result.returncode == 0:
                            return result.stdout.strip()
                    except FileNotFoundError:
                        continue
            except Exception:
                return None
        
        # XFCE xfconf
        if tweak.xfconf_channel and tweak.xfconf_property:
            try:
                result = subprocess.run(
                    ['xfconf-query', '-c', tweak.xfconf_channel, '-p', tweak.xfconf_property],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    return result.stdout.strip()
            except Exception:
                return None
        
        return None
    
    def apply_tweak(self, tweak: Tweak, enable: bool = True) -> bool:
        """Apply or revert a tweak."""
        value = tweak.enabled_value if enable else tweak.disabled_value
        
        # GNOME gsettings
        if tweak.gsettings_schema and tweak.gsettings_key:
            try:
                subprocess.run(
                    ['gsettings', 'set', tweak.gsettings_schema, tweak.gsettings_key, value],
                    check=True, timeout=5
                )
                return True
            except Exception:
                return False
        
        # KDE kconfig
        if tweak.kconfig_file and tweak.kconfig_key:
            try:
                import os
                config_file = os.path.expanduser(tweak.kconfig_file)
                # Try kwriteconfig5 first, then kwriteconfig6 for Plasma 6
                for cmd in ['kwriteconfig5', 'kwriteconfig6', 'kwriteconfig']:
                    try:
                        result = subprocess.run(
                            [cmd, '--file', config_file, '--group', tweak.kconfig_group,
                             '--key', tweak.kconfig_key, value],
                            capture_output=True, timeout=5
                        )
                        if result.returncode == 0:
                            # Notify KWin to reload config if it's a kwin setting
                            if 'kwinrc' in tweak.kconfig_file:
                                subprocess.run(['qdbus', 'org.kde.KWin', '/KWin', 'reconfigure'],
                                              capture_output=True, timeout=5)
                            return True
                    except FileNotFoundError:
                        continue
            except Exception:
                return False
        
        # XFCE xfconf
        if tweak.xfconf_channel and tweak.xfconf_property:
            try:
                # xfconf-query needs type flag for boolean
                cmd = ['xfconf-query', '-c', tweak.xfconf_channel, '-p', tweak.xfconf_property]
                if value.lower() in ('true', 'false'):
                    cmd.extend(['-t', 'bool', '-s', value])
                else:
                    cmd.extend(['-s', value])
                
                subprocess.run(cmd, check=True, timeout=5)
                return True
            except Exception:
                return False
        
        return False


# =============================================================================
# Extension Manager
# =============================================================================

class ExtensionManager:
    """Manages GNOME extensions."""
    
    def __init__(self):
        pass
    
    def is_extension_installed(self, uuid: str) -> bool:
        """Check if a GNOME extension is installed."""
        try:
            result = subprocess.run(
                ['gnome-extensions', 'info', uuid],
                capture_output=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def is_extension_enabled(self, uuid: str) -> bool:
        """Check if a GNOME extension is enabled."""
        try:
            result = subprocess.run(
                ['gnome-extensions', 'info', uuid],
                capture_output=True, text=True, timeout=5
            )
            return 'State: ENABLED' in result.stdout
        except Exception:
            return False
    
    def enable_extension(self, uuid: str) -> bool:
        """Enable a GNOME extension."""
        try:
            subprocess.run(
                ['gnome-extensions', 'enable', uuid],
                check=True, timeout=5
            )
            return True
        except Exception:
            return False
    
    def disable_extension(self, uuid: str) -> bool:
        """Disable a GNOME extension."""
        try:
            subprocess.run(
                ['gnome-extensions', 'disable', uuid],
                check=True, timeout=5
            )
            return True
        except Exception:
            return False


# =============================================================================
# GNOME Extensions Browser API (filesystem-based for speed)
# =============================================================================

EXTENSIONS_API_URL = "https://extensions.gnome.org/extension-query/"
EXTENSION_INFO_URL = "https://extensions.gnome.org/extension-info/"


def get_gnome_shell_version() -> Optional[str]:
    """Get the current GNOME Shell major version."""
    try:
        result = subprocess.run(
            ['gnome-shell', '--version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            version = result.stdout.strip().split()[-1]
            major = version.split('.')[0]
            return major
    except Exception:
        pass
    return None


def get_installed_extensions_from_filesystem() -> tuple[dict, dict]:
    """Get installed extensions by reading filesystem directly (fast!).
    
    Returns:
        (user_extensions, system_extensions)
    """
    import os
    import json
    from pathlib import Path
    
    user_extensions = {}
    system_extensions = {}
    
    # Get enabled extensions list (one gsettings call)
    enabled_uuids = set()
    try:
        result = subprocess.run(
            ['gsettings', 'get', 'org.gnome.shell', 'enabled-extensions'],
            capture_output=True,
            text=True,
            timeout=3
        )
        if result.returncode == 0:
            # Parse the array format: ['ext1@foo', 'ext2@bar']
            raw = result.stdout.strip()
            if raw.startswith('[') and raw.endswith(']'):
                # Remove brackets and split
                inner = raw[1:-1]
                for item in inner.split(','):
                    item = item.strip().strip("'\"")
                    if item:
                        enabled_uuids.add(item)
    except Exception:
        pass
    
    def read_extensions_from_dir(base_path: str, is_user: bool) -> dict:
        """Read all extensions from a directory."""
        extensions = {}
        base = Path(base_path).expanduser()
        
        if not base.exists():
            return extensions
        
        for ext_dir in base.iterdir():
            if not ext_dir.is_dir():
                continue
            
            metadata_file = ext_dir / 'metadata.json'
            if not metadata_file.exists():
                continue
            
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                
                uuid = metadata.get('uuid', ext_dir.name)
                name = metadata.get('name', uuid.split('@')[0].replace('-', ' ').title())
                description = metadata.get('description', '')
                
                extensions[uuid] = {
                    'installed': True,
                    'enabled': uuid in enabled_uuids,
                    'is_user': is_user,
                    'name': name,
                    'description': description[:100] if description else ''
                }
            except Exception:
                # If we can't read metadata, use folder name
                uuid = ext_dir.name
                extensions[uuid] = {
                    'installed': True,
                    'enabled': uuid in enabled_uuids,
                    'is_user': is_user,
                    'name': uuid.split('@')[0].replace('-', ' ').title(),
                    'description': ''
                }
        
        return extensions
    
    # Read user extensions
    user_extensions = read_extensions_from_dir('~/.local/share/gnome-shell/extensions', is_user=True)
    
    # Read system extensions
    system_extensions = read_extensions_from_dir('/usr/share/gnome-shell/extensions', is_user=False)
    
    return user_extensions, system_extensions


def search_extensions_api(query: str, shell_version: str = None) -> list:
    """Search for extensions on extensions.gnome.org."""
    try:
        params = {
            'search': query,
            'n_per_page': 20,
        }
        if shell_version:
            params['shell_version'] = shell_version
        
        url = EXTENSIONS_API_URL + "?" + urllib.parse.urlencode(params)
        
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'TuxAssistant/1.0')
        
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode())
            return data.get('extensions', [])
    except Exception as e:
        print(f"Search error: {e}")
        return []


def get_extension_info(pk: int, shell_version: str) -> Optional[dict]:
    """Get extension info including download URL."""
    try:
        params = {'pk': pk, 'shell_version': shell_version}
        url = EXTENSION_INFO_URL + "?" + urllib.parse.urlencode(params)
        
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'TuxAssistant/1.0')
        
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode())
    except Exception:
        return None


def install_extension_from_ego(pk: int, uuid: str, shell_version: str) -> tuple[bool, str]:
    """Install extension from extensions.gnome.org using DBus.
    
    Uses GNOME Shell's DBus interface to download and install the extension,
    which makes it available immediately without requiring a logout.
    """
    try:
        # Use DBus InstallRemoteExtension - this is what Extension Manager uses
        # It downloads AND loads the extension immediately
        result = subprocess.run(
            [
                'gdbus', 'call', '--session',
                '--dest', 'org.gnome.Shell.Extensions',
                '--object-path', '/org/gnome/Shell/Extensions',
                '--method', 'org.gnome.Shell.Extensions.InstallRemoteExtension',
                uuid
            ],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Check result - DBus returns "()" on success or "('successful',)" etc
        output = result.stdout.strip()
        stderr = result.stderr.strip()
        
        if result.returncode == 0:
            # Try to enable it
            subprocess.run(
                ['gnome-extensions', 'enable', uuid],
                capture_output=True,
                timeout=10
            )
            return True, "Installed and enabled!"
        else:
            # DBus call failed - try the old method as fallback
            return _install_extension_fallback(pk, uuid, shell_version)
    
    except Exception as e:
        # Fallback to manual download method
        return _install_extension_fallback(pk, uuid, shell_version)


def _install_extension_fallback(pk: int, uuid: str, shell_version: str) -> tuple[bool, str]:
    """Fallback installation method using manual download."""
    try:
        info = get_extension_info(pk, shell_version)
        if not info:
            return False, "Could not get extension info"
        
        download_url = info.get('download_url')
        if not download_url:
            version_map = info.get('shell_version_map', {})
            if version_map:
                available = ', '.join(version_map.keys())
                return False, f"Not compatible with GNOME {shell_version}. Available: {available}"
            return False, "No download available for this GNOME version"
        
        full_url = f"https://extensions.gnome.org{download_url}"
        
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp:
            tmp_path = tmp.name
        
        urllib.request.urlretrieve(full_url, tmp_path)
        
        result = subprocess.run(
            ['gnome-extensions', 'install', '--force', tmp_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        os.unlink(tmp_path)
        
        if result.returncode == 0:
            return True, "Installed! Log out and back in to enable."
        else:
            return False, result.stderr or "Installation failed"
    
    except Exception as e:
        return False, str(e)


def enable_extension_by_uuid(uuid: str) -> bool:
    """Enable an extension."""
    try:
        result = subprocess.run(
            ['gnome-extensions', 'enable', uuid],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def disable_extension_by_uuid(uuid: str) -> bool:
    """Disable an extension."""
    try:
        result = subprocess.run(
            ['gnome-extensions', 'disable', uuid],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def uninstall_extension_by_uuid(uuid: str) -> bool:
    """Uninstall an extension."""
    try:
        result = subprocess.run(
            ['gnome-extensions', 'uninstall', uuid],
            capture_output=True,
            timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


# =============================================================================
# GNOME Extensions Browser Page (With Tabs & Popular Extensions)
# =============================================================================

class GnomeExtensionsBrowserPage(Adw.NavigationPage):
    """GNOME Extensions browser with Installed/Browse tabs."""
    
    def __init__(self, window, distro):
        super().__init__(title="GNOME Extensions")
        
        self.window = window
        self.distro = distro
        self.shell_version = get_gnome_shell_version()
        self.user_extensions = {}
        self.system_extensions = {}
        
        # Load installed from filesystem (instant!)
        self.user_extensions, self.system_extensions = get_installed_extensions_from_filesystem()
        
        # Build UI immediately
        self.build_ui()
        
        # Load popular extensions in background AFTER UI is shown
        GLib.timeout_add(100, self._start_loading_popular)
    
    def _start_loading_popular(self):
        """Start loading popular extensions after UI is ready."""
        def do_load():
            results = search_extensions_api("", self.shell_version)
            GLib.idle_add(self._populate_popular, results[:15])
        
        thread = threading.Thread(target=do_load, daemon=True)
        thread.start()
        return False  # Don't repeat
    
    def build_ui(self):
        """Build the UI with tabs."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header bar
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        toolbar_view.add_top_bar(header)
        
        # Main content
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        toolbar_view.set_content(main_box)
        
        # Tab bar (Installed / Browse)
        self.stack = Adw.ViewStack()
        
        switcher = Adw.ViewSwitcher()
        switcher.set_stack(self.stack)
        switcher.set_policy(Adw.ViewSwitcherPolicy.WIDE)
        switcher.set_margin_top(8)
        switcher.set_margin_bottom(8)
        main_box.append(switcher)
        
        main_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        
        # Installed tab
        installed_page = self._create_installed_tab()
        self.stack.add_titled_with_icon(installed_page, "installed", "Installed", "emblem-default-symbolic")
        
        # Browse tab
        browse_page = self._create_browse_tab()
        self.stack.add_titled_with_icon(browse_page, "browse", "Browse", "web-browser-symbolic")
        
        main_box.append(self.stack)
        
        # Status bar
        total = len(self.user_extensions) + len(self.system_extensions)
        version_text = f"GNOME {self.shell_version}" if self.shell_version else "GNOME"
        
        status_label = Gtk.Label()
        status_label.set_markup(f"<small>{version_text} • {total} extension(s) installed</small>")
        status_label.add_css_class("dim-label")
        status_label.set_margin_top(8)
        status_label.set_margin_bottom(8)
        main_box.append(status_label)
    
    def _create_installed_tab(self) -> Gtk.Widget:
        """Create the Installed tab."""
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        
        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_margin_top(16)
        clamp.set_margin_bottom(16)
        clamp.set_margin_start(16)
        clamp.set_margin_end(16)
        scrolled.set_child(clamp)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        clamp.set_child(content)
        
        # User extensions
        if self.user_extensions:
            user_group = Adw.PreferencesGroup()
            user_group.set_title("User-Installed Extensions")
            
            for uuid, info in sorted(self.user_extensions.items(), key=lambda x: x[1].get('name', '').lower()):
                row = self._create_installed_row(uuid, info, is_user=True)
                user_group.add(row)
            
            content.append(user_group)
        
        # System extensions
        if self.system_extensions:
            system_group = Adw.PreferencesGroup()
            system_group.set_title("System Extensions")
            
            for uuid, info in sorted(self.system_extensions.items(), key=lambda x: x[1].get('name', '').lower()):
                row = self._create_installed_row(uuid, info, is_user=False)
                system_group.add(row)
            
            content.append(system_group)
        
        # Empty state
        if not self.user_extensions and not self.system_extensions:
            empty_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
            empty_box.set_valign(Gtk.Align.CENTER)
            empty_box.set_vexpand(True)
            
            empty_label = Gtk.Label(label="No Extensions Installed")
            empty_label.add_css_class("title-2")
            empty_box.append(empty_label)
            
            hint_label = Gtk.Label(label="Browse extensions to find new ones")
            hint_label.add_css_class("dim-label")
            empty_box.append(hint_label)
            
            content.append(empty_box)
        
        return scrolled
    
    def _create_browse_tab(self) -> Gtk.Widget:
        """Create the Browse tab."""
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        
        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_margin_top(16)
        clamp.set_margin_bottom(16)
        clamp.set_margin_start(16)
        clamp.set_margin_end(16)
        scrolled.set_child(clamp)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        clamp.set_child(content)
        
        # Header
        header_label = Gtk.Label()
        header_label.set_markup("<big><b>Search for Extensions</b></big>")
        header_label.set_halign(Gtk.Align.CENTER)
        content.append(header_label)
        
        desc_label = Gtk.Label(label="Enter a keyword to search 'extensions.gnome.org' for GNOME Shell Extensions")
        desc_label.add_css_class("dim-label")
        desc_label.set_halign(Gtk.Align.CENTER)
        content.append(desc_label)
        
        # Search box
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        search_box.set_halign(Gtk.Align.CENTER)
        search_box.set_margin_top(8)
        search_box.set_margin_bottom(8)
        
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search extensions...")
        self.search_entry.set_size_request(400, -1)
        self.search_entry.connect("activate", self._on_search)
        search_box.append(self.search_entry)
        
        content.append(search_box)
        
        # Results/Popular list
        self.browse_list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        content.append(self.browse_list)
        
        # Show loading spinner initially
        self.browse_spinner = Gtk.Spinner()
        self.browse_spinner.set_size_request(32, 32)
        self.browse_spinner.start()
        self.browse_spinner.set_halign(Gtk.Align.CENTER)
        self.browse_spinner.set_margin_top(20)
        self.browse_list.append(self.browse_spinner)
        
        loading_label = Gtk.Label(label="Loading popular extensions...")
        loading_label.add_css_class("dim-label")
        loading_label.set_halign(Gtk.Align.CENTER)
        self.browse_list.append(loading_label)
        
        return scrolled
    
    def _populate_popular(self, extensions: list):
        """Populate with popular extensions."""
        # Clear loading state
        while child := self.browse_list.get_first_child():
            self.browse_list.remove(child)
        
        if not extensions:
            error_label = Gtk.Label(label="Could not load extensions. Check your internet connection.")
            error_label.add_css_class("dim-label")
            error_label.set_halign(Gtk.Align.CENTER)
            self.browse_list.append(error_label)
            return
        
        # Create list
        self._populate_extension_list(extensions)
    
    def _populate_extension_list(self, extensions: list):
        """Populate the browse list with extensions."""
        all_installed = {**self.user_extensions, **self.system_extensions}
        
        list_box = Gtk.ListBox()
        list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        list_box.add_css_class("boxed-list")
        
        for ext in extensions:
            uuid = ext.get('uuid', '')
            name = ext.get('name', uuid.split('@')[0])
            creator = ext.get('creator', '')
            desc = ext.get('description', '')[:60]
            if len(ext.get('description', '')) > 60:
                desc += '...'
            
            row = Adw.ActionRow()
            row.set_title(name)
            row.set_subtitle(f"{creator}\n{desc}" if creator else desc)
            
            # Chevron
            chevron = Gtk.Image.new_from_icon_name("tux-go-next-symbolic")
            chevron.add_css_class("dim-label")
            row.add_suffix(chevron)
            
            if uuid in all_installed:
                # Installed badge
                badge = Gtk.Label(label="Installed")
                badge.add_css_class("dim-label")
                badge.set_valign(Gtk.Align.CENTER)
                badge.set_margin_end(8)
                row.add_suffix(badge)
            else:
                # Install button
                install_btn = Gtk.Button(label="Install")
                install_btn.add_css_class("suggested-action")
                install_btn.set_valign(Gtk.Align.CENTER)
                install_btn.set_margin_end(8)
                install_btn.connect("clicked", self._on_install, ext)
                row.add_suffix(install_btn)
            
            list_box.append(row)
        
        self.browse_list.append(list_box)
    
    def _create_installed_row(self, uuid: str, info: dict, is_user: bool) -> Adw.ActionRow:
        """Create a row for an installed extension."""
        name = info.get('name', uuid.split('@')[0])
        
        row = Adw.ActionRow()
        row.set_title(name)
        row.set_subtitle(uuid)
        
        # Enable/disable switch
        switch = Gtk.Switch()
        switch.set_valign(Gtk.Align.CENTER)
        switch.set_active(info.get('enabled', False))
        switch.connect("state-set", self._on_toggle_extension, uuid)
        row.add_suffix(switch)
        
        # Settings button
        settings_btn = Gtk.Button()
        settings_btn.set_icon_name("tux-emblem-system-symbolic")
        settings_btn.set_valign(Gtk.Align.CENTER)
        settings_btn.add_css_class("flat")
        settings_btn.set_tooltip_text("Settings")
        settings_btn.connect("clicked", self._on_settings, uuid)
        row.add_suffix(settings_btn)
        
        # Chevron
        chevron = Gtk.Image.new_from_icon_name("tux-go-down-symbolic")
        chevron.add_css_class("dim-label")
        row.add_suffix(chevron)
        
        return row
    
    def _on_search(self, widget):
        """Handle search."""
        query = self.search_entry.get_text().strip()
        if not query:
            return
        
        # Show loading
        while child := self.browse_list.get_first_child():
            self.browse_list.remove(child)
        
        spinner = Gtk.Spinner()
        spinner.set_size_request(32, 32)
        spinner.start()
        spinner.set_halign(Gtk.Align.CENTER)
        spinner.set_margin_top(20)
        self.browse_list.append(spinner)
        
        def do_search():
            results = search_extensions_api(query, self.shell_version)
            GLib.idle_add(self._show_search_results, results)
        
        thread = threading.Thread(target=do_search, daemon=True)
        thread.start()
    
    def _show_search_results(self, results: list):
        """Show search results."""
        while child := self.browse_list.get_first_child():
            self.browse_list.remove(child)
        
        if not results:
            empty_label = Gtk.Label(label="No extensions found")
            empty_label.add_css_class("dim-label")
            empty_label.set_halign(Gtk.Align.CENTER)
            self.browse_list.append(empty_label)
            return
        
        self._populate_extension_list(results)
    
    def _on_toggle_extension(self, switch, state, uuid: str):
        """Toggle extension on/off."""
        def do_toggle():
            if state:
                success = enable_extension_by_uuid(uuid)
            else:
                success = disable_extension_by_uuid(uuid)
            
            if success:
                name = uuid.split('@')[0].replace('-', ' ').title()
                msg = f"{'Enabled' if state else 'Disabled'} {name}"
            else:
                msg = "Failed to toggle extension"
            GLib.idle_add(self.window.show_toast, msg)
        
        thread = threading.Thread(target=do_toggle, daemon=True)
        thread.start()
        return False
    
    def _on_settings(self, button, uuid: str):
        """Open extension settings."""
        try:
            subprocess.Popen(
                ['gnome-extensions', 'prefs', uuid],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            self.window.show_toast("Could not open settings")
    
    def _on_install(self, button, ext: dict):
        """Install extension."""
        uuid = ext.get('uuid', '')
        name = ext.get('name', uuid)
        pk = ext.get('pk', 0)
        
        if not pk or not self.shell_version:
            self.window.show_toast("Cannot install")
            return
        
        button.set_sensitive(False)
        button.set_label("Installing...")
        
        def do_install():
            success, message = install_extension_from_ego(pk, uuid, self.shell_version)
            GLib.idle_add(self._on_install_complete, button, name, success, message)
        
        thread = threading.Thread(target=do_install, daemon=True)
        thread.start()
    
    def _on_install_complete(self, button, name: str, success: bool, message: str):
        """Handle install completion."""
        if success:
            button.set_label("Installed")
            button.remove_css_class("suggested-action")
            self.window.show_toast(f"{name}: {message}")
        else:
            button.set_sensitive(True)
            button.set_label("Install")
            self.window.show_toast(f"Failed: {message}")


# =============================================================================
# Plan Execution Dialog (reuse from networking)
# =============================================================================

class PlanExecutionDialog(Adw.Dialog):
    """Dialog for executing installation plans."""
    
    def __init__(self, window, plan: dict, title: str, distro, on_complete_callback=None):
        super().__init__()
        
        self.window = window
        self.plan = plan
        self.distro = distro
        self.process = None
        self.on_complete_callback = on_complete_callback
        
        self.set_title(title)
        self.set_content_width(500)
        self.set_content_height(400)
        self.set_can_close(False)
        
        self.build_ui()
        GLib.timeout_add(100, self.execute_plan)
    
    def build_ui(self):
        """Build dialog UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        toolbar_view.add_top_bar(header)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        content.set_margin_top(20)
        content.set_margin_bottom(20)
        content.set_margin_start(20)
        content.set_margin_end(20)
        toolbar_view.set_content(content)
        
        # Progress bar
        self.progress = Gtk.ProgressBar()
        self.progress.set_show_text(True)
        self.progress.set_text("Preparing...")
        content.append(self.progress)
        
        # Status label
        self.status_label = Gtk.Label(label="Starting...")
        self.status_label.set_wrap(True)
        self.status_label.set_halign(Gtk.Align.START)
        content.append(self.status_label)
        
        # Log output
        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        scrolled.set_vexpand(True)
        scrolled.set_min_content_height(200)
        content.append(scrolled)
        
        self.log_view = Gtk.TextView()
        self.log_view.set_editable(False)
        self.log_view.set_monospace(True)
        self.log_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        scrolled.set_child(self.log_view)
        
        self.log_buffer = self.log_view.get_buffer()
        
        # Close button (hidden initially)
        self.close_btn = Gtk.Button(label="Close")
        self.close_btn.add_css_class("suggested-action")
        self.close_btn.connect("clicked", lambda b: self.close())
        self.close_btn.set_visible(False)
        self.close_btn.set_halign(Gtk.Align.CENTER)
        content.append(self.close_btn)
    
    def execute_plan(self) -> bool:
        """Execute the plan via tux-helper."""
        import json
        import tempfile
        
        # Write plan to temp file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(self.plan, f)
            plan_file = f.name
        
        # Build command
        family = self.distro.family.value
        cmd = ['pkexec', '/usr/bin/tux-helper', '--execute-plan', plan_file, '--family', family]
        
        def run_process():
            import subprocess
            try:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                
                for line in iter(process.stdout.readline, ''):
                    GLib.idle_add(self.process_output, line)
                
                process.wait()
                GLib.idle_add(self.on_complete, process.returncode)
                
            except Exception as e:
                GLib.idle_add(self.on_error, str(e))
            finally:
                import os
                try:
                    os.unlink(plan_file)
                except Exception:
                    pass
        
        thread = threading.Thread(target=run_process, daemon=True)
        thread.start()
        
        return False
    
    def process_output(self, line: str):
        """Process output from tux-helper."""
        line = line.strip()
        
        if line.startswith('[Tux Assistant:PROGRESS]'):
            parts = line.split(':', 2)
            if len(parts) >= 3:
                try:
                    pct = int(parts[1].replace('[Tux Assistant:PROGRESS]', ''))
                    self.progress.set_fraction(pct / 100)
                    self.progress.set_text(f"{pct}%")
                except Exception:
                    pass
        elif line.startswith('[Tux Assistant:STATUS]'):
            status = line.replace('[Tux Assistant:STATUS]', '').strip()
            self.status_label.set_label(status)
        else:
            end_iter = self.log_buffer.get_end_iter()
            self.log_buffer.insert(end_iter, line + '\n')
            
            mark = self.log_buffer.create_mark(None, self.log_buffer.get_end_iter(), False)
            self.log_view.scroll_to_mark(mark, 0, False, 0, 0)
    
    def on_complete(self, return_code: int):
        """Handle completion."""
        self.set_can_close(True)
        self.close_btn.set_visible(True)
        
        if return_code == 0:
            self.progress.set_fraction(1.0)
            self.progress.set_text("Complete")
            self.status_label.set_label("Installation completed successfully!")
        else:
            self.progress.add_css_class("error")
            self.status_label.set_label(f"Installation failed (exit code {return_code})")
        
        # Connect close to callback
        if self.on_complete_callback:
            self.connect("closed", lambda d: GLib.timeout_add(300, self.on_complete_callback))
    
    def on_error(self, error: str):
        """Handle error."""
        self.set_can_close(True)
        self.close_btn.set_visible(True)
        self.progress.add_css_class("error")
        self.status_label.set_label(f"Error: {error}")


# =============================================================================
# Main Desktop Enhancements Page
# =============================================================================

@register_module(
    id="desktop_enhancements",
    name="Desktop Enhancements",
    description="Themes, extensions, widgets, and tweaks",
    icon="tux-preferences-desktop-theme-symbolic",
    category=ModuleCategory.SETUP,
    order=51  # Last in Setup category
)
class DesktopEnhancementsPage(Adw.NavigationPage):
    """Desktop enhancements module page."""
    
    def __init__(self, window):
        super().__init__(title="Desktop Enhancements")
        
        self.window = window
        self.distro = get_distro()
        self.desktop = get_desktop()
        self.theme_manager = ThemeManager(self.distro, self.desktop)
        self.tweak_manager = TweakManager(self.desktop)
        self.extension_manager = ExtensionManager()
        
        self.build_ui()
    
    def build_ui(self):
        """Build the UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header (NavigationView handles back button automatically)
        header = Adw.HeaderBar()
        
        # Refresh button
        refresh_btn = Gtk.Button()
        refresh_btn.set_icon_name("tux-view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh")
        refresh_btn.connect("clicked", self.on_refresh)
        header.pack_end(refresh_btn)
        
        toolbar_view.add_top_bar(header)
        
        # Scrolled content
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled.set_vexpand(True)
        toolbar_view.set_content(self.scrolled)
        
        self._build_content()
    
    def _build_content(self):
        """Build/rebuild scrollable content."""
        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_margin_top(20)
        clamp.set_margin_bottom(20)
        clamp.set_margin_start(20)
        clamp.set_margin_end(20)
        self.scrolled.set_child(clamp)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        clamp.set_child(content)
        
        # Status banner
        content.append(self._create_status_section())
        
        # Appearance section
        content.append(self._create_appearance_section())
        
        # DE-specific sections
        if self.desktop.desktop_env == DesktopEnv.GNOME:
            content.append(self._create_gnome_extensions_section())
            content.append(self._create_gnome_tweaks_section())
        elif self.desktop.desktop_env == DesktopEnv.KDE:
            content.append(self._create_kde_section())
        elif self.desktop.desktop_env == DesktopEnv.XFCE:
            content.append(self._create_xfce_section())
        elif self.desktop.desktop_env == DesktopEnv.CINNAMON:
            content.append(self._create_cinnamon_section())
        elif self.desktop.desktop_env == DesktopEnv.MATE:
            content.append(self._create_mate_section())
        
        # Universal tools
        content.append(self._create_tools_section())
        
        # Fonts section
        content.append(self._create_fonts_section())
    
    def _create_status_section(self) -> Gtk.Widget:
        """Create status banner."""
        group = Adw.PreferencesGroup()
        group.set_title("Desktop Environment")
        
        # DE info
        de_row = Adw.ActionRow()
        de_row.set_title("Environment")
        de_row.set_subtitle(f"{self.desktop.display_name} on {self.desktop.session_type.upper()}")
        de_row.add_prefix(Gtk.Image.new_from_icon_name("tux-computer-symbolic"))
        
        if self.desktop.is_wayland:
            badge = Gtk.Label(label="Wayland")
            badge.add_css_class("success")
            badge.set_valign(Gtk.Align.CENTER)
            de_row.add_suffix(badge)
        else:
            badge = Gtk.Label(label="X11")
            badge.add_css_class("dim-label")
            badge.set_valign(Gtk.Align.CENTER)
            de_row.add_suffix(badge)
        
        group.add(de_row)

        # Current theme - show appropriate info based on desktop
        current_icon = self.theme_manager.get_current_icon_theme()

        theme_row = Adw.ActionRow()
        theme_row.set_title("Current Theme")

        if self.desktop.desktop_env == DesktopEnv.KDE:
            current_plasma = self.theme_manager.get_current_plasma_theme()
            theme_row.set_subtitle(f"Plasma: {current_plasma or 'Unknown'} • Icons: {current_icon or 'Unknown'}")
        else:
            current_gtk = self.theme_manager.get_current_gtk_theme()
            theme_row.set_subtitle(f"GTK: {current_gtk or 'Unknown'} • Icons: {current_icon or 'Unknown'}")

        theme_row.add_prefix(Gtk.Image.new_from_icon_name("tux-applications-graphics-symbolic"))
        group.add(theme_row)

        return group
    
    def _create_appearance_section(self) -> Gtk.Widget:
        """Create appearance section with desktop-appropriate theming options."""
        group = Adw.PreferencesGroup()
        group.set_title("Appearance")

        # KDE Plasma uses different theming system than GTK
        if self.desktop.desktop_env == DesktopEnv.KDE:
            group.set_description("Plasma themes, icons, and cursors")

            # Global Themes (Look and Feel)
            global_row = Adw.ActionRow()
            global_row.set_title("Global Themes")
            global_row.set_subtitle(f"{len(KDE_GLOBAL_THEMES)} Plasma themes available")
            global_row.set_activatable(True)
            global_row.add_prefix(Gtk.Image.new_from_icon_name("tux-preferences-desktop-theme-symbolic"))
            global_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
            global_row.connect("activated", self.on_kde_global_themes)
            group.add(global_row)

            # Kvantum Themes (Qt Application Styling)
            kvantum_row = Adw.ActionRow()
            kvantum_row.set_title("Application Style (Kvantum)")
            kvantum_row.set_subtitle(f"{len(KVANTUM_THEMES)} Qt themes available")
            kvantum_row.set_activatable(True)
            kvantum_row.add_prefix(Gtk.Image.new_from_icon_name("tux-applications-graphics-symbolic"))
            kvantum_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
            kvantum_row.connect("activated", self.on_kvantum_themes)
            group.add(kvantum_row)

            # Color Schemes - launch KDE System Settings
            color_row = Adw.ActionRow()
            color_row.set_title("Color Schemes")
            color_row.set_subtitle("Open KDE System Settings for color customization")
            color_row.set_activatable(True)
            color_row.add_prefix(Gtk.Image.new_from_icon_name("tux-preferences-other-symbolic"))
            color_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
            color_row.connect("activated", self._on_kde_color_schemes)
            group.add(color_row)

            # Icon Themes (uses plasma-apply-icon-theme)
            icon_row = Adw.ActionRow()
            icon_row.set_title("Icon Themes")
            icon_row.set_subtitle(f"{len(ICON_THEMES)} icon packs available")
            icon_row.set_activatable(True)
            icon_row.add_prefix(Gtk.Image.new_from_icon_name("tux-folder-symbolic"))
            icon_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
            icon_row.connect("activated", self.on_icon_themes)
            group.add(icon_row)

            # Cursor Themes (uses plasma-apply-cursortheme)
            cursor_row = Adw.ActionRow()
            cursor_row.set_title("Cursor Themes")
            cursor_row.set_subtitle(f"{len(CURSOR_THEMES)} cursor themes available")
            cursor_row.set_activatable(True)
            cursor_row.add_prefix(Gtk.Image.new_from_icon_name("tux-input-mouse-symbolic"))
            cursor_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
            cursor_row.connect("activated", self.on_cursor_themes)
            group.add(cursor_row)

        else:
            # GTK-based desktops (GNOME, XFCE, Cinnamon, MATE, etc.)
            group.set_description("Themes, icons, and cursors")

            # GTK Themes
            gtk_row = Adw.ActionRow()
            gtk_row.set_title("GTK Themes")
            gtk_row.set_subtitle(f"{len(GTK_THEMES)} themes available")
            gtk_row.set_activatable(True)
            gtk_row.add_prefix(Gtk.Image.new_from_icon_name("tux-preferences-desktop-theme-symbolic"))
            gtk_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
            gtk_row.connect("activated", self.on_gtk_themes)
            group.add(gtk_row)

            # Icon Themes
            icon_row = Adw.ActionRow()
            icon_row.set_title("Icon Themes")
            icon_row.set_subtitle(f"{len(ICON_THEMES)} icon packs available")
            icon_row.set_activatable(True)
            icon_row.add_prefix(Gtk.Image.new_from_icon_name("tux-folder-symbolic"))
            icon_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
            icon_row.connect("activated", self.on_icon_themes)
            group.add(icon_row)

            # Cursor Themes
            cursor_row = Adw.ActionRow()
            cursor_row.set_title("Cursor Themes")
            cursor_row.set_subtitle(f"{len(CURSOR_THEMES)} cursor themes available")
            cursor_row.set_activatable(True)
            cursor_row.add_prefix(Gtk.Image.new_from_icon_name("tux-input-mouse-symbolic"))
            cursor_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
            cursor_row.connect("activated", self.on_cursor_themes)
            group.add(cursor_row)

            # Theme Presets
            presets_row = Adw.ActionRow()
            presets_row.set_title("Theme Presets")
            presets_row.set_subtitle(f"{len(THEME_PRESETS)} complete looks (macOS, Nordic, Dracula...)")
            presets_row.set_activatable(True)
            presets_row.add_prefix(Gtk.Image.new_from_icon_name("tux-emblem-default-symbolic"))
            presets_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
            presets_row.connect("activated", self.on_theme_presets)
            group.add(presets_row)

        return group

    def _on_kde_color_schemes(self, row):
        """Open KDE System Settings to the Colors page."""
        import subprocess
        try:
            # Try to open System Settings directly to Colors module
            subprocess.Popen(['systemsettings', 'kcm_colors'], start_new_session=True)
        except FileNotFoundError:
            try:
                # Fallback: try systemsettings5
                subprocess.Popen(['systemsettings5', 'kcm_colors'], start_new_session=True)
            except FileNotFoundError:
                # Last resort: just open System Settings
                subprocess.Popen(['systemsettings'], start_new_session=True)
    
    def _create_gnome_extensions_section(self) -> Gtk.Widget:
        """Create GNOME extensions section."""
        group = Adw.PreferencesGroup()
        group.set_title("GNOME Extensions")
        group.set_description("Extend GNOME Shell functionality")
        
        # NEW: Extensions Browser (main feature)
        browser_row = Adw.ActionRow()
        browser_row.set_title("Browse & Manage Extensions")
        browser_row.set_subtitle("Search, install, and manage GNOME extensions")
        browser_row.set_activatable(True)
        browser_row.add_prefix(Gtk.Image.new_from_icon_name("tux-web-browser-symbolic"))
        browser_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
        browser_row.connect("activated", self.on_gnome_extensions_browser)
        group.add(browser_row)
        
        # Extension Manager app (external tool)
        em_row = Adw.ActionRow()
        em_row.set_title("Install Extension Manager App")
        em_row.set_subtitle("Standalone app for managing extensions")
        em_row.set_activatable(True)
        em_row.add_prefix(Gtk.Image.new_from_icon_name("tux-application-x-addon-symbolic"))
        em_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
        em_row.connect("activated", self.on_install_extension_manager)
        group.add(em_row)
        
        # Extensions from repos (curated list)
        ext_row = Adw.ActionRow()
        ext_row.set_title("Install from Repos")
        ext_row.set_subtitle(f"{len(GNOME_EXTENSIONS)} extensions in package manager")
        ext_row.set_activatable(True)
        ext_row.add_prefix(Gtk.Image.new_from_icon_name("tux-emblem-system-symbolic"))
        ext_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
        ext_row.connect("activated", self.on_gnome_extensions)
        group.add(ext_row)
        
        return group
    
    def _create_gnome_tweaks_section(self) -> Gtk.Widget:
        """Create GNOME tweaks section with organized categories."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        
        # Define tweak categories by their ID prefixes/keywords
        categories = [
            ("Window Behavior", "windows-symbolic", [
                "titlebar-buttons", "center-new-windows", "edge-tiling", 
                "attach-modal-dialogs", "focus-mode-click", "raise-on-click",
                "resize-with-right-button"
            ]),
            ("Top Bar & Clock", "preferences-system-time-symbolic", [
                "show-weekday", "show-date", "clock-seconds", "clock-24h",
                "show-battery-percentage"
            ]),
            ("Appearance", "preferences-desktop-theme-symbolic", [
                "dark-mode", "animations", "hot-corner"
            ]),
            ("Input Devices", "input-mouse-symbolic", [
                "tap-to-click", "natural-scrolling", "two-finger-scroll",
                "disable-touchpad-typing", "mouse-natural-scroll", "middle-click-paste"
            ]),
            ("Workspaces", "view-grid-symbolic", [
                "dynamic-workspaces", "workspaces-only-primary"
            ]),
            ("Sound", "audio-volume-high-symbolic", [
                "over-amplification", "event-sounds"
            ]),
            ("Power", "battery-symbolic", [
                "suspend-on-lid-close", "show-suspend-button"
            ]),
            ("Privacy & Security", "security-high-symbolic", [
                "automatic-screen-lock", "show-full-name-login"
            ]),
            ("Files", "folder-symbolic", [
                "show-hidden-files", "sort-folders-first"
            ]),
        ]
        
        # Build a lookup dict for tweaks by ID
        tweak_lookup = {tweak.id: tweak for tweak in GNOME_TWEAKS}
        
        for cat_name, cat_icon, tweak_ids in categories:
            group = Adw.PreferencesGroup()
            group.set_title(cat_name)
            
            has_tweaks = False
            for tweak_id in tweak_ids:
                if tweak_id in tweak_lookup:
                    tweak = tweak_lookup[tweak_id]
                    row = Adw.SwitchRow()
                    row.set_title(tweak.name)
                    row.set_subtitle(tweak.description)
                    
                    # Get current state
                    try:
                        is_enabled = self.tweak_manager.is_tweak_enabled(tweak)
                        row.set_active(is_enabled)
                    except Exception:
                        row.set_active(False)
                    
                    # Connect toggle
                    row.connect("notify::active", self.on_tweak_toggled, tweak)
                    
                    group.add(row)
                    has_tweaks = True
            
            if has_tweaks:
                box.append(group)
        
        # GNOME Tweaks tool at the bottom
        tools_group = Adw.PreferencesGroup()
        tools_group.set_title("Advanced Tools")
        
        tweaks_row = Adw.ActionRow()
        tweaks_row.set_title("GNOME Tweaks")
        tweaks_row.set_subtitle("Install the official GNOME Tweaks tool for more options")
        tweaks_row.set_activatable(True)
        tweaks_row.add_prefix(Gtk.Image.new_from_icon_name("tux-applications-system-symbolic"))
        tweaks_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
        tweaks_row.connect("activated", self.on_install_gnome_tweaks)
        tools_group.add(tweaks_row)
        
        # dconf Editor for power users
        dconf_row = Adw.ActionRow()
        dconf_row.set_title("dconf Editor")
        dconf_row.set_subtitle("Low-level settings editor (advanced users)")
        dconf_row.set_activatable(True)
        dconf_row.add_prefix(Gtk.Image.new_from_icon_name("tux-preferences-other-symbolic"))
        dconf_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
        dconf_row.connect("activated", self.on_install_dconf_editor)
        tools_group.add(dconf_row)
        
        box.append(tools_group)
        
        return box
    
    def _create_kde_section(self) -> Gtk.Widget:
        """Create KDE Plasma section with widgets, themes, KWin scripts, and tweaks."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        
        # Widgets section
        widgets_group = Adw.PreferencesGroup()
        widgets_group.set_title("KDE Plasma Widgets")
        widgets_group.set_description("Panel and desktop widgets")
        
        widgets_row = Adw.ActionRow()
        widgets_row.set_title("Plasma Widgets")
        widgets_row.set_subtitle(f"{len(KDE_WIDGETS)} widgets available")
        widgets_row.set_activatable(True)
        widgets_row.add_prefix(Gtk.Image.new_from_icon_name("tux-view-app-grid-symbolic"))
        widgets_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
        widgets_row.connect("activated", self.on_kde_widgets)
        widgets_group.add(widgets_row)

        # Install Kvantum Manager (tool for applying Qt themes)
        kvantum_install = Adw.ActionRow()
        kvantum_install.set_title("Install Kvantum Manager")
        kvantum_install.set_subtitle("Required to apply Kvantum themes from Appearance section")
        kvantum_install.set_activatable(True)
        kvantum_install.add_prefix(Gtk.Image.new_from_icon_name("tux-system-software-install-symbolic"))
        kvantum_install.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
        kvantum_install.connect("activated", self.on_install_kvantum)
        widgets_group.add(kvantum_install)

        box.append(widgets_group)

        # KWin Scripts section
        kwin_group = Adw.PreferencesGroup()
        kwin_group.set_title("KWin Scripts")
        kwin_group.set_description("Window manager extensions")
        
        kwin_row = Adw.ActionRow()
        kwin_row.set_title("Window Manager Scripts")
        kwin_row.set_subtitle(f"{len(KWIN_SCRIPTS)} scripts available (tiling, effects)")
        kwin_row.set_activatable(True)
        kwin_row.add_prefix(Gtk.Image.new_from_icon_name("tux-preferences-system-windows-symbolic"))
        kwin_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
        kwin_row.connect("activated", self.on_kwin_scripts)
        kwin_group.add(kwin_row)
        box.append(kwin_group)
        
        # KDE Tweaks section
        tweaks_group = Adw.PreferencesGroup()
        tweaks_group.set_title("KDE Tweaks")
        tweaks_group.set_description("Quick settings and effects")
        
        for tweak in KDE_TWEAKS:
            row = Adw.SwitchRow()
            row.set_title(tweak.name)
            row.set_subtitle(tweak.description)
            
            # Get current state
            is_enabled = self.tweak_manager.is_tweak_enabled(tweak)
            row.set_active(is_enabled)
            
            # Connect toggle
            row.connect("notify::active", self.on_tweak_toggled, tweak)
            
            tweaks_group.add(row)
        
        box.append(tweaks_group)
        
        return box
    
    def _create_xfce_section(self) -> Gtk.Widget:
        """Create XFCE section with plugins, compositor, and tweaks."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        
        # Plugins section
        plugins_group = Adw.PreferencesGroup()
        plugins_group.set_title("XFCE Panel Plugins")
        plugins_group.set_description("Extend your XFCE panel")
        
        plugins_row = Adw.ActionRow()
        plugins_row.set_title("Panel Plugins")
        plugins_row.set_subtitle(f"{len(XFCE_PLUGINS)} plugins available")
        plugins_row.set_activatable(True)
        plugins_row.add_prefix(Gtk.Image.new_from_icon_name("tux-view-grid-symbolic"))
        plugins_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
        plugins_row.connect("activated", self.on_xfce_plugins)
        plugins_group.add(plugins_row)
        box.append(plugins_group)
        
        # Compositor section
        compositor_group = Adw.PreferencesGroup()
        compositor_group.set_title("Compositor")
        compositor_group.set_description("Window compositing and effects")
        
        compositor_row = Adw.ActionRow()
        compositor_row.set_title("Compositor Tools")
        compositor_row.set_subtitle(f"{len(XFCE_COMPOSITOR_TOOLS)} tools available (picom, compton)")
        compositor_row.set_activatable(True)
        compositor_row.add_prefix(Gtk.Image.new_from_icon_name("tux-applications-graphics-symbolic"))
        compositor_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
        compositor_row.connect("activated", self.on_xfce_compositor)
        compositor_group.add(compositor_row)
        box.append(compositor_group)
        
        # XFCE Tweaks section
        tweaks_group = Adw.PreferencesGroup()
        tweaks_group.set_title("XFCE Tweaks")
        tweaks_group.set_description("Window manager settings")
        
        for tweak in XFCE_TWEAKS:
            row = Adw.SwitchRow()
            row.set_title(tweak.name)
            row.set_subtitle(tweak.description)
            
            # Get current state
            is_enabled = self.tweak_manager.is_tweak_enabled(tweak)
            row.set_active(is_enabled)
            
            # Connect toggle
            row.connect("notify::active", self.on_tweak_toggled, tweak)
            
            tweaks_group.add(row)
        
        box.append(tweaks_group)
        
        return box
    
    def _create_cinnamon_section(self) -> Gtk.Widget:
        """Create Cinnamon-specific section."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        
        # Applets section
        applets_group = Adw.PreferencesGroup()
        applets_group.set_title("Cinnamon Applets")
        applets_group.set_description("Panel applets and widgets")
        
        applets_row = Adw.ActionRow()
        applets_row.set_title("Panel Applets")
        applets_row.set_subtitle(f"{len(CINNAMON_APPLETS)} applets available")
        applets_row.set_activatable(True)
        applets_row.add_prefix(Gtk.Image.new_from_icon_name("tux-list-add-symbolic"))
        applets_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
        applets_row.connect("activated", self.on_cinnamon_applets)
        applets_group.add(applets_row)
        box.append(applets_group)
        
        # Extensions section (Spices)
        extensions_group = Adw.PreferencesGroup()
        extensions_group.set_title("Cinnamon Extensions")
        extensions_group.set_description("Desktop extensions and effects")
        
        extensions_row = Adw.ActionRow()
        extensions_row.set_title("Extensions (Spices)")
        extensions_row.set_subtitle(f"{len(CINNAMON_EXTENSIONS)} extensions available")
        extensions_row.set_activatable(True)
        extensions_row.add_prefix(Gtk.Image.new_from_icon_name("tux-application-x-addon-symbolic"))
        extensions_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
        extensions_row.connect("activated", self.on_cinnamon_extensions)
        extensions_group.add(extensions_row)
        box.append(extensions_group)
        
        # Tools section
        tools_group = Adw.PreferencesGroup()
        tools_group.set_title("Cinnamon Tools")
        tools_group.set_description("Nemo, settings, and utilities")
        
        tools_row = Adw.ActionRow()
        tools_row.set_title("Cinnamon Tools")
        tools_row.set_subtitle(f"{len(CINNAMON_TOOLS)} tools available")
        tools_row.set_activatable(True)
        tools_row.add_prefix(Gtk.Image.new_from_icon_name("tux-applications-utilities-symbolic"))
        tools_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
        tools_row.connect("activated", self.on_cinnamon_tools)
        tools_group.add(tools_row)
        box.append(tools_group)
        
        # Tweaks section
        tweaks_group = Adw.PreferencesGroup()
        tweaks_group.set_title("Cinnamon Tweaks")
        tweaks_group.set_description("Desktop effects and behavior")
        
        for tweak in CINNAMON_TWEAKS:
            row = Adw.SwitchRow()
            row.set_title(tweak.name)
            row.set_subtitle(tweak.description)
            
            # Get current state
            is_enabled = self.tweak_manager.is_tweak_enabled(tweak)
            row.set_active(is_enabled)
            
            # Connect toggle
            row.connect("notify::active", self.on_tweak_toggled, tweak)
            
            tweaks_group.add(row)
        
        box.append(tweaks_group)
        
        return box
    
    def on_cinnamon_applets(self, row):
        """Navigate to Cinnamon applets selection."""
        page = ExtensionSelectionPage(self.window, self.distro, self.desktop,
                                      CINNAMON_APPLETS, "Cinnamon Applets")
        self.window.navigation_view.push(page)
    
    def on_cinnamon_extensions(self, row):
        """Navigate to Cinnamon extensions selection."""
        page = ExtensionSelectionPage(self.window, self.distro, self.desktop,
                                      CINNAMON_EXTENSIONS, "Cinnamon Extensions")
        self.window.navigation_view.push(page)
    
    def on_cinnamon_tools(self, row):
        """Navigate to Cinnamon tools selection."""
        page = ToolSelectionPage(self.window, self.distro, self.desktop,
                                 CINNAMON_TOOLS, "Cinnamon Tools")
        self.window.navigation_view.push(page)
    
    def _create_mate_section(self) -> Gtk.Widget:
        """Create MATE-specific section."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        
        # Applets section
        applets_group = Adw.PreferencesGroup()
        applets_group.set_title("MATE Panel Applets")
        applets_group.set_description("Panel applets and indicators")
        
        applets_row = Adw.ActionRow()
        applets_row.set_title("Panel Applets")
        applets_row.set_subtitle(f"{len(MATE_APPLETS)} applets available")
        applets_row.set_activatable(True)
        applets_row.add_prefix(Gtk.Image.new_from_icon_name("tux-list-add-symbolic"))
        applets_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
        applets_row.connect("activated", self.on_mate_applets)
        applets_group.add(applets_row)
        box.append(applets_group)
        
        # Tools section
        tools_group = Adw.PreferencesGroup()
        tools_group.set_title("MATE Applications")
        tools_group.set_description("Caja, Pluma, and other MATE apps")
        
        tools_row = Adw.ActionRow()
        tools_row.set_title("MATE Tools")
        tools_row.set_subtitle(f"{len(MATE_TOOLS)} tools available")
        tools_row.set_activatable(True)
        tools_row.add_prefix(Gtk.Image.new_from_icon_name("tux-applications-utilities-symbolic"))
        tools_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
        tools_row.connect("activated", self.on_mate_tools)
        tools_group.add(tools_row)
        box.append(tools_group)
        
        # Tweaks section
        tweaks_group = Adw.PreferencesGroup()
        tweaks_group.set_title("MATE Tweaks")
        tweaks_group.set_description("Marco window manager and desktop settings")
        
        for tweak in MATE_TWEAKS:
            row = Adw.SwitchRow()
            row.set_title(tweak.name)
            row.set_subtitle(tweak.description)
            
            # Get current state
            is_enabled = self.tweak_manager.is_tweak_enabled(tweak)
            row.set_active(is_enabled)
            
            # Connect toggle
            row.connect("notify::active", self.on_tweak_toggled, tweak)
            
            tweaks_group.add(row)
        
        box.append(tweaks_group)
        
        return box
    
    def on_mate_applets(self, row):
        """Navigate to MATE applets selection."""
        page = ExtensionSelectionPage(self.window, self.distro, self.desktop,
                                      MATE_APPLETS, "MATE Panel Applets")
        self.window.navigation_view.push(page)
    
    def on_mate_tools(self, row):
        """Navigate to MATE tools selection."""
        page = ToolSelectionPage(self.window, self.distro, self.desktop,
                                 MATE_TOOLS, "MATE Tools")
        self.window.navigation_view.push(page)
    
    def _create_tools_section(self) -> Gtk.Widget:
        """Create universal tools section."""
        group = Adw.PreferencesGroup()
        group.set_title("Desktop Tools")
        group.set_description("Useful utilities for any desktop")
        
        # Filter tools for current DE or universal
        relevant_tools = [t for t in UNIVERSAL_TOOLS 
                        if t.desktop is None or t.desktop == self.desktop.desktop_env]
        
        tools_row = Adw.ActionRow()
        tools_row.set_title("Desktop Utilities")
        tools_row.set_subtitle(f"{len(relevant_tools)} tools available")
        tools_row.set_activatable(True)
        tools_row.add_prefix(Gtk.Image.new_from_icon_name("tux-applications-utilities-symbolic"))
        tools_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
        tools_row.connect("activated", self.on_desktop_tools)
        group.add(tools_row)
        
        return group
    
    def _create_fonts_section(self) -> Gtk.Widget:
        """Create fonts section."""
        group = Adw.PreferencesGroup()
        group.set_title("Fonts")
        group.set_description("Developer and UI fonts")
        
        fonts_row = Adw.ActionRow()
        fonts_row.set_title("Font Packages")
        fonts_row.set_subtitle(f"{len(FONT_PACKAGES)} font families available")
        fonts_row.set_activatable(True)
        fonts_row.add_prefix(Gtk.Image.new_from_icon_name("tux-font-x-generic-symbolic"))
        fonts_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
        fonts_row.connect("activated", self.on_fonts)
        group.add(fonts_row)
        
        return group
    
    # =========================================================================
    # Event Handlers
    # =========================================================================
    
    def on_refresh(self, button):
        """Refresh the page."""
        self._build_content()
        self.window.show_toast("Refreshed")
    
    def on_tweak_toggled(self, row, pspec, tweak: Tweak):
        """Handle tweak toggle."""
        enable = row.get_active()
        success = self.tweak_manager.apply_tweak(tweak, enable)
        
        if success:
            state = "enabled" if enable else "disabled"
            self.window.show_toast(f"{tweak.name} {state}")
        else:
            # Revert the toggle
            row.set_active(not enable)
            self.window.show_toast(f"Failed to apply {tweak.name}")
    
    def on_gtk_themes(self, row):
        """Open GTK themes page."""
        page = ThemeSelectionPage(self.window, self.distro, self.theme_manager, 
                                  GTK_THEMES, ThemeType.GTK, "GTK Themes")
        self.window.navigation_view.push(page)
    
    def on_icon_themes(self, row):
        """Open icon themes page."""
        page = ThemeSelectionPage(self.window, self.distro, self.theme_manager,
                                  ICON_THEMES, ThemeType.ICON, "Icon Themes")
        self.window.navigation_view.push(page)
    
    def on_cursor_themes(self, row):
        """Open cursor themes page."""
        page = ThemeSelectionPage(self.window, self.distro, self.theme_manager,
                                  CURSOR_THEMES, ThemeType.CURSOR, "Cursor Themes")
        self.window.navigation_view.push(page)
    
    def on_gnome_extensions_browser(self, row):
        """Open the GNOME Extensions browser page."""
        page = GnomeExtensionsBrowserPage(self.window, self.distro)
        self.window.navigation_view.push(page)
    
    def on_gnome_extensions(self, row):
        """Open GNOME extensions page."""
        page = ExtensionSelectionPage(self.window, self.distro, self.extension_manager,
                                      GNOME_EXTENSIONS, "GNOME Extensions")
        self.window.navigation_view.push(page)
    
    def on_xfce_plugins(self, row):
        """Open XFCE plugins page."""
        page = ExtensionSelectionPage(self.window, self.distro, None,
                                      XFCE_PLUGINS, "XFCE Plugins")
        self.window.navigation_view.push(page)
    
    def on_desktop_tools(self, row):
        """Open desktop tools page."""
        relevant_tools = [t for t in UNIVERSAL_TOOLS 
                        if t.desktop is None or t.desktop == self.desktop.desktop_env]
        page = ToolSelectionPage(self.window, self.distro, relevant_tools, "Desktop Tools")
        self.window.navigation_view.push(page)
    
    def on_fonts(self, row):
        """Open fonts page."""
        page = ToolSelectionPage(self.window, self.distro, FONT_PACKAGES, "Fonts")
        self.window.navigation_view.push(page)
    
    def on_install_extension_manager(self, row):
        """Install Extension Manager."""
        tool = next((t for t in UNIVERSAL_TOOLS if t.id == "extension-manager"), None)
        if tool:
            self._install_tool(tool)
    
    def on_install_gnome_tweaks(self, row):
        """Install GNOME Tweaks."""
        tool = next((t for t in UNIVERSAL_TOOLS if t.id == "gnome-tweaks"), None)
        if tool:
            self._install_tool(tool)
    
    def on_install_dconf_editor(self, row):
        """Install dconf Editor."""
        tool = next((t for t in UNIVERSAL_TOOLS if t.id == "dconf-editor"), None)
        if tool:
            self._install_tool(tool)
    
    def on_install_kvantum(self, row):
        """Install Kvantum."""
        tool = next((t for t in UNIVERSAL_TOOLS if t.id == "kvantum"), None)
        if tool:
            self._install_tool(tool)
    
    def on_theme_presets(self, row):
        """Open theme presets page."""
        page = ThemePresetPage(self.window, self.distro, self.theme_manager)
        self.window.navigation_view.push(page)
    
    def on_kde_widgets(self, row):
        """Open KDE widgets page."""
        page = ExtensionSelectionPage(self.window, self.distro, None,
                                      KDE_WIDGETS, "KDE Plasma Widgets")
        self.window.navigation_view.push(page)
    
    def on_kde_global_themes(self, row):
        """Open KDE global themes page."""
        page = ThemeSelectionPage(self.window, self.distro, self.theme_manager,
                                  KDE_GLOBAL_THEMES, ThemeType.PLASMA, "KDE Global Themes")
        self.window.navigation_view.push(page)
    
    def on_kvantum_themes(self, row):
        """Open Kvantum themes page."""
        page = ThemeSelectionPage(self.window, self.distro, self.theme_manager,
                                  KVANTUM_THEMES, ThemeType.KVANTUM, "Kvantum Themes")
        self.window.navigation_view.push(page)
    
    def on_kwin_scripts(self, row):
        """Open KWin scripts page."""
        page = ExtensionSelectionPage(self.window, self.distro, None,
                                      KWIN_SCRIPTS, "KWin Scripts")
        self.window.navigation_view.push(page)
    
    def on_xfce_compositor(self, row):
        """Open XFCE compositor tools page."""
        page = ToolSelectionPage(self.window, self.distro, XFCE_COMPOSITOR_TOOLS, "Compositor Tools")
        self.window.navigation_view.push(page)
    
    def _install_tool(self, tool: Tool):
        """Install a tool."""
        family = self.distro.family.value
        packages = tool.packages.get(family, [])
        
        if not packages and tool.flatpak_id:
            # Use Flatpak
            self._install_flatpak(tool.flatpak_id, tool.name)
            return
        
        if not packages:
            self.window.show_toast(f"{tool.name} not available for {self.distro.name}")
            return
        
        plan = {
            "tasks": [{
                "type": "install",
                "name": f"Install {tool.name}",
                "packages": packages
            }]
        }
        
        dialog = PlanExecutionDialog(self.window, plan, f"Installing {tool.name}", self.distro)
        dialog.present()
    
    def _install_flatpak(self, app_id: str, name: str):
        """Install a Flatpak app."""
        import shutil
        
        if not shutil.which('flatpak'):
            self.window.show_toast("Flatpak not installed")
            return
        
        def do_install():
            try:
                result = subprocess.run(
                    ['flatpak', 'install', '-y', 'flathub', app_id],
                    capture_output=True, text=True, timeout=300
                )
                if result.returncode == 0:
                    GLib.idle_add(self.window.show_toast, f"{name} installed")
                else:
                    GLib.idle_add(self.window.show_toast, f"Failed to install {name}")
            except Exception as e:
                GLib.idle_add(self.window.show_toast, f"Error: {e}")
        
        self.window.show_toast(f"Installing {name} from Flathub...")
        thread = threading.Thread(target=do_install, daemon=True)
        thread.start()


# =============================================================================
# Theme Detail Page
# =============================================================================

class ThemeDetailPage(Adw.NavigationPage):
    """Detail page showing theme information."""
    
    def __init__(self, window, theme: Theme, distro, theme_manager: ThemeManager,
                 theme_type: ThemeType, is_queued: bool, has_packages: bool, on_queue_changed,
                 nav_view=None):
        super().__init__(title=theme.name)
        
        self.window = window
        self.theme = theme
        self.distro = distro
        self.theme_manager = theme_manager
        self.theme_type = theme_type
        self.is_queued = is_queued
        self.has_packages = has_packages
        self.on_queue_changed = on_queue_changed
        self.nav_view = nav_view or (window.navigation_view if hasattr(window, 'navigation_view') else None)
        
        self._build_ui()
    
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
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=24)
        clamp.set_child(content_box)
        
        # Theme info header
        info_group = Adw.PreferencesGroup()
        info_group.set_title("Theme Information")
        content_box.append(info_group)
        
        # Name row
        name_row = Adw.ActionRow()
        name_row.set_title("Theme Name")
        name_row.set_subtitle(self.theme.name)
        name_row.add_prefix(Gtk.Image.new_from_icon_name("tux-preferences-desktop-theme-symbolic"))
        info_group.add(name_row)
        
        # Description row
        if self.theme.description:
            desc_row = Adw.ActionRow()
            desc_row.set_title("Description")
            desc_row.set_subtitle(self.theme.description)
            desc_row.add_prefix(Gtk.Image.new_from_icon_name("tux-document-properties-symbolic"))
            info_group.add(desc_row)
        
        # Type row
        type_row = Adw.ActionRow()
        type_row.set_title("Theme Type")
        type_row.set_subtitle(self.theme_type.value.title())
        type_row.add_prefix(Gtk.Image.new_from_icon_name("tux-applications-graphics-symbolic"))
        info_group.add(type_row)
        
        # Packages section
        family = self.distro.family.value
        packages = self.theme.packages.get(family, [])
        
        if packages:
            pkg_group = Adw.PreferencesGroup()
            pkg_group.set_title(f"Packages to Install ({len(packages)})")
            pkg_group.set_description("These packages will be installed from your system's repositories")
            content_box.append(pkg_group)
            
            for pkg in packages:
                pkg_row = Adw.ActionRow()
                pkg_row.set_title(pkg)
                pkg_row.add_prefix(Gtk.Image.new_from_icon_name("tux-package-x-generic-symbolic"))
                pkg_group.add(pkg_row)
        else:
            # Not in repos - show alternative options
            alt_group = Adw.PreferencesGroup()
            alt_group.set_title("Installation Options")
            alt_group.set_description("This theme is not available in your distribution's repositories")
            content_box.append(alt_group)
            
            if self.theme.gnome_look_url and HAS_WEBKIT:
                # Preview & Install via ocs-url (in-app browser)
                gnome_row = Adw.ActionRow()
                gnome_row.set_title("🎨 Preview && Install")
                gnome_row.set_subtitle("Browse and install from gnome-look.org")
                gnome_row.add_prefix(Gtk.Image.new_from_icon_name("tux-applications-graphics-symbolic"))
                gnome_row.set_activatable(True)
                gnome_row.connect("activated", self._on_preview_install)
                
                install_icon = Gtk.Image.new_from_icon_name("tux-go-next-symbolic")
                gnome_row.add_suffix(install_icon)
                alt_group.add(gnome_row)
            elif self.theme.gnome_look_url:
                # Fallback to external browser
                gnome_row = Adw.ActionRow()
                gnome_row.set_title("GNOME Look")
                gnome_row.set_subtitle("Download from gnome-look.org")
                gnome_row.add_prefix(Gtk.Image.new_from_icon_name("tux-web-browser-symbolic"))
                gnome_row.set_activatable(True)
                gnome_row.connect("activated", self._on_open_url, self.theme.gnome_look_url)
                gnome_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
                alt_group.add(gnome_row)
            
            if self.theme.github_url:
                github_row = Adw.ActionRow()
                github_row.set_title("GitHub")
                github_row.set_subtitle("View source and installation instructions")
                github_row.add_prefix(Gtk.Image.new_from_icon_name("tux-folder-remote-symbolic"))
                github_row.set_activatable(True)
                github_row.connect("activated", self._on_open_url, self.theme.github_url)
                github_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
                alt_group.add(github_row)
            
            if self.theme.kde_store_url:
                kde_row = Adw.ActionRow()
                kde_row.set_title("KDE Store")
                kde_row.set_subtitle("Download from KDE Store")
                kde_row.add_prefix(Gtk.Image.new_from_icon_name("tux-web-browser-symbolic"))
                kde_row.set_activatable(True)
                kde_row.connect("activated", self._on_open_url, self.theme.kde_store_url)
                kde_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
                alt_group.add(kde_row)
            
            # AUR hint for Arch
            if self.distro.family == DistroFamily.ARCH:
                aur_row = Adw.ActionRow()
                aur_row.set_title("AUR")
                aur_row.set_subtitle("This theme may be available in the AUR")
                aur_row.add_prefix(Gtk.Image.new_from_icon_name("tux-system-software-install-symbolic"))
                alt_group.add(aur_row)
        
        # Action buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(24)
        content_box.append(button_box)
        
        # Queue button (only if packages available)
        if self.has_packages:
            self.queue_button = Gtk.Button()
            self._update_queue_button()
            self.queue_button.connect("clicked", self._on_queue_clicked)
            button_box.append(self.queue_button)
            
            # Apply button if theme can be applied
            theme_name = self._get_theme_name()
            if theme_name:
                apply_btn = Gtk.Button(label="Apply Theme")
                apply_btn.add_css_class("flat")
                apply_btn.connect("clicked", self._on_apply_clicked)
                button_box.append(apply_btn)
        
        # Status label
        self.status_label = Gtk.Label()
        self.status_label.add_css_class("dim-label")
        self._update_status_label()
        content_box.append(self.status_label)
    
    def _get_theme_name(self) -> str:
        """Get the actual theme name for applying."""
        if self.theme_type == ThemeType.GTK:
            return self.theme.gtk_theme
        elif self.theme_type == ThemeType.ICON:
            return self.theme.icon_theme
        elif self.theme_type == ThemeType.CURSOR:
            return self.theme.cursor_theme
        elif self.theme_type == ThemeType.PLASMA:
            return self.theme.plasma_theme
        elif self.theme_type == ThemeType.KVANTUM:
            return self.theme.kvantum_theme
        return ""
    
    def _on_open_url(self, row, url: str):
        """Open a URL in the default browser."""
        import subprocess
        try:
            subprocess.Popen(['xdg-open', url])
        except Exception as e:
            self.window.show_toast(f"Could not open URL: {e}")
    
    def _on_preview_install(self, row):
        """Open theme preview page for one-click install via ocs-url."""
        if not self.nav_view:
            # Fallback to external browser
            self._on_open_url(row, self.theme.gnome_look_url)
            return
        
        preview_page = ThemePreviewPage(
            window=self.window,
            distro=self.distro,
            theme=self.theme,
            theme_type=self.theme_type,
            nav_view=self.nav_view
        )
        self.nav_view.push(preview_page)
    
    def _on_apply_clicked(self, button):
        """Apply the theme."""
        success = False
        theme_name = self._get_theme_name()
        
        if self.theme_type == ThemeType.GTK and theme_name:
            success = self.theme_manager.apply_gtk_theme(theme_name)
        elif self.theme_type == ThemeType.ICON and theme_name:
            success = self.theme_manager.apply_icon_theme(theme_name)
        elif self.theme_type == ThemeType.CURSOR and theme_name:
            success = self.theme_manager.apply_cursor_theme(theme_name)
        elif self.theme_type == ThemeType.PLASMA and theme_name:
            success = self.theme_manager.apply_plasma_theme(theme_name)
        elif self.theme_type == ThemeType.KVANTUM and theme_name:
            success = self.theme_manager.apply_kvantum_theme(theme_name)
        
        if success:
            self.window.show_toast(f"Applied {theme_name}")
        else:
            self.window.show_toast("Failed to apply theme (is it installed?)")
    
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
        if not self.has_packages:
            self.status_label.set_text("This theme is not available in your repositories")
        elif self.is_queued:
            self.status_label.set_text("✓ This theme is queued for installation")
        else:
            self.status_label.set_text("Click the button above to add to your install queue")
    
    def _on_queue_clicked(self, button):
        """Handle queue button click."""
        self.is_queued = not self.is_queued
        self._update_queue_button()
        self._update_status_label()
        
        # Notify parent
        if self.on_queue_changed:
            self.on_queue_changed(self.theme.id, self.is_queued)


# =============================================================================
# Theme Selection Page
# =============================================================================

class ThemeSelectionPage(Adw.NavigationPage):
    """Page for selecting and installing themes."""
    
    def __init__(self, window, distro, theme_manager: ThemeManager, 
                 themes: list[Theme], theme_type: ThemeType, title: str):
        super().__init__(title=title)
        
        self.window = window
        self.distro = distro
        self.theme_manager = theme_manager
        self.themes = themes
        self.theme_type = theme_type
        self.selected_themes: set[str] = set()
        self.theme_checkboxes: dict[str, Gtk.CheckButton] = {}
        
        self.build_ui()
    
    def build_ui(self):
        """Build the UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
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
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        clamp.set_child(content)
        
        # Current theme info
        current = ""
        if self.theme_type == ThemeType.GTK:
            current = self.theme_manager.get_current_gtk_theme()
        elif self.theme_type == ThemeType.ICON:
            current = self.theme_manager.get_current_icon_theme()
        elif self.theme_type == ThemeType.CURSOR:
            current = self.theme_manager.get_current_cursor_theme()
        elif self.theme_type == ThemeType.PLASMA:
            current = self.theme_manager.get_current_plasma_theme()
        elif self.theme_type == ThemeType.KVANTUM:
            current = self.theme_manager.get_current_kvantum_theme()
        
        if current:
            info_label = Gtk.Label()
            info_label.set_markup(f"<small>Current: <b>{current}</b></small>")
            info_label.add_css_class("dim-label")
            info_label.set_halign(Gtk.Align.START)
            content.append(info_label)
        
        # Theme list
        group = Adw.PreferencesGroup()
        content.append(group)
        
        family = self.distro.family.value
        
        for theme in self.themes:
            packages = theme.packages.get(family, [])
            
            row = Adw.ActionRow()
            row.set_title(theme.name)
            row.set_subtitle(theme.description)
            
            # Checkbox for installation
            checkbox = Gtk.CheckButton()
            checkbox.set_valign(Gtk.Align.CENTER)
            
            # Availability indicator - disable row if no packages
            if packages:
                checkbox.connect("toggled", self.on_theme_toggled, theme.id)
                row.add_prefix(checkbox)
                self.theme_checkboxes[theme.id] = checkbox
                
                # Make row clickable for details
                row.set_activatable(True)
                row.connect("activated", self._on_theme_row_clicked, theme)
                
                # Arrow to show clickable
                arrow = Gtk.Image.new_from_icon_name("tux-go-next-symbolic")
                row.add_suffix(arrow)
            else:
                # Theme not in repos - show helpful installation options
                checkbox.set_sensitive(False)
                row.add_prefix(checkbox)
                
                # Make row clickable even for unavailable themes (to show info/download options)
                row.set_activatable(True)
                row.connect("activated", self._on_theme_row_clicked, theme)
                
                # Arrow to show clickable
                arrow = Gtk.Image.new_from_icon_name("tux-go-next-symbolic")
                row.add_suffix(arrow)
                
                # Status label
                status_label = Gtk.Label(label="Not in repos")
                status_label.add_css_class("dim-label")
                row.add_suffix(status_label)
            
            group.add(row)
        
        # Browse More section
        browse_group = Adw.PreferencesGroup()
        browse_group.set_title("Browse More Online")
        browse_group.set_description("Find and download additional themes")
        content.append(browse_group)
        
        # Determine the appropriate website based on DE
        desktop_info = get_desktop()
        de = desktop_info.desktop_env.value.lower() if desktop_info.desktop_env else "unknown"
        
        # Site URLs by DE and theme type
        sites = []
        
        if self.theme_type == ThemeType.ICON:
            if de in ["gnome", "cinnamon", "mate", "budgie", "unity"]:
                sites.append(("GNOME-Look.org", "https://www.gnome-look.org/browse?cat=132&ord=rating", "tux-emblem-system-symbolic"))
            if de in ["kde", "plasma"]:
                sites.append(("KDE Store", "https://store.kde.org/browse?cat=132&ord=rating", "tux-emblem-system-symbolic"))
            if de == "xfce":
                sites.append(("XFCE-Look.org", "https://www.xfce-look.org/browse?cat=132&ord=rating", "tux-emblem-system-symbolic"))
            sites.append(("Pling.com (Icons)", "https://www.pling.com/browse?cat=132&ord=rating", "tux-emblem-system-symbolic"))
        elif self.theme_type == ThemeType.GTK:
            if de in ["gnome", "cinnamon", "mate", "budgie", "unity"]:
                sites.append(("GNOME-Look.org", "https://www.gnome-look.org/browse?cat=135&ord=rating", "tux-emblem-system-symbolic"))
            if de == "xfce":
                sites.append(("XFCE-Look.org", "https://www.xfce-look.org/browse?cat=135&ord=rating", "tux-emblem-system-symbolic"))
            sites.append(("Pling.com (GTK Themes)", "https://www.pling.com/browse?cat=135&ord=rating", "tux-emblem-system-symbolic"))
        elif self.theme_type == ThemeType.CURSOR:
            sites.append(("GNOME-Look.org (Cursors)", "https://www.gnome-look.org/browse?cat=107&ord=rating", "tux-emblem-system-symbolic"))
            sites.append(("Pling.com (Cursors)", "https://www.pling.com/browse?cat=107&ord=rating", "tux-emblem-system-symbolic"))
        elif self.theme_type == ThemeType.PLASMA:
            sites.append(("KDE Store (Plasma)", "https://store.kde.org/browse?cat=104&ord=rating", "tux-emblem-system-symbolic"))
        elif self.theme_type == ThemeType.KVANTUM:
            sites.append(("KDE Store (Kvantum)", "https://store.kde.org/browse?cat=123&ord=rating", "tux-emblem-system-symbolic"))
        
        for site_name, site_url, icon_name in sites:
            browse_row = Adw.ActionRow()
            browse_row.set_title(f"Browse {site_name}")
            browse_row.set_subtitle("Search and download themes online")
            browse_row.set_activatable(True)
            browse_row.add_prefix(Gtk.Image.new_from_icon_name(icon_name))
            browse_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
            browse_row.connect("activated", self._on_browse_online, site_url)
            browse_group.add(browse_row)
        
        # Install button
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(20)
        content.append(button_box)
        
        self.install_btn = Gtk.Button(label="Install Selected")
        self.install_btn.add_css_class("suggested-action")
        self.install_btn.connect("clicked", self.on_install_clicked)
        self.install_btn.set_sensitive(False)
        button_box.append(self.install_btn)
    
    def _on_theme_row_clicked(self, row, theme: Theme):
        """Show theme detail page when row is clicked."""
        is_queued = theme.id in self.selected_themes
        family = self.distro.family.value
        packages = theme.packages.get(family, [])
        
        detail_page = ThemeDetailPage(
            window=self.window,
            theme=theme,
            distro=self.distro,
            theme_manager=self.theme_manager,
            theme_type=self.theme_type,
            is_queued=is_queued,
            has_packages=len(packages) > 0,
            on_queue_changed=self._on_detail_queue_changed
        )
        self.window.navigation_view.push(detail_page)
    
    def _on_detail_queue_changed(self, theme_id: str, queued: bool):
        """Handle queue change from detail page."""
        if queued:
            self.selected_themes.add(theme_id)
        else:
            self.selected_themes.discard(theme_id)
        
        # Update checkbox state
        if theme_id in self.theme_checkboxes:
            checkbox = self.theme_checkboxes[theme_id]
            checkbox.handler_block_by_func(self.on_theme_toggled)
            checkbox.set_active(queued)
            checkbox.handler_unblock_by_func(self.on_theme_toggled)
        
        self._update_install_button()
    
    def on_theme_toggled(self, checkbox, theme_id: str):
        """Handle theme selection toggle."""
        if checkbox.get_active():
            self.selected_themes.add(theme_id)
        else:
            self.selected_themes.discard(theme_id)
        
        self._update_install_button()
    
    def _on_browse_online(self, row, url: str):
        """Open theme website in embedded browser."""
        page = ThemeBrowserPage(
            window=self.window,
            distro=self.distro,
            url=url,
            title=f"Browse {self.get_title()}",
            theme_type=self.theme_type
        )
        self.window.navigation_view.push(page)
    
    def _update_install_button(self):
        """Update install button state and label."""
        count = len(self.selected_themes)
        self.install_btn.set_sensitive(count > 0)
        if count > 0:
            self.install_btn.set_label(f"Install Selected ({count})")
        else:
            self.install_btn.set_label("Install Selected")
    
    def on_install_clicked(self, button):
        """Install selected themes."""
        family = self.distro.family.value
        all_packages = []
        
        for theme_id in self.selected_themes:
            theme = next((t for t in self.themes if t.id == theme_id), None)
            if theme:
                packages = theme.packages.get(family, [])
                all_packages.extend(packages)
        
        if not all_packages:
            self.window.show_toast("No packages to install")
            return
        
        # Remove duplicates
        all_packages = list(set(all_packages))
        
        plan = {
            "tasks": [{
                "type": "install",
                "name": f"Install themes",
                "packages": all_packages
            }]
        }
        
        dialog = PlanExecutionDialog(self.window, plan, "Installing Themes", self.distro, self._clear_selection_after_install)
        dialog.present()
    
    def _clear_selection_after_install(self):
        """Clear selection after install."""
        self.selected_themes.clear()
        for checkbox in self.theme_checkboxes.values():
            checkbox.set_active(False)
        self.install_btn.set_sensitive(False)
        self.window.show_toast("✓ Themes installed - selection cleared")


class ThemeDownloadDialog(Adw.Dialog):
    """Dialog for downloading/installing themes not in repos."""
    
    def __init__(self, window, distro, theme: Theme, theme_type: ThemeType):
        super().__init__()
        
        self.window = window
        self.distro = distro
        self.theme = theme
        self.theme_type = theme_type
        
        self.set_title(f"Get {theme.name}")
        self.set_content_width(450)
        self.set_content_height(400)
        
        self.build_ui()
    
    def build_ui(self):
        """Build dialog UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        
        close_btn = Gtk.Button(label="Close")
        close_btn.connect("clicked", lambda b: self.close())
        header.pack_start(close_btn)
        
        toolbar_view.add_top_bar(header)
        
        # Content
        clamp = Adw.Clamp()
        clamp.set_maximum_size(400)
        clamp.set_margin_top(20)
        clamp.set_margin_bottom(20)
        clamp.set_margin_start(20)
        clamp.set_margin_end(20)
        toolbar_view.set_content(clamp)
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        clamp.set_child(content)
        
        # Info section
        info_label = Gtk.Label()
        info_label.set_markup(
            f"<b>{self.theme.name}</b> is not available in {self.distro.name}'s "
            f"package repositories.\n\nChoose an installation method below:"
        )
        info_label.set_wrap(True)
        info_label.set_xalign(0)
        content.append(info_label)
        
        # Installation options
        options_group = Adw.PreferencesGroup()
        options_group.set_title("Installation Options")
        content.append(options_group)
        
        # Arch AUR option
        if self.distro.family == DistroFamily.ARCH:
            packages = self.theme.packages.get('arch', [])
            if packages:
                aur_row = Adw.ActionRow()
                aur_row.set_title("Install from AUR")
                aur_row.set_subtitle(f"Package: {packages[0]}")
                aur_row.add_prefix(Gtk.Image.new_from_icon_name("tux-system-software-install-symbolic"))
                
                aur_btn = Gtk.Button(label="Install")
                aur_btn.set_valign(Gtk.Align.CENTER)
                aur_btn.add_css_class("suggested-action")
                aur_btn.connect("clicked", self.on_install_aur, packages[0])
                aur_row.add_suffix(aur_btn)
                
                options_group.add(aur_row)
        
        # gnome-look.org option
        if self.theme.gnome_look_url:
            gnome_row = Adw.ActionRow()
            gnome_row.set_title("Download from GNOME Look")
            gnome_row.set_subtitle("Opens in your browser")
            gnome_row.add_prefix(Gtk.Image.new_from_icon_name("tux-web-browser-symbolic"))
            
            gnome_btn = Gtk.Button(label="Open")
            gnome_btn.set_valign(Gtk.Align.CENTER)
            gnome_btn.connect("clicked", self.on_open_url, self.theme.gnome_look_url)
            gnome_row.add_suffix(gnome_btn)
            
            options_group.add(gnome_row)
        
        # GitHub option
        if self.theme.github_url:
            github_row = Adw.ActionRow()
            github_row.set_title("Download from GitHub")
            github_row.set_subtitle("Clone or download ZIP")
            github_row.add_prefix(Gtk.Image.new_from_icon_name("tux-folder-download-symbolic"))
            
            github_btn = Gtk.Button(label="Open")
            github_btn.set_valign(Gtk.Align.CENTER)
            github_btn.connect("clicked", self.on_open_url, self.theme.github_url)
            github_row.add_suffix(github_btn)
            
            options_group.add(github_row)
        
        # KDE Store option
        if self.theme.kde_store_url:
            kde_row = Adw.ActionRow()
            kde_row.set_title("Download from KDE Store")
            kde_row.set_subtitle("Opens in your browser")
            kde_row.add_prefix(Gtk.Image.new_from_icon_name("tux-kde-symbolic"))
            
            kde_btn = Gtk.Button(label="Open")
            kde_btn.set_valign(Gtk.Align.CENTER)
            kde_btn.connect("clicked", self.on_open_url, self.theme.kde_store_url)
            kde_row.add_suffix(kde_btn)
            
            options_group.add(kde_row)
        
        # Install ocs-url helper
        import shutil
        if not shutil.which('ocs-url'):
            helper_group = Adw.PreferencesGroup()
            helper_group.set_title("One-Click Install Helper")
            helper_group.set_description(
                "Install ocs-url to enable one-click installs from gnome-look.org"
            )
            content.append(helper_group)
            
            ocs_row = Adw.ActionRow()
            ocs_row.set_title("Install ocs-url")
            ocs_row.set_subtitle("Enables 'Install' buttons on gnome-look.org")
            ocs_row.add_prefix(Gtk.Image.new_from_icon_name("tux-application-x-addon-symbolic"))
            
            ocs_btn = Gtk.Button(label="Install")
            ocs_btn.set_valign(Gtk.Align.CENTER)
            ocs_btn.add_css_class("suggested-action")
            ocs_btn.connect("clicked", self.on_install_ocs_url)
            ocs_row.add_suffix(ocs_btn)
            
            helper_group.add(ocs_row)
        
        # Manual install instructions
        manual_group = Adw.PreferencesGroup()
        manual_group.set_title("Manual Installation")
        content.append(manual_group)
        
        # Determine target directory
        if self.theme_type in (ThemeType.GTK, ThemeType.PLASMA, ThemeType.KVANTUM):
            target_dir = "~/.themes"
        elif self.theme_type == ThemeType.ICON:
            target_dir = "~/.icons"
        elif self.theme_type == ThemeType.CURSOR:
            target_dir = "~/.icons"
        else:
            target_dir = "~/.themes"
        
        instructions = Gtk.Label()
        instructions.set_markup(
            f"<small>1. Download the theme archive\n"
            f"2. Extract to <b>{target_dir}</b>\n"
            f"3. Apply using GNOME Tweaks or Settings</small>"
        )
        instructions.set_xalign(0)
        instructions.set_margin_start(15)
        instructions.add_css_class("dim-label")
        manual_group.add(instructions)
    
    def on_open_url(self, button, url: str):
        """Open URL in default browser."""
        import subprocess
        try:
            subprocess.Popen(['xdg-open', url])
            self.window.show_toast(f"Opened in browser")
        except Exception as e:
            self.window.show_toast(f"Failed to open browser")
    
    def on_install_aur(self, button, package: str):
        """Install package from AUR using available helper."""
        import shutil
        
        # Find AUR helper
        aur_helper = None
        for helper in ['yay', 'paru', 'pikaur', 'trizen']:
            if shutil.which(helper):
                aur_helper = helper
                break
        
        if not aur_helper:
            self.window.show_toast("No AUR helper found. Install yay or paru first.")
            return
        
        # Open terminal with AUR install command
        import subprocess
        cmd = f"{aur_helper} -S {package}"
        
        # Try various terminal emulators
        terminals = [
            ['gnome-terminal', '--', 'bash', '-c', f'{cmd}; read -p "Press Enter to close..."'],
            ['konsole', '-e', 'bash', '-c', f'{cmd}; read -p "Press Enter to close..."'],
            ['xfce4-terminal', '-e', f'bash -c "{cmd}; read -p \\"Press Enter to close...\\""'],
            ['xterm', '-e', f'bash -c "{cmd}; read -p \\"Press Enter to close...\\""'],
        ]
        
        for term_cmd in terminals:
            if shutil.which(term_cmd[0]):
                try:
                    subprocess.Popen(term_cmd)
                    self.window.show_toast(f"Installing {package} via {aur_helper}")
                    self.close()
                    return
                except Exception:
                    continue
        
        self.window.show_toast("Could not open terminal. Run manually: " + cmd)
    
    def on_install_ocs_url(self, button):
        """Install ocs-url helper."""
        if self.distro.family == DistroFamily.ARCH:
            # Install from AUR
            self.on_install_aur(button, "ocs-url")
        elif self.distro.family == DistroFamily.FEDORA:
            # Open ocs-url download page for RPM
            self.on_open_url(button, "https://www.gnome-look.org/p/1136805/")
            self.window.show_toast("Download the Fedora RPM and install with: sudo dnf install ./ocs-url*.rpm")
        elif self.distro.family == DistroFamily.DEBIAN:
            # Open ocs-url download page for DEB
            self.on_open_url(button, "https://www.gnome-look.org/p/1136805/")
            self.window.show_toast("Download the DEB and install with: sudo dpkg -i ocs-url*.deb")
        elif self.distro.family == DistroFamily.OPENSUSE:
            # Open ocs-url download page for RPM
            self.on_open_url(button, "https://www.gnome-look.org/p/1136805/")
            self.window.show_toast("Download the openSUSE RPM and install with: sudo zypper install ./ocs-url*.rpm")
        else:
            self.on_open_url(button, "https://www.gnome-look.org/p/1136805/")


# =============================================================================
# Theme Preview Page (with ocs-url integration)
# =============================================================================

class ThemePreviewPage(Adw.NavigationPage):
    """Preview and install themes from gnome-look.org via ocs-url."""
    
    def __init__(self, window, distro, theme: Theme, theme_type: ThemeType, nav_view):
        super().__init__(title=f"Preview: {theme.name}")
        
        self.window = window
        self.distro = distro
        self.theme = theme
        self.theme_type = theme_type
        self.nav_view = nav_view
        self.webview = None
        self.ocs_installing = False
        
        self.build_ui()
    
    def build_ui(self):
        """Build the preview page UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header bar
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)
        
        # Main content box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        toolbar_view.set_content(main_box)
        
        if not HAS_WEBKIT:
            # WebKit not available - show fallback
            self._show_no_webkit_fallback(main_box)
            return
        
        # Info bar at top
        info_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        info_bar.set_margin_start(16)
        info_bar.set_margin_end(16)
        info_bar.set_margin_top(8)
        info_bar.set_margin_bottom(8)
        info_bar.add_css_class("card")
        
        info_icon = Gtk.Image.new_from_icon_name("tux-dialog-information-symbolic")
        info_bar.append(info_icon)
        
        info_label = Gtk.Label()
        info_label.set_markup(
            "<small>Click the <b>Install</b> button on the website to install the theme. "
            "Choose your preferred variant.</small>"
        )
        info_label.set_wrap(True)
        info_label.set_xalign(0)
        info_label.set_hexpand(True)
        info_bar.append(info_label)
        
        main_box.append(info_bar)
        
        # WebView for gnome-look.org
        self.webview = WebKit.WebView()
        self.webview.set_vexpand(True)
        self.webview.set_hexpand(True)
        
        # Connect to decide-policy to intercept ocs:// links
        self.webview.connect("decide-policy", self._on_decide_policy)
        
        # Configure settings
        settings = self.webview.get_settings()
        settings.set_enable_javascript(True)
        settings.set_enable_javascript_markup(True)
        
        # Load the gnome-look page
        url = self.theme.gnome_look_url or self.theme.kde_store_url
        if url:
            self.webview.load_uri(url)
        
        main_box.append(self.webview)
        
        # Status bar at bottom
        status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        status_bar.set_margin_start(16)
        status_bar.set_margin_end(16)
        status_bar.set_margin_top(8)
        status_bar.set_margin_bottom(8)
        
        self.status_label = Gtk.Label(label="Browse the theme and click Install when ready")
        self.status_label.add_css_class("dim-label")
        self.status_label.set_hexpand(True)
        self.status_label.set_xalign(0)
        status_bar.append(self.status_label)
        
        # Manual open button
        open_btn = Gtk.Button(label="Open in Browser")
        open_btn.add_css_class("flat")
        open_btn.connect("clicked", self._on_open_external)
        status_bar.append(open_btn)
        
        main_box.append(status_bar)
    
    def _show_no_webkit_fallback(self, container):
        """Show fallback when WebKit is not available."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_valign(Gtk.Align.CENTER)
        box.set_vexpand(True)
        box.set_margin_start(32)
        box.set_margin_end(32)
        
        icon = Gtk.Image.new_from_icon_name("tux-web-browser-symbolic")
        icon.set_pixel_size(64)
        icon.add_css_class("dim-label")
        box.append(icon)
        
        title = Gtk.Label(label="WebKit Not Available")
        title.add_css_class("title-2")
        box.append(title)
        
        desc = Gtk.Label(label="Install webkit2gtk to enable in-app preview")
        desc.add_css_class("dim-label")
        box.append(desc)
        
        # Open in browser button
        open_btn = Gtk.Button(label="Open in External Browser")
        open_btn.add_css_class("suggested-action")
        open_btn.connect("clicked", self._on_open_external)
        box.append(open_btn)
        
        container.append(box)
    
    def _on_decide_policy(self, webview, decision, decision_type):
        """Handle navigation - intercept ocs:// links."""
        if decision_type == WebKit.PolicyDecisionType.NAVIGATION_ACTION:
            nav_action = decision.get_navigation_action()
            request = nav_action.get_request()
            uri = request.get_uri()
            
            if uri:
                # Check for ocs:// links
                if uri.startswith("ocs://"):
                    decision.ignore()
                    self._handle_ocs_url(uri)
                    return True
                
                # Allow navigation within opendesktop family domains
                allowed_domains = [
                    # GNOME
                    'gnome-look.org', 'www.gnome-look.org',
                    # KDE
                    'kde-store.net', 'www.kde-store.net',
                    'store.kde.org', 'www.store.kde.org',
                    # XFCE
                    'xfce-look.org', 'www.xfce-look.org',
                    # Cinnamon
                    'cinnamon-look.org', 'www.cinnamon-look.org',
                    # MATE
                    'mate-look.org', 'www.mate-look.org',
                    # Enlightenment
                    'enlightenment-themes.org', 'www.enlightenment-themes.org',
                    # General opendesktop
                    'opendesktop.org', 'www.opendesktop.org',
                    'pling.com', 'www.pling.com',
                    'linux-apps.com', 'www.linux-apps.com',
                ]
                
                from urllib.parse import urlparse
                parsed = urlparse(uri)
                if any(domain in parsed.netloc for domain in allowed_domains):
                    decision.use()
                    return False
                
                # Block navigation to other sites
                decision.ignore()
                return True
        
        decision.use()
        return False
    
    def _handle_ocs_url(self, ocs_uri: str):
        """Handle an ocs:// URI - download and install theme directly."""
        self.status_label.set_text("🎨 Downloading theme...")
        
        if self.window:
            self.window.show_toast(f"📦 Downloading {self.theme.name}...")
        
        # Parse the ocs:// URL
        # Format: ocs://install?url=https%3A%2F%2F...&type=themes&filename=Name.tar.xz
        try:
            from urllib.parse import urlparse, parse_qs, unquote
            
            # Remove ocs:// prefix and parse
            if ocs_uri.startswith('ocs://'):
                ocs_uri = ocs_uri[6:]  # Remove 'ocs://'
            
            # Parse the path and query
            if '?' in ocs_uri:
                path, query = ocs_uri.split('?', 1)
            else:
                self.status_label.set_text("Invalid ocs:// URL format")
                return
            
            params = parse_qs(query)
            
            # Get the download URL
            download_url = params.get('url', [None])[0]
            if download_url:
                download_url = unquote(download_url)
            
            # Get the content type
            content_type = params.get('type', ['themes'])[0]
            
            # Get the filename
            filename = params.get('filename', [None])[0]
            if filename:
                filename = unquote(filename)
            
            if not download_url:
                self.status_label.set_text("No download URL in ocs:// link")
                if self.window:
                    self.window.show_toast("❌ Invalid download link")
                return
            
            # Download and install in background thread
            def do_download_and_install():
                try:
                    success, message = self._download_and_install_theme(
                        download_url, content_type, filename
                    )
                    GLib.idle_add(self._on_theme_installed, success, message)
                except Exception as e:
                    GLib.idle_add(self._on_theme_installed, False, str(e))
            
            threading.Thread(target=do_download_and_install, daemon=True).start()
            
        except Exception as e:
            self.status_label.set_text(f"Error parsing URL: {e}")
            if self.window:
                self.window.show_toast(f"❌ Error: {e}")
    
    def _download_and_install_theme(self, url: str, content_type: str, filename: str) -> tuple[bool, str]:
        """Download and install a theme/icon pack. Returns (success, message)."""
        import tempfile
        import tarfile
        import zipfile
        
        # Determine install directory based on content type
        home = Path.home()
        
        # GTK themes (GNOME, XFCE, Cinnamon, MATE)
        if content_type in ['themes', 'gtk3-themes', 'gtk-themes', 'gnome-shell-themes',
                            'xfce-themes', 'cinnamon-themes', 'mate-themes', 'metacity-themes']:
            install_dir = home / '.themes'
        
        # KDE/Plasma specific
        elif content_type in ['plasma-themes', 'plasma5-themes', 'plasma-desktopthemes']:
            install_dir = home / '.local' / 'share' / 'plasma' / 'desktoptheme'
        elif content_type in ['plasma-look-and-feel', 'plasma-lookandfeel']:
            install_dir = home / '.local' / 'share' / 'plasma' / 'look-and-feel'
        elif content_type in ['aurorae-themes', 'kde-window-decorations']:
            install_dir = home / '.local' / 'share' / 'aurorae' / 'themes'
        elif content_type in ['color-schemes', 'kde-color-schemes']:
            install_dir = home / '.local' / 'share' / 'color-schemes'
        elif content_type in ['kvantum-themes', 'kvantum']:
            install_dir = home / '.config' / 'Kvantum'
        elif content_type in ['plasma-splashscreens', 'kde-splash']:
            install_dir = home / '.local' / 'share' / 'plasma' / 'look-and-feel'
        elif content_type in ['konsole-themes', 'konsole']:
            install_dir = home / '.local' / 'share' / 'konsole'
        elif content_type in ['yakuake-skins']:
            install_dir = home / '.local' / 'share' / 'yakuake' / 'skins'
        
        # Icons (use XDG standard path - GNOME Settings looks here)
        elif content_type in ['icons', 'icon-themes', 'full-icon-themes', 'kde-icons',
                              'gnome-icons', 'xfce-icons', 'cinnamon-icons', 'mate-icons',
                              'icon-theme', 'icon', 'icons-gnome', 'icons-kde']:
            install_dir = home / '.local' / 'share' / 'icons'
        
        # Cursors (also go in icons directory)
        elif content_type in ['cursors', 'cursor-themes', 'xcursors', 'x11-cursors',
                              'cursor', 'cursor-theme', 'mouse-cursors', 'xcursor']:
            install_dir = home / '.local' / 'share' / 'icons'
        
        # Wallpapers (universal)
        elif content_type in ['wallpapers', 'wallpaper', 'wallpapers-hd', 'backgrounds',
                              'gnome-backgrounds', 'kde-wallpapers', 'desktop-wallpapers',
                              'wallpapers-uhd', 'wallpapers-4k']:
            install_dir = home / 'Pictures' / 'Wallpapers'
        
        # Fonts (universal)
        elif content_type in ['fonts', 'font', 'ttf-fonts', 'otf-fonts']:
            install_dir = home / '.local' / 'share' / 'fonts'
        
        # SDDM login themes (KDE)
        elif content_type in ['sddm-themes', 'sddm', 'sddm-theme']:
            install_dir = home / '.local' / 'share' / 'sddm' / 'themes'
        
        # GDM/LightDM themes (GNOME)
        elif content_type in ['gdm-themes', 'lightdm-themes']:
            install_dir = home / '.themes'  # These typically need system install
        
        # Conky configs
        elif content_type in ['conky', 'conky-themes', 'conky-configs']:
            install_dir = home / '.config' / 'conky'
        
        # Plank themes (dock)
        elif content_type in ['plank-themes', 'plank']:
            install_dir = home / '.local' / 'share' / 'plank' / 'themes'
        
        # Latte Dock themes (KDE)
        elif content_type in ['latte-dock', 'latte-layouts']:
            install_dir = home / '.config' / 'latte'
        
        # Rofi themes
        elif content_type in ['rofi-themes', 'rofi']:
            install_dir = home / '.config' / 'rofi' / 'themes'
        
        # Default to ~/.themes for unknown types
        else:
            install_dir = home / '.themes'
        
        # Create install directory if needed
        install_dir.mkdir(parents=True, exist_ok=True)
        
        # Create temp directory for download
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Determine filename if not provided
            if not filename:
                filename = url.split('/')[-1]
                if not filename or '.' not in filename:
                    filename = 'theme-download.tar.xz'
            
            download_path = tmpdir / filename
            
            # Download the file
            try:
                result = subprocess.run(
                    ['wget', '-q', '--show-progress', '-O', str(download_path), url],
                    capture_output=True, text=True, timeout=120
                )
                if result.returncode != 0:
                    # Try curl as fallback
                    result = subprocess.run(
                        ['curl', '-L', '-o', str(download_path), url],
                        capture_output=True, text=True, timeout=120
                    )
                    if result.returncode != 0:
                        return False, "Download failed"
            except subprocess.TimeoutExpired:
                return False, "Download timed out"
            except Exception as e:
                return False, f"Download error: {e}"
            
            if not download_path.exists() or download_path.stat().st_size == 0:
                return False, "Downloaded file is empty"
            
            # Extract the archive
            try:
                if filename.endswith('.tar.xz') or filename.endswith('.tar.gz') or filename.endswith('.tar.bz2') or filename.endswith('.tar'):
                    with tarfile.open(download_path) as tar:
                        # Get the top-level directory name
                        members = tar.getmembers()
                        if members:
                            top_dirs = set()
                            for m in members:
                                parts = m.name.split('/')
                                if parts[0]:
                                    top_dirs.add(parts[0])
                            
                            # Extract to install directory
                            tar.extractall(path=install_dir)
                            
                            theme_name = list(top_dirs)[0] if len(top_dirs) == 1 else filename.rsplit('.', 2)[0]
                        else:
                            return False, "Archive is empty"
                            
                elif filename.endswith('.zip'):
                    with zipfile.ZipFile(download_path, 'r') as zf:
                        # Get the top-level directory name
                        names = zf.namelist()
                        if names:
                            top_dirs = set()
                            for n in names:
                                parts = n.split('/')
                                if parts[0]:
                                    top_dirs.add(parts[0])
                            
                            # Extract to install directory
                            zf.extractall(path=install_dir)
                            
                            theme_name = list(top_dirs)[0] if len(top_dirs) == 1 else filename.rsplit('.', 1)[0]
                        else:
                            return False, "Archive is empty"
                else:
                    return False, f"Unsupported archive format: {filename}"
                
                # Update icon cache and create symlinks for icon/cursor themes
                if content_type in ['icons', 'icon-themes', 'full-icon-themes', 'kde-icons',
                                   'gnome-icons', 'xfce-icons', 'cinnamon-icons', 'mate-icons',
                                   'icon-theme', 'icon', 'icons-gnome', 'icons-kde',
                                   'cursors', 'cursor-themes', 'xcursors', 'x11-cursors',
                                   'cursor', 'cursor-theme', 'mouse-cursors', 'xcursor']:
                    theme_path = install_dir / theme_name
                    if theme_path.exists():
                        try:
                            subprocess.run(
                                ['gtk-update-icon-cache', '-f', '-t', str(theme_path)],
                                capture_output=True, timeout=30
                            )
                        except Exception:
                            pass  # Icon cache update is optional
                        
                        # Create symlink in ~/.icons for legacy compatibility
                        legacy_dir = home / '.icons'
                        legacy_dir.mkdir(parents=True, exist_ok=True)
                        legacy_link = legacy_dir / theme_name
                        if not legacy_link.exists():
                            try:
                                legacy_link.symlink_to(theme_path)
                            except Exception:
                                pass  # Symlink is optional
                    
            except Exception as e:
                return False, f"Extraction failed: {e}"
        
        return True, f"Installed to {install_dir}"
    
    def _on_theme_installed(self, success: bool, message: str):
        """Handle theme installation completion."""
        if success:
            self.status_label.set_text(f"✓ {self.theme.name} installed!")
            if self.window:
                self.window.show_toast(f"✓ {self.theme.name} installed! You may need to select it in Settings → Appearance")
        else:
            self.status_label.set_text(f"❌ Installation failed: {message}")
            if self.window:
                self.window.show_toast(f"❌ Failed: {message}")
        
        return False
    
    def _on_open_external(self, button):
        """Open the theme page in external browser."""
        url = self.theme.gnome_look_url or self.theme.kde_store_url
        if url:
            subprocess.Popen(['xdg-open', url])


# =============================================================================
# =============================================================================
# Theme Browser Page (embedded browser for gnome-look/kde-store/etc)
# =============================================================================

class ThemeBrowserPage(Adw.NavigationPage):
    """Embedded browser for browsing and installing themes from online stores."""
    
    def __init__(self, window, distro, url: str, title: str, theme_type: ThemeType):
        super().__init__(title=title)
        
        self.window = window
        self.distro = distro
        self.url = url
        self.theme_type = theme_type
        self.webview = None
        
        self.build_ui()
    
    def build_ui(self):
        """Build the browser UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header bar with navigation
        header = Adw.HeaderBar()
        toolbar_view.add_top_bar(header)
        
        # Navigation buttons
        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        nav_box.add_css_class("linked")
        
        self.back_btn = Gtk.Button()
        self.back_btn.set_icon_name("tux-go-previous-symbolic")
        self.back_btn.set_tooltip_text("Back")
        self.back_btn.set_sensitive(False)
        self.back_btn.connect("clicked", self._on_back)
        nav_box.append(self.back_btn)
        
        self.forward_btn = Gtk.Button()
        self.forward_btn.set_icon_name("tux-go-next-symbolic")
        self.forward_btn.set_tooltip_text("Forward")
        self.forward_btn.set_sensitive(False)
        self.forward_btn.connect("clicked", self._on_forward)
        nav_box.append(self.forward_btn)
        
        refresh_btn = Gtk.Button()
        refresh_btn.set_icon_name("tux-view-refresh-symbolic")
        refresh_btn.set_tooltip_text("Refresh")
        refresh_btn.connect("clicked", self._on_refresh)
        nav_box.append(refresh_btn)
        
        header.pack_start(nav_box)
        
        # Open in external browser button
        external_btn = Gtk.Button()
        external_btn.set_icon_name("tux-emblem-system-symbolic")
        external_btn.set_tooltip_text("Open in external browser")
        external_btn.connect("clicked", self._on_open_external)
        header.pack_end(external_btn)
        
        # Main content
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        toolbar_view.set_content(main_box)
        
        if not HAS_WEBKIT:
            self._show_no_webkit_fallback(main_box)
            return
        
        # Info bar
        info_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        info_bar.set_margin_start(16)
        info_bar.set_margin_end(16)
        info_bar.set_margin_top(8)
        info_bar.set_margin_bottom(8)
        
        info_icon = Gtk.Image.new_from_icon_name("tux-dialog-information-symbolic")
        info_bar.append(info_icon)
        
        info_label = Gtk.Label()
        info_label.set_markup(
            "<small>Click <b>Install</b> on any theme to download and install it automatically. "
            "Tux Assistant handles the installation for you!</small>"
        )
        info_label.set_wrap(True)
        info_label.set_xalign(0)
        info_label.set_hexpand(True)
        info_bar.append(info_label)
        
        main_box.append(info_bar)
        main_box.append(Gtk.Separator(orientation=Gtk.Orientation.HORIZONTAL))
        
        # WebView
        self.webview = WebKit.WebView()
        self.webview.set_vexpand(True)
        self.webview.set_hexpand(True)
        
        # Connect signals
        self.webview.connect("decide-policy", self._on_decide_policy)
        self.webview.connect("load-changed", self._on_load_changed)
        
        # Configure settings
        settings = self.webview.get_settings()
        settings.set_enable_javascript(True)
        settings.set_enable_javascript_markup(True)
        
        # Load the URL
        self.webview.load_uri(self.url)
        
        main_box.append(self.webview)
        
        # Status bar
        self.status_label = Gtk.Label()
        self.status_label.set_markup("<small>Loading...</small>")
        self.status_label.add_css_class("dim-label")
        self.status_label.set_margin_top(4)
        self.status_label.set_margin_bottom(4)
        main_box.append(self.status_label)
    
    def _show_no_webkit_fallback(self, container):
        """Show fallback when WebKit isn't available."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        box.set_valign(Gtk.Align.CENTER)
        box.set_halign(Gtk.Align.CENTER)
        box.set_margin_top(40)
        box.set_margin_bottom(40)
        container.append(box)
        
        icon = Gtk.Image.new_from_icon_name("tux-dialog-warning-symbolic")
        icon.set_pixel_size(64)
        box.append(icon)
        
        label = Gtk.Label()
        label.set_markup("<b>WebKit Not Available</b>\n\nInstall WebKitGTK for the embedded browser.")
        label.set_justify(Gtk.Justification.CENTER)
        box.append(label)
        
        open_btn = Gtk.Button(label="Open in External Browser")
        open_btn.add_css_class("suggested-action")
        open_btn.connect("clicked", self._on_open_external)
        box.append(open_btn)
    
    def _on_back(self, button):
        if self.webview and self.webview.can_go_back():
            self.webview.go_back()
    
    def _on_forward(self, button):
        if self.webview and self.webview.can_go_forward():
            self.webview.go_forward()
    
    def _on_refresh(self, button):
        if self.webview:
            self.webview.reload()
    
    def _on_open_external(self, button):
        import subprocess
        url = self.webview.get_uri() if self.webview else self.url
        try:
            subprocess.Popen(['xdg-open', url])
        except Exception as e:
            self.window.show_toast(f"Could not open browser: {e}")
    
    def _on_load_changed(self, webview, event):
        """Update navigation buttons and status."""
        if event == WebKit.LoadEvent.STARTED:
            self.status_label.set_markup("<small>Loading...</small>")
        elif event == WebKit.LoadEvent.FINISHED:
            title = webview.get_title() or "Theme Browser"
            self.status_label.set_markup(f"<small>{title}</small>")
            self.back_btn.set_sensitive(webview.can_go_back())
            self.forward_btn.set_sensitive(webview.can_go_forward())
    
    def _on_decide_policy(self, webview, decision, decision_type):
        """Intercept navigation to handle ocs:// links."""
        if decision_type == WebKit.PolicyDecisionType.NAVIGATION_ACTION:
            nav_action = decision.get_navigation_action()
            request = nav_action.get_request()
            uri = request.get_uri()
            
            # Handle ocs:// protocol
            if uri and uri.startswith('ocs://'):
                decision.ignore()
                self._handle_ocs_url(uri)
                return True
        
        return False
    
    def _handle_ocs_url(self, ocs_uri: str):
        """Handle ocs:// URL - download and install theme."""
        self.status_label.set_markup("<small>🎨 Downloading theme...</small>")
        self.window.show_toast("📦 Downloading theme...")
        
        try:
            from urllib.parse import parse_qs, unquote
            
            # Parse ocs:// URL
            if ocs_uri.startswith('ocs://'):
                ocs_uri = ocs_uri[6:]
            
            if '?' in ocs_uri:
                path, query = ocs_uri.split('?', 1)
            else:
                self.window.show_toast("❌ Invalid ocs:// URL")
                return
            
            params = parse_qs(query)
            download_url = params.get('url', [None])[0]
            if download_url:
                download_url = unquote(download_url)
            
            content_type = params.get('type', ['themes'])[0]
            filename = params.get('filename', [None])[0]
            if filename:
                filename = unquote(filename)
            
            # Log for debugging
            print(f"[OCS] content_type={content_type}, filename={filename}")
            print(f"[OCS] download_url={download_url}")
            
            if not download_url:
                self.window.show_toast("❌ No download URL in link")
                return
            
            # Download and install in background
            def do_install():
                try:
                    success, message = self._download_and_install_theme(download_url, content_type, filename)
                    GLib.idle_add(self._on_install_complete, success, message)
                except Exception as e:
                    GLib.idle_add(self._on_install_complete, False, str(e))
            
            threading.Thread(target=do_install, daemon=True).start()
            
        except Exception as e:
            self.window.show_toast(f"❌ Error: {e}")
    
    def _download_and_install_theme(self, url: str, content_type: str, filename: str) -> tuple[bool, str]:
        """Download and install a theme. Returns (success, message)."""
        import tempfile
        import tarfile
        import zipfile
        import urllib.request
        import subprocess
        
        home = Path.home()
        content_type_lower = content_type.lower() if content_type else ""
        
        # Determine install directory based on content type
        # Use flexible matching to handle variations
        
        # Icons - check for 'icon' anywhere in the type
        if 'icon' in content_type_lower:
            install_dir = home / '.local' / 'share' / 'icons'
            is_icon_theme = True
        # Cursors
        elif 'cursor' in content_type_lower or 'xcursor' in content_type_lower:
            install_dir = home / '.local' / 'share' / 'icons'
            is_icon_theme = True
        # Plasma/KDE specific
        elif 'plasma' in content_type_lower and 'desktoptheme' in content_type_lower:
            install_dir = home / '.local' / 'share' / 'plasma' / 'desktoptheme'
            is_icon_theme = False
        elif 'plasma' in content_type_lower and ('look' in content_type_lower or 'feel' in content_type_lower):
            install_dir = home / '.local' / 'share' / 'plasma' / 'look-and-feel'
            is_icon_theme = False
        elif 'aurorae' in content_type_lower or 'window-decoration' in content_type_lower:
            install_dir = home / '.local' / 'share' / 'aurorae' / 'themes'
            is_icon_theme = False
        elif 'color-scheme' in content_type_lower:
            install_dir = home / '.local' / 'share' / 'color-schemes'
            is_icon_theme = False
        elif 'kvantum' in content_type_lower:
            install_dir = home / '.config' / 'Kvantum'
            is_icon_theme = False
        # GTK/GNOME themes
        elif 'gtk' in content_type_lower or 'gnome-shell' in content_type_lower:
            install_dir = home / '.themes'
            is_icon_theme = False
        elif 'theme' in content_type_lower:
            # Generic "themes" - probably GTK
            install_dir = home / '.themes'
            is_icon_theme = False
        # Wallpapers
        elif 'wallpaper' in content_type_lower or 'background' in content_type_lower:
            install_dir = home / '.local' / 'share' / 'wallpapers'
            is_icon_theme = False
        else:
            # Default fallback - if we got here via icon themes browser, assume icons
            if self.theme_type == ThemeType.ICON:
                install_dir = home / '.local' / 'share' / 'icons'
                is_icon_theme = True
            elif self.theme_type == ThemeType.CURSOR:
                install_dir = home / '.local' / 'share' / 'icons'
                is_icon_theme = True
            else:
                install_dir = home / '.themes'
                is_icon_theme = False
        
        print(f"[OCS] Installing to: {install_dir}")
        install_dir.mkdir(parents=True, exist_ok=True)
        
        # Download to temp file
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=filename or '.tar.gz') as tmp:
                tmp_path = Path(tmp.name)
                urllib.request.urlretrieve(url, tmp_path)
        except Exception as e:
            return False, f"Download failed: {e}"
        
        theme_name = "Unknown"
        try:
            # Extract archive
            if tmp_path.suffix in ['.gz', '.xz', '.bz2'] or '.tar' in str(tmp_path):
                with tarfile.open(tmp_path) as tar:
                    members = tar.getnames()
                    if members:
                        # Get root folder, handling potential nested structures
                        root_folder = members[0].split('/')[0]
                        theme_name = root_folder
                    
                    # Extract with security filter if available (Python 3.12+)
                    try:
                        tar.extractall(install_dir, filter='data')
                    except TypeError:
                        tar.extractall(install_dir)
                        
            elif tmp_path.suffix == '.zip':
                with zipfile.ZipFile(tmp_path) as zf:
                    members = zf.namelist()
                    if members:
                        root_folder = members[0].split('/')[0]
                        theme_name = root_folder
                    zf.extractall(install_dir)
            else:
                return False, f"Unknown archive format: {tmp_path.suffix}"
            
            # Update icon cache if this was an icon/cursor theme
            if is_icon_theme:
                theme_path = install_dir / theme_name
                if theme_path.exists():
                    try:
                        subprocess.run(
                            ['gtk-update-icon-cache', '-f', '-t', str(theme_path)],
                            capture_output=True, timeout=30
                        )
                        print(f"[OCS] Updated icon cache for {theme_name}")
                    except Exception:
                        pass  # Icon cache update is optional
                
                # Also create symlink in ~/.icons for compatibility
                legacy_dir = home / '.icons'
                legacy_dir.mkdir(parents=True, exist_ok=True)
                legacy_link = legacy_dir / theme_name
                if not legacy_link.exists() and theme_path.exists():
                    try:
                        legacy_link.symlink_to(theme_path)
                        print(f"[OCS] Created symlink: {legacy_link} -> {theme_path}")
                    except Exception:
                        pass  # Symlink is optional
            
            return True, f"Installed: {theme_name} to {install_dir}"
            
        except Exception as e:
            return False, str(e)
        finally:
            tmp_path.unlink(missing_ok=True)
    
    def _on_install_complete(self, success: bool, message: str):
        """Handle installation completion."""
        if success:
            self.status_label.set_markup(f"<small>✓ {message}</small>")
            self.window.show_toast(f"✓ {message} - Check Settings → Appearance to apply")
        else:
            self.status_label.set_markup(f"<small>❌ {message}</small>")
            self.window.show_toast(f"❌ {message}")


# Extension Selection Page
# =============================================================================

class ExtensionSelectionPage(Adw.NavigationPage):
    """Page for selecting and installing extensions."""
    
    def __init__(self, window, distro, extension_manager: Optional[ExtensionManager],
                 extensions: list[Extension], title: str):
        super().__init__(title=title)
        
        self.window = window
        self.distro = distro
        self.extension_manager = extension_manager
        self.extensions = extensions
        self.selected_extensions: set[str] = set()
        
        self.build_ui()
    
    def build_ui(self):
        """Build the UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
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
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        clamp.set_child(content)
        
        # Extension list
        group = Adw.PreferencesGroup()
        content.append(group)
        
        family = self.distro.family.value
        
        # Separate installed vs available
        installed_group = Adw.PreferencesGroup()
        installed_group.set_title("Installed")
        has_installed = False
        
        available_group = Adw.PreferencesGroup()
        available_group.set_title("Available")
        has_available = False
        
        for ext in self.extensions:
            packages = ext.packages.get(family, [])
            
            # Check if installed (for GNOME extensions)
            is_installed = False
            if self.extension_manager and ext.extension_uuid:
                is_installed = self.extension_manager.is_extension_installed(ext.extension_uuid)
            
            if is_installed:
                # Use SwitchRow for installed extensions - cleaner UI
                row = Adw.SwitchRow()
                row.set_title(ext.name)
                row.set_subtitle(ext.description)
                
                # Set current state
                is_enabled = self.extension_manager.is_extension_enabled(ext.extension_uuid)
                row.set_active(is_enabled)
                
                # Connect toggle
                row.connect("notify::active", self.on_extension_toggled, ext)
                
                installed_group.add(row)
                has_installed = True
            else:
                row = Adw.ActionRow()
                row.set_title(ext.name)
                row.set_subtitle(ext.description)
                
                # Checkbox for installation
                checkbox = Gtk.CheckButton()
                checkbox.set_valign(Gtk.Align.CENTER)
                
                if packages:
                    checkbox.connect("toggled", self.on_extension_selected, ext.id)
                    row.add_prefix(checkbox)
                    row.set_activatable_widget(checkbox)
                else:
                    # Unavailable - show disabled checkbox and info
                    checkbox.set_sensitive(False)
                    row.add_prefix(checkbox)
                    
                    unavail = Gtk.Label(label="Not in repos")
                    unavail.add_css_class("dim-label")
                    unavail.set_valign(Gtk.Align.CENTER)
                    row.add_suffix(unavail)
                    
                    # Add tooltip with more info
                    if ext.extension_uuid:
                        row.set_tooltip_text(
                            f"Not in {self.distro.name} repos.\n"
                            f"Install via Extension Manager or extensions.gnome.org"
                        )
                    elif ext.kde_store_id:
                        row.set_tooltip_text(
                            f"Not in {self.distro.name} repos.\n"
                            f"Install via KDE Store or Discover"
                        )
                    else:
                        row.set_tooltip_text(f"Not available for {self.distro.name}")
                
                available_group.add(row)
                has_available = True
        
        # Add groups in order: installed first, then available
        if has_installed:
            content.append(installed_group)
        if has_available:
            content.append(available_group)
        
        # Install button
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(20)
        content.append(button_box)
        
        self.install_btn = Gtk.Button(label="Install Selected")
        self.install_btn.add_css_class("suggested-action")
        self.install_btn.connect("clicked", self.on_install_clicked)
        self.install_btn.set_sensitive(False)
        button_box.append(self.install_btn)
    
    def on_extension_selected(self, checkbox, ext_id: str):
        """Handle extension selection."""
        if checkbox.get_active():
            self.selected_extensions.add(ext_id)
        else:
            self.selected_extensions.discard(ext_id)
        
        self.install_btn.set_sensitive(len(self.selected_extensions) > 0)
        if self.selected_extensions:
            self.install_btn.set_label(f"Install Selected ({len(self.selected_extensions)})")
        else:
            self.install_btn.set_label("Install Selected")
    
    def on_extension_toggled(self, switch, pspec, ext: Extension):
        """Handle extension enable/disable toggle."""
        if not self.extension_manager or not ext.extension_uuid:
            return
        
        if switch.get_active():
            success = self.extension_manager.enable_extension(ext.extension_uuid)
            if success:
                self.window.show_toast(f"Enabled {ext.name}")
            else:
                switch.set_active(False)
                self.window.show_toast(f"Failed to enable {ext.name}")
        else:
            success = self.extension_manager.disable_extension(ext.extension_uuid)
            if success:
                self.window.show_toast(f"Disabled {ext.name}")
            else:
                switch.set_active(True)
                self.window.show_toast(f"Failed to disable {ext.name}")
    
    def on_install_clicked(self, button):
        """Install selected extensions."""
        family = self.distro.family.value
        all_packages = []
        
        for ext_id in self.selected_extensions:
            ext = next((e for e in self.extensions if e.id == ext_id), None)
            if ext:
                packages = ext.packages.get(family, [])
                all_packages.extend(packages)
        
        if not all_packages:
            self.window.show_toast("No packages to install")
            return
        
        all_packages = list(set(all_packages))
        
        plan = {
            "tasks": [{
                "type": "install",
                "name": f"Install extensions",
                "packages": all_packages
            }]
        }
        
        dialog = PlanExecutionDialog(self.window, plan, "Installing Extensions", self.distro)
        dialog.present()


# =============================================================================
# Tool Selection Page
# =============================================================================

class ToolSelectionPage(Adw.NavigationPage):
    """Page for selecting and installing tools."""
    
    def __init__(self, window, distro, tools: list[Tool], title: str):
        super().__init__(title=title)
        
        self.window = window
        self.distro = distro
        self.tools = tools
        self.selected_tools: set[str] = set()
        
        self.build_ui()
    
    def build_ui(self):
        """Build the UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
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
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        clamp.set_child(content)
        
        # Tool list
        group = Adw.PreferencesGroup()
        content.append(group)
        
        family = self.distro.family.value
        
        for tool in self.tools:
            packages = tool.packages.get(family, [])
            has_flatpak = bool(tool.flatpak_id)
            
            row = Adw.ActionRow()
            row.set_title(tool.name)
            row.set_subtitle(tool.description)
            
            # Checkbox
            checkbox = Gtk.CheckButton()
            checkbox.set_valign(Gtk.Align.CENTER)
            
            if packages or has_flatpak:
                checkbox.connect("toggled", self.on_tool_toggled, tool.id)
                row.add_prefix(checkbox)
                row.set_activatable_widget(checkbox)
                
                # Source indicator
                if packages:
                    source = Gtk.Label()
                    source.set_markup(f"<small>{self._get_source_name()}</small>")
                    source.add_css_class("dim-label")
                    source.set_valign(Gtk.Align.CENTER)
                    row.add_suffix(source)
                elif has_flatpak:
                    source = Gtk.Label()
                    source.set_markup("<small>Flathub</small>")
                    source.add_css_class("accent")
                    source.set_valign(Gtk.Align.CENTER)
                    row.add_suffix(source)
            else:
                row.set_sensitive(False)
                unavail = Gtk.Label(label="Not available")
                unavail.add_css_class("dim-label")
                unavail.set_valign(Gtk.Align.CENTER)
                row.add_suffix(unavail)
            
            group.add(row)
        
        # Install button
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(20)
        content.append(button_box)
        
        self.install_btn = Gtk.Button(label="Install Selected")
        self.install_btn.add_css_class("suggested-action")
        self.install_btn.connect("clicked", self.on_install_clicked)
        self.install_btn.set_sensitive(False)
        button_box.append(self.install_btn)
    
    def _get_source_name(self) -> str:
        """Get package manager name."""
        family = self.distro.family.value
        names = {'arch': 'pacman', 'fedora': 'dnf', 'rhel': 'dnf', 
                 'debian': 'apt', 'opensuse': 'zypper'}
        return names.get(family, 'native')
    
    def on_tool_toggled(self, checkbox, tool_id: str):
        """Handle tool selection."""
        if checkbox.get_active():
            self.selected_tools.add(tool_id)
        else:
            self.selected_tools.discard(tool_id)
        
        self.install_btn.set_sensitive(len(self.selected_tools) > 0)
        if self.selected_tools:
            self.install_btn.set_label(f"Install Selected ({len(self.selected_tools)})")
        else:
            self.install_btn.set_label("Install Selected")
    
    def on_install_clicked(self, button):
        """Install selected tools."""
        family = self.distro.family.value
        native_packages = []
        flatpak_apps = []
        
        for tool_id in self.selected_tools:
            tool = next((t for t in self.tools if t.id == tool_id), None)
            if tool:
                packages = tool.packages.get(family, [])
                if packages:
                    native_packages.extend(packages)
                elif tool.flatpak_id:
                    flatpak_apps.append(tool.flatpak_id)
        
        # Install native packages
        if native_packages:
            native_packages = list(set(native_packages))
            plan = {
                "tasks": [{
                    "type": "install",
                    "name": "Install tools",
                    "packages": native_packages
                }]
            }
            dialog = PlanExecutionDialog(self.window, plan, "Installing Tools", self.distro)
            dialog.present()
        
        # Install Flatpaks
        if flatpak_apps:
            self._install_flatpaks(flatpak_apps)
    
    def _install_flatpaks(self, app_ids: list[str]):
        """Install Flatpak apps."""
        import shutil
        
        if not shutil.which('flatpak'):
            self.window.show_toast("Flatpak not installed")
            return
        
        def do_install():
            for app_id in app_ids:
                try:
                    subprocess.run(
                        ['flatpak', 'install', '-y', 'flathub', app_id],
                        capture_output=True, timeout=300
                    )
                except Exception:
                    pass
            GLib.idle_add(self.window.show_toast, f"Installed {len(app_ids)} Flatpak(s)")
        
        self.window.show_toast(f"Installing {len(app_ids)} Flatpak(s)...")
        thread = threading.Thread(target=do_install, daemon=True)
        thread.start()


# =============================================================================
# Theme Preset Page
# =============================================================================

class ThemePresetPage(Adw.NavigationPage):
    """Page for applying complete theme presets."""
    
    def __init__(self, window, distro, theme_manager: ThemeManager):
        super().__init__(title="Theme Presets")
        
        self.window = window
        self.distro = distro
        self.theme_manager = theme_manager
        
        self.build_ui()
    
    def build_ui(self):
        """Build the UI."""
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
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
        
        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        clamp.set_child(content)
        
        # Info banner
        info_label = Gtk.Label()
        info_label.set_markup(
            "<small>Theme presets apply a complete look including GTK theme, icons, and cursor. "
            "Make sure the required themes are installed first.</small>"
        )
        info_label.set_wrap(True)
        info_label.add_css_class("dim-label")
        info_label.set_halign(Gtk.Align.START)
        content.append(info_label)
        
        # Preset list
        group = Adw.PreferencesGroup()
        group.set_title("Available Presets")
        content.append(group)
        
        for preset in THEME_PRESETS:
            row = Adw.ActionRow()
            row.set_title(preset.name)
            row.set_subtitle(preset.description)
            row.set_activatable(True)
            
            # Show what's included
            details = []
            if preset.gtk_theme:
                details.append(f"GTK: {preset.gtk_theme}")
            if preset.icon_theme:
                details.append(f"Icons: {preset.icon_theme}")
            
            if details:
                detail_label = Gtk.Label()
                detail_label.set_markup(f"<small>{' • '.join(details)}</small>")
                detail_label.add_css_class("dim-label")
                detail_label.set_valign(Gtk.Align.CENTER)
                row.add_suffix(detail_label)
            
            # Apply button
            apply_btn = Gtk.Button(label="Apply")
            apply_btn.add_css_class("suggested-action")
            apply_btn.set_valign(Gtk.Align.CENTER)
            apply_btn.connect("clicked", self.on_apply_preset, preset)
            row.add_suffix(apply_btn)
            
            group.add(row)
        
        # Install themes section
        install_group = Adw.PreferencesGroup()
        install_group.set_title("Install Theme Packages")
        install_group.set_description("Install the themes used by these presets")
        content.append(install_group)
        
        install_row = Adw.ActionRow()
        install_row.set_title("Install Popular Theme Packages")
        install_row.set_subtitle("Arc, Papirus, Bibata, and more")
        install_row.set_activatable(True)
        install_row.add_suffix(Gtk.Image.new_from_icon_name("tux-go-next-symbolic"))
        install_row.connect("activated", self.on_install_theme_packages)
        install_group.add(install_row)
    
    def on_apply_preset(self, button, preset: ThemePreset):
        """Apply a theme preset."""
        success_count = 0
        fail_count = 0
        
        # Apply GTK theme
        if preset.gtk_theme:
            if self.theme_manager.apply_gtk_theme(preset.gtk_theme):
                success_count += 1
            else:
                fail_count += 1
        
        # Apply icon theme
        if preset.icon_theme:
            if self.theme_manager.apply_icon_theme(preset.icon_theme):
                success_count += 1
            else:
                fail_count += 1
        
        # Apply cursor theme
        if preset.cursor_theme:
            if self.theme_manager.apply_cursor_theme(preset.cursor_theme):
                success_count += 1
            else:
                fail_count += 1
        
        if fail_count == 0:
            self.window.show_toast(f"Applied {preset.name} preset")
        elif success_count > 0:
            self.window.show_toast(f"Partially applied {preset.name} (some themes not installed)")
        else:
            self.window.show_toast(f"Failed to apply {preset.name} (themes not installed?)")
    
    def on_install_theme_packages(self, row):
        """Install popular theme packages needed for presets."""
        family = self.distro.family.value
        
        # Collect common theme packages
        packages = []
        
        # From GTK themes
        for theme in GTK_THEMES:
            pkgs = theme.packages.get(family, [])
            packages.extend(pkgs)
        
        # From icon themes
        for theme in ICON_THEMES:
            pkgs = theme.packages.get(family, [])
            packages.extend(pkgs)
        
        # From cursor themes
        for theme in CURSOR_THEMES:
            pkgs = theme.packages.get(family, [])
            packages.extend(pkgs)
        
        # Remove duplicates and empty
        packages = list(set(p for p in packages if p))
        
        if not packages:
            self.window.show_toast("No theme packages available for this distribution")
            return
        
        plan = {
            "tasks": [{
                "type": "install",
                "name": "Install theme packages",
                "packages": packages
            }]
        }
        
        dialog = PlanExecutionDialog(self.window, plan, "Installing Theme Packages", self.distro)
        dialog.present()
