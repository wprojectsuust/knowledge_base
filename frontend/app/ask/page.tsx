"use client";

import { useEffect, useRef, useState } from "react";
import { BookmarkLockIcon, SearchIcon, SendIcon, SparkleIcon, TentIcon } from "@/components/Icons";
import { ClarificationPrompt } from "@/components/ClarificationPrompt";
import { FactChips } from "@/components/FactChips";
import { Markdown } from "@/components/Markdown";
import { SourcesList } from "@/components/SourcesList";
import { Typewriter } from "@/components/Typewriter";
import { VenueMap } from "@/components/VenueMap";
import {
  askQuestion,
  extractSources,
  stripSourceTags,
  type Clarification,
  type Fact,
  type HistoryTurn,
  type Location,
  type Route,
} from "@/lib/api";
import { clearChat, loadChat, saveChat } from "@/lib/chatStorage";
import { useStudentFacts } from "@/lib/useStudentFacts";

const SUGGESTIONS = [
  "Где находится деканат?",
  "Как получить справку об обучении?",
  "Когда у меня кончаются пары сегодня?",
  "Что делать, если пропустил пару?",
];

type Exchange = {
  id: number;
  question: string;
  answer: string | null;
  clarification: Clarification | null;
  /** что студент ответил на уточнение - показываем его репликой в ленте */
  clarifiedWith: string | null;
  location: Location | null;
  route: Route | null;
  error: string | null;
  typed: boolean;
  /** восстановлена из прошлого визита - показываем сразу, без печати и без карты */
  restored: boolean;
};

const HISTORY_TURNS = 6;

/** Последние завершённые реплики - контекст для «а туда как пройти?». */
function historyOf(exchanges: Exchange[], exceptId?: number): HistoryTurn[] {
  return exchanges
    .filter((item) => item.answer && item.id !== exceptId)
    .slice(-HISTORY_TURNS)
    .map((item) => ({ question: item.question, answer: stripSourceTags(item.answer!) }));
}

