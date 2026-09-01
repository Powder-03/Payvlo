"""Background Asynchronous Catalog Sync Scheduler."""
import asyncio
import logging
from typing import Optional, Any

logger = logging.getLogger("CatalogSyncScheduler")


class CatalogSyncScheduler:
    """Async background worker for periodic catalog synchronization."""

    def __init__(
        self,
        catalog_service: Optional[Any] = None,
        catalog_repo: Optional[Any] = None,
        sync_uc: Optional[Any] = None,
        check_interval_seconds: int = 300,
    ):
        self.catalog_service = catalog_service or catalog_repo
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
        try:
            merchants = self.catalog_service.list_merchants()
            for m in merchants:
                sync_cfg = getattr(m, "sync_config", None)
                if not sync_cfg or not getattr(sync_cfg, "auto_sync", False):
                    continue

                try:
                    logger.info(
                        f"⏳ Auto-syncing catalog for merchant '{m.merchant_id}'..."
                    )
                    res = self.catalog_service.sync_merchant_catalog(m.merchant_id)
                    if getattr(res, "success", False):
                        logger.info(
                            f"✅ Auto-sync completed for '{m.merchant_id}': {res.synced_products_count} products updated."
                        )
                    else:
                        logger.warning(
                            f"⚠️ Auto-sync warning for '{m.merchant_id}': {getattr(res, 'error_message', '')}"
                        )
                except Exception as e:
                    logger.error(f"❌ Auto-sync failed for merchant '{m.merchant_id}': {e}")
        except Exception as ex:
            logger.debug(f"Catalog sync cycle error: {ex}")

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
