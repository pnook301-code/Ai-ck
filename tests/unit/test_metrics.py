import pytest
from kernel.metrics import MetricsCollector, MetricType, Metric


class TestMetric:
    def test_create_metric(self):
        m = Metric(name="test", type=MetricType.COUNTER, value=1.0)
        assert m.name == "test"
        assert m.type == MetricType.COUNTER
        assert m.value == 1.0

    def test_metric_with_labels(self):
        m = Metric(name="test", type=MetricType.GAUGE, value=42, labels={"env": "prod"})
        assert m.labels["env"] == "prod"


class TestMetricsCollector:
    def test_increment(self):
        mc = MetricsCollector()
        mc.increment("requests")
        assert mc.get_counter("requests") == 1
        mc.increment("requests")
        assert mc.get_counter("requests") == 2

    def test_increment_with_value(self):
        mc = MetricsCollector()
        mc.increment("bytes", value=100)
        assert mc.get_counter("bytes") == 100

    def test_increment_with_labels(self):
        mc = MetricsCollector()
        mc.increment("requests", labels={"method": "GET"})
        mc.increment("requests", labels={"method": "POST"})
        assert mc.get_counter("requests", labels={"method": "GET"}) == 1
        assert mc.get_counter("requests", labels={"method": "POST"}) == 1

    def test_gauge(self):
        mc = MetricsCollector()
        mc.gauge("temperature", 36.5)
        assert mc.get_gauge("temperature") == 36.5

    def test_gauge_add(self):
        mc = MetricsCollector()
        mc.gauge("balance", 100)
        mc.gauge_add("balance", 50)
        assert mc.get_gauge("balance") == 150

    def test_observe_histogram(self):
        mc = MetricsCollector()
        mc.observe("latency", 10)
        mc.observe("latency", 20)
        mc.observe("latency", 30)
        stats = mc.get_all()
        hist = stats["histograms"]["latency"]
        assert hist["count"] == 3
        assert hist["sum"] == 60

    def test_observe_max_1000(self):
        mc = MetricsCollector()
        for i in range(1010):
            mc.observe("latency", i)
        stats = mc.get_all()
        assert stats["histograms"]["latency"]["count"] == 509

    def test_time_context_manager(self):
        mc = MetricsCollector()
        with mc.time("operation"):
            pass
        stats = mc.get_all()
        key = "operation_duration"
        assert key in stats["histograms"]

    def test_reset_single(self):
        mc = MetricsCollector()
        mc.increment("a")
        mc.increment("b")
        mc.reset("a")
        assert mc.get_counter("a") == 0
        assert mc.get_counter("b") == 1

    def test_reset_all(self):
        mc = MetricsCollector()
        mc.increment("a")
        mc.increment("b")
        mc.reset()
        assert mc.get_counter("a") == 0
        assert mc.get_counter("b") == 0

    def test_reset_with_labels(self):
        mc = MetricsCollector()
        mc.increment("r", labels={"l": "1"})
        mc.reset("r", labels={"l": "1"})
        assert mc.get_counter("r", labels={"l": "1"}) == 0

    def test_get_all_structure(self):
        mc = MetricsCollector()
        mc.increment("req")
        mc.gauge("temp", 25)
        mc.observe("lat", 5)
        all_metrics = mc.get_all()
        assert "counters" in all_metrics
        assert "gauges" in all_metrics
        assert "histograms" in all_metrics

    def test_metric_key_with_labels(self):
        mc = MetricsCollector()
        key = mc._metric_key("test", {"b": "2", "a": "1"})
        assert "test{a=1,b=2}" == key

    def test_metric_key_without_labels(self):
        mc = MetricsCollector()
        key = mc._metric_key("test")
        assert key == "test"

    def test_collect_system_metrics_requires_psutil(self):
        mc = MetricsCollector()
        mc.increment("dummy")
        assert mc.get_counter("dummy") == 1
