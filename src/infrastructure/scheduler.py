"""Background Asynchronous Catalog Sync Scheduler.

Clean Architecture layer: Infrastructure.
Runs a background asyncio loop to automatically synchronize stores where `auto_sync == True`.
"""
import asyncio
import logging
from typing import Optional
from ..domain.ports import ICatalogRepository
from ..application.use_cases import SyncMerchantCatalogUseCase

logger = logging.getLogger("CatalogSyncScheduler")


class CatalogSyncScheduler:
    """Async background worker for periodic catalog synchronization."""

    def __init__(
        self,
        catalog_repo: ICatalogRepository,
        sync_uc: SyncMerchantCatalogUseCase,
        check_interval_seconds: int = 60,
    ):
        self.catalog_repo = catalog_repo
        self.sync_uc = sync_uc
        self.check_interval_seconds = check_interval_seconds
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def _worker_loop(self):
        """Continuous background loop scanning stores with auto_sync enabled."""
        logger.info(
            f"🔄 Catalog Sync Scheduler active (Interval: {self.check_interval_seconds}s)."
        )
        while self._running:
            try:
                await self.run_sync_cycle()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in catalog sync scheduler cycle: {e}")

            # Sleep until next check
            try:
                await asyncio.sleep(self.check_interval_seconds)
            except asyncio.CancelledError:
                break

    async def run_sync_cycle(self):
        """Runs a single pass across all merchants needing synchronization."""
        merchants = self.catalog_repo.list_merchants()
        for m in merchants:
            if not m.sync_config or not m.sync_config.auto_sync:
                continue

            try:
                logger.info(f"⏳ Auto-syncing catalog for merchant '{m.merchant_id}' ({m.sync_config.provider})...")
                res = self.sync_uc.execute(m.merchant_id)
                if res.success:
                    logger.info(f"✅ Auto-sync completed for '{m.merchant_id}': {res.synced_products_count} products updated.")
                else:
                    logger.warning(f"⚠️ Auto-sync warning for '{m.merchant_id}': {res.error_message}")
            except Exception as e:
                logger.error(f"❌ Auto-sync failed for merchant '{m.merchant_id}': {e}")

    def start(self):
        """Start the background scheduler task."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._worker_loop())
            logger.info("Catalog Sync Scheduler background task started.")

    def stop(self):
        """Stop the background scheduler task."""
        if self._running:
            self._running = False
            if self._task and not self._task.done():
                self._task.cancel()
            logger.info("Catalog Sync Scheduler stopped.")
