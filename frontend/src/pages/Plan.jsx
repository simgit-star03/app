import React, { useEffect, useState, useCallback } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import TaskRow from "@/components/studyflow/TaskRow";
import TaskEditModal from "@/components/studyflow/TaskEditModal";
import { formatShortDate } from "@/lib/utils-sf";
import { Sparkles } from "lucide-react";
import { toast } from "sonner";

export default function Plan() {
  const [tasks, setTasks] = useState([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);

  const load = useCallback(async () => {
    try {
      const today = new Date().toISOString().slice(0, 10);
      const end = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10);
      const r = await api.get(`/tasks?date_from=${today}&date_to=${end}`);
      setTasks(r.data);
    } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const h = () => load();
    window.addEventListener("studyflow:plan-changed", h);
    return () => window.removeEventListener("studyflow:plan-changed", h);
  }, [load]);

  const generate = async () => {
    setBusy(true);
    try {
      const r = await api.post("/plan/generate");
      toast.success(`Nuovo piano: ${r.data.count} sessioni`);
      load();
    } catch (e) {
      toast.error(e?.response?.data?.detail || "Errore generazione piano");
    } finally { setBusy(false); }
  };

  const setStatus = async (id, status, partialPct) => {
    try {
      await api.put(`/tasks/${id}`, { status, partial_pct: partialPct });
      await load();
    } catch { toast.error("Errore"); }
  };

  const grouped = tasks.reduce((acc, t) => {
    (acc[t.date] = acc[t.date] || []).push(t);
    return acc;
  }, {});
  const dates = Object.keys(grouped).sort();

  return (
    <div className="space-y-4 fade-in">
      <header className="flex items-center justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900">Piano di studio</h1>
          <p className="text-sm text-slate-500 mt-1">Prossimi 30 giorni · tocca per modificare</p>
        </div>
        <Button
          onClick={generate}
          disabled={busy}
          data-testid="plan-generate-button"
          className="rounded-full bg-indigo-600 hover:bg-indigo-700 text-white"
        >
          <Sparkles className="w-4 h-4 mr-1" /> {busy ? "Genero..." : "Rigenera"}
        </Button>
      </header>

      {loading ? (
        <div className="text-slate-500 text-sm">Carico...</div>
      ) : dates.length === 0 ? (
        <div className="bg-white rounded-2xl p-8 text-center border border-slate-100 card-elevated">
          <div className="w-14 h-14 mx-auto rounded-full bg-indigo-50 border border-indigo-100 flex items-center justify-center text-indigo-600 mb-3">
            <Sparkles className="w-6 h-6" />
          </div>
          <h3 className="font-bold text-slate-900">Nessun piano attivo</h3>
          <p className="text-sm text-slate-500 mt-1 mb-4">Aggiungi esami e genera il piano AI</p>
          <Button onClick={generate} disabled={busy} className="rounded-full bg-indigo-600 hover:bg-indigo-700 text-white" data-testid="plan-empty-generate">
            Genera piano ora
          </Button>
        </div>
      ) : (
        <div className="space-y-4 stagger">
          {dates.map((d) => (
            <div key={d} className="bg-white rounded-2xl p-5 border border-slate-100 card-elevated">
              <div className="flex items-baseline justify-between mb-3">
                <h3 className="font-bold text-slate-900">{formatShortDate(d)}</h3>
                <span className="text-xs text-slate-500 font-mono">{grouped[d].length} sessioni</span>
              </div>
              <div className="space-y-2">
                {grouped[d].map((t) => (
                  <TaskRow
                    key={t.id}
                    task={t}
                    testIdPrefix="plan-task"
                    onStatus={(s, pct) => setStatus(t.id, s, pct)}
                    onEdit={setEditing}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      <TaskEditModal
        open={!!editing}
        task={editing}
        onClose={() => setEditing(null)}
        onSaved={() => { setEditing(null); load(); }}
      />
    </div>
  );
}
