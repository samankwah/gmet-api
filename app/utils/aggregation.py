"""
WMO-compliant aggregation utilities for climate products.

This module provides functions for aggregating weather data following World
Meteorological Organization (WMO) guidelines and standards.

CRITICAL RULES - WMO COMPLIANCE:
1. RAINFALL: Always SUM, never average
2. SUNSHINE: Always SUM, never average
3. TEMPERATURE: Calculate MEAN of daily Tmax/Tmin
4. RELATIVE HUMIDITY: Can be averaged (mean of daily means)
5. WIND SPEED: Scalar mean (average of speeds)

Data completeness thresholds:
- Weekly: >= 5 days (71%)
- Monthly: >= 21 days (70%)
- Must have actual observations, not assumed zeros
"""

from datetime import date, datetime, timedelta
from typing import List, Optional, Dict, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
import calendar

from app.models.daily_summary import DailySummary


# ============================================================================
# PERIOD DEFINITION UTILITIES
# ============================================================================

def get_iso_week(date_obj: date) -> Tuple[int, int]:
    """
    Get ISO 8601 week number (1-53) and year.

    ISO 8601 week rules:
    - Week starts on Monday
    - Week 1 is the first week with at least 4 days in the new year
    - Weeks may span across calendar years

    Args:
        date_obj: Date to get ISO week for

    Returns:
        Tuple of (iso_year, week_number)

    Example:
        >>> get_iso_week(date(2024, 1, 1))  # Monday
        (2024, 1)
        >>> get_iso_week(date(2024, 12, 30))  # Monday
        (2025, 1)  # Week 1 of 2025 starts on Dec 30, 2024
    """
    iso_calendar = date_obj.isocalendar()
    return (iso_calendar[0], iso_calendar[1])


def get_week_date_range(year: int, week_number: int) -> Tuple[date, date]:
    """
    Get Monday start and Sunday end dates for an ISO week.

    Args:
        year: ISO year
        week_number: ISO week number (1-53)

    Returns:
        Tuple of (start_date, end_date) where start is Monday, end is Sunday

    Example:
        >>> get_week_date_range(2024, 20)
        (date(2024, 5, 13), date(2024, 5, 19))
    """
    # ISO week starts on Monday, find the Monday of week 1
    jan_4 = date(year, 1, 4)  # Week 1 is the week containing Jan 4
    # Find the Monday of that week
    days_since_monday = jan_4.weekday()
    first_monday = jan_4 - timedelta(days=days_since_monday)

    # Calculate the Monday of the requested week
    start_date = first_monday + timedelta(weeks=week_number - 1)
    end_date = start_date + timedelta(days=6)  # Sunday

    return (start_date, end_date)


def is_leap_year(year: int) -> bool:
    """
    Check if a year is a leap year.

    Args:
        year: Year to check

    Returns:
        True if leap year, False otherwise
    """
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def days_in_month(year: int, month: int) -> int:
    """
    Get number of days in a given month and year.

    Args:
        year: Year
        month: Month (1-12)

    Returns:
        Number of days in the month
    """
    return calendar.monthrange(year, month)[1]


# ============================================================================
# WMO-COMPLIANT AGGREGATION FUNCTIONS
# ============================================================================

