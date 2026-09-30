"use client";

import { useEffect, useState } from "react";
import { Markdown } from "@/components/Markdown";

type TypewriterProps = {
  text: string;
  className?: string;
  /** Сколько миллисекунд в сумме на весь текст, как бы длинным он ни был. */
  durationMs?: number;
  onDone?: () => void;
};

/** Печатает Markdown-текст «как ИИ»: длинный ответ не печатается дольше durationMs. */
export function Typewriter({ text, className, durationMs = 1600, onDone }: TypewriterProps) {
  const [shown, setShown] = useState(0);

  useEffect(() => {
    setShown(0);
    const stepMs = 16;
    const perStep = Math.max(1, Math.ceil(text.length / (durationMs / stepMs)));
    const timer = setInterval(() => {
      setShown((prev) => {
        const next = Math.min(text.length, prev + perStep);
        if (next === text.length) clearInterval(timer);
        return next;
      });
    }, stepMs);
    return () => clearInterval(timer);
  }, [text, durationMs]);

  useEffect(() => {
    if (shown === text.length) onDone?.();
    // onDone намеренно не в зависимостях: вызываем один раз, когда допечатали
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shown, text.length]);

  return (
    <div className={className}>
      <Markdown text={text.slice(0, shown)} />
      {shown < text.length && <span className="caret" />}
    </div>
  );
}
