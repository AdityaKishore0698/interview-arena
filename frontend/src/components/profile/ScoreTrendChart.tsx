'use client';

import { useId, useState } from 'react';

export interface TrendPoint {
  date: string; // ISO
  average: number; // 1-5
}

interface ScoreTrendChartProps {
  points: TrendPoint[];
}

const WIDTH = 640;
const HEIGHT = 220;
const PAD = { top: 16, right: 16, bottom: 28, left: 28 };
const Y_MIN = 1;
const Y_MAX = 5;

function yFor(value: number): number {
  const t = (value - Y_MIN) / (Y_MAX - Y_MIN);
  return PAD.top + (1 - t) * (HEIGHT - PAD.top - PAD.bottom);
}

function xFor(index: number, count: number): number {
  const innerWidth = WIDTH - PAD.left - PAD.right;
  if (count <= 1) return PAD.left + innerWidth / 2;
  return PAD.left + (index / (count - 1)) * innerWidth;
}

// A single series needs no legend — the section heading above this chart
// already says what's plotted. Marks per the design system's chart spec:
// 2px line, round caps, >=8px end markers with a surface-color ring, a light
// area wash, hairline recessive gridlines, and a hover crosshair + tooltip
// (every value it shows is also readable from the endpoint label / axis).
export function ScoreTrendChart({ points }: ScoreTrendChartProps) {
  const gradientId = useId();
  const [hoverIndex, setHoverIndex] = useState<number | null>(null);

  if (points.length < 2) {
    return (
      <div className="flex h-[160px] items-center justify-center rounded-xl border border-dashed border-border/60 bg-surface/20 text-sm text-muted-foreground">
        Complete a couple more interviews to see your trend here.
      </div>
    );
  }

  const coords = points.map((p, i) => ({ x: xFor(i, points.length), y: yFor(p.average), ...p }));
  const linePath = coords.map((c, i) => `${i === 0 ? 'M' : 'L'} ${c.x} ${c.y}`).join(' ');
  const areaPath = `${linePath} L ${coords[coords.length - 1].x} ${HEIGHT - PAD.bottom} L ${coords[0].x} ${HEIGHT - PAD.bottom} Z`;
  const gridValues = [1, 2, 3, 4, 5];
  const hovered = hoverIndex !== null ? coords[hoverIndex] : null;
  const last = coords[coords.length - 1];

  const handleMove = (e: React.PointerEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * WIDTH;
    let nearest = 0;
    let best = Infinity;
    coords.forEach((c, i) => {
      const d = Math.abs(c.x - px);
      if (d < best) { best = d; nearest = i; }
    });
    setHoverIndex(nearest);
  };

  return (
    <div className="relative rounded-xl border border-border/60 bg-surface/40 p-4">
      <svg
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
        className="w-full touch-none"
        role="img"
        aria-label={`Average feedback score trend across ${points.length} interviews, ending at ${last.average.toFixed(1)} out of 5`}
        onPointerMove={handleMove}
        onPointerLeave={() => setHoverIndex(null)}
      >
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--primary)" stopOpacity={0.18} />
            <stop offset="100%" stopColor="var(--primary)" stopOpacity={0} />
          </linearGradient>
        </defs>

        {/* Recessive gridlines, one hairline per whole score */}
        {gridValues.map((v) => (
          <g key={v}>
            <line
              x1={PAD.left}
              x2={WIDTH - PAD.right}
              y1={yFor(v)}
              y2={yFor(v)}
              stroke="var(--border)"
              strokeWidth={1}
            />
            <text x={PAD.left - 8} y={yFor(v)} textAnchor="end" dominantBaseline="middle" className="fill-muted-foreground text-[10px]">
              {v}
            </text>
          </g>
        ))}

        <path d={areaPath} fill={`url(#${gradientId})`} stroke="none" />
        <path d={linePath} fill="none" stroke="var(--primary)" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round" />

        {/* End markers: >=8px, surface-color ring so they read clearly against the line/gridlines */}
        {coords.map((c, i) => (
          <circle
            key={c.date + i}
            cx={c.x}
            cy={c.y}
            r={i === coords.length - 1 || i === hoverIndex ? 5 : 4}
            fill="var(--primary)"
            stroke="var(--surface)"
            strokeWidth={2}
          />
        ))}

        {/* Endpoint label — the one value worth labelling directly */}
        <text x={last.x} y={last.y - 12} textAnchor="middle" className="fill-foreground text-xs font-semibold">
          {last.average.toFixed(1)}
        </text>

        {/* Hover crosshair */}
        {hovered && (
          <line x1={hovered.x} x2={hovered.x} y1={PAD.top} y2={HEIGHT - PAD.bottom} stroke="var(--border-strong)" strokeWidth={1} strokeDasharray="3 3" />
        )}
      </svg>

      {hovered && (
        <div
          className="pointer-events-none absolute z-10 -translate-x-1/2 rounded-lg border border-border/60 bg-popover px-3 py-2 text-xs shadow-elev-md"
          style={{
            left: `${(hovered.x / WIDTH) * 100}%`,
            top: 4,
          }}
        >
          <p className="font-semibold text-foreground">{hovered.average.toFixed(1)} / 5</p>
          <p className="text-muted-foreground">{new Date(hovered.date).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}</p>
        </div>
      )}
    </div>
  );
}
