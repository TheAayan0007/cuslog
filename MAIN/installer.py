#!/usr/bin/env python3
"""
Unified installer for desktop utilities:
  - lockscreen-config (KDE Plasma 6 lock screen, logout & SDDM customizer)
  - customize-dock    (KDE Plasma 6 bottom dock & top bar customizer)
  - ram-cleaner       (Linux memory & idle-process cleaner CLI)
  - uxplay-tray       (UxPlay AirPlay installer, Avahi DNS-SD fix & top-bar toggle)
  - vnc-tray          (VNC 2nd Display for iPhone, krfb/viewer setup & top-bar toggle)
"""

import argparse
import json
import os
import re
import shutil
import signal
import stat
import subprocess
import sys
import time

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_BIN_DIR = os.path.expanduser("~/.local/bin")
DEFAULT_APPS_DIR = os.path.expanduser("~/.local/share/applications")
DEFAULT_AUTOSTART_DIR = os.path.expanduser("~/.config/autostart")
DEFAULT_ICONS_DIR = os.path.expanduser("~/.local/share/icons/hicolor/scalable/apps")
USER_SHELL_DIR = os.path.expanduser("~/.local/share/plasma/shells/org.kde.plasma.desktop")
SYSTEM_SHELL_DIR = "/usr/share/plasma/shells/org.kde.plasma.desktop"

TRIPLE_CLICK_MARKERS = ("import", "helpers", "observer")
MARKER_PREFIX = "customize-dock-triple-click-"

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
        "compact_applet_qml_rel": os.path.join("customize-dock", "CompactApplet.qml"),
        "python_deps": [("PyQt6", "python3-pyqt6", "PyQt6")],
    },
    "ram-cleaner": {
        "description": "RAM Cleaner & Memory Optimizer CLI",
        "binary_rel": os.path.join("ram-cleaner", "ram-cleaner"),
        "desktop_rel": None,
        "python_deps": [("psutil", "python3-psutil", "psutil")],
    },
    "uxplay-tray": {
        "description": "UxPlay AirPlay Mirroring Top-Bar Toggle & GUI Name Editor (Qt6)",
        "binary_rel": os.path.join("uxplay-tray", "uxplay-tray"),
        "desktop_rel": os.path.join("uxplay-tray", "uxplay-tray.desktop"),
        "icon_rel": os.path.join("uxplay-tray", "uxplay-tray.svg"),
        "autostart": True,
        "python_deps": [("PyQt6", "python3-pyqt6", "PyQt6")],
        "system_deps": [
            "uxplay",
            "avahi-daemon",
            "avahi-utils",
            "gstreamer1.0-plugins-base",
            "gstreamer1.0-plugins-good",
            "gstreamer1.0-plugins-bad",
            "gstreamer1.0-libav",
        ],
        "enable_avahi": True,
        "pin_tray_id": "UxPlay AirPlay",
        "start_tray": True,
    },
    "vnc-tray": {
        "description": "VNC 2nd Display & iPhone Control Server Top-Bar Toggle + GUI Configurator (Qt6)",
        "binary_rel": os.path.join("vnc-tray", "vnc-tray"),
        "desktop_rel": os.path.join("vnc-tray", "vnc-tray.desktop"),
        "icon_rel": os.path.join("vnc-tray", "vnc-tray.svg"),
        "autostart": True,
        "python_deps": [("PyQt6", "python3-pyqt6", "PyQt6")],
        "system_deps": [
            "krfb",
            "tigervnc-viewer",
            "avahi-daemon",
            "avahi-utils",
            "libkf6config-bin",
            "libkscreen-bin",
        ],
        "enable_avahi": True,
        "sync_config_flag": "--sync-config",
        "pin_tray_id": "VNC 2nd Display",
        "start_tray": True,
    },
}


