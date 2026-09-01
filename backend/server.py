from fastapi import FastAPI, APIRouter, HTTPException, Depends, Header
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import json
import re
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Literal
import uuid
from datetime import datetime, timezone, timedelta, date
import bcrypt
import jwt as pyjwt
from emergentintegrations.llm.chat import LlmChat, UserMessage

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

JWT_SECRET = os.environ['JWT_SECRET']
JWT_ALG = "HS256"
EMERGENT_LLM_KEY = os.environ['EMERGENT_LLM_KEY']

app = FastAPI(title="StudyFlow API")
api_router = APIRouter(prefix="/api")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("studyflow")

# ============ MODELS ============

Difficulty = Literal["Facile", "Media", "Difficile"]
TaskStatus = Literal["completato", "parziale", "non_completato", "pianificato"]
BlockType = Literal["Teoria", "Esercizi", "Ripasso", "Simulazione", "Altro"]


class SignupIn(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    name: Optional[str] = None
    onboarded: bool = False


class OnboardingIn(BaseModel):
    name: str
    university: str
    degree_course: str
    daily_hours: float
    available_days: List[str]  # ["lun","mar",...]
    graduation_goal: Optional[str] = None


class ExamIn(BaseModel):
    name: str
    exam_date: str  # ISO date
    cfu: int
    difficulty: Difficulty
    prep_percent: int = 0
    estimated_hours: int
    notes: Optional[str] = None


class Exam(ExamIn):
    id: str
    user_id: str
    created_at: str


class TaskUpdate(BaseModel):
    status: TaskStatus
    actual_minutes: Optional[int] = None
    partial_pct: Optional[int] = None  # 25/50/75 when status=parziale


class TaskEditIn(BaseModel):
    exam_id: Optional[str] = None
    date: Optional[str] = None
    start_time: Optional[str] = None
    duration_min: Optional[int] = None
    block_type: Optional[BlockType] = None
    topic: Optional[str] = None


class TaskCreateIn(BaseModel):
    exam_id: str
    date: str
    start_time: str
    duration_min: int = 90
    block_type: BlockType = "Teoria"
    topic: str = "Studio"


class StudyTask(BaseModel):
    id: str
    user_id: str
    exam_id: str
    exam_name: str
    date: str  # YYYY-MM-DD
    start_time: str  # HH:MM
    end_time: str
    block_type: BlockType
    topic: str
    status: TaskStatus = "pianificato"
    duration_min: int


class ChatIn(BaseModel):
    message: str
    session_id: Optional[str] = None


class ReplanIn(BaseModel):
    reason: Optional[str] = "Sono rimasto indietro"


# ============ HELPERS ============

def hash_pw(pw: str) -> str:
    return bcrypt.hashpw(pw.encode(), bcrypt.gensalt()).decode()


def verify_pw(pw: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(pw.encode(), hashed.encode())
    except Exception:
        return False


def make_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(days=30),
        "iat": datetime.now(timezone.utc),
    }
    return pyjwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Non autorizzato")
    token = authorization.split(" ", 1)[1]
    try:
        payload = pyjwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
    except Exception:
        raise HTTPException(401, "Token non valido")
    uid = payload.get("sub")
    user = await db.users.find_one({"id": uid}, {"_id": 0, "password": 0})
    if not user:
        raise HTTPException(401, "Utente non trovato")
    return user


def user_out(u: dict) -> UserOut:
    return UserOut(
        id=u["id"],
        email=u["email"],
        name=u.get("name"),
        onboarded=u.get("onboarded", False),
    )


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ============ AUTH ============

@api_router.post("/auth/signup")
async def signup(inp: SignupIn):
    existing = await db.users.find_one({"email": inp.email.lower()})
    if existing:
        raise HTTPException(400, "Email già registrata")
    uid = str(uuid.uuid4())
    doc = {
        "id": uid,
        "email": inp.email.lower(),
        "password": hash_pw(inp.password),
        "name": inp.name,
        "onboarded": False,
        "university": None,
        "degree_course": None,
        "daily_hours": 4,
        "available_days": ["lun", "mar", "mer", "gio", "ven"],
        "graduation_goal": None,
        "created_at": now_iso(),
    }
    await db.users.insert_one(doc)
    token = make_token(uid)
    return {"token": token, "user": user_out(doc).model_dump()}


@api_router.post("/auth/login")
async def login(inp: LoginIn):
    u = await db.users.find_one({"email": inp.email.lower()})
    if not u or not verify_pw(inp.password, u["password"]):
        raise HTTPException(401, "Email o password non corretti")
    token = make_token(u["id"])
    return {"token": token, "user": user_out(u).model_dump()}


@api_router.get("/auth/me")
async def me(user: dict = Depends(get_current_user)):
    return user_out(user).model_dump()


@api_router.post("/auth/onboarding")
async def onboarding(inp: OnboardingIn, user: dict = Depends(get_current_user)):
    await db.users.update_one(
        {"id": user["id"]},
        {"$set": {
            "name": inp.name,
            "university": inp.university,
            "degree_course": inp.degree_course,
            "daily_hours": inp.daily_hours,
            "available_days": inp.available_days,
            "graduation_goal": inp.graduation_goal,
            "onboarded": True,
        }},
    )
    return {"ok": True}


@api_router.get("/profile")
async def get_profile(user: dict = Depends(get_current_user)):
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password": 0})
    return u


@api_router.put("/profile")
async def update_profile(data: dict, user: dict = Depends(get_current_user)):
    allowed = {"name", "university", "degree_course", "daily_hours",
               "available_days", "graduation_goal"}
    upd = {k: v for k, v in data.items() if k in allowed}
    if upd:
        await db.users.update_one({"id": user["id"]}, {"$set": upd})
    u = await db.users.find_one({"id": user["id"]}, {"_id": 0, "password": 0})
    return u


# ============ EXAMS ============

@api_router.get("/exams")
async def list_exams(user: dict = Depends(get_current_user)):
    exams = await db.exams.find({"user_id": user["id"]}, {"_id": 0}).to_list(500)
    exams.sort(key=lambda e: e["exam_date"])
    return exams


@api_router.post("/exams")
async def create_exam(inp: ExamIn, user: dict = Depends(get_current_user)):
    doc = inp.model_dump()
    doc["id"] = str(uuid.uuid4())
    doc["user_id"] = user["id"]
    doc["initial_prep"] = int(doc.get("prep_percent", 0))
    doc["created_at"] = now_iso()
    await db.exams.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api_router.put("/exams/{exam_id}")
async def update_exam(exam_id: str, data: dict, user: dict = Depends(get_current_user)):
    allowed = {"name", "exam_date", "cfu", "difficulty", "prep_percent",
               "estimated_hours", "notes"}
    upd = {k: v for k, v in data.items() if k in allowed}
    # if user explicitly changes prep_percent, reset baseline
    if "prep_percent" in upd:
        upd["initial_prep"] = int(upd["prep_percent"])
    r = await db.exams.update_one({"id": exam_id, "user_id": user["id"]}, {"$set": upd})
    if r.matched_count == 0:
        raise HTTPException(404, "Esame non trovato")
    # If exam_date moved earlier, drop tasks scheduled after it
    if "exam_date" in upd:
        await db.tasks.delete_many({
            "user_id": user["id"], "exam_id": exam_id,
            "date": {"$gt": upd["exam_date"]},
        })
    exam = await db.exams.find_one({"id": exam_id}, {"_id": 0})
    return exam


@api_router.delete("/exams/{exam_id}")
async def delete_exam(exam_id: str, user: dict = Depends(get_current_user)):
    await db.exams.delete_one({"id": exam_id, "user_id": user["id"]})
    await db.tasks.delete_many({"exam_id": exam_id, "user_id": user["id"]})
    return {"ok": True}


# ============ STUDY PLAN AI ============

async def _generate_plan(user: dict, exams: list, days_ahead: int = 14,
                          start_date: Optional[date] = None,
                          existing_tasks: Optional[list] = None) -> list:
    """Generate a validated study plan. Prefer deterministic planner (reliable),
    optionally enrich topics using LLM if available."""
    if not exams:
        return []
    if start_date is None:
        start_date = date.today()
    existing_tasks = existing_tasks or []
    # Use deterministic planner which enforces: no overlaps, respects exam dates,
    # respects available_days & daily_hours, considers prep_percent for remaining work.
    tasks = _fallback_plan(user, exams, days_ahead, start_date, existing_tasks=existing_tasks)

    # Try to enrich topics via LLM (best-effort, non-blocking on failure)
    if tasks:
        try:
            topics_prompt = (
                "Per ognuna di queste sessioni di studio universitario italiano, suggerisci un argomento "
                "concreto (max 8 parole) coerente con l'esame. Rispondi SOLO JSON: "
                '{"topics": ["argomento 1", ...]} nello stesso ordine.\n\nSessioni:\n'
                + json.dumps([
                    {"esame": t["exam_name"], "tipo": t["block_type"], "data": t["date"]}
                    for t in tasks[:40]
                ], ensure_ascii=False)
            )
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"topics-{user['id']}-{uuid.uuid4()}",
                system_message="Sei un docente universitario. Rispondi solo con JSON valido.",
            ).with_model("anthropic", "claude-sonnet-4-6").with_params(max_tokens=1500)
            resp = await chat.send_message(UserMessage(text=topics_prompt))
            content = resp if isinstance(resp, str) else str(resp)
            m = re.search(r"\{[\s\S]*\}", content)
            if m:
                data = json.loads(m.group(0))
                topics = data.get("topics", [])
                for i, t in enumerate(tasks[:len(topics)]):
                    if topics[i]:
                        t["topic"] = str(topics[i])[:80]
        except Exception as ex:
            logger.info(f"topic enrichment skipped: {ex}")
    return tasks


