from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from pathlib import Path
from datetime import date, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import re
import html
import unicodedata
import time


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Arqueologia Radar",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


PERIOD_DAYS = 365
PAGE_SIZE = 100
REQUEST_TIMEOUT = 30


TED_URL = "https://api.ted.europa.eu/v3/notices/search"

WORLD_BANK_URL = (
    "https://search.worldbank.org/api/v2/procnotices"
)


# ============================================================
# FONTES
# ============================================================

SOURCES = [
    {
        "name": "TED — Europa",
        "region": "Europa",
        "url": "https://ted.europa.eu/en/search",
        "mode": "api"
    },
    {
        "name": "World Bank Procurement",
        "region": "Global",
        "url": "https://projects.worldbank.org/en/projects-operations/procurement",
        "mode": "api"
    },

    {
        "name": "African Development Bank",
        "region": "África",
        "url": "https://www.afdb.org/en/documents/category/general-procurement-notices",
        "mode": "portal"
    },
    {
        "name": "AfDB Specific Procurement",
        "region": "África",
        "url": "https://www.afdb.org/en/documents/category/specific-procurement-notices",
        "mode": "portal"
    },
    {
        "name": "SAM.gov",
        "region": "Américas",
        "url": "https://sam.gov/opportunities",
        "mode": "portal"
    },
    {
        "name": "BASE Portugal",
        "region": "Portugal",
        "url": "https://www.base.gov.pt/",
        "mode": "portal"
    },
    {
        "name": "Contratación Pública España",
        "region": "Espanha",
        "url": "https://contrataciondelestado.es/",
        "mode": "portal"
    },
    {
        "name": "UN Development Business",
        "region": "Global",
        "url": "https://devbusiness.un.org/",
        "mode": "portal"
    },
    {
        "name": "UNGM",
        "region": "Global",
        "url": "https://www.ungm.org/Public/Notice",
        "mode": "portal"
    },
    {
        "name": "EBRD Procurement",
        "region": "Europa",
        "url": "https://www.ebrd.com/work-with-us/procurement.html",
        "mode": "portal"
    },
    {
        "name": "EIB Procurement",
        "region": "Europa",
        "url": "https://www.eib.org/en/projects/procurement/index.htm",
        "mode": "portal"
    },
    {
        "name": "Oman Tender Board",
        "region": "Médio Oriente",
        "url": "https://etendering.tenderboard.gov.om/",
        "mode": "portal"
    },
    {
        "name": "Saudi Etimad",
        "region": "Médio Oriente",
        "url": "https://portal.etimad.sa/",
        "mode": "portal"
    },
    {
        "name": "UAE Federal Procurement",
        "region": "Médio Oriente",
        "url": "https://procurement.gov.ae/",
        "mode": "portal"
    },
    {
        "name": "Qatar Monaqasat",
        "region": "Médio Oriente",
        "url": "https://monaqasat.mof.gov.qa/",
        "mode": "portal"
    },
    {
        "name": "Morocco Marchés Publics",
        "region": "África",
        "url": "https://www.marchespublics.gov.ma/",
        "mode": "portal"
    },
    {
        "name": "South Africa eTenders",
        "region": "África",
        "url": "https://www.etenders.gov.za/",
        "mode": "portal"
    },
    {
        "name": "Uganda eGP",
        "region": "África",
        "url": "https://egpuganda.go.ug/",
        "mode": "portal"
    },
    {
        "name": "Kenya PPIP",
        "region": "África",
        "url": "https://tenders.go.ke/",
        "mode": "portal"
    },
    {
        "name": "Tanzania NeST",
        "region": "África",
        "url": "https://nest.go.tz/",
        "mode": "portal"
    },
    {
        "name": "Mozambique UFSA",
        "region": "África",
        "url": "https://www.ufsa.gov.mz/",
        "mode": "portal"
    },
    {
        "name": "ChileCompra",
        "region": "Américas",
        "url": "https://www.mercadopublico.cl/",
        "mode": "portal"
    },
    {
        "name": "Colombia SECOP",
        "region": "Américas",
        "url": "https://www.colombiacompra.gov.co/secop",
        "mode": "portal"
    },
    {
        "name": "Brasil Compras.gov",
        "region": "Américas",
        "url": "https://www.gov.br/compras/",
        "mode": "portal"
    },
    {
        "name": "IDB Procurement",
        "region": "Américas",
        "url": "https://www.iadb.org/en/how-we-work/procurement",
        "mode": "portal"
    },
    {
        "name": "Asian Development Bank",
        "region": "Ásia-Pacífico",
        "url": "https://www.adb.org/work-with-us/procurement",
        "mode": "portal"
    },
    {
        "name": "Australia AusTender",
        "region": "Ásia-Pacífico",
        "url": "https://www.tenders.gov.au/",
        "mode": "portal"
    },
    {
        "name": "New Zealand GETS",
        "region": "Ásia-Pacífico",
        "url": "https://www.gets.govt.nz/",
        "mode": "portal"
    }
]


