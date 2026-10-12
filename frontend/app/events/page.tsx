"use client";

import { useEffect, useMemo, useState } from "react";
import { CalendarIcon, ExternalLinkIcon, RefreshIcon, SearchIcon } from "@/components/Icons";
import { downloadIcs, fetchEvents, isoDay, type CampusEvent, type EventsPage, type Facet } from "@/lib/events";

type Period = "upcoming" | "week" | "month" | "past" | "custom";

const PERIODS: { id: Period; label: string }[] = [
  { id: "upcoming", label: "Предстоящие" },
  { id: "week", label: "Эта неделя" },
  { id: "month", label: "30 дней" },
  { id: "past", label: "Прошедшие" },
  { id: "custom", label: "Свои даты" },
];

const MONTH = new Intl.DateTimeFormat("ru-RU", { month: "long", year: "numeric" });
const DAY = new Intl.DateTimeFormat("ru-RU", { day: "numeric" });
const SHORT_MONTH = new Intl.DateTimeFormat("ru-RU", { month: "short" });
const WEEKDAY_TIME = new Intl.DateTimeFormat("ru-RU", { weekday: "short", hour: "2-digit", minute: "2-digit" });

function addDays(date: Date, days: number) {
  const copy = new Date(date);
  copy.setDate(copy.getDate() + days);
  return copy;
}

/** Период -> даты для API. Предстоящие - от сегодня по возрастанию, прошедшие - до вчера от свежих. */
function periodRange(period: Period, customFrom: string, customTo: string) {
  const today = new Date();
  switch (period) {
    case "upcoming":
      return { dateFrom: isoDay(today), dateTo: null, newestFirst: false };
    case "week":
      return { dateFrom: isoDay(today), dateTo: isoDay(addDays(today, 6)), newestFirst: false };
    case "month":
      return { dateFrom: isoDay(today), dateTo: isoDay(addDays(today, 30)), newestFirst: false };
    case "past":
      return { dateFrom: null, dateTo: isoDay(addDays(today, -1)), newestFirst: true };
    case "custom":
      return { dateFrom: customFrom || null, dateTo: customTo || null, newestFirst: false };
  }
}

function toggle(list: string[], value: string) {
  return list.includes(value) ? list.filter((item) => item !== value) : [...list, value];
}

function groupByMonth(events: CampusEvent[]) {
  const groups: { month: string; events: CampusEvent[] }[] = [];
  for (const event of events) {
    const month = MONTH.format(new Date(event.starts_at));
    const last = groups[groups.length - 1];
    if (last && last.month === month) last.events.push(event);
    else groups.push({ month, events: [event] });
  }
  return groups;
}

function FacetChips({ facets, selected, onToggle }: { facets: Facet[]; selected: string[]; onToggle: (name: string) => void }) {
  return (
    <div className="events-chips">
      {facets
        .filter((facet) => facet.count > 0 || selected.includes(facet.name))
        .map((facet) => (
          <button
            key={facet.name}
            type="button"
            className={`chip${selected.includes(facet.name) ? " active" : ""}`}
            onClick={() => onToggle(facet.name)}
          >
            {facet.name}
            <span className="events-chip-count">{facet.count}</span>
          </button>
        ))}
    </div>
  );
}

function EventCard({ event }: { event: CampusEvent }) {
  const start = new Date(event.starts_at);
  const past = start.getTime() < Date.now() - 3 * 60 * 60 * 1000;
  return (
    <article className={`event-card${past ? " past" : ""}`}>
      <div className="event-cover">
        {event.image ? <img src={event.image} alt="" loading="lazy" /> : <div className="event-cover-fallback" />}
        <div className="event-date">
          <span className="event-date-day">{DAY.format(start)}</span>
          <span className="event-date-month">{SHORT_MONTH.format(start).replace(".", "")}</span>
        </div>
      </div>
      <div className="event-body">
        <p className="event-when">{WEEKDAY_TIME.format(start)}</p>
        <h3 className="event-title">{event.title}</h3>
        <div className="event-tags">
          <span className="event-tag topic">{event.topic}</span>
          <span className="event-tag">{event.format}</span>
          {event.online && <span className="event-tag online">онлайн</span>}
        </div>
        <div className="event-actions">
          <a className="event-action primary" href={event.url} target="_blank" rel="noreferrer">
            Подробнее
            <ExternalLinkIcon size={14} />
          </a>
          {!past && (
            <button type="button" className="event-action" onClick={() => downloadIcs(event)}>
              <CalendarIcon size={14} />В календарь
            </button>
          )}
        </div>
      </div>
    </article>
  );
}

