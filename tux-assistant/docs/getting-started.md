# Getting Started with Tux Assistant

This guide gets you from zero to running in about five minutes.

## Installation

### Step 1: Download

Grab the latest release from [GitHub](https://github.com/dorrellkc/tux-assistant/releases) or clone the repository:

```bash
git clone https://github.com/dorrellkc/tux-assistant.git
cd tux-assistant
```

### Step 2: Install

Run the installer:

```bash
sudo bash install.sh
```

You'll see a progress display as it:
- Checks dependencies (Python, GTK4, libadwaita)
- Copies files to `/opt/tux-assistant`
- Creates menu entries

### Step 3: Launch

Find **Tux Assistant** in your application menu, or run:

```bash
tux-assistant
```

That's it. You're in.

---

## The Main Screen

When you launch, you'll see the main screen organized into sections:

### System Information
Shows your distribution, desktop environment, package manager, and hardware at a glance. If you see a button to install `hardinfo2`, that's optional—it gives you more detailed hardware info.

### Setup and Configuration
- **Setup Tools**: First-time setup stuff. Codecs, drivers, common apps.
- **Software Center**: Browse and install applications by category.

### Developer Tools
Git project management, SSH key setup, and development utilities. If you're working on code, this is where you'll spend time. See the [Developer Tools guide](modules/developer-tools.md) for the full walkthrough.

### Network and Sharing
- **Networking**: Samba shares, network discovery, firewall settings, Active Directory join.

### Server and Cloud
- **Nextcloud Server**: Set up your own personal cloud.
- **Media Server**: Plex, Jellyfin, or Emby configuration.

### Media and Entertainment
- **Tux Tunes**: Internet radio player with smart recording.

---

## How Things Work

Most features follow the same pattern:

1. **Click a row** to see options or expand details
2. **Click a button** to perform an action
3. **Watch the toast** (notification at bottom) for status
4. **Terminal windows** pop up when you need to enter a password or see progress

When something needs root access, you'll get a terminal window asking for your password. This keeps things transparent—you always see what's happening.

---

## The Version Number

Look at the top-left corner of the window. You'll see something like `v5.7.14`. That's your current version. After updates, you can verify you're running the new version at a glance.

---

## Getting Help Inside the App

- **Hamburger menu** (top right): About dialog, quit
- **Getting Started button** (main page): Quick reference, always available
- **How to Update button** (Developer Tools → Git Projects): Step-by-step update workflow

---

## Next Steps

Depending on what you need:

- **Just installed Linux?** Start with [Setup Tools](modules/setup-tools.md) to get codecs and drivers
- **Working on code?** Head to [Developer Tools](modules/developer-tools.md)
- **Setting up a home server?** Check [Media Server](modules/media-server.md) or [Nextcloud](modules/nextcloud.md)
- **Want to customize your desktop?** See [Desktop Enhancements](modules/desktop-enhancements.md)

---

## Troubleshooting

### App won't launch
Make sure you have the dependencies:
```bash
# Arch-based
sudo pacman -S python gtk4 libadwaita

# Debian/Ubuntu
sudo apt install python3 libgtk-4-1 libadwaita-1-0

# Fedora
sudo dnf install python3 gtk4 libadwaita
```

### "Command not found" when running install.sh
The script needs execute permission:
```bash
chmod +x install.sh
sudo bash install.sh
```

### Something else?
[Open an issue](https://github.com/dorrellkc/tux-assistant/issues) with:
- Your distribution and version
- What you were trying to do
- What happened instead

---

## Further Reading

- [Arch Wiki](https://wiki.archlinux.org/) - Deep dives on almost any Linux topic
- [GNOME Developer Documentation](https://developer.gnome.org/) - GTK4/libadwaita reference
- [Git Documentation](https://git-scm.com/doc) - Official Git reference
