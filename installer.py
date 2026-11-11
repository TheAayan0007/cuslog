#!/usr/bin/env python3
"""
Unified installer for desktop utilities:
  - lockscreen-config (KDE Plasma 6 lock screen, logout & SDDM customizer)
  - customize-dock    (KDE Plasma 6 bottom dock & top bar customizer)
  - ram-cleaner       (Linux memory & idle-process cleaner CLI)
"""

import argparse
import os
import shutil
import stat
import subprocess
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_BIN_DIR = os.path.expanduser("~/.local/bin")
DEFAULT_APPS_DIR = os.path.expanduser("~/.local/share/applications")
USER_SHELL_DIR = os.path.expanduser("~/.local/share/plasma/shells/org.kde.plasma.desktop")
SYSTEM_SHELL_DIR = "/usr/share/plasma/shells/org.kde.plasma.desktop"

APPS = {
    "lockscreen-config": {
        "description": "KDE Plasma 6 Lock Screen, Logout & SDDM Customizer (Qt6 GUI)",
        "binary_rel": os.path.join("lockscreen-config", "lockscreen-config"),
        "desktop_rel": os.path.join("lockscreen-config", "lockscreen-config.desktop"),
        "python_deps": [("PyQt6", "python3-pyqt6", "PyQt6")],
    },
    "customize-dock": {
        "description": "KDE Plasma 6 Bottom Dock & Top Bar Customizer (Qt6 GUI + CLI)",
        "binary_rel": os.path.join("customize-dock", "customize-dock"),
        "desktop_rel": os.path.join("customize-dock", "customize-dock.desktop"),
        "panel_qml_rel": os.path.join("customize-dock", "Panel.qml"),
        "python_deps": [("PyQt6", "python3-pyqt6", "PyQt6")],
    },
    "ram-cleaner": {
        "description": "RAM Cleaner & Memory Optimizer CLI",
        "binary_rel": os.path.join("ram-cleaner", "ram-cleaner"),
        "desktop_rel": None,
        "python_deps": [("psutil", "python3-psutil", "psutil")],
    },
}


def is_module_available(module_name):
    """Return True if a Python module can be imported in the current interpreter."""
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


def ensure_dependencies(selected_apps, dry_run=False):
    """Check required Python modules for selected apps and install missing ones."""
    required = {}
    for app_name in selected_apps:
        for mod_name, apt_pkg, pip_pkg in APPS[app_name]["python_deps"]:
            required[mod_name] = (apt_pkg, pip_pkg)

    missing = [
        (mod, apt_pkg, pip_pkg)
        for mod, (apt_pkg, pip_pkg) in required.items()
        if not is_module_available(mod)
    ]
    if not missing:
        print("[✓] All Python dependencies are already installed.")
        return True

    apt_pkgs = [apt_pkg for _, apt_pkg, _ in missing]
    pip_pkgs = [pip_pkg for _, _, pip_pkg in missing]
    print(f"[*] Missing Python modules: {', '.join(m[0] for m in missing)}")

    if dry_run:
        print(f"    [dry-run] Would install via apt ({' '.join(apt_pkgs)}) or pip ({' '.join(pip_pkgs)})")
        return True

    if shutil.which("apt-get"):
        cmd = ["apt-get", "install", "-y", *apt_pkgs]
        if os.geteuid() != 0:
            cmd = ["sudo", *cmd]
        print(f"[*] Installing dependencies via apt: {' '.join(apt_pkgs)}")
        if os.geteuid() != 0:
            subprocess.run(["sudo", "apt-get", "update"], check=False)
        else:
            subprocess.run(["apt-get", "update"], check=False)
        res = subprocess.run(cmd, check=False)
        if res.returncode == 0 and all(is_module_available(m) for m, _, _ in missing):
            print("[✓] Dependencies installed via apt.")
            return True

    if shutil.which("pip3") or shutil.which("pip"):
        pip_cmd = [sys.executable, "-m", "pip", "install", "--user", *pip_pkgs]
        print(f"[*] Falling back to pip: {' '.join(pip_pkgs)}")
        res = subprocess.run(pip_cmd, check=False)
        if res.returncode == 0:
            print("[✓] Dependencies installed via pip.")
            return True

    print(
        f"[!] Could not automatically install: {', '.join(m[0] for m in missing)}\n"
        f"    Install manually with: sudo apt install {' '.join(apt_pkgs)}  (or pip install {' '.join(pip_pkgs)})"
    )
    return False


def remove_existing_path(path):
    """Remove an existing file or symlink (including broken symlinks)."""
    if os.path.lexists(path):
        os.unlink(path)


