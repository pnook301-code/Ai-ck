"""State Management"""
from typing import Any, Dict, Optional, TypeVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json
import asyncio
import threading

T = TypeVar('T')


@dataclass
class StateSnapshot:
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1


class StateManager:
    """Manages application state with persistence"""

    def __init__(self, data_dir: str = None, logger: Any = None):
        self._data: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._dirty = False
        self._data_dir = Path(data_dir or "/tmp/ck-nexus-state")
        self._data_dir.mkdir(parents=True, exist_ok=True)
        self._state_file = self._data_dir / "state.json"
        self._logger = logger

    async def start(self):
        await self._load()

    async def stop(self):
        if self._dirty:
            await self.persist()

    async def close(self):
        await self.stop()

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any):
        with self._lock:
            self._data[key] = value
            self._dirty = True

    def delete(self, key: str):
        with self._lock:
            self._data.pop(key, None)
            self._dirty = True

    def update(self, data: Dict[str, Any]):
        with self._lock:
            self._data.update(data)
            self._dirty = True

    def clear(self):
        with self._lock:
            self._data.clear()
            self._dirty = True

    def snapshot(self) -> StateSnapshot:
        with self._lock:
            return StateSnapshot(
                data=dict(self._data),
                timestamp=datetime.now(timezone.utc),
                version=self._data.get("_version", 1)
            )

    def all(self) -> Dict[str, Any]:
        with self._lock:
            return dict(self._data)

    async def persist(self):
        with self._lock:
            if not self._dirty:
                return
            try:
                self._data["_version"] = self._data.get("_version", 0) + 1
                self._data["_updated"] = datetime.now(timezone.utc).isoformat()
                with open(self._state_file, 'w') as f:
                    json.dump(self._data, f, indent=2, default=str)
                self._dirty = False
            except Exception as e:
                if self._logger:
                    self._logger.error(f"State persist error: {e}")

    async def _load(self):
        if self._state_file.exists():
            try:
                with open(self._state_file) as f:
                    self._data = json.load(f)
                self._dirty = False
            except Exception as e:
                if self._logger:
                    self._logger.error(f"State load error: {e}")
