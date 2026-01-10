"""
Climate products CRUD operations.

This module handles querying and computing climate aggregations following the
hybrid compute strategy:
- Check cache first (database tables)
- Compute on-demand if not cached
- Save result for future requests

All operations follow WMO aggregation standards.
"""

from datetime import date
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc

from app.models.weekly_summary import WeeklySummary
from app.models.monthly_summary import MonthlySummary
from app.models.dekadal_summary import DekadalSummary
from app.models.seasonal_summary import SeasonalSummary
from app.models.annual_summary import AnnualSummary
from app.models.station import Station
from app.utils.aggregation import (
    compute_weekly_summary,
    compute_monthly_summary,
    compute_dekadal_summary,
    compute_seasonal_summary,
    compute_annual_summary,
    get_iso_week,
    get_week_date_range,
)
from app.crud.base import CRUDBase


# ============================================================================
# WEEKLY SUMMARY CRUD
# ============================================================================

class CRUDWeeklySummary(CRUDBase[WeeklySummary, dict, dict]):
    """
    CRUD operations for WeeklySummary model.

    Implements lazy computation: check cache first, compute if missing.
    """

    async def get_or_compute(
        self,
        db: AsyncSession,
        station_id: int,
        year: int,
        week_number: int
    ) -> Optional[WeeklySummary]:
        """
        Get weekly summary from cache, or compute if not exists.

        Implements lazy computation strategy:
        1. Check if already cached in database
        2. If not, compute from daily_summaries
        3. Cache result for future requests
        4. Return WeeklySummary instance

        Args:
            db: Database session
            station_id: Station ID
            year: ISO year
            week_number: ISO week number (1-53)

        Returns:
            WeeklySummary instance or None if insufficient data
        """
        # Try to get from cache
        result = await db.execute(
            select(WeeklySummary).where(
                and_(
                    WeeklySummary.station_id == station_id,
                    WeeklySummary.year == year,
                    WeeklySummary.week_number == week_number
                )
            )
        )
        cached = result.scalars().first()

        if cached:
            return cached

        # Compute on-demand
        weekly_data = await compute_weekly_summary(db, station_id, year, week_number)

        if not weekly_data:
            return None

        # Save to cache
        weekly_summary = WeeklySummary(**weekly_data)
        db.add(weekly_summary)
        await db.commit()
        await db.refresh(weekly_summary)

        return weekly_summary

    async def get_for_year(
        self,
        db: AsyncSession,
        station_id: int,
        year: int
    ) -> List[WeeklySummary]:
        """
        Get all weekly summaries for a year (weeks 1-52/53).

        Uses lazy computation - computes missing weeks on-demand.

        Args:
            db: Database session
            station_id: Station ID
            year: ISO year

        Returns:
            List of WeeklySummary instances for the year
        """
        # Determine number of weeks in this ISO year
        # ISO year has 53 weeks if Dec 31 is a Thursday, or if Dec 30 is a Thursday in leap year
        last_date = date(year, 12, 31)
        iso_year, max_week = get_iso_week(last_date)

        # If Dec 31 belongs to next year's week 1, this year has 52 weeks
        if iso_year != year:
            max_week = 52

        summaries = []
        for week in range(1, max_week + 1):
            summary = await self.get_or_compute(db, station_id, year, week)
            if summary:
                summaries.append(summary)

        return summaries

    async def get_latest_for_station(
        self,
        db: AsyncSession,
        station_id: int
    ) -> Optional[WeeklySummary]:
        """
        Get the most recent weekly summary for a station.

        Args:
            db: Database session
            station_id: Station ID

        Returns:
            Most recent WeeklySummary or None
        """
        result = await db.execute(
            select(WeeklySummary)
            .where(WeeklySummary.station_id == station_id)
            .order_by(desc(WeeklySummary.year), desc(WeeklySummary.week_number))
            .limit(1)
        )
        return result.scalars().first()


# ============================================================================
# MONTHLY SUMMARY CRUD
# ============================================================================

