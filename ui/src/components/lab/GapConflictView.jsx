export default function GapConflictView({ contradictions }) {
  return (
    <ul className="space-y-2 text-sm">
      {contradictions?.map((c, i) => (
        <li key={i} className="p-2 border border-slate-800 rounded">
          <p className="font-medium">{c.process}</p>
          <p className="text-xs text-slate-400">{c.claim_a} vs {c.claim_b}</p>
        </li>
      ))}
    </ul>
  );
}
