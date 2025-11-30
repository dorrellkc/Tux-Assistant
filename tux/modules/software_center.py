"""
Tux Assistant - Software Center Module

Browse and install applications by category.

Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
"""

import gi
gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

import sys
import os
import json
import tempfile
import subprocess
import threading
from gi.repository import Gtk, Adw, GLib, Gio
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from ..core import get_distro, get_package_manager, DistroFamily


# =============================================================================
# Application Data Structures
# =============================================================================

@dataclass
class App:
    """An application that can be installed."""
    id: str
    name: str
    description: str
    icon: str = "application-x-executable-symbolic"
    # Package names per distro family
    packages: dict = field(default_factory=dict)
    # Flatpak ID (alternative install method)
    flatpak: Optional[str] = None
    # Whether this needs special handling
    special: bool = False
    # Extra commands to run before/after install
    pre_commands: dict = field(default_factory=dict)
    post_commands: dict = field(default_factory=dict)
    
    def get_packages(self, family: DistroFamily) -> list[str]:
        """Get package names for a distro family."""
        family_key = family.value
        return self.packages.get(family_key, self.packages.get('default', []))
    
    def has_packages(self, family: DistroFamily) -> bool:
        """Check if app has packages for this distro."""
        return len(self.get_packages(family)) > 0 or self.flatpak is not None


@dataclass  
class Category:
    """A category of applications."""
    id: str
    name: str
    description: str
    icon: str
    apps: list[App] = field(default_factory=list)


# =============================================================================
# Application Catalog
# =============================================================================

