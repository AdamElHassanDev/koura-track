"""Prepare and restore the existing Assetto Corsa practice-session configuration."""

import argparse
import configparser
import io
import re
from pathlib import Path

from paths import game_paths, require_game_closed


def case_preserving_parser():
    cp = configparser.ConfigParser(strict=False, interpolation=None)
    cp.optionxform = str
    return cp


def backup_path(ini):
    return ini.with_name(f"{ini.name}.koura-backup")


def replace_contents(ini, data):
    temporary = ini.with_name(f"{ini.name}.koura-tmp")
    try:
        with temporary.open("xb") as file:
            file.write(data)
        temporary.chmod(ini.stat().st_mode & 0o777)
        temporary.replace(ini)
    finally:
        if temporary.exists():
            temporary.unlink()


def prepare(ini, root, track, car, layout=""):
    for label, name in (("track", track), ("car", car), ("layout", layout)):
        if name or label != "layout":
            if not re.fullmatch(r"[a-zA-Z0-9_-]+", name):
                raise ValueError(f"Invalid {label}: {name}")
    track_dir = root / "content" / "tracks" / track
    models = track_dir / (f"models_{layout}.ini" if layout else "models.ini")
    if not models.is_file() and (layout or not (track_dir / f"{track}.kn5").is_file()):
        raise FileNotFoundError(models)
    skins = sorted(p.name for p in (root / "content" / "cars" / car / "skins").iterdir() if p.is_dir())
    if not skins:
        raise ValueError(f"No skins for {car}")
    require_game_closed()
    original = ini.read_bytes()
    text = "\n".join(
        line for line in original.decode("utf-8-sig").splitlines()
        if not re.match(r"\s*__CM_CUSTOM_MODE\s*=", line, re.I)
    )
    cp = case_preserving_parser()
    cp.read_string(text)
    for section in cp.sections():
        if section in ("EVENT", "SPECIAL_EVENT") or (
            section.startswith(("CAR_", "SESSION_", "CONDITION_"))
            and section not in ("CAR_0", "SESSION_0")
        ):
            cp.remove_section(section)
    if cp.has_section("CAR_0"):
        cp.remove_option("CAR_0", "_EXT_SETUP_FILENAME")
    updates = {
        "RACE": {"TRACK": track, "CONFIG_TRACK": layout, "MODEL": car, "CARS": "1", "PENALTIES": "0"},
        "CAR_0": {"MODEL": "-", "SKIN": skins[0], "SETUP": "", "MODEL_CONFIG": ""},
        "SESSION_0": {"NAME": "Practice", "TYPE": "1", "DURATION_MINUTES": "0", "SPAWN_SET": "PIT"},
        "REMOTE": {"ACTIVE": "0"},
        "REPLAY": {"ACTIVE": "0"},
        "BENCHMARK": {"ACTIVE": "0"},
        "RESTART": {"ACTIVE": "0"},
        "AUTOSPAWN": {"ACTIVE": "1"},
    }
    for section, values in updates.items():
        if not cp.has_section(section):
            cp.add_section(section)
        cp[section].update(values)
    formatted = io.StringIO()
    cp.write(formatted, space_around_delimiters=False)
    with backup_path(ini).open("xb") as backup:
        backup.write(original)
    try:
        replace_contents(ini, formatted.getvalue().encode())
    except OSError:
        backup_path(ini).unlink()
        raise


def restore(ini):
    backup = backup_path(ini)
    if backup.exists():
        replace_contents(ini, backup.read_bytes())
        backup.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ini", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    start = commands.add_parser("prepare")
    start.add_argument("track")
    start.add_argument("--layout", default="")
    start.add_argument("--car", default="abarth500")
    commands.add_parser("restore")
    args = parser.parse_args()
    root, docs, _ = game_paths()
    ini = args.ini or docs / "cfg" / "race.ini"
    if args.command == "prepare":
        prepare(ini, root, args.track, args.car, args.layout)
    else:
        require_game_closed()
        restore(ini)


if __name__ == "__main__":
    main()
