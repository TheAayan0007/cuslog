#!/usr/bin/env python3
"""
Installer for Lock Screen & SDDM Breeze Customizer (lockscreen-config)
Repository: https://github.com/TheAayan0007/cuslog
"""

import sys
import os
import shutil
import urllib.request
import urllib.error
import subprocess

GITHUB_RAW_URL = "https://raw.githubusercontent.com/TheAayan0007/cuslog/main/lockscreen-config.py"
GITHUB_FALLBACK_URL = "https://github.com/TheAayan0007/cuslog/raw/main/lockscreen-config.py"
APP_NAME = "lockscreen-config"

# ANSI Colors
class Colors:
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

def log_info(msg):
    print(f"{Colors.CYAN}[*]{Colors.RESET} {msg}")

def log_success(msg):
    print(f"{Colors.GREEN}[✓]{Colors.RESET} {Colors.BOLD}{msg}{Colors.RESET}")

def log_warn(msg):
    print(f"{Colors.YELLOW}[!]{Colors.RESET} {msg}")

def log_error(msg):
    print(f"{Colors.RED}[✗]{Colors.RESET} {Colors.BOLD}{msg}{Colors.RESET}")

def download_file(url, fallback_url=None):
    """Downloads content from GitHub raw URL using standard library urllib."""
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) lockscreen-config-installer"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            return response.read().decode("utf-8")
    except Exception as e:
        if fallback_url:
            log_warn(f"Primary URL failed ({e}). Trying fallback URL...")
            req_fb = urllib.request.Request(fallback_url, headers=headers)
            with urllib.request.urlopen(req_fb, timeout=15) as response:
                return response.read().decode("utf-8")
        raise e

def check_dependencies():
    """Checks for required Python libraries."""
    log_info("Checking system dependencies...")
    try:
        import PyQt6
        log_success("PyQt6 is installed.")
        return True
    except ImportError:
        log_warn("PyQt6 is not currently installed in this Python environment.")
        print(f"    {Colors.YELLOW}To install PyQt6, run:{Colors.RESET}")
        print(f"      sudo apt install python3-pyqt6    {Colors.CYAN}(Debian/Ubuntu/Kali){Colors.RESET}")
        print(f"      pip install PyQt6                 {Colors.CYAN}(Pip/Virtualenv){Colors.RESET}\n")
        return False

