from pathlib import Path
from datetime import datetime, date
import html
import re
import unicodedata

import requests
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse


# ============================================================
# CONFIGURAÇÃO
# ============================================================

ROOT = Path(__file__).resolve().parent

app = FastAPI(title="Arqueologia Radar")

TED_URL = "https://api.ted.europa.eu/v3/notices/search"

RESULTS_DAYS = 365
REQUEST_TIMEOUT = 30


# ============================================================
# FONTES
# ============================================================

SOURCES = [
    {
        "name": "TED — Tenders Electronic Daily",
        "region": "Europa",
        "url": "https://ted.europa.eu/",
        "mode": "api",
    },
    {
        "name": "Diário da República — Portugal",
        "region": "Europa",
        "url": "https://diariodarepublica.pt/",
        "mode": "portal",
    },
    {
        "name": "BASE — Contratos Públicos Portugal",
        "region": "Europa",
        "url": "https://www.base.gov.pt/",
        "mode": "portal",
    },
    {
        "name": "Portal dos Contratos Públicos — Espanha",
        "region": "Europa",
        "url": "https://contrataciondelestado.es/",
        "mode": "portal",
    },
    {
        "name": "eForms — Itália",
        "region": "Europa",
        "url": "https://www.acquistinretepa.it/",
        "mode": "portal",
    },
    {
        "name": "Marchés Publics — França",
        "region": "Europa",
        "url": "https://www.marches-publics.gouv.fr/",
        "mode": "portal",
    },
    {
        "name": "SIMAP — União Europeia",
        "region": "Europa",
        "url": "https://simap.ted.europa.eu/",
        "mode": "portal",
    },
    {
        "name": "eTendering — Irlanda",
        "region": "Europa",
        "url": "https://www.etenders.gov.ie/",
        "mode": "portal",
    },
    {
        "name": "Contracts Finder — Reino Unido",
        "region": "Europa",
        "url": "https://www.contractsfinder.service.gov.uk/",
        "mode": "portal",
    },
    {
        "name": "Find a Tender — Reino Unido",
        "region": "Europa",
        "url": "https://www.find-tender.service.gov.uk/",
        "mode": "portal",
    },
    {
        "name": "Mercell",
        "region": "Europa",
        "url": "https://www.mercell.com/",
        "mode": "portal",
    },
    {
        "name": "Doffin — Noruega",
        "region": "Europa",
        "url": "https://www.doffin.no/",
        "mode": "portal",
    },
    {
        "name": "HILMA — Finlândia",
        "region": "Europa",
        "url": "https://www.hankintailmoitukset.fi/",
        "mode": "portal",
    },
    {
        "name": "TED Europa",
        "region": "Europa",
        "url": "https://ted.europa.eu/en/",
        "mode": "portal",
    },
    {
        "name": "eTendering — Malta",
        "region": "Europa",
        "url": "https://contracts.gov.mt/",
        "mode": "portal",
    },
    {
        "name": "Public Procurement Service — Irlanda",
        "region": "Europa",
        "url": "https://www.gov.ie/",
        "mode": "portal",
    },
    {
        "name": "Tenders Electronic Daily — Europa",
        "region": "Europa",
        "url": "https://ted.europa.eu/en/search",
        "mode": "portal",
    },
    {
        "name": "UN Development Business",
        "region": "Internacional",
        "url": "https://devbusiness.un.org/",
        "mode": "portal",
    },
    {
        "name": "World Bank Procurement",
        "region": "Internacional",
        "url": "https://www.worldbank.org/en/projects-operations/products-and-services/procurement-projects-programs",
        "mode": "portal",
    },
    {
        "name": "UNOPS Procurement",
        "region": "Internacional",
        "url": "https://www.unops.org/business-opportunities",
        "mode": "portal",
    },
    {
        "name": "African Development Bank",
        "region": "África",
        "url": "https://www.afdb.org/en/projects-and-operations/procurement",
        "mode": "portal",
    },
    {
        "name": "African Union Procurement",
        "region": "África",
        "url": "https://au.int/",
        "mode": "portal",
    },
    {
        "name": "Asian Development Bank",
        "region": "Ásia-Pacífico",
        "url": "https://www.adb.org/work-with-us",
        "mode": "portal",
    },
    {
        "name": "Inter-American Development Bank",
        "region": "Américas",
        "url": "https://www.iadb.org/en/how-we-can-work-together/procurement",
        "mode": "portal",
    },
    {
        "name": "European Investment Bank",
        "region": "Europa",
        "url": "https://www.eib.org/en/about/procurement/index.htm",
        "mode": "portal",
    },
    {
        "name": "European Bank for Reconstruction and Development",
        "region": "Europa",
        "url": "https://www.ebrd.com/work-with-us/procurement.html",
        "mode": "portal",
    },
    {
        "name": "UNESCO Procurement",
        "region": "Internacional",
        "url": "https://www.unesco.org/en/procurement",
        "mode": "portal",
    },
    {
        "name": "EU Funding & Tenders Portal",
        "region": "Europa",
        "url": "https://ec.europa.eu/info/funding-tenders/opportunities/portal/",
        "mode": "portal",
    },
]


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
    "deadline-receipt-tender-date-lot",
    "deadline-receipt-tender-time-lot",
]


