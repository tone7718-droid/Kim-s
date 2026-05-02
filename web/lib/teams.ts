// Canonical team codes (must match scraper/teams.py).

export interface TeamMeta {
  code: string;
  name: string;       // 한글 짧은 이름
  fullName: string;   // 한글 정식 이름
  color: string;      // hex — used for SVG fill, inline styles
  colorClass: string; // Tailwind bg color class for the team chip
  textClass: string;  // text color on top of the chip
}

export const TEAMS: TeamMeta[] = [
  { code: "KIA", name: "KIA",  fullName: "KIA 타이거즈",  color: "#EA0029", colorClass: "bg-kia",  textClass: "text-white" },
  { code: "SS",  name: "삼성", fullName: "삼성 라이온즈", color: "#074CA1", colorClass: "bg-ss",   textClass: "text-white" },
  { code: "LG",  name: "LG",   fullName: "LG 트윈스",     color: "#C30452", colorClass: "bg-lg",   textClass: "text-white" },
  { code: "OB",  name: "두산", fullName: "두산 베어스",   color: "#131230", colorClass: "bg-ob",   textClass: "text-white" },
  { code: "KT",  name: "KT",   fullName: "KT 위즈",       color: "#000000", colorClass: "bg-kt",   textClass: "text-white" },
  { code: "SSG", name: "SSG",  fullName: "SSG 랜더스",    color: "#CE0E2D", colorClass: "bg-ssg",  textClass: "text-white" },
  { code: "LT",  name: "롯데", fullName: "롯데 자이언츠", color: "#041E42", colorClass: "bg-lt",   textClass: "text-white" },
  { code: "HH",  name: "한화", fullName: "한화 이글스",   color: "#FF6600", colorClass: "bg-hh",   textClass: "text-white" },
  { code: "NC",  name: "NC",   fullName: "NC 다이노스",   color: "#315288", colorClass: "bg-nc",   textClass: "text-white" },
  { code: "WO",  name: "키움", fullName: "키움 히어로즈", color: "#820024", colorClass: "bg-wo",   textClass: "text-white" },
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