def _fallback_plan(user, exams, days_ahead, start_date, existing_tasks=None):
    """Deterministic planner. Respects exam dates, avoids overlaps, distributes by urgency."""
    day_map = {"lun": 0, "mar": 1, "mer": 2, "gio": 3, "ven": 4, "sab": 5, "dom": 6}
    avail = {day_map[d] for d in user.get("available_days", ["lun","mar","mer","gio","ven"]) if d in day_map}
    daily_hours = float(user.get("daily_hours", 4))
    max_daily_min = int(daily_hours * 60)

    # Existing tasks per date (to avoid overlaps and respect daily limit)
    busy_by_day = {}
    for t in (existing_tasks or []):
        busy_by_day.setdefault(t["date"], []).append(t)

    # Compute remaining hours per exam
    exam_remaining = {}
    for e in exams:
        est_total_min = int(e.get("estimated_hours", 40)) * 60
        remaining_min = int(est_total_min * max(0, (100 - int(e.get("prep_percent", 0)))) / 100)
        exam_remaining[e["id"]] = max(60, remaining_min)  # min 1h per exam

    # Sort exams by urgency (soonest first)
    sorted_exams = sorted(
        [e for e in exams if (date.fromisoformat(e["exam_date"]) - start_date).days >= 0],
        key=lambda e: (date.fromisoformat(e["exam_date"]) - start_date).days,
    )
    if not sorted_exams:
        return []

    slot_times = ["09:00", "11:00", "14:30", "16:30", "19:00"]
    block_cycle = ["Teoria", "Esercizi", "Ripasso"]

    tasks = []
    for i in range(days_ahead):
        d = start_date + timedelta(days=i)
        if d.weekday() not in avail:
            continue
        d_iso = d.isoformat()
        # existing busy minutes and time intervals
        existing = busy_by_day.get(d_iso, [])
        used_min = sum(t.get("duration_min", 90) for t in existing)
        busy = sorted([(_time_to_min(t["start_time"]),
                        _time_to_min(t["start_time"]) + t.get("duration_min", 90))
                       for t in existing])
        slot_idx = 0
        # try to fill up to daily budget with exams that still need work
        for exam in sorted_exams:
            if exam_remaining.get(exam["id"], 0) <= 0:
                continue
            if (date.fromisoformat(exam["exam_date"]) - d).days < 0:
                continue
            if used_min >= max_daily_min:
                break
            duration = min(90, exam_remaining[exam["id"]])
            duration = max(45, duration)
            # find a slot that doesn't overlap
            placed = False
            for _ in range(len(slot_times) * 2):
                if slot_idx >= len(slot_times):
                    break
                start = slot_times[slot_idx]
                slot_idx += 1
                s_min = _time_to_min(start)
                e_min = s_min + duration
                if any(_overlaps(s_min, e_min, bs, be) for bs, be in busy):
                    continue
                if used_min + duration > max_daily_min:
                    break
                block = block_cycle[len(tasks) % len(block_cycle)]
                # simulazione close to exam
                days_left = (date.fromisoformat(exam["exam_date"]) - d).days
                if days_left <= 3:
                    block = "Simulazione"
                elif days_left <= 7:
                    block = "Ripasso"
                tasks.append({
                    "id": str(uuid.uuid4()),
                    "user_id": user["id"],
                    "exam_id": exam["id"],
                    "exam_name": exam["name"],
                    "date": d_iso,
                    "start_time": start,
                    "end_time": _min_to_time(e_min),
                    "block_type": block,
                    "topic": f"{block} — {exam['name']}",
                    "status": "pianificato",
                    "partial_pct": None,
                    "duration_min": duration,
                })
                busy.append((s_min, e_min))
                busy.sort()
                used_min += duration
                exam_remaining[exam["id"]] -= duration
                placed = True
                break
            if not placed:
                continue
    return tasks


