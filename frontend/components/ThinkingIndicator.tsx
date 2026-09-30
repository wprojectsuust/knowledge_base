/** Пока ответ готовится: крутящееся кольцо и текущий шаг («Ищу в базе знаний», «Ищу, кто декан»).
 *  key={text} перезапускает анимацию появления при каждой смене шага. */
export function ThinkingIndicator({ text }: { text: string | null }) {
  const label = text ?? "Думаю";
  return (
    <div className="thinking" role="status" aria-live="polite">
      <span className="thinking-orb" aria-hidden="true">
        <span className="thinking-ring" />
        <span className="thinking-core" />
      </span>
      <span key={label} className="thinking-text">
        {label}
        <span className="thinking-dots" aria-hidden="true" />
      </span>
    </div>
  );
}
