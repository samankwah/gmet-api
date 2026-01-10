"""
Compute WMO 1991-2020 climate normals for all stations.

This script computes 30-year climate normals following WMO standards:
- Monthly normals (12 per station)
- Dekadal normals (36 per station)
- Seasonal normals (4 per station)
- Annual normals (1 per station)

Total: 53 normals per station

Usage:
    python scripts/compute_climate_normals.py
    python scripts/compute_climate_normals.py --station-code 04003NAV
    python scripts/compute_climate_normals.py --period-start 1991 --period-end 2020
"""

import asyncio
import sys
import argparse
import statistics
from pathlib import Path
from datetime import date
from typing import Optional, Dict, List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.station import Station
from app.models.daily_summary import DailySummary
from app.models.climate_normal import ClimateNormal
from app.utils.logging_config import setup_logging, get_logger

# Setup logging
setup_logging()
logger = get_logger(__name__)


def is_leap_year(year: int) -> bool:
    """Check if year is a leap year."""
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def calculate_data_quality(
    yearly_values: List[Optional[float]],
    expected_years: int = 30
) -> Tuple[int, float]:
    """
    Calculate data quality metrics for climate normal.

    Args:
        yearly_values: List of values (one per year), None if year missing
        expected_years: Expected number of years (30 for WMO standard)

    Returns:
        (years_with_data, data_completeness_percent)
    """
    years_with_data = sum(1 for v in yearly_values if v is not None)
    completeness = (years_with_data / expected_years) * 100 if expected_years > 0 else 0
    return (years_with_data, round(completeness, 1))


def calculate_normal_and_std(
    values: List[float]
) -> Tuple[Optional[float], Optional[float]]:
    """
    Calculate mean and standard deviation for climate normal.

    Uses unbiased estimator (n-1) for standard deviation.

    Args:
        values: List of valid yearly values (None values already filtered)

    Returns:
        (normal_mean, standard_deviation)
    """
    if len(values) == 0:
        return (None, None)

    mean = statistics.mean(values)
    std = statistics.stdev(values) if len(values) > 1 else 0.0

    return (round(mean, 1), round(std, 1))