# ============================================================
# CORREÇÃO DE TEXTO
# ============================================================

MOJIBAKE_MARKERS = (
    "Ã",
    "Â",
    "â€",
    "â€™",
    "â€œ",
    "â€“",
    "â€”",
    "ð",
    "Ð",
    "�",
)


def mojibake_score(text):
    if not text:
        return 0

    return sum(text.count(x) for x in MOJIBAKE_MARKERS)


def repair_text(value):
    """
    Corrige textos que tenham sido interpretados como Latin-1
    quando originalmente eram UTF-8.

    Faz várias tentativas e apenas aceita uma transformação
    quando a quantidade de sinais de mojibake diminui.
    """

    if value is None:
        return ""

    if isinstance(value, (int, float, bool)):
        return str(value)

    text = str(value)

    # Decodificar entidades HTML, se existirem.
    text = html.unescape(text)

    for _ in range(3):
        before_score = mojibake_score(text)

        if before_score == 0:
            break

        try:
            candidate = text.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            break

        after_score = mojibake_score(candidate)

        if after_score < before_score:
            text = candidate
        else:
            break

    return text


def clean_text(value):
    return repair_text(value).strip()


# ============================================================
# EXTRAÇÃO DE CAMPOS TED
# ============================================================

def flatten_values(value):
    """
    Converte estruturas TED variadas em uma lista simples.
    """

    if value is None:
        return []

    if isinstance(value, list):
        result = []

        for item in value:
            result.extend(flatten_values(item))

        return result

    if isinstance(value, dict):
        result = []

        # Estruturas multilingues frequentes
        for key in (
            "value",
            "text",
            "label",
            "content",
            "literal",
            "name",
            "language",
            "en",
            "pt",
            "fr",
            "de",
            "it",
            "es",
        ):
            if key in value:
                result.extend(flatten_values(value[key]))

        if result:
            return result

        for v in value.values():
            result.extend(flatten_values(v))

        return result

    return [str(value)]


def first_value(value):
    values = flatten_values(value)

    for item in values:
        item = clean_text(item)

        if item:
            return item

    return ""


