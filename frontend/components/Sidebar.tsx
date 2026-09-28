const NAV_ITEMS = [
  { label: "Главная", icon: "🏠", active: true },
  { label: "Задать вопрос", icon: "🔍", active: false },
  { label: "Разделы", icon: "▦", active: false },
  { label: "Избранное", icon: "★", active: false },
  { label: "Уведомления", icon: "🔔", active: false, badge: 2 },
];

export function Sidebar() {
  return (
    <aside
      style={{
        width: 280,
        flexShrink: 0,
        background: "var(--panel)",
        borderRight: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        padding: "32px 20px",
        gap: 32,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 12, padding: "0 8px" }}>
        <div
          style={{
            width: 40,
            height: 40,
            borderRadius: 12,
            background: "var(--accent)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 20,
          }}
        >
          🎓
        </div>
        <div>
          <p style={{ margin: 0, fontFamily: "'Space Grotesk', sans-serif", fontWeight: 700, fontSize: 18 }}>
            УУНиТ
          </p>
          <p style={{ margin: 0, fontSize: 13, color: "var(--muted)" }}>База знаний студентов</p>
        </div>
      </div>

      <nav style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {NAV_ITEMS.map((item) => (
          <div
            key={item.label}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "12px 16px",
              borderRadius: 12,
              background: item.active ? "var(--accent-soft)" : "transparent",
              color: item.active ? "#ffffff" : "var(--muted)",
              fontWeight: item.active ? 600 : 500,
              fontSize: 15,
              cursor: "pointer",
            }}
          >
            <span style={{ display: "flex", alignItems: "center", gap: 12 }}>
              <span aria-hidden>{item.icon}</span>
              {item.label}
            </span>
            {item.badge ? (
              <span
                style={{
                  background: "var(--accent)",
                  color: "#fff",
                  fontSize: 12,
                  fontWeight: 700,
                  borderRadius: 999,
                  padding: "2px 8px",
                }}
              >
                {item.badge}
              </span>
            ) : null}
          </div>
        ))}
      </nav>

      <div style={{ flex: 1 }} />

      <div
        style={{
          background: "var(--panel-2)",
          border: "1px solid var(--border)",
          borderRadius: 16,
          padding: 20,
          display: "flex",
          flexDirection: "column",
          gap: 8,
        }}
      >
        <p style={{ margin: 0, fontWeight: 600, fontSize: 15 }}>Не нашли нужную информацию?</p>
        <p style={{ margin: 0, fontSize: 13, color: "var(--muted)", lineHeight: 1.5 }}>
          Напишите нам — мы добавим её в базу знаний.
        </p>
      </div>
    </aside>
  );
}
