export default function SourceCitation({ source }) {
  return (
    <div className="rounded-lg border border-nn-border bg-nn-gray-light p-2 text-xs dark:border-slate-600 dark:bg-slate-800">
      <p className="font-medium text-gray-900 dark:text-slate-100">{source.title}</p>
      <p className="text-nn-gray dark:text-slate-400">
        {source.author} · {source.date} · {source.confidence_level}
      </p>
    </div>
  );
}