@api_router.post("/plan/generate")
async def generate_plan(user: dict = Depends(get_current_user)):
    exams = await db.exams.find({"user_id": user["id"]}, {"_id": 0}).to_list(500)
    if not exams:
        raise HTTPException(400, "Aggiungi almeno un esame prima di generare il piano")
    today = date.today().isoformat()
    # Clear only future PIANIFICATO tasks (keep any completed/parziale/non_completato history)
    await db.tasks.delete_many({
        "user_id": user["id"],
        "date": {"$gte": today},
        "status": "pianificato",
    })
    # Keep completed/parziale/non_completato tasks as "existing" so we don't overlap them
    kept = await db.tasks.find({"user_id": user["id"], "date": {"$gte": today}}, {"_id": 0}).to_list(500)
    tasks = await _generate_plan(user, exams, days_ahead=21, existing_tasks=kept)
    if tasks:
        await db.tasks.insert_many([dict(t) for t in tasks])
    for t in tasks:
        t.pop("_id", None)
    return {"tasks": tasks, "count": len(tasks)}


@api_router.post("/plan/replan")
async def replan(inp: ReplanIn, user: dict = Depends(get_current_user)):
    """Adaptive replan when the student is behind:
    - Keep completed/parziale (don't touch history)
    - Remove future pianificato AND future non_completato
    - Recompute exam prep_percent to account for parziale
    - Regenerate the future plan respecting exam dates
    """
    exams = await db.exams.find({"user_id": user["id"]}, {"_id": 0}).to_list(500)
    if not exams:
        raise HTTPException(400, "Nessun esame trovato")
    today = date.today().isoformat()

    # Remove upcoming unfinished sessions (they will be redistributed)
    await db.tasks.delete_many({
        "user_id": user["id"],
        "date": {"$gte": today},
        "status": {"$in": ["pianificato", "non_completato"]},
    })
    # Recompute prep based on remaining tasks (completed + parziale)
    for e in exams:
        await _recompute_exam_prep(user["id"], e["id"])
    # Reload exams after recompute
    exams = await db.exams.find({"user_id": user["id"]}, {"_id": 0}).to_list(500)

    # existing future parziale tasks -> keep, avoid overlaps
    kept = await db.tasks.find({"user_id": user["id"], "date": {"$gte": today}}, {"_id": 0}).to_list(500)
    tasks = await _generate_plan(user, exams, days_ahead=21, existing_tasks=kept)
    if tasks:
        await db.tasks.insert_many([dict(t) for t in tasks])
    for t in tasks:
        t.pop("_id", None)
    return {"tasks": tasks, "count": len(tasks), "message": "Piano riadattato ai tuoi tempi"}


