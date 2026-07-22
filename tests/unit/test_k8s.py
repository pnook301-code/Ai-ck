"""Tests for Kubernetes Module — Manifests, Helm, Functions (45+ tests)."""
import pytest
from kernel.k8s.manifests import (
    ManifestBuilder, Deployment, Service, Ingress, HPA, PDB,
    ServiceAccount, Namespace, ConfigMap, Secret,
    K8sMetadata, ContainerPort, EnvVar, ResourceRequirements, Probe, Container,
)
from kernel.k8s.helm import HelmChart, HelmValue, HelmTemplate, create_ck_nexus_chart


class TestK8sMetadata:
    def test_create(self):
        m = K8sMetadata(name="test", namespace="prod")
        assert m.name == "test"
        assert m.namespace == "prod"

    def test_to_dict(self):
        m = K8sMetadata(name="test", labels={"env": "prod"})
        d = m.to_dict()
        assert d["name"] == "test"
        assert d["labels"]["env"] == "prod"

    def test_to_dict_no_labels(self):
        m = K8sMetadata(name="test")
        d = m.to_dict()
        assert "labels" not in d


class TestContainerTypes:
    def test_container_port(self):
        p = ContainerPort(name="http", container_port=8080)
        assert p.container_port == 8080

    def test_env_var(self):
        e = EnvVar(name="LOG_LEVEL", value="INFO")
        assert e.name == "LOG_LEVEL"

    def test_resources(self):
        r = ResourceRequirements(requests={"cpu": "100m"}, limits={"cpu": "500m"})
        assert r.requests["cpu"] == "100m"

    def test_probe_http(self):
        p = Probe(http_get={"path": "/health", "port": 8080})
        d = p.to_dict()
        assert "httpGet" in d
        assert d["httpGet"]["path"] == "/health"

    def test_probe_tcp(self):
        p = Probe(tcp_socket={"port": 8080})
        d = p.to_dict()
        assert "tcpSocket" in d

    def test_container_to_dict(self):
        c = Container(name="app", image="nginx:latest")
        d = c.to_dict()
        assert d["name"] == "app"
        assert d["image"] == "nginx:latest"


class TestDeployment:
    def test_to_dict(self):
        dep = Deployment(
            metadata=K8sMetadata(name="test"),
            replicas=3,
            containers=[Container(name="app", image="nginx")],
        )
        d = dep.to_dict()
        assert d["kind"] == "Deployment"
        assert d["spec"]["replicas"] == 3
        assert len(d["spec"]["template"]["spec"]["containers"]) == 1

    def test_selector_labels(self):
        dep = Deployment(metadata=K8sMetadata(name="test"), selector_labels={"app": "test"})
        d = dep.to_dict()
        assert d["spec"]["selector"]["matchLabels"]["app"] == "test"


class TestService:
    def test_to_dict(self):
        svc = Service(metadata=K8sMetadata(name="test"), port=80, target_port=8080)
        d = svc.to_dict()
        assert d["kind"] == "Service"
        assert d["spec"]["ports"][0]["port"] == 80

    def test_service_type(self):
        svc = Service(metadata=K8sMetadata(name="test"), service_type="NodePort")
        assert svc.to_dict()["spec"]["type"] == "NodePort"


class TestIngress:
    def test_to_dict(self):
        ing = Ingress(metadata=K8sMetadata(name="test"), host="example.com")
        d = ing.to_dict()
        assert d["kind"] == "Ingress"
        assert d["spec"]["rules"][0]["host"] == "example.com"

    def test_tls(self):
        ing = Ingress(metadata=K8sMetadata(name="test"), host="example.com", tls=True)
        d = ing.to_dict()
        assert "tls" in d["spec"]


class TestHPA:
    def test_to_dict(self):
        hpa = HPA(metadata=K8sMetadata(name="test"), min_replicas=1, max_replicas=10)
        d = hpa.to_dict()
        assert d["kind"] == "HorizontalPodAutoscaler"
        assert d["spec"]["minReplicas"] == 1
        assert d["spec"]["maxReplicas"] == 10


class TestPDB:
    def test_to_dict(self):
        pdb = PDB(metadata=K8sMetadata(name="test"), min_available=2)
        d = pdb.to_dict()
        assert d["kind"] == "PodDisruptionBudget"
        assert d["spec"]["minAvailable"] == 2


class TestNamespace:
    def test_to_dict(self):
        ns = Namespace(name="test-ns")
        d = ns.to_dict()
        assert d["kind"] == "Namespace"
        assert d["metadata"]["name"] == "test-ns"


