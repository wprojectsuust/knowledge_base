import type { Fact } from "@/lib/api";
import { factLabel } from "@/lib/useStudentFacts";

type FactChipsProps = {
  facts: Fact[];
  onForget: (field: string) => void;
};

/** Что ИИ уже знает о студенте - с возможностью забыть. */
export function FactChips({ facts, onForget }: FactChipsProps) {
  if (facts.length === 0) return null;

  return (
    <div className="fact-chips">
      <span className="fact-chips-label">ИИ помнит:</span>
      {facts.map((fact) => (
        <span key={fact.field} className="fact-chip">
          {factLabel(fact.field)}: <b>{fact.value}</b>
          <button type="button" aria-label={`Забыть: ${factLabel(fact.field)}`} onClick={() => onForget(fact.field)}>
            ×
          </button>
        </span>
      ))}
    </div>
  );
}
