from pathlib import Path
from datetime import date, datetime, timedelta
from typing import Any
import html
import re

import requests
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse


ROOT = Path(__file__).resolve().parent

TED_URL = "https://api.ted.europa.eu/v3/notices/search"

RESULTS_DAYS = 365
REQUEST_TIMEOUT = 30

TODAY = date.today()
CUTOFF_DATE = TODAY - timedelta(days=RESULTS_DAYS)


SOURCES = [
    {
        "name": "TED — Tenders Electronic Daily",
        "url": "https://ted.europa.eu/",
        "region": "Europa",
        "mode": "api",
    },
    {
        "name": "Diário da República",
        "url": "https://diariodarepublica.pt/",
        "region": "Europa",
        "mode": "portal",
    },
    {
        "name": "BASE — Contratos Públicos",
        "url": "https://www.base.gov.pt/",
        "region": "Europa",
        "mode": "portal",
    },
    {
        "name": "UK Find a Tender",
        "url": "https://www.find-tender.service.gov.uk/",
        "region": "Europa",
        "mode": "portal",
    },
    {
        "name": "Contracts Finder",
        "url": "https://www.contractsfinder.service.gov.uk/",
        "region": "Europa",
        "mode": "portal",
    },
    {
        "name": "eTenders Ireland",
        "url": "https://www.etenders.gov.ie/",
        "region": "Europa",
        "mode": "portal",
    },
    {
        "name": "Mercell",
        "url": "https://www.mercell.com/",
        "region": "Europa",
        "mode": "portal",
    },
    {
        "name": "France Marchés",
        "url": "https://www.marches-publics.gouv.fr/",
        "region": "Europa",
        "mode": "portal",
    },
    {
        "name": "BOAMP",
        "url": "https://www.boamp.fr/",
        "region": "Europa",
        "mode": "portal",
    },
    {
        "name": "Plataforma de Contratación del Sector Público",
        "url": "https://contrataciondelestado.es/",
        "region": "Europa",
        "mode": "portal",
    },
    {
        "name": "UN Global Marketplace",
        "url": "https://www.ungm.org/",
        "region": "Internacional",
        "mode": "portal",
    },
]


app = FastAPI(title="Arqueologia Radar")


# ============================================================
# TEXTO
# ============================================================

def mojibake_score(text: str) -> int:
    return sum(
        text.count(x)
        for x in ["Ã", "Â", "â", "ð", "Ð", "�"]
    )


def repair_text(value: Any) -> str:

    if value is None:
        return ""

    if isinstance(value, (list, tuple)):
        return " ".join(
            repair_text(x)
            for x in value
            if x is not None
        ).strip()

    if isinstance(value, dict):
        return " ".join(
            repair_text(v)
            for v in value.values()
            if v is not None
        ).strip()

    text = html.unescape(str(value))

    best = text

    for _ in range(4):

        candidates = [best]

        for encoding in ("latin1", "cp1252"):

            try:
                candidates.append(
                    best.encode(encoding).decode("utf-8")
                )
            except Exception:
                pass

        candidate = min(
            candidates,
            key=mojibake_score
        )

        if mojibake_score(candidate) < mojibake_score(best):
            best = candidate
        else:
            break

    return best.strip()


def flatten_values(value: Any) -> list[str]:

    if value is None:
        return []

    if isinstance(value, list):

        result = []

        for item in value:
            result.extend(
                flatten_values(item)
            )

        return result

    if isinstance(value, dict):

        result = []

        for item in value.values():
            result.extend(
                flatten_values(item)
            )

        return result

    text = repair_text(value)

    return [text] if text else []


# ============================================================
# DATAS
# ============================================================

def parse_date(value: Any) -> date | None:

    if value is None:
        return None

    text = repair_text(value).strip()

    if not text:
        return None

    text = text.split("T")[0]
    text = text.split(" ")[0]

    for pattern in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
    ):

        try:
            return datetime.strptime(
                text,
                pattern
            ).date()

        except ValueError:
            pass

    match = re.search(
        r"(\d{4})[-/](\d{2})[-/](\d{2})",
        text
    )

    if match:

        try:
            return date(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3))
            )
        except ValueError:
            pass

    return None


# ============================================================
# CAMPOS TED
# ============================================================

