#!/usr/bin/env python3
"""
midas_daemon.py — start the MIDAS server as a fully detached background daemon.

Launching the server from Finder / an AppleScript app as an ordinary child
process fails: macOS terminates the child when the launcher quits, so the
server dies a few seconds after the icon is clicked. This double-forks and
calls setsid() so the server becomes its own session leader, reparents to
launchd (PID 1), and keeps running long after whatever started it has exited.

Idempotent: if the server is already listening on the port, it does nothing.
"""
import os
import socket
import sys

HOST = "127.0.0.1"
PORT = 7432
PROJECT = os.path.dirname(os.path.abspath(__file__))
LOG = "/tmp/midas.log"


def is_running() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((HOST, PORT)) == 0


def main() -> None:
    if is_running():
        return  # already up — nothing to do

    # First fork: return control to the caller immediately.
    if os.fork() > 0:
        return
    # New session, detached from the launcher's process group / controlling tty.
    os.setsid()
    # Second fork: ensure we can't reacquire a controlling terminal.
    if os.fork() > 0:
        os._exit(0)

    os.chdir(PROJECT)
    log_fd = os.open(LOG, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    null_fd = os.open(os.devnull, os.O_RDONLY)
    os.dup2(null_fd, 0)
    os.dup2(log_fd, 1)
    os.dup2(log_fd, 2)

    venv_python = os.path.join(PROJECT, ".venv", "bin", "python")
    python = venv_python if os.path.exists(venv_python) else sys.executable
    os.execv(python, [
        python, "-m", "uvicorn", "app.main:app",
        "--host", HOST, "--port", str(PORT), "--log-level", "info",
    ])


if __name__ == "__main__":
    main()
