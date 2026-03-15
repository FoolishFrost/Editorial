# Security Audit Report

This document records the findings of a full security sweep of this repository.
No source code changes have been made; this report is provided for review before any
remediation work begins.

---

## Findings

### 1. Support email address exposed in source code and installer script

**Severity:** Low  
**Files affected:**
- `editorial.py` (line 59) — `SUPPORT_EMAIL = "johnbowden@foolishdesigns.com"`
- `installer/Editorial.iss` (line 5) — `#define MyAppSupportEmail "johnbowden@foolishdesigns.com"`

The support email address is hardcoded in both the Python source and the Inno Setup
installer script and is therefore visible to anyone who views the repository.  While
this appears to be intentional (the address is displayed in the application's *About*
dialog), it does expose a personal contact address publicly.

**Recommendation:** If the address is intentionally public, no action is required.
If you would prefer to reduce exposure, consider replacing the hardcoded value with a
dedicated project/role address (e.g. `support@foolishdesigns.com`) or moving the
contact detail to a documentation page rather than embedding it directly in source.

---

### 2. Creator's full name hardcoded in source and installer

**Severity:** Informational  
**Files affected:**
- `editorial.py` (line 58) — `CREATOR_NAME = "John Bowden"`
- `installer/Editorial.iss` (line 4) — `#define MyAppCreator "John Bowden"`

The creator's full name appears in source code that is publicly visible.  This is
consistent with the stated intent of the *About* dialog but is noted here for
completeness.

**Recommendation:** No action required unless privacy is a concern.

---

## No Critical Issues Found

The following categories were audited and returned **no findings**:

| Category | Result |
|---|---|
| Hardcoded passwords | ✅ None found |
| API keys / access tokens | ✅ None found |
| Private keys or certificates (`.key`, `.pem`, `.crt`, `.pfx`) | ✅ None found |
| Database connection strings | ✅ None found (no database used) |
| Cloud provider credentials (AWS, Azure, GCP) | ✅ None found |
| Third-party service tokens (Stripe, Twilio, SendGrid, etc.) | ✅ None found |
| `.env` files committed to the repository | ✅ None present |

---

## .gitignore Assessment

The existing `.gitignore` covers the standard Python build artifacts:

```
.venv/
__pycache__/
build/
dist/
release/
*.pyc
```

This is appropriate for the project.  As a precaution, the following entries could be
added to guard against accidental future commits of sensitive files:

```
*.env
.env*
*.key
*.pem
*.p12
*.pfx
secrets/
```

These files do not currently exist in the repository, so adding these entries is
purely a preventive measure.

---

## Summary

The repository is in a **good security posture**.  No credentials, tokens, or
private keys are present.  The only items worth discussing with the repository owner
are the hardcoded support email address and creator name — both appear intentional and
are low severity.

**Recommended next steps (owner's decision required):**

1. Confirm whether the support email address in source code and the installer script
   should remain as-is, be replaced with a role address, or be moved to documentation
   only.
2. Optionally add the extra `.gitignore` patterns listed above as a preventive measure.
