#!/usr/bin/env python3
import sys
import os
import re
import json
import shutil
import subprocess
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QSlider, QSpinBox, QComboBox, QFontComboBox, QCheckBox,
    QLineEdit, QPushButton, QGroupBox, QTabWidget, QMessageBox,
    QFrame, QDialog, QGridLayout, QColorDialog, QScrollArea, QSizePolicy,
    QFileDialog, QInputDialog
)
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QFont, QKeySequence, QDesktopServices, QColor

CONFIG_DIR = os.path.expanduser("~/.config/kde-lockscreen-config")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
LOCKSCREEN_OVERRIDE_DIR = os.path.expanduser("~/.local/share/plasma/shells/org.kde.plasma.desktop")
LOCKSCREEN_QML = os.path.join(LOCKSCREEN_OVERRIDE_DIR, "contents/lockscreen/LockScreenUi.qml")

# Real KDE Plasma Look-and-Feel for Logout (/usr/share/plasma/look-and-feel/org.kde.breeze.desktop)
SYSTEM_LOGOUT_DIR = "/usr/share/plasma/look-and-feel/org.kde.breeze.desktop"
SYSTEM_LOGOUT_QML = os.path.join(SYSTEM_LOGOUT_DIR, "contents/logout/Logout.qml")
USER_LOGOUT_DIR = os.path.expanduser("~/.local/share/plasma/look-and-feel/org.kde.breeze.desktop")
LOGOUT_QML = os.path.join(USER_LOGOUT_DIR, "contents/logout/Logout.qml")

# Real System SDDM Breeze Theme (/usr/share/sddm/themes/breeze)
SYSTEM_SDDM_DIR = "/usr/share/sddm/themes/breeze"
SYSTEM_SDDM_QML = os.path.join(SYSTEM_SDDM_DIR, "Main.qml")
SYSTEM_SDDM_BG_QML = os.path.join(SYSTEM_SDDM_DIR, "Background.qml")
SYSTEM_SDDM_STOCK_BACKUP = os.path.join(CONFIG_DIR, "breeze-stock/Main.qml")
SYSTEM_SDDM_BG_STOCK_BACKUP = os.path.join(CONFIG_DIR, "breeze-stock/Background.qml")
SYSTEM_SDDM_THEME_CONF = os.path.join(SYSTEM_SDDM_DIR, "theme.conf")
SYSTEM_SDDM_THEME_CONF_USER = os.path.join(SYSTEM_SDDM_DIR, "theme.conf.user")
SYSTEM_SDDM_THEME_CONF_STOCK = os.path.join(CONFIG_DIR, "breeze-stock/theme.conf")

# Local User Theme Directory for SDDM testing
SDDM_THEME_DIR = os.path.expanduser("~/.local/share/sddm-themes/breeze-top-clock")
SDDM_QML = os.path.join(SDDM_THEME_DIR, "Main.qml")

DEFAULT_CONFIG = {
    # Position & Alignment
    "clockAlignment": "Center",
    "clockTopMargin": 65,
    "clockHorizontalMargin": 60,

    # Time Numbers
    "timePointSize": 64,
    "timeFontFamily": "Noto Sans Mono ExtraCondensed Thin",
    "timeFontWeight": "Font.Light",
    "timeColor": "#ffffff",
    "timeFormatPreset": "12-Hour (h:mm ap)",
    "timeFormat": "h:mm ap",

    # Date
    "showDate": True,
    "datePointSize": 18,
    "dateFontFamily": "Latin Modern Mono Light",
    "dateFontWeight": "Font.Normal",
    "dateColor": "#cbd5e1",
    "dateFormatPreset": "Full (e.g. Tuesday, November 10)",
    "dateFormat": "dddd, MMMM d",

    # Custom Text / Banner
    "showCustomText": False,
    "customText": "",
    "customTextPointSize": 13,
    "customTextFontFamily": "",
    "customTextFontWeight": "Font.Normal",
    "customTextColor": "#94a3b8",
    "customTextAlignment": "Inherit",
    "customTextTopMargin": 12,

    # Key / Mouse Triggers
    "unlockKeyNames": ["Space"],
    "unlockKeyCodes": [32],
    "unlockMouseButtons": ["Left Click"],
    "unlockOnAnyKey": False,
    "unlockOnMouseMove": False,
    "idleTimeoutSeconds": 15,
    "keepClockVisibleWhenUnlocking": True,

    # Animations
    "enableWindowsGlideAnimation": True,

    # SDDM Breeze Login Screen Customization
    "customizeSddmScreen": True,
    "sddmBackground": "",
    "sddmBackgroundColor": "#0f172a",
    "sddmShowLogo": "hidden",

    # Logout Screen Customization
    "customizeLogoutScreen": True,
    "logoutShowClock": True,
    "logoutClockTopMargin": 45,
    "logoutCustomTitle": "",
    "logoutTitleColor": "#f8fafc",
    "logoutTitlePointSize": 18,
    "logoutWallpaper": "",
    "logoutBgOpacity": 35,
    "logoutBgColor": "#000000",
    "logoutShowCountdown": True,
}

COLOR_PRESETS = [
    ("#ffffff", "White"),
    ("#f8fafc", "Pure Snow"),
    ("#cbd5e1", "Slate Silver"),
    ("#94a3b8", "Muted Gray"),
    ("#38bdf8", "Sky Blue"),
    ("#34d399", "Emerald Green"),
    ("#fbbf24", "Warm Gold"),
    ("#f43f5e", "Rose Coral"),
    ("#c084fc", "Lavender Purple"),
    ("#f97316", "Sunburst Orange"),
]

TIME_WEIGHTS = {
    "Thin (100)": "Font.Thin",
    "ExtraLight (200)": "Font.ExtraLight",
    "Light (300)": "Font.Light",
    "Normal (400)": "Font.Normal",
    "Medium (500)": "Font.Medium",
    "DemiBold (600)": "Font.DemiBold",
    "Bold (700)": "Font.Bold",
    "Black (900)": "Font.Black",
}

WEIGHT_MAP = {
    "Thin (100)": QFont.Weight.Thin,
    "ExtraLight (200)": QFont.Weight.ExtraLight,
    "Light (300)": QFont.Weight.Light,
    "Normal (400)": QFont.Weight.Normal,
    "Medium (500)": QFont.Weight.Medium,
    "DemiBold (600)": QFont.Weight.DemiBold,
    "Bold (700)": QFont.Weight.Bold,
    "Black (900)": QFont.Weight.Black,
}

TIME_FORMATS = {
    "12-Hour (h:mm ap)": "h:mm ap",
    "12-Hour with Seconds (h:mm:ss ap)": "h:mm:ss ap",
    "24-Hour (HH:mm)": "HH:mm",
    "24-Hour with Seconds (HH:mm:ss)": "HH:mm:ss",
    "System Default": "",
    "Custom": "custom",
}

DATE_FORMATS = {
    "Full (e.g. Tuesday, November 10)": "dddd, MMMM d",
    "Short (e.g. Tue, 10 Nov 2026)": "ddd, d MMM yyyy",
    "ISO (e.g. 2026-11-10)": "yyyy-MM-dd",
    "Numeric (e.g. 10/11/2026)": "dd/MM/yyyy",
    "System Default": "",
    "Custom": "custom",
}

POPULAR_FONTS = [
    ("System Default", ""),
    ("Latin Modern Mono", "Latin Modern Mono"),
    ("Noto Sans Mono", "Noto Sans Mono ExtraCondensed Thin"),
    ("Fira Code", "Fira Code"),
    ("Hack", "Hack"),
    ("Cantarell", "Cantarell"),
    ("Liberation Sans", "Liberation Sans"),
    ("Akira Expanded", "Akira Expanded"),
]


