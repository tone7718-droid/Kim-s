export type GameStatus =
  | "completed"
  | "tied"
  | "cancelled"
  | "postponed"
  | "scheduled";

export type GameCategory = "regular" | "postseason" | "preseason" | "unknown";

export interface Game {
  id: string;
  date: string;          // YYYY-MM-DD
  awayTeam: string;      // canonical team code (KIA, SS, LG, ...)
  homeTeam: string;
  awayScore: number | null;
  homeScore: number | null;
  status: GameStatus;
  stadium: string | null;
  category: GameCategory;
  // Naver's original game identifier/record URL when the scraper can read it.
  // Older season JSON files may not have these fields, so the UI also builds
  // a best-effort URL from date + team codes.
  naverGameId?: string | null;
  naverRecordUrl?: string | null;
}

export interface SeasonPayload {
  year: number;
  generatedAt: string;
  games: Game[];
}