# ============ HELPERS: task placement ============

def _time_to_min(t: str) -> int:
    h, m = t.split(":")
    return int(h) * 60 + int(m)


def _min_to_time(m: int) -> str:
    return f"{m // 60:02d}:{m % 60:02d}"


def _overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return a_start < b_end and b_start < a_end


async def _find_free_slot(user_id: str, day: str, duration_min: int,
                           exclude_id: Optional[str] = None) -> Optional[str]:
    """Find first available start time on the given day. Returns HH:MM or None."""
    same_day = await db.tasks.find({"user_id": user_id, "date": day}, {"_id": 0}).to_list(200)
    if exclude_id:
        same_day = [t for t in same_day if t["id"] != exclude_id]
    busy = sorted([(_time_to_min(t["start_time"]),
                    _time_to_min(t["start_time"]) + t.get("duration_min", 90))
                   for t in same_day])
    # workday window 08:00-22:00
    win_start, win_end = 8 * 60, 22 * 60
    cursor = win_start
    for bs, be in busy:
        if bs - cursor >= duration_min:
            return _min_to_time(cursor)
        cursor = max(cursor, be + 15)  # 15-min buffer
    if win_end - cursor >= duration_min:
        return _min_to_time(cursor)
    return None


def _end_time(start: str, duration_min: int) -> str:
    return _min_to_time(_time_to_min(start) + duration_min)


# ============ PROGRESS ============

def _pct_factor(t: dict) -> float:
    """Fraction of duration considered done."""
    s = t.get("status")
    if s == "completato":
        return 1.0
    if s == "parziale":
        pp = t.get("partial_pct")
        if pp in (25, 50, 75):
            return pp / 100.0
        return 0.5
    return 0.0


# ============ TASKS ============

@api_router.get("/tasks")
async def list_tasks(user: dict = Depends(get_current_user),
                     date_from: Optional[str] = None,
                     date_to: Optional[str] = None):
    q = {"user_id": user["id"]}
    if date_from or date_to:
        d = {}
        if date_from: d["$gte"] = date_from
        if date_to: d["$lte"] = date_to
        q["date"] = d
    tasks = await db.tasks.find(q, {"_id": 0}).to_list(2000)
    tasks.sort(key=lambda t: (t["date"], t["start_time"]))
    return tasks


@api_router.get("/tasks/today")
async def today_tasks(user: dict = Depends(get_current_user)):
    today = date.today().isoformat()
    tasks = await db.tasks.find({"user_id": user["id"], "date": today}, {"_id": 0}).to_list(200)
    tasks.sort(key=lambda t: t["start_time"])
    return tasks


async def _recompute_exam_prep(user_id: str, exam_id: str):
    exam = await db.exams.find_one({"id": exam_id, "user_id": user_id}, {"_id": 0})
    if not exam:
        return
    exam_tasks = await db.tasks.find({"exam_id": exam_id, "user_id": user_id}, {"_id": 0}).to_list(1000)
    total = sum(t.get("duration_min", 90) for t in exam_tasks)
    done = sum(t.get("duration_min", 90) * _pct_factor(t) for t in exam_tasks)
    if total <= 0:
        return
    base = exam.get("initial_prep", exam.get("prep_percent", 0))
    # progress = base + (done/total) * (100-base)
    new_pct = int(round(base + (done / total) * (100 - base)))
    new_pct = max(0, min(100, new_pct))
    await db.exams.update_one({"id": exam_id}, {"$set": {"prep_percent": new_pct}})


