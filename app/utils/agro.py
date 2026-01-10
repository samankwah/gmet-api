"""
Agrometeorological calculation functions for the GMet Weather API.

This module provides functions for agricultural meteorology products:
- Growing Degree Days (GDD) for crop development tracking
- Reference Evapotranspiration (ET₀) using Hargreaves method
- Crop water balance calculations
- Onset/cessation detection for rainy seasons

References:
- McMaster & Wilhelm (1997): Growing degree-days methods
- Hargreaves & Samani (1985): Reference crop evapotranspiration from temperature
- Allen et al. (1998): FAO Irrigation and Drainage Paper No. 56
- Sivakumar (1988): Predicting rainy season potential from onset of rains
- WMO (2010): Guide to Agricultural Meteorological Practices (GAMP)
"""

import math
from datetime import date, timedelta
from typing import Optional, Dict, List, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from app.models.daily_summary import DailySummary
from app.models.station import Station


# Crop-specific parameters for Ghana
CROP_PARAMETERS = {
    'maize': {
        'base_temp': 10.0,  # Base temperature (°C)
        'upper_temp': 30.0,  # Upper threshold temperature (°C)
        'maturity_gdd': 1400,  # GDD to maturity (90-110 day varieties)
        'kc_values': {  # Crop coefficients by growth stage
            'initial': 0.3,
            'development': 0.7,
            'mid_season': 1.2,
            'late_season': 0.6
        },
        'critical_stages': {
            'emergence': 100,
            'tasseling': 800,
            'grain_fill': 1200,
            'maturity': 1400
        }
    },
    'rice': {
        'base_temp': 10.0,
        'upper_temp': 35.0,
        'maturity_gdd': 2000,  # GDD to maturity (120-150 days)
        'kc_values': {
            'initial': 1.0,  # Flooded rice
            'development': 1.1,
            'mid_season': 1.2,
            'late_season': 0.9
        },
        'critical_stages': {
            'emergence': 120,
            'tillering': 600,
            'flowering': 1400,
            'maturity': 2000
        }
    },
    'sorghum': {
        'base_temp': 8.0,
        'upper_temp': 35.0,
        'maturity_gdd': 1600,  # GDD to maturity (100-130 days)
        'kc_values': {
            'initial': 0.3,
            'development': 0.7,
            'mid_season': 1.0,
            'late_season': 0.5
        },
        'critical_stages': {
            'emergence': 100,
            'flag_leaf': 900,
            'flowering': 1200,
            'maturity': 1600
        }
    }
}

# Season-specific search windows for onset/cessation
SEASON_WINDOWS = {
    'MAM': {
        'onset_start': (3, 1),  # March 1
        'onset_end': (4, 30),  # April 30
        'cessation_start': (5, 15),  # May 15
        'cessation_end': (6, 30),  # June 30
    },
    'JJA': {
        'onset_start': (6, 1),  # June 1
        'onset_end': (7, 15),  # July 15
        'cessation_start': (8, 1),  # August 1
        'cessation_end': (9, 30),  # September 30
    }
}


def calculate_gdd(
    temp_max: float,
    temp_min: float,
    base_temp: float,
    upper_temp: Optional[float] = None,
    method: str = 'modified'
) -> float:
    """
    Calculate Growing Degree Days using specified method.

    Methods:
    - 'average': GDD = ((Tmax + Tmin) / 2) - Tbase
    - 'modified': Caps Tmax at upper limit, floors Tmin at Tbase (recommended)

    Crop-specific base temperatures (Ghana):
    - Maize: 10°C (upper: 30°C)
    - Rice: 10°C (upper: 35°C)
    - Sorghum: 8°C (upper: 35°C)

    Args:
        temp_max: Daily maximum temperature (°C)
        temp_min: Daily minimum temperature (°C)
        base_temp: Base temperature for crop (°C)
        upper_temp: Upper threshold temperature (optional)
        method: Calculation method ('average' or 'modified')

    Returns:
        GDD value for the day (degree-days)

    Example:
        # Maize GDD for a day with Tmax=32°C, Tmin=22°C
        gdd = calculate_gdd(32, 22, base_temp=10, upper_temp=30)
        # Result: 17 GDD (capped at 30°C max)
    """
    if method == 'modified':
        # Modified method: cap temperatures at thresholds
        tmax_adj = min(temp_max, upper_temp) if upper_temp else temp_max
        tmin_adj = max(temp_min, base_temp)
        tavg = (tmax_adj + tmin_adj) / 2
        gdd = max(0, tavg - base_temp)
    else:
        # Average method
        tavg = (temp_max + temp_min) / 2
        gdd = max(0, tavg - base_temp)

    return gdd


