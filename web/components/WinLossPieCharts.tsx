"use client";

import type { Game } from "@/lib/types";
import { outcomeForTeam } from "@/lib/games";
import { teamColor, teamName } from "@/lib/teams";

interface Props {
  team: string;
  games: Game[];
  attended: Set<string>;
}

interface Slice {
  team: string;
  count: number;
  pct: number;
  color: string;
}

function buildSlices(
  games: Game[], attended: Set<string>, team: string,
  filter: "win" | "loss",
): Slice[] {
  const counts = new Map<string, number>();
  for (const g of games) {
    if (!attended.has(g.id)) continue;
    if (outcomeForTeam(g, team) !== filter) continue;
    const opp = g.homeTeam === team ? g.awayTeam : g.homeTeam;
    counts.set(opp, (counts.get(opp) ?? 0) + 1);
  }
  const total = [...counts.values()].reduce((s, n) => s + n, 0);
  return [...counts.entries()]
    .map(([opp, count]) => ({
      team: opp,
      count,
      pct: total > 0 ? (count / total) * 100 : 0,
      color: teamColor(opp),
    }))
    .sort((a, b) => b.count - a.count);
}

export function WinLossPieCharts({ team, games, attended }: Props) {
  const wins = buildSlices(games, attended, team, "win");
  const losses = buildSlices(games, attended, team, "loss");

  if (wins.length === 0 && losses.length === 0) return null;

  return (
    <div className="grid grid-cols-2 gap-2 bg-white rounded-xl shadow-sm p-3">
      <PieBlock title="승리 상대" slices={wins} unit="승" emptyText="아직 승리 없음" />
      <PieBlock title="패배 상대" slices={losses} unit="패" emptyText="아직 패배 없음" />
    </div>
  );
}

function PieBlock({
  title, slices, unit, emptyText,
}: { title: string; slices: Slice[]; unit: string; emptyText: string }) {
  return (
    <div className="flex flex-col">
      <h4 className="text-[11px] font-semibold text-zinc-500 mb-1.5">{title}</h4>
      {slices.length === 0 ? (
        <div className="flex-1 flex items-center justify-center min-h-[88px] text-[11px] text-zinc-400">
          {emptyText}
        </div>
      ) : (
        <>
          <div className="flex justify-center mb-2">
            <Pie slices={slices} size={88} />
          </div>
          <ul className="space-y-0.5">
            {slices.map((s) => (
              <li key={s.team} className="text-[11px] text-black flex items-center gap-1.5 leading-tight">
                <span
                  className="size-2 rounded-sm shrink-0"
                  style={{ background: s.color }}
                  aria-hidden
                />
                <span className="truncate tabular-nums">
                  {teamName(s.team)} {s.count}{unit}({Math.round(s.pct)}%)
                </span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );
}

function Pie({ slices, size }: { slices: Slice[]; size: number }) {
  const total = slices.reduce((s, x) => s + x.count, 0);
  if (total === 0) return null;

  const cx = size / 2;
  const cy = size / 2;
  const r = size / 2;

  // Single slice — circle, no path math.
  if (slices.length === 1) {
    return (
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden>
        <circle cx={cx} cy={cy} r={r} fill={slices[0].color} />
      </svg>
    );
  }

  let startAngle = -Math.PI / 2;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden>
      {slices.map((slice, i) => {
        const angle = (slice.count / total) * 2 * Math.PI;
        const endAngle = startAngle + angle;
        const x1 = cx + r * Math.cos(startAngle);
        const y1 = cy + r * Math.sin(startAngle);
        const x2 = cx + r * Math.cos(endAngle);
        const y2 = cy + r * Math.sin(endAngle);
        const largeArc = angle > Math.PI ? 1 : 0;
        const path = `M ${cx},${cy} L ${x1.toFixed(3)},${y1.toFixed(3)} A ${r},${r} 0 ${largeArc},1 ${x2.toFixed(3)},${y2.toFixed(3)} Z`;
        startAngle = endAngle;
        return (
          <path
            key={`${slice.team}-${i}`}
            d={path}
            fill={slice.color}
            stroke="white"
            strokeWidth="1"
          />
        );
      })}
    </svg>
  );
}
