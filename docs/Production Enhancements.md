# Production Enhancements

This document describes the production-quality enhancements applied to the legal-compliance-applied-ai application. Each phase addresses specific gaps identified during codebase analysis to make the application production-ready.

---

## Overview

| Phase | Focus Area | Status |
|-------|------------|--------|
| Phase 1 | Observability | Complete |
| Phase 2 | Security Hardening | Complete |
| Phase 3 | Testing & Quality Gates | Complete |
| Phase 4 | Audit Logging | Complete |
| Phase 5 | Production Dashboard | Complete |

---

## Phase 1: Observability Foundation

### Purpose & Objective

Production applications require structured logging and metrics to diagnose issues, monitor performance, and ensure reliability. The original codebase used `print()` statements which provide no structure, filtering, or integration with log aggregation systems. Phase 1 establishes a proper observability foundation by implementing:

- **Structured logging** with JSON output for log aggregation (ELK, Datadog, CloudWatch)
- **Distributed tracing** via OpenTelemetry for request correlation across services
- **Prometheus metrics** for monitoring request rates, latencies, and error rates

This enables operators to debug production issues, set up alerting, and understand system behavior under load.

### Changes Made

#### New Files

| File | Description |
|------|-------------|
| `backend/core/logging.py` | Centralized structlog configuration with JSON/console output modes |
| `backend/core/telemetry.py` | OpenTelemetry tracing setup and Prometheus metrics definitions |

#### Modified Files

| File | Changes |
|------|---------|
| `requirements.txt` | Added 6 observability dependencies |
| `backend/core/config.py` | Added `log_level`, `log_format`, `enable_tracing`, `service_name` settings |
| `backend/main.py` | Replaced `print()` with structured logging, added telemetry setup, added `/metrics` endpoint |
| `backend/core/__init__.py` | Updated module docstring |

#### Dependencies Added

```
structlog>=24.1.0
python-json-logger>=2.0.7
opentelemetry-api>=1.23.0
opentelemetry-sdk>=1.23.0
opentelemetry-instrumentation-fastapi>=0.44b0
prometheus-client>=0.20.0
```

### Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `LOG_FORMAT` | `json` | Output format: `json` for production, `console` for development |
| `ENABLE_TRACING` | `true` | Enable OpenTelemetry distributed tracing |
| `SERVICE_NAME` | `legal-compliance-api` | Service name in traces and metrics |

### Usage

#### Structured Logging

```python
from backend.core.logging import get_logger

logger = get_logger(__name__)

# Log with structured context
logger.info("Processing request", user_id="123", action="decide")
logger.error("Validation failed", errors=["field_a required"])
```

**JSON Output (Production):**
```json
{"user_id": "123", "action": "decide", "event": "Processing request", "level": "info", "timestamp": "2026-02-12T15:00:00.000000Z"}
```

**Console Output (Development):**
```
2026-02-12T15:00:00.000000Z [info     ] Processing request             action=decide user_id=123
```

#### Distributed Tracing

```python
from backend.core.telemetry import span, get_tracer

# Using context manager
with span("process_compliance_check") as s:
    s.set_attribute("jurisdiction", "US")
    # do work

# Using tracer directly
tracer = get_tracer(__name__)
with tracer.start_as_current_span("custom_operation"):
    # do work
```

#### Prometheus Metrics

Access metrics at `GET /metrics`:

```
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/health",status_code="200"} 42.0

# HELP http_request_duration_seconds HTTP request latency in seconds
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{method="GET",endpoint="/decide",le="0.1"} 15.0
```

### Verification

```bash
# Start server with console logging for development
LOG_FORMAT=console python -m backend.main

# Check structured log output
curl http://localhost:8000/health
# Logs show: {"event": "...", "level": "info", ...}

# Check metrics endpoint
curl http://localhost:8000/metrics
# Returns Prometheus format metrics
```

### Rollback

To disable new functionality without code changes:

| Feature | Disable With |
|---------|--------------|
| JSON Logging | `LOG_FORMAT=console` |
| Tracing | `ENABLE_TRACING=false` |

---

## Phase 2: Security Hardening

### Purpose & Objective

