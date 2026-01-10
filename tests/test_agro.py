"""
Tests for agrometeorological calculation functions.

This module tests:
- Growing Degree Days (GDD) calculations
- Reference Evapotranspiration (ET₀) using Hargreaves method
- Crop water balance calculations
- Rainy season onset/cessation detection
"""

import pytest
from datetime import date
import math

from app.utils.agro import (
    calculate_gdd,
    calculate_extraterrestrial_radiation,
    calculate_et0_hargreaves,
    detect_onset,
    detect_cessation,
    CROP_PARAMETERS,
    SEASON_WINDOWS,
)


class TestGDDCalculation:
    """Test Growing Degree Days calculations."""

    def test_calculate_gdd_average_method(self):
        """Test GDD calculation using average method."""
        # Tmax=32°C, Tmin=22°C, Tbase=10°C
        # Tavg = (32 + 22) / 2 = 27°C
        # GDD = 27 - 10 = 17
        gdd = calculate_gdd(32.0, 22.0, base_temp=10.0, method='average')
        assert gdd == 17.0

    def test_calculate_gdd_modified_method(self):
        """Test GDD calculation using modified method (with upper cap)."""
        # Tmax=35°C (capped at 30°C), Tmin=22°C, Tbase=10°C
        # Tavg = (30 + 22) / 2 = 26°C
        # GDD = 26 - 10 = 16
        gdd = calculate_gdd(35.0, 22.0, base_temp=10.0, upper_temp=30.0, method='modified')
        assert gdd == 16.0

    def test_calculate_gdd_modified_method_tmin_floor(self):
        """Test GDD calculation with Tmin below base temperature."""
        # Tmax=20°C, Tmin=5°C (floored to 10°C), Tbase=10°C
        # Tavg = (20 + 10) / 2 = 15°C
        # GDD = 15 - 10 = 5
        gdd = calculate_gdd(20.0, 5.0, base_temp=10.0, method='modified')
        assert gdd == 5.0

    def test_calculate_gdd_below_base_temp(self):
        """Test GDD when average temperature is below base."""
        # Tmax=12°C, Tmin=8°C, Tbase=10°C
        # Tavg = (12 + 8) / 2 = 10°C
        # GDD = 10 - 10 = 0
        gdd = calculate_gdd(12.0, 8.0, base_temp=10.0, method='average')
        assert gdd == 0.0

    def test_calculate_gdd_negative_prevented(self):
        """Test that negative GDD is prevented."""
        # Cold day: Tmax=5°C, Tmin=0°C, Tbase=10°C
        # Should return 0, not negative
        gdd = calculate_gdd(5.0, 0.0, base_temp=10.0, method='average')
        assert gdd == 0.0

    def test_crop_parameters_exist(self):
        """Test that crop parameters are defined for Ghana crops."""
        assert 'maize' in CROP_PARAMETERS
        assert 'rice' in CROP_PARAMETERS
        assert 'sorghum' in CROP_PARAMETERS

        # Check maize parameters
        maize = CROP_PARAMETERS['maize']
        assert maize['base_temp'] == 10.0
        assert maize['upper_temp'] == 30.0
        assert maize['maturity_gdd'] == 1400