def extract_preferred_text(value):
    """
    Tenta encontrar uma versão inglesa ou portuguesa quando
    o TED devolve títulos multilingues.
    """

    if value is None:
        return ""

    if isinstance(value, str):
        return clean_text(value)

    if isinstance(value, list):

        candidates = []

        for item in value:
            text = extract_preferred_text(item)

            if text:
                candidates.append(text)

        if not candidates:
            return ""

        # Preferir títulos que pareçam começar pela versão inglesa.
        for candidate in candidates:
            low = candidate.lower()

            if (
                "archaeological" in low
                or "archaeology" in low
                or "archaeological services" in low
                or "archaeological excavation" in low
            ):
                return candidate

        return candidates[0]

    if isinstance(value, dict):

        # Estruturas explicitamente linguísticas
        for key in ("en", "EN", "eng", "ENG", "pt", "PT", "por", "POR"):
            if key in value:
                result = extract_preferred_text(value[key])

                if result:
                    return result

        # Estruturas com language/lang
        language = str(
            value.get("language")
            or value.get("lang")
            or value.get("language-code")
            or ""
        ).lower()

        content = (
            value.get("value")
            or value.get("text")
            or value.get("content")
            or value.get("literal")
            or value.get("label")
        )

        if content is not None:
            result = extract_preferred_text(content)

            if result:
                return result

        # Última tentativa
        candidates = []

        for v in value.values():
            result = extract_preferred_text(v)

            if result:
                candidates.append(result)

        if candidates:
            return candidates[0]

        return ""

    return clean_text(value)


def get_field(notice, name):
    """
    Obtém um campo TED mesmo quando a API o devolve com pequenas
    diferenças de estrutura.
    """

    if not isinstance(notice, dict):
        return None

    if name in notice:
        return notice[name]

    # Algumas respostas podem envolver campos num objeto.
    for container_name in ("fields", "notice", "data"):
        container = notice.get(container_name)

        if isinstance(container, dict) and name in container:
            return container[name]

    return None


# ============================================================
# DATAS
# ============================================================

