export default function AuditLogTable({ events }) {
  return (
    <table className="w-full text-xs border-collapse">
      <thead>
        <tr>
          <th className="border border-slate-700 px-2 py-1 text-left">Время</th>
          <th className="border border-slate-700 px-2 py-1 text-left">Пользователь</th>
          <th className="border border-slate-700 px-2 py-1 text-left">Действие</th>
          <th className="border border-slate-700 px-2 py-1 text-left">Объект</th>
        </tr>
      </thead>
      <tbody>
        {events.map((e) => (
          <tr key={e.id}>
            <td className="border border-slate-700 px-2 py-1">{e.timestamp}</td>
            <td className="border border-slate-700 px-2 py-1">{e.user}</td>
            <td className="border border-slate-700 px-2 py-1">{e.action}</td>
            <td className="border border-slate-700 px-2 py-1">{e.object}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
