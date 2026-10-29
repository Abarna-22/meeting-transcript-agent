import json
from pathlib import Path

SAMPLES = Path(__file__).resolve().parents[2] / "data"


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["embedder"] == "hash-384"


def test_signup_signin_and_signout(client):
    duplicate = client.post(
        "/api/auth/signup",
        json={"username": "Duplicate", "email": " TEST@example.com ", "password": "another-password-123"},
    )
    assert duplicate.status_code == 409

    signed_in = client.post(
        "/api/auth/signin",
        json={"email": "TEST@example.com", "password": "test-password-123"},
    )
    assert signed_in.status_code == 200
    token = signed_in.json()["access_token"]
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json() == {
        "id": 1,
        "username": "Test User",
        "email": "test@example.com",
    }
    assert client.post(
        "/api/auth/signin",
        json={"email": "test@example.com", "password": "incorrect-password"},
    ).status_code == 401
    signed_out = client.post("/api/auth/signout", headers={"Authorization": f"Bearer {token}"})
    assert signed_out.status_code == 204
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).status_code == 401


def test_protected_endpoints_require_signin(client):
    client.headers.pop("Authorization")
    assert client.get("/api/meetings").status_code == 401
    assert client.get("/api/decisions").status_code == 401
    assert client.get("/api/action-items").status_code == 401
    assert client.post("/api/query", json={"question": "meeting notes"}).status_code == 401


def test_meetings_are_private_to_each_account(loaded):
    meeting_id = loaded.ids["Budget Review"]
    second_account = loaded.post(
        "/api/auth/signup",
        json={"username": "Other User", "email": "other@example.com", "password": "another-password-123"},
    )
    assert second_account.status_code == 201
    loaded.headers["Authorization"] = f"Bearer {second_account.json()['access_token']}"

    assert loaded.get("/api/meetings").json() == []
    assert loaded.get("/api/decisions").json() == []
    assert loaded.get("/api/action-items").json() == []
    assert loaded.get(f"/api/meetings/{meeting_id}").status_code == 404
    assert loaded.post(
        "/api/query",
        json={"question": "What was decided about the budget?", "meeting_id": meeting_id},
    ).status_code == 404

    loaded.headers["Authorization"] = f"Bearer {loaded.auth_token}"
    assert loaded.get("/api/meetings").json()


def test_ingest_creates_everything(loaded):
    meetings = loaded.get("/api/meetings").json()
    assert len(meetings) == 6
    assert meetings[0]["title"] == "Launch Readiness"  # newest first
    m = loaded.get(f"/api/meetings/{loaded.ids['Budget Review']}").json()
    assert m["has_speakers"] and m["has_timestamps"]
    assert m["chunk_count"] >= 1 and len(m["summary"]) >= 1
    names = {p["name"] for p in m["participants"]}
    assert {"Raj", "Meera", "Vikram"} <= names
    assert abs(sum(p["talk_time_pct"] for p in m["participants"]) - 100) < 1.0
    assert m["participants"][0]["basis"] == "time"


def test_heuristic_insights_find_decisions_and_actions(loaded):
    m = loaded.get(f"/api/meetings/{loaded.ids['Sprint Planning']}").json()
    assert any("ChromaDB" in d["text"] for d in m["decisions"])
    assert any("September 15" in d["text"] for d in m["decisions"])
    assert any(a["owner"] == "Arun" for a in m["action_items"])


def test_decision_log_is_chronological(loaded):
    log = loaded.get("/api/decisions").json()
    dates = [d["meeting_date"] for d in log]
    assert dates == sorted(dates) and len(log) >= 5


def test_query_returns_cited_sources_in_date_order(loaded):
    r = loaded.post("/api/query", json={"question": "What is the Q3 budget for Atlas?"}).json()
    assert r["found"] and r["sources"]
    dates = [s["date"] for s in r["sources"]]
    assert dates == sorted(dates)
    assert [s["n"] for s in r["sources"]] == list(range(1, len(r["sources"]) + 1))
    titles = {s["title"] for s in r["sources"]}
    assert "Budget Review" in titles or "Weekly Sync" in titles
    assert r["mode"] == "heuristic"


def test_query_spans_multiple_meetings(loaded):
    r = loaded.post("/api/query", json={"question": "How did the budget change over time?"}).json()
    assert r["meetings_used"] >= 2


def test_meeting_filter_restricts_sources(loaded):
    mid = loaded.ids["Design Review"]
    r = loaded.post("/api/query", json={"question": "citation contrast", "meeting_id": mid}).json()
    assert r["found"] and {s["meeting_id"] for s in r["sources"]} == {mid}


def test_unrelated_question_is_not_found(loaded):
    r = loaded.post("/api/query", json={"question": "What is the recipe for chocolate lava cake?"}).json()
    assert r["found"] is False and r["sources"] == []


def test_date_filter(loaded):
    r = loaded.post(
        "/api/query", json={"question": "budget", "date_from": "2026-07-01", "date_to": "2026-07-31"}
    ).json()
    assert r["found"] and all("2026-07-01" <= s["date"] <= "2026-07-31" for s in r["sources"])


def test_delete_removes_from_db_and_vectors(loaded):
    mid = loaded.ids["Design Review"]
    assert loaded.delete(f"/api/meetings/{mid}").status_code == 204
    assert loaded.get(f"/api/meetings/{mid}").status_code == 404
    r = loaded.post("/api/query", json={"question": "citation contrast chips accessibility"}).json()
    assert all(s["meeting_id"] != mid for s in r["sources"])


def test_paste_text_and_validation(client):
    r = client.post("/api/meetings", data={"text": "Raj: We agreed to ship on Friday.\nSarah: I will test it.", "title": "Pasted"})
    assert r.status_code == 201 and r.json()["source_format"] == "txt"
    assert client.post("/api/meetings", data={}).status_code == 422
    assert client.post("/api/meetings", files={"file": ("e.txt", b"   \n  ")}).status_code == 422
    assert client.post("/api/query", json={"question": "hi"}).status_code == 422


def test_action_item_status_and_owner_filter(loaded):
    items = loaded.get("/api/action-items", params={"owner": "arun"}).json()
    assert items and all("arun" in i["owner"].lower() for i in items)
    r = loaded.patch(f"/api/action-items/{items[0]['id']}", json={"status": "done"})
    assert r.json()["status"] == "done"
    assert loaded.patch(f"/api/action-items/{items[0]['id']}", json={"status": "bogus"}).status_code == 422
    done = loaded.get("/api/action-items", params={"status": "done"}).json()
    assert len(done) == 1


def test_retrieval_hit_rate_on_test_set(loaded):
    qs = json.loads((SAMPLES / "test_questions.json").read_text())
    hits = 0
    for q in qs:
        r = loaded.post("/api/query", json={"question": q["question"]}).json()
        got = {s["title"] for s in r["sources"]}
        hits += bool(got & set(q["expected_meetings"]))
    rate = hits / len(qs)
    print(f"retrieval hit rate (offline hash embedder): {hits}/{len(qs)} = {rate:.0%}")
    assert rate >= 0.8