async def compute_monthly_normal(
    db: AsyncSession,
    station_id: int,
    month: int,
    period_start: int = 1991,
    period_end: int = 2020,
    min_years_required: int = 20
) -> Optional[Dict]:
    """
    Compute 30-year monthly climate normal for a station.

    Process:
    1. Query daily_summaries for all instances of this month in 1991-2020
    2. Group by year, aggregate to monthly values
    3. Calculate mean and std across 30 years
    4. Track data quality (years_with_data, completeness)
    5. Require minimum 20/30 years (67% WMO threshold)

    Args:
        db: Database session
        station_id: Station ID
        month: Month number (1-12)
        period_start: Start year (default: 1991)
        period_end: End year (default: 2020)
        min_years_required: Minimum years needed (default: 20)

    Returns:
        Dictionary with normal values or None if insufficient data
    """
    # Determine days in month
    days_in_month = {
        1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30,
        7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31
    }

    # Collect yearly values
    rainfall_yearly = []
    tmax_yearly = []
    tmin_yearly = []
    sunshine_yearly = []

    expected_years = period_end - period_start + 1  # 30 years

    for year in range(period_start, period_end + 1):
        # Get start and end dates for this month in this year
        start_date = date(year, month, 1)

        # Handle February leap years
        if month == 2:
            last_day = 29 if is_leap_year(year) else 28
        else:
            last_day = days_in_month[month]

        end_date = date(year, month, last_day)

        # Query daily data for this month
        result = await db.execute(
            select(DailySummary).where(
                and_(
                    DailySummary.station_id == station_id,
                    DailySummary.date >= start_date,
                    DailySummary.date <= end_date
                )
            )
        )
        daily_data = result.scalars().all()

        # Check data completeness (need at least 21 days for valid month)
        if len(daily_data) >= 21:
            # Aggregate monthly values
            rainfall_values = [d.rainfall_total for d in daily_data if d.rainfall_total is not None]
            tmax_values = [d.temp_max for d in daily_data if d.temp_max is not None]
            tmin_values = [d.temp_min for d in daily_data if d.temp_min is not None]
            sunshine_values = [d.sunshine_hours for d in daily_data if d.sunshine_hours is not None]

            # Monthly aggregates (following WMO rules)
            rainfall_monthly = sum(rainfall_values) if rainfall_values else None
            tmax_monthly = statistics.mean(tmax_values) if tmax_values else None
            tmin_monthly = statistics.mean(tmin_values) if tmin_values else None
            sunshine_monthly = sum(sunshine_values) if sunshine_values else None

            rainfall_yearly.append(rainfall_monthly)
            tmax_yearly.append(tmax_monthly)
            tmin_yearly.append(tmin_monthly)
            sunshine_yearly.append(sunshine_monthly)
        else:
            # Insufficient data for this year
            rainfall_yearly.append(None)
            tmax_yearly.append(None)
            tmin_yearly.append(None)
            sunshine_yearly.append(None)

    # Calculate data quality
    years_with_data, completeness = calculate_data_quality(rainfall_yearly, expected_years)

    # Check minimum threshold
    if years_with_data < min_years_required:
        logger.warning(
            f"Station {station_id}, month {month}: Only {years_with_data}/{expected_years} "
            f"years available (minimum {min_years_required} required)"
        )
        return None

    # Calculate normals and standard deviations
    rainfall_normal, rainfall_std = calculate_normal_and_std(
        [v for v in rainfall_yearly if v is not None]
    )
    tmax_normal, tmax_std = calculate_normal_and_std(
        [v for v in tmax_yearly if v is not None]
    )
    tmin_normal, tmin_std = calculate_normal_and_std(
        [v for v in tmin_yearly if v is not None]
    )
    sunshine_normal, sunshine_std = calculate_normal_and_std(
        [v for v in sunshine_yearly if v is not None]
    )

    # Calculate mean temperature normal
    temp_mean_values = []
    for tmax, tmin in zip(tmax_yearly, tmin_yearly):
        if tmax is not None and tmin is not None:
            temp_mean_values.append((tmax + tmin) / 2)

    temp_mean_normal, temp_std = calculate_normal_and_std(temp_mean_values)

    return {
        'station_id': station_id,
        'normal_period_start': period_start,
        'normal_period_end': period_end,
        'timescale': 'monthly',
        'month': month,
        'dekad': None,
        'season': None,
        'rainfall_normal': rainfall_normal,
        'rainfall_std': rainfall_std,
        'temp_max_normal': tmax_normal,
        'temp_min_normal': tmin_normal,
        'temp_mean_normal': temp_mean_normal,
        'temp_std': temp_std,
        'sunshine_normal': sunshine_normal,
        'years_with_data': years_with_data,
        'data_completeness_percent': completeness
    }