@api_router.post("/tasks")
async def create_task(inp: TaskCreateIn, user: dict = Depends(get_current_user)):
    exam = await db.exams.find_one({"id": inp.exam_id, "user_id": user["id"]}, {"_id": 0})
    if not exam:
        raise HTTPException(404, "Esame non trovato")
    if inp.date > exam["exam_date"]:
        raise HTTPException(400, "Non puoi pianificare sessioni dopo l'esame")
    # overlap check
    same_day = await db.tasks.find({"user_id": user["id"], "date": inp.date}, {"_id": 0}).to_list(200)
    ns, ne = _time_to_min(inp.start_time), _time_to_min(inp.start_time) + inp.duration_min
    for t in same_day:
        bs = _time_to_min(t["start_time"])
        be = bs + t.get("duration_min", 90)
        if _overlaps(ns, ne, bs, be):
            raise HTTPException(400, f"Sovrapposizione con la sessione delle {t['start_time']}")
    doc = {
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "exam_id": exam["id"],
        "exam_name": exam["name"],
        "date": inp.date,
        "start_time": inp.start_time,
        "end_time": _end_time(inp.start_time, inp.duration_min),
        "block_type": inp.block_type,
        "topic": inp.topic,
        "status": "pianificato",
        "partial_pct": None,
        "duration_min": inp.duration_min,
    }
    await db.tasks.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api_router.patch("/tasks/{task_id}")
async def edit_task(task_id: str, inp: TaskEditIn, user: dict = Depends(get_current_user)):
    current = await db.tasks.find_one({"id": task_id, "user_id": user["id"]}, {"_id": 0})
    if not current:
        raise HTTPException(404, "Task non trovato")
    upd = {}
    if inp.exam_id and inp.exam_id != current["exam_id"]:
        exam = await db.exams.find_one({"id": inp.exam_id, "user_id": user["id"]}, {"_id": 0})
        if not exam:
            raise HTTPException(404, "Esame non trovato")
        upd["exam_id"] = exam["id"]
        upd["exam_name"] = exam["name"]
    if inp.block_type:
        upd["block_type"] = inp.block_type
    if inp.topic is not None:
        upd["topic"] = inp.topic

    new_date = inp.date or current["date"]
    new_start = inp.start_time or current["start_time"]
    new_dur = inp.duration_min if inp.duration_min is not None else current.get("duration_min", 90)

    if inp.date or inp.start_time or inp.duration_min is not None:
        # verify exam date (using new exam if changed, otherwise current)
        eid = upd.get("exam_id", current["exam_id"])
        exam = await db.exams.find_one({"id": eid, "user_id": user["id"]}, {"_id": 0})
        if exam and new_date > exam["exam_date"]:
            raise HTTPException(400, "Non puoi pianificare sessioni dopo l'esame")
        # overlap
        same_day = await db.tasks.find({"user_id": user["id"], "date": new_date, "id": {"$ne": task_id}}, {"_id": 0}).to_list(200)
        ns, ne = _time_to_min(new_start), _time_to_min(new_start) + new_dur
        for t in same_day:
            bs = _time_to_min(t["start_time"])
            be = bs + t.get("duration_min", 90)
            if _overlaps(ns, ne, bs, be):
                raise HTTPException(400, f"Sovrapposizione con la sessione delle {t['start_time']} del {new_date}")
        upd["date"] = new_date
        upd["start_time"] = new_start
        upd["duration_min"] = new_dur
        upd["end_time"] = _end_time(new_start, new_dur)

    if upd:
        await db.tasks.update_one({"id": task_id, "user_id": user["id"]}, {"$set": upd})
    # recompute exam prep in case exam_id changed
    if "exam_id" in upd:
        await _recompute_exam_prep(user["id"], current["exam_id"])
        await _recompute_exam_prep(user["id"], upd["exam_id"])
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    return task


@api_router.put("/tasks/{task_id}")
async def update_task_status(task_id: str, inp: TaskUpdate, user: dict = Depends(get_current_user)):
    task = await db.tasks.find_one({"id": task_id, "user_id": user["id"]}, {"_id": 0})
    if not task:
        raise HTTPException(404, "Task non trovato")
    partial = inp.partial_pct if inp.status == "parziale" else None
    if partial is not None and partial not in (25, 50, 75):
        partial = 50
    await db.tasks.update_one(
        {"id": task_id, "user_id": user["id"]},
        {"$set": {
            k: v for k, v in {
                "status": inp.status,
                "actual_minutes": inp.actual_minutes,
                "partial_pct": partial,
            }.items()
            if v is not None or k == "partial_pct" or k == "status"
        }},
    )
    await _recompute_exam_prep(user["id"], task["exam_id"])
    updated = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    return updated


