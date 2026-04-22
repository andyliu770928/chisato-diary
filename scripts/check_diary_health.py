#!/usr/bin/env python3
"""Quick health check for 小千 diary automation."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path


BASE_DIR = Path("/Users/aliu/MEGA/openclaw/diary")
STATE_FILE = BASE_DIR / "state" / "last-run.json"
LOCK_DIR = BASE_DIR / "state" / "diary.lock"
SCRIPT_LOG_DIR = BASE_DIR / "scripts" / "logs"
RUN_STATUS = SCRIPT_LOG_DIR / "last-run.status"
RUN_PID = SCRIPT_LOG_DIR / "last-run.pid"
RUN_OUT = SCRIPT_LOG_DIR / "last-run.out"
RUN_ERR = SCRIPT_LOG_DIR / "last-run.err"
ARCHIVE_FILE = BASE_DIR / "archive.html"
PUBLIC_BASE = "https://andyliu770928.github.io/chisato-diary"


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def pid_running(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_status_kv(path: Path) -> dict:
    data = {}
    for line in read_text(path).splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            data[key.strip()] = value.strip()
    return data


def tail_lines(path: Path, limit: int = 5) -> list[str]:
    text = read_text(path)
    if not text:
        return []
    return text.splitlines()[-limit:]


def latest_archive_entry() -> tuple[str, str]:
    content = read_text(ARCHIVE_FILE)
    if not content:
        return "", ""
    match = re.search(
        r'<a href="(diary-\d{4}-\d{2}-\d{2}\.html)">\s*'
        r'<div class="diary-date">([^<]+)</div>',
        content,
        flags=re.S,
    )
    if not match:
        return "", ""
    rel = match.group(1)
    date = match.group(2)
    return date, f"{PUBLIC_BASE}/{rel}"


def main() -> int:
    state = read_json(STATE_FILE)
    run_status = read_status_kv(RUN_STATUS)
    latest_date, latest_url = latest_archive_entry()

    lock_exists = LOCK_DIR.exists()
    lock_pid_text = read_text(LOCK_DIR / "pid") if lock_exists else ""
    lock_started = read_text(LOCK_DIR / "started_at") if lock_exists else ""

    run_pid_text = read_text(RUN_PID)
    run_pid = int(run_pid_text) if run_pid_text.isdigit() else None
    run_alive = pid_running(run_pid) if run_pid else False

    print("小千日記健康檢查")
    print(f"- state.status: {state.get('status', 'missing')}")
    print(f"- state.date: {state.get('date', '-')}")
    print(f"- state.updatedAt: {state.get('updatedAt', '-')}")
    if state.get("title"):
        print(f"- state.title: {state['title']}")
    if state.get("provider"):
        print(f"- state.provider: {state['provider']}")
    if state.get("error"):
        print(f"- state.error: {state['error']}")

    print(f"- wrapper.status: {run_status.get('status', 'missing')}")
    print(f"- wrapper.updated_at: {run_status.get('updated_at', '-')}")
    print(f"- wrapper.pid: {run_pid_text or '-'}")
    print(f"- wrapper.pid_running: {'yes' if run_alive else 'no'}")

    print(f"- lock.exists: {'yes' if lock_exists else 'no'}")
    if lock_exists:
        lock_running = lock_pid_text.isdigit() and pid_running(int(lock_pid_text))
        print(f"- lock.pid: {lock_pid_text or '-'}")
        print(f"- lock.pid_running: {'yes' if lock_running else 'no'}")
        print(f"- lock.started_at: {lock_started or '-'}")

    print(f"- latest.archive.date: {latest_date or '-'}")
    print(f"- latest.archive.url: {latest_url or '-'}")
    if state.get("diaryUrl"):
        print(f"- latest.state.url: {state['diaryUrl']}")

    out_tail = tail_lines(RUN_OUT)
    err_tail = tail_lines(RUN_ERR)
    print("- tail.out:")
    if out_tail:
        for line in out_tail:
            print(f"  {line}")
    else:
        print("  (empty)")

    print("- tail.err:")
    if err_tail:
        for line in err_tail:
            print(f"  {line}")
    else:
        print("  (empty)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
