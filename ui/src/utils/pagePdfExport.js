function escapeHtml(value) {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

const S = {
  h2: 'margin:20px 0 10px;font-size:15px;font-weight:600;color:#0057B8;',
  p: 'margin:0 0 8px;font-size:13px;line-height:1.5;color:#374151;',
  table: 'width:100%;border-collapse:collapse;font-size:11px;margin-bottom:12px;',
  th: 'border:1px solid #E5E7EB;padding:6px 8px;text-align:left;background:#F9FAFB;font-weight:600;',
  td: 'border:1px solid #E5E7EB;padding:6px 8px;vertical-align:top;color:#111827;',
  ul: 'margin:0 0 12px;padding-left:18px;font-size:13px;line-height:1.55;color:#374151;',
};

function wrapPage(title, subtitle, body) {
  return `
    <div style="font-family:'Segoe UI',sans-serif;padding:28px;color:#111827;">
      <p style="margin:0 0 4px;font-size:11px;color:#6B7280;">Научный Клубок</p>
      <h1 style="margin:0 0 6px;font-size:20px;color:#0057B8;">${escapeHtml(title)}</h1>
      <p style="margin:0 0 20px;font-size:11px;color:#6B7280;">${escapeHtml(subtitle)}</p>
      ${body}
    </div>
  `;
}

function renderTable(headers, rows) {
  const head = headers.map((h) => `<th style="${S.th}">${escapeHtml(h)}</th>`).join('');
  const body = rows
    .map(
      (row) =>
        `<tr>${row.map((cell) => `<td style="${S.td}">${escapeHtml(cell)}</td>`).join('')}</tr>`,
    )
    .join('');
  return `<table style="${S.table}"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
}

function renderList(items) {
  if (!items?.length) return `<p style="${S.p}">—</p>`;
  return `<ul style="${S.ul}">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join('')}</ul>`;
}

export async function downloadHtmlPdf(filename, html) {
  const { default: html2pdf } = await import('html2pdf.js');
  const wrapper = document.createElement('div');
  wrapper.innerHTML = html;
  document.body.appendChild(wrapper);

  try {
    await html2pdf()
      .set({
        margin: 10,
        filename,
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

function stamp() {
  return new Date().toISOString().slice(0, 10);
}

export async function exportStrategicPdf({ manager, evaluation, t, language }) {
  const exportedAt = new Date().toLocaleString(language === 'en' ? 'en-GB' : 'ru-RU');
  const parts = [];

  if (manager?.totals) {
    const metricRows = Object.entries(manager.totals).map(([key, value]) => [
      t(`strategic.metrics.${key}`, { defaultValue: key }),
      String(value),
    ]);
    parts.push(`<h2 style="${S.h2}">${escapeHtml(t('strategic.managerTitle'))}</h2>`);
    parts.push(renderTable([t('strategic.pdfMetric'), t('strategic.pdfValue')], metricRows));
  }

  if (manager?.directions?.length) {
    parts.push(`<h2 style="${S.h2}">${escapeHtml(t('strategic.coverageTitle'))}</h2>`);
    parts.push(
      renderTable(
        [t('strategic.direction'), t('strategic.metrics.documents'), '%'],
        manager.directions.map((d) => [
          d.name,
          String(d.documents),
          `${Math.round(d.coverage * 100)}`,
        ]),
      ),
    );
  }

  parts.push(`<h2 style="${S.h2}">${escapeHtml(t('strategic.lowCoverage'))}</h2>`);
  parts.push(renderList(manager?.low_coverage_topics));

  parts.push(`<h2 style="${S.h2}">${escapeHtml(t('strategic.highConflict'))}</h2>`);
  parts.push(renderList(manager?.high_conflict_topics));

  if (evaluation?.summary) {
    parts.push(`<h2 style="${S.h2}">${escapeHtml(t('strategic.evaluationTitle'))}</h2>`);
    const evalRows = [
      [t('strategic.evalMetrics.citation_coverage'), `${Math.round(evaluation.summary.avg_citation_coverage * 100)}%`],
      [t('strategic.evalMetrics.numeric_correctness'), `${Math.round(evaluation.summary.avg_numeric_correctness * 100)}%`],
      [t('strategic.evalMetrics.latency'), `${evaluation.summary.avg_latency_ms} ms`],
      [t('strategic.evalMetrics.unsupported_rate'), `${Math.round(evaluation.summary.unsupported_claim_rate * 100)}%`],
      [t('strategic.evalMetrics.entity_f1'), `${Math.round(evaluation.summary.entity_linking_f1 * 100)}%`],
      [t('strategic.evalMetrics.recall_at_5'), `${Math.round(evaluation.summary.evidence_recall_at_5 * 100)}%`],
    ];
    parts.push(renderTable([t('strategic.pdfMetric'), t('strategic.pdfValue')], evalRows));
  }

  if (evaluation?.questions?.length) {
    parts.push(
      `<h2 style="${S.h2}">${escapeHtml(t('strategic.evaluationSubtitle', { count: evaluation.questions.length }))}</h2>`,
    );
    parts.push(
      renderTable(
        [
          'ID',
          t('strategic.sources'),
          t('strategic.missingEvidence'),
          t('strategic.unsupportedClaims'),
          t('strategic.latency'),
          t('strategic.status.pass'),
        ],
        evaluation.questions.map((q) => [
          q.id,
          `${q.actual_sources}/${q.expected_sources}`,
          String(q.missing_evidence),
          String(q.unsupported_claims),
          `${q.latency_ms} ms`,
          t(`strategic.status.${q.status}`, { defaultValue: q.status }),
        ]),
      ),
    );
  }

  const html = wrapPage(t('nav.strategic'), t('common.exportedAt', { date: exportedAt }), parts.join(''));
  await downloadHtmlPdf(`analytics_${stamp()}.pdf`, html);
}

export async function exportLabPdf({ labData, t, language }) {
  const exportedAt = new Date().toLocaleString(language === 'en' ? 'en-GB' : 'ru-RU');
  const parts = [];
  const summary = labData?.summary;

  if (summary) {
    parts.push(`<h2 style="${S.h2}">${escapeHtml(t('lab.summary.experiments'))}</h2>`);
    parts.push(
      renderTable(
        [t('strategic.pdfMetric'), t('strategic.pdfValue')],
        [
          [t('lab.summary.gaps'), String(summary.gap_count)],
          [t('lab.summary.conflicts'), String(summary.conflict_count)],
          [t('lab.summary.sparse'), String(summary.sparse_cells)],
          [t('lab.summary.experiments'), String(summary.experiments_total)],
        ],
      ),
    );
  }

  const coverage = labData?.coverage;
  if (coverage?.materials?.length && coverage?.processes?.length) {
    parts.push(`<h2 style="${S.h2}">${escapeHtml(t('lab.coverageTitle'))}</h2>`);
    const headers = ['', ...coverage.processes];
    const rows = coverage.materials.map((material, rowIndex) => [
      material,
      ...coverage.matrix[rowIndex].map(String),
    ]);
    parts.push(renderTable(headers, rows));
  }

  if (labData?.gaps?.length) {
    parts.push(`<h2 style="${S.h2}">${escapeHtml(t('lab.gapsTitle'))}</h2>`);
    labData.gaps.forEach((gap) => {
      parts.push(`<p style="${S.p}"><strong>${escapeHtml(gap.title)}</strong><br>${escapeHtml(gap.description)}</p>`);
    });
  }

  if (labData?.contradictions?.length) {
    parts.push(`<h2 style="${S.h2}">${escapeHtml(t('lab.conflictsTitle'))}</h2>`);
    parts.push(
      renderTable(
        [t('lab.process'), 'A', 'B', t('lab.summary.conflicts')],
        labData.contradictions.map((c) => [
          c.process,
          `${c.claim_a} (${c.condition_a})`,
          `${c.claim_b} (${c.condition_b})`,
          t(`lab.risk.${c.risk}`, { defaultValue: c.risk }),
        ]),
      ),
    );
  }

  const html = wrapPage(t('nav.lab'), t('common.exportedAt', { date: exportedAt }), parts.join(''));
  await downloadHtmlPdf(`lab_${stamp()}.pdf`, html);
}

export async function exportAdminManagementPdf({ users, policies, t, language }) {
  const exportedAt = new Date().toLocaleString(language === 'en' ? 'en-GB' : 'ru-RU');
  const parts = [];

  parts.push(`<h2 style="${S.h2}">${escapeHtml(t('admin.usersTitle'))}</h2>`);
  parts.push(
    renderTable(
      [t('admin.userName'), t('admin.userEmail'), t('admin.userRole'), t('admin.userStatus')],
      (users ?? []).map((user) => [
        user.name,
        user.email,
        t(`roles.${user.role}`),
        user.active ? t('admin.statusActive') : t('admin.statusInactive'),
      ]),
    ),
  );

  parts.push(`<h2 style="${S.h2}">${escapeHtml(t('admin.accessTitle'))}</h2>`);
  parts.push(
    renderTable(
      [t('admin.document'), t('admin.accessLevel'), t('admin.allowedRoles'), t('admin.export')],
      (policies ?? []).map((policy) => [
        policy.document,
        t(`admin.levels.${policy.level}`, { defaultValue: policy.level }),
        policy.roles.map((role) => t(`roles.${role}`)).join(', '),
        policy.export_allowed ? t('admin.exportYes') : t('admin.exportNo'),
      ]),
    ),
  );

  const html = wrapPage(
    `${t('nav.admin')} — ${t('admin.nav.management')}`,
    t('common.exportedAt', { date: exportedAt }),
    parts.join(''),
  );
  await downloadHtmlPdf(`admin_management_${stamp()}.pdf`, html);
}

export async function exportAdminStatsPdf({ adminData, t, language }) {
  const exportedAt = new Date().toLocaleString(language === 'en' ? 'en-GB' : 'ru-RU');
  const parts = [];
  const summary = adminData?.summary;
  const operations = adminData?.operations;

  if (summary) {
    parts.push(`<h2 style="${S.h2}">${escapeHtml(t('admin.stats.summaryTitle'))}</h2>`);
    parts.push(
      renderTable(
        [t('strategic.pdfMetric'), t('strategic.pdfValue')],
        [
          [t('admin.summary.users'), String(adminData.users?.length ?? summary.users_count)],
          [t('admin.summary.audit24h'), String(summary.audit_events_24h)],
          [t('admin.summary.restricted'), String(summary.restricted_documents)],
          [t('admin.summary.denied24h'), String(summary.access_denied_24h)],
        ],
      ),
    );
  }

  if (operations) {
    parts.push(`<h2 style="${S.h2}">${escapeHtml(t('admin.ops.title'))}</h2>`);
    parts.push(
      renderTable(
        [t('strategic.pdfMetric'), t('strategic.pdfValue')],
        [
          [t('admin.ops.latencyP50'), `${operations.latency_p50_ms} ms`],
          [t('admin.ops.latencyP95'), `${operations.latency_p95_ms} ms`],
          [t('admin.ops.errors24h'), String(operations.errors_24h)],
          [t('admin.ops.rpsTotal'), String(operations.rps_total)],
        ],
      ),
    );

    if (operations.services?.length) {
      parts.push(`<h2 style="${S.h2}">${escapeHtml(t('admin.ops.servicesTitle'))}</h2>`);
      parts.push(
        renderTable(
          [
            t('admin.ops.service'),
            t('admin.ops.rps'),
            'p50',
            'p95',
            t('admin.ops.errors'),
            t('admin.ops.status'),
          ],
          operations.services.map((service) => [
            t(`admin.ops.serviceNames.${service.id}`, { defaultValue: service.id }),
            String(service.rps),
            `${service.latency_p50_ms} ms`,
            `${service.latency_p95_ms} ms`,
            String(service.errors_24h),
            t(`admin.ops.statuses.${service.status}`, { defaultValue: service.status }),
          ]),
        ),
      );
    }
  }

  const html = wrapPage(
    `${t('nav.admin')} — ${t('admin.nav.stats')}`,
    t('common.exportedAt', { date: exportedAt }),
    parts.join(''),
  );
  await downloadHtmlPdf(`admin_stats_${stamp()}.pdf`, html);
}

export async function exportAdminAuditPdf({ events, t, language }) {
  const exportedAt = new Date().toLocaleString(language === 'en' ? 'en-GB' : 'ru-RU');
  const parts = [];

  parts.push(`<h2 style="${S.h2}">${escapeHtml(t('admin.auditTitle'))}</h2>`);
  parts.push(
    renderTable(
      [t('admin.auditTime'), t('admin.auditUser'), t('admin.auditAction'), t('admin.auditObject')],
      (events ?? []).map((event) => [
        new Date(event.timestamp).toLocaleString(language === 'en' ? 'en-GB' : 'ru-RU'),
        event.user,
        t(`admin.actions.${event.action}`, { defaultValue: event.action }),
        event.object,
      ]),
    ),
  );

  const html = wrapPage(
    `${t('nav.admin')} — ${t('admin.nav.audit')}`,
    t('common.exportedAt', { date: exportedAt }),
    parts.join(''),
  );
  await downloadHtmlPdf(`admin_audit_${stamp()}.pdf`, html);
}
