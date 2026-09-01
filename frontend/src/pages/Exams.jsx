import React, { useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import api from "@/lib/api";
import ExamModal from "@/components/studyflow/ExamModal";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { DIFFICULTY_STYLES, daysUntil, formatItalianDate } from "@/lib/utils-sf";
import { CalendarDays, Trash2, Pencil, Plus, BookOpen, Sparkles } from "lucide-react";
import { toast } from "sonner";

export default function Exams() {
  const [exams, setExams] = useState([]);
  const [loading, setLoading] = useState(true);
  const [openAdd, setOpenAdd] = useState(false);
  const [editing, setEditing] = useState(null);
  const [generating, setGenerating] = useState(false);
  const [params] = useSearchParams();

  const load = async () => {
    setLoading(true);
    try {
      const r = await api.get("/exams");
      setExams(r.data);
    } finally { setLoading(false); }
  };

  useEffect(() => {
    load();
    if (params.get("first")) setOpenAdd(true);
  }, []);

  const del = async (id) => {
    try {
      await api.delete(`/exams/${id}`);
      toast.success("Esame eliminato");
      load();
    } catch { toast.error("Errore"); }
  };

  const generatePlan = async () => {
    setGenerating(true);
    try {
      const r = await api.post("/plan/generate");
      toast.success(`Piano generato: ${r.data.count} sessioni di studio`);
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Errore generazione piano");
    } finally { setGenerating(false); }
  };

  return (
    <div className="space-y-4 fade-in">
      <header className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900">I miei esami</h1>
          <p className="text-sm text-slate-500 mt-1">Gestisci gli esami e genera il piano AI</p>
        </div>
        <Button
          onClick={() => { setEditing(null); setOpenAdd(true); }}
          data-testid="exams-add-button"
          className="rounded-full h-10 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold"
        >
          <Plus className="w-4 h-4 mr-1" /> Aggiungi
        </Button>
      </header>

      {exams.length > 0 && (
        <Button
          onClick={generatePlan}
          disabled={generating}
          data-testid="generate-plan-button"
          className="w-full rounded-2xl h-14 bg-white hover:bg-indigo-50 border-2 border-dashed border-indigo-300 text-indigo-700 font-semibold"
        >
          <Sparkles className="w-5 h-5 mr-2" />
          {generating ? "L'AI sta creando il tuo piano..." : "Genera piano di studio con AI"}
        </Button>
      )}

      {loading ? (
        <div className="text-slate-500 text-sm">Carico...</div>
      ) : exams.length === 0 ? (
        <div className="bg-white rounded-2xl p-8 text-center border border-slate-100 card-elevated">
          <div className="w-14 h-14 mx-auto rounded-full bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 mb-3">
            <BookOpen className="w-6 h-6" />
          </div>
          <h3 className="font-bold text-slate-900">Nessun esame ancora</h3>
          <p className="text-sm text-slate-500 mt-1">Aggiungi il primo esame per iniziare</p>
          <Button
            onClick={() => setOpenAdd(true)}
            data-testid="exams-empty-add"
            className="mt-4 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white"
          >
            <Plus className="w-4 h-4 mr-1" /> Aggiungi esame
          </Button>
        </div>
      ) : (
        <div className="space-y-3 stagger">
          {exams.map((e) => {
            const d = daysUntil(e.exam_date);
            const urgent = d <= 7 && d >= 0;
            return (
              <div
                key={e.id}
                data-testid="exam-card-item"
                className="bg-white rounded-2xl p-5 border border-slate-100 card-elevated"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <h3 className="font-bold text-slate-900 text-lg leading-tight">{e.name}</h3>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${DIFFICULTY_STYLES[e.difficulty]}`}>
                        {e.difficulty}
                      </span>
                    </div>
                    <div className="flex items-center gap-3 mt-1.5 text-xs text-slate-500">
                      <span className="flex items-center gap-1"><CalendarDays className="w-3.5 h-3.5" /> {formatItalianDate(e.exam_date)}</span>
                      <span className="font-mono">{e.cfu} CFU</span>
                    </div>
                  </div>
                  <div className={`text-right shrink-0 ${urgent ? "text-rose-600" : d < 0 ? "text-slate-400" : "text-slate-700"}`}>
                    <div className="text-2xl font-bold font-mono leading-none">{d < 0 ? "—" : d}</div>
                    <div className="text-[10px] font-semibold uppercase tracking-wider mt-0.5">{d < 0 ? "passato" : "giorni"}</div>
                  </div>
                </div>

                <div className="mt-4">
                  <div className="flex justify-between text-xs text-slate-500 mb-1.5">
                    <span>Preparazione</span>
                    <span className="font-semibold text-slate-700">{e.prep_percent}%</span>
                  </div>
                  <Progress value={e.prep_percent} className="h-2" />
                </div>

                <div className="flex gap-2 mt-4">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => { setEditing(e); setOpenAdd(true); }}
                    data-testid={`exam-edit-${e.id}`}
                    className="text-slate-600 hover:text-indigo-700 rounded-full"
                  >
                    <Pencil className="w-3.5 h-3.5 mr-1" /> Modifica
                  </Button>
                  <AlertDialog>
                    <AlertDialogTrigger asChild>
                      <Button variant="ghost" size="sm" className="text-slate-600 hover:text-rose-600 rounded-full" data-testid={`exam-delete-${e.id}`}>
                        <Trash2 className="w-3.5 h-3.5 mr-1" /> Elimina
                      </Button>
                    </AlertDialogTrigger>
                    <AlertDialogContent>
                      <AlertDialogHeader>
                        <AlertDialogTitle>Eliminare "{e.name}"?</AlertDialogTitle>
                        <AlertDialogDescription>Verranno rimosse anche le sessioni di studio associate.</AlertDialogDescription>
                      </AlertDialogHeader>
                      <AlertDialogFooter>
                        <AlertDialogCancel>Annulla</AlertDialogCancel>
                        <AlertDialogAction onClick={() => del(e.id)} className="bg-rose-600 hover:bg-rose-700">Elimina</AlertDialogAction>
                      </AlertDialogFooter>
                    </AlertDialogContent>
                  </AlertDialog>
                </div>
              </div>
            );
          })}
        </div>
      )}

      <ExamModal
        open={openAdd}
        exam={editing}
        onClose={() => { setOpenAdd(false); setEditing(null); }}
        onSaved={() => { setOpenAdd(false); setEditing(null); load(); }}
      />
    </div>
  );
}
