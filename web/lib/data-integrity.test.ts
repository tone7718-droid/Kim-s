import { afterEach, describe, expect, it, vi } from "vitest";
import { buildNaverRecordUrl, dataRefreshWarning, isSeasonPayload, loadSeason } from "./games";
import type { SeasonPayload } from "./types";

const season: SeasonPayload = {year:2026,generatedAt:"2026-11-03T00:00:00+09:00",games:[{
  id:"2026-11-03-SS-KT",date:"2026-11-03",awayTeam:"SS",homeTeam:"KT",awayScore:null,homeScore:null,
  status:"scheduled",stadium:"수원",category:"postseason",startTime:"18:30",
}]};
afterEach(() => vi.unstubAllGlobals());
describe("season validation and refresh", () => {
  it.each([{},null,{...season,year:2025},{...season,games:[{...season.games[0],homeTeam:"XX"}]},
    {...season,games:[{...season.games[0],startTime:"25:00"}]},
    {...season,games:[{...season.games[0],awayScore:undefined}]},
    {...season,games:[season.games[0],season.games[0]]},
  ])("rejects malformed season responses", async payload => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify(payload))));
    expect((await loadSeason(2026)).status).toBe("error");
  });
  it("accepts valid data and reports cache fallback", async () => {
    vi.stubGlobal("fetch",vi.fn().mockResolvedValue(new Response(JSON.stringify(season),{headers:{"X-KBO-Cache":"fallback"}})));
    expect(await loadSeason(2026)).toEqual({status:"ok",payload:season,fromCache:true});
  });
  it("keeps unpublished seasons separate from a broken response", async () => {
    vi.stubGlobal("fetch",vi.fn().mockResolvedValue(new Response(null,{status:404})));
    expect(await loadSeason(2026)).toEqual({status:"empty"});
  });
  it("warns about partial refreshes even when the overall timestamp is recent", () => {
    expect(dataRefreshWarning({...season,refresh:{attemptedAt:season.generatedAt,failedMonths:[11]}})).toContain("11월");
  });
  it("does not guess postseason or either doubleheader record", () => {
    expect(buildNaverRecordUrl(season.games[0])).toBeNull();
    expect(buildNaverRecordUrl({...season.games[0],category:"regular"},true)).toBeNull();
  });
  it("rejects invalid dates and inconsistent results", () => {
    expect(isSeasonPayload({...season,games:[{...season.games[0],date:"2026-02-30"}]},2026)).toBe(false);
    expect(isSeasonPayload({...season,games:[{...season.games[0],status:"completed"}]},2026)).toBe(false);
  });
});
