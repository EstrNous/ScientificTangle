export default function IngestionDashboard({ tasks }) {
  return (
    <div className="space-y-2">
      <h3 className="text-sm font-medium">Очередь загрузок</h3>
      <table className="w-full text-xs border-collapse">
        <thead>
          <tr>
            <th className="border border-slate-700 px-2 py-1 text-left">Файл</th>
            <th className="border border-slate-700 px-2 py-1 text-left">Статус</th>
            <th className="border border-slate-700 px-2 py-1 text-left">Spans</th>
            <th className="border border-slate-700 px-2 py-1 text-left">Claims</th>
          </tr>
        </thead>
        <tbody>
          {tasks.map((t) => (
            <tr key={t.task_id}>
              <td className="border border-slate-700 px-2 py-1">{t.filename}</td>
              <td className="border border-slate-700 px-2 py-1">{t.status}</td>
              <td className="border border-slate-700 px-2 py-1">{t.source_spans_count}</td>
              <td className="border border-slate-700 px-2 py-1">{t.claims_count}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
