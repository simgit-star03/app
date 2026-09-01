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
BlockType = Literal["Teoria", "Esercizi", "Ripasso", "Simulazione"]


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
    doc["created_at"] = now_iso()
    await db.exams.insert_one(doc)
    doc.pop("_id", None)
    return doc


@api_router.put("/exams/{exam_id}")
async def update_exam(exam_id: str, data: dict, user: dict = Depends(get_current_user)):
    allowed = {"name", "exam_date", "cfu", "difficulty", "prep_percent",
               "estimated_hours", "notes"}
    upd = {k: v for k, v in data.items() if k in allowed}
    r = await db.exams.update_one({"id": exam_id, "user_id": user["id"]}, {"$set": upd})
    if r.matched_count == 0:
        raise HTTPException(404, "Esame non trovato")
    exam = await db.exams.find_one({"id": exam_id}, {"_id": 0})
    return exam


@api_router.delete("/exams/{exam_id}")
async def delete_exam(exam_id: str, user: dict = Depends(get_current_user)):
    await db.exams.delete_one({"id": exam_id, "user_id": user["id"]})
    await db.tasks.delete_many({"exam_id": exam_id, "user_id": user["id"]})
    return {"ok": True}


# ============ STUDY PLAN AI ============

async def _generate_plan(user: dict, exams: list, days_ahead: int = 14,
                          start_date: Optional[date] = None) -> list:
    """Call Claude to generate a JSON study plan. Returns list of tasks."""
    if not exams:
        return []
    if start_date is None:
        start_date = date.today()

    system = (
        "Sei StudyFlow, un pianificatore di studio AI per studenti universitari italiani. "
        "Genera un piano di studio giornaliero realistico e personalizzato. "
        "Rispondi SOLO con JSON valido, nessun testo extra."
    )

    exam_summaries = []
    for e in exams:
        d_left = (date.fromisoformat(e["exam_date"]) - start_date).days
        remaining_hours = max(1, int(e["estimated_hours"] * (100 - e["prep_percent"]) / 100))
        exam_summaries.append({
            "id": e["id"],
            "name": e["name"],
            "date": e["exam_date"],
            "days_left": d_left,
            "difficulty": e["difficulty"],
            "prep_percent": e["prep_percent"],
            "estimated_remaining_hours": remaining_hours,
            "cfu": e["cfu"],
        })

    prompt = f"""Utente: {user.get('name','studente')} — {user.get('degree_course','')}
Ore studio disponibili al giorno: {user.get('daily_hours',4)}
Giorni della settimana disponibili: {user.get('available_days',[])}
Data di inizio: {start_date.isoformat()}
Genera un piano per i prossimi {days_ahead} giorni.

Esami:
{json.dumps(exam_summaries, ensure_ascii=False, indent=2)}

Regole:
- Priorità: esami più vicini + più difficili + preparazione bassa
- Blocchi da 60-90 minuti con pausa
- Alterna Teoria, Esercizi, Ripasso; aggiungi Simulazione vicino alla data d'esame
- Solo nei giorni disponibili
- Rispetta le ore giornaliere massime
- Fasce orarie realistiche (9:00-12:30 e 15:00-18:30)

Formato JSON:
{{
  "tasks": [
    {{
      "exam_id": "<id>",
      "date": "YYYY-MM-DD",
      "start_time": "HH:MM",
      "end_time": "HH:MM",
      "block_type": "Teoria|Esercizi|Ripasso|Simulazione",
      "topic": "argomento specifico e concreto",
      "duration_min": 90
    }}
  ]
}}
"""

    session_id = f"plan-{user['id']}-{uuid.uuid4()}"
    chat = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-4-6").with_params(max_tokens=4000)

    try:
        resp = await chat.send_message(UserMessage(text=prompt))
        content = resp if isinstance(resp, str) else str(resp)
    except Exception as ex:
        logger.error(f"LLM error: {ex}")
        return _fallback_plan(user, exams, days_ahead, start_date)

    # extract json
    m = re.search(r"\{[\s\S]*\}", content)
    if not m:
        return _fallback_plan(user, exams, days_ahead, start_date)
    try:
        data = json.loads(m.group(0))
    except Exception:
        return _fallback_plan(user, exams, days_ahead, start_date)

    tasks_out = []
    exam_map = {e["id"]: e for e in exams}
    for t in data.get("tasks", []):
        eid = t.get("exam_id")
        exam = exam_map.get(eid) or exams[0]
        tasks_out.append({
            "id": str(uuid.uuid4()),
            "user_id": user["id"],
            "exam_id": exam["id"],
            "exam_name": exam["name"],
            "date": t.get("date"),
            "start_time": t.get("start_time"),
            "end_time": t.get("end_time"),
            "block_type": t.get("block_type", "Teoria"),
            "topic": t.get("topic", "Studio generale"),
            "status": "pianificato",
            "duration_min": int(t.get("duration_min", 90)),
        })
    return tasks_out


