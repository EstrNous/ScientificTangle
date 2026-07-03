export default function SourceViewer({ span }) {
  if (!span) {
    return <p className="text-sm text-slate-400">Выберите источник в таблице доказательств</p>;
  }

  return (
    <div className="text-sm border border-slate-800 rounded p-3">
      <p className="font-medium">{span.title}</p>
      <p className="text-slate-400 text-xs mt-2">Стр. {span.page} · {span.raw_text}</p>
    </div>
  );
}
