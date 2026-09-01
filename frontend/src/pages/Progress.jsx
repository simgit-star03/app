import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { Progress } from "@/components/ui/progress";
import { DIFFICULTY_STYLES, daysUntil, formatShortDate } from "@/lib/utils-sf";
import { BarChart3, TrendingUp, Target } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, ResponsiveContainer, Tooltip, CartesianGrid, Cell,
} from "recharts";

export default function ProgressPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/progress").then((r) => setData(r.data)).finally(() => setLoading(false));
  }, []);

  if (loading || !data) return <div className="text-slate-500">Carico...</div>;

  const upcoming = data.exams.filter(e => daysUntil(e.exam_date) >= 0).slice(0, 5);

  return (
    <div className="space-y-4 fade-in">
      <header>
        <h1 className="text-2xl sm:text-3xl font-bold text-slate-900">Progressi</h1>
        <p className="text-sm text-slate-500 mt-1">Panoramica della tua settimana</p>
      </header>

      <div className="grid grid-cols-3 gap-3">
        <MetricCard icon={<BarChart3 className="w-4 h-4" />} label="Pianificate" value={`${data.week_planned_hours}h`} tone="slate" />
        <MetricCard icon={<TrendingUp className="w-4 h-4" />} label="Completate" value={`${data.week_completed_hours}h`} tone="emerald" />
        <MetricCard icon={<Target className="w-4 h-4" />} label="Completamento" value={`${data.completion_percent}%`} tone="indigo" />
      </div>

      <section className="bg-white rounded-2xl p-5 border border-slate-100 card-elevated">
        <h3 className="font-bold text-slate-900 mb-3">Ore per giorno</h3>
        <div style={{ width: "100%", height: 224, minHeight: 224 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data.daily} barGap={4}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" vertical={false} />
              <XAxis dataKey="day_label" stroke="#94A3B8" fontSize={12} tickLine={false} axisLine={false} />
              <YAxis stroke="#94A3B8" fontSize={12} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{ borderRadius: 12, border: "1px solid #E2E8F0", fontSize: 12 }}
                labelStyle={{ fontWeight: 600, color: "#0F172A" }}
              />
              <Bar dataKey="planned_hours" name="Pianificate" fill="#C7D2FE" radius={[6, 6, 0, 0]} />
              <Bar dataKey="completed_hours" name="Completate" fill="#4F46E5" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="bg-white rounded-2xl p-5 border border-slate-100 card-elevated">
        <h3 className="font-bold text-slate-900 mb-3">Preparazione per esame</h3>
        {data.exams.length === 0 ? (
          <p className="text-sm text-slate-500">Nessun esame ancora.</p>
        ) : (
          <div className="space-y-3">
            {data.exams.map((e) => (
              <div key={e.id} data-testid={`progress-exam-${e.id}`}>
                <div className="flex items-baseline justify-between mb-1.5">
                  <div className="flex items-center gap-2 min-w-0">
                    <p className="font-semibold text-slate-800 truncate">{e.name}</p>
                    <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded-full border ${DIFFICULTY_STYLES[e.difficulty]}`}>{e.difficulty}</span>
                  </div>
                  <span className="text-xs font-mono font-semibold text-slate-600 shrink-0 ml-2">{e.prep_percent}%</span>
                </div>
                <Progress value={e.prep_percent} className="h-2" />
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="bg-white rounded-2xl p-5 border border-slate-100 card-elevated">
        <h3 className="font-bold text-slate-900 mb-3">Prossimi esami</h3>
        {upcoming.length === 0 ? (
          <p className="text-sm text-slate-500">Nessun esame in programma.</p>
        ) : (
          <div className="space-y-2">
            {upcoming.map((e) => (
              <div key={e.id} className="flex items-center justify-between p-3 rounded-xl bg-slate-50/60 border border-slate-100">
                <div className="min-w-0">
                  <p className="font-semibold text-slate-800 truncate">{e.name}</p>
                  <p className="text-xs text-slate-500">{formatShortDate(e.exam_date)}</p>
                </div>
                <div className="text-right shrink-0 ml-2">
                  <div className="text-lg font-bold font-mono text-slate-900">{daysUntil(e.exam_date)}</div>
                  <div className="text-[10px] font-semibold uppercase text-slate-500">giorni</div>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function MetricCard({ icon, label, value, tone }) {
  const tones = {
    slate: "bg-white text-slate-900",
    emerald: "bg-emerald-50 text-emerald-800 border-emerald-100",
    indigo: "bg-indigo-50 text-indigo-800 border-indigo-100",
  };
  return (
    <div className={`rounded-2xl p-4 border ${tone === "slate" ? "border-slate-100" : ""} ${tones[tone]} card-elevated`}>
      <div className="flex items-center gap-1.5 opacity-70 text-xs font-semibold">{icon} {label}</div>
      <div className="text-2xl font-bold font-mono mt-1">{value}</div>
    </div>
  );
}