def build_catalog() -> list[Category]:
    """Build the full application catalog."""
    
    return [
        # -----------------------------------------------------------------
        # Web Browsers
        # -----------------------------------------------------------------
        Category(
            id="browsers",
            name="Web Browsers",
            description="Browse the internet",
            icon="web-browser-symbolic",
            apps=[
                App(
                    id="firefox",
                    name="Firefox",
                    description="Fast, private, open-source browser from Mozilla",
                    icon="firefox-symbolic",
                    packages={
                        "arch": ["firefox"],
                        "debian": ["firefox", "firefox-esr"],
                        "fedora": ["firefox"],
                        "opensuse": ["firefox"],
                    }
                ),
                App(
                    id="chromium",
                    name="Chromium",
                    description="Open-source browser that Chrome is built on",
                    icon="chromium-symbolic",
                    packages={
                        "arch": ["chromium"],
                        "debian": ["chromium"],
                        "fedora": ["chromium"],
                        "opensuse": ["chromium"],
                    }
                ),
                App(
                    id="google-chrome",
                    name="Google Chrome",
                    description="Google's popular web browser",
                    icon="google-chrome-symbolic",
                    flatpak="com.google.Chrome",
                    packages={
                        "arch": ["google-chrome"],  # AUR
                        "fedora": ["google-chrome-stable"],
                    },
                    special=True
                ),
                App(
                    id="brave",
                    name="Brave",
                    description="Privacy-focused browser with built-in ad blocker",
                    icon="brave-symbolic",
                    flatpak="com.brave.Browser",
                    packages={
                        "arch": ["brave-bin"],  # AUR
                    }
                ),
                App(
                    id="vivaldi",
                    name="Vivaldi",
                    description="Feature-rich, customizable browser",
                    icon="vivaldi-symbolic",
                    flatpak="com.vivaldi.Vivaldi",
                    packages={
                        "arch": ["vivaldi"],
                    }
                ),
                App(
                    id="librewolf",
                    name="LibreWolf",
                    description="Privacy-hardened Firefox fork",
                    icon="librewolf-symbolic",
                    flatpak="io.gitlab.librewolf-community",
                    packages={
                        "arch": ["librewolf"],
                    }
                ),
                App(
                    id="epiphany",
                    name="GNOME Web",
                    description="Simple, clean browser for GNOME",
                    icon="epiphany-symbolic",
                    packages={
                        "arch": ["epiphany"],
                        "debian": ["epiphany-browser"],
                        "fedora": ["epiphany"],
                        "opensuse": ["epiphany"],
                    }
                ),
            ]
        ),
        
        # -----------------------------------------------------------------
        # Media Players
        # -----------------------------------------------------------------
        Category(
            id="media",
            name="Media Players",
            description="Play videos, music, and streaming content",
            icon="multimedia-player-symbolic",
            apps=[
                App(
                    id="vlc",
                    name="VLC Media Player",
                    description="Plays almost any media format",
                    icon="vlc-symbolic",
                    packages={
                        "arch": ["vlc"],
                        "debian": ["vlc"],
                        "fedora": ["vlc"],
                        "opensuse": ["vlc"],
                    }
                ),
                App(
                    id="mpv",
                    name="MPV",
                    description="Lightweight, powerful media player",
                    icon="mpv-symbolic",
                    packages={
                        "arch": ["mpv"],
                        "debian": ["mpv"],
                        "fedora": ["mpv"],
                        "opensuse": ["mpv"],
                    }
                ),
                App(
                    id="celluloid",
                    name="Celluloid",
                    description="GTK frontend for MPV",
                    icon="celluloid-symbolic",
                    packages={
                        "arch": ["celluloid"],
                        "debian": ["celluloid"],
                        "fedora": ["celluloid"],
                        "opensuse": ["celluloid"],
                    }
                ),
                App(
                    id="rhythmbox",
                    name="Rhythmbox",
                    description="Music player and library organizer",
                    icon="rhythmbox-symbolic",
                    packages={
                        "arch": ["rhythmbox"],
                        "debian": ["rhythmbox"],
                        "fedora": ["rhythmbox"],
                        "opensuse": ["rhythmbox"],
                    }
                ),
                App(
                    id="elisa",
                    name="Elisa",
                    description="KDE music player",
                    icon="elisa-symbolic",
                    packages={
                        "arch": ["elisa"],
                        "debian": ["elisa"],
                        "fedora": ["elisa"],
                        "opensuse": ["elisa"],
                    }
                ),
                App(
                    id="audacious",
                    name="Audacious",
                    description="Lightweight audio player",
                    icon="audacious-symbolic",
                    packages={
                        "arch": ["audacious"],
                        "debian": ["audacious"],
                        "fedora": ["audacious"],
                        "opensuse": ["audacious"],
                    }
                ),
                App(
                    id="spotify",
                    name="Spotify",
                    description="Music streaming service",
                    icon="spotify-symbolic",
                    flatpak="com.spotify.Client",
                    packages={
                        "arch": ["spotify"],  # AUR
                    }
                ),
                App(
                    id="shortwave",
                    name="Shortwave",
                    description="Internet radio player",
                    icon="shortwave-symbolic",
                    flatpak="de.haeckerfelix.Shortwave",
                    packages={
                        "arch": ["shortwave"],
                        "fedora": ["shortwave"],
                    }
                ),
            ]
        ),
        
        # -----------------------------------------------------------------
        # Office and Productivity
        # -----------------------------------------------------------------
        Category(
            id="office",
            name="Office and Productivity",
            description="Documents, spreadsheets, and productivity tools",
            icon="x-office-document-symbolic",
            apps=[
                App(
                    id="libreoffice",
                    name="LibreOffice",
                    description="Full office suite - documents, spreadsheets, presentations",
                    icon="libreoffice-startcenter-symbolic",
                    packages={
                        "arch": ["libreoffice-fresh"],
                        "debian": ["libreoffice"],
                        "fedora": ["libreoffice"],
                        "opensuse": ["libreoffice"],
                    }
                ),
                App(
                    id="onlyoffice",
                    name="OnlyOffice",
                    description="Microsoft-compatible office suite",
                    icon="onlyoffice-symbolic",
                    flatpak="org.onlyoffice.desktopeditors",
                    packages={
                        "arch": ["onlyoffice-bin"],  # AUR
                    }
                ),
                App(
                    id="thunderbird",
                    name="Thunderbird",
                    description="Email client from Mozilla",
                    icon="thunderbird-symbolic",
                    packages={
                        "arch": ["thunderbird"],
                        "debian": ["thunderbird"],
                        "fedora": ["thunderbird"],
                        "opensuse": ["thunderbird"],
                    }
                ),
                App(
                    id="evince",
                    name="Evince",
                    description="GNOME document viewer (PDF, etc.)",
                    icon="evince-symbolic",
                    packages={
                        "arch": ["evince"],
                        "debian": ["evince"],
                        "fedora": ["evince"],
                        "opensuse": ["evince"],
                    }
                ),
                App(
                    id="okular",
                    name="Okular",
                    description="KDE document viewer",
                    icon="okular-symbolic",
                    packages={
                        "arch": ["okular"],
                        "debian": ["okular"],
                        "fedora": ["okular"],
                        "opensuse": ["okular"],
                    }
                ),
                App(
                    id="obsidian",
                    name="Obsidian",
                    description="Markdown knowledge base",
                    icon="obsidian-symbolic",
                    flatpak="md.obsidian.Obsidian",
                    packages={
                        "arch": ["obsidian"],
                    }
                ),
                App(
                    id="joplin",
                    name="Joplin",
                    description="Note-taking and to-do app",
                    icon="joplin-symbolic",
                    flatpak="net.cozic.joplin_desktop",
                ),
                App(
                    id="foliate",
                    name="Foliate",
                    description="E-book reader",
                    icon="foliate-symbolic",
                    packages={
                        "arch": ["foliate"],
                        "debian": ["foliate"],
                        "fedora": ["foliate"],
                    },
                    flatpak="com.github.johnfactotum.Foliate",
                ),
            ]
        ),
        
        # -----------------------------------------------------------------
        # Graphics and Design
        # -----------------------------------------------------------------
        Category(
            id="graphics",
            name="Graphics and Design",
            description="Image editing, drawing, and design tools",
            icon="applications-graphics-symbolic",
            apps=[
                App(
                    id="gimp",
                    name="GIMP",
                    description="Powerful image editor",
                    icon="gimp-symbolic",
                    packages={
                        "arch": ["gimp"],
                        "debian": ["gimp"],
                        "fedora": ["gimp"],
                        "opensuse": ["gimp"],
                    }
                ),
                App(
                    id="inkscape",
                    name="Inkscape",
                    description="Vector graphics editor",
                    icon="inkscape-symbolic",
                    packages={
                        "arch": ["inkscape"],
                        "debian": ["inkscape"],
                        "fedora": ["inkscape"],
                        "opensuse": ["inkscape"],
                    }
                ),
                App(
                    id="krita",
                    name="Krita",
                    description="Digital painting application",
                    icon="krita-symbolic",
                    packages={
                        "arch": ["krita"],
                        "debian": ["krita"],
                        "fedora": ["krita"],
                        "opensuse": ["krita"],
                    }
                ),
                App(
                    id="blender",
                    name="Blender",
                    description="3D creation suite",
                    icon="blender-symbolic",
                    packages={
                        "arch": ["blender"],
                        "debian": ["blender"],
                        "fedora": ["blender"],
                        "opensuse": ["blender"],
                    }
                ),
                App(
                    id="darktable",
                    name="Darktable",
                    description="Photography workflow and RAW editor",
                    icon="darktable-symbolic",
                    packages={
                        "arch": ["darktable"],
                        "debian": ["darktable"],
                        "fedora": ["darktable"],
                        "opensuse": ["darktable"],
                    }
                ),
                App(
                    id="rawtherapee",
                    name="RawTherapee",
                    description="RAW photo processing",
                    icon="rawtherapee-symbolic",
                    packages={
                        "arch": ["rawtherapee"],
                        "debian": ["rawtherapee"],
                        "fedora": ["rawtherapee"],
                        "opensuse": ["rawtherapee"],
                    }
                ),
                App(
                    id="shotwell",
                    name="Shotwell",
                    description="Photo manager",
                    icon="shotwell-symbolic",
                    packages={
                        "arch": ["shotwell"],
                        "debian": ["shotwell"],
                        "fedora": ["shotwell"],
                        "opensuse": ["shotwell"],
                    }
                ),
                App(
                    id="drawing",
                    name="Drawing",
                    description="Simple image editor for GNOME",
                    icon="drawing-symbolic",
                    packages={
                        "arch": ["drawing"],
                        "debian": ["drawing"],
                        "fedora": ["drawing"],
                    },
                    flatpak="com.github.maoschanz.drawing",
                ),
            ]
        ),
        
        # -----------------------------------------------------------------
        # Communication
        # -----------------------------------------------------------------
        Category(
            id="communication",
            name="Communication",
            description="Chat, video calls, and messaging",
            icon="user-available-symbolic",
            apps=[
                App(
                    id="discord",
                    name="Discord",
                    description="Voice, video, and text chat",
                    icon="discord-symbolic",
                    flatpak="com.discordapp.Discord",
                    packages={
                        "arch": ["discord"],
                    }
                ),
                App(
                    id="slack",
                    name="Slack",
                    description="Team communication platform",
                    icon="slack-symbolic",
                    flatpak="com.slack.Slack",
                ),
                App(
                    id="zoom",
                    name="Zoom",
                    description="Video conferencing",
                    icon="zoom-symbolic",
                    flatpak="us.zoom.Zoom",
                ),
                App(
                    id="teams",
                    name="Microsoft Teams",
                    description="Microsoft's collaboration platform",
                    icon="teams-symbolic",
                    flatpak="com.github.AfonsoRibeiro.Thesis",  # Teams for Linux (unofficial)
                ),
                App(
                    id="signal",
                    name="Signal",
                    description="Secure private messaging",
                    icon="signal-symbolic",
                    flatpak="org.signal.Signal",
                ),
                App(
                    id="telegram",
                    name="Telegram",
                    description="Cloud-based messaging",
                    icon="telegram-symbolic",
                    flatpak="org.telegram.desktop",
                    packages={
                        "arch": ["telegram-desktop"],
                        "fedora": ["telegram-desktop"],
                    }
                ),
                App(
                    id="element",
                    name="Element",
                    description="Matrix chat client",
                    icon="element-symbolic",
                    flatpak="im.riot.Riot",
                    packages={
                        "arch": ["element-desktop"],
                    }
                ),
                App(
                    id="hexchat",
                    name="HexChat",
                    description="IRC client",
                    icon="hexchat-symbolic",
                    packages={
                        "arch": ["hexchat"],
                        "debian": ["hexchat"],
                        "fedora": ["hexchat"],
                        "opensuse": ["hexchat"],
                    }
                ),
            ]
        ),
        
        # -----------------------------------------------------------------
        # Development Tools
        # -----------------------------------------------------------------
        Category(
            id="development",
            name="Development Tools",
            description="Code editors, IDEs, and programming tools",
            icon="applications-development-symbolic",
            apps=[
                App(
                    id="vscode",
                    name="Visual Studio Code",
                    description="Popular code editor from Microsoft",
                    icon="vscode-symbolic",
                    flatpak="com.visualstudio.code",
                    packages={
                        "arch": ["code"],  # Open source version
                    }
                ),
                App(
                    id="vscodium",
                    name="VSCodium",
                    description="VS Code without Microsoft telemetry",
                    icon="vscodium-symbolic",
                    flatpak="com.vscodium.codium",
                    packages={
                        "arch": ["vscodium"],
                    }
                ),
                App(
                    id="sublime-text",
                    name="Sublime Text",
                    description="Fast, sophisticated text editor",
                    icon="sublime-text-symbolic",
                    flatpak="com.sublimetext.three",
                    packages={
                        "arch": ["sublime-text-4"],
                    }
                ),
                App(
                    id="geany",
                    name="Geany",
                    description="Lightweight IDE",
                    icon="geany-symbolic",
                    packages={
                        "arch": ["geany"],
                        "debian": ["geany"],
                        "fedora": ["geany"],
                        "opensuse": ["geany"],
                    }
                ),
                App(
                    id="gnome-builder",
                    name="GNOME Builder",
                    description="IDE for GNOME development",
                    icon="builder-symbolic",
                    packages={
                        "arch": ["gnome-builder"],
                        "debian": ["gnome-builder"],
                        "fedora": ["gnome-builder"],
                    }
                ),
                App(
                    id="kate",
                    name="Kate",
                    description="KDE advanced text editor",
                    icon="kate-symbolic",
                    packages={
                        "arch": ["kate"],
                        "debian": ["kate"],
                        "fedora": ["kate"],
                        "opensuse": ["kate"],
                    }
                ),
                App(
                    id="meld",
                    name="Meld",
                    description="Visual diff and merge tool",
                    icon="meld-symbolic",
                    packages={
                        "arch": ["meld"],
                        "debian": ["meld"],
                        "fedora": ["meld"],
                        "opensuse": ["meld"],
                    }
                ),
                App(
                    id="dbeaver",
                    name="DBeaver",
                    description="Universal database manager",
                    icon="dbeaver-symbolic",
                    flatpak="io.dbeaver.DBeaverCommunity",
                    packages={
                        "arch": ["dbeaver"],
                    }
                ),
            ]
        ),
        
        # -----------------------------------------------------------------
        # Gaming
        # -----------------------------------------------------------------
        Category(
            id="gaming",
            name="Gaming",
            description="Games, game launchers, and gaming tools",
            icon="applications-games-symbolic",
            apps=[
                App(
                    id="steam",
                    name="Steam",
                    description="Valve's game platform",
                    icon="steam-symbolic",
                    packages={
                        "arch": ["steam"],
                        "debian": ["steam"],
                        "fedora": ["steam"],
                        "opensuse": ["steam"],
                    }
                ),
                App(
                    id="lutris",
                    name="Lutris",
                    description="Open gaming platform",
                    icon="lutris-symbolic",
                    packages={
                        "arch": ["lutris"],
                        "debian": ["lutris"],
                        "fedora": ["lutris"],
                        "opensuse": ["lutris"],
                    }
                ),
                App(
                    id="heroic",
                    name="Heroic Games Launcher",
                    description="Epic Games and GOG launcher",
                    icon="heroic-symbolic",
                    flatpak="com.heroicgameslauncher.hgl",
                    packages={
                        "arch": ["heroic-games-launcher"],
                    }
                ),
                App(
                    id="bottles",
                    name="Bottles",
                    description="Run Windows software and games",
                    icon="bottles-symbolic",
                    flatpak="com.usebottles.bottles",
                    packages={
                        "arch": ["bottles"],
                        "fedora": ["bottles"],
                    }
                ),
                App(
                    id="mangohud",
                    name="MangoHud",
                    description="Performance overlay for games",
                    icon="mangohud-symbolic",
                    packages={
                        "arch": ["mangohud"],
                        "debian": ["mangohud"],
                        "fedora": ["mangohud"],
                    }
                ),
                App(
                    id="gamemode",
                    name="GameMode",
                    description="Optimize Linux for gaming",
                    icon="gamemode-symbolic",
                    packages={
                        "arch": ["gamemode", "lib32-gamemode"],
                        "debian": ["gamemode"],
                        "fedora": ["gamemode"],
                    }
                ),
                App(
                    id="protonup-qt",
                    name="ProtonUp-Qt",
                    description="Manage Proton/Wine versions",
                    icon="protonup-qt-symbolic",
                    flatpak="net.davidotek.pupgui2",
                    packages={
                        "arch": ["protonup-qt"],
                    }
                ),
            ]
        ),
        
        # -----------------------------------------------------------------
        # System Tools
        # -----------------------------------------------------------------
        Category(
            id="system",
            name="System Tools",
            description="System utilities and management tools",
            icon="preferences-system-symbolic",
            apps=[
                App(
                    id="gnome-tweaks",
                    name="GNOME Tweaks",
                    description="Advanced GNOME settings",
                    icon="gnome-tweaks-symbolic",
                    packages={
                        "arch": ["gnome-tweaks"],
                        "debian": ["gnome-tweaks"],
                        "fedora": ["gnome-tweaks"],
                        "opensuse": ["gnome-tweaks"],
                    }
                ),
                App(
                    id="dconf-editor",
                    name="dconf Editor",
                    description="Low-level GNOME settings editor",
                    icon="dconf-editor-symbolic",
                    packages={
                        "arch": ["dconf-editor"],
                        "debian": ["dconf-editor"],
                        "fedora": ["dconf-editor"],
                        "opensuse": ["dconf-editor"],
                    }
                ),
                App(
                    id="gparted",
                    name="GParted",
                    description="Partition editor",
                    icon="gparted-symbolic",
                    packages={
                        "arch": ["gparted"],
                        "debian": ["gparted"],
                        "fedora": ["gparted"],
                        "opensuse": ["gparted"],
                    }
                ),
                App(
                    id="timeshift",
                    name="Timeshift",
                    description="System restore utility",
                    icon="timeshift-symbolic",
                    packages={
                        "arch": ["timeshift"],
                        "debian": ["timeshift"],
                        "fedora": ["timeshift"],
                        "opensuse": ["timeshift"],
                    }
                ),
                App(
                    id="bleachbit",
                    name="BleachBit",
                    description="System cleaner",
                    icon="bleachbit-symbolic",
                    packages={
                        "arch": ["bleachbit"],
                        "debian": ["bleachbit"],
                        "fedora": ["bleachbit"],
                        "opensuse": ["bleachbit"],
                    }
                ),
                App(
                    id="stacer",
                    name="Stacer",
                    description="System optimizer and monitor",
                    icon="stacer-symbolic",
                    packages={
                        "arch": ["stacer"],
                    },
                    flatpak="com.oguzhaninan.Stacer",
                ),
                App(
                    id="flatseal",
                    name="Flatseal",
                    description="Manage Flatpak permissions",
                    icon="flatseal-symbolic",
                    flatpak="com.github.tchx84.Flatseal",
                    packages={
                        "arch": ["flatseal"],
                    }
                ),
                App(
                    id="mission-center",
                    name="Mission Center",
                    description="System monitor like Windows Task Manager",
                    icon="mission-center-symbolic",
                    flatpak="io.missioncenter.MissionCenter",
                ),
            ]
        ),
        
        # -----------------------------------------------------------------
        # Video Production
        # -----------------------------------------------------------------
        Category(
            id="video",
            name="Video Production",
            description="Video editing and screen recording",
            icon="camera-video-symbolic",
            apps=[
                App(
                    id="kdenlive",
                    name="Kdenlive",
                    description="Professional video editor",
                    icon="kdenlive-symbolic",
                    packages={
                        "arch": ["kdenlive"],
                        "debian": ["kdenlive"],
                        "fedora": ["kdenlive"],
                        "opensuse": ["kdenlive"],
                    }
                ),
                App(
                    id="shotcut",
                    name="Shotcut",
                    description="Cross-platform video editor",
                    icon="shotcut-symbolic",
                    flatpak="org.shotcut.Shotcut",
                    packages={
                        "arch": ["shotcut"],
                        "fedora": ["shotcut"],
                    }
                ),
                App(
                    id="openshot",
                    name="OpenShot",
                    description="Easy to use video editor",
                    icon="openshot-symbolic",
                    packages={
                        "arch": ["openshot"],
                        "debian": ["openshot-qt"],
                        "fedora": ["openshot"],
                    }
                ),
                App(
                    id="obs-studio",
                    name="OBS Studio",
                    description="Streaming and screen recording",
                    icon="obs-symbolic",
                    packages={
                        "arch": ["obs-studio"],
                        "debian": ["obs-studio"],
                        "fedora": ["obs-studio"],
                        "opensuse": ["obs-studio"],
                    }
                ),
                App(
                    id="handbrake",
                    name="HandBrake",
                    description="Video transcoder",
                    icon="handbrake-symbolic",
                    packages={
                        "arch": ["handbrake"],
                        "debian": ["handbrake"],
                        "fedora": ["handbrake"],
                        "opensuse": ["handbrake"],
                    }
                ),
                App(
                    id="peek",
                    name="Peek",
                    description="Simple GIF screen recorder",
                    icon="peek-symbolic",
                    packages={
                        "arch": ["peek"],
                        "debian": ["peek"],
                        "fedora": ["peek"],
                    },
                    flatpak="com.uploadedlobster.peek",
                ),
            ]
        ),
        
        # -----------------------------------------------------------------
        # Audio Production
        # -----------------------------------------------------------------
        Category(
            id="audio",
            name="Audio Production",
            description="Audio editing and music production",
            icon="audio-x-generic-symbolic",
            apps=[
                App(
                    id="audacity",
                    name="Audacity",
                    description="Audio editor and recorder",
                    icon="audacity-symbolic",
                    packages={
                        "arch": ["audacity"],
                        "debian": ["audacity"],
                        "fedora": ["audacity"],
                        "opensuse": ["audacity"],
                    }
                ),
                App(
                    id="ardour",
                    name="Ardour",
                    description="Digital audio workstation",
                    icon="ardour-symbolic",
                    packages={
                        "arch": ["ardour"],
                        "debian": ["ardour"],
                        "fedora": ["ardour"],
                        "opensuse": ["ardour"],
                    }
                ),
                App(
                    id="lmms",
                    name="LMMS",
                    description="Music production software",
                    icon="lmms-symbolic",
                    packages={
                        "arch": ["lmms"],
                        "debian": ["lmms"],
                        "fedora": ["lmms"],
                        "opensuse": ["lmms"],
                    }
                ),
                App(
                    id="easyeffects",
                    name="Easy Effects",
                    description="Audio effects for PipeWire",
                    icon="easyeffects-symbolic",
                    packages={
                        "arch": ["easyeffects"],
                        "debian": ["easyeffects"],
                        "fedora": ["easyeffects"],
                    },
                    flatpak="com.github.wwmm.easyeffects",
                ),
                App(
                    id="tenacity",
                    name="Tenacity",
                    description="Audacity fork with improvements",
                    icon="tenacity-symbolic",
                    flatpak="org.tenacityaudio.Tenacity",
                    packages={
                        "arch": ["tenacity"],
                    }
                ),
            ]
        ),
        
        # -----------------------------------------------------------------
        # File Management
        # -----------------------------------------------------------------
        Category(
            id="files",
            name="File Management",
            description="File managers and cloud sync",
            icon="folder-symbolic",
            apps=[
                App(
                    id="nautilus",
                    name="Files (Nautilus)",
                    description="GNOME file manager",
                    icon="nautilus-symbolic",
                    packages={
                        "arch": ["nautilus"],
                        "debian": ["nautilus"],
                        "fedora": ["nautilus"],
                        "opensuse": ["nautilus"],
                    }
                ),
                App(
                    id="dolphin",
                    name="Dolphin",
                    description="KDE file manager",
                    icon="dolphin-symbolic",
                    packages={
                        "arch": ["dolphin"],
                        "debian": ["dolphin"],
                        "fedora": ["dolphin"],
                        "opensuse": ["dolphin"],
                    }
                ),
                App(
                    id="thunar",
                    name="Thunar",
                    description="XFCE file manager",
                    icon="thunar-symbolic",
                    packages={
                        "arch": ["thunar"],
                        "debian": ["thunar"],
                        "fedora": ["thunar"],
                        "opensuse": ["thunar"],
                    }
                ),
                App(
                    id="nemo",
                    name="Nemo",
                    description="Cinnamon file manager",
                    icon="nemo-symbolic",
                    packages={
                        "arch": ["nemo"],
                        "debian": ["nemo"],
                        "fedora": ["nemo"],
                    }
                ),
                App(
                    id="doublecmd",
                    name="Double Commander",
                    description="Two-panel file manager",
                    icon="doublecmd-symbolic",
                    packages={
                        "arch": ["doublecmd-qt5"],
                        "debian": ["doublecmd-qt"],
                        "fedora": ["doublecmd-qt"],
                    }
                ),
                App(
                    id="filezilla",
                    name="FileZilla",
                    description="FTP/SFTP client",
                    icon="filezilla-symbolic",
                    packages={
                        "arch": ["filezilla"],
                        "debian": ["filezilla"],
                        "fedora": ["filezilla"],
                        "opensuse": ["filezilla"],
                    }
                ),
                App(
                    id="syncthing",
                    name="Syncthing",
                    description="Continuous file synchronization",
                    icon="syncthing-symbolic",
                    packages={
                        "arch": ["syncthing"],
                        "debian": ["syncthing"],
                        "fedora": ["syncthing"],
                        "opensuse": ["syncthing"],
                    }
                ),
                App(
                    id="rclone",
                    name="Rclone",
                    description="Cloud storage sync tool",
                    icon="rclone-symbolic",
                    packages={
                        "arch": ["rclone"],
                        "debian": ["rclone"],
                        "fedora": ["rclone"],
                        "opensuse": ["rclone"],
                    }
                ),
            ]
        ),
        
        # -----------------------------------------------------------------
        # Security and Privacy
        # -----------------------------------------------------------------
        Category(
            id="security",
            name="Security and Privacy",
            description="Security tools and VPNs",
            icon="security-high-symbolic",
            apps=[
                App(
                    id="keepassxc",
                    name="KeePassXC",
                    description="Password manager",
                    icon="keepassxc-symbolic",
                    packages={
                        "arch": ["keepassxc"],
                        "debian": ["keepassxc"],
                        "fedora": ["keepassxc"],
                        "opensuse": ["keepassxc"],
                    }
                ),
                App(
                    id="bitwarden",
                    name="Bitwarden",
                    description="Cloud-synced password manager",
                    icon="bitwarden-symbolic",
                    flatpak="com.bitwarden.desktop",
                    packages={
                        "arch": ["bitwarden"],
                    }
                ),
                App(
                    id="seahorse",
                    name="Seahorse",
                    description="GNOME keyring manager",
                    icon="seahorse-symbolic",
                    packages={
                        "arch": ["seahorse"],
                        "debian": ["seahorse"],
                        "fedora": ["seahorse"],
                        "opensuse": ["seahorse"],
                    }
                ),
                App(
                    id="veracrypt",
                    name="VeraCrypt",
                    description="Disk encryption",
                    icon="veracrypt-symbolic",
                    packages={
                        "arch": ["veracrypt"],
                        "debian": ["veracrypt"],
                        "fedora": ["veracrypt"],
                    }
                ),
                App(
                    id="clamtk",
                    name="ClamTk",
                    description="Antivirus scanner",
                    icon="clamtk-symbolic",
                    packages={
                        "arch": ["clamtk"],
                        "debian": ["clamtk"],
                        "fedora": ["clamtk"],
                        "opensuse": ["clamtk"],
                    }
                ),
                App(
                    id="gufw",
                    name="GUFW",
                    description="Firewall configuration",
                    icon="gufw-symbolic",
                    packages={
                        "arch": ["gufw"],
                        "debian": ["gufw"],
                        "fedora": ["gufw"],
                        "opensuse": ["gufw"],
                    }
                ),
            ]
        ),
        
        # -----------------------------------------------------------------
        # Special Installation (apps needing extra setup)
        # -----------------------------------------------------------------
        Category(
            id="special",
            name="Special Installation",
            description="Apps requiring additional setup or external repositories",
            icon="emblem-important-symbolic",
            apps=[
                App(
                    id="surfshark",
                    name="Surfshark VPN",
                    description="VPN service with full setup (auto .deb conversion on Fedora/openSUSE)",
                    icon="network-vpn-symbolic",
                    special=True,
                    packages={
                        "arch": ["SPECIAL:surfshark"],
                        "debian": ["SPECIAL:surfshark"],
                        "fedora": ["SPECIAL:surfshark"],
                        "opensuse": ["SPECIAL:surfshark"],
                    },
                ),
                App(
                    id="duckietv",
                    name="DuckieTV",
                    description="TV show tracker (auto .deb conversion on Fedora/openSUSE)",
                    icon="video-television-symbolic",
                    special=True,
                    packages={
                        "arch": ["SPECIAL:duckietv"],
                        "debian": ["SPECIAL:duckietv"],
                        "fedora": ["SPECIAL:duckietv"],
                        "opensuse": ["SPECIAL:duckietv"],
                    },
                ),
                App(
                    id="mullvad",
                    name="Mullvad VPN",
                    description="Privacy-focused VPN",
                    icon="network-vpn-symbolic",
                    flatpak="net.mullvad.MullvadVPN",
                    special=True,
                ),
                App(
                    id="protonvpn",
                    name="ProtonVPN",
                    description="Secure VPN from Proton",
                    icon="network-vpn-symbolic",
                    special=True,
                    packages={
                        "arch": ["protonvpn"],
                        "fedora": ["protonvpn"],
                    },
                    pre_commands={
                        "fedora": [
                            "dnf install -y https://repo.protonvpn.com/fedora-$(rpm -E %fedora)-stable/protonvpn-stable-release/protonvpn-stable-release-1.0.1-2.noarch.rpm || true",
                        ],
                    }
                ),
                App(
                    id="nordvpn",
                    name="NordVPN",
                    description="VPN service (CLI)",
                    icon="network-vpn-symbolic",
                    special=True,
                    packages={
                        "arch": ["nordvpn-bin"],  # AUR
                    },
                ),
                App(
                    id="1password",
                    name="1Password",
                    description="Password manager",
                    icon="dialog-password-symbolic",
                    special=True,
                    flatpak="com.onepassword.OnePassword",
                    packages={
                        "arch": ["1password"],
                    },
                ),
                App(
                    id="dropbox",
                    name="Dropbox",
                    description="Cloud file sync",
                    icon="folder-cloud-symbolic",
                    special=True,
                    flatpak="com.dropbox.Client",
                    packages={
                        "arch": ["dropbox"],
                    },
                ),
                App(
                    id="plex-desktop",
                    name="Plex Desktop",
                    description="Plex media player client",
                    icon="plex-symbolic",
                    special=True,
                    flatpak="tv.plex.PlexDesktop",
                ),
            ]
        ),
    ]