async def compute_dekadal_normal(
    db: AsyncSession,
    station_id: int,
    month: int,
    dekad: int,
    period_start: int = 1991,
    period_end: int = 2020,
    min_years_required: int = 20
) -> Optional[Dict]:
    """
    Compute 30-year dekadal climate normal.

    Dekads are 10-day periods:
    - Dekad 1: Days 1-10
    - Dekad 2: Days 11-20
    - Dekad 3: Days 21-end of month

    Args:
        db: Database session
        station_id: Station ID
        month: Month number (1-12)
        dekad: Dekad number (1-3)
        period_start: Start year (default: 1991)
        period_end: End year (default: 2020)
        min_years_required: Minimum years needed (default: 20)

    Returns:
        Dictionary with normal values or None if insufficient data
    """
    # Determine dekad date range
    days_in_month = {
        1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30,
        7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31
    }

    if dekad == 1:
        start_day, end_day = 1, 10
    elif dekad == 2:
        start_day, end_day = 11, 20
    elif dekad == 3:
        start_day = 21
        end_day = days_in_month[month]  # End of month
    else:
        raise ValueError(f"Invalid dekad: {dekad}")

    # Collect yearly values
    rainfall_yearly = []
    tmax_yearly = []
    tmin_yearly = []
    sunshine_yearly = []

    expected_years = period_end - period_start + 1

    for year in range(period_start, period_end + 1):
        # Adjust end day for February
        if month == 2 and dekad == 3:
            actual_end_day = 29 if is_leap_year(year) else 28
        else:
            actual_end_day = end_day

        start_date = date(year, month, start_day)
        end_date = date(year, month, actual_end_day)

        # Query daily data for this dekad
        result = await db.execute(
            select(DailySummary).where(
                and_(
                    DailySummary.station_id == station_id,
                    DailySummary.date >= start_date,
                    DailySummary.date <= end_date
                )
            )
        )
        daily_data = result.scalars().all()

        # Check data completeness (need at least 7 days for valid dekad)
        if len(daily_data) >= 7:
            # Aggregate dekadal values
            rainfall_values = [d.rainfall_total for d in daily_data if d.rainfall_total is not None]
            tmax_values = [d.temp_max for d in daily_data if d.temp_max is not None]
            tmin_values = [d.temp_min for d in daily_data if d.temp_min is not None]
            sunshine_values = [d.sunshine_hours for d in daily_data if d.sunshine_hours is not None]

            rainfall_dekadal = sum(rainfall_values) if rainfall_values else None
            tmax_dekadal = statistics.mean(tmax_values) if tmax_values else None
            tmin_dekadal = statistics.mean(tmin_values) if tmin_values else None
            sunshine_dekadal = sum(sunshine_values) if sunshine_values else None

            rainfall_yearly.append(rainfall_dekadal)
            tmax_yearly.append(tmax_dekadal)
            tmin_yearly.append(tmin_dekadal)
            sunshine_yearly.append(sunshine_dekadal)
        else:
            rainfall_yearly.append(None)
            tmax_yearly.append(None)
            tmin_yearly.append(None)
            sunshine_yearly.append(None)

    # Calculate data quality
    years_with_data, completeness = calculate_data_quality(rainfall_yearly, expected_years)

    if years_with_data < min_years_required:
        return None

    # Calculate normals
    rainfall_normal, rainfall_std = calculate_normal_and_std(
        [v for v in rainfall_yearly if v is not None]
    )
    tmax_normal, tmax_std = calculate_normal_and_std(
        [v for v in tmax_yearly if v is not None]
    )
    tmin_normal, tmin_std = calculate_normal_and_std(
        [v for v in tmin_yearly if v is not None]
    )
    sunshine_normal, sunshine_std = calculate_normal_and_std(
        [v for v in sunshine_yearly if v is not None]
    )

    temp_mean_values = []
    for tmax, tmin in zip(tmax_yearly, tmin_yearly):
        if tmax is not None and tmin is not None:
            temp_mean_values.append((tmax + tmin) / 2)

    temp_mean_normal, temp_std = calculate_normal_and_std(temp_mean_values)

    return {
        'station_id': station_id,
        'normal_period_start': period_start,
        'normal_period_end': period_end,
        'timescale': 'dekadal',
        'month': month,
        'dekad': dekad,
        'season': None,
        'rainfall_normal': rainfall_normal,
        'rainfall_std': rainfall_std,
        'temp_max_normal': tmax_normal,
        'temp_min_normal': tmin_normal,
        'temp_mean_normal': temp_mean_normal,
        'temp_std': temp_std,
        'sunshine_normal': sunshine_normal,
        'years_with_data': years_with_data,
        'data_completeness_percent': completeness
    }


