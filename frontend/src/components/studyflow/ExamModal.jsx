import React, { useState, useEffect } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Slider } from "@/components/ui/slider";
import { DIFFICULTY_STYLES } from "@/lib/utils-sf";
import { toast } from "sonner";

const empty = {
  name: "", exam_date: "", cfu: 6,
  difficulty: "Media", prep_percent: 0,
  estimated_hours: 40, notes: "",
};

export default function ExamModal({ open, onClose, onSaved, exam }) {
  const [form, setForm] = useState(empty);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (exam) setForm({ ...empty, ...exam });
    else setForm(empty);
  }, [exam, open]);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const submit = async (e) => {
    e.preventDefault();
    if (!form.name || !form.exam_date) {
      toast.error("Nome e data sono obbligatori");
      return;
    }
    setBusy(true);
    try {
      const payload = {
        ...form,
        cfu: Number(form.cfu),
        prep_percent: Number(form.prep_percent),
        estimated_hours: Number(form.estimated_hours),
      };
      if (exam?.id) await api.put(`/exams/${exam.id}`, payload);
      else await api.post("/exams", payload);
      toast.success(exam ? "Esame aggiornato" : "Esame aggiunto");
      onSaved?.();
    } catch (e) {
      toast.error("Errore nel salvataggio");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o)=>!o && onClose?.()}>
      <DialogContent className="max-w-lg rounded-2xl p-0 overflow-hidden max-h-[90vh] overflow-y-auto">
        <DialogHeader className="p-6 pb-3">
          <DialogTitle className="text-xl font-bold text-slate-900">
            {exam ? "Modifica esame" : "Nuovo esame"}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={submit} className="px-6 pb-6 space-y-4">
          <div>
            <Label className="text-xs font-semibold text-slate-600">Nome esame</Label>
            <Input data-testid="exam-name-input" value={form.name} onChange={(e)=>set("name", e.target.value)} placeholder="Es. Analisi I" className="mt-1.5 h-11 rounded-xl" />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs font-semibold text-slate-600">Data</Label>
              <Input data-testid="exam-date-input" type="date" value={form.exam_date} onChange={(e)=>set("exam_date", e.target.value)} className="mt-1.5 h-11 rounded-xl" />
            </div>
            <div>
              <Label className="text-xs font-semibold text-slate-600">CFU</Label>
              <Input data-testid="exam-cfu-input" type="number" min="1" max="24" value={form.cfu} onChange={(e)=>set("cfu", e.target.value)} className="mt-1.5 h-11 rounded-xl" />
            </div>
          </div>

          <div>
            <Label className="text-xs font-semibold text-slate-600">Difficoltà</Label>
            <div className="flex gap-2 mt-1.5">
              {["Facile","Media","Difficile"].map((d) => (
                <button
                  key={d}
                  type="button"
                  data-testid={`exam-difficulty-${d}`}
                  onClick={() => set("difficulty", d)}
                  className={`flex-1 h-10 rounded-full text-sm font-semibold border transition-all ${
                    form.difficulty === d
                      ? `${DIFFICULTY_STYLES[d]} ring-2 ring-offset-1 ring-slate-300`
                      : "bg-white text-slate-600 border-slate-200 hover:border-slate-300"
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>

          <div>
            <div className="flex justify-between items-baseline">
              <Label className="text-xs font-semibold text-slate-600">Preparazione attuale</Label>
              <span className="text-sm font-semibold text-indigo-600">{form.prep_percent}%</span>
            </div>
            <Slider
              value={[Number(form.prep_percent)]}
              onValueChange={(v)=>set("prep_percent", v[0])}
              max={100}
              step={5}
              className="mt-3"
              data-testid="exam-prep-slider"
            />
          </div>

          <div>
            <Label className="text-xs font-semibold text-slate-600">Ore stimate totali</Label>
            <Input data-testid="exam-hours-input" type="number" min="5" max="500" value={form.estimated_hours} onChange={(e)=>set("estimated_hours", e.target.value)} className="mt-1.5 h-11 rounded-xl" />
          </div>

          <div>
            <Label className="text-xs font-semibold text-slate-600">Note (opzionale)</Label>
            <Textarea data-testid="exam-notes-input" value={form.notes || ""} onChange={(e)=>set("notes", e.target.value)} placeholder="Argomenti, capitoli..." className="mt-1.5 rounded-xl" rows={2} />
          </div>

          <div className="flex gap-2 pt-2">
            <Button type="button" variant="outline" onClick={onClose} className="rounded-full h-11 flex-1">Annulla</Button>
            <Button type="submit" disabled={busy} data-testid="exam-save-button" className="rounded-full h-11 flex-1 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold">
              {busy ? "Salvo..." : "Salva"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
