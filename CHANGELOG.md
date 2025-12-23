# Tux Assistant Changelog

All notable changes to Tux Assistant will be documented in this file.

## [1.0.6] - 2025-12-21

### Fixed - Network Sharing & File Manager Integration
- **Fixed network browsing in all file managers** - Nemo, Nautilus, Dolphin, Thunar, Caja now properly browse SMB shares
- **Added gvfs-smb packages** - Required for file manager network integration:
  - Arch/CachyOS/Manjaro: `gvfs-smb`
  - Debian/Ubuntu: `gvfs-backends`
  - Fedora: `gvfs-smb`
  - openSUSE: `gvfs-backend-samba`
- **Fixed usershare infrastructure** - Resolves "net usershare: usershares are currently disabled" error
  - Creates `/var/lib/samba/usershares/` directory
  - Creates `sambashare` group
  - Adds user to sambashare group
  - Sets proper permissions (1770)
  - Adds usershare configuration to smb.conf
- **Enabled avahi-daemon in basic Samba install** - Network discovery works immediately
- **Updated smb.conf template** - Includes usershare settings by default

**Impact:** Network sharing now "just works" across all desktop environments. Click Network in your file manager → see shares. Shares created in Tux Assistant appear everywhere.

## [0.9.279] - 2025-12-18

### Added - Automatic p7zip Installation
- **install.sh now installs p7zip** - Detected and installed for each distro:
  - openSUSE: `zypper install p7zip`
  - Fedora: `dnf install p7zip p7zip-plugins`
  - Debian/Ubuntu: `apt install p7zip-full`
  - Arch: `pacman -S p7zip`
- **Runtime fallback** - If 7z not found when extracting a .7z file:
  - Uses `pkexec` (graphical sudo prompt) to install p7zip
  - Automatically retries extraction after install
  - Shows notification during installation

This is Tux Assistant - we handle the hard stuff so users don't have to.

## [0.9.278] - 2025-12-18

### Fixed - OCS Handler Improvements
- **Case-insensitive content type matching** - Handles `gnome_shell_themes` same as `Gnome Shell Themes`
- **Added 7z extraction support** - Uses system `7z` or `7za` command
- **Partial content type matching** - Falls back to reasonable defaults

## [0.9.277] - 2025-12-18

### Debug
- Added logging to `tux-ocs-handler` - writes to `~/.config/tux-assistant/ocs-handler.log`
- Logs received URLs, parsed parameters, download progress, and results

## [0.9.276] - 2025-12-18

### Changed - Replaced Browser Extension with Protocol Handler
Firefox won't load unsigned extensions. Switched to a much simpler approach.

**Removed:**
- Firefox extension (tux-browser-extension/)
- Native messaging host
- All the complicated XPI/signing stuff

**Added:**
- **OCS Protocol Handler** (`tux-ocs-handler`) - System-level handler for `ocs://` links
- **Desktop entry** (`tux-ocs-handler.desktop`) - Registers with the system

**How it works now:**
1. You browse gnome-look.org in ANY browser
2. Click "Install" on a theme
3. The system sees `ocs://install?...` link
4. System calls Tux Assistant's handler
5. Theme downloads and installs to ~/.themes or ~/.icons
6. Desktop notification confirms success

No browser extension needed. Works with Firefox, Chrome, whatever.

## [0.9.275] - 2025-12-18

### Debug
- Added verbose debugging to XPI creation to track down why extension isn't being installed

## [0.9.274] - 2025-12-18

### Fixed - Extension Auto-Enable
- **Added `extensions.autoDisableScopes = 0`** - Prevents Firefox from disabling sideloaded extensions
- **Added `extensions.enabledScopes = 15`** - Enables all extension scopes
- **Added `extensions.startupScanScopes = 15`** - Scans all scopes on startup
- **Always install native messaging manifest** - Even if extension already exists
- **Updated existing profile handling** - Adds new settings to existing user.js files

These settings should make Firefox automatically enable the Tux Connector extension
instead of silently ignoring it.

## [0.9.273] - 2025-12-18

### Fixed
- **install.sh** - Create `/opt/tux-assistant/scripts/` directory before copying native host

## [0.9.272] - 2025-12-18

### Added - Automatic Extension Installation
- **Auto-install Tux Connector** - Extension is automatically installed to Firefox profile
  - No manual about:debugging steps required
  - Installs on first Tux Browser launch
  - Updates existing profiles automatically
- **Unsigned extension support** - `xpinstall.signatures.required = false` in user.js
- **User-level native messaging** - Manifest also installed to `~/.mozilla/native-messaging-hosts/`

### Changed
- Removed manual installation instructions from install.sh
- Extension now "just works" when you launch Tux Browser

### How It Works
1. First time you click the browser button
2. Profile is created with unsigned extension support enabled
3. Tux Connector extension (XPI) is installed to profile
4. Native messaging manifest is set up
5. Firefox launches with everything ready

One-click installs from gnome-look.org and extensions.gnome.org should work automatically.

## [0.9.271] - 2025-12-18

### Added - Phase 2: Native Messaging Extension
- **Firefox WebExtension** (`tux-browser-extension/`) - Catches install requests
  - Intercepts OCS protocol links (gnome-look.org, pling.com, opendesktop.org)
  - Catches GNOME Extensions install requests (extensions.gnome.org)
  - Sends requests to Tux Assistant via native messaging
- **Native messaging host** (`tux-native-host`) - Receives messages from Firefox
  - Handles GNOME Shell extension installation
  - Handles OCS content installation (themes, icons, cursors)
  - Shows desktop notifications on success
  - Logs activity to `~/.config/tux-assistant/native-host.log`
- **Native messaging manifest** - Registered system-wide for Firefox

### Installation Notes
The extension must be loaded manually in Firefox:
1. Go to `about:debugging#/runtime/this-firefox`
2. Click "Load Temporary Add-on..."
3. Navigate to `/opt/tux-assistant/data/tux-browser-extension/`
4. Select `manifest.json`

(Temporary add-ons are removed on Firefox restart. For permanent installation,
the extension would need to be signed by Mozilla and submitted to AMO.)

## [0.9.270] - 2025-12-18

### Changed - Native Wayland, Firefox Icon
- **Reverted X11 hack** - Firefox runs native Wayland again
- **Removed --class flag** - Let Firefox use its default identity
- **StartupWMClass=firefox** - GNOME/KDE will show Firefox icon
- Desktop file simplified, no shell wrapper hacks

The blue diamond was caused by --class setting a WM_CLASS that didn't match
any desktop file. By not overriding, Firefox reports "firefox" and GNOME
matches it to firefox.desktop for proper icon display.

## [0.9.269] - 2025-12-18

### Fixed - Force X11 Mode for Icon Matching
- **GDK_BACKEND=x11** - Force XWayland mode where --class actually works
- **MOZ_ENABLE_WAYLAND=0** - Explicitly disable Wayland backend
- Firefox on native Wayland ignores --class entirely, X11 respects it
- Updated desktop file, app.py, and CLI handler

This is a workaround for Firefox ignoring custom WM_CLASS on Wayland.

## [0.9.268] - 2025-12-18

### Fixed - Wayland Icon Association
- **MOZ_APP_LAUNCHER env var** - Tells Firefox which .desktop file to use for icon
- **Updated StartupWMClass** - Now matches `com.tuxassistant.tuxbrowser`
- **Desktop file Exec** - Sets MOZ_APP_LAUNCHER before launching Firefox
- **Both app.py and CLI** - Consistent icon behavior from Tux Assistant or command line

This should fix the missing icon in GNOME dock on Wayland.

## [0.9.267] - 2025-12-18

### Fixed
- **Desktop file Exec** - Fixed home directory expansion (use sh -c with $HOME)
- **Simplified Firefox launch** - Removed gio launch attempt, direct Firefox call
- **StartupWMClass** - Should match --class flag for icon association

## [0.9.266] - 2025-12-18

### Added - Tux Browser Desktop Integration
- **Tux Browser desktop entry** - Shows in app menu with proper icon
- **Full-color Tux Browser icon** - Tux with globe/web theme (matches Tux Tunes style)
- **`--browser` command line option** - Launch Tux Browser directly: `tux-assistant --browser`
- **URL support** - Open URLs directly: `tux-assistant --browser https://example.com`

### Changed
- Browser can now be launched standalone from app menu or command line

## [0.9.265] - 2025-12-18

### Fixed
- Added missing `subprocess` import for Firefox launcher

## [0.9.264] - 2025-12-18

### Changed - Tux Browser Now Uses Firefox
- **Major: Browser button now launches Firefox** with a managed profile
- Firefox profile stored at `~/.config/tux-assistant/firefox-profile/`
- First launch creates profile with privacy-focused defaults
- User can sign into Firefox Sync to get their extensions, bookmarks, etc.
- **CAPTCHAs now work** - real browser, real extensions, no fingerprinting issues
- Claude AI panel still uses WebKitGTK (works fine for claude.ai)

### Added
- `_setup_firefox_profile()` - Creates Firefox profile with sensible defaults
- `_launch_tux_browser()` - Launches Firefox with managed profile
- `_find_firefox()` - Detects Firefox installation (native, ESR, Flatpak)
- Privacy defaults in user.js: HTTPS-only, tracking protection, no telemetry

### Technical Notes
- WebKitGTK browser code kept for potential future use
- Browser button changed from ToggleButton to regular Button
- Web searches now open in Firefox instead of internal browser

## [0.9.166] - 2025-12-07

### Fixed - SponsorBlock Complete Rewrite
- **Now injects on ALL YouTube pages** - not just watch pages
- **Properly handles SPA navigation** - when you click a video from a channel, it now works
- **Checks if on watch page** before trying to find segments
- **Listens for yt-navigate-finish** - YouTube's internal navigation event
- **Multiple navigation detection methods** - MutationObserver + URL polling + YouTube events
- **Clearer debug messages** - Shows "Not a watch page" when on channel/search/etc.
- **Better video element reset** - Resets when navigating between videos

### How it works now:
1. Script injects when you visit ANY youtube.com page
2. Script continuously monitors for URL changes
3. When URL contains `/watch`, it fetches segments and attaches to video
4. Skip happens automatically when video reaches segment

## [0.9.165] - 2025-12-07

### Fixed
- **SponsorBlock watch pages only** - Only inject on youtube.com/watch pages, not channel pages
- **Better video element selection** - Target #movie_player video specifically
- **Clearer debug output** - Shows segment times with start-end format
- **Improved skip logging** - Shows "Playing: X:XX | Segment at: Y:YY-Z:ZZ" every 10 seconds

### Changed
- Debug box now shows full segment time ranges
- Terminal shows attached video element for debugging

## [0.9.164] - 2025-12-07

### Added
- **SponsorBlock time tracking** - Shows current time vs next segment time every 5 seconds
- **Better video detection** - Checks for video element more frequently

## [0.9.163] - 2025-12-07

### Added
- **SponsorBlock visual debugger** - Green debug box in top-left corner of YouTube
  - Shows exactly what the script is doing in real-time
  - Will tell us if video ID is detected
  - Will show if API fetch succeeds/fails
  - Will show segment count when found
  - Helps diagnose why skipping isn't working

## [0.9.162] - 2025-12-07

### Fixed
- **SponsorBlock complete rewrite** - Now fully JavaScript-based!
  - Injects a monitor script that runs continuously on YouTube
  - Detects video ID from URL OR from YouTube's internal player data
  - Handles SPA navigation (clicking videos from channel pages)
  - Fetches segments via JavaScript fetch() instead of Python
  - Monitors every second for new videos
  - Works on /watch, /shorts, and embedded videos
  - No longer requires page reload to detect videos

