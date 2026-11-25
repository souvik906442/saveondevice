"""Save on device (Windows): right-click a file -> Send to -> Save on device
copies it into the folder you chose.

  SaveOnDevice.exe                 first run / double-click: choose the folder and add the "Send to" entry
  SaveOnDevice.exe --choose        choose a different folder
  SaveOnDevice.exe --uninstall     remove the "Send to" entry
  SaveOnDevice.exe FILE [FILE...]  copy files/folders to the chosen folder (what "Send to" runs)
"""
import ctypes
import json
import os
import shutil
import subprocess
import sys

APP = "Save on device"
CFG_DIR = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "SaveOnDevice")
CFG = os.path.join(CFG_DIR, "config.json")
SENDTO = os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Windows", "SendTo", APP + ".lnk")


def msg(text, title=APP, seconds=0):
    """Message box; with seconds>0 it closes itself (success notices should not need a click)."""
    try:
        if seconds:
            ctypes.windll.user32.MessageBoxTimeoutW(0, text, title, 0x40, 0, seconds * 1000)
        else:
            ctypes.windll.user32.MessageBoxW(0, text, title, 0x40)
    except Exception:
        print(text)


def load_dest():
    try:
        with open(CFG, encoding="utf-8") as f:
            d = json.load(f).get("dest", "")
        return d if d and os.path.isdir(d) else ""
    except Exception:
        return ""


def save_dest(d):
    os.makedirs(CFG_DIR, exist_ok=True)
    with open(CFG, "w", encoding="utf-8") as f:
        json.dump({"dest": d}, f)


def choose_dest():
    import tkinter as tk
    from tkinter import filedialog
    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    d = filedialog.askdirectory(title="Choose the folder where files should be saved",
                                initialdir=load_dest() or os.path.expanduser("~"))
    root.destroy()
    if d:
        d = os.path.normpath(d)
        save_dest(d)
        return d
    return ""


def unique(path):
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    n = 1
    while os.path.exists(f"{base} ({n}){ext}"):
        n += 1
    return f"{base} ({n}){ext}"


def copy_item(src, dest):
    target = unique(os.path.join(dest, os.path.basename(src.rstrip("\\/"))))
    if os.path.isdir(src):
        shutil.copytree(src, target)
    else:
        shutil.copy2(src, target)


def install():
    exe = sys.executable if getattr(sys, "frozen", False) else os.path.abspath(__file__)
    ps = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut('%s');"
        "$s.TargetPath='%s';$s.IconLocation='%s,0';$s.Save()"
    ) % (SENDTO.replace("'", "''"), exe.replace("'", "''"), exe.replace("'", "''"))
    subprocess.run(["powershell", "-NoProfile", "-WindowStyle", "Hidden", "-Command", ps],
                   creationflags=0x08000000, check=True)


def main():
    args = sys.argv[1:]
    if args and args[0] == "--uninstall":
        try:
            os.remove(SENDTO)
        except FileNotFoundError:
            pass
        msg('Removed from the "Send to" menu.')
        return
    if not args or args[0] == "--choose":
        d = choose_dest()
        if not d:
            return
        try:
            install()
        except Exception as e:
            msg(f"Folder saved, but the Send to entry could not be created:\n{e}")
            return
        msg(f'Done.\n\nRight-click a file -> Send to -> "{APP}"\nSaves to: {d}')
        return

    dest = load_dest() or choose_dest()
    if not dest:
        return
    ok, errors = 0, []
    for p in args:
        try:
            copy_item(p, dest)
            ok += 1
        except Exception as e:
            errors.append(f"{os.path.basename(p)}: {e}")
    if errors:
        msg(f"Saved {ok}, failed {len(errors)}:\n" + "\n".join(errors), seconds=0)
    else:
        msg(f"Saved {ok} item(s) to\n{dest}", seconds=2)


if __name__ == "__main__":
    main()
