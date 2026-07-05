import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import ForceGraph2D from 'react-force-graph-2d';
import { useThemeStore } from '../../stores/themeStore.js';
import { GRAPH_NODE_COLORS } from './graphNodeTypes.js';

export default function KnowledgeGraph({ subgraph, selectedNodeId, onNodeClick, emptyMessage }) {
  const { t } = useTranslation();
  const graphRef = useRef();
  const containerRef = useRef();
  const [size, setSize] = useState({ width: 0, height: 0 });
  const theme = useThemeStore((s) => s.theme);
  const isDark = theme === 'dark';

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return undefined;
    const observer = new ResizeObserver(([entry]) => {
      setSize({
        width: entry.contentRect.width,
        height: entry.contentRect.height,
      });
    });
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (graphRef.current) {
      graphRef.current.d3Force('charge').strength(-140);
    }
  }, [subgraph]);

  if (!subgraph?.nodes?.length) {
    return (
      <div className="flex h-full min-h-[280px] items-center justify-center text-sm text-nn-gray dark:text-slate-400">
        {emptyMessage ?? t('graph.empty')}
      </div>
    );
  }
  const data = {
    nodes: subgraph.nodes.map((n) => ({ ...n, name: n.label })),
    links: subgraph.links.map((l) => ({ ...l })),
  };

  const bgColor = isDark ? '#0f172a' : '#F5F6F8';
  const labelColor = isDark ? '#e2e8f0' : '#1f2937';
  const linkColor = isDark ? '#475569' : '#cbd5e1';

  return (
    <div
      ref={containerRef}
      className="h-full min-h-[280px] overflow-hidden rounded-lg border border-nn-border dark:border-slate-600"
    >
      {size.width > 0 && size.height > 0 && (
        <ForceGraph2D
          ref={graphRef}
          width={size.width}
          height={size.height}
          graphData={data}
          backgroundColor={bgColor}
          linkColor={() => linkColor}
          linkWidth={1.5}
          onNodeClick={(node) => onNodeClick?.(node.id)}
          nodeCanvasObject={(node, ctx, globalScale) => {
            const isSelected = node.id === selectedNodeId;
            const color = GRAPH_NODE_COLORS[node.type] ?? GRAPH_NODE_COLORS.default;
            const radius = isSelected ? 8 : 6;
            ctx.beginPath();
            ctx.arc(node.x, node.y, radius, 0, 2 * Math.PI, false);
            ctx.fillStyle = color;
            ctx.fill();

            if (isSelected) {
              ctx.strokeStyle = isDark ? '#ffffff' : '#004494';
              ctx.lineWidth = 2 / globalScale;
              ctx.stroke();
            }

            const fontSize = Math.max(11 / globalScale, 4);
            ctx.font = `${fontSize}px Segoe UI, sans-serif`;
            ctx.fillStyle = labelColor;
            ctx.fillText(node.name, node.x + radius + 2, node.y + 3);
          }}
        />
      )}
    </div>
  );
}
