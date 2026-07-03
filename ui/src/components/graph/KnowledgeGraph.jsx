import { useEffect, useRef } from 'react';
import ForceGraph2D from 'react-force-graph-2d';

export default function KnowledgeGraph({ subgraph }) {
  const ref = useRef();

  useEffect(() => {
    if (ref.current) {
      ref.current.d3Force('charge').strength(-120);
    }
  }, []);

  if (!subgraph) return null;

  const data = {
    nodes: subgraph.nodes.map((n) => ({ ...n, name: n.label })),
    links: subgraph.links.map((l) => ({ ...l })),
  };

  return (
    <div className="h-full min-h-[240px] bg-slate-900 rounded border border-slate-800">
      <ForceGraph2D
        ref={ref}
        graphData={data}
        nodeLabel="name"
        nodeCanvasObject={(node, ctx, globalScale) => {
          const label = node.name;
          const fontSize = 12 / globalScale;
          ctx.font = `${fontSize}px Sans-Serif`;
          ctx.fillStyle = node.type === 'Material' ? '#34d399' : '#60a5fa';
          ctx.beginPath();
          ctx.arc(node.x, node.y, 5, 0, 2 * Math.PI, false);
          ctx.fill();
          ctx.fillStyle = '#e2e8f0';
          ctx.fillText(label, node.x + 8, node.y + 4);
        }}
      />
    </div>
  );
}
