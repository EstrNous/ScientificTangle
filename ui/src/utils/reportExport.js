function escapeHtml(value) {
  return String(value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function buildReportPayload(sessionId, sessionTitle, messages) {
  return {
    sessionId,
    sessionTitle: sessionTitle || `Сессия ${sessionId}`,
    exportedAt: new Date().toISOString(),
    messages: messages.map((m) => ({
      role: m.role,
      content: m.content || '',
      attachments: m.attachments ?? [],
    })),
  };
}

function buildReportHtml(payload) {
  const messageBlocks = payload.messages
    .map((m) => {
      const roleLabel = m.role === 'user' ? 'Вопрос' : 'Ответ';
      const attachments =
        m.attachments.length > 0
          ? `<p style="margin:8px 0 0;font-size:12px;color:#0057B8;">Файлы: ${m.attachments.map(escapeHtml).join(', ')}</p>`
          : '';
      return `
        <section style="margin-bottom:20px;padding-bottom:16px;border-bottom:1px solid #E5E7EB;">
          <p style="margin:0 0 8px;font-size:12px;font-weight:600;color:#0057B8;text-transform:uppercase;">${roleLabel}</p>
          <p style="margin:0;font-size:14px;line-height:1.5;color:#111827;white-space:pre-wrap;">${escapeHtml(m.content)}</p>
          ${attachments}
        </section>
      `;
    })
    .join('');

  return `
    <div style="font-family:'Segoe UI',sans-serif;padding:32px;color:#111827;">
      <p style="margin:0 0 4px;font-size:12px;color:#6B7280;">НорСинтез</p>
      <h1 style="margin:0 0 8px;font-size:22px;color:#0057B8;">${escapeHtml(payload.sessionTitle)}</h1>
      <p style="margin:0 0 24px;font-size:12px;color:#6B7280;">Экспорт: ${escapeHtml(new Date(payload.exportedAt).toLocaleString('ru-RU'))}</p>
      ${messageBlocks || '<p style="color:#6B7280;">Нет сообщений в сессии</p>'}
    </div>
  `;
}

export function downloadMarkdownReport(payload) {
  const lines = [
    `# ${payload.sessionTitle}`,
    '',
    `Сессия: ${payload.sessionId}`,
    `Экспорт: ${payload.exportedAt}`,
    '',
    ...payload.messages.flatMap((m) => {
      const role = m.role === 'user' ? '## Вопрос' : '## Ответ';
      const files =
        m.attachments.length > 0 ? `\n\n_Файлы: ${m.attachments.join(', ')}_` : '';
      return [role, '', m.content, files, ''];
    }),
  ];
  triggerDownload(
    new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' }),
    `report_${payload.sessionId}.md`
  );
}

export function downloadJsonReport(payload) {
  triggerDownload(
    new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json;charset=utf-8' }),
    `report_${payload.sessionId}.json`
  );
}

export async function downloadPdfReport(payload) {
  const { default: html2pdf } = await import('html2pdf.js');
  const wrapper = document.createElement('div');
  wrapper.innerHTML = buildReportHtml(payload);
  document.body.appendChild(wrapper);

  try {
    await html2pdf()
      .set({
        margin: 12,
        filename: `report_${payload.sessionId}.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2, useCORS: true },
        jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
      })
      .from(wrapper)
      .save();
  } finally {
    document.body.removeChild(wrapper);
  }
}

function triggerDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