class TestET0Calculation:
    """Test reference evapotranspiration calculations."""

    def test_calculate_extraterrestrial_radiation(self):
        """Test extraterrestrial radiation calculation."""
        # Test for Accra (5.6°N) on March 15 (day 74)
        # Expected Ra ~ 35-40 MJ/m²/day (near equator)
        Ra = calculate_extraterrestrial_radiation(5.6, 74)
        assert 35.0 < Ra < 40.0

    def test_extraterrestrial_radiation_equator(self):
        """Test Ra at equator during equinox."""
        # At equator (0°) on March 21 (day 80), Ra should be high
        Ra = calculate_extraterrestrial_radiation(0.0, 80)
        assert Ra > 35.0

    def test_extraterrestrial_radiation_seasonal_variation(self):
        """Test that Ra varies by season at same location."""
        # Accra (5.6°N)
        Ra_march = calculate_extraterrestrial_radiation(5.6, 80)  # March
        Ra_december = calculate_extraterrestrial_radiation(5.6, 355)  # December

        # Ra should be different between seasons
        assert Ra_march != Ra_december

    def test_calculate_et0_hargreaves(self):
        """Test ET₀ calculation using Hargreaves method."""
        # Accra (5.6°N) on March 15 (day 74)
        # Tmax=32°C, Tmin=24°C
        # Expected ET₀: 3-6 mm/day for tropical coastal area
        et0 = calculate_et0_hargreaves(32.0, 24.0, 5.6, 74)
        assert 3.0 < et0 < 6.0

    def test_et0_higher_temp_range_increases_et0(self):
        """Test that larger temperature range increases ET₀."""
        # Same Tmean, different ranges
        # Narrow range: Tmax=28°C, Tmin=26°C (diff=2°C)
        et0_narrow = calculate_et0_hargreaves(28.0, 26.0, 5.6, 74)

        # Wide range: Tmax=32°C, Tmin=22°C (diff=10°C)
        et0_wide = calculate_et0_hargreaves(32.0, 22.0, 5.6, 74)

        # Wider temperature range should give higher ET₀
        assert et0_wide > et0_narrow

    def test_et0_not_negative(self):
        """Test that ET₀ cannot be negative."""
        # Even with unusual conditions, ET₀ should not be negative
        et0 = calculate_et0_hargreaves(15.0, 10.0, 5.6, 1)
        assert et0 >= 0.0


