"""Kubernetes manifest builder — type-safe K8s resource generation."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json
import yaml


@dataclass
class K8sMetadata:
    name: str
    namespace: str = "default"
    labels: Dict[str, str] = field(default_factory=dict)
    annotations: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"name": self.name, "namespace": self.namespace}
        if self.labels:
            d["labels"] = self.labels
        if self.annotations:
            d["annotations"] = self.annotations
        return d


@dataclass
class ContainerPort:
    name: str = "http"
    container_port: int = 8080
    protocol: str = "TCP"


@dataclass
class EnvVar:
    name: str
    value: str = ""
    value_from: Optional[Dict[str, Any]] = None


@dataclass
class ResourceRequirements:
    requests: Dict[str, str] = field(default_factory=dict)
    limits: Dict[str, str] = field(default_factory=dict)


@dataclass
class Probe:
    http_get: Optional[Dict[str, Any]] = None
    tcp_socket: Optional[Dict[str, Any]] = None
    exec: Optional[Dict[str, Any]] = None
    initial_delay_seconds: int = 10
    period_seconds: int = 10
    timeout_seconds: int = 5
    failure_threshold: int = 3

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "initialDelaySeconds": self.initial_delay_seconds,
            "periodSeconds": self.period_seconds,
            "timeoutSeconds": self.timeout_seconds,
            "failureThreshold": self.failure_threshold,
        }
        if self.http_get:
            d["httpGet"] = self.http_get
        elif self.tcp_socket:
            d["tcpSocket"] = self.tcp_socket
        elif self.exec:
            d["exec"] = self.exec
        return d


@dataclass
class Container:
    name: str
    image: str
    ports: List[ContainerPort] = field(default_factory=list)
    env: List[EnvVar] = field(default_factory=list)
    resources: Optional[ResourceRequirements] = None
    readiness_probe: Optional[Probe] = None
    liveness_probe: Optional[Probe] = None
    command: List[str] = field(default_factory=list)
    args: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"name": self.name, "image": self.image}
        if self.ports:
            d["ports"] = [{"name": p.name, "containerPort": p.container_port, "protocol": p.protocol} for p in self.ports]
        if self.env:
            d["env"] = [{"name": e.name, "value": e.value} if not e.value_from else {"name": e.name, "valueFrom": e.value_from} for e in self.env]
        if self.resources:
            d["resources"] = {}
            if self.resources.requests:
                d["resources"]["requests"] = self.resources.requests
            if self.resources.limits:
                d["resources"]["limits"] = self.resources.limits
        if self.readiness_probe:
            d["readinessProbe"] = self.readiness_probe.to_dict()
        if self.liveness_probe:
            d["livenessProbe"] = self.liveness_probe.to_dict()
        if self.command:
            d["command"] = self.command
        if self.args:
            d["args"] = self.args
        return d


@dataclass
class Deployment:
    metadata: K8sMetadata
    replicas: int = 1
    containers: List[Container] = field(default_factory=list)
    selector_labels: Dict[str, str] = field(default_factory=dict)
    strategy: str = "RollingUpdate"

    def to_dict(self) -> Dict[str, Any]:
        labels = self.selector_labels or {"app": self.metadata.name}
        return {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "metadata": self.metadata.to_dict(),
            "spec": {
                "replicas": self.replicas,
                "selector": {"matchLabels": labels},
                "strategy": {"type": self.strategy},
                "template": {
                    "metadata": {"labels": {**labels, **self.metadata.labels}},
                    "spec": {
                        "containers": [c.to_dict() for c in self.containers],
                    },
                },
            },
        }


@dataclass
class Service:
    metadata: K8sMetadata
    selector: Dict[str, str] = field(default_factory=dict)
    port: int = 80
    target_port: int = 8080
    protocol: str = "TCP"
    service_type: str = "ClusterIP"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": self.metadata.to_dict(),
            "spec": {
                "type": self.service_type,
                "selector": self.selector or {"app": self.metadata.name},
                "ports": [{"port": self.port, "targetPort": self.target_port, "protocol": self.protocol}],
            },
        }


@dataclass
class Ingress:
    metadata: K8sMetadata
    host: str = ""
    path: str = "/"
    path_type: str = "Prefix"
    service_name: str = ""
    service_port: int = 80
    tls: bool = False
    tls_secret: str = ""
    annotations: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        svc_ref = {"name": self.service_name or self.metadata.name, "port": {"number": self.service_port}}
        backend = {"service": svc_ref}
        path_entry = {"path": self.path, "pathType": self.path_type, "backend": backend}

        rules = []
        if self.host:
            rules.append({"host": self.host, "http": {"paths": [path_entry]}})
        else:
            rules.append({"http": {"paths": [path_entry]}})

        meta = self.metadata.to_dict()
        if self.annotations:
            meta["annotations"] = {**meta.get("annotations", {}), **self.annotations}

        spec: Dict[str, Any] = {"rules": rules}
        if self.tls:
            spec["tls"] = [{"hosts": [self.host], "secretName": self.tls_secret or f"{self.metadata.name}-tls"}]

        return {"apiVersion": "networking.k8s.io/v1", "kind": "Ingress", "metadata": meta, "spec": spec}


@dataclass
class HPA:
    metadata: K8sMetadata
    min_replicas: int = 1
    max_replicas: int = 10
    target_cpu_percent: int = 80
    target_memory_percent: int = 80

    def to_dict(self) -> Dict[str, Any]:
        return {
            "apiVersion": "autoscaling/v2",
            "kind": "HorizontalPodAutoscaler",
            "metadata": self.metadata.to_dict(),
            "spec": {
                "scaleTargetRef": {"apiVersion": "apps/v1", "kind": "Deployment", "name": self.metadata.name},
                "minReplicas": self.min_replicas,
                "maxReplicas": self.max_replicas,
                "metrics": [
                    {"type": "Resource", "resource": {"name": "cpu", "target": {"type": "Utilization", "averageUtilization": self.target_cpu_percent}}},
                    {"type": "Resource", "resource": {"name": "memory", "target": {"type": "Utilization", "averageUtilization": self.target_memory_percent}}},
                ],
            },
        }


@dataclass
class PDB:
    metadata: K8sMetadata
    min_available: int = 1
    selector_labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "apiVersion": "policy/v1",
            "kind": "PodDisruptionBudget",
            "metadata": self.metadata.to_dict(),
            "spec": {
                "minAvailable": self.min_available,
                "selector": {"matchLabels": self.selector_labels or {"app": self.metadata.name}},
            },
        }


@dataclass
class ServiceAccount:
    metadata: K8sMetadata

    def to_dict(self) -> Dict[str, Any]:
        return {"apiVersion": "v1", "kind": "ServiceAccount", "metadata": self.metadata.to_dict()}


@dataclass
class Namespace:
    name: str
    labels: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": self.name}}
        if self.labels:
            d["metadata"]["labels"] = self.labels
        return d


@dataclass
class ConfigMap:
    metadata: K8sMetadata
    data: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"apiVersion": "v1", "kind": "ConfigMap", "metadata": self.metadata.to_dict(), "data": self.data}


@dataclass
class Secret:
    metadata: K8sMetadata
    string_data: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {"apiVersion": "v1", "kind": "Secret", "metadata": self.metadata.to_dict(), "type": "Opaque", "stringData": self.string_data}


class ManifestBuilder:
    def __init__(self, namespace: str = "default", prefix: str = "ck-nexus"):
        self.namespace = namespace
        self.prefix = prefix
        self._resources: List[Dict[str, Any]] = []

    def _meta(self, name: str, labels: Optional[Dict[str, str]] = None) -> K8sMetadata:
        full_name = f"{self.prefix}-{name}" if not name.startswith(self.prefix) else name
        return K8sMetadata(name=full_name, namespace=self.namespace, labels=labels or {"app": full_name, "managed-by": "ck-nexus"})

    def add_deployment(self, name: str, image: str, replicas: int = 1,
                       ports: Optional[List[int]] = None,
                       env: Optional[Dict[str, str]] = None,
                       cpu_request: str = "100m", cpu_limit: str = "500m",
                       mem_request: str = "128Mi", mem_limit: str = "512Mi") -> Deployment:
        meta = self._meta(name)
        container_ports = [ContainerPort(container_port=p) for p in (ports or [8080])]
        container_env = [EnvVar(name=k, value=v) for k, v in (env or {}).items()]
        resources = ResourceRequirements(requests={"cpu": cpu_request, "memory": mem_request}, limits={"cpu": cpu_limit, "memory": mem_limit})
        readiness = Probe(http_get={"path": "/health", "port": 8080}, initial_delay_seconds=5)
        liveness = Probe(http_get={"path": "/health", "port": 8080}, initial_delay_seconds=15, period_seconds=20)
        container = Container(name=meta.name, image=image, ports=container_ports, env=container_env, resources=resources, readiness_probe=readiness, liveness_probe=liveness)
        dep = Deployment(metadata=meta, replicas=replicas, containers=[container])
        self._resources.append(dep.to_dict())
        return dep

    def add_service(self, name: str, port: int = 80, target_port: int = 8080,
                    service_type: str = "ClusterIP") -> Service:
        meta = self._meta(name)
        svc = Service(metadata=meta, port=port, target_port=target_port, service_type=service_type)
        self._resources.append(svc.to_dict())
        return svc

    def add_ingress(self, name: str, host: str, path: str = "/", tls: bool = False,
                    annotations: Optional[Dict[str, str]] = None) -> Ingress:
        meta = self._meta(name)
        ing = Ingress(metadata=meta, host=host, path=path, tls=tls, annotations=annotations or {})
        self._resources.append(ing.to_dict())
        return ing

    def add_hpa(self, name: str, min_replicas: int = 1, max_replicas: int = 10,
                cpu_percent: int = 80) -> HPA:
        meta = self._meta(name)
        hpa = HPA(metadata=meta, min_replicas=min_replicas, max_replicas=max_replicas, target_cpu_percent=cpu_percent)
        self._resources.append(hpa.to_dict())
        return hpa

    def add_pdb(self, name: str, min_available: int = 1) -> PDB:
        meta = self._meta(name)
        pdb = PDB(metadata=meta, min_available=min_available)
        self._resources.append(pdb.to_dict())
        return pdb

    def add_service_account(self, name: str) -> ServiceAccount:
        meta = self._meta(name)
        sa = ServiceAccount(metadata=meta)
        self._resources.append(sa.to_dict())
        return sa

    def add_namespace(self, name: str, labels: Optional[Dict[str, str]] = None) -> Namespace:
        ns = Namespace(name=name, labels=labels or {"managed-by": "ck-nexus"})
        self._resources.append(ns.to_dict())
        return ns

    def add_configmap(self, name: str, data: Dict[str, str]) -> ConfigMap:
        meta = self._meta(name)
        cm = ConfigMap(metadata=meta, data=data)
        self._resources.append(cm.to_dict())
        return cm

    def add_secret(self, name: str, string_data: Dict[str, str]) -> Secret:
        meta = self._meta(name)
        secret = Secret(metadata=meta, string_data=string_data)
        self._resources.append(secret.to_dict())
        return secret

    def to_yaml(self) -> str:
        return yaml.dump_all(self._resources, default_flow_style=False, sort_keys=False)

    def to_json(self) -> str:
        return json.dumps(self._resources, indent=2)

    def to_dicts(self) -> List[Dict[str, Any]]:
        return list(self._resources)

    def get_resource_count(self) -> int:
        return len(self._resources)

    def clear(self):
        self._resources.clear()