async def compute_gdd_accumulation(
    db: AsyncSession,
    station_id: int,
    start_date: date,
    end_date: date,
    crop: str
) -> Optional[Dict]:
    """
    Compute accumulated GDD for a crop over date range.

    Args:
        db: Database session
        station_id: Station ID
        start_date: Start date for accumulation
        end_date: End date for accumulation
        crop: Crop type ('maize', 'rice', or 'sorghum')

    Returns:
        Dictionary with GDD accumulation data or None if insufficient data

    Example:
        gdd_data = await compute_gdd_accumulation(
            db, station_id=1,
            start_date=date(2024, 3, 15),
            end_date=date(2024, 6, 30),
            crop='maize'
        )
    """
    if crop not in CROP_PARAMETERS:
        return None

    crop_params = CROP_PARAMETERS[crop]
    base_temp = crop_params['base_temp']
    upper_temp = crop_params['upper_temp']

    # Query daily temperature data
    stmt = select(DailySummary).where(
        and_(
            DailySummary.station_id == station_id,
            DailySummary.date >= start_date,
            DailySummary.date <= end_date,
            DailySummary.temp_max.isnot(None),
            DailySummary.temp_min.isnot(None)
        )
    ).order_by(DailySummary.date)

    result = await db.execute(stmt)
    daily_summaries = result.scalars().all()

    if not daily_summaries:
        return None

    # Calculate GDD for each day
    gdd_total = 0.0
    days_count = 0

    for summary in daily_summaries:
        gdd_day = calculate_gdd(
            summary.temp_max,
            summary.temp_min,
            base_temp,
            upper_temp,
            method='modified'
        )
        gdd_total += gdd_day
        days_count += 1

    # Determine crop stage
    crop_stage = None
    days_to_maturity = None

    for stage_name, stage_gdd in crop_params['critical_stages'].items():
        if gdd_total >= stage_gdd:
            crop_stage = stage_name
        else:
            break

    # Estimate days to maturity
    if gdd_total < crop_params['maturity_gdd'] and days_count > 0:
        avg_gdd_per_day = gdd_total / days_count
        if avg_gdd_per_day > 0:
            remaining_gdd = crop_params['maturity_gdd'] - gdd_total
            days_to_maturity = int(remaining_gdd / avg_gdd_per_day)

    return {
        'station_id': station_id,
        'crop': crop,
        'start_date': start_date,
        'end_date': end_date,
        'gdd_accumulated': round(gdd_total, 1),
        'days_count': days_count,
        'average_gdd_per_day': round(gdd_total / days_count, 1) if days_count > 0 else 0,
        'base_temp': base_temp,
        'upper_temp': upper_temp,
        'crop_stage': crop_stage,
        'days_to_maturity': days_to_maturity,
        'maturity_gdd': crop_params['maturity_gdd']
    }


