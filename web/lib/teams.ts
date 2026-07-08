// Canonical team codes (must match scraper/teams.py).

export interface TeamMeta {
  code: string;
  name: string;      // 한글 짧은 이름
  fullName: string;  // 한글 정식 이름
  color: string;     // hex — used for SVG fill and inline styles (TeamPicker border, pie charts)
}

export const TEAMS: TeamMeta[] = [
  { code: "KIA", name: "KIA",  fullName: "KIA 타이거즈",  color: "#EA0029" },
  { code: "SS",  name: "삼성", fullName: "삼성 라이온즈", color: "#0065B3" },
  { code: "LG",  name: "LG",   fullName: "LG 트윈스",     color: "#C30452" },
  { code: "OB",  name: "두산", fullName: "두산 베어스",   color: "#1A1748" },
  { code: "KT",  name: "KT",   fullName: "KT 위즈",       color: "#000000" },
  { code: "SSG", name: "SSG",  fullName: "SSG 랜더스",    color: "#CE0E2D" },
  { code: "LT",  name: "롯데", fullName: "롯데 자이언츠", color: "#041E42" },
  { code: "HH",  name: "한화", fullName: "한화 이글스",   color: "#FC4E00" },
  { code: "NC",  name: "NC",   fullName: "NC 다이노스",   color: "#315288" },
  { code: "WO",  name: "키움", fullName: "키움 히어로즈", color: "#570514" },
];

export const TEAM_BY_CODE: Record<string, TeamMeta> = Object.fromEntries(
  TEAMS.map((t) => [t.code, t]),
);

export function teamName(code: string): string {
  return TEAM_BY_CODE[code]?.name ?? code;
}

export function teamColor(code: string): string {
  return TEAM_BY_CODE[code]?.color ?? "#71717a";
}

