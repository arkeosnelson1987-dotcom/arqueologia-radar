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


# ============================================================
# FONTES API
# ============================================================

TED_URL = "https://api.ted.europa.eu/v3/notices/search"

WORLD_BANK_URL = "https://search.worldbank.org/api/v2/procnotices"


# ============================================================
# FONTES DO RADAR
# ============================================================

SOURCES = [

    # EUROPA
    {
        "name": "TED",
        "region": "Europa",
        "mode": "api",
        "url": "https://ted.europa.eu/"
    },

    {
        "name": "BASE Portugal",
        "region": "Portugal",
        "mode": "portal",
        "url": "https://www.base.gov.pt/"
    },

    {
        "name": "Contratación Pública España",
        "region": "Espanha",
        "mode": "portal",
        "url": "https://contrataciondelestado.es/"
    },

    # GLOBAL
    {
        "name": "World Bank Procurement",
        "region": "Global",
        "mode": "api",
        "url": "https://projects.worldbank.org/en/projects-operations/procurement"
    },

    {
        "name": "UNDB",
        "region": "Global",
        "mode": "portal",
        "url": "https://devbusiness.un.org/"
    },

    {
        "name": "UNGM",
        "region": "Global",
        "mode": "portal",
        "url": "https://www.ungm.org/"
    },

    {
        "name": "EBRD",
        "region": "Global",
        "mode": "portal",
        "url": "https://www.ebrd.com/"
    },

    {
        "name": "EIB",
        "region": "Global",
        "mode": "portal",
        "url": "https://www.eib.org/"
    },

    # ÁFRICA
    {
        "name": "African Development Bank",
        "region": "África",
        "mode": "portal",
        "url": "https://www.afdb.org/"
    },

    {
        "name": "AfDB Procurement Notices",
        "region": "África",
        "mode": "portal",
        "url": "https://www.afdb.org/en/projects-and-operations/procurement"
    },

    {
        "name": "South Africa",
        "region": "África",
        "mode": "portal",
        "url": "https://www.etenders.gov.za/"
    },

    {
        "name": "Uganda",
        "region": "África",
        "mode": "portal",
        "url": "https://www.ppda.go.ug/"
    },

    {
        "name": "Kenya",
        "region": "África",
        "mode": "portal",
        "url": "https://www.tenders.go.ke/"
    },

    {
        "name": "Tanzania",
        "region": "África",
        "mode": "portal",
        "url": "https://www.ppra.go.tz/"
    },

    {
        "name": "Mozambique",
        "region": "África",
        "mode": "portal",
        "url": "https://www.ufsa.gov.mz/"
    },

    {
        "name": "Morocco",
        "region": "África",
        "mode": "portal",
        "url": "https://www.marchespublics.gov.ma/"
    },

    # MÉDIO ORIENTE
    {
        "name": "Oman",
        "region": "Médio Oriente",
        "mode": "portal",
        "url": "https://etendering.tenderboard.gov.om/"
    },

    {
        "name": "Saudi Arabia Etimad",
        "region": "Médio Oriente",
        "mode": "portal",
        "url": "https://tenders.etimad.sa/"
    },

    {
        "name": "UAE",
        "region": "Médio Oriente",
        "mode": "portal",
        "url": "https://www.mof.gov.ae/"
    },

    {
        "name": "Qatar",
        "region": "Médio Oriente",
        "mode": "portal",
        "url": "https://monaqasat.mof.gov.qa/"
    },

    # AMÉRICAS
    {
        "name": "SAM.gov",
        "region": "Américas",
        "mode": "portal",
        "url": "https://sam.gov/"
    },

    {
        "name": "ChileCompra",
        "region": "Américas",
        "mode": "portal",
        "url": "https://www.mercadopublico.cl/"
    },

    {
        "name": "SECOP Colombia",
        "region": "Américas",
        "mode": "portal",
        "url": "https://www.colombiacompra.gov.co/"
    },

    {
        "name": "Compras Brasil",
        "region": "Américas",
        "mode": "portal",
        "url": "https://www.gov.br/compras/"
    },

    {
        "name": "IDB",
        "region": "Américas",
        "mode": "portal",
        "url": "https://www.iadb.org/"
    },

    # ÁSIA
    {
        "name": "Asian Development Bank",
        "region": "Ásia",
        "mode": "portal",
        "url": "https://www.adb.org/"
    },

    # OCEANIA
    {
        "name": "Australia",
        "region": "Oceânia",
        "mode": "portal",
        "url": "https://www.tenders.gov.au/"
    },

    {
        "name": "New Zealand",
        "region": "Oceânia",
        "mode": "portal",
        "url": "https://www.gets.govt.nz/"
    },

    # OUTROS
    {
        "name": "Global Procurement",
        "region": "Global",
        "mode": "portal",
        "url": "https://www.devbusiness.un.org/"
    }

]