def calculate_extraterrestrial_radiation(
    latitude: float,
    julian_day: int
) -> float:
    """
    Calculate daily extraterrestrial radiation (Ra).

    Used in Hargreaves ET₀ equation.
    Based on FAO-56 methodology (Allen et al., 1998).

    Args:
        latitude: Latitude in decimal degrees
        julian_day: Day of year (1-365/366)

    Returns:
        Ra in MJ/m²/day

    Reference:
        Allen, R.G., Pereira, L.S., Raes, D., Smith, M. (1998).
        FAO Irrigation and Drainage Paper No. 56: Crop Evapotranspiration.
    """
    # Convert latitude to radians
    lat_rad = latitude * math.pi / 180.0

    # Solar declination (radians)
    declination = 0.409 * math.sin((2 * math.pi / 365) * julian_day - 1.39)

    # Sunset hour angle (radians)
    ws = math.acos(-math.tan(lat_rad) * math.tan(declination))

    # Inverse relative distance Earth-Sun
    dr = 1 + 0.033 * math.cos(2 * math.pi * julian_day / 365)

    # Solar constant
    Gsc = 0.0820  # MJ/m²/min

    # Extraterrestrial radiation (MJ/m²/day)
    Ra = (24 * 60 / math.pi) * Gsc * dr * (
        ws * math.sin(lat_rad) * math.sin(declination) +
        math.cos(lat_rad) * math.cos(declination) * math.sin(ws)
    )

    return Ra


def calculate_et0_hargreaves(
    temp_max: float,
    temp_min: float,
    latitude: float,
    julian_day: int
) -> float:
    """
    Calculate reference evapotranspiration using Hargreaves method.

    Hargreaves equation (simplified, no radiation data needed):
    ET₀ = 0.0023 × (Tmean + 17.8) × (Tmax - Tmin)^0.5 × Ra

    Where:
    - Tmean = (Tmax + Tmin) / 2
    - Ra = extraterrestrial radiation (calculated from latitude and day of year)

    Advantages:
    - Only requires temperature data (Tmax, Tmin)
    - Suitable for Ghana where radiation data is sparse
    - Reasonably accurate for tropical regions (±10% of Penman-Monteith)

    Args:
        temp_max: Daily maximum temperature (°C)
        temp_min: Daily minimum temperature (°C)
        latitude: Station latitude (degrees)
        julian_day: Day of year (1-365/366)

    Returns:
        ET₀ in mm/day

    Example:
        # For Accra (5.6°N) on March 15 (day 74)
        et0 = calculate_et0_hargreaves(32.0, 24.0, 5.6, 74)
        # Result: ~4.5 mm/day

    Reference:
        Hargreaves, G.H., Samani, Z.A. (1985). Reference crop
        evapotranspiration from temperature. Applied Engineering
        in Agriculture, 1(2), 96-99.
    """
    # Mean temperature
    temp_mean = (temp_max + temp_min) / 2

    # Temperature difference
    temp_diff = temp_max - temp_min

    # Extraterrestrial radiation
    Ra = calculate_extraterrestrial_radiation(latitude, julian_day)

    # Hargreaves equation
    # Ra is in MJ/m²/day, multiply by 0.408 to convert to mm/day equivalent
    et0 = 0.0023 * (temp_mean + 17.8) * math.sqrt(temp_diff) * Ra * 0.408

    return max(0, et0)


async def compute_et0_series(
    db: AsyncSession,
    station_id: int,
    start_date: date,
    end_date: date
) -> List[Dict]:
    """
    Compute ET₀ time series for a station.

    Args:
        db: Database session
        station_id: Station ID
        start_date: Start date
        end_date: End date

    Returns:
        List of daily ET₀ values with dates
    """
    # Get station to retrieve latitude
    stmt_station = select(Station).where(Station.id == station_id)
    result = await db.execute(stmt_station)
    station = result.scalar_one_or_none()

    if not station or station.latitude is None:
        return []

    # Query daily temperature data
    stmt = select(DailySummary).where(
        and_(
            DailySummary.station_id == station_id,
            DailySummary.date >= start_date,
            DailySummary.date <= end_date,
            DailySummary.temp_max.isnot(None),
            DailySummary.temp_min.isnot(None)
        )
    ).order_by(DailySummary.date)

    result = await db.execute(stmt)
    daily_summaries = result.scalars().all()

    et0_series = []
    for summary in daily_summaries:
        julian_day = summary.date.timetuple().tm_yday

        et0 = calculate_et0_hargreaves(
            summary.temp_max,
            summary.temp_min,
            station.latitude,
            julian_day
        )

        et0_series.append({
            'observation_date': summary.date,
            'et0_mm': round(et0, 2),
            'temp_max': summary.temp_max,
            'temp_min': summary.temp_min
        })

    return et0_series


