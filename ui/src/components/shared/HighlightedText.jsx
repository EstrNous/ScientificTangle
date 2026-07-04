function HighlightMark({ children }) {
  return (
    <mark className="rounded bg-amber-200/80 px-0.5 text-gray-900 dark:bg-amber-500/30 dark:text-amber-100">
      {children}
    </mark>
  );
}

export default function HighlightedText({ text, highlight, highlightStart, highlightEnd }) {
  if (!text) {
    return null;
  }

  if (highlightStart != null && highlightEnd != null && highlightEnd > highlightStart) {
    const start = Math.max(0, Math.min(highlightStart, text.length));
    const end = Math.max(start, Math.min(highlightEnd, text.length));
    return (
      <span>
        {text.slice(0, start)}
        <HighlightMark>{text.slice(start, end)}</HighlightMark>
        {text.slice(end)}
      </span>
    );
  }

  if (!highlight || !text.includes(highlight)) {
    return <span>{text}</span>;
  }

  const [before, after] = text.split(highlight);
  return (
    <span>
      {before}
      <HighlightMark>{highlight}</HighlightMark>
      {after}
    </span>
  );
}
