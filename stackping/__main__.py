"""Allow running stackping as a module: python -m stackping."""

import sys

from stackping.cli import main

if __name__ == "__main__":
    sys.exit(main())