# =============================================================================
# Software Center UI
# =============================================================================

from .registry import register_module, ModuleCategory


@register_module(
    id="software_center",
    name="Software Center",
    description="Browse and install applications by category",
    icon="system-software-install-symbolic",
    category=ModuleCategory.SETUP,
    order=3  # Third - install apps like app store
)
class SoftwareCenterPage(Adw.NavigationPage):
    """The Software Center main page showing categories."""
    
    def __init__(self, window: 'LinuxToolkitWindow'):
        super().__init__(title="Software Center")
        
        self.window = window
        self.distro = get_distro()
        self.catalog = build_catalog()
        
        self.build_ui()
    
    def build_ui(self):
        """Build the Software Center UI."""
        # Main container with header for back button
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header (NavigationView handles back button automatically)
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
        clamp.set_margin_top(20)
        clamp.set_margin_bottom(20)
        clamp.set_margin_start(20)
        clamp.set_margin_end(20)
        scrolled.set_child(clamp)
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        clamp.set_child(content_box)
        
        # Info banner
        info_banner = Adw.Banner()
        info_banner.set_title(f"Browse and install applications for {self.distro.name}")
        info_banner.set_revealed(True)
        content_box.append(info_banner)
        
        # Search box
        search_group = Adw.PreferencesGroup()
        content_box.append(search_group)
        
        search_row = Adw.ActionRow()
        search_row.set_title("Search Packages")
        search_row.set_subtitle(f"Search all {self.distro.name} repositories")
        search_group.add(search_row)
        
        # Search entry
        self.search_entry = Gtk.Entry()
        self.search_entry.set_placeholder_text("Search for packages...")
        self.search_entry.set_hexpand(True)
        self.search_entry.set_valign(Gtk.Align.CENTER)
        self.search_entry.connect("activate", self.on_search_activated)
        search_row.add_suffix(self.search_entry)
        
        # Search button
        search_btn = Gtk.Button()
        search_btn.set_icon_name("system-search-symbolic")
        search_btn.set_valign(Gtk.Align.CENTER)
        search_btn.add_css_class("flat")
        search_btn.connect("clicked", self.on_search_activated)
        search_row.add_suffix(search_btn)
        
        # Category list
        group = Adw.PreferencesGroup()
        group.set_title("Categories")
        content_box.append(group)
        
        for category in self.catalog:
            # Count available apps for this distro
            available_count = sum(
                1 for app in category.apps 
                if app.has_packages(self.distro.family)
            )
            
            row = Adw.ActionRow()
            row.set_title(category.name)
            row.set_subtitle(f"{category.description} ({available_count} apps)")
            row.set_activatable(True)
            row.add_prefix(Gtk.Image.new_from_icon_name(category.icon))
            row.add_suffix(Gtk.Image.new_from_icon_name("go-next-symbolic"))
            row.connect("activated", self.on_category_clicked, category)
            group.add(row)
    
    def on_search_activated(self, widget):
        """Handle search activation."""
        query = self.search_entry.get_text().strip()
        if query:
            page = SearchResultsPage(self.window, query, self.distro)
            self.window.navigation_view.push(page)
    
    def on_category_clicked(self, row, category: Category):
        """Open a category page."""
        page = CategoryPage(self.window, category, self.distro)
        self.window.navigation_view.push(page)