# ============================================================
# TERMOS AUTOMÁTICOS DE ARQUEOLOGIA
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


# ============================================================
# CPV DE ARQUEOLOGIA
# ============================================================

ARCHAEOLOGY_CPVS = {

    "71351914",
    "71351910",
    "71351900",
    "71351720",
    "71351811",
    "45112450"

}


# ============================================================
# GRANDES PROJETOS
# ============================================================

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
    "deadline-date-lot",
    "deadline-receipt-request",
    "deadline-receipt-tender",
    "description-proc",
    "description-lot"

]


# ============================================================
# MAPA DE PAÍSES
# ============================================================

COUNTRY_NAMES = {

    "PT": "Portugal",
    "ES": "Espanha",
    "FR": "França",
    "DE": "Alemanha",
    "IT": "Itália",
    "NL": "Países Baixos",
    "BE": "Bélgica",
    "IE": "Irlanda",
    "AT": "Áustria",
    "PL": "Polónia",
    "CZ": "Chéquia",
    "SK": "Eslováquia",
    "HU": "Hungria",
    "RO": "Roménia",
    "BG": "Bulgária",
    "GR": "Grécia",
    "SE": "Suécia",
    "FI": "Finlândia",
    "DK": "Dinamarca",
    "NO": "Noruega",
    "CH": "Suíça",
    "UK": "Reino Unido",

    "MA": "Marrocos",
    "DZ": "Argélia",
    "TN": "Tunísia",
    "EG": "Egito",
    "ZA": "África do Sul",
    "MZ": "Moçambique",
    "AO": "Angola",
    "KE": "Quénia",
    "UG": "Uganda",
    "TZ": "Tanzânia",

    "US": "Estados Unidos",
    "CA": "Canadá",
    "MX": "México",
    "BR": "Brasil",
    "CL": "Chile",
    "CO": "Colômbia",
    "AR": "Argentina",

    "AU": "Austrália",
    "NZ": "Nova Zelândia",

    "SA": "Arábia Saudita",
    "AE": "Emirados Árabes Unidos",
    "QA": "Qatar",
    "OM": "Omã",

    "IN": "Índia",
    "CN": "China",
    "JP": "Japão",
    "KR": "Coreia do Sul"

}


COUNTRY_NAMES_3 = {

    "PRT": "Portugal",
    "ESP": "Espanha",
    "FRA": "França",
    "DEU": "Alemanha",
    "ITA": "Itália",
    "NLD": "Países Baixos",
    "BEL": "Bélgica",
    "IRL": "Irlanda",
    "AUT": "Áustria",
    "POL": "Polónia",
    "CZE": "Chéquia",
    "SVK": "Eslováquia",
    "HUN": "Hungria",
    "ROU": "Roménia",
    "BGR": "Bulgária",
    "GRC": "Grécia",
    "SWE": "Suécia",
    "FIN": "Finlândia",
    "DNK": "Dinamarca",
    "NOR": "Noruega",
    "CHE": "Suíça",
    "GBR": "Reino Unido",

    "MAR": "Marrocos",
    "DZA": "Argélia",
    "TUN": "Tunísia",
    "EGY": "Egito",
    "ZAF": "África do Sul",
    "MOZ": "Moçambique",
    "AGO": "Angola",
    "KEN": "Quénia",
    "UGA": "Uganda",
    "TZA": "Tanzânia",

    "USA": "Estados Unidos",
    "CAN": "Canadá",
    "MEX": "México",
    "BRA": "Brasil",
    "CHL": "Chile",
    "COL": "Colômbia",
    "ARG": "Argentina",

    "AUS": "Austrália",
    "NZL": "Nova Zelândia",

    "SAU": "Arábia Saudita",
    "ARE": "Emirados Árabes Unidos",
    "QAT": "Qatar",
    "OMN": "Omã",

    "IND": "Índia",
    "CHN": "China",
    "JPN": "Japão",
    "KOR": "Coreia do Sul"

}


