"""
CRUD operations for Climate Normals.

This module provides database query functions for retrieving climate normals
(1991-2020 WMO standard) used to calculate anomalies in climate products.
"""

from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.crud.base import CRUDBase
from app.models.climate_normal import ClimateNormal


class CRUDClimateNormal(CRUDBase[ClimateNormal, dict, dict]):
    """CRUD operations for ClimateNormal model."""

    async def get_monthly_normal(
        self,
        db: AsyncSession,
        station_id: int,
        month: int,
        period_start: int = 1991,
        period_end: int = 2020
    ) -> Optional[ClimateNormal]:
        """
        Get monthly climate normal for a specific station and month.

        Args:
            db: Database session
            station_id: Station ID
            month: Month number (1-12)
            period_start: Start year of normal period (default: 1991)
            period_end: End year of normal period (default: 2020)

        Returns:
            ClimateNormal record or None if not found

        Example:
            normal = await climate_normal.get_monthly_normal(db, station_id=1, month=5)
            if normal:
                print(f"May rainfall normal: {normal.rainfall_normal}mm")
        """
        stmt = select(ClimateNormal).where(
            ClimateNormal.station_id == station_id,
            ClimateNormal.normal_period_start == period_start,
            ClimateNormal.normal_period_end == period_end,
            ClimateNormal.timescale == 'monthly',
            ClimateNormal.month == month
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_dekadal_normal(
        self,
        db: AsyncSession,
        station_id: int,
        month: int,
        dekad: int,
        period_start: int = 1991,
        period_end: int = 2020
    ) -> Optional[ClimateNormal]:
        """
        Get dekadal climate normal (10-day period) for a station.

        Dekads are 10-day periods used in agrometeorological monitoring:
        - Dekad 1: Days 1-10
        - Dekad 2: Days 11-20
        - Dekad 3: Days 21-end of month

        Args:
            db: Database session
            station_id: Station ID
            month: Month number (1-12)
            dekad: Dekad number (1-3)
            period_start: Start year of normal period (default: 1991)
            period_end: End year of normal period (default: 2020)

        Returns:
            ClimateNormal record or None if not found

        Example:
            normal = await climate_normal.get_dekadal_normal(db, station_id=1, month=5, dekad=2)
            # Gets normal for May 11-20
        """
        stmt = select(ClimateNormal).where(
            ClimateNormal.station_id == station_id,
            ClimateNormal.normal_period_start == period_start,
            ClimateNormal.normal_period_end == period_end,
            ClimateNormal.timescale == 'dekadal',
            ClimateNormal.month == month,
            ClimateNormal.dekad == dekad
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_seasonal_normal(
        self,
        db: AsyncSession,
        station_id: int,
        season: str,
        period_start: int = 1991,
        period_end: int = 2020
    ) -> Optional[ClimateNormal]:
        """
        Get seasonal climate normal for Ghana-specific climate seasons.

        Ghana Climate Seasons:
        - MAM (March-April-May): Major rainy season - primary planting period
        - JJA (June-July-August): Minor rainy season
        - SON (September-October-November): Post-rainy/transition - harvest period
        - DJF (December-January-February): Dry season/Harmattan

        Args:
            db: Database session
            station_id: Station ID
            season: Season code ('MAM', 'JJA', 'SON', 'DJF')
            period_start: Start year of normal period (default: 1991)
            period_end: End year of normal period (default: 2020)

        Returns:
            ClimateNormal record or None if not found

        Example:
            normal = await climate_normal.get_seasonal_normal(db, station_id=1, season='MAM')
            # Gets normal for major rainy season
        """
        stmt = select(ClimateNormal).where(
            ClimateNormal.station_id == station_id,
            ClimateNormal.normal_period_start == period_start,
            ClimateNormal.normal_period_end == period_end,
            ClimateNormal.timescale == 'seasonal',
            ClimateNormal.season == season
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_annual_normal(
        self,
        db: AsyncSession,
        station_id: int,
        period_start: int = 1991,
        period_end: int = 2020
    ) -> Optional[ClimateNormal]:
        """
        Get annual climate normal for a station.

        Annual normals represent the calendar year (January 1 - December 31).

        Args:
            db: Database session
            station_id: Station ID
            period_start: Start year of normal period (default: 1991)
            period_end: End year of normal period (default: 2020)

        Returns:
            ClimateNormal record or None if not found

        Example:
            normal = await climate_normal.get_annual_normal(db, station_id=1)
            print(f"Annual rainfall normal: {normal.rainfall_normal}mm")
        """
        stmt = select(ClimateNormal).where(
            ClimateNormal.station_id == station_id,
            ClimateNormal.normal_period_start == period_start,
            ClimateNormal.normal_period_end == period_end,
            ClimateNormal.timescale == 'annual'
        )
        result = await db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_for_station(
        self,
        db: AsyncSession,
        station_id: int,
        period_start: int = 1991,
        period_end: int = 2020
    ) -> List[ClimateNormal]:
        """
        Get all climate normals for a station (all timescales).

        Returns up to 53 normals per station:
        - 12 monthly normals (Jan-Dec)
        - 36 dekadal normals (12 months × 3 dekads)
        - 4 seasonal normals (MAM, JJA, SON, DJF)
        - 1 annual normal

        Args:
            db: Database session
            station_id: Station ID
            period_start: Start year of normal period (default: 1991)
            period_end: End year of normal period (default: 2020)

        Returns:
            List of ClimateNormal records

        Example:
            normals = await climate_normal.get_all_for_station(db, station_id=1)
            print(f"Station has {len(normals)}/53 climate normals")
        """
        stmt = select(ClimateNormal).where(
            ClimateNormal.station_id == station_id,
            ClimateNormal.normal_period_start == period_start,
            ClimateNormal.normal_period_end == period_end
        ).order_by(
            ClimateNormal.timescale,
            ClimateNormal.month,
            ClimateNormal.dekad,
            ClimateNormal.season
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_timescale(
        self,
        db: AsyncSession,
        station_id: int,
        timescale: str,
        period_start: int = 1991,
        period_end: int = 2020
    ) -> List[ClimateNormal]:
        """
        Get all climate normals for a station by timescale.

        Args:
            db: Database session
            station_id: Station ID
            timescale: Timescale ('monthly', 'dekadal', 'seasonal', 'annual')
            period_start: Start year of normal period (default: 1991)
            period_end: End year of normal period (default: 2020)

        Returns:
            List of ClimateNormal records

        Example:
            monthly_normals = await climate_normal.get_by_timescale(
                db, station_id=1, timescale='monthly'
            )
            # Returns 12 monthly normals
        """
        stmt = select(ClimateNormal).where(
            ClimateNormal.station_id == station_id,
            ClimateNormal.normal_period_start == period_start,
            ClimateNormal.normal_period_end == period_end,
            ClimateNormal.timescale == timescale
        ).order_by(
            ClimateNormal.month,
            ClimateNormal.dekad,
            ClimateNormal.season
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())


# Create singleton instance for import
climate_normal = CRUDClimateNormal(ClimateNormal)