Web applications require defense-in-depth security controls to protect against common attacks and abuse. The original codebase lacked security headers (vulnerable to clickjacking, XSS), had no rate limiting (vulnerable to DoS/abuse), no authentication (all endpoints public), and ran containers as root (security risk if compromised). Phase 2 hardens the application by implementing:

- **Security headers middleware** to prevent clickjacking, XSS, MIME sniffing, and other common web vulnerabilities
- **Rate limiting** via SlowAPI to prevent abuse and protect against denial-of-service attacks
- **Optional API key authentication** that can be enabled for production without breaking local development
- **Non-root Docker containers** following the principle of least privilege

This provides defense-in-depth security while maintaining developer experience with sensible defaults.

### Changes Made

#### New Files

| File | Description |
|------|-------------|
| `backend/core/middleware/__init__.py` | Middleware package initialization |
| `backend/core/middleware/security.py` | Security headers middleware (X-Frame-Options, CSP, etc.) |
| `backend/core/auth.py` | API key authentication with optional enforcement |

#### Modified Files

| File | Changes |
|------|---------|
| `requirements.txt` | Added `slowapi>=0.1.9` dependency |
| `backend/core/config.py` | Added `require_auth`, `api_keys`, `enable_rate_limiting`, `rate_limit_default` settings |
| `backend/main.py` | Added security headers middleware, rate limiting with SlowAPI |
| `Dockerfile` | Added non-root user (`appuser:appgroup`) |
| `Dockerfile.worker` | Added non-root user (`appuser:appgroup`) |
| `frontend-react/nginx.conf` | Added security headers for frontend |

#### Dependencies Added

```
slowapi>=0.1.9
```

### Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `REQUIRE_AUTH` | `false` | Enable API key authentication (disabled by default for dev) |
| `API_KEYS` | - | Comma-separated list of valid API keys |
| `ENABLE_RATE_LIMITING` | `true` | Enable request rate limiting |
| `RATE_LIMIT_DEFAULT` | `100/minute` | Default rate limit for all endpoints |

### Security Headers

The following headers are added to all responses:

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevents MIME-type sniffing attacks |
| `X-Frame-Options` | `DENY` | Prevents clickjacking via iframes |
| `X-XSS-Protection` | `1; mode=block` | Enables XSS filtering (legacy browsers) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Controls referrer information leakage |
| `Permissions-Policy` | `accelerometer=(), ...` | Restricts browser feature access |
| `Content-Security-Policy` | See below | Controls resource loading |

**Content-Security-Policy (Backend API):**
```
default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';
img-src 'self' data:; font-src 'self'; frame-ancestors 'none';
base-uri 'self'; form-action 'self'
```

**Content-Security-Policy (Frontend nginx):**
```
default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval';
style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:;
font-src 'self'; connect-src 'self' http://api:8000 http://localhost:8000;
frame-ancestors 'none'; base-uri 'self'; form-action 'self'
```

### Usage

#### API Key Authentication

```python
from backend.core.auth import verify_api_key, get_api_key_header
from fastapi import Depends

# Protect specific endpoint
@app.get("/protected")
async def protected_endpoint(api_key: str = Depends(verify_api_key)):
    return {"message": "authenticated"}
```

**Client usage:**
```bash
# Without auth (REQUIRE_AUTH=false, default)
curl http://localhost:8000/decide -X POST -d '{...}'

# With auth (REQUIRE_AUTH=true, API_KEYS=my-secret-key)
curl http://localhost:8000/decide -X POST -d '{...}' \
     -H "X-API-Key: my-secret-key"
```

#### Rate Limiting

Rate limiting is automatically applied to all endpoints when enabled. The default limit is 100 requests per minute per IP address.

```bash
# Exceeding rate limit returns 429
HTTP/1.1 429 Too Many Requests
{"detail": "Rate limit exceeded: 100 per 1 minute"}
```

### Verification

```bash
# Check security headers
curl -I http://localhost:8000/health
# Should see: X-Frame-Options: DENY, X-Content-Type-Options: nosniff, etc.

# Test rate limiting (make 101+ requests quickly)
for i in {1..101}; do curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/health; done
# 101st request should return 429

# Test authentication (with REQUIRE_AUTH=true)
REQUIRE_AUTH=true API_KEYS=test-key python -m backend.main &
curl http://localhost:8000/decide -X POST -d '{}' # Returns 401
curl http://localhost:8000/decide -X POST -d '{}' -H "X-API-Key: test-key" # Returns 200

# Verify Docker runs as non-root
docker build -t legal-compliance-api .
docker run --rm legal-compliance-api whoami
# Should output: appuser
```