# ============================================================
# FUNÇÕES GERAIS
# ============================================================

def today_utc():

    return datetime.utcnow().date()


def cutoff_date():

    return today_utc() - timedelta(
        days=PERIOD_DAYS
    )


def flatten(value):

    if value is None:
        return ""

    if isinstance(value, list):

        return " ".join(
            flatten(item)
            for item in value
        )

    if isinstance(value, dict):

        return " ".join(
            flatten(item)
            for item in value.values()
        )

    return str(value)


def clean_query(value):

    if value is None:
        return ""

    value = str(value).strip()

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value


def normalize_text(value):

    value = flatten(value)

    value = html.unescape(value)

    value = unicodedata.normalize(
        "NFKD",
        value
    )

    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )

    return value.lower()


def parse_date(value):

    if not value:
        return None

    if isinstance(value, date):
        return value

    value = str(value).strip()

    if not value:
        return None

    # ISO
    try:

        return datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00"
            )
        ).date()

    except Exception:
        pass

    # YYYY-MM-DD
    try:

        return datetime.strptime(
            value[:10],
            "%Y-%m-%d"
        ).date()

    except Exception:
        pass

    # DD/MM/YYYY
    try:

        return datetime.strptime(
            value[:10],
            "%d/%m/%Y"
        ).date()

    except Exception:
        pass

    return None


# ============================================================
# PAÍS
# ============================================================

def extract_country(notice):

    value = (
        notice.get("buyer-country")
        or notice.get("buyerCountry")
        or notice.get("country")
        or ""
    )

    value = flatten(value).strip()

    if not value:
        return ""

    upper = value.upper()

    if upper in COUNTRY_NAMES_3:
        return COUNTRY_NAMES_3[upper]

    if upper in COUNTRY_NAMES:
        return COUNTRY_NAMES[upper]

    return value


# ============================================================
# CPV
# ============================================================

def extract_cpvs(notice):

    values = []

    possible_fields = [

        notice.get(
            "classification-cpv"
        ),

        notice.get(
            "classificationCpv"
        ),

        notice.get(
            "cpv"
        ),

        notice.get(
            "cpvs"
        )

    ]

    for value in possible_fields:

        if not value:
            continue

        if isinstance(
            value,
            list
        ):

            values.extend(
                flatten(item)
                for item in value
            )

        else:

            values.append(
                flatten(value)
            )

    result = []

    for value in values:

        matches = re.findall(
            r"\d{8}",
            value
        )

        result.extend(
            matches
        )

    return list(
        dict.fromkeys(
            result
        )
    )


# ============================================================
# DEADLINE
# ============================================================

def extract_deadline(notice):

    possible_fields = [

        "deadline-date-lot",
        "deadline-receipt-request",
        "deadline-receipt-tender",
        "deadlineDateLot",
        "deadlineReceiptRequest",
        "deadlineReceiptTender"

    ]

    for field in possible_fields:

        value = notice.get(
            field
        )

        if value:

            if isinstance(
                value,
                list
            ):

                value = value[0]

            return flatten(
                value
            )

    return ""


# ============================================================
# CLASSIFICAÇÃO
# ============================================================

