#!/bin/bash
#===============================================================================
#
#   Tux Assistant - Installer
#
#   A polished installer that makes setup painless.
#   (Not a PITA - the pain OR the bread)
#
#   Copyright (c) 2025 Christopher Dorrell. All Rights Reserved.
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
        
        # Determine package manager family
        if command -v pacman &>/dev/null; then
            DISTRO_FAMILY="arch"
            PKG_INSTALL="pacman -S --noconfirm --needed"
        elif command -v apt &>/dev/null; then
            DISTRO_FAMILY="debian"
            PKG_INSTALL="apt install -y"
        elif command -v dnf &>/dev/null; then
            DISTRO_FAMILY="fedora"
            PKG_INSTALL="dnf install -y"
        elif command -v zypper &>/dev/null; then
            DISTRO_FAMILY="opensuse"
            PKG_INSTALL="zypper install -y"
        else
            DISTRO_FAMILY="unknown"
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
    
    # Check GStreamer (for Tux Tunes)
    if python3 -c "import gi; gi.require_version('Gst', '1.0'); from gi.repository import Gst" 2>/dev/null; then
        print_success "GStreamer found"
    else
        print_warning "GStreamer not found (needed for Tux Tunes)"
        case $DISTRO_FAMILY in
            arch) missing_pkgs+=("gstreamer" "gst-plugins-base" "gst-plugins-good") ;;
            debian) missing_pkgs+=("gstreamer1.0-tools" "gir1.2-gst-plugins-base-1.0" "gstreamer1.0-plugins-good") ;;
            fedora) missing_pkgs+=("gstreamer1" "gstreamer1-plugins-base" "gstreamer1-plugins-good") ;;
            opensuse) missing_pkgs+=("gstreamer" "gstreamer-plugins-base" "gstreamer-plugins-good") ;;
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
    
    # Create Tux Assistant launcher
    cat > "$BIN_LINK" << 'EOF'
#!/bin/bash
cd /opt/tux-assistant
python3 tux-assistant.py "$@"
EOF
    chmod +x "$BIN_LINK"
    print_success "Created tux-assistant launcher"
    
    # Create Tux Tunes launcher
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
    print_step "Installing icons..."
    
    # Install Tux Assistant icon
    for size in 16 24 32 48 64 128 256; do
        local icon_path="$ICON_DIR/${size}x${size}/apps"
        mkdir -p "$icon_path"
        cp "$INSTALL_DIR/assets/icon.svg" "$icon_path/tux-assistant.svg"
    done
    mkdir -p "$ICON_DIR/scalable/apps"
    cp "$INSTALL_DIR/assets/icon.svg" "$ICON_DIR/scalable/apps/tux-assistant.svg"
    print_success "Installed Tux Assistant icon"
    
    # Install Tux Tunes icon
    for size in 16 24 32 48 64 128 256; do
        local icon_path="$ICON_DIR/${size}x${size}/apps"
        mkdir -p "$icon_path"
        cp "$INSTALL_DIR/assets/tux-tunes.svg" "$icon_path/tux-tunes.svg"
    done
    cp "$INSTALL_DIR/assets/tux-tunes.svg" "$ICON_DIR/scalable/apps/tux-tunes.svg"
    print_success "Installed Tux Tunes icon"
    
    # Update icon cache
    if command -v gtk-update-icon-cache &>/dev/null; then
        gtk-update-icon-cache -f -t "$ICON_DIR" 2>/dev/null || true
        print_success "Updated icon cache"
    fi
}

install_desktop_entries() {
    print_step "Creating desktop entries..."
    
    # Install Tux Assistant desktop entry
    cp "data/tux-assistant.desktop" "$DESKTOP_DIR/"
    print_success "Created Tux Assistant desktop entry"
    
    # Install Tux Tunes desktop entry
    cp "data/tux-tunes.desktop" "$DESKTOP_DIR/"
    print_success "Created Tux Tunes desktop entry"
    
    # Update desktop database
    if command -v update-desktop-database &>/dev/null; then
        update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
        print_success "Updated desktop database"
    fi
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
    
    # Remove desktop entries
    for desktop in "tux-assistant.desktop" "tux-tunes.desktop"; do
        if [ -f "$DESKTOP_DIR/$desktop" ]; then
            rm -f "$DESKTOP_DIR/$desktop"
            print_success "Removed $desktop"
            found_something=true
        fi
    done
    
    # Remove icons
    for icon in "tux-assistant.svg" "tux-tunes.svg"; do
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
