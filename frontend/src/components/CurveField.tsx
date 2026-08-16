export type Tone = "green" | "cyan";

const STOPS: Record<Tone, [string, string, string]> = {
  green: ["#22d3ee", "#3ddc84", "#d9f99d"],
  cyan: ["#818cf8", "#22d3ee", "#6ee7b7"],
};

type Ribbon = {
  /** One long arc. The bundle is this arc offset again and again, with a touch
   * of rotation so the far end opens out. */
  d: string;
  lines: number;
  shift: [number, number];
  spin: number;
  pivot: [number, number];
  fade: number;
};

const RIBBONS: Ribbon[] = [
  {
    d: "M -320 940 C 300 930, 700 830, 1150 90",
    lines: 46,
    shift: [6, -17],
    spin: 0.13,
    pivot: [-320, 940],
    fade: 1,
  },
  {
    d: "M -340 1120 C 120 1110, 420 1030, 660 830",
    lines: 20,
    shift: [4, -14],
    spin: 0.17,
    pivot: [-340, 1120],
    fade: 0.65,
  },
];

export function CurveField({ tone = "green" }: { tone?: Tone }) {
  const [start, middle, end] = STOPS[tone];
  const id = `curve-${tone}`;
  return (
    <svg className="curves" viewBox="0 0 1000 900" fill="none" aria-hidden="true">
      <defs>
        <linearGradient id={id} x1="0" y1="1" x2="1" y2="0">
          <stop offset="0%" stopColor={start} />
          <stop offset="52%" stopColor={middle} />
          <stop offset="100%" stopColor={end} />
        </linearGradient>
        <radialGradient id={`${id}-glow`} cx="0.68" cy="0.28" r="0.55">
          <stop offset="0%" stopColor={middle} stopOpacity="0.14" />
          <stop offset="100%" stopColor={middle} stopOpacity="0" />
        </radialGradient>
        {/* Without this the bundle ends on a hard vertical edge mid-page. */}
        <radialGradient id={`${id}-fade`} cx="0.72" cy="0.26" r="0.78">
          <stop offset="0%" stopColor="#fff" />
          <stop offset="55%" stopColor="#fff" stopOpacity="0.8" />
          <stop offset="100%" stopColor="#000" />
        </radialGradient>
        <mask id={`${id}-mask`}>
          <rect width="1000" height="900" fill={`url(#${id}-fade)`} />
        </mask>
      </defs>
      <rect width="1000" height="900" fill={`url(#${id}-glow)`} />
      <g mask={`url(#${id}-mask)`}>
      {RIBBONS.map((ribbon, r) =>
        Array.from({ length: ribbon.lines }, (_, i) => {
          const t = i / (ribbon.lines - 1);
          const [sx, sy] = ribbon.shift;
          const [px, py] = ribbon.pivot;
          return (
            <path
              key={`${r}-${i}`}
              d={ribbon.d}
              stroke={`url(#${id})`}
              strokeWidth="1"
              opacity={(0.68 - Math.abs(t - 0.42) * 0.5) * ribbon.fade}
              transform={`translate(${i * sx} ${i * sy}) rotate(${i * ribbon.spin} ${px} ${py})`}
            />
          );
        }),
      )}
      </g>
    </svg>
  );
}
