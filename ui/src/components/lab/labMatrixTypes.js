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

export function getLabMatrixSource(labData, rowAxis, colAxis) {
  if (!labData) return null;
  const key = matrixKey(rowAxis, colAxis);
  const view = labData.matrices?.[key];
  if (view) return view;

  if (rowAxis === 'Material' && colAxis === 'Process' && labData.coverage) {
    return {
      rowType: 'Material',
      colType: 'Process',
      rows: labData.coverage.materials,
      cols: labData.coverage.processes,
      matrix: labData.coverage.matrix,
    };
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
  if (!matrixView || !config) return null;

  const rowIndices = matrixView.rows
    .map((name, index) => {
      if (config.rowFilter !== 'all' && name !== config.rowFilter) return -1;
      return index;
    })
    .filter((index) => index >= 0);

  const colIndices = matrixView.cols
    .map((name, index) => {
      if (config.colFilter !== 'all' && name !== config.colFilter) return -1;
      return index;
    })
    .filter((index) => index >= 0);

  if (!rowIndices.length || !colIndices.length) return null;

  const cellSources = matrixView.cell_sources ?? matrixView.cellSources;

  return {
    rowType: matrixView.rowType,
    colType: matrixView.colType,
    rows: rowIndices.map((index) => matrixView.rows[index]),
    cols: colIndices.map((index) => matrixView.cols[index]),
    matrix: rowIndices.map((row) => colIndices.map((col) => matrixView.matrix[row][col])),
    ...(cellSources
      ? {
          cell_sources: rowIndices.map((row) =>
            colIndices.map((col) => cellSources[row][col]),
          ),
        }
      : {}),
  };
}
