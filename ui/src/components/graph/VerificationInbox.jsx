export default function VerificationInbox({ candidates }) {
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium">Инбокс верификации</h3>
      {candidates.map((c) => (
        <div key={c.id} className="p-2 border border-slate-700 rounded text-xs">
          <p>{c.name} ({c.type})</p>
          <p className="text-slate-400">confidence: {c.confidence}</p>
          <div className="flex gap-2 mt-2">
            <button type="button" className="px-2 py-1 rounded bg-emerald-800">Подтвердить</button>
            <button type="button" className="px-2 py-1 rounded bg-red-900">Отклонить</button>
            <button type="button" className="px-2 py-1 rounded bg-slate-700">Править</button>
          </div>
        </div>
      ))}
    </div>
  );
}
