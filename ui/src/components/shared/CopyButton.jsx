export default function CopyButton({ text, label = 'Копировать' }) {
  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      className="nn-btn-ghost text-xs px-2 py-1"
    >
      {label}
    </button>
  );
}