async def compute_weekly_summary(
    db: AsyncSession,
    station_id: int,
    year: int,
    week_number: int
) -> Optional[Dict]:
    """
    Compute weekly summary from daily data following WMO rules.

    WMO AGGREGATION RULES:
    - Rainfall: SUM (never average)
    - Sunshine: SUM (never average)
    - Temperature: MEAN of daily Tmax/Tmin
    - RH: MEAN of daily means
    - Wind: MEAN of daily means

    Requires at least 5 days of data (71% completeness) for valid aggregation.

    Args:
        db: Database session
        station_id: Station ID
        year: ISO year
        week_number: ISO week number (1-53)

    Returns:
        Dictionary with weekly aggregates or None if insufficient data
    """
    # Get start/end dates for ISO week
    start_date, end_date = get_week_date_range(year, week_number)

    # Query daily summaries for the week
    result = await db.execute(
        select(DailySummary).where(
            and_(
                DailySummary.station_id == station_id,
                DailySummary.date >= start_date,
                DailySummary.date <= end_date
            )
        ).order_by(DailySummary.date)
    )
    daily_data = result.scalars().all()

    # Require at least 5 days of data (71% completeness)
    if len(daily_data) < 5:
        return None

    # WMO-compliant aggregation
    # Rainfall: SUM (never average) - only include non-null values
    rainfall_values = [d.rainfall_total for d in daily_data if d.rainfall_total is not None]

    # Temperature: MEAN of daily Tmax/Tmin
    tmax_values = [d.temp_max for d in daily_data if d.temp_max is not None]
    tmin_values = [d.temp_min for d in daily_data if d.temp_min is not None]

    # Other parameters
    rh_values = [d.mean_rh for d in daily_data if d.mean_rh is not None]
    wind_values = [d.wind_speed for d in daily_data if d.wind_speed is not None]

    # Sunshine: SUM (never average) - only include non-null values
    sunshine_values = [d.sunshine_hours for d in daily_data if d.sunshine_hours is not None]

    # Compute wet days (>= 1mm) - only from non-null rainfall values
    wet_days = sum(1 for r in rainfall_values if r >= 1.0)

    # Build result dictionary
    return {
        'station_id': station_id,
        'year': year,
        'week_number': week_number,
        'start_date': start_date,
        'end_date': end_date,

        # Rainfall (WMO: SUM)
        'rainfall_total': sum(rainfall_values) if rainfall_values else None,
        'wet_days_count': wet_days if rainfall_values else None,
        'max_daily_rainfall': max(rainfall_values) if rainfall_values else None,

        # Temperature (WMO: MEAN)
        'temp_max_mean': round(sum(tmax_values) / len(tmax_values), 1) if tmax_values else None,
        'temp_min_mean': round(sum(tmin_values) / len(tmin_values), 1) if tmin_values else None,
        'temp_max_absolute': max(tmax_values) if tmax_values else None,
        'temp_min_absolute': min(tmin_values) if tmin_values else None,

        # Other parameters (WMO: MEAN)
        'mean_rh': round(sum(rh_values) / len(rh_values)) if rh_values else None,
        'mean_wind_speed': round(sum(wind_values) / len(wind_values), 1) if wind_values else None,

        # Sunshine (WMO: SUM)
        'sunshine_total': round(sum(sunshine_values), 1) if sunshine_values else None,
    }


