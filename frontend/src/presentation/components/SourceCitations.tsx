import { Popover, Typography } from "antd";
import { SearchResult } from "../../domain/models";

function snippet(text: string, max = 280): string {
  const clean = text.replace(/\s+/g, " ").trim();
  if (clean.length <= max) return clean;
  return `${clean.slice(0, max - 1)}…`;
}

function CitationCard({ source, index }: { source: SearchResult; index: number }) {
  return (
    <div className="citation-card">
      <div className="citation-card__head">
        <span className="citation-card__badge">{index}</span>
        <div className="citation-card__meta">
          <Typography.Text strong className="citation-card__title">
            {source.title}
          </Typography.Text>
          <Typography.Text type="secondary" className="citation-card__id">
            {source.id}
            {typeof source.rerank_score === "number"
              ? ` · rerank ${source.rerank_score.toFixed(2)}`
              : typeof source.score === "number"
                ? ` · score ${source.score.toFixed(2)}`
                : ""}
          </Typography.Text>
        </div>
      </div>
      <Typography.Paragraph className="citation-card__text">
        {snippet(source.text)}
      </Typography.Paragraph>
    </div>
  );
}

export default function SourceCitations({ sources }: { sources: SearchResult[] }) {
  if (!sources.length) return null;

  return (
    <div className="citation-row" aria-label="Fontes recuperadas">
      <span className="citation-row__label">Fontes</span>
      {sources.map((source, index) => {
        const n = index + 1;
        return (
          <Popover
            key={`${source.id}-${n}`}
            trigger="hover"
            placement="topLeft"
            mouseEnterDelay={0.15}
            content={<CitationCard source={source} index={n} />}
            overlayClassName="citation-popover"
          >
            <button type="button" className="citation-chip" aria-label={`Fonte ${n}: ${source.title}`}>
              {n}
            </button>
          </Popover>
        );
      })}
    </div>
  );
}
