import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "@/lib/api";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { DAYS } from "@/lib/utils-sf";
import { LogOut, GraduationCap, Save } from "lucide-react";
import { toast } from "sonner";

export default function Profile() {
  const { logout, refreshUser } = useAuth();
  const [p, setP] = useState(null);
  const [busy, setBusy] = useState(false);
  const nav = useNavigate();

  useEffect(() => {
    api.get("/profile").then((r) => setP(r.data));
  }, []);

  const set = (k, v) => setP((f) => ({ ...f, [k]: v }));

  const toggleDay = (d) => {
    setP((f) => ({
      ...f,
      available_days: f.available_days?.includes(d)
        ? f.available_days.filter((x) => x !== d)
        : [...(f.available_days || []), d],
    }));
  };

  const save = async () => {
    setBusy(true);
    try {
      await api.put("/profile", p);
      await refreshUser();
      toast.success("Profilo aggiornato");
    } catch { toast.error("Errore"); }
    finally { setBusy(false); }
  };

  const doLogout = () => {
    logout();
    nav("/", { replace: true });
  };

  if (!p) return <div className="text-slate-500">Carico...</div>;

  return (
    <div className="space-y-4 fade-in">
      <header>
        <h1 className="text-2xl sm:text-3xl font-bold text-slate-900">Profilo</h1>
        <p className="text-sm text-slate-500 mt-1">{p.email}</p>
      </header>

      <section className="bg-white rounded-2xl p-5 border border-slate-100 card-elevated space-y-4">
        <div>
          <Label className="text-xs font-semibold text-slate-600">Nome</Label>
          <Input data-testid="profile-name" value={p.name || ""} onChange={(e)=>set("name", e.target.value)} className="mt-1.5 h-11 rounded-xl" />
        </div>
        <div>
          <Label className="text-xs font-semibold text-slate-600">Università</Label>
          <Input data-testid="profile-university" value={p.university || ""} onChange={(e)=>set("university", e.target.value)} className="mt-1.5 h-11 rounded-xl" />
        </div>
        <div>
          <Label className="text-xs font-semibold text-slate-600">Corso di laurea</Label>
          <Input data-testid="profile-degree" value={p.degree_course || ""} onChange={(e)=>set("degree_course", e.target.value)} className="mt-1.5 h-11 rounded-xl" />
        </div>
        <div>
          <Label className="text-xs font-semibold text-slate-600">Obiettivo laurea</Label>
          <Input data-testid="profile-goal" value={p.graduation_goal || ""} onChange={(e)=>set("graduation_goal", e.target.value)} placeholder="Es. 110/110" className="mt-1.5 h-11 rounded-xl" />
        </div>
      </section>

      <section className="bg-white rounded-2xl p-5 border border-slate-100 card-elevated">
        <h3 className="font-bold text-slate-900 flex items-center gap-2 mb-3">
          <GraduationCap className="w-4 h-4 text-indigo-600" /> Disponibilità
        </h3>
        <div>
          <Label className="text-xs font-semibold text-slate-600">Ore al giorno</Label>
          <div className="flex gap-2 mt-1.5">
            {[2,3,4,5,6,8].map((h) => (
              <button
                key={h}
                type="button"
                onClick={() => set("daily_hours", h)}
                data-testid={`profile-hours-${h}`}
                className={`flex-1 h-10 rounded-xl text-sm font-semibold border transition-all ${
                  Number(p.daily_hours) === h
                    ? "bg-indigo-600 text-white border-indigo-600"
                    : "bg-white text-slate-700 border-slate-200 hover:border-indigo-300"
                }`}
              >{h}h</button>
            ))}
          </div>
        </div>
        <div className="mt-4">
          <Label className="text-xs font-semibold text-slate-600">Giorni disponibili</Label>
          <div className="flex gap-1.5 mt-1.5 flex-wrap">
            {DAYS.map((d) => (
              <button
                key={d.id}
                type="button"
                onClick={() => toggleDay(d.id)}
                data-testid={`profile-day-${d.id}`}
                className={`px-3 h-10 rounded-full text-sm font-semibold border transition-all ${
                  p.available_days?.includes(d.id)
                    ? "bg-indigo-600 text-white border-indigo-600"
                    : "bg-white text-slate-700 border-slate-200"
                }`}
              >{d.label}</button>
            ))}
          </div>
        </div>
      </section>

      <Button onClick={save} disabled={busy} data-testid="profile-save" className="w-full h-11 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold">
        <Save className="w-4 h-4 mr-1" /> {busy ? "Salvo..." : "Salva modifiche"}
      </Button>

      <Button onClick={doLogout} variant="outline" data-testid="profile-logout" className="w-full h-11 rounded-full text-rose-600 border-rose-200 hover:bg-rose-50">
        <LogOut className="w-4 h-4 mr-1" /> Esci
      </Button>
    </div>
  );
}
