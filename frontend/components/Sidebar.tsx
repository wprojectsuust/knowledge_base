import { ArrowRightIcon, BellIcon, GridIcon, HomeIcon, LogoMark, SearchIcon, SendIcon, StarIcon } from "@/components/Icons";

const NAV_ITEMS = [
  { label: "Главная", Icon: HomeIcon, active: true },
  { label: "Задать вопрос", Icon: SearchIcon },
  { label: "Разделы", Icon: GridIcon },
  { label: "Избранное", Icon: StarIcon },
  { label: "Уведомления", Icon: BellIcon, badge: 2 },
];

export function Sidebar() {
  return (
    <aside className="sidebar">
      <div className="brand">
        <LogoMark size={38} />
        <div>
          <p className="brand-title">УУНиТ</p>
          <p className="brand-subtitle">База знаний студентов</p>
        </div>
      </div>

      <nav className="nav">
        {NAV_ITEMS.map(({ label, Icon, active, badge }) => (
          <div key={label} className={`nav-item${active ? " active" : ""}`}>
            <Icon size={22} />
            {label}
            {badge ? <span className="nav-badge">{badge}</span> : null}
          </div>
        ))}
      </nav>

      <div className="help-card">
        <p className="help-card-title">Не нашли нужную информацию?</p>
        <p className="help-card-text">Напишите нам — мы добавим её в базу знаний</p>
        <span className="help-card-icon">
          <SendIcon size={20} />
        </span>
        <span className="help-card-arrow">
          <ArrowRightIcon size={16} />
        </span>
      </div>
    </aside>
  );
}
