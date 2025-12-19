# Tux Assistant - Distro Package Audit

This document tracks all packages that Tux Assistant installs and their availability across distributions.

**Last Updated:** 2025-11-30

## Supported Distribution Families

| Family | Examples |
|--------|----------|
| **Arch** | Arch Linux, Manjaro, CachyOS, EndeavourOS, Garuda |
| **Debian** | Debian, Ubuntu, Linux Mint, Pop!_OS, Zorin |
| **Fedora** | Fedora, Nobara, Ultramarine |
| **openSUSE** | Tumbleweed, Leap, Slowroll |

---

## Hardware Manager Module

### Printer Support (CUPS)

| Package | Arch | Debian | Fedora | openSUSE | Notes |
|---------|------|--------|--------|----------|-------|
| cups | ✅ cups | ✅ cups | ✅ cups | ✅ cups | Core printing |
| cups-pdf | ✅ cups-pdf | ✅ cups-pdf | ✅ cups-pdf | ✅ cups-pdf | PDF printer |
| system-config-printer | ✅ system-config-printer | ✅ system-config-printer | ✅ system-config-printer | ✅ system-config-printer | GUI config |

**Status:** ✅ All verified

### Bluetooth Support

| Package | Arch | Debian | Fedora | openSUSE | Notes |
|---------|------|--------|--------|----------|-------|
| bluez | ✅ bluez | ✅ bluez | ✅ bluez | ✅ bluez | Bluetooth stack |
| bluez-utils | ✅ bluez-utils | ❌ N/A | ❌ N/A | ❌ N/A | Arch-specific utils |
| bluetooth (metapackage) | ❌ N/A | ✅ bluetooth | ❌ N/A | ❌ N/A | Debian metapackage |
| bluez-tools | ❌ N/A | ❌ N/A | ✅ bluez-tools | ❌ N/A | Fedora extra tools |
| blueman | ✅ blueman | ✅ blueman | ✅ blueman | ✅ blueman | GUI manager |

**Status:** ✅ All verified - distro-specific packages handled

---

## Backup & Restore Module

### File Backup

| Package | Arch | Debian | Fedora | openSUSE | Notes |
|---------|------|--------|--------|----------|-------|
| rsync | ✅ rsync | ✅ rsync | ✅ rsync | ✅ rsync | Universal |

### System Snapshots

| Package | Arch | Debian | Fedora | openSUSE | Notes |
|---------|------|--------|--------|----------|-------|
| timeshift | ✅ timeshift | ✅ timeshift | ✅ timeshift | ⚠️ timeshift | May need extra repo on openSUSE |

**Note:** Timeshift on openSUSE might need the community repo. Consider adding snapper as alternative for openSUSE.

---

## Networking Module

### VPN Support

| Package | Arch | Debian | Fedora | openSUSE | Notes |
|---------|------|--------|--------|----------|-------|
| OpenVPN NM plugin | ✅ networkmanager-openvpn | ✅ network-manager-openvpn-gnome | ✅ NetworkManager-openvpn-gnome | ✅ NetworkManager-openvpn | Package names differ |
| WireGuard | ✅ wireguard-tools | ✅ wireguard | ✅ wireguard-tools | ✅ wireguard-tools | |

**Status:** ✅ Verified

### Network Tools

| Package | Arch | Debian | Fedora | openSUSE | Notes |
|---------|------|--------|--------|----------|-------|
| speedtest-cli | ✅ speedtest-cli | ✅ speedtest-cli | ✅ speedtest-cli | ✅ speedtest-cli | Universal |

**Status:** ✅ Verified

---

## Gaming Module

### Gaming Platforms

| Package | Arch | Debian | Fedora | openSUSE | Notes |
|---------|------|--------|--------|----------|-------|
| steam | ✅ steam | ✅ steam | ✅ steam | ✅ steam | May need multilib/32-bit |
| lutris | ✅ lutris | ✅ lutris | ✅ lutris | ✅ lutris | |
| bottles | ✅ bottles | ⚠️ Flatpak | ⚠️ Flatpak | ⚠️ Flatpak | AUR/Flatpak only |

### Gaming Utilities

| Package | Arch | Debian | Fedora | openSUSE | Notes |
|---------|------|--------|--------|----------|-------|
| gamemode | ✅ gamemode | ✅ gamemode | ✅ gamemode | ✅ gamemode | |
| lib32-gamemode | ✅ lib32-gamemode | ❌ N/A | ❌ N/A | ❌ N/A | Arch 32-bit lib |
| mangohud | ✅ mangohud | ✅ mangohud | ✅ mangohud | ✅ mangohud | |
| lib32-mangohud | ✅ lib32-mangohud | ❌ N/A | ❌ N/A | ❌ N/A | Arch 32-bit lib |
| protonup-qt | ✅ protonup-qt | ⚠️ Flatpak | ⚠️ Flatpak | ⚠️ Flatpak | AUR/Flatpak |

### Controller Drivers

| Package | Arch | Debian | Fedora | openSUSE | Notes |
|---------|------|--------|--------|----------|-------|
| xboxdrv | ✅ xboxdrv | ✅ xboxdrv | ✅ xboxdrv | ⚠️ May need repo | |
| ds4drv | ✅ ds4drv | ✅ ds4drv | ⚠️ pip/AUR | ⚠️ pip | Python package |

---

## System Maintenance Module

### Cleanup Tools

| Tool | Arch | Debian | Fedora | openSUSE | Notes |
|------|------|--------|--------|----------|-------|
| paccache | ✅ pacman-contrib | ❌ N/A | ❌ N/A | ❌ N/A | Arch-specific |
| apt clean | ❌ N/A | ✅ Built-in | ❌ N/A | ❌ N/A | |
| dnf clean | ❌ N/A | ❌ N/A | ✅ Built-in | ❌ N/A | |
| zypper clean | ❌ N/A | ❌ N/A | ❌ N/A | ✅ Built-in | |

**Status:** ✅ Handled with fallbacks

---

## Issues to Address

### High Priority

1. **Timeshift on openSUSE** - May not be in default repos
   - Consider: Add snapper as openSUSE alternative
   - Or: Document that user may need community repo

2. **Bottles** - Not in most repos
   - Current: Only shows on Arch
   - Consider: Offer Flatpak install option for all distros

3. **ProtonUp-Qt** - Similar to Bottles
   - Consider: Flatpak option

### Medium Priority

4. **ds4drv** - Python package, not in all repos
   - Consider: pip install fallback

5. **xboxdrv on openSUSE** - Availability unclear
   - Need to verify

### Low Priority

6. **32-bit libraries** - Arch-specific (lib32-*)
   - These are optional enhancements, not critical

---

## Package Manager Commands Reference

```bash
# Arch
sudo pacman -S --needed --noconfirm <package>

# Debian/Ubuntu
sudo apt install -y <package>

# Fedora
sudo dnf install -y <package>

# openSUSE
sudo zypper install -y <package>
```

---

## Testing Checklist

Before release, test on:

- [ ] Arch Linux (or CachyOS/EndeavourOS)
- [ ] Ubuntu LTS (or Linux Mint)
- [ ] Fedora (current)
- [ ] openSUSE Tumbleweed

For each, verify:
- [ ] Hardware Manager: Printers install
- [ ] Hardware Manager: Bluetooth install
- [ ] Backup: rsync install
- [ ] Backup: Timeshift install
- [ ] Networking: speedtest-cli install
- [ ] Networking: OpenVPN plugin install
- [ ] Networking: WireGuard install
- [ ] Gaming: Steam install
- [ ] Gaming: Lutris install