async def compute_water_balance(
    db: AsyncSession,
    station_id: int,
    start_date: date,
    end_date: date,
    crop: str
) -> Optional[Dict]:
    """
    Compute crop water balance (rainfall - ET₀).

    Water balance equation:
    ΔS = P - ETc - D

    Where:
    - ΔS = Change in soil moisture
    - P = Precipitation (rainfall)
    - ETc = Crop evapotranspiration (ET₀ × Kc)
    - D = Drainage (assumed 0 for daily calculations)

    Crop coefficient (Kc) adjustments:
    - Maize: Kc varies 0.3-1.2 by growth stage
    - Rice: Kc varies 1.0-1.2 (flooded)
    - Sorghum: Kc varies 0.3-1.0

    Args:
        db: Database session
        station_id: Station ID
        start_date: Start date
        end_date: End date
        crop: Crop type ('maize', 'rice', or 'sorghum')

    Returns:
        Dictionary with water balance data or None if insufficient data
    """
    if crop not in CROP_PARAMETERS:
        return None

    crop_params = CROP_PARAMETERS[crop]

    # Get station for latitude
    stmt_station = select(Station).where(Station.id == station_id)
    result = await db.execute(stmt_station)
    station = result.scalar_one_or_none()

    if not station or station.latitude is None:
        return None

    # Query daily data
    stmt = select(DailySummary).where(
        and_(
            DailySummary.station_id == station_id,
            DailySummary.date >= start_date,
            DailySummary.date <= end_date,
            DailySummary.temp_max.isnot(None),
            DailySummary.temp_min.isnot(None)
        )
    ).order_by(DailySummary.date)

    result = await db.execute(stmt)
    daily_summaries = result.scalars().all()

    if not daily_summaries:
        return None

    # Calculate daily water balance
    total_rainfall = 0.0
    total_et0 = 0.0
    total_etc = 0.0
    deficit_days = 0
    surplus_days = 0
    irrigation_requirement = 0.0
    daily_values = []

    # Use average Kc for simplicity (can be enhanced with growth stage tracking)
    kc_avg = sum(crop_params['kc_values'].values()) / len(crop_params['kc_values'])

    for summary in daily_summaries:
        # Calculate ET₀
        julian_day = summary.date.timetuple().tm_yday
        et0 = calculate_et0_hargreaves(
            summary.temp_max,
            summary.temp_min,
            station.latitude,
            julian_day
        )

        # Calculate crop ET (ETc = ET₀ × Kc)
        etc = et0 * kc_avg

        # Rainfall
        rainfall = summary.rainfall_total if summary.rainfall_total else 0.0

        # Daily water balance
        water_balance_day = rainfall - etc

        # Accumulate totals
        total_rainfall += rainfall
        total_et0 += et0
        total_etc += etc

        if water_balance_day < 0:
            deficit_days += 1
            irrigation_requirement += abs(water_balance_day)
        else:
            surplus_days += 1

        daily_values.append({
            'observation_date': summary.date,
            'rainfall_mm': round(rainfall, 1),
            'et0_mm': round(et0, 2),
            'etc_mm': round(etc, 2),
            'water_balance_mm': round(water_balance_day, 2)
        })

    # Water stress index (deficit as % of ETc)
    water_stress_index = (irrigation_requirement / total_etc * 100) if total_etc > 0 else 0

    return {
        'station_id': station_id,
        'crop': crop,
        'start_date': start_date,
        'end_date': end_date,
        'total_rainfall_mm': round(total_rainfall, 1),
        'total_et0_mm': round(total_et0, 1),
        'total_etc_mm': round(total_etc, 1),
        'water_balance_mm': round(total_rainfall - total_etc, 1),
        'deficit_days': deficit_days,
        'surplus_days': surplus_days,
        'irrigation_requirement_mm': round(irrigation_requirement, 1),
        'water_stress_index': round(water_stress_index, 1),
        'kc_avg': round(kc_avg, 2),
        'daily_values': daily_values
    }


