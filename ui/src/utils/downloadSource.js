import { getFullDocumentPages } from '../api/sourceResolver/index.js';

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function buildHighlightedHtml(text, highlight) {
  if (!highlight || !text.includes(highlight)) {
    return escapeHtml(text);
  }

  const [before, after] = text.split(highlight);
  return `${escapeHtml(before)}<mark style="background:#FDE68A;padding:0 2px;">${escapeHtml(highlight)}</mark>${escapeHtml(after)}`;
}

function buildSourceDocumentHtml(entry) {
  const pages = getFullDocumentPages(entry);
  const pageBlocks = pages
    .map(
      ({ page, raw_text: rawText, highlight, section }) => `
        <section style="margin-bottom:24px;padding-bottom:16px;border-bottom:1px solid #E5E7EB;${
          page > 1 ? 'page-break-before:always;' : ''
        }">
          <p style="margin:0 0 8px;font-size:11px;font-weight:600;color:#0057B8;text-transform:uppercase;">
            Страница ${page}${section ? ` · ${escapeHtml(section)}` : ''}
          </p>
          <p style="margin:0;font-size:13px;line-height:1.6;color:#111827;white-space:pre-wrap;">${buildHighlightedHtml(rawText, highlight)}</p>
        </section>
      `,
    )
    .join('');

  return `
    <div style="font-family:'Segoe UI',sans-serif;padding:32px;color:#111827;">
      <p style="margin:0 0 4px;font-size:12px;color:#6B7280;">НорСинтез</p>
      <h1 style="margin:0 0 8px;font-size:20px;color:#0057B8;">${escapeHtml(entry.title)}</h1>
      <p style="margin:0 0 24px;font-size:12px;color:#6B7280;">Полный документ · ${pages.length} стр.</p>
      ${pageBlocks}
    </div>
  `;
}

export async function downloadSourceDocumentPdf(entry) {
  if (!entry) return;

  const { default: html2pdf } = await import('html2pdf.js');
  const wrapper = document.createElement('div');
  wrapper.innerHTML = buildSourceDocumentHtml(entry);
  document.body.appendChild(wrapper);

  const baseName = entry.file_name?.replace(/\.[^.]+$/, '') || entry.title || 'source';

  try {
    await html2pdf()
      .set({
        margin: 12,
        filename: `${baseName}.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
        pagebreak: { mode: ['css', 'legacy'] },
      })
      .from(wrapper)
      .save();
  } finally {
    document.body.removeChild(wrapper);
  }
}
