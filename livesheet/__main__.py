"""Run LiveSheet: ``python -m livesheet [file.lsheet]``."""

import sys


def main() -> int:
    from .gui.main_window import run

    return run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
