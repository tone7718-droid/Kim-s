// Copies data/seasons/*.json from the repo root into web/public/data/seasons/
// so Next.js can fetch them at runtime. Runs automatically before
// `next dev` and `next build` via npm lifecycle scripts.

import { existsSync, mkdirSync, cpSync, rmSync, readdirSync } from "node:fs";
import { resolve } from "node:path";

const SRC = resolve(process.cwd(), "..", "data", "seasons");
const DST = resolve(process.cwd(), "public", "data", "seasons");

if (!existsSync(SRC)) {
  console.warn(`[prepare-data] no source dir at ${SRC} — skipping`);
  process.exit(0);
}

rmSync(DST, { recursive: true, force: true });
mkdirSync(DST, { recursive: true });
cpSync(SRC, DST, { recursive: true });

const files = readdirSync(DST).filter((f) => f.endsWith(".json"));
console.log(`[prepare-data] copied ${files.length} season file(s) to public/data/seasons/`);
