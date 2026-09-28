"use client";

import { useCallback, useEffect, useState } from "react";
import type { Fact } from "@/lib/api";

const STORAGE_KEY = "uunit.studentFacts";

const FIELD_LABELS: Record<string, string> = {
  group: "Группа",
  faculty: "Факультет",
  course: "Курс",
};

export function factLabel(field: string) {
  return FIELD_LABELS[field] ?? field;
}

function load(): Fact[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Fact[]) : [];
  } catch {
    return [];
  }
}

function save(facts: Fact[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(facts));
  } catch {
    // приватный режим / запрет хранилища - просто не запоминаем между визитами
  }
}

/**
 * Сведения о студенте, которые он уже сообщил в ответ на уточнения ИИ (группа и т.п.).
 * Хранятся только в браузере и отправляются с каждым вопросом, чтобы ИИ не переспрашивал.
 */
export function useStudentFacts() {
  const [facts, setFacts] = useState<Fact[]>([]);

  useEffect(() => setFacts(load()), []);

  const remember = useCallback((fact: Fact) => {
    const next = [...load().filter((item) => item.field !== fact.field), fact];
    save(next);
    setFacts(next);
    return next;
  }, []);

  const forget = useCallback((field: string) => {
    const next = load().filter((item) => item.field !== field);
    save(next);
    setFacts(next);
  }, []);

  return { facts, remember, forget };
}
