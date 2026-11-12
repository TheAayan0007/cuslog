# Desktop Utilities Bundle (`utils`)

Exported utilities inside `MAIN/`:
- **`lockscreen-config`** (`MAIN/lockscreen-config/`): KDE Plasma 6 Breeze lock screen, logout screen, and SDDM login customizer (`PyQt6`).
- **`customize-dock`** (`MAIN/customize-dock/`): KDE Plasma 6 bottom dock & top bar customizer (`PyQt6` GUI + CLI), the `Panel.qml` shell view override for independent top-bar styling, and the `CompactApplet.qml` override that lets you triple-click the bottom Application Launcher (Kali logo) to toggle the bottom dock between **Dodge Windows** and **Auto Hide**.
- **`ram-cleaner`** (`MAIN/ram-cleaner/`): Memory & idle-process cleaner CLI (`psutil`).
- **`uxplay-tray`** (`MAIN/uxplay-tray/`): Installs `uxplay`, `avahi-daemon`, and GStreamer plugins, auto-fixes the `No DNS-SD Server found` (`avahi-daemon`) error, and pins a top-bar AirPlay toggle button (left-click to start/stop mirroring, right-click to edit the AirPlay name via GUI or quit).
- **`vnc-tray`** (`MAIN/vnc-tray/`): Installs `krfb`, `tigervnc-viewer`, `avahi-daemon`, `libkf6config-bin`, and `libkscreen-bin`, pre-syncs KDE `krfbrc` password & remote-control keys (`unattendedPassword` / `desktopPassword`), and pins a top-bar **VNC 2nd Display** button for iPhone screen sharing/control via `krfb` or `krfb-virtualmonitor`.

## Install All Five
```bash
python3 MAIN/installer.py
```

### Useful Options
- Preview without modifying files:
  ```bash
  python3 MAIN/installer.py --dry-run
  ```
- Also symlink into `/usr/local/bin` (useful for `sudo ram-cleaner`):
  ```bash
  python3 MAIN/installer.py --global
  ```
- Install only specific apps:
  ```bash
  python3 MAIN/installer.py --only customize-dock ram-cleaner vnc-tray
  ```
- Uninstall:
  ```bash
  python3 MAIN/installer.py --uninstall
  ```
