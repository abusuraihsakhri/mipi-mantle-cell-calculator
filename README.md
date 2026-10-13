# MIPI — Mantle Cell Lymphoma Prognostic Index

Clinical scoring tools for mantle cell lymphoma. The browser calculator, Python module, command-line tool, and FastAPI endpoint calculate the **original MIPI**, **simplified MIPI (s-MIPI)** and, when Ki-67 is supplied, **biological MIPI (MIPI-b)**.

## Browser application

The static application is in [web/index.html](web/index.html). It runs locally in any current desktop or mobile browser without a server, account, external dependencies, or Python runtime. A GitHub Pages deployment workflow is included in `.github/workflows/pages.yml`; deployment status must be checked in the repository's Actions/Pages settings before a public URL is advertised.

The calculator does not use browser storage or send input values to a server. Avoid submitting real patient identifiers to public services.

## Calculation

Inputs: age (years), ECOG performance status (0–4), WBC in **10⁹/L**, and LDH plus the laboratory LDH upper limit of normal (same units); alternatively supply LDH/ULN ratio. Optional Ki-67 is expressed as a percentage (0–100).

Original MIPI:

```text
0.03535 × age + 0.6978 × [ECOG ≥ 2]
+ 1.367 × log10(LDH / LDH_ULN)
+ 0.9393 × log10(WBC × 1000)
```

The WBC multiplication converts 10⁹/L to 10⁶/L for the published formula. Risk groups use the **unrounded** score:

| Index | Low | Intermediate | High |
|---|---|---|---|
| Original MIPI | < 5.7 | ≥ 5.7 to < 6.2 | ≥ 6.2 |
| s-MIPI | 0–3 points | 4–5 points | 6–11 points |
| MIPI-b | < 5.7 | ≥ 5.7 to < 6.5 | ≥ 6.5 |

MIPI-b = original MIPI + 0.02142 × Ki-67(%). The simplified index assigns points by age, ECOG, LDH/ULN, and WBC using the original published strata.

These are **prognostic** indices, not treatment recommendations or emergency-triage measures. External validity and risk interpretation depend on population, therapy era, and disease biology.

**References:** Hoster E et al. *Blood*. 2008;111:558–565. [DOI: 10.1182/blood-2007-06-095331](https://doi.org/10.1182/blood-2007-06-095331); [MIPI and Ki-67 discussion](https://aacrjournals.org/clincancerres/article/20/20/5194/117174/New-Paradigms-in-Mantle-Cell-Lymphoma-Is-It-Time).

## Local use

Requires Python 3.10+. The scoring module itself uses only the standard library.

```bash
git clone https://github.com/abusuraihsakhri/mipi-mantle-cell-calculator.git
cd mipi-mantle-cell-calculator
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python mipi_calc.py single --age 60 --ecog 0 --ldh 250 --ldh-uln 250 --wbc 10 --ki67 30
python mipi_calc.py batch -i sample.csv -o results.csv
python -m pytest -q
```

Windows activation: `.venv\Scripts\activate`. After installation, `mipi-calc` runs the same clinical CLI.

### CSV batch processing

A CSV requires columns `age`, `ecog`, `wbc`, and either `ldh_ratio` or both `ldh` and `ldh_uln`. `ki67` is optional; other identifier columns are retained. An invalid row is preserved with a nonempty `error` value and no invented risk score. Processing is local. Input and output paths must differ.

### FastAPI

```bash
python cli.py serve --host 127.0.0.1 --port 8000
```

`POST /api/mipi` accepts JSON such as `{"age":60,"ecog":0,"wbc":10,"ldh_ratio":1,"ki67":30}`. Validation errors return HTTP 422. Interactive schema: `http://127.0.0.1:8000/docs`.

The legacy supervisor endpoints (`/api/audit`, `/api/chat`, `/api/audit/logs`) are disabled unless the server defines `AUDIT_API_TOKEN` and requests supply the matching `X-Audit-Token` header. Keep this token server-side. The repository also retains earlier supervisor/audit, simulation and enrichment modules for compatibility. Their arbitrary thresholds and mock-response workflow are **not MIPI calculations**, and their messages must not be interpreted as clinical conclusions. A local audit HMAC secret can be set using `AUDIT_SECRET_KEY`; in-memory audit records do not constitute durable, externally compliant logging.

## Development and deployment

- `mipi_calc.py`: clinical scoring and batch processing
- `web/index.html`: standalone JavaScript browser calculator
- `agents/api.py`: REST interface and retained supervisor endpoints
- `cli.py`: retained supervisor CLI and API server
- `tests/` and `test_mipi_calc.py`: unit and regression checks
- `.github/workflows/ci.yml`: Python CI
- `.github/workflows/pages.yml`: static browser deployment
- `Dockerfile`, `docker-compose.yml`: optional FastAPI hosting

Docker Compose requires a locally configured `AUDIT_SECRET_KEY`. The browser calculator requires no Docker instance and no Pyodide.

Supported browsers: current Chromium, Firefox and Safari variants with standard JavaScript support (no browser-specific APIs required).

## License

MIT — see [LICENSE](LICENSE).
