export const LAB_MATRIX_AXIS_TYPES = [
  'Material',
  'Process',
  'Experiment',
  'Lab',
  'Regime',
  'Author',
];

export function matrixKey(rowAxis, colAxis) {
  return `${rowAxis}_${colAxis}`;
}

export function normalizeMatrixView(view) {
  if (!view) return null;
  return {
    rowType: view.rowType ?? view.row_type ?? 'Material',
    colType: view.colType ?? view.col_type ?? 'Process',
    rows: view.rows ?? [],
    cols: view.cols ?? [],
    matrix: view.matrix ?? [],
    cell_sources: view.cell_sources ?? view.cellSources,
  };
}

export function getLabMatrixSource(labData, rowAxis, colAxis) {
  if (!labData) return null;
  const key = matrixKey(rowAxis, colAxis);
  const view = normalizeMatrixView(labData.matrices?.[key]);
  if (view?.rows?.length && view?.cols?.length) return view;

  if (rowAxis === 'Material' && colAxis === 'Process' && labData.coverage) {
    return normalizeMatrixView({
      rowType: 'Material',
      colType: 'Process',
      rows: labData.coverage.materials,
      cols: labData.coverage.processes,
      matrix: labData.coverage.matrix,
    });
  }

  return null;
}

export function createMatrixConfig() {
  return {
    rowAxis: 'Material',
    colAxis: 'Process',
    rowFilter: 'all',
    colFilter: 'all',
    showValues: false,
  };
}

export function applyMatrixConfig(matrixView, config) {
  const view = normalizeMatrixView(matrixView);
  if (!view || !config) return null;

  const sourceRows = view.rows;
  const sourceCols = view.cols;
  const sourceMatrix = view.matrix;

  const rowIndices = sourceRows
    .map((name, index) => {
      if (config.rowFilter !== 'all' && name !== config.rowFilter) return -1;
      return index;
    })
    .filter((index) => index >= 0);

  const colIndices = sourceCols
    .map((name, index) => {
      if (config.colFilter !== 'all' && name !== config.colFilter) return -1;
      return index;
    })
    .filter((index) => index >= 0);

  if (!rowIndices.length || !colIndices.length) return null;

  const cellSources = view.cell_sources;

  return {
    rowType: view.rowType,
    colType: view.colType,
    rows: rowIndices.map((index) => sourceRows[index]),
    cols: colIndices.map((index) => sourceCols[index]),
    matrix: rowIndices.map((row) =>
      colIndices.map((col) => {
        const value = sourceMatrix[row]?.[col];
        return typeof value === 'number' ? value : 0;
      }),
    ),
    ...(cellSources
      ? {
          cell_sources: rowIndices.map((row) =>
            colIndices.map((col) => cellSources[row]?.[col] ?? []),
          ),
        }
      : {}),
  };
}
