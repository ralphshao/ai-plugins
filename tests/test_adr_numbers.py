"""docs/adr/ numbers: one file per number, no gaps."""

from conftest import REPO_ROOT


def test_adr_numbers_are_unique_and_contiguous():
    names = sorted(p.name for p in (REPO_ROOT / "docs" / "adr").glob("*.md"))
    assert names, "docs/adr has no records"
    for name in names:
        assert name[:4].isdigit() and name[4] == "-", f"{name}: want NNNN-title.md"
    # Sorted names must count 1, 2, 3...: a duplicate or a gap breaks the match.
    numbers = [int(name[:4]) for name in names]
    assert numbers == list(range(1, len(names) + 1)), names
