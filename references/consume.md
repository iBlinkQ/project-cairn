# consume

Pull and cite knowledge from the configured external knowledge base into the current project.

## When

Apply the **graduation-symmetry test** before starting a piece of work (writing code, making a technical decision, debugging an error): would any conclusion this work produces — **or depends on** — qualify as a graduation candidate (see `graduation.md` → Candidate criteria)? If yes, check the INDEX first — someone may already have graduated the same kind of conclusion.

"Produces or depends on" matters: the work's own deliverable may be purely project-local (this repo's CI config file) while the reusable kernel inside it (how to structure CI caching, which pitfalls to avoid) is exactly what another project may have graduated. Test the reusable kernel of the work, not the deliverable.

Examples of applying the test (not an exhaustive list):

- Integrating an external API/SDK this project hasn't used before, where such integration experience is typically reusable → check.
- An error whose *solution shape* would be reusable — after first checking this project's own `cairn/` topic notes (the project's own solved pitfalls take precedence; only when the project has nothing does the INDEX check trigger) → check.
- A technology/architecture selection decision with no recorded conclusion in this project → check.
- The user directly asks "how should we do X" where X is a domain this project has no settled conclusion for → check.
- Configuring this repo's CI caching — the deliverable (a project-local config file) isn't reusable, but the work depends on reusable knowledge another project may have graduated → check.
- Pure project-internal detail judgments (naming a variable) — no reusable kernel anywhere in the work → don't check.

Checking is cheap (the INDEX is a title/summary list); when the test says yes, err toward checking. The precision lives at the citation step below, not here.

## How

1. Read the configured knowledge index from `.cairn/config.yaml` (`graduation.index`).
2. Read only the relevant external notes.
3. Apply the **adoption bar** before writing anything: a note earns a `cairn/Cited.md` entry only when its conclusion was adopted or adapted into the current work's concrete output — a decision made, a code approach taken, a fix applied. Checked the INDEX, opened a note, found it inapplicable or only loosely related → no entry; skip without trace. Checking is not a commitment to cite. Adoption includes **negative adoption**: a note that shaped the judgment by ruling a path out ("we didn't go down road Y because of this note") influenced the actual output and earns an entry — the bar is "influenced the concrete output," not "was copied verbatim."
4. For each note that clears the bar, add a pointer row to `cairn/Cited.md`: what was pulled, why, where it applies, and a link back to the source note. Create `cairn/Cited.md` from the template on first use.
5. Never copy the full body of an external knowledge note into the project — a copy starts rotting the day it is made. Link back and re-read the latest version when needed.
6. Update project topic notes only with project-specific conclusions or adaptations, not with wholesale duplicated knowledge-base text.

`Cited.md` is a pointer list (the knowledge body lives in the knowledge base). `cairn/Reference/` is different: it holds raw external inputs the project owns outright. Keep them separate.
