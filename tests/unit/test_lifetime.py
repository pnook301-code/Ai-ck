from kernel.lifetime import ServiceLifetime


class TestServiceLifetime:
    def test_enum_values(self):
        assert ServiceLifetime.SINGLETON.value == "singleton"
        assert ServiceLifetime.SCOPED.value == "scoped"
        assert ServiceLifetime.TRANSIENT.value == "transient"

    def test_enum_members(self):
        assert len(ServiceLifetime) == 3
        names = {m.name for m in ServiceLifetime}
        assert names == {"SINGLETON", "SCOPED", "TRANSIENT"}
