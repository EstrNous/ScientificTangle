import IngestionDashboard from '../graph/IngestionDashboard.jsx';

export default function DocumentCatalogTable({ items }) {
  const tasks = items.map((item) => ({
    task_id: item.ingestionTaskId ?? item.documentId,
    filename: item.sourcePath ?? item.title,
    status: item.status,
    source_spans_count: item.sourceSpansCount,
    claims_count: item.indexedPointsCount,
  }));

  return (
    <div className="space-y-3">
      <IngestionDashboard tasks={tasks} />
      <div className="overflow-x-auto">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr>
              <th className="border border-slate-700 px-2 py-1 text-left">Документ</th>
              <th className="border border-slate-700 px-2 py-1 text-left">Статус</th>
              <th className="border border-slate-700 px-2 py-1 text-left">Spans</th>
              <th className="border border-slate-700 px-2 py-1 text-left">Points</th>
              <th className="border border-slate-700 px-2 py-1 text-left">Ошибка</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.documentId}>
                <td className="border border-slate-700 px-2 py-1">{item.title}</td>
                <td className="border border-slate-700 px-2 py-1">{item.status}</td>
                <td className="border border-slate-700 px-2 py-1">{item.sourceSpansCount}</td>
                <td className="border border-slate-700 px-2 py-1">{item.indexedPointsCount}</td>
                <td className="border border-slate-700 px-2 py-1">{item.errorMessage ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
