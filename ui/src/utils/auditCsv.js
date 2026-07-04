function escapeCsvCell(value) {
  const text = String(value ?? '');
  if (/[",\n\r]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

export function buildAuditCsv(events) {
  const header = ['id', 'timestamp', 'user', 'role', 'action', 'object', 'resource_type', 'resource_id'];
  const rows = (events ?? []).map((event) =>
    [
      event.id,
      event.timestamp,
      event.user,
      event.role,
      event.action,
      event.object,
      event.resource_type ?? '',
      event.resource_id ?? '',
    ]
      .map(escapeCsvCell)
      .join(','),
  );
  return [header.join(','), ...rows].join('\n');
}

export function downloadAuditCsv(events, filename = 'audit_events.csv') {
  const csv = buildAuditCsv(events);
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
