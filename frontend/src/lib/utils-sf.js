export const DIFFICULTY_STYLES = {
  Facile: "bg-emerald-50 text-emerald-700 border-emerald-200",
  Media: "bg-blue-50 text-blue-700 border-blue-200",
  Difficile: "bg-amber-50 text-amber-800 border-amber-200",
};

export const BLOCK_STYLES = {
  Teoria: "bg-indigo-50 text-indigo-800 border-indigo-200",
  Esercizi: "bg-emerald-50 text-emerald-800 border-emerald-200",
  Ripasso: "bg-amber-50 text-amber-900 border-amber-200",
  Simulazione: "bg-purple-50 text-purple-800 border-purple-200",
};

export const STATUS_STYLES = {
  completato: "bg-emerald-100 text-emerald-800",
  parziale: "bg-amber-100 text-amber-800",
  non_completato: "bg-rose-100 text-rose-700",
  pianificato: "bg-slate-100 text-slate-600",
};

export const STATUS_LABEL = {
  completato: "Completato",
  parziale: "Parziale",
  non_completato: "Non fatto",
  pianificato: "Da fare",
};

export const DAYS = [
  { id: "lun", label: "Lun" },
  { id: "mar", label: "Mar" },
  { id: "mer", label: "Mer" },
  { id: "gio", label: "Gio" },
  { id: "ven", label: "Ven" },
  { id: "sab", label: "Sab" },
  { id: "dom", label: "Dom" },
];

export function daysUntil(dateStr) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const d = new Date(dateStr);
  d.setHours(0, 0, 0, 0);
  return Math.round((d - today) / (1000 * 60 * 60 * 24));
}

export function formatItalianDate(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString("it-IT", { day: "numeric", month: "long", year: "numeric" });
}

export function formatShortDate(dateStr) {
  const d = new Date(dateStr);
  return d.toLocaleDateString("it-IT", { day: "numeric", month: "short" });
}

export function greeting(name) {
  const h = new Date().getHours();
  const prefix = h < 12 ? "Buongiorno" : h < 18 ? "Buon pomeriggio" : "Buonasera";
  return `${prefix}${name ? ", " + name : ""}`;
}
