"""Helm chart templating — generate Chart.yaml, values.yaml, and templates."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
import json
import yaml


@dataclass
class HelmValue:
    key: str
    default: Any = ""
    description: str = ""
    required: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {"value": self.default, "description": self.description, "required": self.required}


@dataclass
class HelmTemplate:
    name: str
    kind: str
    api_version: str = "v1"
    content: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {"name": self.name, "kind": self.kind, "apiVersion": self.api_version, "content": self.content}


@dataclass
class HelmChart:
    name: str
    version: str = "1.0.0"
    app_version: str = "1.0.0"
    description: str = ""
    maintainers: List[Dict[str, str]] = field(default_factory=list)
    values: List[HelmValue] = field(default_factory=list)
    templates: List[HelmTemplate] = field(default_factory=list)

    def add_value(self, key: str, default: Any = "", description: str = "", required: bool = False):
        self.values.append(HelmValue(key=key, default=default, description=description, required=required))
        return self

    def add_template(self, name: str, kind: str, content: str, api_version: str = "v1"):
        self.templates.append(HelmTemplate(name=name, kind=kind, content=content, api_version=api_version))
        return self

    def render_chart_yaml(self) -> str:
        chart = {
            "apiVersion": "v2",
            "name": self.name,
            "version": self.version,
            "appVersion": self.app_version,
            "description": self.description or f"CK-NEXUS Helm chart for {self.name}",
        }
        if self.maintainers:
            chart["maintainers"] = self.maintainers
        return yaml.dump(chart, default_flow_style=False, sort_keys=False)

    def render_values_yaml(self) -> str:
        values_dict = {}
        for v in self.values:
            values_dict[v.key] = v.default
        return yaml.dump(values_dict, default_flow_style=False, sort_keys=False)

    def render_template(self, tpl: HelmTemplate) -> str:
        return tpl.content

    def render_all_templates(self) -> Dict[str, str]:
        return {tpl.name: tpl.content for tpl in self.templates}

    def get_summary(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "app_version": self.app_version,
            "values_count": len(self.values),
            "templates_count": len(self.templates),
        }


def create_ck_nexus_chart(name: str = "ck-nexus", namespace: str = "ck-nexus") -> HelmChart:
    chart = HelmChart(name=name, description="CK-NEXUS Enterprise AIOS Helm Chart")

    chart.add_value("replicaCount", 1, "Number of replicas")
    chart.add_value("image.repository", "ghcr.io/pnook301-code/Ai-ck", "Image repository")
    chart.add_value("image.tag", "latest", "Image tag")
    chart.add_value("service.type", "ClusterIP", "Service type")
    chart.add_value("service.port", 80, "Service port")
    chart.add_value("ingress.enabled", False, "Enable ingress")
    chart.add_value("ingress.host", "", "Ingress host")
    chart.add_value("autoscaling.enabled", True, "Enable HPA")
    chart.add_value("autoscaling.minReplicas", 1, "Min replicas")
    chart.add_value("autoscaling.maxReplicas", 5, "Max replicas")
    chart.add_value("autoscaling.targetCPUUtilizationPercentage", 80, "CPU target %")
    chart.add_value("resources.requests.cpu", "100m", "CPU request")
    chart.add_value("resources.requests.memory", "128Mi", "Memory request")
    chart.add_value("resources.limits.cpu", "500m", "CPU limit")
    chart.add_value("resources.limits.memory", "512Mi", "Memory limit")
    chart.add_value("env.LOG_LEVEL", "INFO", "Log level")
    chart.add_value("env.PORT", 8080, "Application port")

    dep_tpl = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{{{ include "{name}.name" . }}}}
  namespace: {{{{ .Release.Namespace }}}}
spec:
  replicas: {{{{ .Values.replicaCount }}}}
  selector:
    matchLabels:
      app: {{{{ include "{name}.name" . }}}}
  template:
    metadata:
      labels:
        app: {{{{ include "{name}.name" . }}}}
    spec:
      containers:
      - name: {{{{ include "{name}.name" . }}}}
        image: "{{{{ .Values.image.repository }}}}:{{{{ .Values.image.tag }}}}"
        ports:
        - containerPort: {{{{ .Values.env.PORT }}}}
        resources:
          {{{{ toYaml .Values.resources | nindent 10 }}}}
        readinessProbe:
          httpGet:
            path: /health
            port: {{{{ .Values.env.PORT }}}}
          initialDelaySeconds: 5
        livenessProbe:
          httpGet:
            path: /health
            port: {{{{ .Values.env.PORT }}}}
          initialDelaySeconds: 15"""
    chart.add_template("deployment.yaml", "Deployment", dep_tpl, "apps/v1")

    svc_tpl = f"""apiVersion: v1
kind: Service
metadata:
  name: {{{{ include "{name}.name" . }}}}
  namespace: {{{{ .Release.Namespace }}}}
spec:
  type: {{{{ .Values.service.type }}}}
  ports:
  - port: {{{{ .Values.service.port }}}}
    targetPort: {{{{ .Values.env.PORT }}}}
  selector:
    app: {{{{ include "{name}.name" . }}}}"""
    chart.add_template("service.yaml", "Service", svc_tpl, "v1")

    hpa_tpl = f"""{{{{- if .Values.autoscaling.enabled }}}}
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{{{ include "{name}.name" . }}}}
  namespace: {{{{ .Release.Namespace }}}}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{{{ include "{name}.name" . }}}}
  minReplicas: {{{{ .Values.autoscaling.minReplicas }}}}
  maxReplicas: {{{{ .Values.autoscaling.maxReplicas }}}}
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: {{{{ .Values.autoscaling.targetCPUUtilizationPercentage }}}}
{{{{- end }}}}"""
    chart.add_template("hpa.yaml", "HPA", hpa_tpl, "autoscaling/v2")

    return chart