async def compute_monthly_summary(
    db: AsyncSession,
    station_id: int,
    year: int,
    month: int
) -> Optional[Dict]:
    """
    Compute monthly summary from daily data following WMO rules.

    WMO AGGREGATION RULES:
    - Rainfall: SUM (never average)
    - Sunshine: SUM (never average)
    - Temperature: MEAN of daily Tmax/Tmin
    - RH: MEAN of daily means
    - Wind: MEAN of daily means

    Requires at least 21 days of data (70% completeness) for valid aggregation.

    Anomaly calculation (if climate normal exists):
    - Absolute: current_value - normal_value
    - Percent: ((current_value - normal_value) / normal_value) * 100

    Args:
        db: Database session
        station_id: Station ID
        year: Year
        month: Month (1-12)

    Returns:
        Dictionary with monthly aggregates or None if insufficient data
    """
    # Get month date range
    start_date = date(year, month, 1)
    days_in_this_month = days_in_month(year, month)
    end_date = date(year, month, days_in_this_month)

    # Query daily summaries for the month
    result = await db.execute(
        select(DailySummary).where(
            and_(
                DailySummary.station_id == station_id,
                DailySummary.date >= start_date,
                DailySummary.date <= end_date
            )
        ).order_by(DailySummary.date)
    )
    daily_data = result.scalars().all()

    # Calculate data completeness
    days_with_data = len(daily_data)
    data_completeness_percent = (days_with_data / days_in_this_month) * 100

    # Require at least 70% completeness (21 days for 30-day month)
    if data_completeness_percent < 70:
        return None

    # WMO-compliant aggregation
    # Rainfall: SUM (never average) - only include non-null values
    rainfall_values = [d.rainfall_total for d in daily_data if d.rainfall_total is not None]

    # Temperature: MEAN of daily Tmax/Tmin
    tmax_values = [d.temp_max for d in daily_data if d.temp_max is not None]
    tmin_values = [d.temp_min for d in daily_data if d.temp_min is not None]

    # Other parameters
    rh_values = [d.mean_rh for d in daily_data if d.mean_rh is not None]
    wind_values = [d.wind_speed for d in daily_data if d.wind_speed is not None]

    # Sunshine: SUM (never average) - only include non-null values
    sunshine_values = [d.sunshine_hours for d in daily_data if d.sunshine_hours is not None]

    # Compute rainfall days (>= 1mm)
    rainfall_days = sum(1 for r in rainfall_values if r >= 1.0)

    # Calculate mean temperature (average of Tmax_mean and Tmin_mean)
    temp_mean = None
    if tmax_values and tmin_values:
        temp_max_mean = sum(tmax_values) / len(tmax_values)
        temp_min_mean = sum(tmin_values) / len(tmin_values)
        temp_mean = (temp_max_mean + temp_min_mean) / 2

    # Query climate normal for anomaly calculation
    from app.crud.climate_normals import climate_normal

    normal = await climate_normal.get_monthly_normal(db, station_id, month)

    # Calculate anomalies if normal exists
    rainfall_anomaly = None
    rainfall_anomaly_percent = None
    temp_anomaly = None

    if normal:
        # Rainfall anomalies
        if rainfall_values and normal.rainfall_normal is not None:
            rainfall_total = sum(rainfall_values)
            rainfall_anomaly = compute_climate_anomaly(
                rainfall_total,
                normal.rainfall_normal,
                method='absolute'
            )
            rainfall_anomaly_percent = compute_climate_anomaly(
                rainfall_total,
                normal.rainfall_normal,
                method='percent'
            )
            if rainfall_anomaly is not None:
                rainfall_anomaly = round(rainfall_anomaly, 1)
            if rainfall_anomaly_percent is not None:
                rainfall_anomaly_percent = round(rainfall_anomaly_percent, 1)

        # Temperature anomalies
        if temp_mean is not None and normal.temp_mean_normal is not None:
            temp_anomaly = compute_climate_anomaly(
                temp_mean,
                normal.temp_mean_normal,
                method='absolute'
            )
            if temp_anomaly is not None:
                temp_anomaly = round(temp_anomaly, 1)

    # Build result dictionary
    return {
        'station_id': station_id,
        'year': year,
        'month': month,

        # Rainfall (WMO: SUM)
        'rainfall_total': round(sum(rainfall_values), 1) if rainfall_values else None,
        'rainfall_anomaly': rainfall_anomaly,
        'rainfall_anomaly_percent': rainfall_anomaly_percent,
        'rainfall_days': rainfall_days if rainfall_values else None,
        'max_daily_rainfall': round(max(rainfall_values), 1) if rainfall_values else None,

        # Temperature (WMO: MEAN)
        'temp_max_mean': round(sum(tmax_values) / len(tmax_values), 1) if tmax_values else None,
        'temp_min_mean': round(sum(tmin_values) / len(tmin_values), 1) if tmin_values else None,
        'temp_mean': round(temp_mean, 1) if temp_mean else None,
        'temp_max_absolute': max(tmax_values) if tmax_values else None,
        'temp_min_absolute': min(tmin_values) if tmin_values else None,
        'temp_anomaly': temp_anomaly,

        # Other parameters (WMO: MEAN)
        'mean_rh': round(sum(rh_values) / len(rh_values)) if rh_values else None,
        'mean_wind_speed': round(sum(wind_values) / len(wind_values), 1) if wind_values else None,

        # Sunshine (WMO: SUM)
        'sunshine_total': round(sum(sunshine_values), 1) if sunshine_values else None,

        # Data quality
        'days_with_data': days_with_data,
        'data_completeness_percent': round(data_completeness_percent, 1),
    }


