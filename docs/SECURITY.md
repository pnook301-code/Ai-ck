# CK-NEXUS AIOS — Security

## Security Features

### Authentication
- bcrypt password hashing (with legacy SHA256 backward compatibility)
- JWT token authentication with automatic expiry
- API key authentication for service-to-service

### Authorization
- Role-Based Access Control (RBAC) — Phase 9
- Function-level approval for Shadow Bridge operations
- API key scoping

### Data Protection
- All secrets auto-generated (never hardcoded)
- Environment variable-based configuration
- Encrypted at rest (PostgreSQL, Qdrant)

### Network Security
- UFW firewall configured
- Internal services bound to 127.0.0.1
- Only public ports: 22, 3000, 4000, 5678, 6333

### Code Security
- Ruff linting (0 errors)
- No hardcoded secrets
- Input validation on all functions
- Path traversal protection
- URL validation before external requests

## Security Audit Results

| Check | Status | Notes |
|-------|--------|-------|
| No hardcoded secrets | ✅ | Verified via grep |
| bcrypt hashing | ✅ | All passwords hashed |
| JWT expiry enforced | ✅ | Tokens expire automatically |
| Input validation | ✅ | All function inputs validated |
| Path traversal protection | ✅ | Canonical path checks |
| URL validation | ✅ | Schema whitelist |
| Ruff clean | ✅ | 0 lint errors |

## Pending Security Checks

- [ ] Semgrep SAST scan
- [ ] Gitleaks secret scan
- [ ] Dependency vulnerability audit
- [ ] Penetration testing

## Reporting Security Issues

Report security vulnerabilities to: security@ck-nexus.ai
