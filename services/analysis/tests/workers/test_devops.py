"""Tests for the DevopsAnalyzer."""

import pytest

from app.domain.contracts.parser import ParsedFile
from app.workers.devops.analyzer import DevopsAnalyzer


def _make_pf(path: str, content: str) -> ParsedFile:
    return ParsedFile(
        path=path,
        content=content,
        language="yaml",
        ast_data={},
        functions=[],
        classes=[],
        imports=[],
        exports=[],
        routes=[],
        lines_count=len(content.split("\n")),
        errors=[],
        size_bytes=len(content.encode("utf-8")),
    )


@pytest.mark.asyncio
class TestAnalyzeDockerfile:
    async def test_detects_missing_healthcheck(self) -> None:
        content = "FROM python:3.11-slim\nWORKDIR /app\nCMD ['python', 'app.py']\n"
        pfs = [_make_pf("Dockerfile", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "missing_healthcheck" in types

    async def test_detects_running_as_root(self) -> None:
        content = "FROM python:3.11-slim\nRUN apt-get update\nCMD ['python', 'app.py']\n"
        pfs = [_make_pf("Dockerfile", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "running_as_root" in types

    async def test_skips_non_dockerfile(self) -> None:
        pfs = [_make_pf("app.py", "print('hello')")]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        dockerfile_types = [r.devops_type for r in results if r.category == "containerization"]
        assert len(dockerfile_types) == 0


@pytest.mark.asyncio
class TestAnalyzeDockerCompose:
    async def test_detects_no_healthcheck(self) -> None:
        content = "version: '3'\nservices:\n  web:\n    image: nginx:1.25\n"
        pfs = [_make_pf("docker-compose.yml", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "no_healthcheck" in types

    async def test_skips_non_compose_file(self) -> None:
        pfs = [_make_pf("requirements.txt", "flask==2.0")]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "no_restart_policy" not in types


@pytest.mark.asyncio
class TestAnalyzeCICD:
    async def test_detects_no_test_step(self) -> None:
        content = "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - run: echo building\n"
        pfs = [_make_pf(".github/workflows/ci.yml", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "no_test_step" in types

    async def test_skips_non_ci_file(self) -> None:
        pfs = [_make_pf("random.yml", "key: value")]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "no_test_step" not in types


@pytest.mark.asyncio
class TestAnalyzeTerraform:
    async def test_detects_hardcoded_credentials(self) -> None:
        content = 'provider "aws" {\n  access_key = "AKIAIOSFODNN7EXAMPLE"\n  secret_key = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"\n}\n'
        pfs = [_make_pf("main.tf", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "hardcoded_credentials" in types

    async def test_skips_non_tf_file(self) -> None:
        pfs = [_make_pf("notes.txt", "some content")]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "no_provider_version" not in types


@pytest.mark.asyncio
class TestAnalyzeHelm:
    async def test_detects_missing_probes(self) -> None:
        content = "apiVersion: apps/v1\nkind: Deployment\nspec:\n  template:\n    spec:\n      containers:\n        - name: app\n          image: myapp:1.0\n"
        pfs = [_make_pf("templates/deployment.yaml", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "missing_probes" in types

    async def test_skips_non_helm_file(self) -> None:
        pfs = [_make_pf("deploy.py", "def deploy(): pass")]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "missing_probes" not in types


@pytest.mark.asyncio
class TestAnalyzeKubernetes:
    async def test_detects_no_resource_limits(self) -> None:
        content = "apiVersion: apps/v1\nkind: Deployment\nspec:\n  template:\n    spec:\n      containers:\n        - name: app\n          image: myapp:1.0\n"
        pfs = [_make_pf("deployment.yaml", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "no_resource_limits" in types

    async def test_skips_non_k8s_yaml(self) -> None:
        pfs = [_make_pf("config.yaml", "key: value")]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "no_resource_limits" not in types


@pytest.mark.asyncio
class TestAnalyzeNginx:
    async def test_detects_no_rate_limiting(self) -> None:
        content = "server {\n  listen 80;\n  location / {\n    proxy_pass http://backend;\n  }\n}\n"
        pfs = [_make_pf("nginx.conf", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "no_rate_limiting" in types

    async def test_skips_non_nginx_file(self) -> None:
        pfs = [_make_pf("server.py", "print('ok')")]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "no_rate_limiting" not in types


@pytest.mark.asyncio
class TestAnalyzeObservability:
    async def test_detects_metrics_endpoint(self) -> None:
        content = "scrape_configs:\n  - job_name: 'app'\n    metrics_path: '/metrics'\n"
        pfs = [_make_pf("prometheus.yml", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "prometheus_metrics" in types

    async def test_returns_missing_when_no_observability(self) -> None:
        pfs = [_make_pf("app.py", "def hello(): return 'world'")]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "missing_observability" in types


@pytest.mark.asyncio
class TestAnalyzeHealth:
    async def test_detects_health_endpoint(self) -> None:
        content = '@app.route("/health")\ndef health():\n    return {"status": "ok"}\n'
        pfs = [_make_pf("app.py", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "health_endpoint" in types

    async def test_returns_missing_when_no_health(self) -> None:
        pfs = [_make_pf("app.py", "def index(): return 'hello'")]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "missing_health_endpoint" in types


@pytest.mark.asyncio
class TestAnalyzeEnv:
    async def test_detects_hardcoded_secret(self) -> None:
        content = "SECRET_KEY=super-secret-value-12345\n"
        pfs = [_make_pf(".env", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "hardcoded_secret_in_env" in types

    async def test_skips_non_env_file(self) -> None:
        pfs = [_make_pf("main.py", "x = 1")]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "env_example_exists" not in types


@pytest.mark.asyncio
class TestAnalyzeOperations:
    async def test_detects_backup_config(self) -> None:
        content = "backup:\n  schedule: '0 2 * * *'\n  retention: 30\n"
        pfs = [_make_pf("backup.yml", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "backup_config" in types

    async def test_returns_missing_when_no_operations(self) -> None:
        pfs = [_make_pf("simple.py", "x = 1")]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "missing_operations" in types


@pytest.mark.asyncio
class TestEdgeCases:
    async def test_empty_content_no_findings(self) -> None:
        pfs = [_make_pf("Dockerfile", "")]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        assert isinstance(results, list)

    async def test_binary_content_no_crash(self) -> None:
        pfs = [_make_pf("binary.bin", "\x00\x01\x02\x03\xff\xfe\xfd\xfc")]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        assert isinstance(results, list)

    async def test_mixed_content_all_modules_run(self) -> None:
        pfs = [
            _make_pf("Dockerfile", "FROM python:3.11-slim\nCMD python app.py\n"),
            _make_pf("docker-compose.yml", "version: '3'\nservices:\n  web:\n    image: nginx\n"),
            _make_pf(".github/workflows/ci.yml", "name: CI\non: [push]\njobs:\n  build:\n    steps:\n      - run: build\n"),
        ]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        assert len(results) >= 3
        types = [r.devops_type for r in results]
        assert "missing_healthcheck" in types
        assert "no_healthcheck" in types
        assert "no_test_step" in types

    async def test_no_false_positives_for_unrelated_files(self) -> None:
        pfs = [
            _make_pf("main.py", "import flask\napp = flask.Flask(__name__)\n"),
            _make_pf("index.html", "<html><body>Hello</body></html>"),
            _make_pf("styles.css", "body { color: red; }"),
        ]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        devops_types = [r.devops_type for r in results]
        assert "no_resource_limits" not in devops_types

    async def test_very_large_content_no_crash(self) -> None:
        content = "# comment\n" * 10000
        pfs = [_make_pf("large.txt", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        assert isinstance(results, list)


@pytest.mark.asyncio
class TestDockerfileAdvanced:
    async def test_detects_using_latest_tag(self) -> None:
        content = "FROM python:latest\nWORKDIR /app\nCMD python app.py\n"
        pfs = [_make_pf("Dockerfile", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "using_latest_tag" in types

    async def test_detects_using_add_instead_of_copy(self) -> None:
        content = "FROM python:3.11\nADD . /app\nCMD python app.py\n"
        pfs = [_make_pf("Dockerfile", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "using_add_instead_of_copy" in types

    async def test_detects_no_multi_stage_build(self) -> None:
        content = "FROM python:3.11-slim\nCOPY . /app\nRUN pip install -r requirements.txt\nCMD python app.py\n"
        pfs = [_make_pf("Dockerfile", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "no_multi_stage_build" in types

    async def test_optimal_dockerfile_has_minimal_findings(self) -> None:
        content = "FROM python:3.11-slim AS builder\nWORKDIR /app\nCOPY requirements.txt .\nRUN pip install -r requirements.txt\nFROM python:3.11-slim\nCOPY --from=builder /app /app\nUSER appuser\nHEALTHCHECK --interval=30s CMD curl -f http://localhost:8080/health || exit 1\nCMD python app.py\n"
        pfs = [_make_pf("Dockerfile", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "missing_healthcheck" not in types
        assert "running_as_root" not in types
        assert "using_latest_tag" not in types
        assert "using_add_instead_of_copy" not in types


@pytest.mark.asyncio
class TestDockerComposeAdvanced:
    async def test_detects_no_restart_policy(self) -> None:
        content = "version: '3'\nservices:\n  web:\n    image: nginx:1.25\n"
        pfs = [_make_pf("docker-compose.yml", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "no_restart_policy" in types

    async def test_detects_missing_resource_limits(self) -> None:
        content = "version: '3'\nservices:\n  web:\n    image: nginx:1.25\n    restart: always\n"
        pfs = [_make_pf("docker-compose.yml", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "missing_resource_limits" in types

    async def test_optimal_compose_has_minimal_findings(self) -> None:
        content = "version: '3'\nservices:\n  web:\n    image: nginx:1.25\n    restart: always\n    healthcheck:\n      test: curl -f http://localhost || exit 1\n    deploy:\n      resources:\n        limits:\n          memory: 512M\n"
        pfs = [_make_pf("docker-compose.yml", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "no_healthcheck" not in types
        assert "no_restart_policy" not in types
        assert "missing_resource_limits" not in types


@pytest.mark.asyncio
class TestCICDAdvanced:
    async def test_detects_missing_cache_config(self) -> None:
        content = "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - run: npm install\n      - run: npm test\n"
        pfs = [_make_pf(".github/workflows/ci.yml", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "missing_cache_config" in types

    async def test_detects_no_build_artifact(self) -> None:
        content = "name: CI\non: [push]\njobs:\n  build:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v2\n      - run: npm install\n      - run: npm test\n"
        pfs = [_make_pf(".github/workflows/ci.yml", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "no_build_artifact" in types


@pytest.mark.asyncio
class TestTerraformAdvanced:
    async def test_detects_no_provider_version(self) -> None:
        content = 'provider "aws" {\n  region = "us-east-1"\n}\n'
        pfs = [_make_pf("main.tf", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "no_provider_version" in types

    async def test_detects_no_remote_backend(self) -> None:
        content = 'provider "aws" {\n  version = "~> 4.0"\n  region  = "us-east-1"\n}\n'
        pfs = [_make_pf("main.tf", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "no_remote_backend" in types

    async def test_detects_s3_no_versioning(self) -> None:
        content = 'provider "aws" {\n  version = "~> 4.0"\n}\nresource "aws_s3_bucket" "data" {\n  bucket = "my-data"\n}\n'
        pfs = [_make_pf("s3.tf", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "s3_no_versioning" in types


@pytest.mark.asyncio
class TestKubernetesAdvanced:
    async def test_detects_using_latest_tag(self) -> None:
        content = "apiVersion: apps/v1\nkind: Deployment\nspec:\n  template:\n    spec:\n      containers:\n        - name: app\n          image: myapp:latest\n"
        pfs = [_make_pf("deployment.yaml", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "using_latest_tag" in types

    async def test_detects_privileged_container(self) -> None:
        content = "apiVersion: apps/v1\nkind: Deployment\nspec:\n  template:\n    spec:\n      containers:\n        - name: app\n          image: myapp:1.0\n          securityContext:\n            privileged: true\n"
        pfs = [_make_pf("deployment.yaml", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "privileged_container" in types

    async def test_detects_no_pod_disruption_budget(self) -> None:
        content = "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: app\n"
        pfs = [_make_pf("deployment.yaml", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "no_pod_disruption_budget" in types

    async def test_detects_single_replica(self) -> None:
        content = "apiVersion: apps/v1\nkind: Deployment\nspec:\n  replicas: 1\n  template:\n    spec:\n      containers:\n        - name: app\n          image: myapp:1.0\n"
        pfs = [_make_pf("deployment.yaml", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "single_replica" in types

    async def test_ha_deployment_no_single_replica_warning(self) -> None:
        content = "apiVersion: apps/v1\nkind: Deployment\nspec:\n  replicas: 3\n  template:\n    spec:\n      containers:\n        - name: app\n          image: myapp:1.0\n          resources:\n            limits:\n              memory: 512Mi\n"
        pfs = [_make_pf("deployment.yaml", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "single_replica" not in types


@pytest.mark.asyncio
class TestNginxAdvanced:
    async def test_detects_no_ssl_tls(self) -> None:
        content = "server {\n  listen 80;\n  location / {\n    proxy_pass http://backend;\n  }\n}\n"
        pfs = [_make_pf("nginx.conf", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "no_ssl_tls" in types

    async def test_detects_no_gzip_compression(self) -> None:
        content = "server {\n  listen 443 ssl;\n  location / {\n    proxy_pass http://backend;\n  }\n}\n"
        pfs = [_make_pf("nginx.conf", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "no_gzip_compression" in types

    async def test_detects_server_tokens_exposed(self) -> None:
        content = "server {\n  listen 80;\n  location / {\n    proxy_pass http://backend;\n  }\n}\n"
        pfs = [_make_pf("nginx.conf", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "server_tokens_exposed" in types

    async def test_detects_missing_security_headers(self) -> None:
        content = "server {\n  listen 443 ssl;\n  gzip on;\n  server_tokens off;\n  location / {\n    proxy_pass http://backend;\n  }\n}\n"
        pfs = [_make_pf("nginx.conf", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "missing_security_headers" in types

    async def test_optimal_nginx_has_minimal_findings(self) -> None:
        content = "server {\n  listen 443 ssl;\n  ssl_certificate /etc/ssl/certs/server.crt;\n  ssl_certificate_key /etc/ssl/private/server.key;\n  gzip on;\n  server_tokens off;\n  add_header X-Frame-Options SAMEORIGIN;\n  add_header X-Content-Type-Options nosniff;\n  limit_req zone=mylimit burst=20;\n  location / {\n    proxy_pass http://backend;\n  }\n}\n"
        pfs = [_make_pf("nginx.conf", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "no_rate_limiting" not in types
        assert "no_ssl_tls" not in types
        assert "no_gzip_compression" not in types
        assert "server_tokens_exposed" not in types
        assert "missing_security_headers" not in types


@pytest.mark.asyncio
class TestEnvAdvanced:
    async def test_detects_env_example_exists(self) -> None:
        content = "# Environment variables\nDATABASE_URL=postgres://localhost:5432/db\n"
        pfs = [_make_pf(".env.example", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "env_example_exists" in types

    async def test_detects_missing_env_documentation(self) -> None:
        content = "DATABASE_URL=postgres://localhost:5432/db\n"
        pfs = [_make_pf(".env", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "missing_env_docs" in types


@pytest.mark.asyncio
class TestOperationsAdvanced:
    async def test_detects_autoscaling_config(self) -> None:
        content = "apiVersion: autoscaling/v2\nkind: HorizontalPodAutoscaler\nmetadata:\n  name: app-hpa\n"
        pfs = [_make_pf("hpa.yaml", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "autoscaling_config" in types

    async def test_detects_rollback_strategy(self) -> None:
        content = "deployment:\n  strategy:\n    type: blue-green\n    canary:\n      enabled: true\n"
        pfs = [_make_pf("deploy-strategy.yaml", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "rollback_strategy" in types

    async def test_detects_iac_quality(self) -> None:
        content = "run: terraform fmt -check\n"
        pfs = [_make_pf("Makefile", content)]
        analyzer = DevopsAnalyzer(pfs)
        results = await analyzer.scan_all()
        types = [r.devops_type for r in results]
        assert "iac_quality" in types
