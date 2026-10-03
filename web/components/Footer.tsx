import Link from "next/link";
import { Logo } from "./Logo";
import { Cuts } from "./Cuts";
import { footer, site } from "@/lib/content";

export function Footer() {
  return (
    <footer className="bg-ink text-paper">
      <div className="container-site py-16 md:py-20">
        <div className="grid gap-12 lg:grid-cols-[1.4fr_repeat(4,1fr)] lg:gap-8">
          <div className="max-w-xs">
            <Logo tone="paper" />
            <p className="mt-5 text-body text-paper/70">{site.mission}</p>
          </div>

          {footer.groups.map((group) => (
            <div key={group.title}>
              <h2 className="text-small font-semibold uppercase tracking-[0.08em] text-paper/60">
                {group.title}
              </h2>
              <ul className="mt-3 flex flex-col gap-1.5">
                {group.links.map((link) => (
                  <li key={link.label} className="text-[15px]">
                    {link.href ? (
                      <Link
                        href={link.href}
                        className="inline-block py-1 text-paper/85 transition-colors duration-200 hover:text-sun"
                      >
                        {link.label}
                      </Link>
                    ) : "plain" in link && link.plain ? (
                      <span className="text-paper/85">{link.label}</span>
                    ) : (
                      <span className="inline-flex items-center gap-2 text-paper/55">
                        {link.label}
                        <span className="rounded-full border border-paper/20 px-2 py-0.5 text-[11px] font-semibold uppercase tracking-[0.06em] text-paper/55">
                          {footer.coming}
                        </span>
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-16 flex flex-col gap-4 border-t border-paper/10 pt-8 text-small text-paper/60 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3">
            <Cuts className="text-sun" height={12} stroke={3} />
            <span>{site.city}</span>
          </div>
          <span>{site.copyright}</span>
        </div>
      </div>
    </footer>
  );
}