def classify_result(
    title,
    description,
    cpvs
):

    text = normalize_text(
        " ".join(
            [
                flatten(title),
                flatten(description)
            ]
        )
    )

    archaeology_hits = 0

    for term in DEFAULT_TERMS:

        if normalize_text(term) in text:

            archaeology_hits += 1

    major_hits = 0

    for term in MAJOR_PROJECT_TERMS:

        if normalize_text(term) in text:

            major_hits += 1

    cpv_archaeology = any(
        cpv in ARCHAEOLOGY_CPVS
        for cpv in cpvs
    )

    if archaeology_hits >= 1:

        score = min(
            100,
            60
            + archaeology_hits * 5
            + major_hits * 2
        )

        return (
            "Arqueologia direta",
            score
        )

    if cpv_archaeology:

        return (
            "Arqueologia direta",
            80
        )

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
        10
    )


# ============================================================
# QUERY TED
# ============================================================
def build_ted_query(
    term,
    country_code=None
):

    term = clean_query(term)

    if not term:
        return ""

    # ========================================================
    # MODO AUTOMÁTICO
    # ========================================================

    if term.lower() in (
        "archaeology",
        "arqueologia"
    ):

        parts = []

        for item in DEFAULT_TERMS[:12]:

            item = clean_query(item)

            parts.append(
                f'FT~"{item}"'
            )

        query = " OR ".join(parts)

    else:

        # ====================================================
        # PESQUISA DIRETA
        # ====================================================

        # Retirar aspas introduzidas pelo utilizador
        term = term.replace(
            '"',
            ''
        )

        term = term.replace(
            "'",
            ''
        )

        # O TED funciona melhor com a expressão
        # entre aspas.
        query = f'FT~"{term}"'

    # ========================================================
    # PAÍS
    # ========================================================

    if country_code:

        query += (
            f" AND buyer-country={country_code}"
        )

    # ========================================================
    # ORDENAÇÃO
    # ========================================================

    query += (
        " SORT BY publication-date DESC"
    )

    return query


# ============================================================
# CONVERTER AVISO TED EM RESULTADO
# ============================================================

def notice_to_result(
    notice
):

    publication_date = (
        notice.get(
            "publication-date"
        )
        or notice.get(
            "publicationDate"
        )
        or ""
    )

    parsed_date = parse_date(
        publication_date
    )

    if (
        parsed_date
        and parsed_date < cutoff_date()
    ):

        return None

    title = (
        notice.get(
            "notice-title"
        )
        or notice.get(
            "noticeTitle"
        )
        or ""
    )

    buyer = (
        notice.get(
            "buyer-name"
        )
        or notice.get(
            "buyerName"
        )
        or ""
    )

    country = extract_country(
        notice
    )

    cpvs = extract_cpvs(
        notice
    )

    description = " ".join(
        [
            flatten(
                notice.get(
                    "description-proc",
                    ""
                )
            ),
            flatten(
                notice.get(
                    "description-lot",
                    ""
                )
            )
        ]
    )

    category, score = classify_result(
        title,
        description,
        cpvs
    )

    if (
        any(
            cpv in ARCHAEOLOGY_CPVS
            for cpv in cpvs
        )
        and score < 75
    ):

        category = (
            "Arqueologia direta"
        )

        score = 75

    publication_number = (
        notice.get(
            "publication-number"
        )
        or notice.get(
            "publicationNumber"
        )
        or ""
    )

    deadline = extract_deadline(
        notice
    )

    url = ""

    if publication_number:

        url = (
            "https://ted.europa.eu/"
            "en/notice/-/detail/"
            + str(publication_number)
        )

    return {

        "title": flatten(
            title
        ),

        "buyer": flatten(
            buyer
        ),

        "country": country,

        "date": flatten(
            publication_date
        ),

        "deadline": flatten(
            deadline
        ),

        "cpv": cpvs,

        "category": category,

        "score": score,

        "source": "TED",

        "url": url,

        "publication_number":
            flatten(
                publication_number
            ),

        "description":
            flatten(
                description
            )

    }


