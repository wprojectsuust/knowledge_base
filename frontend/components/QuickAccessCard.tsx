import type { ReactNode } from "react";
import { ArrowRightIcon } from "@/components/Icons";

type QuickAccessCardProps = {
  icon: ReactNode;
  title: string;
  description: string;
  onClick?: () => void;
};

export function QuickAccessCard({ icon, title, description, onClick }: QuickAccessCardProps) {
  return (
    <button className="quick-card" onClick={onClick}>
      <div className="quick-icon">{icon}</div>
      <p className="quick-title">{title}</p>
      <p className="quick-text">{description}</p>
      <span className="quick-arrow">
        <ArrowRightIcon size={20} />
      </span>
    </button>
  );
}