@api_router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, user: dict = Depends(get_current_user)):
    task = await db.tasks.find_one({"id": task_id, "user_id": user["id"]}, {"_id": 0})
    if not task:
        raise HTTPException(404, "Task non trovato")
    await db.tasks.delete_one({"id": task_id, "user_id": user["id"]})
    await _recompute_exam_prep(user["id"], task["exam_id"])
    return {"ok": True}


# ============ PROGRESS ============

@api_router.get("/progress")
async def progress(user: dict = Depends(get_current_user)):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    week_tasks = await db.tasks.find({
        "user_id": user["id"],
        "date": {"$gte": week_start.isoformat(), "$lte": week_end.isoformat()},
    }, {"_id": 0}).to_list(500)

    planned_min = sum(t.get("duration_min", 90) for t in week_tasks)
    done_min = sum(t.get("duration_min", 90) * _pct_factor(t) for t in week_tasks)
    completion = int((done_min / planned_min * 100) if planned_min else 0)

    daily = []
    for i in range(7):
        d = (week_start + timedelta(days=i)).isoformat()
        day_tasks = [t for t in week_tasks if t["date"] == d]
        p = sum(t.get("duration_min", 90) for t in day_tasks)
        c = sum(t.get("duration_min", 90) * _pct_factor(t) for t in day_tasks)
        daily.append({
            "date": d,
            "day_label": ["Lun","Mar","Mer","Gio","Ven","Sab","Dom"][i],
            "planned_hours": round(p / 60, 1),
            "completed_hours": round(c / 60, 1),
        })

    exams = await db.exams.find({"user_id": user["id"]}, {"_id": 0}).to_list(500)
    exams.sort(key=lambda e: e["exam_date"])
    return {
        "week_planned_hours": round(planned_min / 60, 1),
        "week_completed_hours": round(done_min / 60, 1),
        "completion_percent": completion,
        "daily": daily,
        "exams": exams,
    }


# ============ AI CHAT WITH TOOLS ============