class PackageDetailPage(Adw.NavigationPage):
    """Detail page showing package information before installation."""
    
    def __init__(self, window, pkg: dict, source: str, pkg_key: str,
                 is_queued: bool, on_queue_changed, source_display: str = ""):
        super().__init__(title=pkg.get('name', 'Package Details'))
        
        self.window = window
        self.pkg = pkg
        self.source = source
        self.pkg_key = pkg_key
        self.is_queued = is_queued
        self.on_queue_changed = on_queue_changed
        self.source_display = source_display or source
        
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
        
        # Package info header
        info_group = Adw.PreferencesGroup()
        info_group.set_title("Package Information")
        content_box.append(info_group)
        
        # Name row
        name_row = Adw.ActionRow()
        name_row.set_title("Package Name")
        name_row.set_subtitle(self.pkg.get('name', 'Unknown'))
        name_row.add_prefix(Gtk.Image.new_from_icon_name("package-x-generic-symbolic"))
        info_group.add(name_row)
        
        # Description row
        if self.pkg.get('description'):
            desc_row = Adw.ActionRow()
            desc_row.set_title("Description")
            desc_row.set_subtitle(self.pkg.get('description'))
            desc_row.add_prefix(Gtk.Image.new_from_icon_name("document-properties-symbolic"))
            info_group.add(desc_row)
        
        # Version row
        if self.pkg.get('version'):
            ver_row = Adw.ActionRow()
            ver_row.set_title("Version")
            ver_row.set_subtitle(self.pkg.get('version'))
            ver_row.add_prefix(Gtk.Image.new_from_icon_name("software-update-available-symbolic"))
            info_group.add(ver_row)
        
        # Source row
        source_row = Adw.ActionRow()
        source_row.set_title("Source")
        source_row.set_subtitle(self.source_display)
        if self.source == "flatpak":
            source_row.add_prefix(Gtk.Image.new_from_icon_name("system-software-install-symbolic"))
        else:
            source_row.add_prefix(Gtk.Image.new_from_icon_name("drive-harddisk-symbolic"))
        info_group.add(source_row)
        
        # Flatpak App ID if available
        if self.pkg.get('app_id'):
            appid_row = Adw.ActionRow()
            appid_row.set_title("Flatpak App ID")
            appid_row.set_subtitle(self.pkg.get('app_id'))
            appid_row.add_prefix(Gtk.Image.new_from_icon_name("application-x-executable-symbolic"))
            info_group.add(appid_row)
        
        # Installation status
        is_installed = self.pkg.get('installed', False)
        if is_installed:
            status_row = Adw.ActionRow()
            status_row.set_title("Status")
            status_row.set_subtitle("Already installed on your system")
            status_row.add_prefix(Gtk.Image.new_from_icon_name("emblem-ok-symbolic"))
            info_group.add(status_row)
        
        # Action buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(24)
        content_box.append(button_box)
        
        if not is_installed:
            # Queue toggle button
            self.queue_button = Gtk.Button()
            self._update_queue_button()
            self.queue_button.connect("clicked", self._on_queue_clicked)
            button_box.append(self.queue_button)
        
        # Status label
        self.status_label = Gtk.Label()
        self.status_label.add_css_class("dim-label")
        self._update_status_label()
        content_box.append(self.status_label)
    
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
        is_installed = self.pkg.get('installed', False)
        if is_installed:
            self.status_label.set_text("✓ This package is already installed")
        elif self.is_queued:
            self.status_label.set_text("✓ This package is queued for installation")
        else:
            self.status_label.set_text("Click the button above to add to your install queue")
    
    def _on_queue_clicked(self, button):
        """Handle queue button click."""
        self.is_queued = not self.is_queued
        self._update_queue_button()
        self._update_status_label()
        
        # Notify parent
        if self.on_queue_changed:
            self.on_queue_changed(self.pkg_key, self.source, self.pkg, self.is_queued)


