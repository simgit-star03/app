import React, { useEffect, useRef, useState } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Sparkles, Send } from "lucide-react";

const SUGGESTIONS = [
  "Ho solo 2 ore oggi, come modifico il piano?",
  "Non posso studiare venerdì.",
  "Quale esame devo prioritizzare?",
  "Quanto dovrei studiare oggi?",
];

export default function Assistant() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const scrollRef = useRef(null);

  useEffect(() => {
    api.get("/chat/history").then((r) => {
      const hist = [];
      r.data.forEach((h) => {
        hist.push({ role: "user", text: h.user_msg });
        hist.push({ role: "assistant", text: h.assistant_msg });
      });
      setMessages(hist);
      if (r.data.length) setSessionId(r.data[r.data.length - 1].session_id);
    });
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  const send = async (text) => {
    if (!text.trim()) return;
    setMessages((m) => [...m, { role: "user", text }]);
    setInput("");
    setBusy(true);
    try {
      const r = await api.post("/chat", { message: text, session_id: sessionId });
      setSessionId(r.data.session_id);
      setMessages((m) => [...m, { role: "assistant", text: r.data.reply }]);
    } catch (e) {
      setMessages((m) => [...m, { role: "assistant", text: "Errore nel rispondere. Riprova." }]);
    } finally { setBusy(false); }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] md:h-[calc(100vh-4rem)] fade-in">
      <header className="pb-3">
        <div className="flex items-center gap-2">
          <div className="w-10 h-10 rounded-full bg-indigo-600 text-white flex items-center justify-center">
            <Sparkles className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-slate-900">Tutor AI</h1>
            <p className="text-xs text-slate-500">Conosce i tuoi esami e il tuo piano</p>
          </div>
        </div>
      </header>

      <div ref={scrollRef} className="flex-1 overflow-y-auto space-y-3 pb-4 pr-1" data-testid="chat-messages">
        {messages.length === 0 && (
          <div className="bg-white rounded-2xl p-5 border border-slate-100 card-elevated">
            <p className="text-sm text-slate-700 font-semibold mb-3">Prova a chiedermi:</p>
            <div className="grid gap-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  data-testid={`chat-suggestion-${s.slice(0,10)}`}
                  className="text-left text-sm px-4 py-2.5 rounded-xl bg-indigo-50/70 hover:bg-indigo-100 text-indigo-800 border border-indigo-100 transition-all"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap ${
              m.role === "user"
                ? "bg-indigo-600 text-white rounded-br-md"
                : "bg-white border border-slate-100 text-slate-800 rounded-bl-md card-elevated"
            }`}>
              {m.text}
            </div>
          </div>
        ))}
        {busy && (
          <div className="flex justify-start">
            <div className="bg-white border border-slate-100 rounded-2xl px-4 py-3 text-sm text-slate-500 flex gap-1">
              <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
              <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
              <span className="w-1.5 h-1.5 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
            </div>
          </div>
        )}
      </div>

      <form onSubmit={(e) => { e.preventDefault(); send(input); }} className="flex gap-2 pt-2 border-t border-slate-100">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Scrivi al tutor..."
          data-testid="ai-chat-input-field"
          disabled={busy}
          className="h-11 rounded-full flex-1"
        />
        <Button
          type="submit"
          disabled={busy || !input.trim()}
          data-testid="ai-chat-send-button"
          className="h-11 w-11 p-0 rounded-full bg-indigo-600 hover:bg-indigo-700 text-white shrink-0"
        >
          <Send className="w-4 h-4" />
        </Button>
      </form>
    </div>
  );
}
