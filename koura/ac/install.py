"""Install a generated track from an output stage or a track directory."""

import argparse
import re
import shutil
from pathlib import Path

from paths import PROJECT, game_paths, require_game_closed


def track_source(stage, track_id=None):
    path = Path(stage)
    if path.is_dir() and (path / "ui").is_dir() and (path / "data").is_dir():
        if track_id and path.name != track_id:
            raise ValueError(f"Expected a track named {track_id}, got {path.name}")
        return path
    if not path.is_dir():
        path = PROJECT / "out" / stage
    exports = path / "assetto_corsa"
    tracks = sorted(entry for entry in exports.iterdir() if entry.is_dir())
    if track_id:
        selected = exports / track_id
        if selected not in tracks:
            raise ValueError(f"No track named {track_id} in {exports}")
        return selected
    if len(tracks) != 1:
        raise ValueError(f"Specify --track-id to choose among {', '.join(t.name for t in tracks)}")
    return tracks[0]


def install(source, root):
    if not re.fullmatch(r"[a-z0-9_]{1,32}", source.name):
        raise ValueError(f"Invalid track ID: {source.name}")
    if not list(source.glob("*.kn5")):
        raise ValueError(f"No KN5 file in {source}")
    require_game_closed()
    tracks = root / "content" / "tracks"
    dest = tracks / source.name
    if source.resolve() == dest.resolve():
        return dest
    if dest.is_symlink():
        raise ValueError(f"Refusing to replace a symlink: {dest}")

    incoming = dest.with_name(f".{source.name}.koura-incoming")
    previous = dest.with_name(f".{source.name}.koura-previous")
    if incoming.exists() or previous.exists():
        raise RuntimeError(f"An unfinished install exists beside {dest}")
    try:
        shutil.copytree(source, incoming)
        require_game_closed()
        if dest.exists():
            dest.rename(previous)
        try:
            incoming.rename(dest)
        except OSError:
            if previous.exists():
                previous.rename(dest)
            raise
        if previous.exists():
            shutil.rmtree(previous)
    finally:
        if incoming.exists():
            shutil.rmtree(incoming)
    for cache in ("ai_grids", "ai_payloads"):
        for entry in (root / "cache" / cache).glob(f"{source.name}__*"):
            if entry.is_file() or entry.is_symlink():
                entry.unlink()
    return dest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", help="Stage under out/ or path to a generated track")
    parser.add_argument("--track-id")
    args = parser.parse_args()
    root, _, _ = game_paths()
    print(install(track_source(args.stage, args.track_id), root))


if __name__ == "__main__":
    main()
