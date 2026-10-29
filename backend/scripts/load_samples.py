"""Upload every transcript in data/sample_transcripts through the running API.

    python scripts/load_samples.py [--api http://localhost:8000]
"""
import argparse
import getpass
import json
import sys
from pathlib import Path

import httpx

SAMPLES = Path(__file__).resolve().parents[2] / "data" / "sample_transcripts"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", default="http://localhost:8000")
    args = ap.parse_args()

    manifest = json.loads((SAMPLES / "manifest.json").read_text())
    with httpx.Client(base_url=args.api, timeout=300) as c:
        email = input("Account email: ").strip()
        password = getpass.getpass("Account password: ")
        auth = c.post("/api/auth/signin", json={"email": email, "password": password})
        if auth.status_code != 200:
            print(f"Sign-in failed: {auth.status_code} {auth.text}")
            return 1
        c.headers["Authorization"] = f"Bearer {auth.json()['access_token']}"
        existing = {m["title"] for m in c.get("/api/meetings").json()}
        for m in manifest:
            if m["title"] in existing:
                print(f"skip   {m['title']} (already loaded)")
                continue
            r = c.post(
                "/api/meetings",
                files={"file": (m["file"], (SAMPLES / m["file"]).read_bytes())},
                data={"title": m["title"], "meeting_date": m["date"], "platform": m["platform"]},
            )
            if r.status_code != 201:
                print(f"FAILED {m['title']}: {r.status_code} {r.text}")
                return 1
            d = r.json()
            print(f"loaded {d['title']:<18} {d['chunk_count']} chunks, {d['decision_count']} decisions, {d['action_item_count']} actions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
