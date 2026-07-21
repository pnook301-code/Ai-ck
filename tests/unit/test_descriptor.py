from kernel.descriptor import ServiceDescriptor, create_service_descriptor
from kernel.lifetime import ServiceLifetime


class TestServiceDescriptor:
    def test_default_lifetime_is_transient(self):
        desc = ServiceDescriptor(name="test", implementation=str)
        assert desc.lifetime == ServiceLifetime.TRANSIENT

    def test_factory_detection_from_callable(self):
        def factory():
            return "hello"
        desc = ServiceDescriptor(name="factory", implementation=factory)
        assert desc.factory is not None
        assert desc.factory() == "hello"

    def test_factory_not_set_for_class(self):
        desc = ServiceDescriptor(name="class", implementation=str)
        assert desc.factory is None

    def test_is_class(self):
        desc = ServiceDescriptor(name="str", implementation=str)
        assert desc.is_class() is True
        desc2 = ServiceDescriptor(name="inst", implementation="hello")
        assert desc2.is_class() is False

    def test_is_factory(self):
        desc = ServiceDescriptor(name="f", implementation=lambda: 1)
        assert desc.is_factory() is True
        desc2 = ServiceDescriptor(name="s", implementation="hello")
        assert desc2.is_factory() is False

    def test_is_instance_for_non_callable(self):
        desc = ServiceDescriptor(name="inst", implementation=42)
        assert desc.is_instance() is True

    def test_is_instance_with_explicit_instance(self):
        desc = ServiceDescriptor(
            name="test", implementation=str, instance="override"
        )
        assert desc.is_instance() is True

    def test_dependencies_and_tags(self):
        desc = ServiceDescriptor(
            name="complex",
            implementation=str,
            dependencies=["config", "logger"],
            tags={"version": "1", "type": "core"}
        )
        assert desc.dependencies == ["config", "logger"]
        assert desc.tags["version"] == "1"
        assert desc.tags["type"] == "core"


class TestCreateServiceDescriptor:
    def test_create_with_minimal_args(self):
        desc = create_service_descriptor("minimal", int)
        assert desc.name == "minimal"
        assert desc.implementation is int
        assert desc.lifetime == ServiceLifetime.TRANSIENT
        assert desc.dependencies == []
        assert desc.tags == {}

    def test_create_with_all_args(self):
        desc = create_service_descriptor(
            "full", dict,
            lifetime=ServiceLifetime.SINGLETON,
            dependencies=["a", "b"],
            tags={"env": "test"}
        )
        assert desc.name == "full"
        assert desc.lifetime == ServiceLifetime.SINGLETON
        assert desc.dependencies == ["a", "b"]
        assert desc.tags == {"env": "test"}

    def test_dependencies_default_to_empty_list(self):
        desc = create_service_descriptor("x", int)
        assert desc.dependencies == []

    def test_tags_default_to_empty_dict(self):
        desc = create_service_descriptor("x", int)
        assert desc.tags == {}
