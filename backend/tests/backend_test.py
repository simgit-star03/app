"""StudyFlow backend regression tests - iteration 2.
Covers: task CRUD (POST/PATCH/PUT/DELETE), partial_pct + progress math,
plan generate/replan quality, exam date shrink, auth isolation.
AI chat tool-calling tests live in test_chat_tools.py.
"""
import os
from datetime import date, timedelta

import pytest
import requests
from dotenv import dotenv_values

frontend_env = dotenv_values("/app/frontend/.env")
BASE_URL = (os.environ.get("REACT_APP_BACKEND_URL") or frontend_env["REACT_APP_BACKEND_URL"]).rstrip("/")
API = f"{BASE_URL}/api"
T = 90


def _mins(t):
    h, m = t.split(":")
    return int(h) * 60 + int(m)


# ---------- helpers ----------
def _exams(c):
    r = c.get(f"{API}/exams", timeout=T)
    assert r.status_code == 200, r.text
    return r.json()


def _free_day_for(c, exam, offset_start=1):
    """Find a future date <= exam_date that has no tasks, else return a date with tasks."""
    tasks = c.get(f"{API}/tasks", timeout=T).json()
    busy_days = {t["date"] for t in tasks}
    for i in range(offset_start, 40):
        d = (date.today() + timedelta(days=i)).isoformat()
        if d > exam["exam_date"]:
            break
        if d not in busy_days:
            return d
    return None


# ============ HEALTH / AUTH ============
class TestHealth:
    def test_login_and_me(self, demo_client):
        r = demo_client.get(f"{API}/auth/me", timeout=T)
        assert r.status_code == 200
        assert r.json()["email"] == "demo@studyflow.it"

    def test_no_mongo_id_leak(self, demo_client):
        for ep in ["/exams", "/tasks", "/tasks/today"]:
            r = demo_client.get(f"{API}{ep}", timeout=T)
            assert r.status_code == 200, ep
            for item in r.json():
                assert "_id" not in item.keys(), f"_id leaked in {ep}"


# ============ TASK CREATE ============
class TestTaskCreate:
    def test_create_success_and_persist(self, demo_client):
        exams = _exams(demo_client)
        assert exams, "demo user must have exams"
        exam = max(exams, key=lambda e: e["exam_date"])
        d = _free_day_for(demo_client, exam)
        assert d, "no free day found"
        payload = {"exam_id": exam["id"], "date": d, "start_time": "08:00",
                   "duration_min": 90, "block_type": "Esercizi", "topic": "TEST_create"}
        r = demo_client.post(f"{API}/tasks", json=payload, timeout=T)
        assert r.status_code in (200, 201), r.text
        doc = r.json()
        assert doc["end_time"] == "09:30"
        assert doc["status"] == "pianificato"
        assert doc["exam_name"] == exam["name"]
        assert doc["block_type"] == "Esercizi"
        # persisted?
        allt = demo_client.get(f"{API}/tasks", params={"date_from": d, "date_to": d}, timeout=T).json()
        assert any(t["id"] == doc["id"] and t["topic"] == "TEST_create" for t in allt)
        demo_client.delete(f"{API}/tasks/{doc['id']}", timeout=T)

    def test_create_overlap_rejected(self, demo_client):
        exams = _exams(demo_client)
        exam = max(exams, key=lambda e: e["exam_date"])
        d = _free_day_for(demo_client, exam)
        base = demo_client.post(f"{API}/tasks", json={
            "exam_id": exam["id"], "date": d, "start_time": "10:00",
            "duration_min": 90, "block_type": "Teoria", "topic": "TEST_base"}, timeout=T)
        assert base.status_code in (200, 201), base.text
        bid = base.json()["id"]
        try:
            r = demo_client.post(f"{API}/tasks", json={
                "exam_id": exam["id"], "date": d, "start_time": "11:00",
                "duration_min": 60, "block_type": "Teoria", "topic": "TEST_overlap"}, timeout=T)
            assert r.status_code == 400, f"expected 400, got {r.status_code}: {r.text}"
            assert "ovrappos" in r.text
        finally:
            demo_client.delete(f"{API}/tasks/{bid}", timeout=T)

    def test_create_after_exam_date_rejected(self, demo_client):
        exams = _exams(demo_client)
        exam = exams[0]
        after = (date.fromisoformat(exam["exam_date"]) + timedelta(days=3)).isoformat()
        r = demo_client.post(f"{API}/tasks", json={
            "exam_id": exam["id"], "date": after, "start_time": "08:00",
            "duration_min": 60, "block_type": "Teoria", "topic": "TEST_late"}, timeout=T)
        assert r.status_code == 400, r.text
        assert "dopo l'esame" in r.text

    def test_create_unknown_exam_404(self, demo_client):
        r = demo_client.post(f"{API}/tasks", json={
            "exam_id": "does-not-exist", "date": (date.today() + timedelta(days=2)).isoformat(),
            "start_time": "08:00", "duration_min": 60, "block_type": "Teoria", "topic": "x"}, timeout=T)
        assert r.status_code == 404, r.text

    def test_create_requires_auth(self):
        r = requests.post(f"{API}/tasks", json={"exam_id": "x", "date": "2026-08-01",
                                                "start_time": "08:00"}, timeout=T)
        assert r.status_code == 401