class CRUDMonthlySummary(CRUDBase[MonthlySummary, dict, dict]):
    """
    CRUD operations for MonthlySummary model.

    Implements lazy computation with anomaly calculation support.
    """

    async def get_or_compute(
        self,
        db: AsyncSession,
        station_id: int,
        year: int,
        month: int
    ) -> Optional[MonthlySummary]:
        """
        Get monthly summary from cache, or compute if not exists.

        Implements lazy computation strategy:
        1. Check if already cached in database
        2. If not, compute from daily_summaries
        3. Include anomaly calculation if climate normal exists (Phase 2)
        4. Cache result for future requests
        5. Return MonthlySummary instance

        Args:
            db: Database session
            station_id: Station ID
            year: Year
            month: Month (1-12)

        Returns:
            MonthlySummary instance or None if insufficient data
        """
        # Try to get from cache
        result = await db.execute(
            select(MonthlySummary).where(
                and_(
                    MonthlySummary.station_id == station_id,
                    MonthlySummary.year == year,
                    MonthlySummary.month == month
                )
            )
        )
        cached = result.scalars().first()

        if cached:
            return cached

        # Compute on-demand
        monthly_data = await compute_monthly_summary(db, station_id, year, month)

        if not monthly_data:
            return None

        # TODO Phase 2: Query climate_normals and add anomaly calculations
        # For now, anomalies are set to None in compute_monthly_summary

        # Save to cache
        monthly_summary = MonthlySummary(**monthly_data)
        db.add(monthly_summary)
        await db.commit()
        await db.refresh(monthly_summary)

        return monthly_summary

    async def get_for_year(
        self,
        db: AsyncSession,
        station_id: int,
        year: int
    ) -> List[MonthlySummary]:
        """
        Get all monthly summaries for a year (months 1-12).

        Uses lazy computation - computes missing months on-demand.

        Args:
            db: Database session
            station_id: Station ID
            year: Year

        Returns:
            List of MonthlySummary instances for the year
        """
        summaries = []
        for month in range(1, 13):
            summary = await self.get_or_compute(db, station_id, year, month)
            if summary:
                summaries.append(summary)

        return summaries

    async def get_latest_for_station(
        self,
        db: AsyncSession,
        station_id: int
    ) -> Optional[MonthlySummary]:
        """
        Get the most recent monthly summary for a station.

        Args:
            db: Database session
            station_id: Station ID

        Returns:
            Most recent MonthlySummary or None
        """
        result = await db.execute(
            select(MonthlySummary)
            .where(MonthlySummary.station_id == station_id)
            .order_by(desc(MonthlySummary.year), desc(MonthlySummary.month))
            .limit(1)
        )
        return result.scalars().first()

    async def get_in_date_range(
        self,
        db: AsyncSession,
        station_id: int,
        start_year: int,
        start_month: int,
        end_year: int,
        end_month: int
    ) -> List[MonthlySummary]:
        """
        Get monthly summaries within a date range.

        Uses lazy computation for missing months.

        Args:
            db: Database session
            station_id: Station ID
            start_year: Start year
            start_month: Start month (1-12)
            end_year: End year
            end_month: End month (1-12)

        Returns:
            List of MonthlySummary instances in date range
        """
        summaries = []

        current_year = start_year
        current_month = start_month

        while (current_year < end_year) or (current_year == end_year and current_month <= end_month):
            summary = await self.get_or_compute(db, station_id, current_year, current_month)
            if summary:
                summaries.append(summary)

            # Move to next month
            current_month += 1
            if current_month > 12:
                current_month = 1
                current_year += 1

        return summaries


# ============================================================================
# BATCH POPULATION UTILITIES
# ============================================================================

async def batch_populate_weekly_summaries(
    db: AsyncSession,
    station_id: int,
    start_year: int,
    end_year: int
) -> int:
    """
    Pre-compute weekly summaries for a station across multiple years.

    Used for batch population of recent years (2023-2025) to ensure
    fast response times for current queries.

    Args:
        db: Database session
        station_id: Station ID
        start_year: Start year (inclusive)
        end_year: End year (inclusive)

    Returns:
        Number of weekly summaries successfully computed
    """
    count = 0

    for year in range(start_year, end_year + 1):
        # Determine number of weeks in this ISO year
        last_date = date(year, 12, 31)
        iso_year, max_week = get_iso_week(last_date)

        if iso_year != year:
            max_week = 52

        for week in range(1, max_week + 1):
            weekly_data = await compute_weekly_summary(db, station_id, year, week)

            if weekly_data:
                # Check if already exists
                result = await db.execute(
                    select(WeeklySummary).where(
                        and_(
                            WeeklySummary.station_id == station_id,
                            WeeklySummary.year == year,
                            WeeklySummary.week_number == week
                        )
                    )
                )
                existing = result.scalars().first()

                if not existing:
                    weekly_summary = WeeklySummary(**weekly_data)
                    db.add(weekly_summary)
                    count += 1

    await db.commit()
    return count


