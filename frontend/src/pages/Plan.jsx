import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { BLOCK_STYLES, STATUS_LABEL, STATUS_STYLES, formatShortDate } from "@/lib/utils-sf";
import { Sparkles, Check, Clock, CircleDashed } from "lucide-react";
import { toast } from "sonner";

export default function Plan() {
  const [tasks, setTasks] = useState([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  const load = async () => {
    setLoading(true);
    try {
      const today = new Date().toISOString().slice(0, 10);
      const end = new Date(Date.now() + 30 * 86400000).toISOString().slice(0, 10);
      const r = await api.get(`/tasks?date_from=${today}&date_to=${end}`);
      setTasks(r.data);
    } finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

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

  const setStatus = async (id, status) => {
    try {
      await api.put(`/tasks/${id}`, { status });
      setTasks(ts => ts.map(t => t.id === id ? { ...t, status } : t));
    } catch { toast.error("Errore"); }
  };

  const grouped = tasks.reduce((acc, t) => {
    (acc[t.date] = acc[t.date] || []).push(t);
    return acc;
  }, {});
  const dates = Object.keys(grouped).sort();

  return (
    <div className="space-y-4 fade-in">
      <header className="flex items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900">Piano di studio</h1>
          <p className="text-sm text-slate-500 mt-1">Prossimi 30 giorni</p>
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
                  <div key={t.id} className="flex items-center gap-3 p-3 rounded-xl bg-slate-50/60 border border-slate-100" data-testid={`plan-task-${t.id}`}>
                    <div className="font-mono text-xs font-semibold text-slate-700 min-w-[86px]">
                      {t.start_time}–{t.end_time}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${BLOCK_STYLES[t.block_type] || BLOCK_STYLES.Teoria}`}>{t.block_type}</span>
                        <span className="text-xs text-slate-500 truncate">{t.exam_name}</span>
                      </div>
                      <p className="text-sm text-slate-800 font-medium mt-0.5 truncate">{t.topic}</p>
                    </div>
                    <StatusPicker task={t} onChange={(s) => setStatus(t.id, s)} />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function StatusPicker({ task, onChange }) {
  const opts = [
    { s: "completato", icon: Check, cls: "text-emerald-600" },
    { s: "parziale", icon: Clock, cls: "text-amber-600" },
    { s: "non_completato", icon: CircleDashed, cls: "text-rose-500" },
  ];
  return (
    <div className="flex gap-1 shrink-0">
      {opts.map(({ s, icon: Icon, cls }) => (
        <button
          key={s}
          onClick={() => onChange(s)}
          data-testid={`plan-status-${task.id}-${s}`}
          title={STATUS_LABEL[s]}
          className={`w-8 h-8 rounded-full flex items-center justify-center border transition-all ${
            task.status === s
              ? `${STATUS_STYLES[s]} border-transparent`
              : `bg-white ${cls} border-slate-200 hover:border-slate-300`
          }`}
        >
          <Icon className="w-3.5 h-3.5" />
        </button>
      ))}
    </div>
  );
}
