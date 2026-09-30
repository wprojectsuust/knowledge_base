"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ArrowRightIcon, HomeIcon, LogoMark, MapPinIcon, SearchIcon, SendIcon } from "@/components/Icons";

const NAV_ITEMS = [
  { label: "Главная", short: "Главная", href: "/", Icon: HomeIcon },
  { label: "Задать вопрос", short: "Спросить", href: "/ask", Icon: SearchIcon },
  { label: "Карта кампуса", short: "Карта", href: "/map", Icon: MapPinIcon },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar">
      <Link href="/" className="brand">
        <LogoMark size={38} />
        <div>
          <p className="brand-title">УУНиТ</p>
          <p className="brand-subtitle">База знаний студентов</p>
        </div>
      </Link>

      <nav className="nav">
        {NAV_ITEMS.map(({ label, href, Icon }) => (
          <Link key={href} href={href} className={`nav-item${pathname === href ? " active" : ""}`}>
            <Icon size={22} />
            {label}
          </Link>
        ))}
      </nav>

      <a className="help-card" href="https://t.me/karrrad" target="_blank" rel="noreferrer">
        <p className="help-card-title">Не нашли нужную информацию?</p>
        <p className="help-card-text">Напишите нам в Telegram — мы добавим её в базу знаний</p>
        <p className="help-card-handle">@karrrad</p>
        <span className="help-card-icon">
          <SendIcon size={20} />
        </span>
        <span className="help-card-arrow">
          <ArrowRightIcon size={16} />
        </span>
      </a>
    </aside>
  );
}

/** На телефоне сайдбара нет - та же навигация нижней панелью вкладок. */
export function MobileNav() {
  const pathname = usePathname();

  return (
    <nav className="mobile-nav" aria-label="Разделы">
      {NAV_ITEMS.map(({ short, href, Icon }) => (
        <Link key={href} href={href} className={`mobile-nav-item${pathname === href ? " active" : ""}`}>
          <Icon size={22} />
          <span>{short}</span>
        </Link>
      ))}
    </nav>
  );
}
