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
}

export interface SeasonPayload {
  year: number;
  generatedAt: string;
  games: Game[];
}