async def batch_populate_monthly_summaries(
    db: AsyncSession,
    station_id: int,
    start_year: int,
    end_year: int
) -> int:
    """
    Pre-compute monthly summaries for a station across multiple years.

    Used for batch population of recent years (2023-2025) to ensure
    fast response times for current queries.

    Args:
        db: Database session
        station_id: Station ID
        start_year: Start year (inclusive)
        end_year: End year (inclusive)

    Returns:
        Number of monthly summaries successfully computed
    """
    count = 0

    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            monthly_data = await compute_monthly_summary(db, station_id, year, month)

            if monthly_data:
                # Check if already exists
                result = await db.execute(
                    select(MonthlySummary).where(
                        and_(
                            MonthlySummary.station_id == station_id,
                            MonthlySummary.year == year,
                            MonthlySummary.month == month
                        )
                    )
                )
                existing = result.scalars().first()

                if not existing:
                    monthly_summary = MonthlySummary(**monthly_data)
                    db.add(monthly_summary)
                    count += 1

    await db.commit()
    return count


# ============================================================================
# DEKADAL SUMMARY CRUD (Phase 2)
# ============================================================================

class CRUDDekadalSummary(CRUDBase[DekadalSummary, dict, dict]):
    """
    CRUD operations for DekadalSummary model.

    Implements lazy computation for 10-day climate products.
    """

    async def get_or_compute(
        self,
        db: AsyncSession,
        station_id: int,
        year: int,
        month: int,
        dekad: int
    ) -> Optional[DekadalSummary]:
        """
        Get dekadal summary from cache, or compute if not exists.

        Args:
            db: Database session
            station_id: Station ID
            year: Year
            month: Month (1-12)
            dekad: Dekad number (1, 2, or 3)

        Returns:
            DekadalSummary instance or None if insufficient data
        """
        # Try to get from cache
        result = await db.execute(
            select(DekadalSummary).where(
                and_(
                    DekadalSummary.station_id == station_id,
                    DekadalSummary.year == year,
                    DekadalSummary.month == month,
                    DekadalSummary.dekad == dekad
                )
            )
        )
        cached = result.scalars().first()

        if cached:
            return cached

        # Compute on-demand
        dekadal_data = await compute_dekadal_summary(db, station_id, year, month, dekad)

        if not dekadal_data:
            return None

        # Save to cache
        dekadal_summary = DekadalSummary(**dekadal_data)
        db.add(dekadal_summary)
        await db.commit()
        await db.refresh(dekadal_summary)

        return dekadal_summary

    async def get_for_month(
        self,
        db: AsyncSession,
        station_id: int,
        year: int,
        month: int
    ) -> List[DekadalSummary]:
        """
        Get all dekadal summaries for a month (dekads 1-3).

        Args:
            db: Database session
            station_id: Station ID
            year: Year
            month: Month (1-12)

        Returns:
            List of DekadalSummary instances for the month
        """
        summaries = []
        for dekad in range(1, 4):
            summary = await self.get_or_compute(db, station_id, year, month, dekad)
            if summary:
                summaries.append(summary)

        return summaries


# ============================================================================
# SEASONAL SUMMARY CRUD (Phase 2)
# ============================================================================

