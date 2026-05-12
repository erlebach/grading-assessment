# Ollama SIGKILL: GamePolicyAgent Root Cause and Mitigations

## Symptom

`ollama serve` is killed with `signal: killed` on a strikingly regular ~203 s cadence.
Every in-flight HTTP request from the Python grading pipeline receives a connection error.
The pattern is visible in `~/.ollama/logs/app.log` as repeating `signal: killed` entries
(from `server.go:224`).

## Root Cause

**`/usr/libexec/GamePolicyAgent`** runs a Launch Services database scan every ~203 seconds
to decide whether each installed `.app` bundle is a game. When it encounters a
*placeholder bundle* — an app directory in `/Applications/` that has no valid executable
in `Contents/MacOS/` — it fails to register it, creates a corrupt database entry, and
immediately retries, entering an infinite loop.

Reference: Apple Discussions thread #256283688 confirms this as a macOS system bug
requiring a kernel-level fix.

### The Kill Chain (Electron Ollama variant)

```
GamePolicyAgent scans /Applications/
  └─ Ollama.app found (Electron wrapper)
  └─ backgroundtaskmanagementd enumerates Ollama login-item + LaunchAgent
  └─ Electron wrapper Ollama[PID] re-registers with AppIntents
  └─ Electron wrapper SIGKILLs its child `ollama serve` subprocess
```

The Electron wrapper acts as a supervisor. When `backgroundtaskmanagementd` signals it
during a GamePolicyAgent scan cycle, the wrapper interprets this as a restart event and
kills/restarts the underlying `ollama serve` process — interrupting all active LLM calls.

### Why bare `ollama serve` (no Electron) Does Not Fully Help

Running `ollama serve` from a terminal (bypassing the Electron app) removes the
supervisor-kill chain for that process. However, **GamePolicyAgent's scan loop continues
to run**, causing system-level interference (CPU spikes, Launch Services database thrash)
that can still degrade model inference or occasionally crash the bare server when the loop
is particularly active.

The root problem is the corrupt Launch Services database feeding the loop, not just the
Electron wrapper.

### Triggering Conditions

Placeholder bundles in `/Applications/` arise from:
- Incomplete app uninstalls that leave the `.app` bundle but remove the executable
- Specific apps: Authy, Parallels Mounter (commonly cited)
- iOS app stubs synced to the Mac via iPhone USB connection

### Ollama.app Auto-Start (SMAppService Login Item)

Ollama.app registers itself as a per-user login item via `com.apple.xpc.ServiceManagement`
(macOS SMAppService API), label `com.ollama.ollama`. This means it **auto-starts at every
login without user intervention**, even if the user never opens it from /Applications.

Because the Electron wrapper is what the GamePolicyAgent kill chain targets, its presence
re-enables the kill chain after every reboot — even if you previously quit it manually.

**To permanently remove the auto-start:**
- System Settings → General → Login Items → find Ollama → click `–`
- Do NOT re-open `/Applications/Ollama.app` — use `ollama serve` from terminal only.

## Mitigations

Two launchd agents are deployed to break the cycle.

### 1. Kill GamePolicyAgent every 10 seconds

**Script:** `~/.local/bin/kill-gamepolicy.sh`  
**launchd plist:** `~/Library/LaunchAgents/com.user.kill-gamepolicy.plist`  
**Interval:** 10 s

Kills `GamePolicyAgent` with `pkill` before the ~203 s scan cycle can accumulate
database corruption. The process relaunches immediately (macOS auto-restart), but the
cycle clock resets, so the infinite loop never gets traction.

This is a **permanent suppression workaround**, not a fix. It must remain loaded for
the mitigations to hold.

### 2. Remove placeholder bundles every 30 minutes

**Script:** `~/.local/bin/cleanup-bundles.sh`  
**launchd plist:** `~/Library/LaunchAgents/com.user.cleanup-bundles.plist`  
**Interval:** 1800 s (30 min)

Scans `/Applications/` for bundles whose `Contents/MacOS/` directory is missing or
empty (no valid executable). Only removes bundles older than 1 hour to avoid touching
apps that are mid-install. If any bundle is removed, runs:

```
lsregister -kill -r -domain local -domain system -domain user
```

This rebuilds the Launch Services database from scratch, clearing corrupt entries.
`lsregister` only runs when something was actually removed — not on every cron tick.

## Managing the launchd Agents

### Load (first time or after editing)
```bash
launchctl bootout  gui/$(id -u) com.user.kill-gamepolicy  2>/dev/null || true
launchctl bootout  gui/$(id -u) com.user.cleanup-bundles  2>/dev/null || true
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.user.kill-gamepolicy.plist
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.user.cleanup-bundles.plist
```