def run_privileged(cmd):
    """Run a command directly as root or prefixed with sudo."""
    full_cmd = cmd if os.geteuid() == 0 else ["sudo", *cmd]
    return subprocess.run(full_cmd, check=False)


def is_module_available(module_name):
    """Return True if a Python module can be imported in the current interpreter."""
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


def is_deb_package_installed(pkg_name):
    """Return True if an apt/dpkg package is installed on Debian-based systems."""
    res = subprocess.run(
        ["dpkg-query", "-W", "-f=${Status}", pkg_name],
        capture_output=True,
        text=True,
        check=False,
    )
    return res.returncode == 0 and "install ok installed" in res.stdout


def ensure_system_dependencies(selected_apps, dry_run=False):
    """Install required system apt packages (such as uxplay & avahi-daemon)."""
    required = []
    for app_name in selected_apps:
        for pkg in APPS[app_name].get("system_deps", []):
            if pkg not in required:
                required.append(pkg)

    if not required:
        return True

    if not shutil.which("dpkg-query") or not shutil.which("apt-get"):
        print(
            f"[!] Non-apt system detected; ensure these packages are installed: {', '.join(required)}"
        )
        return True

    missing = [pkg for pkg in required if not is_deb_package_installed(pkg)]
    if not missing:
        print("[✓] All required system packages are already installed.")
        return True

    print(f"[*] Missing system packages: {', '.join(missing)}")
    if dry_run:
        print(f"    [dry-run] Would install via apt: {' '.join(missing)}")
        return True

    print(f"[*] Installing system packages via apt: {' '.join(missing)}")
    run_privileged(["apt-get", "update"])
    res = run_privileged(["apt-get", "install", "-y", *missing])
    if res.returncode == 0 and all(is_deb_package_installed(pkg) for pkg in missing):
        print("[✓] System packages installed via apt.")
        return True

    print(
        f"[!] Could not install all system packages automatically.\n"
        f"    Install manually with: sudo apt install {' '.join(missing)}"
    )
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
        print(f"[*] Installing dependencies via apt: {' '.join(apt_pkgs)}")
        run_privileged(["apt-get", "update"])
        res = run_privileged(["apt-get", "install", "-y", *apt_pkgs])
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


def ensure_user_shell_dir(dry_run=False):
    """Ensure the user Plasma desktop shell override directory exists."""
    if os.path.exists(USER_SHELL_DIR):
        return
    if not os.path.exists(SYSTEM_SHELL_DIR):
        return
    if dry_run:
        print(f"    [dry-run] Would copy Plasma shell base: {SYSTEM_SHELL_DIR} -> {USER_SHELL_DIR}")
        return
    shutil.copytree(SYSTEM_SHELL_DIR, USER_SHELL_DIR)


def backup_existing_file(path):
    """Create a one-time .bak copy before overwriting an existing file."""
    if not os.path.lexists(path):
        return
    backup = path + ".bak"
    if not os.path.exists(backup):
        shutil.copy2(path, backup)
    remove_existing_path(path)


def install_shell_file(src_qml, rel_dest, label, dry_run=False):
    """Install a Plasma shell QML override file and return True if modified."""
    dest_qml = os.path.join(USER_SHELL_DIR, rel_dest)
    if dry_run:
        if files_identical(src_qml, dest_qml):
            print(f"    [✓] Plasma {label} override already up to date: {dest_qml}")
            return False
        print(f"    [dry-run] Would install Plasma {label} override: {dest_qml}")
        return True

    ensure_user_shell_dir(dry_run=False)
    os.makedirs(os.path.dirname(dest_qml), exist_ok=True)
    if files_identical(src_qml, dest_qml):
        print(f"    [✓] Plasma {label} override already up to date: {dest_qml}")
        return False

    backup_existing_file(dest_qml)
    shutil.copy2(src_qml, dest_qml)
    os.chmod(dest_qml, 0o644)
    print(f"    [✓] Installed Plasma {label} override: {dest_qml}")
    return True


