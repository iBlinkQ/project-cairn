# consume

Pull and cite knowledge from the configured external knowledge base into the current project.

## When

Before entering a new domain, debugging an external integration, or preparing work where prior cross-project knowledge may apply.

## How

1. Read the configured knowledge index from `.cairn/config.yaml` (`graduation.index`).
2. Read only the relevant external notes.
3. Add a pointer row to `cairn/Cited.md`: what was pulled, why, where it applies, and a link back to the source note. Create `cairn/Cited.md` from the template on first use.
4. Never copy the full body of an external knowledge note into the project — a copy starts rotting the day it is made. Link back and re-read the latest version when needed.
5. Update project topic notes only with project-specific conclusions or adaptations, not with wholesale duplicated knowledge-base text.

`Cited.md` is a pointer list (the knowledge body lives in the knowledge base). `cairn/Reference/` is different: it holds raw external inputs the project owns outright. Keep them separate.
