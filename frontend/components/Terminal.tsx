"use client";

import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "motion/react";
import { RotateCcw } from "lucide-react";
import { howItWorks } from "@/lib/content";
import { Cuts } from "./Cuts";

const { command, lines } = howItWorks.terminal;

type Phase = "idle" | "typing" | "streaming" | "done";

const statusColor: Record<string, string> = {
  pass: "text-[#7fd3a0]",
  partial: "text-sun",
  fail: "text-[#ff8f73]",
};

/** Types the command, then streams results. Fully static under reduced motion. */
export function Terminal() {
  const reduce = useReducedMotion();
  const ref = useRef<HTMLDivElement>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [typed, setTyped] = useState(0);
  const [shown, setShown] = useState(0);
  const [run, setRun] = useState(0);

  // Start once when scrolled into view.
  useEffect(() => {
    if (reduce) {
      setPhase("done");
      setTyped(command.length);
      setShown(lines.length);
      return;
    }
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          setPhase((p) => (p === "idle" ? "typing" : p));
          io.disconnect();
        }
      },
      { threshold: 0.4 },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [reduce, run]);

  // Typewriter
  useEffect(() => {
    if (phase !== "typing") return;
    if (typed >= command.length) {
      const t = setTimeout(() => setPhase("streaming"), 350);
      return () => clearTimeout(t);
    }
    const t = setTimeout(() => setTyped((n) => n + 1), 16 + Math.random() * 26);
    return () => clearTimeout(t);
  }, [phase, typed]);

  // Stream results
  useEffect(() => {
    if (phase !== "streaming") return;
    if (shown >= lines.length) {
      setPhase("done");
      return;
    }
    const next = lines[shown];
    const delay = next.kind === "info" ? 420 : next.kind === "done" ? 600 : 520;
    const t = setTimeout(() => setShown((n) => n + 1), delay);
    return () => clearTimeout(t);
  }, [phase, shown]);

  const replay = () => {
    setTyped(0);
    setShown(0);
    setPhase("typing");
    setRun((r) => r + 1);
  };

  return (
    <div ref={ref} className="overflow-hidden rounded-card bg-ink text-paper shadow-raised ring-1 ring-paper/10">
      <div className="flex items-center justify-between border-b border-paper/10 px-5 py-3">
        <div className="flex items-center gap-3">
          <Cuts className="text-sun" height={12} stroke={3} />
          <span className="font-mono text-[13px] text-paper/60">terminal</span>
        </div>
        {!reduce && (
          <button
            type="button"
            onClick={replay}
            disabled={phase !== "done"}
            className="inline-flex h-9 items-center gap-1.5 rounded-control px-2.5 text-[13px] font-semibold text-paper/70 transition-colors duration-200 hover:text-paper disabled:opacity-40"
            aria-label="Run again"
          >
            <RotateCcw size={14} aria-hidden="true" />
            Run again
          </button>
        )}
      </div>

      <div
        className="min-h-[300px] overflow-x-auto p-5 font-mono text-[13px] leading-[1.75] md:min-h-[332px] md:text-[14px]"
        aria-live="polite"
      >
        <div className="whitespace-pre-wrap break-all">
          <span className="text-sun">$ </span>
          <span className="text-paper">{command.slice(0, typed)}</span>
          {(phase === "idle" || phase === "typing") && (
            <span className="animate-caret inline-block h-[1.1em] w-[0.55em] translate-y-[0.2em] bg-paper/80" />
          )}
        </div>

        <ol className="mt-1">
          {lines.slice(0, shown).map((l, i) => (
            <li key={i} className="whitespace-pre-wrap break-words">
              {l.kind === "note" ? (
                <span className="text-paper/40">{l.text}</span>
              ) : l.kind === "done" ? (
                <span className="text-[#7fd3a0]">✓ {l.text}</span>
              ) : (
                <>
                  <span className="text-paper/40">→ </span>
                  <span className="text-paper/85">{l.text}</span>
                  {"status" in l && l.status ? (
                    <span className={`ml-3 font-semibold ${statusColor[l.kind] ?? "text-paper"}`}>{l.status}</span>
                  ) : null}
                </>
              )}
            </li>
          ))}
        </ol>

        {phase === "streaming" && shown < lines.length && (
          <div className="mt-2 flex items-center gap-3 text-paper/50">
            <span className="cuts-loading text-sun" aria-hidden="true" />
            <span className="text-[12px]">running</span>
          </div>
        )}
      </div>
    </div>
  );
}