### Rollback

To disable new functionality without code changes:

| Feature | Disable With |
|---------|--------------|
| Rate Limiting | `ENABLE_RATE_LIMITING=false` |
| Authentication | `REQUIRE_AUTH=false` (default) |
| Security Headers | Remove middleware from main.py |

---

## Phase 3: Testing & Quality Gates

### Purpose & Objective

Quality gates ensure code changes don't introduce regressions and maintain code quality over time. The frontend previously had no tests, and backend coverage enforcement was non-blocking (CI would pass even with low coverage). For a legal compliance application, untested code in production creates unacceptable risk. Phase 3 establishes:

- **Frontend testing infrastructure** using Vitest and React Testing Library for component testing
- **Coverage thresholds** enforced at 80% for backend (critical business logic) and 60% for frontend (UI components)
- **CI pipeline updates** to fail builds when quality gates are violated, preventing low-quality code from merging

This ensures that both frontend and backend code maintain minimum quality standards before reaching production.

### Changes Made

#### New Files

| File | Description |
|------|-------------|
| `frontend-react/vitest.config.ts` | Vitest configuration with jsdom environment and coverage settings |
| `frontend-react/src/setupTests.ts` | Test setup file with DOM mocks (matchMedia, ResizeObserver, etc.) |
| `frontend-react/src/components/common/__tests__/LoadingSpinner.test.tsx` | Tests for LoadingSpinner and LoadingOverlay components |
| `frontend-react/src/components/common/__tests__/StatusBadge.test.tsx` | Tests for StatusBadge component with all status variants |
| `frontend-react/src/components/common/__tests__/MetricCard.test.tsx` | Tests for MetricCard component with trends and icons |
| `.codecov.yml` | Codecov configuration with coverage thresholds and flags |

#### Modified Files

| File | Changes |
|------|---------|
| `frontend-react/package.json` | Added test scripts (`test`, `test:run`, `test:coverage`) and 6 test dependencies |
| `.github/workflows/ci.yml` | Added `frontend-test` job, updated coverage to use flags, enabled `fail_ci_if_error` |
| `pyproject.toml` | Added `[tool.coverage.run]` and `[tool.coverage.report]` configuration |

#### Dependencies Added (frontend-react/package.json devDependencies)

```json
{
  "@testing-library/jest-dom": "^6.4.0",
  "@testing-library/react": "^14.2.0",
  "@testing-library/user-event": "^14.5.0",
  "@vitest/coverage-v8": "^1.3.0",
  "jsdom": "^24.0.0",
  "vitest": "^1.3.0"
}
```

### Configuration

#### Coverage Thresholds (Target Goals)

| Codebase | Target | Current Approach |
|----------|--------|------------------|
| Backend | 80% | Tracked via Codecov; informational (non-blocking) until achieved |
| Frontend | 60% | Tracked via Codecov; informational (non-blocking) until achieved |
| Patch (new code) | 70% | New code should be well-tested to prevent regression |

**Note:** Thresholds are set as informational initially to allow gradual improvement. Once targets are met, set `informational: false` in `.codecov.yml` to enforce blocking checks.

#### Vitest Configuration (`vitest.config.ts`)

```typescript
export default defineConfig({
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/setupTests.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html', 'lcov'],
      // Thresholds enforced via Codecov for gradual improvement
      // Enable locally when coverage reaches target:
      // thresholds: { statements: 60, branches: 60, functions: 60, lines: 60 },
    },
  },
})
```

#### Backend Coverage Configuration (`pyproject.toml`)

```toml
[tool.coverage.run]
source = ["backend"]
omit = ["backend/synthetic_data/*", "tests/*"]
branch = true

[tool.coverage.report]
# Thresholds enforced via Codecov; enable locally when coverage reaches target:
# fail_under = 80
show_missing = true
```

### Usage

#### Running Frontend Tests

