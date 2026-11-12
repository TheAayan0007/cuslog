# ⚡ RAM Cleaner & Memory Optimizer (`ram-cleaner`)

A smart, safe Linux memory optimization utility designed to detect and terminate unnecessary background software, idle scripts, and leaked daemons to drive active RAM usage down to your target goal (e.g. **1.7 – 1.8 GB**).

---

## 🎯 How It Works on Your System

On your PC, memory is typically divided between:
1. **Desktop & System Baseline:** KDE Plasma, KWin, Wayland, and PipeWire audio (~1.1 – 1.3 GB).
2. **Current Active IDE (Antigravity):** ~1.1 – 1.3 GB (protected so your session never crashes).
3. **Heavy Background Apps:** **Spotify** alone holds **~1.9 GB** across 10 processes, even when minimized or idle!
4. **Leaked Greeter Daemons:** `sddm-greeter-qt6` often leaks and lingers after Wayland login, holding **~272 MB**.
5. **Idle Background Scripts:** Orphaned or detached Python/Node/Bash workers running with 0% CPU.

When `ram-cleaner` runs, it scans running processes, calculates how much RAM is required to reach your target (e.g., `1.8 GB`), prioritizes the heaviest idle consumers, and safely terminates them.

---

## 🚀 Quick Start

The script is installed globally at `/home/windows/.local/bin/ram-cleaner` (which is already in your `$PATH`). You can run it from any terminal:

### 1. Interactive Mode (Default)
Inspects running software, shows current RAM usage vs target, and lets you choose:
```bash
ram-cleaner
```
You will be prompted:
- `[1]` Auto-quit enough apps to reach your 1.80 GB target
- `[2]` Quit all detected idle applications & scripts
- `[3]` Select specific applications to close by number
- `[c]` Flush kernel pagecache & buffers (`drop_caches`)
- `[q]` Cancel / Exit

### 2. One-Shot Auto-Clean
Directly closes the heaviest idle applications until your target RAM is met:
```bash
ram-cleaner -y
```

### 3. Custom Target (e.g. 1.7 GB)
Specify any target RAM threshold:
```bash
ram-cleaner --target 1.7 -y
```

### 4. Check Status (No Changes)
View current memory usage and detected candidates without modifying anything:
```bash
ram-cleaner --status
```

### 5. Safe Simulation (Dry-Run)
See what would be closed and estimated RAM freed without terminating any process:
```bash
ram-cleaner --dry-run
```

### 6. Full Clean with Root (Global Symlink & Cache)
To make `sudo ram-cleaner` work directly with sudo's `secure_path`, link it once:
```bash
sudo ln -s ~/.local/bin/ram-cleaner /usr/local/bin/ram-cleaner
```
Then you can run with root anywhere:
```bash
sudo ram-cleaner -y -c
```
*(Or simply run `ram-cleaner -y -c` as normal user; it will elevate via sudo automatically when needed).*

---

## 🛡️ Ironclad Protection (Safety Whitelist)

`ram-cleaner` has built-in protections and will **NEVER** kill:
- **Your active terminal & shell:** The shell running `ram-cleaner` and all parent processes up to PID 1 are detected and protected.
- **Your active IDE / AI session:** Antigravity IDE and language server are preserved.
- **Desktop Environment:** `plasmashell`, `kwin_wayland`, `ksmserver`, `kded6`, `Xwayland`, `krunner`.
- **Core System Daemons:** `systemd`, `dbus`, `NetworkManager`, `wireplumber`, `pipewire`, `bluetoothd`.

---

## 📋 Command Line Flags

| Flag | Short | Description |
|---|---|---|
| `--target <GB>` | `-t` | Set custom target RAM usage in GB (default: `1.8`) |
| `--auto` | `-y` | Automatically quit candidates until target RAM is reached |
| `--all` | `-a` | Quit all detected candidates regardless of target |
| `--dry-run` | `-n` | Preview actions without quitting any processes |
| `--status` | `-s` | Print current memory stats and candidate list |
| `--drop-cache` | `-c` | Flush Linux pagecache, inodes, and dentries |
| `--include-browsers` | `-b` | Include idle web browsers (Chrome, Firefox, Brave) |
| `--aggressive` | | Include browsers and all background runtime workers |
