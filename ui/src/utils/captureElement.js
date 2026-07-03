export async function waitForPaint(delayMs = 150) {
  await new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(resolve));
  });
  if (delayMs > 0) {
    await new Promise((resolve) => setTimeout(resolve, delayMs));
  }
}

export async function captureElementImage(
  element,
  { backgroundColor = '#ffffff', fullContent = false } = {},
) {
  if (!element) return '';

  await waitForPaint();

  const { default: html2canvas } = await import('html2canvas');
  const options = {
    scale: 2,
    useCORS: true,
    backgroundColor,
    logging: false,
  };

  if (fullContent) {
    options.height = element.scrollHeight;
    options.windowHeight = element.scrollHeight;
  }

  const canvas = await html2canvas(element, options);
  return canvas.toDataURL('image/png');
}

export function renderPdfImage(dataUrl, maxHeight = 320) {
  if (!dataUrl) return '';
  return `<img src="${dataUrl}" alt="" style="display:block;width:100%;max-height:${maxHeight}px;object-fit:contain;margin-bottom:12px;border:1px solid #E5E7EB;border-radius:8px;" />`;
}