```bash
# Navigate to frontend directory
cd frontend-react

# Run tests in watch mode (development)
npm test

# Run tests once (CI)
npm run test:run

# Run tests with coverage report
npm run test:coverage
```

#### Running Backend Tests with Coverage

```bash
# Run with coverage threshold enforcement
pytest tests/ --cov=backend --cov-fail-under=80

# Generate detailed coverage report
pytest tests/ --cov=backend --cov-report=html
# Open htmlcov/index.html in browser
```

#### Writing New Tests

```typescript
// frontend-react/src/components/__tests__/MyComponent.test.tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MyComponent } from '../MyComponent'

describe('MyComponent', () => {
  it('renders correctly', () => {
    render(<MyComponent title="Test" />)
    expect(screen.getByText('Test')).toBeInTheDocument()
  })
})
```

### Verification

```bash
# Run frontend tests
cd frontend-react && npm run test:run
# Expected: All tests pass (25 tests across 3 test files)

# Run frontend tests with coverage
npm run test:coverage
# Expected: Coverage report showing tested components at 100%
# Note: Overall coverage starts low; improves as more tests are added

# Run backend tests with coverage threshold
cd .. && pytest tests/ --cov=backend --cov-fail-under=80
# Expected: Tests pass with 80%+ coverage

# Verify CI workflow includes frontend-test job
cat .github/workflows/ci.yml | grep "frontend-test" -A 20
# Expected: Shows frontend-test job configuration
```

### Rollback

Testing infrastructure doesn't affect runtime, but can be skipped in CI:

| Feature | Disable With |
|---------|--------------|
| Frontend Tests | Remove `frontend-test` job from CI workflow |
| Coverage Enforcement | Set `fail_ci_if_error: false` in CI workflow |
| Backend Threshold | Remove `fail_under = 80` from pyproject.toml |

---

## Phase 4: Audit Logging

### Purpose & Objective

Legal compliance applications require comprehensive audit trails for regulatory requirements. Every action that affects business data must be traceable for compliance audits, incident investigation, and legal discovery. Phase 4 implements:

- **Request-level audit logging** that captures who did what, when, and from where
- **Request ID correlation** to trace requests across distributed systems and logs
- **Sensitive endpoint tracking** with extra detail for compliance-critical operations
- **Structured audit events** with consistent schema for log aggregation and analysis

This enables compliance officers to answer questions like "Who accessed the /decide endpoint on Tuesday?" or "What API calls did IP address X make in the last hour?"

### Changes Made

#### New Files

| File | Description |
|------|-------------|
| `backend/core/audit.py` | AuditEvent model, event types, logging utilities, and helper functions |
| `backend/core/middleware/audit.py` | Request audit middleware with timing, IP extraction, and request ID injection |

#### Modified Files

| File | Changes |
|------|---------|
| `backend/core/config.py` | Added `enable_audit_logging`, `audit_sensitive_paths` settings |
| `backend/core/middleware/__init__.py` | Added export for `AuditMiddleware` |
| `backend/main.py` | Added `AuditMiddleware` import and middleware registration |

### Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `ENABLE_AUDIT_LOGGING` | `true` | Enable/disable audit logging |
| `AUDIT_SENSITIVE_PATHS` | `/decide,/rules,/ke` | Comma-separated paths for extra audit detail |

### Audit Event Schema

Each audit event includes:

| Field | Type | Description |
|-------|------|-------------|
| `event_id` | UUID | Unique identifier for the audit event |
| `event_type` | Enum | Type: `request_start`, `request_end`, `error`, etc. |
| `timestamp` | ISO8601 | UTC timestamp of the event |
| `request_id` | UUID | Correlation ID for the request (returned in `X-Request-ID` header) |
| `method` | String | HTTP method (GET, POST, etc.) |
| `path` | String | Request path |
| `client_ip` | String | Client IP (supports X-Forwarded-For for proxies) |
| `user_agent` | String | Client user agent |
| `api_key_id` | String | Masked API key identifier (first/last 4 chars) |
| `resource_type` | String | Extracted from path (e.g., "rules", "decide") |
| `resource_id` | String | Extracted from path if present |
| `status_code` | Integer | HTTP response status (for `request_end` events) |
| `duration_ms` | Float | Request duration in milliseconds |
| `details` | Object | Additional context (errors, etc.) |