def detect_onset(
    daily_rainfall: List[Tuple[date, float]],
    start_search_date: date,
    end_search_date: date,
    onset_threshold_mm: float = 20.0,
    onset_days: int = 3,
    false_start_dry_spell_days: int = 7,
    false_start_check_days: int = 20
) -> Optional[date]:
    """
    Detect rainy season onset using WMO agrometeorology criteria.

    WMO Onset Definition (adapted for Ghana):
    1. First occurrence after start_search_date where:
       - Cumulative rainfall >= 20mm in 3 consecutive days
    2. AND no dry spell >= 7 days in the following 20 days
       (dry spell = consecutive days with < 1mm rain)

    Ghana-specific adjustments:
    - MAM onset: Search March 1 - April 30
    - JJA onset: Search June 1 - July 15

    Args:
        daily_rainfall: List of (date, rainfall_mm) tuples sorted by date
        start_search_date: When to start looking for onset
        end_search_date: When to stop looking for onset
        onset_threshold_mm: Cumulative rainfall threshold (default: 20mm)
        onset_days: Days to accumulate rainfall (default: 3)
        false_start_dry_spell_days: Dry spell length to invalidate onset (default: 7)
        false_start_check_days: Days to check for false starts (default: 20)

    Returns:
        Onset date or None if no valid onset found

    Reference:
        Sivakumar, M.V.K. (1988). Predicting rainy season potential from
        the onset of rains in Southern Sahelian and Sudanian climatic
        zones of West Africa. Agricultural and Forest Meteorology, 42(4), 295-305.
    """
    # Convert to dictionary for easy lookup
    rainfall_dict = {d: r for d, r in daily_rainfall}

    # Search for potential onset dates
    current_date = start_search_date

    while current_date <= end_search_date:
        # Check if we have 3 consecutive days with cumulative >= 20mm
        cumulative = 0.0
        valid_onset_window = True

        for i in range(onset_days):
            check_date = current_date + timedelta(days=i)
            if check_date in rainfall_dict:
                cumulative += rainfall_dict[check_date]
            else:
                valid_onset_window = False
                break

        # If cumulative threshold met, check for false starts
        if valid_onset_window and cumulative >= onset_threshold_mm:
            # Check next 20 days for dry spell >= 7 days
            is_false_start = False
            consecutive_dry_days = 0

            for i in range(false_start_check_days):
                check_date = current_date + timedelta(days=onset_days + i)
                if check_date in rainfall_dict:
                    rainfall = rainfall_dict[check_date]
                    if rainfall < 1.0:  # Dry day threshold
                        consecutive_dry_days += 1
                        if consecutive_dry_days >= false_start_dry_spell_days:
                            is_false_start = True
                            break
                    else:
                        consecutive_dry_days = 0
                else:
                    # Missing data - be conservative and assume dry
                    consecutive_dry_days += 1
                    if consecutive_dry_days >= false_start_dry_spell_days:
                        is_false_start = True
                        break

            # Valid onset found
            if not is_false_start:
                return current_date

        current_date += timedelta(days=1)

    return None


def detect_cessation(
    daily_rainfall: List[Tuple[date, float]],
    onset_date: date,
    end_search_date: date,
    cessation_threshold_mm: float = 10.0,
    cessation_days: int = 20
) -> Optional[date]:
    """
    Detect rainy season cessation.

    WMO Cessation Definition:
    Last day with rainfall before a period where:
    - Cumulative rainfall < 10mm in 20 consecutive days

    Must occur after the onset date.

    Args:
        daily_rainfall: List of (date, rainfall_mm) tuples sorted by date
        onset_date: Previously detected onset date
        end_search_date: When to stop looking for cessation
        cessation_threshold_mm: Max cumulative rainfall (default: 10mm)
        cessation_days: Days to check for low rainfall (default: 20)

    Returns:
        Cessation date or None if season hasn't ended
    """
    # Convert to dictionary
    rainfall_dict = {d: r for d, r in daily_rainfall}

    # Start searching after onset
    current_date = onset_date + timedelta(days=1)
    last_rainy_date = None

    while current_date <= end_search_date:
        # Check cumulative rainfall in next 20 days
        cumulative = 0.0
        data_available = True

        for i in range(cessation_days):
            check_date = current_date + timedelta(days=i)
            if check_date in rainfall_dict:
                cumulative += rainfall_dict[check_date]
            else:
                # If we don't have data for the full period, can't confirm cessation
                data_available = False
                break

        # If cumulative < threshold, cessation occurred
        if data_available and cumulative < cessation_threshold_mm:
            # Find the last day with significant rain before this dry period
            # Go back from current_date to find last rainy day
            search_back_date = current_date - timedelta(days=1)
            while search_back_date >= onset_date:
                if search_back_date in rainfall_dict:
                    if rainfall_dict[search_back_date] >= 1.0:  # Significant rain
                        return search_back_date
                search_back_date -= timedelta(days=1)

            # If no rainy day found, return day before dry period started
            return current_date - timedelta(days=1)

        current_date += timedelta(days=1)

    return None


