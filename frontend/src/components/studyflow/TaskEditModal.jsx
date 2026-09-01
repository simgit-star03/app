import React, { useEffect, useState } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent,
  AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle, AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { BLOCK_STYLES } from "@/lib/utils-sf";
import { Trash2 } from "lucide-react";
import { toast } from "sonner";

const BLOCKS = ["Teoria", "Esercizi", "Ripasso", "Simulazione", "Altro"];

export default function TaskEditModal({ open, task, onClose, onSaved }) {
  const [form, setForm] = useState(null);
  const [exams, setExams] = useState([]);
  const [busy, setBusy] = useState(false);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (open) {
      api.get("/exams").then((r) => setExams(r.data));
    }
  }, [open]);

  useEffect(() => {
    if (task) {
      setForm({
        exam_id: task.exam_id,
        date: task.date,
        start_time: task.start_time,
        duration_min: task.duration_min || 90,
        block_type: task.block_type,
        topic: task.topic || "",
      });
    }
  }, [task]);

  if (!form) return null;

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.patch(`/tasks/${task.id}`, {
        exam_id: form.exam_id,
        date: form.date,
        start_time: form.start_time,
        duration_min: Number(form.duration_min),
        block_type: form.block_type,
        topic: form.topic,
      });
      toast.success("Sessione aggiornata");
      onSaved?.();
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Errore aggiornamento");
    } finally {
      setBusy(false);
    }
  };

  const del = async () => {
    setDeleting(true);
    try {
      await api.delete(`/tasks/${task.id}`);
      toast.success("Sessione eliminata");
      onSaved?.();
    } catch (err) {
      toast.error("Errore eliminazione");
    } finally {
      setDeleting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose?.()}>
      <DialogContent className="max-w-md rounded-2xl p-0 overflow-hidden max-h-[92vh] overflow-y-auto">
        <DialogHeader className="p-6 pb-3">
          <DialogTitle className="text-xl font-bold text-slate-900">Modifica sessione</DialogTitle>
        </DialogHeader>
        <form onSubmit={save} className="px-6 pb-6 space-y-4">
          <div>
            <Label className="text-xs font-semibold text-slate-600">Esame</Label>
            <Select value={form.exam_id} onValueChange={(v) => set("exam_id", v)}>
              <SelectTrigger data-testid="task-edit-exam" className="mt-1.5 h-11 rounded-xl">
                <SelectValue placeholder="Seleziona esame" />
              </SelectTrigger>
              <SelectContent>
                {exams.map((e) => (
                  <SelectItem key={e.id} value={e.id}>{e.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs font-semibold text-slate-600">Data</Label>
              <Input
                data-testid="task-edit-date"
                type="date"
                value={form.date}
                onChange={(e) => set("date", e.target.value)}
                className="mt-1.5 h-11 rounded-xl"
                required
              />
            </div>
            <div>
              <Label className="text-xs font-semibold text-slate-600">Ora inizio</Label>
              <Input
                data-testid="task-edit-start"
                type="time"
                value={form.start_time}
                onChange={(e) => set("start_time", e.target.value)}
                className="mt-1.5 h-11 rounded-xl"
                required
              />
            </div>
          </div>

          <div>
            <Label className="text-xs font-semibold text-slate-600">Durata</Label>
            <div className="flex gap-2 mt-1.5 flex-wrap">
              {[30, 45, 60, 90, 120].map((m) => (
                <button
                  type="button"
                  key={m}
                  data-testid={`task-edit-dur-${m}`}
                  onClick={() => set("duration_min", m)}
                  className={`flex-1 min-w-[52px] h-10 rounded-full text-sm font-semibold border transition-all ${
                    Number(form.duration_min) === m
                      ? "bg-indigo-600 text-white border-indigo-600"
                      : "bg-white text-slate-700 border-slate-200 hover:border-indigo-300"
                  }`}
                >
                  {m}m
                </button>
              ))}
            </div>
          </div>

          <div>
            <Label className="text-xs font-semibold text-slate-600">Tipo di attività</Label>
            <div className="flex gap-1.5 mt-1.5 flex-wrap">
              {BLOCKS.map((b) => (
                <button
                  type="button"
                  key={b}
                  data-testid={`task-edit-block-${b}`}
                  onClick={() => set("block_type", b)}
                  className={`px-3 h-9 rounded-full text-xs font-semibold border transition-all ${
                    form.block_type === b
                      ? `${BLOCK_STYLES[b] || "bg-slate-100 text-slate-800 border-slate-300"} ring-2 ring-offset-1 ring-slate-300`
                      : "bg-white text-slate-600 border-slate-200"
                  }`}
                >
                  {b}
                </button>
              ))}
            </div>
          </div>

          <div>
            <Label className="text-xs font-semibold text-slate-600">Descrizione</Label>
            <Textarea
              data-testid="task-edit-topic"
              value={form.topic}
              onChange={(e) => set("topic", e.target.value)}
              rows={2}
              className="mt-1.5 rounded-xl"
              placeholder="Argomento della sessione"
            />
          </div>

          <div className="flex gap-2 pt-2">
            <AlertDialog>
              <AlertDialogTrigger asChild>
                <Button
                  type="button"
                  variant="outline"
                  disabled={deleting}
                  data-testid="task-edit-delete"
                  className="rounded-full h-11 text-rose-600 border-rose-200 hover:bg-rose-50"
                >
                  <Trash2 className="w-4 h-4 mr-1" /> {deleting ? "..." : "Elimina"}
                </Button>
              </AlertDialogTrigger>
              <AlertDialogContent>
                <AlertDialogHeader>
                  <AlertDialogTitle>Eliminare questa sessione?</AlertDialogTitle>
                  <AlertDialogDescription>La sessione verrà rimossa dal piano e i progressi ricalcolati.</AlertDialogDescription>
                </AlertDialogHeader>
                <AlertDialogFooter>
                  <AlertDialogCancel>Annulla</AlertDialogCancel>
                  <AlertDialogAction onClick={del} data-testid="task-edit-delete-confirm" className="bg-rose-600 hover:bg-rose-700">
                    Elimina
                  </AlertDialogAction>
                </AlertDialogFooter>
              </AlertDialogContent>
            </AlertDialog>
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              data-testid="task-edit-cancel"
              className="rounded-full h-11 flex-1"
            >
              Annulla
            </Button>
            <Button
              type="submit"
              disabled={busy}
              data-testid="task-edit-save"
              className="rounded-full h-11 flex-1 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold"
            >
              {busy ? "Salvo..." : "Salva"}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  );
}
