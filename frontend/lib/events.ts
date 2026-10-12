import { apiUrl } from "@/lib/api";

export type CampusEvent = {
  slug: string;
  title: string;
  /** ISO с часовым поясом */
  starts_at: string;
  url: string;
  image: string | null;
  topic: string;
  format: string;
  online: boolean;
};

export type Facet = { name: string; count: number };

export type EventsPage = {
  events: CampusEvent[];
  topics: Facet[];
  formats: Facet[];
};

export type EventsFilter = {
  dateFrom?: string | null;
  dateTo?: string | null;
  topics: string[];
  formats: string[];
  onlineOnly: boolean;
  text: string;
  newestFirst: boolean;
};

/** Каталог мероприятий: GET /events с фильтрами по датам, тематике, формату и поиском. */
export async function fetchEvents(filter: EventsFilter, signal?: AbortSignal): Promise<EventsPage> {
  const params = new URLSearchParams();
  if (filter.dateFrom) params.set("date_from", filter.dateFrom);
  if (filter.dateTo) params.set("date_to", filter.dateTo);
  filter.topics.forEach((topic) => params.append("topic", topic));
  filter.formats.forEach((format) => params.append("format", format));
  if (filter.onlineOnly) params.set("online", "true");
  if (filter.text.trim()) params.set("q", filter.text.trim());
  params.set("order", filter.newestFirst ? "desc" : "asc");
  params.set("limit", "120");

  const response = await fetch(apiUrl(`/events?${params}`), { signal });
  if (!response.ok) throw new Error(`Сервер ответил ${response.status}`);
  return response.json();
}

/** Дата в формате YYYY-MM-DD по местному времени - для полей <input type="date"> и API. */
export function isoDay(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function icsStamp(date: Date): string {
  return date.toISOString().replace(/[-:]/g, "").replace(/\.\d{3}/, "");
}

function icsEscape(text: string): string {
  return text.replace(/[\\;,]/g, (c) => `\\${c}`).replace(/\n/g, "\\n");
}

/** Файл .ics «Добавить в календарь» - открывается в Google/Apple/Яндекс календарях и Outlook. */
export function downloadIcs(event: CampusEvent) {
  const start = new Date(event.starts_at);
  const end = new Date(start.getTime() + 90 * 60 * 1000); // на сайте нет длительности - полтора часа
  const ics = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//UUST//Events catalog//RU",
    "BEGIN:VEVENT",
    `UID:${event.slug}@uust-events`,
    `DTSTAMP:${icsStamp(new Date())}`,
    `DTSTART:${icsStamp(start)}`,
    `DTEND:${icsStamp(end)}`,
    `SUMMARY:${icsEscape(event.title)}`,
    `DESCRIPTION:${icsEscape(`${event.topic} · ${event.format}\n${event.url}`)}`,
    `URL:${event.url}`,
    "END:VEVENT",
    "END:VCALENDAR",
  ].join("\r\n");
  const link = document.createElement("a");
  link.href = URL.createObjectURL(new Blob([ics], { type: "text/calendar;charset=utf-8" }));
  link.download = `${event.slug.slice(0, 60)}.ics`;
  link.click();
  URL.revokeObjectURL(link.href);
}
