"use client";

import { useMemo } from "react";
import type { Game } from "@/lib/types";
import { outcomeForTeam, statusBadge } from "@/lib/games";
import { teamName } from "@/lib/teams";

interface Props {
  team: string;
  games: Game[];
  attended: Set<string>;
  onToggle: (id: string) => void;
}

export function GameList({ team, games, attended, onToggle }: Props) {
  // Group by month for sticky headers.
  const sections = useMemo(() => {
    const m = new Map<string, Game[]>();
    for (const g of games) {
      const key = g.date.slice(0, 7); // YYYY-MM
      const arr = m.get(key) ?? [];
      arr.push(g);
      m.set(key, arr);
    }
    return [...m.entries()].sort(([a], [b]) => (a < b ? -1 : 1));
  }, [games]);

  if (games.length === 0) {
    return (
      <div className="text-center text-zinc-500 py-12 text-sm">
        이 시즌의 {teamName(team)} 경기가 아직 없어요.
      </div>
    );
  }

  return (
    <div className="space-y-1">
      {sections.map(([yyyymm, gs]) => (
        <section key={yyyymm}>
          <h3 className="sticky top-0 z-10 bg-zinc-100/95 backdrop-blur px-3 py-1.5 text-xs font-semibold text-zinc-500">
            {yyyymm.replace("-", "년 ")}월
          </h3>
          <ul className="divide-y divide-zinc-100">
            {gs.map((g) => (
              <GameRow
                key={g.id}
                team={team}
                game={g}
                checked={attended.has(g.id)}
                onToggle={onToggle}
              />
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}

function GameRow({
  team, game, checked, onToggle,
}: { team: string; game: Game; checked: boolean; onToggle: (id: string) => void }) {
  const isHome = game.homeTeam === team;
  const opp = isHome ? game.awayTeam : game.homeTeam;
  const out = outcomeForTeam(game, team);
  const badge = statusBadge(game.status);

  const scoreText =
    game.awayScore === null || game.homeScore === null
      ? "—"
      : isHome
        ? `${game.homeScore} : ${game.awayScore}`
        : `${game.awayScore} : ${game.homeScore}`;

  const outcomeClass =
    out === "win"  ? "text-emerald-600 font-bold"
    : out === "loss" ? "text-rose-600 font-bold"
    : out === "tie"  ? "text-zinc-500"
    : "text-zinc-400";
  const outcomeText =
    out === "win" ? "승" : out === "loss" ? "패" : out === "tie" ? "무" : "—";

  return (
    <li>
      <label className="flex items-center gap-3 px-3 py-2.5 active:bg-zinc-50">
        <input
          type="checkbox"
          checked={checked}
          onChange={() => onToggle(game.id)}
          className="size-5 accent-zinc-900 shrink-0"
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-baseline gap-2">
            <span className="text-xs text-zinc-500 tabular-nums shrink-0">
              {game.date.slice(5)}
            </span>
            <span
              className={`text-[10px] font-bold px-1.5 py-0.5 rounded shrink-0 ${
                isHome ? "bg-emerald-100 text-emerald-700" : "bg-violet-100 text-violet-700"
              }`}
            >
              {isHome ? "홈" : "원정"}
            </span>
            <span className="text-sm truncate">vs {teamName(opp)}</span>
          </div>
          {game.stadium && (
            <div className="text-[11px] text-zinc-400 mt-0.5 truncate">{game.stadium}</div>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-sm tabular-nums">{scoreText}</span>
          <span className={`text-sm w-5 text-center ${outcomeClass}`}>{outcomeText}</span>
          {game.status !== "completed" && game.status !== "tied" && (
            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${badge.className}`}>
              {badge.label}
            </span>
          )}
        </div>
      </label>
    </li>
  );
}