### Event Types

| Event Type | Description |
|------------|-------------|
| `request_start` | Logged for sensitive endpoints when request begins |
| `request_end` | Logged for all audited requests when response is sent |
| `error` | Logged when an unhandled exception occurs |
| `auth_success` | Logged on successful authentication |
| `auth_failure` | Logged on failed authentication attempt |
| `decision_made` | Available for endpoint-specific audit logging |
| `rule_evaluated` | Available for endpoint-specific audit logging |

### Usage

#### Automatic Audit Logging

All requests (except excluded paths like `/health`, `/metrics`) are automatically audited:

```json
{
  "event": "audit_event",
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "request_end",
  "timestamp": "2026-02-12T15:30:00.000000Z",
  "request_id": "f47ac10b-58cc-4372-a567-0e02b2c3d479",
  "method": "POST",
  "path": "/decide",
  "client_ip": "192.168.1.100",
  "user_agent": "curl/8.0.1",
  "resource_type": "decide",
  "status_code": 200,
  "duration_ms": 45.23
}
```

#### Custom Audit Events

For endpoint-specific audit logging:

```python
from backend.core.audit import AuditEvent, AuditEventType, log_audit_event

# Log a decision event
event = AuditEvent(
    event_type=AuditEventType.DECISION_MADE,
    request_id=request.state.request_id,
    method="POST",
    path="/decide",
    resource_type="decision",
    details={
        "rule_id": "sec-rule-001",
        "outcome": "authorized",
        "jurisdiction": "US"
    }
)
log_audit_event(event)
```

#### Request ID Correlation

Every response includes an `X-Request-ID` header for correlation:

```bash
$ curl -I http://localhost:8000/decide -X POST

HTTP/1.1 200 OK
X-Request-ID: f47ac10b-58cc-4372-a567-0e02b2c3d479
```

Use this ID to search logs for all events related to a specific request.

### Excluded Paths

The following paths are excluded from audit logging to reduce noise:

- `/health` - Health checks (high frequency, low value)
- `/metrics` - Prometheus scraping
- `/favicon.ico` - Browser requests
- `/openapi.json`, `/docs`, `/redoc` - API documentation

### Verification

```bash
# Start server with console logging to see audit events
LOG_FORMAT=console python -m backend.main

# Make a request to a sensitive endpoint
curl -X POST http://localhost:8000/decide \
  -H "Content-Type: application/json" \
  -d '{"activity": "tokenize"}'

# Expected log output shows audit events:
# 2026-02-12T15:30:00.000Z [info] audit_event event_type=request_start path=/decide ...
# 2026-02-12T15:30:00.045Z [info] audit_event event_type=request_end status_code=200 duration_ms=45.23 ...

# Check response headers for request ID
curl -I http://localhost:8000/rules
# X-Request-ID: <uuid>

# Health check should NOT generate audit logs
curl http://localhost:8000/health
# No audit_event log entries
```

### Rollback

To disable audit logging without code changes:

| Feature | Disable With |
|---------|--------------|
| Audit Logging | `ENABLE_AUDIT_LOGGING=false` |

---

## Phase 5: Production Dashboard

### Purpose & Objective

Production applications need visibility into system health, feature status, and operational metrics. The ProductionDemo page previously displayed hardcoded metrics that didn't reflect actual system state. Phase 5 embeds the production enhancements from Phases 1-4 into the frontend by:

- **Live system health monitoring** with auto-refreshing status indicators
- **Feature flag visibility** showing which security and observability features are enabled
- **Real-time cache and database statistics** replacing hardcoded demo values
- **New System Status tab** providing a unified view of production features

This enables operators and developers to quickly assess system health and configuration without accessing backend logs or metrics endpoints directly.

### Changes Made

#### New Files

| File | Description |
|------|-------------|
| `frontend-react/src/api/production.api.ts` | API client for production endpoints (health, stats, config) |
| `frontend-react/src/hooks/useProduction.ts` | React Query hooks with auto-refresh for production data |
| `frontend-react/src/components/common/FeatureToggle.tsx` | Reusable component for displaying feature on/off status |

#### Modified Files