async def compute_seasonal_normal(
    db: AsyncSession,
    station_id: int,
    season: str,
    period_start: int = 1991,
    period_end: int = 2020,
    min_years_required: int = 20
) -> Optional[Dict]:
    """
    Compute 30-year seasonal climate normal.

    Ghana seasons:
    - MAM (March-April-May): Major rainy season
    - JJA (June-July-August): Minor rainy season
    - SON (September-October-November): Post-rainy/transition
    - DJF (December-January-February): Dry season/Harmattan

    Args:
        db: Database session
        station_id: Station ID
        season: Season code ('MAM', 'JJA', 'SON', 'DJF')
        period_start: Start year (default: 1991)
        period_end: End year (default: 2020)
        min_years_required: Minimum years needed (default: 20)

    Returns:
        Dictionary with normal values or None if insufficient data
    """
    # Collect yearly values
    rainfall_yearly = []
    tmax_yearly = []
    tmin_yearly = []
    sunshine_yearly = []

    expected_years = period_end - period_start + 1

    for year in range(period_start, period_end + 1):
        # Get season date range
        if season == 'MAM':
            start_date = date(year, 3, 1)
            end_date = date(year, 5, 31)
        elif season == 'JJA':
            start_date = date(year, 6, 1)
            end_date = date(year, 8, 31)
        elif season == 'SON':
            start_date = date(year, 9, 1)
            end_date = date(year, 11, 30)
        elif season == 'DJF':
            start_date = date(year, 12, 1)
            end_date = date(year + 1, 2, 28 if not is_leap_year(year + 1) else 29)
        else:
            raise ValueError(f"Invalid season: {season}")

        # Query daily data for this season
        result = await db.execute(
            select(DailySummary).where(
                and_(
                    DailySummary.station_id == station_id,
                    DailySummary.date >= start_date,
                    DailySummary.date <= end_date
                )
            )
        )
        daily_data = result.scalars().all()

        # Check data completeness (need at least 63 days for valid season - 70%)
        if len(daily_data) >= 63:
            # Aggregate seasonal values
            rainfall_values = [d.rainfall_total for d in daily_data if d.rainfall_total is not None]
            tmax_values = [d.temp_max for d in daily_data if d.temp_max is not None]
            tmin_values = [d.temp_min for d in daily_data if d.temp_min is not None]
            sunshine_values = [d.sunshine_hours for d in daily_data if d.sunshine_hours is not None]

            rainfall_seasonal = sum(rainfall_values) if rainfall_values else None
            tmax_seasonal = statistics.mean(tmax_values) if tmax_values else None
            tmin_seasonal = statistics.mean(tmin_values) if tmin_values else None
            sunshine_seasonal = sum(sunshine_values) if sunshine_values else None

            rainfall_yearly.append(rainfall_seasonal)
            tmax_yearly.append(tmax_seasonal)
            tmin_yearly.append(tmin_seasonal)
            sunshine_yearly.append(sunshine_seasonal)
        else:
            rainfall_yearly.append(None)
            tmax_yearly.append(None)
            tmin_yearly.append(None)
            sunshine_yearly.append(None)

    # Calculate data quality
    years_with_data, completeness = calculate_data_quality(rainfall_yearly, expected_years)

    if years_with_data < min_years_required:
        return None

    # Calculate normals
    rainfall_normal, rainfall_std = calculate_normal_and_std(
        [v for v in rainfall_yearly if v is not None]
    )
    tmax_normal, tmax_std = calculate_normal_and_std(
        [v for v in tmax_yearly if v is not None]
    )
    tmin_normal, tmin_std = calculate_normal_and_std(
        [v for v in tmin_yearly if v is not None]
    )
    sunshine_normal, sunshine_std = calculate_normal_and_std(
        [v for v in sunshine_yearly if v is not None]
    )

    temp_mean_values = []
    for tmax, tmin in zip(tmax_yearly, tmin_yearly):
        if tmax is not None and tmin is not None:
            temp_mean_values.append((tmax + tmin) / 2)

    temp_mean_normal, temp_std = calculate_normal_and_std(temp_mean_values)

    return {
        'station_id': station_id,
        'normal_period_start': period_start,
        'normal_period_end': period_end,
        'timescale': 'seasonal',
        'month': None,
        'dekad': None,
        'season': season,
        'rainfall_normal': rainfall_normal,
        'rainfall_std': rainfall_std,
        'temp_max_normal': tmax_normal,
        'temp_min_normal': tmin_normal,
        'temp_mean_normal': temp_mean_normal,
        'temp_std': temp_std,
        'sunshine_normal': sunshine_normal,
        'years_with_data': years_with_data,
        'data_completeness_percent': completeness
    }


