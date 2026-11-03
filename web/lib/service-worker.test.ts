import { readFileSync } from "node:fs";
import vm from "node:vm";
import { describe, expect, it, vi } from "vitest";

const source = readFileSync("public/sw.js", "utf8");
function worker(status: number | "offline", cached = true) {
  const match = vi.fn(async () => cached ? new Response('{"cached":true}') : undefined);
  const put = vi.fn();
  const fetchMock = vi.fn(async () => {
    if (status === "offline") throw new TypeError("offline");
    return new Response('{"fresh":true}', {status});
  });
  const context = vm.createContext({self:{addEventListener:vi.fn()}, caches:{open:async()=>({match,put})}, fetch:fetchMock,Headers,Response});
  vm.runInContext(source,context);
  return {context,match,put};
}
describe("service worker fallback", () => {
  it.each([500,503,"offline"] as const)("uses cached data for %s", async status => {
    const w=worker(status);
    const response: Response = await vm.runInContext('networkFirst({},"data")',w.context);
    expect(response.status).toBe(200);
    expect(response.headers.get("X-KBO-Cache")).toBe("fallback");
    expect(await response.json()).toEqual({cached:true});
  });
  it("does not resurrect a missing season on a 404", async () => {
    const w=worker(404);
    expect((await vm.runInContext('networkFirst({},"data")',w.context)).status).toBe(404);
    expect(w.match).not.toHaveBeenCalled();
  });
  it("caches a successful fresh response", async () => {
    const w=worker(200);
    const response:Response=await vm.runInContext('networkFirst({},"data")',w.context);
    expect(w.put).toHaveBeenCalledOnce();
    expect(response.headers.get("X-KBO-Cache")).toBeNull();
  });
  it("returns the server error when no cache is available", async () => {
    const w=worker(503,false);
    expect((await vm.runInContext('networkFirst({},"data")',w.context)).status).toBe(503);
  });
});