TED_FIELDS = [
    "publication-number",
    "publication-date",
    "notice-title",
    "buyer-name",
    "buyer-country",
    "classification-cpv",
    "notice-type",
    "procedure-identifier",

    "deadline-date-lot",
    "deadline-receipt-tender-date-lot",
    "deadline-receipt-request-date-lot",
    "deadline-receipt-expressions-date-lot",
]


# ============================================================
# TERMOS
# ============================================================

ARCHAEOLOGY_TERMS = [
    "archaeology",
    "archaeological",
    "archaeologist",
    "archaeologists",
    "archaeological excavation",
    "archaeological monitoring",
    "archaeological survey",
    "archaeological investigation",
    "excavation",
    "excavations",
    "archäologie",
    "archäologisch",
    "arqueologia",
    "arqueológico",
    "arqueológica",
    "escavação",
    "escavações",
    "acompanhamento arqueológico",
]

HERITAGE_TERMS = [
    "cultural heritage",
    "heritage",
    "historic monument",
    "historical monument",
    "built heritage",
    "património cultural",
    "patrimoine culturel",
    "kulturerbe",
]


def classify(title: str, cpv: str) -> str:

    text = f"{title} {cpv}".lower()

    if any(
        term in text
        for term in ARCHAEOLOGY_TERMS
    ):
        return "Arqueologia direta"

    if any(
        term in text
        for term in HERITAGE_TERMS
    ):
        return "Património cultural"

    return "Grande projeto / potencial subcontratação"


def calculate_score(
    title: str,
    cpv: str,
    deadline_date: date | None
) -> int:

    text = f"{title} {cpv}".lower()

    score = 30

    if any(
        x in text
        for x in [
            "archaeolog",
            "archäolog",
            "arqueolog",
        ]
    ):
        score += 30

    if any(
        x in text
        for x in [
            "excavat",
            "monitoring",
            "survey",
            "escava",
            "acompanhamento",
        ]
    ):
        score += 15

    if "71351914" in cpv:
        score += 15

    if deadline_date and deadline_date >= TODAY:
        score += 5

    return min(score, 100)


# ============================================================
# PESQUISA TED
# ============================================================

