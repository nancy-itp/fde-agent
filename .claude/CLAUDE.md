2. Coding Standards
• Type safety: type hints on all public functions/methods; mypy run in strict mode (disallow_untyped_defs, disallow_any_generics, warn_return_any) as a CI gate. No bare Any in application code (Protocol/TypeVar + narrowing instead); # type: ignore requires a comment justifying it and a linked ticket.
• Style & linting: Ruff (lint) + Black (format) enforced via pre-commit hook and CI gate; a build with lint or type errors cannot merge.
• Project structure: one module per Core Application Service (Scheduler, Prio Integration, Review Workflow, Notification Service, Employee/Profile Management), each with its own router / service / repository layers so business logic never talks to SQLAlchemy sessions or HTTP clients directly — this keeps the Score Store and external adapters swappable and testable.
• Naming: snake_case for variables/functions/modules, PascalCase for classes, UPPER_SNAKE_CASE for constants and environment variable keys; file names mirror the primary export.
• Error handling: never swallow errors silently; use typed exception classes (ValidationError, UpstreamIntegrationError, AuthorizationError) caught once at the API boundary (FastAPI exception handlers) and mapped to safe, generic client-facing messages — raw stack traces or upstream error bodies (Prio, Microsoft Graph, LLM engine) must never reach the client.
• SQLAlchemy/DB access: no raw string-built SQL; use SQLAlchemy's parameterized query construction (select(), mapped_column-based models) for anything not expressible via the ORM. All schema changes go through versioned Alembic migrations, reviewed like code (see backend/alembic/versions/).
• Documentation: exported functions and all API route handlers carry docstrings; every Core Application Service maintains a short README.md describing its inputs, outputs and the events it emits/consumes (e.g. "Triggers Biweekly Scoring Pipeline").
• Dependency hygiene: no new dependency added without checking weekly download count, last publish date and open CVEs; prefer the standard library or an existing dependency over a new one for trivial needs.
3. Development Workflow Standards
• Branching: trunk-based with short-lived feature branches (feat/, fix/, chore/), squash-merged into main behind a required PR; main is always deployable.
• Code review: minimum one approving reviewer, two for changes touching auth, scoring logic, or an external integration adapter; reviewers explicitly check for the security items in Sections 4–6, not just correctness.
• CI/CD gates: every PR runs lint (Ruff), type-check (mypy), unit tests (pytest), dependency vulnerability scan (e.g. pip-audit / Safety / Dependabot), and a container image scan before merge; deploys to staging are automatic on merge to main, production deploys are manual/approved and tagged releases only.
• Environment parity: staging mirrors production topology (same Prio/M365/IdP integration pattern, pointed at sandbox/test tenants) so integration bugs surface before release, never against production tenants.
• Secrets & config: no secrets in source control, .env files, or CI logs; managed through a secrets manager (Vault, AWS Secrets Manager, or equivalent) and injected at runtime; .env.example documents required keys with placeholder values only.
• Dependency management: pinned, hash-locked requirements (requirements.txt generated via pip-compile --generate-hashes, or a uv/poetry lockfile) committed and CI-enforced (pip install --require-hashes, never an unpinned install); scheduled (weekly) automated dependency update PRs, reviewed rather than auto-merged for anything touching auth, crypto, or the SQLAlchemy/Alembic layer.
• Infrastructure as code: environment and network configuration (see Section 5) defined in version-controlled IaC (Terraform/Pulumi), reviewed with the same rigor as application code — no manual console changes to production infrastructure.
4. Application Security Guidelines
Mapped to OWASP Top 10 as it applies to this architecture:
Risk
How it applies here
Required control
Broken access control
Manager vs Employee dashboard scope, cross-tenant/cross-employee data leakage
Enforce authorization server-side on every route (never trust client-sent role); row-level checks so an employee can only fetch their own scores and a manager only their own team's
Cryptographic failures
Score data, resumes, PII in transit/at rest
TLS 1.2+ everywhere; AES-256 at rest for the Score Store and any file storage; no custom crypto — use vetted libraries
Injection
Prio/Graph API payloads, self-report free text feeding scoring prompts
Parameterized SQLAlchemy queries only; validate/sanitize all inbound payloads with Pydantic models at every FastAPI service boundary, including data pulled from Prio and Microsoft 365
Insecure design
Auto-accept vs manager-review branch in the scoring pipeline
Threat-model each pipeline branch; default-deny (route to manager review) on any confidence/mismatch ambiguity rather than defaulting to auto-accept
Security misconfiguration
Multiple services, multiple external API keys
Hardened, minimal-privilege default configs per service; no debug endpoints or verbose error output in production; automated config drift detection
Vulnerable & outdated components
Python/SQLAlchemy/pip dependency tree
Automated SCA scanning in CI (Section 3); patch critical CVEs within 72 hours
Identification & auth failures
Manager/Employee login via Enterprise Auth/IdP
Delegate authentication entirely to the IdP (OIDC/SAML); enforce MFA for manager and admin roles; short-lived access tokens with refresh rotation; no locally stored passwords
Software & data integrity failures
AI Scoring/LLM Engine outputs feeding audit history
Verify integrity of packages via lockfile hashes and signed container images; treat LLM engine output as untrusted input requiring validation before it is persisted as a score
Security logging & monitoring failures
Score approvals, overrides, exception routing
Structured audit logging (Section 7) for every score change, approval, and manager override, shipped to a monitored, tamper-evident log store
Server-side request forgery
Notification Service and Prio Integration making outbound calls based on stored config
Allow-list outbound destinations (Prio API, Graph API, LLM engine endpoints only); never build outbound URLs from user-controlled input
Additional controls specific to this app: rate limiting and account lockout on the Employee/Manager login paths; strict Content Security Policy and output encoding on both dashboards to prevent stored/reflected XSS from self-report free-text fields; CSRF tokens on all state-changing dashboard requests.
5. Network & Infrastructure Security
• Transport security: TLS 1.2+ (prefer 1.3) on every hop — dashboard-to-service, service-to-service, and service-to-external-API; HSTS enabled on both dashboards; internal traffic between Core Application Services (Scheduler, Prio Integration, Review Workflow, Notification Service, Employee/Profile Management) encrypted even inside the VPC.
• Network segmentation: separate subnets/security groups for the Presentation Layer, Core Application Services, and the Persistence Layer (Score Store); the Score Store accepts connections only from the Employee/Profile Management and Review Workflow services, never directly from the Presentation Layer or the public internet.
• Least-privilege firewall rules: default-deny inbound; explicit allow rules per service pair matching the documented data flows (e.g. Scheduler → Prio Integration, Review Workflow → Notification Service); outbound rules allow-list only the four named external endpoints (Prio API, Graph API, AI Scoring/LLM Engine, Enterprise IdP) plus package registries needed at build time.
• API gateway / edge: a single ingress point in front of the Manager and Employee Dashboards enforcing TLS termination, WAF rules (SQLi/XSS signature blocking), and rate limiting per authenticated user and per IP.
• Rate limiting & abuse protection: throttle login attempts, dashboard API calls, and the Scheduler's biweekly trigger endpoints; back off and alert on repeated 401/403 responses from any single source.
• Secrets in transit: API keys/tokens for Prio, Microsoft Graph, and the LLM engine are never placed in query strings or logs; sent only in headers over TLS, rotated on a fixed schedule (e.g. every 90 days) and immediately on suspected compromise.
• Bastion/VPN access: production database and internal service access restricted to a bastion host or VPN with MFA; no direct public IP exposure on the Score Store or internal services.
• DDoS & availability: front the Presentation Layer with a CDN/DDoS-protection layer; define autoscaling limits so the Weekly Monday Staffing Workflow and biweekly scoring runs can't be used to exhaust compute via a flood of triggered jobs.
6. Third-Party Integration Security
Integration
Attack surface
Required hardening
Prio Task Tracker API
Pulls task/ticket data feeding scoring; a compromised or malicious ticket payload could inject content
Dedicated scoped API credential (read-only where possible); validate/sanitize every field before it reaches the scoring pipeline; retry with backoff and circuit-break on repeated failures rather than retry-storming Prio
Microsoft 365 / Outlook API
Sends staffing/notification emails on the user's behalf; OAuth token compromise = mail-send abuse
Use OAuth 2.0 with least-privilege Graph API scopes (Mail.Send only, not full mailbox access); store refresh tokens encrypted; short-lived access tokens; monitor for anomalous send volume
AI Scoring / LLM Engine
Self-report free text and Prio data are passed into prompts; a crafted self-report could attempt prompt injection to manipulate the score
Treat all user-supplied text as untrusted input to the prompt; strip/escape instructions-like content before inclusion; validate the engine's structured output against an expected schema before persisting; never let the engine's output alone auto-approve a score without the existing mismatch/confidence check
Enterprise Auth / IdP
Single point of authentication for managers and employees
OIDC/SAML only, no local password fallback; validate token signature, issuer and audience on every request; short token lifetimes with refresh rotation; immediately revoke sessions on role change or offboarding
General integration rules: every external call has a timeout and a circuit breaker; secrets for each integration are scoped separately (a Prio credential compromise should not expose Graph or IdP credentials); all external API responses are schema-validated before being written to the Score Store; integration failures fail closed (route to manager review / block the action) rather than fail open.
7. Data Protection, Logging & Compliance
• Data classification: resumes, self-reports, skill matrices and performance scores are classified as sensitive employee data; access is need-to-know (an employee sees only their own record, a manager only their own team).
• Encryption: AES-256 at rest for the Score Store and any file/resume storage; TLS in transit (Section 5); encryption keys managed via a KMS, not embedded in application config.
• Retention & deletion: define a retention period for cycle records and audit history aligned with HR policy; support deletion/anonymization of a departed employee's personal data on request, while preserving anonymized audit history where legally required.
• Audit logging: every score approval, manager override, and mismatch resolution (per the Review Workflow) is written to an append-only audit log with actor, timestamp, before/after values — this is the system of record the "Persist Cycle Record & Audit History" step depends on.
• Application logging: structured (JSON) logs with correlation/request IDs across service boundaries; never log secrets, tokens, full resumes, or raw self-report text — log references/IDs instead; logs shipped to a centralized, access-controlled log store with alerting on authorization failures and integration errors.
• PII minimization: pass only the fields each downstream step needs (e.g. the AI Scoring Engine receives task/profile evidence, not unrelated PII); redact or tokenize identifiers where the scoring logic doesn't need the real value.
• Compliance alignment: handle employee data consistent with applicable data protection law (e.g. GDPR/local labor data regulations) — lawful basis for processing, data subject access support, and breach notification procedures should be defined with Legal/HR before go-live.
8. Testing, Monitoring & Incident Response
• Testing pyramid: unit tests for scoring logic and validation rules; integration tests against sandboxed Prio/Graph/IdP tenants; contract tests for each external API adapter so upstream schema changes are caught before production; end-to-end tests covering the full biweekly scoring pipeline and weekly staffing workflow.
• Security testing: SAST (Bandit / Semgrep) in CI on every PR; DAST and dependency/container scanning on a schedule; an annual (minimum) third-party penetration test covering the dashboards, API gateway and integration adapters; authenticated and unauthenticated access-control test cases specifically for cross-employee and cross-manager data access.
• Monitoring & alerting: uptime/health checks per Core Application Service; alert on authentication failure spikes, unusual score-override rates, integration timeout/error rate increases, and anomalous outbound traffic to non-allow-listed destinations.
• Incident response: a documented runbook covering credential compromise (Prio/Graph/LLM/IdP), data breach, and scoring-integrity incidents; defined severity levels, on-call escalation, and communication plan; post-incident review feeding back into this standards document.
• Backup & recovery: encrypted, regularly tested backups of the Score Store; documented RTO/RPO; restoration drills at least twice a year.
9. Pre-Deployment Security Checklist
[ ] All secrets sourced from the secrets manager; none in source control, CI logs, or .env committed files
[ ] TLS 1.2+ enforced on every service-to-service and external hop; HSTS on both dashboards
[ ] Server-side authorization checks in place for every Manager/Employee data access path
[ ] IdP-based auth (OIDC/SAML) with MFA for manager/admin roles; no local password store
[ ] Input validation (schema-based) on every route and every external API response before persistence
[ ] Rate limiting and account lockout active on login and dashboard API endpoints
[ ] Outbound network allow-list restricted to Prio API, Graph API, LLM engine, and IdP endpoints
[ ] Audit logging live for score approvals, overrides, and mismatch resolutions
[ ] Dependency/container vulnerability scan clean of critical/high findings
[ ] Backup and restore drill completed within the last 6 months
[ ] Incident response runbook reviewed and on-call rotation confirmed