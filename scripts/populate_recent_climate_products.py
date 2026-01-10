"""
Batch populate recent climate products (2023-2025).

This script pre-computes weekly and monthly summaries for recent years
to ensure fast response times for current queries.

Part of the hybrid compute strategy:
- Recent years (2023-2025): Pre-computed (this script)
- Historical years (1960-2022): Computed on-demand

Run after migration:
    python scripts/populate_recent_climate_products.py

Run monthly (incremental):
    python scripts/populate_recent_climate_products.py --incremental
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session_maker
from app.models.station import Station
from app.crud.products import (
    batch_populate_weekly_summaries,
    batch_populate_monthly_summaries,
)
from app.utils.logging_config import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


async def populate_station_products(
    db: AsyncSession,
    station: Station,
    start_year: int,
    end_year: int
) -> tuple[int, int]:
    """
    Populate climate products for a single station.

    Args:
        db: Database session
        station: Station instance
        start_year: Start year (inclusive)
        end_year: End year (inclusive)

    Returns:
        Tuple of (weekly_count, monthly_count)
    """
    logger.info(f"Processing station: {station.name} ({station.code})")

    # Populate weekly summaries
    weekly_count = await batch_populate_weekly_summaries(
        db, station.id, start_year, end_year
    )
    logger.info(f"  ✓ Created {weekly_count} weekly summaries")

    # Populate monthly summaries
    monthly_count = await batch_populate_monthly_summaries(
        db, station.id, start_year, end_year
    )
    logger.info(f"  ✓ Created {monthly_count} monthly summaries")

    return (weekly_count, monthly_count)


async def populate_all_stations(start_year: int, end_year: int):
    """
    Populate climate products for all stations.

    Args:
        start_year: Start year (inclusive)
        end_year: End year (inclusive)
    """
    logger.info("=" * 70)
    logger.info("GMet Climate Products - Batch Population Script")
    logger.info("=" * 70)
    logger.info(f"Period: {start_year} - {end_year}")
    logger.info("")

    async with async_session_maker() as db:
        # Get all stations
        result = await db.execute(select(Station))
        stations = result.scalars().all()

        if not stations:
            logger.error("No stations found in database!")
            return

        logger.info(f"Found {len(stations)} stations")
        logger.info("")

        total_weekly = 0
        total_monthly = 0

        for i, station in enumerate(stations, 1):
            logger.info(f"[{i}/{len(stations)}] Processing {station.name} ({station.code})")

            try:
                weekly_count, monthly_count = await populate_station_products(
                    db, station, start_year, end_year
                )

                total_weekly += weekly_count
                total_monthly += monthly_count

            except Exception as e:
                logger.error(f"  ✗ Error processing {station.code}: {str(e)}")
                continue

            logger.info("")

        logger.info("=" * 70)
        logger.info("BATCH POPULATION COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Total stations processed: {len(stations)}")
        logger.info(f"Total weekly summaries created: {total_weekly}")
        logger.info(f"Total monthly summaries created: {total_monthly}")
        logger.info("")
        logger.info("Climate products are now cached for fast API responses!")
        logger.info("=" * 70)


async def populate_current_year():
    """Populate only the current year (for incremental updates)."""
    current_year = datetime.now().year

    logger.info("=" * 70)
    logger.info("GMet Climate Products - Incremental Update")
    logger.info("=" * 70)
    logger.info(f"Updating products for year: {current_year}")
    logger.info("")

    async with async_session_maker() as db:
        # Get all stations
        result = await db.execute(select(Station))
        stations = result.scalars().all()

        logger.info(f"Found {len(stations)} stations")
        logger.info("")

        total_weekly = 0
        total_monthly = 0

        for i, station in enumerate(stations, 1):
            logger.info(f"[{i}/{len(stations)}] Updating {station.name} ({station.code})")

            try:
                weekly_count, monthly_count = await populate_station_products(
                    db, station, current_year, current_year
                )

                total_weekly += weekly_count
                total_monthly += monthly_count

            except Exception as e:
                logger.error(f"  ✗ Error: {str(e)}")
                continue

            logger.info("")

        logger.info("=" * 70)
        logger.info("INCREMENTAL UPDATE COMPLETE")
        logger.info("=" * 70)
        logger.info(f"Total weekly summaries updated: {total_weekly}")
        logger.info(f"Total monthly summaries updated: {total_monthly}")
        logger.info("=" * 70)


def main():
    """Main entry point for batch population script."""
    parser = argparse.ArgumentParser(
        description="Populate recent climate products for GMet API"
    )
    parser.add_argument(
        '--incremental',
        action='store_true',
        help='Only update current year (for monthly cron jobs)'
    )
    parser.add_argument(
        '--start-year',
        type=int,
        default=2023,
        help='Start year for full population (default: 2023)'
    )
    parser.add_argument(
        '--end-year',
        type=int,
        default=2025,
        help='End year for full population (default: 2025)'
    )

    args = parser.parse_args()

    try:
        if args.incremental:
            # Incremental mode: update current year only
            asyncio.run(populate_current_year())
        else:
            # Full mode: populate specified year range
            asyncio.run(populate_all_stations(args.start_year, args.end_year))

        logger.info("")
        logger.info("✓ Script completed successfully!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Start the API: uvicorn app.main:app --reload")
        logger.info("2. Test endpoints:")
        logger.info("   GET /api/v1/products/weekly?station_code=23024TEM&year=2024")
        logger.info("   GET /api/v1/products/monthly?station_code=23016ACC&year=2024")
        logger.info("")

    except KeyboardInterrupt:
        logger.warning("")
        logger.warning("Script interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"")
        logger.error(f"Fatal error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
