export default function HighlightedText({ text, highlight }) {
  if (!highlight || !text?.includes(highlight)) {
    return <span>{text}</span>;
  }

  const [before, after] = text.split(highlight);
  return (
    <span>
      {before}
      <mark className="rounded bg-amber-200/80 px-0.5 text-gray-900 dark:bg-amber-500/30 dark:text-amber-100">
        {highlight}
      </mark>
      {after}
    </span>
  );
}