def install(is_system=False):
    is_root = (os.geteuid() == 0)
    if is_system or is_root:
        bin_dir = "/usr/local/bin"
        app_dir = "/usr/share/applications"
    else:
        bin_dir = os.path.expanduser("~/.local/bin")
        app_dir = os.path.expanduser("~/.local/share/applications")

    target_bin = os.path.join(bin_dir, APP_NAME)
    target_desktop = os.path.join(app_dir, f"{APP_NAME}.desktop")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    local_candidates = [
        os.path.join(script_dir, "lockscreen-config.py"),
        os.path.join(script_dir, "lockscreen-config"),
        os.path.join(os.getcwd(), "lockscreen-config.py"),
    ]

    source_code = None
    source_path_used = None

    for candidate in local_candidates:
        if os.path.isfile(candidate) and os.path.getsize(candidate) > 1000:
            source_path_used = candidate
            log_info(f"Found local file at: {candidate}")
            with open(candidate, "r", encoding="utf-8") as f:
                source_code = f.read()
            break

    if not source_code:
        log_info(f"Local {APP_NAME}.py not found in same directory.")
        log_info(f"Fetching from GitHub ({GITHUB_RAW_URL})...")
        try:
            source_code = download_file(GITHUB_RAW_URL, GITHUB_FALLBACK_URL)
            log_success(f"Downloaded successfully ({len(source_code)} characters).")

            # Save a local copy in script_dir if writable
            local_save = os.path.join(script_dir, "lockscreen-config.py")
            try:
                with open(local_save, "w", encoding="utf-8") as f:
                    f.write(source_code)
                os.chmod(local_save, 0o755)
                log_info(f"Cached a local copy at {local_save}")
            except Exception:
                pass
        except Exception as e:
            log_error(f"Failed to download lockscreen-config.py from GitHub: {e}")
            sys.exit(1)

    # Ensure shebang exists
    if not source_code.startswith("#!"):
        source_code = "#!/usr/bin/env python3\n" + source_code

    # Create target bin directory
    os.makedirs(bin_dir, exist_ok=True)

    # Remove existing symlink or file if present
    if os.path.islink(target_bin) or os.path.exists(target_bin):
        try:
            os.remove(target_bin)
        except Exception as e:
            log_error(f"Cannot overwrite existing {target_bin}: {e}")
            if not is_root:
                log_info("Try running with sudo if permissions are required.")
            sys.exit(1)

    # Write target executable binary
    log_info(f"Installing binary to {target_bin}...")
    with open(target_bin, "w", encoding="utf-8") as f:
        f.write(source_code)

    os.chmod(target_bin, 0o755)
    log_success(f"Installed executable at {target_bin}")

    # Install Desktop Application entry
    os.makedirs(app_dir, exist_ok=True)
    desktop_content = f"""[Desktop Entry]
Name=Lock Screen & Login Customizer
Comment=Configure KDE Breeze lock screen and SDDM login screen fonts, positions, time, and animations
Exec={target_bin}
Icon=preferences-desktop-screensaver
Terminal=false
Type=Application
Categories=Settings;DesktopSettings;Qt;KDE;
StartupNotify=true
"""
    log_info(f"Creating application menu entry at {target_desktop}...")
    try:
        with open(target_desktop, "w", encoding="utf-8") as f:
            f.write(desktop_content)
        log_success(f"Desktop launcher created at {target_desktop}")

        # Update desktop database if tool is installed
        if shutil.which("update-desktop-database"):
            subprocess.run(["update-desktop-database", app_dir], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        log_warn(f"Could not create desktop shortcut: {e}")

    # Check dependencies
    check_dependencies()

    # Check if bin_dir is in PATH
    path_env = os.environ.get("PATH", "")
    in_path = any(os.path.abspath(p) == os.path.abspath(bin_dir) for p in path_env.split(os.pathsep) if p)

    print()
    print("=" * 60)
    log_success("Installation complete!")
    print("=" * 60)
    if in_path:
        print(f"You can now launch the customizer from anywhere by typing:")
        print(f"  {Colors.BOLD}{Colors.GREEN}{APP_NAME}{Colors.RESET}\n")
    else:
        log_warn(f"{bin_dir} is not in your current PATH environment variable.")
        print(f"Add it by adding this line to your ~/.bashrc or ~/.zshrc:")
        print(f"  export PATH=\"{bin_dir}:$PATH\"\n")
        print(f"Or run directly with:")
        print(f"  {target_bin}\n")

def uninstall(is_system=False):
    is_root = (os.geteuid() == 0)
    if is_system or is_root:
        target_bin = f"/usr/local/bin/{APP_NAME}"
        target_desktop = f"/usr/share/applications/{APP_NAME}.desktop"
    else:
        target_bin = os.path.expanduser(f"~/.local/bin/{APP_NAME}")
        target_desktop = os.path.expanduser(f"~/.local/share/applications/{APP_NAME}.desktop")

    removed = False
    for path in [target_bin, target_desktop]:
        if os.path.exists(path) or os.path.islink(path):
            try:
                os.remove(path)
                log_success(f"Removed: {path}")
                removed = True
            except Exception as e:
                log_error(f"Failed to remove {path}: {e}")

    if removed:
        log_success("Uninstallation complete.")
    else:
        log_info("Nothing to uninstall.")

if __name__ == "__main__":
    if "--help" in sys.argv or "-h" in sys.argv:
        print(f"{Colors.BOLD}{Colors.CYAN}lockscreen-config installer{Colors.RESET}")
        print("Usage:")
        print("  python3 installer.py            Install for current user (~/.local/bin)")
        print("  sudo python3 installer.py       Install system-wide (/usr/local/bin)")
        print("  python3 installer.py --system   Install to /usr/local/bin (requires root)")
        print("  python3 installer.py --uninstall Remove lockscreen-config and desktop entry")
        sys.exit(0)
    elif "--uninstall" in sys.argv:
        uninstall(is_system="--system" in sys.argv)
    else:
        install(is_system="--system" in sys.argv)