# ============================================================
# TERMOS DE ARQUEOLOGIA
# ============================================================

DEFAULT_TERMS = [
    "archaeology",
    "archaeological",
    "archaeological monitoring",
    "archaeological excavation",
    "archaeological services",
    "archaeological survey",
    "archaeological assessment",
    "archaeological investigation",
    "archaeological works",
    "excavation",
    "cultural heritage",
    "heritage",
    "historic environment",
    "chance finds",
    "heritage management",
    "unesco",
    "monument",
    "arqueologia",
    "património cultural",
    "patrimonio cultural"
]


ARCHAEOLOGY_CPVS = {
    "71351914",
    "71351910",
    "71351900",
    "71351720",
    "71351811",
    "45112450"
}


MAJOR_PROJECT_TERMS = [
    "railway",
    "rail",
    "road",
    "highway",
    "mine",
    "mining",
    "copper",
    "lithium",
    "oil",
    "gas",
    "lng",
    "pipeline",
    "airport",
    "port",
    "dam",
    "hydroelectric",
    "solar",
    "wind",
    "energy",
    "refinery",
    "corridor",
    "metro",
    "subway",
    "transmission line",
    "power line"
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
    "deadline-receipt-tender-date-lot",
    "deadline-receipt-request-date-lot",
    "description-proc",
    "description-lot"
]


# ============================================================
# MAPA DE PAÍSES
# ============================================================

COUNTRY_MAP = {

    # Europa
    "AT": "Áustria",
    "BE": "Bélgica",
    "BG": "Bulgária",
    "HR": "Croácia",
    "CY": "Chipre",
    "CZ": "Chéquia",
    "DK": "Dinamarca",
    "EE": "Estónia",
    "FI": "Finlândia",
    "FR": "França",
    "DE": "Alemanha",
    "GR": "Grécia",
    "HU": "Hungria",
    "IE": "Irlanda",
    "IT": "Itália",
    "LV": "Letónia",
    "LT": "Lituânia",
    "LU": "Luxemburgo",
    "MT": "Malta",
    "NL": "Países Baixos",
    "PL": "Polónia",
    "PT": "Portugal",
    "RO": "Roménia",
    "SK": "Eslováquia",
    "SI": "Eslovénia",
    "ES": "Espanha",
    "SE": "Suécia",
    "IS": "Islândia",
    "LI": "Liechtenstein",
    "NO": "Noruega",
    "CH": "Suíça",
    "UK": "Reino Unido",

    # África
    "ZA": "África do Sul",
    "DZ": "Argélia",
    "AO": "Angola",
    "BJ": "Benim",
    "BW": "Botswana",
    "BF": "Burkina Faso",
    "BI": "Burundi",
    "CM": "Camarões",
    "CV": "Cabo Verde",
    "CF": "República Centro-Africana",
    "TD": "Chade",
    "KM": "Comores",
    "CG": "Congo",
    "CD": "República Democrática do Congo",
    "CI": "Costa do Marfim",
    "DJ": "Djibouti",
    "EG": "Egito",
    "ER": "Eritreia",
    "SZ": "Eswatini",
    "ET": "Etiópia",
    "GA": "Gabão",
    "GM": "Gâmbia",
    "GH": "Gana",
    "GN": "Guiné",
    "GW": "Guiné-Bissau",
    "KE": "Quénia",
    "LS": "Lesoto",
    "LR": "Libéria",
    "LY": "Líbia",
    "MG": "Madagáscar",
    "MW": "Malawi",
    "ML": "Mali",
    "MR": "Mauritânia",
    "MU": "Maurícia",
    "MA": "Marrocos",
    "MZ": "Moçambique",
    "NA": "Namíbia",
    "NE": "Níger",
    "NG": "Nigéria",
    "RW": "Ruanda",
    "SN": "Senegal",
    "SL": "Serra Leoa",
    "SO": "Somália",
    "SD": "Sudão",
    "TZ": "Tanzânia",
    "TG": "Togo",
    "TN": "Tunísia",
    "UG": "Uganda",
    "ZM": "Zâmbia",
    "ZW": "Zimbabwe"
}


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def today_utc():
    return datetime.utcnow().date()


