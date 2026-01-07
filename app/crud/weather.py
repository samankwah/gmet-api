"""
Weather data CRUD operations.

This module contains CRUD operations for weather-related models.
"""

from datetime import datetime, date, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import and_, desc

from app.crud.base import CRUDBase
from app.models.weather_data import Station, Observation
from app.models.daily_summary import DailySummary


class CRUDStation(CRUDBase[Station, Station, dict]):
    """
    CRUD operations for Station model.
    """

    async def get_by_code(self, db: AsyncSession, *, code: str) -> Optional[Station]:
        """
        Get station by code.

        Args:
            db: Database session
            code: Station code

        Returns:
            Station instance or None if not found
        """
        result = await db.execute(
            select(Station).where(Station.code == code)
        )
        return result.scalars().first()

    async def get_by_region(
        self, db: AsyncSession, *, region: str, skip: int = 0, limit: int = 100
    ) -> List[Station]:
        """
        Get stations by region.

        Args:
            db: Database session
            region: Region name
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Station instances
        """
        result = await db.execute(
            select(Station)
            .where(Station.region == region)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()


class CRUDObservation(CRUDBase[Observation, Observation, dict]):
    """
    CRUD operations for Observation model.
    """

    async def get_latest_for_station(
        self, db: AsyncSession, *, station_id: int
    ) -> Optional[Observation]:
        """
        Get the latest observation for a station.

        Args:
            db: Database session
            station_id: Station ID

        Returns:
            Latest Observation instance or None
        """
        result = await db.execute(
            select(Observation)
            .where(Observation.station_id == station_id)
            .order_by(desc(Observation.obs_datetime))
            .limit(1)
        )
        return result.scalars().first()

    async def get_observations_in_date_range(
        self,
        db: AsyncSession,
        *,
        station_id: int,
        start_date: datetime,
        end_date: datetime,
        skip: int = 0,
        limit: int = 1000
    ) -> List[Observation]:
        """
        Get observations within a date range for a station.

        Args:
            db: Database session
            station_id: Station ID
            start_date: Start of date range
            end_date: End of date range
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of Observation instances
        """
        result = await db.execute(
            select(Observation)
            .where(
                and_(
                    Observation.station_id == station_id,
                    Observation.obs_datetime >= start_date,
                    Observation.obs_datetime <= end_date
                )
            )
            .order_by(Observation.obs_datetime)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_recent_observations(
        self,
        db: AsyncSession,
        *,
        hours: int = 24,
        skip: int = 0,
        limit: int = 1000
    ) -> List[Observation]:
        """
        Get recent observations from all stations.

        Args:
            db: Database session
            hours: Number of hours back to look
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of recent Observation instances
        """
        from datetime import timedelta
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=hours)

        result = await db.execute(
            select(Observation)
            .where(Observation.obs_datetime >= cutoff_time)
            .order_by(desc(Observation.obs_datetime))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()


class CRUDDailySummary(CRUDBase[DailySummary, dict, dict]):
    """
    CRUD operations for DailySummary model.

    Provides methods to query daily weather summaries with separate
    min/max temperatures, mean humidity, and rainfall totals.
    """

    async def get_latest_for_station(
        self, db: AsyncSession, *, station_id: int
    ) -> Optional[DailySummary]:
        """
        Get the most recent daily summary for a station.

        Args:
            db: Database session
            station_id: Station ID

        Returns:
            Most recent DailySummary instance or None
        """
        result = await db.execute(
            select(DailySummary)
            .where(DailySummary.station_id == station_id)
            .order_by(desc(DailySummary.date))
            .limit(1)
        )
        return result.scalars().first()

    async def get_summaries_in_date_range(
        self,
        db: AsyncSession,
        *,
        station_id: int,
        start_date: date,
        end_date: date,
        skip: int = 0,
        limit: int = 1000
    ) -> List[DailySummary]:
        """
        Get daily summaries within a date range for a station.

        Args:
            db: Database session
            station_id: Station ID
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of DailySummary instances
        """
        result = await db.execute(
            select(DailySummary)
            .where(
                and_(
                    DailySummary.station_id == station_id,
                    DailySummary.date >= start_date,
                    DailySummary.date <= end_date
                )
            )
            .order_by(DailySummary.date)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()

    async def get_summaries_for_station(
        self,
        db: AsyncSession,
        *,
        station_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[DailySummary]:
        """
        Get daily summaries for a station (most recent first).

        Args:
            db: Database session
            station_id: Station ID
            skip: Number of records to skip
            limit: Maximum records to return

        Returns:
            List of DailySummary instances
        """
        result = await db.execute(
            select(DailySummary)
            .where(DailySummary.station_id == station_id)
            .order_by(desc(DailySummary.date))
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()


# Create instances of CRUD classes
station = CRUDStation(Station)
observation = CRUDObservation(Observation)
daily_summary = CRUDDailySummary(DailySummary)

# """
# Weather data CRUD operations.

# This module contains CRUD operations for weather-related models.
# """

# from datetime import datetime
# from typing import List, Optional
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from sqlalchemy import and_, desc

# from app.crud.base import CRUDBase
# from app.models.weather_data import Station, SynopticObservation as Observation


# class CRUDStation(CRUDBase[Station, Station, dict]):
#     """
#     CRUD operations for Station model.
#     """

#     async def get_by_code(self, db: AsyncSession, *, code: str) -> Optional[Station]:
#         """
#         Get station by code.

#         Args:
#             db: Database session
#             code: Station code

#         Returns:
#             Station instance or None if not found
#         """
#         result = await db.execute(
#             select(Station).where(Station.code == code)
#         )
#         return result.scalars().first()

#     async def get_by_region(
#         self, db: AsyncSession, *, region: str, skip: int = 0, limit: int = 100
#     ) -> List[Station]:
#         """
#         Get stations by region.

#         Args:
#             db: Database session
#             region: Region name
#             skip: Number of records to skip
#             limit: Maximum number of records to return

#         Returns:
#             List of Station instances
#         """
#         result = await db.execute(
#             select(Station)
#             .where(Station.region == region)
#             .offset(skip)
#             .limit(limit)
#         )
#         return result.scalars().all()


# class CRUDObservation(CRUDBase[Observation, Observation, dict]):
#     """
#     CRUD operations for Observation model.
#     """

#     async def get_latest_for_station(
#         self, db: AsyncSession, *, station_id: int
#     ) -> Optional[Observation]:
#         """
#         Get the latest observation for a station.

#         Args:
#             db: Database session
#             station_id: Station ID

#         Returns:
#             Latest Observation instance or None
#         """
#         result = await db.execute(
#             select(Observation)
#             .where(Observation.station_id == station_id)
#             .order_by(desc(Observation.obs_datetime))  # Changed from timestamp to obs_datetime
#             .limit(1)
#         )
#         return result.scalars().first()

#     async def get_observations_in_date_range(
#         self,
#         db: AsyncSession,
#         *,
#         station_id: int,
#         start_date: datetime,
#         end_date: datetime,
#         skip: int = 0,
#         limit: int = 1000
#     ) -> List[Observation]:
#         """
#         Get observations within a date range for a station.

#         Args:
#             db: Database session
#             station_id: Station ID
#             start_date: Start of date range
#             end_date: End of date range
#             skip: Number of records to skip
#             limit: Maximum number of records to return

#         Returns:
#             List of Observation instances
#         """
#         result = await db.execute(
#             select(Observation)
#             .where(
#                 and_(
#                     Observation.station_id == station_id,
#                     Observation.obs_datetime >= start_date,  # Changed from timestamp
#                     Observation.obs_datetime <= end_date     # Changed from timestamp
#                 )
#             )
#             .order_by(Observation.obs_datetime)  # Changed from timestamp
#             .offset(skip)
#             .limit(limit)
#         )
#         return result.scalars().all()

#     async def get_recent_observations(
#         self,
#         db: AsyncSession,
#         *,
#         hours: int = 24,
#         skip: int = 0,
#         limit: int = 1000
#     ) -> List[Observation]:
#         """
#         Get recent observations from all stations.

#         Args:
#             db: Database session
#             hours: Number of hours back to look
#             skip: Number of records to skip
#             limit: Maximum number of records to return

#         Returns:
#             List of recent Observation instances
#         """
#         from datetime import timedelta
#         cutoff_time = datetime.utcnow() - timedelta(hours=hours)

#         result = await db.execute(
#             select(Observation)
#             .where(Observation.obs_datetime >= cutoff_time)  # Changed from timestamp
#             .order_by(desc(Observation.obs_datetime))        # Changed from timestamp
#             .offset(skip)
#             .limit(limit)
#         )
#         return result.scalars().all()


# # Create instances of CRUD classes
# station = CRUDStation(Station)
# observation = CRUDObservation(Observation)