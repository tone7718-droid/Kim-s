import { afterEach, describe, expect, it, vi } from "vitest";
import { exportAttendanceJson, importAttendanceJson, readFromStorage, writeToStorage } from "./storage";

afterEach(() => vi.unstubAllGlobals());
function storage(initial: string | null = null, fail = false) {
  let raw = initial;
  const dispatchEvent = vi.fn();
  vi.stubGlobal("window", { localStorage: {
    getItem: () => raw,
    setItem: (_key: string, value: string) => { if (fail) throw new Error("QuotaExceededError"); raw = value; },
  }, dispatchEvent });
  return { read: () => raw, dispatchEvent };
}
describe("attendance persistence", () => {
  it("does not report a successful import when storage rejects the write", () => {
    const s = storage('["existing"]', true);
    expect(importAttendanceJson('{"version":1,"attended":["new"]}').ok).toBe(false);
    expect(s.read()).toBe('["existing"]');
    expect(s.dispatchEvent).not.toHaveBeenCalled();
  });
  it("merges backups without dropping existing games", () => {
    storage('["existing"]');
    expect(importAttendanceJson('{"version":1,"attended":["new","existing"]}')).toEqual({ok:true,count:2,added:1});
    expect([...readFromStorage()]).toEqual(["existing","new"]);
  });
  it("preserves data when the stored payload is corrupted", () => {
    const s = storage('{"wrong":true}');
    expect(importAttendanceJson('{"version":1,"attended":["new"]}').ok).toBe(false);
    expect(s.read()).toBe('{"wrong":true}');
  });
  it("rejects unsupported backup versions and non-string ids", () => {
    storage();
    expect(importAttendanceJson('{"version":2,"attended":[]}').ok).toBe(false);
    expect(importAttendanceJson('{"version":1,"attended":[42]}').ok).toBe(false);
  });
  it("surfaces failed clear writes", () => {
    storage('["existing"]',true);
    expect(() => writeToStorage(new Set())).toThrow();
  });
});

describe("attendance export", () => {
  it("exports stored records as an importable backup", () => {
    storage('["2026-04-01-LG-NC"]');
    const result = exportAttendanceJson(new Date("2026-11-17T00:00:00Z"));
    expect(result.ok).toBe(true);
    if (result.ok) expect(JSON.parse(result.text).attended).toEqual(["2026-04-01-LG-NC"]);
  });

  it("does not produce an empty backup from corrupted storage", () => {
    storage('{"broken":');
    expect(exportAttendanceJson()).toEqual({ ok: false, raw: '{"broken":' });
  });
});
