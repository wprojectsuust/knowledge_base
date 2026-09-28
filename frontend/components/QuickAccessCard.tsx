type QuickAccessCardProps = {
  icon: string;
  title: string;
  description: string;
  onClick?: () => void;
};

export function QuickAccessCard({ icon, title, description, onClick }: QuickAccessCardProps) {
  return (
    <button
      onClick={onClick}
      style={{
        textAlign: "left",
        background: "var(--panel)",
        border: "1px solid var(--border)",
        borderRadius: 20,
        padding: 28,
        display: "flex",
        flexDirection: "column",
        gap: 16,
        cursor: onClick ? "pointer" : "default",
        color: "inherit",
      }}
    >
      <div
        style={{
          width: 48,
          height: 48,
          borderRadius: 12,
          background: "var(--accent-soft)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 22,
        }}
      >
        {icon}
      </div>
      <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
        <p style={{ margin: 0, fontWeight: 600, fontSize: 18 }}>{title}</p>
        <p style={{ margin: 0, fontSize: 14, color: "var(--muted)", lineHeight: 1.5 }}>{description}</p>
      </div>
      <span style={{ color: "var(--accent)", fontSize: 20 }}>→</span>
    </button>
  );
}
