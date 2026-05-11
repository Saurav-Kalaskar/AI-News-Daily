"""
AI News Daily - Main entry point.
Runs 3-stage pipeline: Collection → Synthesis → Delivery.
"""
import logging

from settings import Settings
from collect import collect
from synthesize import synthesize
from deliver import deliver

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def main() -> None:
    log.info("=" * 50)
    log.info("AI News Daily starting")
    log.info("=" * 50)

    settings = Settings()

    # Stage 1: Collection
    log.info("--- Stage 1: Collection ---")
    stories = collect(settings)
    if not stories:
        log.warning("No new stories. Exiting.")
        return
    log.info(f"Collected {len(stories)} new stories")

    # Stage 2: Synthesis
    log.info("--- Stage 2: Synthesis ---")
    brief = synthesize(settings, stories)

    # Stage 3: Delivery
    log.info("--- Stage 3: Delivery ---")
    deliver(settings, brief, stories)

    log.info("AI News Daily done.")


if __name__ == "__main__":
    main()