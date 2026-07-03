import { useCallback, useState } from 'react';

function clampPopoverPosition(rect, width = 300) {
  const margin = 12;
  const maxLeft = Math.max(margin, window.innerWidth - width - margin);
  const left = Math.min(Math.max(rect.left, margin), maxLeft);
  const spaceBelow = window.innerHeight - rect.bottom - margin;
  const estimatedHeight = 220;
  const openAbove = spaceBelow < estimatedHeight && rect.top > estimatedHeight;
  const top = openAbove ? Math.max(margin, rect.top - estimatedHeight - 8) : rect.bottom + 8;
  return { top, left, width, openAbove };
}

export function useSourceRefsPopover() {
  const [state, setState] = useState(null);

  const openPopover = useCallback((event, payload) => {
    const sources = payload?.sources?.filter(Boolean) ?? [];
    if (!sources.length) return;
    const target = event?.currentTarget ?? event?.target;
    if (!target?.getBoundingClientRect) return;
    const rect = target.getBoundingClientRect();
    setState({
      title: payload.title ?? '',
      subtitle: payload.subtitle ?? '',
      sources,
      position: clampPopoverPosition(rect),
    });
  }, []);

  const closePopover = useCallback(() => setState(null), []);

  return { popover: state, openPopover, closePopover };
}
