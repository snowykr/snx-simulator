from __future__ import annotations

import argparse
import sys
from pathlib import Path

from snx.runner import run_program_from_file

PROG_NAME = "snx"
DESCRIPTION = "SN/X assembly simulator"
EPILOG = """\
Examples:
  snx sample.s
  snx ./examples/fib.s
  snx ~/snx-programs/demo.s
"""


def main() -> int:
    parser = argparse.ArgumentParser(
        prog=PROG_NAME,
        description=DESCRIPTION,
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "path",
        metavar="PATH",
        type=Path,
        help="path to an SN/X assembly source file (.s)",
    )

    args = parser.parse_args()
    return run_program_from_file(args.path)


if __name__ == "__main__":
    sys.exit(main())
