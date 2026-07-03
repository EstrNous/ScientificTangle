export default function SynonymTransparency({ synonyms }) {
  return (
    <p className="text-xs text-nn-gray">
      Поиск также велся по: {synonyms.join(', ')}
    </p>
  );
}