def compute_climate_anomaly(
    value: Optional[float],
    normal: Optional[float],
    method: str = 'absolute'
) -> Optional[float]:
    """
    Compute climate anomaly compared to normal.

    Args:
        value: Current observed value
        normal: Climate normal (30-year mean)
        method: 'absolute' for difference, 'percent' for percentage

    Returns:
        Anomaly value or None if either input is None

    Examples:
        >>> compute_climate_anomaly(150.0, 120.0, 'absolute')
        30.0
        >>> compute_climate_anomaly(150.0, 120.0, 'percent')
        25.0
    """
    if value is None or normal is None:
        return None

    if method == 'absolute':
        return value - normal
    elif method == 'percent':
        if normal == 0:
            return None  # Avoid division by zero
        return ((value - normal) / normal) * 100
    else:
        raise ValueError(f"Unknown anomaly method: {method}")


# ============================================================================
# PHASE 2: ADVANCED PERIOD DEFINITIONS
# ============================================================================

def get_dekad_for_date(date_obj: date) -> Tuple[int, int, int, date, date]:
    """
    Get dekad information for a given date.

    CRITICAL - Dekad definitions (NOT arbitrary 10-day windows):
    - Dekad 1: Days 1-10
    - Dekad 2: Days 11-20
    - Dekad 3: Days 21 to end of month (28/29/30/31)

    Args:
        date_obj: Date to get dekad for

    Returns:
        Tuple of (year, month, dekad, start_date, end_date)

    Example:
        >>> get_dekad_for_date(date(2024, 5, 15))
        (2024, 5, 2, date(2024, 5, 11), date(2024, 5, 20))
    """
    year = date_obj.year
    month = date_obj.month
    day = date_obj.day

    if day <= 10:
        dekad = 1
        start_date = date(year, month, 1)
        end_date = date(year, month, 10)
    elif day <= 20:
        dekad = 2
        start_date = date(year, month, 11)
        end_date = date(year, month, 20)
    else:
        dekad = 3
        start_date = date(year, month, 21)
        last_day = days_in_month(year, month)
        end_date = date(year, month, last_day)

    return (year, month, dekad, start_date, end_date)


# Ghana-specific season definitions
GHANA_SEASONS = {
    'MAM': {'name': 'Major Rainy Season', 'months': [3, 4, 5], 'start_month': 3, 'end_month': 5},
    'JJA': {'name': 'Minor Rainy Season', 'months': [6, 7, 8], 'start_month': 6, 'end_month': 8},
    'SON': {'name': 'Post-Rainy/Transition', 'months': [9, 10, 11], 'start_month': 9, 'end_month': 11},
    'DJF': {'name': 'Dry Season/Harmattan', 'months': [12, 1, 2], 'start_month': 12, 'end_month': 2},
}


def get_season_for_date(date_obj: date) -> Tuple[str, int, date, date]:
    """
    Get Ghana-specific season for a given date.

    Ghana climate seasons:
    - MAM (March-April-May): Major rainy season
    - JJA (June-July-August): Minor rainy season
    - SON (September-October-November): Post-rainy/transition
    - DJF (December-January-February): Dry season/Harmattan

    Note: DJF spans two calendar years (Dec Y -> Jan/Feb Y+1)

    Args:
        date_obj: Date to get season for

    Returns:
        Tuple of (season_code, year, start_date, end_date)
        For DJF, year refers to the December year

    Example:
        >>> get_season_for_date(date(2024, 4, 15))
        ('MAM', 2024, date(2024, 3, 1), date(2024, 5, 31))
    """
    month = date_obj.month
    year = date_obj.year

    if month in [3, 4, 5]:
        return ('MAM', year, date(year, 3, 1), date(year, 5, 31))
    elif month in [6, 7, 8]:
        return ('JJA', year, date(year, 6, 1), date(year, 8, 31))
    elif month in [9, 10, 11]:
        return ('SON', year, date(year, 9, 1), date(year, 11, 30))
    else:  # month in [12, 1, 2]
        # DJF: December of year Y to February of year Y+1
        # We use December's year as the season year
        if month == 12:
            djf_year = year
            start_date = date(year, 12, 1)
            end_date = date(year + 1, 2, 28 if not is_leap_year(year + 1) else 29)
        else:  # January or February
            djf_year = year - 1
            start_date = date(year - 1, 12, 1)
            end_date = date(year, 2, 28 if not is_leap_year(year) else 29)
        return ('DJF', djf_year, start_date, end_date)


# ============================================================================
# PHASE 2: ADVANCED AGGREGATION FUNCTIONS
# ============================================================================

