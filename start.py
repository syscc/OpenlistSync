import os
import sys
import subprocess
from pathlib import Path


def find_npm():
    paths = [
        r"C:\\Program Files\\nodejs\\npm.cmd",
        r"C:\\Program Files (x86)\\nodejs\\npm.cmd",
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    from shutil import which
    w = which("npm")
    return w or "npm"


def run(cmd, cwd=None, env=None):
    r = subprocess.run(cmd, cwd=cwd, env=env)
    return r.returncode == 0


def build_if_needed(base):
    dist_index = base / "frontend" / "dist" / "index.html"
    if dist_index.exists():
        return True
    npm = find_npm()
    if not run([npm, "install", "--legacy-peer-deps"], cwd=str(base / "frontend")):
        print("npm install failed")
        return False
    if not run([npm, "run", "build"], cwd=str(base / "frontend")):
        print("npm run build failed")
        return False
    return True


def start():
    base = Path(__file__).resolve().parent
    os.chdir(base)
    if not build_if_needed(base):
        sys.exit(1)
    py = sys.executable
    p = subprocess.Popen([py, "main.py"], cwd=str(base))
    pid_file = base / "data" / "server.pid"
    try:
        pid_file.parent.mkdir(parents=True, exist_ok=True)
        pid_file.write_text(str(p.pid), encoding="utf-8")
    except Exception:
        pass
    try:
        p.wait()
    except KeyboardInterrupt:
        pass


def find_pid_by_port(port):
    try:
        out = subprocess.check_output(["netstat", "-ano"], encoding="utf-8", errors="ignore")
    except Exception:
        return None
    for line in out.splitlines():
        if f":{port}" in line and "LISTENING" in line:
            parts = [x for x in line.split() if x]
            if parts:
                pid = parts[-1]
                if pid.isdigit():
                    return int(pid)
    return None


def stop():
    base = Path(__file__).resolve().parent
    os.chdir(base)
    try:
        from common.config import getConfig
        port = getConfig()["server"]["port"]
    except Exception:
        port = 8023
    pid_file = base / "data" / "server.pid"
    pid = None
    if pid_file.exists():
        try:
            pid = int(pid_file.read_text(encoding="utf-8").strip())
        except Exception:
            pid = None
    if pid is None:
        pid = find_pid_by_port(port)
    if pid is None:
        print("not running")
        return
    try:
        subprocess.run(["taskkill", "/PID", str(pid), "/F", "/T"], check=False)
    except Exception:
        pass
    try:
        if pid_file.exists():
            pid_file.unlink()
    except Exception:
        pass


def restart():
    stop()
    start()


if __name__ == "__main__":
    args = sys.argv[1:]
    if "-stop" in args:
        stop()
    elif "-r" in args or "-restart" in args:
        restart()
    else:
        start()
