# Changelog

All notable changes to Tux Assistant will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [5.10.1] - 2025-11-30

### Fixed - Missing Dependencies Handled
- Backup: rsync check and install dialog before backup starts
- System Maintenance: Arch package cache cleaning works without pacman-contrib
- System Maintenance: Arch update check works without checkupdates (falls back to pacman -Qu)

## [5.10.0] - 2025-11-30

### Added - Backup & Restore Module (NEW!)
Simple file backup and system snapshot management:

**File Backup**
- Auto-detects external/removable drives
- Select folders to backup (Documents, Pictures, Music, Videos, Desktop)
- Add custom folders
- Uses rsync for reliable copying with progress
- Creates timestamped backup folders

**System Snapshots (Timeshift)**
- Install Timeshift if not present
- Create snapshots with one click
- Open Timeshift GUI for full management

**Backup Tips**
- 3-2-1 rule reminder
- Best practices guidance

## [5.9.1] - 2025-11-30

### Fixed - Disk Analyzer Installation
- "Analyze" button now offers to install baobab or filelight if none found
- Shows dialog with GNOME or KDE option
- Installs via proper package manager for each distro family

## [5.9.0] - 2025-11-30

### Added - Gaming Module (NEW!)
A simple, safe gaming setup module:

**Gaming Readiness**
- 32-bit library support check
- Vulkan support check

**Gaming Platforms**
- Steam (with Proton for Windows games)
- Lutris (for GOG, Epic, Origin games)
- Heroic Games Launcher (Epic/GOG alternative)
- Bottles (Wine manager for Windows apps)

**Gaming Utilities**
- GameMode (automatic performance optimization)
- MangoHud (FPS/stats overlay)
- ProtonUp-Qt (manage Proton versions)

**Controller Support**
- Info about Xbox/PlayStation controller compatibility

**Quick Tips**
- Guidance on Steam Play/Proton
- Link to ProtonDB for game compatibility

Each app shows Install or Launch button based on status.
Supports native packages and Flatpak fallback.

## [5.8.2] - 2025-11-30

### Fixed - System Maintenance Page Crash
- Fixed AdwPreferencesGroup row removal causing critical errors
- Startup apps section now properly tracks and removes rows
- Page loads and displays correctly now

## [5.8.1] - 2025-11-30

### Fixed - Crash on Launch
- Added missing `id` parameter to System Maintenance module registration
- App now launches correctly

## [5.8.0] - 2025-11-30

### Added - System Maintenance Module (NEW!)
A complete system maintenance toolkit for keeping your Linux healthy:

**System Cleanup**
- Package cache cleaning (pacman, apt, dnf, zypper)
- Application cache cleanup
- Thumbnail cache clearing
- System log rotation (keeps last 7 days)
- Trash emptying
- "Clean All" one-click option with total size display

**System Updates**
- Check for available updates
- One-click update in terminal
- Shows update count

**Startup Applications**
- See all apps that run at login
- Enable/disable with toggle switches
- Works with user and system autostart entries

**Storage Overview**
- Disk usage display
- Launch disk analyzer (baobab, filelight, etc.)

### Changed
- New category "System and Maintenance" appears first in menu
- Reorganized module categories for better flow

## [5.7.17] - 2025-11-30

### Fixed - Removed Duplicate Back Buttons
- Oops! NavigationView already adds back buttons automatically
- Removed the manual ones I added (double back buttons LOL)
- Now just ONE back button per page, as intended

## [5.7.16] - 2025-11-30

### Fixed - Back Button on All Module Pages!
- Added back arrow (←) button to ALL module pages
- No more getting stuck in a module
- Works on:
  - Developer Tools
  - Setup Tools
  - Software Center
  - Networking
  - Desktop Enhancements
  - Media Server
  - Nextcloud
  - Tux Tunes

## [5.7.15] - 2025-11-30

### Added - Documentation
- Created `docs/` folder with full documentation structure
- **README.md**: Overview and navigation
- **getting-started.md**: Installation, first launch, orientation
- **developer-tools.md**: Complete Git workflow guide (detailed)
- Placeholder docs for all other modules (to be expanded)

### Added - "Getting Started" Button
- New button in header bar (next to version number)
- Opens quick reference dialog
- Covers all main sections at a glance
- Always accessible from the main page

## [5.7.14] - 2025-11-29

### Added - "How to Update" Help Button
- New "How to Update" button in Git Projects header
- Opens dialog with step-by-step workflow guide
- Covers: Update from ZIP → Push → Install to System → Restart
- No more guessing the workflow!

## [5.7.13] - 2025-11-29

### Improved - Better Update Workflow
- "Install to System" button now in project row (expand to see it)
- Button only appears for projects with install.sh
- Update from ZIP dialog now shows clear next steps:
  1. Click "← Back to Push"
  2. Click Push button
  3. Expand project → Click "Install to System"
- Logical flow: Update files → Push to git → Install to system

## [5.7.12] - 2025-11-29

### Fixed - Version Display Sync
- About dialog and header now read from VERSION file
- No more hardcoded version in __init__.py
- Version updates automatically propagate everywhere

## [5.7.11] - 2025-11-29

### Improved - Update from ZIP Workflow
- After update completes, "Update Project" button changes to "← Back to Push"
- New "Install to System" button appears after update
- "Install to System" opens terminal and runs `sudo bash install.sh`
- No more confusion about next steps - clear buttons guide you through!

### Full Workflow Now:
1. Download ZIP → Update from ZIP → Click "Update Project"
2. Click "← Back to Push" → Click Push button → Enter passphrase
3. Click "Update from ZIP" again → Click "Install to System" → Enter sudo password
4. Restart app from menu → Running new version!

## [5.7.10] - 2025-11-29

### Added - Version Display
- Version number now shown in header bar (top left)
- Quick visual confirmation of which version you're running
- About dialog still available via hamburger menu

## [5.7.9] - 2025-11-29

### Fixed - Auto-fix Execute Permissions
- Update from ZIP now automatically runs chmod +x on:
  - install.sh
  - tux-helper
  - tux-assistant.py
- No more "command not found" errors after extracting ZIPs
- Status shows "✓ Fixed execute permissions" 

## [5.7.8] - 2025-11-29

### Fixed - hardinfo2 Installation via Terminal
- hardinfo2 install now opens a terminal window (like git push/pull)
- User can see progress, enter sudo password, and confirm prompts
- Works across all supported distros (Arch, Debian, Fedora, openSUSE)
- For Arch: Automatically installs yay AUR helper if needed
- UI updates automatically when installation completes

## [5.7.7] - 2025-11-29

### Improved - Clearer Push/Pull Buttons
- Buttons now show "↓ Pull" and "↑ Push" with labels
- No longer look like minimize/maximize window buttons
- Better tooltips explaining what each does
- More spacing between buttons

## [5.7.6] - 2025-11-29

### Changed - Terminal for Git Operations
- Push and Pull now open a terminal window
- User can see the passphrase prompt and enter it
- Terminal shows clear success/failure message
- "Press Enter to close..." keeps terminal open so you see the result
- Works with: Konsole, GNOME Terminal, XFCE Terminal, Tilix, Alacritty, Kitty

### Why?
SSH passphrase prompts can't be captured by the GUI. Opening a terminal window lets you:
1. See exactly what git is doing
2. Enter your passphrase when prompted
3. See success/failure clearly

## [5.7.5] - 2025-11-29

### Fixed
- Fixed CommitPushDialog signal error (same issue as UpdateFromZipDialog)
- Push button now properly shows commit message dialog

## [5.7.4] - 2025-11-29

