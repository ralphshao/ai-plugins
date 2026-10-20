# 14. flow credits its sources in its README

Status: accepted (#28, 2026-10-20). Supersedes ADR 1's "credit it in the
skill" consequence.

## Context

ADR 1 had each skill that adapts mattpocock/skills credit it in a line at
the top of its `SKILL.md`. Five files did: `change-body`, `tdd`,
`interview`, `retro`, and deep-review's `smell-baseline.md`.

Those lines load with the skill every time it runs and tell the model
nothing it acts on. They also fell short of the MIT License, which asks
that copies keep the copyright and permission notice; a one-line "(MIT)"
is neither. flow now adapts humanlayer/skills too, so the lines were
about to grow.

## Decision

- No file under `plugins/flow/skills/` carries an upstream credit.
- `plugins/flow/README.md` ends with a `## Credits` table: each adapted
  flow skill and the upstream skill it comes from.
- `plugins/flow/THIRD_PARTY_NOTICES.md` holds each upstream's full MIT
  notice, copyright line included. The README links it.
- A citation the model uses stays where it is used: `smell-baseline.md`
  keeps "From Fowler's *Refactoring*, ch. 3", which says what the smell
  names mean.
- An idea borrowed without its text, rewritten in flow's own words, gets a
  README row too.

Both files sit in the plugin folder, so they ship wherever the skills do,
and neither is loaded with a skill.

## Alternatives

- **Keep the line in each skill.** Rejected: context cost on every load,
  and still not the notice MIT asks for.
- **Copyright lines and LICENSE links in the README, no notices file.**
  Rejected: a link is not the notice itself.

## Consequences

- Adapting a new upstream skill means a README row and, for a new
  upstream, its notice in `THIRD_PARTY_NOTICES.md`.
