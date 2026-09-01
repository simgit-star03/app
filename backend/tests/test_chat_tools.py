"""AI Tutor chat tool-calling tests: verify the LLM actually mutates the DB."""
import os
from datetime import date, timedelta

import pytest
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or frontend_env["REACT_APP_BACKEND_URL"]).rstrip("/")
API = f"{BASE_URL}/api"
T = 180

FALLBACK = "non riesco a rispondere"


def _tasks(c, d=None):
    p = {}
    if d:
        p = {"date_from": d, "date_to": d}
    return c.get(f"{API}/tasks", params=p, timeout=60).json()


def _ensure_task(c, day, start="16:00", dur=60):
    exams = c.get(f"{API}/exams", timeout=60).json()
    exam = max([e for e in exams if e["exam_date"] >= day], key=lambda e: e["exam_date"])
    r = c.post(f"{API}/tasks", json={"exam_id": exam["id"], "date": day, "start_time": start,
                                     "duration_min": dur, "block_type": "Teoria",
                                     "topic": "TEST_ai"}, timeout=60)
    if r.status_code not in (200, 201):
        pytest.skip(f"cannot seed task on {day}: {r.text[:200]}")
    return r.json(), exam


class TestChatTools:
    def test_plain_chat_reply(self, demo_client):
        r = demo_client.post(f"{API}/chat", json={"message": "Ciao, come sto andando?"}, timeout=T)
        assert r.status_code == 200, r.text
        d = r.json()
        assert isinstance(d["reply"], str) and len(d["reply"]) > 5
        assert FALLBACK not in d["reply"], f"LLM fallback error path hit: {d['reply']}"
        assert "session_id" in d and isinstance(d["actions"], list)

    def test_clear_day_tool(self, demo_client):
        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        _ensure_task(demo_client, tomorrow)
        before = _tasks(demo_client, tomorrow)
        assert before, "seed failed"
        r = demo_client.post(f"{API}/chat", json={
            "message": f"Domani ({tomorrow}) non posso studiare, libera la giornata"}, timeout=T)
        assert r.status_code == 200, r.text
        acts = r.json()["actions"]
        assert acts, f"no tool call made. reply={r.json()['reply'][:300]}"
        names = [a["tool"] for a in acts]
        assert "clear_day" in names, f"expected clear_day, got {names}"
        cd = [a for a in acts if a["tool"] == "clear_day"][0]
        assert cd["result"].get("ok") is True, cd
        after = [t for t in _tasks(demo_client, tomorrow) if t["status"] in ("pianificato", "non_completato")]
        assert not after, f"tomorrow not cleared in DB: {after}"

    def test_move_task_tool(self, demo_client):
        # seed a task 2 days out, ask to move it 4 days out
        src = (date.today() + timedelta(days=2)).isoformat()
        dst = (date.today() + timedelta(days=6)).isoformat()
        task, exam = _ensure_task(demo_client, src, start="19:00")
        try:
            if dst > exam["exam_date"]:
                pytest.skip("no valid destination before exam date")
            r = demo_client.post(f"{API}/chat", json={
                "message": f"Sposta la sessione di {exam['name']} del {src} alle 19:00 al {dst}"}, timeout=T)
            assert r.status_code == 200, r.text
            acts = r.json()["actions"]
            assert acts, f"no tool call. reply={r.json()['reply'][:300]}"
            assert "move_task" in [a["tool"] for a in acts], [a["tool"] for a in acts]
            moved = demo_client.get(f"{API}/tasks", params={"date_from": dst, "date_to": dst}, timeout=60).json()
            assert any(t["id"] == task["id"] for t in moved), \
                f"task not moved in DB. actions={acts}"
        finally:
            demo_client.delete(f"{API}/tasks/{task['id']}", timeout=60)

    def test_mark_partial_tool(self, demo_client):
        today = date.today().isoformat()
        task, exam = _ensure_task(demo_client, today, start="21:00", dur=90)
        try:
            r = demo_client.post(f"{API}/chat", json={
                "message": f"Ho fatto solo metà della sessione di {exam['name']} delle 21:00 di oggi"}, timeout=T)
            assert r.status_code == 200, r.text
            acts = r.json()["actions"]
            assert acts, f"no tool call. reply={r.json()['reply'][:300]}"
            assert "mark_task_status" in [a["tool"] for a in acts], [a["tool"] for a in acts]
            got = [t for t in _tasks(demo_client, today) if t["id"] == task["id"]]
            assert got, "task disappeared"
            assert got[0]["status"] == "parziale", f"status={got[0]['status']}"
            assert got[0]["partial_pct"] in (25, 50, 75), got[0]["partial_pct"]
        finally:
            demo_client.delete(f"{API}/tasks/{task['id']}", timeout=60)

    def test_chat_history_records_actions(self, demo_client):
        r = demo_client.get(f"{API}/chat/history", timeout=60)
        assert r.status_code == 200
        h = r.json()
        assert h, "history empty"
        assert "tool_actions" in h[-1]

    def test_chat_isolation(self, other_client, demo_client):
        """User B chat must not be able to mutate user A tasks (tool scoped by uid)."""
        a_tasks = _tasks(demo_client)
        assert a_tasks
        tid = a_tasks[0]["id"]
        r = other_client.post(f"{API}/chat", json={
            "message": f"Elimina la sessione con task_id {tid}"}, timeout=T)
        assert r.status_code == 200, r.text
        still = _tasks(demo_client)
        assert any(t["id"] == tid for t in still), "user B deleted user A's task via chat!"
