import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/context/AuthContext";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Sparkles, GraduationCap, Zap, ArrowRight } from "lucide-react";
import { toast } from "sonner";

export default function Landing() {
  const { login, signup, user } = useAuth();
  const nav = useNavigate();
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [busy, setBusy] = useState(false);

  React.useEffect(() => {
    if (user) nav(user.onboarded ? "/home" : "/onboarding");
  }, [user, nav]);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const u = mode === "login"
        ? await login(email, password)
        : await signup(email, password, name);
      toast.success(mode === "login" ? "Bentornato!" : "Benvenuto in StudyFlow");
      nav(u.onboarded ? "/home" : "/onboarding");
    } catch (err) {
      toast.error(err?.response?.data?.detail || "Errore. Riprova.");
    } finally {
      setBusy(false);
    }
  };

  const fillDemo = () => {
    setEmail("demo@studyflow.it");
    setPassword("Demo1234!");
    setMode("login");
  };

  return (
    <div className="min-h-screen grid-noise flex items-center justify-center p-4">
      <div className="max-w-5xl w-full grid md:grid-cols-2 gap-8 items-center">
        <div className="fade-in space-y-6 md:pr-8">
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white border border-slate-200 pill-shadow text-xs font-semibold text-indigo-700">
            <Sparkles className="w-3.5 h-3.5" /> AI-powered study planner
          </div>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-extrabold text-slate-900 leading-[1.05]">
            StudyFlow
          </h1>
          <p className="text-lg sm:text-xl text-slate-600 max-w-md">
            Il tuo piano di studio.<br/>
            <span className="text-indigo-600 font-semibold">Sempre al passo con te.</span>
          </p>
          <div className="space-y-3 pt-2">
            <Feature icon={<GraduationCap className="w-4 h-4" />} text="Aggiungi i tuoi esami e ricevi un piano su misura" />
            <Feature icon={<Zap className="w-4 h-4" />} text="Se rimani indietro, l'AI ricalcola tutto in un tap" />
            <Feature icon={<Sparkles className="w-4 h-4" />} text="Tutor AI che conosce i tuoi esami e ti risponde" />
          </div>
          <Button
            variant="outline"
            onClick={fillDemo}
            data-testid="landing-demo-fill"
            className="rounded-full border-slate-300 text-slate-700"
          >
            Prova con account demo <ArrowRight className="w-4 h-4 ml-1" />
          </Button>
        </div>

        <div className="bg-white rounded-3xl p-6 sm:p-8 card-elevated border border-slate-100 fade-in">
          <Tabs value={mode} onValueChange={setMode}>
            <TabsList className="grid grid-cols-2 w-full rounded-full bg-slate-100 p-1 h-11">
              <TabsTrigger value="login" data-testid="landing-login-tab" className="rounded-full">Accedi</TabsTrigger>
              <TabsTrigger value="signup" data-testid="landing-signup-tab" className="rounded-full">Registrati</TabsTrigger>
            </TabsList>

            <form onSubmit={submit} className="space-y-4 mt-6">
              {mode === "signup" && (
                <div>
                  <Label htmlFor="name" className="text-xs font-semibold text-slate-600">Nome</Label>
                  <Input id="name" data-testid="signup-name-input" value={name} onChange={(e)=>setName(e.target.value)} placeholder="Il tuo nome" required className="mt-1.5 h-11 rounded-xl" />
                </div>
              )}
              <div>
                <Label htmlFor="email" className="text-xs font-semibold text-slate-600">Email</Label>
                <Input id="email" data-testid="auth-email-input" type="email" value={email} onChange={(e)=>setEmail(e.target.value)} placeholder="tu@università.it" required className="mt-1.5 h-11 rounded-xl" />
              </div>
              <div>
                <Label htmlFor="pw" className="text-xs font-semibold text-slate-600">Password</Label>
                <Input id="pw" data-testid="auth-password-input" type="password" value={password} onChange={(e)=>setPassword(e.target.value)} placeholder="min. 8 caratteri" required minLength={6} className="mt-1.5 h-11 rounded-xl" />
              </div>
              <Button
                type="submit"
                disabled={busy}
                data-testid="auth-submit-button"
                className="w-full h-11 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white font-semibold"
              >
                {busy ? "Attendi..." : mode === "login" ? "Accedi" : "Crea account"}
              </Button>
              <p className="text-xs text-slate-500 text-center">
                Continuando accetti i termini di StudyFlow.
              </p>
            </form>
          </Tabs>
        </div>
      </div>
    </div>
  );
}

function Feature({ icon, text }) {
  return (
    <div className="flex items-center gap-3">
      <div className="w-8 h-8 rounded-full bg-indigo-50 border border-indigo-100 text-indigo-600 flex items-center justify-center">
        {icon}
      </div>
      <span className="text-sm text-slate-700">{text}</span>
    </div>
  );
}