async def compute_annual_normal(
    db: AsyncSession,
    station_id: int,
    period_start: int = 1991,
    period_end: int = 2020,
    min_years_required: int = 20
) -> Optional[Dict]:
    """
    Compute 30-year annual climate normal.

    Args:
        db: Database session
        station_id: Station ID
        period_start: Start year (default: 1991)
        period_end: End year (default: 2020)
        min_years_required: Minimum years needed (default: 20)

    Returns:
        Dictionary with normal values or None if insufficient data
    """
    # Collect yearly values
    rainfall_yearly = []
    tmax_yearly = []
    tmin_yearly = []
    sunshine_yearly = []

    expected_years = period_end - period_start + 1

    for year in range(period_start, period_end + 1):
        start_date = date(year, 1, 1)
        end_date = date(year, 12, 31)

        # Query daily data for this year
        result = await db.execute(
            select(DailySummary).where(
                and_(
                    DailySummary.station_id == station_id,
                    DailySummary.date >= start_date,
                    DailySummary.date <= end_date
                )
            )
        )
        daily_data = result.scalars().all()

        # Check data completeness (need at least 292 days for valid year - 80%)
        if len(daily_data) >= 292:
            # Aggregate annual values
            rainfall_values = [d.rainfall_total for d in daily_data if d.rainfall_total is not None]
            tmax_values = [d.temp_max for d in daily_data if d.temp_max is not None]
            tmin_values = [d.temp_min for d in daily_data if d.temp_min is not None]
            sunshine_values = [d.sunshine_hours for d in daily_data if d.sunshine_hours is not None]

            rainfall_annual = sum(rainfall_values) if rainfall_values else None
            tmax_annual = statistics.mean(tmax_values) if tmax_values else None
            tmin_annual = statistics.mean(tmin_values) if tmin_values else None
            sunshine_annual = sum(sunshine_values) if sunshine_values else None

            rainfall_yearly.append(rainfall_annual)
            tmax_yearly.append(tmax_annual)
            tmin_yearly.append(tmin_annual)
            sunshine_yearly.append(sunshine_annual)
        else:
            rainfall_yearly.append(None)
            tmax_yearly.append(None)
            tmin_yearly.append(None)
            sunshine_yearly.append(None)

    # Calculate data quality
    years_with_data, completeness = calculate_data_quality(rainfall_yearly, expected_years)

    if years_with_data < min_years_required:
        return None

    # Calculate normals
    rainfall_normal, rainfall_std = calculate_normal_and_std(
        [v for v in rainfall_yearly if v is not None]
    )
    tmax_normal, tmax_std = calculate_normal_and_std(
        [v for v in tmax_yearly if v is not None]
    )
    tmin_normal, tmin_std = calculate_normal_and_std(
        [v for v in tmin_yearly if v is not None]
    )
    sunshine_normal, sunshine_std = calculate_normal_and_std(
        [v for v in sunshine_yearly if v is not None]
    )

    temp_mean_values = []
    for tmax, tmin in zip(tmax_yearly, tmin_yearly):
        if tmax is not None and tmin is not None:
            temp_mean_values.append((tmax + tmin) / 2)

    temp_mean_normal, temp_std = calculate_normal_and_std(temp_mean_values)

    return {
        'station_id': station_id,
        'normal_period_start': period_start,
        'normal_period_end': period_end,
        'timescale': 'annual',
        'month': None,
        'dekad': None,
        'season': None,
        'rainfall_normal': rainfall_normal,
        'rainfall_std': rainfall_std,
        'temp_max_normal': tmax_normal,
        'temp_min_normal': tmin_normal,
        'temp_mean_normal': temp_mean_normal,
        'temp_std': temp_std,
        'sunshine_normal': sunshine_normal,
        'years_with_data': years_with_data,
        'data_completeness_percent': completeness
    }


async def compute_station_normals(
    db: AsyncSession,
    station: Station,
    period_start: int = 1991,
    period_end: int = 2020
) -> Dict[str, int]:
    """
    Compute all climate normals for a single station.

    Computes 53 normals:
    - 12 monthly normals (Jan-Dec)
    - 36 dekadal normals (12 months × 3 dekads)
    - 4 seasonal normals (MAM, JJA, SON, DJF)
    - 1 annual normal

    Args:
        db: Database session
        station: Station instance
        period_start: Start year (default: 1991)
        period_end: End year (default: 2020)

    Returns:
        Dictionary with counts: {'monthly': 12, 'dekadal': 36, 'seasonal': 4, 'annual': 1}
    """
    logger.info(f"Processing station: {station.name} ({station.code})")

    normals_to_insert = []
    counts = {'monthly': 0, 'dekadal': 0, 'seasonal': 0, 'annual': 0}

    # 1. Compute monthly normals (12)
    for month in range(1, 13):
        normal_data = await compute_monthly_normal(
            db, station.id, month, period_start, period_end
        )
        if normal_data:
            normals_to_insert.append(ClimateNormal(**normal_data))
            counts['monthly'] += 1

    logger.info(f"  ✓ Computed {counts['monthly']}/12 monthly normals")

    # 2. Compute dekadal normals (36)
    for month in range(1, 13):
        for dekad in range(1, 4):
            normal_data = await compute_dekadal_normal(
                db, station.id, month, dekad, period_start, period_end
            )
            if normal_data:
                normals_to_insert.append(ClimateNormal(**normal_data))
                counts['dekadal'] += 1

    logger.info(f"  ✓ Computed {counts['dekadal']}/36 dekadal normals")

    # 3. Compute seasonal normals (4)
    for season in ['MAM', 'JJA', 'SON', 'DJF']:
        normal_data = await compute_seasonal_normal(
            db, station.id, season, period_start, period_end
        )
        if normal_data:
            normals_to_insert.append(ClimateNormal(**normal_data))
            counts['seasonal'] += 1

    logger.info(f"  ✓ Computed {counts['seasonal']}/4 seasonal normals")

    # 4. Compute annual normal (1)
    normal_data = await compute_annual_normal(
        db, station.id, period_start, period_end
    )
    if normal_data:
        normals_to_insert.append(ClimateNormal(**normal_data))
        counts['annual'] += 1

    logger.info(f"  ✓ Computed {counts['annual']}/1 annual normal")

    # Bulk insert all normals for this station
    if normals_to_insert:
        db.add_all(normals_to_insert)
        await db.commit()
        logger.info(f"  ✓ Saved {len(normals_to_insert)} normals to database")

    total = sum(counts.values())
    logger.info(f"  Total: {total}/53 normals computed\n")

    return counts


