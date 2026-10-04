"use client";

import { useId, useRef, type KeyboardEvent, type ReactNode } from "react";

export interface TabItem {
  id: string;
  label: ReactNode;
  count?: number;
}

/** WAI-ARIA tabs with roving focus: arrows move, Home/End jump, activation on focus. */
export function Tabs({
  items,
  value,
  onChange,
  label,
}: {
  items: TabItem[];
  value: string;
  onChange: (id: string) => void;
  label: string;
}) {
  const base = useId();
  const refs = useRef<Array<HTMLButtonElement | null>>([]);

  function onKeyDown(e: KeyboardEvent<HTMLDivElement>) {
    const index = items.findIndex((item) => item.id === value);
    let next = index;
    if (e.key === "ArrowRight") next = (index + 1) % items.length;
    else if (e.key === "ArrowLeft") next = (index - 1 + items.length) % items.length;
    else if (e.key === "Home") next = 0;
    else if (e.key === "End") next = items.length - 1;
    else return;
    e.preventDefault();
    onChange(items[next].id);
    refs.current[next]?.focus();
  }

  return (
    <div
      role="tablist"
      aria-label={label}
      onKeyDown={onKeyDown}
      className="-mb-px flex gap-1 overflow-x-auto border-b border-line"
    >
      {items.map((item, i) => {
        const selected = item.id === value;
        return (
          <button
            key={item.id}
            ref={(el) => {
              refs.current[i] = el;
            }}
            role="tab"
            id={`${base}-tab-${item.id}`}
            aria-selected={selected}
            aria-controls={`${base}-panel-${item.id}`}
            tabIndex={selected ? 0 : -1}
            type="button"
            onClick={() => onChange(item.id)}
            className={`inline-flex min-h-11 shrink-0 items-center gap-2 border-b-2 px-3 text-[14px] font-semibold transition-colors ${
              selected
                ? "border-ink text-ink"
                : "border-transparent text-ink-soft hover:border-line-strong hover:text-ink"
            }`}
          >
            {item.label}
            {item.count !== undefined ? (
              <span className="rounded-full bg-cream-deep px-1.5 py-0.5 font-mono text-[11px] text-ink-soft">
                {item.count}
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}

export function TabPanel({
  id,
  active,
  children,
  className = "",
}: {
  id: string;
  active: boolean;
  children: ReactNode;
  className?: string;
}) {
  if (!active) return null;
  return (
    <div role="tabpanel" id={`panel-${id}`} tabIndex={0} className={`pt-6 focus:outline-none ${className}`}>
      {children}
    </div>
  );
}
