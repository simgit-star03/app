import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { BLOCK_STYLES, STATUS_LABEL, STATUS_STYLES, daysUntil, greeting, formatShortDate } from "@/lib/utils-sf";
import { CalendarClock, Zap, Check, Clock, AlertTriangle, ArrowRight, Sparkles, Circle } from "lucide-react";
import { toast } from "sonner";

export default function Home() {
  const { user } = useAuth();
  const [tasks, setTasks] = useState([]);
  const [progress, setProgress] = useState(null);
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [replaning, setReplaning] = useState(false);
  const nav = useNavigate();

  const load = async () => {
    setLoading(true);
    try {
      const [t, p, e] = await Promise.all([
        api.get("/tasks/today"),
        api.get("/progress"),
        api.get("/exams"),
      ]);
      setTasks(t.data);
      setProgress(p.data);
      setExams(e.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  const nextExam = exams.filter(e => daysUntil(e.exam_date) >= 0)[0];

  const setStatus = async (id, status) => {
    try {
      await api.put(`/tasks/${id}`, { status });
      setTasks(ts => ts.map(t => t.id === id ? { ...t, status } : t));
      load();
    } catch { toast.error("Errore"); }
  };

  const replan = async () => {
    setReplaning(true);
    try {
      const r = await api.post("/plan/replan", { reason: "Sono rimasto indietro" });
      toast.success(r.data.message || "Piano riadattato");
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Errore riadattamento");
    } finally { setReplaning(false); }
  };

  const doneTasks = tasks.filter(t => t.status === "completato").length;
  const todayPct = tasks.length ? Math.round((doneTasks / tasks.length) * 100) : 0;

  return (
    <div className="space-y-4 fade-in">
      <header>
        <p className="text-sm text-slate-500">{greeting(user?.name)}</p>
        <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 mt-0.5">
          Ecco il tuo piano per oggi
        </h1>
      </header>

      {nextExam ? (
        <div className="bg-gradient-to-br from-indigo-600 to-indigo-500 text-white rounded-2xl p-5 card-elevated">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-xs uppercase tracking-wider text-indigo-100 font-semibold">Prossimo esame</div>
              <h2 className="text-xl sm:text-2xl font-bold mt-1">{nextExam.name}</h2>
              <div className="text-sm text-indigo-100 mt-1">{formatShortDate(nextExam.exam_date)} · {nextExam.cfu} CFU</div>
            </div>
            <div className="text-right">
              <div className="text-4xl sm:text-5xl font-bold font-mono leading-none">{daysUntil(nextExam.exam_date)}</div>
              <div className="text-xs font-semibold text-indigo-100 mt-1">giorni</div>
            </div>
          </div>
          <div className="mt-4">
            <div className="flex justify-between text-xs text-indigo-100 mb-1.5">
              <span>Preparazione</span>
              <span className="font-semibold">{nextExam.prep_percent}%</span>
            </div>
            <div className="h-2 bg-indigo-800/40 rounded-full overflow-hidden">
              <div className="h-full bg-white rounded-full transition-all" style={{ width: `${nextExam.prep_percent}%` }} />
            </div>
          </div>
        </div>
      ) : (
        <div className="bg-white rounded-2xl p-5 border border-slate-100 card-elevated text-center">
          <p className="text-slate-700 font-semibold">Nessun esame in programma</p>
          <Button onClick={() => nav("/esami")} className="mt-3 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white" data-testid="home-add-exam-cta">
            Aggiungi il primo esame <ArrowRight className="w-4 h-4 ml-1" />
          </Button>
        </div>
      )}

      {/* Today's plan */}
      <section className="bg-white rounded-2xl p-5 border border-slate-100 card-elevated">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="font-bold text-slate-900 flex items-center gap-2">
              <CalendarClock className="w-4 h-4 text-indigo-600" /> Piano di oggi
            </h3>
            <p className="text-xs text-slate-500 mt-0.5">{doneTasks}/{tasks.length} sessioni · {todayPct}% completato</p>
          </div>
          {tasks.length > 0 && (
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  size="sm"
                  data-testid="fell-behind-button"
                  className="rounded-full bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 text-xs font-semibold"
                >
                  <AlertTriangle className="w-3.5 h-3.5 mr-1" /> Sono rimasto indietro
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle className="flex items-center gap-2"><Sparkles className="w-5 h-5 text-indigo-600" /> Riadatto il piano?</AlertDialogTitle>
                  <AlertDialogDescription>
                    L'AI ricalcolerà le sessioni non completate e le ridistribuirà nei prossimi giorni disponibili, mantenendo l'obiettivo.
                  </AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Annulla</AlertDialogCancel>
                  <AlertDialogAction onClick={replan} disabled={replaning} className="bg-indigo-600 hover:bg-indigo-700" data-testid="replan-confirm-button">
                    {replaning ? "Ricalcolo..." : "Applica nuovo piano"}
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
          )}
        </div>

        {tasks.length === 0 ? (
          <div className="py-6 text-center">
            <p className="text-sm text-slate-500">Nessuna sessione oggi.</p>
            <Button onClick={() => nav("/esami")} variant="outline" size="sm" className="mt-3 rounded-full" data-testid="home-gen-plan">
              <Sparkles className="w-4 h-4 mr-1" /> Genera piano
            </Button>
          </div>
        ) : (
          <div className="space-y-2 stagger">
            {tasks.map((t) => (
              <TaskRow key={t.id} task={t} onStatus={(s) => setStatus(t.id, s)} />
            ))}
          </div>
        )}

        {tasks.length > 0 && (
          <div className="mt-4 pt-4 border-t border-slate-100">
            <div className="flex justify-between text-xs text-slate-500 mb-1.5">
              <span>Progresso di oggi</span>
              <span className="font-semibold text-slate-700">{todayPct}%</span>
            </div>
            <Progress value={todayPct} className="h-2" />
          </div>
        )}
      </section>

      {/* Weekly progress */}
      {progress && (
        <section className="bg-white rounded-2xl p-5 border border-slate-100 card-elevated">
          <h3 className="font-bold text-slate-900 flex items-center gap-2 mb-3">
            <Zap className="w-4 h-4 text-emerald-600" /> Questa settimana
          </h3>
          <div className="grid grid-cols-3 gap-3">
            <Stat label="Ore pianificate" value={`${progress.week_planned_hours}h`} />
            <Stat label="Ore completate" value={`${progress.week_completed_hours}h`} />
            <Stat label="Completamento" value={`${progress.completion_percent}%`} accent />
          </div>
        </section>
      )}
    </div>
  );
}

function Stat({ label, value, accent }) {
  return (
    <div className="text-center py-2">
      <div className={`text-xl sm:text-2xl font-bold font-mono ${accent ? "text-indigo-600" : "text-slate-900"}`}>{value}</div>
      <div className="text-[10px] font-semibold uppercase tracking-wider text-slate-500 mt-1">{label}</div>
    </div>
  );
}

function TaskRow({ task, onStatus }) {
  const done = task.status === "completato";
  return (
    <div className={`flex items-center gap-3 p-3 rounded-xl border ${done ? "bg-emerald-50/40 border-emerald-100" : "bg-slate-50/60 border-slate-100"}`} data-testid={`task-row-${task.id}`}>
      <button
        onClick={() => onStatus(done ? "pianificato" : "completato")}
        data-testid={`task-toggle-${task.id}`}
        className={`shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center transition-all ${
          done ? "bg-emerald-500 border-emerald-500 text-white" : "border-slate-300 hover:border-indigo-400"
        }`}
      >
        {done ? <Check className="w-3.5 h-3.5" /> : <Circle className="w-3 h-3 text-transparent" />}
      </button>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-mono text-xs font-semibold text-slate-700">{task.start_time}–{task.end_time}</span>
          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${BLOCK_STYLES[task.block_type] || BLOCK_STYLES.Teoria}`}>{task.block_type}</span>
        </div>
        <p className={`text-sm mt-0.5 truncate ${done ? "text-slate-400 line-through" : "text-slate-800 font-medium"}`}>{task.topic}</p>
        <p className="text-xs text-slate-500 truncate">{task.exam_name}</p>
      </div>
      <div className="flex gap-1 shrink-0">
        <button
          onClick={() => onStatus("parziale")}
          data-testid={`task-partial-${task.id}`}
          className={`text-[10px] px-2 py-1 rounded-full font-semibold ${task.status === "parziale" ? STATUS_STYLES.parziale : "bg-white text-slate-500 border border-slate-200"}`}
        >
          Parziale
        </button>
      </div>
    </div>
  );
}
