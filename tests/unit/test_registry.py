import pytest
from kernel.registry import ServiceRegistry
from kernel.descriptor import ServiceDescriptor
from kernel.lifetime import ServiceLifetime


class TestServiceRegistry:
    def test_register_and_resolve(self):
        registry = ServiceRegistry()
        registry.register_simple("str", str)
        result = registry.resolve("str")
        assert isinstance(result, str)
        assert result == ""

    def test_register_instance(self):
        registry = ServiceRegistry()
        obj = {"key": "value"}
        registry.register_instance("config", obj)
        result = registry.resolve("config")
        assert result is obj

    def test_resolve_singleton_returns_same_instance(self):
        registry = ServiceRegistry()

        class MyService:
            pass

        registry.register_simple("svc", MyService, lifetime=ServiceLifetime.SINGLETON)
        a = registry.resolve("svc")
        b = registry.resolve("svc")
        assert a is b

    def test_resolve_transient_returns_new_instance(self):
        registry = ServiceRegistry()

        class MyService:
            pass

        registry.register_simple("svc", MyService, lifetime=ServiceLifetime.TRANSIENT)
        a = registry.resolve("svc")
        b = registry.resolve("svc")
        assert a is not b

    def test_resolve_scoped_same_scope(self):
        registry = ServiceRegistry()

        class MyService:
            pass

        registry.register_simple("svc", MyService, lifetime=ServiceLifetime.SCOPED)
        a = registry.resolve("svc", scope="req1")
        b = registry.resolve("svc", scope="req1")
        assert a is b

    def test_resolve_scoped_different_scopes(self):
        registry = ServiceRegistry()

        class MyService:
            pass

        registry.register_simple("svc", MyService, lifetime=ServiceLifetime.SCOPED)
        a = registry.resolve("svc", scope="req1")
        b = registry.resolve("svc", scope="req2")
        assert a is not b

    def test_unregister(self):
        registry = ServiceRegistry()
        registry.register_simple("svc", str)
        assert registry.has_service("svc") is True
        assert registry.unregister("svc") is True
        assert registry.has_service("svc") is False
        assert registry.unregister("svc") is False

    def test_resolve_nonexistent_raises(self):
        registry = ServiceRegistry()
        with pytest.raises(KeyError, match="not registered"):
            registry.resolve("nonexistent")

    def test_resolve_typed_by_class(self):
        registry = ServiceRegistry()

        class Base:
            pass

        class Impl(Base):
            pass

        registry.register_simple("impl", Impl)
        result = registry.resolve_typed(Impl)
        assert isinstance(result, Impl)

    def test_resolve_typed_by_base(self):
        registry = ServiceRegistry()

        class Base:
            pass

        class Impl(Base):
            pass

        registry.register_simple("impl", Impl)
        result = registry.resolve_typed(Base)
        assert isinstance(result, Impl)

    def test_resolve_typed_no_match(self):
        registry = ServiceRegistry()
        registry.register_simple("str", str)
        result = registry.resolve_typed(int)
        assert result is None

    def test_resolve_all_with_tag(self):
        registry = ServiceRegistry()
        registry.register_simple("a", str, tags={"tier": "core"})
        registry.register_simple("b", int, tags={"tier": "core"})
        registry.register_simple("c", float, tags={"tier": "extra"})
        results = registry.resolve_all_with_tag("tier", "core")
        assert len(results) == 2

    def test_resolve_all_with_tag_key_only(self):
        registry = ServiceRegistry()
        registry.register_simple("a", str, tags={"env": "test"})
        registry.register_simple("b", int, tags={"env": "prod"})
        results = registry.resolve_all_with_tag("env")
        assert len(results) == 2

    def test_clear_scope(self):
        registry = ServiceRegistry()

        class MyService:
            pass

        registry.register_simple("svc", MyService, lifetime=ServiceLifetime.SCOPED)
        a = registry.resolve("svc", scope="req1")
        registry.clear_scope("req1")
        b = registry.resolve("svc", scope="req1")
        assert a is not b

    def test_clear_all(self):
        registry = ServiceRegistry()
        registry.register_simple("a", str)
        registry.register_simple("b", int)
        assert len(registry.get_names()) == 2
        registry.clear_all()
        assert len(registry.get_names()) == 0

    def test_has_service(self):
        registry = ServiceRegistry()
        assert registry.has_service("x") is False
        registry.register_simple("x", str)
        assert registry.has_service("x") is True

    def test_get_names(self):
        registry = ServiceRegistry()
        registry.register_simple("a", str)
        registry.register_simple("b", int)
        names = registry.get_names()
        assert sorted(names) == ["a", "b"]

    def test_factory_function_resolves(self):
        registry = ServiceRegistry()

        def maker():
            return {"created": True}

        registry.register_simple("maker", maker)
        result = registry.resolve("maker")
        assert result == {"created": True}

    def test_logger_passthrough(self, test_logger):
        registry = ServiceRegistry(logger=test_logger)
        registry.register_simple("svc", str)
        assert registry.has_service("svc")

    def test_resolve_singleton_factory(self):
        registry = ServiceRegistry()
        calls = []

        def factory():
            calls.append(1)
            return {"count": len(calls)}

        registry.register_simple("f", factory, lifetime=ServiceLifetime.SINGLETON)
        a = registry.resolve("f")
        b = registry.resolve("f")
        assert a is b
        assert len(calls) == 1

    def test_service_descriptor_in_services_property(self):
        registry = ServiceRegistry()
        desc = ServiceDescriptor(name="svc", implementation=str)
        registry.register(desc)
        assert registry.services["svc"] is desc
