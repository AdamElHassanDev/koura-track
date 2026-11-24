"""Run the local CSP probe in Assetto Corsa and collect one session's evidence."""

import argparse
import json
import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

from paths import APP_ID, PROJECT, game_paths, game_pids, require_game_closed
from race_ini import prepare, restore


def launch_options(prefix):
    proton = Path(os.environ.get(
        "KOURA_PROTON", Path.home() / ".steam/root/compatibilitytools.d/GE-Proton9-20/proton"
    ))
    overrides = os.environ.get("WINEDLLOVERRIDES", "")
    if not any("dwrite" in pair.split("=")[0].split(",") for pair in overrides.split(";")):
        overrides = ";".join(filter(None, (overrides, "dwrite=n,b")))
    env = {
        **os.environ,
        "STEAM_COMPAT_CLIENT_INSTALL_PATH": str(Path.home() / ".steam/steam"),
        "STEAM_COMPAT_DATA_PATH": str(prefix),
        "SteamAppId": APP_ID,
        "SteamGameId": APP_ID,
        "WINEDLLOVERRIDES": overrides,
    }
    return (
        ("proton", [str(proton), "run", "acs.exe"], env),
        ("protontricks", ["protontricks-launch", "--appid", APP_ID, "acs.exe"], env),
        ("steam", ["steam", "-applaunch", APP_ID], env),
    )


def signature(path):
    try:
        st = path.stat()
        return st.st_ino, st.st_mtime_ns, st.st_size
    except FileNotFoundError:
        return None


def status(path):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def close_session(process):
    # The machine was checked for a pre-existing game before launching.
    for _ in range(20):
        if not list(game_pids()) and process.poll() is not None:
            return
        time.sleep(0.2)
    for pid in game_pids():
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
    for _ in range(25):
        if not list(game_pids()):
            return
        time.sleep(0.2)
    for pid in game_pids():
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    require_game_closed()


def attempt(method, command, env, root, docs, probe, points, evidence, timeout):
    require_game_closed()
    evidence.mkdir(parents=True, exist_ok=True)
    probe.mkdir(parents=True, exist_ok=True)
    for pattern in ("status.json", "results.json", "shot_*.png"):
        for path in probe.glob(pattern):
            path.unlink()
    (probe / "points.json").write_bytes(points)
    logs = [docs / "logs" / name for name in ("log.txt", "custom_shaders_patch.log")]
    before = {path: signature(path) for path in logs}
    first = time.monotonic()
    outcome = "timed out"
    seen_game = False
    proc = None
    try:
        with (evidence / "launch.log").open("w") as log:
            try:
                proc = subprocess.Popen(command, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT)
            except OSError as err:
                log.write(f"{type(err).__name__}: {err}\n")
                outcome = str(err)
            if proc:
                deadline = first + timeout
                while time.monotonic() < deadline:
                    result = status(probe / "status.json")
                    if result.get("state") == "done" and (probe / "results.json").is_file():
                        outcome = "done"
                        break
                    pids = list(game_pids())
                    seen_game |= bool(pids)
                    if not pids and proc.poll() is not None and (method != "steam" or seen_game):
                        outcome = f"process exited {proc.returncode}"
                        break
                    time.sleep(0.25)
    finally:
        elapsed = round(time.monotonic() - first, 2)
        if proc:
            close_session(proc)
        for path in logs:
            if path.exists() and signature(path) != before[path]:
                shutil.copy2(path, evidence / path.name)
        for pattern in ("status.json", "results.json", "shot_*.png"):
            for path in probe.glob(pattern):
                shutil.copy2(path, evidence / path.name)
        (probe / "points.json").unlink(missing_ok=True)
        diagnostics = {"method": method, "command": command, "outcome": outcome,
                       "elapsed_s": elapsed, "game_process_observed": seen_game,
                       "status": status(evidence / "status.json")}
        (evidence / "attempt.json").write_text(json.dumps(diagnostics, indent=2) + "\n")
        print(f"{method}: {outcome} after {elapsed:.2f} s", flush=True)
    return outcome == "done"


def run(track, points_file, evidence, car, layout, methods, timeout):
    root, docs, prefix = game_paths()
    require_game_closed()
    points = points_file.read_bytes()
    if not json.loads(points).get("points"):
        raise ValueError("No probe points")
    ini = docs / "cfg" / "race.ini"
    app = root / "apps" / "lua" / "koura_probe"
    app.mkdir(parents=True, exist_ok=True)
    for name in ("manifest.ini", "koura_probe.lua"):
        shutil.copy2(Path(__file__).parent / "koura_probe" / name, app / name)
    appid = root / "steam_appid.txt"
    if not appid.exists():
        appid.write_text(APP_ID + "\n")
    for method, command, env in launch_options(prefix):
        if method not in methods:
            continue
        prepare(ini, root, track, car, layout)
        try:
            folder = evidence / method
            if attempt(method, command, env, root, docs, docs / "koura_probe", points, folder, timeout):
                for path in folder.iterdir():
                    shutil.copy2(path, evidence / path.name)
                return 0
        finally:
            restore(ini)
    return 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("track")
    parser.add_argument("--points", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, default=PROJECT / "out" / "poc" / "ingame")
    parser.add_argument("--car", default="abarth500")
    parser.add_argument("--layout", default="")
    parser.add_argument("--method", choices=("proton", "protontricks", "steam"), action="append")
    parser.add_argument("--timeout", type=float, default=180)
    args = parser.parse_args()
    args.evidence.mkdir(parents=True, exist_ok=True)
    raise SystemExit(run(args.track, args.points, args.evidence, args.car, args.layout,
                         args.method or ("proton", "protontricks", "steam"), args.timeout))


if __name__ == "__main__":
    main()
