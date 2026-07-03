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
import { apiGet } from '../api/client.js';
import { captureElementImage, waitForPaint } from '../utils/captureElement.js';
import { exportLabMatrixPdf } from '../utils/pagePdfExport.js';

export default function LabMatrixPage() {
  const { t, i18n } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [labData, setLabData] = useState(null);
  const [matrixConfig, setMatrixConfig] = useState(createMatrixConfig);
  const [matrixExpanded, setMatrixExpanded] = useState(false);
  const summaryRef = useRef(null);
  const matrixRef = useRef(null);

  useEffect(() => {
    apiGet('/lab/coverage')
      .then(setLabData)
      .finally(() => setLoading(false));
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
