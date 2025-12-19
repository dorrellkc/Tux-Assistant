#!/bin/bash
#===============================================================================
#
#   Tux Assistant - Installer
#
#   A polished installer that makes setup painless.
#   (Not a PITA - the pain OR the bread)
#
#   Copyright (c) 2025 Christopher Dorrell. Licensed under GPL-3.0.
#
#===============================================================================

set -e

# Colors for pretty output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Installation paths
INSTALL_DIR="/opt/tux-assistant"
BIN_LINK="/usr/local/bin/tux-assistant"
TUXTUNES_BIN="/usr/local/bin/tux-tunes"
DESKTOP_DIR="/usr/share/applications"
ICON_DIR="/usr/share/icons/hicolor"
POLKIT_FILE="/usr/share/polkit-1/actions/com.tuxassistant.helper.policy"

# App info
VERSION=$(cat VERSION 2>/dev/null || echo "5.0.0")

#-------------------------------------------------------------------------------
# Helper Functions
#-------------------------------------------------------------------------------

print_banner() {
    echo -e "${PURPLE}"
    echo "  ╔═══════════════════════════════════════════╗"
    echo "  ║                                           ║"
    echo "  ║   🐧  Tux Assistant Installer  🐧        ║"
    echo "  ║                                           ║"
    echo "  ║   Version: $VERSION                         ║"
    echo "  ║                                           ║"
    echo "  ╚═══════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "${CYAN}==>${NC} ${BOLD}$1${NC}"
}

print_success() {
    echo -e "${GREEN}  ✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}  ⚠${NC} $1"
}

print_error() {
    echo -e "${RED}  ✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}  ℹ${NC} $1"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "This installer needs root privileges."
        echo ""
        echo "  Please run with sudo:"
        echo -e "  ${CYAN}sudo ./install.sh${NC}"
        echo ""
        exit 1
    fi
}

detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO_ID="${ID}"
        DISTRO_NAME="${NAME}"
        DISTRO_FAMILY=""
        
        # First, try to determine family from os-release ID/ID_LIKE (most reliable)
        case "${ID}" in
            arch|manjaro|endeavouros|garuda|cachyos)
                DISTRO_FAMILY="arch"
                PKG_INSTALL="pacman -S --noconfirm --needed"
                ;;
            opensuse*|suse*)
                DISTRO_FAMILY="opensuse"
                PKG_INSTALL="zypper install -y"
                ;;
            fedora|rhel|centos|rocky|alma|nobara)
                DISTRO_FAMILY="fedora"
                PKG_INSTALL="dnf install -y"
                ;;
            debian|ubuntu|linuxmint|pop|zorin|elementary|kali)
                DISTRO_FAMILY="debian"
                PKG_INSTALL="apt install -y"
                ;;
        esac
        
        # If ID didn't match, check ID_LIKE
        if [ -z "$DISTRO_FAMILY" ] && [ -n "${ID_LIKE}" ]; then
            case "${ID_LIKE}" in
                *arch*)
                    DISTRO_FAMILY="arch"
                    PKG_INSTALL="pacman -S --noconfirm --needed"
                    ;;
                *suse*|*opensuse*)
                    DISTRO_FAMILY="opensuse"
                    PKG_INSTALL="zypper install -y"
                    ;;
                *fedora*|*rhel*)
                    DISTRO_FAMILY="fedora"
                    PKG_INSTALL="dnf install -y"
                    ;;
                *debian*|*ubuntu*)
                    DISTRO_FAMILY="debian"
                    PKG_INSTALL="apt install -y"
                    ;;
            esac
        fi
        
        # Fall back to package manager detection only if os-release didn't help
        if [ -z "$DISTRO_FAMILY" ]; then
            if command -v pacman &>/dev/null; then
                DISTRO_FAMILY="arch"
                PKG_INSTALL="pacman -S --noconfirm --needed"
            elif command -v zypper &>/dev/null; then
                DISTRO_FAMILY="opensuse"
                PKG_INSTALL="zypper install -y"
            elif command -v dnf &>/dev/null; then
                DISTRO_FAMILY="fedora"
                PKG_INSTALL="dnf install -y"
            elif command -v apt &>/dev/null; then
                DISTRO_FAMILY="debian"
                PKG_INSTALL="apt install -y"
            else
                DISTRO_FAMILY="unknown"
            fi
        fi
    else
        DISTRO_FAMILY="unknown"
        DISTRO_NAME="Unknown"
    fi
}

