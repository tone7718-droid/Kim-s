import { describe, it, expect } from "vitest";
import {
  outcomeForTeam,
  computeStats,
  gamesForTeam,
  buildNaverRecordUrl,
  breakdownByVenue,
} from "./games";
import type { Game } from "./types";

// Build a Game with sensible defaults; override only what a test cares about.
function game(partial: Partial<Game> = {}): Game {
  return {
    id: "2024-04-01-OB-LG",
    date: "2024-04-01",
    awayTeam: "OB",
    homeTeam: "LG",
    awayScore: 3,
    homeScore: 5,
    status: "completed",
    stadium: "잠실",
    category: "regular",
    ...partial,
  };
}

describe("outcomeForTeam", () => {
  it("home team win", () => {
    expect(outcomeForTeam(game({ homeScore: 5, awayScore: 3 }), "LG")).toBe("win");
  });
  it("home team loss", () => {
    expect(outcomeForTeam(game({ homeScore: 3, awayScore: 5 }), "LG")).toBe("loss");
  });
  it("away team win (perspective flips)", () => {
    expect(outcomeForTeam(game({ homeScore: 3, awayScore: 5 }), "OB")).toBe("win");
  });
  it("tie status is a tie regardless of scores", () => {
    expect(outcomeForTeam(game({ status: "tied", homeScore: 4, awayScore: 4 }), "LG")).toBe("tie");
  });
  it("cancelled game has no result", () => {
    expect(outcomeForTeam(game({ status: "cancelled", homeScore: null, awayScore: null }), "LG")).toBe("noresult");
  });
  it("completed but missing scores is no result", () => {
    expect(outcomeForTeam(game({ status: "completed", homeScore: null, awayScore: null }), "LG")).toBe("noresult");
  });
});

describe("computeStats", () => {
  const games = [
    game({ id: "g1", homeTeam: "LG", awayTeam: "OB", homeScore: 5, awayScore: 3 }), // LG win
    game({ id: "g2", homeTeam: "OB", awayTeam: "LG", homeScore: 7, awayScore: 2 }), // LG loss
    game({ id: "g3", status: "tied", homeTeam: "LG", awayTeam: "OB", homeScore: 4, awayScore: 4 }), // tie
    game({ id: "g4", status: "cancelled", homeTeam: "LG", awayTeam: "OB", homeScore: null, awayScore: null }), // noresult
  ];

  it("counts only attended games", () => {
    const stats = computeStats(games, new Set(["g1", "g2"]), "LG");
    expect(stats.total).toBe(2);
    expect(stats.wins).toBe(1);
    expect(stats.losses).toBe(1);
  });

  it("win rate is W / (W + L), excluding ties and no-results", () => {
    const stats = computeStats(games, new Set(["g1", "g2", "g3", "g4"]), "LG");
    expect(stats.total).toBe(4);
    expect(stats.wins).toBe(1);
    expect(stats.losses).toBe(1);
    expect(stats.ties).toBe(1);
    expect(stats.noresult).toBe(1);
    expect(stats.winRate).toBeCloseTo(0.5, 5);
  });

  it("win rate is null when there are no decided games", () => {
    const stats = computeStats(games, new Set(["g3", "g4"]), "LG");
    expect(stats.winRate).toBeNull();
  });

  it("empty attended set yields zero stats", () => {
    const stats = computeStats(games, new Set(), "LG");
    expect(stats).toMatchObject({ total: 0, wins: 0, losses: 0, winRate: null });
  });
});

describe("gamesForTeam", () => {
  const games = [
    game({ id: "a", date: "2024-05-02", homeTeam: "LG", awayTeam: "OB", category: "regular" }),
    game({ id: "b", date: "2024-05-01", homeTeam: "KT", awayTeam: "LG", category: "regular" }),
    game({ id: "c", date: "2024-03-10", homeTeam: "LG", awayTeam: "SS", category: "preseason" }),
    game({ id: "d", date: "2024-10-15", homeTeam: "LG", awayTeam: "KT", category: "postseason" }),
    game({ id: "e", date: "2024-06-01", homeTeam: "NC", awayTeam: "SS", category: "regular" }), // no LG
  ];

  it("keeps only games involving the team", () => {
    const ids = gamesForTeam(games, { team: "LG" }).map((g) => g.id);
    expect(ids).not.toContain("e");
  });

  it("excludes preseason by default, includes postseason by default", () => {
    const ids = gamesForTeam(games, { team: "LG" }).map((g) => g.id);
    expect(ids).toContain("d"); // postseason
    expect(ids).not.toContain("c"); // preseason
  });

  it("respects includePreseason / includePostseason flags", () => {
    const withPre = gamesForTeam(games, { team: "LG", includePreseason: true }).map((g) => g.id);
    expect(withPre).toContain("c");
    const noPost = gamesForTeam(games, { team: "LG", includePostseason: false }).map((g) => g.id);
    expect(noPost).not.toContain("d");
  });

  it("sorts by date ascending", () => {
    const dates = gamesForTeam(games, { team: "LG", includePreseason: true }).map((g) => g.date);
    expect(dates).toEqual([...dates].sort());
  });
});

describe("buildNaverRecordUrl", () => {
  it("prefers an explicit naverRecordUrl", () => {
    const url = "https://m.sports.naver.com/game/EXPLICIT/record";
    expect(buildNaverRecordUrl(game({ naverRecordUrl: url }))).toBe(url);
  });

  it("uses naverGameId when present", () => {
    expect(buildNaverRecordUrl(game({ naverGameId: "20240401OBLG02024" }))).toBe(
      "https://m.sports.naver.com/game/20240401OBLG02024/record",
    );
  });

  it("falls back to a URL built from date + team codes", () => {
    const g = game({ id: "2024-04-01-OB-LG", naverGameId: null, naverRecordUrl: null });
    expect(buildNaverRecordUrl(g)).toBe(
      "https://m.sports.naver.com/game/20240401OBLG02024/record",
    );
  });

  it("maps a doubleheader id suffix to the game sequence", () => {
    const g = game({ id: "2024-04-01-OB-LG-2", naverGameId: null, naverRecordUrl: null });
    expect(buildNaverRecordUrl(g)).toBe(
      "https://m.sports.naver.com/game/20240401OBLG12024/record",
    );
  });

  it("translates KIA/SSG to Naver's HT/SK codes", () => {
    const g = game({
      id: "2024-04-01-KIA-SSG",
      awayTeam: "KIA",
      homeTeam: "SSG",
      naverGameId: null,
      naverRecordUrl: null,
    });
    expect(buildNaverRecordUrl(g)).toBe(
      "https://m.sports.naver.com/game/20240401HTSK02024/record",
    );
  });
});

describe("breakdownByVenue", () => {
  it("splits attended games into home and away buckets", () => {
    const games = [
      game({ id: "h1", homeTeam: "LG", awayTeam: "OB", homeScore: 5, awayScore: 1 }), // LG home win
      game({ id: "a1", homeTeam: "KT", awayTeam: "LG", homeScore: 1, awayScore: 6 }), // LG away win
    ];
    const rows = breakdownByVenue(games, new Set(["h1", "a1"]), "LG");
    const home = rows.find((r) => r.key === "홈");
    const away = rows.find((r) => r.key === "원정");
    expect(home?.stats.wins).toBe(1);
    expect(away?.stats.wins).toBe(1);
  });
});
