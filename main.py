from pathlib import Path
from datetime import date, datetime, timedelta
import html
import re
import unicodedata

import requests

from fastapi import FastAPI
from fastapi.responses import JSONResponse, FileResponse


ROOT = Path(__file__).resolve().parent

TED_URL = "https://api.ted.europa.eu/v3/notices/search"

app = FastAPI(title="Arqueologia Radar")


# ============================================================
# CONFIGURAÇÃO
# ============================================================

PERIOD_DAYS = 365

TED_FIELDS = [
    "publication-number",
    "publication-date",
    "notice-title",
    "buyer-name",
    "buyer-country",
    "classification-cpv",
    "notice-type",
    "deadline-date-lot",
]


SEARCH_TERMS = [
    "archaeology",
    "archaeological",
    "excavation",
    "cultural heritage",
    "archaeological monitoring",
]


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def repair_text(value):
    """
    Corrige problemas de codificação do tipo:
    ServiÃ§os arqueolÃ³gicos
    """

    if value is None:
        return ""

    if isinstance(value, list):
        return " ".join(
            repair_text(x)
            for x in value
        )

    if isinstance(value, dict):
        return " ".join(
            repair_text(x)
            for x in value.values()
        )

    text = str(value)

    for _ in range(2):
        try:
            repaired = text.encode(
                "latin1"
            ).decode(
                "utf-8"
            )

            if repaired == text:
                break

            text = repaired

        except Exception:
            break

    return html.unescape(text)


def normalize_text(value):
    text = repair_text(value)

    text = unicodedata.normalize(
        "NFKD",
        text
    )

    text = "".join(
        c for c in text
        if not unicodedata.combining(c)
    )

    return text.lower()


def first_language_value(value):
    """
    TED devolve vários campos como:
    {
        "por": "...",
        "eng": "..."
    }

    ou como listas.
    """

    if value is None:
        return ""

    if isinstance(value, str):
        return repair_text(value)

    if isinstance(value, list):
        for item in value:
            result = first_language_value(item)

            if result:
                return result

        return ""

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
                result = first_language_value(
                    value[lang]
                )

                if result:
                    return result

        for item in value.values():

            result = first_language_value(item)

            if result:
                return result

    return repair_text(value)


