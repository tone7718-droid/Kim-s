// LocalStorage-backed set of attended game IDs. One global set across all
// seasons — game IDs are already unique by date+teams.

import { useCallback, useEffect, useState } from "react";

const KEY = "kbo-attended-v1";
const CHANGE_EVENT = "kbo-attended-change";

export function readFromStorage(): Set<string> {
  if (typeof window === "undefined") return new Set();
  const raw = window.localStorage.getItem(KEY);
  if (!raw) return new Set();
  const parsed = JSON.parse(raw);
  if (!Array.isArray(parsed) || parsed.some((x) => typeof x !== "string")) {
    throw new Error("저장된 기록을 읽지 못했어요. 기존 데이터를 지우지 말고 백업을 확인해 주세요.");
  }
  return new Set(parsed);
}

export function writeToStorage(set: Set<string>) {
  if (typeof window === "undefined") throw new Error("저장소를 사용할 수 없어요.");
  window.localStorage.setItem(KEY, JSON.stringify([...set]));
  window.dispatchEvent(new Event(CHANGE_EVENT));
}

const STORAGE_ERROR = "기록을 저장하지 못했어요. 저장 공간과 브라우저의 저장 허용 설정을 확인해 주세요.";
export type ImportResult = { ok: true; count: number; added: number } | { ok: false; count: 0; added: 0; error: string };

export function importAttendanceJson(text: string): ImportResult {
  let parsed;
  try { parsed = JSON.parse(text); } catch {
    return { ok: false, count: 0, added: 0, error: "파일 형식이 맞지 않아요." };
  }
  if (!parsed || parsed.version !== 1 || !Array.isArray(parsed.attended) ||
      parsed.attended.some((x: unknown) => typeof x !== "string")) {
    return { ok: false, count: 0, added: 0, error: "파일 형식이나 백업 버전이 맞지 않아요." };
  }
  try {
    const merged = readFromStorage();
    const before = merged.size;
    for (const id of parsed.attended) merged.add(id);
    writeToStorage(merged);
    return { ok: true, count: merged.size, added: merged.size - before };
  } catch {
    return { ok: false, count: 0, added: 0, error: STORAGE_ERROR };
  }
}

export function useAttended() {
  const [attended, setAttended] = useState<Set<string>>(() => new Set());
  const [hydrated, setHydrated] = useState(false);
  const [storageError, setStorageError] = useState<string | null>(null);

  useEffect(() => {
    const onChange = () => {
      try { setAttended(readFromStorage()); setStorageError(null); }
      catch { setStorageError("저장된 기록에 접근하지 못했어요. 브라우저 저장 설정과 백업을 확인해 주세요."); }
    };
    onChange();
    setHydrated(true);
    window.addEventListener(CHANGE_EVENT, onChange);
    window.addEventListener("storage", onChange); // cross-tab
    return () => {
      window.removeEventListener(CHANGE_EVENT, onChange);
      window.removeEventListener("storage", onChange);
    };
  }, []);

  const toggle = useCallback((id: string) => {
    try {
      const next = new Set(readFromStorage());
      if (next.has(id)) next.delete(id);
      else next.add(id);
      writeToStorage(next);
      setStorageError(null);
    } catch { setStorageError(STORAGE_ERROR); }
  }, []);

  const clear = useCallback(() => {
    try {
      writeToStorage(new Set());
      setStorageError(null);
      return true;
    } catch { setStorageError(STORAGE_ERROR); return false; }
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
    (text: string): ImportResult => {
      const result = importAttendanceJson(text);
      setStorageError(result.ok ? null : result.error);
      return result;
    },
    [],
  );

  return { attended, toggle, clear, exportJson, importJson, hydrated, storageError };
}