def search_ted(
    query: str
) -> tuple[list[dict], dict]:

    payload = {
        "query": f'FT~("{query}")',
        "fields": TED_FIELDS,
        "page": 1,
        "limit": 100,
        "scope": "ACTIVE",
        "checkQuerySyntax": True,
        "paginationMode": "PAGE_NUMBER",
    }

    try:

        response = requests.post(
            TED_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

    except Exception as exc:

        return [], {
            "source": "TED",
            "ok": False,
            "count": 0,
            "total": 0,
            "query": payload["query"],
            "period_days": RESULTS_DAYS,
            "searched_at": TODAY.isoformat(),
            "error": str(exc),
        }

    notices = data.get("notices", [])

    if not isinstance(notices, list):
        notices = []

    total = (
        data.get("totalNoticeCount")
        or data.get("total")
        or data.get("totalCount")
        or len(notices)
    )

    results = []

    for notice in notices:

        title = repair_text(
            notice.get("notice-title", "")
        )

        buyer = repair_text(
            notice.get("buyer-name", "")
        )

        country = repair_text(
            notice.get("buyer-country", "")
        )

        publication_number = repair_text(
            notice.get("publication-number", "")
        )

        procedure_id = repair_text(
            notice.get("procedure-identifier", "")
        )

        notice_type = repair_text(
            notice.get("notice-type", "")
        )

        publication_date = None

        for value in flatten_values(
            notice.get("publication-date")
        ):

            publication_date = parse_date(value)

            if publication_date:
                break

        cpv = "; ".join(
            dict.fromkeys(
                flatten_values(
                    notice.get("classification-cpv")
                )
            )
        )

        deadline_date = None

        deadline_fields = [
            "deadline-date-lot",
            "deadline-receipt-tender-date-lot",
            "deadline-receipt-request-date-lot",
            "deadline-receipt-expressions-date-lot",
        ]

        for field in deadline_fields:

            for value in flatten_values(
                notice.get(field)
            ):

                parsed = parse_date(value)

                if parsed:

                    if (
                        deadline_date is None
                        or parsed > deadline_date
                    ):
                        deadline_date = parsed

        # ----------------------------------------------------
        # FILTRO DE DATA
        # ----------------------------------------------------

        recent = (
            publication_date is not None
            and publication_date >= CUTOFF_DATE
        )

        active = (
            deadline_date is not None
            and deadline_date >= TODAY
        )

        if not recent and not active:
            continue

        # ----------------------------------------------------
        # RELEVÂNCIA
        # ----------------------------------------------------

        combined = (
            f"{title} {buyer} {cpv}"
        ).lower()

        relevant = (
            any(
                term in combined
                for term in ARCHAEOLOGY_TERMS
            )
            or "71351914" in cpv
            or any(
                term in combined
                for term in HERITAGE_TERMS
            )
        )

        if not relevant:
            continue

        # ----------------------------------------------------
        # STATUS
        # ----------------------------------------------------

        if deadline_date:

            if deadline_date >= TODAY:
                status = "Prazo aberto"
            else:
                status = "Prazo terminado"

        else:
            status = "Prazo não identificado"

        category = classify(
            title,
            cpv
        )

        score = calculate_score(
            title,
            cpv,
            deadline_date
        )

        url = (
            "https://ted.europa.eu/en/notice/-/detail/"
            + publication_number
            if publication_number
            else "https://ted.europa.eu/"
        )

        results.append({

            "title": title,

            "source": "TED",

            "date": (
                publication_date.isoformat()
                if publication_date
                else ""
            ),

            "publication_date": (
                publication_date.isoformat()
                if publication_date
                else ""
            ),

            "deadline": (
                deadline_date.isoformat()
                if deadline_date
                else ""
            ),

            "deadline_date": (
                deadline_date.isoformat()
                if deadline_date
                else ""
            ),

            "status": status,

            "country": country,

            "buyer": buyer,

            "cpv": cpv,

            "notice_type": notice_type,

            "publication_number": publication_number,

            "procedure_id": procedure_id,

            "category": category,

            "score": score,

            "url": url,
        })

    diagnostics = {

        "source": "TED",

        "ok": True,

        "count": len(results),

        "total": total,

        "notices_received": len(notices),

        "query": payload["query"],

        "period_days": RESULTS_DAYS,

        "cutoff_date": CUTOFF_DATE.isoformat(),

        "today": TODAY.isoformat(),

        "searched_at": TODAY.isoformat(),
    }

    return results, diagnostics


# ============================================================
# DEDUPLICAÇÃO
# ============================================================

def deduplicate(
    results: list[dict]
) -> list[dict]:

    seen = set()
    output = []

    for item in results:

        if item.get("procedure_id"):

            key = (
                "procedure",
                item["procedure_id"]
            )

        elif item.get("publication_number"):

            key = (
                "publication",
                item["publication_number"]
            )

        else:

            key = (
                "text",
                item.get(
                    "title",
                    ""
                ).lower(),
                item.get(
                    "buyer",
                    ""
                ).lower(),
            )

        if key in seen:
            continue

        seen.add(key)
        output.append(item)

    return output


# ============================================================
# ORDENAÇÃO
# ============================================================

def sort_results(
    results: list[dict]
) -> list[dict]:

    def sort_key(item):

        deadline = parse_date(
            item.get("deadline_date")
        )

        publication = parse_date(
            item.get("publication_date")
        )

        if deadline and deadline >= TODAY:
            status_order = 0

        elif not deadline:
            status_order = 1

        else:
            status_order = 2

        return (
            status_order,
            deadline or date.max,
            -(
                publication.toordinal()
                if publication
                else 0
            ),
            -int(
                item.get("score", 0)
            ),
        )

    return sorted(
        results,
        key=sort_key
    )


# ============================================================
# API
# ============================================================

@app.get("/api/search")
def api_search(
    q: str = Query(
        default="archaeology"
    ),
    region: str = "",
    category: str = "",
):

    query = q.strip() or "archaeology"

    results, diagnostics = search_ted(
        query
    )

    if category:

        results = [
            item
            for item in results
            if item.get("category") == category
        ]

    results = deduplicate(results)

    results = sort_results(results)

    return JSONResponse({

        "results": results,

        "diagnostics": [
            diagnostics
        ],

        "portal_count": len(SOURCES),

        "api_count": 1,

        "searched_at": TODAY.isoformat(),
    })


@app.get("/api/sources")
def api_sources():

    return JSONResponse(SOURCES)


@app.get("/api/health")
def health():

    return {
        "ok": True,
        "sources": len(SOURCES),
        "api_sources": 1,
        "today": TODAY.isoformat(),
        "cutoff_date": CUTOFF_DATE.isoformat(),
    }


@app.get("/")
def home():

    return FileResponse(
        ROOT / "index.html"
    )


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
