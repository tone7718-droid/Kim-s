"use client";

import { useRef, useState } from "react";
import { useAttended } from "@/lib/storage";

export function SettingsMenu() {
  const [open, setOpen] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const { attended, exportJson, importJson, clear } = useAttended();

  function flash(text: string) {
    setMsg(text);
    window.setTimeout(() => setMsg(null), 2500);
  }

  function handleExport() {
    const blob = new Blob([exportJson()], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `kbo-attendance-${new Date().toISOString().slice(0, 10)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    flash(`내보냈어요 (${attended.size}경기)`);
  }

  function handleImportClick() {
    fileRef.current?.click();
  }

  function handleFileChosen(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = ""; // reset so the same file can be re-chosen
    if (!file) return;
    file.text().then((text) => {
      const result = importJson(text);
      flash(result.ok ? `불러왔어요 (${result.count}경기)` : "파일 형식이 맞지 않아요.");
    });
  }

  function handleClear() {
    if (!window.confirm(`정말 ${attended.size}개 직관 기록을 모두 지울까요?`)) return;
    clear();
    flash("모두 지웠어요.");
  }

  return (
    <>
      <button
        onClick={() => setOpen(true)}
        aria-label="설정"
        className="size-8 rounded-full bg-zinc-200 text-zinc-700 active:opacity-70 flex items-center justify-center"
      >
        <GearIcon />
      </button>

      {open && (
        <div
          className="fixed inset-0 z-50 bg-black/50 flex items-end sm:items-center justify-center p-4"
          onClick={() => setOpen(false)}
        >
          <div
            className="bg-white w-full max-w-sm rounded-2xl p-5 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-baseline justify-between mb-3">
              <h2 className="text-base font-bold">설정</h2>
              <span className="text-xs text-zinc-500 tabular-nums">
                현재 {attended.size}경기 기록됨
              </span>
            </div>

            <p className="text-xs text-zinc-500 mb-4 leading-relaxed">
              직관 기록은 이 기기의 브라우저에만 저장돼요. 폰을 바꾸거나 브라우저
              데이터를 지울 예정이라면 미리 내보내두세요.
            </p>

            <div className="space-y-2">
              <button
                onClick={handleExport}
                className="w-full py-3 rounded-lg bg-zinc-900 text-white text-sm font-semibold"
              >
                내보내기 (JSON 다운로드)
              </button>
              <button
                onClick={handleImportClick}
                className="w-full py-3 rounded-lg bg-zinc-200 text-zinc-800 text-sm font-semibold"
              >
                불러오기 (JSON 파일 선택)
              </button>
              <input
                ref={fileRef}
                type="file"
                accept="application/json,.json"
                onChange={handleFileChosen}
                hidden
              />
              <button
                onClick={handleClear}
                className="w-full py-3 rounded-lg text-rose-600 text-sm font-semibold"
              >
                모두 지우기
              </button>
            </div>

            {msg && (
              <div className="mt-3 text-center text-xs text-emerald-700 bg-emerald-50 py-2 rounded-lg">
                {msg}
              </div>
            )}

            <button
              onClick={() => setOpen(false)}
              className="mt-4 w-full py-2.5 rounded-lg text-zinc-500 text-sm"
            >
              닫기
            </button>
          </div>
        </div>
      )}
    </>
  );
}

function GearIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="12" cy="12" r="3" />
      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 1 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 1 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 1 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 1 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 1 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 1 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 1 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 1 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z" />
    </svg>
  );
}