class SearchResultsPage(Adw.NavigationPage):
    """Page showing search results from package manager and Flatpak."""
    
    # Source type constants
    SOURCE_NATIVE = "native"
    SOURCE_AUR = "aur"
    SOURCE_FLATPAK = "flatpak"
    
    def __init__(self, window: 'LinuxToolkitWindow', query: str, distro):
        super().__init__(title=f"Search: {query}")
        
        self.window = window
        self.query = query
        self.distro = distro
        self.selected_packages: dict[str, dict] = {}  # pkg_key -> package info
        self.pkg_checkboxes: dict[str, Gtk.CheckButton] = {}  # pkg_key -> checkbox
        self.search_results: list[dict] = []
        self.flatpak_available = self._check_flatpak_available()
        
        self.build_ui()
        # Start search after UI is built
        GLib.timeout_add(100, self.run_search)
    
    def _check_flatpak_available(self) -> bool:
        """Check if flatpak is installed and flathub is configured."""
        import shutil
        if not shutil.which('flatpak'):
            return False
        
        try:
            result = subprocess.run(
                ['flatpak', 'remotes'],
                capture_output=True, text=True, timeout=5
            )
            return 'flathub' in result.stdout.lower()
        except:
            return False
    
    def build_ui(self):
        """Build the search results UI."""
        # Main container with header for back button
        toolbar_view = Adw.ToolbarView()
        self.set_child(toolbar_view)
        
        # Header with back button only (no window controls)
        header = Adw.HeaderBar()
        header.set_show_end_title_buttons(False)
        header.set_show_start_title_buttons(False)
        toolbar_view.add_top_bar(header)
        
        # Scrollable content
        self.scrolled = Gtk.ScrolledWindow()
        self.scrolled.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scrolled.set_vexpand(True)
        toolbar_view.set_content(self.scrolled)
        
        # Content with clamp
        clamp = Adw.Clamp()
        clamp.set_maximum_size(800)
        clamp.set_margin_top(20)
        clamp.set_margin_bottom(20)
        clamp.set_margin_start(20)
        clamp.set_margin_end(20)
        self.scrolled.set_child(clamp)
        
        self.content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        clamp.set_child(self.content_box)
        
        # Loading indicator
        self.spinner = Gtk.Spinner()
        self.spinner.set_size_request(48, 48)
        self.spinner.start()
        
        spinner_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        spinner_box.set_valign(Gtk.Align.CENTER)
        spinner_box.set_vexpand(True)
        spinner_box.append(self.spinner)
        
        self.loading_label = Gtk.Label(label=f"Searching for '{self.query}'...")
        spinner_box.append(self.loading_label)
        
        self.content_box.append(spinner_box)
    
    def run_search(self) -> bool:
        """Run the search in background thread."""
        import threading
        thread = threading.Thread(target=self._do_search, daemon=True)
        thread.start()
        return False
    
    def _do_search(self):
        """Execute the search across native repos and Flatpak."""
        import subprocess
        
        all_results = []
        
        # Update status
        GLib.idle_add(self._update_loading, "Searching native packages...")
        
        # 1. Search native package manager
        try:
            native_results = self._search_native()
            all_results.extend(native_results)
        except Exception as e:
            # Show a non-blocking hint instead of printing to stdout
            if hasattr(self, "window") and self.window is not None:
                GLib.idle_add(self.window.show_toast, f"Native search failed: {e}")
        
        # 2. Search Flatpak (if available)
        if self.flatpak_available:
            GLib.idle_add(self._update_loading, "Searching Flathub...")
            try:
                flatpak_results = self._search_flatpak()
                all_results.extend(flatpak_results)
            except Exception as e:
                if hasattr(self, "window") and self.window is not None:
                    GLib.idle_add(self.window.show_toast, f"Flathub search failed: {e}")
        
        # Sort results: Native first, then AUR/third-party, then Flatpak
        source_order = {self.SOURCE_NATIVE: 0, self.SOURCE_AUR: 1, self.SOURCE_FLATPAK: 2}
        all_results.sort(key=lambda x: (source_order.get(x.get('source', self.SOURCE_NATIVE), 99), x['name'].lower()))
        
        self.search_results = all_results[:100]  # Limit total results
        GLib.idle_add(self._show_results)
    
    def _update_loading(self, message: str):
        """Update loading message."""
        self.loading_label.set_label(message)
    
    def _search_native(self) -> list[dict]:
        """Search native package manager."""
        results = []
        family = self.distro.family.value
        
        try:
            if family == 'arch':
                proc = subprocess.run(
                    ['pacman', '-Ss', self.query],
                    capture_output=True, text=True, timeout=30
                )
                results = self._parse_pacman_results(proc.stdout)
                
            elif family in ('fedora', 'rhel'):
                proc = subprocess.run(
                    ['dnf', 'search', self.query],
                    capture_output=True, text=True, timeout=30
                )
                output = proc.stdout + proc.stderr
                results = self._parse_dnf_results(output)
                
            elif family == 'debian':
                proc = subprocess.run(
                    ['apt', 'search', self.query],
                    capture_output=True, text=True, timeout=30
                )
                results = self._parse_apt_results(proc.stdout)
                
            elif family == 'opensuse':
                proc = subprocess.run(
                    ['zypper', 'search', self.query],
                    capture_output=True, text=True, timeout=30
                )
                results = self._parse_zypper_results(proc.stdout)
        
        except subprocess.TimeoutExpired:
            # Treat timeout as "no results" without scaring the user
            pass
        except Exception as e:
            if hasattr(self, "window") and self.window is not None:
                GLib.idle_add(self.window.show_toast, f"Native search failed: {e}")
        
        # Mark all as native source
        for r in results:
            r['source'] = self.SOURCE_NATIVE
            r['source_display'] = self._get_native_source_name()
        
        return results[:50]  # Limit native results
    
    def _search_flatpak(self) -> list[dict]:
        """Search Flatpak/Flathub."""
        results = []
        
        try:
            proc = subprocess.run(
                ['flatpak', 'search', '--columns=name,description,application,version', self.query],
                capture_output=True, text=True, timeout=30
            )
            
            for line in proc.stdout.strip().split('\n'):
                if not line or line.startswith('Name'):
                    continue
                
                parts = line.split('\t')
                if len(parts) >= 3:
                    name = parts[0].strip()
                    desc = parts[1].strip() if len(parts) > 1 else ""
                    app_id = parts[2].strip() if len(parts) > 2 else ""
                    version = parts[3].strip() if len(parts) > 3 else ""
                    
                    # Check if already installed
                    installed = self._check_flatpak_installed(app_id)
                    
                    results.append({
                        'name': name,
                        'description': desc,
                        'version': version,
                        'app_id': app_id,
                        'installed': installed,
                        'source': self.SOURCE_FLATPAK,
                        'source_display': 'Flathub'
                    })
        
        except subprocess.TimeoutExpired:
            # Timeout → just treat as zero results
            pass
        except Exception as e:
            if hasattr(self, "window") and self.window is not None:
                GLib.idle_add(self.window.show_toast, f"Flathub search failed: {e}")
        
        return results[:30]  # Limit flatpak results
    
    def _check_flatpak_installed(self, app_id: str) -> bool:
        """Check if a Flatpak app is installed."""
        try:
            result = subprocess.run(
                ['flatpak', 'info', app_id],
                capture_output=True, timeout=5
            )
            return result.returncode == 0
        except:
            return False
    
    def _get_native_source_name(self) -> str:
        """Get display name for the native package source."""
        family = self.distro.family.value
        source_names = {
            'arch': 'pacman',
            'fedora': 'dnf',
            'rhel': 'dnf',
            'debian': 'apt',
            'opensuse': 'zypper',
        }
        return source_names.get(family, self.distro.package_manager)
    
    def _parse_pacman_results(self, output: str) -> list[dict]:
        """Parse pacman -Ss output."""
        results = []
        lines = output.strip().split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            if line and not line.startswith(' '):
                # Package line: repo/name version
                parts = line.split()
                if parts:
                    full_name = parts[0]
                    name = full_name.split('/')[-1] if '/' in full_name else full_name
                    version = parts[1] if len(parts) > 1 else ""
                    
                    # Next line is description
                    desc = ""
                    if i + 1 < len(lines) and lines[i + 1].startswith(' '):
                        desc = lines[i + 1].strip()
                        i += 1
                    
                    results.append({
                        'name': name,
                        'version': version,
                        'description': desc,
                        'installed': '[installed]' in line.lower()
                    })
            i += 1
        return results[:50]  # Limit results
    
    def _parse_dnf_results(self, output: str) -> list[dict]:
        """Parse dnf/dnf5 search output."""
        results = []
        lines = output.strip().split('\n')
        
        for line in lines:
            # Skip empty lines
            if not line:
                continue
            
            # Skip header/status lines
            if any(skip in line for skip in [
                'Updating and loading',
                'Repositories loaded',
                'Last metadata',
                'Matched fields:',
                'Importing OpenPGP',
                'UserID',
                'Fingerprint',
                'From',
                'Is this ok',
                'key was',
                '>>>'
            ]):
                continue
            
            # Skip lines that don't look like package entries
            if line.startswith('='):
                continue
            
            # dnf5 format: " package.arch   Description here"
            # Starts with space, has .arch suffix, multiple spaces before description
            if line.startswith(' '):
                line = line.strip()
                
                # Split on multiple spaces (2 or more) to separate name from description
                import re
                parts = re.split(r'\s{2,}', line, maxsplit=1)
                
                if len(parts) >= 1:
                    name_arch = parts[0].strip()
                    desc = parts[1].strip() if len(parts) > 1 else ""
                    
                    # Extract name (remove .arch suffix)
                    name = name_arch
                    for suffix in ['.x86_64', '.noarch', '.i686', '.aarch64', '.armv7hl']:
                        if name.endswith(suffix):
                            name = name[:-len(suffix)]
                            break
                    
                    if name:  # Only add if we got a valid name
                        results.append({
                            'name': name,
                            'version': '',
                            'description': desc,
                            'installed': False
                        })
            
            # Old dnf format: "package.arch : Description"
            elif ' : ' in line:
                parts = line.split(' : ', 1)
                name_arch = parts[0].strip()
                desc = parts[1].strip() if len(parts) > 1 else ""
                
                # Extract name (remove .arch suffix)
                name = name_arch
                for suffix in ['.x86_64', '.noarch', '.i686', '.aarch64', '.armv7hl']:
                    if name.endswith(suffix):
                        name = name[:-len(suffix)]
                        break
                
                if name:
                    results.append({
                        'name': name,
                        'version': '',
                        'description': desc,
                        'installed': False
                    })
        
        return results[:50]
    
    def _parse_apt_results(self, output: str) -> list[dict]:
        """Parse apt search output."""
        results = []
        lines = output.strip().split('\n')
        
        for line in lines:
            if not line or line.startswith('Sorting') or line.startswith('Full Text'):
                continue
            
            # Format: package/repo version arch [installed]
            #         description
            if '/' in line and not line.startswith(' '):
                parts = line.split()
                if parts:
                    name = parts[0].split('/')[0]
                    version = parts[1] if len(parts) > 1 else ""
                    installed = '[installed' in line.lower()
                    
                    results.append({
                        'name': name,
                        'version': version,
                        'description': '',
                        'installed': installed
                    })
            elif line.startswith(' ') and results:
                # Description line
                results[-1]['description'] = line.strip()
        
        return results[:50]
    
    def _parse_zypper_results(self, output: str) -> list[dict]:
        """Parse zypper search output."""
        results = []
        lines = output.strip().split('\n')
        
        for line in lines:
            # Skip headers
            if not line or line.startswith('-') or line.startswith('S '):
                continue
            
            # Format: S | Name | Summary | Type
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 3:
                status = parts[0]
                name = parts[1]
                desc = parts[2]
                
                results.append({
                    'name': name,
                    'version': '',
                    'description': desc,
                    'installed': status == 'i'
                })
        
        return results[:50]
    
    def _show_error(self, message: str):
        """Show error message."""
        # Clear content
        while self.content_box.get_first_child():
            self.content_box.remove(self.content_box.get_first_child())
        
        error_label = Gtk.Label(label=f"Search failed: {message}")
        error_label.add_css_class("error")
        self.content_box.append(error_label)
    
    def _show_results(self):
        """Display search results."""
        # Clear loading indicator
        while self.content_box.get_first_child():
            self.content_box.remove(self.content_box.get_first_child())
        
        if not self.search_results:
            no_results = Gtk.Label(label=f"No packages found for '{self.query}'")
            no_results.add_css_class("dim-label")
            self.content_box.append(no_results)
            
            # Hint about Flatpak if not available
            if not self.flatpak_available:
                hint = Gtk.Label()
                hint.set_markup("<small>Tip: Enable Flathub in Setup Tools for more results</small>")
                hint.add_css_class("dim-label")
                hint.set_margin_top(10)
                self.content_box.append(hint)
            return
        
        # Count results by source
        native_count = sum(1 for r in self.search_results if r.get('source') == self.SOURCE_NATIVE)
        flatpak_count = sum(1 for r in self.search_results if r.get('source') == self.SOURCE_FLATPAK)
        
        # Results header
        header_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        header_box.set_margin_bottom(5)
        self.content_box.append(header_box)
        
        header_label = Gtk.Label()
        header_label.set_markup(f"<b>Found {len(self.search_results)} packages</b>")
        header_label.set_halign(Gtk.Align.START)
        header_label.set_hexpand(True)
        header_box.append(header_label)
        
        # Source summary
        sources = []
        if native_count > 0:
            sources.append(f"{native_count} {self._get_native_source_name()}")
        if flatpak_count > 0:
            sources.append(f"{flatpak_count} Flathub")
        
        if sources:
            source_label = Gtk.Label()
            source_label.set_markup(f"<small>{' • '.join(sources)}</small>")
            source_label.add_css_class("dim-label")
            source_label.set_halign(Gtk.Align.END)
            header_box.append(source_label)
        
        # Results list
        group = Adw.PreferencesGroup()
        self.content_box.append(group)
        
        for pkg in self.search_results:
            row = Adw.ActionRow()
            row.set_title(pkg['name'])
            
            # Build subtitle with version and description
            subtitle_parts = []
            if pkg.get('version'):
                subtitle_parts.append(pkg['version'])
            if pkg.get('description'):
                subtitle_parts.append(pkg['description'])
            row.set_subtitle(" - ".join(subtitle_parts) if subtitle_parts else "No description")
            
            # Source badge (before checkbox)
            source = pkg.get('source', self.SOURCE_NATIVE)
            source_display = pkg.get('source_display', self._get_native_source_name())
            
            source_badge = Gtk.Label()
            source_badge.set_markup(f"<small>{source_display}</small>")
            source_badge.set_valign(Gtk.Align.CENTER)
            source_badge.set_width_chars(8)
            
            # Color code by source
            if source == self.SOURCE_FLATPAK:
                source_badge.add_css_class("accent")  # Blue-ish for Flatpak
            else:
                source_badge.add_css_class("dim-label")  # Grey for native
            
            # Check if installed
            is_installed = pkg.get('installed', False)
            if not is_installed and source == self.SOURCE_NATIVE:
                is_installed = self._check_if_installed(pkg['name'])
            
            # Create unique key for this package
            pkg_key = f"{pkg['name']}:{source}"
            if source == self.SOURCE_FLATPAK:
                pkg_key = pkg.get('app_id', pkg['name'])
            
            # Checkbox for selection
            checkbox = Gtk.CheckButton()
            checkbox.set_valign(Gtk.Align.CENTER)
            
            if is_installed:
                # Installed - disabled checkbox
                checkbox.set_sensitive(False)
                checkbox.set_active(True)
                
                # Installed badge
                installed_label = Gtk.Label(label="Installed")
                installed_label.add_css_class("success")
                installed_label.set_valign(Gtk.Align.CENTER)
                row.add_suffix(installed_label)
            else:
                # Not installed - enable checkbox and track it
                checkbox.connect("toggled", self.on_package_toggled, pkg_key, source, pkg)
                self.pkg_checkboxes[pkg_key] = checkbox
            
            row.add_prefix(checkbox)
            
            # Add source badge after checkbox
            row.add_prefix(source_badge)
            
            # Make row clickable for details (not linked to checkbox)
            row.set_activatable(True)
            row.connect("activated", self._on_package_row_clicked, pkg, source, pkg_key, source_display)
            
            # Arrow to show clickable
            arrow = Gtk.Image.new_from_icon_name("go-next-symbolic")
            row.add_suffix(arrow)
            
            group.add(row)
        
        # Flathub hint if not available
        if not self.flatpak_available:
            hint_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
            hint_box.set_halign(Gtk.Align.CENTER)
            hint_box.set_margin_top(10)
            
            hint_icon = Gtk.Image.new_from_icon_name("dialog-information-symbolic")
            hint_icon.add_css_class("dim-label")
            hint_box.append(hint_icon)
            
            hint_label = Gtk.Label()
            hint_label.set_markup("<small>Enable Flathub in Setup Tools for more results</small>")
            hint_label.add_css_class("dim-label")
            hint_box.append(hint_label)
            
            self.content_box.append(hint_box)
        
        # Install button
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(20)
        self.content_box.append(button_box)
        
        self.install_btn = Gtk.Button(label="Install Selected")
        self.install_btn.add_css_class("suggested-action")
        self.install_btn.connect("clicked", self.on_install_clicked)
        self.install_btn.set_sensitive(False)
        button_box.append(self.install_btn)
    
    def _check_if_installed(self, package_name: str) -> bool:
        """Check if a package is installed using the package manager."""
        import subprocess
        family = self.distro.family.value
        
        try:
            if family == 'arch':
                result = subprocess.run(
                    ['pacman', '-Q', package_name],
                    capture_output=True, timeout=5
                )
                return result.returncode == 0
            
            elif family in ('fedora', 'rhel'):
                result = subprocess.run(
                    ['rpm', '-q', package_name],
                    capture_output=True, timeout=5
                )
                return result.returncode == 0
            
            elif family == 'debian':
                result = subprocess.run(
                    ['dpkg', '-s', package_name],
                    capture_output=True, timeout=5
                )
                return result.returncode == 0
            
            elif family == 'opensuse':
                result = subprocess.run(
                    ['rpm', '-q', package_name],
                    capture_output=True, timeout=5
                )
                return result.returncode == 0
        except:
            pass
        
        return False
    
    def on_package_toggled(self, checkbox: Gtk.CheckButton, pkg_key: str, source: str, pkg: dict):
        """Handle package checkbox toggle."""
        if checkbox.get_active():
            self.selected_packages[pkg_key] = {
                'source': source,
                'name': pkg['name'],
                'app_id': pkg.get('app_id', ''),
                'pkg': pkg
            }
        else:
            self.selected_packages.pop(pkg_key, None)
        
        self._update_install_button()
    
    def _update_install_button(self):
        """Update install button state and label."""
        count = len(self.selected_packages)
        self.install_btn.set_sensitive(count > 0)
        if count > 0:
            self.install_btn.set_label(f"Install Selected ({count})")
        else:
            self.install_btn.set_label("Install Selected")
    
    def _on_package_row_clicked(self, row, pkg: dict, source: str, pkg_key: str, source_display: str):
        """Show package detail page when row is clicked."""
        is_queued = pkg_key in self.selected_packages
        detail_page = PackageDetailPage(
            window=self.window,
            pkg=pkg,
            source=source,
            pkg_key=pkg_key,
            is_queued=is_queued,
            on_queue_changed=self._on_detail_queue_changed,
            source_display=source_display
        )
        self.window.navigation_view.push(detail_page)
    
    def _on_detail_queue_changed(self, pkg_key: str, source: str, pkg: dict, queued: bool):
        """Handle queue change from detail page."""
        if queued:
            self.selected_packages[pkg_key] = {
                'source': source,
                'name': pkg['name'],
                'app_id': pkg.get('app_id', ''),
                'pkg': pkg
            }
        else:
            self.selected_packages.pop(pkg_key, None)
        
        # Update checkbox state
        if pkg_key in self.pkg_checkboxes:
            checkbox = self.pkg_checkboxes[pkg_key]
            checkbox.handler_block_by_func(self.on_package_toggled)
            checkbox.set_active(queued)
            checkbox.handler_unblock_by_func(self.on_package_toggled)
        
        self._update_install_button()
    
    def on_install_clicked(self, button):
        """Install selected packages."""
        if not self.selected_packages:
            return
        
        # Separate by source
        native_packages = []
        flatpak_packages = []
        
        for key, info in self.selected_packages.items():
            if info['source'] == self.SOURCE_FLATPAK:
                flatpak_packages.append(info)
            else:
                native_packages.append(info)
        
        num_packages = len(self.selected_packages)
        
        # Build body text showing sources
        body_lines = []
        if native_packages:
            body_lines.append(f"Native ({self._get_native_source_name()}):")
            for pkg in native_packages[:5]:
                body_lines.append(f"  • {pkg['name']}")
            if len(native_packages) > 5:
                body_lines.append(f"  ... and {len(native_packages) - 5} more")
        
        if flatpak_packages:
            if native_packages:
                body_lines.append("")
            body_lines.append("Flathub:")
            for pkg in flatpak_packages[:5]:
                body_lines.append(f"  • {pkg['name']}")
            if len(flatpak_packages) > 5:
                body_lines.append(f"  ... and {len(flatpak_packages) - 5} more")
        
        body = f"Install {num_packages} package(s)?\n\n" + "\n".join(body_lines)
        
        # Warning for large selections
        if num_packages >= 15:
            heading = "⚠️ Large Installation"
            body = f"You're about to install {num_packages} packages!\n\n" + \
                   "This may take a while and use significant disk space.\n\n" + \
                   "\n".join(body_lines) + "\n\n" + \
                   "Are you sure you want to continue?"
        elif num_packages >= 10:
            heading = "Install Multiple Packages"
        else:
            heading = "Install Packages"
        
        # Confirmation dialog
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading=heading,
            body=body
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("install", "Install")
        
        # Make it more obvious for large installs
        if num_packages >= 15:
            dialog.set_response_appearance("install", Adw.ResponseAppearance.DESTRUCTIVE)
        else:
            dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
        
        dialog.set_default_response("cancel" if num_packages >= 15 else "install")
        dialog.set_close_response("cancel")
        
        dialog.connect("response", self._on_install_response, native_packages, flatpak_packages)
        dialog.present()
    
    def _on_install_response(self, dialog, response, native_packages, flatpak_packages):
        """Handle install confirmation."""
        if response != "install":
            return
        
        # Install native packages via tux-helper
        if native_packages:
            apps = [App(
                id=pkg['name'],
                name=pkg['name'],
                description=f"Package: {pkg['name']}",
                packages={self.distro.family.value: [pkg['name']]}
            ) for pkg in native_packages]
            
            install_dialog = AppInstallDialog(self.window, apps, self.distro)
            install_dialog.present()
        
        # Install Flatpak packages (no sudo needed)
        if flatpak_packages:
            self._install_flatpaks(flatpak_packages)
    
    def _install_flatpaks(self, packages: list):
        """Install Flatpak packages."""
        import threading
        
        # Create a simple progress dialog
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Installing Flatpaks",
            body=f"Installing {len(packages)} Flatpak package(s)..."
        )
        dialog.add_response("close", "Close")
        dialog.set_response_enabled("close", False)
        
        def do_install():
            success = []
            failed = []
            
            for pkg in packages:
                app_id = pkg.get('app_id', pkg['name'])
                try:
                    result = subprocess.run(
                        ['flatpak', 'install', '-y', 'flathub', app_id],
                        capture_output=True, text=True, timeout=300
                    )
                    if result.returncode == 0:
                        success.append(pkg['name'])
                    else:
                        failed.append(pkg['name'])
                except Exception as e:
                    failed.append(pkg['name'])
            
            GLib.idle_add(finish_install, success, failed)
        
        def finish_install(success, failed):
            dialog.set_response_enabled("close", True)
            
            if failed:
                dialog.set_heading("Installation Complete (with errors)")
                dialog.set_body(
                    f"Installed: {len(success)}\nFailed: {len(failed)}\n\n"
                    f"Failed packages: {', '.join(failed)}"
                )
            else:
                dialog.set_heading("Installation Complete")
                dialog.set_body(f"Successfully installed {len(success)} Flatpak package(s)")
        
        dialog.present()
        thread = threading.Thread(target=do_install, daemon=True)
        thread.start()