async def compute_dekadal_summary(
    db: AsyncSession,
    station_id: int,
    year: int,
    month: int,
    dekad: int
) -> Optional[Dict]:
    """
    Compute dekadal summary from daily data following WMO rules.

    WMO AGGREGATION RULES (same as weekly/monthly):
    - Rainfall: SUM (never average)
    - Sunshine: SUM (never average)
    - Temperature: MEAN of daily Tmax/Tmin
    - RH: MEAN of daily means

    Requires at least 7 days of data (70% completeness) for valid aggregation.

    Args:
        db: Database session
        station_id: Station ID
        year: Year
        month: Month (1-12)
        dekad: Dekad number (1, 2, or 3)

    Returns:
        Dictionary with dekadal aggregates or None if insufficient data
    """
    # Get dekad date range
    if dekad == 1:
        start_date = date(year, month, 1)
        end_date = date(year, month, 10)
    elif dekad == 2:
        start_date = date(year, month, 11)
        end_date = date(year, month, 20)
    else:  # dekad == 3
        start_date = date(year, month, 21)
        last_day = days_in_month(year, month)
        end_date = date(year, month, last_day)

    # Query daily summaries for the dekad
    result = await db.execute(
        select(DailySummary).where(
            and_(
                DailySummary.station_id == station_id,
                DailySummary.date >= start_date,
                DailySummary.date <= end_date
            )
        ).order_by(DailySummary.date)
    )
    daily_data = result.scalars().all()

    # Require at least 7 days of data (70% completeness)
    if len(daily_data) < 7:
        return None

    # WMO-compliant aggregation
    rainfall_values = [d.rainfall_total for d in daily_data if d.rainfall_total is not None]
    tmax_values = [d.temp_max for d in daily_data if d.temp_max is not None]
    tmin_values = [d.temp_min for d in daily_data if d.temp_min is not None]
    rh_values = [d.mean_rh for d in daily_data if d.mean_rh is not None]
    sunshine_values = [d.sunshine_hours for d in daily_data if d.sunshine_hours is not None]

    # Compute rainy days (>= 1mm)
    rainy_days = sum(1 for r in rainfall_values if r >= 1.0)

    # Query climate normal for anomaly calculation
    from app.crud.climate_normals import climate_normal

    normal = await climate_normal.get_dekadal_normal(db, station_id, month, dekad)

    # Calculate anomalies if normal exists
    rainfall_anomaly = None
    rainfall_anomaly_percent = None

    if normal and rainfall_values and normal.rainfall_normal is not None:
        rainfall_total = sum(rainfall_values)
        rainfall_anomaly = compute_climate_anomaly(
            rainfall_total,
            normal.rainfall_normal,
            method='absolute'
        )
        rainfall_anomaly_percent = compute_climate_anomaly(
            rainfall_total,
            normal.rainfall_normal,
            method='percent'
        )
        if rainfall_anomaly is not None:
            rainfall_anomaly = round(rainfall_anomaly, 1)
        if rainfall_anomaly_percent is not None:
            rainfall_anomaly_percent = round(rainfall_anomaly_percent, 1)

    return {
        'station_id': station_id,
        'year': year,
        'month': month,
        'dekad': dekad,
        'start_date': start_date,
        'end_date': end_date,

        # Rainfall (WMO: SUM)
        'rainfall_total': round(sum(rainfall_values), 1) if rainfall_values else None,
        'rainfall_anomaly': rainfall_anomaly,
        'rainfall_anomaly_percent': rainfall_anomaly_percent,
        'rainy_days': rainy_days if rainfall_values else None,

        # Temperature (WMO: MEAN)
        'temp_max_mean': round(sum(tmax_values) / len(tmax_values), 1) if tmax_values else None,
        'temp_min_mean': round(sum(tmin_values) / len(tmin_values), 1) if tmin_values else None,
        'temp_max_absolute': max(tmax_values) if tmax_values else None,
        'temp_min_absolute': min(tmin_values) if tmin_values else None,

        # Other parameters
        'mean_rh': round(sum(rh_values) / len(rh_values)) if rh_values else None,

        # Sunshine (WMO: SUM)
        'sunshine_total': round(sum(sunshine_values), 1) if sunshine_values else None,
    }