def _marker_regex(name):
    start = re.escape(f"// >>> {MARKER_PREFIX}{name}")
    end = re.escape(f"// <<< {MARKER_PREFIX}{name}")
    return re.compile(rf"\n?{start}\n.*?\n{end}", re.DOTALL)


def extract_marked_blocks(qml_text):
    """Extract the marked triple-click QML blocks from the bundled CompactApplet.qml."""
    blocks = {}
    for name in TRIPLE_CLICK_MARKERS:
        start = f"// >>> {MARKER_PREFIX}{name}"
        end = f"// <<< {MARKER_PREFIX}{name}"
        match = re.search(rf"({re.escape(start)}\n.*?\n{re.escape(end)})", qml_text, re.DOTALL)
        if not match:
            raise ValueError(f"Missing marker block '{name}' in bundled CompactApplet.qml")
        blocks[name] = match.group(1)
    return blocks


def strip_marked_blocks(qml_text):
    """Remove any previously injected triple-click marker blocks from CompactApplet.qml."""
    cleaned = qml_text
    for name in TRIPLE_CLICK_MARKERS:
        cleaned = _marker_regex(name).sub("", cleaned)
    return cleaned


def apply_compact_applet_patch(base_text, blocks):
    """Inject triple-click blocks into a Plasma 6 CompactApplet.qml; return None if anchors fail."""
    cleaned = strip_marked_blocks(base_text)
    anchors = [
        ("import", "import org.kde.kirigami as Kirigami"),
        ("helpers", "    property PlasmoidItem plasmoidItem"),
    ]
    patched = cleaned
    for name, anchor in anchors:
        if patched.count(anchor) != 1:
            return None
        patched = patched.replace(anchor, f"{anchor}\n{blocks[name]}", 1)

    keys_anchor = (
        "        Keys.onPressed: event => {\n"
        "            switch (event.key) {\n"
        "            case Qt.Key_Space:\n"
        "            case Qt.Key_Enter:\n"
        "            case Qt.Key_Return:\n"
        "            case Qt.Key_Select:\n"
        "                Plasmoid.activated();\n"
        "                break;\n"
        "            }\n"
        "        }"
    )
    focus_anchor = (
        "    FocusScope {\n"
        "        id: compactRepresentationParent\n"
        "        anchors.fill: parent"
    )
    if patched.count(keys_anchor) == 1:
        patched = patched.replace(keys_anchor, f"{keys_anchor}\n{blocks['observer']}", 1)
    elif patched.count(focus_anchor) == 1:
        patched = patched.replace(focus_anchor, f"{focus_anchor}\n{blocks['observer']}", 1)
    else:
        return None
    return patched


def install_compact_applet_qml(src_qml, dry_run=False):
    """Patch target PC's CompactApplet.qml with triple-click toggle (or copy fallback)."""
    rel_dest = os.path.join("contents", "applet", "CompactApplet.qml")
    dest_qml = os.path.join(USER_SHELL_DIR, rel_dest)
    sys_qml = os.path.join(SYSTEM_SHELL_DIR, rel_dest)

    with open(src_qml, "r", encoding="utf-8") as f:
        blocks = extract_marked_blocks(f.read())

    # On a fresh system during --dry-run, inspect system CompactApplet.qml if user copy doesn't exist yet
    read_path = dest_qml if os.path.isfile(dest_qml) else (sys_qml if dry_run and os.path.isfile(sys_qml) else None)
    if read_path is None:
        return install_shell_file(src_qml, rel_dest, "CompactApplet.qml", dry_run=dry_run)

    with open(read_path, "r", encoding="utf-8") as f:
        current_text = f.read()

    patched_text = apply_compact_applet_patch(current_text, blocks)
    if patched_text is None:
        return install_shell_file(src_qml, rel_dest, "CompactApplet.qml", dry_run=dry_run)

    if os.path.isfile(dest_qml) and current_text == patched_text:
        print(f"    [✓] Plasma CompactApplet.qml triple-click toggle already up to date: {dest_qml}")
        return False

    if dry_run:
        print(f"    [dry-run] Would patch Plasma CompactApplet.qml triple-click toggle: {dest_qml}")
        return True

    ensure_user_shell_dir(dry_run=False)
    os.makedirs(os.path.dirname(dest_qml), exist_ok=True)
    backup_existing_file(dest_qml)
    with open(dest_qml, "w", encoding="utf-8") as f:
        f.write(patched_text)
    os.chmod(dest_qml, 0o644)
    print(f"    [✓] Installed Plasma CompactApplet.qml triple-click toggle: {dest_qml}")
    return True


