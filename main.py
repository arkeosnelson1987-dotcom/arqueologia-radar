from pathlib import Path
from datetime import date, datetime, timedelta
from typing import Any
import html
import re

import requests
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles


# ============================================================
# CONFIGURAÇÃO
# ============================================================

ROOT = Path(__file__).resolve().parent

TED_URL = "https://api.ted.europa.eu/v3/notices/search"

RESULTS_DAYS = 365
REQUEST_TIMEOUT = 30

TODAY = date.today()
CUTOFF_DATE = TODAY - timedelta(days=RESULTS_DAYS)


# ============================================================
# FONTES
# ============================================================

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
        "name": "TED Europa",
        "url": "https://ted.europa.eu/",
        "region": "Europa",
        "mode": "portal",
    },

    {
        "name": "SIMAP",
        "url": "https://simap.ted.europa.eu/",
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
        "name": "ANAC",
        "url": "https://www.anticorruzione.it/",
        "region": "Europa",
        "mode": "portal",
    },

    {
        "name": "eProcurement Italy",
        "url": "https://www.acquistinretepa.it/",
        "region": "Europa",
        "mode": "portal",
    },

    {
        "name": "Mercado Público España",
        "url": "https://contrataciondelestado.es/",
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
        "name": "e-Procurement Greece",
        "url": "https://portal.eprocurement.gov.gr/",
        "region": "Europa",
        "mode": "portal",
    },

    {
        "name": "Public Procurement Bulgaria",
        "url": "https://app.eop.bg/",
        "region": "Europa",
        "mode": "portal",
    },

    {
        "name": "Public Procurement Romania",
        "url": "https://www.e-licitatie.ro/",
        "region": "Europa",
        "mode": "portal",
    },

    {
        "name": "Public Procurement Croatia",
        "url": "https://eojn.nn.hr/",
        "region": "Europa",
        "mode": "portal",
    },

    {
        "name": "Public Procurement Slovenia",
        "url": "https://www.enarocanje.si/",
        "region": "Europa",
        "mode": "portal",
    },

    {
        "name": "Public Procurement Poland",
        "url": "https://ezamowienia.gov.pl/",
        "region": "Europa",
        "mode": "portal",
    },

    {
        "name": "Public Procurement Czech Republic",
        "url": "https://nen.nipez.cz/",
        "region": "Europa",
        "mode": "portal",
    },

    {
        "name": "Public Procurement Slovakia",
        "url": "https://www.uvo.gov.sk/",
        "region": "Europa",
        "mode": "portal",
    },

    {
        "name": "Public Procurement Hungary",
        "url": "https://ekr.gov.hu/",
        "region": "Europa",
        "mode": "portal",
    },

    {
        "name": "Public Procurement Lithuania",
        "url": "https://viesiejipirkimai.lt/",
        "region": "Europa",
        "mode": "portal",
    },

    {
        "name": "Public Procurement Latvia",
        "url": "https://www.eis.gov.lv/",
        "region": "Europa",
        "mode": "portal",
    },

    {
        "name": "Public Procurement Estonia",
        "url": "https://riigihanked.riik.ee/",
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


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(title="Arqueologia Radar")


# ============================================================
# TEXTO / CODIFICAÇÃO
# ============================================================

def mojibake_score(text: str) -> int:
    """
    Quanto maior o valor, maior a probabilidade de o texto
    estar com problemas de codificação.
    """
    suspicious = [
        "Ã",
        "Â",
        "â",
        "ð",
        "Ð",
        "�",
    ]

    return sum(text.count(x) for x in suspicious)


def repair_text(value: Any) -> str:
    """
    Corrige casos de UTF-8 interpretado como Latin-1/CP1252.
    """
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
                candidate = best.encode(encoding).decode("utf-8")
                candidates.append(candidate)
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
    """
    Converte estruturas TED em uma lista simples de valores.
    """
    result = []

    if value is None:
        return result

    if isinstance(value, list):
        for item in value:
            result.extend(flatten_values(item))
        return result

    if isinstance(value, dict):
        for item in value.values():
            result.extend(flatten_values(item))
        return result

    text = repair_text(value)

    if text:
        result.append(text)

    return result


# ============================================================
# DATAS
# ============================================================

def parse_date(value: Any) -> date | None:
    if value is None:
        return None

    text = repair_text(value).strip()

    if not text:
        return None

    # Remove horas quando aparecem
    text = text.split("T")[0]
    text = text.split(" ")[0]

    patterns = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%d-%m-%Y",
        "%Y/%m/%d",
    ]

    for pattern in patterns:
        try:
            return datetime.strptime(
                text,
                pattern
            ).date()
        except ValueError:
            pass

    # Procurar uma data no meio de texto
    match = re.search(
        r"(\d{4})[-/](\d{2})[-/](\d{2})",
        text
    )

    if match:
        try:
            return date(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
            )
        except ValueError:
            pass

    return None


