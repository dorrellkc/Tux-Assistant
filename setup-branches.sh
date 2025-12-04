#!/bin/bash
# ============================================================================
# Tux Assistant - Git Branch Reorganization
# Run this in your local tux-assistant repository
# ============================================================================

echo "════════════════════════════════════════════════════════════"
echo "  🐧 Tux Assistant - Git Branch Reorganization"
echo "════════════════════════════════════════════════════════════"
echo ""

# Safety check
if [ ! -d ".git" ]; then
    echo "ERROR: Not in a git repository!"
    echo "Please cd to your tux-assistant directory first."
    exit 1
fi

echo "This script will:"
echo "  1. Create a 'dev' branch with all current development code"
echo "  2. Clean up 'main' branch for public release"
echo ""
read -p "Continue? [y/N] " confirm
if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "[1/6] Ensuring we're on main branch..."
git checkout main

echo ""
echo "[2/6] Creating dev branch from current main..."
git checkout -b dev

echo ""
echo "[3/6] Pushing dev branch to GitHub..."
git push -u origin dev

echo ""
echo "[4/6] Switching back to main branch..."
git checkout main

echo ""
echo "[5/6] Creating clean public structure..."
echo "      (You'll need to manually add the .run file and screenshots)"

# Create the public structure (keeping only what's needed)
mkdir -p screenshots
mkdir -p releases

echo ""
echo "════════════════════════════════════════════════════════════"
echo "  ✓ Branch setup complete!"
echo "════════════════════════════════════════════════════════════"
echo ""
echo "NEXT STEPS:"
echo ""
echo "1. Copy your new files to the repo:"
echo "   - README-public.md → README.md (replace existing)"
echo "   - Tux-Assistant-v0.9.0.run → releases/"
echo "   - Add screenshots to screenshots/"
echo ""
echo "2. On MAIN branch (public release):"
echo "   - Keep: README.md, LICENSE, CHANGELOG.md, screenshots/, releases/"
echo "   - Remove: tux/, scripts/, *.py, etc. (source code)"
echo ""
echo "3. Commit and push main:"
echo "   git add ."
echo "   git commit -m 'v0.9.0 - First public release'"
echo "   git push origin main"
echo ""
echo "4. Create a GitHub Release:"
echo "   - Go to GitHub → Releases → Create new release"
echo "   - Tag: v0.9.0"
echo "   - Upload: Tux-Assistant-v0.9.0.run"
echo ""
echo "5. For future development:"
echo "   git checkout dev"
echo "   (make changes)"
echo "   git push origin dev"
echo ""