# ============ TASK PATCH (edit) ============
class TestTaskEdit:
    @pytest.fixture
    def temp_task(self, demo_client):
        exams = _exams(demo_client)
        exam = max(exams, key=lambda e: e["exam_date"])
        d = _free_day_for(demo_client, exam)
        r = demo_client.post(f"{API}/tasks", json={
            "exam_id": exam["id"], "date": d, "start_time": "08:00",
            "duration_min": 60, "block_type": "Teoria", "topic": "TEST_edit"}, timeout=T)
        assert r.status_code in (200, 201), r.text
        t = r.json()
        yield t, exam, d
        demo_client.delete(f"{API}/tasks/{t['id']}", timeout=T)

    def test_patch_all_fields(self, demo_client, temp_task):
        t, exam, d = temp_task
        r = demo_client.patch(f"{API}/tasks/{t['id']}", json={
            "start_time": "14:00", "duration_min": 120,
            "block_type": "Simulazione", "topic": "TEST_edited"}, timeout=T)
        assert r.status_code == 200, r.text
        u = r.json()
        assert u["start_time"] == "14:00"
        assert u["duration_min"] == 120
        assert u["end_time"] == "16:00", f"end_time not recomputed: {u['end_time']}"
        assert u["block_type"] == "Simulazione"
        assert u["topic"] == "TEST_edited"
        # verify via GET
        g = demo_client.get(f"{API}/tasks", params={"date_from": d, "date_to": d}, timeout=T).json()
        got = [x for x in g if x["id"] == t["id"]][0]
        assert got["end_time"] == "16:00" and got["topic"] == "TEST_edited"

    def test_patch_move_date(self, demo_client, temp_task):
        t, exam, d = temp_task
        newd = _free_day_for(demo_client, exam, offset_start=1)
        # pick a different free day
        cand = [x for x in range(1, 40)]
        target = None
        tasks = demo_client.get(f"{API}/tasks", timeout=T).json()
        busy = {x["date"] for x in tasks if x["id"] != t["id"]}
        for i in cand:
            dd = (date.today() + timedelta(days=i)).isoformat()
            if dd > exam["exam_date"]:
                break
            if dd not in busy and dd != t["date"]:
                target = dd
                break
        assert target, "no alternative free day"
        r = demo_client.patch(f"{API}/tasks/{t['id']}", json={"date": target}, timeout=T)
        assert r.status_code == 200, r.text
        assert r.json()["date"] == target

    def test_patch_change_exam(self, demo_client, temp_task):
        t, exam, d = temp_task
        exams = _exams(demo_client)
        other = [e for e in exams if e["id"] != exam["id"] and e["exam_date"] >= t["date"]]
        if not other:
            pytest.skip("no alternative exam with later date")
        r = demo_client.patch(f"{API}/tasks/{t['id']}", json={"exam_id": other[0]["id"]}, timeout=T)
        assert r.status_code == 200, r.text
        assert r.json()["exam_id"] == other[0]["id"]
        assert r.json()["exam_name"] == other[0]["name"]

    def test_patch_overlap_rejected(self, demo_client, temp_task):
        t, exam, d = temp_task
        second = demo_client.post(f"{API}/tasks", json={
            "exam_id": exam["id"], "date": t["date"], "start_time": "12:00",
            "duration_min": 60, "block_type": "Teoria", "topic": "TEST_second"}, timeout=T)
        assert second.status_code in (200, 201), second.text
        sid = second.json()["id"]
        try:
            r = demo_client.patch(f"{API}/tasks/{t['id']}", json={"start_time": "12:30"}, timeout=T)
            assert r.status_code == 400, f"expected overlap 400 got {r.status_code}: {r.text}"
        finally:
            demo_client.delete(f"{API}/tasks/{sid}", timeout=T)

    def test_patch_after_exam_date_rejected(self, demo_client, temp_task):
        t, exam, d = temp_task
        after = (date.fromisoformat(exam["exam_date"]) + timedelta(days=5)).isoformat()
        r = demo_client.patch(f"{API}/tasks/{t['id']}", json={"date": after}, timeout=T)
        assert r.status_code == 400, r.text

    def test_patch_invalid_block_type_422(self, demo_client, temp_task):
        t, _, _ = temp_task
        r = demo_client.patch(f"{API}/tasks/{t['id']}", json={"block_type": "Bogus"}, timeout=T)
        assert r.status_code == 422, r.text

    def test_patch_unknown_task_404(self, demo_client):
        r = demo_client.patch(f"{API}/tasks/nope-{'x'*8}", json={"topic": "y"}, timeout=T)
        assert r.status_code == 404


