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

  const importJson = useCallback((text: string): { ok: boolean; count: number } => {
    try {
      const parsed = JSON.parse(text);
      const list = Array.isArray(parsed?.attended) ? parsed.attended : [];
      const set = new Set<string>(list.filter((x: unknown) => typeof x === "string"));
      writeToStorage(set);
      return { ok: true, count: set.size };
    } catch {
      return { ok: false, count: 0 };
    }
  }, []);

  return { attended, toggle, clear, exportJson, importJson, hydrated };
}

