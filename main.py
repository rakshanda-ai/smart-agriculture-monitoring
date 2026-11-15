"""Application entry point for Smart Agriculture Monitoring."""

from __future__ import annotations

import logging
import sys
from pathlib import Path


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from smart_agriculture_monitoring.gui import SmartAgricultureApp
else:
    from .gui import SmartAgricultureApp


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    app = SmartAgricultureApp()
    app.mainloop()


if __name__ == "__main__":
    main()
