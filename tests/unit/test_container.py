import pytest
import pytest
from kernel.container import DIContainer, inject, Inject
from kernel.registry import ServiceRegistry


class TestDIContainer:
    def test_register_and_resolve(self):
        c = DIContainer()
        c.register("str", str)
        result = c.resolve("str")
        assert isinstance(result, str)
        assert result == ""

    def test_register_instance(self):
        c = DIContainer()
        obj = {"key": "val"}
        c.register_instance("cfg", obj)
        assert c.resolve("cfg") is obj

    def test_register_factory(self):
        c = DIContainer()
        c.register_factory("maker", lambda: {"created": True})
        assert c.resolve("maker") == {"created": True}

    def test_resolve_nonexistent_raises(self):
        c = DIContainer()
        with pytest.raises(KeyError, match="Cannot resolve"):
            c.resolve("nothing")

    def test_has(self):
        c = DIContainer()
        assert c.has("x") is False
        c.register("x", str)
        assert c.has("x") is True

    def test_has_from_factory(self):
        c = DIContainer()
        c.register_factory("f", lambda: 1)
        assert c.has("f") is True

    @pytest.mark.asyncio
    async def test_close_clears(self):
        c = DIContainer()
        c.register_instance("x", 1)
        await c.close()
        assert c.has("x") is False

    def test_resolve_typed_with_registry(self):
        registry = ServiceRegistry()

        class Service:
            pass

        registry.register_simple("svc", Service)
        c = DIContainer(registry=registry)
        result = c.resolve_typed(Service)
        assert isinstance(result, Service)

    def test_resolve_typed_no_registry(self):
        c = DIContainer()
        assert c.resolve_typed(str) is None

    def test_resolve_falls_back_to_registry(self):
        registry = ServiceRegistry()
        registry.register_simple("from_reg", str)
        c = DIContainer(registry=registry)
        result = c.resolve("from_reg")
        assert isinstance(result, str)
        assert result == ""

    def test_factory_called_once_cached_as_instance(self):
        c = DIContainer()
        calls = []

        def factory():
            calls.append(1)
            return len(calls)

        c.register_factory("f", factory)
        assert c.resolve("f") == 1
        assert c.resolve("f") == 1
        assert len(calls) == 1

    def test_resolve_class_factory(self):
        c = DIContainer()

        class Service:
            pass

        c.register_factory("svc", Service)
        result = c.resolve("svc")
        assert isinstance(result, Service)


class TestInjectDecorator:
    def test_inject_resolves_from_container(self):
        c = DIContainer()
        c.register_instance("db", "connected")

        @inject(container=c)
        def my_func(db=None):
            return db

        result = my_func()
        assert result == "connected"

    def test_inject_does_not_override_explicit_kwargs(self):
        c = DIContainer()
        c.register_instance("db", "from_container")

        @inject(container=c)
        def my_func(db=None):
            return db

        result = my_func(db="explicit")
        assert result == "explicit"

    def test_inject_no_container_no_error(self):
        @inject()
        def my_func(x=None):
            return x

        result = my_func(x=42)
        assert result == 42

    def test_inject_missing_key_ignored(self):
        c = DIContainer()

        @inject(container=c)
        def my_func(db=None, missing=None):
            return (db, missing)

        result = my_func(db="val")
        assert result == ("val", None)


class TestInjectDescriptor:
    def test_inject_marker(self):
        marker = Inject(name="db_service")
        assert marker.name == "db_service"

    def test_inject_marker_default_name(self):
        marker = Inject()
        assert marker.name is None

    def test_inject_marker_equality(self):
        a = Inject("db")
        b = Inject("db")
        c = Inject("cache")
        assert a.name == b.name
        assert a.name != c.name