async def compute_onset_cessation_for_season(
    db: AsyncSession,
    station_id: int,
    year: int,
    season: str
) -> Dict:
    """
    Compute onset and cessation for a specific season.

    Season-specific search windows:
    - MAM: Onset search Mar 1 - Apr 30, Cessation search May 1 - Jun 30
    - JJA: Onset search Jun 1 - Jul 15, Cessation search Aug 1 - Sep 30
    - SON: (Typically dry season transition, less critical)
    - DJF: (Dry season, no onset/cessation)

    Args:
        db: Database session
        station_id: Station ID
        year: Year
        season: Season code ('MAM', 'JJA', 'SON', 'DJF')

    Returns:
        Dictionary with onset/cessation data
    """
    if season not in SEASON_WINDOWS:
        # No onset/cessation for SON and DJF (dry seasons)
        return {
            'station_id': station_id,
            'year': year,
            'season': season,
            'onset_date': None,
            'cessation_date': None,
            'season_length_days': None,
            'search_window_start': None,
            'search_window_end': None,
            'status': 'not_applicable'
        }

    windows = SEASON_WINDOWS[season]

    # Create search window dates
    onset_start = date(year, windows['onset_start'][0], windows['onset_start'][1])
    onset_end = date(year, windows['onset_end'][0], windows['onset_end'][1])
    cessation_end = date(year, windows['cessation_end'][0], windows['cessation_end'][1])

    # Query daily rainfall data for entire period
    stmt = select(DailySummary).where(
        and_(
            DailySummary.station_id == station_id,
            DailySummary.date >= onset_start,
            DailySummary.date <= cessation_end
        )
    ).order_by(DailySummary.date)

    result = await db.execute(stmt)
    daily_summaries = result.scalars().all()

    # Convert to list of tuples
    daily_rainfall = [
        (summary.date, summary.rainfall_total if summary.rainfall_total else 0.0)
        for summary in daily_summaries
    ]

    if not daily_rainfall:
        return {
            'station_id': station_id,
            'year': year,
            'season': season,
            'onset_date': None,
            'cessation_date': None,
            'season_length_days': None,
            'search_window_start': onset_start,
            'search_window_end': cessation_end,
            'status': 'no_data'
        }

    # Detect onset
    onset_date = detect_onset(
        daily_rainfall,
        onset_start,
        onset_end
    )

    # Detect cessation (only if onset was detected)
    cessation_date = None
    season_length_days = None

    if onset_date:
        cessation_date = detect_cessation(
            daily_rainfall,
            onset_date,
            cessation_end
        )

        if cessation_date:
            season_length_days = (cessation_date - onset_date).days

    # Determine status
    if onset_date and cessation_date:
        status = 'detected'
    elif onset_date and not cessation_date:
        status = 'pending'  # Season started but hasn't ended yet
    else:
        status = 'not_found'

    return {
        'station_id': station_id,
        'year': year,
        'season': season,
        'onset_date': onset_date,
        'cessation_date': cessation_date,
        'season_length_days': season_length_days,
        'search_window_start': onset_start,
        'search_window_end': cessation_end,
        'status': status
    }