# ============ DELETE ============
class TestTaskDelete:
    def test_delete_and_gone(self, demo_client):
        exams = _exams(demo_client)
        exam = max(exams, key=lambda e: e["exam_date"])
        d = _free_day_for(demo_client, exam)
        r = demo_client.post(f"{API}/tasks", json={
            "exam_id": exam["id"], "date": d, "start_time": "09:00",
            "duration_min": 60, "block_type": "Teoria", "topic": "TEST_del"}, timeout=T)
        tid = r.json()["id"]
        dr = demo_client.delete(f"{API}/tasks/{tid}", timeout=T)
        assert dr.status_code == 200, dr.text
        assert dr.json().get("ok") is True
        rest = demo_client.get(f"{API}/tasks", params={"date_from": d, "date_to": d}, timeout=T).json()
        assert all(x["id"] != tid for x in rest)
        # second delete -> 404
        assert demo_client.delete(f"{API}/tasks/{tid}", timeout=T).status_code == 404


# ============ STATUS / PARTIAL PCT & PROGRESS MATH ============
class TestStatusAndProgress:
    @pytest.fixture
    def today_task(self, demo_client):
        """Create an isolated task today (or nearest allowed day) for status math."""
        exams = _exams(demo_client)
        exam = max(exams, key=lambda e: e["exam_date"])
        today = date.today().isoformat()
        # find free slot today
        existing = demo_client.get(f"{API}/tasks", params={"date_from": today, "date_to": today}, timeout=T).json()
        busy = sorted([(_mins(t["start_time"]), _mins(t["start_time"]) + t.get("duration_min", 90)) for t in existing])
        cursor = 6 * 60
        start = None
        for bs, be in busy:
            if bs - cursor >= 90:
                start = cursor
                break
            cursor = max(cursor, be + 15)
        if start is None:
            start = cursor
        hhmm = f"{start//60:02d}:{start%60:02d}"
        r = demo_client.post(f"{API}/tasks", json={
            "exam_id": exam["id"], "date": today, "start_time": hhmm,
            "duration_min": 90, "block_type": "Teoria", "topic": "TEST_status"}, timeout=T)
        assert r.status_code in (200, 201), r.text
        t = r.json()
        yield t
        demo_client.delete(f"{API}/tasks/{t['id']}", timeout=T)

    @pytest.mark.parametrize("pct", [25, 50, 75])
    def test_partial_pct_persist_and_progress(self, demo_client, today_task, pct):
        before = demo_client.get(f"{API}/progress", timeout=T).json()["week_completed_hours"]
        r = demo_client.put(f"{API}/tasks/{today_task['id']}",
                            json={"status": "parziale", "partial_pct": pct}, timeout=T)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "parziale"
        assert r.json()["partial_pct"] == pct
        # persistence
        g = demo_client.get(f"{API}/tasks/today", timeout=T).json()
        got = [x for x in g if x["id"] == today_task["id"]][0]
        assert got["partial_pct"] == pct
        after = demo_client.get(f"{API}/progress", timeout=T).json()["week_completed_hours"]
        expected_delta = round(90 * pct / 100 / 60, 1)
        assert abs((after - before) - expected_delta) < 0.15, \
            f"progress delta {after-before} != expected {expected_delta} (pct={pct})"

    def test_partial_invalid_pct_falls_back_50(self, demo_client, today_task):
        r = demo_client.put(f"{API}/tasks/{today_task['id']}",
                            json={"status": "parziale", "partial_pct": 33}, timeout=T)
        assert r.status_code == 200, r.text
        assert r.json()["partial_pct"] == 50

    def test_completato_then_non_completato(self, demo_client, today_task):
        base = demo_client.get(f"{API}/progress", timeout=T).json()["week_completed_hours"]
        r = demo_client.put(f"{API}/tasks/{today_task['id']}", json={"status": "completato"}, timeout=T)
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "completato"
        assert r.json()["partial_pct"] is None
        full = demo_client.get(f"{API}/progress", timeout=T).json()["week_completed_hours"]
        assert abs((full - base) - 1.5) < 0.15, f"completato delta {full-base} != 1.5"
        r2 = demo_client.put(f"{API}/tasks/{today_task['id']}", json={"status": "non_completato"}, timeout=T)
        assert r2.status_code == 200
        zero = demo_client.get(f"{API}/progress", timeout=T).json()["week_completed_hours"]
        assert abs(zero - base) < 0.15, f"non_completato should revert to {base}, got {zero}"

    def test_invalid_status_422(self, demo_client, today_task):
        r = demo_client.put(f"{API}/tasks/{today_task['id']}", json={"status": "bogus"}, timeout=T)
        assert r.status_code == 422

    def test_progress_shape(self, demo_client):
        r = demo_client.get(f"{API}/progress", timeout=T)
        assert r.status_code == 200
        d = r.json()
        assert len(d["daily"]) == 7
        assert 0 <= d["completion_percent"] <= 100
        for day in d["daily"]:
            assert day["completed_hours"] <= day["planned_hours"] + 0.01

    def test_exam_prep_recomputed_on_status(self, demo_client, today_task):
        eid = today_task["exam_id"]
        before = [e for e in _exams(demo_client) if e["id"] == eid][0]["prep_percent"]
        demo_client.put(f"{API}/tasks/{today_task['id']}", json={"status": "completato"}, timeout=T)
        after = [e for e in _exams(demo_client) if e["id"] == eid][0]["prep_percent"]
        assert after >= before, f"prep_percent decreased {before}->{after}"


