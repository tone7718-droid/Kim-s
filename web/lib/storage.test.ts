import { afterEach, describe, expect, it, vi } from "vitest";
import { importAttendanceJson, readFromStorage, writeToStorage } from "./storage";

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
