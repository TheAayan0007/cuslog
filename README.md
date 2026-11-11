# Desktop Utilities Bundle (`utils`)

Exported utilities:
- **`lockscreen-config`** (`lockscreen-config/`): KDE Plasma 6 Breeze lock screen, logout screen, and SDDM login customizer (`PyQt6`).
- **`customize-dock`** (`customize-dock/`): KDE Plasma 6 bottom dock & top bar customizer (`PyQt6` GUI + CLI) plus the `Panel.qml` shell view override for independent top-bar styling.
- **`ram-cleaner`** (`ram-cleaner/`): Memory & idle-process cleaner CLI (`psutil`).

## Install All Three
```bash
python3 installer.py
```

### Useful Options
- Preview without modifying files:
  ```bash
  python3 installer.py --dry-run
  ```
- Also symlink into `/usr/local/bin` (useful for `sudo ram-cleaner`):
  ```bash
  python3 installer.py --global
  ```
- Install only specific apps:
  ```bash
  python3 installer.py --only customize-dock ram-cleaner
  ```
- Uninstall:
  ```bash
  python3 installer.py --uninstall
  ```