## [0.9.161] - 2025-12-07

### Fixed
- **SponsorBlock debugging** - Added extensive logging to diagnose detection issues
  - Logs URL checking on every page load
  - Logs SponsorBlock enabled/disabled state
  - Improved YouTube URL patterns (www., m., shorts)
  - JS console logs showing video detection attempts
  - Fixed urllib.error import for proper HTTP error handling

## [0.9.160] - 2025-12-07

### Added
- **SponsorBlock Integration** 🎉 - Auto-skip YouTube sponsor segments!
  - Uses free SponsorBlock API (sponsor.ajay.app)
  - Skips: Sponsors, Self-promo, Interaction reminders, Intros, Outros
  - Visual notification when skipping ("🛡️ Skipped Sponsor (30s)")
  - Toggle in Privacy Shield popover
  - Runs automatically on any YouTube video page
  - Background API fetch (non-blocking)
  - Handles YouTube SPA navigation

## [0.9.159] - 2025-12-07

### Added
- **Browser Settings Panel** - Complete Phase 4! New settings button (⚙️) with:
  - Homepage URL setting (applied to home button and new tabs)
  - Search engine dropdown (DuckDuckGo, Google, Bing, Startpage, Brave)
  - Default zoom level (50% - 200%)
  - Clear History button
  - Clear Cookies button  
  - Clear Cache button
  - Clear All Data button (with confirmation dialog)
- Search engine setting now applies to:
  - URL bar searches (non-URL text)
  - Main page search box
  - Web search fallback from module search

## [0.9.158] - 2025-12-07

### Added
- **uBlock Origin-style ad blocking** - Smarter banner detection:
  - Banner-sized image detection (IAB standard sizes: 728x90, 300x250, etc.)
  - Ad keyword detection in image URLs (banner, sponsor, affiliate, etc.)
  - Affiliate link detection (ShareASale, Awin, Impact, CJ, etc.)
  - WebKit UserContentFilterStore integration (when available)
  - Network-level blocking rules in Safari/WebKit JSON format

## [0.9.157] - 2025-12-07

### Fixed
- **Privacy Shield v3** - Made ad blocking more conservative
  - Removed overly broad selectors that were hiding legitimate content
  - Now only targets definite ad patterns (ad-container, adsbygoogle, etc.)
  - Removed text-based matching that was too aggressive
  - Sites like Yahoo now display correctly while still blocking ads

## [0.9.156] - 2025-12-07

### Enhanced
- **Privacy Shield v2** 🛡️
  - **CSS-based ad hiding** - Injects stylesheet to hide ad containers, sponsored content, and popups
  - Expanded ad blocklist to 50+ ad networks (added mobile ad networks, verification services)
  - Expanded tracker blocklist to 60+ domains (added analytics APIs, marketing automation, app tracking)
  - Blocks cookie consent banners and GDPR popups
  - Blocks newsletter/subscription popups
  - Hides Taboola, Outbrain, and other "recommended content" widgets

## [0.9.155] - 2025-12-07

### Added
- **Phase 5: Privacy Shield** 🛡️
  - Privacy shield button in browser toolbar
  - **Force HTTPS** - Automatically upgrades HTTP links to HTTPS
  - **Ad Blocking** - Blocks 30+ common ad networks (Google Ads, Facebook Ads, Amazon Ads, etc.)
  - **Tracker Blocking** - Blocks 40+ tracking domains (Google Analytics, Facebook Pixel, Hotjar, etc.)
  - Live blocked count display ("🛡️ X blocked this session")
  - All settings toggleable and persist across sessions
  - Smart blocking: skips localhost and local network addresses

## [0.9.154] - 2025-12-07

### Added
- **Downloads Manager** 📥
  - Downloads button in browser toolbar
  - Shows download progress, completed, and failed downloads
  - Open file button (▶️) to launch downloaded files
  - Open folder button (📁) to open containing folder
  - "Open Downloads Folder" button
  - "Clear" button to remove completed downloads from list
  - Policy handler for proper download detection

### Fixed
- History navigation now works (was calling non-existent method)
- Ampersand characters in URLs now display correctly in history
- Downloads properly trigger via decide-policy handler

## [0.9.153] - 2025-12-07

### Added
- **Downloads Manager** 📥
  - Downloads button in browser toolbar
  - Shows download progress, completed, and failed downloads
  - Open file directly from downloads list
  - Open Downloads folder button
  - Clear completed downloads

## [0.9.152] - 2025-12-07

### Added
- **Print Page (Ctrl+P)** 🖨️
  - Opens system print dialog
  - Print to printer or save as PDF

## [0.9.151] - 2025-12-07

### Added
- **Fullscreen Mode (F11)** 🖥️
  - Press F11 to toggle fullscreen anywhere in the app
  - Press Escape to exit fullscreen
  - Immersive browsing experience
  - Works via window-level handler (not blocked by WebView)

## [0.9.150] - 2025-12-07

### Added
- **Find in Page (Ctrl+F)** - Phase 4 begins! 🔍
  - Search bar appears at bottom of browser
  - Live search as you type
  - Match count display
  - Previous/Next navigation (Shift+Enter / Enter)
  - Case-insensitive with wrap-around
  - Escape to close
  - Visual feedback for no matches

### Fixed
- Keyboard shortcuts use CAPTURE phase to intercept before WebView
- Focus returns to webview after closing find bar (fixes Ctrl+F not working after first use)

## [0.9.149] - 2025-12-07

### Added
- **Persistent Zoom Level** - Browser remembers your zoom preference
  - Saved to `~/.config/tux-assistant/browser.conf`
  - Applied to all tabs automatically
  - Persists between app launches

## [0.9.148] - 2025-12-07

### Added
- **Browser Zoom Controls** 🔍
  - Ctrl++ (or Ctrl+=): Zoom in
  - Ctrl+-: Zoom out
  - Ctrl+0: Reset to 100%
  - Ctrl+Scroll wheel: Zoom in/out (throttled for smooth scrolling)
  - Zoom range: 30% to 300%
  - Toast notification shows current zoom level (keyboard shortcuts only)

### Changed
- **Browser opens wide by default** - When docked, browser now takes most of the window, leaving just enough navigation sidebar to browse. Makes the browser the star of the show!

## [0.9.147] - 2025-12-07

### Added - Browser Phase 3: Complete History System 🎉

**History Database**
- SQLite database at `~/.config/tux-assistant/history.db`
- Frecency scoring (frequency × recency) for smart autocomplete
- Auto-records every page visit with title
- 200MB / 500k entry limits designed for years of daily use
- Background maintenance: cleanup and VACUUM without UI freeze

**History Panel**
- New history button in browser toolbar (clock icon)
- Dropdown showing recent history with time grouping
- Sections: Today, Yesterday, This Week, Older
- Search, delete individual entries, clear by time range

**Full History Window**
- Dedicated window for comprehensive history management
- Time filter: All Time, Today, Yesterday, This Week, This Month
- Search by URL or title
- Multi-select with bulk delete
- Keyboard shortcuts: Delete, Ctrl+A, Ctrl+F, Escape

**URL Bar Autocomplete**
- Smart suggestions as you type (2+ characters)
- Frecency-ranked results - your frequent sites appear first
- Bookmarks (⭐) prioritized over history (🕐)
- Keyboard navigation: Up/Down arrows, Enter, Escape

### Fixed
- Browser panel now builds lazily (fixes startup on some systems)
- Clear history uses dialog instead of nested popover

## [0.9.143] - 2025-12-07

### Added
- **Complete Tags System** - Phase 2 complete! 🎉
  - Tag filter dropdown in Bookmark Manager header
  - Tags displayed on bookmark rows (up to 3 inline, "+N" for more)
  - Full tag editing in bookmark edit dialog:
    - Current tags shown as removable chips
    - Add new tags via entry (Enter to add)
    - Click suggestions from existing tags
  - Tag Management dialog (tag icon in header):
    - View all tags with bookmark counts
    - Rename tag (updates all bookmarks)
    - Delete tag (removes from all bookmarks)
  - Search includes tag names
  - Tags stored as `["tag1", "tag2"]` array in bookmark data

## [0.9.142] - 2025-12-07

### Added
- **Full Bookmark Manager window** - Phase 2 milestone!
  - Dedicated window for comprehensive bookmark management
  - Multi-select support (Ctrl+Click, Shift+Click)
  - Bulk delete selected bookmarks
  - Move selected to folder dropdown
  - Create new folders from manager
  - Edit bookmark details inline
  - Search/filter all bookmarks
  - Folders shown as collapsible sections
  - Keyboard shortcuts: Delete, Ctrl+A (select all), Ctrl+F (search), Escape (close)
  - Access via "Manage..." button in bookmark dropdown

## [0.9.140] - 2025-12-06

### Fixed
- **Separator drag & drop COMPLETE** - Full reordering support!
  - Separators can now be dragged and reordered on toolbar
  - Bookmarks can be dragged past separators
  - Drop ON widgets to reorder (standard GTK4 behavior)
  - Uses proper `GObject.TYPE_STRING` content providers
  - Added `accept` signal handlers for reliable drop acceptance
  - Removed parent bar drop target that was intercepting child drops

### Technical Details
- `_on_unified_drop` handler for all toolbar reordering
- `_on_drop_accept` always returns True to accept drops
- `set_preload(True)` on all drop targets for reliable data transfer
- Typed `GObject.Value` instead of raw bytes for DnD content

## [0.9.139] - 2025-12-06

### Fixed
- **Separator drag & drop** - Separators can now be reordered via drag & drop
  - Updated reorder handler to find separators (they have no URL)
  - Added drag source to toolbar separators (previously static)
  - Separators in dropdown list can be dragged to reorder
  - Separators in toolbar can be dragged to reorder

## [0.9.138] - 2025-12-06

### Added
- **Bookmark Separators** - Add visual separators between bookmarks
  - New "Separator" button in bookmarks popover
  - Separators appear as horizontal lines in dropdown list
  - Separators appear as vertical lines in toolbar
  - Can delete separators with trash icon
  - Separators can be dragged to reorder

## [0.9.137] - 2025-12-06

### Fixed
- **Drag from folder popover to toolbar** - Fixed critical bug where dragging bookmarks OUT of folder popovers in toolbar didn't work
  - Root cause: autohide=True was closing popover when drag started, destroying the widget mid-drag
  - Solution: Disable autohide on folder popovers, close manually when drag begins
  - Added separate drag handlers for popover rows
- Removed debug output

## [0.9.136] - 2025-12-06

### Fixed
- **Drag from folder to toolbar** - Fixed bug where dragging a bookmark from a folder popover to the toolbar didn't work (reorder handler only searched unfiled bookmarks, now searches all)

## [0.9.135] - 2025-12-06

### Added
- **Drag from folder popovers** - Bookmarks inside folder dropdowns in toolbar now have drag sources
- Drag a bookmark out of a folder dropdown and drop on toolbar to unfiled
- Complete drag & drop: dropdown ↔ toolbar ↔ folder popovers

## [0.9.134] - 2025-12-06

### Added
- **Drag from toolbar** - Bookmark buttons in the toolbar now have drag sources
- **Reorder in toolbar** - Drag and drop bookmarks to reorder them in the toolbar
- Drop on another bookmark to swap positions
- Tooltip now shows "(drag to reorder)"

## [0.9.133] - 2025-12-06

### Fixed
- **Drag and drop crash** - Fixed force close when dropping bookmarks (used instance variable instead of DnD type system)
- Added error handling to all drag/drop callbacks