### Fixed
- Fixed markup error with email display (using parentheses instead of angle brackets)
- Fixed "Drag & drop" ampersand causing markup parse error
- Fixed UpdateFromZipDialog signal error (Adw.Dialog doesn't support response signal)
- Changed to callback pattern for dialog completion

## [5.7.3] - 2025-11-29

### Added - Update from ZIP 🎉
- **One-click project updates** - No more terminal commands for updating projects!
- New "Update Project from ZIP" in Other Git Tools
- Step-by-step wizard:
  1. Select downloaded ZIP file (defaults to ~/Downloads)
  2. Select target project from your list
  3. Click Update - safely replaces files while preserving .git
- Status updates during the process
- Automatic git status check after update
- Shows how many files changed

### How It Works
1. Download ZIP from Claude (or wherever)
2. Open Developer Tools → Update Project from ZIP
3. Browse to ZIP, select your project
4. Click Update
5. Project files replaced, .git preserved
6. Click Push button to commit and push!

### Safe By Design
- Verifies .git folder exists before touching anything
- Extracts to temp directory first
- Only removes non-.git files
- Handles nested folders in ZIP automatically

## [5.7.2] - 2025-11-29

### Added - Developer Kit & Improved Onboarding
- **Developer Kit Export** - Save SSH keys, Git identity, and project list to USB/folder
- **Developer Kit Import** - Restore dev setup on fresh installs with one click
- **Improved empty state** - When no projects found, shows:
  - Scanned directories status (✓/✗)
  - "Clone a Repository" button
  - "Create ~/Development Folder" button (if missing)
  - "Import Developer Kit" button (if SSH keys missing)
  - "Add Manually (Advanced)" option
- Warning on export: "Keep this safe - contains your SSH keys!"
- Skip existing keys on import (won't overwrite)

### Changed
- Empty state dynamically rebuilds based on current system state
- Scan complete message improved for empty results

### The Safe Workflow
1. First machine: Set up git, export Developer Kit to USB
2. Fresh install: Import Developer Kit from USB
3. Clone your repos, push/pull with one click
4. Keys stay on USB, not in the app or git history

## [5.7.1] - 2025-11-29

### Added - Git Manager 🚀
- **One-click Pull/Push** - Manage git repos without touching the terminal
- **Project scanning** - Auto-detect git repos in ~/Development, ~/Projects, etc.
- **Manual project add** - For advanced users with repos in custom locations
- **Prerequisites check** - Shows SSH key and Git identity status with setup buttons
- **Project status display** - Shows branch, uncommitted changes, ahead/behind counts
- **Commit message dialog** - Enter commit message before pushing changes
- **Expandable project rows** - See path, remote URL, last commit
- **Quick actions** - Open folder, open terminal, remove from list
- **Git identity configuration** - Set name/email from the UI

### Features
- Scan button finds all git repos in common directories
- Push button disabled when nothing to push (smart guardrails)
- Pull/Push blocked if SSH keys not set up (with link to setup)
- Project list persisted to config file

## [5.7.0] - 2025-11-29

### Added
- **Hardware Information row** on front page showing CPU, RAM summary
- **hardinfo2 integration** - Install with one click, launches detailed hardware viewer
- **Smart pre-wiring** - Installing hardinfo2 on Arch sets up AUR helper (yay) automatically
- **Developer Tools** promoted to front-page category (no longer buried in Setup Tools)
- New `tux/core/hardware.py` module for hardware detection
- New `tux/modules/developer_tools.py` as standalone module
- `DEVELOPER` category added to ModuleCategory enum

### Changed
- Developer Tools (Git Clone, SSH Key Restore) now accessible from main menu
- Hardware row shows "Install hardinfo2 (Recommended)" button for first-time users
- After hardinfo2 install, button changes to launcher

### Technical
- Infrastructure prep: AUR helper installation benefits future AUR package installs
- Graceful fallback: Basic hardware info from /proc when hardinfo2 unavailable

## [5.6.4] - 2025-11-29

### Added
- Delete button (trash icon) for custom stations with confirmation dialog
- Custom stations now show: Edit (pencil) | Delete (trash) | Play

### Changed
- Favorite star button hidden for custom stations (delete button replaces it)
- Clearer UX: custom stations have distinct management controls

## [5.6.3] - 2025-11-29

### Added
- Edit button for custom stations (pencil icon appears only on user-added stations)
- EditStationDialog for modifying custom station name, URL, and genre
- `update_favorite()` method in library for in-place station updates

### Changed
- Custom stations now clearly editable - users don't have to delete and re-add to fix URLs

## [5.6.2] - 2025-11-29

### Fixed
- Fixed Add Custom Station dialog not opening (Adw.Dialog doesn't support emit("response"))
- Changed dialog to use callback pattern for GTK4/libadwaita compatibility

### Added
- Auto-save recordings feature with first-run prompt
- One-time dialog asks user preference: "Auto-Save" or "Ask Each Time"
- Auto-saved recordings show brief 2-second confirmation toast
- Preference accessible anytime in Preferences → Recording → Recording Mode

### Changed
- Recording mode option renamed from "Save all tracks" to "Auto-save all tracks"
- Internal config uses 'auto' instead of 'all' for clarity

## [5.5.9] - 2025-11-29

### Fixed
- Fixed application icons not showing in taskbar/dock (Wayland/GTK4 compatibility)
- Fixed StartupWMClass matching for both Tux Assistant and Tux Tunes

### Added
- Audio analysis dependencies for smart recording (numpy, scipy, librosa, pydub)
- Automatic dependency installation via Tux Assistant UI
- Auto-refresh after dependency installation
- Grace period for initial track metadata settling
- 15-second save prompt for completed recordings

## [5.3.2] - 2025-11-29

### Fixed - Tux Tunes Now Visible! 📻

**The Bug:** Tux Tunes module wasn't showing in the main menu because:
1. Missing `MEDIA` category in ModuleCategory enum
2. Module not imported in `__init__.py`
3. Module using wrong registration pattern

**Fixed:**
- Added `ModuleCategory.MEDIA = "Media and Entertainment"`
- Added `from . import tux_tunes` to modules/__init__.py
- Rewrote module to use `@register_module` decorator
- Added `media_server` and `nextcloud_setup` imports too (were missing!)

**Now Shows:**
```
Media and Entertainment
├── Tux Tunes          ← NEW! 📻
│   Internet radio with smart song recording

Server and Cloud
├── Nextcloud Server
├── Media Server
```

**Module Features:**
- Status check for GStreamer dependencies
- One-click dependency installation
- Launch Tux Tunes button
- Create desktop shortcut button
- Feature list with descriptions

---

## [5.3.1] - 2025-11-29

### Enhanced - Tux Tunes Features 📻

**Genre Browsing with Pill Buttons:**
- 24 popular genres as clickable pills
- Tap any genre to see matching stations
- Genres include: Rock, Pop, Jazz, Classical, Electronic, Hip Hop, Country, Blues, Metal, Alternative, Indie, R&B, Reggae, Folk, Latin, 80s, 90s, Oldies, News, Talk, Sports, Ambient, Chill, Dance

**Add Custom Stations:**
- New "+" button in header bar
- Enter: Station name, Stream URL, Genre (optional)
- Validates URL format (http:// or https://)
- Custom stations saved to favorites
- Supports: MP3, AAC, OGG streams

**Live Search:**
- Search starts after 2 characters
- Results update as you type
- Press Enter for immediate search

**Keyboard Shortcuts:**
- Ctrl+F: Toggle search
- Space: Play/Pause

**UI Improvements:**
- Separate tabs: Favorites, Browse (genres + popular), Search, Recent
- Now Playing bar shows current station with favorite toggle
- Genre pills in Browse view for quick filtering
- Loading spinners for async operations

---

## [5.3.0] - 2025-11-29

### Added - 🎵 Tux Tunes Internet Radio Player!

**A brand new app built into Tux Assistant!**

Tux Tunes is a GTK4/Libadwaita internet radio player that fixes the recording problems found in Shortwave and other radio apps.

**Features:**
- 📻 Access to 50,000+ stations via radio-browser.info
- 🎵 Smart Recording with pre/post buffering (captures FULL songs!)
- ⭐ Favorites library
- 🕐 Recent stations history
- 🔍 Search by name, country, or genre
- 🔊 Volume control with memory
- 📝 Track metadata display

**The Key Innovation - Smart Recording:**
```
Problem: Other apps cut off song beginnings/endings
Solution: 
- Pre-buffer: Keeps last 8 seconds in memory
- Post-buffer: Records 3 seconds after metadata change
- Result: Complete songs every time!
```

**Architecture:**
- Self-contained in `tux/apps/tux_tunes/`
- Can be split off as standalone app later
- Integrates via module in Tux Assistant
- Creates `.desktop` file for app menu

**Files Added:**
- `tux/apps/tux_tunes/__init__.py` - Package info
- `tux/apps/tux_tunes/api.py` - radio-browser.info client
- `tux/apps/tux_tunes/library.py` - Favorites & config
- `tux/apps/tux_tunes/player.py` - GStreamer playback + smart recording
- `tux/apps/tux_tunes/window.py` - GTK4 UI
- `tux/apps/tux_tunes/app.py` - Application class
- `tux/apps/tux_tunes/tux-tunes.py` - Standalone launcher
- `tux/modules/tux_tunes.py` - Tux Assistant integration module

---

## [5.2.6] - 2025-11-29

### Added - Remember Window Size

The app now remembers your preferred window size between sessions!

**How it works:**
- When you resize the window, the new size is saved automatically
- When you maximize, that state is saved too
- Next launch restores your preferred size

**Technical details:**
- Config saved to: `~/.config/tux-assistant/window.conf`
- Saves: width, height, maximized state
- Minimum size enforced: 800x600
- Maximum size enforced: 3000x2000
- Doesn't save while minimized/hidden (prevents saving bad sizes)

**Example config file:**
```
width=1400
height=900
maximized=false
```

No more resizing every time you launch! 🎉

---

## [5.2.5] - 2025-11-29

### Added - UX Improvements

**Software Center - Search in Categories**
- Each category page now has a search box at the top
- Type to filter apps in the current category
- Placeholder text: "Search for other apps..."
- Live filtering as you type

**Networking - Reordered Sections**
- "File Sharing (Samba)" section now comes FIRST
- Quick Share is now immediately accessible when entering Networking
- Network Discovery (scans) moved below File Sharing
- Makes the most common task (sharing a folder) easier to find

**Before:**
1. Network Discovery (scans)
2. File Sharing (Samba) ← Quick Share buried here
3. Active Directory
4. Firewall

**After:**
1. File Sharing (Samba) ← Quick Share right at top!
2. Network Discovery (scans)
3. Active Directory
4. Firewall

---

## [5.2.4] - 2025-11-29

### Fixed - Grandpa-Friendly Error Messages 👴

**The Problem:** Backup step failed on fresh installs (no smb.conf exists), showing scary "Failed: 1" message even though everything actually worked.

**The Solution:** Smart backup that doesn't scare Grandpa!

```bash
# Before (scary failure on fresh install):
cp /etc/samba/smb.conf /etc/samba/smb.conf.bak-...
# ERROR! File not found! FAILED! 😱

# After (graceful handling):
[ -f /etc/samba/smb.conf ] && cp ... || echo 'No existing config to backup (fresh install)'
# OK! Nothing to backup, that's fine! ✅
```

**Changes:**
- `create_share_plan()`: Conditional backup + ensures smb.conf exists
- `create_delete_share_plan()`: Conditional backup
- `create_modify_share_plan()`: Conditional backup

**Result:** All tasks succeed, Grandpa is happy, fist remains unshaken! 👴✨

---

## [5.2.3] - 2025-11-29

### Fixed

**Samba password task not executing**

- Bug: Was doing `plan.append()` instead of `plan['tasks'].append()`
- Result: Password command was added to wrong place, dialog didn't appear
- Also added: Password escaping for special characters

---

## [5.2.2] - 2025-11-29

### Added - Samba Password Setup (Grandpa-Friendly!) 👴

**The Problem:** When creating a Samba share without guest access, users couldn't connect because they had no Samba password set. Grandpa was shaking his fist!

**The Solution:** Quick Share dialog now includes password fields:

- When "Guest Access" is OFF, password fields appear
- Password + Confirm Password entries
- Real-time validation:
  - ⚠ Passwords do not match (red)
  - ⚠ Password is too short (yellow)
  - ✓ Passwords match (green)
- Minimum 4 character password
- Automatically runs `smbpasswd -a` as part of share setup

**Now the flow is:**
1. Pick folder
2. Set share name  
3. Choose options (writable, guest)
4. **If not guest → enter password** ← NEW!
5. Click Share
6. **Everything works!** ✨

No more terminal commands for Grandpa! 🎉

---

## [5.2.1] - 2025-11-29

### Fixed

**Critical: tux-helper not found**

- Install script wasn't creating symlink for `tux-helper` in `/usr/bin/`
- Code looks for `/usr/bin/tux-helper` for pkexec operations
- Helper was only in `/opt/tux-assistant/tux-helper`
- **Result:** Samba setup, software installs, and other privileged operations failed

**Fix:**
- Install script now creates: `ln -sf /opt/tux-assistant/tux-helper /usr/bin/tux-helper`
- Uninstall script now removes the symlink

**Workaround for v5.2.0 users:**
```bash
sudo ln -s /opt/tux-assistant/tux-helper /usr/bin/tux-helper
```

---

## [5.2.0] - 2025-11-28

### Added - Enhanced Network Scan Progress

Network scans now show detailed progress information so you know exactly what's happening!

#### New Progress UI

```
╔════════════════════════════════════════════════════════════╗
║  🔍 Scanning Network                                       ║
║                                                            ║
║  ████████████░░░░░░░░░░░░░░░░░░░░░░  47%                  ║
║                                                            ║
║  Elapsed: 1:45 | Checked: 119 of 254 | Found: 3 | ETA: ~2:00║
║                                                            ║
║  ┌──────────────────────────────────────────────────────┐  ║
║  │  💡 Fun fact rotating here...                        │  ║
║  └──────────────────────────────────────────────────────┘  ║
╚════════════════════════════════════════════════════════════╝
```

#### Features
- **Progress bar** with percentage
- **Elapsed time** counter
- **IP addresses checked** (X of 254)
- **Devices found** so far
- **Estimated time remaining** (calculated from rolling average)

#### Technical Changes
- `NetworkScanner.scan_for_shares()` now accepts optional `progress_callback`
- `_scan_smb_hosts()` and `_scan_all_hosts()` report per-IP progress
- ETA calculated using rolling average of last 20 IP scan times
- Works with both nmap and fallback ping sweep methods

#### Note on nmap
When nmap is available, it handles the scan more efficiently but doesn't provide per-IP progress (it's faster though!). The progress bar will pulse during nmap scans, then show detailed progress when checking shares.

---

## [5.1.3] - 2025-11-28

### Fixed

**GTK4 API Fix**
- `Gtk.Label` doesn't have `set_line_wrap_mode()` - it's `set_wrap_mode()`
- Also requires `Pango.WrapMode` instead of `Gtk.WrapMode`
- Added missing Pango import

---

## [5.1.2] - 2025-11-28

### Fixed

**Critical Fix: Module Loading Completely Broken**

- `registry.py` was still using `package='ltk.modules'` instead of `package='tux.modules'`
- This caused ALL modules to fail to load with "No module named 'ltk'" errors
- Modules appeared in sidebar but clicking them did nothing
- Now properly uses `tux.modules` package name

**Lesson learned:** Always grep for the old name after a rebrand! 🤦

---

## [5.1.1] - 2025-11-28

### Fixed

**Thanks to ChatGPT for the code review!** 🤝

#### Helper Tag Mismatch (Critical)
- Fixed: `tux-helper` was still outputting `[LTK:PROGRESS]` and `[LTK:STATUS]` tags
- Now correctly outputs `[Tux Assistant:PROGRESS]` and `[Tux Assistant:STATUS]`
- This was causing progress bars to appear frozen during operations

#### Fun Facts Not Displaying
- Fixed: `RotatingFunFactWidget` wasn't starting rotation properly
- Changed from `do_realize()` override to proper GTK4 signal connections
- Now uses `map` and `unmap` signals for start/stop rotation
- Fun facts now display correctly during network scans!

---

## [5.1.0] - 2025-11-28

### Added - Fun Facts While You Wait! 🎉

**"Well done, not medium rare"** - Christopher

Network scans taking forever? Now you'll be entertained AND educated while you wait!

#### New Feature: Rotating Fun Facts

When performing slow operations like network scans, Tux Assistant now displays:
- **App Feature Facts** - Learn what Tux Assistant can do (12 facts)
- **Linux Myth Busters** - Common myths debunked with facts (12 facts)
- **Distro Unity Facts** - How Tux Assistant unites Linux distros (8 facts)
- **Linux History** - Fun historical tidbits (9 facts)
- **Linux Fun Facts** - Did you know? (14 facts)
- **Tux Tips** - Helpful tips for using the app (6 facts)

**Total: 61 rotating facts!**

#### What You'll See

```
╔════════════════════════════════════════════╗
║  🔍 Scanning network...                    ║
║                                            ║
║  This may take several minutes.            ║
║  Please be patient!                        ║
║                                            ║
║  ┌────────────────────────────────────┐    ║
║  │  🚀 Did You Know?                  │    ║
║  │                                    │    ║
║  │  NASA's Ingenuity helicopter on    │    ║
║  │  Mars runs Linux. The penguin has  │    ║
║  │  conquered another planet!         │    ║
║  └────────────────────────────────────┘    ║
╚════════════════════════════════════════════╝
```

Facts rotate every 8 seconds and never repeat until all have been shown!

#### User-Extensible

Add your own facts in `~/.config/tux-assistant/fun_facts.json`:
```json
{
  "facts": [
    {
      "category": "linux_fun",
      "content": "Your custom fact here!",
      "icon": "🎯"
    }
  ]
}
```

#### New Files
- `tux/ui/fun_facts.py` (~650 lines)
  - `FunFact` dataclass
  - `FunFactsManager` - manages fact rotation
  - `FunFactBox` - displays a single fact
  - `RotatingFunFactWidget` - auto-rotating fact display
  - `LongOperationDialog` - reusable dialog for slow operations

#### Integration
- Network Scan page now shows fun facts during scans
- Reusable for any future slow operations

---

## [5.0.0] - 2025-11-28

### 🐧 Rebranded to Tux Assistant!

**Linux Toolkit is now Tux Assistant** - a fresh name for a fresh start.

#### Changes
- Renamed project from "Linux Toolkit" to "Tux Assistant"
- New app ID: `com.tuxassistant.app`
- New binary names: `tux-assistant`, `tux-helper`
- New package directory: `tux/`
- Version bump to 5.0.0 to mark the rebrand

#### Why the Change?
- More memorable and catchy name
- Tux the penguin is the universal Linux mascot
- "Assistant" conveys the helpful, supportive nature of the app
- Better branding potential for the future

#### Migration
If upgrading from Linux Toolkit:
1. Uninstall the old version
2. Install Tux Assistant fresh
3. Your system settings are unchanged

---

## [4.10.0] - 2025-11-28

### Added - Media Server Setup Module 🎬

**"You will move it double quick time!"** - Gunnery Sergeant Hartman

Full setup and drive configuration for Plex, Jellyfin, and Emby media servers.

#### Features

**Install Media Servers:**
- Plex Media Server (with official repo setup)
- Jellyfin (free & open-source)
- Emby Server

**Configure Drives:**
- Auto-detect external/secondary drives via `lsblk`
- Add drives to `/etc/fstab` with proper mount options (`nosuid,nodev,nofail`)
- Create mount points at `/media/$USER/<label>`
- Set permissions for media server user/group
- Configure ACLs for seamless access

**Configure Folders:**
- Select specific media folders
- Recursive permission setting (`chmod -R +rwX`)
- ACL configuration for media server group

**Server Management:**
- Start/stop service
- View service status
- Open web interface

#### UI Flow

```
┌─────────────────────────────────────────┐
│  🎬 Media Server Setup                  │
├─────────────────────────────────────────┤
│  Install Media Server                   │
│  ├── Plex Media Server              →   │
│  ├── Jellyfin                       →   │
│  └── Emby Server                    →   │
├─────────────────────────────────────────┤
│  Configure Drives                       │
│  ├── Configure Drive for Media      →   │
│  └── Configure Media Folder         →   │
├─────────────────────────────────────────┤
│  Manage Server (if installed)           │
│  ├── Service Status: [Running]          │
│  ├── Start/Stop Server                  │
│  └── Open Web Interface             →   │
└─────────────────────────────────────────┘
```

#### Drive Configuration Dialog

```
┌─────────────────────────────────────────┐
│  Select Drives                          │
│  ┌───────────────────────────────────┐  │
│  │ [x] Seagate 4TB (4T)              │  │
│  │     /dev/sdb1 • ext4              │  │
│  ├───────────────────────────────────┤  │
│  │ [ ] WD Elements 2TB (2T)          │  │
│  │     /dev/sdc1 • ntfs              │  │
│  └───────────────────────────────────┘  │
│                                         │
│  What This Does:                        │
│  ✓ Add drive to /etc/fstab              │
│  ✓ Create mount point in /media/$USER/  │
│  ✓ Set read permissions                 │
│  ✓ Configure ACL for media server       │
│                                         │
│       [Configure Selected Drives]       │
└─────────────────────────────────────────┘
```

#### Technical Details

**Media Server Definitions:**

| Server | Service | User/Group | Port |
|--------|---------|------------|------|
| Plex | plexmediaserver | plex | 32400 |
| Jellyfin | jellyfin | jellyfin | 8096 |
| Emby | emby-server | emby | 8096 |

**Drive Detection:**
- Uses `lsblk -J` for JSON output
- Filters out system partitions (/, /boot, /home)
- Filters out small partitions (<10GB)
- Detects: device, label, UUID, fstype, size, mountpoint, model

**Mount Point Strategy:**
- Uses `/media/$USER/<label>` consistently
- Works regardless of udisks2 configuration
- fstab entry overrides desktop auto-mount behavior

**Permission Commands:**
```bash
# Base directory
sudo chmod go+rx /media/$USER
sudo setfacl -m g:plex:rx /media/$USER

# Each drive
sudo chmod go+rx /media/$USER/<drive>
sudo setfacl -m g:plex:rx /media/$USER/<drive>

# Media folders (recursive)
sudo chmod -R +rwX /media/$USER/<drive>/<folder>
sudo setfacl -R -m g:plex:rx /media/$USER/<drive>/<folder>
```

#### New File

**ltk/modules/media_server.py** (~950 lines):
- `MediaServer` enum (PLEX, JELLYFIN, EMBY)
- `MediaServerInfo` dataclass
- `DriveInfo` dataclass
- `detect_drives()` function
- `detect_installed_media_server()` function
- `MediaServerPage` - main module page
- `InstallServerDialog` - server installation wizard
- `InstallProgressDialog` - installation progress
- `ConfigureDriveDialog` - drive selection and configuration
- `DriveConfigProgressDialog` - drive configuration progress
- `ConfigureFolderDialog` - folder permission configuration

---

## [4.9.2] - 2025-11-28

### Added - MATE Desktop Support 🐕🐕

**The puppy found a mate!**

MATE desktop now has full enhancement support, completing the GTK-based desktop trifecta (GNOME, Cinnamon, MATE).

#### New Components

**MATE_APPLETS** - 6 panel applets:
- Sensors Applet (hardware monitoring)
- Netspeed Applet (network monitor)
- Dock Applet (application dock)
- Brisk Menu (modern app menu)
- Indicator Applet (app indicators)
- Media Applet (volume control)

**MATE_TWEAKS** - 10 toggle settings:
- Compositing Manager (Marco effects)
- Window Animations
- Show Desktop Icons
- Show Trash on Desktop
- Show Home on Desktop
- Show Computer on Desktop
- Center New Windows
- Edge Tiling
- Show Hidden Files (Caja)
- Show Thumbnails (Caja)

**MATE_TOOLS** - 9 utilities:
- MATE Tweak (advanced customization)
- Caja File Manager
- Caja Extensions
- Pluma Text Editor
- Atril Document Viewer
- Engrampa Archive Manager
- Eye of MATE (image viewer)
- MATE Calculator
- MATE System Monitor

#### Theme Application

GTK themes, icon themes, and cursor themes can now be applied on MATE via:
- `org.mate.interface` (GTK/icons)
- `org.mate.peripherals-mouse` (cursor)

#### Desktop Support Summary

| Desktop | Applets/Widgets | Extensions | Tweaks | Tools |
|---------|-----------------|------------|--------|-------|
| GNOME | - | ✅ | ✅ | ✅ |
| KDE | ✅ | - | ✅ | ✅ |
| XFCE | ✅ | - | ✅ | ✅ |
| Cinnamon | ✅ | ✅ | ✅ | ✅ |
| **MATE** | ✅ | - | ✅ | ✅ |

---

## [4.9.1] - 2025-11-28

### Added - Cinnamon Desktop Support 🐕

**The puppy has been saved from the cold!**

Cinnamon now joins GNOME, KDE, and XFCE with full desktop enhancement support.

#### New Components

**CINNAMON_APPLETS** - 6 panel applets:
- Weather Applet
- Calendar Applet
- Removable Drives
- System Monitor
- Workspace Switcher
- Timer Applet

**CINNAMON_EXTENSIONS** - 4 desktop extensions:
- Transparent Panels
- Blur Overview
- Workspace Grid
- gTile (window tiling)

**CINNAMON_TWEAKS** - 10 toggle settings:
- Desktop Effects
- Startup Animation
- Workspace OSD
- Panel Auto-hide
- Hot Corner
- Snap OSD
- Window Animations
- Show Desktop Icons
- Natural Scrolling
- Edge Tiling

**CINNAMON_TOOLS** - 6 utilities:
- Cinnamon Settings
- Nemo File Manager
- Nemo Extensions Pack
- Cinnamon Screensaver
- Mint Themes Collection
- Control Center

#### Theme Application

GTK themes, icon themes, and cursor themes can now be applied on Cinnamon via:
- `org.cinnamon.desktop.interface` gsettings schema

#### UI Integration

When running on Cinnamon desktop:
```
┌─────────────────────────────────────────┐
│ 🖥️  Desktop Environment                │
│ Cinnamon on X11                         │
├─────────────────────────────────────────┤
│ 📦 Cinnamon Applets                     │
│    6 applets available               →  │
├─────────────────────────────────────────┤
│ 🧩 Cinnamon Extensions                  │
│    4 extensions available            →  │
├─────────────────────────────────────────┤
│ 🔧 Cinnamon Tools                       │
│    6 tools available                 →  │
├─────────────────────────────────────────┤
│ ⚙️  Cinnamon Tweaks                     │
│    [x] Desktop Effects                  │
│    [x] Window Animations                │
│    [ ] Panel Auto-hide                  │
│    ... (10 toggles)                     │
└─────────────────────────────────────────┘
```

#### Files Modified

**desktop_enhancements.py** (now ~4,650 lines):
- Added CINNAMON_APPLETS list
- Added CINNAMON_EXTENSIONS list
- Added CINNAMON_TWEAKS list
- Added CINNAMON_TOOLS list
- Added `_create_cinnamon_section()` method
- Added Cinnamon handlers: `on_cinnamon_applets()`, `on_cinnamon_extensions()`, `on_cinnamon_tools()`
- Updated `apply_gtk_theme()` for Cinnamon
- Updated `apply_icon_theme()` for Cinnamon
- Updated `apply_cursor_theme()` for Cinnamon
- Updated docstring to mention Cinnamon

---

## [4.9.0] - 2025-11-28

### Added - Nextcloud Server Setup 🌩️

**Replace Google Drive with your own personal cloud!**

New module: "Nextcloud Server" - A complete self-hosted cloud solution with a 5-field setup wizard.

#### What It Does

Timmy can now help Grandpa set up his own cloud server:

```
┌─────────────────────────────────────────────────────────┐
│           NEXTCLOUD SETUP WIZARD                        │
├─────────────────────────────────────────────────────────┤
│  Admin username:     [grandpa            ]              │
│  Admin password:     [••••••••••••       ]              │
│                                                         │
│  Data storage:       [/mnt/bigdrive/cloud   ] [Browse]  │
│                                                         │
│  DuckDNS subdomain:  [grandpas-cloud     ].duckdns.org  │
│  DuckDNS token:      [xxxxxxxx-xxxx-xxxx ]              │
│                                                         │
│                    [Install Nextcloud]                  │
└─────────────────────────────────────────────────────────┘
```

Click one button, enter your password, and the toolkit:

1. **Installs packages** - Apache, PHP 8.x, MariaDB, Redis, Certbot
2. **Sets up database** - Creates Nextcloud DB and user
3. **Downloads Nextcloud** - Latest stable release
4. **Configures everything** - Data directory, permissions, occ installer
5. **Sets up Apache** - Virtual host, modules, HTTPS redirect
6. **Obtains SSL cert** - Let's Encrypt automatic HTTPS
7. **Configures DuckDNS** - Auto-updates when your IP changes
8. **Finalizes** - Redis caching, cron jobs, firewall rules

#### Dynamic DNS (The Magic Part)

Your ISP changes your IP? No problem:
- DuckDNS updates every 5 minutes automatically
- Your `grandpas-cloud.duckdns.org` always points to the right IP
- SSL certificate is tied to domain name, not IP

#### What You Get

| Feature | Replaces |
|---------|----------|
| File Sync | Google Drive |
| Calendar | Google Calendar (optional app) |
| Contacts | Google Contacts (optional app) |
| Notes | Google Keep (optional app) |
| Photos | Google Photos (optional app) |

#### Requirements

- A DuckDNS account (free, 30 seconds to create)
- Storage space (local drive or mounted)
- Ports 80/443 forwarded on your router

#### Technical Implementation

**New Files:**
- `ltk/modules/nextcloud_setup.py` (~800 lines)
  - `NextcloudSetupWizard` - 5-field configuration dialog
  - `NextcloudInstallDialog` - Progress tracking with 8 steps
  - `NextcloudSetupPage` - Main module page with features list

**tux-helper additions** (~500 lines):
- `--nextcloud-install PLAN_FILE` argument
- `install_nextcloud()` - Main orchestrator
- `nc_install_packages()` - Cross-distro package installation
- `nc_setup_database()` - MariaDB setup
- `nc_download_nextcloud()` - Download and extract
- `nc_configure_nextcloud()` - Run occ installer
- `nc_configure_apache()` - Virtual host and modules
- `nc_setup_ssl()` - Let's Encrypt via certbot
- `nc_setup_duckdns()` - Dynamic DNS cron job
- `nc_finalize()` - Redis, cron, firewall

**Registry:**
- Added `ModuleCategory.SERVER` for server-related modules

#### Cross-Distro Support

| Component | Arch | Debian/Ubuntu | Fedora | OpenSUSE |
|-----------|------|---------------|--------|----------|
| Web Server | httpd | apache2 | httpd | apache2 |
| PHP | php, php-* | php, php8.x-* | php, php-* | php8, php8-* |
| Database | mariadb | mariadb-server | mariadb-server | mariadb |
| Cache | redis | redis-server | redis | redis |
| SSL | certbot | certbot | certbot | certbot |

#### New Distro Support

Added detection for:
- **Siduction** - Debian Sid derivative
- **Forky** - Debian Testing derivative  
- **Tuxedo OS** - Ubuntu derivative
- **Kubuntu Focus** - Ubuntu derivative with KDE

---

## [4.8.2] - 2025-11-28

### Added - Source Verification & User Preferences 🔧

The final two improvements from the v4.8 roadmap.

#### 7. Source Verification/Validation

Alternative sources are now verified before showing them to users:

```
📦 shortwave
   Via Fedora COPR • Elementary apps COPR
   [Install]

📦 some-old-package  ⚠️
   Via AUR • Requires yay or paru
   [Install]
   ^ Warning: Source could not be verified - may not exist
```

**Verification Methods:**
| Source Type | How Verified |
|-------------|--------------|
| Flatpak | `flatpak search` for app ID |
| AUR | AUR RPC API (`/rpc/v5/info/{pkg}`) |
| COPR | COPR API (`/api_3/project?...`) |
| PPA | Assumed valid (can't verify without adding) |
| RPM Fusion/Packman | Always valid (standard repos) |
| OBS | Assumed valid (in database) |

Results are cached to avoid repeated network calls.

#### 8. "Remember My Choice" Source Preferences

New preference toggles in the Alternative Sources section:

```
┌─────────────────────────────────────────────────────┐
│ 📦 Available from Alternative Sources (3)          │
│ Preferring Flatpak (sandboxed) • Click ⚙ to change │
├─────────────────────────────────────────────────────┤
│ Source Preference                                   │
│ Choose between sandboxed Flatpak or native packages │
│                        [Flatpak ✓] [Native]        │
├─────────────────────────────────────────────────────┤
│ shortwave                                           │
│ Via Flatpak (Flathub) (also: copr, aur)            │
│                                         [Install]  │
└─────────────────────────────────────────────────────┘
```

**Features:**
- Toggle between Flatpak-first or Native-first
- Shows alternative source types available: "(also: copr, aur)"
- Preferences saved to `~/.config/tux-assistant/source-preferences.json`
- List re-sorts automatically when preference changes
- Persists across sessions

**Preference Options:**
- **Prefer Flatpak**: Sandboxed, universal, auto-updates
- **Prefer Native**: AUR/COPR/PPA - tighter system integration
- **Default**: Uses built-in priority order

### Technical Implementation

**package_sources.py** (now 780+ lines):

New verification functions:
```python
verify_source_exists(source, family) -> (bool, str)
_verify_flatpak(app_id) -> (bool, str)
_verify_aur(pkg_name) -> (bool, str)  
_verify_copr(repo_id) -> (bool, str)
clear_verification_cache()
```

New preference functions:
```python
get_preferred_source(package, family) -> PackageSource
get_all_sources_for_package(package, family) -> list[PackageSource]
set_source_preference(prefer_flatpak=None, prefer_native=None, source_order=None)
get_source_preferences() -> dict
```

**setup_tools.py**:
- `_create_alternative_sources_section()`: Added preference toggles and verification indicators
- `_on_pref_flatpak_toggled()` / `_on_pref_native_toggled()`: Handle preference changes
- Updated to pass all available sources to UI

---

## [4.8.1] - 2025-11-28

### Added - Six Quality-of-Life Improvements 🎯

Building on v4.8.0's alternative source system, this release adds polish and automation.

#### 1. AUR Helper Auto-Installation (Arch)

No more "please install yay first" dead ends!

```
No AUR helper found - installing yay automatically...
Installing prerequisites (git, base-devel)...
Cloning yay-bin from AUR...
Building and installing yay...
✓ yay installed successfully!

Using yay to install shortwave from AUR...
```

The toolkit now automatically:
- Installs `git` and `base-devel` via pacman
- Clones `yay-bin` (prebuilt binary for speed)
- Builds and installs yay
- Continues with the original AUR package

#### 2. Batch Alternative Installs

New "Install All" button when multiple packages have alternatives:

```
📦 Available from Alternative Sources (3)
┌─────────────────────────────────────────────┐
│ Install All from Alternative Sources        │
│ Enable required repos and install all 3     │
│                              [Install All]  │
├─────────────────────────────────────────────┤
│ shortwave          [◌ pending]    [Install] │
│ cozy               [◌ pending]    [Install] │
│ foliate            [◌ pending]    [Install] │
└─────────────────────────────────────────────┘
```

Features:
- Groups packages by source type (one COPR enable, multiple installs)
- Visual progress per package (pending → installing → ✓/✗)
- Single authentication prompt
- Shows detailed output in expandable section
- Reports success/failure counts at completion

#### 3. Package Check Progress Feedback

Instead of just a spinner, now shows:

```
Checking package 3/9: foliate
Checking package 4/9: vlc
...
```

Users know exactly what's happening and how long to wait.

#### 4. Robust Flatpak Setup

Before installing a Flatpak, the toolkit now:
- Checks if Flatpak is installed, auto-installs if missing
- Verifies Flathub remote is configured, adds if needed
- Tries user-level install first (no root), falls back to system
- Works across all distro families

#### 5. OBS (OpenSUSE Build Service) Support

New source type for OpenSUSE users:

```bash
# tux-helper now supports:
pkexec tux-helper --enable-source obs --repo-id games --install-package lutris
pkexec tux-helper --enable-source obs --repo-id "home:user/project" --install-package myapp
```

Automatically:
- Detects OpenSUSE version (Leap/Tumbleweed)
- Constructs correct OBS repo URL
- Imports GPG keys
- Refreshes zypper

#### 6. Improved UI Feedback

- Individual package buttons now say "Install" (shorter, cleaner)
- Batch install shows per-package status icons during install
- Failed packages get "Retry" button
- Success shows checkmarks inline

### Technical Changes

**setup_tools.py** (now ~2,900 lines):
- `_check_packages_async()`: Added progress callback
- `_update_check_progress()`: New method for live progress
- `_create_alternative_sources_section()`: Added batch install button and button tracking
- `_on_install_all_clicked()`: New batch handler
- `_on_batch_install_complete()`: Handles mixed success/failure
- `_install_aur()`: Added `_auto_install_yay()` integration
- `_install_flatpak()`: Added `_auto_install_flatpak()` integration
- New `BatchAlternativeInstallDialog` class (~300 lines)

**tux-helper** (now ~2,820 lines):
- Added `--enable-source obs` choice
- New `enable_obs()` function with version detection

---

## [4.8.0] - 2025-11-28

### Added - Alternative Package Sources with Inline Installation 🚀

**Major Feature:** When packages aren't available in your base repos, the toolkit now shows you exactly where to get them - and lets you enable those sources with a single click!

#### The Problem This Solves

Before: You'd see "shortwave - Not available" and have to figure out on your own that it needs COPR on Fedora or AUR on Arch.

Now: You see "📦 Available from Alternative Sources" with an "Enable & Install" button that handles everything automatically.

#### Supported Source Types

| Source Type | Distro | Example |
|-------------|--------|---------|
| COPR | Fedora | `decathorpe/elementary-apps` |
| PPA | Debian/Ubuntu | `ppa:user/repo` |
| AUR | Arch (via yay/paru) | Any AUR package |
| Flatpak | All (via Flathub) | `com.spotify.Client` |
| RPM Fusion | Fedora | Auto-enabled for codecs |
| Packman | OpenSUSE | Auto-enabled for codecs |

#### How It Works

1. **Package Detection**: Task shows which packages are available vs unavailable
2. **Source Lookup**: Unavailable packages are checked against the alternatives database
3. **User Choice**: Packages with known alternatives show "Enable & Install" button
4. **One-Click Install**: Button triggers repo enablement + package installation
5. **No Restart Needed**: Cache clears automatically, UI updates instantly

#### User Experience

**In Task Detail Page:**
```
Packages to Install (5)
✅ vlc - Available
✅ mpv - Available

📦 Available from Alternative Sources (2)
📦 shortwave
   Available via Fedora COPR • Elementary apps COPR
   [Enable & Install]
   
📦 cozy  
   Available via Flatpak (Flathub) • Available via Flathub
   [Enable & Install]
```

#### New Files

**ltk/modules/package_sources.py** - The alternatives database:
```python
ALTERNATIVE_SOURCES = {
    "shortwave": {
        "fedora": PackageSource(SourceType.COPR, "decathorpe/elementary-apps"),
        "arch": PackageSource(SourceType.AUR, "shortwave", requires_helper=True),
        "opensuse": PackageSource(SourceType.FLATPAK, "de.haeckerfelix.Shortwave"),
    },
    # ... more packages
}
```

#### New tux-helper Commands

```bash
# Enable COPR and install package
pkexec tux-helper --enable-source copr --repo-id decathorpe/elementary-apps --install-package shortwave

# Enable PPA and install package  
pkexec tux-helper --enable-source ppa --repo-id spotify/stable --install-package spotify-client

# Enable RPM Fusion (no repo-id needed)
pkexec tux-helper --enable-source rpmfusion --install-package ffmpeg

# Enable Packman
pkexec tux-helper --enable-source packman --install-package ffmpeg
```

#### Technical Implementation

**AlternativeSourceInstallDialog** - New dialog class that:
- Shows progress and output during installation
- Handles Flatpak installs (no root needed)
- Handles AUR via yay/paru (detects available helper)
- Handles COPR/PPA/RPM Fusion/Packman via tux-helper with pkexec
- Clears package cache after repo enablement
- Updates UI without app restart

**Package Sources Database** covers:
- Media apps (shortwave, cozy, foliate, spotify)
- Browsers (chrome, brave)
- Dev tools (vscode, sublime-text)
- Communication (discord, slack, zoom)
- Gaming (steam, lutris)
- System tools (timeshift, stacer, btop)
- Codecs (ffmpeg, libdvdcss, gstreamer plugins)

#### For 10-Year-Old Timmy

Whether you're on Arch, Fedora, or Debian, the toolkit just handles it:
- On Arch? Uses yay/paru automatically
- On Fedora? Enables the right COPR
- On Debian? Adds the right PPA
- Everywhere? Flatpak works as universal fallback

No more "how do I install X on distro Y?" - just click the button!

---

## [4.7.0] - 2025-11-28

### Added - Dynamic Package Availability Detection 🎯

**Major Feature:** The toolkit now dynamically checks which packages are actually available in your enabled repositories at runtime!

#### How It Works

1. **Package Wishlists**: Tasks define a "wishlist" of desired packages (same for all distros)
2. **Runtime Detection**: When viewing a task, the toolkit queries your package manager to see what's actually available
3. **Smart Filtering**: Only available packages are shown/installed; unavailable ones are greyed out with explanation
4. **Repo-Aware**: If you enable additional repos (COPR, PPA, Packman), those packages automatically become available!

#### User Experience

**In the Task Detail Panel:**
- Shows a loading spinner while checking package availability
- ✅ Green checkmark for available packages
- ❌ Red X for unavailable packages (with "Not available in enabled repositories" subtitle)
- Package count reflects only what will actually be installed

**During Installation:**
- Only attempts to install available packages
- Shows warning for any skipped unavailable packages
- No more "package not found" errors!

#### Technical Implementation

**New Functions in setup_tools.py:**
```python
check_package_available(package, family) -> bool
filter_available_packages(packages, family) -> list
get_available_packages_for_task(task, family) -> list
clear_package_cache()  # Call after enabling new repos
```

**New CLI in tux-helper:**
```bash
# Check package availability (returns JSON, no root needed)
./tux-helper --check-packages shortwave cozy vlc --family debian
# Output: {"family": "debian", "available": ["shortwave", "cozy", "vlc"], "unavailable": []}
```

**Package Manager Queries:**
| Family | Command Used |
|--------|--------------|
| Debian | `apt-cache show <pkg>` |
| Arch | `pacman -Si <pkg>` |
| Fedora | `dnf info <pkg>` |
| OpenSUSE | `zypper info <pkg>` |

#### Practical Example

**KDE Enhancements wishlist includes:** shortwave, cozy, foliate, vlc, mpv, etc.

| Distro | What Gets Installed |
|--------|---------------------|
| Debian | All 9 packages (great repo coverage!) |
| Fedora | 7 packages (shortwave/cozy are Flatpak-only) |
| Arch | 7 packages (shortwave is AUR-only) |
| Fedora + COPR enabled | 9 packages! (COPR adds shortwave) |

**The magic:** Enable a COPR/PPA repo → restart toolkit → those packages now appear as available! 🪄

## [4.6.2] - 2025-11-28

### Fixed - KDE_ENHANCEMENTS Package Availability Per Distro

**Issue:** Some packages (shortwave, cozy) are not available in official repos for all distros, causing install failures.

**Research findings:**
- **Shortwave**: Only in Debian repos. Arch (AUR only), Fedora (COPR only), OpenSUSE (not available) → Flatpak recommended
- **Cozy**: Only in Debian repos. Others require Flatpak or third-party repos

**Updated package lists:**

| Distro | Packages |
|--------|----------|
| **Arch** | kaccounts-integration, kaccounts-providers, kio-gdrive, ktorrent, foliate, vlc, mpv |
| **Debian** | kaccounts-integration, kaccounts-providers, kio-gdrive, ktorrent, **shortwave**, foliate, **cozy**, vlc, mpv |
| **Fedora** | kaccounts-integration, kaccounts-providers, kio-gdrive, ktorrent, foliate, vlc, mpv |
| **OpenSUSE** | kaccounts-integration, kaccounts-providers, kio-gdrive, ktorrent, foliate, vlc, mpv |

Debian gets the most apps because it has the best repo coverage for these packages!

## [4.6.1] - 2025-11-28

### Fixed - Desktop-Specific Task Filtering

**Issue:** Desktop enhancement tasks (XFCE, KDE, GNOME) were showing to all users regardless of their desktop environment.

**Fix:** Updated `get_tasks_for_distro()` to accept desktop environment parameter and filter appropriately:

```python
def get_tasks_for_distro(family: DistroFamily, desktop_env: Optional[DesktopEnv] = None):
    # Tasks with desktop_specific set will only show if desktop_env matches
```

**Result:**
| User's Desktop | Sees XFCE Enhancements | Sees KDE Enhancements | Sees GNOME Enhancements |
|----------------|------------------------|----------------------|-------------------------|
| XFCE | ✅ Yes | ❌ No | ❌ No |
| KDE | ❌ No | ✅ Yes | ❌ No |
| GNOME | ❌ No | ❌ No | ✅ Yes |
| Other | ❌ No | ❌ No | ❌ No |

**Non-desktop-specific tasks** (Essential Tools, Codecs, Drivers, etc.) continue to show for all users.

## [4.6.0] - 2025-11-28

### Added - GNOME Extensions & Tweaks Manager GUI 🎨✨

A **full GTK4/libadwaita GUI** for managing GNOME Shell extensions and tweaks!

#### Features

**Extensions Tab:**
- 🔍 **Search extensions** from extensions.gnome.org directly in the app
- 📦 **Install extensions** with one click (downloads, installs, enables automatically)
- ✅ **Enable/disable** installed extensions with toggle switches
- 🗑️ **Uninstall** extensions you no longer need
- ⭐ **Popular extensions** pre-loaded: Dash to Dock, Blur My Shell, AppIndicator, Caffeine, GSConnect, Vitals, ArcMenu, Clipboard Indicator, User Themes, Just Perfection

**Tweaks Tab:**
- 🪟 **Window Controls**: Button layout (right/left/minimal)
- ⏰ **Top Bar**: Show weekday, seconds, battery percentage
- ⚡ **Behavior**: Hot corners, animations, night light
- 🖱️ **Input**: Tap to click, natural scrolling

**Installed Tab:**
- 📋 View all installed extensions
- 🔄 Refresh to detect new installations
- Toggle and remove from one place

#### Technical Details

**Built with:**
- GTK4 + libadwaita for modern GNOME look
- Async extension installation (threaded, non-blocking UI)
- Direct integration with extensions.gnome.org API
- gsettings for tweak management

**Packages installed:**

| Distro | Packages |
|--------|----------|
| Arch | gnome-tweaks, gnome-shell-extensions, dconf-editor, python-gobject, libadwaita |
| Debian | gnome-tweaks, gnome-shell-extensions, dconf-editor, python3-gi, gir1.2-adw-1, gir1.2-gtk-4.0 |
| Fedora | gnome-tweaks, gnome-extensions-app, dconf-editor, python3-gobject, libadwaita |
| OpenSUSE | gnome-tweaks, gnome-shell-extensions, dconf-editor, python3-gobject, libadwaita, typelib-1_0-Adw-1 |

**Installation creates:**
- `~/.local/bin/ltk-gnome-manager` - standalone launcher
- `~/.local/share/applications/ltk-gnome-manager.desktop` - app menu entry

**Launch methods:**
1. Search "GNOME Enhancements" in app menu
2. Run `ltk-gnome-manager` from terminal

#### Screenshots (conceptual)
```
┌─────────────────────────────────────────────────────────────┐
│  GNOME Enhancements - Tux Assistant                    [X]  │
├─────────────────────────────────────────────────────────────┤
│        [Extensions]  [Tweaks]  [Installed]                  │
├─────────────────────────────────────────────────────────────┤
│  🔍 Search extensions...                         [Search]   │
│                                                             │
│  Popular Extensions                                         │
│  ┌────────────────────────────────────────────────────────┐ │
│  │ Dash to Dock                                           │ │
│  │ A dock for GNOME Shell (like macOS)    [━━━○] [Remove] │ │
│  ├────────────────────────────────────────────────────────┤ │
│  │ Blur My Shell                                          │ │
│  │ Add blur effect to Shell               [Install]       │ │
│  └────────────────────────────────────────────────────────┘ │
│                                                             │
│  GNOME Shell 46 • 5 extensions installed                    │
└─────────────────────────────────────────────────────────────┘
```

### Desktop Enhancements Complete! 🎉

All three major desktop environments now have enhancement tasks:
- **XFCE**: Super key binding, Thunar actions, Samba sharing (5 options)
- **KDE**: Google account fix, kio-gdrive, media apps
- **GNOME**: Full GTK GUI for extensions and tweaks

## [4.5.3] - 2025-11-28

### Added - KDE Online Accounts Fix & Enhancements 🔧

#### KDE_ENHANCEMENTS Task
Fixes the notorious KDE Google account integration bug and installs useful KDE apps.

**The Problem:** KDE's Online Accounts has been broken for Google integration due to outdated OAuth2 configuration in the provider file.

**The Fix:** Creates/updates `~/.local/share/accounts/providers/google.provider` with proper OAuth2 configuration including:
- Correct OAuth2 endpoints (accounts.google.com)
- Required scopes: email, profile, calendar, tasks, drive
- Proper client credentials
- Offline access token support

**Post-install actions:**
1. Backs up existing google.provider (if present)
2. Creates fixed google.provider with correct OAuth2 config
3. Fixes file ownership (runs as root, files owned by user)
4. Restarts kded6 (KDE daemon)
5. Restarts plasma-kglobalaccel (keyboard shortcuts service)

**Packages installed:**

| Distro | Packages |
|--------|----------|
| All | kaccounts-integration, kaccounts-providers, kio-gdrive, ktorrent, shortwave, foliate, vlc, mpv |
| Debian | + cozy (audiobook player) |

**Apps included:**
- **kio-gdrive** - Google Drive integration in Dolphin
- **VLC & MPV** - Media players
- **Foliate** - Ebook reader
- **KTorrent** - BitTorrent client
- **Shortwave** - Internet radio

**Only shows on KDE desktop** (`desktop_specific=DesktopEnv.KDE`)

### Technical Notes
- OAuth2 fix embedded directly (no external curl dependency)
- Service restarts run as actual user via `su -`
- Graceful fallback if services can't restart (will apply on next login)

## [4.5.2] - 2025-11-28

### Added - Snap Removal & Enhanced XFCE Samba Sharing 🧹📁

#### Complete Snap Removal (Ubuntu only)
Full "snap exorcism" that:
1. **Dynamically detects** all installed snaps via `snap list`
2. **Sorts by dependency order** - apps first, then themes, then base snaps, then core/snapd last
3. **Removes each snap** in correct order to avoid dependency errors
4. **Stops, disables, and masks** snapd service
5. **Purges** snapd package via apt
6. **Removes all snap directories:**
   - ~/snap
   - /snap
   - /var/snap
   - /var/lib/snapd
   - /var/cache/snapd
7. **Creates apt pin** at `/etc/apt/preferences.d/nosnap.pref` to block reinstallation

**Snap removal priority order:**
| Priority | Snaps |
|----------|-------|
| 10 | firefox, thunderbird, chromium (apps) |
| 15 | snap-store, firmware-updater, canonical-livepatch |
| 20 | snapd-desktop-integration |
| 25 | gtk-common-themes |
| 30 | gnome-46-2404, gnome-42-2204, etc. |
| 50 | (unknown snaps - default) |
| 80 | core24, core22, core20, core18 |
| 85 | core |
| 90 | bare |
| 100 | snapd (last!) |

#### Enhanced XFCE Thunar Samba Actions
Expanded from 3 options to **5 complete options** covering all share scenarios:

| Action | Command | Use Case |
|--------|---------|----------|
| Samba: Share Public (Read Only) | `net usershare add %n %f "" Everyone:R guest_ok=y` | Anyone can view, no password |
| Samba: Share Public (Writeable) | `net usershare add %n %f "" Everyone:F guest_ok=y && chmod 777 %f` | Anyone can read/write, no password |
| Samba: Share Private (Read Only) | `net usershare add %n %f "" Everyone:R guest_ok=n` | Requires login, read only |
| Samba: Share Private (Writeable) | `net usershare add %n %f "" Everyone:F guest_ok=n && chmod 777 %f` | Requires login, full access |
| Samba: Unshare Folder | `net usershare delete %n && chmod 755 %f` | Remove share & restore permissions |

Icons: `folder-publicshare` for public, `folder-remote` for private, `edit-delete` for unshare

## [4.5.1] - 2025-11-28

### Added - Virtualization Support 🖥️💻

#### VirtualBox Task
**Packages by distro:**
| Distro | Packages |
|--------|----------|
| Arch | virtualbox, virtualbox-host-modules-arch, virtualbox-guest-iso |
| Debian | virtualbox, virtualbox-ext-pack, virtualbox-guest-additions-iso |
| Fedora | VirtualBox, akmod-VirtualBox, virtualbox-guest-additions (RPM Fusion auto-enabled!) |
| OpenSUSE | virtualbox, virtualbox-host-source, virtualbox-guest-tools |

**Post-install setup:**
- Creates/checks `vboxusers` group
- Adds user to `vboxusers` group
- Loads `vboxdrv` kernel module
- Fedora: Runs `akmods --force` for kernel module
- OpenSUSE: Runs vboxdrv.sh setup

#### Virt-Manager (QEMU/KVM) Task
**Packages by distro:**
| Distro | Packages |
|--------|----------|
| Arch | qemu-full, libvirt, virt-manager, virt-viewer, dnsmasq, bridge-utils, openbsd-netcat, edk2-ovmf |
| Debian | qemu-system, qemu-utils, libvirt-daemon-system, libvirt-clients, virt-manager, virt-viewer, virtinst, dnsmasq-base, bridge-utils, ovmf |
| Fedora | qemu-kvm, libvirt, virt-manager, virt-viewer, virt-install, dnsmasq, bridge-utils, edk2-ovmf |
| OpenSUSE | qemu-kvm, libvirt, virt-manager, virt-viewer, virt-install, dnsmasq, bridge-utils, qemu-ovmf-x86_64 |

**Post-install setup:**
- Checks KVM hardware support (/dev/kvm, CPU flags)
- Adds user to `libvirt`, `kvm` groups (and `libvirt-qemu` on Debian)
- Enables and starts `libvirtd` service
- Enables `virtlogd.socket` for logging
- Creates/starts default NAT network for VMs
- Provides helpful quick-start instructions

### Technical Details
- Both tasks marked `requires_reboot=True`
- User informed about logout/login requirement for group membership
- KVM support detection with helpful BIOS hints

## [4.5.0] - 2025-11-28

### Added - XFCE Desktop Enhancements 🖥️

**"XFCE Enhancements" task - makes XFCE feel like home!**

#### Super Key → Whisker Menu
- Installs `xcape` to map Super key to Alt+F1
- Creates autostart entry: `~/.config/autostart/xcape-super-whisker.desktop`
- Works on key release (so Super+E, Super+D etc. still work!)

#### Thunar Custom Actions (right-click menu)
Creates `~/.config/Thunar/uca.xml` with:
- **Open as Root** - `pkexec thunar %f` (folders)
- **Edit as Root** - `pkexec mousepad %f` (text files)
- **Share Folder (Public)** - `net usershare` read-only
- **Share Folder (Read-Write)** - `net usershare` with write access
- **Unshare Folder** - Remove Samba share
- **Open Terminal Here** - `exo-open` terminal

#### Samba Usershare Setup
- Creates `/var/lib/samba/usershares` directory
- Creates `sambashare` group if needed
- Adds user to `sambashare` group
- Sets proper permissions (1770)

### Packages Installed
| Distro | Packages |
|--------|----------|
| All | xcape, xfce4-whiskermenu-plugin, mousepad, samba |

### Technical Details
- Task is desktop-specific (only shows on XFCE)
- Backs up existing uca.xml before overwriting
- Fixes file ownership to actual user (not root)
- Logout/login required for full effect

## [4.4.2] - 2025-11-28

### Added
- **Emoji Support task with auto keyboard shortcut! 🎉**
  - Installs `gnome-characters` and emoji fonts
  - **Automatically configures Super+. (Super+Period) shortcut on GNOME**
  - Detects KDE and notes built-in picker
  - Falls back to manual instructions for other DEs
  
- New `special_handler` field in SetupTask for post-install configuration
- `setup_emoji_keyboard()` handler in tux-helper

### Technical
- Uses gsettings to configure GNOME custom keybindings
- Idempotent: checks if shortcut already exists before adding
- Graceful fallback if shortcut setup fails (packages still install)

### Packages by Distro
| Distro | Packages |
|--------|----------|
| Arch | gnome-characters, noto-fonts-emoji |
| Debian | gnome-characters, fonts-noto-color-emoji |
| Fedora | gnome-characters, google-noto-emoji-color-fonts |
| OpenSUSE | gnome-characters, noto-coloremoji-fonts |

## [4.4.1] - 2025-11-28

### Added
- **OpenSUSE support for special app installations**
  - Surfshark VPN: Downloads .deb → alien converts to .rpm → installs + systemd setup
  - DuckieTV: Downloads .deb from GitHub → alien converts → installs
  - Uses zypper for dependency installation (alien, dpkg, rpm-build)
  
### Changed
- Updated app descriptions to reflect multi-distro support
- Refactored special installers to detect package manager (dnf vs zypper)

## [4.4.0] - 2025-11-28

### Added - MAJOR: Automagic Repository Enablement for ALL Distros 🎉

**"10-year-old setting up grandpa's computer" - it just works!**

Now ALL distributions automatically get the repos they need for multimedia:

#### Debian/Ubuntu
- Auto-enables `contrib` and `non-free` repos when needed
- Supports both traditional sources.list and DEB822 (.sources) format
- Packages: libdvd-pkg, ttf-mscorefonts-installer, unrar, nvidia-driver

#### Fedora
- Auto-enables RPM Fusion (free + nonfree) when needed
- Detects Fedora version automatically
- Packages: ffmpeg, libdvdcss, vlc, nvidia drivers, gstreamer-ugly/libav

#### OpenSUSE
- Auto-enables Packman repository when needed
- Supports both Tumbleweed and Leap (auto-detects version)
- Auto-switches system packages to Packman versions for consistency
- Packages: ffmpeg, libdvdcss2, vlc, gstreamer-ugly/libav

### Removed
- Manual "RPM Fusion Repositories" task (now automatic)
- Manual "Packman Repository" task (now automatic)
- Users no longer need to think about repos at all!

### Changed
- Updated Multimedia Codecs description: "repos auto-enabled"
- Simplified task list - fewer choices, better results

## [4.3.8] - 2025-11-28

### Restored
- **Full DVD Support for Debian** - Same treatment as other distros
  - Restored `libdvd-pkg` package (auto-enables contrib repo)
  - Restored `dpkg-reconfigure libdvd-pkg` command to compile libdvdcss
  - DVD playback now works automagically on Debian too!

### Changed
- Updated description: "Audio/video codecs including DVD playback support"
- Cleaned up contrib/non-free package lists in helper

## [4.3.7] - 2025-11-28

### Added
- **Automagic Debian Repo Enablement** - "10-year-old setting up grandpa's computer" philosophy
  - Helper automatically detects when packages need contrib/non-free repos
  - Automatically enables repos before installing (no user intervention needed)
  - Supports both traditional sources.list and modern DEB822 (.sources) format
  - Runs `apt update` after enabling repos

### Restored
- `ttf-mscorefonts-installer` in Fonts (contrib auto-enabled)
- `unrar` in Archive Support (non-free auto-enabled)

### Technical
- New functions in tux-helper:
  - `check_debian_repos_enabled()` - Detects current repo state
  - `enable_debian_repos()` - Modifies sources files
  - `ensure_debian_repos_for_packages()` - Smart detection of what's needed

## [4.3.6] - 2025-11-28

### Fixed
- **Debian 13**: Removed `ttf-mscorefonts-installer` (requires contrib repo)
- Added `fonts-noto-color-emoji` to Debian fonts for emoji support

## [4.3.5] - 2025-11-28

### Fixed
- **Debian 13 (Trixie) Compatibility** - Major package availability fixes:
  - Essential Tools: `neofetch` → `fastfetch` (neofetch removed from Debian 13)
  - Archive Support: `unrar` → `unrar-free` (unrar requires non-free repo)
  - Multimedia Codecs: Removed `libdvd-pkg` (not available in Debian 13)
  - Printing Support: Removed `cups-pdf` (not available in Debian 13)
  - Removed `dpkg-reconfigure libdvd-pkg` command

- **Critical: Task Execution Order** - Fixed packages vs commands ordering
  - Previously: Commands ran BEFORE packages (broke Flatpak setup)
  - Now: Packages install FIRST, then setup commands run
  - This fixes "flatpak: not found" when adding Flathub repo

### Changed
- Updated OpenSUSE to use `fastfetch` instead of `neofetch`
- Improved code comments documenting Debian 13+ package changes

## [4.3.4] - 2025-11-28

### Fixed
- **Critical**: Correct Debian 12+ package names for polkit
  - Changed from `policykit-1` (transitional) to `pkexec polkitd` (actual packages)
  - In Debian 12 Bookworm, polkit was split into separate packages

## [4.3.3] - 2025-11-28

### Fixed
- **Critical**: Fresh Debian installations missing polkit/pkexec
  - install.sh now installs `policykit-1` on Debian (polkit on others)
  - install.sh now checks for pkexec availability before proceeding
  - Setup Tools now falls back to `sudo` if `pkexec` not available
  - Better error message: "Neither pkexec nor sudo found!"

### Changed
- install.sh dependency check now includes polkit verification
- Fallback authentication shows warning: "Note: pkexec not found, using sudo fallback"

## [4.3.2] - 2025-11-28

### Fixed
- **Software Center**: Replaced `print()` error messages with user-friendly toasts
  - Native search errors now show as toasts
  - Flatpak search errors now show as toasts
  - Uses GLib.idle_add for thread safety
- **Networking**: Replaced `print()` error messages with silent handling
  - smb.conf parsing errors fail gracefully (empty list)
  - Domain discovery errors fail gracefully (empty dict)
- **Networking**: Replaced "TODO" toast with proper "Not Implemented" dialog
  - Leave Domain now shows helpful message with distro-specific commands
  - Lists: realm leave, adcli, yast2 auth-client

### Changed
- Error handling now follows production best practices (no stdout noise)

## [4.3.1] - 2025-11-28

### Added
- **Setup Tools**: GPU detail dialog when clicking detected GPU row
  - Shows GPU name, PCI ID, vendor, recommended driver
  - Friendly emoji icon (🖥️)
- **Setup Tools**: NVIDIA repo warning dialogs
  - Fedora: Warns about needing RPM Fusion (nonfree)
  - Debian: Warns about needing non-free/contrib repos
  - Only shows when selecting NVIDIA drivers on affected distros

### Changed
- GPU detection section now says "click for details" in description
- GPU rows are now clickable (activatable) in addition to having Select button

## [4.3.0] - 2025-11-28

### Added
- **Main Screen**: "I'm Done!" button at bottom of home page
  - Friendly airplane emoji theme (✈️)
  - Shows goodbye dialog with thank you message:
    "Thank you for using the Tux Assistant. Please return your tray tables to the upright position. We hope it has been beneficial and you enjoyed the ride!"
  - "Wait, Go Back" option if user clicks by accident
  - "Exit" button cleanly closes the application
- **Main Screen**: Separator line and hint text above Done button

## [4.2.9] - 2025-11-28

### Added
- **Setup Tools**: GPU auto-detection with driver recommendations
  - Detects NVIDIA, AMD, and Intel GPUs via lspci
  - Shows detected GPUs at top of Drivers section
  - Recommends appropriate driver based on GPU generation
  - "Select" button to auto-select recommended driver
- **Setup Tools**: Expanded NVIDIA driver options
  - NVIDIA Latest (580.x) - RTX 40/30/20, GTX 16/10 series
  - NVIDIA 550.x (Stable LTS) - Maxwell, Pascal, Volta, Turing, Ampere, Ada
  - NVIDIA 535.x (Legacy LTS) - Older Maxwell through Ampere
  - NVIDIA 470.x (Legacy) - Kepler GPUs (GTX 600/700 series)
  - NVIDIA 390.x (Very Old Legacy) - Fermi GPUs (GTX 400/500 series)
  - NVIDIA Open Kernel (Experimental) - Turing+ architecture
- **Setup Tools**: AMD PRO Graphics driver option
  - For Radeon Pro/Workstation GPUs
  - Includes ROCm OpenCL runtime on Arch

### Changed
- AMD Graphics renamed to "AMD Graphics (Open Source)" with clearer description
- Selecting a recommended driver now clears other GPU driver selections to prevent conflicts

## [4.2.8] - 2025-11-28

### Added
- **Software Center**: Pamac-style detail pages for search results
  - Click checkbox to queue, click row to see package details
  - PackageDetailPage shows: name, description, version, source, app ID
  - Queue sync between list and detail page
- **Software Center**: Pamac-style detail pages for category apps
  - AppDetailPage shows: name, description, packages, flatpak info, special requirements
  - Apply same checkbox/row click pattern
- **Desktop Enhancements**: Pamac-style detail pages for themes
  - ThemeDetailPage shows: packages to install, theme type, apply button
  - For unavailable themes: shows download links (GNOME Look, GitHub, KDE Store)
  - AUR hint for Arch users

### Changed
- All three modules now use consistent UX pattern:
  - ☐ Checkbox click → immediate queue toggle
  - Row/text click → navigate to detail page with full info
  - Detail page has "Add to Queue" / "Remove from Queue" button
  - Queue state syncs when returning to list

## [4.2.7] - 2025-11-28

### Added
- **Setup Tools**: New task detail page (pamac-style UX)
  - Click checkbox to queue/unqueue items directly
  - Click row text to see detailed info about what will be installed
  - Detail page shows: category, reboot requirement, all packages, any additional commands
  - "Add to Install Queue" / "Remove from Queue" button on detail page
  - Queued state syncs between detail page and main checkbox
- **Setup Tools**: Select All and Clear buttons now actually work

### Changed
- **Setup Tools**: Row click now navigates to detail page instead of toggling checkbox
- **Setup Tools**: Added arrow indicator on rows to show they're clickable for details

## [4.2.6] - 2025-11-28

### Fixed
- **UI**: Removed CSS styling that was making checkboxes look ugly/square
- **UI**: Button styling now more specific - only affects text buttons, not checkboxes

## [4.2.5] - 2025-11-28

### Changed
- **UI**: Larger default window size (1100x800, up from 900x650)
- **UI**: Increased base font size to 11pt for better readability
- **UI**: Larger preference group titles (13pt bold)
- **UI**: Taller action rows (60px) for easier clicking
- **UI**: Larger buttons with more padding (min-height 36px)
- **UI**: Pill buttons even larger (42px height, 12pt font)
- **UI**: Status page titles increased to 18pt
- **UI**: Message dialog headings at 14pt
- **UI**: Wider content area (950px max, up from 800px)
- **UI**: All changes via CSS - no structural modifications

## [4.2.4] - 2025-11-28

### Fixed
- **Installer**: Fixed "permission denied" error when running install.sh after extraction
- **Package**: All executable scripts (install.sh, tux.py, tux-helper) now have proper execute permissions in the zip file

## [4.2.3] - 2025-11-28

### Changed
- **ISO Creator**: Replaced terminal-based "eggs mom" with integrated GUI guide
  - New "Learn First" option shows friendly tour of penguins-eggs features
  - Covers: What is eggs, Snapshot modes, Compression options, Advanced features, Workflow, Output location
  - All within the GTK4 interface - no scary terminal needed
  - "Configure & Continue" button at end runs dad configuration
- **ISO Creator**: Renamed "Guided Mode" to "Learn First" and "Quick Mode" to "Quick Start"

### Removed
- **ISO Creator**: Terminal emulator detection and launching (no longer needed)

## [4.2.2] - 2025-11-28

### Added
- **ISO Creator**: New setup choice page after installation with two paths:
  - **Guided Mode (Mom)**: Launches `eggs mom` in terminal for interactive exploration of all commands and documentation
  - **Quick Mode (Dad)**: Auto-configures with `eggs dad -d` for immediate ISO creation
- **ISO Creator**: Terminal emulator auto-detection (supports gnome-terminal, konsole, xfce4-terminal, mate-terminal, tilix, terminator, alacritty, kitty, xterm)
- **ISO Creator**: "Skip to ISO Creator" option for already-configured systems

### Changed
- **ISO Creator**: Configuration flow now presents user choice instead of auto-running dad
- **ISO Creator**: Configure button on main page now shows setup choice instead of auto-configuring

## [4.2.1] - 2025-11-28

### Fixed
- **ISO Creator**: Configuration detection now more lenient (checks for common eggs output indicators)
- **ISO Creator**: Fixed duplicate "Configure" buttons appearing on refresh
- **ISO Creator**: Added `--nointeractive` flag to all eggs commands to prevent hangs
- **ISO Creator**: Done button label now resets properly between different operations
- **ISO Creator**: Configure button now uses `eggs dad -d` instead of deprecated `eggs config`

## [4.2.0] - 2025-11-28

### Added
- **ISO Creator Module** - Beautiful GUI wrapper for penguins-eggs
  - Create bootable live ISOs from your running system
  - Three snapshot modes: Clean (no user data), Clone (with data), Encrypted Clone (LUKS)
  - Compression options: Fast (zstd), Pendrive optimized, Standard (xz), Maximum
  - Custom ISO naming support
  - Offline installation capability (yolk)
  - Tools menu: Clean ISOs, System cache cleanup, Calamares installation, Status
  - Real-time terminal output with progress tracking
  - Automatic detection of penguins-eggs installation status
  - Distro-specific installation instructions (fresh-eggs, AUR, Manjaro repo)
  - Proper attribution: "Powered by penguins-eggs by Piero Proietti"

### Technical Details
- Wraps penguins-eggs CLI rather than reimplementing ISO creation
- Supports all distributions that penguins-eggs supports:
  - Fedora, AlmaLinux, Rocky Linux
  - Arch, Manjaro, EndeavourOS, Garuda  
  - Debian, Ubuntu, Linux Mint, Pop!_OS
  - OpenSUSE, and many more derivatives
- Includes Calamares/Krill installer integration via eggs
- Uses pkexec for GUI privilege escalation when available

## [4.1.0] - 2025-11-27

### Added
- **Theme Download Dialog**: New dialog for installing themes not in repos
  - Direct links to gnome-look.org and GitHub
  - AUR installation support for Arch with auto-detection of yay/paru
  - ocs-url helper installation for one-click theme installs
  - Distro-specific installation instructions
- **New GTK Themes**: Added 6 new themes available across all distros
  - Adwaita Dark, Arc Darker, Numix, Adapta, Adapta Nokto, Breeze Dark
- **Theme URL metadata**: Themes now include gnome-look.org, GitHub, and KDE Store URLs
- **Samba Share Management**: Full CRUD operations for Samba shares
  - View all shares with expandable details
  - Edit share properties (name, path, permissions, guest access)
  - Delete shares with confirmation
  - Workgroup and service status display

### Changed
- Theme rows for unavailable packages now show "Get" button instead of being disabled
- Improved tooltips with distro-specific guidance

### Fixed
- Theme availability now correctly detects distro family
- Apply button hidden for themes without packages (prevents confusion)

## [4.0.0] - 2025-11-26

### Added
- **Desktop Enhancements Module** (3,900+ lines)
  - GTK/Icon/Cursor theme management with install and apply
  - GNOME extensions management with enable/disable toggles
  - KDE widgets and Plasma theme support
  - XFCE panel plugins
  - Desktop tweaks for all three DEs (GNOME, KDE, XFCE)
  - Theme presets for quick desktop customization
  - Desktop tools installation (Tweaks, Extensions, Kvantum, etc.)
- **Networking Module** (2,500+ lines)
  - Samba quick share creation wizard
  - Active Directory domain joining
  - Firewall management (firewalld, ufw)
  - Network browser with mDNS/Avahi discovery
- **Software Center Module** (2,600+ lines)
  - Curated software categories
  - Flatpak and native package support
  - Batch installation with progress tracking
- **Setup Tools Module** (900+ lines)
  - Post-installation automation
  - Multimedia codec installation
  - Development environment setup

### Changed
- Complete rewrite from Bash to Python with GTK4/Libadwaita
- Modular architecture with shared core libraries
- Modern UI with Adwaita design language

## [3.x] - Legacy Bash Version

The 3.x series was the final Bash-based version of the toolkit.
See git history for details.

---

## Version Numbering

- **Major** (X.0.0): Breaking changes, major rewrites, new architecture
- **Minor** (0.X.0): New features, modules, significant enhancements
- **Patch** (0.0.X): Bug fixes, small improvements, documentation

## Links

- **Author**: Christopher Dorrell
- **Email**: dorrellkc@gmail.com
- **GitHub**: github.com/dorrelkc
