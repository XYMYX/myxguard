"""Allow ``python -m myxguard``."""

from myxguard.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
