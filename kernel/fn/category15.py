"""Category 15 — Kubernetes Functions (15.1–15.12)."""
from typing import Any, Dict


async def fn_15_1_create_deployment(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.k8s.manifests import ManifestBuilder
    builder = ManifestBuilder(namespace=input_data.get("namespace", "default"), prefix=input_data.get("prefix", "ck-nexus"))
    dep = builder.add_deployment(
        name=input_data.get("name", "app"),
        image=input_data.get("image", "nginx:latest"),
        replicas=input_data.get("replicas", 1),
        ports=input_data.get("ports", [8080]),
    )
    return {"deployment": dep.to_dict(), "yaml": builder.to_yaml()}


async def fn_15_2_create_service(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.k8s.manifests import ManifestBuilder
    builder = ManifestBuilder(namespace=input_data.get("namespace", "default"))
    svc = builder.add_service(name=input_data.get("name", "app"), port=input_data.get("port", 80), target_port=input_data.get("target_port", 8080), service_type=input_data.get("type", "ClusterIP"))
    return {"service": svc.to_dict(), "yaml": builder.to_yaml()}


async def fn_15_3_create_ingress(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.k8s.manifests import ManifestBuilder
    builder = ManifestBuilder(namespace=input_data.get("namespace", "default"))
    ing = builder.add_ingress(name=input_data.get("name", "app"), host=input_data.get("host", ""), path=input_data.get("path", "/"), tls=input_data.get("tls", False))
    return {"ingress": ing.to_dict(), "yaml": builder.to_yaml()}


async def fn_15_4_create_hpa(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.k8s.manifests import ManifestBuilder
    builder = ManifestBuilder(namespace=input_data.get("namespace", "default"))
    hpa = builder.add_hpa(name=input_data.get("name", "app"), min_replicas=input_data.get("min_replicas", 1), max_replicas=input_data.get("max_replicas", 10), cpu_percent=input_data.get("cpu_percent", 80))
    return {"hpa": hpa.to_dict(), "yaml": builder.to_yaml()}


async def fn_15_5_create_pdb(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.k8s.manifests import ManifestBuilder
    builder = ManifestBuilder(namespace=input_data.get("namespace", "default"))
    pdb = builder.add_pdb(name=input_data.get("name", "app"), min_available=input_data.get("min_available", 1))
    return {"pdb": pdb.to_dict(), "yaml": builder.to_yaml()}


async def fn_15_6_create_namespace(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.k8s.manifests import ManifestBuilder
    builder = ManifestBuilder()
    ns = builder.add_namespace(name=input_data.get("name", "ck-nexus"), labels=input_data.get("labels", {}))
    return {"namespace": ns.to_dict(), "yaml": builder.to_yaml()}


async def fn_15_7_create_configmap(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.k8s.manifests import ManifestBuilder
    builder = ManifestBuilder(namespace=input_data.get("namespace", "default"))
    cm = builder.add_configmap(name=input_data.get("name", "config"), data=input_data.get("data", {}))
    return {"configmap": cm.to_dict(), "yaml": builder.to_yaml()}


async def fn_15_8_create_secret(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.k8s.manifests import ManifestBuilder
    builder = ManifestBuilder(namespace=input_data.get("namespace", "default"))
    secret = builder.add_secret(name=input_data.get("name", "secret"), string_data=input_data.get("string_data", {}))
    return {"secret": secret.to_dict(), "yaml": builder.to_yaml()}


async def fn_15_9_full_stack(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.k8s.manifests import ManifestBuilder
    ns = input_data.get("namespace", "ck-nexus")
    name = input_data.get("name", "ck-nexus")
    image = input_data.get("image", "ghcr.io/pnook301-code/Ai-ck:latest")
    host = input_data.get("host", "")
    builder = ManifestBuilder(namespace=ns, prefix=name)
    builder.add_namespace(ns)
    builder.add_deployment(name=name, image=image, replicas=input_data.get("replicas", 2))
    builder.add_service(name=name)
    if host:
        builder.add_ingress(name=name, host=host, tls=input_data.get("tls", False))
    if input_data.get("autoscaling", True):
        builder.add_hpa(name=name, min_replicas=input_data.get("min_replicas", 1), max_replicas=input_data.get("max_replicas", 5))
    builder.add_pdb(name=name, min_available=1)
    builder.add_service_account(name)
    return {"resources": builder.to_dicts(), "count": builder.get_resource_count(), "yaml": builder.to_yaml()}


async def fn_15_10_render_helm(input_data: Dict[str, Any]) -> Dict[str, Any]:
    from kernel.k8s.helm import create_ck_nexus_chart
    chart = create_ck_nexus_chart(name=input_data.get("name", "ck-nexus"), namespace=input_data.get("namespace", "ck-nexus"))
    return {"chart_yaml": chart.render_chart_yaml(), "values_yaml": chart.render_values_yaml(), "templates": chart.render_all_templates(), "summary": chart.get_summary()}


async def fn_15_11_validate_manifest(input_data: Dict[str, Any]) -> Dict[str, Any]:
    manifest = input_data.get("manifest", {})
    errors = []
    if not isinstance(manifest, dict):
        return {"valid": False, "errors": ["Manifest must be a dict"]}
    if "apiVersion" not in manifest:
        errors.append("Missing apiVersion")
    if "kind" not in manifest:
        errors.append("Missing kind")
    if "metadata" not in manifest:
        errors.append("Missing metadata")
    elif "name" not in manifest.get("metadata", {}):
        errors.append("Missing metadata.name")
    if manifest.get("kind") == "Deployment":
        spec = manifest.get("spec", {})
        if "selector" not in spec:
            errors.append("Deployment missing selector")
        if "template" not in spec:
            errors.append("Deployment missing template")
    return {"valid": len(errors) == 0, "errors": errors, "kind": manifest.get("kind", "unknown")}


async def fn_15_12_status(input_data: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "module": "kubernetes",
        "supported_resources": ["Deployment", "Service", "Ingress", "HPA", "PDB", "Namespace", "ConfigMap", "Secret", "ServiceAccount"],
        "functions": 12,
        "helm_support": True,
    }


def _def(name, fn_id, desc, handler, params):
    from kernel.fn.types import FunctionDefinition, FunctionCategory
    return FunctionDefinition(
        id=fn_id, name=name, description=desc,
        category=FunctionCategory.KUBERNETES,
        handler=handler, input_schema=params,
    )


def register_kubernetes(registry):
    fns = [
        _def("k8s_create_deployment", "15.1", "Create K8s Deployment manifest", fn_15_1_create_deployment, {
            "name": {"type": "string", "required": True}, "image": {"type": "string", "required": True},
            "replicas": {"type": "integer", "default": 1}, "ports": {"type": "array", "default": [8080]},
            "namespace": {"type": "string", "default": "default"}, "prefix": {"type": "string", "default": "ck-nexus"},
        }),
        _def("k8s_create_service", "15.2", "Create K8s Service manifest", fn_15_2_create_service, {
            "name": {"type": "string", "required": True}, "port": {"type": "integer", "default": 80},
            "target_port": {"type": "integer", "default": 8080}, "type": {"type": "string", "default": "ClusterIP"},
            "namespace": {"type": "string", "default": "default"},
        }),
        _def("k8s_create_ingress", "15.3", "Create K8s Ingress manifest", fn_15_3_create_ingress, {
            "name": {"type": "string", "required": True}, "host": {"type": "string", "required": True},
            "path": {"type": "string", "default": "/"}, "tls": {"type": "boolean", "default": False},
            "namespace": {"type": "string", "default": "default"},
        }),
        _def("k8s_create_hpa", "15.4", "Create K8s HPA manifest", fn_15_4_create_hpa, {
            "name": {"type": "string", "required": True}, "min_replicas": {"type": "integer", "default": 1},
            "max_replicas": {"type": "integer", "default": 10}, "cpu_percent": {"type": "integer", "default": 80},
            "namespace": {"type": "string", "default": "default"},
        }),
        _def("k8s_create_pdb", "15.5", "Create K8s PDB manifest", fn_15_5_create_pdb, {
            "name": {"type": "string", "required": True}, "min_available": {"type": "integer", "default": 1},
            "namespace": {"type": "string", "default": "default"},
        }),
        _def("k8s_create_namespace", "15.6", "Create K8s Namespace", fn_15_6_create_namespace, {
            "name": {"type": "string", "required": True}, "labels": {"type": "object", "default": {}},
        }),
        _def("k8s_create_configmap", "15.7", "Create K8s ConfigMap", fn_15_7_create_configmap, {
            "name": {"type": "string", "required": True}, "data": {"type": "object", "required": True},
            "namespace": {"type": "string", "default": "default"},
        }),
        _def("k8s_create_secret", "15.8", "Create K8s Secret", fn_15_8_create_secret, {
            "name": {"type": "string", "required": True}, "string_data": {"type": "object", "required": True},
            "namespace": {"type": "string", "default": "default"},
        }),
        _def("k8s_full_stack", "15.9", "Generate full K8s stack (ns+dep+svc+ing+hpa+pdb)", fn_15_9_full_stack, {
            "name": {"type": "string", "required": True}, "image": {"type": "string", "required": True},
            "namespace": {"type": "string", "default": "ck-nexus"}, "host": {"type": "string", "default": ""},
            "replicas": {"type": "integer", "default": 2}, "tls": {"type": "boolean", "default": False},
            "autoscaling": {"type": "boolean", "default": True}, "min_replicas": {"type": "integer", "default": 1},
            "max_replicas": {"type": "integer", "default": 5},
        }),
        _def("k8s_render_helm", "15.10", "Render CK-NEXUS Helm chart", fn_15_10_render_helm, {
            "name": {"type": "string", "default": "ck-nexus"}, "namespace": {"type": "string", "default": "ck-nexus"},
        }),
        _def("k8s_validate_manifest", "15.11", "Validate K8s manifest structure", fn_15_11_validate_manifest, {
            "manifest": {"type": "object", "required": True},
        }),
        _def("k8s_status", "15.12", "Kubernetes module status", fn_15_12_status, {}),
    ]
    for fn in fns:
        registry.register(fn)
    return len(fns)
