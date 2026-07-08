// LocalStorage-backed set of attended game IDs. One global set across all
// seasons — game IDs are already unique by date+teams.

import { useCallback, useEffect, useState } from "react";

const KEY = "kbo-attended-v1";
const CHANGE_EVENT = "kbo-attended-change";

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
    window.dispatchEvent(new Event(CHANGE_EVENT));
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
    const onChange = () => setAttended(readFromStorage());
    window.addEventListener(CHANGE_EVENT, onChange);
    window.addEventListener("storage", onChange); // cross-tab
    return () => {
      window.removeEventListener(CHANGE_EVENT, onChange);
      window.removeEventListener("storage", onChange);
    };
  }, []);

  const toggle = useCallback((id: string) => {
    const next = new Set(readFromStorage());
    if (next.has(id)) next.delete(id);
    else next.add(id);
    writeToStorage(next);
  }, []);

  const clear = useCallback(() => {
    writeToStorage(new Set());
  }, []);

  const exportJson = useCallback(() => {
    return JSON.stringify(
      { version: 1, exportedAt: new Date().toISOString(), attended: [...readFromStorage()] },
      null,
      2,
    );
  }, []);

  // Merge (union) the imported IDs into whatever is already stored rather
  // than replacing. Attendance is a set of games you went to, so a union
  // never loses a record — importing an older backup can only add games,
  // not silently drop ones you checked since. A file that parses but has
  // no `attended` array is rejected (returns ok:false) instead of being
  // treated as an empty set, which would otherwise wipe all records.
  const importJson = useCallback(
    (text: string): { ok: boolean; count: number; added: number } => {
      try {
        const parsed = JSON.parse(text);
        if (!parsed || !Array.isArray(parsed.attended)) {
          return { ok: false, count: 0, added: 0 };
        }
        const incoming = parsed.attended.filter(
          (x: unknown): x is string => typeof x === "string",
        );
        const merged = new Set(readFromStorage());
        const before = merged.size;
        for (const id of incoming) merged.add(id);
        writeToStorage(merged);
        return { ok: true, count: merged.size, added: merged.size - before };
      } catch {
        return { ok: false, count: 0, added: 0 };
      }
    },
    [],
  );

  return { attended, toggle, clear, exportJson, importJson, hydrated };
}

