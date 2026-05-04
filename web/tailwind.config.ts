import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // KBO 팀 컬러 — public/teams/colors.md 기준
        kia:  "#EA0029",
        ss:   "#0065B3",
        lg:   "#C30452",
        ob:   "#1A1748",
        kt:   "#000000",
        ssg:  "#CE0E2D",
        lt:   "#041E42",
        hh:   "#FC4E00",
        nc:   "#315288",
        wo:   "#570514",
      },
    },
  },
  plugins: [],
};

export default config;
