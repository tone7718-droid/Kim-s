"use client";

import { useState } from "react";
import { useInstallState } from "@/lib/install";

export function InstallButton() {
  const state = useInstallState();
  const [showIosHelp, setShowIosHelp] = useState(false);

  if (state.mode === "installed" || state.mode === "unsupported") return null;

  const onClick = () => {
    if (state.mode === "android") {
      void state.prompt();
    } else if (state.mode === "ios") {
      setShowIosHelp(true);
    }
  };

  return (
    <>
      <button
        onClick={onClick}
        className="text-xs font-semibold px-3 py-1.5 rounded-full bg-zinc-900 text-white active:opacity-80"
        aria-label="홈 화면에 추가"
      >
        + 홈 화면에 추가
      </button>

      {showIosHelp && (
        <div
          className="fixed inset-0 z-50 bg-black/50 flex items-end sm:items-center justify-center p-4"
          onClick={() => setShowIosHelp(false)}
        >
          <div
            className="bg-white w-full max-w-sm rounded-2xl p-5 shadow-xl"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-base font-bold mb-2">iOS에서 설치하기</h2>
            <p className="text-sm text-zinc-600 mb-4">
              iOS Safari는 자동 설치를 지원하지 않아서, 두 단계만 직접 눌러주세요.
            </p>
            <ol className="space-y-3 text-sm">
              <li className="flex gap-3 items-start">
                <span className="size-6 shrink-0 rounded-full bg-zinc-900 text-white text-xs font-bold flex items-center justify-center">1</span>
                <div>
                  Safari 하단의{" "}
                  <span className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-zinc-100 text-zinc-800 font-semibold">
                    <ShareIcon /> 공유
                  </span>{" "}
                  버튼을 누르세요.
                </div>
              </li>
              <li className="flex gap-3 items-start">
                <span className="size-6 shrink-0 rounded-full bg-zinc-900 text-white text-xs font-bold flex items-center justify-center">2</span>
                <div>
                  메뉴를 아래로 스크롤해서{" "}
                  <span className="px-1.5 py-0.5 rounded bg-zinc-100 text-zinc-800 font-semibold">
                    홈 화면에 추가
                  </span>
                  를 누르고{" "}
                  <span className="px-1.5 py-0.5 rounded bg-zinc-100 text-zinc-800 font-semibold">
                    추가
                  </span>
                  를 누르면 끝!
                </div>
              </li>
            </ol>
            <button
              onClick={() => setShowIosHelp(false)}
              className="mt-5 w-full py-2.5 rounded-lg bg-zinc-900 text-white text-sm font-semibold"
            >
              알겠어요
            </button>
          </div>
        </div>
      )}
    </>
  );
}

function ShareIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M12 16V4" />
      <path d="m7 9 5-5 5 5" />
      <path d="M5 12v7a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-7" />
    </svg>
  );
}
