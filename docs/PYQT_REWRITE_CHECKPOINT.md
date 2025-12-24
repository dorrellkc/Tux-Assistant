# Tux Assistant v1.0.16 - Complete Feature Catalog
## Checkpoint for PyQt Rewrite

*Generated: December 23, 2025*
*Total Lines of Code: ~46,000+ Python*
*Total Methods: 272 in app.py alone*

---

## Table of Contents

1. [Application Overview](#1-application-overview)
2. [Core Application (app.py)](#2-core-application-apppy)
3. [Module Catalog](#3-module-catalog)
4. [Embedded Apps](#4-embedded-apps)
5. [Core Infrastructure](#5-core-infrastructure)
6. [Browser Features (Falkon-style rewrite target)](#6-browser-features)
7. [Data Storage & Configuration](#7-data-storage--configuration)
8. [Cross-Distribution Support](#8-cross-distribution-support)

---

## 1. Application Overview

### 1.1 What Tux Assistant Is
- GTK4/Libadwaita Linux system configuration tool
- Post-installation setup wizard
- System maintenance utility
- Embedded web browser with privacy features
- Embedded AI assistant (Claude integration)
- Internet radio player (Tux Tunes)
- 600+ users have cloned the repository

### 1.2 Architecture Summary
```
tux-assistant/
├── tux/
│   ├── app.py              # Main application (9,489 lines)
│   ├── styles.css          # Custom CSS styling
│   ├── __init__.py         # Package metadata
│   ├── core/               # Core infrastructure
│   │   ├── commands.py     # Command execution utilities
│   │   ├── desktop.py      # Desktop environment detection
│   │   ├── distro.py       # Distribution detection
│   │   ├── hardware.py     # Hardware detection
│   │   ├── logger.py       # Logging system
│   │   └── packages.py     # Package manager abstraction
│   ├── modules/            # Feature modules (17 modules)
│   │   ├── registry.py     # Module registration system
│   │   └── [16 feature modules]
│   └── apps/               # Embedded applications
│       └── tux_tunes/      # Internet radio player
├── assets/                 # Icons and images
│   ├── icons/              # 130+ custom tux-* SVG icons
│   └── [app icons]
├── data/                   # Desktop files, polkit policies
├── scripts/                # Build and helper scripts
└── install.sh              # Installation script
```

### 1.3 Supported Distributions
| Family | Distributions |
|--------|---------------|
| Arch | Arch Linux, Manjaro, EndeavourOS, Garuda |
| Debian | Debian, Ubuntu, Linux Mint, Pop!_OS, Zorin |
| Fedora | Fedora, Nobara |
| openSUSE | Tumbleweed, Leap |

### 1.4 Supported Desktop Environments
- GNOME (primary)
- KDE Plasma
- XFCE
- Cinnamon
- MATE
- Budgie

---

## 2. Core Application (app.py)

### 2.1 Main Application Class: `TuxAssistantApp`
**Inherits:** `Adw.Application`
**Lines:** 63-363

| Method | Function |
|--------|----------|
| `__init__` | Initialize application, register icons, actions |
| `on_startup` | Register bundled icons, load CSS |
| `_register_bundled_icons` | NO-OP (icons in hicolor) |
| `_register_bundled_icons_fallback` | NO-OP (legacy) |
| `load_css` | Load custom CSS from styles.css |
| `on_activate` | Create main window |
| `on_open` | Handle file/URL opening |
| `_open_pending_urls` | Process URLs passed at launch |
| `create_actions` | Setup keyboard shortcuts (Ctrl+Q, etc.) |
| `on_quit` | Clean shutdown |
| `on_about` | Show About dialog |
| `_check_audio_dependencies` | Verify GStreamer available |

### 2.2 Main Window Class: `TuxAssistantWindow`
**Inherits:** `Adw.ApplicationWindow`
**Lines:** 364-9471

#### 2.2.1 Window Management
| Method | Function |
|--------|----------|
| `__init__` | Setup window, load settings, build UI |
| `_set_window_icon` | Set taskbar/window icon |
| `_on_window_key_pressed` | Global keyboard shortcuts |
| `_get_available_icon` | Icon fallback system |
| `_load_window_size` | Restore window dimensions |
| `_save_window_size` | Persist window dimensions |
| `build_ui` | Main UI construction |

#### 2.2.2 Bookmarks System (Browser)
| Method | Function |
|--------|----------|
| `_load_bookmarks` | Load from ~/.config/tux-assistant/bookmarks.json |
| `_save_bookmarks` | Persist bookmarks |
| `_refresh_bookmarks_bar` | Update toolbar bookmarks |
| `_refresh_bookmarks_list` | Update manager list |
| `_on_bookmark_add_manual` | Add bookmark dialog |
| `_on_bookmark_edit` | Edit bookmark dialog |
| `_on_bookmark_delete` | Delete bookmark |
| `_on_bookmark_new_folder` | Create folder |
| `_on_bookmark_add_separator` | Add separator |
| `_on_bookmarks_import` | Import from HTML |
| `_on_bookmarks_export` | Export to HTML |
| `_show_bookmark_manager` | Full bookmark manager window |
| `_get_all_tags` | Get unique tags |
| `_create_tag_chip` | Create tag UI element |
| `_show_tag_manager` | Tag management dialog |
| `_rename_tag` | Rename tag across all bookmarks |
| `_delete_tag` | Remove tag from all bookmarks |

**Bookmark Drag & Drop:**
| Method | Function |
|--------|----------|
| `_on_bookmark_drag_prepare` | Prepare drag data |
| `_on_bookmark_drag_begin` | Start drag visual |
| `_on_bookmark_drop_to_folder` | Drop into folder |
| `_on_bookmark_reorder_drop` | Reorder bookmarks |
| `_on_separator_drag_prepare` | Separator drag |
| `_on_unified_drop` | Universal drop handler |

#### 2.2.3 History System (Browser)
| Method | Function |
|--------|----------|
| `_init_history_db` | Initialize SQLite database |
| `_record_history` | Add URL to history |
| `_calculate_frecency` | Calculate frecency score |
| `_get_history` | Query history with filters |
| `_get_history_suggestions` | Autocomplete suggestions |
| `_get_history_count` | Total history entries |
| `_delete_history_entry` | Delete single entry |
| `_delete_history_entries` | Batch delete |
| `_clear_history` | Clear by time range |
| `_check_history_maintenance` | Periodic cleanup check |
| `_cleanup_old_history` | Remove old entries |
| `_vacuum_history_db` | Compact database |

**History Window Methods:**
| Method | Function |
|--------|----------|
| `_create_hw_row` | Create history row widget |
| `_on_hw_search_changed` | Search history |
| `_on_hw_time_filter_changed` | Filter by time |
| `_on_hw_visit_clicked` | Open history URL |
| `_on_hw_delete_selected` | Delete selected |
| `_on_hw_clear_all` | Clear all history |

#### 2.2.4 Browser Settings
| Method | Function |
|--------|----------|
| `_load_browser_settings` | Load from browser.conf |
| `_save_browser_settings` | Persist settings |
| `_load_bookmarks_bar_visible` | Bar visibility state |
| `_save_bookmarks_bar_visible` | Persist bar visibility |
| `_load_zoom_level` | Get default zoom |
| `_save_zoom_level` | Persist zoom |

#### 2.2.5 Claude AI Panel
| Method | Function |
|--------|----------|
| `_build_global_claude_panel` | Build Claude sidebar |
| `_on_claude_toggle` | Show/hide Claude |
| `_show_claude_docked` | Dock Claude in sidebar |
| `_show_claude_floating` | Pop-out Claude window |
| `_on_claude_window_close` | Handle window close |
| `_on_claude_external` | Open in external browser |
| `_on_claude_download_started` | Handle file downloads |
| `_on_claude_download_decide_destination` | Set download path |
| `_on_claude_download_finished` | Download complete |
| `_on_claude_download_failed` | Download error |

#### 2.2.6 Browser Panel
| Method | Function |
|--------|----------|
| `_build_global_browser_panel` | Build browser sidebar |
| `_on_browser_toggle` | Show/hide browser |
| `_show_browser_docked` | Dock browser |
| `_show_browser_floating` | Pop-out window |
| `_on_browser_clicked` | Browser button handler |
| `_create_browser_webview` | Create WebKit view |
| `_browser_new_tab` | New tab |
| `_browser_close_current_tab` | Close current tab |
| `_browser_next_tab` | Next tab (Ctrl+Tab) |
| `_browser_prev_tab` | Previous tab |
| `_get_current_browser_webview` | Get active webview |
| `_on_browser_tab_changed` | Tab switch handler |
| `_on_browser_tab_close` | Tab close handler |
| `_close_browser_panel` | Close browser |
| `_on_browser_title_changed` | Update tab title |
| `_on_browser_home` | Go to homepage |
| `_on_browser_url_activate` | Navigate to URL |
| `_create_url_autocomplete_popover` | URL suggestions |

**Browser Navigation:**
| Method | Function |
|--------|----------|
| `_on_browser_decide_policy` | Handle navigation decisions |
| `_on_webview_decide_policy` | WebKit policy decisions |
| `_should_block_uri` | Check if URI blocked |
| `_handle_ocs_url` | Handle ocs:// URLs |

**Browser Zoom:**
| Method | Function |
|--------|----------|
| `_browser_zoom_in` | Increase zoom |
| `_browser_zoom_out` | Decrease zoom |
| `_browser_zoom_reset` | Reset to 100% |
| `_apply_zoom_to_all_tabs` | Apply zoom globally |
| `_show_zoom_toast` | Show zoom level |

**Find in Page:**
| Method | Function |
|--------|----------|
| `_show_find_bar` | Show find bar (Ctrl+F) |
| `_hide_find_bar` | Hide find bar |
| `_on_find_text_changed` | Search as typing |
| `_on_find_match_count` | Update match count |
| `_on_find_next` | Next match |
| `_on_find_prev` | Previous match |

**Fullscreen & Print:**
| Method | Function |
|--------|----------|
| `_toggle_fullscreen` | Toggle F11 fullscreen |
| `_browser_print` | Print page (Ctrl+P) |

#### 2.2.7 Privacy Shield (Ad/Tracker Blocking)
| Method | Function |
|--------|----------|
| `_init_content_filters` | Initialize filter system |
| `_load_or_create_filters` | Load filter rules |
| `_create_filter_rules` | Generate filter JSON |
| `_save_and_load_filter` | Apply filters |
| `_apply_ad_blocking_css` | CSS-based hiding |
| `_inject_ad_hiding_js` | JavaScript-based hiding |
| `_inject_sponsorblock_monitor` | YouTube ad skipping |
| `_update_blocked_count` | Update blocked counter |
| `_on_https_toggled` | Force HTTPS setting |
| `_on_ads_toggled` | Ad blocking setting |
| `_on_trackers_toggled` | Tracker blocking setting |
| `_on_sponsorblock_toggled` | SponsorBlock setting |

**Blocked Networks:** 50+ ad networks, 60+ tracker domains

#### 2.2.8 Text-to-Speech (Read Aloud)
| Method | Function |
|--------|----------|
| `_read_aloud` | Read text with espeak-ng |
| `_stop_read_aloud` | Stop playback |
| `_read_selection_aloud` | Read selected text |
| `_read_article_aloud` | Read full page |
| `_enable_reader_mode` | Extract article content |
| `_tts_playback_finished` | Cleanup after reading |
| `_on_tts_voice_changed` | Change voice |
| `_on_tts_speed_changed` | Change speed |
| `_on_tts_test_clicked` | Test voice |

#### 2.2.9 Downloads Manager
| Method | Function |
|--------|----------|
| `_on_browser_download_started` | Download started |
| `_on_browser_download_decide_destination` | Choose save location |
| `_on_browser_download_finished` | Download complete |
| `_on_browser_download_failed` | Download failed |
| `_on_browser_download_progress` | Update progress |
| `_update_downloads_ui` | Refresh downloads list |
| `_open_downloads_folder` | Open Downloads folder |
| `_open_file` | Open downloaded file |
| `_open_containing_folder` | Show in file manager |
| `_clear_completed_downloads` | Clear completed |

#### 2.2.10 Browser Context Menu
| Method | Function |
|--------|----------|
| `_on_browser_context_menu` | Right-click menu |
| `_on_read_article_clicked` | Read aloud menu item |

#### 2.2.11 Browser Settings UI
| Method | Function |
|--------|----------|
| `_on_homepage_changed` | Set homepage |
| `_on_search_engine_changed` | Set search engine |
| `_on_default_zoom_changed` | Set default zoom |
| `_on_clear_history_clicked` | Clear history |
| `_on_clear_cookies_clicked` | Clear cookies |
| `_on_clear_cache_clicked` | Clear cache |
| `_on_clear_all_clicked` | Clear all data |
| `_update_default_browser_status` | Check default browser |
| `_on_set_default_browser_clicked` | Set as default |

#### 2.2.12 Update Checker
| Method | Function |
|--------|----------|
| `_setup_update_popover` | Update notification UI |
| `_check_for_updates` | Check GitHub releases |
| `_compare_versions` | Compare version strings |
| `_show_update_available` | Show update notification |
| `_on_update_download_clicked` | Download update |

#### 2.2.13 Main Page & Navigation
| Method | Function |
|--------|----------|
| `create_menu` | Application menu |
| `_show_getting_started` | Getting started guide |
| `create_main_page` | Main navigation page |
| `create_system_info_banner` | System info display |
| `create_module_group_from_registry` | Module grid |
| `on_module_clicked` | Navigate to module |

#### 2.2.14 System Info
| Method | Function |
|--------|----------|
| `_on_launch_hardinfo2` | Launch hardinfo2 |
| `_on_install_hardinfo2` | Install hardinfo2 |
| `_check_hardinfo2_installed` | Check if installed |
| `_on_fastfetch_clicked` | Run fastfetch |

#### 2.2.15 Search
| Method | Function |
|--------|----------|
| `_build_search_index` | Build searchable index |
| `_on_search_changed` | Search as you type |
| `_on_search_activated` | Execute search |
| `_get_search_url` | Get search engine URL |
| `_do_web_search` | Web search in browser |

#### 2.2.16 Tux Tunes Integration
| Method | Function |
|--------|----------|
| `_on_tux_tunes_clicked` | Launch Tux Tunes |

#### 2.2.17 Installation
| Method | Function |
|--------|----------|
| `_on_install_to_system` | Install from source |
| `_on_install_response` | Confirm installation |
| `_is_running_portable` | Check if portable |
| `_is_installed` | Check if installed |

---

## 3. Module Catalog

### 3.1 Setup Tools (`setup_tools.py`)
**Lines:** 4,521
**Purpose:** Post-installation setup, driver installation, repository management

#### Classes:
| Class | Purpose |
|-------|---------|
| `SetupCategory` | Enum: ESSENTIALS, MULTIMEDIA, PRODUCTIVITY, etc. |
| `SetupTask` | Task definition with per-distro packages |
| `DetectedGPU` | GPU info for driver recommendations |
| `TaskDetailPage` | Individual task detail view |
| `AlternativeSourceInstallDialog` | Install from Flatpak/AUR/COPR |
| `BatchAlternativeInstallDialog` | Batch install from alt sources |
| `SetupToolsPage` | Main setup page |
| `SSHKeyRestoreDialog` | Restore SSH keys from backup |
| `GitCloneDialog` | Clone git repository |
| `InstallationDialog` | Package installation progress |

#### Features:
- **Task Categories:**
  - Essentials (codecs, fonts, archive tools)
  - Multimedia (VLC, GIMP, Audacity)
  - Productivity (LibreOffice, Calibre)
  - Development (VS Code, Git, Docker)
  - Gaming (Steam, Lutris, Wine)
  - System Tools (htop, neofetch)
  - Communication (Discord, Slack)
  - Utilities (timeshift, flatpak)

- **GPU Driver Detection:**
  - NVIDIA proprietary drivers
  - AMD drivers
  - Intel drivers
  - Automatic driver recommendations

- **Repository Management:**
  - Enable Flathub
  - Enable Multilib (Arch)
  - Install AUR helper (yay/paru)
  - Enable RPM Fusion (Fedora)
  - Enable Packman (openSUSE)

- **Alternative Package Sources:**
  - Flatpak installation
  - AUR installation
  - COPR (Fedora)
  - PPA (Ubuntu)
  - OBS (openSUSE)

- **SSH Key Restore:**
  - Restore from backup location
  - Set correct permissions

- **Git Clone:**
  - Clone repositories to ~/Development

### 3.2 Networking (`networking.py`)
**Lines:** 4,467
**Purpose:** Network configuration, file sharing, VPN, firewall

#### Classes:
| Class | Purpose |
|-------|---------|
| `NetworkHost` | Discovered network host |
| `SambaShare` | Samba share configuration |
| `FirewallBackend` | Enum: FIREWALLD, UFW, IPTABLES |
| `ScanType` | Enum: QUICK_SMB, FULL_NETWORK |
| `NetworkScanner` | Network discovery |
| `SambaManager` | Samba configuration |
| `ADManager` | Active Directory join/leave |
| `FirewallManager` | Firewall configuration |
| `SimpleNetworkingPage` | Simple networking view |
| `NetworkingPage` | Advanced networking view |
| `NetworkScanPage` | Network scan results |
| `ChangeHostnameDialog` | Change hostname |
| `QuickShareDialog` | Quick folder share |
| `ManageSharesPage` | Manage Samba shares |
| `EditShareDialog` | Edit share settings |
| `SambaUserDialog` | Manage Samba users |
| `DomainJoinDialog` | Join AD domain |
| `QuickOpenPortDialog` | Open firewall port |
| `FirewallPage` | Firewall management |
| `PlanExecutionDialog` | Execute network operations |

#### Features:
- **Network Discovery:**
  - Quick SMB scan
  - Full network scan
  - Browse network shares
  - Resolve hostnames

- **Samba File Sharing:**
  - Install Samba packages
  - Create/edit/delete shares
  - Guest access option
  - User management
  - Usershare support

- **Active Directory:**
  - Join Windows domain
  - Leave domain
  - Domain discovery

- **Firewall Management:**
  - Support for firewalld, ufw, iptables
  - Open/close ports
  - View open ports
  - Service management

- **WiFi:**
  - View WiFi status
  - Open WiFi settings
  - Connect to hidden networks
  - Create WiFi hotspot

- **VPN:**
  - Import OpenVPN configs
  - Import WireGuard configs
  - Open VPN settings

- **Network Tools:**
  - Edit /etc/hosts
  - Run speedtest
  - Change hostname

### 3.3 Desktop Enhancements (`desktop_enhancements.py`)
**Lines:** 7,053
**Purpose:** Themes, extensions, tweaks, customization

#### Classes:
| Class | Purpose |
|-------|---------|
| `ThemeType` | Enum: GTK, ICON, CURSOR, PLASMA, KVANTUM |
| `Theme` | Theme definition |
| `Extension` | GNOME extension definition |
| `Tweak` | Desktop tweak definition |
| `Tool` | Customization tool definition |
| `ThemePreset` | Preset theme combinations |
| `ThemeManager` | Apply/manage themes |
| `TweakManager` | Apply/check tweaks |
| `ExtensionManager` | Manage GNOME extensions |
| `GnomeExtensionsBrowserPage` | Browse extensions.gnome.org |
| `PlanExecutionDialog` | Execute theme operations |
| `DesktopEnhancementsPage` | Main customization page |
| `ThemeDetailPage` | Theme details |
| `ThemeSelectionPage` | Select themes to install |
| `ThemeDownloadDialog` | Download theme progress |
| `ThemePreviewPage` | Preview theme in browser |
| `ThemeBrowserPage` | Browse themes online |
| `ExtensionSelectionPage` | Select extensions |
| `ToolSelectionPage` | Select tools |
| `ThemePresetPage` | Apply theme presets |

#### Features:
- **Theme Management:**
  - GTK themes
  - Icon themes
  - Cursor themes
  - Plasma themes (KDE)
  - Kvantum themes

- **Theme Sources:**
  - Bundled themes
  - Download from gnome-look.org
  - AUR packages
  - Install from tar/zip

- **GNOME Extensions:**
  - Browse installed extensions
  - Enable/disable extensions
  - Browse extensions.gnome.org
  - Install extensions

- **Desktop Tweaks:**
  - Show desktop icons
  - Minimize on click
  - Button layout
  - Font settings
  - Animation settings

- **Tools:**
  - Install Extension Manager
  - Install GNOME Tweaks
  - Install dconf Editor
  - Install Kvantum Manager

- **Theme Presets:**
  - Pre-configured theme combinations
  - One-click apply

### 3.4 Software Center (`software_center.py`)
**Lines:** 3,160
**Purpose:** Software discovery and installation

#### Classes:
| Class | Purpose |
|-------|---------|
| `App` | Application definition |
| `Category` | Software category |
| `SoftwareCenterPage` | Main software center |
| `PackageDetailPage` | Package details |
| `SearchResultsPage` | Search results |
| `AppDetailPage` | Application details |
| `CategoryPage` | Category browser |
| `AppInstallDialog` | Installation progress |

#### Features:
- **Categories:**
  - Audio & Video
  - Development
  - Education
  - Games
  - Graphics
  - Internet
  - Office
  - Science
  - System
  - Utilities

- **Search:**
  - Native package search
  - Flatpak search
  - Combined results

- **Installation:**
  - Queue multiple packages
  - Batch installation
  - Flatpak support
  - Progress tracking

- **Package Info:**
  - Description
  - Version
  - Repository source
  - Installed status

### 3.5 Developer Tools (`developer_tools.py`)
**Lines:** 4,981
**Purpose:** Git management, package building, Tux Assistant development

#### Classes:
| Class | Purpose |
|-------|---------|
| `GitProject` | Git repository info |
| `DeveloperToolsPage` | Main developer page |
| `CommitPushDialog` | Commit and push |
| `GitIdentityDialog` | Configure git user |
| `UpdateFromZipDialog` | Update Tux Assistant |

#### Features:
- **Prerequisites:**
  - Check/install Git
  - Check/install GitHub CLI
  - Check/install fpm (packaging)
  - Check/install Ruby/Gems

- **Tux Assistant Development:**
  - View current version
  - Sync repo from installed
  - Pull from dev branch
  - Push to dev branch
  - Build .run installer
  - Build DEB package
  - Build RPM packages (Fedora, openSUSE)
  - Build all packages
  - Publish to AUR
  - Publish GitHub release
  - Full release workflow

- **SSH Key Management:**
  - Check SSH agent status
  - Unlock SSH key
  - Add key to agent

- **Git Projects:**
  - Scan for projects
  - Add project manually
  - Create ~/Development folder
  - Pull projects
  - Push projects
  - Commit and push
  - Open in file manager
  - Open terminal
  - Install to system

- **Package Generation:**
  - Generate PKGBUILD
  - Generate .SRCINFO
  - Generate install hooks
  - Generate metainfo XML
  - Generate post-install scripts

### 3.6 System Maintenance (`system_maintenance.py`)
**Lines:** 1,066
**Purpose:** System cleanup, updates, startup apps

#### Classes:
| Class | Purpose |
|-------|---------|
| `CleanupItem` | Cleanup task definition |
| `StartupApp` | Startup application |
| `SystemMaintenancePage` | Main maintenance page |

#### Features:
- **Cleanup:**
  - Clean package cache
  - Clean user cache
  - Clean thumbnails
  - Clean systemd journal
  - Empty trash
  - Clean all at once

- **Updates:**
  - Check for updates
  - Run system updates
  - Update count display

- **Startup Apps:**
  - List startup applications
  - Enable/disable apps
  - Autostart management

- **Storage:**
  - Disk usage display
  - Launch disk analyzer (baobab)
  - Install analyzer if missing

### 3.7 Hardware Manager (`hardware_manager.py`)
**Lines:** 1,278
**Purpose:** Hardware configuration

#### Classes:
| Class | Purpose |
|-------|---------|
| `PrinterInfo` | Printer information |
| `BluetoothDevice` | Bluetooth device |
| `AudioDevice` | Audio device |
| `DisplayInfo` | Display information |
| `HardwareManagerPage` | Main hardware page |

#### Features:
- **Printers:**
  - List printers
  - Printer status
  - Start CUPS service
  - Install CUPS
  - Add printer (system-config-printer)

- **Bluetooth:**
  - List devices
  - Enable/disable Bluetooth
  - Start Bluetooth service
  - Install Bluetooth tools
  - Open Bluetooth settings

- **Audio:**
  - List output devices
  - List input devices
  - Set default device
  - Open sound settings

- **Displays:**
  - List displays
  - Resolution info
  - Refresh rate
  - Open display settings

### 3.8 Backup & Restore (`backup_restore.py`)
**Lines:** 1,077
**Purpose:** File backup and system snapshots

#### Classes:
| Class | Purpose |
|-------|---------|
| `BackupLocation` | Backup destination |
| `BackupRestorePage` | Main backup page |

#### Features:
- **File Backup:**
  - Select folders to backup
  - Common folders (Documents, Pictures, etc.)
  - Custom folder selection
  - Local destination
  - Network destination (SMB/SFTP)
  - Install rsync if needed

- **System Snapshots:**
  - Timeshift integration
  - Create snapshot
  - Open Timeshift
  - Install Timeshift

- **Network Backup:**
  - SMB/CIFS shares
  - SFTP/SSH
  - Connect to network location

### 3.9 Media Server (`media_server.py`)
**Lines:** 1,270
**Purpose:** Media server installation and configuration

#### Classes:
| Class | Purpose |
|-------|---------|
| `MediaServer` | Enum: PLEX, JELLYFIN, EMBY |
| `MediaServerInfo` | Server information |
| `DriveInfo` | Storage drive info |
| `MediaServerPage` | Main media server page |
| `InstallServerDialog` | Install server |
| `InstallProgressDialog` | Installation progress |
| `ConfigureDriveDialog` | Configure storage |
| `DriveConfigProgressDialog` | Drive config progress |
| `ConfigureFolderDialog` | Configure media folder |

#### Features:
- **Servers:**
  - Plex Media Server
  - Jellyfin
  - Emby

- **Installation:**
  - Download and install
  - Service management
  - Open web interface

- **Storage:**
  - List available drives
  - Configure mount points
  - Set permissions
  - Add media folders

### 3.10 ISO Creator (`iso_creator.py`)
**Lines:** 1,434
**Purpose:** Create bootable ISOs from current system

#### Classes:
| Class | Purpose |
|-------|---------|
| `SnapshotMode` | Enum: FULL, PERSONAL |
| `CompressionMode` | Enum: FAST, BALANCED, MAX |
| `EggsStatus` | Penguins-eggs status |
| `ISOCreatorPage` | Main ISO creator page |

#### Features:
- **Penguins-eggs Integration:**
  - Install eggs
  - Check status
  - Configure eggs

- **Snapshot Types:**
  - Full system snapshot
  - Personal data excluded

- **Compression:**
  - Fast (gzip)
  - Balanced (zstd)
  - Maximum (xz)

- **ISO Creation:**
  - Create bootable ISO
  - Progress tracking
  - Output location selection

### 3.11 Printer Wizard (`printer_wizard.py`)
**Lines:** 1,026
**Purpose:** Guided printer setup

#### Classes:
| Class | Purpose |
|-------|---------|
| `PrinterConnectionType` | Enum: USB, NETWORK, WIRELESS |
| `PrinterBrand` | Enum: HP, BROTHER, EPSON, CANON, etc. |
| `DiscoveredPrinter` | Discovered printer |
| `PrinterWizardPage` | Main wizard page |

#### Features:
- **Printer Discovery:**
  - USB printers
  - Network printers
  - Wireless printers

- **Brand-specific Setup:**
  - HP (hplip)
  - Brother
  - Epson
  - Canon
  - Generic

- **Driver Installation:**
  - Install printer drivers
  - PPD file selection
  - CUPS configuration

### 3.12 Help & Learning (`help_learning.py`)
**Lines:** 1,246
**Purpose:** Tutorials, troubleshooting, quick tasks

#### Classes:
| Class | Purpose |
|-------|---------|
| `Tutorial` | Tutorial definition |
| `TroubleshootItem` | Troubleshooting item |
| `QuickTask` | Quick task definition |
| `HelpLearningPage` | Main help page |
| `TutorialPage` | Tutorial viewer |
| `TroubleshooterPage` | Troubleshooter |
| `AllTasksPage` | All quick tasks |

#### Features:
- **Tutorials:**
  - Basic Linux commands
  - Package management
  - File system navigation
  - User management

- **Troubleshooting:**
  - No sound
  - No WiFi
  - Black screen
  - Boot issues

- **Quick Tasks:**
  - Common administrative tasks
  - One-click execution

### 3.13 Gaming (`gaming.py`)
**Lines:** 623
**Purpose:** Gaming setup

#### Classes:
| Class | Purpose |
|-------|---------|
| `GamingApp` | Gaming application |
| `GamingPage` | Main gaming page |

#### Features:
- **Gaming Platforms:**
  - Steam
  - Lutris
  - Heroic Games Launcher
  - Bottles

- **Wine/Proton:**
  - Wine installation
  - Proton-GE
  - DXVK

- **Gaming Tools:**
  - GameMode
  - MangoHud
  - ProtonUp-Qt

### 3.14 Nextcloud Setup (`nextcloud_setup.py`)
**Lines:** 979
**Purpose:** Nextcloud client setup

#### Classes:
| Class | Purpose |
|-------|---------|
| `NextcloudConfig` | Configuration |
| `NextcloudSetupWizard` | Setup wizard |
| `NextcloudInstallDialog` | Installation dialog |
| `NextcloudSetupPage` | Main page |

#### Features:
- **Client Installation:**
  - Install Nextcloud client
  - Configure server URL
  - Login setup

- **Sync Configuration:**
  - Select sync folders
  - Sync settings

### 3.15 Repository Management (`repo_management.py`)
**Lines:** 887
**Purpose:** Manage software repositories

#### Classes:
| Class | Purpose |
|-------|---------|
| `RepoManagementPage` | Main repo page |

#### Features:
- **Repository Operations:**
  - List repositories
  - Enable/disable repos
  - Add repositories
  - Remove repositories

- **Flatpak:**
  - Add Flathub
  - Manage remotes

### 3.16 Package Sources (`package_sources.py`)
**Lines:** 890
**Purpose:** Alternative package source definitions

#### Classes:
| Class | Purpose |
|-------|---------|
| `SourceType` | Enum: FLATPAK, AUR, COPR, PPA, etc. |
| `PackageSource` | Source definition |

#### Features:
- **Source Types:**
  - Flatpak
  - AUR (Arch)
  - COPR (Fedora)
  - PPA (Ubuntu)
  - RPM Fusion (Fedora)
  - Packman (openSUSE)
  - OBS (openSUSE)

### 3.17 Module Registry (`registry.py`)
**Lines:** 305
**Purpose:** Module registration and icon management

#### Classes:
| Class | Purpose |
|-------|---------|
| `ModuleCategory` | Enum: SETUP, SYSTEM, NETWORK, etc. |
| `ModuleInfo` | Module metadata |
| `ModuleRegistry` | Module registration |

#### Functions:
| Function | Purpose |
|----------|---------|
| `create_icon` | Create icon with fallback |
| `create_icon_simple` | Simple icon creation |
| `register_module` | Register module decorator |

---

## 4. Embedded Apps

### 4.1 Tux Tunes (Internet Radio)
**Location:** `tux/apps/tux_tunes/`
**Total Lines:** ~3,300

#### 4.1.1 Files Overview
| File | Purpose | Lines |
|------|---------|-------|
| `app.py` | Application class, preferences | 285 |
| `window.py` | Main window, all UI | 1,318 |
| `player.py` | GStreamer playback/recording | 850 |
| `api.py` | Radio-Browser.info API | 245 |
| `library.py` | Favorites, recents, config | 205 |
| `audio_analyzer.py` | Song boundary detection | 420 |

#### 4.1.2 Application Class (`app.py`)
| Class | Purpose |
|-------|---------|
| `TuxTunesApp` | Main application |
| `PreferencesDialog` | Settings dialog |

| Method | Purpose |
|--------|---------|
| `__init__` | Initialize app |
| `_setup_actions` | Setup keyboard shortcuts |
| `do_activate` | Create window |
| `_check_audio_deps` | Verify GStreamer |
| `do_shutdown` | Clean shutdown |
| `_on_about` | About dialog |
| `_on_preferences` | Open preferences |
| `_on_shortcuts` | Keyboard shortcuts help |
| `_on_quit` | Quit application |

#### 4.1.3 Main Window (`window.py`)
| Class | Purpose |
|-------|---------|
| `TuxTunesWindow` | Main application window |
| `AddStationDialog` | Add custom station |
| `EditStationDialog` | Edit custom station |

**Window Methods:**
| Method | Purpose |
|--------|---------|
| `_build_ui` | Build main interface |
| `_setup_shortcuts` | Keyboard shortcuts |
| `_create_menu` | Application menu |
| `_create_now_playing_bar` | Now playing display |
| `_create_player_controls` | Play/pause/stop/record |
| `_create_favorites_view` | Favorites tab |
| `_create_browse_view` | Browse/genre tabs |
| `_create_search_view` | Search tab |
| `_create_recents_view` | Recent stations tab |
| `_create_station_list_page` | Station list page |
| `_create_station_row` | Station row widget |
| `_load_initial_content` | Load on startup |
| `_refresh_favorites` | Refresh favorites list |
| `_refresh_recents` | Refresh recents list |
| `_load_popular_stations` | Load popular stations |
| `_do_search` | Execute search |
| `_on_genre_clicked` | Browse by genre |
| `_play_station` | Play a station |
| `_toggle_favorite` | Add/remove favorite |
| `_on_play_pause` | Toggle playback |
| `_on_stop` | Stop playback |
| `_on_record_toggle` | Start/stop recording |
| `_on_volume_changed` | Volume control |
| `_on_player_state_changed` | Update UI for state |
| `_on_metadata_changed` | Update now playing |
| `_on_track_changed` | Track change handler |
| `_on_recording_state` | Recording UI update |
| `_on_recording_ready` | Recording complete |
| `_show_auto_save_prompt` | Auto-save dialog |
| `_save_recording` | Save to disk |
| `_on_add_custom_station` | Add custom dialog |
| `_on_edit_custom_station` | Edit custom dialog |
| `_on_delete_custom_station` | Delete custom station |

#### 4.1.4 Player Engine (`player.py`)
| Class | Purpose |
|-------|---------|
| `TrackInfo` | Track metadata |
| `CachedRecording` | Cached recording data |
| `AudioBuffer` | Audio buffer for recording |
| `Player` | GStreamer player |

**Player Methods:**
| Method | Purpose |
|--------|---------|
| `__init__` | Initialize GStreamer |
| `_create_pipeline` | Create GStreamer pipeline |
| `_on_pad_added` | Dynamic pad linking |
| `_on_bus_message` | Handle GStreamer messages |
| `_handle_tags` | Extract metadata |
| `_on_track_change` | Track change detection |
| `_rotate_recording` | Rotate cached recordings |
| `_start_new_track` | Start recording new track |
| `_start_auto_recording` | Begin auto-recording |
| `_finalize_current_recording` | Complete recording |
| `_stop_recording_internal` | Stop recording |
| `save_cached_recording` | Save recording to file |
| `discard_cached_recording` | Delete cached recording |
| `cleanup_all_cached` | Clean temp files |
| `play` | Play station |
| `stop` | Stop playback |
| `pause` | Pause playback |
| `resume` | Resume playback |
| `toggle_play_pause` | Toggle play/pause |
| `set_volume` | Set volume level |
| `get_volume` | Get volume level |
| `start_recording` | Start manual recording |
| `stop_recording` | Stop manual recording |
| `toggle_recording` | Toggle recording |
| `get_current_metadata` | Get now playing info |
| `get_track_history` | Get track history |
| `get_cached_recordings` | Get pending recordings |
| `cleanup` | Cleanup on exit |

#### 4.1.5 Radio Browser API (`api.py`)
| Class | Purpose |
|-------|---------|
| `Station` | Station data model |
| `RadioBrowserAPI` | API client |

| Method | Purpose |
|--------|---------|
| `search` | Search by name |
| `search_by_tag` | Search by genre tag |
| `search_by_country` | Search by country |
| `get_popular` | Get popular stations |
| `get_trending` | Get trending stations |
| `get_top_voted` | Get top voted |
| `get_tags` | Get genre list |
| `get_countries` | Get country list |
| `click` | Record station click |
| `vote` | Vote for station |

#### 4.1.6 Library Management (`library.py`)
| Class | Purpose |
|-------|---------|
| `Library` | Favorites/recents storage |

| Method | Purpose |
|--------|---------|
| `_load_favorites` | Load favorites JSON |
| `_save_favorites` | Save favorites JSON |
| `_load_recents` | Load recents JSON |
| `_save_recents` | Save recents JSON |
| `_load_config` | Load settings |
| `save_config` | Save settings |
| `add_favorite` | Add favorite |
| `remove_favorite` | Remove favorite |
| `update_favorite` | Update favorite |
| `is_favorite` | Check if favorite |
| `get_favorites` | Get all favorites |
| `add_recent` | Add to recents |
| `get_recents` | Get recents |
| `clear_recents` | Clear recents |
| `get_recordings_dir` | Get save location |
| `set_recordings_dir` | Set save location |
| `get_recordings` | List saved recordings |

#### 4.1.7 Audio Analyzer (`audio_analyzer.py`)
| Class | Purpose |
|-------|---------|
| `BoundaryResult` | Song boundary result |
| `AudioAnalyzer` | Audio analysis engine |

| Method | Purpose |
|--------|---------|
| `get_missing_dependencies` | Check scipy/numpy |
| `get_install_command` | Get install command |
| `find_song_boundary` | Detect song boundary |
| `_detect_silence_boundary` | Find silence gaps |
| `_detect_spectral_boundary` | Spectral analysis |
| `split_at_boundary` | Split audio at boundary |

#### 4.1.8 Features Summary
- **Playback:** GStreamer-based streaming
- **Recording:** Manual and auto-recording modes
- **Smart Recording:** Track detection, song boundary split
- **Favorites:** Unlimited favorites storage
- **Recents:** Last 50 stations
- **Custom Stations:** Add/edit/delete custom URLs
- **Search:** By name, genre, country
- **Browse:** Popular, trending, top voted
- **Genres:** 50+ genre categories
- **Metadata:** Now playing, track history
- **Volume:** 0-100% with mute
- **Recording Formats:** MP3, OGG
- **Pre-buffer:** Capture start of songs
- **Post-buffer:** Capture end of songs

---

## 5. Core Infrastructure

### 5.1 Commands (`core/commands.py`)
**Lines:** 387

| Function | Purpose |
|----------|---------|
| `command_exists` | Check if command available |
| `run` | Run command, capture output |
| `run_sudo` | Run with sudo |
| `run_with_callback` | Async with progress callback |
| `check_sudo_access` | Check sudo availability |
| `sudo_write_file` | Write file as root |
| `sudo_append_file` | Append to file as root |
| `sudo_copy` | Copy file as root |
| `sudo_move` | Move file as root |
| `sudo_mkdir` | Create directory as root |
| `sudo_chmod` | Change permissions |
| `sudo_chown` | Change ownership |
| `get_terminal_commands` | Get terminal launch command |
| `find_terminal` | Find available terminal |
| `run_in_terminal` | Run script in terminal |

### 5.2 Desktop Detection (`core/desktop.py`)
**Lines:** 264

| Class/Function | Purpose |
|----------------|---------|
| `DesktopEnv` | Enum: GNOME, KDE, XFCE, etc. |
| `DisplayServer` | Enum: X11, WAYLAND |
| `DesktopInfo` | Desktop information |
| `get_running_processes` | List running processes |
| `detect_display_server` | Detect X11/Wayland |
| `detect_from_environment` | Detect from env vars |
| `detect_from_processes` | Detect from running processes |
| `detect` | Full detection |
| `get_desktop` | Get cached desktop info |
| `is_kde` | Check if KDE |
| `is_gnome` | Check if GNOME |
| `is_xfce` | Check if XFCE |
| `is_wayland` | Check if Wayland |
| `is_x11` | Check if X11 |

### 5.3 Distribution Detection (`core/distro.py`)
**Lines:** 262

| Class/Function | Purpose |
|----------------|---------|
| `DistroFamily` | Enum: ARCH, DEBIAN, FEDORA, SUSE |
| `DistroInfo` | Distribution information |
| `parse_os_release` | Parse /etc/os-release |
| `detect_family` | Detect distro family |
| `get_package_manager_info` | Get PM commands |
| `detect_aur_helper` | Find yay/paru |
| `detect` | Full detection |
| `get_distro` | Get cached distro info |
| `get_family` | Get distro family |
| `get_install_command` | Get install command |
| `get_search_command` | Get search command |

### 5.4 Hardware Detection (`core/hardware.py`)
**Lines:** 158

| Function | Purpose |
|----------|---------|
| `get_cpu_info` | Get CPU name, cores, threads |
| `get_ram_info` | Get RAM in GB |
| `get_gpu_info` | Get GPU name |
| `get_disk_info` | Get disk info |
| `check_hardinfo2_available` | Check hardinfo2 |
| `get_hardware_info` | Get all hardware info |
| `get_hardinfo2_package_name` | Get package name |
| `is_aur_package` | Check if AUR |
| `launch_hardinfo2` | Launch hardinfo2 |

### 5.5 Package Manager (`core/packages.py`)
**Lines:** 379

| Class | Purpose |
|-------|---------|
| `Package` | Package information |
| `InstallResult` | Installation result |
| `PackageManager` | Package manager abstraction |

| Method | Purpose |
|--------|---------|
| `is_installed` | Check if package installed |
| `search` | Search packages |
| `install` | Install packages |
| `remove` | Remove packages |
| `update` | Update package list |
| `upgrade` | Upgrade all packages |
| `get_installed` | List installed packages |

### 5.6 Logging (`core/logger.py`)
**Lines:** 113

| Class/Function | Purpose |
|----------------|---------|
| `TuxFormatter` | Custom log formatter |
| `setup_logging` | Configure logging |
| `get_logger` | Get logger instance |
| `is_debug_enabled` | Check debug mode |

---

## 5.5 UI Components (`tux/ui/`)

### 5.5.1 Fun Facts (`fun_facts.py`)
**Lines:** 813
**Purpose:** Display fun facts during long operations

#### Classes:
| Class | Purpose |
|-------|---------|
| `FactCategory` | Enum: LINUX, OPEN_SOURCE, TECH, HISTORICAL, COMMUNITY |
| `FunFact` | Fact with title, content, category, source |
| `FunFactsManager` | Manages fact database |
| `FunFactBox` | Single fact display widget |
| `RotatingFunFactWidget` | Auto-rotating fact display |
| `LongOperationDialog` | Dialog with progress + facts |

#### Features:
- 100+ curated Linux/open source facts
- Categories for filtering
- Auto-rotation during waits
- Progress bar integration
- Source attribution

### 5.5.2 GNOME Manager (`gnome_manager.py`)
**Lines:** 913
**Purpose:** Standalone GNOME extension/tweak manager

#### Functions:
| Function | Purpose |
|----------|---------|
| `get_gnome_shell_version` | Get GNOME Shell version |
| `get_installed_extensions` | List installed extensions |
| `install_extension` | Install extension from UUID |
| `enable_extension` | Enable extension |
| `disable_extension` | Disable extension |
| `uninstall_extension` | Remove extension |
| `get_gsetting` | Get GSettings value |
| `set_gsetting` | Set GSettings value |
| `search_extensions` | Search extensions.gnome.org |

#### Classes:
| Class | Purpose |
|-------|---------|
| `ExtensionRow` | Extension list row |
| `TweakRow` | Tweak toggle row |
| `GnomeManagerWindow` | Main manager window |
| `GnomeManagerApp` | Application class |

### 5.5.3 Tux Fetch (`tux_fetch.py`)
**Lines:** 203
**Purpose:** System info sidebar widget

#### Classes:
| Class | Purpose |
|-------|---------|
| `TuxFetchSidebar` | System info display sidebar |

#### Features:
- Distro name and version
- Kernel version
- Desktop environment
- CPU info
- Memory info
- Disk usage
- Uptime

### 5.5.4 Weather Widget (`weather_widget.py`)
**Lines:** 1,220
**Purpose:** Weather and news widget for main page

#### Functions:
| Function | Purpose |
|----------|---------|
| `load_widget_config` | Load widget settings |
| `save_widget_config` | Save widget settings |

#### Classes:
| Class | Purpose |
|-------|---------|
| `Weather` | Weather data model |
| `NewsItem` | News article model |
| `WeatherService` | Open-Meteo API client |
| `NewsService` | RSS news fetcher |
| `WeatherCard` | Weather display card |
| `NewsCard` | News article card |
| `WeatherWidget` | Main weather/news popover |
| `WidgetSettingsDialog` | Widget configuration |

#### Features:
- Open-Meteo API integration (free, no API key)
- Location auto-detection via IP
- Manual location setting
- Temperature units (C/F)
- 5-day forecast
- RSS news feed reader
- Configurable news sources
- Automatic refresh

---

## 5.6 Privileged Helper (`tux-helper`)

### Overview
**Lines:** 4,152
**Purpose:** Runs with elevated privileges via pkexec for system operations

### 5.6.1 Core Functions
| Function | Purpose |
|----------|---------|
| `detect_distro_family` | Detect Linux family |
| `get_package_manager_commands` | Get PM commands per family |
| `emit_status` | Send status to GUI |
| `emit_progress` | Send progress updates |
| `emit_output` | Send command output |
| `install_packages` | Install packages |
| `remove_packages` | Remove packages |
| `run_command` | Run arbitrary command |
| `execute_plan` | Execute installation plan |

### 5.6.2 Repository Management
| Function | Purpose |
|----------|---------|
| `check_debian_repos_enabled` | Check contrib/non-free |
| `enable_debian_repos` | Enable contrib/non-free |
| `ensure_debian_repos_for_packages` | Auto-enable repos |
| `check_opensuse_packman_enabled` | Check Packman repo |
| `enable_opensuse_packman` | Enable Packman |
| `check_opensuse_games_repo_enabled` | Check games repo |
| `enable_opensuse_games_repo` | Enable games repo |
| `check_fedora_rpmfusion_enabled` | Check RPM Fusion |
| `enable_fedora_rpmfusion` | Enable RPM Fusion |
| `enable_copr` | Enable COPR repo |
| `enable_ppa` | Enable PPA |
| `enable_obs` | Enable OBS repo |
| `refresh_package_cache` | Refresh package cache |

### 5.6.3 Package Availability
| Function | Purpose |
|----------|---------|
| `check_package_available_debian` | Check Debian pkg |
| `check_package_available_arch` | Check Arch pkg |
| `check_package_available_fedora` | Check Fedora pkg |
| `check_package_available_opensuse` | Check openSUSE pkg |
| `check_packages_available` | Check multiple packages |
| `filter_available_packages` | Filter to available |
| `get_available_packages_report` | Report available/missing |

### 5.6.4 Special Application Installers
| Function | Purpose |
|----------|---------|
| `install_special_app` | Install by app ID |
| `install_surfshark` | Surfshark VPN installer |
| `install_duckietv` | DuckieTV installer |
| `install_rustdesk` | RustDesk installer |
| `install_plex_desktop` | Plex Desktop installer |

### 5.6.5 Desktop Enhancement Setup
| Function | Purpose |
|----------|---------|
| `setup_emoji_keyboard` | Install emoji input |
| `setup_xfce_enhancements` | XFCE tweaks |
| `setup_kde_enhancements` | KDE tweaks |
| `setup_gnome_enhancements` | GNOME tweaks |

### 5.6.6 System Configuration
| Function | Purpose |
|----------|---------|
| `setup_virtualbox` | Install VirtualBox |
| `setup_virtmanager` | Install virt-manager/KVM |
| `remove_snap_completely` | Remove Snap + packages |
| `set_system_hostname` | Change hostname |
| `enable_alternative_source` | Enable alt package source |

### 5.6.7 Nextcloud Installation
| Function | Purpose |
|----------|---------|
| `install_nextcloud` | Full Nextcloud installer |
| `nc_install_packages` | Install NC packages |
| `nc_setup_database` | Setup MySQL/PostgreSQL |
| `nc_download_nextcloud` | Download NC files |
| `nc_configure_nextcloud` | Configure NC |
| `nc_configure_apache` | Setup Apache vhost |
| `nc_setup_ssl` | Setup Let's Encrypt SSL |
| `nc_setup_duckdns` | Setup DuckDNS DDNS |
| `nc_finalize` | Final setup steps |

---

## 5.7 Scripts

### 5.7.1 install.sh
**Lines:** 800+
**Purpose:** Main installation script

| Function | Purpose |
|----------|---------|
| `print_banner` | Show Tux Assistant banner |
| `detect_distro` | Detect distribution |
| `check_dependencies` | Check required deps |
| `install_dependencies` | Install dependencies |
| `install_app` | Install Tux Assistant |
| `install_icons` | Install 130+ icons |
| `install_desktop_entries` | Install .desktop files |
| `install_native_messaging` | Browser extension support |
| `uninstall_app` | Remove installation |

### 5.7.2 build-run.sh
**Lines:** 76
**Purpose:** Development build and run

### 5.7.3 run-header.sh
**Lines:** 364
**Purpose:** Self-extracting installer header

### 5.7.4 tux-native-host
**Lines:** 242
**Purpose:** Native messaging host for browser extension

### 5.7.5 tux-ocs-handler
**Lines:** 302
**Purpose:** Handle ocs:// URLs for theme installation

---

## 5.8 Browser Extension

### Location: `data/tux-browser-extension/`

### Files:
| File | Purpose |
|------|---------|
| `manifest.json` | Extension manifest |
| `background.js` | Background service worker |
| `icon.svg` | Extension icon |

### Features:
- Intercepts ocs:// URLs
- Communicates with tux-native-host
- Triggers theme downloads in Tux Assistant

---

## 6. Browser Features (Falkon-style rewrite target)

### 6.1 Current Browser Features
| Feature | Implementation |
|---------|----------------|
| Tabbed browsing | Adw.TabView |
| URL bar with autocomplete | Gtk.Entry + Popover |
| Bookmarks bar | Gtk.Box with buttons |
| Bookmark folders | JSON nested structure |
| Bookmark separators | Custom widget |
| Bookmark manager | Full window |
| Bookmark tags | JSON array per bookmark |
| Bookmark import/export | HTML format |
| History | SQLite with frecency |
| History manager | Full window |
| Downloads | WebKit downloads |
| Downloads manager | List in popover |
| Find in page | WebKit find controller |
| Zoom (30%-300%) | WebKit zoom |
| Print | WebKit print |
| Fullscreen | F11 toggle |
| Privacy Shield | Content blocking |
| Ad blocking | Network + CSS |
| Tracker blocking | Domain blocking |
| Force HTTPS | URL rewriting |
| SponsorBlock | YouTube integration |
| Reader mode | Content extraction |
| Read aloud (TTS) | espeak-ng |
| Context menu | Custom menu |
| Settings panel | Popover |
| Homepage | Configurable |
| Search engine | Configurable |
| Default browser | xdg-settings |

### 6.2 Falkon Features to Implement
| Feature | Priority |
|---------|----------|
| Session management | High |
| Tab groups | Medium |
| Built-in ad blocker UI | High |
| Extension support | Low |
| Speed dial | Medium |
| RSS reader | Low |
| Web inspector | Medium |
| Cookie manager | High |
| Password manager | High |
| Sync | Low |

---

## 7. Data Storage & Configuration

### 7.1 Configuration Files
| File | Purpose |
|------|---------|
| `~/.config/tux-assistant/bookmarks.json` | Browser bookmarks |
| `~/.config/tux-assistant/history.db` | Browser history (SQLite) |
| `~/.config/tux-assistant/browser.conf` | Browser settings |
| `~/.config/tux-assistant/window.conf` | Window size/state |
| `~/.config/tux-assistant/filters/` | Ad blocking filters |

### 7.2 Bookmarks JSON Structure
```json
[
  {
    "id": "uuid",
    "title": "Example",
    "url": "https://example.com",
    "favicon": "base64...",
    "tags": ["work", "reference"],
    "folder": null,
    "type": "bookmark"
  },
  {
    "id": "uuid",
    "title": "Folder Name",
    "type": "folder",
    "children": [...]
  },
  {
    "id": "uuid",
    "type": "separator"
  }
]
```

### 7.3 History Database Schema
```sql
CREATE TABLE history (
    id INTEGER PRIMARY KEY,
    url TEXT UNIQUE,
    title TEXT,
    visit_count INTEGER DEFAULT 1,
    last_visit TIMESTAMP,
    first_visit TIMESTAMP,
    frecency REAL DEFAULT 0
);

CREATE INDEX idx_frecency ON history(frecency DESC);
CREATE INDEX idx_last_visit ON history(last_visit DESC);
```

### 7.4 Browser Settings
```ini
[General]
homepage=https://duckduckgo.com
search_engine=duckduckgo
default_zoom=100

[Privacy]
force_https=true
block_ads=true
block_trackers=true
sponsorblock=false

[TTS]
voice=en
speed=175
```

---

## 8. Cross-Distribution Support

### 8.1 Package Manager Commands
| Family | Install | Search | Update | Upgrade |
|--------|---------|--------|--------|---------|
| Arch | pacman -S | pacman -Ss | pacman -Sy | pacman -Syu |
| Debian | apt install | apt search | apt update | apt upgrade |
| Fedora | dnf install | dnf search | dnf check-update | dnf upgrade |
| openSUSE | zypper install | zypper search | zypper refresh | zypper update |

### 8.2 Package Name Mappings
Many packages have different names across distributions. See `setup_tools.py` `SetupTask` definitions for complete mappings.

### 8.3 Desktop-Specific Features
| Feature | GNOME | KDE | XFCE |
|---------|-------|-----|------|
| Themes | GTK themes | Plasma themes | GTK themes |
| Extensions | GNOME extensions | KDE widgets | Panel plugins |
| Settings | gsettings | kwriteconfig5 | xfconf-query |
| File manager | Nautilus | Dolphin | Thunar |

---

## 9. PyQt Rewrite Considerations

### 9.1 GTK → Qt Widget Mapping
| GTK4/Libadwaita | PyQt6/Qt6 |
|-----------------|-----------|
| Adw.Application | QApplication |
| Adw.ApplicationWindow | QMainWindow |
| Adw.NavigationView | QStackedWidget |
| Adw.NavigationPage | QWidget |
| Adw.PreferencesGroup | QGroupBox |
| Adw.ActionRow | Custom widget |
| Adw.ExpanderRow | QTreeWidget item |
| Adw.SwitchRow | QCheckBox |
| Adw.ComboRow | QComboBox |
| Adw.EntryRow | QLineEdit |
| Adw.Toast | QToolTip / custom |
| Adw.Dialog | QDialog |
| Adw.TabView | QTabWidget |
| Gtk.Box | QVBoxLayout/QHBoxLayout |
| Gtk.ListBox | QListWidget |
| Gtk.FlowBox | QFlowLayout (custom) |
| Gtk.ScrolledWindow | QScrollArea |
| Gtk.Button | QPushButton |
| Gtk.Label | QLabel |
| Gtk.Entry | QLineEdit |
| Gtk.Image | QLabel + QPixmap |
| Gtk.ProgressBar | QProgressBar |
| Gtk.Popover | QMenu / QToolTip |

### 9.2 WebKit → QtWebEngine
| WebKit2GTK | QtWebEngine |
|------------|-------------|
| WebKit.WebView | QWebEngineView |
| WebKit.WebContext | QWebEngineProfile |
| WebKit.Settings | QWebEngineSettings |
| WebKit.DownloadManager | QWebEngineDownloadRequest |
| WebKit.FindController | QWebEnginePage.findText |
| WebKit.UserContentManager | QWebEngineScript |

### 9.3 Business Logic to Extract
These components can be reused with minimal changes:
- Distribution detection (`core/distro.py`)
- Desktop detection (`core/desktop.py`)
- Hardware detection (`core/hardware.py`)
- Command execution (`core/commands.py`)
- Package manager abstraction (`core/packages.py`)
- Setup task definitions (`setup_tools.py` - task data)
- Software app definitions (`software_center.py` - app data)
- Theme definitions (`desktop_enhancements.py` - theme data)
- Network managers (`networking.py` - SambaManager, ADManager, etc.)

### 9.4 UI to Rewrite
All UI code needs complete rewrite:
- Main window
- All module pages
- All dialogs
- Browser panel
- Claude panel
- Tux Tunes player

---

## 10. Statistics Summary

| Component | Lines of Code |
|-----------|---------------|
| **Main Application** | |
| app.py | 9,489 |
| **Modules** | |
| setup_tools.py | 4,521 |
| networking.py | 4,467 |
| desktop_enhancements.py | 7,053 |
| software_center.py | 3,160 |
| developer_tools.py | 4,981 |
| system_maintenance.py | 1,066 |
| hardware_manager.py | 1,278 |
| backup_restore.py | 1,077 |
| media_server.py | 1,270 |
| iso_creator.py | 1,434 |
| printer_wizard.py | 1,026 |
| help_learning.py | 1,246 |
| gaming.py | 623 |
| nextcloud_setup.py | 979 |
| repo_management.py | 887 |
| package_sources.py | 890 |
| registry.py | 305 |
| **UI Components** | |
| fun_facts.py | 813 |
| gnome_manager.py | 913 |
| tux_fetch.py | 203 |
| weather_widget.py | 1,220 |
| **Tux Tunes** | |
| window.py | 1,318 |
| player.py | 850 |
| app.py | 285 |
| api.py | 245 |
| library.py | 205 |
| audio_analyzer.py | 420 |
| **Core Infrastructure** | |
| commands.py | 387 |
| desktop.py | 264 |
| distro.py | 262 |
| hardware.py | 158 |
| packages.py | 379 |
| logger.py | 113 |
| **Helper & Scripts** | |
| tux-helper | 4,152 |
| install.sh | 800 |
| Other scripts | 984 |
| **TOTAL PYTHON** | **54,748** |
| **TOTAL WITH SCRIPTS** | **~60,000+** |

### File Counts
| Type | Count |
|------|-------|
| Python files | 43 |
| Shell scripts | 5 |
| Desktop entries | 6 |
| Icons (SVG) | 130+ |

### Method/Function Counts
| File | Methods/Functions |
|------|-------------------|
| app.py | 272 methods |
| setup_tools.py | 120+ methods |
| networking.py | 150+ methods |
| desktop_enhancements.py | 200+ methods |
| tux-helper | 60+ functions |
| **TOTAL** | **800+ functions/methods** |

### Class Counts
| Category | Count |
|----------|-------|
| Main application | 2 |
| Modules | 95+ |
| UI components | 12 |
| Tux Tunes | 8 |
| Core | 10 |
| **TOTAL** | **127+ classes** |

---

*This checkpoint document catalogs every feature of Tux Assistant v1.0.16 for use in the PyQt rewrite.*

*Last updated: December 23, 2025*
