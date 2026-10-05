import { Notice } from "@/components/ui/Notice";
import { legal } from "@/lib/content";
import { launch } from "@/lib/launch";

/**
 * The visible draft notice on a legal page. It names exactly which facts are missing. One
 * flag, launch.legalPublished, removes it (and the noindex) when the facts exist and
 * counsel has signed off.
 */
export function DraftNotice({ page, needs, counsel = true }: { page: string; needs: string[]; counsel?: boolean }) {
  if (launch.legalPublished) return null;
  return (
    <Notice tone="warn" title={`Draft ${page}, pending ${needs.length ? "company facts and " : ""}legal review`} className="mb-10" role="status">
      {legal.draftNotice}
      {needs.length ? (
        <>
          {" "}
          Missing: {needs.join(", ")}.
        </>
      ) : null}
      {counsel ? " A qualified lawyer has not yet reviewed this text." : null}
    </Notice>
  );
}

/** A clearly marked blank inside otherwise complete text. Never a guessed value. */
export function Blank({ what }: { what: string }) {
  return <em className="blank">[{what}: {legal.pending}]</em>;
}

/** A one-line plain-English summary above a section. */
export function Summary({ children }: { children: React.ReactNode }) {
  return <p className="summary">In short: {children}</p>;
}

/** Version, effective date and change log for a legal document. */
export function DocMeta({ version, effective, changes }: { version: string; effective: string | null; changes: Array<{ date: string; note: string }> }) {
  return (
    <table tabIndex={0}>
      <tbody>
        <tr><th scope="row">Version</th><td>{version}</td></tr>
        <tr><th scope="row">Effective date</th><td>{effective ?? <Blank what="effective date, set on publication" />}</td></tr>
        <tr>
          <th scope="row">Change log</th>
          <td>
            <ul className="m-0">
              {changes.map((c) => (
                <li key={c.date + c.note}>{c.date}: {c.note}</li>
              ))}
            </ul>
          </td>
        </tr>
      </tbody>
    </table>
  );
}

export function Toc({ items }: { items: Array<{ id: string; title: string }> }) {
  return (
    <nav aria-label="Contents" className="not-prose mb-10 rounded-[12px] bg-cream-deep/60 p-5">
      <p className="text-eyebrow text-ink-soft">Contents</p>
      <ol className="mt-3 grid list-decimal gap-1 pl-5 font-sans text-[15px] text-ink sm:grid-cols-2">
        {items.map((i) => (
          <li key={i.id}>
            <a href={`#${i.id}`} className="underline-offset-4 hover:underline">
              {i.title}
            </a>
          </li>
        ))}
      </ol>
    </nav>
  );
}