def uninstall_compact_applet_qml(dry_run=False):
    """Remove injected triple-click blocks from CompactApplet.qml if present."""
    dest_qml = os.path.join(USER_SHELL_DIR, "contents", "applet", "CompactApplet.qml")
    if not os.path.isfile(dest_qml):
        return False
    with open(dest_qml, "r", encoding="utf-8") as f:
        current_text = f.read()
    stripped_text = strip_marked_blocks(current_text)
    if stripped_text == current_text:
        return False
    if dry_run:
        print(f"    [dry-run] Would remove triple-click toggle patch from: {dest_qml}")
        return True
    with open(dest_qml, "w", encoding="utf-8") as f:
        f.write(stripped_text)
    os.chmod(dest_qml, 0o644)
    print(f"    [✓] Removed triple-click toggle patch from: {dest_qml}")
    return True


def restart_plasmashell_if_running(dry_run=False):
    """Reload plasma-plasmashell so shell QML overrides take effect immediately."""
    if dry_run:
        print("[dry-run] Would restart plasma-plasmashell.service if running.")
        return
    if shutil.which("systemctl"):
        check = subprocess.run(
            ["systemctl", "--user", "is-active", "--quiet", "plasma-plasmashell"],
            check=False,
        )
        if check.returncode == 0:
            subprocess.run(["systemctl", "--user", "reset-failed", "plasma-plasmashell"], check=False)
            res = subprocess.run(["systemctl", "--user", "restart", "plasma-plasmashell"], check=False)
            if res.returncode == 0:
                print("[✓] Reloaded KDE Plasma shell (plasma-plasmashell.service).")
                return
    print("[!] Restart plasmashell or log out and back in for Plasma QML overrides to take effect.")


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
        res = run_privileged(["ln", "-sf", bin_path, global_path])
        if res.returncode == 0:
            print(f"    [✓] Linked globally: {global_path}")
        else:
            print(f"    [!] Failed to create global symlink: {global_path}")