### Added
- **Drop to bookmarks bar** - Drag bookmarks onto folder buttons in the toolbar
- **Drop to bar itself** - Drag to the bar area to move to unfiled
- Tooltips now indicate drop capability ("drop to add")

## [0.9.132] - 2025-12-06

### Added
- **Drag and drop bookmarks** - Drag bookmarks between folders
  - Drag handle icon on each bookmark row
  - Drop on folder header to move bookmark into folder
  - Drop on "Unfiled" section to remove from folder
  - Visual highlight when dragging over drop targets
  - Drag icon shows bookmark title

## [0.9.131] - 2025-12-06

### Fixed
- **tux-helper Permission denied error** - Fixed issue where privileged operations failed with "Permission denied" error on .run installer or when running from extracted location. The helper script now gets execute permissions automatically before running.

## [0.9.130] - 2025-12-06

### Added
- **Folders in bookmarks bar** - Folders show as dropdown menus with their bookmarks
- **Empty folders visible** - Empty folders now show in the list with "(empty)" indicator
- **Delete folder button** - Trash icon on each folder to delete it (bookmarks move to Unfiled)
- Folder expanders now properly collapse/expand their contents

## [0.9.129] - 2025-12-06

### Added
- **Bookmark Folders** - Organize bookmarks into folders
  - "New Folder" button to create folders
  - Folder dropdown when adding/editing bookmarks
  - Folders shown as collapsible expanders in bookmarks list
  - Unfiled bookmarks shown separately
  - Clear All now also clears folders
- Backwards compatible with existing bookmarks (auto-migrates old format)

## [0.9.128] - 2025-12-06

### Added
- **Show/Hide Bookmarks Bar toggle** - Switch in bookmarks dropdown to show or hide the bookmarks bar
- Preference saved to `~/.config/tux-assistant/browser.conf`

## [0.9.127] - 2025-12-06

### Fixed
- Bookmarks popover now closes properly when clicking outside after using sort dropdown

## [0.9.126] - 2025-12-06

### Added
- **Ctrl+D shortcut** - Quickly bookmark/unbookmark current page
- **Sort bookmarks** - Dropdown to sort by Default, Name A-Z, Name Z-A, or Recent
- **Favicons** - Website icons shown next to bookmarks (cached locally)
- Bookmarks now store timestamps for "Recent" sorting

## [0.9.125] - 2025-12-06

### Added
- **Bookmark Manager Enhancements (Phase 2.5)**
  - **Search bar** - Filter bookmarks by title or URL in real-time
  - **Add button** - Manually add bookmarks with custom title and URL
  - **Edit button** - Modify existing bookmark title and URL
  - Edit and delete buttons now shown on each bookmark row

## [0.9.124] - 2025-12-06

### Fixed
- **Browser panel sizing issue** - Bookmarks bar now scrolls horizontally instead of expanding the window beyond screen bounds

## [0.9.123] - 2025-12-06

### Added
- **Bookmarks Bar** - Visual bar below URL bar showing bookmarks as buttons
  - Click any bookmark to navigate directly
  - Shows up to 15 bookmarks with "+N more" indicator
  - Auto-updates when bookmarks change
- **Clear All Bookmarks** - Red "Clear All" button in bookmarks dropdown
  - Confirmation dialog before deleting
  - Shows count of bookmarks to be deleted

## [0.9.122] - 2025-12-06

### Added
- **Bookmark Import/Export (Phase 2 Complete)**
  - Import button: Load bookmarks from Firefox/Chrome HTML format
  - Export button: Save bookmarks to HTML (compatible with all browsers)
  - Automatically skips duplicate URLs on import
  - Standard Netscape bookmark format for maximum compatibility

## [0.9.121] - 2025-12-06

### Added
- **Browser Bookmarks (Phase 2)**
  - Star button in toolbar to add/remove current page
  - Bookmarks menu button with dropdown list
  - Click bookmark to navigate
  - Delete button on each bookmark
  - Bookmarks saved to `~/.config/tux-assistant/bookmarks.json`
  - Star icon updates based on current URL (filled = bookmarked)

## [0.9.120] - 2025-12-06

### Fixed
- **System Fetch now works on Fedora 43+** - added ptyxis terminal support
- Terminal detection uses exact same code as Developer Tools (which works)
- Added ptyxis to all terminal detection lists across the app

## [0.9.117] - 2025-12-06

### Fixed
- **System Fetch button now finds terminal on all distros**
  - Uses proper terminal detection from `core/commands.py`
  - Supports: konsole, kgx (gnome-console), gnome-terminal, xfce4-terminal, mate-terminal, qterminal, lxterminal, tilix, terminator, alacritty, kitty, foot, wezterm, and more

### Changed
- **System Fetch button moved under Hardware** in System Information section

## [0.9.116] - 2025-12-06

### Changed
- System Fetch button placed in System Information section

## [0.9.115] - 2025-12-06

### Changed
- **Tux Tunes button moved to header bar** - now next to Claude and Browser buttons
- **Sidebar removed** (code preserved for future use)
- Cleaner main page layout without right sidebar

## [0.9.114] - 2025-12-06

### Changed
- **Search bar moved above system info banner** on main page
- **Removed TuxFetch sidebar panel** - no more fastfetch in the sidebar
- **Added System Fetch button** in "Quick Tools" section at bottom of main page
  - Opens fastfetch in your terminal (gnome-terminal, konsole, xfce4-terminal, kitty, alacritty, tilix, xterm)
  - Shows "Press Enter to close..." after output

### Fixed
- **Tab close now works properly** - can close any tab except the last one
- **No more tab explosion** when trying to close the last tab

## [0.9.113] - 2025-12-06

### Added - Tabbed Browser (Phase 1)
- **Full tabbed browsing in Tux Browser!**
  - Adw.TabView + Adw.TabBar for modern libadwaita tabs
  - Open unlimited tabs, each with its own webview
  - Tab titles auto-update to page title
  - Close tabs with X button (always keeps at least one tab)
  - New tab button in toolbar

- **Keyboard shortcuts**
  - Ctrl+T: New tab
  - Ctrl+W: Close current tab
  - Ctrl+L: Focus URL bar
  - Ctrl+Tab: Next tab
  - Ctrl+Shift+Tab: Previous tab
  - Ctrl+R: Reload page

- **Shared browser session**
  - All tabs share cookies and cache
  - Stay logged in across tabs
  - Downloads work from any tab

## [0.9.100] - 2025-12-05

### Fixed
- **Tux Tunes icon now appears in AUR installs**
  - Added `tux-assistant.install` hook file to update icon cache after install
  - Runs `gtk-update-icon-cache` and `update-desktop-database` on post_install/post_upgrade
  - Added `hicolor-icon-theme` as dependency to ensure base icon theme exists
  - Updated PKGBUILD and .SRCINFO to include the install hook

## [0.9.99] - 2025-12-05

### Fixed
- **Bluetooth toggle now works on XFCE/Arch** (and other systems)
  - Fixed `bluetoothctl` command syntax - args were incorrectly combined
  - Changed from `['bluetoothctl', 'power on']` to `['bluetoothctl', 'power', 'on']`
  - Added instant visual feedback: button shows "Enabling..." / "Disabling..." during operation
  - Operation runs in background thread to prevent UI freeze

- **XFCE themes no longer revert after applying**
  - Now sets both GTK theme (`xsettings`) AND window manager theme (`xfwm4`)
  - Without setting xfwm4, window decorations wouldn't match and could revert on session restart

## [0.9.98] - 2025-12-05

### Fixed
- **AUR publish button now works reliably**
  - Fixed path mismatch: was using `~/.cache/tux-assistant/aur/tux-assistant`, now uses `~/.cache/tux-assistant/aur-repo`
  - Added `git reset --hard` before pull to handle local changes
  - Added `--rebase` to pull to handle diverged branches
  - If pull fails, automatically re-clones fresh
  - Better error messages showing actual failure reason

## [0.9.97] - 2025-12-05

### Fixed
- **AUR publish now works from any distro** (not just Arch-based)
  - .SRCINFO is generated in Python, doesn't require makepkg
  - Fixed branch handling - explicitly uses 'master' (what AUR requires)
  - Auto-detects current branch instead of hardcoding
  - Better error messages on push failure
  - Cleans up broken repo directories before fresh clone

## [0.9.96] - 2025-12-05

### Fixed
- **Software Center: Fixed dnf5 package parsing** on Fedora 43+
  - Package names were including arch suffix and description in install command
  - Improved parsing to handle tab, multiple spaces, or single space separators
  - Added safety sanitization to strip .x86_64/.noarch suffix and descriptions
  - Package names are now properly cleaned before installation

## [0.9.95] - 2025-12-05

### Fixed
- **Codec detection now checks if packages are INSTALLED first** before checking repo availability
  - Fixes bug where already-installed packages showed as "unavailable" 
  - Fixes Fedora ffmpeg detection when installed from RPM Fusion
- Added binary existence fallback for ffmpeg detection (handles package name variations)
- Packages that are already installed will now correctly show as installed regardless of repo state

## [0.9.94] - 2025-12-05

### Fixed
- **AUR PKGBUILD now installs Tux Tunes properly:**
  - Added `/usr/bin/tux-tunes` launcher script
  - Added `/usr/share/applications/com.tuxassistant.tuxtunes.desktop`
  - Added `/usr/share/icons/hicolor/scalable/apps/tux-tunes.svg`
- Added GStreamer dependencies to AUR package (gstreamer, gst-plugins-base, gst-plugins-good)
- Added optional GStreamer plugins (ugly, bad) for extended audio format support

## [0.9.93] - 2025-12-05

### Fixed
- Fixed zypper command syntax (`--non-interactive` instead of `-y`)
- Added fallback package names if distro not recognized
- Ensures rpm-build is properly installed for Fedora/openSUSE RPM builds

## [0.9.92] - 2025-12-05

### Added
- **Auto-dependency installation** for package building:
  - Detects distro (Arch, Fedora, openSUSE, Debian/Ubuntu)
  - Auto-installs `ruby` if missing
  - Auto-installs `binutils` (provides `ar`) for .deb builds
  - Auto-installs `rpm-build` for .rpm builds
  - Shows helpful dialog if auto-install fails with manual command
- Support for EndeavourOS, Manjaro, Rocky Linux, CentOS, Mint, Pop!_OS detection

## [0.9.91] - 2025-12-05

### Fixed
- fpm detection now checks `gems/fpm-*/bin/fpm` path (user-install location)
- Uses glob to find fpm regardless of version number in path
- Should now correctly find fpm after `gem install --user-install fpm`

## [0.9.90] - 2025-12-05

