// LocalStorage-backed set of attended game IDs. One global set across all
// seasons — game IDs are already unique by date+teams.

import { useCallback, useEffect, useState } from "react";

const KEY = "kbo-attended-v1";

function readFromStorage(): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = window.localStorage.getItem(KEY);
    if (!raw) return new Set();
    const parsed = JSON.parse(raw);
    if (Array.isArray(parsed)) return new Set(parsed.filter((x) => typeof x === "string"));
  } catch {
    // fall through
  }
  return new Set();
}

function writeToStorage(set: Set<string>) {
  if (typeof window === "undefined") return;
  try {
    window.localStorage.setItem(KEY, JSON.stringify([...set]));
  } catch {
    /* quota etc — silently drop */
  }
}

export function useAttended() {
  const [attended, setAttended] = useState<Set<string>>(() => new Set());
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setAttended(readFromStorage());
    setHydrated(true);
  }, []);

  const toggle = useCallback((id: string) => {
    setAttended((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      writeToStorage(next);
      return next;
    });
  }, []);

  const clear = useCallback(() => {
    setAttended(new Set());
    writeToStorage(new Set());
  }, []);

  const exportJson = useCallback(() => {
    return JSON.stringify({ version: 1, attended: [...attended] }, null, 2);
  }, [attended]);

  const importJson = useCallback((text: string): { ok: boolean; count: number } => {
    try {
      const parsed = JSON.parse(text);
      const list = Array.isArray(parsed?.attended) ? parsed.attended : [];
      const set = new Set<string>(list.filter((x: unknown) => typeof x === "string"));
      setAttended(set);
      writeToStorage(set);
      return { ok: true, count: set.size };
    } catch {
      return { ok: false, count: 0 };
    }
  }, []);

  return { attended, toggle, clear, exportJson, importJson, hydrated };
}