# ============================================================
# PESQUISA TED
# ============================================================
def query_ted(
    term
):

    query = build_ted_query(
        term
    )

    payload = {

        "query": query,

        "fields": TED_FIELDS,

        "page": 1,

        "limit": PAGE_SIZE,

        "scope": "ACTIVE",

        "checkQuerySyntax": False,

        "paginationMode":
            "PAGE_NUMBER",

        "onlyLatestVersions":
            True

    }

    last_error = None

    for attempt in range(3):

        try:

            response = requests.post(
                TED_URL,
                json=payload,
                timeout=REQUEST_TIMEOUT
            )

            # =================================================
            # DIAGNÓSTICO ESPECIAL PARA ERROS TED
            # =================================================

            if response.status_code >= 400:

                error_text = response.text

                try:
                    error_json = response.json()
                except Exception:
                    error_json = None

                return [], {

                    "source": "TED",

                    "term": term,

                    "ok": False,

                    "count": 0,

                    "query_sent": query,

                    "status_code":
                        response.status_code,

                    "error":
                        error_text,

                    "error_json":
                        error_json

                }

            data = response.json()

            notices = (
                data.get(
                    "notices",
                    []
                )
            )

            results = []

            for notice in notices:

                result = notice_to_result(
                    notice
                )

                if result:

                    results.append(
                        result
                    )

            status = {

                "source":
                    "TED",

                "term":
                    term,

                "ok":
                    True,

                "count":
                    len(results),

                "query":
                    query

            }

            return results, status

        except Exception as exc:

            last_error = str(
                exc
            )

            time.sleep(
                1
            )

    return [], {

        "source":
            "TED",

        "term":
            term,

        "ok":
            False,

        "count":
            0,

        "query_sent":
            query,

        "error":
            last_error

    }

# ============================================================
# WORLD BANK
# ============================================================

