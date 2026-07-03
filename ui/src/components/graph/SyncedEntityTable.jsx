export default function SyncedEntityTable({ entities, onChange }) {
  return (
    <table className="w-full text-xs border-collapse">
      <thead>
        <tr>
          <th className="border border-slate-700 px-2 py-1 text-left">Имя</th>
          <th className="border border-slate-700 px-2 py-1 text-left">Тип</th>
          <th className="border border-slate-700 px-2 py-1 text-left">Статус</th>
        </tr>
      </thead>
      <tbody>
        {entities.map((e) => (
          <tr key={e.id}>
            <td className="border border-slate-700 px-2 py-1">
              <input
                className="bg-transparent w-full"
                value={e.name}
                onChange={(ev) => onChange?.(e.id, { name: ev.target.value })}
              />
            </td>
            <td className="border border-slate-700 px-2 py-1">{e.type}</td>
            <td className="border border-slate-700 px-2 py-1">{e.status}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
