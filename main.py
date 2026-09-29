from pathlib import Path
from datetime import date, timedelta
import html
import re

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
    "buyer-name",
    "buyer-country",
    "classification-cpv",
    "notice-type",
]


def repair_text(value):

    if value is None:
        return ""

    if isinstance(value, list):
        return " ".join(
            repair_text(x)
            for x in value
        )

    if isinstance(value, dict):

        preferred = [
            "por",
            "eng",
            "spa",
            "fra",
            "deu",
            "ita",
            "nld",
        ]

        for lang in preferred:
            if lang in value:
                result = repair_text(
                    value[lang]
                )
                if result:
                    return result

        for item in value.values():
            result = repair_text(item)
            if result:
                return result

        return ""

    text = str(value)

    for _ in range(2):

        try:

            fixed = text.encode(
                "latin1"
            ).decode(
                "utf-8"
            )

            if fixed == text:
                break

            text = fixed

        except Exception:
            break

    return html.unescape(text)


def parse_date(value):

    if not value:
        return None

    match = re.search(
        r"(\d{4})[-]?(\d{2})[-]?(\d{2})",
        str(value)
    )

    if not match:
        return None

    try:

        return date(
            int(match.group(1)),
            int(match.group(2)),
            int(match.group(3)),
        )

    except Exception:

        return None


def get_title(notice):

    return repair_text(
        notice.get("notice-title")
    )


def get_buyer(notice):

    return repair_text(
        notice.get("buyer-name")
    )


def get_country(notice):

    return repair_text(
        notice.get("buyer-country")
    )


def get_cpvs(notice):

    value = notice.get(
        "classification-cpv"
    )

    if not value:
        return []

    if isinstance(value, list):
        return [
            str(x)
            for x in value
        ]

    return [str(value)]


def get_url(notice):

    links = notice.get("links", {})

    if isinstance(links, dict):

        html_links = links.get(
            "html",
            {}
        )

        if isinstance(
            html_links,
            dict
        ):

            for lang in [
                "POR",
                "ENG",
                "SPA",
                "FRA",
            ]:

                if html_links.get(lang):
                    return html_links[lang]

    number = notice.get(
        "publication-number"
    )

    if number:

        return (
            "https://ted.europa.eu/en/"
            f"notice/-/detail/{number}"
        )

    return "https://ted.europa.eu/"


def classify(title):

    text = title.lower()

    if any(
        x in text
        for x in [
            "archaeolog",
            "arqueolog",
            "archéolog",
            "archäolog",
            "archaeological",
            "archaeology",
            "escava",
            "excavation",
        ]
    ):

        return "Arqueologia direta"

    if any(
        x in text
        for x in [
            "cultural heritage",
            "patrimonio",
            "heritage",
            "historical",
            "historic monument",
        ]
    ):

        return "Património cultural"

    return "Grande projeto / potencial subcontratação"


def score(title, cpvs, category):

    text = title.lower()

    value = 30

    if any(
        x in text
        for x in [
            "archaeolog",
            "arqueolog",
            "archaeological",
            "archaeology",
            "excavat",
            "escava",
        ]
    ):

        value += 40

    if category == "Arqueologia direta":
        value += 20

    elif category == "Património cultural":
        value += 10

    if any(
        str(cpv).startswith(
            prefix
        )
        for cpv in cpvs
        for prefix in [
            "71351914",
            "92500000",
            "92520000",
            "92521000",
            "92522000",
        ]
    ):

        value += 10

    return min(
        value,
        100
    )


def search_ted(term):

    payload = {
        "query": f'notice-title~("{term}")',
        "fields": TED_FIELDS,
        "page": 1,
        "limit": 100,
        "scope": "ALL",
        "checkQuerySyntax": False,
        "paginationMode": "PAGE_NUMBER",
    }

    response = requests.post(
        TED_URL,
        json=payload,
        timeout=45,
    )

    data = response.json()

    if response.status_code != 200:

        raise RuntimeError(
            str(
                data.get(
                    "error",
                    data
                )
            )
        )

    return data


@app.get("/api/search")
def search(
    q: str = "archaeology",
    region: str = "",
    category: str = "",
):

    today = date.today()

    cutoff = (
        today
        - timedelta(days=365)
    )

    terms = [
        q.strip()
    ]

    for term in [
        "archaeological",
        "excavation",
        "cultural heritage",
        "archaeological monitoring",
    ]:

        if term.lower() not in [
            x.lower()
            for x in terms
        ]:

            terms.append(term)

    results = []

    diagnostics = []

    seen = set()

    for term in terms:

        try:

            data = search_ted(
                term
            )

            notices = data.get(
                "notices",
                []
            )

            added = 0

            for notice in notices:

                number = notice.get(
                    "publication-number"
                )

                if not number:
                    continue

                if number in seen:
                    continue

                publication_date = parse_date(
                    notice.get(
                        "publication-date"
                    )
                )

                if not publication_date:
                    continue

                # Apenas últimos 365 dias.
                if publication_date < cutoff:
                    continue

                title = get_title(
                    notice
                )

                buyer = get_buyer(
                    notice
                )

                country = get_country(
                    notice
                )

                cpvs = get_cpvs(
                    notice
                )

                classified = classify(
                    title
                )

                if category and (
                    classified != category
                ):
                    continue

                item = {
                    "title": title,
                    "source": "TED",
                    "date": publication_date.isoformat(),
                    "country": country,
                    "buyer": buyer,
                    "deadline": "",
                    "cpv": ", ".join(cpvs),
                    "category": classified,
                    "score": score(
                        title,
                        cpvs,
                        classified
                    ),
                    "url": get_url(
                        notice
                    ),
                    "publication_number": number,
                }

                seen.add(
                    number
                )

                results.append(
                    item
                )

                added += 1

            diagnostics.append({
                "source": f"TED — {term}",
                "ok": True,
                "count": added,
                "received": len(
                    notices
                ),
                "total": data.get(
                    "totalNoticeCount"
                ),
            })

        except Exception as e:

            diagnostics.append({
                "source": f"TED — {term}",
                "ok": False,
                "count": 0,
                "error": str(e),
            })

    results.sort(
        key=lambda x: (
            -x["score"],
            x["date"]
        ),
        reverse=False
    )

    results = results[:100]

    return {
        "results": results,
        "diagnostics": diagnostics,
        "portal_count": 0,
        "api_count": 1,
        "searched_at": today.isoformat(),
        "period_days": 365,
    }


@app.get("/api/health")
def health():

    return {
        "ok": True,
        "sources": 1,
        "api_sources": 1,
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