def parse_deadline_values(notice: dict) -> tuple[date | None, str]:
    """
    Procura o prazo em vários campos TED.
    """

    fields = [
        "deadline-receipt-tender-date-lot",
        "deadline-receipt-tender-time-lot",
        "deadline-receipt-request-date-lot",
        "deadline-receipt-expressions-date-lot",
        "deadline-receipt-tender-date",
        "deadline-receipt-tender-time",
        "deadline-receipt-request-date",
        "deadline-receipt-expressions-date",
    ]

    candidates = []

    for field in fields:
        if field not in notice:
            continue

        for value in flatten_values(notice.get(field)):
            candidates.append(value)

    deadline_date = None

    for value in candidates:
        parsed = parse_date(value)

        if parsed is None:
            continue

        if deadline_date is None or parsed > deadline_date:
            deadline_date = parsed

    if deadline_date:
        return deadline_date, deadline_date.isoformat()

    return None, ""


# ============================================================
# TEXTO PREFERENCIAL
# ============================================================

def extract_preferred_text(value: Any) -> str:
    """
    Escolhe texto legível quando o TED fornece versões
    multilingues.
    """

    if value is None:
        return ""

    if isinstance(value, str):
        return repair_text(value)

    if isinstance(value, list):
        values = []

        for item in value:
            text = extract_preferred_text(item)

            if text:
                values.append(text)

        if not values:
            return ""

        # Preferir português / inglês
        for text in values:
            low = text.lower()

            if any(
                marker in low
                for marker in [
                    "archaeolog",
                    "archäolog",
                    "arqueolog",
                    "heritage",
                    "patrimoine",
                    "archäologie",
                ]
            ):
                return text

        return values[0]

    if isinstance(value, dict):

        # Estruturas do tipo {"eng": "...", "por": "..."}
        preferred_keys = [
            "eng",
            "por",
            "pt",
            "en",
        ]

        for key in preferred_keys:
            if key in value:
                text = extract_preferred_text(value[key])

                if text:
                    return text

        values = []

        for item in value.values():
            text = extract_preferred_text(item)

            if text:
                values.append(text)

        return values[0] if values else ""

    return repair_text(value)


# ============================================================
# RELEVÂNCIA
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

INFRASTRUCTURE_TERMS = [
    "construction",
    "railway",
    "road",
    "highway",
    "airport",
    "energy",
    "electricity",
    "pipeline",
    "water",
    "infrastructure",
    "construction works",
    "construção",
    "infraestrutura",
]


def classify(title: str, cpv: str) -> str:
    text = (
        f"{title} {cpv}"
    ).lower()

    direct = any(
        term in text
        for term in ARCHAEOLOGY_TERMS
    )

    heritage = any(
        term in text
        for term in HERITAGE_TERMS
    )

    infrastructure = any(
        term in text
        for term in INFRASTRUCTURE_TERMS
    )

    if direct:
        return "Arqueologia direta"

    if heritage:
        return "Património cultural"

    if infrastructure:
        return "Grande projeto / potencial subcontratação"

    return "Grande projeto / potencial subcontratação"


def calculate_score(
    title: str,
    cpv: str,
    category: str,
    deadline_date: date | None,
) -> int:

    text = f"{title} {cpv}".lower()

    score = 30

    # Arqueologia explícita
    if any(
        term in text
        for term in [
            "archaeolog",
            "archäolog",
            "arqueolog",
        ]
    ):
        score += 30

    # Escavação / acompanhamento
    if any(
        term in text
        for term in [
            "excavat",
            "monitoring",
            "survey",
            "escava",
            "acompanhamento",
        ]
    ):
        score += 15

    # CPV de arqueologia
    if "71351914" in cpv:
        score += 15

    # Património
    if category == "Património cultural":
        score += 5

    # Prazo futuro
    if deadline_date:
        if deadline_date >= TODAY:
            score += 5

    return min(score, 100)


# ============================================================
# TED
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

    "deadline-receipt-tender-date-lot",
    "deadline-receipt-tender-time-lot",
    "deadline-receipt-request-date-lot",
    "deadline-receipt-expressions-date-lot",

    "deadline-receipt-tender-date",
    "deadline-receipt-tender-time",
    "deadline-receipt-request-date",
    "deadline-receipt-expressions-date",
]


