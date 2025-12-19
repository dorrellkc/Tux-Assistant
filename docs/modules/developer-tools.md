# Developer Tools

Developer Tools handles Git project management, SSH keys, and development environment setup. If you're working on code and want to push/pull without touching the terminal, this is your section.

---

## Prerequisites

Before you can push or pull code, you need two things set up:

### SSH Keys

SSH keys let you authenticate with GitHub, GitLab, or other Git hosts without typing a password every time.

**If you already have keys**: The app will show a checkmark and your key type (like `id_ed25519`).

**If you need to generate keys**:
1. Click the SSH Keys row
2. Follow the prompts to generate a new key pair
3. Copy the public key to your Git host (GitHub → Settings → SSH Keys)

**If you have keys on another machine**: Use the Developer Kit import feature (explained below).

### Git Identity

Your name and email that appear on commits. If not set, click the Git Identity row to configure.

---

## Git Projects

This is the main section. It shows your repositories and lets you push/pull with buttons instead of commands.

### Finding Your Projects

**Automatic scan**: Click the magnifying glass icon. The app checks common locations:
- `~/Development`
- `~/Projects`
- `~/Code`
- `~/repos`
- `~/git`

**Manual add**: Click the `+` icon to select a folder that contains a `.git` directory.

### Understanding the Project Row

Each project shows:
- **Name**: Folder name
- **Branch**: Current branch (usually `main`)
- **Status**: 
  - `✓ Up to date` - Nothing to do
  - `📝 Changes` - You have uncommitted changes
  - `⬆️ X ahead` - You have commits to push
  - `⬇️ X behind` - Remote has commits you don't have

### Push and Pull Buttons

**Pull** (down arrow): Gets the latest changes from the remote. Use this when someone else (or you on another machine) pushed changes.

**Push** (up arrow): Sends your commits to the remote. Use this after you've made and committed changes.

When you click either button, a terminal window opens. This is intentional—if your SSH key has a passphrase, you'll need to type it here. You'll also see exactly what Git is doing.

### The Expanded View

Click the arrow on a project row to expand it. You'll see:
- **Path**: Where the project lives on your disk
- **Remote**: The GitHub/GitLab URL
- **Last Commit**: Most recent commit message
- **Actions**:
  - **Install to System**: Runs `install.sh` if the project has one (for apps like Tux Assistant itself)
  - **Open Folder**: Opens in your file manager
  - **Terminal**: Opens a terminal in that directory
  - **Trash icon**: Removes from the list (doesn't delete the actual files)

---

## The Update Workflow

This is specifically for updating a project from a downloaded ZIP file—like when you download a new version of Tux Assistant.

### Why This Exists

When you download a ZIP from GitHub (or anywhere), you have new files but no Git history. This workflow:
1. Extracts the ZIP into your existing project
2. Preserves your `.git` folder (keeps your history intact)
3. Lets you commit and push the changes
4. Installs the update to your system

### Step-by-Step

**Step 1: Update the files**
1. Scroll down to "Other Git Tools"
2. Click "Update Project from ZIP"
3. Click "Browse" and select your downloaded ZIP
4. Select your project from the list
5. Click "Update Project"
6. Wait for the checkmarks to complete
7. Click "← Back to Push"

**Step 2: Push to Git**
1. Find your project in the Git Projects list
2. Click the "Push" button
3. A terminal opens—enter your SSH passphrase if prompted
4. Wait for "Push successful"
5. Press Enter to close the terminal

**Step 3: Install to System**
1. Click the arrow on your project to expand it
2. Click "Install to System"
3. A terminal opens—enter your sudo password
4. Wait for installation to complete
5. Press Enter to close the terminal

**Step 4: Restart**
1. Close Tux Assistant
2. Relaunch from your application menu
3. Check the version number (top-left) to confirm the update

### The "How to Update" Button

Can't remember these steps? Click the "How to Update" button in the Git Projects header. It shows this same workflow in a popup.

---

## Developer Kit

Moving to a new machine? The Developer Kit exports everything you need to get back up and running.

### What Gets Exported

- SSH keys (the files in `~/.ssh`)
- Git identity (name and email)
- Project list (so you don't have to scan again)

### Exporting

1. Click "Export Developer Kit"
2. Choose where to save (like a USB drive)
3. A folder is created with your keys and a manifest file

### Importing

1. Click "Import Developer Kit"
2. Navigate to the folder you exported
3. Your keys and settings are restored

**Security note**: Your SSH private key is sensitive. Keep the export on a USB drive you control, not in cloud storage.

---

## Other Git Tools

### Clone Git Repository
Downloads a repository from GitHub/GitLab. Enter the SSH URL (like `git@github.com:username/repo.git`) and it clones to your Development folder.

### Restore SSH Keys
Drag and drop backed-up SSH key files to restore them. Useful if you backed up keys manually rather than using Developer Kit.

---

## Common Questions

### Why does a terminal window open?

Two reasons:
1. **SSH passphrase**: If your key is password-protected, you need to type it somewhere. A terminal is the standard way.
2. **Sudo password**: Installing to system requires root access. You should see exactly what's happening.

### Can I avoid typing my passphrase every time?

Yes. Run this once after logging in:
```bash
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519
```
Enter your passphrase once, and it's remembered for the session.

Or, generate keys without a passphrase (less secure, but convenient for personal machines).

### What if push fails?

Common causes:
- **Passphrase typo**: Try again, type carefully
- **No remote access**: Make sure your public key is added to GitHub/GitLab
- **Branch protection**: Some repos require pull requests instead of direct pushes

### What if the project list is empty?

Either:
- You don't have any Git repos in the scanned folders
- Your repos are in non-standard locations → Use "Add Manually"
- You need to clone a repo first → Use "Clone Git Repository"

---

## Further Reading

- [GitHub SSH Setup Guide](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)
- [Git Basics](https://git-scm.com/book/en/v2/Getting-Started-Git-Basics)
- [Understanding Git Push/Pull](https://www.atlassian.com/git/tutorials/syncing)
