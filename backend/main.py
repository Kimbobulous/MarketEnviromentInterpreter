from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_payload(tab: str) -> dict:
    timestamp = _iso_now()
    panel_id_prefix = "intraday" if tab == "intraday" else "swing"

    return {
        "tab": tab,
        "last_updated": timestamp,
        "panels": [
            {
                "id": f"{panel_id_prefix}_vol_state",
                "title": "Intraday Volatility State",
                "raw_metrics": [{"key": "range_pct", "value": 1.2, "unit": "%"}],
                "context": [
                    {"key": "range_percentile", "value": 72, "unit": "pctile"}
                ],
                "interpretation": [
                    "Current range is elevated relative to recent sessions.",
                    "Historically this tends to coincide with wider short-term dispersion.",
                ],
                "why_toggle": "Range measures the distance between high and low relative to prior sessions.",
                "status": "ok",
                "last_updated": timestamp,
            }
        ],
        "conditional_sensitivity": [
            "If volatility were to expand further, intraday dispersion could increase.",
            "If volatility compresses, range behavior may normalize.",
        ],
        "summary": [
            "Intraday volatility is currently above its recent median.",
            "This has historically been associated with wider short-term price swings.",
            "Other structural forces are not yet modeled in this stub.",
        ],
    }


@app.get("/api/intraday")
def get_intraday():
    return _build_payload("intraday")


@app.get("/api/swing")
def get_swing():
    return _build_payload("swing")