def query_world_bank(
    term
):

    term = clean_query(
        term
    )

    params = {

        "qterm": term,

        "format": "json",

        "rows": PAGE_SIZE,

        "os": 0

    }

    try:

        response = requests.get(
            WORLD_BANK_URL,
            params=params,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

        results = []

        notices = []

        if isinstance(
            data,
            dict
        ):

            for key in (
                "procnotices",
                "notices",
                "results"
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

                    notices = list(
                        value.values()
                    )

                    break

        for notice in notices:

            if not isinstance(
                notice,
                dict
            ):

                continue

            title = (
                notice.get(
                    "project_name"
                )
                or notice.get(
                    "notice_title"
                )
                or notice.get(
                    "title"
                )
                or ""
            )

            buyer = (
                notice.get(
                    "borrower"
                )
                or notice.get(
                    "buyer"
                )
                or notice.get(
                    "country"
                )
                or ""
            )

            description = (
                notice.get(
                    "description"
                )
                or notice.get(
                    "notice_description"
                )
                or ""
            )

            country = (
                notice.get(
                    "country"
                )
                or ""
            )

            deadline = (
                notice.get(
                    "submission_deadline"
                )
                or notice.get(
                    "deadline"
                )
                or ""
            )

            publication_date = (
                notice.get(
                    "publication_date"
                )
                or notice.get(
                    "date"
                )
                or ""
            )

            category, score = classify_result(
                title,
                description,
                []
            )

            results.append({

                "title":
                    flatten(title),

                "buyer":
                    flatten(buyer),

                "country":
                    flatten(country),

                "date":
                    flatten(
                        publication_date
                    ),

                "deadline":
                    flatten(deadline),

                "cpv": [],

                "category":
                    category,

                "score":
                    score,

                "source":
                    "World Bank Procurement",

                "url":
                    "https://projects.worldbank.org/"
                    "en/projects-operations/"
                    "procurement",

                "publication_number":
                    "",

                "description":
                    flatten(description)

            })

        return results, {

            "source":
                "World Bank Procurement",

            "term":
                term,

            "ok":
                True,

            "count":
                len(results)

        }

    except Exception as exc:

        return [], {

            "source":
                "World Bank Procurement",

            "term":
                term,

            "ok":
                False,

            "count":
                0,

            "error":
                str(exc)

        }


# ============================================================
# DEDUPLICAÇÃO
# ============================================================

def deduplicate_results(
    results
):

    unique = {}

    for result in results:

        key = (
            normalize_text(
                result.get(
                    "title",
                    ""
                )
            ),
            normalize_text(
                result.get(
                    "buyer",
                    ""
                )
            ),
            normalize_text(
                result.get(
                    "country",
                    ""
                )
            )
        )

        if key not in unique:

            unique[key] = result

        else:

            # Mantém o resultado com maior score
            if (
                result.get(
                    "score",
                    0
                )
                >
                unique[key].get(
                    "score",
                    0
                )
            ):

                unique[key] = result

    return list(
        unique.values()
    )


# ============================================================
# FILTRO DE REGIÃO
# ============================================================

def region_matches(
    result,
    region
):

    if not region:

        return True

    region = normalize_text(
        region
    )

    country = normalize_text(
        result.get(
            "country",
            ""
        )
    )

    mapping = {

        "europa": [
            "portugal",
            "espanha",
            "franca",
            "alemanha",
            "italia",
            "paises baixos",
            "belgica",
            "irlanda",
            "austria",
            "polonia",
            "chequia",
            "eslovaquia",
            "hungria",
            "romenia",
            "bulgaria",
            "grecia",
            "suecia",
            "finlandia",
            "dinamarca",
            "noruega",
            "suica",
            "reino unido"
        ],

        "africa": [
            "marrocos",
            "argelia",
            "tunisia",
            "egito",
            "africa do sul",
            "mocambique",
            "angola",
            "quenia",
            "uganda",
            "tanzania"
        ],

        "americas": [
            "estados unidos",
            "canada",
            "mexico",
            "brasil",
            "chile",
            "colombia",
            "argentina"
        ],

        "medio oriente": [
            "arabia saudita",
            "emirados arabes unidos",
            "qatar",
            "oma"
        ],

        "asia": [
            "india",
            "china",
            "japao",
            "coreia do sul"
        ],

        "oceania": [
            "australia",
            "nova zelandia"
        ]

    }

    countries = mapping.get(
        region,
        []
    )

    return any(
        country_name in country
        for country_name in countries
    )


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
    # PESQUISA
    # --------------------------------------------------------
    #
    # "archaeology" = modo automático
    #
    # Qualquer outro termo é pesquisado
    # diretamente, sem acrescentar automaticamente
    # todos os termos de arqueologia.
    #
    # Exemplos:
    #
    # archaeology
    # archaeological
    # heritage
    # excavation
    # railway
    # banana123456
    #
    # --------------------------------------------------------

    user_query = clean_query(
        q
    )

    automatic_mode = (
        not user_query
        or user_query.lower()
        == "archaeology"
    )

    if automatic_mode:

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

        world_bank_terms = [

            "archaeology",
            "archaeological",
            "cultural heritage",
            "archaeological excavation"

        ]

    else:

        # ====================================================
        # AQUI ESTÁ A CORREÇÃO PRINCIPAL
        # ====================================================
        #
        # O termo introduzido pelo utilizador é pesquisado
        # sozinho.
        #
        # Assim:
        #
        # banana123456 -> 0 resultados
        #
        # archaeological -> pesquisa archaeological
        #
        # heritage -> pesquisa heritage
        #
        # ====================================================

        search_terms = [
            user_query
        ]

        world_bank_terms = [
            user_query
        ]


    # --------------------------------------------------------
    # REMOVER TERMOS DUPLICADOS
    # --------------------------------------------------------

    clean_terms = []

    for term in search_terms:

        if term.lower() not in [
            x.lower()
            for x in clean_terms
        ]:

            clean_terms.append(
                term
            )


    clean_world_bank_terms = []

    for term in world_bank_terms:

        if term.lower() not in [
            x.lower()
            for x in clean_world_bank_terms
        ]:

            clean_world_bank_terms.append(
                term
            )


    # --------------------------------------------------------
    # EXECUÇÃO EM PARALELO
    # --------------------------------------------------------

    tasks = []

    with ThreadPoolExecutor(
        max_workers=10
    ) as executor:

        # TED
        for term in clean_terms:

            tasks.append(
                executor.submit(
                    query_ted,
                    term
                )
            )

        # WORLD BANK
        for term in clean_world_bank_terms:

            tasks.append(
                executor.submit(
                    query_world_bank,
                    term
                )
            )


        # ----------------------------------------------------
        # RECEBER RESULTADOS
        # ----------------------------------------------------

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

                diagnostics.append({

                    "source": "API",

                    "ok": False,

                    "count": 0,

                    "error":
                        str(exc)

                })


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
            )
            == category

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

    def result_date(
        result
    ):

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

        if source["mode"]
        == "api"

    )


    portal_count = sum(

        1

        for source in SOURCES

        if source["mode"]
        == "portal"

        and (

            not region

            or source["region"]
            in (
                region,
                "Global"
            )

        )

    )


    # --------------------------------------------------------
    # RESPOSTA
    # --------------------------------------------------------

    return {

        "ok": True,

        "query": q,

        "region": region,

        "category": category,

        "results": results,

        "count":
            len(results),

        "sources":
            len(SOURCES),

        "api_sources":
            api_count,

        "portal_count":
            portal_count,

        "diagnostics":
            diagnostics,

        "searched_at":
            today_utc().isoformat()

    }