def cutoff_date():
    return today_utc() - timedelta(days=PERIOD_DAYS)


def flatten(value):
    """
    Converte valores TED, incluindo listas e dicionários
    multilingues, num texto simples.
    """

    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, list):
        values = []

        for item in value:
            text = flatten(item)

            if text:
                values.append(text)

        return " | ".join(values)

    if isinstance(value, dict):

        preferred = [
            "eng",
            "en",
            "por",
            "pt",
            "spa",
            "es",
            "fra",
            "fr"
        ]

        for key in preferred:
            if key in value:
                text = flatten(value[key])

                if text:
                    return text

        values = []

        for item in value.values():
            text = flatten(item)

            if text:
                values.append(text)

        return " | ".join(values)

    return str(value)


def clean_query(text):
    """
    Remove caracteres que possam interferir com a sintaxe
    da pesquisa TED.
    """

    text = str(text or "")

    text = re.sub(r'["\\]', " ", text)

    return text.strip()


def normalize_text(text):
    text = flatten(text)

    text = unicodedata.normalize(
        "NFKD",
        text
    )

    text = "".join(
        c for c in text
        if not unicodedata.combining(c)
    )

    return text.lower()


def extract_country(value):
    text = flatten(value)

    if not text:
        return ""

    upper = text.upper()

    # Primeiro procurar códigos ISO
    for code, country in COUNTRY_MAP.items():

        if re.search(
            rf"\b{re.escape(code)}\b",
            upper
        ):
            return country

    # Depois nomes
    normalized = normalize_text(text)

    for country in COUNTRY_MAP.values():

        if normalize_text(country) in normalized:
            return country

    return text


def extract_cpvs(value):
    text = flatten(value)

    found = re.findall(
        r"\b\d{8}\b",
        text
    )

    return sorted(set(found))


def extract_deadline(notice):
    """
    Tenta encontrar a data limite para apresentação
    de propostas.
    """

    values = [
        notice.get(
            "deadline-receipt-tender-date-lot"
        ),
        notice.get(
            "deadline-receipt-request-date-lot"
        )
    ]

    for value in values:

        text = flatten(value)

        if text:
            return text

    return ""


def parse_date(value):

    text = flatten(value).strip()

    if not text:
        return None

    formats = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S%z",
        "%d/%m/%Y",
        "%Y%m%d"
    ]

    for fmt in formats:

        try:
            return datetime.strptime(
                text[:26],
                fmt
            ).date()

        except Exception:
            pass

    match = re.search(
        r"(20\d{2})[-/](\d{2})[-/](\d{2})",
        text
    )

    if match:

        try:
            return date(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3))
            )

        except Exception:
            pass

    return None


def classify_result(text):

    normalized = normalize_text(text)

    archaeology_hits = 0
    major_hits = 0

    for term in DEFAULT_TERMS:

        if normalize_text(term) in normalized:
            archaeology_hits += 1

    for term in MAJOR_PROJECT_TERMS:

        if normalize_text(term) in normalized:
            major_hits += 1

    # Arqueologia diretamente identificada
    if archaeology_hits >= 1:

        score = min(
            100,
            60 + archaeology_hits * 5 + major_hits * 2
        )

        return (
            "Arqueologia direta",
            score
        )

    # Grande projeto com potencial componente arqueológico
    if major_hits:

        score = min(
            100,
            25 + major_hits * 4
        )

        return (
            "Grande projeto / potencial subcontratação",
            score
        )

    return (
        "Outro",
        0
    )


