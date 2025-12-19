# Tux Assistant - HONEST Distro Compatibility Audit

**CRITICAL: This audit identifies what we KNOW works vs what we're ASSUMING works.**

**Status Legend:**
- ✅ VERIFIED - Tested on real hardware or definitively confirmed
- ⚠️ ASSUMED - Package name exists in web searches but NOT tested
- ❌ BROKEN - Known to not work or require extra steps
- ❓ UNKNOWN - No verification at all

---

## CURRENT STATUS: NOT FULLY VERIFIED

We have only tested on **Arch-based** (CachyOS/Start-DE). The following need REAL testing:
- Debian/Ubuntu
- Fedora
- openSUSE

---

## Module: Hardware Manager

### Printer Support (CUPS Install)

| Distro | Package(s) | Status | Notes |
|--------|------------|--------|-------|
| Arch | `cups cups-pdf system-config-printer` | ✅ VERIFIED | Tested |
| Debian | `cups cups-pdf system-config-printer` | ⚠️ ASSUMED | Need to test |
| Fedora | `cups cups-pdf system-config-printer` | ⚠️ ASSUMED | Need to test |
| openSUSE | `cups cups-pdf system-config-printer` | ⚠️ ASSUMED | Need to test |

### Bluetooth Install

| Distro | Package(s) | Status | Notes |
|--------|------------|--------|-------|
| Arch | `bluez bluez-utils` | ✅ VERIFIED | Tested |
| Debian | `bluez bluetooth` | ⚠️ ASSUMED | Is `bluetooth` a real metapackage? |
| Fedora | `bluez bluez-tools` | ⚠️ ASSUMED | Is `bluez-tools` correct name? |
| openSUSE | `bluez` | ⚠️ ASSUMED | Need to test |

### Blueman Install

| Distro | Package(s) | Status | Notes |
|--------|------------|--------|-------|
| Arch | `blueman` | ✅ VERIFIED | Tested |
| Debian | `blueman` | ⚠️ ASSUMED | Probably works |
| Fedora | `blueman` | ⚠️ ASSUMED | Probably works |
| openSUSE | `blueman` | ⚠️ ASSUMED | Probably works |

---

## Module: Backup & Restore

### rsync Install

| Distro | Package(s) | Status | Notes |
|--------|------------|--------|-------|
| Arch | `rsync` | ✅ VERIFIED | Universal |
| Debian | `rsync` | ⚠️ ASSUMED | Almost certainly works |
| Fedora | `rsync` | ⚠️ ASSUMED | Almost certainly works |
| openSUSE | `rsync` | ⚠️ ASSUMED | Almost certainly works |

### Timeshift Install

| Distro | Package(s) | Status | Notes |
|--------|------------|--------|-------|
| Arch | `timeshift` | ✅ VERIFIED | In official repos |
| Debian | `timeshift` | ⚠️ ASSUMED | May need PPA on older Ubuntu |
| Fedora | `timeshift` | ⚠️ ASSUMED | Need to verify |
| openSUSE | `timeshift` | ❌ BROKEN | **REQUIRES EXTRA REPO** - We added repo but untested |

---

## Module: Networking (Simple)

### speedtest-cli Install

| Distro | Package(s) | Status | Notes |
|--------|------------|--------|-------|
| Arch | `speedtest-cli` | ✅ VERIFIED | Just tested, plan format was wrong |
| Debian | `speedtest-cli` | ⚠️ ASSUMED | |
| Fedora | `speedtest-cli` | ⚠️ ASSUMED | |
| openSUSE | `speedtest-cli` | ⚠️ ASSUMED | |

---

## Module: Networking (Advanced)

### OpenVPN Plugin Install

| Distro | Package(s) | Status | Notes |
|--------|------------|--------|-------|
| Arch | `networkmanager-openvpn` | ⚠️ ASSUMED | |
| Debian | `network-manager-openvpn-gnome` | ⚠️ ASSUMED | Long name - verify |
| Fedora | `NetworkManager-openvpn-gnome` | ⚠️ ASSUMED | CamelCase - verify |
| openSUSE | `NetworkManager-openvpn` | ⚠️ ASSUMED | Different from Fedora? |

### WireGuard Install

| Distro | Package(s) | Status | Notes |
|--------|------------|--------|-------|
| Arch | `wireguard-tools` | ⚠️ ASSUMED | |
| Debian | `wireguard` | ⚠️ ASSUMED | Different name! |
| Fedora | `wireguard-tools` | ⚠️ ASSUMED | |
| openSUSE | `wireguard-tools` | ⚠️ ASSUMED | |

---

## Module: Gaming

### Steam Install

| Distro | Package(s) | Status | Notes |
|--------|------------|--------|-------|
| Arch | `steam` | ✅ VERIFIED | Requires multilib |
| Debian | `steam` | ⚠️ ASSUMED | May need i386 arch enabled |
| Fedora | `steam` | ❌ BROKEN? | **Requires RPM Fusion** - do we enable it? |
| openSUSE | `steam` | ❌ BROKEN? | **May require extra repo** |

### Lutris Install

| Distro | Package(s) | Status | Notes |
|--------|------------|--------|-------|
| Arch | `lutris` | ✅ VERIFIED | |
| Debian | `lutris` | ⚠️ ASSUMED | May need PPA |
| Fedora | `lutris` | ⚠️ ASSUMED | |
| openSUSE | `lutris` | ⚠️ ASSUMED | |

