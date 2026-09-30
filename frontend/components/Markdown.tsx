import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

// ссылки из ответа (документы, новости) - в новой вкладке, чтобы не терять чат
const components: Components = {
  a: ({ node: _node, ...props }) => <a {...props} target="_blank" rel="noreferrer" />,
};

/** Ответ ИИ в Markdown: абзацы, списки, **жирный**, таблицы и ссылки (remark-gfm). Сырой HTML не рендерится. */
export function Markdown({ text }: { text: string }) {
  return (
    <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
      {text}
    </ReactMarkdown>
  );
}
