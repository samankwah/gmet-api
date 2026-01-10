"""
Tests for climate normals computation and CRUD operations.
"""

import pytest
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.station import Station
from app.models.daily_summary import DailySummary
from app.models.climate_normal import ClimateNormal
from app.crud.climate_normals import climate_normal
from scripts.compute_climate_normals import (
    compute_monthly_normal,
    compute_dekadal_normal,
    compute_seasonal_normal,
    compute_annual_normal,
    calculate_data_quality,
    calculate_normal_and_std,
)


class TestClimateNormalCRUD:
    """Test CRUD operations for climate normals."""

    @pytest.mark.asyncio
    async def test_get_monthly_normal(self, db_session: AsyncSession):
        """Test retrieving monthly climate normal."""
        # Create test station
        station = Station(name="Test Station", code="TEST01")
        db_session.add(station)
        await db_session.commit()
        await db_session.refresh(station)

        # Create test normal
        normal = ClimateNormal(
            station_id=station.id,
            normal_period_start=1991,
            normal_period_end=2020,
            timescale='monthly',
            month=1,
            rainfall_normal=150.5,
            rainfall_std=45.2,
            temp_mean_normal=28.5,
            years_with_data=28,
            data_completeness_percent=93.3
        )
        db_session.add(normal)
        await db_session.commit()

        # Query it
        result = await climate_normal.get_monthly_normal(
            db_session, station.id, month=1
        )

        assert result is not None
        assert result.rainfall_normal == 150.5
        assert result.temp_mean_normal == 28.5
        assert result.years_with_data == 28
        assert result.data_completeness_percent == 93.3

    @pytest.mark.asyncio
    async def test_get_monthly_normal_not_found(self, db_session: AsyncSession):
        """Test retrieving monthly normal that doesn't exist."""
        # Create test station
        station = Station(name="Test Station", code="TEST01")
        db_session.add(station)
        await db_session.commit()
        await db_session.refresh(station)

        # Query non-existent normal
        result = await climate_normal.get_monthly_normal(
            db_session, station.id, month=5
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_get_dekadal_normal(self, db_session: AsyncSession):
        """Test retrieving dekadal climate normal."""
        # Create test station
        station = Station(name="Test Station", code="TEST01")
        db_session.add(station)
        await db_session.commit()
        await db_session.refresh(station)

        # Create test normal
        normal = ClimateNormal(
            station_id=station.id,
            normal_period_start=1991,
            normal_period_end=2020,
            timescale='dekadal',
            month=5,
            dekad=2,
            rainfall_normal=45.3,
            years_with_data=25,
            data_completeness_percent=83.3
        )
        db_session.add(normal)
        await db_session.commit()

        # Query it
        result = await climate_normal.get_dekadal_normal(
            db_session, station.id, month=5, dekad=2
        )

        assert result is not None
        assert result.rainfall_normal == 45.3
        assert result.month == 5
        assert result.dekad == 2

    @pytest.mark.asyncio
    async def test_get_seasonal_normal(self, db_session: AsyncSession):
        """Test retrieving seasonal climate normal."""
        # Create test station
        station = Station(name="Test Station", code="TEST01")
        db_session.add(station)
        await db_session.commit()
        await db_session.refresh(station)

        # Create test normal
        normal = ClimateNormal(
            station_id=station.id,
            normal_period_start=1991,
            normal_period_end=2020,
            timescale='seasonal',
            season='MAM',
            rainfall_normal=450.8,
            temp_mean_normal=29.5,
            years_with_data=27,
            data_completeness_percent=90.0
        )
        db_session.add(normal)
        await db_session.commit()

        # Query it
        result = await climate_normal.get_seasonal_normal(
            db_session, station.id, season='MAM'
        )

        assert result is not None
        assert result.rainfall_normal == 450.8
        assert result.season == 'MAM'
        assert result.temp_mean_normal == 29.5

    @pytest.mark.asyncio
    async def test_get_annual_normal(self, db_session: AsyncSession):
        """Test retrieving annual climate normal."""
        # Create test station
        station = Station(name="Test Station", code="TEST01")
        db_session.add(station)
        await db_session.commit()
        await db_session.refresh(station)

        # Create test normal
        normal = ClimateNormal(
            station_id=station.id,
            normal_period_start=1991,
            normal_period_end=2020,
            timescale='annual',
            rainfall_normal=1200.5,
            temp_mean_normal=28.0,
            years_with_data=29,
            data_completeness_percent=96.7
        )
        db_session.add(normal)
        await db_session.commit()

        # Query it
        result = await climate_normal.get_annual_normal(
            db_session, station.id
        )

        assert result is not None
        assert result.rainfall_normal == 1200.5
        assert result.timescale == 'annual'

    @pytest.mark.asyncio
    async def test_get_all_for_station(self, db_session: AsyncSession):
        """Test retrieving all climate normals for a station."""
        # Create test station
        station = Station(name="Test Station", code="TEST01")
        db_session.add(station)
        await db_session.commit()
        await db_session.refresh(station)

        # Create multiple normals
        normals = [
            ClimateNormal(
                station_id=station.id,
                normal_period_start=1991,
                normal_period_end=2020,
                timescale='monthly',
                month=i,
                rainfall_normal=100.0 + i,
                years_with_data=25
            )
            for i in range(1, 13)
        ]
        db_session.add_all(normals)
        await db_session.commit()

        # Query all
        results = await climate_normal.get_all_for_station(
            db_session, station.id
        )

        assert len(results) == 12
        assert all(r.timescale == 'monthly' for r in results)


class TestDataQualityFunctions:
    """Test data quality calculation functions."""

    def test_calculate_data_quality_full(self):
        """Test data quality with all years present."""
        yearly_values = [100.0] * 30  # 30 valid years
        years, completeness = calculate_data_quality(yearly_values, 30)

        assert years == 30
        assert completeness == 100.0

    def test_calculate_data_quality_partial(self):
        """Test data quality with some missing years."""
        yearly_values = [100.0] * 25 + [None] * 5  # 25 valid, 5 missing
        years, completeness = calculate_data_quality(yearly_values, 30)

        assert years == 25
        assert completeness == 83.3

    def test_calculate_data_quality_minimum(self):
        """Test data quality at minimum threshold."""
        yearly_values = [100.0] * 20 + [None] * 10  # 20 valid, 10 missing
        years, completeness = calculate_data_quality(yearly_values, 30)

        assert years == 20
        assert completeness == 66.7  # Just below 67% threshold

    def test_calculate_normal_and_std(self):
        """Test normal and std calculation."""
        values = [100.0, 110.0, 90.0, 105.0, 95.0]
        mean, std = calculate_normal_and_std(values)

        assert mean == 100.0  # (100+110+90+105+95)/5
        assert std > 0  # Should have some variability

    def test_calculate_normal_and_std_empty(self):
        """Test with empty values."""
        values = []
        mean, std = calculate_normal_and_std(values)

        assert mean is None
        assert std is None

    def test_calculate_normal_and_std_single_value(self):
        """Test with single value (std = 0)."""
        values = [100.0]
        mean, std = calculate_normal_and_std(values)

        assert mean == 100.0
        assert std == 0.0


class TestClimateNormalComputation:
    """Test climate normal computation functions."""

    @pytest.mark.asyncio
    async def test_compute_monthly_normal_insufficient_data(self, db_session: AsyncSession):
        """Test monthly normal computation with insufficient data."""
        # Create test station
        station = Station(name="Test Station", code="TEST01")
        db_session.add(station)
        await db_session.commit()
        await db_session.refresh(station)

        # Create data for only 15 years (below 20-year threshold)
        for year in range(1991, 2006):  # Only 15 years
            for day in range(1, 26):  # 25 days per month
                summary = DailySummary(
                    station_id=station.id,
                    date=date(year, 1, day),
                    rainfall_total=10.0,
                    temp_max=32.0,
                    temp_min=24.0
                )
                db_session.add(summary)

        await db_session.commit()

        # Compute normal (should return None due to insufficient years)
        result = await compute_monthly_normal(
            db_session, station.id, month=1,
            period_start=1991, period_end=2020,
            min_years_required=20
        )

        assert result is None  # Not enough years

    @pytest.mark.asyncio
    async def test_compute_monthly_normal_success(self, db_session: AsyncSession):
        """Test successful monthly normal computation."""
        # Create test station
        station = Station(name="Test Station", code="TEST01")
        db_session.add(station)
        await db_session.commit()
        await db_session.refresh(station)

        # Create data for 25 years (above threshold)
        for year in range(1991, 2016):  # 25 years
            for day in range(1, 26):  # 25 days per month
                summary = DailySummary(
                    station_id=station.id,
                    date=date(year, 1, day),
                    rainfall_total=5.0,  # 5mm per day
                    temp_max=32.0,
                    temp_min=24.0
                )
                db_session.add(summary)

        await db_session.commit()

        # Compute normal
        result = await compute_monthly_normal(
            db_session, station.id, month=1,
            period_start=1991, period_end=2020,
            min_years_required=20
        )

        assert result is not None
        assert result['timescale'] == 'monthly'
        assert result['month'] == 1
        assert result['rainfall_normal'] is not None
        assert result['rainfall_normal'] > 0  # Should be ~125mm (25 days × 5mm)
        assert result['years_with_data'] == 25
        assert result['data_completeness_percent'] > 80.0


# Fixture for database session (to be provided by test setup)
@pytest.fixture
async def db_session():
    """
    Provide a database session for tests.

    NOTE: This is a placeholder. In actual tests, this should be configured
    to use a test database with proper setup/teardown.
    """
    from app.database import async_session

    async with async_session() as session:
        yield session
        await session.rollback()