def parse_date(value):
    if not value:
        return None

    text = first_value(value)

    if not text:
        return None

    text = text[:10]

    for fmt in (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%Y%m%d",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass

    return None


def format_date_pt(value):
    parsed = parse_date(value)

    if not parsed:
        return ""

    return parsed.strftime("%d/%m/%Y")


def today():
    return date.today()


# ============================================================
# CLASSIFICAÇÃO
# ============================================================

ARCHAEOLOGY_TERMS = [
    "archaeolog",
    "arqueolog",
    "archéolog",
    "archäolog",
    "archeolog",
    "archeologisch",
    "archaeological",
    "archaeology",
    "archaeological services",
    "archaeological monitoring",
    "archaeological excavation",
    "archaeological research",
    "excavation",
    "fouilles",
    "fouille",
    "archäologische",
    "záchranný archeologický",
    "archaeologische",
    "archaeologischen",
]

HERITAGE_TERMS = [
    "cultural heritage",
    "heritage",
    "patrimoine",
    "patrimonio cultural",
    "patrimoine culturel",
    "kulturerbe",
    "historical heritage",
    "historic monument",
    "monument historique",
    "historic building",
    "archaeological heritage",
]

CONSTRUCTION_TERMS = [
    "construction",
    "infrastructure",
    "railway",
    "road",
    "highway",
    "bridge",
    "water",
    "sewer",
    "pipeline",
    "energy",
    "electricity",
    "substation",
    "development",
    "development project",
    "building works",
]


def normalise_for_search(text):
    text = clean_text(text)

    text = unicodedata.normalize("NFKD", text)

    text = "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )

    return text.lower()


def contains_any(text, terms):
    text = normalise_for_search(text)

    return any(
        normalise_for_search(term) in text
        for term in terms
    )


def classify_notice(title, cpv):
    combined = f"{title} {cpv}"

    if contains_any(combined, ARCHAEOLOGY_TERMS):
        return "Arqueologia direta"

    if contains_any(combined, HERITAGE_TERMS):
        return "Património cultural"

    if contains_any(combined, CONSTRUCTION_TERMS):
        return "Grande projeto / potencial subcontratação"

    return "Grande projeto / potencial subcontratação"


def calculate_score(title, cpv, category, deadline_date):
    score = 50

    text = f"{title} {cpv}"

    if contains_any(text, ARCHAEOLOGY_TERMS):
        score += 30

    if contains_any(cpv, ["71351914"]):
        score += 15

    if category == "Arqueologia direta":
        score += 5

    if deadline_date:
        remaining = (deadline_date - today()).days

        if remaining >= 0:
            if remaining <= 7:
                score += 10
            elif remaining <= 30:
                score += 7
            elif remaining <= 90:
                score += 4

    return min(score, 100)


# ============================================================
# ESTADO
# ============================================================

def calculate_status(deadline_date, publication_date):
    now = today()

    if deadline_date:
        if deadline_date < now:
            return "Prazo terminado"

        days = (deadline_date - now).days

        if days <= 7:
            return "Prazo termina em breve"

        if days <= 30:
            return "Prazo aberto — próximo"

        return "Prazo aberto"

    if publication_date:
        days_since = (now - publication_date).days

        if days_since <= 30:
            return "Publicação recente"

    return "Prazo não identificado"


# ============================================================
# TED
# ============================================================

def search_ted(query):
    """
    Pesquisa no TED Search API.

    A documentação oficial confirma que o endpoint é público
    e permite pesquisa de avisos publicados. 
    """

    query = (query or "archaeology").strip()

    if not query:
        query = "archaeology"

    # Pesquisa full text no TED.
    expert_query = f'FT~("{query}")'

    payload = {
        "query": expert_query,
        "fields": TED_FIELDS,
        "page": 1,
        "limit": 100,
        "scope": "ACTIVE",
        "checkQuerySyntax": False,
        "paginationMode": "PAGE_NUMBER",
    }

    response = requests.post(
        TED_URL,
        json=payload,
        timeout=REQUEST_TIMEOUT,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Arqueologia-Radar/1.0",
        },
    )

    response.raise_for_status()

    data = response.json()

    notices = data.get("notices", [])

    if not isinstance(notices, list):
        notices = []

    results = []

    for notice in notices:

        publication_number = clean_text(
            first_value(
                get_field(
                    notice,
                    "publication-number",
                )
            )
        )

        publication_date = parse_date(
            get_field(
                notice,
                "publication-date",
            )
        )

        title = extract_preferred_text(
            get_field(
                notice,
                "notice-title",
            )
        )

        buyer = extract_preferred_text(
            get_field(
                notice,
                "buyer-name",
            )
        )

        country = first_value(
            get_field(
                notice,
                "buyer-country",
            )
        )

        notice_type = first_value(
            get_field(
                notice,
                "notice-type",
            )
        )

        procedure_id = first_value(
            get_field(
                notice,
                "procedure-identifier",
            )
        )

        cpv_values = flatten_values(
            get_field(
                notice,
                "classification-cpv",
            )
        )

        cpv_values = [
            clean_text(x)
            for x in cpv_values
            if clean_text(x)
        ]

        # Retirar duplicados mantendo a ordem.
        cpv_values = list(dict.fromkeys(cpv_values))

        cpv = " | ".join(cpv_values)

        deadline_values = flatten_values(
            get_field(
                notice,
                "deadline-receipt-tender-date-lot",
            )
        )

        deadline_date = None

        for value in deadline_values:
            candidate = parse_date(value)

            if candidate:
                if deadline_date is None or candidate > deadline_date:
                    deadline_date = candidate

        # Título mínimo válido.
        if not title:
            title = "Concurso TED sem título disponível"

        # Evitar resultados que não tenham relação clara
        # com arqueologia quando a pesquisa é muito ampla.
        combined = f"{title} {cpv} {buyer}"

        if not contains_any(
            combined,
            ARCHAEOLOGY_TERMS + HERITAGE_TERMS,
        ):
            continue

        category = classify_notice(
            title,
            cpv,
        )

        score = calculate_score(
            title,
            cpv,
            category,
            deadline_date,
        )

        status = calculate_status(
            deadline_date,
            publication_date,
        )

        url = ""

        if publication_number:
            url = (
                "https://ted.europa.eu/en/notice/-/detail/"
                + publication_number
            )

        results.append(
            {
                "title": clean_text(title),
                "source": "TED",
                "date": format_date_pt(publication_date),
                "publication_date": (
                    publication_date.isoformat()
                    if publication_date
                    else ""
                ),
                "deadline": format_date_pt(deadline_date),
                "deadline_date": (
                    deadline_date.isoformat()
                    if deadline_date
                    else ""
                ),
                "status": status,
                "country": clean_text(country),
                "buyer": clean_text(buyer),
                "cpv": cpv,
                "notice_type": clean_text(notice_type),
                "publication_number": publication_number,
                "procedure_id": procedure_id,
                "category": category,
                "score": score,
                "url": url,
            }
        )

    return results, expert_query, data


