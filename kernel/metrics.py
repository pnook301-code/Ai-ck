"""Metrics Collection - Prometheus integration"""
from typing import Dict, Any, List
from enum import Enum
from dataclasses import dataclass, field
import time
import threading


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


@dataclass
class Metric:
    name: str
    type: MetricType
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class MetricsCollector:
    """Collects and exposes metrics"""

    def __init__(self, logger: Any = None):
        self._metrics: Dict[str, Metric] = {}
        self._counters: Dict[str, float] = {}
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, List[float]] = {}
        self._lock = threading.RLock()
        self._logger = logger
        self._system_metrics_enabled = True

    def increment(self, name: str, value: float = 1, labels: Dict[str, str] = None):
        with self._lock:
            key = self._metric_key(name, labels)
            self._counters[key] = self._counters.get(key, 0) + value

    def gauge(self, name: str, value: float, labels: Dict[str, str] = None):
        with self._lock:
            key = self._metric_key(name, labels)
            self._gauges[key] = value

    def gauge_add(self, name: str, delta: float, labels: Dict[str, str] = None):
        with self._lock:
            key = self._metric_key(name, labels)
            self._gauges[key] = self._gauges.get(key, 0) + delta

    def observe(self, name: str, value: float, labels: Dict[str, str] = None):
        with self._lock:
            key = self._metric_key(name, labels)
            if key not in self._histograms:
                self._histograms[key] = []
            self._histograms[key].append(value)
            if len(self._histograms[key]) > 1000:
                self._histograms[key] = self._histograms[key][-500:]

    def time(self, name: str, labels: Dict[str, str] = None):
        class Timer:
            def __init__(self, collector, name, labels):
                self.collector = collector
                self.name = name
                self.labels = labels
                self.start = time.time()
            def __enter__(self):
                return self
            def __exit__(self, *args):
                self.collector.observe(self.name, time.time() - self.start, self.labels)
        return Timer(self, f"{name}_duration", labels)

    def get_counter(self, name: str, labels: Dict[str, str] = None) -> float:
        return self._counters.get(self._metric_key(name, labels), 0)

    def get_gauge(self, name: str, labels: Dict[str, str] = None) -> float:
        return self._gauges.get(self._metric_key(name, labels), 0)

    def get_all(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {k: {"count": len(v), "sum": sum(v), "avg": sum(v)/len(v) if v else 0}
                              for k, v in self._histograms.items()},
            }

    def collect_system_metrics(self):
        import psutil
        self.gauge("system.cpu.percent", psutil.cpu_percent())
        self.gauge("system.memory.percent", psutil.virtual_memory().percent)
        self.gauge("system.disk.percent", psutil.disk_usage('/').percent)
        self.gauge("system.processes", len(psutil.pids()))

    def reset(self, name: str = None, labels: Dict[str, str] = None):
        with self._lock:
            if name:
                key = self._metric_key(name, labels)
                self._counters.pop(key, None)
                self._gauges.pop(key, None)
                self._histograms.pop(key, None)
            else:
                self._counters.clear()
                self._gauges.clear()
                self._histograms.clear()

    def _metric_key(self, name: str, labels: Dict[str, str] = None) -> str:
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in sorted(labels.items()))
            return f"{name}{{{label_str}}}"
        return name