def write_system_file(dest_path, content, stock_backup_path=None, parent_widget=None):
    """
    Safely writes content to dest_path.
    If dest_path is in a system directory (like /usr/share/sddm/themes/breeze):
    - Backs up original to stock_backup_path or dest_path + '.stock' if not already done.
    - Uses direct write if writable, or pkexec (Polkit GUI), or GUI password prompt with sudo.
    """
    stock_backup = stock_backup_path or (dest_path + ".stock")
    temp_dir = os.path.expanduser("~/.cache/kde-lockscreen-config")
    os.makedirs(temp_dir, exist_ok=True)
    temp_file = os.path.join(temp_dir, os.path.basename(dest_path) + ".tmp")
    if isinstance(content, bytes):
        with open(temp_file, "wb") as f:
            f.write(content)
    else:
        with open(temp_file, "w", encoding="utf-8") as f:
            f.write(content)

    # 1. Try direct write if we already have permissions
    try:
        dest_dir = os.path.dirname(dest_path)
        if os.access(dest_path, os.W_OK) or (not os.path.exists(dest_path) and os.access(dest_dir, os.W_OK)):
            if not os.path.exists(stock_backup) and os.path.exists(dest_path):
                try:
                    shutil.copy2(dest_path, stock_backup)
                except Exception:
                    pass
            shutil.copy2(temp_file, dest_path)
            try:
                os.chmod(dest_path, 0o644)
            except Exception:
                pass
            return True
    except Exception:
        pass

    # 2. Try pkexec (graphical polkit agent handles password)
    sh_script = f'''
if [ ! -f "{stock_backup}" ] && [ -f "{dest_path}" ]; then
    cp -p "{dest_path}" "{stock_backup}"
fi
cp "{temp_file}" "{dest_path}" && chmod 644 "{dest_path}"
'''
    try:
        res = subprocess.run(["pkexec", "sh", "-c", sh_script], capture_output=True, text=True)
        if res.returncode == 0:
            return True
    except Exception as e:
        print(f"pkexec attempt note: {e}")

    # 3. Fallback: Prompt user with clean PyQt dialog and use sudo -S
    if parent_widget:
        user_name = os.environ.get("USER", "windows")
        pwd, ok = QInputDialog.getText(
            parent_widget,
            "Root Privileges Required",
            f"Modifying '{dest_path}' requires administrative permissions.\nPlease enter password for user '{user_name}':",
            QLineEdit.EchoMode.Password
        )
        if ok and pwd:
            p = subprocess.Popen(
                ["sudo", "-S", "sh", "-c", sh_script],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            out, err = p.communicate(input=pwd + "\n")
            if p.returncode == 0:
                return True
            else:
                raise PermissionError(f"Authentication failed: {err.strip()}")
        else:
            raise PermissionError("Administrator authentication was cancelled.")
    else:
        raise PermissionError(f"Could not write to {dest_path} (pkexec failed)")


def restore_system_stock_file(dest_path, stock_backup_path=None, user_fallback_backup=None, parent_widget=None):
    """
    Restores dest_path back to the pristine stock version from stock backup.
    """
    stock_backup = stock_backup_path or (dest_path + ".stock")
    src = None
    if os.path.exists(stock_backup):
        src = stock_backup
    elif user_fallback_backup and os.path.exists(user_fallback_backup):
        src = user_fallback_backup

    if not src:
        raise FileNotFoundError(f"No stock backup file found to restore {dest_path}")

    # 1. Direct write
    try:
        if os.access(dest_path, os.W_OK) or os.access(os.path.dirname(dest_path), os.W_OK):
            shutil.copy2(src, dest_path)
            try:
                os.chmod(dest_path, 0o644)
            except Exception:
                pass
            return True
    except Exception:
        pass

    # 2. pkexec
    sh_script = f'cp "{src}" "{dest_path}" && chmod 644 "{dest_path}"'
    try:
        res = subprocess.run(["pkexec", "sh", "-c", sh_script], capture_output=True, text=True)
        if res.returncode == 0:
            return True
    except Exception:
        pass

    # 3. sudo fallback
    if parent_widget:
        user_name = os.environ.get("USER", "windows")
        pwd, ok = QInputDialog.getText(
            parent_widget,
            "Root Privileges Required",
            f"Restoring '{dest_path}' to stock requires administrative permissions.\nPlease enter password for user '{user_name}':",
            QLineEdit.EchoMode.Password
        )
        if ok and pwd:
            p = subprocess.Popen(
                ["sudo", "-S", "sh", "-c", sh_script],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            out, err = p.communicate(input=pwd + "\n")
            if p.returncode == 0:
                return True
            else:
                raise PermissionError(f"Authentication failed: {err.strip()}")
        else:
            raise PermissionError("Administrator authentication was cancelled.")
    else:
        raise PermissionError(f"Could not restore {dest_path} (pkexec failed)")


def get_current_lockscreen_wallpaper():
    """Reads wallpaper image path from ~/.config/kscreenlockerrc if present."""
    k_rc = os.path.expanduser("~/.config/kscreenlockerrc")
    if os.path.exists(k_rc):
        try:
            with open(k_rc, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip().startswith("Image="):
                        val = line.split("=", 1)[1].strip()
                        if os.path.isfile(val):
                            return val
        except Exception:
            pass
    return ""


def copy_image_to_system_sddm(image_path, parent_widget=None):
    """
    Copies any local user image (jpg, png, webp, svg, bmp) directly to
    /usr/share/sddm/themes/breeze/custom_wallpaper.<ext> with 0644 permissions.
    Preserves 100% uncompressed raw file bytes so SDDM greeter can read it losslessly.
    Returns the installed system file path.
    """
    if not image_path or not os.path.isfile(image_path):
        return ""
    ext = os.path.splitext(image_path)[1].lower()
    if not ext:
        ext = ".png"
    target_system_path = os.path.join(SYSTEM_SDDM_DIR, f"custom_wallpaper{ext}")
    with open(image_path, "rb") as f:
        img_bytes = f.read()
    write_system_file(target_system_path, img_bytes, stock_backup_path=None, parent_widget=parent_widget)
    return target_system_path


def patch_system_sddm_background_qml(parent_widget=None):
    """
    Ensures /usr/share/sddm/themes/breeze/Background.qml has an uncompressed Image loader:
    - fillMode: Image.PreserveAspectCrop
    - smooth: true, mipmap: true
    - NO sourceSize (zero downsampling/compression artifacts)
    - Fallback background color #0f172a (never flashes white)
    """
    if not os.path.exists(SYSTEM_SDDM_BG_QML):
        return
    if not os.path.exists(SYSTEM_SDDM_BG_STOCK_BACKUP):
        os.makedirs(os.path.dirname(SYSTEM_SDDM_BG_STOCK_BACKUP), exist_ok=True)
        try:
            shutil.copy2(SYSTEM_SDDM_BG_QML, SYSTEM_SDDM_BG_STOCK_BACKUP)
        except Exception:
            pass

    bg_qml_content = """/*
    SPDX-FileCopyrightText: 2016 Boudhayan Gupta <bgupta@kde.org>
    SPDX-License-Identifier: LGPL-2.0-or-later
*/

import QtQuick

FocusScope {
    id: sceneBackground

    property var sceneBackgroundType
    property alias sceneBackgroundColor: sceneColorBackground.color
    property alias sceneBackgroundImage: sceneImageBackground.source

    Rectangle {
        id: sceneColorBackground
        anchors.fill: parent
        color: "#0f172a"
    }

    Image {
        id: sceneImageBackground
        anchors.fill: parent
        fillMode: Image.PreserveAspectCrop
        smooth: true
        mipmap: true
        asynchronous: false
        cache: true
    }

    states: [
        State {
            name: "imageBackground"
            when: sceneBackgroundType === "image"
            PropertyChanges {
                target: sceneColorBackground
                visible: true
            }
            PropertyChanges {
                target: sceneImageBackground
                visible: true
            }
        },
        State {
            name: "colorBackground"
            when: sceneBackgroundType !== "image"
            PropertyChanges {
                target: sceneColorBackground
                visible: true
            }
            PropertyChanges {
                target: sceneImageBackground
                visible: false
            }
        }
    ]
}
"""
    write_system_file(SYSTEM_SDDM_BG_QML, bg_qml_content, stock_backup_path=SYSTEM_SDDM_BG_QML + ".stock", parent_widget=parent_widget)


def build_lockscreen(src_path, dst_path, is_sddm=False):
    with open(src_path, "r") as f:
        content = f.read()

    if "import org.kde.plasma.clock as PlasmaClock" not in content:
        content = content.replace(
            "import org.kde.breeze.components",
            "import org.kde.breeze.components\nimport org.kde.plasma.clock as PlasmaClock"
        )

    custom_cfg = """
    QtObject {
        id: customConfig
        property string clockAlignment: "Center"
        property int clockTopMargin: 65
        property int clockHorizontalMargin: 60
        property int timePointSize: 64
        property int datePointSize: 18
        property int hintPointSize: 13
        property string timeFormat: "h:mm ap"
        property string dateFormat: "dddd, MMMM d"
        property bool showDate: true
        property string timeFontFamily: "Noto Sans Mono ExtraCondensed Thin"
        property string dateFontFamily: "Latin Modern Mono Light"
        property int timeFontWeight: Font.Light
        property int dateFontWeight: Font.Normal
        property string timeColor: "#ffffff"
        property string dateColor: "#cbd5e1"
        property bool showUnlockHint: false
        property string unlockHintText: ""
        property string hintFontFamily: ""
        property int hintFontWeight: Font.Normal
        property string hintColor: "#94a3b8"
        property string hintAlignment: "Inherit"
        property int hintTopMargin: 12

        // Custom interaction triggers
        property var unlockKeyCodes: [32]
        property var unlockKeyNames: ["Space"]
        property var unlockMouseButtons: ["Left Click"]
        property bool unlockOnAnyKey: false
        property bool unlockOnMouseMove: false
        property int idleTimeoutSeconds: 15
        property bool keepClockVisibleWhenUnlocking: true

        // Animations
        property bool enableWindowsGlideAnimation: true

        // Wallpaper & Fallback Tint
        property string customWallpaper: ""
        property string wallpaperColor: "#0f172a"
    }
"""
    root_item_header = "Item {\n    id: lockScreenUi" if not is_sddm else "Item {\n    id: root"
    content = content.replace(root_item_header, root_item_header + custom_cfg, 1)

    target_id = "lockScreenRoot" if not is_sddm else "loginScreenRoot"
    target_pwd = "mainBlock.mainPasswordBox" if not is_sddm else "userListComponent.mainPasswordBox"

    new_mouse_area = f"""    MouseArea {{
        id: {target_id}

        property bool uiVisible: false
        property bool seenPositionChange: false
        property bool blockUI: (mainStack.depth > 1 || {target_pwd}.text.length > 0 || inputPanel.keyboardActive)

        x: parent.x
        y: parent.y
        width: parent.width
        height: parent.height
        hoverEnabled: true
        acceptedButtons: Qt.LeftButton | Qt.RightButton | Qt.MiddleButton
        cursorShape: Qt.ArrowCursor
        drag.filterChildren: true

        onPositionChanged: {{
            if (customConfig.unlockOnMouseMove) {{
                uiVisible = true;
            }}
        }}

        onPressed: mouse => {{
            if (customConfig.unlockMouseButtons.indexOf("Left Click") !== -1 && mouse.button === Qt.LeftButton) {{
                uiVisible = true;
            }} else if (customConfig.unlockMouseButtons.indexOf("Right Click") !== -1 && mouse.button === Qt.RightButton) {{
                uiVisible = true;
            }} else if (customConfig.unlockMouseButtons.indexOf("Middle Click") !== -1 && mouse.button === Qt.MiddleButton) {{
                uiVisible = true;
            }}
        }}

        onDoubleClicked: mouse => {{
            if (customConfig.unlockMouseButtons.indexOf("Double Click") !== -1) {{
                uiVisible = true;
            }}
        }}

        onWheel: wheel => {{
            if (customConfig.unlockMouseButtons.indexOf("Mouse Wheel / Scroll") !== -1) {{
                uiVisible = true;
            }}
        }}

        onUiVisibleChanged: {{
            {"if (uiVisible) { Window.window.requestActivate(); }" if not is_sddm else "if (uiVisible) { userListComponent.mainPasswordBox.forceActiveFocus(); }"}
            if (blockUI) {{
                fadeoutTimer.running = false;
            }} else if (uiVisible) {{
                fadeoutTimer.restart();
            }}
            {"authenticator.startAuthenticating();" if not is_sddm else ""}
        }}
        onBlockUIChanged: {{
            if (blockUI) {{
                fadeoutTimer.running = false;
                uiVisible = true;
            }} else {{
                fadeoutTimer.restart();
            }}
        }}
        onExited: {{
            if (!blockUI) {{
                fadeoutTimer.restart();
            }}
        }}
        Keys.onEscapePressed: {{
            if (uiVisible) {{
                uiVisible = false;
                if (inputPanel.keyboardActive) {{
                    inputPanel.showHide();
                }}
                {"root.clearPassword();" if not is_sddm else "userListComponent.mainPasswordBox.text = \"\";"}
            }}
        }}
        Keys.onPressed: event => {{
            if (!uiVisible) {{
                if (customConfig.unlockOnAnyKey) {{
                    uiVisible = true;
                    event.accepted = false;
                }} else if (customConfig.unlockKeyCodes.indexOf(event.key) !== -1) {{
                    uiVisible = true;
                    if (event.key === Qt.Key_Space || event.key === Qt.Key_Return || event.key === Qt.Key_Enter) {{
                        event.accepted = true;
                    }} else {{
                        event.accepted = false;
                    }}
                }} else {{
                    event.accepted = true;
                }}
            }} else {{
                event.accepted = false;
            }}
        }}
        Timer {{
            id: fadeoutTimer
            interval: Math.max(1, customConfig.idleTimeoutSeconds) * 1000
            running: customConfig.idleTimeoutSeconds > 0
            onTriggered: {{
                if (!{target_id}.blockUI && customConfig.idleTimeoutSeconds > 0) {{
                    {target_pwd}.showPassword = false;
                    {target_id}.uiVisible = false;
                }}
            }}
        }}"""

    if not is_sddm:
        old_mouse_re = r"MouseArea\s*\{\s*id:\s*lockScreenRoot.*?(?=\n\s*Timer\s*\{\s*id:\s*notificationRemoveTimer)"
    else:
        old_mouse_re = r"MouseArea\s*\{\s*id:\s*loginScreenRoot.*?(?=\n\s*WallpaperFader)"

    content = re.sub(old_mouse_re, new_mouse_area, content, count=1, flags=re.DOTALL)

    clock_to_replace = r"DropShadow\s*\{\s*id:\s*clockShadow.*?Clock\s*\{\s*id:\s*clock.*?\}"
    new_clock_block = f"""        // Top Customizable Clock with Glide Animation
        ColumnLayout {{
            id: topClock
            anchors.horizontalCenter: customConfig.clockAlignment === "Center" ? parent.horizontalCenter : undefined
            anchors.left: customConfig.clockAlignment === "Left" ? parent.left : undefined
            anchors.leftMargin: customConfig.clockHorizontalMargin
            anchors.right: customConfig.clockAlignment === "Right" ? parent.right : undefined
            anchors.rightMargin: customConfig.clockHorizontalMargin
            y: (customConfig.enableWindowsGlideAnimation && {target_id}.uiVisible)
               ? (-height - 140)
               : customConfig.clockTopMargin
            spacing: 6
            z: 10

            opacity: (customConfig.enableWindowsGlideAnimation && {target_id}.uiVisible)
                     ? 0.0
                     : ((!{target_id}.uiVisible || customConfig.keepClockVisibleWhenUnlocking) ? 1.0 : 0.0)

            Behavior on y {{
                NumberAnimation {{
                    duration: 450
                    easing.type: Easing.OutCubic
                }}
            }}

            Behavior on opacity {{
                NumberAnimation {{
                    duration: 400
                    easing.type: Easing.InOutQuad
                }}
            }}

            PlasmaClock.Clock {{
                id: customTimeSource
                trackSeconds: customConfig.timeFormat.includes("s") || Qt.locale().timeFormat(Locale.ShortFormat).includes("s")
            }}

            Text {{
                text: customConfig.timeFormat !== ""
                      ? Qt.formatDateTime(customTimeSource.dateTime, customConfig.timeFormat)
                      : Qt.formatTime(customTimeSource.dateTime, Qt.locale(), Locale.ShortFormat)
                textFormat: Text.PlainText
                font.pointSize: customConfig.timePointSize
                font.weight: customConfig.timeFontWeight
                font.family: customConfig.timeFontFamily !== "" ? customConfig.timeFontFamily : Kirigami.Theme.defaultFont.family
                renderType: Text.NativeRendering
                color: customConfig.timeColor !== "" ? customConfig.timeColor : Kirigami.Theme.textColor
                Layout.alignment: customConfig.clockAlignment === "Left" ? Qt.AlignLeft : (customConfig.clockAlignment === "Right" ? Qt.AlignRight : Qt.AlignHCenter)

                layer.enabled: true
                layer.effect: DropShadow {{
                    transparentBorder: true
                    radius: 12
                    samples: 16
                    verticalOffset: 2
                    color: Qt.rgba(0, 0, 0, 0.75)
                }}
            }}

            Text {{
                visible: customConfig.showDate
                text: customConfig.dateFormat !== ""
                      ? Qt.formatDateTime(customTimeSource.dateTime, customConfig.dateFormat)
                      : Qt.formatDate(customTimeSource.dateTime, Qt.locale(), Locale.LongFormat)
                textFormat: Text.PlainText
                font.pointSize: customConfig.datePointSize
                font.weight: customConfig.dateFontWeight
                font.family: customConfig.dateFontFamily !== "" ? customConfig.dateFontFamily : Kirigami.Theme.defaultFont.family
                renderType: Text.NativeRendering
                color: customConfig.dateColor !== "" ? customConfig.dateColor : Kirigami.Theme.textColor
                Layout.alignment: customConfig.clockAlignment === "Left" ? Qt.AlignLeft : (customConfig.clockAlignment === "Right" ? Qt.AlignRight : Qt.AlignHCenter)

                layer.enabled: true
                layer.effect: DropShadow {{
                    transparentBorder: true
                    radius: 8
                    samples: 16
                    verticalOffset: 1
                    color: Qt.rgba(0, 0, 0, 0.7)
                }}
            }}

            Text {{
                visible: customConfig.showUnlockHint && !{target_id}.uiVisible
                text: customConfig.unlockHintText
                textFormat: Text.PlainText
                font.pointSize: customConfig.hintPointSize
                font.weight: customConfig.hintFontWeight
                font.family: customConfig.hintFontFamily !== "" ? customConfig.hintFontFamily : Kirigami.Theme.defaultFont.family
                opacity: 0.85
                renderType: Text.NativeRendering
                color: customConfig.hintColor !== "" ? customConfig.hintColor : Kirigami.Theme.textColor
                Layout.alignment: customConfig.hintAlignment === "Left" ? Qt.AlignLeft
                                : (customConfig.hintAlignment === "Right" ? Qt.AlignRight
                                : (customConfig.hintAlignment === "Center" ? Qt.AlignHCenter
                                : (customConfig.clockAlignment === "Left" ? Qt.AlignLeft
                                : (customConfig.clockAlignment === "Right" ? Qt.AlignRight : Qt.AlignHCenter))))
                Layout.topMargin: customConfig.hintTopMargin

                layer.enabled: true
                layer.effect: DropShadow {{
                    transparentBorder: true
                    radius: 6
                    samples: 12
                    verticalOffset: 1
                    color: Qt.rgba(0, 0, 0, 0.6)
                }}
            }}
        }}

        // Hidden dummy clock to preserve WallpaperFader bindings
        DropShadow {{
            id: clockShadow
            visible: false
            width: 0
            height: 0
        }}

        Clock {{
            id: clock
            property Item shadow: clockShadow
            visible: false
            width: 0
            height: 0
        }}"""

    content = re.sub(clock_to_replace, new_clock_block, content, count=1, flags=re.DOTALL)

    if is_sddm:
        old_bg_block = r"Background\s*\{\s*x:\s*geometry\.x.*?sceneBackgroundImage:\s*config\.background\s*\}"
        new_bg_block = """Background {
                x: geometry.x; y: geometry.y; width: geometry.width; height: geometry.height
                sceneBackgroundType: "image"
                sceneBackgroundColor: (customConfig && customConfig.wallpaperColor !== "") ? customConfig.wallpaperColor : (config.color ? config.color : "#0f172a")
                sceneBackgroundImage: {
                    var p = (customConfig && customConfig.customWallpaper && customConfig.customWallpaper !== "") ? customConfig.customWallpaper : (config.background ? config.background : "");
                    if (!p || p === "") return "";
                    return (p.indexOf(":") === -1) ? ("file://" + p) : p;
                }
            }"""
        content = re.sub(old_bg_block, new_bg_block, content, count=1, flags=re.DOTALL)

    prefix = "QQC2." if is_sddm else ""
    old_main_stack = r"(?:QQC2\.)?StackView\s*\{\s*id:\s*mainStack\s*anchors\s*\{[^}]+\}\s*height:"
    new_main_stack = f"""{prefix}StackView {{
            id: mainStack
            anchors {{
                left: parent.left
                right: parent.right
            }}
            y: (customConfig.enableWindowsGlideAnimation && !{target_id}.uiVisible)
               ? ({target_id}.height + 150)
               : 0

            Behavior on y {{
                NumberAnimation {{
                    duration: 450
                    easing.type: Easing.OutCubic
                }}
            }}

            height:"""
    content = re.sub(old_main_stack, new_main_stack, content, count=1)

    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with open(dst_path, "w") as f:
        f.write(content)


def build_logout_screen(src_path, dst_path):
    """Patches KDE Plasma's Logout.qml to support top clock, custom banner, and uncompressed background wallpaper."""
    if not os.path.exists(src_path):
        return
    with open(src_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "import org.kde.plasma.clock as PlasmaClock" not in content:
        content = "import org.kde.plasma.clock as PlasmaClock\n" + content

    logout_overlay = """
    QtObject {
        id: logoutCustomConfig
        property bool enabled: true
        property bool showClock: true
        property int clockTopMargin: 45
        property string clockAlignment: "Center"
        property int clockHorizontalMargin: 60
        property int timePointSize: 54
        property string timeFontFamily: "Noto Sans Mono ExtraCondensed Thin"
        property int timeFontWeight: Font.Light
        property string timeColor: "#ffffff"
        property string timeFormat: "h:mm ap"
        property bool showDate: true
        property int datePointSize: 16
        property string dateFontFamily: "Latin Modern Mono Light"
        property int dateFontWeight: Font.Normal
        property string dateColor: "#cbd5e1"
        property string dateFormat: "dddd, MMMM d"
        property string customTitle: ""
        property string titleColor: "#f8fafc"
        property int titlePointSize: 18
        property string wallpaperPath: ""
        property double bgOpacity: 0.35
        property string bgColor: "#000000"
        property bool showCountdown: true
    }

    Item {
        id: customLogoutBgContainer
        anchors.fill: parent
        z: -2
        visible: logoutCustomConfig.enabled

        Rectangle {
            id: customLogoutFallbackBg
            anchors.fill: parent
            color: logoutCustomConfig.bgColor !== "" ? logoutCustomConfig.bgColor : "#0f172a"
        }

        Image {
            id: customLogoutWallpaper
            anchors.fill: parent
            visible: logoutCustomConfig.wallpaperPath !== ""
            source: {
                var wp = logoutCustomConfig.wallpaperPath;
                if (!wp || wp === "") return "";
                return (wp.indexOf(":") === -1) ? ("file://" + wp) : wp;
            }
            fillMode: Image.PreserveAspectCrop
            smooth: true
            mipmap: true
            asynchronous: false
            cache: true
        }

        Rectangle {
            id: customLogoutDimOverlay
            anchors.fill: parent
            color: logoutCustomConfig.bgColor !== "" ? logoutCustomConfig.bgColor : "#000000"
            opacity: logoutCustomConfig.bgOpacity
        }
    }

    ColumnLayout {
        id: logoutTopClock
        visible: logoutCustomConfig.enabled && (logoutCustomConfig.showClock || logoutCustomConfig.customTitle !== "")
        anchors.horizontalCenter: logoutCustomConfig.clockAlignment === "Center" ? parent.horizontalCenter : undefined
        anchors.left: logoutCustomConfig.clockAlignment === "Left" ? parent.left : undefined
        anchors.leftMargin: logoutCustomConfig.clockHorizontalMargin
        anchors.right: logoutCustomConfig.clockAlignment === "Right" ? parent.right : undefined
        anchors.rightMargin: logoutCustomConfig.clockHorizontalMargin
        y: logoutCustomConfig.clockTopMargin
        spacing: 4
        z: 99

        PlasmaClock.Clock {
            id: logoutTimeSource
            trackSeconds: logoutCustomConfig.timeFormat.includes("s")
        }

        Text {
            visible: logoutCustomConfig.showClock
            text: logoutCustomConfig.timeFormat !== ""
                  ? Qt.formatDateTime(logoutTimeSource.dateTime, logoutCustomConfig.timeFormat)
                  : Qt.formatTime(logoutTimeSource.dateTime, Qt.locale(), Locale.ShortFormat)
            textFormat: Text.PlainText
            font.pointSize: logoutCustomConfig.timePointSize
            font.weight: logoutCustomConfig.timeFontWeight
            font.family: logoutCustomConfig.timeFontFamily !== "" ? logoutCustomConfig.timeFontFamily : Kirigami.Theme.defaultFont.family
            color: logoutCustomConfig.timeColor
            Layout.alignment: logoutCustomConfig.clockAlignment === "Left" ? Qt.AlignLeft : (logoutCustomConfig.clockAlignment === "Right" ? Qt.AlignRight : Qt.AlignHCenter)

            style: Text.Raised
            styleColor: Qt.rgba(0, 0, 0, 0.75)
        }

        Text {
            visible: logoutCustomConfig.showClock && logoutCustomConfig.showDate
            text: logoutCustomConfig.dateFormat !== ""
                  ? Qt.formatDateTime(logoutTimeSource.dateTime, logoutCustomConfig.dateFormat)
                  : Qt.formatDate(logoutTimeSource.dateTime, Qt.locale(), Locale.LongFormat)
            textFormat: Text.PlainText
            font.pointSize: logoutCustomConfig.datePointSize
            font.weight: logoutCustomConfig.dateFontWeight
            font.family: logoutCustomConfig.dateFontFamily !== "" ? logoutCustomConfig.dateFontFamily : Kirigami.Theme.defaultFont.family
            color: logoutCustomConfig.dateColor
            Layout.alignment: logoutCustomConfig.clockAlignment === "Left" ? Qt.AlignLeft : (logoutCustomConfig.clockAlignment === "Right" ? Qt.AlignRight : Qt.AlignHCenter)

            style: Text.Raised
            styleColor: Qt.rgba(0, 0, 0, 0.7)
        }

        Text {
            visible: logoutCustomConfig.customTitle !== ""
            text: logoutCustomConfig.customTitle
            textFormat: Text.PlainText
            font.pointSize: logoutCustomConfig.titlePointSize
            font.weight: Font.DemiBold
            color: logoutCustomConfig.titleColor
            Layout.topMargin: 6
            Layout.alignment: logoutCustomConfig.clockAlignment === "Left" ? Qt.AlignLeft : (logoutCustomConfig.clockAlignment === "Right" ? Qt.AlignRight : Qt.AlignHCenter)

            style: Text.Raised
            styleColor: Qt.rgba(0, 0, 0, 0.6)
        }
    }
"""
    match = re.search(r"(?:Item|FocusScope)\s*\{\s*id:\s*\w+", content)
    if match:
        insert_pos = match.end()
        content = content[:insert_pos] + "\n" + logout_overlay + content[insert_pos:]

    # Hide stock black backgroundRect when custom wallpaper is used
    rect_replacement = """Rectangle {
        id: backgroundRect
        anchors.fill: parent
        color: "black"
        opacity: (logoutCustomConfig.enabled && logoutCustomConfig.wallpaperPath !== "") ? 0.0 : 0.85
        visible: !logoutCustomConfig.enabled || logoutCustomConfig.wallpaperPath === ""
    }"""
    content = re.sub(
        r"Rectangle\s*\{\s*id:\s*backgroundRect.*?(?=\n\s*MouseArea)",
        rect_replacement,
        content,
        count=1,
        flags=re.DOTALL
    )

    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    with open(dst_path, "w", encoding="utf-8") as f:
        f.write(content)


class KeyCaptureDialog(QDialog):
    """Clean, properly sized dialog listening for any keyboard key press"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Press Any Key")
        self.setMinimumSize(460, 240)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                color: #f8fafc;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        lbl = QLabel("⌨️ Press any key on your keyboard...")
        lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub = QLabel("Press the key you want to set as unlock trigger (e.g. Space, Enter, Tab, A-Z)")
        sub.setStyleSheet("color: #94a3b8; font-size: 13px;")
        sub.setWordWrap(True)
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.card = QFrame()
        self.card.setMinimumHeight(54)
        self.card.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 2px dashed #0284c7;
                border-radius: 8px;
            }
        """)
        card_l = QHBoxLayout(self.card)
        card_l.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.lbl_detected = QLabel("Listening for key press...")
        self.lbl_detected.setStyleSheet("font-size: 15px; font-weight: bold; color: #34d399; border: none; background: transparent;")
        card_l.addWidget(self.lbl_detected)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setMinimumSize(110, 36)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #e2e8f0;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: #475569;
            }
        """)
        btn_cancel.clicked.connect(self.reject)

        layout.addWidget(lbl)
        layout.addWidget(sub)
        layout.addWidget(self.card)
        layout.addWidget(btn_cancel, 0, Qt.AlignmentFlag.AlignCenter)

        self.captured_key_name = None
        self.captured_key_code = None

    def keyPressEvent(self, event):
        key = event.key()
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return

        if key == Qt.Key.Key_Space:
            key_name = "Space"
        elif key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            key_name = "Enter"
        elif key == Qt.Key.Key_Tab:
            key_name = "Tab"
        elif key == Qt.Key.Key_Backspace:
            key_name = "Backspace"
        elif key == Qt.Key.Key_Escape:
            key_name = "Escape"
        else:
            key_name = QKeySequence(key).toString()
            if not key_name or key_name == " ":
                key_name = f"Key_{key}"

        self.captured_key_name = key_name
        self.captured_key_code = key
        self.lbl_detected.setText(f"✓ Selected: {key_name}")
        self.card.setStyleSheet("""
            QFrame {
                background-color: #064e3b;
                border: 2px solid #10b981;
                border-radius: 8px;
            }
        """)
        QTimer.singleShot(250, self.accept)


class MouseCaptureDialog(QDialog):
    """Clean dialog allowing click detection or direct one-click selection"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Mouse Trigger")
        self.setMinimumSize(480, 290)
        self.setModal(True)
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                color: #f8fafc;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        lbl = QLabel("🖱️ Select Mouse Action")
        lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sub = QLabel("Click any button below, or click directly in this window:")
        sub.setStyleSheet("color: #94a3b8; font-size: 13px;")
        sub.setWordWrap(True)
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        grid = QGridLayout()
        grid.setSpacing(10)

        options = [
            ("Left Click", "Primary click anywhere on screen"),
            ("Right Click", "Secondary / context click"),
            ("Middle Click", "Scroll-wheel press"),
            ("Double Click", "Fast double left click"),
        ]

        self.captured_action = None

        row = 0
        col = 0
        for opt_name, desc in options:
            btn = QPushButton(f"🖱️ {opt_name}")
            btn.setMinimumHeight(44)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #1e293b;
                    border: 1px solid #334155;
                    border-radius: 8px;
                    color: #f1f5f9;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 8px 14px;
                }
                QPushButton:hover {
                    background-color: #0284c7;
                    border-color: #38bdf8;
                }
            """)
            btn.clicked.connect(lambda checked, name=opt_name: self.choose_action(name))
            grid.addWidget(btn, row, col)
            col += 1
            if col > 1:
                col = 0
                row += 1

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setMinimumSize(110, 36)
        btn_cancel.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #e2e8f0;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                padding: 6px 16px;
            }
            QPushButton:hover {
                background-color: #475569;
            }
        """)
        btn_cancel.clicked.connect(self.reject)

        layout.addWidget(lbl)
        layout.addWidget(sub)
        layout.addLayout(grid)
        layout.addWidget(btn_cancel, 0, Qt.AlignmentFlag.AlignCenter)

    def choose_action(self, action_name):
        self.captured_action = action_name
        self.accept()

    def mousePressEvent(self, event):
        btn = event.button()
        if btn == Qt.MouseButton.LeftButton:
            self.captured_action = "Left Click"
        elif btn == Qt.MouseButton.RightButton:
            self.captured_action = "Right Click"
        elif btn == Qt.MouseButton.MiddleButton:
            self.captured_action = "Middle Click"
        if self.captured_action:
            self.accept()

    def mouseDoubleClickEvent(self, event):
        self.captured_action = "Double Click"
        self.accept()


class LockscreenConfigApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KDE Lock, Login & Logout Customizer — by Aayan")
        # Flexible minimum size so it works on any screen resolution with scrollbars
        self.setMinimumSize(780, 600)
        self.resize(940, 820)
        self.config = self.load_config()

        try:
            self.ensure_theme_installed()
        except Exception as e:
            print(f"Theme auto-install note: {e}")

        self.key_triggers = list(self.config.get("unlockKeyNames", ["Space"]))
        self.key_codes = list(self.config.get("unlockKeyCodes", [32]))
        self.mouse_triggers = list(self.config.get("unlockMouseButtons", ["Left Click"]))

        self.init_ui()
        self.load_values_to_ui()
        self.update_preview()

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_preview)
        self.clock_timer.start(1000)

    def wrap_in_scroll_area(self, content_widget):
        """Wraps any tab widget inside a clean QScrollArea so nothing ever collides or gets cut off."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setWidget(content_widget)
        return scroll

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    data = json.load(f)
                    cfg = DEFAULT_CONFIG.copy()
                    cfg.update(data)
                    return cfg
            except Exception:
                pass
        return DEFAULT_CONFIG.copy()

    def save_config_to_file(self):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f, indent=4)

    # -----------------------------
    # Color Picker Helpers
    # -----------------------------
    def update_color_button(self, button, hex_color):
        try:
            c = QColor(hex_color)
            if c.isValid():
                button.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {hex_color};
                        border: 2px solid #64748b;
                        border-radius: 6px;
                    }}
                    QPushButton:hover {{
                        border: 2px solid #38bdf8;
                    }}
                """)
        except Exception:
            pass

    def pick_color_dialog(self, current_hex, on_selected_cb):
        init_col = QColor(current_hex) if QColor(current_hex).isValid() else QColor("#ffffff")
        col = QColorDialog.getColor(init_col, self, "Select Color")
        if col.isValid():
            on_selected_cb(col.name())

    def build_color_picker_row(self, label_text, txt_widget, btn_swatch, on_pick_click, on_preset_click):
        v_box = QVBoxLayout()
        v_box.setSpacing(8)

        h_row = QHBoxLayout()
        h_row.setSpacing(10)
        lbl = QLabel(label_text)
        lbl.setMinimumWidth(145)
        lbl.setStyleSheet("font-weight: bold;")
        h_row.addWidget(lbl)

        btn_swatch.setFixedSize(36, 34)
        btn_swatch.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_swatch.setToolTip("Click to open color picker")
        btn_swatch.clicked.connect(on_pick_click)
        h_row.addWidget(btn_swatch)

        txt_widget.setMinimumWidth(105)
        txt_widget.setMaximumWidth(120)
        txt_widget.setMinimumHeight(34)
        h_row.addWidget(txt_widget)

        btn_pick = QPushButton("🎨 Pick Color...")
        btn_pick.setMinimumHeight(34)
        btn_pick.setStyleSheet("padding: 4px 14px;")
        btn_pick.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_pick.clicked.connect(on_pick_click)
        h_row.addWidget(btn_pick)

        h_row.addStretch()
        v_box.addLayout(h_row)

        h_presets = QHBoxLayout()
        h_presets.setSpacing(6)
        lbl_p = QLabel("Quick Palette:")
        lbl_p.setMinimumWidth(145)
        lbl_p.setStyleSheet("color: #94a3b8; font-size: 12px;")
        h_presets.addWidget(lbl_p)

        for hex_code, name in COLOR_PRESETS:
            chip = QPushButton()
            chip.setFixedSize(24, 24)
            chip.setCursor(Qt.CursorShape.PointingHandCursor)
            chip.setToolTip(f"{name} ({hex_code})")
            chip.setStyleSheet(f"""
                QPushButton {{
                    background-color: {hex_code};
                    border: 1px solid #475569;
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    border: 2px solid #38bdf8;
                }}
            """)
            chip.clicked.connect(lambda checked, h=hex_code: on_preset_click(h))
            h_presets.addWidget(chip)
        h_presets.addStretch()
        v_box.addLayout(h_presets)

        return v_box

    def build_font_presets_grid(self, callback):
        """Creates a clean multi-row grid of font preset buttons so they never collide."""
        box = QVBoxLayout()
        box.setSpacing(6)
        lbl = QLabel("Quick Font Presets:")
        lbl.setStyleSheet("color: #94a3b8; font-size: 12px;")
        box.addWidget(lbl)

        grid = QGridLayout()
        grid.setSpacing(8)
        cols = 4
        for idx, (name, font_name) in enumerate(POPULAR_FONTS):
            btn = QPushButton(name)
            btn.setMinimumHeight(32)
            btn.setStyleSheet("padding: 4px 10px;")
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            btn.clicked.connect(lambda checked, fn=font_name: callback(fn))
            grid.addWidget(btn, idx // cols, idx % cols)
        box.addLayout(grid)
        return box

    def choose_time_color(self):
        self.pick_color_dialog(self.txt_time_color.text().strip(), self.set_time_color)

    def set_time_color(self, hex_color):
        self.txt_time_color.setText(hex_color)
        self.update_color_button(self.btn_time_color, hex_color)
        self.update_preview()

    def on_time_color_text_changed(self, text):
        t = text.strip()
        if QColor(t).isValid():
            self.update_color_button(self.btn_time_color, t)
            self.update_preview()

    def choose_date_color(self):
        self.pick_color_dialog(self.txt_date_color.text().strip(), self.set_date_color)

    def set_date_color(self, hex_color):
        self.txt_date_color.setText(hex_color)
        self.update_color_button(self.btn_date_color, hex_color)
        self.update_preview()

    def on_date_color_text_changed(self, text):
        t = text.strip()
        if QColor(t).isValid():
            self.update_color_button(self.btn_date_color, t)
            self.update_preview()

    def choose_text_color(self):
        self.pick_color_dialog(self.txt_text_color.text().strip(), self.set_text_color)

    def set_text_color(self, hex_color):
        self.txt_text_color.setText(hex_color)
        self.update_color_button(self.btn_text_color, hex_color)
        self.update_preview()

    def on_text_color_text_changed(self, text):
        t = text.strip()
        if QColor(t).isValid():
            self.update_color_button(self.btn_text_color, t)
            self.update_preview()

    def choose_logout_title_color(self):
        self.pick_color_dialog(self.txt_logout_title_color.text().strip(), self.set_logout_title_color)

    def set_logout_title_color(self, hex_color):
        self.txt_logout_title_color.setText(hex_color)
        self.update_color_button(self.btn_logout_title_color, hex_color)

    def on_logout_title_color_changed(self, text):
        t = text.strip()
        if QColor(t).isValid():
            self.update_color_button(self.btn_logout_title_color, t)

    def choose_logout_bg_color(self):
        self.pick_color_dialog(self.txt_logout_bg_color.text().strip(), self.set_logout_bg_color)

    def set_logout_bg_color(self, hex_color):
        self.txt_logout_bg_color.setText(hex_color)
        self.update_color_button(self.btn_logout_bg_color, hex_color)

    def on_logout_bg_color_changed(self, text):
        t = text.strip()
        if QColor(t).isValid():
            self.update_color_button(self.btn_logout_bg_color, t)

    def choose_sddm_bg_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select SDDM Background Image", "", "Images (*.png *.jpg *.jpeg *.svg *.bmp *.webp);;All Files (*)"
        )
        if file_path:
            self.txt_sddm_bg.setText(file_path)

    def clear_sddm_bg_file(self):
        self.txt_sddm_bg.setText("")

    def match_lockscreen_sddm_bg(self):
        wall = get_current_lockscreen_wallpaper()
        if wall:
            self.txt_sddm_bg.setText(wall)
        else:
            QMessageBox.information(self, "Lock Screen Wallpaper", "No custom wallpaper found in ~/.config/kscreenlockerrc.")

    def choose_logout_wallpaper_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Logout Background Image", "", "Images (*.png *.jpg *.jpeg *.svg *.bmp *.webp);;All Files (*)"
        )
        if file_path:
            self.txt_logout_wallpaper.setText(file_path)

    def clear_logout_wallpaper_file(self):
        self.txt_logout_wallpaper.setText("")

    def match_login_logout_wallpaper(self):
        login_bg = self.txt_sddm_bg.text().strip() if hasattr(self, "txt_sddm_bg") else ""
        if login_bg:
            self.txt_logout_wallpaper.setText(login_bg)
        else:
            QMessageBox.information(self, "Login Wallpaper", "Please select a login screen wallpaper first.")

    def match_lockscreen_logout_wallpaper(self):
        wall = get_current_lockscreen_wallpaper()
        if wall:
            self.txt_logout_wallpaper.setText(wall)
        else:
            QMessageBox.information(self, "Lock Screen Wallpaper", "No custom wallpaper found in ~/.config/kscreenlockerrc.")

    def choose_sddm_bg_color(self):
        self.pick_color_dialog(self.txt_sddm_bg_color.text().strip(), self.set_sddm_bg_color)

    def set_sddm_bg_color(self, hex_color):
        self.txt_sddm_bg_color.setText(hex_color)
        self.update_color_button(self.btn_sddm_bg_color, hex_color)

    def on_sddm_bg_color_changed(self, text):
        t = text.strip()
        if QColor(t).isValid():
            self.update_color_button(self.btn_sddm_bg_color, t)

    def update_sddm_status_badge(self):
        if not hasattr(self, "lbl_sddm_status"):
            return
        is_patched = self.is_qml_patched(SYSTEM_SDDM_QML)
        if is_patched:
            self.lbl_sddm_status.setText("🟢 Active & Customized (/usr/share/sddm/themes/breeze)\nTop Clock, Custom Text & Glide Animation are active on Login Screen.")
            self.lbl_sddm_status.setStyleSheet("color: #34d399; font-weight: bold; font-size: 13px;")
        else:
            self.lbl_sddm_status.setText("⚪ Stock KDE Breeze Default (/usr/share/sddm/themes/breeze)\nStock theme currently unmodified.")
            self.lbl_sddm_status.setStyleSheet("color: #94a3b8; font-style: italic; font-size: 13px;")

    def on_clock_align_changed(self, text):
        is_centered = ("Center" in text)
        if hasattr(self, 'slider_h_margin'):
            self.slider_h_margin.setEnabled(not is_centered)
            self.spin_h_margin.setEnabled(not is_centered)
            if is_centered:
                self.lbl_h_margin.setText("Edge Margin (px) [Center Mode]:")
                self.lbl_h_margin.setStyleSheet("color: #64748b;")
            else:
                self.lbl_h_margin.setText("Distance from Screen Edge (px):")
                self.lbl_h_margin.setStyleSheet("")
        self.update_preview()

    def set_position_preset(self, align_name, top_margin, h_margin):
        self.cmb_clock_align.setCurrentText(align_name)
        self.spin_top_margin.setValue(top_margin)
        self.spin_h_margin.setValue(h_margin)
        self.on_clock_align_changed(align_name)
        self.update_preview()

    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(16, 12, 16, 12)

        # -----------------------------
        # Live Preview Panel
        # -----------------------------
        preview_group = QGroupBox("Live Lock / Login / Logout Clock Preview")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(10, 10, 10, 10)

        self.preview_box = QFrame()
        self.preview_box.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #181d27, stop:1 #0a0d14);
                border: 1px solid #2e384d;
                border-radius: 12px;
            }
        """)
        self.preview_box.setMinimumHeight(175)
        self.preview_box.setMaximumHeight(210)
        self.box_layout = QVBoxLayout(self.preview_box)
        self.box_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.box_layout.setSpacing(4)
        self.box_layout.setContentsMargins(24, 10, 24, 10)

        self.lbl_prev_time = QLabel("12:00")
        self.lbl_prev_time.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_prev_time.setStyleSheet("color: #ffffff; background: transparent; border: none;")

        self.lbl_prev_date = QLabel("Tuesday, November 10")
        self.lbl_prev_date.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_prev_date.setStyleSheet("color: #cbd5e1; background: transparent; border: none;")

        self.lbl_prev_text = QLabel("Custom Text")
        self.lbl_prev_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_prev_text.setStyleSheet("color: #94a3b8; background: transparent; border: none;")

        self.box_layout.addWidget(self.lbl_prev_time)
        self.box_layout.addWidget(self.lbl_prev_date)
        self.box_layout.addWidget(self.lbl_prev_text)

        preview_layout.addWidget(self.preview_box)
        main_layout.addWidget(preview_group)

        # -----------------------------
        # Tabs for Customization (All Scrollable)
        # -----------------------------
        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(True)
        main_layout.addWidget(self.tabs, 1)

        self.create_time_tab()
        self.create_date_tab()
        self.create_position_tab()
        self.create_text_tab()
        self.create_interaction_tab()
        self.create_sddm_tab()
        self.create_logout_tab()
        self.create_animations_tab()
        self.create_about_tab()

        # -----------------------------
        # Bottom Action Bar
        # -----------------------------
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self.btn_reset = QPushButton("🔄 Reset Defaults")
        self.btn_reset.setMinimumHeight(38)
        self.btn_reset.setStyleSheet("padding: 6px 14px;")
        self.btn_reset.clicked.connect(self.reset_defaults)

        self.btn_reset_stock = QPushButton("⏮️ Reset to Stock Breeze")
        self.btn_reset_stock.setMinimumHeight(38)
        self.btn_reset_stock.setStyleSheet("""
            QPushButton {
                background-color: #7f1d1d;
                color: #fecaca;
                font-weight: bold;
                padding: 6px 14px;
                border: 1px solid #991b1b;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #991b1b;
                color: #ffffff;
            }
        """)
        self.btn_reset_stock.setToolTip("Restore SDDM Breeze, Lockscreen, or Logout to unmodified stock KDE defaults")
        self.btn_reset_stock.clicked.connect(self.reset_to_stock_menu)

        self.btn_test_sddm = QPushButton("💻 Test Login Screen")
        self.btn_test_sddm.setMinimumHeight(38)
        self.btn_test_sddm.setStyleSheet("font-weight: bold; padding: 6px 14px;")
        self.btn_test_sddm.setToolTip("Test SDDM Login Screen in test mode with sddm-greeter-qt6")
        self.btn_test_sddm.clicked.connect(self.test_sddm_screen)

        self.btn_test_logout = QPushButton("🚪 Test Logout Screen")
        self.btn_test_logout.setMinimumHeight(38)
        self.btn_test_logout.setStyleSheet("font-weight: bold; padding: 6px 14px;")
        self.btn_test_logout.clicked.connect(self.test_logout_screen)

        self.btn_test = QPushButton("👁 Test Lock Screen")
        self.btn_test.setMinimumHeight(38)
        self.btn_test.setStyleSheet("font-weight: bold; padding: 6px 14px;")
        self.btn_test.clicked.connect(self.test_lockscreen)

        self.btn_apply = QPushButton("💾 Apply All Settings")
        self.btn_apply.setMinimumHeight(40)
        self.btn_apply.setStyleSheet("""
            QPushButton {
                background-color: #2563eb;
                color: white;
                font-weight: bold;
                padding: 8px 22px;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #1d4ed8;
            }
        """)
        self.btn_apply.clicked.connect(self.apply_settings)

        btn_layout.addWidget(self.btn_reset)
        btn_layout.addWidget(self.btn_reset_stock)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_test_sddm)
        btn_layout.addWidget(self.btn_test_logout)
        btn_layout.addWidget(self.btn_test)
        btn_layout.addWidget(self.btn_apply)

        main_layout.addLayout(btn_layout)

    # -----------------------------
    # Tab 1: Time Numbers (Digits)
    # -----------------------------
    def create_time_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)
        layout.setContentsMargins(16, 16, 16, 16)

        lbl_info = QLabel("Customize font, size, weight, color, and format for the <b>TIME NUMBERS (Clock Digits)</b>:")
        lbl_info.setWordWrap(True)
        layout.addWidget(lbl_info)

        h_font = QHBoxLayout()
        h_font.setSpacing(10)
        lbl_tf = QLabel("Time Numbers Font:")
        lbl_tf.setMinimumWidth(145)
        lbl_tf.setStyleSheet("font-weight: bold;")
        h_font.addWidget(lbl_tf)

        self.cmb_time_font = QFontComboBox()
        self.cmb_time_font.setMinimumHeight(34)
        self.cmb_time_font.currentFontChanged.connect(self.on_time_font_changed)
        h_font.addWidget(self.cmb_time_font, 1)

        self.chk_time_custom_font = QCheckBox("Use Custom Font")
        self.chk_time_custom_font.setChecked(True)
        self.chk_time_custom_font.toggled.connect(self.toggle_time_custom_font)
        h_font.addWidget(self.chk_time_custom_font)
        layout.addLayout(h_font)

        layout.addLayout(self.build_font_presets_grid(self.set_time_font))

        self.lbl_time_digits_sample = QLabel("Numbers Sample:  0 1 2 3 4 5 6 7 8 9 :")
        self.lbl_time_digits_sample.setMinimumHeight(38)
        self.lbl_time_digits_sample.setStyleSheet(
            "background: #1e2430; border: 1px solid #3b4252; padding: 6px 12px; border-radius: 6px; font-size: 15px; color: #60a5fa;"
        )
        layout.addWidget(self.lbl_time_digits_sample)

        self.btn_time_color = QPushButton()
        self.txt_time_color = QLineEdit("#ffffff")
        self.txt_time_color.textChanged.connect(self.on_time_color_text_changed)
        time_color_box = self.build_color_picker_row(
            "Numbers Font Color:",
            self.txt_time_color,
            self.btn_time_color,
            self.choose_time_color,
            self.set_time_color
        )
        layout.addLayout(time_color_box)

        h_size = QHBoxLayout()
        h_size.setSpacing(10)
        lbl_sz = QLabel("Numbers Size (pt):")
        lbl_sz.setMinimumWidth(145)
        h_size.addWidget(lbl_sz)
        self.slider_time_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_time_size.setRange(24, 140)
        self.spin_time_size = QSpinBox()
        self.spin_time_size.setRange(24, 140)
        self.spin_time_size.setMinimumSize(78, 34)
        self.slider_time_size.valueChanged.connect(self.spin_time_size.setValue)
        self.spin_time_size.valueChanged.connect(self.slider_time_size.setValue)
        self.spin_time_size.valueChanged.connect(lambda: self.update_preview())
        h_size.addWidget(self.slider_time_size, 1)
        h_size.addWidget(self.spin_time_size)
        layout.addLayout(h_size)

        h_weight = QHBoxLayout()
        h_weight.setSpacing(10)
        lbl_wt = QLabel("Numbers Weight:")
        lbl_wt.setMinimumWidth(145)
        h_weight.addWidget(lbl_wt)
        self.cmb_time_weight = QComboBox()
        self.cmb_time_weight.setMinimumHeight(34)
        for name in TIME_WEIGHTS.keys():
            self.cmb_time_weight.addItem(name)
        self.cmb_time_weight.currentTextChanged.connect(lambda: self.update_preview())
        h_weight.addWidget(self.cmb_time_weight, 1)
        layout.addLayout(h_weight)

        h_fmt = QHBoxLayout()
        h_fmt.setSpacing(10)
        lbl_fm = QLabel("Time Format:")
        lbl_fm.setMinimumWidth(145)
        h_fmt.addWidget(lbl_fm)
        self.cmb_time_fmt = QComboBox()
        self.cmb_time_fmt.setMinimumHeight(34)
        for name in TIME_FORMATS.keys():
            self.cmb_time_fmt.addItem(name)
        self.cmb_time_fmt.currentTextChanged.connect(self.on_time_fmt_changed)
        h_fmt.addWidget(self.cmb_time_fmt, 1)
        layout.addLayout(h_fmt)

        h_custom_fmt = QHBoxLayout()
        h_custom_fmt.setSpacing(10)
        lbl_cf = QLabel("Custom Format:")
        lbl_cf.setMinimumWidth(145)
        h_custom_fmt.addWidget(lbl_cf)
        self.txt_custom_time_fmt = QLineEdit()
        self.txt_custom_time_fmt.setMinimumHeight(34)
        self.txt_custom_time_fmt.setPlaceholderText("e.g. HH:mm or h:mm:ss ap")
        self.txt_custom_time_fmt.textChanged.connect(lambda: self.update_preview())
        h_custom_fmt.addWidget(self.txt_custom_time_fmt, 1)
        layout.addLayout(h_custom_fmt)

        layout.addStretch()
        self.tabs.addTab(self.wrap_in_scroll_area(tab), "⏰ Time Numbers")

    # -----------------------------
    # Tab 2: Date & Day Words
    # -----------------------------
    def create_date_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)
        layout.setContentsMargins(16, 16, 16, 16)

        self.chk_show_date = QCheckBox("Show Date (Day and Month)")
        self.chk_show_date.toggled.connect(lambda: self.update_preview())
        layout.addWidget(self.chk_show_date)

        h_font = QHBoxLayout()
        h_font.setSpacing(10)
        lbl_df = QLabel("Date Font Family:")
        lbl_df.setMinimumWidth(145)
        lbl_df.setStyleSheet("font-weight: bold;")
        h_font.addWidget(lbl_df)

        self.cmb_date_font = QFontComboBox()
        self.cmb_date_font.setMinimumHeight(34)
        self.cmb_date_font.currentFontChanged.connect(lambda: self.update_preview())
        h_font.addWidget(self.cmb_date_font, 1)

        self.chk_date_custom_font = QCheckBox("Use Custom Font")
        self.chk_date_custom_font.setChecked(True)
        self.chk_date_custom_font.toggled.connect(self.toggle_date_custom_font)
        h_font.addWidget(self.chk_date_custom_font)
        layout.addLayout(h_font)

        layout.addLayout(self.build_font_presets_grid(self.set_date_font))

        self.btn_date_color = QPushButton()
        self.txt_date_color = QLineEdit("#cbd5e1")
        self.txt_date_color.textChanged.connect(self.on_date_color_text_changed)
        date_color_box = self.build_color_picker_row(
            "Date Font Color:",
            self.txt_date_color,
            self.btn_date_color,
            self.choose_date_color,
            self.set_date_color
        )
        layout.addLayout(date_color_box)

        h_size = QHBoxLayout()
        h_size.setSpacing(10)
        lbl_ds = QLabel("Date Font Size (pt):")
        lbl_ds.setMinimumWidth(145)
        h_size.addWidget(lbl_ds)
        self.slider_date_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_date_size.setRange(10, 48)
        self.spin_date_size = QSpinBox()
        self.spin_date_size.setRange(10, 48)
        self.spin_date_size.setMinimumSize(78, 34)
        self.slider_date_size.valueChanged.connect(self.spin_date_size.setValue)
        self.spin_date_size.valueChanged.connect(self.slider_date_size.setValue)
        self.spin_date_size.valueChanged.connect(lambda: self.update_preview())
        h_size.addWidget(self.slider_date_size, 1)
        h_size.addWidget(self.spin_date_size)
        layout.addLayout(h_size)

        h_weight = QHBoxLayout()
        h_weight.setSpacing(10)
        lbl_dw = QLabel("Date Font Weight:")
        lbl_dw.setMinimumWidth(145)
        h_weight.addWidget(lbl_dw)
        self.cmb_date_weight = QComboBox()
        self.cmb_date_weight.setMinimumHeight(34)
        for name in TIME_WEIGHTS.keys():
            self.cmb_date_weight.addItem(name)
        self.cmb_date_weight.setCurrentText("Normal (400)")
        self.cmb_date_weight.currentTextChanged.connect(lambda: self.update_preview())
        h_weight.addWidget(self.cmb_date_weight, 1)
        layout.addLayout(h_weight)

        h_fmt = QHBoxLayout()
        h_fmt.setSpacing(10)
        lbl_dfm = QLabel("Date Format:")
        lbl_dfm.setMinimumWidth(145)
        h_fmt.addWidget(lbl_dfm)
        self.cmb_date_fmt = QComboBox()
        self.cmb_date_fmt.setMinimumHeight(34)
        for name in DATE_FORMATS.keys():
            self.cmb_date_fmt.addItem(name)
        self.cmb_date_fmt.currentTextChanged.connect(self.on_date_fmt_changed)
        h_fmt.addWidget(self.cmb_date_fmt, 1)
        layout.addLayout(h_fmt)

        h_custom_date_fmt = QHBoxLayout()
        h_custom_date_fmt.setSpacing(10)
        lbl_cdf = QLabel("Custom Format:")
        lbl_cdf.setMinimumWidth(145)
        h_custom_date_fmt.addWidget(lbl_cdf)
        self.txt_custom_date_fmt = QLineEdit()
        self.txt_custom_date_fmt.setMinimumHeight(34)
        self.txt_custom_date_fmt.setPlaceholderText("e.g. dddd, MMMM d or yyyy-MM-dd")
        self.txt_custom_date_fmt.textChanged.connect(lambda: self.update_preview())
        h_custom_date_fmt.addWidget(self.txt_custom_date_fmt, 1)
        layout.addLayout(h_custom_date_fmt)

        layout.addStretch()
        self.tabs.addTab(self.wrap_in_scroll_area(tab), "📅 Date & Day")

    # -----------------------------
    # Tab 3: Position & Spacing
    # -----------------------------
    def create_position_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        h_align = QHBoxLayout()
        h_align.setSpacing(10)
        lbl_al = QLabel("Clock Horizontal Alignment:")
        lbl_al.setMinimumWidth(190)
        lbl_al.setStyleSheet("font-weight: bold;")
        h_align.addWidget(lbl_al)
        self.cmb_clock_align = QComboBox()
        self.cmb_clock_align.setMinimumHeight(34)
        self.cmb_clock_align.addItems(["Center (Default)", "Left Aligned", "Right Aligned"])
        self.cmb_clock_align.currentTextChanged.connect(self.on_clock_align_changed)
        h_align.addWidget(self.cmb_clock_align, 1)
        layout.addLayout(h_align)

        preset_box = QVBoxLayout()
        preset_box.setSpacing(6)
        lbl_qp = QLabel("Quick Alignment Presets:")
        lbl_qp.setStyleSheet("color: #94a3b8; font-size: 12px;")
        preset_box.addWidget(lbl_qp)

        preset_grid = QGridLayout()
        preset_grid.setSpacing(8)
        p_buttons = [
            ("Top Center", "Center (Default)", 65, 60),
            ("Top Left", "Left Aligned", 65, 60),
            ("Top Right", "Right Aligned", 65, 60),
            ("Left Wide", "Left Aligned", 80, 100),
            ("Right Wide", "Right Aligned", 80, 100),
        ]
        for idx, (title, al, tm, hm) in enumerate(p_buttons):
            btn = QPushButton(title)
            btn.setMinimumHeight(32)
            btn.setStyleSheet("padding: 4px 12px;")
            btn.clicked.connect(lambda checked, a=al, t=tm, h=hm: self.set_position_preset(a, t, h))
            preset_grid.addWidget(btn, 0, idx)
        preset_box.addLayout(preset_grid)
        layout.addLayout(preset_box)

        h_h_margin = QHBoxLayout()
        h_h_margin.setSpacing(10)
        self.lbl_h_margin = QLabel("Distance from Screen Edge (px):")
        self.lbl_h_margin.setMinimumWidth(190)
        h_h_margin.addWidget(self.lbl_h_margin)
        self.slider_h_margin = QSlider(Qt.Orientation.Horizontal)
        self.slider_h_margin.setRange(10, 600)
        self.spin_h_margin = QSpinBox()
        self.spin_h_margin.setRange(10, 600)
        self.spin_h_margin.setMinimumSize(78, 34)
        self.slider_h_margin.valueChanged.connect(self.spin_h_margin.setValue)
        self.spin_h_margin.valueChanged.connect(self.slider_h_margin.setValue)
        self.spin_h_margin.valueChanged.connect(lambda: self.update_preview())
        h_h_margin.addWidget(self.slider_h_margin, 1)
        h_h_margin.addWidget(self.spin_h_margin)
        layout.addLayout(h_h_margin)

        h_pos = QHBoxLayout()
        h_pos.setSpacing(10)
        lbl_tm = QLabel("Distance from Top (pixels):")
        lbl_tm.setMinimumWidth(190)
        h_pos.addWidget(lbl_tm)
        self.slider_top_margin = QSlider(Qt.Orientation.Horizontal)
        self.slider_top_margin.setRange(10, 300)
        self.spin_top_margin = QSpinBox()
        self.spin_top_margin.setRange(10, 300)
        self.spin_top_margin.setMinimumSize(78, 34)
        self.slider_top_margin.valueChanged.connect(self.spin_top_margin.setValue)
        self.spin_top_margin.valueChanged.connect(self.slider_top_margin.setValue)
        self.spin_top_margin.valueChanged.connect(lambda: self.update_preview())
        h_pos.addWidget(self.slider_top_margin, 1)
        h_pos.addWidget(self.spin_top_margin)
        layout.addLayout(h_pos)

        info_lbl = QLabel(
            "Configure where your clock sits on the screen. Select Left, Center, or Right alignment, "
            "and customize horizontal and vertical distance from the screen borders."
        )
        info_lbl.setWordWrap(True)
        info_lbl.setStyleSheet("color: #888888; font-style: italic;")
        layout.addWidget(info_lbl)

        layout.addStretch()
        self.tabs.addTab(self.wrap_in_scroll_area(tab), "📍 Position")

    # -----------------------------
    # Tab 4: Custom Text / Banner
    # -----------------------------
    def create_text_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)
        layout.setContentsMargins(16, 16, 16, 16)

        self.chk_show_custom_text = QCheckBox("Show Custom Text / Banner below clock")
        self.chk_show_custom_text.toggled.connect(self.toggle_custom_text)
        layout.addWidget(self.chk_show_custom_text)

        h_txt = QHBoxLayout()
        h_txt.setSpacing(10)
        lbl_tc = QLabel("Text Content:")
        lbl_tc.setMinimumWidth(145)
        h_txt.addWidget(lbl_tc)
        self.txt_custom_text = QLineEdit()
        self.txt_custom_text.setMinimumHeight(34)
        self.txt_custom_text.setPlaceholderText("e.g. Workstation | Personal Note | Leave empty to hide")
        self.txt_custom_text.textChanged.connect(lambda: self.update_preview())
        h_txt.addWidget(self.txt_custom_text, 1)
        layout.addLayout(h_txt)

        h_font = QHBoxLayout()
        h_font.setSpacing(10)
        lbl_f = QLabel("Font Family:")
        lbl_f.setMinimumWidth(145)
        lbl_f.setStyleSheet("font-weight: bold;")
        h_font.addWidget(lbl_f)
        self.cmb_text_font = QFontComboBox()
        self.cmb_text_font.setMinimumHeight(34)
        self.cmb_text_font.currentFontChanged.connect(lambda: self.update_preview())
        h_font.addWidget(self.cmb_text_font, 1)

        self.chk_text_custom_font = QCheckBox("Use Custom Font")
        self.chk_text_custom_font.setChecked(False)
        self.chk_text_custom_font.toggled.connect(self.toggle_text_custom_font)
        h_font.addWidget(self.chk_text_custom_font)
        layout.addLayout(h_font)

        layout.addLayout(self.build_font_presets_grid(self.set_text_font))

        h_size = QHBoxLayout()
        h_size.setSpacing(10)
        lbl_ts = QLabel("Text Size (pt):")
        lbl_ts.setMinimumWidth(145)
        h_size.addWidget(lbl_ts)
        self.slider_text_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_text_size.setRange(8, 48)
        self.spin_text_size = QSpinBox()
        self.spin_text_size.setRange(8, 48)
        self.spin_text_size.setMinimumSize(78, 34)
        self.slider_text_size.valueChanged.connect(self.spin_text_size.setValue)
        self.spin_text_size.valueChanged.connect(self.slider_text_size.setValue)
        self.spin_text_size.valueChanged.connect(lambda: self.update_preview())
        h_size.addWidget(self.slider_text_size, 1)
        h_size.addWidget(self.spin_text_size)
        layout.addLayout(h_size)

        h_weight = QHBoxLayout()
        h_weight.setSpacing(10)
        lbl_tw = QLabel("Font Weight:")
        lbl_tw.setMinimumWidth(145)
        h_weight.addWidget(lbl_tw)
        self.cmb_text_weight = QComboBox()
        self.cmb_text_weight.setMinimumHeight(34)
        for name in TIME_WEIGHTS.keys():
            self.cmb_text_weight.addItem(name)
        self.cmb_text_weight.setCurrentText("Normal (400)")
        self.cmb_text_weight.currentTextChanged.connect(lambda: self.update_preview())
        h_weight.addWidget(self.cmb_text_weight, 1)
        layout.addLayout(h_weight)

        self.btn_text_color = QPushButton()
        self.txt_text_color = QLineEdit("#94a3b8")
        self.txt_text_color.textChanged.connect(self.on_text_color_text_changed)
        text_color_box = self.build_color_picker_row(
            "Font Color:",
            self.txt_text_color,
            self.btn_text_color,
            self.choose_text_color,
            self.set_text_color
        )
        layout.addLayout(text_color_box)

        h_align = QHBoxLayout()
        h_align.setSpacing(10)
        lbl_ta = QLabel("Text Alignment:")
        lbl_ta.setMinimumWidth(145)
        lbl_ta.setStyleSheet("font-weight: bold;")
        h_align.addWidget(lbl_ta)
        self.cmb_text_align = QComboBox()
        self.cmb_text_align.setMinimumHeight(34)
        self.cmb_text_align.addItems(["Inherit (Match Clock)", "Center Aligned", "Left Aligned", "Right Aligned"])
        self.cmb_text_align.currentTextChanged.connect(lambda: self.update_preview())
        h_align.addWidget(self.cmb_text_align, 1)
        layout.addLayout(h_align)

        h_margin = QHBoxLayout()
        h_margin.setSpacing(10)
        lbl_tm = QLabel("Spacing from Clock (px):")
        lbl_tm.setMinimumWidth(145)
        h_margin.addWidget(lbl_tm)
        self.slider_text_top_margin = QSlider(Qt.Orientation.Horizontal)
        self.slider_text_top_margin.setRange(0, 100)
        self.spin_text_top_margin = QSpinBox()
        self.spin_text_top_margin.setRange(0, 100)
        self.spin_text_top_margin.setMinimumSize(78, 34)
        self.slider_text_top_margin.valueChanged.connect(self.spin_text_top_margin.setValue)
        self.spin_text_top_margin.valueChanged.connect(self.slider_text_top_margin.setValue)
        self.spin_text_top_margin.valueChanged.connect(lambda: self.update_preview())
        h_margin.addWidget(self.slider_text_top_margin, 1)
        h_margin.addWidget(self.spin_text_top_margin)
        layout.addLayout(h_margin)

        layout.addStretch()
        self.tabs.addTab(self.wrap_in_scroll_area(tab), "💬 Custom Text")

    # -----------------------------
    # Tab 5: Dynamic Interaction Triggers
    # -----------------------------
    def create_interaction_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        grp_kb = QGroupBox("Keyboard Unlock Triggers")
        l_kb = QVBoxLayout(grp_kb)
        l_kb.setSpacing(12)

        h_kb_head = QHBoxLayout()
        lbl_kbh = QLabel("Active Key Triggers:")
        lbl_kbh.setStyleSheet("font-weight: bold; font-size: 13px;")
        h_kb_head.addWidget(lbl_kbh)
        h_kb_head.addStretch()

        self.btn_add_key = QPushButton("➕ Add Key")
        self.btn_add_key.setMinimumSize(120, 34)
        self.btn_add_key.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_key.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                background-color: #0284c7;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        self.btn_add_key.clicked.connect(self.prompt_add_key)
        h_kb_head.addWidget(self.btn_add_key)
        l_kb.addLayout(h_kb_head)

        self.frame_key_tray = QFrame()
        self.frame_key_tray.setMinimumHeight(52)
        self.frame_key_tray.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 8px;
            }
        """)
        self.layout_key_tags = QGridLayout(self.frame_key_tray)
        self.layout_key_tags.setContentsMargins(10, 8, 10, 8)
        self.layout_key_tags.setSpacing(8)
        l_kb.addWidget(self.frame_key_tray)

        self.chk_unlock_any_key = QCheckBox("Unlock on Any Key (type password directly without trigger)")
        self.chk_unlock_any_key.setMinimumHeight(26)
        l_kb.addWidget(self.chk_unlock_any_key)
        layout.addWidget(grp_kb)

        grp_mouse = QGroupBox("Mouse Unlock Triggers")
        l_mouse = QVBoxLayout(grp_mouse)
        l_mouse.setSpacing(12)

        h_m_head = QHBoxLayout()
        lbl_mh = QLabel("Active Mouse Actions:")
        lbl_mh.setStyleSheet("font-weight: bold; font-size: 13px;")
        h_m_head.addWidget(lbl_mh)
        h_m_head.addStretch()

        self.btn_add_mouse = QPushButton("➕ Add Mouse Action")
        self.btn_add_mouse.setMinimumSize(170, 34)
        self.btn_add_mouse.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_add_mouse.setStyleSheet("""
            QPushButton {
                font-weight: bold;
                background-color: #0284c7;
                color: #ffffff;
                border: none;
                border-radius: 6px;
                font-size: 13px;
                padding: 6px 14px;
            }
            QPushButton:hover {
                background-color: #0369a1;
            }
        """)
        self.btn_add_mouse.clicked.connect(self.prompt_add_mouse)
        h_m_head.addWidget(self.btn_add_mouse)
        l_mouse.addLayout(h_m_head)

        self.frame_mouse_tray = QFrame()
        self.frame_mouse_tray.setMinimumHeight(52)
        self.frame_mouse_tray.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 8px;
            }
        """)
        self.layout_mouse_tags = QGridLayout(self.frame_mouse_tray)
        self.layout_mouse_tags.setContentsMargins(10, 8, 10, 8)
        self.layout_mouse_tags.setSpacing(8)
        l_mouse.addWidget(self.frame_mouse_tray)

        self.chk_unlock_mouse_move = QCheckBox("Move cursor to continue to password section")
        self.chk_unlock_mouse_move.setMinimumHeight(26)
        l_mouse.addWidget(self.chk_unlock_mouse_move)
        layout.addWidget(grp_mouse)

        grp_timeout = QGroupBox("Inactivity Timeout")
        l_t = QHBoxLayout(grp_timeout)
        l_t.setContentsMargins(14, 12, 14, 12)
        l_t.setSpacing(12)

        lbl_to = QLabel("Auto-Return to Clock:")
        lbl_to.setStyleSheet("font-size: 13px;")
        l_t.addWidget(lbl_to)

        self.spin_timeout = QSpinBox()
        self.spin_timeout.setRange(0, 120)
        self.spin_timeout.setSpecialValueText("Never (0s)")
        self.spin_timeout.setMinimumSize(125, 34)
        l_t.addWidget(self.spin_timeout)

        lbl_to_hint = QLabel("(Hides password field if no keys are typed)")
        lbl_to_hint.setWordWrap(True)
        lbl_to_hint.setStyleSheet("color: #94a3b8; font-size: 12px;")
        l_t.addWidget(lbl_to_hint, 1)
        layout.addWidget(grp_timeout)

        layout.addStretch()
        self.tabs.addTab(self.wrap_in_scroll_area(tab), "🎮 Interaction")

    # -----------------------------
    # Tab 6: SDDM Breeze Login Screen
    # -----------------------------
    def create_sddm_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        lbl_intro = QLabel(
            "Customize the <b>Real System SDDM Breeze Login Screen</b> (<code>/usr/share/sddm/themes/breeze</code>).<br>"
            "The same Clock Numbers font, Date, Custom Banner, Keyboard/Mouse triggers, and "
            "smooth Windows Glide animation from your Lock Screen will be applied directly to SDDM."
        )
        lbl_intro.setWordWrap(True)
        layout.addWidget(lbl_intro)

        # Status Group
        grp_status = QGroupBox("SDDM Breeze Theme Status")
        l_stat = QVBoxLayout(grp_status)
        l_stat.setContentsMargins(14, 12, 14, 12)
        l_stat.setSpacing(8)

        self.lbl_sddm_status = QLabel("Checking SDDM status...")
        self.lbl_sddm_status.setWordWrap(True)
        l_stat.addWidget(self.lbl_sddm_status)
        layout.addWidget(grp_status)

        self.chk_customize_sddm = QCheckBox("Apply Custom Styling to SDDM Breeze Login Screen (/usr/share/sddm/themes/breeze)")
        self.chk_customize_sddm.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.chk_customize_sddm.setChecked(True)
        layout.addWidget(self.chk_customize_sddm)

        grp_look = QGroupBox("SDDM Wallpaper & Appearance (theme.conf.user)")
        l_look = QVBoxLayout(grp_look)
        l_look.setSpacing(12)

        # Background Image Picker
        h_bg = QHBoxLayout()
        h_bg.setSpacing(10)
        lbl_bg = QLabel("Background Wallpaper:")
        lbl_bg.setMinimumWidth(160)
        h_bg.addWidget(lbl_bg)

        self.txt_sddm_bg = QLineEdit()
        self.txt_sddm_bg.setMinimumHeight(34)
        self.txt_sddm_bg.setPlaceholderText("Path to any JPG, PNG, WEBP image (raw uncompressed)")
        h_bg.addWidget(self.txt_sddm_bg, 1)

        btn_browse = QPushButton("📁 Browse...")
        btn_browse.setMinimumHeight(34)
        btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse.clicked.connect(self.choose_sddm_bg_file)
        h_bg.addWidget(btn_browse)

        btn_clear = QPushButton("❌ Clear")
        btn_clear.setMinimumHeight(34)
        btn_clear.setToolTip("Restore system stock Breeze wallpaper")
        btn_clear.clicked.connect(self.clear_sddm_bg_file)
        h_bg.addWidget(btn_clear)

        btn_match_lock = QPushButton("🖼️ Match Lock Screen")
        btn_match_lock.setMinimumHeight(34)
        btn_match_lock.setToolTip("Use the wallpaper currently set in KDE Lock Screen")
        btn_match_lock.clicked.connect(self.match_lockscreen_sddm_bg)
        h_bg.addWidget(btn_match_lock)
        l_look.addLayout(h_bg)

        # Background Tint Color
        self.btn_sddm_bg_color = QPushButton()
        self.txt_sddm_bg_color = QLineEdit("#2777ff")
        self.txt_sddm_bg_color.textChanged.connect(self.on_sddm_bg_color_changed)
        l_look.addLayout(self.build_color_picker_row(
            "Background Tint Color:",
            self.txt_sddm_bg_color,
            self.btn_sddm_bg_color,
            self.choose_sddm_bg_color,
            self.set_sddm_bg_color
        ))

        # Logo Visibility
        h_logo = QHBoxLayout()
        h_logo.setSpacing(10)
        lbl_lg = QLabel("Distribution Logo:")
        lbl_lg.setMinimumWidth(160)
        h_logo.addWidget(lbl_lg)
        self.cmb_sddm_logo = QComboBox()
        self.cmb_sddm_logo.setMinimumHeight(34)
        self.cmb_sddm_logo.addItems(["hidden", "shown"])
        h_logo.addWidget(self.cmb_sddm_logo, 1)
        l_look.addLayout(h_logo)

        layout.addWidget(grp_look)

        # SDDM Quick Actions
        grp_act = QGroupBox("SDDM Actions & Reset")
        l_act = QHBoxLayout(grp_act)
        l_act.setSpacing(12)

        btn_tab_test_sddm = QPushButton("💻 Test SDDM Login Screen")
        btn_tab_test_sddm.setMinimumHeight(38)
        btn_tab_test_sddm.setStyleSheet("font-weight: bold; background-color: #0284c7; color: white; border-radius: 6px; padding: 6px 14px;")
        btn_tab_test_sddm.clicked.connect(self.test_sddm_screen)
        l_act.addWidget(btn_tab_test_sddm)

        btn_tab_reset_sddm = QPushButton("⏮️ Reset SDDM Breeze to Stock")
        btn_tab_reset_sddm.setMinimumHeight(38)
        btn_tab_reset_sddm.setStyleSheet("font-weight: bold; background-color: #7f1d1d; color: #fecaca; border: 1px solid #991b1b; border-radius: 6px; padding: 6px 14px;")
        btn_tab_reset_sddm.clicked.connect(self.reset_sddm_to_stock)
        l_act.addWidget(btn_tab_reset_sddm)

        layout.addWidget(grp_act)
        layout.addStretch()

        self.tabs.addTab(self.wrap_in_scroll_area(tab), "💻 Login Screen (Breeze)")

    # -----------------------------
    # Tab 7: Logout Screen Customization
    # -----------------------------
    def create_logout_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        lbl_intro = QLabel(
            "Customize the <b>KDE Logout / Shutdown / Reboot Screen</b> (<code>Logout.qml</code>) "
            "with top clock, banner, and uncompressed wallpaper:"
        )
        lbl_intro.setWordWrap(True)
        layout.addWidget(lbl_intro)

        self.chk_customize_logout = QCheckBox("Enable Custom Logout / Power Screen Overlay")
        self.chk_customize_logout.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.chk_customize_logout)

        grp_clock = QGroupBox("Logout Screen Clock & Greeting Banner")
        l_clk = QVBoxLayout(grp_clock)
        l_clk.setSpacing(12)

        self.chk_logout_show_clock = QCheckBox("Show Top Clock & Date on Logout Screen (uses your Time & Date styles)")
        l_clk.addWidget(self.chk_logout_show_clock)

        h_top = QHBoxLayout()
        h_top.setSpacing(10)
        lbl_ltm = QLabel("Clock Top Margin (px):")
        lbl_ltm.setMinimumWidth(160)
        h_top.addWidget(lbl_ltm)
        self.slider_logout_top = QSlider(Qt.Orientation.Horizontal)
        self.slider_logout_top.setRange(10, 200)
        self.spin_logout_top = QSpinBox()
        self.spin_logout_top.setRange(10, 200)
        self.spin_logout_top.setMinimumSize(78, 34)
        self.slider_logout_top.valueChanged.connect(self.spin_logout_top.setValue)
        self.spin_logout_top.valueChanged.connect(self.slider_logout_top.setValue)
        h_top.addWidget(self.slider_logout_top, 1)
        h_top.addWidget(self.spin_logout_top)
        l_clk.addLayout(h_top)

        h_title = QHBoxLayout()
        h_title.setSpacing(10)
        lbl_gt = QLabel("Custom Logout Banner:")
        lbl_gt.setMinimumWidth(160)
        h_title.addWidget(lbl_gt)
        self.txt_logout_title = QLineEdit()
        self.txt_logout_title.setMinimumHeight(34)
        self.txt_logout_title.setPlaceholderText("e.g. See you soon, Aayan! (Leave empty to hide)")
        h_title.addWidget(self.txt_logout_title, 1)
        l_clk.addLayout(h_title)

        h_tsz = QHBoxLayout()
        h_tsz.setSpacing(10)
        lbl_lts = QLabel("Banner Font Size (pt):")
        lbl_lts.setMinimumWidth(160)
        h_tsz.addWidget(lbl_lts)
        self.slider_logout_title_size = QSlider(Qt.Orientation.Horizontal)
        self.slider_logout_title_size.setRange(10, 42)
        self.spin_logout_title_size = QSpinBox()
        self.spin_logout_title_size.setRange(10, 42)
        self.spin_logout_title_size.setMinimumSize(78, 34)
        self.slider_logout_title_size.valueChanged.connect(self.spin_logout_title_size.setValue)
        self.spin_logout_title_size.valueChanged.connect(self.slider_logout_title_size.setValue)
        h_tsz.addWidget(self.slider_logout_title_size, 1)
        h_tsz.addWidget(self.spin_logout_title_size)
        l_clk.addLayout(h_tsz)

        self.btn_logout_title_color = QPushButton()
        self.txt_logout_title_color = QLineEdit("#f8fafc")
        self.txt_logout_title_color.textChanged.connect(self.on_logout_title_color_changed)
        l_clk.addLayout(self.build_color_picker_row(
            "Banner Text Color:",
            self.txt_logout_title_color,
            self.btn_logout_title_color,
            self.choose_logout_title_color,
            self.set_logout_title_color
        ))

        layout.addWidget(grp_clock)

        # Logout Screen Wallpaper & Appearance
        grp_bg = QGroupBox("Logout Screen Wallpaper & Background")
        l_bg = QVBoxLayout(grp_bg)
        l_bg.setSpacing(12)

        # Wallpaper Picker Row
        h_lwall = QHBoxLayout()
        h_lwall.setSpacing(10)
        lbl_lw = QLabel("Background Wallpaper:")
        lbl_lw.setMinimumWidth(160)
        h_lwall.addWidget(lbl_lw)
        self.txt_logout_wallpaper = QLineEdit()
        self.txt_logout_wallpaper.setMinimumHeight(34)
        self.txt_logout_wallpaper.setPlaceholderText("Path to any JPG, PNG, WEBP image (Leave empty to use dark backdrop)")
        h_lwall.addWidget(self.txt_logout_wallpaper, 1)

        btn_browse_lw = QPushButton("📁 Browse...")
        btn_browse_lw.setMinimumHeight(34)
        btn_browse_lw.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse_lw.clicked.connect(self.choose_logout_wallpaper_file)
        h_lwall.addWidget(btn_browse_lw)

        btn_clear_lw = QPushButton("❌ Clear")
        btn_clear_lw.setMinimumHeight(34)
        btn_clear_lw.clicked.connect(self.clear_logout_wallpaper_file)
        h_lwall.addWidget(btn_clear_lw)
        l_bg.addLayout(h_lwall)

        # Sync buttons row
        h_sync = QHBoxLayout()
        h_sync.setSpacing(10)
        lbl_spc = QLabel("")
        lbl_spc.setMinimumWidth(160)
        h_sync.addWidget(lbl_spc)

        btn_sync_login = QPushButton("🖼️ Match Login Screen Wallpaper")
        btn_sync_login.setMinimumHeight(32)
        btn_sync_login.clicked.connect(self.match_login_logout_wallpaper)
        h_sync.addWidget(btn_sync_login)

        btn_sync_lock = QPushButton("🖼️ Match Lock Screen Wallpaper")
        btn_sync_lock.setMinimumHeight(32)
        btn_sync_lock.clicked.connect(self.match_lockscreen_logout_wallpaper)
        h_sync.addWidget(btn_sync_lock)
        h_sync.addStretch()
        l_bg.addLayout(h_sync)

        # Opacity Dimming Slider
        h_op = QHBoxLayout()
        h_op.setSpacing(10)
        lbl_op = QLabel("Wallpaper Dimming (%):")
        lbl_op.setMinimumWidth(160)
        h_op.addWidget(lbl_op)
        self.slider_logout_opacity = QSlider(Qt.Orientation.Horizontal)
        self.slider_logout_opacity.setRange(0, 100)
        self.spin_logout_opacity = QSpinBox()
        self.spin_logout_opacity.setRange(0, 100)
        self.spin_logout_opacity.setMinimumSize(78, 34)
        self.slider_logout_opacity.valueChanged.connect(self.spin_logout_opacity.setValue)
        self.spin_logout_opacity.valueChanged.connect(self.slider_logout_opacity.setValue)
        h_op.addWidget(self.slider_logout_opacity, 1)
        h_op.addWidget(self.spin_logout_opacity)
        l_bg.addLayout(h_op)

        # Tint Color
        self.btn_logout_bg_color = QPushButton()
        self.txt_logout_bg_color = QLineEdit("#000000")
        self.txt_logout_bg_color.textChanged.connect(self.on_logout_bg_color_changed)
        l_bg.addLayout(self.build_color_picker_row(
            "Backdrop Dim/Tint Color:",
            self.txt_logout_bg_color,
            self.btn_logout_bg_color,
            self.choose_logout_bg_color,
            self.set_logout_bg_color
        ))

        layout.addWidget(grp_bg)

        # Quick Actions
        grp_lact = QGroupBox("Logout Actions & Preview")
        l_lact = QHBoxLayout(grp_lact)
        l_lact.setSpacing(12)

        btn_tab_test_logout = QPushButton("🚪 Test Logout Screen (Windowed)")
        btn_tab_test_logout.setMinimumHeight(38)
        btn_tab_test_logout.setStyleSheet("font-weight: bold; background-color: #0284c7; color: white; border-radius: 6px; padding: 6px 14px;")
        btn_tab_test_logout.clicked.connect(self.test_logout_screen)
        l_lact.addWidget(btn_tab_test_logout)

        btn_tab_reset_logout = QPushButton("⏮️ Reset Logout Screen to Stock")
        btn_tab_reset_logout.setMinimumHeight(38)
        btn_tab_reset_logout.setStyleSheet("font-weight: bold; background-color: #7f1d1d; color: #fecaca; border: 1px solid #991b1b; border-radius: 6px; padding: 6px 14px;")
        btn_tab_reset_logout.clicked.connect(self.reset_logout_to_stock)
        l_lact.addWidget(btn_tab_reset_logout)

        layout.addWidget(grp_lact)
        layout.addStretch()
        self.tabs.addTab(self.wrap_in_scroll_area(tab), "🚪 Logout Screen")

    def render_trigger_tags(self):
        while self.layout_key_tags.count():
            item = self.layout_key_tags.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not self.key_triggers:
            lbl_none = QLabel("No keys assigned (Click ➕ Add Key to set one)")
            lbl_none.setStyleSheet("color: #64748b; font-style: italic; border: none; background: transparent;")
            self.layout_key_tags.addWidget(lbl_none, 0, 0)
        else:
            cols = 4
            for idx, name in enumerate(self.key_triggers):
                tag = QFrame()
                tag.setObjectName("triggerTag")
                tag.setMinimumHeight(34)
                tag.setStyleSheet("""
                    QFrame#triggerTag {
                        background-color: #1e293b;
                        border: 1px solid #475569;
                        border-radius: 6px;
                    }
                """)
                t_layout = QHBoxLayout(tag)
                t_layout.setContentsMargins(10, 2, 8, 2)
                t_layout.setSpacing(8)

                lbl_name = QLabel(f"⌨️ {name}")
                lbl_name.setStyleSheet("font-weight: bold; color: #38bdf8; border: none; background: transparent; font-size: 13px;")

                btn_del = QPushButton("✕")
                btn_del.setFixedSize(22, 22)
                btn_del.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_del.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border: none;
                        color: #ef4444;
                        font-weight: bold;
                        font-size: 13px;
                    }
                    QPushButton:hover {
                        background-color: #ef4444;
                        color: white;
                        border-radius: 11px;
                    }
                """)
                btn_del.clicked.connect(lambda checked, n=name: self.remove_key_trigger(n))

                t_layout.addWidget(lbl_name)
                t_layout.addStretch()
                t_layout.addWidget(btn_del)
                self.layout_key_tags.addWidget(tag, idx // cols, idx % cols)

        while self.layout_mouse_tags.count():
            item = self.layout_mouse_tags.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        if not self.mouse_triggers:
            lbl_none_m = QLabel("No mouse actions assigned (Click ➕ Add Mouse Action to set one)")
            lbl_none_m.setStyleSheet("color: #64748b; font-style: italic; border: none; background: transparent;")
            self.layout_mouse_tags.addWidget(lbl_none_m, 0, 0)
        else:
            cols = 3
            for idx, act in enumerate(self.mouse_triggers):
                tag_m = QFrame()
                tag_m.setObjectName("triggerTagMouse")
                tag_m.setMinimumHeight(34)
                tag_m.setStyleSheet("""
                    QFrame#triggerTagMouse {
                        background-color: #1e293b;
                        border: 1px solid #475569;
                        border-radius: 6px;
                    }
                """)
                tm_layout = QHBoxLayout(tag_m)
                tm_layout.setContentsMargins(10, 2, 8, 2)
                tm_layout.setSpacing(8)

                lbl_m = QLabel(f"🖱️ {act}")
                lbl_m.setStyleSheet("font-weight: bold; color: #34d399; border: none; background: transparent; font-size: 13px;")

                btn_del_m = QPushButton("✕")
                btn_del_m.setFixedSize(22, 22)
                btn_del_m.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_del_m.setStyleSheet("""
                    QPushButton {
                        background: transparent;
                        border: none;
                        color: #ef4444;
                        font-weight: bold;
                        font-size: 13px;
                    }
                    QPushButton:hover {
                        background-color: #ef4444;
                        color: white;
                        border-radius: 11px;
                    }
                """)
                btn_del_m.clicked.connect(lambda checked, a=act: self.remove_mouse_trigger(a))

                tm_layout.addWidget(lbl_m)
                tm_layout.addStretch()
                tm_layout.addWidget(btn_del_m)
                self.layout_mouse_tags.addWidget(tag_m, idx // cols, idx % cols)

    def prompt_add_key(self):
        dlg = KeyCaptureDialog(self)
        if dlg.exec() and dlg.captured_key_name:
            if dlg.captured_key_name not in self.key_triggers:
                self.key_triggers.append(dlg.captured_key_name)
                self.key_codes.append(dlg.captured_key_code)
                self.render_trigger_tags()

    def remove_key_trigger(self, key_name):
        if key_name in self.key_triggers:
            idx = self.key_triggers.index(key_name)
            self.key_triggers.pop(idx)
            if idx < len(self.key_codes):
                self.key_codes.pop(idx)
            self.render_trigger_tags()

    def prompt_add_mouse(self):
        dlg = MouseCaptureDialog(self)
        if dlg.exec() and dlg.captured_action:
            if dlg.captured_action not in self.mouse_triggers:
                self.mouse_triggers.append(dlg.captured_action)
                self.render_trigger_tags()

    def remove_mouse_trigger(self, action_name):
        if action_name in self.mouse_triggers:
            self.mouse_triggers.remove(action_name)
            self.render_trigger_tags()

    # -----------------------------
    # Tab 7: Animations
    # -----------------------------
    def create_animations_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(14)
        layout.setContentsMargins(16, 16, 16, 16)

        grp_anim = QGroupBox("Stock Windows Lock Screen Animation")
        l_anim = QVBoxLayout(grp_anim)
        l_anim.setSpacing(12)

        self.chk_windows_glide = QCheckBox("Enable Stock Windows Glide Animation")
        self.chk_windows_glide.setStyleSheet("font-size: 15px; font-weight: bold;")
        l_anim.addWidget(self.chk_windows_glide)

        lbl_anim_desc = QLabel(
            "<b>How it works:</b><br>"
            "• When locked, your clean clock and date are displayed at the top.<br>"
            "• When you press your assigned trigger key or click, the time <b>glides smoothly upwards</b> "
            "and disappears off the top edge, while the password prompt glides in from below.<br>"
            "• Pressing <b>Escape</b> smoothly glides the clock back down into position.<br>"
            "• <i>Uncheck this box to disable the glide effect and keep the clock stationary.</i>"
        )
        lbl_anim_desc.setStyleSheet("color: #cbd5e1; font-size: 13px; line-height: 1.5; background: #1e293b; padding: 12px; border-radius: 8px;")
        lbl_anim_desc.setWordWrap(True)
        l_anim.addWidget(lbl_anim_desc)

        layout.addWidget(grp_anim)
        layout.addStretch()
        self.tabs.addTab(self.wrap_in_scroll_area(tab), "🎬 Animations")

    # -----------------------------
    # Tab 8: About Section
    # -----------------------------
    def create_about_tab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)

        lbl_author = QLabel("Made by Aayan")
        lbl_author.setStyleSheet("font-size: 24px; font-weight: bold; color: #ffffff;")
        lbl_author.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_author)

        lbl_gh = QLabel('<a href="http://github.com/theAayan0007/" style="color: #38bdf8; text-decoration: none; font-size: 16px; font-weight: bold;">http://github.com/theAayan0007/</a>')
        lbl_gh.setOpenExternalLinks(True)
        lbl_gh.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_gh)

        btn_gh = QPushButton("🌐 Visit GitHub")
        btn_gh.setMinimumSize(190, 40)
        btn_gh.setStyleSheet("""
            QPushButton {
                background-color: #0369a1;
                color: white;
                font-weight: bold;
                padding: 8px 18px;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #0284c7;
            }
        """)
        btn_gh.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("http://github.com/theAayan0007/")))
        layout.addWidget(btn_gh, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addSpacing(20)

        btn_full_reset = QPushButton("⚠️ Full Reset to Stock KDE Breeze")
        btn_full_reset.setMinimumSize(320, 44)
        btn_full_reset.setStyleSheet("""
            QPushButton {
                background-color: #b91c1c;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #dc2626;
            }
        """)
        btn_full_reset.clicked.connect(self.full_reset_to_stock)
        layout.addWidget(btn_full_reset, 0, Qt.AlignmentFlag.AlignCenter)

        layout.addStretch()
        self.tabs.addTab(self.wrap_in_scroll_area(tab), "ℹ️ About")

    def reset_to_stock_menu(self):
        """Presents clear options to reset SDDM Breeze, Lockscreen, Logout, or All back to pristine stock KDE Breeze."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Reset to Stock KDE Breeze")
        dlg.setMinimumSize(480, 360)
        dlg.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                color: #f8fafc;
            }
        """)
        layout = QVBoxLayout(dlg)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        lbl = QLabel("⏮️ Reset to Stock KDE Breeze")
        lbl.setStyleSheet("font-size: 18px; font-weight: bold; color: #38bdf8;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl)

        desc = QLabel(
            "Select which screens you want to restore back to original default stock KDE Breeze:\n"
            "(All custom top clocks, glide animations, and key triggers will be removed)"
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #94a3b8; font-size: 13px;")
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(desc)

        btn_all = QPushButton("⚠️ Reset ALL to Stock (Login + Lock + Logout)")
        btn_all.setMinimumHeight(44)
        btn_all.setStyleSheet("""
            QPushButton {
                background-color: #991b1b;
                color: white;
                font-weight: bold;
                border: 1px solid #dc2626;
                border-radius: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #b91c1c;
            }
        """)
        btn_all.clicked.connect(lambda: [dlg.accept(), self.full_reset_to_stock()])
        layout.addWidget(btn_all)

        btn_sddm = QPushButton("💻 Reset SDDM Breeze Login Screen Only")
        btn_sddm.setMinimumHeight(40)
        btn_sddm.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #38bdf8;
                border: 1px solid #334155;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0284c7;
                color: white;
            }
        """)
        btn_sddm.clicked.connect(lambda: [dlg.accept(), self.reset_sddm_to_stock()])
        layout.addWidget(btn_sddm)

        btn_lock = QPushButton("👁 Reset Lock Screen Only")
        btn_lock.setMinimumHeight(40)
        btn_lock.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        btn_lock.clicked.connect(lambda: [dlg.accept(), self.reset_lockscreen_to_stock()])
        layout.addWidget(btn_lock)

        btn_logout = QPushButton("🚪 Reset Logout Screen Only")
        btn_logout.setMinimumHeight(40)
        btn_logout.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #e2e8f0;
                border: 1px solid #334155;
                border-radius: 8px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        btn_logout.clicked.connect(lambda: [dlg.accept(), self.reset_logout_to_stock()])
        layout.addWidget(btn_logout)

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setMinimumHeight(34)
        btn_cancel.setStyleSheet("background-color: #334155; color: #e2e8f0; border-radius: 6px;")
        btn_cancel.clicked.connect(dlg.reject)
        layout.addWidget(btn_cancel)

        dlg.exec()

    def reset_sddm_to_stock(self):
        try:
            restore_system_stock_file(
                SYSTEM_SDDM_QML,
                stock_backup_path=SYSTEM_SDDM_QML + ".stock",
                user_fallback_backup=SYSTEM_SDDM_STOCK_BACKUP,
                parent_widget=self
            )
            if os.path.exists(SYSTEM_SDDM_BG_QML + ".stock"):
                try:
                    restore_system_stock_file(
                        SYSTEM_SDDM_BG_QML,
                        stock_backup_path=SYSTEM_SDDM_BG_QML + ".stock",
                        user_fallback_backup=SYSTEM_SDDM_BG_STOCK_BACKUP,
                        parent_widget=self
                    )
                except Exception:
                    pass
            if os.path.exists(SYSTEM_SDDM_THEME_CONF + ".stock"):
                try:
                    restore_system_stock_file(
                        SYSTEM_SDDM_THEME_CONF,
                        stock_backup_path=SYSTEM_SDDM_THEME_CONF + ".stock",
                        user_fallback_backup=SYSTEM_SDDM_THEME_CONF_STOCK,
                        parent_widget=self
                    )
                except Exception:
                    pass
            if os.path.exists(SYSTEM_SDDM_THEME_CONF_USER + ".stock"):
                try:
                    restore_system_stock_file(
                        SYSTEM_SDDM_THEME_CONF_USER,
                        stock_backup_path=SYSTEM_SDDM_THEME_CONF_USER + ".stock",
                        parent_widget=self
                    )
                except Exception:
                    pass
            # Remove custom wallpaper copies
            for item in os.listdir(SYSTEM_SDDM_DIR):
                if item.startswith("custom_wallpaper."):
                    try:
                        p = os.path.join(SYSTEM_SDDM_DIR, item)
                        write_system_file(p, "", stock_backup_path=None, parent_widget=self)
                        os.remove(p)
                    except Exception:
                        pass
            if os.path.exists(SDDM_QML) and os.path.exists(SYSTEM_SDDM_STOCK_BACKUP):
                shutil.copy2(SYSTEM_SDDM_STOCK_BACKUP, SDDM_QML)
            if hasattr(self, "lbl_sddm_status"):
                self.update_sddm_status_badge()
            QMessageBox.information(
                self, "Reset SDDM Breeze",
                "SDDM Breeze Login Screen (/usr/share/sddm/themes/breeze) has been successfully restored to stock KDE Breeze defaults!"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to reset SDDM Breeze:\n{e}")

    def reset_lockscreen_to_stock(self):
        try:
            if os.path.exists(LOCKSCREEN_QML):
                os.remove(LOCKSCREEN_QML)
            src_lock = "/usr/share/plasma/shells/org.kde.plasma.desktop/contents/lockscreen/LockScreenUi.qml"
            if os.path.exists(src_lock):
                shutil.copy2(src_lock, LOCKSCREEN_QML)
            QMessageBox.information(
                self, "Reset Lock Screen",
                "KDE Lock Screen has been restored to default stock behavior!"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to reset Lock Screen:\n{e}")

    def reset_logout_to_stock(self):
        try:
            if os.path.exists(LOGOUT_QML):
                os.remove(LOGOUT_QML)
            if os.path.exists(USER_LOGOUT_DIR):
                shutil.rmtree(USER_LOGOUT_DIR, ignore_errors=True)
            QMessageBox.information(
                self, "Reset Logout Screen",
                "KDE Logout Screen has been restored to default stock behavior!"
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to reset Logout Screen:\n{e}")

    def full_reset_to_stock(self):
        reply = QMessageBox.warning(
            self, "Confirm Full Reset",
            "Are you sure you want to completely reset your Lock, Login (SDDM Breeze), and Logout screens back to default stock KDE Breeze?\n\n"
            "This will restore all system files and remove custom overlays.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            errors = []
            try:
                restore_system_stock_file(
                    SYSTEM_SDDM_QML,
                    stock_backup_path=SYSTEM_SDDM_QML + ".stock",
                    user_fallback_backup=SYSTEM_SDDM_STOCK_BACKUP,
                    parent_widget=self
                )
            except Exception as e:
                errors.append(f"SDDM Breeze: {e}")

            try:
                if os.path.exists(LOCKSCREEN_OVERRIDE_DIR):
                    shutil.rmtree(LOCKSCREEN_OVERRIDE_DIR)
            except Exception as e:
                errors.append(f"Lock Screen: {e}")

            try:
                if os.path.exists(SDDM_THEME_DIR):
                    shutil.rmtree(SDDM_THEME_DIR)
            except Exception as e:
                errors.append(f"Local SDDM theme: {e}")

            try:
                if os.path.exists(CONFIG_DIR):
                    os.remove(CONFIG_FILE)
            except Exception as e:
                errors.append(f"Config: {e}")

            if errors:
                QMessageBox.warning(self, "Reset Warnings", "Reset finished with some notes:\n" + "\n".join(errors))
            else:
                QMessageBox.information(
                    self, "Reset Complete",
                    "All Lock, Login (SDDM Breeze), and Logout screens have been restored to default stock KDE Breeze!"
                )
            self.config = DEFAULT_CONFIG.copy()
            self.load_values_to_ui()
            self.update_preview()
            if hasattr(self, "lbl_sddm_status"):
                self.update_sddm_status_badge()

    # -----------------------------
    # General UI Helpers
    # -----------------------------
    def set_time_font(self, font_name):
        if font_name == "":
            self.chk_time_custom_font.setChecked(False)
        else:
            self.chk_time_custom_font.setChecked(True)
            self.cmb_time_font.setCurrentFont(QFont(font_name))
        self.update_preview()

    def set_date_font(self, font_name):
        if font_name == "":
            self.chk_date_custom_font.setChecked(False)
        else:
            self.chk_date_custom_font.setChecked(True)
            self.cmb_date_font.setCurrentFont(QFont(font_name))
        self.update_preview()

    def set_text_font(self, font_name):
        if font_name == "":
            self.chk_text_custom_font.setChecked(False)
        else:
            self.chk_text_custom_font.setChecked(True)
            self.cmb_text_font.setCurrentFont(QFont(font_name))
        self.update_preview()

    def toggle_time_custom_font(self, checked):
        self.cmb_time_font.setEnabled(checked)
        self.update_preview()

    def toggle_date_custom_font(self, checked):
        self.cmb_date_font.setEnabled(checked)
        self.update_preview()

    def toggle_text_custom_font(self, checked):
        self.cmb_text_font.setEnabled(checked)
        self.update_preview()

    def on_time_font_changed(self):
        self.update_preview()

    def toggle_custom_text(self, checked):
        self.txt_custom_text.setEnabled(checked)
        self.chk_text_custom_font.setEnabled(checked)
        self.cmb_text_font.setEnabled(checked and self.chk_text_custom_font.isChecked())
        self.slider_text_size.setEnabled(checked)
        self.spin_text_size.setEnabled(checked)
        self.cmb_text_weight.setEnabled(checked)
        self.btn_text_color.setEnabled(checked)
        self.txt_text_color.setEnabled(checked)
        self.cmb_text_align.setEnabled(checked)
        self.slider_text_top_margin.setEnabled(checked)
        self.spin_text_top_margin.setEnabled(checked)
        self.update_preview()

    def on_time_fmt_changed(self, text):
        is_custom = (text == "Custom")
        self.txt_custom_time_fmt.setEnabled(is_custom)
        if not is_custom:
            self.txt_custom_time_fmt.setText(TIME_FORMATS.get(text, ""))
        self.update_preview()

    def on_date_fmt_changed(self, text):
        is_custom = (text == "Custom")
        self.txt_custom_date_fmt.setEnabled(is_custom)
        if not is_custom:
            self.txt_custom_date_fmt.setText(DATE_FORMATS.get(text, ""))
        self.update_preview()

    def load_values_to_ui(self):
        cfg = self.config

        clock_align = cfg.get("clockAlignment", "Center")
        if clock_align == "Left":
            self.cmb_clock_align.setCurrentText("Left Aligned")
        elif clock_align == "Right":
            self.cmb_clock_align.setCurrentText("Right Aligned")
        else:
            self.cmb_clock_align.setCurrentText("Center (Default)")
        self.spin_top_margin.setValue(cfg.get("clockTopMargin", 65))
        self.spin_h_margin.setValue(cfg.get("clockHorizontalMargin", 60))
        self.on_clock_align_changed(self.cmb_clock_align.currentText())

        tf = cfg.get("timeFontFamily", "")
        if tf:
            self.chk_time_custom_font.setChecked(True)
            self.cmb_time_font.setCurrentFont(QFont(tf))
            self.cmb_time_font.setEnabled(True)
        else:
            self.chk_time_custom_font.setChecked(False)
            self.cmb_time_font.setEnabled(False)

        self.spin_time_size.setValue(cfg.get("timePointSize", 64))

        weight_str = cfg.get("timeFontWeight", "Font.Light")
        weight_name = "Light (300)"
        for k, v in TIME_WEIGHTS.items():
            if v == weight_str:
                weight_name = k
                break
        self.cmb_time_weight.setCurrentText(weight_name)

        self.set_time_color(cfg.get("timeColor", "#ffffff"))

        fmt = cfg.get("timeFormat", "h:mm ap")
        preset = cfg.get("timeFormatPreset", "12-Hour (h:mm ap)")
        if preset in TIME_FORMATS:
            self.cmb_time_fmt.setCurrentText(preset)
        else:
            self.cmb_time_fmt.setCurrentText("Custom")
        self.txt_custom_time_fmt.setText(fmt)
        self.txt_custom_time_fmt.setEnabled(self.cmb_time_fmt.currentText() == "Custom")

        self.chk_show_date.setChecked(cfg.get("showDate", True))
        df = cfg.get("dateFontFamily", "")
        if df:
            self.chk_date_custom_font.setChecked(True)
            self.cmb_date_font.setCurrentFont(QFont(df))
            self.cmb_date_font.setEnabled(True)
        else:
            self.chk_date_custom_font.setChecked(False)
            self.cmb_date_font.setEnabled(False)

        self.spin_date_size.setValue(cfg.get("datePointSize", 18))

        date_weight_str = cfg.get("dateFontWeight", "Font.Normal")
        date_weight_name = "Normal (400)"
        for k, v in TIME_WEIGHTS.items():
            if v == date_weight_str:
                date_weight_name = k
                break
        self.cmb_date_weight.setCurrentText(date_weight_name)

        self.set_date_color(cfg.get("dateColor", "#cbd5e1"))

        date_fmt = cfg.get("dateFormat", "dddd, MMMM d")
        date_preset = cfg.get("dateFormatPreset", "Full (e.g. Tuesday, November 10)")
        if date_preset in DATE_FORMATS:
            self.cmb_date_fmt.setCurrentText(date_preset)
        else:
            self.cmb_date_fmt.setCurrentText("Custom")
        self.txt_custom_date_fmt.setText(date_fmt)
        self.txt_custom_date_fmt.setEnabled(self.cmb_date_fmt.currentText() == "Custom")

        show_txt = cfg.get("showCustomText", False)
        self.chk_show_custom_text.setChecked(show_txt)
        self.txt_custom_text.setText(cfg.get("customText", ""))
        self.spin_text_size.setValue(cfg.get("customTextPointSize", 13))

        ctf = cfg.get("customTextFontFamily", "")
        if ctf:
            self.chk_text_custom_font.setChecked(True)
            self.cmb_text_font.setCurrentFont(QFont(ctf))
            self.cmb_text_font.setEnabled(True)
        else:
            self.chk_text_custom_font.setChecked(False)
            self.cmb_text_font.setEnabled(False)

        text_weight_str = cfg.get("customTextFontWeight", "Font.Normal")
        text_weight_name = "Normal (400)"
        for k, v in TIME_WEIGHTS.items():
            if v == text_weight_str:
                text_weight_name = k
                break
        self.cmb_text_weight.setCurrentText(text_weight_name)

        self.set_text_color(cfg.get("customTextColor", "#94a3b8"))

        text_align = cfg.get("customTextAlignment", "Inherit")
        if text_align == "Left":
            self.cmb_text_align.setCurrentText("Left Aligned")
        elif text_align == "Right":
            self.cmb_text_align.setCurrentText("Right Aligned")
        elif text_align == "Center":
            self.cmb_text_align.setCurrentText("Center Aligned")
        else:
            self.cmb_text_align.setCurrentText("Inherit (Match Clock)")

        self.spin_text_top_margin.setValue(cfg.get("customTextTopMargin", 12))
        self.toggle_custom_text(show_txt)

        self.chk_unlock_any_key.setChecked(cfg.get("unlockOnAnyKey", False))
        self.chk_unlock_mouse_move.setChecked(cfg.get("unlockOnMouseMove", False))
        self.spin_timeout.setValue(cfg.get("idleTimeoutSeconds", 15))
        self.render_trigger_tags()

        self.chk_windows_glide.setChecked(cfg.get("enableWindowsGlideAnimation", True))

        # Logout Screen settings
        self.chk_customize_logout.setChecked(cfg.get("customizeLogoutScreen", True))
        self.chk_logout_show_clock.setChecked(cfg.get("logoutShowClock", True))
        self.spin_logout_top.setValue(cfg.get("logoutClockTopMargin", 45))
        self.txt_logout_title.setText(cfg.get("logoutCustomTitle", ""))
        self.spin_logout_title_size.setValue(cfg.get("logoutTitlePointSize", 18))
        self.set_logout_title_color(cfg.get("logoutTitleColor", "#f8fafc"))
        self.txt_logout_wallpaper.setText(cfg.get("logoutWallpaper", ""))
        self.set_logout_bg_color(cfg.get("logoutBgColor", "#000000"))
        self.spin_logout_opacity.setValue(cfg.get("logoutBgOpacity", 35))

        # SDDM Login Screen (Breeze) settings
        if hasattr(self, "chk_customize_sddm"):
            self.chk_customize_sddm.setChecked(cfg.get("customizeSddmScreen", True))
        if hasattr(self, "txt_sddm_bg"):
            self.txt_sddm_bg.setText(cfg.get("sddmBackground", ""))
        if hasattr(self, "txt_sddm_bg_color"):
            self.set_sddm_bg_color(cfg.get("sddmBackgroundColor", "#0f172a"))
        if hasattr(self, "cmb_sddm_logo"):
            self.cmb_sddm_logo.setCurrentText(cfg.get("sddmShowLogo", "hidden"))
        if hasattr(self, "lbl_sddm_status"):
            self.update_sddm_status_badge()

    def update_preview(self):
        now = datetime.now()

        t_fmt = self.txt_custom_time_fmt.text() if hasattr(self, 'txt_custom_time_fmt') else ""
        if not t_fmt:
            time_str = now.strftime("%I:%M %p").lstrip("0")
        else:
            py_fmt = t_fmt.replace("hh", "%I").replace("h", "%-I")\
                          .replace("HH", "%H").replace("H", "%-H")\
                          .replace("mm", "%M").replace("m", "%-M")\
                          .replace("ss", "%S").replace("s", "%-S")\
                          .replace("ap", "%p").replace("AP", "%p")
            try:
                time_str = now.strftime(py_fmt)
            except Exception:
                time_str = now.strftime("%I:%M %p").lstrip("0")

        self.lbl_prev_time.setText(time_str)

        if hasattr(self, 'chk_time_custom_font') and self.chk_time_custom_font.isChecked():
            font_time = QFont(self.cmb_time_font.currentFont().family())
            fam_name = self.cmb_time_font.currentFont().family()
        else:
            font_time = QFont()
            fam_name = "System Default"

        if hasattr(self, 'lbl_time_digits_sample'):
            sample_font = QFont(font_time)
            sample_font.setPointSize(14)
            self.lbl_time_digits_sample.setFont(sample_font)
            self.lbl_time_digits_sample.setText(f"Numbers Font [{fam_name}]:  0 1 2 3 4 5 6 7 8 9 :")

        preview_pt_size = max(18, int(self.spin_time_size.value() * 0.50)) if hasattr(self, 'spin_time_size') else 32
        font_time.setPointSize(preview_pt_size)

        weight_str = self.cmb_time_weight.currentText() if hasattr(self, 'cmb_time_weight') else "Light (300)"
        font_time.setWeight(WEIGHT_MAP.get(weight_str, QFont.Weight.Light))
        self.lbl_prev_time.setFont(font_time)

        time_color = self.txt_time_color.text().strip() if hasattr(self, 'txt_time_color') and QColor(self.txt_time_color.text().strip()).isValid() else "#ffffff"
        self.lbl_prev_time.setStyleSheet(f"color: {time_color}; background: transparent; border: none;")

        align_text = self.cmb_clock_align.currentText() if hasattr(self, 'cmb_clock_align') else "Center (Default)"
        if "Left" in align_text:
            clock_align = "Left"
            h_align_flag = Qt.AlignmentFlag.AlignLeft
        elif "Right" in align_text:
            clock_align = "Right"
            h_align_flag = Qt.AlignmentFlag.AlignRight
        else:
            clock_align = "Center"
            h_align_flag = Qt.AlignmentFlag.AlignHCenter

        if hasattr(self, 'box_layout'):
            self.box_layout.setAlignment(h_align_flag | Qt.AlignmentFlag.AlignVCenter)
            hm = int(self.spin_h_margin.value() * 0.35) if hasattr(self, 'spin_h_margin') else 20
            hm = max(15, min(120, hm))
            if clock_align == "Left":
                self.box_layout.setContentsMargins(hm, 8, 15, 8)
            elif clock_align == "Right":
                self.box_layout.setContentsMargins(15, 8, hm, 8)
            else:
                self.box_layout.setContentsMargins(20, 8, 20, 8)

        self.lbl_prev_time.setAlignment(h_align_flag)
        self.lbl_prev_date.setAlignment(h_align_flag)

        if hasattr(self, 'chk_show_date') and self.chk_show_date.isChecked():
            self.lbl_prev_date.show()
            d_fmt = self.txt_custom_date_fmt.text() if hasattr(self, 'txt_custom_date_fmt') else ""
            if not d_fmt:
                date_str = now.strftime("%A, %B %-d")
            else:
                py_d_fmt = d_fmt.replace("dddd", "%A").replace("ddd", "%a")\
                                .replace("MMMM", "%B").replace("MMM", "%b")\
                                .replace("yyyy", "%Y").replace("yy", "%y")\
                                .replace("dd", "%d").replace("d", "%-d")\
                                .replace("MM", "%m").replace("M", "%-m")
                try:
                    date_str = now.strftime(py_d_fmt)
                except Exception:
                    date_str = now.strftime("%A, %B %-d")

            self.lbl_prev_date.setText(date_str)

            if hasattr(self, 'chk_date_custom_font') and self.chk_date_custom_font.isChecked():
                font_date = QFont(self.cmb_date_font.currentFont().family())
            else:
                font_date = QFont()
            font_date.setPointSize(max(10, int(self.spin_date_size.value() * 0.65)) if hasattr(self, 'spin_date_size') else 13)

            date_weight_str = self.cmb_date_weight.currentText() if hasattr(self, 'cmb_date_weight') else "Normal (400)"
            font_date.setWeight(WEIGHT_MAP.get(date_weight_str, QFont.Weight.Normal))
            self.lbl_prev_date.setFont(font_date)

            date_color = self.txt_date_color.text().strip() if hasattr(self, 'txt_date_color') and QColor(self.txt_date_color.text().strip()).isValid() else "#cbd5e1"
            self.lbl_prev_date.setStyleSheet(f"color: {date_color}; background: transparent; border: none;")
        else:
            self.lbl_prev_date.hide()

        if hasattr(self, 'chk_show_custom_text') and self.chk_show_custom_text.isChecked() and self.txt_custom_text.text().strip():
            self.lbl_prev_text.show()
            self.lbl_prev_text.setText(self.txt_custom_text.text())

            if hasattr(self, 'chk_text_custom_font') and self.chk_text_custom_font.isChecked():
                f_text = QFont(self.cmb_text_font.currentFont().family())
            else:
                f_text = QFont()
            f_text.setPointSize(self.spin_text_size.value() if hasattr(self, 'spin_text_size') else 12)

            text_weight_str = self.cmb_text_weight.currentText() if hasattr(self, 'cmb_text_weight') else "Normal (400)"
            f_text.setWeight(WEIGHT_MAP.get(text_weight_str, QFont.Weight.Normal))
            self.lbl_prev_text.setFont(f_text)

            txt_col = self.txt_text_color.text().strip() if hasattr(self, 'txt_text_color') and QColor(self.txt_text_color.text().strip()).isValid() else "#94a3b8"
            tm = self.spin_text_top_margin.value() if hasattr(self, 'spin_text_top_margin') else 12
            self.lbl_prev_text.setStyleSheet(f"color: {txt_col}; margin-top: {max(2, int(tm * 0.4))}px; background: transparent; border: none;")

            txt_align_opt = self.cmb_text_align.currentText() if hasattr(self, 'cmb_text_align') else "Inherit (Match Clock)"
            if "Left" in txt_align_opt:
                self.lbl_prev_text.setAlignment(Qt.AlignmentFlag.AlignLeft)
            elif "Right" in txt_align_opt:
                self.lbl_prev_text.setAlignment(Qt.AlignmentFlag.AlignRight)
            elif "Center" in txt_align_opt:
                self.lbl_prev_text.setAlignment(Qt.AlignmentFlag.AlignHCenter)
            else:
                self.lbl_prev_text.setAlignment(h_align_flag)
        else:
            self.lbl_prev_text.hide()

    def gather_config_from_ui(self):
        time_family = self.cmb_time_font.currentFont().family() if self.chk_time_custom_font.isChecked() else ""
        date_family = self.cmb_date_font.currentFont().family() if self.chk_date_custom_font.isChecked() else ""
        text_family = self.cmb_text_font.currentFont().family() if (hasattr(self, 'chk_text_custom_font') and self.chk_text_custom_font.isChecked()) else ""

        align_txt = self.cmb_clock_align.currentText()
        if "Left" in align_txt:
            clock_align = "Left"
        elif "Right" in align_txt:
            clock_align = "Right"
        else:
            clock_align = "Center"

        txt_align_txt = self.cmb_text_align.currentText()
        if "Left" in txt_align_txt:
            text_align = "Left"
        elif "Right" in txt_align_txt:
            text_align = "Right"
        elif "Center" in txt_align_txt:
            text_align = "Center"
        else:
            text_align = "Inherit"

        cfg = {
            "clockAlignment": clock_align,
            "clockTopMargin": self.spin_top_margin.value(),
            "clockHorizontalMargin": self.spin_h_margin.value() if hasattr(self, 'spin_h_margin') else 60,

            "timePointSize": self.spin_time_size.value(),
            "timeFontFamily": time_family,
            "timeFontWeight": TIME_WEIGHTS.get(self.cmb_time_weight.currentText(), "Font.Light"),
            "timeColor": self.txt_time_color.text().strip() if hasattr(self, 'txt_time_color') else "#ffffff",
            "timeFormatPreset": self.cmb_time_fmt.currentText(),
            "timeFormat": self.txt_custom_time_fmt.text().strip(),

            "showDate": self.chk_show_date.isChecked(),
            "datePointSize": self.spin_date_size.value(),
            "dateFontFamily": date_family,
            "dateFontWeight": TIME_WEIGHTS.get(self.cmb_date_weight.currentText(), "Font.Normal"),
            "dateColor": self.txt_date_color.text().strip() if hasattr(self, 'txt_date_color') else "#cbd5e1",
            "dateFormatPreset": self.cmb_date_fmt.currentText(),
            "dateFormat": self.txt_custom_date_fmt.text().strip(),

            "showCustomText": self.chk_show_custom_text.isChecked(),
            "customText": self.txt_custom_text.text(),
            "customTextPointSize": self.spin_text_size.value(),
            "customTextFontFamily": text_family,
            "customTextFontWeight": TIME_WEIGHTS.get(self.cmb_text_weight.currentText(), "Font.Normal"),
            "customTextColor": self.txt_text_color.text().strip() if hasattr(self, 'txt_text_color') else "#94a3b8",
            "customTextAlignment": text_align,
            "customTextTopMargin": self.spin_text_top_margin.value(),

            "unlockKeyNames": self.key_triggers,
            "unlockKeyCodes": self.key_codes,
            "unlockMouseButtons": self.mouse_triggers,
            "unlockOnAnyKey": self.chk_unlock_any_key.isChecked(),
            "unlockOnMouseMove": self.chk_unlock_mouse_move.isChecked(),
            "idleTimeoutSeconds": self.spin_timeout.value(),
            "keepClockVisibleWhenUnlocking": not self.chk_windows_glide.isChecked(),

            "enableWindowsGlideAnimation": self.chk_windows_glide.isChecked(),

            # Logout Screen
            "customizeLogoutScreen": self.chk_customize_logout.isChecked(),
            "logoutShowClock": self.chk_logout_show_clock.isChecked(),
            "logoutClockTopMargin": self.spin_logout_top.value(),
            "logoutCustomTitle": self.txt_logout_title.text().strip(),
            "logoutTitlePointSize": self.spin_logout_title_size.value(),
            "logoutTitleColor": self.txt_logout_title_color.text().strip() or "#f8fafc",
            "logoutWallpaper": self.txt_logout_wallpaper.text().strip() if hasattr(self, "txt_logout_wallpaper") else "",
            "logoutBgColor": self.txt_logout_bg_color.text().strip() or "#000000",
            "logoutBgOpacity": self.spin_logout_opacity.value(),

            # SDDM Breeze Login Screen
            "customizeSddmScreen": self.chk_customize_sddm.isChecked() if hasattr(self, "chk_customize_sddm") else True,
            "sddmBackground": self.txt_sddm_bg.text().strip() if hasattr(self, "txt_sddm_bg") else "",
            "sddmBackgroundColor": self.txt_sddm_bg_color.text().strip() if hasattr(self, "txt_sddm_bg_color") else "#0f172a",
            "sddmShowLogo": self.cmb_sddm_logo.currentText() if hasattr(self, "cmb_sddm_logo") else "hidden",
        }
        return cfg

    def is_qml_patched(self, path):
        if not os.path.exists(path):
            return False
        try:
            with open(path, "r") as f:
                content = f.read()
            return ("id: customConfig" in content and "id: topClock" in content)
        except Exception:
            return False

    def is_logout_patched(self, path):
        if not os.path.exists(path):
            return False
        try:
            with open(path, "r") as f:
                content = f.read()
            return ("id: logoutCustomConfig" in content and "id: logoutTopClock" in content)
        except Exception:
            return False

    def ensure_theme_installed(self):
        # 1. KDE Shell Overlay (LockScreen + Logout)
        if not os.path.exists(LOCKSCREEN_OVERRIDE_DIR):
            os.makedirs(os.path.dirname(LOCKSCREEN_OVERRIDE_DIR), exist_ok=True)
            if os.path.exists("/usr/share/plasma/shells/org.kde.plasma.desktop"):
                shutil.copytree("/usr/share/plasma/shells/org.kde.plasma.desktop", LOCKSCREEN_OVERRIDE_DIR)

        if not self.is_qml_patched(LOCKSCREEN_QML):
            src_lock = "/usr/share/plasma/shells/org.kde.plasma.desktop/contents/lockscreen/LockScreenUi.qml"
            if os.path.exists(src_lock):
                os.makedirs(os.path.dirname(LOCKSCREEN_QML), exist_ok=True)
                build_lockscreen(src_lock, LOCKSCREEN_QML, is_sddm=False)

        if not self.is_logout_patched(LOGOUT_QML):
            if os.path.exists(SYSTEM_LOGOUT_QML):
                os.makedirs(os.path.dirname(LOGOUT_QML), exist_ok=True)
                build_logout_screen(SYSTEM_LOGOUT_QML, LOGOUT_QML)

        # 2. SDDM Breeze Stock Backup & Local Overlay
        if not os.path.exists(SYSTEM_SDDM_STOCK_BACKUP):
            os.makedirs(os.path.dirname(SYSTEM_SDDM_STOCK_BACKUP), exist_ok=True)
            if os.path.exists(SYSTEM_SDDM_QML) and not self.is_qml_patched(SYSTEM_SDDM_QML):
                shutil.copy2(SYSTEM_SDDM_QML, SYSTEM_SDDM_STOCK_BACKUP)

        if not os.path.exists(SDDM_THEME_DIR):
            os.makedirs(SDDM_THEME_DIR, exist_ok=True)
            if os.path.exists(SYSTEM_SDDM_DIR):
                for item in os.listdir(SYSTEM_SDDM_DIR):
                    s = os.path.join(SYSTEM_SDDM_DIR, item)
                    d = os.path.join(SDDM_THEME_DIR, item)
                    if os.path.isdir(s):
                        if not os.path.exists(d):
                            shutil.copytree(s, d)
                    else:
                        shutil.copy2(s, d)

        if not self.is_qml_patched(SDDM_QML):
            src_sddm = SYSTEM_SDDM_STOCK_BACKUP if os.path.exists(SYSTEM_SDDM_STOCK_BACKUP) else SYSTEM_SDDM_QML
            if os.path.exists(src_sddm):
                os.makedirs(os.path.dirname(SDDM_QML), exist_ok=True)
                build_lockscreen(src_sddm, SDDM_QML, is_sddm=True)

    def write_system_sddm_config(self, cfg):
        """Builds and installs custom top clock, uncompressed wallpaper & animations directly to /usr/share/sddm/themes/breeze/Main.qml and Background.qml"""
        src_stock = SYSTEM_SDDM_STOCK_BACKUP if os.path.exists(SYSTEM_SDDM_STOCK_BACKUP) else (
            SYSTEM_SDDM_QML + ".stock" if os.path.exists(SYSTEM_SDDM_QML + ".stock") else SYSTEM_SDDM_QML
        )
        temp_qml = os.path.expanduser("~/.cache/kde-lockscreen-config/sddm_breeze_patched.qml")
        os.makedirs(os.path.dirname(temp_qml), exist_ok=True)
        build_lockscreen(src_stock, temp_qml, is_sddm=True)

        # Handle custom wallpaper installation
        user_bg = cfg.get("sddmBackground", "").strip()
        system_bg_installed = ""
        if user_bg and os.path.isfile(user_bg):
            try:
                system_bg_installed = copy_image_to_system_sddm(user_bg, parent_widget=self)
                cfg["sddmBackgroundSys"] = system_bg_installed
            except Exception as e:
                print(f"Warning: could not copy wallpaper to SDDM theme dir: {e}")

        # Ensure Background.qml uses uncompressed full resolution Image
        try:
            patch_system_sddm_background_qml(parent_widget=self)
        except Exception as e:
            print(f"Warning: patch Background.qml: {e}")

        self.write_qml_config(temp_qml, cfg)

        with open(temp_qml, "r", encoding="utf-8") as f:
            final_content = f.read()

        write_system_file(SYSTEM_SDDM_QML, final_content, stock_backup_path=SYSTEM_SDDM_QML + ".stock", parent_widget=self)

    def write_sddm_theme_conf(self, cfg):
        """Updates theme.conf and theme.conf.user in /usr/share/sddm/themes/breeze with custom wallpaper and colors"""
        user_bg = cfg.get("sddmBackground", "").strip()
        sys_bg = cfg.get("sddmBackgroundSys", "")
        bg_col = cfg.get("sddmBackgroundColor", "#0f172a").strip()
        logo_opt = cfg.get("sddmShowLogo", "hidden").strip()

        # Determine effective wallpaper path for theme.conf
        effective_bg = ""
        if sys_bg and os.path.exists(sys_bg):
            effective_bg = sys_bg
        elif user_bg and os.path.exists(user_bg):
            effective_bg = user_bg
        else:
            if os.path.exists("/usr/share/wallpapers/Next/contents/images/5120x2880.png"):
                effective_bg = "/usr/share/wallpapers/Next/contents/images/5120x2880.png"
            elif os.path.exists("/usr/share/desktop-base/kali-theme/login/background"):
                effective_bg = "/usr/share/desktop-base/kali-theme/login/background"

        lines = ["[General]"]
        lines.append("type=image")
        if effective_bg:
            lines.append(f"background={effective_bg}")
        lines.append(f"color={bg_col or '#0f172a'}")
        lines.append(f"showlogo={logo_opt or 'hidden'}")
        lines.append("logo=/usr/share/sddm/themes/breeze/default-logo.svg")
        lines.append("fontSize=10")
        lines.append("showClock=true")
        lines.append("needsFullUserModel=false")
        lines.append("")

        conf_content = "\n".join(lines)
        try:
            write_system_file(SYSTEM_SDDM_THEME_CONF, conf_content, stock_backup_path=SYSTEM_SDDM_THEME_CONF + ".stock", parent_widget=self)
            write_system_file(SYSTEM_SDDM_THEME_CONF_USER, conf_content, stock_backup_path=SYSTEM_SDDM_THEME_CONF_USER + ".stock", parent_widget=self)
        except Exception as e:
            print(f"SDDM theme.conf update note: {e}")

    def write_logout_qml_config(self, qml_path, cfg):
        src_logout = SYSTEM_LOGOUT_QML
        if not os.path.exists(src_logout):
            return

        # Ensure look-and-feel package files exist in user override
        user_laf_dir = os.path.dirname(os.path.dirname(qml_path))
        src_laf_dir = os.path.dirname(os.path.dirname(src_logout))
        os.makedirs(os.path.join(user_laf_dir, "contents/logout"), exist_ok=True)
        meta_src = os.path.join(src_laf_dir, "metadata.json")
        meta_dst = os.path.join(user_laf_dir, "metadata.json")
        if os.path.exists(meta_src) and not os.path.exists(meta_dst):
            try:
                shutil.copy2(meta_src, meta_dst)
            except Exception:
                pass

        for supp_file in ["LogoutButton.qml", "timer.js"]:
            s_f = os.path.join(src_laf_dir, "contents/logout", supp_file)
            d_f = os.path.join(user_laf_dir, "contents/logout", supp_file)
            if os.path.exists(s_f) and not os.path.exists(d_f):
                try:
                    shutil.copy2(s_f, d_f)
                except Exception:
                    pass

        # Build patched version
        build_logout_screen(src_logout, qml_path)

        with open(qml_path, "r", encoding="utf-8") as f:
            content = f.read()

        escaped_title = cfg.get("logoutCustomTitle", "").replace('\\', '\\\\').replace('"', '\\"')
        escaped_wall = cfg.get("logoutWallpaper", "").replace('\\', '\\\\').replace('"', '\\"')
        bg_opacity = round(cfg.get("logoutBgOpacity", 35) / 100.0, 2)

        new_logout_cfg = f"""    QtObject {{
        id: logoutCustomConfig
        property bool enabled: {str(cfg.get('customizeLogoutScreen', True)).lower()}
        property bool showClock: {str(cfg.get('logoutShowClock', True)).lower()}
        property int clockTopMargin: {cfg.get('logoutClockTopMargin', 45)}
        property string clockAlignment: "{cfg.get('clockAlignment', 'Center')}"
        property int clockHorizontalMargin: {cfg.get('clockHorizontalMargin', 60)}
        property int timePointSize: {max(24, int(cfg['timePointSize'] * 0.85))}
        property string timeFontFamily: "{cfg['timeFontFamily']}"
        property int timeFontWeight: {cfg['timeFontWeight']}
        property string timeColor: "{cfg.get('timeColor', '#ffffff')}"
        property string timeFormat: "{cfg['timeFormat']}"
        property bool showDate: {str(cfg['showDate']).lower()}
        property int datePointSize: {cfg['datePointSize']}
        property string dateFontFamily: "{cfg['dateFontFamily']}"
        property int dateFontWeight: {cfg.get('dateFontWeight', 'Font.Normal')}
        property string dateColor: "{cfg.get('dateColor', '#cbd5e1')}"
        property string dateFormat: "{cfg['dateFormat']}"
        property string customTitle: "{escaped_title}"
        property string titleColor: "{cfg.get('logoutTitleColor', '#f8fafc')}"
        property int titlePointSize: {cfg.get('logoutTitlePointSize', 18)}
        property string wallpaperPath: "{escaped_wall}"
        property double bgOpacity: {bg_opacity}
        property string bgColor: "{cfg.get('logoutBgColor', '#000000')}"
        property bool showCountdown: true
    }}"""

        content, count = re.subn(
            r'QtObject\s*\{\s*id:\s*logoutCustomConfig.*?^\s*\}',
            new_logout_cfg,
            content,
            flags=re.MULTILINE | re.DOTALL
        )
        if count > 0:
            with open(qml_path, "w", encoding="utf-8") as f:
                f.write(content)

    def apply_settings(self):
        self.config = self.gather_config_from_ui()
        self.save_config_to_file()
        try:
            self.ensure_theme_installed()
        except Exception as e:
            QMessageBox.warning(self, "Warning", f"Could not initialize theme files:\n{e}")

        updated_targets = []
        errors = []

        # 1. Update KDE Lock Screen
        if os.path.exists(LOCKSCREEN_QML):
            try:
                self.write_qml_config(LOCKSCREEN_QML, self.config)
                updated_targets.append("KDE Lock Screen")
            except Exception as e:
                errors.append(f"Lock Screen: {e}")

        # 2. Update System SDDM Breeze theme (/usr/share/sddm/themes/breeze)
        if self.config.get("customizeSddmScreen", True):
            try:
                self.write_system_sddm_config(self.config)
                updated_targets.append("SDDM Breeze Login Screen (/usr/share/sddm/themes/breeze)")
            except Exception as e:
                errors.append(f"SDDM Breeze: {e}")

            # Also update local SDDM theme copy
            if os.path.exists(SDDM_QML):
                try:
                    self.write_qml_config(SDDM_QML, self.config)
                except Exception:
                    pass

            # Update SDDM theme.conf.user if custom background or color set
            try:
                self.write_sddm_theme_conf(self.config)
            except Exception as e:
                print(f"SDDM theme.conf.user note: {e}")
        else:
            # If disabled by user, restore stock
            try:
                if self.is_qml_patched(SYSTEM_SDDM_QML):
                    restore_system_stock_file(SYSTEM_SDDM_QML, stock_backup_path=SYSTEM_SDDM_QML + ".stock",
                                              user_fallback_backup=SYSTEM_SDDM_STOCK_BACKUP, parent_widget=self)
                    updated_targets.append("SDDM Breeze (Restored to Stock)")
            except Exception as e:
                errors.append(f"SDDM Restore: {e}")

        # 3. Update Logout Screen
        if self.config.get("customizeLogoutScreen", True):
            try:
                self.write_logout_qml_config(LOGOUT_QML, self.config)
                updated_targets.append("KDE Logout / Power Screen")
            except Exception as e:
                errors.append(f"Logout Screen: {e}")

        if hasattr(self, "lbl_sddm_status"):
            self.update_sddm_status_badge()

        if updated_targets:
            msg = "Settings successfully applied to:\n• " + "\n• ".join(updated_targets) + "\n\n"
            msg += f"• Clock Alignment: {self.config.get('clockAlignment', 'Center')}\n"
            msg += f"• Time Color: {self.config.get('timeColor', '#ffffff')}\n"
            msg += f"• Windows Glide Animation: {'Enabled' if self.config.get('enableWindowsGlideAnimation', True) else 'Disabled'}\n"
            msg += f"• Active Key Triggers: {', '.join(self.config['unlockKeyNames']) or 'None'}\n"
            msg += f"• Active Mouse Triggers: {', '.join(self.config['unlockMouseButtons']) or 'None'}\n\n"
            msg += "Use 'Test Login Screen', 'Test Lock Screen', or 'Test Logout Screen' below to preview live."
            if errors:
                msg += "\n\nWarnings:\n" + "\n".join(errors)
            QMessageBox.information(self, "Settings Applied", msg)
        else:
            QMessageBox.critical(self, "Error", "Failed to update screen files:\n" + "\n".join(errors))

    def write_qml_config(self, qml_path, cfg):
        if not self.is_qml_patched(qml_path):
            is_sddm = (qml_path == SDDM_QML or qml_path == SYSTEM_SDDM_QML or "sddm" in qml_path)
            src = SYSTEM_SDDM_STOCK_BACKUP if (is_sddm and os.path.exists(SYSTEM_SDDM_STOCK_BACKUP)) else (
                "/usr/share/sddm/themes/breeze/Main.qml" if is_sddm else "/usr/share/plasma/shells/org.kde.plasma.desktop/contents/lockscreen/LockScreenUi.qml"
            )
            build_lockscreen(src, qml_path, is_sddm=is_sddm)

        with open(qml_path, "r") as f:
            content = f.read()

        key_codes_json = json.dumps(cfg.get("unlockKeyCodes", [32]))
        key_names_json = json.dumps(cfg.get("unlockKeyNames", ["Space"]))
        mouse_btns_json = json.dumps(cfg.get("unlockMouseButtons", ["Left Click"]))
        escaped_custom_text = cfg.get('customText', '').replace('\\', '\\\\').replace('"', '\\"')

        new_config_block = f"""    QtObject {{
        id: customConfig
        property string clockAlignment: "{cfg.get('clockAlignment', 'Center')}"
        property int clockTopMargin: {cfg['clockTopMargin']}
        property int clockHorizontalMargin: {cfg.get('clockHorizontalMargin', 60)}
        property int timePointSize: {cfg['timePointSize']}
        property int datePointSize: {cfg['datePointSize']}
        property int hintPointSize: {cfg['customTextPointSize']}
        property string timeFormat: "{cfg['timeFormat']}"
        property string dateFormat: "{cfg['dateFormat']}"
        property bool showDate: {str(cfg['showDate']).lower()}
        property string timeFontFamily: "{cfg['timeFontFamily']}"
        property string dateFontFamily: "{cfg['dateFontFamily']}"
        property int timeFontWeight: {cfg['timeFontWeight']}
        property int dateFontWeight: {cfg.get('dateFontWeight', 'Font.Normal')}
        property string timeColor: "{cfg.get('timeColor', '#ffffff')}"
        property string dateColor: "{cfg.get('dateColor', '#cbd5e1')}"
        property bool showUnlockHint: {str(cfg['showCustomText']).lower()}
        property string unlockHintText: "{escaped_custom_text}"
        property string hintFontFamily: "{cfg.get('customTextFontFamily', '')}"
        property int hintFontWeight: {cfg.get('customTextFontWeight', 'Font.Normal')}
        property string hintColor: "{cfg.get('customTextColor', '#94a3b8')}"
        property string hintAlignment: "{cfg.get('customTextAlignment', 'Inherit')}"
        property int hintTopMargin: {cfg.get('customTextTopMargin', 12)}

        // Dynamic Triggers
        property var unlockKeyCodes: {key_codes_json}
        property var unlockKeyNames: {key_names_json}
        property var unlockMouseButtons: {mouse_btns_json}
        property bool unlockOnAnyKey: {str(cfg.get('unlockOnAnyKey', False)).lower()}
        property bool unlockOnMouseMove: {str(cfg.get('unlockOnMouseMove', False)).lower()}
        property int idleTimeoutSeconds: {cfg['idleTimeoutSeconds']}
        property bool keepClockVisibleWhenUnlocking: {str(cfg['keepClockVisibleWhenUnlocking']).lower()}

        // Animations
        property bool enableWindowsGlideAnimation: {str(cfg['enableWindowsGlideAnimation']).lower()}

        // Wallpaper & Fallback Tint
        property string customWallpaper: "{cfg.get('sddmBackgroundSys', cfg.get('sddmBackground', ''))}"
        property string wallpaperColor: "{cfg.get('sddmBackgroundColor', '#0f172a')}"
    }}"""

        content, count = re.subn(
            r'QtObject\s*\{\s*id:\s*customConfig.*?^\s*\}',
            new_config_block,
            content,
            flags=re.MULTILINE | re.DOTALL
        )
        if count == 0:
            raise RuntimeError(f"Could not inject customConfig into {qml_path}")

        with open(qml_path, "w") as f:
            f.write(content)

    def test_sddm_screen(self):
        try:
            self.config = self.gather_config_from_ui()
            self.save_config_to_file()

            target_theme = SYSTEM_SDDM_DIR if os.path.exists(SYSTEM_SDDM_DIR) else SDDM_THEME_DIR

            greeter_cmds = [
                ["sddm-greeter-qt6", "--test-mode", "--theme", target_theme],
                ["/usr/bin/sddm-greeter-qt6", "--test-mode", "--theme", target_theme],
                ["sddm-greeter", "--test-mode", "--theme", target_theme],
                ["/usr/lib/sddm/sddm-greeter", "--test-mode", "--theme", target_theme],
            ]
            started = False
            for cmd in greeter_cmds:
                if shutil.which(cmd[0]) or os.path.exists(cmd[0]):
                    try:
                        subprocess.Popen(cmd)
                        started = True
                        break
                    except Exception:
                        continue
            if not started:
                QMessageBox.warning(
                    self, "Greeter Not Found",
                    "Could not find sddm-greeter-qt6 or sddm-greeter on this system to run test mode."
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to test SDDM Login Screen:\n{e}")

    def test_lockscreen(self):
        try:
            self.config = self.gather_config_from_ui()
            self.save_config_to_file()
            self.ensure_theme_installed()
            if os.path.exists(LOCKSCREEN_QML):
                self.write_qml_config(LOCKSCREEN_QML, self.config)

            greeter_paths = [
                "/usr/lib/x86_64-linux-gnu/libexec/kscreenlocker_greet",
                "/usr/lib/libexec/kscreenlocker_greet",
                "/usr/libexec/kscreenlocker_greet",
            ]
            exe = next((p for p in greeter_paths if os.path.exists(p)), "kscreenlocker_greet")
            subprocess.Popen([exe, "--testing"])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to launch kscreenlocker_greet:\n{e}")

    def test_logout_screen(self):
        try:
            self.config = self.gather_config_from_ui()
            self.save_config_to_file()
            self.ensure_theme_installed()
            self.write_logout_qml_config(LOGOUT_QML, self.config)

            greeter_bin = "/usr/lib/x86_64-linux-gnu/libexec/ksmserver-logout-greeter"
            if os.path.exists(greeter_bin):
                subprocess.Popen([greeter_bin, "--windowed"])
                return

            try:
                subprocess.Popen(["qdbus", "org.kde.LogoutPrompt", "/LogoutPrompt", "promptAll"])
            except Exception:
                subprocess.Popen(["qdbus6", "org.kde.LogoutPrompt", "/LogoutPrompt", "promptAll"])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not preview Logout screen:\n{e}")

    def reset_defaults(self):
        reply = QMessageBox.question(
            self, "Reset to Defaults",
            "Are you sure you want to reset all settings to default values?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.config = DEFAULT_CONFIG.copy()
            self.key_triggers = list(self.config.get("unlockKeyNames", ["Space"]))
            self.key_codes = list(self.config.get("unlockKeyCodes", [32]))
            self.mouse_triggers = list(self.config.get("unlockMouseButtons", ["Left Click"]))
            self.load_values_to_ui()
            self.update_preview()


def main():
    app = QApplication(sys.argv)
    window = LockscreenConfigApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()