def install_icon(src_icon, icons_dir, dry_run=False):
    """Install a scalable SVG application icon into the user's hicolor theme."""
    dest_icon = os.path.join(icons_dir, os.path.basename(src_icon))
    if dry_run:
        print(f"    [dry-run] Would install icon: {src_icon} -> {dest_icon}")
        return dest_icon

    os.makedirs(icons_dir, exist_ok=True)
    remove_existing_path(dest_icon)
    shutil.copy2(src_icon, dest_icon)
    os.chmod(dest_icon, 0o644)
    if shutil.which("gtk-update-icon-cache"):
        theme_root = os.path.dirname(os.path.dirname(icons_dir))
        subprocess.run(
            ["gtk-update-icon-cache", "-f", "-t", theme_root],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    print(f"    [✓] Installed icon: {dest_icon}")
    return dest_icon


def ensure_avahi_dns_sd(dry_run=False):
    """Enable and start avahi-daemon to prevent UxPlay No DNS-SD Server errors."""
    if not shutil.which("systemctl"):
        print("    [!] systemctl not found; ensure avahi-daemon is running manually.")
        return False

    enabled = (
        subprocess.run(
            ["systemctl", "is-enabled", "--quiet", "avahi-daemon"], check=False
        ).returncode
        == 0
    )
    active = (
        subprocess.run(
            ["systemctl", "is-active", "--quiet", "avahi-daemon"], check=False
        ).returncode
        == 0
    )
    dbus_alias = os.path.exists("/etc/systemd/system/dbus-org.freedesktop.Avahi.service")

    if enabled and active and dbus_alias:
        print("    [✓] Avahi DNS-SD service is already enabled and running.")
        return True

    if dry_run:
        print("    [dry-run] Would enable and start avahi-daemon (systemctl enable --now avahi-daemon)")
        return True

    print("    [*] Enabling and starting avahi-daemon (fixes UxPlay DNS-SD error)...")
    res = run_privileged(["systemctl", "enable", "--now", "avahi-daemon"])
    if res.returncode == 0:
        print("    [✓] Avahi DNS-SD service enabled and started.")
        return True

    print(
        "    [!] Failed to enable/start avahi-daemon automatically.\n"
        "        Run manually: sudo systemctl enable --now avahi-daemon"
    )
    return False


def pin_plasma_tray_item(item_id, dry_run=False):
    """Ensure a StatusNotifierItem ID is pinned visible in the KDE Plasma top system tray."""
    qdbus_bin = shutil.which("qdbus6") or shutil.which("qdbus")
    if not qdbus_bin:
        return
    if dry_run:
        print(f"    [dry-run] Would pin '{item_id}' in KDE Plasma top bar System Tray")
        return

    js_item = json.dumps(item_id)
    script = (
        "var changed = false;\n"
        "for (var p of panels()) {\n"
        "  for (var w of p.widgets()) {\n"
        "    if (w.type === 'org.kde.plasma.systemtray') {\n"
        "      w.currentConfigGroup = ['General'];\n"
        "      var shown = String(w.readConfig('shownItems') || '').split(',').filter(Boolean);\n"
        "      var hidden = String(w.readConfig('hiddenItems') || '').split(',').filter(Boolean);\n"
        f"      var target = {js_item};\n"
        "      if (shown.indexOf(target) === -1) {\n"
        "        shown.push(target);\n"
        "        w.writeConfig('shownItems', shown.join(','));\n"
        "        changed = true;\n"
        "      }\n"
        "      var idx = hidden.indexOf(target);\n"
        "      if (idx !== -1) {\n"
        "        hidden.splice(idx, 1);\n"
        "        w.writeConfig('hiddenItems', hidden.join(','));\n"
        "        changed = true;\n"
        "      }\n"
        "    }\n"
        "  }\n"
        "}\n"
        "print(changed ? 'PINNED' : 'ALREADY_PINNED');\n"
    )
    res = subprocess.run(
        [
            qdbus_bin,
            "org.kde.plasmashell",
            "/PlasmaShell",
            "org.kde.PlasmaShell.evaluateScript",
            script,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode == 0:
        print(f"    [✓] Pinned '{item_id}' in KDE Plasma top bar System Tray.")


def _find_running_app_pids(app_name):
    """Return PIDs running app_name via /proc/<pid>/cmdline (handles python3 shebangs safely)."""
    pids = []
    self_pid = os.getpid()
    try:
        entries = os.listdir("/proc")
    except OSError:
        return pids

    for entry in entries:
        if not entry.isdigit():
            continue
        pid = int(entry)
        if pid == self_pid:
            continue
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                raw = f.read()
        except OSError:
            continue
        args = [part.decode("utf-8", errors="replace") for part in raw.split(b"\x00") if part]
        if not args:
            continue
        first_base = os.path.basename(args[0])
        is_python = first_base.startswith("python")
        if first_base == app_name or (is_python and len(args) > 1 and os.path.basename(args[1]) == app_name):
            pids.append(pid)
    return pids


def stop_tray_service(app_name, dry_run=False):
    """Stop any running systemd-run, XDG autostart, or standalone instance of the tray utility."""
    if dry_run:
        print(f"    [dry-run] Would stop running {app_name} tray instance")
        return

    if shutil.which("systemctl"):
        escaped = app_name.replace("-", r"\x2d")
        for unit in (f"{app_name}.service", f"app-{escaped}@autostart.service"):
            subprocess.run(
                ["systemctl", "--user", "stop", unit],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

    remaining = _find_running_app_pids(app_name)
    for pid in remaining:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass

    if remaining:
        deadline = time.monotonic() + 2.0
        while time.monotonic() < deadline and _find_running_app_pids(app_name):
            time.sleep(0.1)
        for pid in _find_running_app_pids(app_name):
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass


def sync_app_config(app_name, bin_path, flag, dry_run=False):
    """Pre-sync application and backend config (e.g. krfbrc password keys) during install."""
    if dry_run:
        print(f"    [dry-run] Would sync {app_name} configuration ({bin_path} {flag})")
        return

    res = subprocess.run([bin_path, flag], capture_output=True, text=True, check=False)
    if res.returncode == 0:
        print(f"    [✓] Synced {app_name} config & krfb password keys (unattendedPassword / desktopPassword).")
    else:
        detail = res.stderr.strip() or res.stdout.strip() or f"exit code {res.returncode}"
        print(f"    [!] Config sync warning for {app_name}: {detail}")


def start_tray_service(app_name, bin_path, dry_run=False):
    """Launch or restart the tray icon inside the active graphical user session."""
    if dry_run:
        print(f"    [dry-run] Would launch {bin_path} in the active desktop session")
        return

    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        print(f"    [*] No active GUI display detected; {app_name} will auto-start on next desktop login.")
        return

    stop_tray_service(app_name, dry_run=False)
    if shutil.which("systemd-run"):
        res = subprocess.run(
            [
                "systemd-run",
                "--user",
                "--unit",
                app_name,
                "--collect",
                f"--description={app_name} top-bar toggle",
                bin_path,
            ],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if res.returncode == 0:
            print(f"    [✓] Started {app_name} in top bar ({app_name}.service).")
            return

    subprocess.Popen(
        [bin_path],
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    print(f"    [✓] Started {app_name} in top bar.")


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
        ensure_system_dependencies(selected, dry_run=args.dry_run)
        ensure_dependencies(selected, dry_run=args.dry_run)

    qml_changed = False
    for app_name in selected:
        meta = APPS[app_name]
        print(f"\n==> Installing {app_name}: {meta['description']}")

        src_bin = os.path.join(SCRIPT_DIR, meta["binary_rel"])
        if not os.path.isfile(src_bin):
            print(f"    [!] Missing source file: {src_bin}", file=sys.stderr)
            return 1

        dest_bin = install_binary(app_name, src_bin, args.bin_dir, dry_run=args.dry_run)

        if meta.get("icon_rel"):
            src_icon = os.path.join(SCRIPT_DIR, meta["icon_rel"])
            if os.path.isfile(src_icon):
                install_icon(src_icon, DEFAULT_ICONS_DIR, dry_run=args.dry_run)

        if meta.get("desktop_rel"):
            src_desktop = os.path.join(SCRIPT_DIR, meta["desktop_rel"])
            if os.path.isfile(src_desktop):
                install_desktop_entry(src_desktop, args.apps_dir, dest_bin, dry_run=args.dry_run)
                if meta.get("autostart"):
                    install_desktop_entry(
                        src_desktop, DEFAULT_AUTOSTART_DIR, dest_bin, dry_run=args.dry_run
                    )

        if meta.get("panel_qml_rel") and not args.skip_qml:
            src_qml = os.path.join(SCRIPT_DIR, meta["panel_qml_rel"])
            if os.path.isfile(src_qml):
                qml_changed |= install_shell_file(
                    src_qml, os.path.join("contents", "views", "Panel.qml"), "Panel.qml", dry_run=args.dry_run
                )

        if meta.get("compact_applet_qml_rel") and not args.skip_qml:
            src_compact_qml = os.path.join(SCRIPT_DIR, meta["compact_applet_qml_rel"])
            if os.path.isfile(src_compact_qml):
                qml_changed |= install_compact_applet_qml(src_compact_qml, dry_run=args.dry_run)

        if args.global_link:
            link_globally(app_name, dest_bin, dry_run=args.dry_run)

        if meta.get("enable_avahi"):
            ensure_avahi_dns_sd(dry_run=args.dry_run)

        if meta.get("sync_config_flag"):
            if meta.get("start_tray"):
                # Stop active tray/krfb before syncing so krfb's shutdown saveConfig() cannot overwrite krfbrc.
                stop_tray_service(app_name, dry_run=args.dry_run)
            sync_app_config(app_name, dest_bin, meta["sync_config_flag"], dry_run=args.dry_run)

        if meta.get("pin_tray_id"):
            pin_plasma_tray_item(meta["pin_tray_id"], dry_run=args.dry_run)

        if meta.get("start_tray"):
            start_tray_service(app_name, dest_bin, dry_run=args.dry_run)

    refresh_desktop_cache(args.apps_dir, dry_run=args.dry_run)
    if qml_changed:
        restart_plasmashell_if_running(dry_run=args.dry_run)

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
    qml_changed = False
    for app_name in selected:
        meta = APPS[app_name]
        if meta.get("start_tray"):
            stop_tray_service(app_name, dry_run=args.dry_run)

        bin_path = os.path.join(args.bin_dir, app_name)
        if os.path.lexists(bin_path):
            if args.dry_run:
                print(f"    [dry-run] Would remove: {bin_path}")
            else:
                remove_existing_path(bin_path)
                print(f"    [✓] Removed: {bin_path}")

        if meta.get("desktop_rel"):
            desktop_name = os.path.basename(meta["desktop_rel"])
            for target_dir in (
                [args.apps_dir, DEFAULT_AUTOSTART_DIR]
                if meta.get("autostart")
                else [args.apps_dir]
            ):
                desktop_path = os.path.join(target_dir, desktop_name)
                if os.path.lexists(desktop_path):
                    if args.dry_run:
                        print(f"    [dry-run] Would remove: {desktop_path}")
                    else:
                        remove_existing_path(desktop_path)
                        print(f"    [✓] Removed: {desktop_path}")

        if meta.get("icon_rel"):
            icon_path = os.path.join(DEFAULT_ICONS_DIR, os.path.basename(meta["icon_rel"]))
            if os.path.lexists(icon_path):
                if args.dry_run:
                    print(f"    [dry-run] Would remove: {icon_path}")
                else:
                    remove_existing_path(icon_path)
                    print(f"    [✓] Removed: {icon_path}")

        if meta.get("compact_applet_qml_rel") and not args.skip_qml:
            qml_changed |= uninstall_compact_applet_qml(dry_run=args.dry_run)

        global_path = os.path.join("/usr/local/bin", app_name)
        if args.global_link and os.path.lexists(global_path):
            if args.dry_run:
                print(f"    [dry-run] Would remove global symlink: {global_path}")
            else:
                run_privileged(["rm", "-f", global_path])
                print(f"    [✓] Removed global symlink: {global_path}")

    refresh_desktop_cache(args.apps_dir, dry_run=args.dry_run)
    if qml_changed:
        restart_plasmashell_if_running(dry_run=args.dry_run)
    print("[✓] Uninstall finished.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Install lockscreen-config, customize-dock, ram-cleaner, uxplay-tray, and vnc-tray."
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
        help="Skip installing KDE Plasma shell QML overrides (Panel.qml and CompactApplet.qml) for customize-dock",
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
