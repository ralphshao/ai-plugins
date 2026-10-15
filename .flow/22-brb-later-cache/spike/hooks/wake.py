"""Spike: wake the session once, 60s after its first Stop."""
import json, sys, tempfile, time
from pathlib import Path

data = json.load(sys.stdin)
flag = Path(tempfile.gettempdir()) / f"brb-spike-{data.get('session_id')}"
if flag.exists():
    sys.exit(0)  # one wake per session, no loop
flag.write_text(str(time.time()))
time.sleep(60)
print("brb-spike wake. Do two things: 1) Try to run compaction by calling the "
      "Skill tool with skill \"compact\" and report what happened. 2) Reply "
      "'pong' and nothing else.", file=sys.stderr)
sys.exit(2)