def _tutor_tools():
    return [
        {
            "type": "function",
            "function": {
                "name": "move_task",
                "description": "Sposta una sessione di studio a un'altra data e/o ora. Usa quando l'utente dice cose come 'sposta la sessione di X a venerdì'.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"},
                        "new_date": {"type": "string", "description": "YYYY-MM-DD"},
                        "new_start_time": {"type": "string", "description": "HH:MM (opzionale)"},
                    },
                    "required": ["task_id", "new_date"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "delete_task",
                "description": "Elimina una sessione di studio quando l'utente vuole rimuoverla.",
                "parameters": {
                    "type": "object",
                    "properties": {"task_id": {"type": "string"}},
                    "required": ["task_id"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "mark_task_status",
                "description": "Aggiorna lo stato di una sessione (completato, parziale, non_completato). Per 'parziale' specifica partial_pct (25, 50 o 75).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string"},
                        "status": {"type": "string", "enum": ["completato","parziale","non_completato","pianificato"]},
                        "partial_pct": {"type": "integer", "enum": [25, 50, 75]},
                    },
                    "required": ["task_id", "status"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "clear_day",
                "description": "Elimina tutte le sessioni pianificate in una data specifica (es. 'domani non posso studiare'). Non tocca sessioni già completate.",
                "parameters": {
                    "type": "object",
                    "properties": {"day": {"type": "string", "description": "YYYY-MM-DD"}},
                    "required": ["day"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "replan_all",
                "description": "Riadatta l'intero piano futuro: elimina le sessioni future non completate e le ridistribuisce.",
                "parameters": {"type": "object", "properties": {}},
            },
        },
    ]


async def _dispatch_tutor_tool(name: str, args: dict, user: dict) -> dict:
    uid = user["id"]
    if name == "move_task":
        tid = args.get("task_id")
        new_date = args.get("new_date")
        task = await db.tasks.find_one({"id": tid, "user_id": uid}, {"_id": 0})
        if not task:
            return {"ok": False, "error": "Sessione non trovata"}
        exam = await db.exams.find_one({"id": task["exam_id"], "user_id": uid}, {"_id": 0})
        if exam and new_date > exam["exam_date"]:
            return {"ok": False, "error": "La data è successiva all'esame"}
        duration = task.get("duration_min", 90)
        new_start = args.get("new_start_time")
        if not new_start:
            new_start = await _find_free_slot(uid, new_date, duration, exclude_id=tid)
            if not new_start:
                return {"ok": False, "error": f"Nessuno slot libero il {new_date}"}
        # verify no overlap
        same_day = await db.tasks.find({"user_id": uid, "date": new_date, "id": {"$ne": tid}}, {"_id": 0}).to_list(200)
        ns, ne = _time_to_min(new_start), _time_to_min(new_start) + duration
        for t in same_day:
            bs = _time_to_min(t["start_time"]); be = bs + t.get("duration_min", 90)
            if _overlaps(ns, ne, bs, be):
                return {"ok": False, "error": f"Sovrapposizione con la sessione delle {t['start_time']}"}
        await db.tasks.update_one(
            {"id": tid, "user_id": uid},
            {"$set": {"date": new_date, "start_time": new_start,
                      "end_time": _end_time(new_start, duration)}}
        )
        return {"ok": True, "task_id": tid, "moved_to": {"date": new_date, "start_time": new_start}}

    if name == "delete_task":
        tid = args.get("task_id")
        task = await db.tasks.find_one({"id": tid, "user_id": uid}, {"_id": 0})
        if not task:
            return {"ok": False, "error": "Sessione non trovata"}
        await db.tasks.delete_one({"id": tid, "user_id": uid})
        await _recompute_exam_prep(uid, task["exam_id"])
        return {"ok": True, "deleted": tid}

    if name == "mark_task_status":
        tid = args.get("task_id")
        status = args.get("status")
        partial_pct = args.get("partial_pct") if status == "parziale" else None
        if partial_pct is not None and partial_pct not in (25, 50, 75):
            partial_pct = 50
        task = await db.tasks.find_one({"id": tid, "user_id": uid}, {"_id": 0})
        if not task:
            return {"ok": False, "error": "Sessione non trovata"}
        await db.tasks.update_one(
            {"id": tid, "user_id": uid},
            {"$set": {"status": status, "partial_pct": partial_pct}}
        )
        await _recompute_exam_prep(uid, task["exam_id"])
        return {"ok": True, "task_id": tid, "status": status, "partial_pct": partial_pct}

    if name == "clear_day":
        day = args.get("day")
        r = await db.tasks.delete_many({
            "user_id": uid, "date": day,
            "status": {"$in": ["pianificato", "non_completato"]},
        })
        return {"ok": True, "day": day, "deleted": r.deleted_count}

    if name == "replan_all":
        exams = await db.exams.find({"user_id": uid}, {"_id": 0}).to_list(500)
        today = date.today().isoformat()
        await db.tasks.delete_many({
            "user_id": uid, "date": {"$gte": today},
            "status": {"$in": ["pianificato", "non_completato"]},
        })
        for e in exams:
            await _recompute_exam_prep(uid, e["id"])
        exams = await db.exams.find({"user_id": uid}, {"_id": 0}).to_list(500)
        kept = await db.tasks.find({"user_id": uid, "date": {"$gte": today}}, {"_id": 0}).to_list(500)
        tasks = await _generate_plan(user, exams, days_ahead=21, existing_tasks=kept)
        if tasks:
            await db.tasks.insert_many([dict(t) for t in tasks])
        return {"ok": True, "regenerated": len(tasks)}

    return {"ok": False, "error": f"Tool sconosciuto: {name}"}


@api_router.post("/chat")
async def chat(inp: ChatIn, user: dict = Depends(get_current_user)):
    exams = await db.exams.find({"user_id": user["id"]}, {"_id": 0}).to_list(500)
    today = date.today().isoformat()
    horizon = (date.today() + timedelta(days=21)).isoformat()
    future_tasks = await db.tasks.find({
        "user_id": user["id"],
        "date": {"$gte": today, "$lte": horizon},
    }, {"_id": 0}).to_list(500)
    future_tasks.sort(key=lambda t: (t["date"], t["start_time"]))

    # Compact context. Include IDs so the model can invoke tools with correct task_id.
    ctx = {
        "oggi": today,
        "studente": user.get("name"),
        "corso": user.get("degree_course"),
        "ore_al_giorno": user.get("daily_hours"),
        "giorni_disponibili": user.get("available_days"),
        "esami": [
            {"id": e["id"], "nome": e["name"], "data": e["exam_date"],
             "difficolta": e["difficulty"], "preparazione": e["prep_percent"], "cfu": e["cfu"]}
            for e in exams
        ],
        "prossime_sessioni": [
            {"task_id": t["id"], "data": t["date"],
             "orario": f"{t['start_time']}-{t['end_time']}",
             "tipo": t["block_type"], "argomento": t["topic"],
             "esame": t["exam_name"], "esame_id": t["exam_id"],
             "stato": t["status"]}
            for t in future_tasks[:40]
        ],
    }

    system = (
        "Sei il Tutor AI di StudyFlow. Aiuti studenti universitari italiani.\n"
        "Rispondi SEMPRE in italiano, in modo pratico, breve e amichevole.\n"
        "Quando l'utente ti chiede di MODIFICARE il piano (spostare, eliminare, marcare come fatto, "
        "liberare un giorno, ricalcolare tutto), DEVI usare i tool disponibili invece di solo suggerire.\n"
        "IMPORTANTE: non dire mai di aver modificato qualcosa se non hai chiamato il tool corrispondente.\n"
        "Se manca un dato (es. quale giorno di destinazione), chiedi conferma prima di chiamare il tool.\n"
        "Fai riferimento agli esami usando il nome, ma internamente usa task_id/esame_id per i tool.\n\n"
        f"Contesto attuale:\n{json.dumps(ctx, ensure_ascii=False)}"
    )

    session_id = inp.session_id or f"chat-{user['id']}-{uuid.uuid4()}"
    chat_instance = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-4-6").with_params(max_tokens=1500)
    chat_instance = chat_instance.with_tools(_tutor_tools(), tool_choice="auto")

    tool_actions = []
    try:
        response = await chat_instance.send_message_with_tools(UserMessage(text=inp.message))
        # loop over tool calls
        for _ in range(4):
            if not getattr(response, "tool_calls", None):
                break
            for tc in response.tool_calls:
                try:
                    args = tc.arguments if isinstance(tc.arguments, dict) else json.loads(tc.arguments)
                except Exception:
                    args = {}
                result = await _dispatch_tutor_tool(tc.name, args, user)
                tool_actions.append({"tool": tc.name, "args": args, "result": result})
                chat_instance.add_tool_result(tc.id, json.dumps(result, ensure_ascii=False))
            response = await chat_instance.send_message_with_tools()
        text = getattr(response, "content", None) or "Ok."
        if not isinstance(text, str):
            text = str(text)
    except Exception as ex:
        logger.error(f"Chat error: {ex}")
        text = "Mi dispiace, al momento non riesco a rispondere. Riprova tra poco."

    await db.chat_history.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "session_id": session_id,
        "user_msg": inp.message,
        "assistant_msg": text,
        "tool_actions": tool_actions,
        "created_at": now_iso(),
    })
    return {"reply": text, "session_id": session_id, "actions": tool_actions}