class CRUDSeasonalSummary(CRUDBase[SeasonalSummary, dict, dict]):
    """
    CRUD operations for SeasonalSummary model.

    Implements lazy computation for Ghana-specific seasonal products.
    """

    async def get_or_compute(
        self,
        db: AsyncSession,
        station_id: int,
        year: int,
        season: str
    ) -> Optional[SeasonalSummary]:
        """
        Get seasonal summary from cache, or compute if not exists.

        Args:
            db: Database session
            station_id: Station ID
            year: Year (for DJF, this is the December year)
            season: Season code ('MAM', 'JJA', 'SON', 'DJF')

        Returns:
            SeasonalSummary instance or None if insufficient data
        """
        # Try to get from cache
        result = await db.execute(
            select(SeasonalSummary).where(
                and_(
                    SeasonalSummary.station_id == station_id,
                    SeasonalSummary.year == year,
                    SeasonalSummary.season == season
                )
            )
        )
        cached = result.scalars().first()

        if cached:
            return cached

        # Compute on-demand
        seasonal_data = await compute_seasonal_summary(db, station_id, year, season)

        if not seasonal_data:
            return None

        # Save to cache
        seasonal_summary = SeasonalSummary(**seasonal_data)
        db.add(seasonal_summary)
        await db.commit()
        await db.refresh(seasonal_summary)

        return seasonal_summary

    async def get_for_year(
        self,
        db: AsyncSession,
        station_id: int,
        year: int
    ) -> List[SeasonalSummary]:
        """
        Get all seasonal summaries for a year (MAM, JJA, SON, DJF).

        Note: DJF for year Y includes Dec Y through Feb Y+1.

        Args:
            db: Database session
            station_id: Station ID
            year: Year

        Returns:
            List of SeasonalSummary instances for the year
        """
        summaries = []
        for season in ['MAM', 'JJA', 'SON', 'DJF']:
            summary = await self.get_or_compute(db, station_id, year, season)
            if summary:
                summaries.append(summary)

        return summaries


# ============================================================================
# ANNUAL SUMMARY CRUD (Phase 2)
# ============================================================================

class CRUDAnnualSummary(CRUDBase[AnnualSummary, dict, dict]):
    """
    CRUD operations for AnnualSummary model.

    Implements lazy computation for annual climate products.
    """

    async def get_or_compute(
        self,
        db: AsyncSession,
        station_id: int,
        year: int
    ) -> Optional[AnnualSummary]:
        """
        Get annual summary from cache, or compute if not exists.

        Args:
            db: Database session
            station_id: Station ID
            year: Year

        Returns:
            AnnualSummary instance or None if insufficient data
        """
        # Try to get from cache
        result = await db.execute(
            select(AnnualSummary).where(
                and_(
                    AnnualSummary.station_id == station_id,
                    AnnualSummary.year == year
                )
            )
        )
        cached = result.scalars().first()

        if cached:
            return cached

        # Compute on-demand
        annual_data = await compute_annual_summary(db, station_id, year)

        if not annual_data:
            return None

        # Save to cache
        annual_summary = AnnualSummary(**annual_data)
        db.add(annual_summary)
        await db.commit()
        await db.refresh(annual_summary)

        return annual_summary

    async def get_for_range(
        self,
        db: AsyncSession,
        station_id: int,
        start_year: int,
        end_year: int
    ) -> List[AnnualSummary]:
        """
        Get annual summaries for a range of years.

        Args:
            db: Database session
            station_id: Station ID
            start_year: Start year (inclusive)
            end_year: End year (inclusive)

        Returns:
            List of AnnualSummary instances for the year range
        """
        summaries = []
        for year in range(start_year, end_year + 1):
            summary = await self.get_or_compute(db, station_id, year)
            if summary:
                summaries.append(summary)

        return summaries

    async def get_latest_for_station(
        self,
        db: AsyncSession,
        station_id: int
    ) -> Optional[AnnualSummary]:
        """
        Get the most recent annual summary for a station.

        Args:
            db: Database session
            station_id: Station ID

        Returns:
            Most recent AnnualSummary or None
        """
        result = await db.execute(
            select(AnnualSummary)
            .where(AnnualSummary.station_id == station_id)
            .order_by(desc(AnnualSummary.year))
            .limit(1)
        )
        return result.scalars().first()


# Create instances of CRUD classes
weekly_summary = CRUDWeeklySummary(WeeklySummary)
monthly_summary = CRUDMonthlySummary(MonthlySummary)
dekadal_summary = CRUDDekadalSummary(DekadalSummary)
seasonal_summary = CRUDSeasonalSummary(SeasonalSummary)
annual_summary = CRUDAnnualSummary(AnnualSummary)
