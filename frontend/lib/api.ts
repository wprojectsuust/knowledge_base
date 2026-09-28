const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

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

/** Ровно одно из answer / clarification не null. */
export type AskQuestionResponse = {
  answer: string | null;
  clarification: Clarification | null;
  location: Location | null;
};

export async function askQuestion(question: string, facts: Fact[] = []): Promise<AskQuestionResponse> {
  const response = await fetch(`${API_BASE_URL}/question`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, facts: facts.map(({ field, value }) => ({ field, value })) }),
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