def files_identical(src, dst):
    """Return True if both files exist and have identical contents."""
    if not (os.path.isfile(src) and os.path.isfile(dst)):
        return False
    with open(src, "rb") as f1, open(dst, "rb") as f2:
        return f1.read() == f2.read()


def install_binary(app_name, src_path, bin_dir, dry_run=False):
    """Copy an executable script into bin_dir and mark it 0755."""
    dest_path = os.path.join(bin_dir, app_name)
    if dry_run:
        print(f"    [dry-run] Would install binary: {src_path} -> {dest_path}")
        return dest_path

    os.makedirs(bin_dir, exist_ok=True)
    remove_existing_path(dest_path)
    shutil.copy2(src_path, dest_path)
    mode = os.stat(dest_path).st_mode
    os.chmod(dest_path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    print(f"    [✓] Installed binary: {dest_path}")
    return dest_path


def install_desktop_entry(src_desktop, apps_dir, exec_target, dry_run=False):
    """Install a .desktop launcher with Exec= updated to the target binary path."""
    dest_desktop = os.path.join(apps_dir, os.path.basename(src_desktop))
    with open(src_desktop, "r", encoding="utf-8") as f:
        lines = f.readlines()

    updated_lines = []
    replaced_exec = False
    for line in lines:
        if line.startswith("Exec="):
            updated_lines.append(f"Exec={exec_target}\n")
            replaced_exec = True
        else:
            updated_lines.append(line)
    if not replaced_exec:
        updated_lines.append(f"Exec={exec_target}\n")

    if dry_run:
        print(f"    [dry-run] Would install launcher: {dest_desktop} (Exec={exec_target})")
        return

    os.makedirs(apps_dir, exist_ok=True)
    remove_existing_path(dest_desktop)
    with open(dest_desktop, "w", encoding="utf-8") as f:
        f.writelines(updated_lines)
    os.chmod(dest_desktop, 0o644)
    print(f"    [✓] Installed launcher: {dest_desktop}")


def install_panel_qml(src_qml, dry_run=False):
    """Install the Plasma 6 Panel.qml override needed for independent top-bar styling."""
    dest_qml = os.path.join(USER_SHELL_DIR, "contents", "views", "Panel.qml")
    if dry_run:
        print(f"    [dry-run] Would install Plasma Panel.qml override: {dest_qml}")
        return

    if not os.path.exists(USER_SHELL_DIR) and os.path.exists(SYSTEM_SHELL_DIR):
        shutil.copytree(SYSTEM_SHELL_DIR, USER_SHELL_DIR)

    os.makedirs(os.path.dirname(dest_qml), exist_ok=True)
    if files_identical(src_qml, dest_qml):
        print(f"    [✓] Plasma Panel.qml override already up to date: {dest_qml}")
        return

    if os.path.lexists(dest_qml):
        backup = dest_qml + ".bak"
        if not os.path.exists(backup):
            shutil.copy2(dest_qml, backup)
        remove_existing_path(dest_qml)

    shutil.copy2(src_qml, dest_qml)
    os.chmod(dest_qml, 0o644)
    print(f"    [✓] Installed Plasma Panel.qml override: {dest_qml}")


def link_globally(app_name, bin_path, dry_run=False):
    """Create a symlink in /usr/local/bin so the tool works under sudo secure_path."""
    global_path = os.path.join("/usr/local/bin", app_name)
    if dry_run:
        print(f"    [dry-run] Would symlink {bin_path} -> {global_path}")
        return

    if os.geteuid() == 0:
        remove_existing_path(global_path)
        os.symlink(bin_path, global_path)
        print(f"    [✓] Linked globally: {global_path}")
    else:
        res = subprocess.run(["sudo", "ln", "-sf", bin_path, global_path], check=False)
        if res.returncode == 0:
            print(f"    [✓] Linked globally: {global_path}")
        else:
            print(f"    [!] Failed to create global symlink: {global_path}")


def refresh_desktop_cache(apps_dir, dry_run=False):
    """Refresh desktop launcher and KDE service caches when tools are available."""
    if dry_run:
        return
    if shutil.which("update-desktop-database"):
        subprocess.run(["update-desktop-database", apps_dir], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if shutil.which("kbuildsycoca6"):
        subprocess.run(["kbuildsycoca6"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def install_all(args):
    selected = args.only or list(APPS.keys())
    print(f"[*] Installing utilities from: {SCRIPT_DIR}")
    print(f"[*] Target bin directory    : {args.bin_dir}")
    print(f"[*] Target desktop entries  : {args.apps_dir}\n")

    if not args.skip_deps:
        ensure_dependencies(selected, dry_run=args.dry_run)

    for app_name in selected:
        meta = APPS[app_name]
        print(f"\n==> Installing {app_name}: {meta['description']}")

        src_bin = os.path.join(SCRIPT_DIR, meta["binary_rel"])
        if not os.path.isfile(src_bin):
            print(f"    [!] Missing source file: {src_bin}", file=sys.stderr)
            return 1

        dest_bin = install_binary(app_name, src_bin, args.bin_dir, dry_run=args.dry_run)

        if meta.get("desktop_rel"):
            src_desktop = os.path.join(SCRIPT_DIR, meta["desktop_rel"])
            if os.path.isfile(src_desktop):
                install_desktop_entry(src_desktop, args.apps_dir, dest_bin, dry_run=args.dry_run)

        if meta.get("panel_qml_rel") and not args.skip_qml:
            src_qml = os.path.join(SCRIPT_DIR, meta["panel_qml_rel"])
            if os.path.isfile(src_qml):
                install_panel_qml(src_qml, dry_run=args.dry_run)

        if args.global_link:
            link_globally(app_name, dest_bin, dry_run=args.dry_run)

    refresh_desktop_cache(args.apps_dir, dry_run=args.dry_run)

    path_entries = [os.path.normpath(p) for p in os.environ.get("PATH", "").split(":") if p]
    if os.path.normpath(args.bin_dir) not in path_entries:
        print(
            f"\n[!] Note: '{args.bin_dir}' is not currently in your PATH.\n"
            f"    Add this to ~/.bashrc or ~/.zshrc:\n"
            f"      export PATH=\"{args.bin_dir}:$PATH\""
        )

    print("\n[✓] Installation complete!")
    print("    Run from terminal or app launcher:")
    for app_name in selected:
        print(f"      - {app_name}")
    return 0


def uninstall_all(args):
    selected = args.only or list(APPS.keys())
    print(f"[*] Uninstalling: {', '.join(selected)}")
    for app_name in selected:
        meta = APPS[app_name]
        bin_path = os.path.join(args.bin_dir, app_name)
        if os.path.lexists(bin_path):
            if args.dry_run:
                print(f"    [dry-run] Would remove: {bin_path}")
            else:
                remove_existing_path(bin_path)
                print(f"    [✓] Removed: {bin_path}")

        if meta.get("desktop_rel"):
            desktop_path = os.path.join(args.apps_dir, os.path.basename(meta["desktop_rel"]))
            if os.path.lexists(desktop_path):
                if args.dry_run:
                    print(f"    [dry-run] Would remove: {desktop_path}")
                else:
                    remove_existing_path(desktop_path)
                    print(f"    [✓] Removed: {desktop_path}")

        global_path = os.path.join("/usr/local/bin", app_name)
        if args.global_link and os.path.lexists(global_path):
            if args.dry_run:
                print(f"    [dry-run] Would remove global symlink: {global_path}")
            else:
                if os.geteuid() == 0:
                    remove_existing_path(global_path)
                else:
                    subprocess.run(["sudo", "rm", "-f", global_path], check=False)
                print(f"    [✓] Removed global symlink: {global_path}")

    refresh_desktop_cache(args.apps_dir, dry_run=args.dry_run)
    print("[✓] Uninstall finished.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Install lockscreen-config, customize-dock, and ram-cleaner."
    )
    parser.add_argument(
        "--only",
        nargs="+",
        choices=list(APPS.keys()),
        help="Install or uninstall only specific utilities",
    )
    parser.add_argument(
        "--bin-dir",
        default=DEFAULT_BIN_DIR,
        help=f"Directory to install executables (default: {DEFAULT_BIN_DIR})",
    )
    parser.add_argument(
        "--apps-dir",
        default=DEFAULT_APPS_DIR,
        help=f"Directory to install .desktop launchers (default: {DEFAULT_APPS_DIR})",
    )
    parser.add_argument(
        "--global",
        dest="global_link",
        action="store_true",
        help="Also create symlinks in /usr/local/bin (requires sudo)",
    )
    parser.add_argument(
        "--skip-deps",
        action="store_true",
        help="Skip Python dependency checks/installation",
    )
    parser.add_argument(
        "--skip-qml",
        action="store_true",
        help="Skip installing the KDE Plasma Panel.qml override for customize-dock",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview actions without modifying any files",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Remove installed executables and desktop launchers",
    )
    args = parser.parse_args()

    if args.uninstall:
        return uninstall_all(args)
    return install_all(args)


if __name__ == "__main__":
    sys.exit(main())
