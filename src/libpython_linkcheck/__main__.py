"""Command line: report ELF objects whose own DT_NEEDED entries name libpython.

Exit status: 0 if no file links libpython, 1 if at least one does, 2 if any
file could not be read or is not a valid ELF object.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from ._elf import ELFError, libpython_dependencies


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m libpython_linkcheck",
        description=(
            "Report ELF shared objects (e.g. extension modules) whose own DT_NEEDED "
            "entries name libpython. Exit status: 0 none found, 1 found, 2 error."
        ),
    )
    parser.add_argument("files", nargs="+", metavar="FILE", help="ELF object to inspect")
    args = parser.parse_args(argv)

    found = error = False
    for path in args.files:
        try:
            needed = libpython_dependencies(path)
        except (OSError, ELFError) as e:
            print(f"{path}: error: {e}", file=sys.stderr)
            error = True
            continue
        if needed:
            print(f"{path}: DT_NEEDED {', '.join(needed)}")
            found = True
    return 2 if error else 1 if found else 0


if __name__ == "__main__":
    sys.exit(main())
