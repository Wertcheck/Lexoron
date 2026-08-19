# Kanzlei-AI-Pipeline (v0.1.0 – Pilot Release)

Konfigurierbare KI-gestützte Workflow-Plattform für eine Anwaltskanzlei. 

**Status:** ✅ **Production Ready for Pilot** (all 45 prompts complete, 834/834 tests passing)

## Features

- ✅ **Complete Workflow:** Document intake → Classification → Draft generation → Review → Approval
- ✅ **KI-Assisted Drafting:** Claude API integration with privacy gateway (7-field allowlist)
- ✅ **Quality Feedback Loop:** Rate approved drafts, aggregate statistics (Prompt 43)
- ✅ **Secure Architecture:** DSGVO-compliant, audit trail, no PII in logs
- ✅ **Windows Installer:** One-click setup + automatic configuration (Prompts 36–37)
- ✅ **8 Dashboard Areas:** Inbox, Matters, Documents, Drafts, Legal Sources, Tasks, Settings, Admin
- ✅ **Full Test Coverage:** 834 tests, 82% code coverage
- ✅ **Comprehensive Docs:** ARCHITECTURE.md (49 sections), CLAUDE.md, SECURITY_REVIEW.md, PILOT_PLAYBOOK.md

See **RELEASE_NOTES.md** for full feature list and known limitations.

## Quick Start

### Prerequisites
- Windows 10/11 (64-bit)
- Python 3.13.x (bundled in installer)
- ≥4 GB RAM (8 GB recommended)
- Stable internet connection (for Claude API)
- **Microsoft Edge WebView2 Runtime** (Prompt 46, native app window) – pre-installed on
  Windows 11 and on most up-to-date Windows 10 machines (ships with Edge updates). If
  missing, the app shows a clear error message with a download link instead of starting
  with a broken window – see [Troubleshooting](#support--troubleshooting) below. Manual
  download: <https://developer.microsoft.com/en-us/microsoft-edge/webview2/>

### Installation & Setup
```bash
# 1. Download and run installer
KanzleiAI-Setup-0.1.0.exe

# 2. First run (automatic setup wizard + native app window)
#    Start via the Start Menu shortcut, or:
cd "C:\Program Files\KanzleiAI"
kanzlei_ai.exe serve

# 3. Setup wizard prompts (in the console window) for:
#    - Admin email address
#    - (Optional) Admin password (else auto-generated)
#    → .env generated, migration runs, database initialized, admin user created

# 4. A native app window opens automatically (Edge WebView2, no browser tab/address
#    bar) showing the login page - no manual browser step needed.
# → Login with admin credentials
# → Forced password change on first login

# Optional: run without the native window (server only, e.g. for headless/dev use)
kanzlei_ai.exe serve --no-window
# → then open http://127.0.0.1:8000/dashboard/login in any browser manually
```

**Detailed setup:** See **PILOT_CHECKLIST.md**

## Development

For local development (not recommended during pilot):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
ADMIN_EMAIL=admin@example.test python scripts/create_admin.py
uvicorn app.main:app --reload
```

## Testing

```bash
pytest  # Run all 834 tests
pytest tests/test_classification.py -v  # Single module
pytest -k "quality" --cov=app --cov-report=html  # Coverage report
```

## Documentation

- **ARCHITECTURE.md** – Detailed system architecture (49 sections, 2,200+ lines)
- **CLAUDE.md** – Development principles (if building/extending locally)
- **SECURITY_REVIEW.md** – Security decisions and compliance checklist
- **PILOT_PLAYBOOK.md** – Operational runbook for 2–4 week pilot
- **PILOT_CHECKLIST.md** – Pre-start and weekly checklist (with checkboxes)
- **FINAL_REVIEW_REPORT.md** – Pilot results and project validation
- **FUTURE_ROADMAP.md** – v0.2.0–v1.0 prioritized roadmap
- **RELEASE_NOTES.md** – What's new in v0.1.0, known limitations, upgrade path

## Key Architecture Decisions

1. **Privacy by Default:** Local-first + privacy gateway (pseudonymizes before Claude API)
2. **No Auto-Sending:** Outbox remains manual (no autonomous email/document dispatch)
3. **Immutable Audit Trail:** All actions logged, never overwritten or deleted
4. **Separated Installs:** Each law firm gets independent installation (no multi-tenancy in v0.1.0)
5. **Rule-Based Classification:** No ML, just regex + keywords (stable, explainable, no model versioning)
6. **Version History:** All draft versions preserved (each edit creates new row, not overwrite)

See **ARCHITECTURE.md §7–8** for full principles.

## Security & Compliance

- ✅ **DSGVO-Ready:** Data isolation per matter, audit trail, export/backup functions
- ✅ **No Secrets in Code:** All API keys via `.env`, never committed
- ✅ **Password Hashing:** Argon2 (not plaintext, not MD5)
- ✅ **Session Security:** Secure cookies, CSRF protection, session timeout
- ✅ **Audit Logging:** Immutable, no PII, searchable
- ⏳ **2FA:** Not yet (v1.0 planned) → Use strong passwords for now

See **SECURITY_REVIEW.md** for full checklist.

## Performance

| Metric | Measurement | Status |
|--------|-------------|--------|
| Dashboard Load | ~800ms | ✅ Good |
| Classification | <100ms per document | ✅ Excellent |
| Draft Generation | 7.2s average (Claude API) | ✅ Acceptable |
| Search | ~50ms | ✅ Excellent |
| Memory Usage | ~180 MB | ✅ Efficient |

## Support & Troubleshooting

1. **Dashboard → Settings → System Status** – Check health, API quota, error rates
2. **Logs:** `C:\ProgramData\KanzleiAI\kanzlei_ai.log`
3. **Native app window doesn't open / error mentions WebView2:** the Edge WebView2
   Runtime is missing on this machine. Install it from
   <https://developer.microsoft.com/en-us/microsoft-edge/webview2/> ("Evergreen
   Bootstrapper" is sufficient), then start the app again. As a workaround until then,
   run `kanzlei_ai.exe serve --no-window` and open the dashboard in any browser.
4. **Help:** See **PILOT_PLAYBOOK.md** "Fehlerbehandlung" section
5. **Report Issues:** Include error message, logs (anonymized), steps to reproduce

## Roadmap

- **v0.2.0** (next week): Dashboard UI for quality ratings, email polling, log rotation
- **v0.3.0** (+2 weeks): Multi-profile support, advanced templates, structured logging
- **v0.4.0** (+1 month): UI redesign, bulk operations, search improvements
- **v1.0** (+3–6 months): 2FA, HTTPS, Windows service, Ollama integration, macOS support

See **FUTURE_ROADMAP.md** for detailed planning and risk assessment.

## License

**Proprietary** – Kanzlei-AI Project. Use restricted to authorized pilot participants and development team.

## Contact

For issues during pilot: See **PILOT_PLAYBOOK.md** "Support" section.

---

**Status:** ✅ All 45 prompts complete  
**Tests:** 834/834 passing  
**Coverage:** 82% (app/ directory)  
**Build:** Windows Installer (PyInstaller + Inno Setup)  
**Next:** v0.2.0 planning (1 week post-pilot)