# ============================================================
# DEDUPLICAÇÃO
# ============================================================

def deduplicate_results(results):
    unique = {}

    for item in results:

        key = (
            item.get("procedure_id")
            or item.get("publication_number")
            or (
                normalise_for_search(item.get("title", "")),
                normalise_for_search(item.get("buyer", "")),
            )
        )

        if key not in unique:
            unique[key] = item
            continue

        # Se existir duplicado, conservar o que tiver maior score.
        if item.get("score", 0) > unique[key].get("score", 0):
            unique[key] = item

    return list(unique.values())


# ============================================================
# ORDENAÇÃO
# ============================================================

def sort_results(results):
    def sort_key(item):

        status = item.get("status", "")

        # Primeiro os concursos com prazo aberto.
        if status == "Prazo termina em breve":
            priority = 0
        elif status == "Prazo aberto — próximo":
            priority = 1
        elif status == "Prazo aberto":
            priority = 2
        elif status == "Publicação recente":
            priority = 3
        elif status == "Prazo não identificado":
            priority = 4
        else:
            priority = 5

        deadline = item.get("deadline_date") or "9999-12-31"

        publication = item.get("publication_date") or "1900-01-01"

        return (
            priority,
            -int(item.get("score", 0)),
            deadline,
            publication,
        )

    return sorted(results, key=sort_key)


# ============================================================
# API
# ============================================================

@app.get("/api/health")
def health():
    return {
        "ok": True,
        "sources": len(SOURCES),
        "api_sources": sum(
            1
            for source in SOURCES
            if source.get("mode") == "api"
        ),
    }


@app.get("/api/sources")
def sources():
    return SOURCES


@app.get("/api/search")
def api_search(
    q: str = Query("archaeology"),
    region: str = Query(""),
    category: str = Query(""),
):
    searched_at = today().isoformat()

    diagnostics = []

    all_results = []

    # --------------------------------------------------------
    # TED
    # --------------------------------------------------------

    try:

        ted_results, ted_query, ted_data = search_ted(q)

        if region:
            # TED país/região não é suficiente para uma divisão
            # continental perfeita; mantemos o filtro simples
            # apenas quando explicitamente suportado no futuro.
            pass

        if category:
            ted_results = [
                item
                for item in ted_results
                if item.get("category") == category
            ]

        all_results.extend(ted_results)

        diagnostics.append(
            {
                "source": "TED",
                "ok": True,
                "count": len(ted_results),
                "total": ted_data.get(
                    "totalNoticeCount",
                    len(ted_results),
                ),
                "query": ted_query,
                "period_days": RESULTS_DAYS,
                "searched_at": searched_at,
            }
        )

    except Exception as exc:

        diagnostics.append(
            {
                "source": "TED",
                "ok": False,
                "count": 0,
                "error": str(exc),
            }
        )

    # --------------------------------------------------------
    # DEDUPLICAÇÃO E ORDENAÇÃO
    # --------------------------------------------------------

    all_results = deduplicate_results(
        all_results
    )

    all_results = sort_results(
        all_results
    )

    return JSONResponse(
        {
            "results": all_results,
            "diagnostics": diagnostics,
            "portal_count": len(SOURCES),
            "api_count": sum(
                1
                for source in SOURCES
                if source.get("mode") == "api"
            ),
            "searched_at": searched_at,
        }
    )


# ============================================================
# FICHEIROS ESTÁTICOS
# ============================================================

@app.get("/")
def index():
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
