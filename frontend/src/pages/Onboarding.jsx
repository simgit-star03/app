import React, { useState } from "react";
import { useNavigate, Navigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { DAYS } from "@/lib/utils-sf";
import { toast } from "sonner";
import { ArrowRight, ArrowLeft, Check } from "lucide-react";

export default function Onboarding() {
  const { user, refreshUser } = useAuth();
  const nav = useNavigate();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState({
    name: user?.name || "",
    university: "",
    degree_course: "",
    daily_hours: 4,
    available_days: ["lun","mar","mer","gio","ven"],
    graduation_goal: "",
  });
  const [busy, setBusy] = useState(false);

  if (!user) return <Navigate to="/" replace />;
  if (user.onboarded) return <Navigate to="/home" replace />;

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const toggleDay = (d) => {
    setForm((f) => ({
      ...f,
      available_days: f.available_days.includes(d)
        ? f.available_days.filter((x) => x !== d)
        : [...f.available_days, d],
    }));
  };

  const submit = async () => {
    setBusy(true);
    try {
      await api.post("/auth/onboarding", form);
      await refreshUser();
      toast.success("Perfetto! Aggiungiamo il primo esame.");
      nav("/esami?first=1");
    } catch (e) {
      toast.error("Errore. Riprova.");
    } finally {
      setBusy(false);
    }
  };

  const steps = [
    { title: "Come ti chiami?", sub: "Iniziamo con qualche info di base" },
    { title: "Dove studi?", sub: "Aiutaci a personalizzare il piano" },
    { title: "Quando puoi studiare?", sub: "La routine settimanale" },
    { title: "Obiettivo (opzionale)", sub: "Un traguardo che vuoi raggiungere" },
  ];

  const canNext = () => {
    if (step === 0) return form.name.trim().length > 0;
    if (step === 1) return form.university.trim() && form.degree_course.trim();
    if (step === 2) return form.daily_hours > 0 && form.available_days.length > 0;
    return true;
  };

  return (
    <div className="min-h-screen grid-noise p-4 sm:p-8 flex items-center justify-center">
      <div className="max-w-lg w-full">
        <div className="flex items-center gap-2 mb-6">
          {steps.map((_, i) => (
            <div
              key={i}
              className={`h-1.5 flex-1 rounded-full transition-all ${
                i <= step ? "bg-indigo-600" : "bg-slate-200"
              }`}
            />
          ))}
        </div>

        <div className="bg-white rounded-3xl p-6 sm:p-8 card-elevated border border-slate-100 fade-in">
          <p className="text-xs font-semibold text-indigo-600 uppercase tracking-wider">Passo {step + 1} / {steps.length}</p>
          <h2 className="text-2xl sm:text-3xl font-bold text-slate-900 mt-1">{steps[step].title}</h2>
          <p className="text-sm text-slate-500 mt-1">{steps[step].sub}</p>

          <div className="mt-6 space-y-4">
            {step === 0 && (
              <div>
                <Label className="text-xs font-semibold text-slate-600">Nome</Label>
                <Input data-testid="onb-name-input" value={form.name} onChange={(e)=>set("name", e.target.value)} placeholder="Il tuo nome" className="mt-1.5 h-11 rounded-xl" />
              </div>
            )}
            {step === 1 && (
              <>
                <div>
                  <Label className="text-xs font-semibold text-slate-600">Università</Label>
                  <Input data-testid="onb-university-input" value={form.university} onChange={(e)=>set("university", e.target.value)} placeholder="Es. Università di Bologna" className="mt-1.5 h-11 rounded-xl" />
                </div>
                <div>
                  <Label className="text-xs font-semibold text-slate-600">Corso di laurea</Label>
                  <Input data-testid="onb-degree-input" value={form.degree_course} onChange={(e)=>set("degree_course", e.target.value)} placeholder="Es. Ingegneria Informatica" className="mt-1.5 h-11 rounded-xl" />
                </div>
              </>
            )}
            {step === 2 && (
              <>
                <div>
                  <Label className="text-xs font-semibold text-slate-600">Ore di studio al giorno</Label>
                  <div className="flex gap-2 mt-1.5">
                    {[2,3,4,5,6,8].map((h) => (
                      <button
                        key={h}
                        type="button"
                        data-testid={`onb-hours-${h}`}
                        onClick={() => set("daily_hours", h)}
                        className={`flex-1 h-11 rounded-xl text-sm font-semibold border transition-all ${
                          form.daily_hours === h
                            ? "bg-indigo-600 text-white border-indigo-600"
                            : "bg-white text-slate-700 border-slate-200 hover:border-indigo-300"
                        }`}
                      >
                        {h}h
                      </button>
                    ))}
                  </div>
                </div>
                <div>
                  <Label className="text-xs font-semibold text-slate-600">Giorni disponibili</Label>
                  <div className="flex gap-1.5 mt-1.5 flex-wrap">
                    {DAYS.map((d) => (
                      <button
                        key={d.id}
                        type="button"
                        data-testid={`onb-day-${d.id}`}
                        onClick={() => toggleDay(d.id)}
                        className={`px-3 h-10 rounded-full text-sm font-semibold border transition-all ${
                          form.available_days.includes(d.id)
                            ? "bg-indigo-600 text-white border-indigo-600"
                            : "bg-white text-slate-700 border-slate-200 hover:border-indigo-300"
                        }`}
                      >
                        {d.label}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}
            {step === 3 && (
              <div>
                <Label className="text-xs font-semibold text-slate-600">Il tuo obiettivo</Label>
                <Input data-testid="onb-goal-input" value={form.graduation_goal} onChange={(e)=>set("graduation_goal", e.target.value)} placeholder="Es. Laurea con 108/110" className="mt-1.5 h-11 rounded-xl" />
                <p className="text-xs text-slate-400 mt-2">Puoi lasciarlo vuoto e aggiungerlo più tardi.</p>
              </div>
            )}
          </div>

          <div className="mt-8 flex gap-3">
            {step > 0 && (
              <Button variant="outline" onClick={() => setStep(step - 1)} className="rounded-full h-11 flex-1">
                <ArrowLeft className="w-4 h-4 mr-1" /> Indietro
              </Button>
            )}
            {step < steps.length - 1 ? (
              <Button
                onClick={() => setStep(step + 1)}
                disabled={!canNext()}
                data-testid="onb-next-button"
                className="rounded-full h-11 flex-1 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold"
              >
                Continua <ArrowRight className="w-4 h-4 ml-1" />
              </Button>
            ) : (
              <Button
                onClick={submit}
                disabled={busy}
                data-testid="onb-complete-button"
                className="rounded-full h-11 flex-1 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold"
              >
                <Check className="w-4 h-4 mr-1" /> {busy ? "Salvo..." : "Iniziamo"}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
