"use client";

import { useEffect, useMemo, useState } from "react";
import { TeamPicker } from "@/components/TeamPicker";
import { StatsCard } from "@/components/StatsCard";
import { GameList } from "@/components/GameList";
import { InstallButton } from "@/components/InstallButton";
import { SettingsMenu } from "@/components/SettingsMenu";
import { BreakdownStats } from "@/components/BreakdownStats";
import {
  availableSeasons,
  computeStats,
  gamesForTeam,
  loadSeason,
} from "@/lib/games";
import { useAttended } from "@/lib/storage";
import type { SeasonPayload } from "@/lib/types";

const PREFS_KEY = "kbo-attendance-prefs-v1";
type Prefs = {
  team?: string;
  year?: number;
  includePostseason?: boolean;
  includePreseason?: boolean;
  attendedOnly?: boolean;
};

function readPrefs(): Prefs {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.localStorage.getItem(PREFS_KEY);
    return raw ? (JSON.parse(raw) as Prefs) : {};
  } catch {
    return {};
  }
}
function writePrefs(p: Prefs) {
  if (typeof window === "undefined") return;
  try { window.localStorage.setItem(PREFS_KEY, JSON.stringify(p)); } catch { /* ignore */ }
}

export default function HomePage() {
  const seasons = useMemo(() => availableSeasons(), []);
  const [year, setYear] = useState<number>(seasons[seasons.length - 1]);
  const [team, setTeam] = useState<string | null>(null);
  const [season, setSeason] = useState<SeasonPayload | null>(null);
  const [loading, setLoading] = useState(false);
  const [includePostseason, setIncludePostseason] = useState(true);
  const [includePreseason, setIncludePreseason] = useState(false);
  const [attendedOnly, setAttendedOnly] = useState(false);
  const { attended, toggle, hydrated } = useAttended();

  // hydrate prefs
  useEffect(() => {
    const p = readPrefs();
    if (p.team) setTeam(p.team);
    if (p.year && seasons.includes(p.year)) setYear(p.year);
    if (typeof p.includePostseason === "boolean") setIncludePostseason(p.includePostseason);
    if (typeof p.includePreseason === "boolean") setIncludePreseason(p.includePreseason);
    if (typeof p.attendedOnly === "boolean") setAttendedOnly(p.attendedOnly);
  }, [seasons]);

  // persist prefs
  useEffect(() => {
    writePrefs({
      team: team ?? undefined,
      year,
      includePostseason,
      includePreseason,
      attendedOnly,
    });
  }, [team, year, includePostseason, includePreseason, attendedOnly]);

  // load season data
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    loadSeason(year).then((p) => {
      if (cancelled) return;
      setSeason(p);
      setLoading(false);
    });
    return () => { cancelled = true; };
  }, [year]);

  const games = useMemo(() => {
    if (!season || !team) return [];
    return gamesForTeam(season.games, { team, includePostseason, includePreseason });
  }, [season, team, includePostseason, includePreseason]);

  const visibleGames = useMemo(() => {
    return attendedOnly ? games.filter((g) => attended.has(g.id)) : games;
  }, [games, attendedOnly, attended]);

  const stats = useMemo(() => {
    if (!team) return null;
    return computeStats(games, attended, team);
  }, [games, attended, team]);

  return (
    <main className="mx-auto max-w-md px-4 py-5 pb-24">
      <header className="mb-4 flex items-start justify-between gap-3">
        <div>
          <h1 className="text-xl font-bold tracking-tight">내 직관 승률</h1>
          <p className="text-xs text-zinc-500 mt-0.5">KBO · 응원팀 직관 기록 → 승률 자동 계산</p>
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <InstallButton />
          <SettingsMenu />
        </div>
      </header>

      <section className="mb-4">
        <label className="text-xs font-semibold text-zinc-500 mb-1.5 block">시즌</label>
        <div className="flex gap-1.5 flex-wrap">
          {seasons.map((y) => (
            <button
              key={y}
              onClick={() => setYear(y)}
              className={[
                "px-3 py-1.5 rounded-full text-sm font-semibold tabular-nums",
                y === year ? "bg-zinc-900 text-white" : "bg-zinc-200 text-zinc-700",
              ].join(" ")}
            >
              {y}
            </button>
          ))}
        </div>
      </section>

      <section className="mb-4">
        <label className="text-xs font-semibold text-zinc-500 mb-1.5 block">응원팀</label>
        <TeamPicker selected={team} onSelect={setTeam} />
      </section>

      {team && stats && (
        <section className="mb-4 sticky top-2 z-20">
          <StatsCard team={team} stats={stats} />
        </section>
      )}

      {team && stats && stats.total > 0 && (
        <section className="mb-4">
          <BreakdownStats team={team} games={games} attended={attended} />
        </section>
      )}

      {team && (
        <section className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs text-zinc-600">
          <label className="flex items-center gap-1.5">
            <input
              type="checkbox"
              checked={attendedOnly}
              onChange={(e) => setAttendedOnly(e.target.checked)}
              className="size-4 accent-zinc-900"
            />
            직관 경기만 보기
          </label>
          <label className="flex items-center gap-1.5">
            <input
              type="checkbox"
              checked={includePostseason}
              onChange={(e) => setIncludePostseason(e.target.checked)}
              className="size-4 accent-zinc-900"
            />
            포스트시즌
          </label>
          <label className="flex items-center gap-1.5">
            <input
              type="checkbox"
              checked={includePreseason}
              onChange={(e) => setIncludePreseason(e.target.checked)}
              className="size-4 accent-zinc-900"
            />
            시범경기
          </label>
        </section>
      )}

      <section className="bg-white rounded-xl shadow-sm overflow-hidden">
        {!team ? (
          <div className="text-center text-zinc-500 py-12 text-sm">
            응원팀을 골라주세요
          </div>
        ) : loading || !hydrated ? (
          <div className="text-center text-zinc-400 py-12 text-sm">불러오는 중…</div>
        ) : !season ? (
          <div className="text-center text-zinc-500 py-12 text-sm">
            {year} 시즌 데이터가 아직 없어요.
          </div>
        ) : attendedOnly && visibleGames.length === 0 ? (
          <div className="text-center text-zinc-500 py-12 text-sm">
            직관 체크된 경기가 없어요.
          </div>
        ) : (
          <GameList team={team} games={visibleGames} attended={attended} onToggle={toggle} />
        )}
      </section>

      <footer className="mt-6 text-center text-[11px] text-zinc-400">
        직관 기록은 이 기기의 브라우저에만 저장됩니다.
      </footer>
    </main>
  );
}