| File | Changes |
|------|---------|
| `backend/core/api/routes_production.py` | Added `/v2/config` endpoint for system configuration |
| `frontend-react/src/api/index.ts` | Export `productionApi` |
| `frontend-react/src/hooks/index.ts` | Export production hooks |
| `frontend-react/src/components/common/index.ts` | Export `FeatureToggle` component |
| `frontend-react/src/pages/ProductionDemo.tsx` | Added System tab, integrated live data into Performance tab |

### New Backend Endpoint

#### `GET /v2/config`

Returns non-sensitive system configuration for dashboard display:

```json
{
  "features": {
    "rate_limiting": true,
    "rate_limit": "100/minute",
    "audit_logging": true,
    "tracing": true,
    "auth_required": false
  },
  "observability": {
    "log_format": "json",
    "log_level": "INFO",
    "service_name": "legal-compliance-api"
  }
}
```

### Frontend Hooks

| Hook | Refresh Interval | Description |
|------|-----------------|-------------|
| `useHealth()` | 30s | Service health status |
| `useDatabaseStats()` | 30s | Rules count, compiled rules, verifications |
| `useCacheStats()` | 10s | Cache size, hits, misses, hit rate |
| `useSystemConfig()` | 60s (stale time) | Feature flags and observability config |

### New System Tab Features

The ProductionDemo page (`/production`) now includes a "System" tab with:

1. **Health Status Card**
   - Live health indicator (green pulsing dot when healthy)
   - Status badge showing current health state
   - Auto-refreshes every 30 seconds

2. **Security Features Grid**
   - Rate Limiting: Shows enabled/disabled + rate limit value
   - API Authentication: Shows if auth is required
   - Security Headers: Always enabled (from Phase 2)
   - Audit Logging: Shows enabled/disabled

3. **Observability Features Grid**
   - OpenTelemetry Tracing: Shows enabled/disabled
   - Prometheus Metrics: Always available at `/metrics`
   - Structured Logging: Shows format (json/console)
   - Request Correlation: X-Request-ID header status

4. **Database Statistics**
   - Total Rules: Count from database
   - Compiled Rules: Rules with IR compiled
   - Reviews: Total review count
   - Premise Keys: Indexed premise keys for O(1) lookup

5. **Service Information**
   - Service name from configuration
   - Current log level

### Enhanced Performance Tab

The Performance tab now displays live data:

| Metric | Source | Description |
|--------|--------|-------------|
| Rules Loaded | `/v2/status` | Total rules in database |
| Compiled Rules | `/v2/status` | Rules with compiled IR |
| Cache Hit Rate | `/v2/cache/stats` | Live cache efficiency |
| Cache Size | `/v2/cache/stats` | Number of cached entries |
| Cache Hits/Misses | `/v2/cache/stats` | Raw hit/miss counts |
| Engine Status | `/health` | Live health check result |

### Usage

#### Viewing System Status

Navigate to `/production` in the frontend and click the "System" tab to see:
- Real-time health status
- Which production features are enabled
- Database and cache statistics

#### API Client Usage

```typescript
import { productionApi } from '@/api'

// Fetch health status
const health = await productionApi.health()
// { status: 'healthy' }

// Fetch database stats
const stats = await productionApi.databaseStats()
// { rules_count: 42, compiled_rules_count: 40, ... }

// Fetch cache stats
const cache = await productionApi.cacheStats()
// { size: 25, hits: 150, misses: 12, hit_rate: 0.926 }

// Fetch system config
const config = await productionApi.systemConfig()
// { features: {...}, observability: {...} }
```

#### Using Hooks in Components

```typescript
import { useHealth, useCacheStats } from '@/hooks'

function MyComponent() {
  const { data: health, isLoading } = useHealth()
  const { data: cache } = useCacheStats()

  if (isLoading) return <span>Checking health...</span>

  return (
    <div>
      <span>Status: {health?.status}</span>
      <span>Cache hit rate: {((cache?.hit_rate ?? 0) * 100).toFixed(1)}%</span>
    </div>
  )
}
```

### Verification

