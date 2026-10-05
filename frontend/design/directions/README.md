# Art direction: three quick drafts

**Chosen on 2026-10-05: A, Daylight, with B's restrained linework for hatches and diagrams.** The drafts below are kept as the record of the choice; the built site is the reference now.

Stop two of the redesign. Three directions, each as a static draft page showing the hero
and one representative lower section (10, Suncly Data), shot at 1440 and 390 px. Open the
HTML files in a browser, or look at `board.png` and the `shots/` folder. All three obey
brief sections 4.3 to 4.8: one sun, shadows and hatches at the brand angle (18.4°), no
blue, no score, the sun mark untouched.

What is shared by all three: paper `#FAF7F0`, ink `#1B1814`, gold `#F2C14E`, amber and
ember for depth; Newsreader for display and lead text (weight 390, optical size on);
JetBrains Mono for labels, status lines and captions; the same proposed copy from brief
section 5 (not yet sourced in `CONTENT.md`; that happens when a direction is chosen); the
Works-with row in its "none verified" state; the traced wordmark in the lockup.

| | A, Daylight | B, Instrument | C, Print |
| --- | --- | --- | --- |
| File | `a-daylight.html` | `b-instrument.html` | `c-print.html` |
| Idea | The still-life world: simple forms under a low sun, long shadows, the wrong shadow as the story | The same idea drawn: engraved hairlines in ink and brass, a sundial's vocabulary, hatched shadows | Almost no imagery: large type, paper grain, blind embossing, the seal |
| Interface sans | Figtree | Hanken Grotesk | Figtree |
| Hero picture | "Two cards" as a flat SVG study with shadow gradients and grain, standing in for a rendered still | "Two cards" as linework: outlined cards, hatched shadows, hour lines from a drawn sun, dimension marks | No picture: the headline at display size with "Then" in italic, and the seal blind-embossed as a specimen |
| Data picture | "The aperture" as a dark last-light plate inside the pale section | "The aperture" as an isometric line drawing with a ruled fan of light | No picture: the three facts set large as a numbered list with hairlines |
| Buttons | Gold pill | Gold rectangle, 2 px radius | Ink pill, underlined ghost link |
| Footer banner (not drafted; proposed treatment) | Ivory wordmark on dusk, lit from the mark's side by a gold edge light; hairline horizon | Wordmark as an engraved outline on dusk with brass hairlines, the ™ drawn as part of the engraving | Wordmark blind-embossed in paper at monumental scale; the dusk comes only from a warm gradient at the page foot |
| Rationale | Light is evidence, literally: what the sun shows is in the light, what it does not is shadow. The pictures carry the brand and the page needs few words. | Keeps the idea and removes the rendering risk: linework is reproducible in SVG at any size, prints well, and reads as instrument and measurement. | The most bookish and the cheapest to build. Typography and paper alone; the seal is the one object. Closest to the Claude feeling. |
| Main risk | Picture quality. Without an image generator the stills come from code; the drafts show flat studies and the finals need a path-traced render or a commission. | Can look thin or diagrammatic, and the hatched shadow is close to a chart. Needs restraint in every section or it becomes a technical manual. | Without pictures the page must be short and the type perfect; at phone width it is a column of text, and the brand has less to own than the other two. |
| Phone | Picture stacks under the copy and still reads; caption wraps below | Drawing stacks and reads, slightly small | Seal under the copy; the big facts list works well |

## Recommendation

Ship **A, Daylight**, with B's linework kept as the vocabulary for diagrams, hatches and
the "not tested" language inside A. The drafts show why: A is the only one where a
stranger could name the brand with the logo hidden, and the one-sun idea does the
explaining before any word is read. Its risk is real but bounded: the forms are planes,
boxes and discs, so a small path tracer in headless Chromium can render them with true
shadows and grain, and if the renders fall short the layout holds with the flat studies
you see here while a still is commissioned. C is the fallback if the pictures cannot be
made to editorial quality: everything in C is already in A's typography.

Sans side by side: Figtree (A and C) and Hanken Grotesk (B) are both fine at interface
sizes. Figtree sits a little rounder and friendlier next to Newsreader; Hanken Grotesk is
a touch more neutral and narrower, which helps the status line and the Works-with row
fit at phone width. Either beats Manrope's geometric width here. Recommendation: Figtree
with A, Hanken Grotesk with B.

## The wordmark trace

`../wordmark/`: `wordmark-trace.svg` (the six letters, six closed outlines, from
`assets/suncly-black.png` through potrace at a 128 luminance threshold), `mark-trace.svg`
(the yellow mark from the same file, three pieces) and `lockup-trace.svg` (both). The PNGs
beside them are renders for review. Note: the mark in the PNG lockup extends its two cut
bands past the circle as stripes; `public/mark.svg` is a plain circle with two cuts. The
site keeps `mark.svg` as the mark (brief 4.3) and the traced lockup for the nav and
banner, unless you say the stripes version is the current mark.

## Not in these drafts

Final artwork, the badge, the other sections, motion, and the legal drafting wait for the
chosen direction. The pictures here are flat SVG studies made quickly; the words
"Specimen" and "draft" are on the pages. Network access did not change since stop one,
so the reference sites still could not be opened in a browser; the drafts rest on your
notes in brief 4.2 and on the two reachable pages (claude.com, anthropic.com).

## Files

- `base.css`, `a-daylight.html`, `b-instrument.html`, `c-print.html`: the drafts.
- `fonts/`: full variable TTFs for the drafts only (OFL); the site will ship latin subsets.
- `shoot.mjs`: `node design/directions/shoot.mjs` from `frontend/` writes `shots/` and `board.png`
  with the installed Chromium.