# ============================================================
# TESTE TED - MARROCOS
# ============================================================

@app.get("/api/test-ted-country")
def test_ted_country():

    test_query = (
        'FT~"works" '
        'AND buyer-country=MAR'
    )

    payload = {

        "query":
            test_query,

        "fields":
            TED_FIELDS,

        "page":
            1,

        "limit":
            PAGE_SIZE,

        "scope":
            "ACTIVE",

        "checkQuerySyntax":
            False,

        "paginationMode":
            "PAGE_NUMBER",

        "onlyLatestVersions":
            True

    }

    try:

        response = requests.post(

            TED_URL,

            json=payload,

            timeout=REQUEST_TIMEOUT

        )

        return {

            "ok":
                True,

            "status_code":
                response.status_code,

            "query":
                test_query,

            "response":
                response.json()

        }

    except Exception as exc:

        return {

            "ok":
                False,

            "query":
                test_query,

            "error":
                str(exc)

        }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return {

        "ok":
            True,

        "service":
            "Arqueologia Radar",

        "sources":
            len(SOURCES),

        "api_sources":
            sum(
                1
                for source in SOURCES
                if source["mode"]
                == "api"
            ),

        "date":
            today_utc().isoformat()

    }


# ============================================================
# RAIZ
# ============================================================

@app.get("/")
def root():

    index_file = (
        BASE_DIR
        / "index.html"
    )

    if index_file.exists():

        return FileResponse(
            index_file
        )

    return JSONResponse({

        "ok":
            True,

        "message":
            "Arqueologia Radar"

    })


# ============================================================
# APP.JS
# ============================================================

@app.get("/app.js")
def app_js():

    app_file = (
        BASE_DIR
        / "app.js"
    )

    if app_file.exists():

        return FileResponse(
            app_file,
            media_type=
                "application/javascript"
        )

    return JSONResponse({

        "ok":
            False,

        "error":
            "app.js não encontrado"

    })


# ============================================================
# MANIFEST
# ============================================================

@app.get("/manifest.json")
def manifest():

    manifest_file = (
        BASE_DIR
        / "manifest.json"
    )

    if manifest_file.exists():

        return FileResponse(
            manifest_file,
            media_type=
                "application/json"
        )

    return JSONResponse({

        "name":
            "Arqueologia Radar",

        "short_name":
            "Radar",

        "start_url":
            "/",

        "display":
            "standalone"

    })
