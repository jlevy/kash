import threading
import time

from funlog import format_duration

from kash.config.logger import get_logger
from kash.file_storage.file_store import FileStore

log = get_logger(__name__)


def warm_file_store(file_store: FileStore):
    """
    Load all the items so they are in file cache. A simple way to speed up some
    lookups.
    """

    def load_all_items():
        start_time = time.time()
        count = 0
        for store_path in file_store.walk_items():
            try:
                file_store.load(store_path)
                count += 1
            except Exception as e:
                log.info("Error loading item %s: %s", store_path, e)

        duration = time.time() - start_time
        log.info(
            "Warmed file store cache for %s (%s items) in %s (%s/s).",
            file_store,
            count,
            format_duration(duration),
            int(count / duration) if duration > 0 else 0,
        )

    threading.Thread(target=load_all_items, daemon=True).start()
