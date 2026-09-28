export const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type Location = {
  building: string;
  room: string | null;
  floor: number | null;
};

export type Clarification = {
  field: string;
  question: string;
};

export type Fact = {
  field: string;
  value: string;
};

export type RoutePoint = {
  x: number;
  y: number;
  /** 0 - улица */
  floor: number;
  building: string | null;
};

export type Route = {
  campus: string;
  from_label: string;
  to_label: string;
  steps: string[];
  text: string;
  distance_m: number;
  minutes: number;
  points: RoutePoint[];
};

/** Ровно одно из answer / clarification не null. route - если спросили «как пройти». */
export type AskQuestionResponse = {
  answer: string | null;
  clarification: Clarification | null;
  location: Location | null;
  route: Route | null;
};

/** Реплика чата для контекста («а туда как пройти?»). */
export type HistoryTurn = {
  question: string;
  answer: string;
};

export async function askQuestion(
  question: string,
  facts: Fact[] = [],
  history: HistoryTurn[] = [],
): Promise<AskQuestionResponse> {
  const response = await fetch(`${API_BASE_URL}/question`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, facts: facts.map(({ field, value }) => ({ field, value })), history }),
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Сервер ответил ${response.status}`);
  }

  const data: AskQuestionResponse = await response.json();
  return {
    answer: data.answer ?? null,
    clarification: data.clarification ?? null,
    location: data.location ?? null,
    route: data.route ?? null,
  };
}

const SOURCE_PATTERN = /\[Источник:\s*([^\]]+)]/gi;

export function extractSources(answer: string): string[] {
  const found = new Set<string>();
  for (const match of answer.matchAll(SOURCE_PATTERN)) {
    found.add(match[1].trim());
  }
  return Array.from(found);
}

export function stripSourceTags(answer: string): string {
  return answer.replace(SOURCE_PATTERN, "").replace(/[ \t]+\n/g, "\n").trim();
}

/** Маршрут по кампусу: откуда (по умолчанию КПП) и куда - "7-404", "7", "7@3", "kpp", "place:library". */
export async function buildRoute(source: string | null, target: string): Promise<Route> {
  const response = await fetch(`${API_BASE_URL}/route`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source, target }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Сервер ответил ${response.status}`);
  }
  return response.json();
}