def search_ted(query: str) -> tuple[list[dict], dict]:

    payload = {
        "query": f'FT~("{query}")',
        "fields": TED_FIELDS,
        "page": 1,
        "limit": 100,
        "scope": "ACTIVE",
        "checkQuerySyntax": True,
        "paginationMode": "ITERATION",
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

    total = data.get(
        "totalNoticeCount",
        len(notices)
    )

    results = []

    for notice in notices:

        title = extract_preferred_text(
            notice.get("notice-title")
        )

        buyer = extract_preferred_text(
            notice.get("buyer-name")
        )

        country = extract_preferred_text(
            notice.get("buyer-country")
        )

        publication_number = extract_preferred_text(
            notice.get("publication-number")
        )

        procedure_id = extract_preferred_text(
            notice.get("procedure-identifier")
        )

        notice_type = extract_preferred_text(
            notice.get("notice-type")
        )

        publication_date = None

        publication_values = flatten_values(
            notice.get("publication-date")
        )

        for value in publication_values:
            parsed = parse_date(value)

            if parsed:
                publication_date = parsed
                break

        cpv_values = flatten_values(
            notice.get("classification-cpv")
        )

        cpv = "; ".join(
            dict.fromkeys(cpv_values)
        )

        deadline_date, deadline_text = parse_deadline_values(
            notice
        )

        # ----------------------------------------------------
        # FILTRO DE DATA
        # ----------------------------------------------------

        recent_enough = (
            publication_date is not None
            and publication_date >= CUTOFF_DATE
        )

        still_active = (
            deadline_date is not None
            and deadline_date >= TODAY
        )

        # Mantemos:
        # 1. avisos publicados nos últimos 365 dias;
        # 2. avisos antigos que tenham prazo futuro.
        if not recent_enough and not still_active:
            continue

        # ----------------------------------------------------
        # RELEVÂNCIA
        # ----------------------------------------------------

        category = classify(
            title,
            cpv
        )

        combined = (
            f"{title} "
            f"{buyer} "
            f"{cpv}"
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

        score = calculate_score(
            title,
            cpv,
            category,
            deadline_date,
        )

        # URL TED
        if publication_number:
            url = (
                "https://ted.europa.eu/en/notice/-/detail/"
                + publication_number
            )
        else:
            url = "https://ted.europa.eu/"

        results.append({
            "title": repair_text(title),
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
            "deadline": deadline_text,
            "deadline_date": deadline_text,
            "status": status,
            "country": repair_text(country),
            "buyer": repair_text(buyer),
            "cpv": repair_text(cpv),
            "notice_type": repair_text(notice_type),
            "publication_number": repair_text(
                publication_number
            ),
            "procedure_id": repair_text(
                procedure_id
            ),
            "category": category,
            "score": score,
            "url": url,
        })

    diagnostics = {
        "source": "TED",
        "ok": True,
        "count": len(results),
        "total": total,
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

def deduplicate(results: list[dict]) -> list[dict]:

    seen = set()
    output = []

    for item in results:

        key = None

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
                item.get("title", "").lower(),
                item.get("buyer", "").lower(),
            )

        if key in seen:
            continue

        seen.add(key)
        output.append(item)

    return output


# ============================================================
# ORDENAÇÃO
# ============================================================

def sort_results(results: list[dict]) -> list[dict]:

    def key(item):

        deadline = parse_date(
            item.get("deadline_date")
        )

        publication = parse_date(
            item.get("publication_date")
        )

        # 0 = prazo aberto
        if deadline and deadline >= TODAY:
            status_order = 0

        # 1 = prazo não identificado
        elif not deadline:
            status_order = 1

        # 2 = terminado
        else:
            status_order = 2

        deadline_sort = (
            deadline
            if deadline
            else date.max
        )

        publication_sort = (
            publication
            if publication
            else date.min
        )

        return (
            status_order,
            deadline_sort,
            -publication_sort.toordinal(),
            -int(item.get("score", 0)),
        )

    return sorted(
        results,
        key=key
    )


# ============================================================
# API SEARCH
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

    ted_results, ted_diag = search_ted(
        query
    )

    results = ted_results

    # Filtro adicional de categoria
    if category:
        results = [
            item
            for item in results
            if item.get("category") == category
        ]

    results = deduplicate(
        results
    )

    results = sort_results(
        results
    )

    return JSONResponse({
        "results": results,
        "diagnostics": [
            ted_diag
        ],
        "portal_count": len(SOURCES),
        "api_count": 1,
        "searched_at": TODAY.isoformat(),
    })


# ============================================================
# SOURCES
# ============================================================

@app.get("/api/sources")
def api_sources():

    return JSONResponse(
        SOURCES
    )


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():

    return {
        "ok": True,
        "sources": len(SOURCES),
        "api_sources": 1,
        "today": TODAY.isoformat(),
        "cutoff_date": CUTOFF_DATE.isoformat(),
    }


# ============================================================
# FICHEIROS ESTÁTICOS
# ============================================================

@app.get("/")
def home():

    return FileResponse(
        ROOT / "index.html"
    )


@app.get("/app.js")
def javascript():

    return FileResponse(
        ROOT / "app.js",
        media_type="application/javascript",
    )


@app.get("/manifest.json")
def manifest():

    return FileResponse(
        ROOT / "manifest.json",
        media_type="application/manifest+json",
    )
