#!/usr/bin/env python3
"""Ollama stability probe.

Issues N tiny prompts sequentially through the same Ollama client used by
the v2 pipeline (context_window=8192, keep_alive=24h, json_mode=True) and
tails ~/.ollama/logs/app.log for `signal: killed` events in parallel.
Correlates kill events with in-flight requests so the SIGKILL cadence is
visible before kicking off the (~30-45 min) v2 benchmark.

Usage:
    .venv/bin/python scripts/probe_ollama.py --model gpt-oss:20b --n 50 --interval 5
"""

import argparse
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from llama_index.core.llms import ChatMessage

from config.llm_config import configure_llm


def now() -> str:
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


class KillWatcher(threading.Thread):
    """Tails the Ollama app log for `signal: killed` lines."""

    def __init__(self, log_path: Path):
        super().__init__(daemon=True)
        self.log_path = log_path
        self.events: list[tuple[float, str]] = []
        self.stop_event = threading.Event()
        self._available = log_path.exists()

    def run(self) -> None:
        if not self._available:
            return
        with self.log_path.open("r") as f:
            f.seek(0, 2)
            while not self.stop_event.is_set():
                line = f.readline()
                if not line:
                    time.sleep(0.2)
                    continue
                if "signal: killed" in line:
                    self.events.append((time.time(), line.rstrip()))
                    print(f"  [{now()}] !! KILL detected: {line.rstrip()}", flush=True)

    def stop(self) -> None:
        self.stop_event.set()


def probe(model: str, n: int, interval: float, log_path: Path) -> int:
    print(f"[{now()}] Configuring Ollama client (model={model})...", flush=True)
    llm = configure_llm("ollama", model=model)
    print(f"[{now()}] Client ready. Watching {log_path} for kill events.", flush=True)

    watcher = KillWatcher(log_path)
    watcher.start()
    if not watcher._available:
        print(f"[{now()}] WARNING: {log_path} not found — proceeding without kill detection.", flush=True)

    prompt = 'Respond with exactly this JSON and nothing else: {"answer": "OK"}'
    results: list[dict] = []
    streak = 0
    longest_streak = 0
    start = time.time()

    try:
        for i in range(1, n + 1):
            t0 = time.time()
            entry: dict = {"i": i, "t0": t0, "ok": False, "latency_s": 0.0, "err": None, "len": 0}
            try:
                resp = llm.chat([ChatMessage(role="user", content=prompt)])
                content = resp.message.content or ""
                entry["ok"] = True
                entry["len"] = len(content)
                streak += 1
                longest_streak = max(longest_streak, streak)
            except Exception as e:
                entry["err"] = f"{type(e).__name__}: {e}"
                streak = 0
            entry["latency_s"] = time.time() - t0
            results.append(entry)
            status = "OK " if entry["ok"] else "ERR"
            tail = f"len={entry['len']}" if entry["ok"] else entry["err"][:80]
            print(f"[{now()}] {i:3d}/{n} {status} {entry['latency_s']:6.2f}s  {tail}", flush=True)
            if i < n:
                time.sleep(interval)
    except KeyboardInterrupt:
        print(f"\n[{now()}] Interrupted by user.", flush=True)
    finally:
        watcher.stop()
        watcher.join(timeout=1.0)

    elapsed = time.time() - start
    ok_count = sum(1 for r in results if r["ok"])
    err_count = len(results) - ok_count
    latencies = [r["latency_s"] for r in results if r["ok"]]
    avg = sum(latencies) / len(latencies) if latencies else 0.0
    p_max = max(latencies) if latencies else 0.0

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"Calls:           {len(results)}  ({ok_count} ok / {err_count} err)")
    print(f"Wall time:       {elapsed:.1f}s")
    print(f"Avg latency:     {avg:.2f}s   (max {p_max:.2f}s)")
    print(f"Longest streak:  {longest_streak} consecutive successes")
    print(f"Kill events:     {len(watcher.events)}")
    for t, line in watcher.events:
        ts = datetime.fromtimestamp(t).strftime("%H:%M:%S")
        print(f"  {ts}  {line}")

    if err_count == 0 and len(watcher.events) == 0:
        print("\nVERDICT: stable — safe to run the benchmark.")
        return 0
    print("\nVERDICT: unstable — investigate before running the benchmark.")
    return 1


def main() -> int:
    p = argparse.ArgumentParser(description="Probe Ollama stability with N tiny prompts.")
    p.add_argument("--model", default="gpt-oss:20b", help="Ollama model tag (default: gpt-oss:20b).")
    p.add_argument("--n", type=int, default=50, help="Number of probe calls (default: 50).")
    p.add_argument("--interval", type=float, default=5.0, help="Seconds between calls (default: 5.0).")
    p.add_argument(
        "--log",
        default=str(Path.home() / ".ollama" / "logs" / "app.log"),
        help="Ollama app log to tail for `signal: killed` (default: ~/.ollama/logs/app.log).",
    )
    args = p.parse_args()
    return probe(args.model, args.n, args.interval, Path(args.log))


if __name__ == "__main__":
    sys.exit(main())