async def compute_seasonal_summary(
    db: AsyncSession,
    station_id: int,
    year: int,
    season: str
) -> Optional[Dict]:
    """
    Compute seasonal summary from daily data following WMO rules.

    Ghana seasons: MAM, JJA, SON, DJF
    For DJF, year refers to December year (e.g., DJF 2024 = Dec 2024 - Feb 2025)

    Requires at least 63 days of data (70% completeness) for valid aggregation.

    Args:
        db: Database session
        station_id: Station ID
        year: Year (for DJF, this is the December year)
        season: Season code ('MAM', 'JJA', 'SON', or 'DJF')

    Returns:
        Dictionary with seasonal aggregates or None if insufficient data
    """
    # Get season date range
    if season == 'MAM':
        start_date = date(year, 3, 1)
        end_date = date(year, 5, 31)
        expected_days = 92
    elif season == 'JJA':
        start_date = date(year, 6, 1)
        end_date = date(year, 8, 31)
        expected_days = 92
    elif season == 'SON':
        start_date = date(year, 9, 1)
        end_date = date(year, 11, 30)
        expected_days = 91
    elif season == 'DJF':
        start_date = date(year, 12, 1)
        end_date = date(year + 1, 2, 28 if not is_leap_year(year + 1) else 29)
        expected_days = 90 if not is_leap_year(year + 1) else 91
    else:
        raise ValueError(f"Invalid season: {season}")

    # Query daily summaries for the season
    result = await db.execute(
        select(DailySummary).where(
            and_(
                DailySummary.station_id == station_id,
                DailySummary.date >= start_date,
                DailySummary.date <= end_date
            )
        ).order_by(DailySummary.date)
    )
    daily_data = result.scalars().all()

    # Require at least 70% completeness
    days_with_data = len(daily_data)
    data_completeness = (days_with_data / expected_days) * 100
    if data_completeness < 70:
        return None

    # WMO-compliant aggregation
    rainfall_values = [d.rainfall_total for d in daily_data if d.rainfall_total is not None]
    tmax_values = [d.temp_max for d in daily_data if d.temp_max is not None]
    tmin_values = [d.temp_min for d in daily_data if d.temp_min is not None]
    rh_values = [d.mean_rh for d in daily_data if d.mean_rh is not None]
    sunshine_values = [d.sunshine_hours for d in daily_data if d.sunshine_hours is not None]

    # Compute rainy days and hot days
    rainy_days = sum(1 for r in rainfall_values if r >= 1.0)
    hot_days_count = sum(1 for t in tmax_values if t > 35.0)

    # Calculate dry spells (consecutive days without rain >= 7 days)
    max_dry_spell = 0
    dry_spells_count = 0
    current_dry_spell = 0

    for d in daily_data:
        if d.rainfall_total is not None:
            if d.rainfall_total < 1.0:
                current_dry_spell += 1
                max_dry_spell = max(max_dry_spell, current_dry_spell)
            else:
                if current_dry_spell >= 7:
                    dry_spells_count += 1
                current_dry_spell = 0

    # Check if last dry spell was >= 7 days
    if current_dry_spell >= 7:
        dry_spells_count += 1

    # Onset/cessation detection for agricultural seasons (MAM, JJA)
    onset_date = None
    cessation_date = None
    season_length_days = None

    if season in ['MAM', 'JJA']:
        from app.utils.agro import compute_onset_cessation_for_season

        onset_cessation_data = await compute_onset_cessation_for_season(
            db, station_id, year, season
        )

        onset_date = onset_cessation_data.get('onset_date')
        cessation_date = onset_cessation_data.get('cessation_date')

        if onset_date and cessation_date:
            season_length_days = (cessation_date - onset_date).days

    # Calculate mean temperature
    temp_mean = None
    if tmax_values and tmin_values:
        temp_max_mean = sum(tmax_values) / len(tmax_values)
        temp_min_mean = sum(tmin_values) / len(tmin_values)
        temp_mean = (temp_max_mean + temp_min_mean) / 2

    # Query climate normal for anomaly calculation
    from app.crud.climate_normals import climate_normal

    normal = await climate_normal.get_seasonal_normal(db, station_id, season)

    # Calculate anomalies if normal exists
    rainfall_anomaly = None
    rainfall_anomaly_percent = None
    temp_anomaly = None

    if normal:
        # Rainfall anomalies
        if rainfall_values and normal.rainfall_normal is not None:
            rainfall_total = sum(rainfall_values)
            rainfall_anomaly = compute_climate_anomaly(
                rainfall_total,
                normal.rainfall_normal,
                method='absolute'
            )
            rainfall_anomaly_percent = compute_climate_anomaly(
                rainfall_total,
                normal.rainfall_normal,
                method='percent'
            )
            if rainfall_anomaly is not None:
                rainfall_anomaly = round(rainfall_anomaly, 1)
            if rainfall_anomaly_percent is not None:
                rainfall_anomaly_percent = round(rainfall_anomaly_percent, 1)

        # Temperature anomalies
        if temp_mean is not None and normal.temp_mean_normal is not None:
            temp_anomaly = compute_climate_anomaly(
                temp_mean,
                normal.temp_mean_normal,
                method='absolute'
            )
            if temp_anomaly is not None:
                temp_anomaly = round(temp_anomaly, 1)

    return {
        'station_id': station_id,
        'year': year,
        'season': season,
        'start_date': start_date,
        'end_date': end_date,

        # Rainfall (WMO: SUM)
        'rainfall_total': round(sum(rainfall_values), 1) if rainfall_values else None,
        'rainfall_anomaly': rainfall_anomaly,
        'rainfall_anomaly_percent': rainfall_anomaly_percent,
        'rainy_days': rainy_days if rainfall_values else None,

        # Agricultural timing
        'onset_date': onset_date,
        'cessation_date': cessation_date,
        'season_length_days': season_length_days,

        # Dry spell analysis
        'max_dry_spell_days': max_dry_spell if rainfall_values else None,
        'dry_spells_count': dry_spells_count if rainfall_values else None,

        # Temperature (WMO: MEAN)
        'temp_max_mean': round(sum(tmax_values) / len(tmax_values), 1) if tmax_values else None,
        'temp_min_mean': round(sum(tmin_values) / len(tmin_values), 1) if tmin_values else None,
        'temp_anomaly': temp_anomaly,

        # Extreme events
        'hot_days_count': hot_days_count if tmax_values else None,

        # Other parameters
        'mean_rh': round(sum(rh_values) / len(rh_values)) if rh_values else None,

        # Sunshine (WMO: SUM)
        'sunshine_total': round(sum(sunshine_values), 1) if sunshine_values else None,
    }


