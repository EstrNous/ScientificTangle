import { renderPdfImage } from './captureElement.js';

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

function renderCoverageBarsHtml(directions) {
  if (!directions?.length) return '';
  const rows = directions
    .map((d) => {
      const pct = Math.round(d.coverage * 100);
      return `
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;font-size:11px;">
          <span style="width:120px;flex-shrink:0;color:#111827;">${escapeHtml(d.name)}</span>
          <div style="flex:1;height:8px;background:#F3F4F6;border-radius:4px;overflow:hidden;">
            <div style="width:${pct}%;height:100%;background:#0057B8;border-radius:4px;"></div>
          </div>
          <span style="width:36px;text-align:right;color:#6B7280;">${pct}%</span>
        </div>
      `;
    })
    .join('');
  return `<div style="margin-bottom:12px;">${rows}</div>`;
}

export async function exportStrategicCoveragePdf({ manager, t, language, chartImage = '' }) {
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
    if (chartImage) {
      parts.push(renderPdfImage(chartImage, 240));
    } else {
      parts.push(renderCoverageBarsHtml(manager.directions));
    }
    parts.push(`<h3 style="${S.h2}font-size:13px;">${escapeHtml(t('strategic.coverageList'))}</h3>`);
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

  const html = wrapPage(
    `${t('nav.strategic')} — ${t('strategic.nav.coverage')}`,
    t('common.exportedAt', { date: exportedAt }),
    parts.join(''),
  );
  await downloadHtmlPdf(`analytics_coverage_${stamp()}.pdf`, html);
}

export async function exportStrategicQualityPdf({ evaluation, t, language, dashboardImage = '' }) {
  const exportedAt = new Date().toLocaleString(language === 'en' ? 'en-GB' : 'ru-RU');
  const parts = [];

  if (evaluation?.summary || evaluation?.questions?.length) {
    parts.push(`<h2 style="${S.h2}">${escapeHtml(t('strategic.evaluationTitle'))}</h2>`);
    if (dashboardImage) {
      parts.push(renderPdfImage(dashboardImage, 480));
    }
  }

  if (evaluation?.summary) {
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

  const html = wrapPage(
    `${t('nav.strategic')} — ${t('strategic.nav.quality')}`,
    t('common.exportedAt', { date: exportedAt }),
    parts.join(''),
  );
  await downloadHtmlPdf(`analytics_quality_${stamp()}.pdf`, html);
}

export async function exportLabMatrixPdf({
  labData,
  t,
  language,
  summaryImage = '',
  matrixImage = '',
}) {
  const exportedAt = new Date().toLocaleString(language === 'en' ? 'en-GB' : 'ru-RU');
  const parts = [];
  const summary = labData?.summary;

  if (summary) {
    parts.push(`<h2 style="${S.h2}">${escapeHtml(t('lab.summary.links'))}</h2>`);
    if (summaryImage) {
      parts.push(renderPdfImage(summaryImage, 120));
    }
    parts.push(
      renderTable(
        [t('strategic.pdfMetric'), t('strategic.pdfValue')],
        [
          [t('lab.summary.gaps'), String(summary.gap_count)],
          [t('lab.summary.conflicts'), String(summary.conflict_count)],
          [t('lab.summary.sparse'), String(summary.sparse_cells)],
          [t('lab.summary.links'), String(summary.links_total ?? summary.experiments_total)],
        ],
      ),
    );
  }

  const view = labData?.matrixView ?? labData?.coverage;
  if (view?.rows?.length && view?.cols?.length) {
    const rowLabel = t(`lab.nodeTypes.${view.rowType}`, { defaultValue: view.rowType });
    const colLabel = t(`lab.nodeTypes.${view.colType}`, { defaultValue: view.colType });
    parts.push(
      `<h2 style="${S.h2}">${escapeHtml(t('lab.matrixTitle', { row: rowLabel, col: colLabel }))}</h2>`,
    );
    if (matrixImage) {
      parts.push(renderPdfImage(matrixImage, 360));
    }
    const headers = ['', ...view.cols];
    const rows = view.rows.map((row, rowIndex) => [
      row,
      ...view.matrix[rowIndex].map(String),
    ]);
    parts.push(renderTable(headers, rows));
  } else if (view?.materials?.length && view?.processes?.length) {
    parts.push(`<h2 style="${S.h2}">${escapeHtml(t('lab.matrixTitle', { row: t('lab.nodeTypes.Material'), col: t('lab.nodeTypes.Process') }))}</h2>`);
    if (matrixImage) {
      parts.push(renderPdfImage(matrixImage, 360));
    }
    const headers = ['', ...view.processes];
    const rows = view.materials.map((material, rowIndex) => [
      material,
      ...view.matrix[rowIndex].map(String),
    ]);
    parts.push(renderTable(headers, rows));
  }

  const html = wrapPage(
    `${t('nav.lab')} — ${t('lab.nav.matrix')}`,
    t('common.exportedAt', { date: exportedAt }),
    parts.join(''),
  );
  await downloadHtmlPdf(`lab_matrix_${stamp()}.pdf`, html);
}

export async function exportLabInsightsPdf({ labData, t, language, insightsImage = '' }) {
  const exportedAt = new Date().toLocaleString(language === 'en' ? 'en-GB' : 'ru-RU');
  const parts = [];

  if (labData?.gaps?.length || labData?.contradictions?.length) {
    if (insightsImage) {
      parts.push(renderPdfImage(insightsImage, 480));
    }
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

  const html = wrapPage(
    `${t('nav.lab')} — ${t('lab.nav.insights')}`,
    t('common.exportedAt', { date: exportedAt }),
    parts.join(''),
  );
  await downloadHtmlPdf(`lab_insights_${stamp()}.pdf`, html);
}

export async function exportAdminManagementPdf({
  users,
  policies,
  t,
  language,
  dashboardImage = '',
}) {
  const exportedAt = new Date().toLocaleString(language === 'en' ? 'en-GB' : 'ru-RU');
  const parts = [];

  if (dashboardImage) {
    parts.push(renderPdfImage(dashboardImage, 480));
  }

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

export async function exportAdminStatsPdf({ adminData, t, language, dashboardImage = '' }) {
  const exportedAt = new Date().toLocaleString(language === 'en' ? 'en-GB' : 'ru-RU');
  const parts = [];
  const summary = adminData?.summary;
  const operations = adminData?.operations;

  if (dashboardImage) {
    parts.push(renderPdfImage(dashboardImage, 480));
  }

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

export async function exportAdminAuditPdf({ events, t, language, auditImage = '' }) {
  const exportedAt = new Date().toLocaleString(language === 'en' ? 'en-GB' : 'ru-RU');
  const parts = [];

  parts.push(`<h2 style="${S.h2}">${escapeHtml(t('admin.auditTitle'))}</h2>`);
  if (auditImage) {
    parts.push(renderPdfImage(auditImage, 480));
  }
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
