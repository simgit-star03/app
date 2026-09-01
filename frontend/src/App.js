import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import Landing from "@/pages/Landing";
import Onboarding from "@/pages/Onboarding";
import AppShell from "@/pages/AppShell";
import Home from "@/pages/Home";
import Exams from "@/pages/Exams";
import Plan from "@/pages/Plan";
import Progress from "@/pages/Progress";
import Assistant from "@/pages/Assistant";
import Profile from "@/pages/Profile";

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="p-8 text-slate-500">Caricamento...</div>;
  if (!user) return <Navigate to="/" replace />;
  if (!user.onboarded) return <Navigate to="/onboarding" replace />;
  return children;
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Toaster position="top-center" richColors />
        <Routes>
          <Route path="/" element={<Landing />} />
          <Route path="/onboarding" element={<Onboarding />} />
          <Route element={<Protected><AppShell /></Protected>}>
            <Route path="/home" element={<Home />} />
            <Route path="/esami" element={<Exams />} />
            <Route path="/piano" element={<Plan />} />
            <Route path="/progressi" element={<Progress />} />
            <Route path="/tutor" element={<Assistant />} />
            <Route path="/profilo" element={<Profile />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