class TestConfigMap:
    def test_to_dict(self):
        cm = ConfigMap(metadata=K8sMetadata(name="cfg"), data={"key": "val"})
        d = cm.to_dict()
        assert d["kind"] == "ConfigMap"
        assert d["data"]["key"] == "val"


class TestSecret:
    def test_to_dict(self):
        s = Secret(metadata=K8sMetadata(name="sec"), string_data={"password": "123"})
        d = s.to_dict()
        assert d["kind"] == "Secret"
        assert d["type"] == "Opaque"


class TestManifestBuilder:
    def test_add_deployment(self):
        b = ManifestBuilder(namespace="prod")
        dep = b.add_deployment("app", "nginx:latest", replicas=3)
        assert dep.metadata.namespace == "prod"
        assert b.get_resource_count() == 1

    def test_add_service(self):
        b = ManifestBuilder()
        svc = b.add_service("app", port=80, target_port=8080)
        assert svc.port == 80
        assert b.get_resource_count() == 1

    def test_add_ingress(self):
        b = ManifestBuilder()
        ing = b.add_ingress("app", host="example.com")
        assert ing.host == "example.com"

    def test_add_hpa(self):
        b = ManifestBuilder()
        hpa = b.add_hpa("app", min_replicas=2, max_replicas=8)
        assert hpa.min_replicas == 2

    def test_add_pdb(self):
        b = ManifestBuilder()
        pdb = b.add_pdb("app", min_available=2)
        assert pdb.min_available == 2

    def test_add_namespace(self):
        b = ManifestBuilder()
        ns = b.add_namespace("prod")
        assert ns.name == "prod"

    def test_add_configmap(self):
        b = ManifestBuilder()
        cm = b.add_configmap("cfg", {"key": "value"})
        assert cm.data["key"] == "value"

    def test_add_secret(self):
        b = ManifestBuilder()
        s = b.add_secret("sec", {"token": "abc"})
        assert s.string_data["token"] == "abc"

    def test_add_service_account(self):
        b = ManifestBuilder()
        sa = b.add_service_account("runner")
        assert sa.metadata.name == "ck-nexus-runner"

    def test_to_yaml(self):
        b = ManifestBuilder()
        b.add_deployment("app", "nginx")
        y = b.to_yaml()
        assert "Deployment" in y
        assert "nginx" in y

    def test_to_json(self):
        b = ManifestBuilder()
        b.add_deployment("app", "nginx")
        j = b.to_json()
        assert "Deployment" in j

    def test_to_dicts(self):
        b = ManifestBuilder()
        b.add_deployment("app", "nginx")
        b.add_service("app")
        d = b.to_dicts()
        assert len(d) == 2

    def test_clear(self):
        b = ManifestBuilder()
        b.add_deployment("app", "nginx")
        b.clear()
        assert b.get_resource_count() == 0


class TestHelmChart:
    def test_create(self):
        chart = HelmChart(name="test")
        assert chart.name == "test"

    def test_add_value(self):
        chart = HelmChart(name="test")
        chart.add_value("replicas", 1, "Number of replicas")
        assert len(chart.values) == 1
        assert chart.values[0].key == "replicas"

    def test_add_template(self):
        chart = HelmChart(name="test")
        chart.add_template("deployment.yaml", "Deployment", "content here")
        assert len(chart.templates) == 1

    def test_render_chart_yaml(self):
        chart = HelmChart(name="test", version="2.0.0")
        y = chart.render_chart_yaml()
        assert "test" in y
        assert "2.0.0" in y

    def test_render_values_yaml(self):
        chart = HelmChart(name="test")
        chart.add_value("replicas", 3)
        y = chart.render_values_yaml()
        assert "3" in y or "replicas" in y

    def test_render_all_templates(self):
        chart = HelmChart(name="test")
        chart.add_template("dep.yaml", "Deployment", "dep-content")
        chart.add_template("svc.yaml", "Service", "svc-content")
        tpls = chart.render_all_templates()
        assert len(tpls) == 2
        assert "dep.yaml" in tpls

    def test_summary(self):
        chart = HelmChart(name="test", version="1.0.0")
        chart.add_value("a", 1)
        chart.add_template("t.yaml", "Deployment", "c")
        s = chart.get_summary()
        assert s["values_count"] == 1
        assert s["templates_count"] == 1


class TestCreateCKNexusChart:
    def test_creates_full_chart(self):
        chart = create_ck_nexus_chart()
        assert chart.name == "ck-nexus"
        assert len(chart.values) > 10
        assert len(chart.templates) >= 2

    def test_custom_name(self):
        chart = create_ck_nexus_chart(name="my-app")
        assert chart.name == "my-app"
