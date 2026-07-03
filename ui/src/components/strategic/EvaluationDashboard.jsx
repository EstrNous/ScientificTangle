export default function EvaluationDashboard({ data }) {
  if (!data?.questions) return null;

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-medium">Evaluation</h3>
      {data.questions.map((q) => (
        <div key={q.id} className="p-3 rounded border border-slate-800 text-xs space-y-1">
          <p className="font-medium">{q.text}</p>
          <p>Источники: {q.actual_sources}/{q.expected_sources}</p>
          <p>Missing evidence: {q.missing_evidence}</p>
          <p>Latency: {q.latency_ms} ms</p>
        </div>
      ))}
    </div>
  );
}