#-------------------------------------------------------------------------------
# Dependency Checking
#-------------------------------------------------------------------------------

check_dependencies() {
    print_step "Checking dependencies..."
    
    local missing_pkgs=()
    
    # Check Python 3
    if command -v python3 &>/dev/null; then
        local py_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        print_success "Python $py_version found"
    else
        print_error "Python 3 not found"
        case $DISTRO_FAMILY in
            arch) missing_pkgs+=("python") ;;
            debian) missing_pkgs+=("python3") ;;
            fedora) missing_pkgs+=("python3") ;;
            opensuse) missing_pkgs+=("python3") ;;
        esac
    fi
    
    # Check GTK4
    if python3 -c "import gi; gi.require_version('Gtk', '4.0'); from gi.repository import Gtk" 2>/dev/null; then
        print_success "GTK4 found"
    else
        print_error "GTK4 not found"
        case $DISTRO_FAMILY in
            arch) missing_pkgs+=("gtk4" "python-gobject") ;;
            debian) missing_pkgs+=("libgtk-4-dev" "python3-gi" "gir1.2-gtk-4.0") ;;
            fedora) missing_pkgs+=("gtk4" "python3-gobject") ;;
            opensuse) missing_pkgs+=("gtk4" "python3-gobject" "typelib-1_0-Gtk-4_0") ;;
        esac
    fi
    
    # Check Libadwaita
    if python3 -c "import gi; gi.require_version('Adw', '1'); from gi.repository import Adw" 2>/dev/null; then
        print_success "Libadwaita found"
    else
        print_error "Libadwaita not found"
        case $DISTRO_FAMILY in
            arch) missing_pkgs+=("libadwaita") ;;
            debian) missing_pkgs+=("libadwaita-1-dev" "gir1.2-adw-1") ;;
            fedora) missing_pkgs+=("libadwaita") ;;
            opensuse) missing_pkgs+=("libadwaita" "typelib-1_0-Adw-1") ;;
        esac
    fi
    
    # Check WebKitGTK 6.0 (for Browser and Claude AI)
    if python3 -c "import gi; gi.require_version('WebKit', '6.0'); from gi.repository import WebKit" 2>/dev/null; then
        print_success "WebKitGTK 6.0 found"
    else
        print_warning "WebKitGTK 6.0 not found (needed for Browser and Claude AI)"
        case $DISTRO_FAMILY in
            arch) missing_pkgs+=("webkit2gtk-4.1") ;;
            debian) missing_pkgs+=("gir1.2-webkit-6.0" "libwebkitgtk-6.0-4") ;;
            fedora) missing_pkgs+=("webkitgtk6.0") ;;
            opensuse) missing_pkgs+=("libwebkitgtk-6_0-4" "typelib-1_0-WebKit-6_0" "typelib-1_0-WebKitWebProcessExtension-6_0") ;;
        esac
    fi
    
    # Check GStreamer (for Tux Tunes)
    if python3 -c "import gi; gi.require_version('Gst', '1.0'); from gi.repository import Gst" 2>/dev/null; then
        print_success "GStreamer found"
    else
        print_warning "GStreamer not found (needed for Tux Tunes)"
        case $DISTRO_FAMILY in
            arch) missing_pkgs+=("gstreamer" "gst-plugins-base" "gst-plugins-good") ;;
            debian) missing_pkgs+=("gstreamer1.0-tools" "gir1.2-gst-plugins-base-1.0" "gstreamer1.0-plugins-good") ;;
            fedora) missing_pkgs+=("gstreamer1" "gstreamer1-plugins-base" "gstreamer1-plugins-good") ;;
            opensuse) missing_pkgs+=("gstreamer" "gstreamer-plugins-base" "gstreamer-plugins-good" "typelib-1_0-Gst-1_0" "typelib-1_0-GstPlayer-1_0" "typelib-1_0-GstAudio-1_0" "typelib-1_0-GstVideo-1_0" "typelib-1_0-GstPbutils-1_0" "typelib-1_0-GstTag-1_0") ;;
        esac
    fi
    
    # Check for polkit
    if command -v pkexec &>/dev/null; then
        print_success "Polkit found"
    else
        print_warning "Polkit not found (some features may not work)"
    fi
    
    # Return missing packages
    if [ ${#missing_pkgs[@]} -gt 0 ]; then
        echo ""
        MISSING_PACKAGES="${missing_pkgs[*]}"
        return 1
    fi
    
    return 0
}

install_dependencies() {
    print_step "Installing missing dependencies..."
    echo ""
    print_info "The following packages will be installed:"
    echo -e "    ${CYAN}$MISSING_PACKAGES${NC}"
    echo ""
    
    read -p "  Proceed with installation? [Y/n] " -n 1 -r
    echo ""
    
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        echo ""
        $PKG_INSTALL $MISSING_PACKAGES
        echo ""
        print_success "Dependencies installed"
        
        # Install Python audio dependencies via pip (librosa not in most repos)
        print_info "Installing Python audio libraries..."
        pip3 install --user --break-system-packages --quiet numpy librosa pydub 2>/dev/null || \
        pip3 install --user --quiet numpy librosa pydub 2>/dev/null || \
        pip install --user --quiet numpy librosa pydub 2>/dev/null || true
        print_success "Audio libraries installed"
    else
        print_error "Cannot continue without dependencies"
        exit 1
    fi
}

#-------------------------------------------------------------------------------
# Installation
#-------------------------------------------------------------------------------

install_app() {
    print_step "Installing Tux Assistant..."
    
    # Create install directory
    if [ -d "$INSTALL_DIR" ]; then
        print_info "Removing previous installation..."
        rm -rf "$INSTALL_DIR"
    fi
    
    mkdir -p "$INSTALL_DIR"
    print_success "Created $INSTALL_DIR"
    
    # Copy application files
    cp -r tux "$INSTALL_DIR/"
    cp -r assets "$INSTALL_DIR/"
    cp tux-assistant.py "$INSTALL_DIR/"
    cp tux-helper "$INSTALL_DIR/"
    cp VERSION "$INSTALL_DIR/"
    chmod +x "$INSTALL_DIR/tux-assistant.py"
    chmod +x "$INSTALL_DIR/tux-helper"
    chmod +x "$INSTALL_DIR/tux/apps/tux_tunes/tux-tunes.py"
    print_success "Copied application files"
    
    # Create Tux Assistant launcher (remove any existing symlink first!)
    rm -f "$BIN_LINK"
    cat > "$BIN_LINK" << 'EOF'
#!/bin/bash
cd /opt/tux-assistant
python3 tux-assistant.py "$@"
EOF
    chmod +x "$BIN_LINK"
    print_success "Created tux-assistant launcher"
    
    # Create Tux Tunes launcher (remove any existing symlink first!)
    rm -f "$TUXTUNES_BIN"
    cat > "$TUXTUNES_BIN" << 'EOF'
#!/bin/bash
python3 /opt/tux-assistant/tux/apps/tux_tunes/tux-tunes.py "$@"
EOF
    chmod +x "$TUXTUNES_BIN"
    print_success "Created tux-tunes launcher"
    
    # Create tux-helper symlink for pkexec operations
    ln -sf "$INSTALL_DIR/tux-helper" /usr/bin/tux-helper
    print_success "Created helper symlink"
    
    # Install polkit policy
    if [ -f "data/com.tuxassistant.helper.policy" ]; then
        cp "data/com.tuxassistant.helper.policy" "$POLKIT_FILE"
        print_success "Installed polkit policy"
    fi
}

install_icons() {
    print_step "Installing self-contained icon theme..."
    
    # ==========================================================================
    # BULLETPROOF ICON STRATEGY
    # ==========================================================================
    # We create our OWN icon theme at /opt/tux-assistant/icons/tux-icons/
    # This theme is self-contained and doesn't rely on system icon themes.
    # The app prepends this path to GTK's icon search, so we're found FIRST.
    #
    # We ALSO install to hicolor as a backup (belt and suspenders).
    # We ALSO update both GTK and KDE icon caches.
    # ==========================================================================
    
    local THEME_DIR="$INSTALL_DIR/icons/tux-icons"
    local THEME_SCALABLE="$THEME_DIR/scalable"
    
    # Create theme directory structure
    mkdir -p "$THEME_SCALABLE/apps"
    mkdir -p "$THEME_SCALABLE/actions"
    mkdir -p "$THEME_SCALABLE/status"
    mkdir -p "$THEME_SCALABLE/emblems"
    mkdir -p "$THEME_SCALABLE/categories"
    mkdir -p "$THEME_SCALABLE/devices"
    mkdir -p "$THEME_SCALABLE/mimetypes"
    mkdir -p "$THEME_SCALABLE/places"
    
    # Create index.theme - this makes it a proper icon theme
    cat > "$THEME_DIR/index.theme" << 'THEME_EOF'
[Icon Theme]
Name=Tux Icons
Comment=Self-contained icon theme for Tux Assistant
Inherits=hicolor,Adwaita,breeze,gnome,elementary
Directories=scalable/apps,scalable/actions,scalable/status,scalable/emblems,scalable/categories,scalable/devices,scalable/mimetypes,scalable/places

[scalable/apps]
Size=64
MinSize=16
MaxSize=512
Type=Scalable
Context=Applications

[scalable/actions]
Size=64
MinSize=16
MaxSize=512
Type=Scalable
Context=Actions

[scalable/status]
Size=64
MinSize=16
MaxSize=512
Type=Scalable
Context=Status

[scalable/emblems]
Size=64
MinSize=16
MaxSize=512
Type=Scalable
Context=Emblems

[scalable/categories]
Size=64
MinSize=16
MaxSize=512
Type=Scalable
Context=Categories

[scalable/devices]
Size=64
MinSize=16
MaxSize=512
Type=Scalable
Context=Devices

[scalable/mimetypes]
Size=64
MinSize=16
MaxSize=512
Type=Scalable
Context=MimeTypes

[scalable/places]
Size=64
MinSize=16
MaxSize=512
Type=Scalable
Context=Places
THEME_EOF
    print_success "Created icon theme definition"
    
    # --------------------------------------------------------------------------
    # Install app icons with BOTH friendly names AND app-id names
    # This covers: GNOME (uses friendly name), KDE (often uses app-id)
    # --------------------------------------------------------------------------
    
    # Tux Assistant icon
    cp "$INSTALL_DIR/assets/icon.svg" "$THEME_SCALABLE/apps/tux-assistant.svg"
    cp "$INSTALL_DIR/assets/icon.svg" "$THEME_SCALABLE/apps/com.tuxassistant.app.svg"
    
    # Tux Tunes icon
    cp "$INSTALL_DIR/assets/tux-tunes.svg" "$THEME_SCALABLE/apps/tux-tunes.svg"
    cp "$INSTALL_DIR/assets/tux-tunes.svg" "$THEME_SCALABLE/apps/com.tuxassistant.tuxtunes.svg"
    
    # Tux Browser icon  
    cp "$INSTALL_DIR/assets/tux-browser.svg" "$THEME_SCALABLE/apps/tux-browser.svg"
    cp "$INSTALL_DIR/assets/tux-browser.svg" "$THEME_SCALABLE/apps/com.tuxassistant.tuxbrowser.svg"
    
    # Tux Claude icon (AI assistant)
    cp "$INSTALL_DIR/assets/tux-claude.svg" "$THEME_SCALABLE/apps/tux-claude.svg"
    
    print_success "Installed app icons (friendly + app-id names)"
    
    # --------------------------------------------------------------------------
    # Install all symbolic icons to multiple contexts
    # Different DEs look in different places, so we cover them all
    # --------------------------------------------------------------------------
    
    local icon_count=0
    if [ -d "$INSTALL_DIR/assets/icons" ]; then
        for icon_file in "$INSTALL_DIR/assets/icons/"*.svg; do
            if [ -f "$icon_file" ]; then
                icon_name=$(basename "$icon_file")
                # Install to all relevant contexts
                cp "$icon_file" "$THEME_SCALABLE/actions/$icon_name"
                cp "$icon_file" "$THEME_SCALABLE/status/$icon_name"
                cp "$icon_file" "$THEME_SCALABLE/apps/$icon_name"
                cp "$icon_file" "$THEME_SCALABLE/emblems/$icon_name"
                icon_count=$((icon_count + 1))
            fi
        done
        print_success "Installed $icon_count symbolic icons (4 contexts each)"
    fi
    
    # --------------------------------------------------------------------------
    # BACKUP: Also install to system hicolor theme
    # This is belt-and-suspenders - if our theme somehow isn't found,
    # hicolor is the universal fallback that every toolkit checks
    # --------------------------------------------------------------------------
    
    print_info "Also installing to system hicolor (backup)..."
    
    # Create hicolor directories
    for size in 16 24 32 48 64 128 256 scalable; do
        if [ "$size" = "scalable" ]; then
            mkdir -p "$ICON_DIR/scalable/apps"
        else
            mkdir -p "$ICON_DIR/${size}x${size}/apps"
        fi
    done
    
    # Install app icons to hicolor at multiple sizes
    for size in 16 24 32 48 64 128 256; do
        cp "$INSTALL_DIR/assets/icon.svg" "$ICON_DIR/${size}x${size}/apps/tux-assistant.svg"
        cp "$INSTALL_DIR/assets/icon.svg" "$ICON_DIR/${size}x${size}/apps/com.tuxassistant.app.svg"
        cp "$INSTALL_DIR/assets/tux-tunes.svg" "$ICON_DIR/${size}x${size}/apps/tux-tunes.svg"
        cp "$INSTALL_DIR/assets/tux-tunes.svg" "$ICON_DIR/${size}x${size}/apps/com.tuxassistant.tuxtunes.svg"
        cp "$INSTALL_DIR/assets/tux-browser.svg" "$ICON_DIR/${size}x${size}/apps/tux-browser.svg"
        cp "$INSTALL_DIR/assets/tux-browser.svg" "$ICON_DIR/${size}x${size}/apps/com.tuxassistant.tuxbrowser.svg"
        cp "$INSTALL_DIR/assets/tux-claude.svg" "$ICON_DIR/${size}x${size}/apps/tux-claude.svg"
    done
    
    # Scalable versions
    cp "$INSTALL_DIR/assets/icon.svg" "$ICON_DIR/scalable/apps/tux-assistant.svg"
    cp "$INSTALL_DIR/assets/icon.svg" "$ICON_DIR/scalable/apps/com.tuxassistant.app.svg"
    cp "$INSTALL_DIR/assets/tux-tunes.svg" "$ICON_DIR/scalable/apps/tux-tunes.svg"
    cp "$INSTALL_DIR/assets/tux-tunes.svg" "$ICON_DIR/scalable/apps/com.tuxassistant.tuxtunes.svg"
    cp "$INSTALL_DIR/assets/tux-browser.svg" "$ICON_DIR/scalable/apps/tux-browser.svg"
    cp "$INSTALL_DIR/assets/tux-browser.svg" "$ICON_DIR/scalable/apps/com.tuxassistant.tuxbrowser.svg"
    cp "$INSTALL_DIR/assets/tux-claude.svg" "$ICON_DIR/scalable/apps/tux-claude.svg"
    
    # Install symbolic icons to hicolor actions (for apps that check there)
    mkdir -p "$ICON_DIR/scalable/actions"
    mkdir -p "$ICON_DIR/scalable/status"
    if [ -d "$INSTALL_DIR/assets/icons" ]; then
        for icon_file in "$INSTALL_DIR/assets/icons/"*.svg; do
            if [ -f "$icon_file" ]; then
                icon_name=$(basename "$icon_file")
                cp "$icon_file" "$ICON_DIR/scalable/actions/$icon_name"
                cp "$icon_file" "$ICON_DIR/scalable/status/$icon_name"
            fi
        done
    fi
    
    print_success "Installed to hicolor theme"
    
    # --------------------------------------------------------------------------
    # Update ALL icon caches - GTK, KDE, and any others
    # --------------------------------------------------------------------------
    
    print_info "Updating icon caches..."
    
    # GTK icon cache
    if command -v gtk-update-icon-cache &>/dev/null; then
        gtk-update-icon-cache -f -t "$ICON_DIR" 2>/dev/null || true
        gtk-update-icon-cache -f -t "$THEME_DIR" 2>/dev/null || true
        print_success "Updated GTK icon cache"
    fi
    
    # GTK4 icon cache (some systems have separate command)
    if command -v gtk4-update-icon-cache &>/dev/null; then
        gtk4-update-icon-cache -f -t "$ICON_DIR" 2>/dev/null || true
        gtk4-update-icon-cache -f -t "$THEME_DIR" 2>/dev/null || true
        print_success "Updated GTK4 icon cache"
    fi
    
    # KDE icon cache (Plasma 5)
    if command -v kbuildsycoca5 &>/dev/null; then
        kbuildsycoca5 --noincremental 2>/dev/null || true
        print_success "Updated KDE5 cache"
    fi
    
    # KDE icon cache (Plasma 6)
    if command -v kbuildsycoca6 &>/dev/null; then
        kbuildsycoca6 --noincremental 2>/dev/null || true
        print_success "Updated KDE6 cache"
    fi
    
    # XDG icon resource (used by some DEs)
    if command -v xdg-icon-resource &>/dev/null; then
        xdg-icon-resource forceupdate --theme hicolor 2>/dev/null || true
    fi
    
    print_success "Icon installation complete"
}

install_desktop_entries() {
    print_step "Creating desktop entries..."
    
    # Remove old naming convention desktop files (cleanup from previous versions)
    rm -f "$DESKTOP_DIR/tux-assistant.desktop" 2>/dev/null || true
    rm -f "$DESKTOP_DIR/tux-tunes.desktop" 2>/dev/null || true
    
    # Install Tux Assistant desktop entry (GNOME standard naming)
    cp "data/com.tuxassistant.app.desktop" "$DESKTOP_DIR/"
    print_success "Created Tux Assistant desktop entry"
    
    # Install Tux Tunes desktop entry (GNOME standard naming)
    cp "data/com.tuxassistant.tuxtunes.desktop" "$DESKTOP_DIR/"
    print_success "Created Tux Tunes desktop entry"
    
    # Install Tux Browser desktop entry (GNOME standard naming)
    cp "data/com.tuxassistant.tuxbrowser.desktop" "$DESKTOP_DIR/"
    print_success "Created Tux Browser desktop entry"
    
    # Update desktop database
    if command -v update-desktop-database &>/dev/null; then
        update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
        print_success "Updated desktop database"
    fi
}

install_native_messaging() {
    print_step "Installing OCS protocol handler..."
    
    # Ensure scripts directory exists
    mkdir -p "$INSTALL_DIR/scripts"
    
    # Install OCS handler script
    cp "scripts/tux-ocs-handler" "$INSTALL_DIR/scripts/"
    chmod +x "$INSTALL_DIR/scripts/tux-ocs-handler"
    print_success "Installed OCS handler script"
    
    # Install OCS handler desktop file
    cp "data/tux-ocs-handler.desktop" "$DESKTOP_DIR/"
    print_success "Installed OCS handler desktop entry"
    
    # Register as protocol handler for ocs:// links
    if command -v xdg-mime &>/dev/null; then
        xdg-mime default tux-ocs-handler.desktop x-scheme-handler/ocs 2>/dev/null || true
        print_success "Registered ocs:// protocol handler"
    fi
    
    # Update desktop database
    if command -v update-desktop-database &>/dev/null; then
        update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    fi
    
    echo ""
    echo -e "  ${GREEN}✓ One-click theme installs from gnome-look.org now work!${NC}"
    echo -e "  ${DIM}Click 'Install' on any theme and Tux Assistant will handle it.${NC}"
    echo ""
}

#-------------------------------------------------------------------------------
# Uninstallation
#-------------------------------------------------------------------------------

uninstall_app() {
    print_banner
    print_step "Uninstalling Tux Assistant & Tux Tunes..."
    echo ""
    
    local found_something=false
    
    # Remove install directory
    if [ -d "$INSTALL_DIR" ]; then
        rm -rf "$INSTALL_DIR"
        print_success "Removed $INSTALL_DIR"
        found_something=true
    fi
    
    # Remove launchers
    for launcher in "$BIN_LINK" "$TUXTUNES_BIN" "/usr/bin/tux-helper"; do
        if [ -f "$launcher" ] || [ -L "$launcher" ]; then
            rm -f "$launcher"
            print_success "Removed $launcher"
            found_something=true
        fi
    done
    
    # Remove desktop entries (both old and new naming conventions)
    for desktop in "tux-assistant.desktop" "tux-tunes.desktop" "com.tuxassistant.app.desktop" "com.tuxassistant.tuxtunes.desktop" "com.tuxassistant.tuxbrowser.desktop" "tux-ocs-handler.desktop"; do
        if [ -f "$DESKTOP_DIR/$desktop" ]; then
            rm -f "$DESKTOP_DIR/$desktop"
            print_success "Removed $desktop"
            found_something=true
        fi
    done
    
    # Remove native messaging host manifest (legacy, may not exist)
    if [ -f "/usr/lib/mozilla/native-messaging-hosts/tux_assistant.json" ]; then
        rm -f "/usr/lib/mozilla/native-messaging-hosts/tux_assistant.json"
        print_success "Removed Firefox native messaging manifest"
        found_something=true
    fi
    
    # Remove icons (both friendly names AND app-id names)
    for icon in "tux-assistant.svg" "tux-tunes.svg" "tux-browser.svg" "com.tuxassistant.app.svg" "com.tuxassistant.tuxtunes.svg" "com.tuxassistant.tuxbrowser.svg"; do
        for size in 16 24 32 48 64 128 256 scalable; do
            local icon_path="$ICON_DIR/${size}x${size}/apps/$icon"
            if [ "$size" = "scalable" ]; then
                icon_path="$ICON_DIR/scalable/apps/$icon"
            fi
            if [ -f "$icon_path" ]; then
                rm -f "$icon_path"
                found_something=true
            fi
        done
    done
    
    # Remove bundled tux-* symbolic icons
    for category in actions status apps emblems; do
        if [ -d "$ICON_DIR/scalable/$category" ]; then
            for icon_file in "$ICON_DIR/scalable/$category"/tux-*.svg; do
                if [ -f "$icon_file" ]; then
                    rm -f "$icon_file"
                    found_something=true
                fi
            done
        fi
    done
    
    # Remove runtime icon theme (created by the app)
    if [ -d "$HOME/.local/share/icons/tux-runtime" ]; then
        rm -rf "$HOME/.local/share/icons/tux-runtime"
        found_something=true
    fi
    
    if [ "$found_something" = true ]; then
        print_success "Removed icons"
    fi
    
    # Remove polkit policy
    if [ -f "$POLKIT_FILE" ]; then
        rm -f "$POLKIT_FILE"
        print_success "Removed polkit policy"
        found_something=true
    fi
    
    # Update caches
    if command -v update-desktop-database &>/dev/null; then
        update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
    fi
    if command -v gtk-update-icon-cache &>/dev/null; then
        gtk-update-icon-cache -f -t "$ICON_DIR" 2>/dev/null || true
    fi
    
    echo ""
    if [ "$found_something" = true ]; then
        echo -e "${GREEN}${BOLD}  Tux Assistant has been uninstalled.${NC}"
    else
        echo -e "${YELLOW}  Tux Assistant was not installed.${NC}"
    fi
    echo ""
}

#-------------------------------------------------------------------------------
# Main
#-------------------------------------------------------------------------------

show_help() {
    echo "Tux Assistant Installer"
    echo ""
    echo "Usage: sudo ./install.sh [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --uninstall    Remove Tux Assistant from your system"
    echo "  --help, -h     Show this help message"
    echo ""
}

main() {
    # Parse arguments
    case "${1:-}" in
        --uninstall)
            check_root
            uninstall_app
            exit 0
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
    esac
    
    # Normal installation
    print_banner
    
    check_root
    
    print_step "Detecting system..."
    detect_distro
    print_success "Detected: $DISTRO_NAME ($DISTRO_FAMILY)"
    echo ""
    
    # Check and install dependencies
    if ! check_dependencies; then
        echo ""
        if [ "$DISTRO_FAMILY" = "unknown" ]; then
            print_error "Could not detect package manager."
            print_info "Please install GTK4, Libadwaita, and GStreamer manually, then re-run."
            exit 1
        fi
        install_dependencies
        echo ""
        
        # Re-check
        if ! check_dependencies; then
            print_error "Dependencies still missing after installation."
            print_info "Please install them manually and try again."
            exit 1
        fi
    fi
    
    echo ""
    install_app
    echo ""
    install_icons
    echo ""
    install_desktop_entries
    echo ""
    install_native_messaging
    
    # Ensure 7z is available for extracting themes from gnome-look.org
    echo ""
    print_step "Ensuring archive extraction tools..."
    if ! command -v 7z &>/dev/null && ! command -v 7za &>/dev/null; then
        # Install based on distro
        if command -v zypper &>/dev/null; then
            zypper install -y p7zip 2>/dev/null || true
        elif command -v dnf &>/dev/null; then
            dnf install -y p7zip p7zip-plugins 2>/dev/null || true
        elif command -v apt &>/dev/null; then
            apt install -y p7zip-full 2>/dev/null || true
        elif command -v pacman &>/dev/null; then
            pacman -S --noconfirm p7zip 2>/dev/null || true
        fi
    fi
    if command -v 7z &>/dev/null || command -v 7za &>/dev/null; then
        print_success "7z extraction ready"
    else
        echo -e "  ${YELLOW}⚠ Could not install p7zip - some theme archives may not extract${NC}"
    fi
    
    # Ensure Python audio libraries are installed (for Tux Tunes audio analysis)
    echo ""
    print_step "Ensuring Python audio libraries..."
    pip3 install --user --break-system-packages --quiet numpy librosa pydub 2>/dev/null || \
    pip3 install --user --quiet numpy librosa pydub 2>/dev/null || \
    pip install --user --quiet numpy librosa pydub 2>/dev/null || true
    print_success "Audio libraries ready"
    
    echo ""
    echo -e "${GREEN}${BOLD}  ╔═══════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}${BOLD}  ║                                           ║${NC}"
    echo -e "${GREEN}${BOLD}  ║   🐧  Installation Complete!  🐧         ║${NC}"
    echo -e "${GREEN}${BOLD}  ║                                           ║${NC}"
    echo -e "${GREEN}${BOLD}  ╚═══════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  You can now launch from your application menu:"
    echo ""
    echo -e "    ${CYAN}•${NC} Tux Assistant - System configuration tool"
    echo -e "    ${CYAN}•${NC} Tux Tunes - Internet radio player"
    echo ""
    echo -e "  Or from terminal:"
    echo -e "    ${CYAN}tux-assistant${NC}"
    echo -e "    ${CYAN}tux-tunes${NC}"
    echo ""
    echo -e "  To uninstall later, run:"
    echo -e "    ${CYAN}sudo ./install.sh --uninstall${NC}"
    echo ""
}

# Run main
main "$@"
