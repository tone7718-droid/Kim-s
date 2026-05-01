"use client";

import { useMemo, useState } from "react";
import type { Game } from "@/lib/types";
import {
  type BreakdownRow,
  breakdownByOpponent,
  breakdownByVenue,
  breakdownByMonth,
} from "@/lib/games";
import { teamName } from "@/lib/teams";

type Tab = "opp" | "venue" | "month";

interface Props {
  team: string;
  games: Game[];
  attended: Set<string>;
}

export function BreakdownStats({ team, games, attended }: Props) {
  const [tab, setTab] = useState<Tab>("opp");

  const data = useMemo(() => ({
    opp: breakdownByOpponent(games, attended, team),
    venue: breakdownByVenue(games, attended, team),
    month: breakdownByMonth(games, attended, team),
  }), [games, attended, team]);

  const empty = data.opp.length === 0;
  if (empty) return null;

  const rows = data[tab];

  return (
    <div className="bg-white rounded-xl shadow-sm overflow-hidden">
      <div className="flex border-b border-zinc-100 text-xs font-semibold">
        <TabButton active={tab === "opp"} onClick={() => setTab("opp")}>
          상대팀별
        </TabButton>
        <TabButton active={tab === "venue"} onClick={() => setTab("venue")}>
          홈/원정
        </TabButton>
        <TabButton active={tab === "month"} onClick={() => setTab("month")}>
          월별
        </TabButton>
      </div>
      <ul className="divide-y divide-zinc-100">
        {rows.map((row) => (
          <Row key={row.key} row={row} labelMap={tab === "opp" ? teamName : (s) => s} />
        ))}
      </ul>
    </div>
  );
}

function TabButton({
  active, onClick, children,
}: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      className={[
        "flex-1 py-2.5 transition",
        active ? "text-zinc-900 border-b-2 border-zinc-900 -mb-px" : "text-zinc-500",
      ].join(" ")}
    >
      {children}
    </button>
  );
}

function Row({
  row, labelMap,
}: { row: BreakdownRow; labelMap: (k: string) => string }) {
  const { key, stats } = row;
  const wr = stats.winRate === null ? "—" : stats.winRate.toFixed(3).replace(/^0/, "");
  return (
    <li className="px-3 py-2.5 flex items-center justify-between">
      <div className="text-sm font-semibold w-14 shrink-0">{labelMap(key)}</div>
      <div className="text-xs text-zinc-500 tabular-nums flex-1 ml-2">
        <span className="text-emerald-600 font-bold">{stats.wins}</span>
        <span className="mx-0.5 text-zinc-300">·</span>
        <span className="text-rose-600 font-bold">{stats.losses}</span>
        <span className="mx-0.5 text-zinc-300">·</span>
        <span>{stats.ties}무</span>
        {stats.noresult > 0 && (
          <>
            <span className="mx-0.5 text-zinc-300">·</span>
            <span className="text-zinc-400">{stats.noresult}기타</span>
          </>
        )}
      </div>
      <div className="text-base font-bold tabular-nums w-14 text-right">{wr}</div>
    </li>
  );
}
