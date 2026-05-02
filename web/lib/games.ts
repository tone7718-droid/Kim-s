import type { Game, GameStatus, SeasonPayload } from "./types";

// Default to seasons 2021..currentYear.
export function availableSeasons(currentYear: number = new Date().getFullYear()): number[] {
  const years: number[] = [];
  for (let y = 2021; y <= currentYear; y++) years.push(y);
  return years;
}

// Fetches a single season's payload from the static JSON shipped under
// /public/data/seasons. The cache buster (today's date) ensures users
// see fresh data within a day of the scraper publishing it without
// burning bandwidth on every navigation.
export async function loadSeason(year: number): Promise<SeasonPayload | null> {
  const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD (UTC-ish)
  try {
    const res = await fetch(`/data/seasons/${year}.json?d=${today}`, {
      cache: "no-cache", // forces revalidation against the network
    });
    if (!res.ok) return null;
    return (await res.json()) as SeasonPayload;
  } catch {
    return null;
  }
}

export interface FilterOptions {
  team: string;
  includePostseason?: boolean;
  includePreseason?: boolean;
}

export function gamesForTeam(
  games: Game[],
  { team, includePostseason = true, includePreseason = false }: FilterOptions,
): Game[] {
  return games
    .filter((g) => g.awayTeam === team || g.homeTeam === team)
    .filter((g) => {
      if (g.category === "preseason") return includePreseason;
      if (g.category === "postseason") return includePostseason;
      return true; // regular | unknown
    })
    .sort((a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : a.id.localeCompare(b.id)));
}

export type GameOutcome = "win" | "loss" | "tie" | "noresult";

export function outcomeForTeam(game: Game, team: string): GameOutcome {
  if (game.status === "tied") return "tie";
  if (game.status !== "completed") return "noresult";
  if (game.awayScore === null || game.homeScore === null) return "noresult";
  const isHome = game.homeTeam === team;
  const teamScore = isHome ? game.homeScore : game.awayScore;
  const oppScore = isHome ? game.awayScore : game.homeScore;
  return teamScore > oppScore ? "win" : "loss";
}

export interface AttendanceStats {
  total: number;
  wins: number;
  losses: number;
  ties: number;
  noresult: number; // 취소/연기/미진행으로 결과 없음
  // KBO 공식: W / (W + L). 무승부/취소/연기 제외.
  winRate: number | null; // null means undefined (no W/L games)
}

export function computeStats(
  games: Game[],
  attended: Set<string>,
  team: string,
): AttendanceStats {
  let wins = 0, losses = 0, ties = 0, noresult = 0;
  let total = 0;
  for (const g of games) {
    if (!attended.has(g.id)) continue;
    total++;
    const o = outcomeForTeam(g, team);
    if (o === "win") wins++;
    else if (o === "loss") losses++;
    else if (o === "tie") ties++;
    else noresult++;
  }
  const denom = wins + losses;
  return {
    total, wins, losses, ties, noresult,
    winRate: denom === 0 ? null : wins / denom,
  };
}

export function statusBadge(status: GameStatus): { label: string; className: string } {
  switch (status) {
    case "completed":  return { label: "종료",   className: "bg-zinc-200 text-zinc-700" };
    case "tied":       return { label: "무",     className: "bg-zinc-200 text-zinc-700" };
    case "cancelled":  return { label: "취소",   className: "bg-amber-100 text-amber-800" };
    case "postponed":  return { label: "연기",   className: "bg-amber-100 text-amber-800" };
    case "scheduled":  return { label: "예정",   className: "bg-sky-100 text-sky-800" };
  }
}

// === Breakdown stats ========================================================

export interface BreakdownRow {
  key: string;       // group label (e.g. "KIA", "홈", "4월")
  stats: AttendanceStats;
}

function statsFromGames(games: Game[], team: string): AttendanceStats {
  let wins = 0, losses = 0, ties = 0, noresult = 0;
  for (const g of games) {
    const o = outcomeForTeam(g, team);
    if (o === "win") wins++;
    else if (o === "loss") losses++;
    else if (o === "tie") ties++;
    else noresult++;
  }
  const denom = wins + losses;
  return {
    total: games.length, wins, losses, ties, noresult,
    winRate: denom === 0 ? null : wins / denom,
  };
}

export function breakdownByOpponent(
  games: Game[], attended: Set<string>, team: string,
): BreakdownRow[] {
  const groups = new Map<string, Game[]>();
  for (const g of games) {
    if (!attended.has(g.id)) continue;
    const opp = g.homeTeam === team ? g.awayTeam : g.homeTeam;
    const arr = groups.get(opp) ?? [];
    arr.push(g);
    groups.set(opp, arr);
  }
  return [...groups.entries()]
    .map(([key, gs]) => ({ key, stats: statsFromGames(gs, team) }))
    .sort((a, b) => b.stats.total - a.stats.total);
}

export function breakdownByVenue(
  games: Game[], attended: Set<string>, team: string,
): BreakdownRow[] {
  const home: Game[] = [];
  const away: Game[] = [];
  for (const g of games) {
    if (!attended.has(g.id)) continue;
    (g.homeTeam === team ? home : away).push(g);
  }
  const out: BreakdownRow[] = [];
  if (home.length) out.push({ key: "홈", stats: statsFromGames(home, team) });
  if (away.length) out.push({ key: "원정", stats: statsFromGames(away, team) });
  return out;
}

export function breakdownByMonth(
  games: Game[], attended: Set<string>, team: string,
): BreakdownRow[] {
  const groups = new Map<string, Game[]>();
  for (const g of games) {
    if (!attended.has(g.id)) continue;
    const month = g.date.slice(5, 7); // "04"
    const arr = groups.get(month) ?? [];
    arr.push(g);
    groups.set(month, arr);
  }
  return [...groups.entries()]
    .sort(([a], [b]) => (a < b ? -1 : 1))
    .map(([key, gs]) => ({
      key: `${parseInt(key, 10)}월`,
      stats: statsFromGames(gs, team),
    }));
}