# ============================================================
# CONSTRUÇÃO DA PESQUISA TED
# ============================================================

def build_ted_query(term):

    term = clean_query(term)

    if not term:
        term = "archaeology"

    # A pesquisa principal usa vários termos arqueológicos.
    # O SORT BY permite que os resultados mais recentes
    # apareçam primeiro.
    if term.lower() in {
        "archaeology",
        "arqueologia"
    }:

        clauses = []

        for item in DEFAULT_TERMS[:12]:

            cleaned = clean_query(item)

            if cleaned:

                clauses.append(
                    f'FT~"{cleaned}"'
                )

        return (
            "("
            + " OR ".join(clauses)
            + ") SORT BY publication-date DESC"
        )

    return (
        f'FT~"{term}" '
        f'SORT BY publication-date DESC'
    )


# ============================================================
# CONVERSÃO DE AVISO TED
# ============================================================

def notice_to_result(notice):

    publication_number = flatten(
        notice.get("publication-number")
    )

    publication_date = flatten(
        notice.get("publication-date")
    )

    pub_date = parse_date(
        publication_date
    )

    # Não aceitar avisos demasiado antigos
    if pub_date and pub_date < cutoff_date():
        return None

    title = (
        flatten(
            notice.get("notice-title")
        )
        or "Concurso TED"
    )

    buyer = flatten(
        notice.get("buyer-name")
    )

    country_raw = flatten(
        notice.get("buyer-country")
    )

    country = extract_country(
        country_raw
    )

    cpv_raw = flatten(
        notice.get("classification-cpv")
    )

    cpvs = extract_cpvs(
        cpv_raw
    )

    deadline = extract_deadline(
        notice
    )

    notice_type = flatten(
        notice.get("notice-type")
    )

    description_proc = flatten(
        notice.get("description-proc")
    )

    description_lot = flatten(
        notice.get("description-lot")
    )

    searchable_text = " ".join(
        [
            title,
            buyer,
            country,
            cpv_raw,
            notice_type,
            description_proc,
            description_lot
        ]
    )

    category, score = classify_result(
        searchable_text
    )

    # Se houver CPV arqueológico, reforçar classificação
    if any(
        cpv in ARCHAEOLOGY_CPVS
        for cpv in cpvs
    ):

        category = "Arqueologia direta"

        score = max(
            score,
            75
        )

    if publication_number:

        url = (
            "https://ted.europa.eu/en/notice/"
            f"-/detail/{publication_number}"
        )

    else:

        url = (
            "https://ted.europa.eu/en/search"
        )

    return {
        "title": title,
        "source": "TED",
        "date": publication_date,
        "deadline": deadline,
        "country": country,
        "buyer": buyer,
        "cpv": ", ".join(cpvs),
        "notice_type": notice_type,
        "url": url,
        "category": category,
        "score": score
    }


# ============================================================
# TED — API
# ============================================================