export default function AskPage() {
  const [question, setQuestion] = useState("");
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [loading, setLoading] = useState(false);
  const threadEndRef = useRef<HTMLDivElement>(null);
  const { facts, remember, forget } = useStudentFacts();
  const [chatLoaded, setChatLoaded] = useState(false);

  useEffect(() => {
    setExchanges(
      loadChat().map((item) => ({
        ...item,
        // ответ так и не пришёл (закрыли вкладку во время запроса)
        error: item.answer || item.clarification || item.error ? item.error : "Ответ не был получен — спросите ещё раз.",
        location: null,
        route: null,
        typed: true,
        restored: true,
      })),
    );
    setChatLoaded(true);
  }, []);

  useEffect(() => {
    if (!chatLoaded) return;
    saveChat(
      exchanges.map(({ id, question, answer, clarification, clarifiedWith, error }) => ({
        id,
        question,
        answer,
        clarification,
        clarifiedWith,
        error,
      })),
    );
  }, [exchanges, chatLoaded]);

  function newChat() {
    clearChat();
    setExchanges([]);
  }

  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [exchanges]);

  function update(id: number, patch: Partial<Exchange>) {
    setExchanges((prev) => prev.map((item) => (item.id === id ? { ...item, ...patch } : item)));
  }

  async function run(id: number, text: string, knownFacts: Fact[], history: HistoryTurn[]) {
    setLoading(true);
    try {
      const result = await askQuestion(text, knownFacts, history);
      update(id, { answer: result.answer, clarification: result.clarification, location: result.location, route: result.route });
    } catch (error) {
      update(id, { error: error instanceof Error ? error.message : "Не удалось получить ответ." });
    } finally {
      setLoading(false);
    }
  }

  function handleAsk(text: string) {
    const trimmed = text.trim();
    if (!trimmed || loading) return;

    const id = Date.now();
    setExchanges((prev) => [
      ...prev,
      {
        id,
        question: trimmed,
        answer: null,
        clarification: null,
        clarifiedWith: null,
        location: null,
        route: null,
        error: null,
        typed: false,
        restored: false,
      },
    ]);
    setQuestion("");
    void run(id, trimmed, facts, historyOf(exchanges));
  }

  function answerClarification(item: Exchange, value: string) {
    if (!item.clarification) return;
    const nextFacts = remember({ field: item.clarification.field, value });
    update(item.id, { clarification: null, clarifiedWith: value });
    // тот же исходный вопрос, но уже с новым сведением о студенте
    void run(item.id, item.question, nextFacts, historyOf(exchanges, item.id));
  }

  const searchForm = (
    <form
      className="search ask-search"
      onSubmit={(event) => {
        event.preventDefault();
        void handleAsk(question);
      }}
    >
      <SearchIcon size={22} />
      <input
        autoFocus
        value={question}
        onChange={(event) => setQuestion(event.target.value)}
        placeholder="Спросите что угодно об университете…"
      />
      <button className="search-button" type="submit" disabled={loading} aria-label="Спросить">
        <SendIcon size={22} />
      </button>
    </form>
  );

  const factChips = <FactChips facts={facts} onForget={forget} />;

  // карту показываем только для самого свежего ответа, если в нём есть место
  const last = exchanges[exchanges.length - 1];
  const lastWithLocation = !last?.restored && (last?.location || last?.route) ? last : null;

  if (exchanges.length === 0) {
    return (
      <section className="ask-empty">
        <span className="pill">
          <TentIcon size={14} />
          УУНиТ База знаний
        </span>
        <h1 className="hero-title ask-title">
          Чем <span className="accent">помочь?</span>
        </h1>
        <p className="ask-subtitle">
          Спросите про учёбу, документы, корпуса или своё расписание — ответ придёт с источниками.
        </p>
        {searchForm}
        {factChips}
        <div className="chips ask-chips">
          {SUGGESTIONS.map((item) => (
            <button key={item} className="chip" type="button" onClick={() => handleAsk(item)}>
              {item}
            </button>
          ))}
        </div>
      </section>
    );
  }

  return (
    <section className="ask-chat">
      <div className="ask-chat-head">
        <span className="ask-chat-note">Чат хранится только в этом браузере</span>
        <button type="button" className="chip" onClick={newChat} disabled={loading}>
          Новый чат
        </button>
      </div>
      <div className="ask-thread">
        {exchanges.map((item) => {
          const done = item.answer !== null || item.error !== null || item.clarification !== null;
          return (
            <article key={item.id} className="answer-shell">
              <div className="question-bar">
                <span className="q-icon">
                  <BookmarkLockIcon size={15} />
                </span>
                <span className="q-text">{item.question}</span>
              </div>

              <div className="answer-card ask-answer">
                <div className="answer-head">
                  <SparkleIcon size={18} />
                  Ответ
                </div>

                {item.clarifiedWith && (
                  <div className="clarified">
                    <span>{item.clarifiedWith}</span>
                  </div>
                )}
                {item.clarification && (
                  <ClarificationPrompt
                    clarification={item.clarification}
                    onSubmit={(value) => answerClarification(item, value)}
                  />
                )}
                {!done && (
                  <div className="skeleton">
                    <span style={{ width: "92%" }} />
                    <span style={{ width: "80%" }} />
                    <span style={{ width: "64%" }} />
                  </div>
                )}
                {item.error && <p className="answer-text error-text">{item.error}</p>}
                {item.answer !== null && (
                  <>
                    {item.restored ? (
                      <div className="answer-text">
                        <Markdown text={stripSourceTags(item.answer)} />
                      </div>
                    ) : (
                      <Typewriter
                        className="answer-text"
                        text={stripSourceTags(item.answer)}
                        onDone={() => update(item.id, { typed: true })}
                      />
                    )}
                    <SourcesList sources={extractSources(item.answer)} />
                  </>
                )}
              </div>
            </article>
          );
        })}
        <div ref={threadEndRef} />
      </div>

      <div className="ask-composer">
        {searchForm}
        {factChips}
      </div>

      {lastWithLocation && (
        <VenueMap
          key={lastWithLocation.id}
          location={lastWithLocation.location}
          route={lastWithLocation.route}
          ready={lastWithLocation.typed}
          onDismiss={() => update(lastWithLocation.id, { location: null, route: null })}
        />
      )}
    </section>
  );
}
