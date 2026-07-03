export default function CoverageMatrix({ coverage }) {
  if (!coverage) return null;

  return (
    <div className="overflow-auto">
      <table className="text-xs border-collapse">
        <thead>
          <tr>
            <th className="border border-slate-700 p-1" />
            {coverage.processes.map((p) => (
              <th key={p} className="border border-slate-700 p-1">
                {p}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {coverage.materials.map((m, i) => (
            <tr key={m}>
              <td className="border border-slate-700 p-1 font-medium">{m}</td>
              {coverage.matrix[i].map((val, j) => (
                <td
                  key={j}
                  title={`${val} экспериментов`}
                  className={`border border-slate-700 p-1 text-center ${
                    val > 5 ? 'bg-emerald-900' : val > 0 ? 'bg-amber-900' : 'bg-red-950'
                  }`}
                >
                  {val}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
