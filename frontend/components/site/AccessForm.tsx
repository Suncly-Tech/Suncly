"use client";

import { useState, type FormEvent } from "react";
import { Check } from "lucide-react";
import { Button } from "@/components/Button";
import { Field, Input, Textarea, describedBy } from "@/components/ui/Field";
import { Notice } from "@/components/ui/Notice";
import { accessPage, site } from "@/lib/content";

type Status = "idle" | "sending" | "success" | "error";

const endpoint = process.env.NEXT_PUBLIC_SIGNUP_ENDPOINT;

/**
 * The pilot request form. Posts { email, note, source } to NEXT_PUBLIC_SIGNUP_ENDPOINT when
 * set; otherwise opens the visitor's mail client addressed to the team. No payment details,
 * no account creation: there is no account system yet.
 */
export function AccessForm() {
  const f = accessPage.form;
  const [status, setStatus] = useState<Status>("idle");
  const [email, setEmail] = useState("");
  const [note, setNote] = useState("");
  const [emailError, setEmailError] = useState<string | null>(null);

  function validate(): boolean {
    const trimmed = email.trim();
    if (!trimmed) {
      setEmailError("Enter the work email we should write back to.");
      return false;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(trimmed)) {
      setEmailError("This does not look like an email address.");
      return false;
    }
    setEmailError(null);
    return true;
  }

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (status === "sending") return;
    if (!validate()) return;

    if (!endpoint) {
      const subject = encodeURIComponent("Suncly pilot access");
      const body = encodeURIComponent(`Please contact ${email.trim()} about pilot access.${note.trim() ? `\n\nWhat we would evaluate first: ${note.trim()}` : ""}`);
      window.location.href = `mailto:${site.email}?subject=${subject}&body=${body}`;
      setStatus("success");
      return;
    }

    setStatus("sending");
    try {
      const res = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), note: note.trim(), source: "suncly.com/access" }),
      });
      if (!res.ok) throw new Error(`status ${res.status}`);
      setStatus("success");
    } catch {
      setStatus("error");
    }
  }

  if (status === "success") {
    return (
      <div role="status" className="flex items-center gap-3 rounded-card bg-paper p-6 ring-1 ring-line">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-sun text-ink">
          <Check size={20} strokeWidth={3} aria-hidden="true" />
        </span>
        <p className="text-body text-ink">{f.success}</p>
      </div>
    );
  }

  return (
    <form onSubmit={onSubmit} noValidate className="flex flex-col gap-5 rounded-card bg-paper p-6 ring-1 ring-line md:p-8">
      <Field id="access-email" label={f.fieldLabel} error={emailError} required>
        <Input
          id="access-email"
          name="email"
          type="email"
          autoComplete="email"
          inputMode="email"
          placeholder={f.placeholder}
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          onBlur={() => email && validate()}
          aria-invalid={emailError ? true : undefined}
          aria-describedby={describedBy("access-email", false, Boolean(emailError))}
          required
        />
      </Field>
      <Field id="access-note" label={f.noteLabel} help="Optional. Helps us prepare the first evaluation.">
        <Textarea
          id="access-note"
          name="note"
          placeholder={f.notePlaceholder}
          value={note}
          onChange={(e) => setNote(e.target.value)}
          aria-describedby={describedBy("access-note", true, false)}
          rows={3}
        />
      </Field>
      {status === "error" ? (
        <Notice tone="error" role="alert">
          {f.error}
        </Notice>
      ) : null}
      <div className="flex flex-wrap items-center gap-4">
        <Button type="submit" disabled={status === "sending"}>
          {status === "sending" ? f.sending : f.button}
        </Button>
        <p className="text-[13px] text-ink-soft">No payment details are collected. We reply by email.</p>
      </div>
    </form>
  );
}
