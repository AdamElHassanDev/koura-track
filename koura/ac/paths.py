"""Local Assetto Corsa paths shared by the game probe commands."""

import os
import tomllib
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
STEAMAPPS = Path("/mnt/Linux_HDD/SteamLibrary/steamapps")
APP_ID = "244210"
DEFAULT_ROOT = STEAMAPPS / "common" / "assettocorsa"


def game_paths():
    config = PROJECT / "koura" / "config.toml"
    settings = tomllib.loads(config.read_text()) if config.exists() else {}
    root = Path(os.environ.get("KOURA_AC_ROOT", settings.get("ac_root", DEFAULT_ROOT))).expanduser()
    prefix = root.parent.parent / "compatdata" / APP_ID
    documents = prefix / "pfx" / "drive_c/users/steamuser/Documents/Assetto Corsa"
    docs = Path(os.environ.get("KOURA_AC_DOCS", settings.get("ac_docs", documents))).expanduser()
    return root, docs, prefix


def game_pids():
    """Read exact process names, avoiding matches against command lines of the calling shell."""
    names = {"acs.exe", "acs_x86.exe", "assetto_corsa.exe", "assettocorsa.exe", "content manager.exe"}
    for entry in Path("/proc").iterdir():
        if entry.name.isdigit():
            try:
                if entry.stat().st_uid != os.getuid():
                    continue
                name = (entry / "comm").read_text().strip().lower()
                # Assetto Corsa can rename its main thread after loading.
                executable = (entry / "cmdline").read_bytes().split(b"\0", 1)[0]
                executable = Path(os.fsdecode(executable).replace("\\", "/")).name.lower()
                if name in names or executable in names:
                    yield int(entry.name)
            except (FileNotFoundError, PermissionError, ProcessLookupError):
                continue


def require_game_closed():
    pids = list(game_pids())
    if pids:
        raise RuntimeError(f"Assetto Corsa is running (PID {', '.join(map(str, pids))})")