class AppDetailPage(Adw.NavigationPage):
    """Detail page showing app information before installation."""
    
    def __init__(self, window, app: App, distro, is_queued: bool, on_queue_changed):
        super().__init__(title=app.name)
        
        self.window = window
        self.app = app
        self.distro = distro
        self.is_queued = is_queued
        self.on_queue_changed = on_queue_changed
        
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
        
        # App info header
        info_group = Adw.PreferencesGroup()
        info_group.set_title("Application Information")
        content_box.append(info_group)
        
        # Name and description
        name_row = Adw.ActionRow()
        name_row.set_title("Application")
        name_row.set_subtitle(self.app.name)
        name_row.add_prefix(Gtk.Image.new_from_icon_name(self.app.icon))
        info_group.add(name_row)
        
        desc_row = Adw.ActionRow()
        desc_row.set_title("Description")
        desc_row.set_subtitle(self.app.description)
        desc_row.add_prefix(Gtk.Image.new_from_icon_name("document-properties-symbolic"))
        info_group.add(desc_row)
        
        # Installation method
        packages = self.app.get_packages(self.distro.family)
        if packages:
            method_row = Adw.ActionRow()
            method_row.set_title("Installation Method")
            method_row.set_subtitle(f"Native packages via {self.distro.package_manager}")
            method_row.add_prefix(Gtk.Image.new_from_icon_name("drive-harddisk-symbolic"))
            info_group.add(method_row)
        elif self.app.flatpak:
            method_row = Adw.ActionRow()
            method_row.set_title("Installation Method")
            method_row.set_subtitle("Flatpak from Flathub")
            method_row.add_prefix(Gtk.Image.new_from_icon_name("system-software-install-symbolic"))
            info_group.add(method_row)
        
        # Special requirements
        if self.app.special:
            special_row = Adw.ActionRow()
            special_row.set_title("Special Requirements")
            special_row.set_subtitle("This app may require additional setup steps")
            special_row.add_prefix(Gtk.Image.new_from_icon_name("emblem-important-symbolic"))
            info_group.add(special_row)
        
        # Packages section
        if packages:
            pkg_group = Adw.PreferencesGroup()
            pkg_group.set_title(f"Packages to Install ({len(packages)})")
            pkg_group.set_description("These packages will be installed from your system's repositories")
            content_box.append(pkg_group)
            
            for pkg in packages:
                pkg_row = Adw.ActionRow()
                pkg_row.set_title(pkg)
                pkg_row.add_prefix(Gtk.Image.new_from_icon_name("package-x-generic-symbolic"))
                pkg_group.add(pkg_row)
        
        # Flatpak info
        if self.app.flatpak:
            flatpak_group = Adw.PreferencesGroup()
            flatpak_group.set_title("Flatpak Information")
            content_box.append(flatpak_group)
            
            flatpak_row = Adw.ActionRow()
            flatpak_row.set_title("Flatpak App ID")
            flatpak_row.set_subtitle(self.app.flatpak)
            flatpak_row.add_prefix(Gtk.Image.new_from_icon_name("application-x-executable-symbolic"))
            flatpak_group.add(flatpak_row)
        
        # Action buttons
        button_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        button_box.set_halign(Gtk.Align.CENTER)
        button_box.set_margin_top(24)
        content_box.append(button_box)
        
        # Queue toggle button
        self.queue_button = Gtk.Button()
        self._update_queue_button()
        self.queue_button.connect("clicked", self._on_queue_clicked)
        button_box.append(self.queue_button)
        
        # Status label
        self.status_label = Gtk.Label()
        self.status_label.add_css_class("dim-label")
        self._update_status_label()
        content_box.append(self.status_label)
    
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
            self.status_label.set_text("✓ This app is queued for installation")
        else:
            self.status_label.set_text("Click the button above to add to your install queue")
    
    def _on_queue_clicked(self, button):
        """Handle queue button click."""
        self.is_queued = not self.is_queued
        self._update_queue_button()
        self._update_status_label()
        
        # Notify parent
        if self.on_queue_changed:
            self.on_queue_changed(self.app.id, self.is_queued)