### Check status
```bash
launchctl list | grep com.user
```

### Disable permanently
```bash
launchctl bootout gui/$(id -u) com.user.kill-gamepolicy
launchctl bootout gui/$(id -u) com.user.cleanup-bundles
```

### Logs
```bash
tail -f /tmp/kill-gamepolicy.log
tail -f /tmp/cleanup-bundles.log
```

## Separate Crash Root Cause: GGML-format Model Blobs

**Symptom:** `ollama serve` crashes immediately on startup with repeated
`error reading tensor index=0 error="unexpected EOF"` and/or
`failed to hydrate local model show cache ... error="invalid file magic"`.
No kill events in `app.log`; no crash report in `~/Library/Logs/DiagnosticReports/`.

**Cause:** Ollama's startup routine scans **every installed model manifest** to build a
model-show cache used by `ollama list` / `ollama show` / `/api/tags`. If any blob on disk
uses the old GGML format (magic bytes `746a6767` = `ggjt`, pre-GGUF), the tensor read
fails fatally and kills the server — even though that model is never being actively used.

Old GGML blobs originate from models downloaded before Ollama switched to GGUF format
(roughly 2023 and earlier). They are **not corrupt** — they are simply an incompatible
format that modern Ollama cannot read.

**Why `ollama rm` does not work for these models:** `ollama rm` calls `POST /api/show`
first to retrieve model metadata before deleting. This triggers the same tensor read,
crashes the server, and aborts the delete mid-operation.

**Fix: delete manifests and blobs directly from disk:**

```bash
# 1. Identify GGML blobs (magic != GGUF)
python3 - << 'EOF'
import os, glob
blobs = os.path.expanduser("~/.ollama/models/blobs")
for f in sorted(glob.glob(f"{blobs}/*")):
    if os.path.getsize(f) < 100_000_000: continue
    magic = open(f,'rb').read(4)
    if magic != b'GGUF':
        print(f"GGML: {os.path.basename(f)[:30]}  {os.path.getsize(f)/1e9:.1f}GB  {magic.hex()}")
EOF

# 2. Find which manifests reference them and delete, then delete the blobs
#    (see scripts/clean_ggml_blobs.py in this repo for the full script)
```

On 2026-05-12, 8 blobs (44.5 GB) were removed this way: four 3.8 GB files and four
7.3–7.4 GB files covering `llama2:13b-chat`, `llama2:13b-text`, `llama2:text`,
`codellama:13b`, `codellama:7b-code`, `codellama:7b-instruct`, `codellama:latest`,
`ge:latest`, `ge_model:latest`, `codeup:latest`.

**This root cause is completely independent of GamePolicyAgent.** If `ollama serve`
crashes with tensor errors at startup, investigate GGML blobs before suspecting
GamePolicyAgent.

## Verification

Run `scripts/probe_ollama.py` (in this repo) before and after deploying the agents:

```bash
.venv/bin/python scripts/probe_ollama.py --n 50 --interval 5
```

A `signal: killed` count of 0 with consecutive successes = 50 confirms the mitigations
are holding.

**Verified result (2026-05-12, `gemma4:26b`, after GGML blob removal):**
```
Calls: 50 (50 ok / 0 err)  Avg latency: 2.75s  Longest streak: 50  Kill events: 0
VERDICT: stable — safe to run the benchmark.
```

## Timeline

| Date | Event |
|------|-------|
| 2026-05-11 20:05 | Ollama SIGKILL first observed; 3 code fixes land (context_window, keep_alive, check_type) |
| 2026-05-11 22:22 | `scripts/probe_ollama.py` added to diagnose cadence |
| 2026-05-11 22:54 | Root cause traced to GamePolicyAgent via unified-log; bare CLI workaround documented |
| 2026-05-12 09:xx | Apple Discussions #256283688 confirms macOS bug; placeholder-bundle loop confirmed; launchd mitigations deployed |
| 2026-05-12 10:xx | Crashes diagnosed as GGML-format model blobs (`ggjt` magic), not GamePolicyAgent; `ollama rm` also crashes server on GGML models |
| 2026-05-12 10:xx | `com.ollama.ollama` SMAppService login item found auto-starting Electron Ollama.app without user intent; killed and disabled |
| 2026-05-12 13:05 | 8 GGML blobs (44.5 GB) + 10 manifests deleted directly from disk; probe 50/50 OK, 0 kills — stable |