### GameMode Install

| Distro | Package(s) | Status | Notes |
|--------|------------|--------|-------|
| Arch | `gamemode lib32-gamemode` | ✅ VERIFIED | |
| Debian | `gamemode` | ⚠️ ASSUMED | |
| Fedora | `gamemode` | ⚠️ ASSUMED | |
| openSUSE | `gamemode` | ❌ BROKEN | **Requires games:tools repo** |

### MangoHud Install

| Distro | Package(s) | Status | Notes |
|--------|------------|--------|-------|
| Arch | `mangohud lib32-mangohud` | ✅ VERIFIED | |
| Debian | `mangohud` | ⚠️ ASSUMED | |
| Fedora | `mangohud` | ⚠️ ASSUMED | |
| openSUSE | `mangohud` | ⚠️ ASSUMED | May need games:tools repo |

### Xbox Controller (xboxdrv)

| Distro | Package(s) | Status | Notes |
|--------|------------|--------|-------|
| Arch | `xboxdrv` | ⚠️ ASSUMED | May be AUR only |
| Debian | `xboxdrv` | ⚠️ ASSUMED | |
| Fedora | `xboxdrv` | ⚠️ ASSUMED | |
| openSUSE | **MISSING** | ❌ BROKEN | **Not defined in code!** |

### PlayStation Controller (ds4drv)

| Distro | Package(s) | Status | Notes |
|--------|------------|--------|-------|
| Arch | `ds4drv` | ⚠️ ASSUMED | AUR only? |
| Debian | `ds4drv` | ⚠️ ASSUMED | |
| Fedora | **MISSING** | ❌ BROKEN | **Not defined in code!** |
| openSUSE | **MISSING** | ❌ BROKEN | **Not defined in code!** |

### Bottles Install

| Distro | Package(s) | Status | Notes |
|--------|------------|--------|-------|
| Arch | `bottles` | ✅ VERIFIED | |
| Debian | **Flatpak only** | ⚠️ ASSUMED | Falls back to Flatpak |
| Fedora | **Flatpak only** | ⚠️ ASSUMED | Falls back to Flatpak |
| openSUSE | **Flatpak only** | ⚠️ ASSUMED | Falls back to Flatpak |

### ProtonUp-Qt Install

| Distro | Package(s) | Status | Notes |
|--------|------------|--------|-------|
| Arch | `protonup-qt` | ✅ VERIFIED | |
| Others | **Flatpak only** | ⚠️ ASSUMED | Falls back to Flatpak |

---

## Module: System Maintenance

### Disk Analyzer (baobab/filelight)

| Distro | Package(s) | Status | Notes |
|--------|------------|--------|-------|
| Arch | `baobab` or `filelight` | ⚠️ ASSUMED | |
| Debian | `baobab` or `filelight` | ⚠️ ASSUMED | |
| Fedora | `baobab` or `filelight` | ⚠️ ASSUMED | |
| openSUSE | `baobab` or `filelight` | ⚠️ ASSUMED | |

---

## CRITICAL ISSUES FOUND

### 1. Missing Package Definitions
These packages are NOT defined for all distros:
- `xboxdrv` - Missing openSUSE
- `ds4drv` - Missing Fedora and openSUSE

### 2. Packages Requiring Extra Repos (NOT HANDLED)
These will FAIL on fresh installs:
- **Steam on Fedora** - Needs RPM Fusion
- **Steam on openSUSE** - May need extra repo  
- **GameMode on openSUSE** - Needs games:tools repo
- **Timeshift on openSUSE** - Needs Archiving:Backup repo (we added this)

### 3. Package Name Variations (UNVERIFIED)
These have different names across distros - need testing:
- Bluetooth packages
- OpenVPN NM plugin
- WireGuard

### 4. AUR-Only Packages on Arch
Some packages may be AUR-only, not in official repos:
- `xboxdrv` - verify
- `ds4drv` - verify

---

## WHAT NEEDS TO HAPPEN

### Option A: Test on Real Hardware (BEST)
1. Spin up VMs for Debian, Fedora, openSUSE
2. Install Tux Assistant on each
3. Test EVERY install button
4. Document what works and what fails
5. Fix failures

### Option B: Add Graceful Failure Handling
1. Before installing, check if package exists
2. If not, show helpful message: "This package requires [X repo]"
3. Offer to enable the repo or suggest Flatpak alternative

### Option C: Use Flatpak for Everything Uncertain
1. For any package not in default repos, use Flatpak
2. Requires Flatpak to be installed first
3. Less "native" but more reliable

---

## RECOMMENDED APPROACH

**Hybrid: Test what we can + Add graceful failures + Flatpak fallbacks**

1. Keep native packages for things that definitely work
2. Add repo-enabling for known requirements (RPM Fusion, games:tools)
3. Fall back to Flatpak when native isn't available
4. ALWAYS check if package install succeeded and report clearly

---

## NEXT STEPS

1. [ ] YOU test on Debian/Ubuntu VM
2. [ ] YOU test on Fedora VM
3. [ ] YOU test on openSUSE VM
4. [ ] Document all failures
5. [ ] Fix each failure with appropriate solution
6. [ ] Re-test until all green

**The "It Just Works" promise requires REAL testing, not web searches.**
