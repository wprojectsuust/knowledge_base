"use client";

import { useState } from "react";
import { Sidebar } from "@/components/Sidebar";
import { QuickAccessCard } from "@/components/QuickAccessCard";
import { askQuestion, extractSources, stripSourceTags } from "@/lib/api";

const POPULAR_QUESTIONS = [
  "Где находится деканат?",
  "Как получить справку?",
  "Расписание занятий",
  "Кто мой тьютор?",
  "Что делать, если пропустил пару?",
  "Где найти методички?",
];

const QUICK_ACCESS = [
  {
    icon: "🗓️",
    title: "Расписание",
    description: "Узнайте своё расписание, найдите аудитории и получите подсказки по маршруту.",
    question: "Как узнать расписание своей группы?",
  },
  {
    icon: "📍",
    title: "Навигация",
    description: "Как добраться до корпусов, аудиторий и подразделений университета.",
    question: "Как добраться до главного корпуса?",
  },
  {
    icon: "📄",
    title: "Документы",
    description: "Справки, заявления, образцы и важные формы.",
    question: "Как получить справку об обучении?",
  },
  {
    icon: "🛡️",
    title: "Правила и регламенты",
    description: "Учебный процесс, пересдачи, стипендии, проживание и другие правила.",
    question: "Какие правила пересдачи экзаменов?",
  },
];

type Status = "idle" | "loading" | "error";

