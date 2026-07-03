import { useEffect, useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import PageShell from '../components/shared/PageShell.jsx';
import Loader from '../components/shared/Loader.jsx';
import PdfDownloadButton from '../components/shared/PdfDownloadButton.jsx';
import {
  applyMatrixConfig,
  CoverageMatrix,
  createMatrixConfig,
  getLabMatrixSource,
  LabSubNav,
  LabSummaryCards,
  MatrixConfigPanel,
} from '../components/lab/index.js';
import { ensureAuth } from '../api/auth.js';
import { fetchLabCoverage } from '../api/lab.js';
import { captureElementImage, waitForPaint } from '../utils/captureElement.js';
import { exportLabMatrixPdf } from '../utils/pagePdfExport.js';

function getApiErrorMessage(error, fallback) {
  return error?.response?.data?.message ?? error?.message ?? fallback;
}

export default function LabMatrixPage() {
  const { t, i18n } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [labData, setLabData] = useState(null);
  const [matrixConfig, setMatrixConfig] = useState(createMatrixConfig);
  const [matrixExpanded, setMatrixExpanded] = useState(false);
  const summaryRef = useRef(null);
  const matrixRef = useRef(null);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setError(null);
      try {
        await ensureAuth();
        const data = await fetchLabCoverage();
        if (!cancelled) setLabData(data);
      } catch (loadError) {
        if (!cancelled) {
          setError(getApiErrorMessage(loadError, 'lab_load_failed'));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const availablePairs = useMemo(
    () => Object.keys(labData?.matrices ?? {}),
    [labData],
  );

  const matrixSource = useMemo(
    () => getLabMatrixSource(labData, matrixConfig.rowAxis, matrixConfig.colAxis),
    [labData, matrixConfig.rowAxis, matrixConfig.colAxis],
  );

  const filteredMatrix = useMemo(
    () => applyMatrixConfig(matrixSource, matrixConfig),
    [matrixSource, matrixConfig],
  );

  const handleExportPdf = async () => {
    const wasExpanded = matrixExpanded;
    if (wasExpanded) setMatrixExpanded(false);
    await waitForPaint(200);

    const exportData = { ...labData, matrixView: filteredMatrix };
    const [summaryImage, matrixImage] = await Promise.all([
      captureElementImage(summaryRef.current, { fullContent: true }),
      matrixRef.current?.getExportImage?.() ?? Promise.resolve(''),
    ]);
    await exportLabMatrixPdf({
      labData: exportData,
      t,
      language: i18n.language,
      summaryImage,
      matrixImage,
    });

    if (wasExpanded) setMatrixExpanded(true);
  };

  if (loading) return <Loader />;

  if (error) {
    return (
      <PageShell>
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-900 dark:bg-red-950/40 dark:text-red-200">
          {error}
        </div>
      </PageShell>
    );
  }

  return (
    <PageShell>
      <div className="flex h-full min-h-0 flex-col gap-2 overflow-hidden">
        <LabSubNav action={<PdfDownloadButton onExport={handleExportPdf} />} />
        {!matrixExpanded && (
          <>
            <div ref={summaryRef} className="shrink-0">
              <LabSummaryCards summary={labData?.summary} />
            </div>
            <MatrixConfigPanel
              matrixView={matrixSource}
              config={matrixConfig}
              onChange={setMatrixConfig}
              availablePairs={availablePairs}
            />
          </>
        )}
        <CoverageMatrix
          ref={matrixRef}
          view={filteredMatrix}
          fill
          showValues={matrixConfig.showValues}
          expanded={matrixExpanded}
          onToggleExpand={() => setMatrixExpanded((prev) => !prev)}
        />
      </div>
    </PageShell>
  );
}
