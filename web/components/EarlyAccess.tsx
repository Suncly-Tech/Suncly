"use client";

import { useState, type FormEvent } from "react";
import { Check, AlertCircle } from "lucide-react";
import { earlyAccess, site } from "@/lib/content";
import { SectionLabel } from "./SectionHeader";

type Status = "idle" | "sending" | "success" | "error";

const endpoint = process.env.NEXT_PUBLIC_SIGNUP_ENDPOINT;

export function EarlyAccess() {
  const [status, setStatus] = useState<Status>("idle");
  const [email, setEmail] = useState("");

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (status === "sending") return;

    if (!endpoint) {
      // Fallback: open the user's mail client addressed to the team.
      const subject = encodeURIComponent("Suncly early access");
      const body = encodeURIComponent(`Please add ${email} to the early-access list.`);
      window.location.href = `mailto:${site.email}?subject=${subject}&body=${body}`;
      setStatus("success");
      return;
    }

    setStatus("sending");
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, source: "suncly.com" }),
      });
      if (!res.ok) throw new Error(`status ${res.status}`);
      setStatus("success");
    } catch {
      setStatus("error");
    }
  }

  return (
    <section id="early-access" className="scroll-mt-20 bg-ink py-24 text-paper md:py-32" aria-labelledby="access-heading">
      <div className="container-site">
        <div className="grid gap-10 lg:grid-cols-2 lg:gap-16">
          <div>
            <SectionLabel tone="paper">{earlyAccess.headline.replace(/\.$/, "")}</SectionLabel>
            <h2 id="access-heading" className="mt-5 text-display-lg text-paper">
              {earlyAccess.headline}
            </h2>
            <p className="mt-6 max-w-[480px] text-body text-paper/70">{earlyAccess.body}</p>
          </div>

          <div className="lg:pt-14">
            {status === "success" ? (
              <div
                role="status"
                className="flex items-center gap-3 rounded-card bg-paper/5 p-6 ring-1 ring-paper/15"
              >
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-sun text-ink">
                  <Check size={20} strokeWidth={3} aria-hidden="true" />
                </span>
                <p className="text-body text-paper">{earlyAccess.success}</p>
              </div>
            ) : (
              <form onSubmit={onSubmit} className="flex flex-col gap-3" noValidate={false}>
                <label htmlFor="email" className="text-small font-semibold text-paper/80">
                  {earlyAccess.fieldLabel}
                </label>
                <div className="flex flex-col gap-3 sm:flex-row">
                  <input
                    id="email"
                    name="email"
                    type="email"
                    required
                    autoComplete="email"
                    inputMode="email"
                    placeholder={earlyAccess.placeholder}
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    aria-invalid={status === "error" || undefined}
                    aria-describedby={status === "error" ? "email-error" : undefined}
                    className="h-12 min-w-0 flex-1 rounded-control border border-paper/20 bg-paper/5 px-4 text-body text-paper placeholder:text-paper/40 focus:border-sun focus:outline-none focus-visible:ring-2 focus-visible:ring-sun"
                  />
                  <button
                    type="submit"
                    disabled={status === "sending"}
                    className="btn-base btn-primary disabled:opacity-60"
                  >
                    {status === "sending" ? earlyAccess.sending : earlyAccess.button}
                  </button>
                </div>
                {status === "error" && (
                  <p id="email-error" role="alert" className="flex items-center gap-2 text-small text-[#ffb09a]">
                    <AlertCircle size={16} aria-hidden="true" />
                    {earlyAccess.error}
                  </p>
                )}
              </form>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