### Fixed
- Simplified fpm detection - removed execute permission check that was failing
- Now just checks if file exists (Ruby scripts don't always have +x)
- Added more gem path locations to search

## [0.9.89] - 2025-12-05

### Fixed
- fpm path detection now USES the found path instead of asking user to update PATH
- Added Ruby 3.4.0 to fallback paths
- Should now work without requiring PATH modification

## [0.9.88] - 2025-12-05

### Improved
- fpm PATH errors now show a dialog instead of a toast
- Dialog includes exact commands to add fpm to PATH
- Dialog stays visible until dismissed

## [0.9.87] - 2025-12-05

### Fixed
- fpm detection now uses Ruby to dynamically find gem bin path
- Checks `Gem.user_dir` and `gem environment gempath` for correct locations
- Shows actual path to add to PATH if fpm still not found

## [0.9.86] - 2025-12-05

### Fixed
- Package builder now properly finds fpm in common gem paths
- Removed problematic --after-install flag from fpm command
- Better error reporting when files are missing
- Added path verification before package build

## [0.9.85] - 2025-12-05

### Fixed
- Fixed Developer Tools not loading (was using wrong container method)

## [0.9.84] - 2025-12-05

### Added
- **DEB/RPM Package Builder** in Developer Tools:
  - Build .deb packages for Debian/Ubuntu/Mint/Pop!_OS
  - Build .rpm packages for Fedora/RHEL/CentOS/Rocky
  - Build .rpm packages for openSUSE Tumbleweed/Leap
  - Auto-installs fpm (Ruby gem) if not present
  - Output to ~/Tux-Assistant-Packages/ folder
  - Auto-opens folder after successful build
  - Proper dependency lists for each distribution family

## [0.9.83] - 2025-12-05

### Added
- **Expanded content type support** for native theme installer:
  - More icon variations: gnome-icons, xfce-icons, cinnamon-icons, mate-icons
  - More cursor variations: x11-cursors, mouse-cursors, xcursor
  - More wallpaper types: backgrounds, wallpapers-uhd, wallpapers-4k
  - SDDM login themes → ~/.local/share/sddm/themes
  - Latte Dock layouts → ~/.config/latte
  - Rofi themes → ~/.config/rofi/themes
  - Font variations: ttf-fonts, otf-fonts

## [0.9.82] - 2025-12-05

### Added
- **Multi-DE theme support** - Native installer now handles all desktop environments:
  - GNOME, XFCE, Cinnamon, MATE (GTK themes → ~/.themes)
  - KDE Plasma themes → ~/.local/share/plasma/desktoptheme
  - KDE Look-and-Feel → ~/.local/share/plasma/look-and-feel
  - Aurorae window decorations → ~/.local/share/aurorae/themes
  - Kvantum themes → ~/.config/Kvantum
  - KDE color schemes → ~/.local/share/color-schemes
  - Konsole themes, Yakuake skins
  - Conky configs, Plank dock themes
- **More theme sites allowed** in browser:
  - xfce-look.org, cinnamon-look.org, mate-look.org
  - enlightenment-themes.org, linux-apps.com

## [0.9.81] - 2025-12-05

### Fixed
- Added missing `pathlib` import for native theme installer

## [0.9.80] - 2025-12-05

### Changed
- **Native theme installer** - Replaced abandoned ocs-url with built-in handler
- Downloads themes directly from gnome-look.org without third-party tools
- Extracts to correct location based on type (~/.themes, ~/.icons, etc.)
- Supports tar.xz, tar.gz, tar.bz2, and zip archives

### Removed
- Removed all ocs-url installation code (tool is abandoned since 2017)
- Removed terminal popup for ocs-url installation

## [0.9.79] - 2025-12-05

### Added
- **Theme Preview & Install** - Embedded browser for gnome-look.org themes
- **ocs-url integration** - One-click theme installation via ocs:// links
- Auto-installs ocs-url helper when needed (AUR on Arch, manual on others)
- Themes not in repos now show "Preview & Install" instead of just external link
- Intercepts ocs:// links in WebKit browser and handles installation

## [0.9.78] - 2025-12-05

### Fixed
- **Fedora codec detection fix** - Added `ffmpeg-free` (Fedora native) to codec list
- Codecs now properly detected on Fedora without RPM Fusion enabled
- Native Fedora packages listed first, RPM Fusion packages as extras

### Added
- **RPM Fusion Enable button** - One-click enable RPM Fusion repos on Fedora
- **Show locked packages** - RPM Fusion packages now shown with lock icon and "Enable Repos" button
- Page auto-refreshes after enabling repos to show newly available packages

## [0.9.77] - 2025-12-05

### Added
- **Complete README overhaul** with all 10 screenshots
- Added screenshots folder with properly named images
- AUR installation instructions in README
- Feature highlights table

### Changed
- README now showcases: Main, Setup Tools, Software Center, Gaming, Desktop Enhancements, Networking, Media Server, Hardware Manager, System Maintenance, and Tux Tunes

## [0.9.76] - 2025-12-05

### Fixed
- Fixed AUR publish button - `gh release view` now runs from correct directory

## [0.9.75] - 2025-12-05

### Added
- **"Publish to AUR" button** - One click to push to Arch User Repository
- Generates PKGBUILD and .SRCINFO automatically (works from any distro!)
- Downloads tarball, calculates sha256sum, pushes to AUR
- Tux Assistant is now available on AUR: `yay -S tux-assistant`

## [0.9.74] - 2025-12-04

### Fixed
- **Speed Test now works on Fedora!** Added support for Ptyxis (Fedora 43's default terminal)
- Terminal detection now prioritizes: ptyxis → kgx → gnome-terminal → konsole → xfce4-terminal
- Fixed terminal launch across all modules (networking, developer tools)

## [0.9.73] - 2025-12-04

### Changed
- **Simplified Developer Tools** - Reduced from 8 rows to 4 rows
- **New "Install from ZIP" button** - One click to extract, copy, and install from Claude's ZIP
- **New "Publish Release" button** - One click for full workflow: commit → push → build .run → create GitHub release
- Status row now shows version, branch, and SSH status in one compact line
- Updated help guide to match new 2-button workflow

### Removed
- Separate Pull/Push buttons (integrated into Publish)
- Separate "Build .run Only" and "Build & Push to Main" buttons (merged into Publish)
- Separate "Create GitHub Release" button (merged into Publish)
- Separate Refresh Status row (now an icon button)

## [0.9.72] - 2025-12-04

### Changed
- **Extensions now install AND enable immediately!** Uses DBus `InstallRemoteExtension` like Extension Manager
- No more "log out and back in" - extensions are ready to use right away
- Falls back to manual download method if DBus fails

## [0.9.71] - 2025-12-04

### Added
- **GitHub Release button** in Developer Tools → Tux Assistant Development
- Creates proper GitHub release with tag and uploads .run file
- Checks for `gh` CLI and shows install instructions if missing
- Confirmation dialog before publishing

## [0.9.70] - 2025-12-04

### Fixed
- Fixed missing icons in Extensions Browser tabs (globe → web-browser, starred → emblem-default)

## [0.9.69] - 2025-12-04

### Added
- **Installed / Browse tabs** like Extension Manager app
- **Popular extensions** load by default in Browse tab (in background)
- Search box with results that replace the list
- Spinner while loading popular extensions

### Changed
- UI now matches Extension Manager app style
- Popular extensions load AFTER UI is visible (100ms delay)
- Uses GLib.timeout_add to ensure UI renders first

## [0.9.68] - 2025-12-04

### Changed
- **Complete rewrite of Extensions Browser** - Now uses filesystem instead of gnome-extensions command!
- Reads extensions directly from `~/.local/share/gnome-shell/extensions/` and `/usr/share/gnome-shell/extensions/`
- Parses `metadata.json` files for extension info (instant, no subprocess calls)
- Single `gsettings` call for enabled status
- Search only queries API when user explicitly searches (no pre-loading)
- Simpler, faster, no freezing!

## [0.9.67] - 2025-12-04

### Fixed
- **Extensions browser no longer freezes!** Replaced slow per-extension info calls with fast bulk queries
- Now uses `--user` and `--system` flags instead of calling `gnome-extensions info` for each extension
- Loading time reduced from 10+ seconds to under 1 second

## [0.9.66] - 2025-12-04

### Added
- **GNOME Extensions Browser** - Full-featured extension manager built into Tux Assistant!
  - Browse extensions directly from extensions.gnome.org
  - Search functionality with instant results
  - One-click install with GNOME version compatibility checking
  - View installed extensions (User vs System separated)
  - Enable/disable toggles for each extension
  - Uninstall user extensions
  - Global "Use Extensions" toggle
  - Extension settings access
  - Popular extensions shown by default
- New "Browse & Manage Extensions" option in Desktop Enhancements → GNOME Extensions

### Fixed
- **All loading is now async** - No more "Not Responding" dialogs!
- Page loads instantly with a spinner while data loads in background
- All subprocess calls run in background threads

## [0.9.65] - 2025-12-03

### Added
- External links in embedded browser now open in default system browser!
- Links that try to open new windows (target="_blank") open in Firefox/Chrome
- Claude panel external links also open in default browser

## [0.9.64] - 2025-12-03

### Fixed
- Removed "Smart recording limited" toast notification (since recording is disabled)
- No more annoying popups about missing libraries

## [0.9.63] - 2025-12-03

### Removed
- Removed record button from Tux Tunes UI (code preserved for future)
- No password prompts at startup

## [0.9.62] - 2025-12-03

### Changed
- Disabled Tux Tunes recording temporarily (all distros) - code preserved for future
- Disabled auto audio dependency install (no more password prompts at startup!)
- Record button shows "Recording coming soon" tooltip
- To re-enable: set auto_record=True in player.py, _recording_enabled=True in window.py

## [0.9.61] - 2025-12-03

### Changed
- Disabled Tux Tunes recording on Fedora (Python 3.14 incompatible with numba/librosa)
- Record button shows "Recording unavailable on Fedora" tooltip
- Auto-recording also disabled on Fedora
- Recording works on Arch, Debian, Ubuntu, openSUSE

## [0.9.60] - 2025-12-03

### Fixed
- Record button now actually SAVES the file! 🎉
- Recordings saved to ~/Music/Tux Tunes/ with station name and timestamp
- Shows toast notification with filename when saved
- Cleans up cache file after copying

## [0.9.59] - 2025-12-03

### Added
- Manual Record button in Tux Tunes! 🎙️
- Button appears between Stop and Volume controls
- Shows red stop icon when recording, normal record icon when not
- Tooltip shows current state (Start/Stop Recording)

### Notes
- librosa cannot install on Python 3.14 (Fedora 43) - numba doesn't support 3.14 yet
- Recording works without librosa - just no audio visualization

## [0.9.58] - 2025-12-03

### Fixed
- librosa needs scipy! Now installs python3-scipy via dnf BEFORE pip install librosa
- Added scipy to the checked/installed dependencies list
- System packages (numpy, scipy) installed first, then pip packages (pydub, librosa)

## [0.9.57] - 2025-12-03

### Fixed
- Fixed audio deps AGAIN - pydub is NOT in Fedora repos!
- Now: numpy via dnf, then install pip, then pydub+librosa via pip
- Proper order: install python3-pip BEFORE trying to use pip
- Better error messages showing actual failure reason

## [0.9.56] - 2025-12-03

### Fixed
- PROPERLY fixed audio deps - uses system package manager (dnf/apt/pacman) instead of pip!
- Fedora: installs python3-numpy, python3-pydub via dnf
- Debian/Ubuntu: installs python3-numpy, python3-pydub via apt
- Arch: installs python-numpy, python-pydub via pacman
- Only librosa uses pip (not in system repos)
- Also installs python3-pip if needed before pip operations

## [0.9.55] - 2025-12-03

### Fixed
- Fixed pip not found on Fedora - now uses `python3 -m pip` which works on ALL distros
- No more searching for pip binary - uses sys.executable directly

## [0.9.54] - 2025-12-03

### Fixed
- ACTUALLY fixed audio dependency auto-install at startup (was silently failing)
- Non-daemon thread so pip installs complete properly
- Multiple pip command detection (/usr/bin/pip3, pip3, pip)
- Better error logging to console
- Fallback without --break-system-packages for older distros

## [0.9.53] - 2025-12-03

### Fixed
- Fixed Fedora multimedia codecs installation - now properly enables RPM Fusion repos first!
- Both RPM Fusion Free and Nonfree are auto-enabled before installing codec packages
- Updated all RPM Fusion URLs from download1.rpmfusion.org to mirrors.rpmfusion.org (more reliable)
- Fixed duplicate desktop icons - now uses single GNOME-standard naming (com.tuxassistant.app.desktop)
- install.sh now cleans up old naming convention on upgrade
- Fixed audio dependencies (numpy, librosa, pydub) not installing on Fedora
- Added --break-system-packages flag for pip on Fedora 39+
- App now auto-checks and installs missing audio deps at startup (all distros)

## [0.9.51] - 2025-12-03

### Fixed
- Fixed hardinfo2 terminal install on Fedora (added ptyxis, fixed kgx syntax)
- Fixed Developer Tools branch warning (now expects main, not dev)
- Updated all Dev Branch references to Main Branch for main-only workflow
- Pull/Push buttons now work correctly with main branch

## [0.9.50] - 2025-12-03

### Fixed
- Added kgx (GNOME Console) and ptyxis terminal support for Fedora
- All terminal operations now work on Fedora Workstation!

## [0.9.49] - 2025-12-03

### Added
- Developer Kit import now shows "Unlock SSH Key" button after import
- Automatic prompt to clone projects after unlocking SSH
- Full guided flow: Import → Unlock → Clone all projects!

## [0.9.48] - 2025-12-03

### Changed
- Switched license from "All Rights Reserved" to GPL-3.0
- Updated all copyright headers across 34+ files
- More Linux community friendly!

## [0.9.47] - 2025-12-03

### Fixed
- Floating windows now use Gtk.Window (not Adw.Window) for proper Wayland move/drag support

## [0.9.46] - 2025-12-03

### Fixed
- Floating windows (Claude/Browser) are now fully movable/draggable

## [0.9.45] - 2025-12-03

### Added - Global Web Browser Panel!
- 🌐 button in header bar toggles web browser panel
- URL bar with search (DuckDuckGo) or direct URL entry
- Navigation: back, forward, reload, home
- Pop-out button to make browser a floating window
- Smart panel logic: first clicked gets side panel, second opens floating
- Both Claude and Browser can be open simultaneously!
- Downloads work in browser too

### Changed
- Removed embedded Claude from Developer Tools (now global - less confusion!)
- Developer Tools back to clean single-column layout

## [0.9.44] - 2025-12-02

### Added - Global Claude AI Toggle!
- 🤖 button in header bar toggles Claude AI panel on ANY page
- Panel slides in from right on all pages (not just Developer Tools)
- Click again to hide - panel remembers state
- Same WebKit setup with persistent cookies
- Same download handling
- Claude now available everywhere in the app!

## [0.9.43] - 2025-12-02

### Fixed - Downloads Now Work!
- Removed file:// prefix from set_destination() - THIS WAS THE BUG!
- Added MIME type detection for correct file extensions
- Debug output when running from terminal (harmless, useful for troubleshooting)
- Downloads now save to ~/Downloads with correct filenames

## [0.9.42] - 2025-12-02

### Fixed - Download Filename Detection
- Added MIME type detection to get correct file extension
- Maps common types: .zip, .txt, .html, .py, .json, .md, .pdf, .png, etc.
- Fallback name now includes extension: claude_download_TIMESTAMP.zip
- Allows parentheses in filenames (e.g., "Tux Assistant (v0.9.41).zip")
- Removed debug print statements

## [0.9.41] - 2025-12-02

### Added - Resizable Claude Panel & Download Support
- Changed from Gtk.Box to Gtk.Paned for split layout
- Draggable divider between Dev Tools and Claude panel
- Drag left to make Claude bigger, drag right to make it smaller
- Minimum width of 350px for Claude panel
- Left side expands with window, right side stays fixed width
- **Download handling**: Files now download to ~/Downloads
- Toast notifications for download started/completed/failed
- Handles duplicate filenames with _1, _2 suffix

## [0.9.40] - 2025-12-02

### Changed - Claude WebView: Use GNOME Web-style Configuration
- Use NetworkSession.new() with custom data/cache directories (WebKit 6.0)
- Fallback to WebContext cookie manager for older WebKit2
- Persistent cookies stored in ~/.local/share/tux-assistant/webview/
- Cache stored in ~/.cache/tux-assistant/webview/
- Changed user agent to match GNOME Web/Epiphany (Safari-based)
- Enabled more web features: mediasource, encrypted_media
- Should work like GNOME Web for Cloudflare verification

## [0.9.39] - 2025-12-02

### Fixed - Claude WebView Crash
- Fixed Developer Tools page not loading due to WebKit API incompatibility
- Added try/except fallback for WebView creation
- Detects WebKit 6.0 (NetworkSession) vs older WebKit2 APIs
- Falls back to basic WebView if advanced features fail
- All settings wrapped in try/except for cross-version compatibility
- Still attempts persistent cookies on WebKit 6.0+

## [0.9.38] - 2025-12-02

### Changed - Claude WebView: Persistent Storage & Better Browser Emulation
- Added persistent cookie/data storage in ~/.local/share/tux-assistant/claude-webview
- Added cache storage in ~/.cache/tux-assistant/claude-webview
- Cookies persist between sessions (should help with Cloudflare verification)
- Enabled HTML5 local storage and database
- Enabled hardware acceleration and WebGL
- Enabled page cache and smooth scrolling
- Updated user agent to Chrome 131 (current version)
- Set cookie accept policy to ALWAYS
- Goal: Pass Cloudflare's "Verify you are human" check

## [0.9.37] - 2025-12-02

### Changed - Claude AI: Split Layout with Pop-out
- Developer Tools now has split layout (like front page)
- Left side: Git tools, prerequisites, dev kit, etc.
- Right side: Claude AI panel (450px wide)
- Embedded WebKitGTK webview loads claude.ai
- Navigation toolbar: back, forward, reload, home
- **Pop-out feature**: Click window icon to open Claude in separate window
- **Pop-in feature**: Click restore icon to bring Claude back to panel
- When popped out, panel shows "Claude is in a separate window" with pop-in button
- Closing the Claude window automatically pops it back in
- External browser button to open claude.ai in default browser

## [0.9.36] - 2025-12-02

### Added - Claude AI Assistant Integration
- New "Claude AI Assistant" section in Developer Tools
- Dedicated window with WebKitGTK webview to load claude.ai
- Navigation toolbar: back, forward, reload, home buttons
- Option to open Claude in external browser
- Auto-detects WebKit availability (WebKit 6.0 or WebKit2 5.0)
- Shows install button with distro-specific commands if WebKit not found
- Custom user agent for better compatibility

## [0.9.35] - 2025-12-02

### Removed - ISO Creator Module
- Removed ISO Creator (penguins-eggs wrapper) from the application
- penguins-eggs installation methods are too unstable:
  - Repository URLs frequently change/break
  - fresh-eggs script has incomplete distro support
  - Package names vary across distros
- Module preserved in git history if needed later
- Simplifies maintenance and improves stability

## [0.9.33] - 2025-12-02

### Fixed - Git Identity Dialog Not Opening
- Fixed `GitIdentityDialog` not appearing when clicking Configure button
- Changed from broken emit/response pattern to callback pattern
- Dialog now properly shows and saves git config
- Added `_refresh_prereq_section()` to update UI after configuration

## [0.9.32] - 2025-12-02

### Changed - ISO Creator: Universal fresh-eggs Installer
- Replaced distro-specific penguins-eggs installation methods with fresh-eggs
- fresh-eggs auto-detects distribution and uses appropriate install method
- More maintainable - adapts to upstream repo URL changes automatically
- Supports all distros: Arch, Manjaro, Debian, Ubuntu, Fedora, openSUSE, AlmaLinux, Rocky
- Added git availability check before installation
- Fixes 404 error on openSUSE due to changed repo URLs

## [0.9.31] - 2025-12-02

### Added - Change Hostname Feature
- Network & Sharing page now has edit button on Hostname row
- New `ChangeHostnameDialog` for changing system hostname
- Uses `hostnamectl` via tux-helper for safe hostname changes
- Validates hostname format (letters, numbers, hyphens only)
- Added `--set-hostname` option to tux-helper

## [0.9.30] - 2025-12-02

### Fixed - Gtk.show_uri Focus Across All Modules
- Changed `Gtk.show_uri(self.window, ...)` to `Gtk.show_uri(None, ...)` in all modules
- Fixes file manager and browser windows appearing behind Tux Assistant
- Affected: networking.py, media_server.py, nextcloud_setup.py

## [0.9.29] - 2025-12-02

### Fixed - Usershare Detection (Manjaro/Dolphin/KDE)
- `get_shares()` now checks BOTH sources:
  1. `/etc/samba/smb.conf` (admin-created shares)
  2. `net usershare info --long` (GUI-created shares from Dolphin, Nautilus, etc.)
- Fixes shares not appearing on distros using `kdenetwork-filesharing` or similar
- Properly parses usershare ACL to determine writable status

## [0.9.28] - 2025-12-02

### Fixed - File Manager Focus
- Changed share folder click from `subprocess.Popen(['xdg-open'...])` to `Gtk.show_uri()`
- File manager now properly comes to front when clicking a share
- Added `Gdk` import to networking.py

## [0.9.27] - 2025-12-02

### Added - Auto-Refresh UI Across All Modules

Comprehensive UI feedback improvements - actions now provide instant visual feedback:

**Media Server:**
- Added refresh button to header
- Page auto-rebuilds when install dialog closes
- Server status updates immediately after installation

**Repository Manager (Setup Tools):**
- When repo is enabled, row transforms to show checkmark icon
- No more stale "Enable" buttons after successful enable

**Software Center:**
- Selection clears after install completes
- Checkboxes reset, install button disables
- Toast confirms "Installation complete - selection cleared"

**Desktop Enhancements:**
- Theme selection clears after install
- Checkboxes reset automatically
- Toast confirms completion

**Technical Implementation:**
- Added `on_complete_callback` parameter to:
  - `InstallServerDialog` / `InstallProgressDialog` (media_server.py)
  - `AppInstallDialog` (software_center.py)
  - `PlanExecutionDialog` (desktop_enhancements.py)
- Callbacks fire when dialogs close, triggering UI refresh
- 300ms delay allows services to fully initialize

## [0.9.26] - 2025-12-02

### Added - Auto-Refresh Share Section

The Share Files section now automatically refreshes after:
- Enabling file sharing (no need to navigate away and back)
- Creating a new share (share appears instantly in the list)

**Implementation:**
- Store references to `self.content_box` and `self.share_section`
- `_refresh_share_section()` - removes old section and creates new one in place
- `_execute_plan_with_refresh()` - executes plan and triggers refresh when dialog closes
- 500ms delay before refresh to allow services to fully start

## [0.9.25] - 2025-12-02

### Added - Comprehensive File Sharing Setup

When file sharing service is not running or not installed, clicking "Enable File Sharing" now sets up EVERYTHING needed for successful cross-platform file sharing:

**What Gets Installed & Configured:**
1. **Samba packages** - samba, smbclient, cifs-utils
2. **Avahi (mDNS/Bonjour)** - Makes your PC visible to macOS and other Linux machines
3. **wsdd** - Web Services Discovery Daemon - Makes your PC visible to Windows 10/11
4. **Firewall rules** - Opens samba and mDNS ports (firewalld or ufw)
5. **Optimized smb.conf** - Includes:
   - macOS compatibility (fruit VFS module)
   - Windows compatibility
   - Performance optimizations
   - Disabled printing (cleaner for home users)

**Services Enabled:**
- smbd/smb (Samba file server)
- nmbd/nmb (NetBIOS name service)
- avahi-daemon (mDNS/Bonjour)
- wsdd (Windows discovery)

**Implementation:**
- `SambaManager.get_discovery_packages()` - Returns avahi, nss-mdns, wsdd per distro
- `SambaManager.create_full_sharing_plan()` - Creates comprehensive setup plan
- `_on_enable_full_sharing()` - Handler for enable button

## [0.9.24] - 2025-12-02

### Added - List Current Samba Shares

Enhanced the "Share Files" section to show currently shared folders:

**New Features:**
- Lists each shared folder individually under "Share a Folder"
- Shows share name as title, path as subtitle
- Clickable rows open the folder in file manager
- Icons indicate share type:
  - Public share icon for guest-accessible shares
  - Documents icon for writable shares
  - Folder icon for read-only shares
- Shows "No folders shared" when none configured
- Shows warning when Samba service not running

**Implementation:**
- `_on_open_share_folder()` - opens share path with xdg-open

## [0.9.23] - 2025-12-02

### Fixed - Single Package Install Command

Fixed the individual package install button failing immediately:

**The Problem:**
- Used `tux-helper install` instead of `tux-helper --install`
- tux-helper didn't recognize the command, returned error

**The Fix:**
- Changed `['pkexec', '/usr/bin/tux-helper', 'install', package]`
- To `['pkexec', '/usr/bin/tux-helper', '--install', package]`

## [0.9.22] - 2025-12-02

### Added - Clickable Install Button for Individual Packages

Made the "+" icon next to uninstalled packages an actual clickable button:

**New Behavior:**
- Click the "+" button to install just that one package
- Button shows loading spinner during install
- Changes to green checkmark (✓) on success
- Shows "Retry" on failure
- Package status count updates automatically after install
- Toast notification confirms success/failure

**Implementation:**
- `_on_install_single_package()` - handles button click, runs install in background
- `_on_single_package_installed()` - updates UI after install completes
- Uses `tux-helper` for consistent package installation across distros

## [0.9.21] - 2025-12-02

### Fixed - TA Dev Push SSH Environment

Fixed the purple "Push" button in TA Development section not using SSH agent:

**The Problem:**
- `_do_ta_push_dev()` ran `git push` without passing SSH environment
- Even after unlocking SSH key, push would fail with "ssh_askpass" error
- User had to manually run `git push` from terminal

**The Fix:**
- Added `ssh_env = self._get_ssh_env()` at start of push function
- Passed `env=ssh_env` to all subprocess.run git operations
- Also fixed `_do_ta_release()` to use SSH env consistently for all git commands

## [0.9.20] - 2025-12-02

### Fixed - Package Status UI (Follow-up)

Fixed issues from v0.9.19:

**Spinner Row Not Disappearing:**
- Stored spinner_row as instance variable for explicit removal
- Changed from iterating children (unreliable with PreferencesGroup) to direct removal
- Spinner row now properly disappears when package check completes

**Count Logic Fixed:**
- Status now based on AVAILABLE packages, not total wishlist
- If 13 packages available and all 13 installed = "✓ All 13 packages installed"
- Previously showed "13/14 installed" when 1 package was unavailable

**Removed Deprecated Package:**
- Removed `neofetch` from Arch and Fedora package lists (deprecated/unmaintained)
- `fastfetch` is already included as the replacement

## [0.9.19] - 2025-12-02

### Improved - Package Status UI Feedback

Replaced the perpetual "Checking packages..." spinner with clear status feedback:

**The Problem:**
- Spinner row with "Checking packages..." would stay visible even after package check completed
- Users didn't know if checking was done or how many packages were installed

**The Fix:**
- Added `check_package_installed()` function to check actual installation status
- After checking completes, spinner is replaced with status summary row showing "X/Y installed"
- Group title now shows "Packages (X/Y installed)" instead of "Packages to Install (N)"
- Installed packages show green checkmark (✓)
- Available-but-not-installed packages show plus icon (+) with "Not installed" subtitle
- Status row shows:
  - All installed: "✓ All N packages installed" (green)
  - Partial: "X of Y packages installed" with "N remaining to install"
  - None: "0 of N packages installed" with guidance

## [0.9.18] - 2025-12-01

### Fixed - Install.sh Symlink Corruption Bug

Fixed critical bug where install.sh would corrupt tux-assistant.py:

**The Problem:**
- Old installations left a symlink at `/usr/local/bin/tux-assistant` pointing to `/opt/tux-assistant/tux-assistant.py`
- When install.sh ran `cat > "$BIN_LINK"`, it wrote THROUGH the symlink
- This overwrote the Python file with bash launcher content
- Result: App wouldn't launch from icon

**The Fix:**
- Added `rm -f "$BIN_LINK"` before creating launcher
- Added `rm -f "$TUXTUNES_BIN"` before creating Tux Tunes launcher
- Removes any existing symlinks before writing new launcher scripts

## [0.9.17] - 2025-12-01

### Fixed - Share Folder Dialog Hidden Behind Main Window

Fixed Quick Share dialog disappearing behind main window on GNOME:

**The Problem:**
- FileDialog used main window as parent
- When FileDialog closed, focus returned to main window
- Adw.Dialog (overlay) got covered by its own parent

**The Fix:**
- FileDialog now uses `None` as parent (independent window)
- Dialog stays visible after folder selection

## [0.9.16] - 2025-12-01

### Fixed - hardinfo2 Install on openSUSE

Fixed hardinfo2 install button crash on openSUSE:

**The Problem:**
- Code used `DistroFamily.SUSE` which doesn't exist
- Correct enum value is `DistroFamily.OPENSUSE`

**The Fix:**
- Changed `DistroFamily.SUSE` to `DistroFamily.OPENSUSE`

## [0.9.15] - 2025-12-01

### Fixed - hardinfo2 Install Button Not Working

Fixed hardinfo2 install button doing nothing on openSUSE/GNOME:

**The Problem:**
- Multi-line install scripts with special characters failed when passed directly to terminal
- `kgx -e bash -c "multi\nline\nscript"` doesn't work reliably

**The Fix:**
- Now writes install script to a temp file first
- Executes the script file instead of inline commands
- Script self-deletes after completion
- Works reliably across all terminal emulators

## [0.9.14] - 2025-12-01

### Fixed - Samba Install Detection on openSUSE

Fixed Samba showing as "Not installed" even when installed on openSUSE:

**The Problem:**
- Install check looked for `smbd` binary using `shutil.which()`
- On openSUSE, `smbd` is installed to `/usr/sbin/` which is not in normal user PATH
- Result: Samba appeared uninstalled even though it was working

**The Fix:**
- Now also checks `/usr/sbin/smbd` directly
- Works on all distros regardless of PATH configuration

## [0.9.13] - 2025-12-01

### Fixed - Terminal Emulator Support

Fixed "Could not find terminal emulator" error across the entire application:

**The Problem:**
- Multiple places in the code had limited terminal lists (only 4-6 terminals)
- openSUSE GNOME uses gnome-console (kgx) which wasn't supported
- Many popular terminals were missing
- Code was duplicated in 13+ places

**The Fix:**
- Created centralized terminal helper functions in `tux/core/commands.py`:
  - `get_terminal_commands(script_path)` - Returns all terminal commands
  - `find_terminal()` - Finds first available terminal
  - `run_in_terminal(script_path)` - Runs script in terminal
- Added comprehensive terminal support (20+ terminals):
  - GNOME: gnome-console/kgx, gnome-terminal
  - KDE: konsole
  - XFCE: xfce4-terminal
  - MATE: mate-terminal
  - LXQt/LXDE: qterminal, lxterminal
  - Popular: tilix, terminator, alacritty, kitty, foot, wezterm
  - Lightweight: sakura, terminology, urxvt, rxvt, st
  - Fallback: xterm
- Updated hardinfo2 installation to use comprehensive terminal list
- Updated repository enable (Packman, etc.) to use comprehensive list
- Improved error message suggests installing a terminal if none found

## [0.9.12] - 2025-12-01

### Fixed - Tux Tunes GNOME Icon

Fixed Tux Tunes icon not appearing in GNOME dock/launcher:

**The Problem:**
- Install script only installed Tux Assistant icon and desktop file
- Tux Tunes had no system-installed icon or desktop entry
- GNOME couldn't match the running window to its icon

**The Fix:**
- Added Tux Tunes icon installation (`tux-tunes.svg`)
- Added Tux Tunes desktop file with `StartupWMClass=com.tuxassistant.tuxtunes`
- Desktop file named `com.tuxassistant.tuxtunes.desktop` (GNOME best practice)
- Cleans up old `tux-tunes.desktop` if exists

**To apply:** Reinstall via "Install to System" button.

## [0.9.11] - 2025-12-01

### Fixed - tux-helper Packaging

Fixed tux-helper not being included in .run installer:
- Added `tux-helper` to build-run.sh package list
- Install no longer fails with "tux-helper: No such file or directory"

### Fixed - openSUSE Audio Dependencies

Fixed Tux Tunes audio dependencies for openSUSE:
- Added `ffmpeg` to zypper package list
- Fixed pip librosa install with `--user --break-system-packages` flags
- Now properly installs: python3-numpy, python3-pydub, ffmpeg, librosa

### Fixed - Packman Repository Enable

Fixed "Enable Packman" button failing silently on openSUSE:
- Changed from background subprocess to terminal script (for password prompt)
- Added GPG key auto-import with `--gpg-auto-import-keys refresh`
- Now opens terminal window for proper sudo authentication

## [0.9.10] - 2025-12-01

### Fixed - GTK Markup Warnings

Fixed GTK warnings about ampersand characters in markup:
- Escaped `&` as `&amp;` in all titles and labels
- Affected: "Backup & Restore", "Help & Learning", "Setup & Help", "Build & Release", etc.
- App now runs without GTK-WARNING messages

## [0.9.9] - 2025-12-01

### Added - Repository Manager

New "Repository Manager" section in Setup Tools showing all package sources:

**Currently Enabled Repositories:**
- Shows all repos configured on your system
- Arch: Lists all pacman repos (core, extra, multilib, endeavouros, etc.)
- Fedora: Lists all dnf repos
- Debian/Ubuntu: Lists apt sources
- openSUSE: Lists zypper repos
- All: Shows Flatpak remotes

**Available to Enable:**
- Flathub (all distros)
- Arch: Multilib, AUR Helper (yay)
- Fedora: RPM Fusion Free, RPM Fusion Nonfree
- openSUSE: Packman

Each item shows status (✓ Enabled or Enable button) at a glance.

## [0.9.8] - 2025-12-01

### Fixed - GNOME Icon Display

Fixed the icon not appearing in GNOME dock/launcher:

**The Problem:**
- Install script was creating a desktop file without `StartupWMClass`
- GNOME couldn't match the running window to its icon
- Result: Generic gear icon instead of Tux penguin

**The Fix:**
- Added `StartupWMClass=com.tuxassistant.app` to installed desktop file
- Renamed desktop file to `com.tuxassistant.app.desktop` (GNOME best practice)
- Cleans up old `tux-assistant.desktop` if exists

**To apply:** Reinstall via "Install to System" button.

## [0.9.7] - 2025-11-30

### Added - Git Workflow Help Guide

Added "Setup & Help" button to Developer Tools that opens a comprehensive guide:

- **Quick Start** - 6-step GUI workflow for updates
- **Troubleshooting** - Common errors and fixes (SSH issues, commit errors)
- **Manual Commands** - Full terminal fallback command

No more guessing how to use the Git features!

## [0.9.6] - 2025-11-30

### Changed - Module Organization

Moved Gaming and Desktop Enhancements to Setup and Configuration category for better flow:

**Setup and Configuration now contains:**
1. Setup Tools
2. Software Center
3. Gaming
4. Desktop Enhancements

## [0.9.5] - 2025-11-30

### Fixed - SSH Agent Persistence

Fixed the SSH unlock button so it actually works for subsequent git operations:

**The Problem:**
- SSH agent was started in a terminal, but when that terminal closed, 
  the SSH_AUTH_SOCK environment variable was lost
- Tux Assistant's git operations never saw the unlocked key

**The Fix:**
- SSH unlock now saves agent info to `~/.ssh/agent-info`
- All git operations (push, pull, Build & Push to Main) now load this file
- Terminal-based git commands also source the agent info
- SSH status check now properly detects unlocked keys

**How it works now:**
1. Click "Unlock SSH Key" → enter passphrase → terminal closes
2. Agent info is saved to a file that persists
3. Push/Pull buttons read this file and use the running agent
4. Works until you log out or reboot

## [0.9.4] - 2025-11-30

### Changed - Category Order

Reordered the main menu categories for better user flow:

1. Setup and Configuration
2. Media and Entertainment
3. Network and Sharing
4. System and Maintenance
5. Server and Cloud
6. Developer Tools

## [0.9.3] - 2025-11-30

### Fixed - Ubuntu/GNOME Compatibility

Bug fixes discovered during Ubuntu 24.04 testing on Lenovo T450s:

**Install to System fixes:**
- tux-helper now properly installed to /usr/bin/ (fixes Samba install, codecs, etc.)
- App icon now displays correctly in GNOME app launcher
- Icon installed to standard hicolor theme location
- Desktop database updated after install

**Browse Network fix:**
- GNOME/Nautilus now opens network browser correctly
- Uses `network:///` for GNOME, `smb://` for KDE/others
- Previously did nothing on Ubuntu due to `smb://` not working in Nautilus

**Tux Tunes dependency fix:**
- Added GStreamer pbutils packages for Ubuntu (gir1.2-gst-plugins-base-1.0)
- Tux Tunes no longer crashes on first launch

**Smart Recording dependencies:**
- Added pip, numpy, pydub to all distro package lists
- Attempts to install librosa via pip after package install
- Reduces "Smart recording limited" warnings

**Packages added to dependency installer:**
- apt: gir1.2-gst-plugins-base-1.0, gstreamer1.0-plugins-good, python3-pip, python3-numpy, python3-pydub
- pacman: gst-plugins-base, gst-plugins-good, python-pip, python-numpy, python-pydub  
- dnf: gstreamer1-plugins-base, gstreamer1-plugins-good, python3-pip, python3-numpy, python3-pydub
- zypper: gstreamer-plugins-base, gstreamer-plugins-good, python3-pip, python3-numpy, python3-pydub

## [0.9.2] - 2025-11-30

### Added - SSH Key Unlock Button

The Tux Assistant Development panel now includes an "Unlock SSH Key" button:

**How it works:**
1. Click "Unlock SSH Key" 
2. A terminal opens asking for your SSH passphrase
3. Enter passphrase once
4. SSH key stays unlocked for your session
5. Push/Pull buttons now work without prompting!

**Features:**
- Shows current SSH status (Locked/Unlocked)
- Auto-detects your SSH key (ed25519, RSA, or ECDSA)
- Works with gnome-terminal, konsole, xfce4-terminal, and others
- Status auto-refreshes after unlocking
- Refresh button also updates SSH status

**Why this helps:**
- Git push/pull from GUI apps can't show the passphrase prompt
- Unlocking once at start of session makes all git operations smooth
- No more stuck terminals waiting for invisible passphrase input!

## [0.9.1] - 2025-11-30

### Added - Tux Assistant Development Panel

New section in Developer Tools specifically for Tux Assistant development:

**Features:**
- Shows current branch (dev/main) with status indicator
- Detects uncommitted changes
- **Pull Dev** - Switches to dev branch and pulls latest
- **Push Dev** - Prompts for commit message, commits, and pushes to dev
- **Build .run Only** - Runs build-run.sh to create distributable
- **Build & Push to Main** - Full release workflow:
  1. Builds .run file
  2. Switches to main branch  
  3. Copies .run to releases/
  4. Commits and pushes to main
  5. Switches back to dev

**Auto-detection:**
- Only appears if Tux Assistant repo found at:
  - ~/Development/Tux-Assistant
  - ~/Development/tux-assistant
  - ~/Projects/Tux-Assistant
  - Or similar locations

This makes the git workflow much easier - no more remembering terminal commands!

## [0.9.0] - 2025-11-30 - First Public Release 🎉

### Overview
First public release of Tux Assistant - a comprehensive Linux system configuration 
tool with a modern GTK4/Libadwaita interface.

### Features
- **Multi-Distribution Support** - Arch, Debian, Fedora, openSUSE and derivatives
- **System Information** - Fastfetch-powered system info panel in sidebar
- **Software Center** - Browse and install apps by category
- **Setup Tools** - One-click codec, driver, and essential app installation
- **Gaming** - Steam, Lutris, and gaming utilities setup
- **Developer Tools** - Git manager, SSH keys, development environments
- **Desktop Enhancements** - Themes, extensions, and tweaks (GNOME, KDE, XFCE)
- **Hardware Manager** - Printers, Bluetooth, displays, audio configuration
- **Networking** - WiFi, file sharing, hotspot, speed tests
- **Advanced Networking** - VPN, Active Directory, firewall, Samba
- **Media Server** - Plex, Jellyfin, Emby setup
- **Nextcloud Server** - Personal cloud setup
- **Backup & Restore** - System snapshots and file backup
- **ISO Creator** - Create bootable ISOs from your system
- **Tux Tunes** - Bonus internet radio player with smart recording!

### Distribution
- Self-extracting `.run` file - works on any Linux distribution
- Automatic dependency installation (Python, GTK4, Libadwaita)
- "Install to System" button for permanent installation
- Portable mode - run without installing

### Technical
- GTK4 + Libadwaita for modern GNOME-style UI
- Modular architecture for easy extension
- Responsive design - adapts to window size
- Window size persistence between sessions

---

## Development History

The version numbers below reflect internal development history.

## [5.14.7] - 2025-11-30

### Changed - TuxFetch Uses Real Fastfetch

Complete rewrite of TuxFetch to use actual fastfetch output:

**How it works:**
1. Checks if fastfetch is installed
2. If not, offers to install it (pacman/apt/dnf/zypper)
3. Runs fastfetch with optimized settings for sidebar width
4. Strips ANSI color codes for clean monochrome display
5. Falls back to basic info if fastfetch unavailable

**Benefits:**
- 100% accurate logos and information
- Honors fastfetch project (uses their tool, doesn't copy)
- Monochrome display is distinctly "TuxFetch"
- User's fastfetch config is respected
- Dramatically simpler code (~200 lines vs ~1200)

**Settings used:**
- `--logo-width 12` - Fits sidebar
- `--logo-padding-top 0` - Compact
- `--logo-padding-left 0` - Left aligned
- `--logo-padding-right 1` - Small gap before info

**Fallback output (if no fastfetch):**
- user@hostname
- OS, Kernel, Uptime, Shell, DE
- CPU, Memory
- Hint to install fastfetch

## [5.14.6] - 2025-11-30

### Fixed - Distro Logo Accuracy

**Dynamic Logo Detection:**
- Now tries to fetch logo from fastfetch if installed
- Extracts clean ASCII art directly from fastfetch output
- Falls back to built-in logos only if fastfetch unavailable

**Improved Built-in Logos:**
- Cleaner, simpler ASCII art that renders properly
- No special Unicode characters that might break
- Proper escape sequences for backslashes

**Distros with built-in logos:**
- EndeavourOS, Arch, Manjaro, CachyOS, Garuda
- Debian, Ubuntu, Linux Mint, Pop!_OS
- Fedora, openSUSE, Zorin
- Generic Tux for unknown distros

**Why fastfetch-first approach:**
- Fastfetch has 300+ logos maintained by the community
- Always accurate and up-to-date
- Our built-in logos are just fallbacks

## [5.14.5] - 2025-11-30

### Changed - Tux Tunes Moved to Sidebar

Relocated Tux Tunes from the module list to the sidebar:

**New Layout:**
- Tux Tunes button at top of sidebar
- TuxFetch system info below it
- Scrollable area at bottom for future widgets

**Benefits:**
- Quick access without scrolling
- Stays visible as you scroll modules
- Module list focused on setup/config tasks
- Sidebar becomes a "dashboard" with info + quick tools

**Styling:**
- Accent-colored button with gradient
- Music note icon (🎵)
- Title and subtitle
- Hover effect

**Removed:**
- Tux Tunes no longer appears in "Media and Entertainment" category

## [5.14.4] - 2025-11-30

### Fixed - Accurate Distro ASCII Logos

Updated ASCII logos to match fastfetch style more closely:

**Logos Added/Improved:**
- EndeavourOS - Curved mountain peak shape (not generic triangle)
- Arch Linux - Classic A-frame design
- Manjaro - Blocky M with squared corners
- CachyOS - Arch derivative with icon
- Garuda - Bird/eagle shape
- Debian - Classic swirl
- Ubuntu - Circle of friends
- Linux Mint - Leaf shape
- Pop!_OS - Stylized P
- Fedora - Infinity loop
- openSUSE - Gecko/chameleon
- Zorin - Z shape
- Generic Tux - Penguin for unknown distros

**Detection:**
- Exact distro ID matching first
- Partial name matching for derivatives
- Family-based fallback (Arch family gets Arch logo, etc.)

## [5.14.3] - 2025-11-30

### Added - Comprehensive System Info (Fastfetch Parity)

TuxFetch now displays nearly all the info that fastfetch shows:

**System:**
- OS (with architecture)
- Host (laptop/PC model name)
- Kernel
- Uptime
- Packages (with package manager)
- Shell (with version)

**Display/Desktop:**
- Display resolution
- DE (with version: KDE Plasma 6.x, GNOME 4x, etc.)
- WM (KWin, Mutter, Sway, etc.)
- Theme (GTK theme)
- Icons (icon theme)
- Terminal (with version)

**Hardware:**
- CPU
- GPU
- Memory (with progress bar)
- Swap usage
- Disk (with progress bar)

**Network/Power:**
- Local IP address
- Battery status (for laptops: percentage, charging state)
- Locale

Now we're at ~90% feature parity with fastfetch! 🐧

## [5.14.2] - 2025-11-30

### Changed - Sidebar Layout Fix

Split the right sidebar into two distinct areas:

**Top: Fixed TuxFetch Panel**
- Compact system info display
- Stays fixed at the top
- Doesn't expand to fill space

**Bottom: Scrollable Dark Area**
- Dark background matching main content
- Scrollable independently
- Reserved for future widgets/modules
- Shows "More widgets coming soon..." placeholder

**Styling:**
- Main sidebar has border-left separator
- Bottom area uses darker background
- Clean visual separation between fixed and scrollable areas

## [5.14.1] - 2025-11-30

### Changed - TuxFetch Sidebar Redesign

Reworked TuxFetch to be a fixed sidebar that blends with the window:

**New Design:**
- Fixed position (doesn't scroll with content)
- Blends into window chrome (subtle background, border)
- More compact layout (~280px wide)
- Smaller, denser information display
- Progress bars for RAM and Disk usage
- Compact ASCII logos

**Layout:**
- Sidebar stays visible as you scroll modules
- Content area scrolls independently
- Clean separation between content and info panel

**Visual:**
- Subtle left border
- Semi-transparent background
- Smaller font sizes
- Thin progress bars (4px height)

## [5.14.0] - 2025-11-30

### Added - TuxFetch System Info Panel 🐧

**Fastfetch-style system information display on the main page!**

A beautiful side panel showing:
- **User & Hostname** - user@hostname header
- **ASCII Distro Logo** - Arch, Debian, Ubuntu, Fedora, openSUSE, Manjaro, and more
- **OS** - Distribution name
- **Kernel** - Linux kernel version
- **Uptime** - How long system has been running
- **Packages** - Count of installed packages (pacman/dpkg/rpm)
- **Shell** - Current shell (bash, zsh, fish, etc.)
- **DE** - Desktop environment
- **WM** - Window manager / display server
- **Resolution** - Screen resolution
- **Terminal** - Terminal emulator
- **CPU** - Processor model (shortened)
- **GPU** - Graphics card (shortened)
- **Memory** - RAM usage with percentage
- **Disk** - Root partition usage with percentage
- **Color Palette** - Terminal color blocks

**Responsive Design:**
- Panel automatically hides on windows narrower than 900px
- Default window size increased to 1280x850 to show panel
- Window size is remembered between sessions

**Native Implementation:**
- No external dependencies (no fastfetch required)
- Uses existing hardware detection code
- Lightweight and fast

### Changed
- Main page now uses horizontal layout (modules left, TuxFetch right)
- Module list clamp reduced to 750px to make room for panel

## [5.13.3] - 2025-11-30

### Improved - Distribution Future-Proofing

**ID_LIKE Fallback Detection**
- Added fallback to `ID_LIKE` field in `/etc/os-release`
- New distros that properly declare their base (e.g., `ID_LIKE="arch"`) will work automatically
- No need to manually add every new derivative to our lists

**dnf5 Support (Fedora 41+)**
- Added automatic detection of `dnf5` vs `dnf`
- Fedora is transitioning to dnf5 as default package manager
- Both distro.py and tux-helper now check for dnf5 first

**How Future-Proofing Works:**
1. We detect by **family** (Arch, Debian, Fedora, openSUSE), not specific versions
2. Package managers (`pacman`, `apt`, `dnf`, `zypper`) are stable within families
3. New distros set `ID_LIKE` in os-release → we detect them automatically
4. If a distro changes package managers, we detect the binary on disk

**What Still Requires Updates:**
- New distros that don't set `ID_LIKE` properly
- Major package name changes (rare)
- Entirely new package managers (we'd need to add support)

## [5.13.2] - 2025-11-30

### Changed - Main Page Module Order

Reordered modules to create a natural progression from "new to Linux" to "power user":

**Tier 1: Fun & Familiar** (New User Hooks)
1. Tux Tunes - Fun music player to explore first
2. Help & Learning - "I'm new, help me!"
3. Software Center - Install apps like an app store

**Tier 2: Windows Refugee Essentials**
4. Gaming - "Can I play my games?"
5. Hardware Manager - Printers, Bluetooth, audio
6. Networking - WiFi, file sharing
7. Desktop Enhancements - Make it look nice

**Tier 3: System Care**
8. System Maintenance - Updates, cleanup
9. Backup & Restore - Protect your files

**Tier 4: Power User / Advanced**
10. Setup Tools - System configuration
11. Advanced Networking - VPN, AD, firewall
12. Developer Tools - Git, coding

**Tier 5: Specialized**
13. Media Server - Plex, Jellyfin
14. Nextcloud Server - Self-hosted cloud
15. ISO Creator - Create custom distros

## [5.13.1] - 2025-11-30

### Fixed - Module ID References
- Updated fun_facts.py to use `networking_simple` instead of old `networking` ID
- Prevents potential errors when fun facts try to navigate to networking module

**Note on ChatGPT suggestion:** The stacked decorator approach for backward compatibility wouldn't work correctly in Python. The simpler fix is to update references to use the new module IDs directly.

## [5.13.0] - 2025-11-30

### Added - Help & Learning Module 🎓

**The final TODO priority is COMPLETE!**

#### Interactive Tutorials
Step-by-step guides for Linux beginners:
- **Terminal Basics** - Learn the command line without fear
- **Installing Software** - Package managers, Flatpak, and more
- **Files & Folders** - Navigate Linux file structure
- **Updates & Security** - Keep your system safe

#### "I Want To..." Quick Tasks
One-click shortcuts to common tasks:
- Play a DVD
- Connect to WiFi
- Print a document
- Install an application
- Play games
- Back up files
- Share files on network
- Customize desktop
- Update system
- Fix audio problems

#### Troubleshooter
Guided diagnosis for common problems:
- **No Sound** - Audio troubleshooting
- **WiFi Not Working** - Network diagnosis
- **Printer Not Working** - Print queue and CUPS
- **System Running Slow** - Performance fixes
- **App Keeps Crashing** - Stability help
- **Bluetooth Problems** - Connection issues

#### Quick Reference
- Essential keyboard shortcuts
- Linux terminology explained
- Links to online help resources

### Summary
**All 6 TODO priorities are now COMPLETE! 🎉**
- ✅ System Maintenance (v5.8.0)
- ✅ Backup & Restore (v5.10.0)
- ✅ Gaming (v5.9.0)
- ✅ Hardware Manager (v5.11.0)
- ✅ Networking Additions (v5.12.0)
- ✅ Help & Learning (v5.13.0)

## [5.12.4] - 2025-11-30

### Improved - Cross-Distro Compatibility (REAL fixes)

**tux-helper improvements:**
- Added `steam` and `lutris` to Fedora RPM Fusion auto-enable list
- Added openSUSE `games:tools` repository auto-enablement for gaming packages
- Gaming packages (steam, lutris, gamemode, mangohud) now auto-enable required repos

**Gaming module fixes:**
- Added `xboxdrv` package for openSUSE
- Updated controller descriptions to be more accurate
- DualSense (PS5) controller noted as working out of box on modern kernels

**Documentation:**
- Created `docs/DISTRO_AUDIT_HONEST.md` with real status of what's verified vs assumed
- Marked packages that need real-world testing on each distro

### Known Limitations (Being Honest)
- Only tested thoroughly on Arch-based distros (CachyOS/Start-DE)
- Debian, Fedora, openSUSE need real hardware testing
- ds4drv not available via package manager on Fedora/openSUSE (pip or AUR only)
- Some packages may still fail if repos aren't available

**The "It Just Works" promise requires real testing on each distro family.**

## [5.12.3] - 2025-11-30

### Fixed - Distro Compatibility Audit
- **Hardware Manager:** Added system-config-printer to openSUSE CUPS install
- **Backup & Restore:** openSUSE Timeshift now adds required Archiving:Backup repo before install
- **Backup & Restore:** Added note about snapper (openSUSE's native BTRFS snapshot tool)
- **Documentation:** Added docs/DISTRO_PACKAGES.md with full package availability matrix

### Verified Package Availability
- CUPS, Bluetooth tools, rsync, speedtest-cli: All distros ✅
- Timeshift: All distros (openSUSE needs extra repo) ✅
- Gaming apps: Flatpak fallback for Bottles/ProtonUp-Qt on non-Arch ✅

## [5.12.2] - 2025-11-30

### Fixed - Install Plan Format
- Fixed package installation plan format in Networking module
- Plans now use correct `tasks` format expected by tux-helper
- Affects: speedtest-cli, OpenVPN plugin, WireGuard installs

## [5.12.1] - 2025-11-30

### Changed - Split Networking into Simple and Advanced

**Networking** (Simple - for everyone):
- Network status (IP, WiFi connection)
- WiFi settings and hidden network connection
- Share a Folder (quick Samba share)
- Find Shared Folders (network scan)
- Hotspot, Speed Test, Network Settings

**Advanced Networking** (for power users):
- Full network status with Samba/AD info
- VPN setup (OpenVPN, WireGuard)
- Active Directory / Domain join
- Firewall port management
- Advanced Samba management
- Hosts file editor

This follows the "Timmy Test" - new users see simple options, power users can find advanced features.

## [5.12.0] - 2025-11-30

### Added - Networking Additions
Major expansion of the Networking module:

**WiFi Management**
- View current WiFi status (connected/disconnected)
- Open WiFi settings
- Connect to hidden networks

**VPN Support**
- View VPN connection status
- Import OpenVPN (.ovpn) configurations
- Import WireGuard (.conf) configurations
- Offers to install missing plugins (networkmanager-openvpn, wireguard-tools)
- Open VPN settings

**Network Tools**
- Create WiFi Hotspot (share your connection)
- Stop existing hotspot
- Speed Test (uses speedtest-cli, offers to install)
- Edit /etc/hosts file
- Open system network settings

All features work with NetworkManager and support GNOME, KDE, and XFCE settings apps.

## [5.11.3] - 2025-11-30

### Fixed - Printer Setup Same Pattern as Bluetooth
Now properly handles all printer states:

| State | What Shows |
|-------|-----------|
| CUPS not installed | "Install CUPS" button |
| Service stopped | "Start Service" button |
| No printers | "Add Printer" button |
| Has printers | Printer list + "Add Printer" |

- Installs cups, cups-pdf, and system-config-printer
- Enables and starts service automatically after install
- UI refreshes after installation completes

## [5.11.2] - 2025-11-30

### Fixed - Bluetooth UX Completely Rewritten
Dynamic UI that rebuilds based on actual state:

| State | What Shows |
|-------|-----------|
| No tools | "Install Bluetooth" button |
| Service stopped | "Start Service" button |
| No adapter | Informative message |
| Bluetooth off | "Enable Bluetooth" button |
| Bluetooth on | "Disable" button + paired devices + settings |

- No more confusing toggle switches
- Each state has ONE clear action
- "Bluetooth Settings" now offers to install Blueman if no manager found
- Proper state transitions without getting stuck

## [5.11.1] - 2025-11-30

### Fixed - Bluetooth Setup Help
- Detects when Bluetooth tools are not installed → offers "Install" button
- Detects when Bluetooth service is stopped → offers "Start Service" button  
- Detects when no Bluetooth adapter is present → shows informative message
- Installs bluez/bluez-utils and enables service automatically
- Works across all distro families

## [5.11.0] - 2025-11-30

### Added - Hardware Manager Module (NEW!)
Friendly interface for managing hardware:

**Printers**
- List configured printers with status
- Start CUPS if not running
- Add printer button (opens system-config-printer or CUPS web)

**Bluetooth**
- Power on/off toggle
- List paired devices with connection status
- Open system Bluetooth settings for pairing

**Audio**
- List output devices (speakers, headphones)
- List input devices (microphones)
- Set default device with one click
- Open system sound settings

**Displays**
- Show connected monitors with resolution/refresh rate
- Indicate primary display
- Open system display settings

Works with GNOME, KDE, and XFCE settings tools.

## [5.10.2] - 2025-11-30

### Enhanced - Backup Destination Options
- Now shows ALL drives: internal, external, and network
- Drives labeled with type icons: 💾 Internal, 🔌 External, 🌐 Network, 📁 Custom
- **Browse...** button to select any folder as backup destination
- **Network...** button with connection wizard:
  - Samba (Windows shares) with optional username/password
  - NFS support
  - Creates mount point automatically
- Auto-detects already-mounted network shares (CIFS/NFS)

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
- **GitHub**: github.com/dorrellkc
