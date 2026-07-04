# Security Policy

## Threat Model

Kraivor is a multi-service code analysis platform consisting of:

- **AI service** — LLM-powered chat, retrieval-augmented generation (RAG), and code enrichment
- **Core service** — GitHub integration, webhook processing, and task orchestration
- **Auth service** — Django-based authentication, OAuth (GitHub), JWT, and API key management
- **Analysis service** — Static analysis, dependency scanning, and detection pipelines

Data flows between services via Kafka and a shared database. All external access enters through authenticated API endpoints.

**Trust boundary:** The API gateway and auth service. All other services are internal and should not be directly reachable from the internet. Reporters should assume an attacker who can send arbitrary HTTP requests to any public endpoint.

## Supported Versions

| Version | Supported |
|---------|-----------|
| `dev` | ✅ Active development — security fixes land here |
| tagged releases | ✅ Stable — patch the latest tag |
| `main` | ❌ Integration branch — not deployed |

We do not maintain long-term release branches. Pin to a specific tag or commit SHA for stability.

## Scope

### In scope

- Authentication bypass or privilege escalation
- SQL injection, NoSQL injection, or ORM parameter tampering
- Path traversal or local/remote file inclusion
- Server-side request forgery (SSRF)
- Remote code execution (RCE)
- Cross-site scripting (XSS) in any rendered output
- Insecure direct object references (IDOR)
- Sensitive data exposure (secrets, PII, tokens) in logs, responses, or errors
- Denial of service via resource exhaustion
- Memory safety bugs in native dependencies

### Out of scope

- Social engineering, phishing, or physical attacks
- Self-XSS or attacks requiring attacker-in-the-middle on a local network
- Rate limiting bypass on non-authentication endpoints
- Missing HTTP security headers (HSTS, CSP, etc.) — our deployment proxy handles these
- Vulnerabilities in unmodified third-party dependencies (report upstream)
- Configuration weaknesses that require attacker-in-the-middle or local access
- Theoretical attacks without a practical exploit path

## Reporting a Vulnerability

**Do not open a public GitHub issue.** Use one of the following channels:

### Preferred: GitHub Private Security Advisory

1. Go to [github.com/anomalyco/kraivor/security/advisories](https://github.com/anomalyco/kraivor/security/advisories)
2. Click **New draft security advisory**
3. Fill in the details — you can submit anonymously

### Email

Send details to **security@kraivor.dev** (GPG key below).

**Encrypt sensitive reports** with our GPG key:

```
-----BEGIN PGP PUBLIC KEY BLOCK-----

FIXME: Insert your team's GPG public key here
-----END PGP PUBLIC KEY BLOCK-----
```

### What to include

- Service / endpoint affected
- Steps to reproduce (concise proof of concept preferred)
- Impact assessment
- Suggested fix (optional)

## Disclosure Timeline

| Severity | Initial Response | Status Update Cadence | Target Fix Time |
|----------|-----------------|----------------------|-----------------|
| Critical | ≤ 24 hours | Daily | ≤ 7 days |
| High | ≤ 48 hours | Every 2 days | ≤ 14 days |
| Medium | ≤ 72 hours | Weekly | ≤ 30 days |
| Low | ≤ 7 days | Monthly | ≤ 90 days |

- **Triage:** You will receive acknowledgment within the Initial Response window above.
- **Fix:** Once a fix is ready, we will coordinate a release date with you.
- **Disclosure:** We follow a **90-day disclosure deadline**. You may publish your write-up 90 days after the fix is released, or earlier by mutual agreement.

## Recognition

We maintain a **Hall of Fame** in [`HALL_OF_FAME.md`](HALL_OF_FAME.md) (or `SECURITY_HALL_OF_FAME.md`). With your permission, we will add your name/alias and a link (Twitter, GitHub, blog) when the advisory is published.

## Security Measures (Implemented)

- **Authentication:** JWT (RS256) with refresh token rotation; API key hashing via PBKDF2; GitHub OAuth
- **Authorization:** Scope-based permissions on API keys; user-level role checks
- **Secrets management:** All secrets injected via environment variables — never committed
- **Dependency scanning:** Dependabot configured for automated CVE alerts
- **SAST:** Ruff (lint), Bandit (security), MyPy (type safety) run in CI — **zero warnings policy**
- **Container:** Non-root user in all Docker images; read-only root filesystem where possible
- **Database:** Parameterized queries (SQLAlchemy / Django ORM); connection encryption in transit

## Infrastructure Security

This project is developed and tested against ephemeral environments. If you self-host:

- Place all services behind a TLS-terminating reverse proxy
- Restrict direct network access to the auth service and API gateway only
- Use a dedicated secrets vault (e.g., HashiCorp Vault, AWS Secrets Manager) in production
- Enable audit logging on the database and Kafka cluster

## Third-Party Dependencies

We track known vulnerabilities via Dependabot. If you discover a vulnerability in a dependency used by Kraivor, please report it to the upstream project first. If the vulnerability has a CVE and our usage is affected, you may report it to us as a secondary advisory.

## Policy Updates

This policy may be updated without prior notice. Material changes (scope, timeline, contact) will be documented in the commit history of this file.

---

*Last updated: July 2026*