def query_ted(term):

    diagnostics = {
        "source": f"TED — {term}",
        "ok": False,
        "count": 0,
        "query": "",
        "raw_count": 0,
        "ted_total": None,
        "ted_response_keys": [],
        "sample": ""
    }

    query = build_ted_query(
        term
    )

    diagnostics["query"] = query

    payload = {
        "query": query,
        "fields": TED_FIELDS,
        "page": 1,
        "limit": PAGE_SIZE,
        "scope": "ACTIVE",
        "checkQuerySyntax": False,
        "paginationMode": "PAGE_NUMBER",
        "onlyLatestVersions": True
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Arqueologia-Radar/1.0"
    }

    last_error = None

    for attempt in range(3):

        try:

            response = requests.post(
                TED_URL,
                json=payload,
                headers=headers,
                timeout=REQUEST_TIMEOUT
            )

            if response.status_code in (
                429,
                500,
                502,
                503,
                504
            ):

                if attempt < 2:

                    time.sleep(
                        2 ** attempt
                    )

                    continue

            response.raise_for_status()

            data = response.json()

            break

        except Exception as exc:

            last_error = exc

            if attempt < 2:

                time.sleep(
                    2 ** attempt
                )

            else:

                diagnostics["error"] = str(
                    last_error
                )

                return [], diagnostics

    diagnostics["ted_response_keys"] = (
        list(data.keys())
        if isinstance(data, dict)
        else [str(type(data))]
    )

    if isinstance(data, dict):

        diagnostics["ted_total"] = (
            data.get(
                "totalNoticeCount"
            )
        )

    notices = []

    if isinstance(data, dict):

        for key in (
            "notices",
            "results",
            "data"
        ):

            value = data.get(
                key
            )

            if isinstance(
                value,
                list
            ):

                notices = value

                break

            if isinstance(
                value,
                dict
            ):

                for subkey in (
                    "notices",
                    "results",
                    "data",
                    "rows"
                ):

                    subvalue = value.get(
                        subkey
                    )

                    if isinstance(
                        subvalue,
                        list
                    ):

                        notices = subvalue

                        break

                if notices:
                    break

    elif isinstance(
        data,
        list
    ):

        notices = data

    diagnostics["raw_count"] = len(
        notices
    )

    if notices:

        diagnostics["sample"] = str(
            notices[0]
        )[:1200]

    else:

        diagnostics["sample"] = "SEM AVISOS"

    results = []

    for notice in notices:

        try:

            result = notice_to_result(
                notice
            )

            if result:

                results.append(
                    result
                )

        except Exception:

            continue

    diagnostics["count"] = len(
        results
    )

    diagnostics["ok"] = True

    return (
        results,
        diagnostics
    )


# ============================================================
# WORLD BANK
# ============================================================

