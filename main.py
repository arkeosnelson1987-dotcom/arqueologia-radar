from pathlib import Path
import requests

from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse


ROOT = Path(__file__).resolve().parent

TED_URL = "https://api.ted.europa.eu/v3/notices/search"

app = FastAPI(title="Arqueologia Radar")


TED_FIELDS = [
    "publication-number",
    "publication-date",
    "notice-title",
]


@app.get("/api/search")
def search():

    payload = {
        "query": "",
        "fields": TED_FIELDS,
        "page": 1,
        "limit": 10,
        "scope": "ALL",
        "checkQuerySyntax": True,
        "paginationMode": "PAGE_NUMBER",
    }

    try:

        response = requests.post(
            TED_URL,
            json=payload,
            timeout=30,
        )

        data = response.json()

        return JSONResponse({
            "http_status": response.status_code,
            "response_keys": list(data.keys()),
            "totalNoticeCount": data.get("totalNoticeCount"),
            "notices_count": len(
                data.get("notices", [])
            ),
            "first_notice": (
                data.get("notices", [None])[0]
                if data.get("notices")
                else None
            ),
            "timedOut": data.get("timedOut"),
            "error": data.get("error"),
        })

    except Exception as e:

        return JSONResponse({
            "ok": False,
            "error": str(e),
        })


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/")
def home():
    return FileResponse(ROOT / "index.html")


@app.get("/app.js")
def javascript():
    return FileResponse(
        ROOT / "app.js",
        media_type="application/javascript"
    )


@app.get("/manifest.json")
def manifest():
    return FileResponse(
        ROOT / "manifest.json",
        media_type="application/manifest+json"
    )
