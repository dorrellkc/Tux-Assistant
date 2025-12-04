# Tux Assistant

<p align="center">
  <img src="assets/icon.svg" width="128" height="128" alt="Tux Assistant">
</p>

<p align="center">
  <strong>Your friendly Linux post-installation companion</strong>
</p>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#installation">Installation</a> •
  <a href="#included-apps">Apps</a> •
  <a href="#supported-distributions">Distros</a> •
  <a href="#license">License</a>
</p>

---

## What is Tux Assistant?

Tux Assistant is a GTK4/Libadwaita application that simplifies Linux post-installation setup. Instead of hunting through wikis and running dozens of terminal commands, Tux Assistant provides a friendly GUI to configure your system, install software, and set up services.

**Built for humans, not just power users.**

## Features

- 🖥️ **Desktop Enhancements** - Install themes, icons, fonts, extensions
- 📦 **Software Center** - One-click install of popular applications
- 🌐 **Network Setup** - Configure Samba shares, Active Directory, SSH
- 🎬 **Media Servers** - Set up Plex, Jellyfin, Emby with ease
- ☁️ **Nextcloud** - Deploy your own private cloud
- 💿 **ISO Creator** - Build custom live system snapshots
- 🎵 **Tux Tunes** - Internet radio player with smart recording

## Screenshots

<p align="center">
  <img src="screenshots/main.png" width="600" alt="Tux Assistant Main Window">
</p>
<p align="center"><em>Main Window - Your starting point for system setup</em></p>

<p align="center">
  <img src="screenshots/setup-tools.png" width="600" alt="Setup Tools">
</p>
<p align="center"><em>Setup Tools - Codecs, drivers, and essential configuration</em></p>

<p align="center">
  <img src="screenshots/gaming.png" width="600" alt="Gaming">
</p>
<p align="center"><em>Gaming - Steam, Lutris, and gaming utilities</em></p>

<p align="center">
  <img src="screenshots/media-server.png" width="600" alt="Media Server">
</p>
<p align="center"><em>Media Server - Plex, Jellyfin, and Emby setup</em></p>

## Included Apps

### Tux Tunes 🎵

<p align="center">
  <img src="assets/tux-tunes.svg" width="64" height="64" alt="Tux Tunes">
</p>

Internet radio player with access to 50,000+ stations via radio-browser.info.

**Features:**
- Search and browse stations by genre
- Save favorites and custom stations
- Smart recording with automatic song detection
- Pre-buffering to capture complete songs

## Installation

### Requirements

- Python 3.10+
- GTK 4.0+
- Libadwaita 1.0+
- GStreamer 1.0+ (for Tux Tunes)

### Quick Install

```bash
git clone https://github.com/dorrellkc/tux-assistant.git
cd tux-assistant
sudo ./install.sh
```

### Manual Install

```bash
# Clone the repo
git clone https://github.com/dorrellkc/tux-assistant.git
cd tux-assistant

# Copy to /opt
sudo cp -r . /opt/tux-assistant

# Run install script for icons and desktop entries
sudo ./install.sh
```

### Launch

After installation:
- **Tux Assistant** - Find in your app menu or run `tux-assistant`
- **Tux Tunes** - Find in your app menu or run `tux-tunes`

## Supported Distributions

| Distribution | Status |
|-------------|--------|
| Arch Linux | ✅ Full Support |
| CachyOS | ✅ Full Support |
| Manjaro | ✅ Full Support |
| EndeavourOS | ✅ Full Support |
| Debian | ✅ Full Support |
| Ubuntu | ✅ Full Support |
| Linux Mint | ✅ Full Support |
| Fedora | ✅ Full Support |
| openSUSE | ✅ Full Support |

## Project Structure

```
tux-assistant/
├── tux/
│   ├── apps/           # Standalone applications
│   │   └── tux_tunes/  # Internet radio player
│   ├── modules/        # Tux Assistant feature modules
│   ├── core/           # Shared libraries (distro detection, packages)
│   └── ui/             # UI components
├── assets/             # Icons and images
├── data/               # Desktop entries, polkit policies
├── install.sh          # Installation script
└── tux-assistant.py    # Main entry point
```

## Development

### Running from source

```bash
# Clone
git clone https://github.com/dorrellkc/tux-assistant.git
cd tux-assistant

# Run Tux Assistant
python3 tux-assistant.py

# Run Tux Tunes
python3 tux/apps/tux_tunes/tux-tunes.py
```

### Architecture

Tux Assistant uses a modular architecture where each feature is a self-contained module that registers itself with the main application. This makes it easy to add new features without modifying core code.

Apps like Tux Tunes are designed to work both as integrated modules and as standalone applications.

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## License

Copyright © 2025 Christopher Dorrell. Licensed under GPL-3.0.

This software is proprietary. See [LICENSE](LICENSE) for details.

## Acknowledgments

- [radio-browser.info](https://www.radio-browser.info/) - Free internet radio station database
- [GNOME](https://www.gnome.org/) - GTK and Libadwaita
- [Arch Linux](https://archlinux.org/) - Primary development platform

---

<p align="center">
  Made with 🐧 by Christopher Dorrell
</p>
