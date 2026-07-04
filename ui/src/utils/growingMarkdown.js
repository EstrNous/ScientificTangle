export function splitMarkdownRevealChunks(text, chunkSize = 24) {
  if (!text) return [];
  const normalized = String(text);
  if (normalized.length <= chunkSize) return [normalized];

  const chunks = [];
  let cursor = 0;
  while (cursor < normalized.length) {
    let end = Math.min(cursor + chunkSize, normalized.length);
    if (end < normalized.length) {
      const spaceIndex = normalized.lastIndexOf(' ', end);
      if (spaceIndex > cursor + Math.floor(chunkSize / 2)) {
        end = spaceIndex + 1;
      }
    }
    chunks.push(normalized.slice(0, end));
    cursor = end;
  }
  return chunks;
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function revealMarkdownText(
  text,
  { onReveal, chunkDelayMs = 40, chunkSize = 24 } = {},
) {
  const chunks = splitMarkdownRevealChunks(text, chunkSize);
  let latest = '';
  for (const chunk of chunks) {
    latest = chunk;
    onReveal?.(latest);
    if (chunk !== chunks[chunks.length - 1]) {
      await delay(chunkDelayMs);
    }
  }
  return latest;
}
