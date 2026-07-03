export default function WarningsPanel({ confidence }) {
  if (confidence >= 0.8) return null;
  return (
    <p className="text-xs text-amber-600">
      Уверенность ответа: {(confidence * 100).toFixed(0)}% — проверьте источники
    </p>
  );
}