export default function EventsPage() {
  const [period, setPeriod] = useState<Period>("upcoming");
  const [customFrom, setCustomFrom] = useState(isoDay(new Date()));
  const [customTo, setCustomTo] = useState(isoDay(addDays(new Date(), 30)));
  const [topics, setTopics] = useState<string[]>([]);
  const [formats, setFormats] = useState<string[]>([]);
  const [onlineOnly, setOnlineOnly] = useState(false);
  const [text, setText] = useState("");
  const [debouncedText, setDebouncedText] = useState("");
  const [page, setPage] = useState<EventsPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const timer = setTimeout(() => setDebouncedText(text), 300);
    return () => clearTimeout(timer);
  }, [text]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    fetchEvents(
      { ...periodRange(period, customFrom, customTo), topics, formats, onlineOnly, text: debouncedText },
      controller.signal,
    )
      .then(setPage)
      .catch((reason) => {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : "Не удалось загрузить");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [period, customFrom, customTo, topics, formats, onlineOnly, debouncedText]);

  const groups = useMemo(() => groupByMonth(page?.events ?? []), [page]);
  const filtered = topics.length > 0 || formats.length > 0 || onlineOnly || debouncedText.trim() !== "";

  function reset() {
    setTopics([]);
    setFormats([]);
    setOnlineOnly(false);
    setText("");
  }

  return (
    <section className="events-page">
      <header className="events-head">
        <span className="pill">
          <CalendarIcon size={14} />
          Афиша УУНиТ
        </span>
        <h1 className="hero-title events-title">
          Мероприятия <span className="accent">университета</span>
        </h1>
        <p className="events-subtitle">
          Все события uust.ru в одном каталоге: фильтруйте по дате, тематике и формату и добавляйте в свой календарь.
        </p>
      </header>

      <div className="events-filters">
        <label className="search events-search">
          <SearchIcon size={18} />
          <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Поиск по названию: хакатон, стипендия, концерт…" />
        </label>

        <div className="events-row">
          <span className="events-label">Когда</span>
          <div className="events-chips">
            {PERIODS.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`chip${period === item.id ? " active" : ""}`}
                onClick={() => setPeriod(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
          {period === "custom" && (
            <div className="events-dates">
              <input type="date" value={customFrom} onChange={(e) => setCustomFrom(e.target.value)} aria-label="С" />
              <span>—</span>
              <input type="date" value={customTo} onChange={(e) => setCustomTo(e.target.value)} aria-label="По" />
            </div>
          )}
        </div>

        <div className="events-row">
          <span className="events-label">Тематика</span>
          <FacetChips facets={page?.topics ?? []} selected={topics} onToggle={(name) => setTopics(toggle(topics, name))} />
        </div>

        <div className="events-row">
          <span className="events-label">Формат</span>
          <FacetChips facets={page?.formats ?? []} selected={formats} onToggle={(name) => setFormats(toggle(formats, name))} />
          <button type="button" className={`chip${onlineOnly ? " active" : ""}`} onClick={() => setOnlineOnly(!onlineOnly)}>
            Только онлайн
          </button>
        </div>
      </div>

      <div className="events-summary">
        <span>{loading ? "Загружаю…" : `Найдено: ${page?.events.length ?? 0}`}</span>
        {filtered && (
          <button type="button" className="events-reset" onClick={reset}>
            <RefreshIcon size={14} />
            Сбросить фильтры
          </button>
        )}
      </div>

      {error && <p className="answer-text error-text">{error}</p>}

      {!loading && !error && page && page.events.length === 0 && (
        <div className="events-empty">
          <p>Под эти условия мероприятий нет.</p>
          {period !== "past" && (
            <button type="button" className="chip active" onClick={() => setPeriod("past")}>
              Посмотреть прошедшие
            </button>
          )}
          {filtered && (
            <button type="button" className="chip" onClick={reset}>
              Сбросить фильтры
            </button>
          )}
        </div>
      )}

      {groups.map((group) => (
        <div key={group.month} className="events-month">
          <h2 className="events-month-title">{group.month}</h2>
          <div className="events-grid">
            {group.events.map((event) => (
              <EventCard key={event.slug} event={event} />
            ))}
          </div>
        </div>
      ))}
    </section>
  );
}
