"use client";

import { useEffect, useRef, type ReactNode } from "react";
import { X } from "lucide-react";

/**
 * A native <dialog> so focus trapping, Escape and the backdrop come from the browser.
 * Closing by clicking the backdrop is supported; Escape fires `onClose` through `cancel`.
 */
export function Dialog({
  open,
  onClose,
  title,
  description,
  children,
  footer,
}: {
  open: boolean;
  onClose: () => void;
  title: string;
  description?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      className="dialog-base"
      aria-labelledby="dialog-title"
      aria-describedby={description ? "dialog-description" : undefined}
      onCancel={(e) => {
        e.preventDefault();
        onClose();
      }}
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
    >
      <div className="flex flex-col gap-4 p-6 md:p-7">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="dialog-title" className="text-heading-md text-ink">
              {title}
            </h2>
            {description ? (
              <p id="dialog-description" className="mt-1 text-small text-ink-soft">
                {description}
              </p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-full text-ink-soft hover:bg-cream hover:text-ink"
            aria-label="Close dialog"
          >
            <X size={18} aria-hidden="true" />
          </button>
        </div>
        <div>{children}</div>
        {footer ? <div className="flex flex-wrap justify-end gap-3 pt-2">{footer}</div> : null}
      </div>
    </dialog>
  );
}