async def populate_all_climate_normals(
    period_start: int = 1991,
    period_end: int = 2020,
    station_code: Optional[str] = None
):
    """
    Main entry point: compute climate normals for all stations.

    Args:
        period_start: Start year (default: 1991)
        period_end: End year (default: 2020)
        station_code: Optional station code to process only one station
    """
    logger.info("=" * 70)
    logger.info("GMet Climate Normals - Computation Script")
    logger.info("=" * 70)
    logger.info(f"WMO Reference Period: {period_start}-{period_end}")
    logger.info("")

    async with async_session() as db:
        # Get stations to process
        if station_code:
            result = await db.execute(
                select(Station).where(Station.code == station_code)
            )
            stations = [result.scalar_one_or_none()]
            if stations[0] is None:
                logger.error(f"Station not found: {station_code}")
                return
        else:
            result = await db.execute(select(Station))
            stations = result.scalars().all()

        if not stations:
            logger.error("No stations found in database!")
            return

        logger.info(f"Found {len(stations)} station(s) to process\n")

        # Track overall statistics
        total_counts = {'monthly': 0, 'dekadal': 0, 'seasonal': 0, 'annual': 0}
        stations_processed = 0

        # Process each station
        for station in stations:
            try:
                counts = await compute_station_normals(
                    db, station, period_start, period_end
                )

                # Update totals
                for key in total_counts:
                    total_counts[key] += counts[key]

                stations_processed += 1

            except Exception as e:
                logger.error(f"Error processing station {station.code}: {e}", exc_info=True)
                continue

    # Final summary
    logger.info("=" * 70)
    logger.info("COMPUTATION COMPLETE")
    logger.info("=" * 70)
    logger.info(f"Stations processed: {stations_processed}/{len(stations)}")
    logger.info(f"Monthly normals: {total_counts['monthly']}")
    logger.info(f"Dekadal normals: {total_counts['dekadal']}")
    logger.info(f"Seasonal normals: {total_counts['seasonal']}")
    logger.info(f"Annual normals: {total_counts['annual']}")
    logger.info(f"Total normals computed: {sum(total_counts.values())}")
    logger.info("")

    expected_total = stations_processed * 53
    actual_total = sum(total_counts.values())
    completeness_pct = (actual_total / expected_total * 100) if expected_total > 0 else 0

    logger.info(f"Expected normals: {expected_total} (53 per station)")
    logger.info(f"Data completeness: {completeness_pct:.1f}%")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Verify normals in database: SELECT COUNT(*) FROM climate_normals;")
    logger.info("2. Test API endpoints to see anomaly calculations")
    logger.info("3. Run tests: pytest tests/test_climate_normals.py -v")
    logger.info("=" * 70)


def main():
    """Command-line entry point."""
    parser = argparse.ArgumentParser(
        description="Compute WMO 1991-2020 climate normals for GMet API"
    )
    parser.add_argument(
        '--period-start',
        type=int,
        default=1991,
        help='Start year of normal period (default: 1991)'
    )
    parser.add_argument(
        '--period-end',
        type=int,
        default=2020,
        help='End year of normal period (default: 2020)'
    )
    parser.add_argument(
        '--station-code',
        type=str,
        help='Compute normals for specific station only (e.g., 04003NAV)'
    )

    args = parser.parse_args()

    # Run computation
    asyncio.run(populate_all_climate_normals(
        period_start=args.period_start,
        period_end=args.period_end,
        station_code=args.station_code
    ))


if __name__ == "__main__":
    main()