def _fallback_plan(user, exams, days_ahead, start_date):
    """Simple deterministic fallback if LLM fails."""
    day_map = {"lun": 0, "mar": 1, "mer": 2, "gio": 3, "ven": 4, "sab": 5, "dom": 6}
    avail = {day_map[d] for d in user.get("available_days", ["lun","mar","mer","gio","ven"]) if d in day_map}
    tasks = []
    slots = [("09:00","10:30","Teoria"),("11:00","12:30","Esercizi"),("15:00","16:30","Ripasso")]
    daily = int(min(len(slots), max(1, user.get("daily_hours",4) / 1.5)))
    slots = slots[:daily]

    # sort exams by urgency
    sorted_exams = sorted(exams, key=lambda e: (date.fromisoformat(e["exam_date"]) - start_date).days)
    ex_idx = 0
    for i in range(days_ahead):
        d = start_date + timedelta(days=i)
        if d.weekday() not in avail:
            continue
        for s, e_t, bt in slots:
            exam = sorted_exams[ex_idx % len(sorted_exams)]
            if (date.fromisoformat(exam["exam_date"]) - d).days < 0:
                continue
            tasks.append({
                "id": str(uuid.uuid4()),
                "user_id": user["id"],
                "exam_id": exam["id"],
                "exam_name": exam["name"],
                "date": d.isoformat(),
                "start_time": s,
                "end_time": e_t,
                "block_type": bt,
                "topic": f"{bt} — {exam['name']}",
                "status": "pianificato",
                "duration_min": 90,
            })
            ex_idx += 1
    return tasks


@api_router.post("/plan/generate")
async def generate_plan(user: dict = Depends(get_current_user)):
    exams = await db.exams.find({"user_id": user["id"]}, {"_id": 0}).to_list(500)
    if not exams:
        raise HTTPException(400, "Aggiungi almeno un esame prima di generare il piano")
    # clear future pianificato tasks (keep completed history)
    today = date.today().isoformat()
    await db.tasks.delete_many({
        "user_id": user["id"],
        "date": {"$gte": today},
        "status": "pianificato",
    })
    tasks = await _generate_plan(user, exams)
    if tasks:
        await db.tasks.insert_many([dict(t) for t in tasks])
    for t in tasks:
        t.pop("_id", None)
    return {"tasks": tasks, "count": len(tasks)}


@api_router.post("/plan/replan")
async def replan(inp: ReplanIn, user: dict = Depends(get_current_user)):
    """Adaptive replan: redistribute unfinished + future tasks."""
    exams = await db.exams.find({"user_id": user["id"]}, {"_id": 0}).to_list(500)
    if not exams:
        raise HTTPException(400, "Nessun esame trovato")
    today = date.today().isoformat()
    # remove future pianificato + non_completato tasks
    await db.tasks.delete_many({
        "user_id": user["id"],
        "date": {"$gte": today},
        "status": {"$in": ["pianificato", "non_completato", "parziale"]},
    })
    tasks = await _generate_plan(user, exams)
    if tasks:
        await db.tasks.insert_many([dict(t) for t in tasks])
    for t in tasks:
        t.pop("_id", None)
    return {"tasks": tasks, "count": len(tasks), "message": "Piano riadattato ai tuoi tempi"}


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