def parse_date(value):
    """
    Aceita:
    2026-09-29
    2026-09-29+02:00
    20260929
    """

    if not value:
        return None

    value = str(value).strip()

    match = re.search(
        r"(\d{4})[-]?(\d{2})[-]?(\d{2})",
        value
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


def extract_deadline(notice):
    """
    Procura o prazo em vários formatos possíveis
    devolvidos pelo TED.
    """

    candidates = []

    for field in [
        "deadline-date-lot",
        "deadline",
        "deadline-date-part",
    ]:

        value = notice.get(field)

        if value:
            candidates.append(value)

    for value in candidates:

        result = parse_date(value)

        if result:
            return result

        if isinstance(value, list):

            for item in value:

                result = parse_date(item)

                if result:
                    return result

        if isinstance(value, dict):

            for item in value.values():

                result = parse_date(item)

                if result:
                    return result

    return None


def get_country(notice):
    value = notice.get(
        "buyer-country"
    )

    return first_language_value(value)


def get_buyer(notice):
    return first_language_value(
        notice.get("buyer-name")
    )


def get_title(notice):
    return first_language_value(
        notice.get("notice-title")
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


def get_notice_url(notice):
    """
    Usa a ligação oficial devolvida pelo TED.
    """

    links = notice.get("links")

    if isinstance(links, dict):

        html_links = links.get(
            "html"
        )

        if isinstance(
            html_links,
            dict
        ):

            for language in [
                "POR",
                "ENG",
                "SPA",
                "FRA",
            ]:

                if html_links.get(language):
                    return html_links[language]

            for value in html_links.values():

                if value:
                    return value

    publication_number = notice.get(
        "publication-number"
    )

    if publication_number:

        return (
            "https://ted.europa.eu/en/"
            f"notice/-/detail/"
            f"{publication_number}"
        )

    return "https://ted.europa.eu/"


# ============================================================
# CLASSIFICAÇÃO
# ============================================================

def classify_notice(
    title,
    cpvs,
    query_term,
):

    text = normalize_text(
        title
    )

    archaeology_words = [
        "archaeolog",
        "arqueolog",
        "archaeological",
        "archaeology",
        "escavacao",
        "excavation",
        "excavacoes",
        "excavation",
        "archaeological monitoring",
    ]

    heritage_words = [
        "cultural heritage",
        "heritage",
        "patrimonio cultural",
        "historical heritage",
        "historic monument",
        "monument",
        "archaeological heritage",
    ]

    construction_words = [
        "construction",
        "construction work",
        "infrastructure",
        "railway",
        "road",
        "highway",
        "building",
        "construction works",
        "empreitada",
    ]

    direct = any(
        word in text
        for word in archaeology_words
    )

    heritage = any(
        word in text
        for word in heritage_words
    )

    construction = any(
        word in text
        for word in construction_words
    )

    if direct:
        category = "Arqueologia direta"

    elif heritage:
        category = "Património cultural"

    elif construction:
        category = (
            "Grande projeto / potencial subcontratação"
        )

    else:
        category = "Património cultural"

    return category


def calculate_score(
    title,
    cpvs,
    deadline,
    category,
):

    text = normalize_text(
        title
    )

    score = 30

    if any(
        word in text
        for word in [
            "archaeolog",
            "arqueolog",
            "excavation",
            "escavacao",
        ]
    ):
        score += 35

    if any(
        cpv.startswith(prefix)
        for cpv in cpvs
        for prefix in [
            "71351914",
            "92500000",
            "92520000",
            "92521000",
            "92522000",
        ]
    ):
        score += 20

    if category == "Arqueologia direta":
        score += 10

    elif category == "Património cultural":
        score += 5

    if deadline:

        today = date.today()

        if deadline >= today:

            days = (
                deadline - today
            ).days

            if days <= 30:
                score += 10

            elif days <= 90:
                score += 5

    return min(
        score,
        100
    )


# ============================================================
# TED
# ============================================================

def search_ted(
    query,
    period_days=PERIOD_DAYS,
):

    today = date.today()

    cutoff = (
        today
        - timedelta(
            days=period_days
        )
    )

    cutoff_text = cutoff.strftime(
        "%Y%m%d"
    )

    # A data é filtrada no próprio TED.
    #
    # Ordenamos por data descendente para que
    # os avisos mais recentes apareçam primeiro.
    expert_query = (
        f'{query} '
        f'AND publication-date>={cutoff_text} '
        f'SORT BY publication-date DESC'
    )

    payload = {
        "query": expert_query,
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

        error = data.get(
            "error"
        )

        if isinstance(
            error,
            list
        ):
            error = "; ".join(
                str(x)
                for x in error
            )

        raise RuntimeError(
            error
            or data.get(
                "message"
            )
            or f"TED HTTP {response.status_code}"
        )

    notices = data.get(
        "notices",
        []
    )

    return (
        notices,
        data,
        expert_query,
        cutoff,
    )


# ============================================================
# API PRINCIPAL
# ============================================================

@app.get("/api/search")
def search(
    q: str = "archaeology",
    region: str = "",
    category: str = "",
):

    today = date.today()

    results = []

    diagnostics = []

    seen = set()

    # O texto introduzido pelo utilizador passa
    # a ser a primeira pesquisa.
    terms = []

    if q.strip():
        terms.append(
            q.strip()
        )

    for term in SEARCH_TERMS:

        if normalize_text(term) not in [
            normalize_text(x)
            for x in terms
        ]:
            terms.append(term)

    for term in terms:

        query = (
            f'notice-title~("{term}")'
        )

        try:

            (
                notices,
                data,
                expert_query,
                cutoff,
            ) = search_ted(
                query
            )

            added = 0

            for notice in notices:

                publication_number = (
                    notice.get(
                        "publication-number"
                    )
                )

                if not publication_number:
                    continue

                if publication_number in seen:
                    continue

                title = get_title(
                    notice
                )

                publication_date = parse_date(
                    notice.get(
                        "publication-date"
                    )
                )

                if not publication_date:
                    continue

                deadline = extract_deadline(
                    notice
                )

                # Segurança adicional:
                # mesmo com o filtro TED, confirmamos
                # localmente o período.
                if (
                    publication_date < cutoff
                    and (
                        not deadline
                        or deadline < today
                    )
                ):
                    continue

                # Ignorar avisos já encerrados.
                if (
                    deadline
                    and deadline < today
                ):
                    continue

                cpvs = get_cpvs(
                    notice
                )

                buyer = get_buyer(
                    notice
                )

                country = get_country(
                    notice
                )

                classified = classify_notice(
                    title,
                    cpvs,
                    term,
                )

                if category and (
                    classified != category
                ):
                    continue

                score = calculate_score(
                    title,
                    cpvs,
                    deadline,
                    classified,
                )

                result = {
                    "title": title,
                    "source": "TED",
                    "date": publication_date.isoformat(),
                    "country": country,
                    "buyer": buyer,
                    "deadline": (
                        deadline.isoformat()
                        if deadline
                        else ""
                    ),
                    "cpv": ", ".join(
                        cpvs
                    ),
                    "category": classified,
                    "score": score,
                    "url": get_notice_url(
                        notice
                    ),
                    "publication_number":
                        publication_number,
                }

                seen.add(
                    publication_number
                )

                results.append(
                    result
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
                "query": expert_query,
                "period_days": period_days,
            })

        except Exception as e:

            diagnostics.append({
                "source": f"TED — {term}",
                "ok": False,
                "count": 0,
                "error": str(e),
                "query": query,
                "period_days": period_days,
            })

    # Ordenação:
    # 1. concursos com prazo conhecido e futuro
    # 2. prazo mais próximo
    # 3. pontuação
    # 4. publicação mais recente
    def sort_key(item):

        deadline = parse_date(
            item.get(
                "deadline"
            )
        )

        publication = parse_date(
            item.get(
                "date"
            )
        )

        return (
            0 if deadline else 1,
            deadline
            or date.max,
            -item.get(
                "score",
                0
            ),
            -(publication.toordinal()
              if publication
              else 0),
        )

    results.sort(
        key=sort_key
    )

    # Limite final para a interface.
    results = results[:100]

    return {
        "results": results,
        "diagnostics": diagnostics,
        "portal_count": 0,
        "api_count": 1,
        "searched_at": today.isoformat(),
        "period_days": PERIOD_DAYS,
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():

    return {
        "ok": True,
        "sources": 1,
        "api_sources": 1,
    }


# ============================================================
# INTERFACE
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
        media_type="application/javascript"
    )


@app.get("/manifest.json")
def manifest():

    return FileResponse(
        ROOT / "manifest.json",
        media_type="application/manifest+json"
    )
