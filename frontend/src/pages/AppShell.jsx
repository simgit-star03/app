import React, { useState } from "react";
import { Outlet, NavLink, useNavigate, useLocation } from "react-router-dom";
import { Home as HomeIcon, BookOpen, Calendar, BarChart3, Sparkles, User, Plus } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import ExamModal from "@/components/studyflow/ExamModal";

const NAV = [
  { to: "/home", label: "Home", icon: HomeIcon, key: "home" },
  { to: "/esami", label: "Esami", icon: BookOpen, key: "esami" },
  { to: "/piano", label: "Piano", icon: Calendar, key: "piano" },
  { to: "/progressi", label: "Progressi", icon: BarChart3, key: "progressi" },
  { to: "/tutor", label: "Tutor AI", icon: Sparkles, key: "assistant" },
  { to: "/profilo", label: "Profilo", icon: User, key: "profilo" },
];

export default function AppShell() {
  const { user } = useAuth();
  const [addOpen, setAddOpen] = useState(false);
  const nav = useNavigate();
  const loc = useLocation();

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Desktop sidebar */}
      <aside className="hidden md:flex flex-col w-64 fixed left-0 top-0 bottom-0 bg-white border-r border-slate-200 p-5 z-30">
        <div className="flex items-center gap-2 mb-8">
          <div className="w-9 h-9 rounded-xl bg-indigo-600 text-white flex items-center justify-center font-bold">SF</div>
          <div>
            <div className="font-bold text-slate-900 leading-tight">StudyFlow</div>
            <div className="text-xs text-slate-500">Piano al passo con te</div>
          </div>
        </div>
        <nav className="flex-1 space-y-1">
          {NAV.map((n) => (
            <NavLink
              key={n.key}
              to={n.to}
              data-testid={`nav-item-${n.key}`}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${
                  isActive
                    ? "bg-indigo-50 text-indigo-700"
                    : "text-slate-600 hover:bg-slate-100"
                }`
              }
            >
              <n.icon className="w-4 h-4" /> {n.label}
            </NavLink>
          ))}
        </nav>
        <button
          onClick={() => setAddOpen(true)}
          data-testid="fab-add-exam-button-desktop"
          className="mt-4 w-full h-11 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-sm flex items-center justify-center gap-2 pill-shadow"
        >
          <Plus className="w-4 h-4" /> Nuovo esame
        </button>
        {user && (
          <div className="mt-4 pt-4 border-t border-slate-100 flex items-center gap-2">
            <div className="w-8 h-8 rounded-full bg-slate-100 text-slate-700 font-semibold text-xs flex items-center justify-center">
              {(user.name || user.email || "?").slice(0, 1).toUpperCase()}
            </div>
            <div className="min-w-0">
              <div className="text-xs font-semibold text-slate-900 truncate">{user.name}</div>
              <div className="text-xs text-slate-500 truncate">{user.email}</div>
            </div>
          </div>
        )}
      </aside>

      <main className="md:ml-64 pb-24 md:pb-8 min-h-screen">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 py-4 sm:py-8">
          <Outlet />
        </div>
      </main>

      {/* Mobile FAB */}
      <button
        onClick={() => setAddOpen(true)}
        data-testid="fab-add-exam-button"
        className="md:hidden fixed bottom-20 right-4 z-50 w-14 h-14 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white flex items-center justify-center pill-shadow active:scale-95 transition-all"
        aria-label="Aggiungi esame"
      >
        <Plus className="w-6 h-6" />
      </button>

      {/* Bottom nav mobile */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-40 bg-white/95 backdrop-blur-md border-t border-slate-200 px-2 py-2 flex justify-around">
        {NAV.filter(n => n.key !== "profilo" || true).slice(0, 5).map((n) => {
          const active = loc.pathname === n.to;
          return (
            <button
              key={n.key}
              onClick={() => nav(n.to)}
              data-testid={`bottom-nav-${n.key}`}
              className={`flex flex-col items-center justify-center px-2 py-1 rounded-lg min-w-[52px] ${
                active ? "text-indigo-600" : "text-slate-500"
              }`}
            >
              <n.icon className="w-5 h-5" />
              <span className="text-[10px] font-medium mt-0.5">{n.label}</span>
            </button>
          );
        })}
        <button
          onClick={() => nav("/profilo")}
          data-testid="bottom-nav-profilo"
          className={`flex flex-col items-center justify-center px-2 py-1 rounded-lg min-w-[52px] ${
            loc.pathname === "/profilo" ? "text-indigo-600" : "text-slate-500"
          }`}
        >
          <User className="w-5 h-5" />
          <span className="text-[10px] font-medium mt-0.5">Profilo</span>
        </button>
      </nav>

      <ExamModal open={addOpen} onClose={() => setAddOpen(false)} onSaved={() => setAddOpen(false)} />
    </div>
  );
}
