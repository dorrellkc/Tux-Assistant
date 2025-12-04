#!/bin/bash
# ============================================================================
# Tux Assistant - Self-Extracting Runner
# Copyright (c) 2025 Christopher Dorrell. Licensed under GPL-3.0.
# ============================================================================

set -e

APP_NAME="Tux Assistant"
EXTRACT_DIR="/tmp/tux-assistant-$$"
SCRIPT_PATH="$(readlink -f "$0")"

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# Utility Functions
# ============================================================================

print_status() {
    echo -e "${BLUE}[*]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

cleanup() {
    if [ -d "$EXTRACT_DIR" ]; then
        rm -rf "$EXTRACT_DIR"
    fi
}

trap cleanup EXIT

# ============================================================================
# Dialog Functions (GUI prompts)
# ============================================================================

show_question_dialog() {
    local title="$1"
    local message="$2"
    
    # Try zenity (GNOME/GTK)
    if command -v zenity &>/dev/null; then
        zenity --question --title="$title" --text="$message" \
            --ok-label="Install" --cancel-label="Cancel" --width=400 2>/dev/null
        return $?
    fi
    
    # Try kdialog (KDE)
    if command -v kdialog &>/dev/null; then
        kdialog --title "$title" --yesno "$message" 2>/dev/null
        return $?
    fi
    
    # Try yad (alternative GTK)
    if command -v yad &>/dev/null; then
        yad --title="$title" --text="$message" --button="Cancel:1" --button="Install:0" \
            --width=400 --center 2>/dev/null
        return $?
    fi
    
    # Try xmessage (basic X11)
    if command -v xmessage &>/dev/null; then
        xmessage -center -buttons "Install:0,Cancel:1" "$message" 2>/dev/null
        return $?
    fi
    
    # Terminal fallback
    echo ""
    echo "═══════════════════════════════════════════"
    echo "  $title"
    echo "═══════════════════════════════════════════"
    echo ""
    echo "$message"
    echo ""
    read -p "Proceed? [y/N] " response
    [[ "$response" =~ ^[Yy]$ ]]
    return $?
}

show_error_dialog() {
    local title="$1"
    local message="$2"
    
    if command -v zenity &>/dev/null; then
        zenity --error --title="$title" --text="$message" --width=400 2>/dev/null
    elif command -v kdialog &>/dev/null; then
        kdialog --title "$title" --error "$message" 2>/dev/null
    elif command -v yad &>/dev/null; then
        yad --title="$title" --text="$message" --button="OK:0" --width=400 --center 2>/dev/null
    elif command -v xmessage &>/dev/null; then
        xmessage -center "$message" 2>/dev/null
    else
        print_error "$message"
    fi
}

show_info_dialog() {
    local title="$1"
    local message="$2"
    
    if command -v zenity &>/dev/null; then
        zenity --info --title="$title" --text="$message" --width=400 2>/dev/null
    elif command -v kdialog &>/dev/null; then
        kdialog --title "$title" --msgbox "$message" 2>/dev/null
    elif command -v yad &>/dev/null; then
        yad --title="$title" --text="$message" --button="OK:0" --width=400 --center 2>/dev/null
    else
        print_success "$message"
    fi
}

show_progress() {
    local message="$1"
    
    if command -v zenity &>/dev/null; then
        zenity --progress --title="$APP_NAME" --text="$message" --pulsate --auto-close --no-cancel --width=300 2>/dev/null &
        echo $!
    else
        print_status "$message"
        echo ""
    fi
}

close_progress() {
    local pid="$1"
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        kill "$pid" 2>/dev/null || true
    fi
}

# ============================================================================
# Package Manager Detection
# ============================================================================

detect_package_manager() {
    if command -v pacman &>/dev/null; then
        echo "pacman"
    elif command -v apt &>/dev/null; then
        echo "apt"
    elif command -v dnf &>/dev/null; then
        echo "dnf"
    elif command -v zypper &>/dev/null; then
        echo "zypper"
    else
        echo "unknown"
    fi
}

# ============================================================================
# Dependency Checking
# ============================================================================

check_python() {
    command -v python3 &>/dev/null
}

check_gtk_deps() {
    # Try to import the required modules
    python3 -c "import gi; gi.require_version('Gtk', '4.0'); gi.require_version('Adw', '1'); from gi.repository import Gtk, Adw" 2>/dev/null
}

check_all_deps() {
    check_python && check_gtk_deps
}

# ============================================================================
# Dependency Installation
# ============================================================================

get_install_packages() {
    local pm="$1"
    
    case "$pm" in
        pacman)
            echo "python python-gobject gtk4 libadwaita gst-plugins-base gst-plugins-good python-pip python-numpy python-pydub"
            ;;
        apt)
            echo "python3 python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 libadwaita-1-0 gir1.2-gst-plugins-base-1.0 gstreamer1.0-plugins-good python3-pip python3-numpy python3-pydub"
            ;;
        dnf)
            echo "python3 python3-gobject gtk4 libadwaita gstreamer1-plugins-base gstreamer1-plugins-good python3-pip python3-numpy python3-pydub"
            ;;
        zypper)
            echo "python3 python3-gobject python3-gobject-Gdk typelib-1_0-Gtk-4_0 typelib-1_0-Adw-1 libadwaita-1-0 gstreamer-plugins-base gstreamer-plugins-good python3-pip python3-numpy python3-pydub ffmpeg"
            ;;
        *)
            echo ""
            ;;
    esac
}

