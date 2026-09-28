"use client";

import { useState } from "react";
import { QuickAccessCard } from "@/components/QuickAccessCard";
import { SourcesList } from "@/components/SourcesList";
import {
  BookmarkLockIcon,
  CalendarIcon,
  DatabaseIcon,
  DocumentIcon,
  ExternalLinkIcon,
  MapPinIcon,
  RefreshIcon,
  SearchIcon,
  SendIcon,
  ShieldCheckIcon,
  ShieldIcon,
  SparkleIcon,
  TentIcon,
  ZapIcon,
} from "@/components/Icons";
import { ClarificationPrompt } from "@/components/ClarificationPrompt";
import { FactChips } from "@/components/FactChips";
import { Typewriter } from "@/components/Typewriter";
import { VenueMap } from "@/components/VenueMap";
import { askQuestion, extractSources, stripSourceTags, type Clarification, type Fact, type Location, type Route } from "@/lib/api";
import { useStudentFacts } from "@/lib/useStudentFacts";

const POPULAR_QUESTIONS = [
  "Где находится деканат?",
  "Как получить справку?",
  "Расписание занятий",
  "Кто мой тьютор?",
  "Что делать, если пропустил пару?",
  "Где найти методички?",
  "Какие есть мероприятия?",
];

const QUICK_ACCESS = [
  {
    icon: <CalendarIcon size={28} />,
    title: "Расписание",
    description: "Узнайте своё расписание, найдите аудитории и получите подсказки по маршруту.",
    question: "Как узнать расписание своей группы?",
  },
  {
    icon: <MapPinIcon size={28} />,
    title: "Навигация",
    description: "Как добраться до корпусов, аудиторий и подразделений университета.",
    question: "Как добраться до главного корпуса?",
  },
  {
    icon: <DocumentIcon size={28} />,
    title: "Документы",
    description: "Справки, заявления, образцы и важные формы.",
    question: "Как получить справку об обучении?",
  },
  {
    icon: <ShieldIcon size={28} />,
    title: "Правила и регламенты",
    description: "Учебный процесс, пересдачи, стипендии, проживание и другие правила.",
    question: "Какие правила пересдачи экзаменов?",
  },
];

const TRUST_ITEMS = [
  { Icon: DatabaseIcon, title: "Актуальная информация", sub: "из официальных источников УУНиТ" },
  { Icon: ShieldIcon, title: "Проверенные данные", sub: "с ссылками на источники" },
  { Icon: ZapIcon, title: "Быстрый поиск", sub: "и умная фильтрация" },
];

type Status = "idle" | "loading" | "error";

