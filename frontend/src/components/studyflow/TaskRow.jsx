import React, { useState } from "react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { Check, Clock, X, CircleDashed, Pencil } from "lucide-react";
import { BLOCK_STYLES } from "@/lib/utils-sf";

const PARTIAL_OPTIONS = [25, 50, 75];

export default function TaskRow({ task, onStatus, onEdit, testIdPrefix = "task" }) {
  const [partialOpen, setPartialOpen] = useState(false);
  const done = task.status === "completato";
  const partial = task.status === "parziale";
  const notDone = task.status === "non_completato";

  const setPartial = (pct) => {
    onStatus("parziale", pct);
    setPartialOpen(false);
  };

  return (
    <div
      className={`flex items-center gap-3 p-3 rounded-xl border transition-all ${
        done ? "bg-emerald-50/60 border-emerald-100"
        : partial ? "bg-amber-50/60 border-amber-100"
        : notDone ? "bg-rose-50/60 border-rose-100"
        : "bg-slate-50/60 border-slate-100"
      }`}
      data-testid={`${testIdPrefix}-row-${task.id}`}
    >
      <button
        onClick={() => onStatus(done ? "pianificato" : "completato")}
        data-testid={`${testIdPrefix}-toggle-${task.id}`}
        className={`shrink-0 w-7 h-7 rounded-full border-2 flex items-center justify-center transition-all ${
          done ? "bg-emerald-500 border-emerald-500 text-white"
          : "border-slate-300 hover:border-indigo-400 bg-white"
        }`}
        aria-label={done ? "Segna come da fare" : "Segna come completata"}
      >
        {done && <Check className="w-4 h-4" />}
      </button>

      <button
        onClick={() => onEdit?.(task)}
        data-testid={`${testIdPrefix}-open-edit-${task.id}`}
        className="min-w-0 flex-1 text-left"
      >
        <div className="flex items-center gap-2 flex-wrap">
          <span className="font-mono text-xs font-semibold text-slate-700">
            {task.start_time}–{task.end_time}
          </span>
          <span className={`text-[10px] font-semibold px-2 py-0.5 rounded-full border ${BLOCK_STYLES[task.block_type] || "bg-slate-100 border-slate-200 text-slate-700"}`}>
            {task.block_type}
          </span>
          {partial && task.partial_pct && (
            <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200">
              {task.partial_pct}%
            </span>
          )}
        </div>
        <p className={`text-sm mt-0.5 truncate ${done ? "text-slate-400 line-through" : "text-slate-800 font-medium"}`}>
          {task.topic}
        </p>
        <p className="text-xs text-slate-500 truncate">{task.exam_name}</p>
      </button>

      <div className="flex gap-1 shrink-0">
        <Popover open={partialOpen} onOpenChange={setPartialOpen}>
          <PopoverTrigger asChild>
            <button
              data-testid={`${testIdPrefix}-partial-${task.id}`}
              className={`w-8 h-8 rounded-full flex items-center justify-center border transition-all ${
                partial
                  ? "bg-amber-100 border-amber-300 text-amber-800"
                  : "bg-white text-amber-600 border-slate-200 hover:border-amber-300"
              }`}
              aria-label="Segna parziale"
            >
              <Clock className="w-3.5 h-3.5" />
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-40 p-2 rounded-xl" side="top">
            <p className="text-[10px] font-semibold text-slate-500 uppercase mb-1.5 px-2">Quanto hai fatto?</p>
            <div className="grid grid-cols-3 gap-1">
              {PARTIAL_OPTIONS.map((p) => (
                <button
                  key={p}
                  onClick={() => setPartial(p)}
                  data-testid={`${testIdPrefix}-partial-${task.id}-${p}`}
                  className={`h-8 rounded-lg text-xs font-semibold ${
                    task.partial_pct === p
                      ? "bg-amber-500 text-white"
                      : "bg-amber-50 text-amber-800 hover:bg-amber-100"
                  }`}
                >
                  {p}%
                </button>
              ))}
            </div>
          </PopoverContent>
        </Popover>

        <button
          onClick={() => onStatus(notDone ? "pianificato" : "non_completato")}
          data-testid={`${testIdPrefix}-notdone-${task.id}`}
          className={`w-8 h-8 rounded-full flex items-center justify-center border transition-all ${
            notDone
              ? "bg-rose-100 border-rose-300 text-rose-700"
              : "bg-white text-rose-500 border-slate-200 hover:border-rose-300"
          }`}
          aria-label="Segna non svolta"
        >
          <X className="w-3.5 h-3.5" />
        </button>

        <button
          onClick={() => onEdit?.(task)}
          data-testid={`${testIdPrefix}-edit-${task.id}`}
          className="w-8 h-8 rounded-full flex items-center justify-center border bg-white text-slate-500 border-slate-200 hover:border-indigo-300 hover:text-indigo-600 transition-all"
          aria-label="Modifica"
        >
          <Pencil className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
}