class CategoryPage(Adw.NavigationPage):
    """Page showing apps in a category."""
    
    def __init__(self, window: 'LinuxToolkitWindow', category: Category, distro):
        super().__init__(title=category.name)
        
        self.window = window
        self.category = category
        self.distro = distro
        self.selected_apps: set[str] = set()
        self.app_checkboxes: dict[str, Gtk.CheckButton] = {}
        
        self.build_ui()
    
    def build_ui(self):
        """Build the category page UI."""
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
        
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        clamp.set_child(content_box)
        
        # Search box for finding apps not in the list
        search_group = Adw.PreferencesGroup()
        content_box.append(search_group)
        
        self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text("Search for other apps...")
        self.search_entry.connect("activate", self._on_search_activated)
        self.search_entry.connect("search-changed", self._on_search_changed)
        search_group.add(self.search_entry)
        
        # Store all app rows for filtering
        self.app_rows: dict[str, Adw.ActionRow] = {}
        
        # Description banner
        if self.category.id == "special":
            banner = Adw.Banner()
            banner.set_title("These apps may require Flatpak or manual setup")
            banner.set_revealed(True)
            content_box.append(banner)
            
            # Add info box
            info_group = Adw.PreferencesGroup()
            info_group.set_description(
                "Some apps don't have native packages for all distros. "
                "Flatpak versions are used when available. Apps marked with ⚠️ "
                "may require additional manual steps after installation."
            )
            content_box.append(info_group)
        
        # App list
        self.app_group = Adw.PreferencesGroup()
        self.app_group.set_title(f"{self.category.name}")
        self.app_group.set_description(self.category.description)
        content_box.append(self.app_group)
        
        for app in self.category.apps:
            if not app.has_packages(self.distro.family):
                continue
            
            row = Adw.ActionRow()
            row.set_title(app.name)
            row.set_subtitle(app.description)
            
            # Checkbox
            checkbox = Gtk.CheckButton()
            checkbox.set_valign(Gtk.Align.CENTER)
            checkbox.connect("toggled", self.on_app_toggled, app.id)
            row.add_prefix(checkbox)
            
            # Track checkbox
            self.app_checkboxes[app.id] = checkbox
            
            # Make row clickable for details
            row.set_activatable(True)
            row.connect("activated", self._on_app_row_clicked, app)
            
            # Arrow to show clickable
            arrow = Gtk.Image.new_from_icon_name("go-next-symbolic")
            row.add_suffix(arrow)
            
            # Flatpak indicator
            if app.flatpak and not app.get_packages(self.distro.family):
                flatpak_badge = Gtk.Label(label="Flatpak")
                flatpak_badge.add_css_class("dim-label")
                row.add_suffix(flatpak_badge)
            
            # Special indicator
            if app.special:
                special_icon = Gtk.Image.new_from_icon_name("emblem-important-symbolic")
                special_icon.set_tooltip_text("Requires additional setup")
                row.add_suffix(special_icon)
            
            self.app_group.add(row)
            self.app_rows[app.id] = row
        
        # Bottom action bar
        action_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        action_bar.set_halign(Gtk.Align.CENTER)
        action_bar.set_margin_top(20)
        content_box.append(action_bar)
        
        # Install button
        self.install_btn = Gtk.Button(label="Install Selected")
        self.install_btn.add_css_class("suggested-action")
        self.install_btn.connect("clicked", self.on_install_clicked)
        self.install_btn.set_sensitive(False)
        action_bar.append(self.install_btn)
    
    def _on_search_changed(self, entry):
        """Filter apps as user types."""
        query = entry.get_text().lower().strip()
        
        for app_id, row in self.app_rows.items():
            if not query:
                row.set_visible(True)
            else:
                # Search in title and subtitle
                title = row.get_title().lower()
                subtitle = row.get_subtitle().lower() if row.get_subtitle() else ""
                matches = query in title or query in subtitle
                row.set_visible(matches)
    
    def _on_search_activated(self, entry):
        """Handle Enter key in search - could search package manager."""
        query = entry.get_text().strip()
        if query:
            # For now, just filter. Could expand to search package manager
            pass
    
    def _on_app_row_clicked(self, row, app: App):
        """Show app detail page when row is clicked."""
        is_queued = app.id in self.selected_apps
        detail_page = AppDetailPage(
            window=self.window,
            app=app,
            distro=self.distro,
            is_queued=is_queued,
            on_queue_changed=self._on_detail_queue_changed
        )
        self.window.navigation_view.push(detail_page)
    
    def _on_detail_queue_changed(self, app_id: str, queued: bool):
        """Handle queue change from detail page."""
        if queued:
            self.selected_apps.add(app_id)
        else:
            self.selected_apps.discard(app_id)
        
        # Update checkbox state
        if app_id in self.app_checkboxes:
            checkbox = self.app_checkboxes[app_id]
            checkbox.handler_block_by_func(self.on_app_toggled)
            checkbox.set_active(queued)
            checkbox.handler_unblock_by_func(self.on_app_toggled)
        
        self._update_install_button()
    
    def on_app_toggled(self, checkbox: Gtk.CheckButton, app_id: str):
        """Handle app checkbox toggle."""
        if checkbox.get_active():
            self.selected_apps.add(app_id)
        else:
            self.selected_apps.discard(app_id)
        
        self._update_install_button()
    
    def _update_install_button(self):
        """Update install button state and label."""
        count = len(self.selected_apps)
        self.install_btn.set_sensitive(count > 0)
        if count > 0:
            self.install_btn.set_label(f"Install Selected ({count})")
        else:
            self.install_btn.set_label("Install Selected")
    
    def on_install_clicked(self, button):
        """Start installation of selected apps."""
        if not self.selected_apps:
            return
        
        # Get selected app objects
        apps_to_install = [
            app for app in self.category.apps
            if app.id in self.selected_apps
        ]
        
        # Count packages
        total_packages = 0
        has_special = False
        for app in apps_to_install:
            pkgs = app.get_packages(self.distro.family)
            total_packages += len(pkgs) if pkgs else 1  # Count flatpak as 1
            if app.special:
                has_special = True
        
        # Build confirmation message
        app_list = "\n".join(f"  • {app.name}" for app in apps_to_install)
        special_warning = "\n\n⚠️ Some apps require adding external repositories." if has_special else ""
        
        # Show confirmation dialog
        dialog = Adw.MessageDialog(
            transient_for=self.window,
            heading="Confirm Installation",
            body=f"Install {len(apps_to_install)} app(s)?\n\n{app_list}{special_warning}"
        )
        dialog.add_response("cancel", "Cancel")
        dialog.add_response("install", "Install")
        dialog.set_response_appearance("install", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("install")
        dialog.set_close_response("cancel")
        
        dialog.connect("response", self._on_confirm_response, apps_to_install)
        dialog.present()
    
    def _on_confirm_response(self, dialog, response, apps_to_install):
        """Handle confirmation dialog response."""
        if response == "install":
            install_dialog = AppInstallDialog(self.window, apps_to_install, self.distro)
            install_dialog.present()


class AppInstallDialog(Adw.Dialog):
    """Dialog for installing applications."""
    
    def __init__(self, parent: Gtk.Window, apps: list[App], distro):
        super().__init__()
        
        self.parent_window = parent
        self.apps = apps
        self.distro = distro
        self.cancelled = False
        
        self.successful_apps = []
        self.failed_apps = []
        
        self.set_title("Installing Applications...")
        self.set_content_width(650)
        self.set_content_height(500)
        
        self.build_ui()
    
    def build_ui(self):
        """Build the dialog UI."""
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
        
        # Current app label
        self.app_label = Gtk.Label()
        self.app_label.set_halign(Gtk.Align.START)
        self.app_label.add_css_class("dim-label")
        box.append(self.app_label)
        
        # Progress bar
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_show_text(True)
        box.append(self.progress_bar)
        
        # Output view
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
        
        # Text tags
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
        
        # Start installation
        GLib.timeout_add(500, self.start_installation)
    
    def append_output(self, text: str, tag: str = None):
        """Append text to output view."""
        end_iter = self.output_buffer.get_end_iter()
        if tag:
            self.output_buffer.insert_with_tags_by_name(end_iter, text + "\n", tag)
        else:
            self.output_buffer.insert(end_iter, text + "\n")
        GLib.idle_add(self._scroll_to_bottom)
    
    def _scroll_to_bottom(self):
        mark = self.output_buffer.create_mark(None, self.output_buffer.get_end_iter(), False)
        self.output_view.scroll_mark_onscreen(mark)
        self.output_buffer.delete_mark(mark)
        return False
    
    def start_installation(self) -> bool:
        """Start installation in background thread."""
        import threading
        thread = threading.Thread(target=self._run_installation, daemon=True)
        thread.start()
        return False
    
    def _run_installation(self):
        """Run installation."""
        import tempfile
        import json
        
        GLib.idle_add(self.append_output, "=" * 50, "header")
        GLib.idle_add(self.append_output, "Software Center - Installing Applications", "header")
        GLib.idle_add(self.append_output, "=" * 50, "header")
        GLib.idle_add(self.append_output, "")
        
        # Build plan
        plan = {"tasks": []}
        
        for app in self.apps:
            # Pre-commands (like adding repos)
            pre_cmds = app.pre_commands.get(self.distro.family.value, [])
            for cmd in pre_cmds:
                plan["tasks"].append({
                    "type": "command",
                    "name": f"{app.name} (setup)",
                    "command": cmd
                })
            
            # Package installation
            packages = app.get_packages(self.distro.family)
            if packages:
                # Check for SPECIAL: prefix (complex installs handled by tux-helper)
                special_packages = [p for p in packages if p.startswith("SPECIAL:")]
                native_packages = [p for p in packages if not p.startswith("SPECIAL:") and not p.startswith("AUR:")]
                
                # Handle special installations
                for special_pkg in special_packages:
                    app_id = special_pkg.replace("SPECIAL:", "")
                    plan["tasks"].append({
                        "type": "special",
                        "name": app.name,
                        "app_id": app_id
                    })
                
                # Handle native packages
                if native_packages:
                    plan["tasks"].append({
                        "type": "install",
                        "name": app.name,
                        "packages": native_packages
                    })
            elif app.flatpak:
                # Flatpak installation
                plan["tasks"].append({
                    "type": "command",
                    "name": f"{app.name} (Flatpak)",
                    "command": f"flatpak install -y flathub {app.flatpak}"
                })
            
            # Post-commands
            post_cmds = app.post_commands.get(self.distro.family.value, [])
            for cmd in post_cmds:
                plan["tasks"].append({
                    "type": "command",
                    "name": f"{app.name} (configure)",
                    "command": cmd
                })
        
        if not plan["tasks"]:
            GLib.idle_add(self.append_output, "No packages to install", "warning")
            GLib.idle_add(self._installation_complete)
            return
        
        # Write plan file
        plan_file = tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            prefix='ltk-sw-plan-',
            delete=False
        )
        json.dump(plan, plan_file)
        plan_file.close()
        
        GLib.idle_add(self.append_output, f"Installation plan: {len(plan['tasks'])} task(s)", "info")
        GLib.idle_add(self.append_output, "")
        
        # Find helper
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
            GLib.idle_add(self.append_output, "Error: tux-helper not found!", "error")
            GLib.idle_add(self._installation_complete)
            return
        
        GLib.idle_add(self.append_output, "Requesting authentication...", "info")
        GLib.idle_add(self.append_output, "")
        
        # Run helper
        cmd = ['pkexec', helper_path, '--execute-plan', plan_file.name]
        
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
                
                # Parse status messages
                if line.startswith('[Tux Assistant:'):
                    try:
                        end_bracket = line.index(']')
                        status_type = line[5:end_bracket].lower()
                        message = line[end_bracket + 2:]
                        
                        if status_type == 'success':
                            GLib.idle_add(self.append_output, f"✓ {message}", "success")
                        elif status_type == 'error':
                            GLib.idle_add(self.append_output, f"✗ {message}", "error")
                        elif status_type == 'warning':
                            GLib.idle_add(self.append_output, f"⚠ {message}", "warning")
                        elif status_type == 'start':
                            GLib.idle_add(self.append_output, f"→ {message}", "info")
                        elif status_type == 'progress':
                            parts = message.split(' ', 1)
                            if '/' in parts[0]:
                                current, total = parts[0].split('/')
                                try:
                                    progress = int(current) / int(total)
                                    task_name = parts[1] if len(parts) > 1 else ""
                                    GLib.idle_add(self._update_progress, progress, current, total, task_name)
                                except ValueError:
                                    pass
                        elif status_type == 'complete':
                            GLib.idle_add(self.append_output, f"● {message}", "info")
                        else:
                            GLib.idle_add(self.append_output, line)
                    except (ValueError, IndexError):
                        GLib.idle_add(self.append_output, line)
                else:
                    GLib.idle_add(self.append_output, line)
            
            process.wait()
            
        except Exception as e:
            GLib.idle_add(self.append_output, f"Error: {str(e)}", "error")
        finally:
            try:
                os.unlink(plan_file.name)
            except:
                pass
        
        GLib.idle_add(self._installation_complete)
    
    def _update_progress(self, progress: float, current: str, total: str, task_name: str):
        """Update progress display."""
        self.progress_bar.set_fraction(progress)
        self.progress_bar.set_text(f"{current}/{total}")
        if task_name:
            self.status_label.set_markup(f"<b>Installing: {task_name}</b>")
    
    def _installation_complete(self):
        """Handle installation complete."""
        self.progress_bar.set_fraction(1.0)
        
        if self.cancelled:
            self.status_label.set_markup("<b>Installation cancelled</b>")
            self.progress_bar.set_text("Cancelled")
        else:
            self.status_label.set_markup("<b>Installation complete!</b>")
            self.progress_bar.set_text("Done")
        
        self.app_label.set_text("")
        self.cancel_btn.set_sensitive(False)
        self.close_btn.set_sensitive(True)
    
    def on_cancel(self, button):
        """Handle cancel."""
        self.cancelled = True
        self.append_output("")
        self.append_output("⚠ Cancelling...", "warning")
        self.cancel_btn.set_sensitive(False)
    
    def on_close(self, button):
        """Handle close."""
        self.close()
