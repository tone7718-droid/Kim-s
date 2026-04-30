"use client";

import { TEAMS } from "@/lib/teams";

interface Props {
  selected: string | null;
  onSelect: (code: string) => void;
}

export function TeamPicker({ selected, onSelect }: Props) {
  return (
    <div className="grid grid-cols-5 gap-2">
      {TEAMS.map((t) => {
        const isSel = t.code === selected;
        return (
          <button
            key={t.code}
            onClick={() => onSelect(t.code)}
            className={[
              "rounded-lg py-3 text-sm font-bold tracking-tight transition",
              t.colorClass,
              t.textClass,
              isSel ? "ring-2 ring-offset-2 ring-offset-white ring-zinc-900 scale-[1.02]" : "opacity-80 hover:opacity-100",
            ].join(" ")}
            aria-pressed={isSel}
          >
            {t.name}
          </button>
        );
      })}
    </div>
  );
}
