"use client";

import React, { createContext, useContext, useState, useCallback, useEffect } from "react";
import en from "@/locales/en.json";
import pt from "@/locales/pt.json";

export type Language = "en" | "pt";

const translations: Record<Language, Record<string, unknown>> = { en, pt };

function resolvePath(obj: Record<string, unknown>, path: string): string {
  return path.split(".").reduce<unknown>((acc, key) => {
    if (acc && typeof acc === "object") return (acc as Record<string, unknown>)[key];
    return undefined;
  }, obj) as string ?? path;
}

interface LanguageContextValue {
  lang: Language;
  setLang: (lang: Language) => void;
  t: (key: string, vars?: Record<string, string | number>) => string;
}

const LanguageContext = createContext<LanguageContextValue>({
  lang: "en",
  setLang: () => {},
  t: (key) => key,
});

export function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Language>("en");

  useEffect(() => {
    const stored = localStorage.getItem("xiaolee_lang") as Language | null;
    if (stored === "en" || stored === "pt") setLangState(stored);
  }, []);

  const setLang = useCallback((l: Language) => {
    setLangState(l);
    localStorage.setItem("xiaolee_lang", l);
    document.documentElement.lang = l === "pt" ? "pt-BR" : "en";
  }, []);

  const t = useCallback((key: string, vars?: Record<string, string | number>): string => {
    let str = resolvePath(translations[lang] as Record<string, unknown>, key);
    if (vars) {
      Object.entries(vars).forEach(([k, v]) => {
        str = str.replace(`{{${k}}}`, String(v));
      });
    }
    return str;
  }, [lang]);

  return (
    <LanguageContext.Provider value={{ lang, setLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export const useLanguage = () => useContext(LanguageContext);
