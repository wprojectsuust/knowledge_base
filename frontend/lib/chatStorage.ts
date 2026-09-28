import type { Clarification } from "@/lib/api";

const STORAGE_KEY = "uunit.chat";
const MAX_STORED = 50;

/** Что из реплики переживает перезагрузку. Карта и маршрут - нет: они нужны только в моменте. */
export type StoredExchange = {
  id: number;
  question: string;
  answer: string | null;
  clarification: Clarification | null;
  clarifiedWith: string | null;
  error: string | null;
};

/**
 * Чат живёт только в браузере (localStorage): без аккаунтов и серверных сессий.
 * Сервер получает последние реплики вместе с вопросом и нигде их не хранит.
 */
export function loadChat(): StoredExchange[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as StoredExchange[]) : [];
  } catch {
    return [];
  }
}

export function saveChat(exchanges: StoredExchange[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(exchanges.slice(-MAX_STORED)));
  } catch {
    // приватный режим / переполнение - просто не сохраняем
  }
}

export function clearChat() {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // нечего чистить
  }
}
