export default function ManagerDashboard({ data }) {
  if (!data) return null;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-2 text-xs">
        {Object.entries(data.totals).map(([k, v]) => (
          <div key={k} className="p-2 rounded bg-slate-900 border border-slate-800">
            <p className="text-slate-400">{k}</p>
            <p className="text-lg font-semibold">{v}</p>
          </div>
        ))}
      </div>
      <div>
        <h3 className="text-sm font-medium mb-2">Покрытие по направлениям</h3>
        <ul className="space-y-1 text-sm">
          {data.directions.map((d) => (
            <li key={d.id} className="flex justify-between">
              <span>{d.name}</span>
              <span>{(d.coverage * 100).toFixed(0)}%</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
