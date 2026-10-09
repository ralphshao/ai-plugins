# Smell baseline

From Fowler's *Refactoring*, ch. 3; list adapted from mattpocock/skills (MIT).
Report a smell as a Readability or Simplification finding labelled
"possible <smell>", never as a hard violation, and drop it where a
documented repo standard endorses the pattern.

- Mysterious Name: the name doesn't reveal what it does or holds.
- Duplicated Code: the same logic shape in more than one hunk or file.
- Feature Envy: a function that uses another object's data more than its own.
- Data Clumps: the same few fields or params always travel together.
- Primitive Obsession: a string or number standing in for a domain concept.
- Repeated Switches: the same switch or if-cascade on the same type in several places.
- Shotgun Surgery: one logical change forces scattered edits across many files.
- Divergent Change: one module edited for several unrelated reasons.
- Speculative Generality: abstraction, parameters, or hooks no requirement asks for.
- Message Chains: long `a.b().c().d()` walks the caller shouldn't depend on.
- Middle Man: a function or class that mostly delegates onward.
- Refused Bequest: a subclass that ignores or overrides most of what it inherits.
