import { ExternalLinkIcon, FileBadgeIcon, SourcesIcon } from "@/components/Icons";

function isUrl(value: string) {
  return /^https?:\/\//i.test(value);
}

type SourcesListProps = {
  sources: string[];
  emptyText?: string;
};

export function SourcesList({ sources, emptyText }: SourcesListProps) {
  if (sources.length === 0 && !emptyText) return null;

  return (
    <div className="sources">
      <div className="sources-head">
        <SourcesIcon size={17} />
        Источники
      </div>
      {sources.length > 0 ? (
        sources.map((source) => (
          <div key={source} className="source-row">
            <span className="source-icon">
              <FileBadgeIcon size={12} />
            </span>
            {isUrl(source) ? (
              <a href={source} target="_blank" rel="noreferrer">
                {source}
              </a>
            ) : (
              <span className="source-name">{source}</span>
            )}
            <span className="ext">
              <ExternalLinkIcon size={13} />
            </span>
          </div>
        ))
      ) : (
        <div className="source-row answer-muted">{emptyText}</div>
      )}
    </div>
  );
}
