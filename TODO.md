# Tux Assistant - Development Roadmap

**Goal:** Make Linux easier than Windows. So easy that 10-year-old Timmy has been a pro since he was 5.

**The Timmy Test:** For every feature, ask "Could a 10-year-old figure this out without asking an adult?"

---

## Priority 1: System Maintenance (NEW MODULE) ✅ IMPLEMENTED in v5.8.0

- [x] One-click system cleanup
  - [x] Package cache (pacman, apt, dnf, zypper)
  - [x] Old/orphaned packages (partial - manual for now)
  - [x] Journal logs (older than 7 days)
  - [x] Trash emptying
  - [x] Thumbnail cache
- [x] Update manager
  - [x] See available updates count
  - [x] One-click apply all
  - [ ] Update history (future)
  - [ ] Scheduled updates (future)
- [x] Startup apps manager
  - [x] List what runs at boot
  - [x] Enable/disable toggle
  - [ ] Add new startup apps (future)
- [x] Storage analyzer
  - [x] Disk usage display
  - [x] Launch external analyzer (baobab/filelight)
  - [ ] Built-in folder size breakdown (future)
- [ ] Battery/power management (laptops) - future
  - [ ] Power profiles
  - [ ] Battery health info

---

## Priority 2: Backup & Restore (NEW MODULE) ✅ IMPLEMENTED in v5.10.0

- [x] Simple file backup
  - [x] Select folders to backup
  - [x] Backup to USB/external drive
  - [x] Auto-detect removable drives
  - [x] Add custom folders
  - [x] rsync with progress
- [x] Timeshift integration
  - [x] Install if not present
  - [x] Create system snapshot
  - [x] Open Timeshift GUI
- [x] Backup tips section

---

## Priority 3: Gaming (NEW MODULE) ✅ IMPLEMENTED in v5.9.0

- [x] Steam installation
- [x] Lutris for non-Steam games
- [x] Heroic Games Launcher
- [x] Bottles (Wine manager)
- [x] GameMode (performance optimization)
- [x] MangoHud (FPS overlay)
- [x] ProtonUp-Qt (Proton version manager)
- [x] Controller info
- [x] Quick tips + ProtonDB link

---

## Priority 4: Hardware Manager (NEW MODULE) ✅ IMPLEMENTED in v5.11.0

- [x] Printer management
  - [x] List configured printers
  - [x] Start CUPS if not running
  - [x] Add printer (opens system tools)
- [x] Bluetooth management
  - [x] Power on/off toggle
  - [x] List paired devices
  - [x] Open system Bluetooth settings
- [x] Display info
  - [x] Show connected monitors
  - [x] Resolution and refresh rate
  - [x] Open display settings
- [x] Audio devices
  - [x] Switch output device
  - [x] Switch input device
  - [x] Set default with one click

---

## Priority 5: Networking Additions ✅ IMPLEMENTED in v5.12.0

- [x] WiFi management
  - [x] View WiFi status
  - [x] Open WiFi settings
  - [x] Hidden networks connection
- [x] VPN setup
  - [x] OpenVPN import (.ovpn files)
  - [x] WireGuard import (.conf files)
  - [x] Auto-install missing plugins
- [x] Hotspot creation
  - [x] Create hotspot with name/password
  - [x] Stop existing hotspot
- [x] Network speed test
  - [x] Uses speedtest-cli
  - [x] Offers to install if missing
- [x] Hosts file editor

---

## Priority 6: Help & Learning (NEW MODULE)

- [ ] Interactive tutorials
- [ ] "What is this?" mode
- [ ] Common tasks wizard
  - [ ] "I want to play a DVD"
  - [ ] "I want to connect to WiFi"
  - [ ] "I want to print something"
  - [ ] "My sound isn't working"
- [ ] Troubleshooter
  - [ ] Guided diagnosis
  - [ ] Common fixes

---

## Enhancements to Existing Modules

### Setup Tools
- [ ] Language/locale settings
- [ ] Keyboard layouts
- [ ] Time/date/timezone
- [ ] Default applications manager
- [ ] Font installation

### Software Center
- [ ] Flatpak/Snap preference toggle
- [ ] Installed apps list with uninstall
- [ ] App permissions viewer

### Desktop Enhancements
- [ ] Wallpaper manager (download, slideshow)
- [ ] Screen lock settings
- [ ] Accessibility options
  - [ ] Large text
  - [ ] High contrast
  - [ ] Screen reader setup

---

## Future Ideas

### Parental Controls
- [ ] Screen time limits
- [ ] App restrictions
- [ ] Web filtering
- [ ] Activity reports

---

## Completed ✓

- [x] Hardware info display on main page (v5.7.0)
- [x] Developer Tools with Git Manager (v5.7.0+)
- [x] Update from ZIP workflow (v5.7.6)
- [x] Developer Kit export/import (v5.7.0)
- [x] "How to Update" guide (v5.7.14)
- [x] Documentation structure (v5.7.15)
- [x] Getting Started button (v5.7.15)
- [x] Back buttons on all pages (v5.7.17)

---

*Last updated: 2025-11-30*
