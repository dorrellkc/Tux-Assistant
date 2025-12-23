#!/bin/bash
# Build script for creating Tux Assistant .run installer
# Uses makeself to create self-extracting installer

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Tux Assistant .run Builder ===${NC}"

# Get version
VERSION=$(cat VERSION)
echo "Version: $VERSION"

# Check for makeself
if ! command -v makeself &> /dev/null; then
    echo -e "${RED}Error: makeself is not installed${NC}"
    echo "Install it with:"
    echo "  openSUSE: sudo zypper install makeself"
    echo "  Debian/Ubuntu: sudo apt install makeself"
    echo "  Fedora: sudo dnf install makeself"
    echo "  Arch: sudo pacman -S makeself"
    exit 1
fi

# Create build directory
BUILD_DIR="build/tux-assistant-$VERSION"
rm -rf build
mkdir -p "$BUILD_DIR"

echo "Copying files to build directory..."

# Copy all necessary files
cp -r tux "$BUILD_DIR/"
cp -r assets "$BUILD_DIR/"
cp -r data "$BUILD_DIR/"
cp -r scripts "$BUILD_DIR/"
cp -r docs "$BUILD_DIR/" 2>/dev/null || true
cp VERSION "$BUILD_DIR/"
cp LICENSE "$BUILD_DIR/"
cp README.md "$BUILD_DIR/"
cp install.sh "$BUILD_DIR/"
cp tux-assistant.py "$BUILD_DIR/"
cp tux-helper "$BUILD_DIR/"
cp tux-assistant.install "$BUILD_DIR/" 2>/dev/null || true

# Make scripts executable
chmod +x "$BUILD_DIR/install.sh"
chmod +x "$BUILD_DIR/tux-assistant.py"
chmod +x "$BUILD_DIR/tux-helper"
chmod +x "$BUILD_DIR/scripts/"* 2>/dev/null || true

# Create the .run file
OUTPUT="tux-assistant-v${VERSION}.run"
echo "Creating $OUTPUT..."

makeself --notemp \
    "$BUILD_DIR" \
    "$OUTPUT" \
    "Tux Assistant v${VERSION} Installer" \
    ./install.sh

echo -e "${GREEN}✓ Created: $OUTPUT${NC}"
echo ""
echo "To install, run:"
echo "  chmod +x $OUTPUT"
echo "  ./$OUTPUT"
echo ""
echo "The installer will automatically run with sudo for system-wide installation."

# Clean up
rm -rf build