export default function HomePage() {
  const [question, setQuestion] = useState("");
  const [askedQuestion, setAskedQuestion] = useState<string | null>(null);
  const [answer, setAnswer] = useState<string | null>(null);
  const [status, setStatus] = useState<Status>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  async function handleAsk(text: string) {
    const trimmed = text.trim();
    if (!trimmed) return;

    setStatus("loading");
    setErrorMessage(null);
    setAskedQuestion(trimmed);

    try {
      const result = await askQuestion(trimmed);
      setAnswer(result);
      setStatus("idle");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Не удалось получить ответ.");
      setStatus("error");
    }
  }

  function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    void handleAsk(question);
  }

  const sources = answer ? extractSources(answer) : [];
  const answerText = answer ? stripSourceTags(answer) : "";

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      <Sidebar />

      <main style={{ flex: 1, padding: "48px 56px", display: "flex", flexDirection: "column", gap: 48 }}>
        <div style={{ display: "flex", gap: 48, alignItems: "flex-start" }}>
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 24 }}>
            <span
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 8,
                width: "fit-content",
                fontSize: 13,
                fontWeight: 600,
                letterSpacing: 1,
                textTransform: "uppercase",
                color: "var(--muted)",
                background: "var(--panel)",
                border: "1px solid var(--border)",
                borderRadius: 999,
                padding: "8px 16px",
              }}
            >
              ✦ УУНиТ · База знаний
            </span>

            <h1
              style={{
                margin: 0,
                fontFamily: "'Space Grotesk', sans-serif",
                fontWeight: 700,
                fontSize: 48,
                lineHeight: 1.15,
              }}
            >
              Задайте вопрос — <span style={{ color: "var(--accent)" }}>получите ответ</span>
            </h1>

            <p style={{ margin: 0, fontSize: 18, color: "var(--muted)", lineHeight: 1.6, maxWidth: 560 }}>
              База знаний УУНиТ собрала всё важное об университете, учёбе и студенческой жизни в одном
              месте.
            </p>

            <form
              onSubmit={handleSubmit}
              style={{
                display: "flex",
                gap: 12,
                background: "var(--panel)",
                border: "1px solid var(--border-strong)",
                borderRadius: 16,
                padding: 8,
              }}
            >
              <input
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="Например: где получить справку об обучении?"
                style={{
                  flex: 1,
                  background: "transparent",
                  border: "none",
                  outline: "none",
                  color: "var(--text)",
                  fontSize: 16,
                  padding: "12px 16px",
                }}
              />
              <button
                type="submit"
                disabled={status === "loading"}
                style={{
                  background: "var(--accent)",
                  border: "none",
                  borderRadius: 12,
                  color: "#fff",
                  fontWeight: 600,
                  fontSize: 15,
                  padding: "0 24px",
                  cursor: "pointer",
                  opacity: status === "loading" ? 0.7 : 1,
                }}
              >
                {status === "loading" ? "Ищу…" : "Спросить →"}
              </button>
            </form>

            <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
              <p style={{ margin: 0, fontSize: 14, color: "var(--muted)" }}>Популярные вопросы:</p>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 10 }}>
                {POPULAR_QUESTIONS.map((item) => (
                  <button
                    key={item}
                    onClick={() => {
                      setQuestion(item);
                      void handleAsk(item);
                    }}
                    style={{
                      background: "var(--panel)",
                      border: "1px solid var(--border)",
                      borderRadius: 999,
                      color: "var(--text)",
                      fontSize: 14,
                      padding: "10px 18px",
                      cursor: "pointer",
                    }}
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div
            style={{
              flex: 1,
              maxWidth: 480,
              background: "var(--panel)",
              border: "1px solid var(--border)",
              borderRadius: 20,
              padding: 28,
              display: "flex",
              flexDirection: "column",
              gap: 20,
              minHeight: 420,
            }}
          >
            {askedQuestion ? (
              <div
                style={{
                  background: "var(--accent-soft)",
                  border: `1px solid var(--accent-border)`,
                  borderRadius: 14,
                  padding: "14px 18px",
                  fontSize: 15,
                  fontWeight: 500,
                }}
              >
                {askedQuestion}
              </div>
            ) : (
              <p style={{ margin: 0, color: "var(--muted)", fontSize: 15 }}>
                Задайте вопрос слева — ответ появится здесь, вместе с источниками.
              </p>
            )}

            {status === "loading" && (
              <p style={{ margin: 0, color: "var(--muted)", fontSize: 15 }}>Ищу ответ в базе знаний…</p>
            )}

            {status === "error" && (
              <p style={{ margin: 0, color: "#ff9a94", fontSize: 15 }}>{errorMessage}</p>
            )}

            {answer && status !== "loading" && (
              <>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <span style={{ color: "var(--accent)" }}>✦</span>
                  <p style={{ margin: 0, fontWeight: 600, fontSize: 15 }}>Ответ</p>
                </div>
                <p style={{ margin: 0, fontSize: 15, lineHeight: 1.7, color: "var(--text)", whiteSpace: "pre-wrap" }}>
                  {answerText}
                </p>

                {sources.length > 0 && (
                  <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                    <p style={{ margin: 0, fontWeight: 600, fontSize: 14, color: "var(--muted)" }}>Источники</p>
                    {sources.map((source) => (
                      <div
                        key={source}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: 10,
                          fontSize: 14,
                          color: "var(--muted)",
                        }}
                      >
                        <span>📎</span>
                        {source}
                      </div>
                    ))}
                  </div>
                )}

                <button
                  onClick={() => {
                    setAnswer(null);
                    setAskedQuestion(null);
                    setQuestion("");
                  }}
                  style={{
                    marginTop: "auto",
                    background: "var(--panel-2)",
                    border: "1px solid var(--border)",
                    borderRadius: 12,
                    color: "var(--text)",
                    fontSize: 14,
                    fontWeight: 500,
                    padding: "12px",
                    cursor: "pointer",
                  }}
                >
                  ⟳ Задать новый вопрос
                </button>
              </>
            )}
          </div>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
          <p style={{ margin: 0, fontSize: 15, fontWeight: 600, color: "var(--muted)" }}>Быстрый доступ</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 20 }}>
            {QUICK_ACCESS.map((item) => (
              <QuickAccessCard
                key={item.title}
                icon={item.icon}
                title={item.title}
                description={item.description}
                onClick={() => {
                  setQuestion(item.question);
                  void handleAsk(item.question);
                }}
              />
            ))}
          </div>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "var(--panel)",
            border: "1px solid var(--border)",
            borderRadius: 20,
            padding: "24px 32px",
            flexWrap: "wrap",
            gap: 16,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
            <span style={{ fontSize: 22 }}>🛡️</span>
            <p style={{ margin: 0, fontSize: 15, color: "var(--muted)" }}>
              Ответы формируются по данным университета и сопровождаются источниками.
            </p>
          </div>
          <div style={{ display: "flex", gap: 24, fontSize: 14, color: "var(--muted-2)" }}>
            <span>🗄️ Актуальная информация из официальных источников УУНиТ</span>
            <span>✅ Проверенные данные со ссылками на источники</span>
            <span>⚡ Быстрый поиск и умная фильтрация</span>
          </div>
        </div>
      </main>
    </div>
  );
}
