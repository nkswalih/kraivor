import math
import re

from app.core.logging import get_logger
from app.workers.devops.models import DevOpsFinding

logger = get_logger(__name__)


class DevopsAnalyzer:
    def __init__(self, parsed_files):
        self.parsed_files = parsed_files
        self._project_has_health = False
        self._project_has_observability = False
        self._project_has_operations = False

    async def scan_all(self) -> list[DevOpsFinding]:
        results = []
        for pf in self.parsed_files:
            fp = pf.path.lower()
            content = pf.content
            results.extend(self._analyze_dockerfile(fp, content))
            results.extend(self._analyze_docker_compose(fp, content))
            results.extend(self._analyze_ci_cd(fp, content))
            results.extend(self._analyze_terraform(fp, content))
            results.extend(self._analyze_helm(fp, content))
            results.extend(self._analyze_kubernetes(fp, content))
            results.extend(self._analyze_nginx(fp, content))
            results.extend(self._analyze_observability(fp, content))
            results.extend(self._analyze_health(fp, content))
            results.extend(self._analyze_env(fp, content))
            results.extend(self._analyze_operations(fp, content))
        # Project-level checks (emit at most 1 finding per check)
        if not self._project_has_health:
            results.append(DevOpsFinding(
                devops_type="missing_health_endpoint",
                severity="high",
                title="No health check endpoint found",
                description="No health endpoint, readiness probe, or liveness probe detected across the entire project.",
                file_path="",
                recommendation="Add a /health endpoint returning service status and dependency health",
                category="health_checks",
                confidence=0.8,
            ))
        if not self._project_has_observability:
            results.append(DevOpsFinding(
                devops_type="missing_observability",
                severity="medium",
                title="No observability configuration detected",
                description="No metrics, tracing, structured logging, or log aggregation configuration found across the project.",
                file_path="",
                recommendation="Set up Prometheus metrics, structured logging, and distributed tracing",
                category="observability",
                confidence=0.7,
            ))
        if not self._project_has_operations:
            results.append(DevOpsFinding(
                devops_type="missing_operations",
                severity="medium",
                title="No operations configuration detected",
                description="No backup, autoscaling, disaster recovery, or deployment strategy found across the project.",
                file_path="",
                recommendation="Set up backup strategy, autoscaling, and a deployment strategy (blue-green/canary)",
                category="operations",
                confidence=0.7,
            ))
        return results

    def _analyze_dockerfile(self, fp: str, content: str) -> list[DevOpsFinding]:
        findings: list[DevOpsFinding] = []
        is_dockerfile = (
            "dockerfile" in fp
            or fp.endswith(".dockerfile")
        )
        if not is_dockerfile:
            return findings
        lines = content.split("\n")
        has_healthcheck = bool(re.search(r'(?i)^\s*HEALTHCHECK\s', content, re.MULTILINE))
        if not has_healthcheck:
            findings.append(DevOpsFinding(
                devops_type="missing_healthcheck",
                severity="medium",
                title="Dockerfile missing HEALTHCHECK instruction",
                description="No HEALTHCHECK instruction found. Docker will not monitor container health.",
                file_path=fp,
                recommendation="Add HEALTHCHECK instruction to enable container health monitoring",
                category="containerization",
                confidence=0.9,
            ))
        has_user = bool(re.search(r'(?i)^\s*USER\s', content, re.MULTILINE))
        has_latest = bool(re.search(r'(?i)(?:FROM\s+\S+):latest\b', content))
        if has_latest:
            findings.append(DevOpsFinding(
                devops_type="using_latest_tag",
                severity="medium",
                title="Dockerfile uses 'latest' tag",
                description="Using 'latest' tag makes builds non-reproducible and can pull unexpected versions.",
                file_path=fp,
                recommendation="Pin base image to a specific version tag instead of 'latest'",
                category="containerization",
                confidence=0.9,
            ))
        if not has_user:
            findings.append(DevOpsFinding(
                devops_type="running_as_root",
                severity="high",
                title="Container runs as root",
                description="No USER instruction found. Containers running as root pose a security risk.",
                file_path=fp,
                recommendation="Add a USER instruction to run with non-root privileges",
                category="containerization",
                confidence=0.9,
            ))
        has_add = bool(re.search(r'(?i)^\s*ADD\s', content, re.MULTILINE))
        has_copy = bool(re.search(r'(?i)^\s*COPY\s', content, re.MULTILINE))
        if has_add and not has_copy:
            for line_num, line in enumerate(lines, 1):
                if re.search(r'(?i)^\s*ADD\s', line) and not re.search(r'(?i)\b(?:tar|gz|zip|url|https?://)\b', line):
                    findings.append(DevOpsFinding(
                        devops_type="using_add_instead_of_copy",
                        severity="low",
                        title="Using ADD instead of COPY for local files",
                        description="ADD has extra features like tar extraction and URL download. For local file copying, COPY is preferred.",
                        file_path=fp,
                        line_start=line_num,
                        code_snippet=line.strip(),
                        recommendation="Use COPY instead of ADD for copying local files into the image",
                        category="containerization",
                        confidence=0.8,
                    ))
                    break
        stages = [l for l in lines if re.search(r'(?i)^\s*FROM\s', l)]
        if len(stages) < 2:
            findings.append(DevOpsFinding(
                devops_type="no_multi_stage_build",
                severity="low",
                title="Multi-stage build not used",
                description="Single-stage build may result in larger image size including build tooling.",
                file_path=fp,
                recommendation="Use multi-stage builds to separate build and runtime dependencies",
                category="containerization",
                confidence=0.7,
            ))
        return findings

    def _analyze_docker_compose(self, fp: str, content: str) -> list[DevOpsFinding]:
        findings: list[DevOpsFinding] = []
        is_compose = bool(re.search(r'(?i)(?:docker-compose|compose)\.(?:yml|yaml)$', fp))
        if not is_compose:
            return findings
        lines = content.split("\n")
        full_lower = content.lower()
        services_section = False
        for line_num, line in enumerate(lines, 1):
            stripped = line.strip()
            if re.match(r'^services:', stripped):
                services_section = True
                continue
            if services_section:
                if re.match(r'^\w', stripped) and ":" in stripped and not stripped.startswith(" "):
                    services_section = False
        if not re.search(r'restart\s*:', full_lower):
            findings.append(DevOpsFinding(
                devops_type="no_restart_policy",
                severity="medium",
                title="Docker Compose service missing restart policy",
                description="No restart policy defined. Services won't auto-restart on failure.",
                file_path=fp,
                recommendation="Add restart: unless-stopped or restart: always to each service",
                category="containerization",
                confidence=0.85,
            ))
        has_resource_limits = bool(
            re.search(r'deploy\s*:\s*\n\s+resources\s*:', content, re.DOTALL)
            or re.search(r'(?i)mem_limit\s*:', content)
            or re.search(r'(?i)cpus\s*:', content)
        )
        if not has_resource_limits:
            findings.append(DevOpsFinding(
                devops_type="missing_resource_limits",
                severity="medium",
                title="Docker Compose service missing resource limits",
                description="No memory or CPU limits defined. Services can consume all host resources.",
                file_path=fp,
                recommendation="Add deploy.resources.limits (memory, cpus) to each service",
                category="containerization",
                confidence=0.85,
            ))
        has_healthcheck = bool(re.search(r'(?i)healthcheck\s*:', full_lower))
        if not has_healthcheck:
            findings.append(DevOpsFinding(
                devops_type="no_healthcheck",
                severity="medium",
                title="Docker Compose service missing healthcheck",
                description="No healthcheck defined. Docker won't monitor service health.",
                file_path=fp,
                recommendation="Add healthcheck configuration to each service",
                category="containerization",
                confidence=0.85,
            ))
        has_latest = bool(re.search(r'(?i)image\s*:\s*\S+:\s*latest\b', content))
        if has_latest:
            findings.append(DevOpsFinding(
                devops_type="using_latest_tag",
                severity="medium",
                title="Docker Compose uses 'latest' tag",
                description="Using 'latest' tag for images makes deployments non-reproducible.",
                file_path=fp,
                recommendation="Pin images to specific version tags instead of 'latest'",
                category="containerization",
                confidence=0.9,
            ))
        return findings

    def _analyze_ci_cd(self, fp: str, content: str) -> list[DevOpsFinding]:
        findings: list[DevOpsFinding] = []
        is_ci = any([
            ".github/workflows/" in fp,
            fp.endswith(".gitlab-ci.yml"),
            "jenkinsfile" in fp,
            ".circleci/" in fp,
            fp.endswith(".drone.yml"),
            fp.endswith(".woodpecker.yml"),
        ])
        if not is_ci:
            return findings
        full_lower = content.lower()
        if "cache" not in full_lower:
            findings.append(DevOpsFinding(
                devops_type="missing_cache_config",
                severity="low",
                title="CI/CD workflow missing cache configuration",
                description="No cache configuration found. Pipeline runs will be slower without dependency caching.",
                file_path=fp,
                recommendation="Add cache configuration for package managers (pip, npm, gradle, etc.)",
                category="ci_cd",
                confidence=0.8,
            ))
        has_test = bool(
            re.search(r'(?i)\btest\b', full_lower)
            and not re.search(r'(?i)#.*test', content)
        )
        if not has_test:
            findings.append(DevOpsFinding(
                devops_type="no_test_step",
                severity="high",
                title="CI/CD workflow missing test step",
                description="No test step found in CI/CD pipeline. Code changes may break without detection.",
                file_path=fp,
                recommendation="Add a test step running unit tests and integration tests",
                category="ci_cd",
                confidence=0.9,
            ))
        has_artifacts = bool(
            re.search(r'(?i)artifacts\s*:', content)
            or re.search(r'(?i)upload-artifact', content)
        )
        if not has_artifacts:
            findings.append(DevOpsFinding(
                devops_type="no_build_artifact",
                severity="medium",
                title="CI/CD workflow missing build artifact",
                description="No artifact upload step found. Build outputs are not preserved.",
                file_path=fp,
                recommendation="Add an artifacts step to upload build outputs for deployment",
                category="ci_cd",
                confidence=0.8,
            ))
        if "secrets:" in content and "${{ secrets." not in content:
            findings.append(DevOpsFinding(
                devops_type="hardcoded_secrets",
                severity="high",
                title="Hardcoded secrets detected in CI/CD workflow",
                description="Found secrets: declaration without GitHub's ${{ secrets.XXX }} pattern. Secrets may be exposed.",
                file_path=fp,
                recommendation="Use GitHub Secrets (${{ secrets.SECRET_NAME }}) or your CI/CD platform's secret management",
                category="ci_cd",
                confidence=0.75,
            ))
        return findings

    def _analyze_terraform(self, fp: str, content: str) -> list[DevOpsFinding]:
        findings: list[DevOpsFinding] = []
        is_tf = any([
            fp.endswith(".tf"),
            fp.endswith(".tfvars"),
            fp.endswith(".tfstate"),
        ])
        if not is_tf:
            return findings
        if "required_providers" not in content and "source  =" not in content and "version" not in content:
            findings.append(DevOpsFinding(
                devops_type="no_provider_version",
                severity="medium",
                title="Terraform provider missing version constraint",
                description="Provider without version constraint may introduce breaking changes on upgrade.",
                file_path=fp,
                recommendation="Add required_providers block with version constraints for each provider",
                category="infrastructure",
                confidence=0.8,
            ))
        secrets_patterns = [
            r'(?i)(?:password|secret|access_key|secret_key|api_key)\s*=\s*["\'][^"\']+["\']',
            r'(?i)aws_secret_key\s*=\s*["\'][^"\']+["\']',
        ]
        for line_num, line in enumerate(content.split("\n"), 1):
            for pat in secrets_patterns:
                if re.search(pat, line) and "var." not in line:
                    findings.append(DevOpsFinding(
                        devops_type="hardcoded_credentials",
                        severity="critical",
                        title="Hardcoded credentials in Terraform",
                        description="Sensitive credentials hardcoded in Terraform files. They will be stored in state.",
                        file_path=fp,
                        line_start=line_num,
                        code_snippet=line.strip(),
                        recommendation="Use variables with sensitive=true or a secrets backend (Vault, AWS Secrets Manager)",
                        category="infrastructure",
                        confidence=0.95,
                    ))
                    break
        has_backend = bool(re.search(r'(?i)backend\s+"', content))
        if not has_backend:
            findings.append(DevOpsFinding(
                devops_type="no_remote_backend",
                severity="medium",
                title="Terraform remote backend not configured",
                description="No remote backend configured. State is stored locally and not shared with the team.",
                file_path=fp,
                recommendation="Configure a remote backend (s3, gcs, azurerm, terraform cloud) for state management",
                category="infrastructure",
                confidence=0.85,
            ))
        if "aws_s3_bucket" in content:
            has_versioning = bool(
                re.search(r'(?i)versioning\s*\{[^}]*enabled\s*=\s*true', content, re.DOTALL)
            )
            if not has_versioning:
                findings.append(DevOpsFinding(
                    devops_type="s3_no_versioning",
                    severity="high",
                    title="S3 bucket without versioning enabled",
                    description="S3 bucket resource without versioning enabled. Data loss from accidental deletes cannot be recovered.",
                    file_path=fp,
                    recommendation="Enable versioning on S3 buckets to protect against accidental deletion",
                    category="infrastructure",
                    confidence=0.85,
                ))
        return findings

    def _analyze_helm(self, fp: str, content: str) -> list[DevOpsFinding]:
        findings: list[DevOpsFinding] = []
        is_helm = any([
            fp.endswith("chart.yaml"),
            fp.endswith("values.yaml"),
            ("/templates/" in fp or "templates/" in fp) and fp.endswith(".yaml"),
        ])
        if not is_helm:
            return findings
        if fp.endswith("values.yaml") or fp.endswith("templates/") or "/templates/" in fp:
            if not re.search(r'\{\{\s*\.Values\.', content):
                findings.append(DevOpsFinding(
                    devops_type="hardcoded_values",
                    severity="medium",
                    title="Hardcoded values instead of Helm Values",
                    description="Values directly hardcoded in templates instead of referencing .Values.",
                    file_path=fp,
                    recommendation="Use {{ .Values.<key> }} to make values configurable via values.yaml",
                    category="infrastructure",
                    confidence=0.8,
                ))
        has_liveness = bool(re.search(r'(?i)livenessProbe\s*:', content))
        has_readiness = bool(re.search(r'(?i)readinessProbe\s*:', content))
        if not has_liveness or not has_readiness:
            findings.append(DevOpsFinding(
                devops_type="missing_probes",
                severity="high",
                title="Helm chart missing liveness/readiness probes",
                description="Kubernetes probes not configured. Pod health won't be monitored.",
                file_path=fp,
                recommendation="Add livenessProbe and readinessProbe to container specifications",
                category="infrastructure",
                confidence=0.85,
            ))
        has_resources = bool(re.search(r'(?i)resources\s*:\s*\n\s+limits\s*:', content, re.DOTALL))
        if not has_resources:
            findings.append(DevOpsFinding(
                devops_type="missing_resource_limits",
                severity="medium",
                title="Helm chart missing resource limits",
                description="No resource limits defined in template. Containers can overcommit cluster resources.",
                file_path=fp,
                recommendation="Add resources.limits (cpu, memory) to container specifications",
                category="infrastructure",
                confidence=0.85,
            ))
        if "namespace:" in content and ("default" in content.split("namespace:")[1].split("\n")[0].strip().strip('"')):
            findings.append(DevOpsFinding(
                devops_type="using_default_namespace",
                severity="low",
                title="Helm chart uses default namespace",
                description="Deploying to default Kubernetes namespace can cause conflicts with other services.",
                file_path=fp,
                recommendation="Use a dedicated namespace for the application instead of 'default'",
                category="infrastructure",
                confidence=0.8,
            ))
        return findings

    def _analyze_kubernetes(self, fp: str, content: str) -> list[DevOpsFinding]:
        findings: list[DevOpsFinding] = []
        is_k8s = (
            (fp.endswith(".yaml") or fp.endswith(".yml"))
            and "apiVersion:" in content
            and "kind:" in content
        )
        if not is_k8s:
            return findings
        if "containers:" in content:
            has_resource_limits = bool(
                re.search(r'(?i)resources\s*:\s*\n\s+limits\s*:', content, re.DOTALL)
            )
            if not has_resource_limits:
                findings.append(DevOpsFinding(
                    devops_type="no_resource_limits",
                    severity="high",
                    title="Kubernetes container missing resource limits",
                    description="Container without resource limits can starve other pods on the node.",
                    file_path=fp,
                    recommendation="Add resources.limits (cpu and memory) to all containers",
                    category="cloud_readiness",
                    confidence=0.9,
                ))
            for line_num, line in enumerate(content.split("\n"), 1):
                if re.search(r'(?i)image\s*:\s*\S+:\s*latest\b', line):
                    findings.append(DevOpsFinding(
                        devops_type="using_latest_tag",
                        severity="medium",
                        title="Kubernetes manifest uses 'latest' image tag",
                        description="Using 'latest' tag makes deployments unpredictable and hard to rollback.",
                        file_path=fp,
                        line_start=line_num,
                        code_snippet=line.strip(),
                        recommendation="Pin container images to a specific version tag",
                        category="cloud_readiness",
                        confidence=0.9,
                    ))
                    break
            for line_num, line in enumerate(content.split("\n"), 1):
                if re.search(r'(?i)privileged\s*:\s*true', line):
                    findings.append(DevOpsFinding(
                        devops_type="privileged_container",
                        severity="critical",
                        title="Privileged container detected",
                        description="Privileged container has full host access and poses a major security risk.",
                        file_path=fp,
                        line_start=line_num,
                        code_snippet=line.strip(),
                        recommendation="Avoid privileged containers. Use specific securityContext capabilities instead.",
                        category="cloud_readiness",
                        confidence=0.95,
                    ))
                    break
        if "PodDisruptionBudget" not in content and "poddisruptionbudget" not in content.lower():
            has_deployment = bool(re.search(r'(?i)kind\s*:\s*Deployment', content))
            if has_deployment:
                findings.append(DevOpsFinding(
                    devops_type="no_pod_disruption_budget",
                    severity="medium",
                    title="No PodDisruptionBudget defined",
                    description="Without PodDisruptionBudget, voluntary disruptions can take down all replicas.",
                    file_path=fp,
                    recommendation="Create a PodDisruptionBudget to ensure minimum available replicas during disruptions",
                    category="cloud_readiness",
                    confidence=0.8,
                ))
        for line_num, line in enumerate(content.split("\n"), 1):
            if re.search(r'(?i)replicas\s*:\s*1\b', line):
                findings.append(DevOpsFinding(
                    devops_type="single_replica",
                    severity="medium",
                    title="Single replica without high availability",
                    description="Only one replica configured. The service will be unavailable during updates or node failures.",
                    file_path=fp,
                    line_start=line_num,
                    code_snippet=line.strip(),
                    recommendation="Set replicas to at least 2 for production workloads",
                    category="cloud_readiness",
                    confidence=0.85,
                ))
                break
        return findings

    def _analyze_nginx(self, fp: str, content: str) -> list[DevOpsFinding]:
        findings: list[DevOpsFinding] = []
        is_nginx = any([
            fp.endswith("nginx.conf"),
            fp.endswith(".nginx.conf"),
            "/sites-enabled/" in fp,
            "/conf.d/" in fp and fp.endswith(".conf"),
        ])
        if not is_nginx:
            return findings
        full_lower = content.lower()
        if "limit_req" not in full_lower and "limit_conn" not in full_lower:
            findings.append(DevOpsFinding(
                devops_type="no_rate_limiting",
                severity="medium",
                title="Nginx rate limiting not configured",
                description="No rate limiting rules found. Server is vulnerable to abuse and DDoS attacks.",
                file_path=fp,
                recommendation="Add limit_req and limit_conn directives to protect against abuse",
                category="infrastructure",
                confidence=0.85,
            ))
        if "ssl_certificate" not in full_lower and "ssl_certificate_key" not in full_lower:
            findings.append(DevOpsFinding(
                devops_type="no_ssl_tls",
                severity="high",
                title="Nginx SSL/TLS not configured",
                description="No SSL certificate configuration found. Traffic is transmitted in plaintext.",
                file_path=fp,
                recommendation="Configure SSL/TLS with ssl_certificate and ssl_certificate_key directives",
                category="infrastructure",
                confidence=0.9,
            ))
        if "gzip" not in full_lower:
            findings.append(DevOpsFinding(
                devops_type="no_gzip_compression",
                severity="low",
                title="Nginx gzip compression not enabled",
                description="No gzip compression configured. Responses are larger and slower to transmit.",
                file_path=fp,
                recommendation="Enable gzip compression to reduce response sizes",
                category="infrastructure",
                confidence=0.8,
            ))
        if "server_tokens" not in full_lower:
            findings.append(DevOpsFinding(
                devops_type="server_tokens_exposed",
                severity="low",
                title="Nginx server version exposed",
                description="Nginx server version is exposed in response headers, revealing version info to attackers.",
                file_path=fp,
                recommendation="Add 'server_tokens off;' to hide Nginx version from response headers",
                category="infrastructure",
                confidence=0.85,
            ))
        missing_headers = []
        if "X-Frame-Options" not in content and "X_FRAME_OPTIONS" not in content:
            missing_headers.append("X-Frame-Options")
        if "X-Content-Type-Options" not in content and "X_CONTENT_TYPE_OPTIONS" not in content:
            missing_headers.append("X-Content-Type-Options")
        if missing_headers:
            findings.append(DevOpsFinding(
                devops_type="missing_security_headers",
                severity="medium",
                title="Nginx missing security headers",
                description=f"Missing security headers: {', '.join(missing_headers)}.",
                file_path=fp,
                recommendation=f"Add: add_header {'; add_header '.join(missing_headers)} ...; in server/location block",
                category="infrastructure",
                confidence=0.85,
            ))
        return findings

    def _analyze_observability(self, fp: str, content: str) -> list[DevOpsFinding]:
        findings: list[DevOpsFinding] = []
        full_lower = content.lower()
        has_metrics = bool(re.search(r'(?i)(?:metrics|/metrics|prometheus)', full_lower))
        has_grafana = bool(re.search(r'(?i)(?:grafana|dashboard)', full_lower))
        has_tracing = bool(re.search(r'(?i)(?:opentelemetry|opentracing|otel|jaeger)', full_lower))
        has_structured_logging = bool(re.search(r'(?i)(?:json|structured|logstash)\s*(?:format|formatter)', full_lower))
        has_log_agg = bool(re.search(r'(?i)(?:filebeat|logstash|fluentd|fluent\s*bit|datadog)', full_lower))
        has_any = has_metrics or has_grafana or has_tracing or has_structured_logging or has_log_agg

        if has_any:
            self._project_has_observability = True
            if has_metrics:
                findings.append(DevOpsFinding(
                    devops_type="prometheus_metrics",
                    severity="info",
                    title="Prometheus metrics endpoint configured",
                    description="Metrics endpoint or Prometheus configuration detected - enables monitoring.",
                    file_path=fp,
                    recommendation="Ensure metrics are scraped by Prometheus and relevant dashboards exist",
                    category="observability",
                    confidence=0.9,
                ))
            if has_grafana:
                findings.append(DevOpsFinding(
                    devops_type="grafana_dashboard",
                    severity="info",
                    title="Grafana dashboard detected",
                    description="Grafana dashboard configuration found - enables visualization.",
                    file_path=fp,
                    recommendation="Verify dashboards cover key service metrics and SLOs",
                    category="observability",
                    confidence=0.9,
                ))
            if has_tracing:
                findings.append(DevOpsFinding(
                    devops_type="tracing_instrumentation",
                    severity="info",
                    title="Distributed tracing instrumentation detected",
                    description="OpenTelemetry/OpenTracing instrumentation found - enables request tracing.",
                    file_path=fp,
                    recommendation="Ensure traces are exported to a backend (Jaeger, Tempo, etc.)",
                    category="observability",
                    confidence=0.9,
                ))
            if has_structured_logging:
                findings.append(DevOpsFinding(
                    devops_type="structured_logging",
                    severity="info",
                    title="Structured logging configured",
                    description="JSON or structured log format detected - enables log analysis.",
                    file_path=fp,
                    recommendation="Ensure logs are collected by a centralized logging system",
                    category="observability",
                    confidence=0.9,
                ))
            if has_log_agg:
                findings.append(DevOpsFinding(
                    devops_type="log_aggregation",
                    severity="info",
                    title="Log aggregation configured",
                    description="Log shipping tool detected - enables centralized log management.",
                    file_path=fp,
                    recommendation="Verify logs are properly indexed and searchable in the aggregation system",
                    category="observability",
                    confidence=0.9,
                ))
        return findings

    def _analyze_health(self, fp: str, content: str) -> list[DevOpsFinding]:
        findings: list[DevOpsFinding] = []
        full_lower = content.lower()
        has_health_endpoint = bool(re.search(r'(?i)(?:["\']/health["\']|["\']/healthz["\']|["\']/ready["\']|["\']/live["\']|health_check|healthcheck)', content))
        has_readiness = bool(re.search(r'(?i)readinessProbe\s*:', content))
        has_liveness = bool(re.search(r'(?i)livenessProbe\s*:', content))
        has_any = has_health_endpoint or has_readiness or has_liveness

        if has_any:
            self._project_has_health = True
            if has_health_endpoint:
                findings.append(DevOpsFinding(
                    devops_type="health_endpoint",
                    severity="info",
                    title="Health check endpoint defined",
                    description="Health check endpoint detected - enables load balancer health monitoring.",
                    file_path=fp,
                    recommendation="Ensure health endpoint returns proper status codes and dependency checks",
                    category="health_checks",
                    confidence=0.9,
                ))
            if has_readiness:
                findings.append(DevOpsFinding(
                    devops_type="readiness_probe",
                    severity="info",
                    title="Readiness probe defined",
                    description="Readiness probe detected - ensures traffic only reaches ready pods.",
                    file_path=fp,
                    recommendation="Verify readiness probe correctly checks service dependencies",
                    category="health_checks",
                    confidence=0.9,
                ))
            if has_liveness:
                findings.append(DevOpsFinding(
                    devops_type="liveness_probe",
                    severity="info",
                    title="Liveness probe defined",
                    description="Liveness probe detected - enables automatic restart of unhealthy containers.",
                    file_path=fp,
                    recommendation="Verify liveness probe checks internal health without external dependencies",
                    category="health_checks",
                    confidence=0.9,
                ))
        return findings

    def _analyze_env(self, fp: str, content: str) -> list[DevOpsFinding]:
        findings: list[DevOpsFinding] = []
        is_env_file = any([
            ".env" in fp,
            fp.endswith(".env"),
        ])
        if not is_env_file:
            return findings
        if "example" in fp or "template" in fp or "dist" in fp or ".env.sample" in fp:
            findings.append(DevOpsFinding(
                devops_type="env_example_exists",
                severity="info",
                title="Environment template found",
                description="Environment example or template file detected - helps onboarding.",
                file_path=fp,
                recommendation="Keep template up to date with all required environment variables",
                category="environment",
                confidence=0.9,
            ))
        secrets_pattern = re.compile(r'(?im)^\s*(?:SECRET|SECRET_KEY|API_KEY|PASSWORD|TOKEN|PRIVATE_KEY|ACCESS_KEY)\s*[=:]\s*["\']?[^"\'${\s]+["\']?\s*$')
        has_secrets = False
        if ".gitignore" in fp:
            if ".env" not in content and ".env" not in content:
                findings.append(DevOpsFinding(
                    devops_type="env_not_in_gitignore",
                    severity="high",
                    title="Environment files not in .gitignore",
                    description=".env files not excluded via .gitignore - secrets could be committed to the repository.",
                    file_path=fp,
                    recommendation="Add .env and *.env to .gitignore to prevent accidental secret exposure",
                    category="environment",
                    confidence=0.9,
                ))
        else:
            for line_num, line in enumerate(content.split("\n"), 1):
                if secrets_pattern.search(line):
                    has_secrets = True
                    findings.append(DevOpsFinding(
                        devops_type="hardcoded_secret_in_env",
                        severity="critical",
                        title="Hardcoded secret in environment file",
                        description="Sensitive value detected in environment file. This could expose credentials.",
                        file_path=fp,
                        line_start=line_num,
                        code_snippet=line.strip(),
                        recommendation="Remove secrets from env files. Use secret management (Vault, Kubernetes Secrets, etc.)",
                        category="environment",
                        confidence=0.95,
                    ))
                    break
            if not has_secrets and "example" not in fp and "template" not in fp:
                has_docs = bool(re.search(r'(?i)#\s*(?:required|needed|mandatory|document)', content))
                if not has_docs:
                    findings.append(DevOpsFinding(
                        devops_type="missing_env_docs",
                        severity="medium",
                        title="Missing environment variable documentation",
                        description="Environment file lacks comments documenting required variables.",
                        file_path=fp,
                        recommendation="Add comments documenting each environment variable's purpose and format",
                        category="environment",
                        confidence=0.8,
                    ))
        return findings

    def _analyze_operations(self, fp: str, content: str) -> list[DevOpsFinding]:
        findings: list[DevOpsFinding] = []
        full_lower = content.lower()
        has_backup = bool(re.search(r'(?i)(?:backup|snapshot|restore)', full_lower))
        has_autoscaling = bool(re.search(r'(?i)(?:autoscal|hpa\b|horizontalpodautoscal|horizontal.*autoscale|auto.scale)', full_lower))
        has_dr = bool(re.search(r'(?i)(?:disaster.recovery|dr\s*plan|failover|multi.region|region.replication)', full_lower))
        has_rollback = bool(re.search(r'(?i)(?:rollback|blue.green|canary|gradual.rollout|deployment.strategy)', full_lower))
        has_iac_quality = bool(re.search(r'(?i)(?:terraform.fmt|tfsec|checkov|terragrunt|terrascan)', full_lower))
        has_any = has_backup or has_autoscaling or has_dr or has_rollback or has_iac_quality

        if has_any:
            self._project_has_operations = True
            if has_backup:
                findings.append(DevOpsFinding(
                    devops_type="backup_config",
                    severity="info",
                    title="Backup configuration detected",
                    description="Backup or snapshot mechanism detected - enables data recovery.",
                    file_path=fp,
                    recommendation="Verify backups are tested regularly and meet RPO/RTO requirements",
                    category="operations",
                    confidence=0.9,
                ))
            if has_autoscaling:
                findings.append(DevOpsFinding(
                    devops_type="autoscaling_config",
                    severity="info",
                    title="Autoscaling configuration detected",
                    description="Horizontal pod autoscaler or auto-scaling config found - enables dynamic scaling.",
                    file_path=fp,
                    recommendation="Verify autoscaling thresholds and min/max replica counts are appropriate",
                    category="operations",
                    confidence=0.9,
                ))
            if has_dr:
                findings.append(DevOpsFinding(
                    devops_type="disaster_recovery",
                    severity="info",
                    title="Disaster recovery plan detected",
                    description="Disaster recovery or failover configuration found - enables business continuity.",
                    file_path=fp,
                    recommendation="Regularly test DR plan and verify RTO/RPO targets are met",
                    category="operations",
                    confidence=0.9,
                ))
            if has_rollback:
                findings.append(DevOpsFinding(
                    devops_type="rollback_strategy",
                    severity="info",
                    title="Rollback strategy detected",
                    description="Blue-green or canary deployment strategy found - enables safe rollbacks.",
                    file_path=fp,
                    recommendation="Document rollback procedure and test it regularly",
                    category="operations",
                    confidence=0.9,
                ))
            if has_iac_quality:
                findings.append(DevOpsFinding(
                    devops_type="iac_quality",
                    severity="info",
                    title="IaC quality checks configured",
                    description="Terraform fmt, linting, or security scanning detected - ensures IaC best practices.",
                    file_path=fp,
                    recommendation="Integrate IaC quality checks into CI/CD pipeline",
                    category="operations",
                    confidence=0.9,
                ))
        return findings