install_dependencies() {
    local pm=$(detect_package_manager)
    local packages=$(get_install_packages "$pm")
    
    if [ -z "$packages" ]; then
        show_error_dialog "$APP_NAME" "Could not detect package manager.\n\nPlease manually install:\n- Python 3\n- PyGObject\n- GTK4\n- Libadwaita"
        return 1
    fi
    
    print_status "Installing dependencies using $pm..."
    
    case "$pm" in
        pacman)
            pkexec pacman -S --noconfirm --needed $packages
            # Install librosa via pip (Arch is permissive), ensure pydub as fallback
            pip install --quiet librosa pydub 2>/dev/null || true
            ;;
        apt)
            pkexec bash -c "apt update && apt install -y $packages"
            # Install librosa via pip, ensure pydub as fallback
            pip3 install --user --break-system-packages --quiet librosa pydub 2>/dev/null || true
            ;;
        dnf)
            pkexec dnf install -y $packages
            # Install librosa and ensure pydub via pip (Fedora 39+ requires --break-system-packages)
            pip3 install --user --break-system-packages --quiet librosa pydub 2>/dev/null || true
            ;;
        zypper)
            pkexec zypper install -y $packages
            # Install librosa via pip, ensure pydub as fallback (openSUSE requires --break-system-packages)
            pip3 install --user --break-system-packages --quiet librosa pydub 2>/dev/null || true
            ;;
    esac
    
    return $?
}

# ============================================================================
# Extraction
# ============================================================================

extract_payload() {
    print_status "Extracting $APP_NAME..."
    
    mkdir -p "$EXTRACT_DIR"
    
    # Find the line where the payload starts (after __PAYLOAD_BELOW__)
    local payload_line=$(awk '/^__PAYLOAD_BELOW__$/{print NR + 1; exit 0;}' "$SCRIPT_PATH")
    
    if [ -z "$payload_line" ]; then
        print_error "Could not find payload marker"
        return 1
    fi
    
    # Extract the payload
    tail -n +${payload_line} "$SCRIPT_PATH" | tar -xzf - -C "$EXTRACT_DIR"
    
    if [ $? -ne 0 ]; then
        print_error "Failed to extract payload"
        return 1
    fi
    
    print_success "Extraction complete"
    return 0
}

# ============================================================================
# Main Application Launch
# ============================================================================

launch_app() {
    cd "$EXTRACT_DIR/tux-assistant"
    
    # Set environment variable so app knows it's running portable
    export TUX_ASSISTANT_PORTABLE=1
    export TUX_ASSISTANT_RUN_FILE="$SCRIPT_PATH"
    
    # Launch the application
    python3 tux-assistant.py "$@"
}

# ============================================================================
# Main Entry Point
# ============================================================================

main() {
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "  🐧 $APP_NAME"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    
    # Check if we have all dependencies
    if ! check_all_deps; then
        print_warning "Missing dependencies detected"
        
        # Build the message
        local missing=""
        if ! check_python; then
            missing="• Python 3\n"
        fi
        if check_python && ! check_gtk_deps; then
            missing="${missing}• GTK4 and Libadwaita\n• PyGObject"
        fi
        
        local message="$APP_NAME requires the following to run:\n\n${missing}\n\nWould you like to install them now?\n\n(Administrator password required)"
        
        if show_question_dialog "$APP_NAME - Dependencies Required" "$message"; then
            local progress_pid=$(show_progress "Installing dependencies...")
            
            if install_dependencies; then
                close_progress "$progress_pid"
                print_success "Dependencies installed successfully"
                
                # Verify installation
                if ! check_all_deps; then
                    show_error_dialog "$APP_NAME" "Dependencies were installed but verification failed.\n\nPlease try running the application again."
                    exit 1
                fi
            else
                close_progress "$progress_pid"
                show_error_dialog "$APP_NAME" "Failed to install dependencies.\n\nPlease install them manually and try again."
                exit 1
            fi
        else
            print_warning "Installation cancelled by user"
            exit 0
        fi
    fi
    
    print_success "All dependencies satisfied"
    
    # Extract the application
    if ! extract_payload; then
        show_error_dialog "$APP_NAME" "Failed to extract application files."
        exit 1
    fi
    
    # Launch the application
    print_status "Launching $APP_NAME..."
    echo ""
    
    launch_app "$@"
    
    exit_code=$?
    
    echo ""
    print_status "Application closed"
    
    exit $exit_code
}

# Run main
main "$@"

# The payload (tarball) will be appended below this line
exit 0
__PAYLOAD_BELOW__
