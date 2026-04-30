import type { AttendanceStats } from "@/lib/games";
import { teamName } from "@/lib/teams";

interface Props {
  team: string;
  stats: AttendanceStats;
}

export function StatsCard({ team, stats }: Props) {
  const { total, wins, losses, ties, noresult, winRate } = stats;
  const wr = winRate === null ? "—" : winRate.toFixed(3).replace(/^0/, "");
  return (
    <div className="rounded-xl bg-zinc-900 text-white p-4 shadow-lg">
      <div className="flex items-baseline justify-between mb-2">
        <div className="text-sm opacity-70">내가 본 {teamName(team)} 경기</div>
        <div className="text-2xl font-bold tabular-nums">{total}경기</div>
      </div>
      <div className="grid grid-cols-4 gap-2 text-center">
        <Stat label="승" value={wins} accent="text-emerald-300" />
        <Stat label="패" value={losses} accent="text-rose-300" />
        <Stat label="무" value={ties} />
        <Stat label="기타" value={noresult} subtle />
      </div>
      <div className="mt-3 flex items-baseline justify-between border-t border-white/10 pt-3">
        <div className="text-sm opacity-70">승률 (W / W+L)</div>
        <div className="text-3xl font-bold tabular-nums">{wr}</div>
      </div>
    </div>
  );
}

function Stat({
  label, value, accent, subtle,
}: { label: string; value: number; accent?: string; subtle?: boolean }) {
  return (
    <div className={subtle ? "opacity-60" : ""}>
      <div className={`text-xl font-bold tabular-nums ${accent ?? ""}`}>{value}</div>
      <div className="text-[11px] opacity-70 mt-0.5">{label}</div>
    </div>
  );
}
