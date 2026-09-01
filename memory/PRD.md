# StudyFlow — PRD

## Original Problem Statement
Build "StudyFlow", an AI-powered personal study planner for Italian university students. Students enter exams (name, date, CFU, difficulty, prep %, estimated hours), and StudyFlow uses Claude Sonnet 4.6 to generate a personalized daily study plan. If the student falls behind, tapping "Sono rimasto indietro" triggers the AI to replan the remaining schedule. UI must be fully in Italian, mobile-first, light minimal aesthetic.

## Architecture
- **Backend**: FastAPI + MongoDB (motor). JWT auth (bcrypt + pyjwt). AI via `emergentintegrations` + Claude `claude-sonnet-4-6` (Emergent LLM key).
- **Frontend**: React 19, react-router-dom v7, TailwindCSS, shadcn/ui, Recharts, lucide-react, sonner.
- **Data collections**: `users`, `exams`, `tasks`, `chat_history`.
- **Auth**: JWT bearer tokens; every route scoped to `user_id`.

## User Personas
1. Italian undergrad juggling 3-5 exams per session — wants realistic plans, not rigid.
2. Grad student targeting a specific final grade — wants adaptive rescheduling.

## Core Requirements (Static)
- Italian UI, mobile-first, light minimal theme.
- Auth: signup, login, logout, profile.
- Onboarding wizard (name, uni, corso, ore/giorno, giorni disponibili, obiettivo).
- Exam CRUD with progress bars, difficulty badges, days-remaining.
- AI-generated daily study plan (blocks: Teoria/Esercizi/Ripasso/Simulazione).
- Task completion states: completato / parziale / non_completato / pianificato.
- "Sono rimasto indietro" → AI replan.
- Progressi page with weekly hours chart and per-exam progress.
- AI tutor chat contextualised with the user's exams + plan.
- Bottom nav on mobile + sidebar on desktop + FAB for new exam.

## Implemented (2026-02-01)
- Full auth (JWT signup/login/me/onboarding) + protected routes.
- Exams CRUD with modal (create/edit/delete) and 3-difficulty pills + prep-slider.
- AI plan generation using Claude Sonnet 4.6 (with deterministic fallback) — 14-day horizon.
- Adaptive `/plan/replan` endpoint tied to "Sono rimasto indietro" AlertDialog.
- Home dashboard: greeting, next-exam card, today's plan, weekly stats, fell-behind button.
- Piano page: 30-day plan grouped by date, per-task status pickers.
- Progressi page: metric cards, Recharts BarChart (planned vs completed), per-exam progress, upcoming exams.
- Tutor AI chat page with suggestions and persisted history.
- Profile edit + logout.
- Demo account auto-seeded on backend startup (demo@studyflow.it / Demo1234!) with 3 sample exams and pre-populated tasks.
- Testing agent passed backend + frontend at 100%.

## Backlog / Next Steps
- P1: Weekly view toggle on Piano; add drag-to-reschedule.
- P1: Push/email reminders for upcoming sessions.
- P2: Multi-language support (English).
- P2: Streak/gamification badges.
- P2: Import CFU/exam list from major Italian universities via CSV.
- P2: Export plan to Google Calendar / .ics.