class TestOnsetCessationDetection:
    """Test rainy season onset and cessation detection."""

    def test_detect_onset_valid(self):
        """Test detection of valid onset."""
        # Create rainfall data with valid onset on March 18
        # Days 15-17: low rain, Days 18-20: 25mm total, Days 21-37: scattered rain
        daily_rainfall = []

        # March 1-17: little rain
        for day in range(1, 18):
            daily_rainfall.append((date(2024, 3, day), 0.5))

        # March 18-20: 25mm total (meets 20mm in 3 days threshold)
        daily_rainfall.append((date(2024, 3, 18), 8.0))
        daily_rainfall.append((date(2024, 3, 19), 10.0))
        daily_rainfall.append((date(2024, 3, 20), 7.0))

        # March 21-April 7: scattered rain (no 7-day dry spell)
        for day in range(21, 32):
            daily_rainfall.append((date(2024, 3, day), 2.0))
        for day in range(1, 8):
            daily_rainfall.append((date(2024, 4, day), 3.0))

        onset = detect_onset(
            daily_rainfall,
            start_search_date=date(2024, 3, 1),
            end_search_date=date(2024, 4, 30)
        )

        assert onset == date(2024, 3, 18)

    def test_detect_onset_false_start(self):
        """Test rejection of false start (7-day dry spell after onset)."""
        daily_rainfall = []

        # March 15-17: 25mm total (meets threshold)
        daily_rainfall.append((date(2024, 3, 15), 8.0))
        daily_rainfall.append((date(2024, 3, 16), 10.0))
        daily_rainfall.append((date(2024, 3, 17), 7.0))

        # March 18-24: 7-day dry spell (invalidates onset)
        for day in range(18, 25):
            daily_rainfall.append((date(2024, 3, day), 0.2))

        # March 25-27: 25mm total (new valid onset)
        daily_rainfall.append((date(2024, 3, 25), 8.0))
        daily_rainfall.append((date(2024, 3, 26), 10.0))
        daily_rainfall.append((date(2024, 3, 27), 7.0))

        # March 28-April 15: regular rain
        for day in range(28, 32):
            daily_rainfall.append((date(2024, 3, day), 3.0))
        for day in range(1, 16):
            daily_rainfall.append((date(2024, 4, day), 3.0))

        onset = detect_onset(
            daily_rainfall,
            start_search_date=date(2024, 3, 1),
            end_search_date=date(2024, 4, 30)
        )

        # Should detect March 25, not March 15 (false start)
        assert onset == date(2024, 3, 25)

    def test_detect_onset_not_found(self):
        """Test when no valid onset exists."""
        # Dry period with no 20mm in 3 days
        daily_rainfall = []
        for day in range(1, 32):
            daily_rainfall.append((date(2024, 3, day), 2.0))
        for day in range(1, 31):
            daily_rainfall.append((date(2024, 4, day), 2.0))

        onset = detect_onset(
            daily_rainfall,
            start_search_date=date(2024, 3, 1),
            end_search_date=date(2024, 4, 30)
        )

        assert onset is None

    def test_detect_cessation_valid(self):
        """Test detection of valid cessation."""
        # Create rainfall with cessation on May 20
        daily_rainfall = []

        # March-May: regular rain
        for day in range(1, 32):  # March
            daily_rainfall.append((date(2024, 3, day), 3.0))
        for day in range(1, 31):  # April
            daily_rainfall.append((date(2024, 4, day), 3.0))
        for day in range(1, 21):  # May 1-20: last rainy day
            daily_rainfall.append((date(2024, 5, day), 3.0))

        # May 21-June 9: dry spell (< 10mm in 20 days)
        for day in range(21, 32):
            daily_rainfall.append((date(2024, 5, day), 0.2))
        for day in range(1, 10):
            daily_rainfall.append((date(2024, 6, day), 0.2))

        cessation = detect_cessation(
            daily_rainfall,
            onset_date=date(2024, 3, 18),
            end_search_date=date(2024, 6, 30)
        )

        # Should detect last rainy day before dry spell
        assert cessation is not None
        # The function should find the last day with >= 1mm before the dry period
        # Days 1-20 have 3mm each, so last rainy day is May 20 or earlier
        assert date(2024, 5, 18) <= cessation <= date(2024, 5, 20)

    def test_detect_cessation_season_continues(self):
        """Test when season hasn't ended yet."""
        # Continuous rain with no cessation
        daily_rainfall = []

        for day in range(1, 32):  # March
            daily_rainfall.append((date(2024, 3, day), 3.0))
        for day in range(1, 31):  # April
            daily_rainfall.append((date(2024, 4, day), 3.0))
        for day in range(1, 32):  # May
            daily_rainfall.append((date(2024, 5, day), 3.0))
        for day in range(1, 31):  # June
            daily_rainfall.append((date(2024, 6, day), 3.0))

        cessation = detect_cessation(
            daily_rainfall,
            onset_date=date(2024, 3, 18),
            end_search_date=date(2024, 6, 30)
        )

        # No cessation found (season continues)
        assert cessation is None

    def test_season_windows_defined(self):
        """Test that season search windows are properly defined."""
        assert 'MAM' in SEASON_WINDOWS
        assert 'JJA' in SEASON_WINDOWS

        # Check MAM windows
        mam = SEASON_WINDOWS['MAM']
        assert mam['onset_start'] == (3, 1)  # March 1
        assert mam['onset_end'] == (4, 30)  # April 30
        assert mam['cessation_end'] == (6, 30)  # June 30

        # Check JJA windows
        jja = SEASON_WINDOWS['JJA']
        assert jja['onset_start'] == (6, 1)  # June 1
        assert jja['onset_end'] == (7, 15)  # July 15


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_gdd_identical_tmax_tmin(self):
        """Test GDD when Tmax == Tmin."""
        # Tmax=25°C, Tmin=25°C, Tbase=10°C
        # GDD = 25 - 10 = 15
        gdd = calculate_gdd(25.0, 25.0, base_temp=10.0)
        assert gdd == 15.0

    def test_et0_zero_temp_range(self):
        """Test ET₀ when Tmax == Tmin."""
        # When temp range is zero, sqrt(0) = 0, ET₀ should be near zero
        et0 = calculate_et0_hargreaves(25.0, 25.0, 5.6, 74)
        assert et0 >= 0.0
        assert et0 < 1.0  # Should be very low

    def test_extraterrestrial_radiation_high_latitude(self):
        """Test Ra at higher latitude (edge of tropics)."""
        # Northern Ghana (10°N)
        Ra = calculate_extraterrestrial_radiation(10.0, 74)
        assert Ra > 0.0  # Should be positive

    def test_detect_onset_empty_data(self):
        """Test onset detection with empty rainfall data."""
        onset = detect_onset(
            [],
            start_search_date=date(2024, 3, 1),
            end_search_date=date(2024, 4, 30)
        )
        assert onset is None

    def test_detect_onset_sparse_data(self):
        """Test onset detection with sparse data."""
        # Only a few days of data
        daily_rainfall = [
            (date(2024, 3, 15), 10.0),
            (date(2024, 3, 20), 5.0),
            (date(2024, 3, 25), 8.0),
        ]

        onset = detect_onset(
            daily_rainfall,
            start_search_date=date(2024, 3, 1),
            end_search_date=date(2024, 4, 30)
        )

        # Should not find onset (gaps in data)
        assert onset is None