@api_router.get("/chat/history")
async def chat_history(user: dict = Depends(get_current_user)):
    h = await db.chat_history.find(
        {"user_id": user["id"]}, {"_id": 0}
    ).sort("created_at", 1).to_list(100)
    return h


# ============ DEMO SEED ============

@api_router.post("/demo/seed")
async def demo_seed():
    """Idempotent demo account creation with sample data."""
    email = "demo@studyflow.it"
    password = "Demo1234!"
    existing = await db.users.find_one({"email": email})
    if existing:
        uid = existing["id"]
        # ensure clean sample data
        await db.exams.delete_many({"user_id": uid})
        await db.tasks.delete_many({"user_id": uid})
    else:
        uid = str(uuid.uuid4())
        await db.users.insert_one({
            "id": uid,
            "email": email,
            "password": hash_pw(password),
            "name": "Giulia",
            "university": "Università di Bologna",
            "degree_course": "Ingegneria Informatica",
            "daily_hours": 5,
            "available_days": ["lun","mar","mer","gio","ven","sab"],
            "graduation_goal": "Laurea con 108/110",
            "onboarded": True,
            "created_at": now_iso(),
        })

    today = date.today()
    sample_exams = [
        {
            "id": str(uuid.uuid4()),
            "user_id": uid,
            "name": "Analisi Matematica II",
            "exam_date": (today + timedelta(days=12)).isoformat(),
            "cfu": 9,
            "difficulty": "Difficile",
            "prep_percent": 35,
            "initial_prep": 35,
            "estimated_hours": 60,
            "notes": "Focus su integrali di superficie e serie di Fourier",
            "created_at": now_iso(),
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": uid,
            "name": "Basi di Dati",
            "exam_date": (today + timedelta(days=20)).isoformat(),
            "cfu": 6,
            "difficulty": "Media",
            "prep_percent": 55,
            "initial_prep": 55,
            "estimated_hours": 40,
            "notes": "Normalizzazione, SQL avanzato",
            "created_at": now_iso(),
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": uid,
            "name": "Reti di Calcolatori",
            "exam_date": (today + timedelta(days=32)).isoformat(),
            "cfu": 6,
            "difficulty": "Media",
            "prep_percent": 20,
            "initial_prep": 20,
            "estimated_hours": 45,
            "notes": None,
            "created_at": now_iso(),
        },
    ]
    await db.exams.insert_many([dict(e) for e in sample_exams])

    # generate simple tasks for the next 10 days
    user = await db.users.find_one({"id": uid}, {"_id": 0})
    tasks = _fallback_plan(user, sample_exams, 10, today)
    # mark yesterday's tasks as completed for realistic progress
    for t in tasks:
        if t["date"] < today.isoformat():
            t["status"] = "completato"
    if tasks:
        await db.tasks.insert_many([dict(t) for t in tasks])

    return {"email": email, "password": password, "message": "Account demo pronto"}


# ============ HEALTH ============

@api_router.get("/")
async def root():
    return {"app": "StudyFlow", "status": "ok"}


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_seed():
    """Seed demo account on startup (idempotent)."""
    try:
        existing = await db.users.find_one({"email": "demo@studyflow.it"})
        if not existing:
            await demo_seed()
            logger.info("Demo account seeded")
    except Exception as e:
        logger.error(f"Startup seed failed: {e}")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
