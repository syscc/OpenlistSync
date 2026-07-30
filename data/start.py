#!/usr/bin/env python3
import os
import platform
import signal
import subprocess
import sys
import time
from pathlib import Path
from shutil import which


BACKEND_PORT = 8023
FRONTEND_PORT = 8080
BACKEND_PID = "backend.pid"
FRONTEND_PID = "frontend.pid"


def is_windows():
    return platform.system().lower() == "windows"


def project_root():
    return Path(__file__).resolve().parent.parent


def data_dir(base):
    path = base / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def find_npm():
    if is_windows():
        for path in [
            r"C:\Program Files\nodejs\npm.cmd",
            r"C:\Program Files (x86)\nodejs\npm.cmd",
        ]:
            if os.path.exists(path):
                return path
    return which("npm") or "npm"


def python_executable(base):
    if is_windows():
        venv_python = base / ".venv" / "Scripts" / "python.exe"
    else:
        venv_python = base / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def run(cmd, cwd=None, env=None):
    result = subprocess.run(cmd, cwd=cwd, env=env, shell=False)
    return result.returncode == 0


def install_python_deps(base):
    requirements = base / "requirements.txt"
    if not requirements.exists():
        print(f"requirements.txt not found: {requirements}")
        return False

    py = python_executable(base)
    return run([py, "-m", "pip", "install", "-r", str(requirements)], cwd=str(base))


def install_frontend_deps(base):
    frontend = base / "web"
    package_json = frontend / "package.json"
    if not package_json.exists():
        print(f"web/package.json not found: {package_json}")
        return False

    if (frontend / "node_modules").exists():
        return True

    npm = find_npm()
    if (frontend / "package-lock.json").exists():
        return run([npm, "ci"], cwd=str(frontend))
    return run([npm, "install"], cwd=str(frontend))


def read_configured_backend_port(base):
    os.chdir(base)
    try:
        sys.path.insert(0, str(base))
        from common.config import getConfig

        return int(getConfig()["server"]["port"])
    except Exception:
        return BACKEND_PORT


def find_listen_pid_by_port(port):
    if is_windows():
        return find_windows_listen_pid_by_port(port)
    return find_posix_listen_pid_by_port(port)


def find_posix_listen_pid_by_port(port):
    try:
        out = subprocess.check_output(
            ["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN", "-t"],
            encoding="utf-8",
            errors="ignore",
        )
    except Exception:
        return None

    for line in out.splitlines():
        line = line.strip()
        if line.isdigit():
            return int(line)
    return None


def find_windows_listen_pid_by_port(port):
    try:
        out = subprocess.check_output(["netstat", "-ano"], encoding="utf-8", errors="ignore")
    except Exception:
        return None

    suffix = f":{port}"
    for line in out.splitlines():
        parts = [part for part in line.split() if part]
        if len(parts) < 5:
            continue
        proto, local_addr, _, state, pid = parts[:5]
        if not proto.upper().startswith("TCP"):
            continue
        if state.upper() != "LISTENING":
            continue
        if local_addr.endswith(suffix) and pid.isdigit():
            return int(pid)
    return None


def pid_is_running(pid):
    if is_windows():
        try:
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/NH"],
                capture_output=True,
                text=True,
                check=False,
            )
            return str(pid) in result.stdout
        except Exception:
            return False

    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_pid(path):
    try:
        pid = int(path.read_text(encoding="utf-8").strip())
        return pid if pid_is_running(pid) else None
    except Exception:
        return None


def write_pid(path, pid):
    path.write_text(str(pid), encoding="utf-8")


def log_file(base, name):
    log_dir = data_dir(base) / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / name


def start_backend(base):
    port = read_configured_backend_port(base)
    existing_pid = find_listen_pid_by_port(port)
    if existing_pid:
        print(f"Backend already listening on {port}, PID: {existing_pid}")
        return None

    py = python_executable(base)
    log = open(log_file(base, "backend_source.log"), "a", encoding="utf-8")
    proc = subprocess.Popen([py, "main.py"], cwd=str(base), stdout=log, stderr=subprocess.STDOUT)
    write_pid(data_dir(base) / BACKEND_PID, proc.pid)
    print(f"Backend started, PID: {proc.pid}, http://127.0.0.1:{port}/")
    return proc


def start_frontend(base):
    existing_pid = find_listen_pid_by_port(FRONTEND_PORT)
    if existing_pid:
        print(f"Frontend already listening on {FRONTEND_PORT}, PID: {existing_pid}")
        return None

    npm = find_npm()
    frontend = base / "web"
    env = os.environ.copy()
    env["PORT"] = str(FRONTEND_PORT)

    log = open(log_file(base, "frontend_source.log"), "a", encoding="utf-8")
    proc = subprocess.Popen(
        [npm, "run", "dev", "--", "--host", "0.0.0.0", "--port", str(FRONTEND_PORT)],
        cwd=str(frontend),
        env=env,
        stdout=log,
        stderr=subprocess.STDOUT,
    )
    write_pid(data_dir(base) / FRONTEND_PID, proc.pid)
    print(f"Frontend started, PID: {proc.pid}, http://127.0.0.1:{FRONTEND_PORT}/")
    return proc


def stop_pid(pid, label):
    if not pid or not pid_is_running(pid):
        return False

    if is_windows():
        try:
            subprocess.run(["taskkill", "/PID", str(pid), "/F", "/T"], check=False)
            print(f"{label} stopped, PID: {pid}")
            return True
        except Exception as exc:
            print(f"Failed to stop {label}, PID: {pid}: {exc}")
            return False

    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(20):
            if not pid_is_running(pid):
                print(f"{label} stopped, PID: {pid}")
                return True
            time.sleep(0.2)
        os.kill(pid, signal.SIGKILL)
        print(f"{label} killed, PID: {pid}")
        return True
    except Exception as exc:
        print(f"Failed to stop {label}, PID: {pid}: {exc}")
        return False


def stop():
    base = project_root()
    os.chdir(base)
    pids = [
        ("Backend", data_dir(base) / BACKEND_PID),
        ("Frontend", data_dir(base) / FRONTEND_PID),
    ]

    stopped_any = False
    for label, pid_file in pids:
        pid = read_pid(pid_file)
        stopped_any = stop_pid(pid, label) or stopped_any
        try:
            pid_file.unlink()
        except FileNotFoundError:
            pass
        except Exception:
            pass

    if not stopped_any:
        print("No source-mode service is running")


def start():
    base = project_root()
    os.chdir(base)

    if not install_python_deps(base):
        sys.exit(1)
    if not install_frontend_deps(base):
        sys.exit(1)

    backend = start_backend(base)
    frontend = start_frontend(base)
    print("Source mode is running. Press Ctrl+C to stop services.")

    try:
        while True:
            if backend and backend.poll() is not None:
                print(f"Backend exited with code {backend.returncode}")
                break
            if frontend and frontend.poll() is not None:
                print(f"Frontend exited with code {frontend.returncode}")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping source-mode services...")
    finally:
        stop()


def restart():
    stop()
    start()


if __name__ == "__main__":
    args = sys.argv[1:]
    if "-s" in args or "-stop" in args or "--stop" in args:
        stop()
    elif "-r" in args or "-restart" in args or "--restart" in args:
        restart()
    else:
        start()