class TestWMOCompliance:
    """Test WMO agrometeorology guideline compliance."""

    def test_onset_criteria_20mm_3days(self):
        """Test that onset requires exactly 20mm in 3 days."""
        # Test threshold boundary: 19.9mm (should fail)
        daily_rainfall_fail = [
            (date(2024, 3, 18), 6.6),
            (date(2024, 3, 19), 6.6),
            (date(2024, 3, 20), 6.7),  # Total: 19.9mm
        ]
        # Add remaining March days
        for day in range(21, 32):
            daily_rainfall_fail.append((date(2024, 3, day), 2.0))
        # Add April days
        for day in range(1, 8):
            daily_rainfall_fail.append((date(2024, 4, day), 2.0))

        onset_fail = detect_onset(
            daily_rainfall_fail,
            start_search_date=date(2024, 3, 1),
            end_search_date=date(2024, 4, 30),
            onset_threshold_mm=20.0
        )
        assert onset_fail is None

        # Test threshold met: 20.1mm (should pass)
        daily_rainfall_pass = [
            (date(2024, 3, 18), 6.7),
            (date(2024, 3, 19), 6.7),
            (date(2024, 3, 20), 6.7),  # Total: 20.1mm
        ]
        # Add remaining March days
        for day in range(21, 32):
            daily_rainfall_pass.append((date(2024, 3, day), 2.0))
        # Add April days
        for day in range(1, 8):
            daily_rainfall_pass.append((date(2024, 4, day), 2.0))

        onset_pass = detect_onset(
            daily_rainfall_pass,
            start_search_date=date(2024, 3, 1),
            end_search_date=date(2024, 4, 30),
            onset_threshold_mm=20.0
        )
        assert onset_pass == date(2024, 3, 18)

    def test_false_start_7day_dry_spell(self):
        """Test that 7-day dry spell invalidates onset."""
        # 6-day dry spell (should pass - not enough to invalidate)
        daily_rainfall_6days = []
        daily_rainfall_6days.append((date(2024, 3, 18), 8.0))
        daily_rainfall_6days.append((date(2024, 3, 19), 8.0))
        daily_rainfall_6days.append((date(2024, 3, 20), 8.0))
        # 6 dry days (< 1mm) - days 21-26
        for day in range(21, 27):
            daily_rainfall_6days.append((date(2024, 3, day), 0.5))
        # Rain resumes - need full 20-day check period
        for day in range(27, 32):  # March 27-31
            daily_rainfall_6days.append((date(2024, 3, day), 3.0))
        for day in range(1, 8):  # April 1-7 (to complete 20-day check)
            daily_rainfall_6days.append((date(2024, 4, day), 3.0))

        onset_6days = detect_onset(
            daily_rainfall_6days,
            start_search_date=date(2024, 3, 1),
            end_search_date=date(2024, 4, 30)
        )
        assert onset_6days == date(2024, 3, 18)  # Valid onset (only 6-day dry spell)

    def test_cessation_criteria_10mm_20days(self):
        """Test that cessation requires <10mm in 20 days."""
        daily_rainfall = []

        # Regular rain until May 15
        for day in range(1, 32):
            daily_rainfall.append((date(2024, 3, day), 3.0))
        for day in range(1, 16):
            daily_rainfall.append((date(2024, 5, day), 3.0))

        # Dry period: 9.5mm in 20 days (should trigger cessation)
        for day in range(16, 32):
            daily_rainfall.append((date(2024, 5, day), 0.3))
        for day in range(1, 5):
            daily_rainfall.append((date(2024, 6, day), 0.3))

        cessation = detect_cessation(
            daily_rainfall,
            onset_date=date(2024, 3, 18),
            end_search_date=date(2024, 6, 30),
            cessation_threshold_mm=10.0
        )

        assert cessation is not None
        assert cessation <= date(2024, 5, 16)