# ============ PLAN GENERATE / REPLAN ============
class TestPlan:
    def _validate(self, demo_client, tasks):
        exams = {e["id"]: e for e in _exams(demo_client)}
        allowed = {"Teoria", "Esercizi", "Ripasso", "Simulazione", "Altro"}
        by_day = {}
        for t in tasks:
            assert t["block_type"] in allowed, t["block_type"]
            e = exams.get(t["exam_id"])
            assert e, f"task references unknown exam {t['exam_id']}"
            assert t["date"] <= e["exam_date"], f"task {t['date']} after exam {e['exam_date']}"
            by_day.setdefault(t["date"], []).append(t)
        for d, lst in by_day.items():
            iv = sorted([(_mins(x["start_time"]), _mins(x["start_time"]) + x["duration_min"]) for x in lst])
            for i in range(1, len(iv)):
                assert iv[i][0] >= iv[i - 1][1], f"overlap on {d}: {iv}"

    def test_generate_plan_quality(self, demo_client):
        r = demo_client.post(f"{API}/plan/generate", timeout=180)
        assert r.status_code == 200, r.text
        data = r.json()
        assert data["count"] >= 10, f"only {data['count']} tasks generated"
        self._validate(demo_client, data["tasks"])

    def test_generated_plan_no_overlap_with_all_db_tasks(self, demo_client):
        today = date.today().isoformat()
        tasks = demo_client.get(f"{API}/tasks", params={"date_from": today}, timeout=T).json()
        self._validate(demo_client, tasks)

    def test_daily_hours_cap(self, demo_client):
        prof = demo_client.get(f"{API}/profile", timeout=T).json()
        cap_min = float(prof.get("daily_hours", 4)) * 60
        today = date.today().isoformat()
        tasks = demo_client.get(f"{API}/tasks", params={"date_from": today}, timeout=T).json()
        per_day = {}
        for t in tasks:
            per_day[t["date"]] = per_day.get(t["date"], 0) + t.get("duration_min", 90)
        offenders = {d: m for d, m in per_day.items() if m > cap_min + 1}
        assert not offenders, f"daily_hours cap {cap_min}min exceeded: {offenders}"

    def test_available_days_respected(self, demo_client):
        prof = demo_client.get(f"{API}/profile", timeout=T).json()
        avail = set(prof.get("available_days") or [])
        if not avail:
            pytest.skip("no available_days")
        names = ["lun", "mar", "mer", "gio", "ven", "sab", "dom"]
        today = date.today().isoformat()
        tasks = demo_client.get(f"{API}/tasks", params={"date_from": today}, timeout=T).json()
        bad = [t["date"] for t in tasks
               if t["status"] == "pianificato" and names[date.fromisoformat(t["date"]).weekday()] not in avail]
        assert not bad, f"tasks planned on unavailable days: {sorted(set(bad))}"

    def test_replan_keeps_completed(self, demo_client):
        today = date.today().isoformat()
        tasks = demo_client.get(f"{API}/tasks", params={"date_from": today}, timeout=T).json()
        assert tasks, "need future tasks"
        target = tasks[0]
        demo_client.put(f"{API}/tasks/{target['id']}", json={"status": "completato"}, timeout=T)
        target2 = tasks[1] if len(tasks) > 1 else None
        if target2:
            demo_client.put(f"{API}/tasks/{target2['id']}", json={"status": "parziale", "partial_pct": 50}, timeout=T)
        r = demo_client.post(f"{API}/plan/replan", json={"reason": "Sono rimasto indietro"}, timeout=180)
        assert r.status_code == 200, r.text
        assert r.json()["count"] >= 1
        after = demo_client.get(f"{API}/tasks", params={"date_from": today}, timeout=T).json()
        ids = {x["id"]: x for x in after}
        assert target["id"] in ids, "completato task was deleted by replan"
        assert ids[target["id"]]["status"] == "completato"
        if target2:
            assert target2["id"] in ids, "parziale task was deleted by replan"
        self._validate(demo_client, after)

    def test_replan_requires_auth(self):
        assert requests.post(f"{API}/plan/replan", json={}, timeout=T).status_code == 401