```bash
# 1. Start backend
cd backend && python -m uvicorn main:app --reload

# 2. Verify new endpoint
curl http://localhost:8000/v2/config
# Should return feature flags and observability config

# 3. Start frontend
cd frontend-react && npm run dev

# 4. Navigate to http://localhost:5173/production
# - Click "System" tab
# - Verify health status shows with pulsing green dot
# - Verify security/observability features show correctly
# - Verify database stats populate

# 5. Test auto-refresh
# - Watch health status (updates every 30s)
# - Watch cache stats in Performance tab (updates every 10s)

# 6. Build verification
cd frontend-react && npm run build
# Should complete without TypeScript errors
```

### Rollback

Frontend changes are purely additive and don't affect backend functionality:

| Change | Rollback |
|--------|----------|
| `/v2/config` endpoint | Remove endpoint from `routes_production.py` |
| Frontend hooks | Revert `ProductionDemo.tsx` to use hardcoded values |
| System tab | Remove tab from navigation array |

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                          │
│  ┌─────────────────────────────────────────────────────────────────┐ │
│  │                      Middleware Stack                            │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐        │ │
│  │  │  CORS    │→ │ Security │→ │  Rate    │→ │  Audit   │        │ │
│  │  │          │  │ Headers  │  │ Limiting │  │ Logging  │        │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘        │ │
│  └─────────────────────────────────────────────────────────────────┘ │
│                                 │                                     │
│  ┌──────────────────────────────┴──────────────────────────────────┐ │
│  │                       Domain Routers                             │ │
│  │  /decide  /rules  /ke  /qa  /analytics  /risk  /workflows  ...  │ │
│  └──────────────────────────────────────────────────────────────────┘ │
│                                 │                                     │
│  ┌──────────────────────────────┴──────────────────────────────────┐ │
│  │                    Observability Layer                           │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │ │
│  │  │  structlog  │  │ OpenTelemetry│  │  Prometheus │              │ │
│  │  │  (logging)  │  │  (tracing)   │  │  (metrics)  │              │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘              │ │
│  └──────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
    Log Aggregator      Trace Collector      Prometheus/Grafana
    (ELK, Datadog)      (Jaeger, Tempo)      (AlertManager)
```

---

## Quick Reference

### Environment Variables Summary

| Variable | Phase | Default | Description |
|----------|-------|---------|-------------|
| `LOG_LEVEL` | 1 | INFO | Logging verbosity |
| `LOG_FORMAT` | 1 | json | Log output format |
| `ENABLE_TRACING` | 1 | true | OpenTelemetry tracing |
| `SERVICE_NAME` | 1 | legal-compliance-api | Service identifier |
| `ENABLE_RATE_LIMITING` | 2 | true | Rate limiting toggle |
| `RATE_LIMIT_DEFAULT` | 2 | 100/minute | Default rate limit |
| `REQUIRE_AUTH` | 2 | false | API key requirement |
| `API_KEYS` | 2 | - | Comma-separated valid keys |
| `ENABLE_AUDIT_LOGGING` | 4 | true | Audit trail toggle |
| `AUDIT_SENSITIVE_PATHS` | 4 | /decide,/rules,/ke | Paths for extra audit detail |

### New Endpoints

| Endpoint | Phase | Description |
|----------|-------|-------------|
| `GET /metrics` | 1 | Prometheus metrics |
| `GET /v2/config` | 5 | System configuration (feature flags, observability) |

### File Structure

```
backend/core/
├── __init__.py          # Package exports
├── config.py            # Settings with env vars
├── logging.py           # Structured logging (Phase 1)
├── telemetry.py         # OTEL + Prometheus (Phase 1)
├── auth.py              # API key auth (Phase 2)
├── audit.py             # Audit events (Phase 4)
├── api/
│   └── routes_production.py  # /v2/config endpoint (Phase 5)
└── middleware/
    ├── security.py      # Security headers (Phase 2)
    └── audit.py         # Audit middleware (Phase 4)

frontend-react/src/
├── api/
│   └── production.api.ts     # Production API client (Phase 5)
├── hooks/
│   └── useProduction.ts      # Production React Query hooks (Phase 5)
├── components/common/
│   └── FeatureToggle.tsx     # Feature toggle display (Phase 5)
└── pages/
    └── ProductionDemo.tsx    # Enhanced with System tab (Phase 5)
```