@api_router.put("/tasks/{task_id}")
async def update_task(task_id: str, inp: TaskUpdate, user: dict = Depends(get_current_user)):
    r = await db.tasks.update_one(
        {"id": task_id, "user_id": user["id"]},
        {"$set": {"status": inp.status, "actual_minutes": inp.actual_minutes}},
    )
    if r.matched_count == 0:
        raise HTTPException(404, "Task non trovato")

    # auto-update exam prep_percent based on completed tasks
    task = await db.tasks.find_one({"id": task_id}, {"_id": 0})
    if task and inp.status in ("completato", "parziale"):
        exam_tasks = await db.tasks.find({"exam_id": task["exam_id"], "user_id": user["id"]}, {"_id": 0}).to_list(1000)
        total = sum(t["duration_min"] for t in exam_tasks)
        done = sum(
            t["duration_min"] * (1.0 if t["status"] == "completato" else 0.5 if t["status"] == "parziale" else 0)
            for t in exam_tasks
        )
        exam = await db.exams.find_one({"id": task["exam_id"]}, {"_id": 0})
        if exam and total > 0:
            base = exam.get("prep_percent", 0)
            increment = int((done / total) * (100 - base) * 0.3)
            new_pct = min(100, base + increment)
            await db.exams.update_one({"id": task["exam_id"]}, {"$set": {"prep_percent": new_pct}})
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

    planned_min = sum(t["duration_min"] for t in week_tasks)
    done_min = sum(
        t["duration_min"] * (1.0 if t["status"] == "completato" else 0.5 if t["status"] == "parziale" else 0)
        for t in week_tasks
    )
    completion = int((done_min / planned_min * 100) if planned_min else 0)

    # daily breakdown
    daily = []
    for i in range(7):
        d = (week_start + timedelta(days=i)).isoformat()
        day_tasks = [t for t in week_tasks if t["date"] == d]
        p = sum(t["duration_min"] for t in day_tasks)
        c = sum(t["duration_min"] for t in day_tasks if t["status"] == "completato")
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


# ============ AI CHAT ============

@api_router.post("/chat")
async def chat(inp: ChatIn, user: dict = Depends(get_current_user)):
    exams = await db.exams.find({"user_id": user["id"]}, {"_id": 0}).to_list(500)
    today = date.today().isoformat()
    week_end = (date.today() + timedelta(days=7)).isoformat()
    week_tasks = await db.tasks.find({
        "user_id": user["id"],
        "date": {"$gte": today, "$lte": week_end},
    }, {"_id": 0}).to_list(500)

    context = {
        "studente": user.get("name"),
        "corso": user.get("degree_course"),
        "ore_al_giorno": user.get("daily_hours"),
        "giorni_disponibili": user.get("available_days"),
        "esami": [
            {
                "nome": e["name"],
                "data": e["exam_date"],
                "difficolta": e["difficulty"],
                "preparazione": f"{e['prep_percent']}%",
                "cfu": e["cfu"],
            }
            for e in exams
        ],
        "piano_prossimi_giorni": [
            {
                "data": t["date"],
                "orario": f"{t['start_time']}-{t['end_time']}",
                "tipo": t["block_type"],
                "argomento": t["topic"],
                "esame": t["exam_name"],
                "stato": t["status"],
            }
            for t in week_tasks[:20]
        ],
    }

    system = (
        "Sei il Tutor AI di StudyFlow. Aiuti studenti universitari italiani a organizzare lo studio. "
        "Rispondi sempre in italiano, in modo pratico, breve e amichevole. "
        "Fai riferimento agli esami e al piano dello studente. "
        f"Contesto:\n{json.dumps(context, ensure_ascii=False, indent=2)}"
    )

    session_id = inp.session_id or f"chat-{user['id']}"
    chat_instance = LlmChat(
        api_key=EMERGENT_LLM_KEY,
        session_id=session_id,
        system_message=system,
    ).with_model("anthropic", "claude-sonnet-4-6").with_params(max_tokens=1000)

    try:
        resp = await chat_instance.send_message(UserMessage(text=inp.message))
        text = resp if isinstance(resp, str) else str(resp)
    except Exception as ex:
        logger.error(f"Chat error: {ex}")
        text = "Mi dispiace, al momento non riesco a rispondere. Riprova tra poco."

    # save to history
    await db.chat_history.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user["id"],
        "session_id": session_id,
        "user_msg": inp.message,
        "assistant_msg": text,
        "created_at": now_iso(),
    })
    return {"reply": text, "session_id": session_id}


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
