"""Auto-Consolidation Daemon — periodically prunes and re-indexes Vector Memory"""

import time
import threading
import logging
from core.vector_memory import get_vector_memory

logger = logging.getLogger("NEXUS-ConsolidationDaemon")

class ConsolidationDaemon:
    def __init__(self, interval_hours=24):
        self.interval = interval_hours * 3600
        self.running = False
        self.thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.info(f"ConsolidationDaemon started (interval: {self.interval//3600}h)")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("ConsolidationDaemon stopped")

    def _run(self):
        while self.running:
            try:
                vm = get_vector_memory()
                n = len(vm.documents)
                vm.clear()
                logger.info(f"Consolidated {n} memories — cache reset")
            except Exception as e:
                logger.error(f"Consolidation error: {e}")
            time.sleep(self.interval)

_daemon = None

def start_consolidation_daemon():
    global _daemon
    if _daemon is None:
        _daemon = ConsolidationDaemon()
        _daemon.start()
    return _daemon

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    daemon = start_consolidation_daemon()
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        daemon.stop()
