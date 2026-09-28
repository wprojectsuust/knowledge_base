"use client";

import { useState } from "react";
import { SendIcon, SparkleIcon } from "@/components/Icons";
import { Typewriter } from "@/components/Typewriter";
import type { Clarification } from "@/lib/api";

type ClarificationPromptProps = {
  clarification: Clarification;
  onSubmit: (value: string) => void;
};

/**
 * ИИ просит уточнить сведения о студенте: вопрос печатается, затем выезжает поле ответа.
 * После отправки исходный вопрос уходит заново уже с этим сведением.
 */
export function ClarificationPrompt({ clarification, onSubmit }: ClarificationPromptProps) {
  const [showInput, setShowInput] = useState(false);
  const [value, setValue] = useState("");

  return (
    <div className="clarify">
      <div className="clarify-head">
        <SparkleIcon size={16} />
        Нужно уточнение
      </div>
      <Typewriter
        className="clarify-question"
        text={clarification.question}
        durationMs={700}
        onDone={() => setShowInput(true)}
      />
      {showInput && (
        <form
          className="clarify-form"
          onSubmit={(event) => {
            event.preventDefault();
            const trimmed = value.trim();
            if (trimmed) onSubmit(trimmed);
          }}
        >
          <input autoFocus value={value} onChange={(event) => setValue(event.target.value)} placeholder="Ваш ответ…" />
          <button type="submit" aria-label="Ответить" disabled={!value.trim()}>
            <SendIcon size={18} />
          </button>
        </form>
      )}
      <p className="clarify-note">Запомню и больше не буду спрашивать.</p>
    </div>
  );
}
