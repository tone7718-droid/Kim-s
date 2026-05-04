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
              "relative aspect-square rounded-lg overflow-hidden bg-white",
              "border-[3px] transition-all",
              isSel ? "scale-[1.04] shadow-md" : "opacity-85 hover:opacity-100",
            ].join(" ")}
            // Border picks up each team's brand color when selected so
            // it's clear which team is active without adding a separate
            // accent element. Using inline style because Tailwind can't
            // generate per-team border colors at build time.
            style={{
              borderColor: isSel ? t.color : "rgb(228 228 231)" /* zinc-200 */,
            }}
            aria-pressed={isSel}
            aria-label={t.fullName}
            title={t.fullName}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={`/teams/${t.code.toLowerCase()}.png`}
              alt={t.name}
              // object-contain keeps non-square logos intact (no
              // stretching, no cropping) and the padding gives a small
              // breathing margin inside the tile.
              className="absolute inset-0 size-full object-contain p-1.5"
              loading="lazy"
              decoding="async"
            />
          </button>
        );
      })}
    </div>
  );
}