async def compute_annual_summary(
    db: AsyncSession,
    station_id: int,
    year: int
) -> Optional[Dict]:
    """
    Compute annual summary from daily data following WMO rules.

    Requires at least 292 days of data (80% completeness) for valid aggregation.

    Args:
        db: Database session
        station_id: Station ID
        year: Year

    Returns:
        Dictionary with annual aggregates or None if insufficient data
    """
    # Get year date range
    start_date = date(year, 1, 1)
    end_date = date(year, 12, 31)
    expected_days = 366 if is_leap_year(year) else 365

    # Query daily summaries for the year
    result = await db.execute(
        select(DailySummary).where(
            and_(
                DailySummary.station_id == station_id,
                DailySummary.date >= start_date,
                DailySummary.date <= end_date
            )
        ).order_by(DailySummary.date)
    )
    daily_data = result.scalars().all()

    # Calculate data completeness
    days_with_data = len(daily_data)
    data_completeness_percent = (days_with_data / expected_days) * 100

    # Require at least 80% completeness (292 days)
    if data_completeness_percent < 80:
        return None

    # WMO-compliant aggregation
    rainfall_values = [d.rainfall_total for d in daily_data if d.rainfall_total is not None]
    tmax_values = [d.temp_max for d in daily_data if d.temp_max is not None]
    tmin_values = [d.temp_min for d in daily_data if d.temp_min is not None]
    rh_values = [d.mean_rh for d in daily_data if d.mean_rh is not None]
    sunshine_values = [d.sunshine_hours for d in daily_data if d.sunshine_hours is not None]

    # Find extremes with dates
    max_rainfall = None
    max_rainfall_date = None
    if rainfall_values:
        max_rainfall_day = max(daily_data, key=lambda d: d.rainfall_total if d.rainfall_total else 0)
        max_rainfall = max_rainfall_day.rainfall_total
        max_rainfall_date = max_rainfall_day.date

    max_temp = None
    max_temp_date = None
    if tmax_values:
        max_temp_day = max(daily_data, key=lambda d: d.temp_max if d.temp_max else -999)
        max_temp = max_temp_day.temp_max
        max_temp_date = max_temp_day.date

    min_temp = None
    min_temp_date = None
    if tmin_values:
        min_temp_day = min(daily_data, key=lambda d: d.temp_min if d.temp_min else 999)
        min_temp = min_temp_day.temp_min
        min_temp_date = min_temp_day.date

    # Count extreme events
    rainfall_days = sum(1 for r in rainfall_values if r >= 1.0)
    heavy_rain_days = sum(1 for r in rainfall_values if r > 50.0)
    hot_days_count = sum(1 for t in tmax_values if t > 35.0)
    very_hot_days_count = sum(1 for t in tmax_values if t > 40.0)

    # Calculate mean annual temperature
    temp_mean_annual = None
    if tmax_values and tmin_values:
        temp_max_mean = sum(tmax_values) / len(tmax_values)
        temp_min_mean = sum(tmin_values) / len(tmin_values)
        temp_mean_annual = (temp_max_mean + temp_min_mean) / 2

    # Query climate normal for anomaly calculation
    from app.crud.climate_normals import climate_normal

    normal = await climate_normal.get_annual_normal(db, station_id)

    # Calculate anomalies if normal exists
    rainfall_anomaly = None
    rainfall_anomaly_percent = None
    temp_anomaly = None

    if normal:
        # Rainfall anomalies
        if rainfall_values and normal.rainfall_normal is not None:
            rainfall_total = sum(rainfall_values)
            rainfall_anomaly = compute_climate_anomaly(
                rainfall_total,
                normal.rainfall_normal,
                method='absolute'
            )
            rainfall_anomaly_percent = compute_climate_anomaly(
                rainfall_total,
                normal.rainfall_normal,
                method='percent'
            )
            if rainfall_anomaly is not None:
                rainfall_anomaly = round(rainfall_anomaly, 1)
            if rainfall_anomaly_percent is not None:
                rainfall_anomaly_percent = round(rainfall_anomaly_percent, 1)

        # Temperature anomalies
        if temp_mean_annual is not None and normal.temp_mean_normal is not None:
            temp_anomaly = compute_climate_anomaly(
                temp_mean_annual,
                normal.temp_mean_normal,
                method='absolute'
            )
            if temp_anomaly is not None:
                temp_anomaly = round(temp_anomaly, 1)

    return {
        'station_id': station_id,
        'year': year,

        # Rainfall (WMO: SUM)
        'rainfall_total': round(sum(rainfall_values), 1) if rainfall_values else None,
        'rainfall_anomaly': rainfall_anomaly,
        'rainfall_anomaly_percent': rainfall_anomaly_percent,
        'rainfall_days': rainfall_days if rainfall_values else None,
        'max_daily_rainfall': round(max_rainfall, 1) if max_rainfall else None,
        'max_daily_rainfall_date': max_rainfall_date,

        # Temperature extremes
        'temp_max_absolute': max_temp,
        'temp_max_absolute_date': max_temp_date,
        'temp_min_absolute': min_temp,
        'temp_min_absolute_date': min_temp_date,
        'temp_mean_annual': round(temp_mean_annual, 1) if temp_mean_annual else None,
        'temp_anomaly': temp_anomaly,

        # Extreme event counts
        'hot_days_count': hot_days_count if tmax_values else None,
        'very_hot_days_count': very_hot_days_count if tmax_values else None,
        'heavy_rain_days': heavy_rain_days if rainfall_values else None,

        # Other parameters
        'mean_rh_annual': round(sum(rh_values) / len(rh_values)) if rh_values else None,

        # Sunshine (WMO: SUM)
        'sunshine_total': round(sum(sunshine_values), 1) if sunshine_values else None,

        # Data quality
        'data_completeness_percent': round(data_completeness_percent, 1),
    }