# ============ EXAM DATE SHRINK ============
class TestExamDateShrink:
    def test_moving_exam_earlier_drops_late_tasks(self, demo_client):
        # create own exam + tasks so we don't destroy demo data
        far = (date.today() + timedelta(days=30)).isoformat()
        e = demo_client.post(f"{API}/exams", json={
            "name": "TEST_ShrinkExam", "exam_date": far, "cfu": 6,
            "difficulty": "Media", "prep_percent": 0, "estimated_hours": 20}, timeout=T)
        assert e.status_code in (200, 201), e.text
        exam = e.json()
        try:
            d_late = (date.today() + timedelta(days=25)).isoformat()
            d_early = (date.today() + timedelta(days=5)).isoformat()
            t_late = demo_client.post(f"{API}/tasks", json={
                "exam_id": exam["id"], "date": d_late, "start_time": "20:00",
                "duration_min": 60, "block_type": "Teoria", "topic": "TEST_late_t"}, timeout=T)
            t_early = demo_client.post(f"{API}/tasks", json={
                "exam_id": exam["id"], "date": d_early, "start_time": "20:00",
                "duration_min": 60, "block_type": "Teoria", "topic": "TEST_early_t"}, timeout=T)
            assert t_late.status_code in (200, 201), t_late.text
            assert t_early.status_code in (200, 201), t_early.text
            new_date = (date.today() + timedelta(days=10)).isoformat()
            u = demo_client.put(f"{API}/exams/{exam['id']}", json={"exam_date": new_date}, timeout=T)
            assert u.status_code == 200, u.text
            assert u.json()["exam_date"] == new_date
            remaining = demo_client.get(f"{API}/tasks", timeout=T).json()
            ids = {x["id"] for x in remaining}
            assert t_late.json()["id"] not in ids, "task after new exam_date was not deleted"
            assert t_early.json()["id"] in ids, "task before exam_date wrongly deleted"
        finally:
            demo_client.delete(f"{API}/exams/{exam['id']}", timeout=T)


# ============ AUTH ISOLATION ============
class TestAuthIsolation:
    def test_user_b_cannot_touch_user_a_task(self, demo_client, other_client):
        tasks = demo_client.get(f"{API}/tasks", timeout=T).json()
        assert tasks
        tid = tasks[0]["id"]
        assert other_client.patch(f"{API}/tasks/{tid}", json={"topic": "HACK"}, timeout=T).status_code == 404
        assert other_client.put(f"{API}/tasks/{tid}", json={"status": "completato"}, timeout=T).status_code == 404
        assert other_client.delete(f"{API}/tasks/{tid}", timeout=T).status_code == 404
        # still intact
        still = demo_client.get(f"{API}/tasks", timeout=T).json()
        assert any(x["id"] == tid for x in still)

    def test_user_b_cannot_create_on_user_a_exam(self, demo_client, other_client):
        exam = _exams(demo_client)[0]
        r = other_client.post(f"{API}/tasks", json={
            "exam_id": exam["id"], "date": (date.today() + timedelta(days=1)).isoformat(),
            "start_time": "08:00", "duration_min": 60, "block_type": "Teoria", "topic": "HACK"}, timeout=T)
        assert r.status_code == 404, r.text

    def test_user_b_task_list_empty_of_a(self, demo_client, other_client):
        a_ids = {x["id"] for x in demo_client.get(f"{API}/tasks", timeout=T).json()}
        b_ids = {x["id"] for x in other_client.get(f"{API}/tasks", timeout=T).json()}
        assert not (a_ids & b_ids)
