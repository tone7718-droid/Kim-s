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
        // KBO 팀 컬러 (대략) — UI 강조용
        kia:  "#EA0029",
        ss:   "#074CA1",
        lg:   "#C30452",
        ob:   "#131230",
        kt:   "#000000",
        ssg:  "#CE0E2D",
        lt:   "#041E42",
        hh:   "#FF6600",
        nc:   "#315288",
        wo:   "#820024",
      },
    },
  },
  plugins: [],
};

export default config;
