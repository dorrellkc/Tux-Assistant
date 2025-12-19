#!/bin/bash
# ============================================================================
# Tux Assistant - Build Script
# Creates the self-extracting .run file for distribution
# Copyright (c) 2025 Christopher Dorrell. Licensed under GPL-3.0.
# ============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BUILD_DIR="$PROJECT_DIR/build"
OUTPUT_DIR="$PROJECT_DIR/dist"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${BLUE}[*]${NC} $1"; }
print_success() { echo -e "${GREEN}[✓]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[!]${NC} $1"; }
print_error() { echo -e "${RED}[✗]${NC} $1"; }

# ============================================================================
# Main Build Process
# ============================================================================

main() {
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "  🐧 Tux Assistant - Build Script"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    
    # Read version
    if [ -f "$PROJECT_DIR/VERSION" ]; then
        VERSION=$(cat "$PROJECT_DIR/VERSION")
    else
        VERSION="0.9.0"
    fi
    
    print_status "Building version: $VERSION"
    
    # Clean up previous builds
    print_status "Cleaning previous builds..."
    rm -rf "$BUILD_DIR"
    mkdir -p "$BUILD_DIR"
    mkdir -p "$OUTPUT_DIR"
    
    # Create the application bundle
    print_status "Creating application bundle..."
    mkdir -p "$BUILD_DIR/tux-assistant"
    
    # Copy application files
    cp -r "$PROJECT_DIR/tux" "$BUILD_DIR/tux-assistant/"
    cp "$PROJECT_DIR/tux-assistant.py" "$BUILD_DIR/tux-assistant/"
    cp "$PROJECT_DIR/VERSION" "$BUILD_DIR/tux-assistant/"
    cp "$PROJECT_DIR/LICENSE" "$BUILD_DIR/tux-assistant/" 2>/dev/null || true
    cp "$PROJECT_DIR/tux-helper" "$BUILD_DIR/tux-assistant/" 2>/dev/null || true
    cp -r "$PROJECT_DIR/assets" "$BUILD_DIR/tux-assistant/" 2>/dev/null || true
    cp -r "$PROJECT_DIR/data" "$BUILD_DIR/tux-assistant/" 2>/dev/null || true
    
    # Remove any __pycache__ directories
    find "$BUILD_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "$BUILD_DIR" -type f -name "*.pyc" -delete 2>/dev/null || true
    
    # Create the tarball
    print_status "Creating compressed archive..."
    cd "$BUILD_DIR"
    tar -czf payload.tar.gz tux-assistant
    
    # Combine header + payload
    print_status "Building self-extracting executable..."
    OUTPUT_FILE="$OUTPUT_DIR/Tux-Assistant-v${VERSION}.run"
    
    cat "$SCRIPT_DIR/run-header.sh" payload.tar.gz > "$OUTPUT_FILE"
    chmod +x "$OUTPUT_FILE"
    
    # Get file size
    FILE_SIZE=$(du -h "$OUTPUT_FILE" | cut -f1)
    
    # Cleanup
    print_status "Cleaning up..."
    rm -rf "$BUILD_DIR"
    
    echo ""
    print_success "Build complete!"
    echo ""
    echo "════════════════════════════════════════════════════════════"
    echo "  Output: $OUTPUT_FILE"
    echo "  Size:   $FILE_SIZE"
    echo "════════════════════════════════════════════════════════════"
    echo ""
    echo "To test locally:"
    echo "  chmod +x $OUTPUT_FILE"
    echo "  $OUTPUT_FILE"
    echo ""
}

main "$@"