def query_world_bank(term):

    diagnostics = {
        "source": f"World Bank — {term}",
        "ok": False,
        "count": 0,
        "query": term,
        "raw_count": 0
    }

    params = {
        "format": "json",
        "qterm": term,
        "rows": 100,
        "os": 0,
        "fl": (
            "id,"
            "procurement_notice_id,"
            "project_id,"
            "project_name,"
            "project_ctry_name,"
            "submission_deadline_date,"
            "notice_title,"
            "notice_type,"
            "url"
        ),
        "srt": "submission_deadline_date",
        "order": "desc",
        "apilang": "en",
        "srce": "both"
    }

    try:

        response = requests.get(
            WORLD_BANK_URL,
            params=params,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

    except Exception as exc:

        diagnostics["error"] = str(
            exc
        )

        return [], diagnostics

    notices = []

    if isinstance(data, dict):

        for key in (
            "procnotices",
            "notices",
            "results",
            "data"
        ):

            value = data.get(
                key
            )

            if isinstance(
                value,
                list
            ):

                notices = value

                break

            if isinstance(
                value,
                dict
            ):

                for subkey in (
                    "procnotices",
                    "notices",
                    "results",
                    "data"
                ):

                    subvalue = value.get(
                        subkey
                    )

                    if isinstance(
                        subvalue,
                        list
                    ):

                        notices = subvalue

                        break

                if notices:
                    break

    diagnostics["raw_count"] = len(
        notices
    )

    results = []

    for notice in notices:

        if not isinstance(
            notice,
            dict
        ):

            continue

        title = (
            flatten(
                notice.get(
                    "notice_title"
                )
            )
            or flatten(
                notice.get(
                    "procurement_notice_title"
                )
            )
            or flatten(
                notice.get(
                    "project_name"
                )
            )
            or "World Bank Procurement"
        )

        project_name = flatten(
            notice.get(
                "project_name"
            )
        )

        country = flatten(
            notice.get(
                "project_ctry_name"
            )
        )

        deadline = flatten(
            notice.get(
                "submission_deadline_date"
            )
        )

        notice_type = flatten(
            notice.get(
                "notice_type"
            )
        )

        project_id = flatten(
            notice.get(
                "project_id"
            )
        )

        identifier = (
            flatten(
                notice.get("id")
            )
            or flatten(
                notice.get(
                    "procurement_notice_id"
                )
            )
        )

        searchable_text = " ".join(
            [
                title,
                project_name,
                country,
                notice_type,
                term
            ]
        )

        category, score = classify_result(
            searchable_text
        )

        url = flatten(
            notice.get("url")
        )

        if not url:

            if identifier:

                url = (
                    "https://projects.worldbank.org/"
                    "en/projects-operations/"
                    f"procurement-detail/{identifier}"
                )

            else:

                url = (
                    "https://projects.worldbank.org/"
                    "en/projects-operations/procurement"
                )

        results.append(
            {
                "title": title,
                "source": "World Bank",
                "date": "",
                "deadline": deadline,
                "country": country,
                "buyer": "World Bank",
                "cpv": "",
                "notice_type": notice_type,
                "url": url,
                "category": category,
                "score": score,
                "project_id": project_id
            }
        )

    diagnostics["count"] = len(
        results
    )

    diagnostics["ok"] = True

    return (
        results,
        diagnostics
    )


# ============================================================
# DEDUPLICAÇÃO
# ============================================================

def deduplicate_results(results):

    unique = {}

    for result in results:

        key = (
            normalize_text(
                result.get("title", "")
            ),
            normalize_text(
                result.get("source", "")
            ),
            normalize_text(
                result.get("country", "")
            )
        )

        if key not in unique:

            unique[key] = result

        else:

            old = unique[key]

            if result.get("score", 0) > old.get(
                "score",
                0
            ):

                unique[key] = result

    return list(
        unique.values()
    )


# ============================================================
# FILTRO REGIONAL
# ============================================================

def region_matches(result, region):

    if not region:
        return True

    country = normalize_text(
        result.get("country", "")
    )

    if region == "Europa":

        european_names = [
            normalize_text(v)
            for v in COUNTRY_MAP.values()
        ]

        return any(
            name in country
            for name in european_names
        )

    if region == "África":

        african_terms = [
            "africa",
            "angola",
            "mocambique",
            "mozambique",
            "quenia",
            "kenya",
            "tanzania",
            "uganda",
            "marrocos",
            "morocco",
            "africa do sul",
            "south africa",
            "nigeria",
            "ghana",
            "senegal",
            "zambia",
            "zimbabwe"
        ]

        return any(
            term in country
            for term in african_terms
        )

    if region == "Américas":

        american_terms = [
            "america",
            "brazil",
            "brasil",
            "chile",
            "colombia",
            "argentina",
            "peru",
            "mexico",
            "canada",
            "united states",
            "estados unidos"
        ]

        return any(
            term in country
            for term in american_terms
        )

    if region == "Portugal":

        return (
            "portugal" in country
        )

    if region == "Espanha":

        return (
            "espanha" in country
            or "spain" in country
        )

    if region == "Médio Oriente":

        terms = [
            "oman",
            "saudi",
            "arabia",
            "uae",
            "emirates",
            "qatar"
        ]

        return any(
            term in country
            for term in terms
        )

    if region == "Ásia-Pacífico":

        terms = [
            "australia",
            "new zealand",
            "japan",
            "china",
            "india",
            "asia"
        ]

        return any(
            term in country
            for term in terms
        )

    return True


# ============================================================
# ENDPOINT SOURCES
# ============================================================

@app.get("/api/sources")
def get_sources():

    return {
        "sources": SOURCES,
        "count": len(SOURCES),
        "api_sources": sum(
            1
            for source in SOURCES
            if source["mode"] == "api"
        ),
        "portal_sources": sum(
            1
            for source in SOURCES
            if source["mode"] == "portal"
        )
    }


# ============================================================
# ENDPOINT SEARCH
# ============================================================

@app.get("/api/search")
def search(
    q: str = Query(
        "archaeology"
    ),
    region: str = "",
    category: str = ""
):

    results = []
    diagnostics = []

    # --------------------------------------------------------
    # TERMOS TED
    # --------------------------------------------------------

    search_terms = [
        "archaeological excavation",
        "archaeological monitoring",
        "archaeological services",
        "archaeology",
        "archaeological",
        "excavation",
        "cultural heritage",
        "heritage",
        "archaeological survey",
        "archaeological assessment"
    ]

    # Se o utilizador pesquisar algo específico,
    # colocamos esse termo no início.
    if q:

        user_query = clean_query(
            q
        )

        if user_query.lower() not in [
            x.lower()
            for x in search_terms
        ]:

            search_terms.insert(
                0,
                user_query
            )

    # Evitar duplicados
    clean_terms = []

    for term in search_terms:

        if term.lower() not in [
            x.lower()
            for x in clean_terms
        ]:

            clean_terms.append(
                term
            )

    # --------------------------------------------------------
    # WORLD BANK
    # --------------------------------------------------------

    world_bank_terms = [
        "archaeology",
        "archaeological",
        "cultural heritage",
        "archaeological excavation"
    ]

    if q:

        user_query = clean_query(
            q
        )

        if user_query.lower() not in [
            x.lower()
            for x in world_bank_terms
        ]:

            world_bank_terms.insert(
                0,
                user_query
            )

    # --------------------------------------------------------
    # EXECUÇÃO EM PARALELO
    # --------------------------------------------------------

    tasks = []

    with ThreadPoolExecutor(
        max_workers=10
    ) as executor:

        for term in clean_terms:

            tasks.append(
                executor.submit(
                    query_ted,
                    term
                )
            )

        for term in world_bank_terms:

            tasks.append(
                executor.submit(
                    query_world_bank,
                    term
                )
            )

        for future in as_completed(
            tasks
        ):

            try:

                task_results, status = (
                    future.result()
                )

                results.extend(
                    task_results
                )

                diagnostics.append(
                    status
                )

            except Exception as exc:

                diagnostics.append(
                    {
                        "source": "API",
                        "ok": False,
                        "count": 0,
                        "error": str(exc)
                    }
                )

    # --------------------------------------------------------
    # DEDUPLICAÇÃO
    # --------------------------------------------------------

    results = deduplicate_results(
        results
    )

    # --------------------------------------------------------
    # FILTRO DE REGIÃO
    # --------------------------------------------------------

    if region:

        results = [
            result
            for result in results
            if region_matches(
                result,
                region
            )
        ]

    # --------------------------------------------------------
    # FILTRO DE CATEGORIA
    # --------------------------------------------------------

    if category:

        results = [
            result
            for result in results
            if result.get(
                "category"
            ) == category
        ]

    # --------------------------------------------------------
    # REMOVER DEADLINES EXPIRADOS
    # --------------------------------------------------------

    filtered_results = []

    today = today_utc()

    for result in results:

        deadline_text = result.get(
            "deadline",
            ""
        )

        deadline_date = parse_date(
            deadline_text
        )

        if deadline_date:

            if deadline_date < today:

                continue

        filtered_results.append(
            result
        )

    results = filtered_results

    # --------------------------------------------------------
    # ORDENAÇÃO
    # --------------------------------------------------------

    def result_date(result):

        parsed = parse_date(
            result.get(
                "date",
                ""
            )
        )

        if parsed:

            return parsed

        return date.min

    results.sort(
        key=lambda item: (
            result_date(item),
            item.get(
                "score",
                0
            )
        ),
        reverse=True
    )

    # --------------------------------------------------------
    # CONTADORES
    # --------------------------------------------------------

    api_count = sum(
        1
        for source in SOURCES
        if source["mode"] == "api"
    )

    portal_count = sum(
        1
        for source in SOURCES
        if source["mode"] == "portal"
        and (
            not region
            or source["region"] in (
                region,
                "Global"
            )
        )
    )

    return {
        "ok": True,
        "query": q,
        "region": region,
        "category": category,
        "results": results,
        "count": len(results),
        "sources": len(SOURCES),
        "api_sources": api_count,
        "portal_count": portal_count,
        "diagnostics": diagnostics,
        "searched_at": today_utc().isoformat()
    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health():

    return {
        "ok": True,
        "sources": len(SOURCES),
        "api_sources": sum(
            1
            for source in SOURCES
            if source["mode"] == "api"
        ),
        "portal_sources": sum(
            1
            for source in SOURCES
            if source["mode"] == "portal"
        ),
        "period_days": PERIOD_DAYS
    }


# ============================================================
# FICHEIROS DA APLICAÇÃO
# ============================================================

@app.get("/")
def home():

    return FileResponse(
        BASE_DIR / "index.html"
    )


@app.get("/app.js")
def javascript():

    return FileResponse(
        BASE_DIR / "app.js",
        media_type="application/javascript"
    )


@app.get("/manifest.json")
def manifest():

    return FileResponse(
        BASE_DIR / "manifest.json",
        media_type="application/manifest+json"
    )