export default function HomePage() {
  const [question, setQuestion] = useState("");
  const [askedQuestion, setAskedQuestion] = useState<string | null>(null);
  const [answer, setAnswer] = useState<string | null>(null);
  const [location, setLocation] = useState<Location | null>(null);
  const [route, setRoute] = useState<Route | null>(null);
  const [typed, setTyped] = useState(false);
  const [status, setStatus] = useState<Status>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [clarification, setClarification] = useState<Clarification | null>(null);
  const [clarifiedWith, setClarifiedWith] = useState<string | null>(null);
  const { facts, remember, forget } = useStudentFacts();

  async function handleAsk(text: string, knownFacts: Fact[] = facts, keepClarified = false) {
    const trimmed = text.trim();
    if (!trimmed || status === "loading") return;

    setClarification(null);
    if (!keepClarified) setClarifiedWith(null);

    setStatus("loading");
    setErrorMessage(null);
    setAnswer(null);
    setLocation(null);
    setRoute(null);
    setTyped(false);
    setAskedQuestion(trimmed);

    try {
      const result = await askQuestion(trimmed, knownFacts);
      setClarification(result.clarification);
      setAnswer(result.answer);
      setLocation(result.location);
      setRoute(result.route);
      setStatus("idle");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Не удалось получить ответ.");
      setStatus("error");
    }
  }

  function ask(text: string) {
    setQuestion(text);
    void handleAsk(text);
  }

  function answerClarification(value: string) {
    if (!clarification || !askedQuestion) return;
    const nextFacts = remember({ field: clarification.field, value });
    setClarifiedWith(value);
    void handleAsk(askedQuestion, nextFacts, true);
  }

  function reset() {
    setRoute(null);
    setClarification(null);
    setClarifiedWith(null);
    setAnswer(null);
    setLocation(null);
    setAskedQuestion(null);
    setQuestion("");
    setStatus("idle");
    setErrorMessage(null);
  }

  const sources = answer ? extractSources(answer) : [];
  const answerText = answer ? stripSourceTags(answer) : "";

  return (
    <>
      <section className="hero">
        <div className="hero-left">
          <span className="pill">
            <TentIcon size={14} />
            УУНиТ База знаний
          </span>

          <h1 className="hero-title">
            Задайте вопрос —<br />
            <span className="accent">получите ответ</span>
          </h1>

          <p className="hero-text">
            База знаний УУНиТ собрала всю важную информацию об университете, учебе и студенческой жизни в
            одном месте.
          </p>

          <form
            className="search"
            onSubmit={(event) => {
              event.preventDefault();
              void handleAsk(question);
            }}
          >
            <SearchIcon size={22} />
            <input
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Например: где получить справку об обучении?"
            />
            <button className="search-button" type="submit" disabled={status === "loading"} aria-label="Спросить">
              <SendIcon size={22} />
            </button>
          </form>

          <FactChips facts={facts} onForget={forget} />

          <p className="popular-label">Популярные вопросы:</p>
          <div className="chips">
            {POPULAR_QUESTIONS.map((item) => (
              <button key={item} className="chip" type="button" onClick={() => ask(item)}>
                {item}
              </button>
            ))}
          </div>
        </div>

        <div className="answer-shell">
          <div className="question-bar">
            <span className="q-icon">
              <BookmarkLockIcon size={15} />
            </span>
            <span className="q-text">{askedQuestion ?? "Ваш вопрос появится здесь"}</span>
            <span className="q-link">
              <ExternalLinkIcon size={16} />
            </span>
          </div>

          <div className="answer-card">
            <div className="answer-head">
              <SparkleIcon size={18} />
              Ответ
            </div>

            {clarifiedWith && (
              <div className="clarified">
                <span>{clarifiedWith}</span>
              </div>
            )}

            {clarification && status === "idle" && (
              <ClarificationPrompt clarification={clarification} onSubmit={answerClarification} />
            )}

            {status === "loading" && (
              <div className="skeleton">
                <span style={{ width: "92%" }} />
                <span style={{ width: "80%" }} />
                <span style={{ width: "86%" }} />
                <span style={{ width: "60%" }} />
              </div>
            )}

            {status === "error" && <p className="answer-text error-text">{errorMessage}</p>}

            {status === "idle" && !answer && !clarification && (
              <p className="answer-text answer-muted">
                Задайте вопрос или выберите популярный — ответ из базы знаний появится здесь вместе с
                источниками.
              </p>
            )}

            {answer && status === "idle" && (
              <Typewriter key={answer} className="answer-text" text={answerText} onDone={() => setTyped(true)} />
            )}

            <SourcesList sources={sources} emptyText="Появятся вместе с ответом" />

            <button className="new-question" type="button" onClick={reset}>
              <RefreshIcon size={16} />
              Задать новый вопрос
            </button>
          </div>
        </div>
      </section>

      <div className="divider" />

      <h2 className="section-title">Быстрый доступ</h2>
      <div className="quick-grid">
        {QUICK_ACCESS.map((item) => (
          <QuickAccessCard
            key={item.title}
            icon={item.icon}
            title={item.title}
            description={item.description}
            onClick={() => ask(item.question)}
          />
        ))}
      </div>

      <section className="trust">
        <div className="trust-main">
          <span className="trust-badge">
            <ShieldCheckIcon size={30} />
          </span>
          <span>
            Ответы формируются по данным университета
            <br />и сопровождаются источниками.
          </span>
        </div>
        <div className="trust-items">
          {TRUST_ITEMS.map(({ Icon, title, sub }) => (
            <div key={title} className="trust-item">
              <span className="trust-item-icon">
                <Icon size={20} />
              </span>
              <span>
                {title}
                <br />
                <span className="sub">{sub}</span>
              </span>
            </div>
          ))}
        </div>
      </section>

      {(location || route) && answer && (
        <VenueMap
          key={answer}
          location={location}
          route={route}
          ready={typed}
          onDismiss={() => {
            setLocation(null);
            setRoute(null);
          }}
        />
      )}
    </>
  );
}
