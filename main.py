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
import os


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Arqueologia Radar",
    version="2.0"
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
# URLS DAS FONTES AUTOMÁTICAS
# ============================================================

TED_URL = "https://api.ted.europa.eu/v3/notices/search"

WORLD_BANK_URL = (
    "https://search.worldbank.org/api/v2/procnotices"
)

SOUTH_AFRICA_OCDS_URL = (
    "https://ocds-api.etenders.gov.za/api/OCDSReleases"
)

COLOMBIA_SECOP_URL = (
    "https://www.datos.gov.co/resource/p6dx-8zbt.json"
)


# ============================================================
# FONTES
#
# automatic=True  -> o Radar efectivamente pesquisa a fonte
# automatic=False -> portal de referência / expansão futura
# ============================================================

SOURCES = [

    {
        "name": "TED — Europa",
        "region": "Europa",
        "type": "api",
        "automatic": True,
        "url": "https://ted.europa.eu/"
    },

    {
        "name": "World Bank Procurement",
        "region": "Global",
        "type": "api",
        "automatic": True,
        "url": "https://projects.worldbank.org/en/projects-operations/procurement"
    },

    {
        "name": "South Africa eTenders — OCDS",
        "region": "África",
        "type": "api",
        "automatic": True,
        "url": "https://www.etenders.gov.za/"
    },

    {
        "name": "SECOP II — Colômbia",
        "region": "Américas",
        "type": "api",
        "automatic": True,
        "url": "https://www.datos.gov.co/"
    },

    {
        "name": "BASE Portugal",
        "region": "Europa",
        "type": "portal",
        "automatic": False,
        "url": "https://www.base.gov.pt/"
    },

    {
        "name": "Contratación Pública España",
        "region": "Europa",
        "type": "portal",
        "automatic": False,
        "url": "https://contrataciondelestado.es/"
    },

    {
        "name": "UNDB",
        "region": "Global",
        "type": "portal",
        "automatic": False,
        "url": "https://devbusiness.un.org/"
    },

    {
        "name": "UNGM",
        "region": "Global",
        "type": "portal",
        "automatic": False,
        "url": "https://www.ungm.org/"
    },

    {
        "name": "EBRD",
        "region": "Global",
        "type": "portal",
        "automatic": False,
        "url": "https://www.ebrd.com/"
    },

    {
        "name": "EIB",
        "region": "Global",
        "type": "portal",
        "automatic": False,
        "url": "https://www.eib.org/"
    },

    {
        "name": "African Development Bank",
        "region": "África",
        "type": "portal",
        "automatic": False,
        "url": "https://www.afdb.org/"
    },

    {
        "name": "AfDB Procurement Notices",
        "region": "África",
        "type": "portal",
        "automatic": False,
        "url": "https://www.afdb.org/en/projects-and-operations/procurement"
    },

    {
        "name": "Uganda",
        "region": "África",
        "type": "portal",
        "automatic": False,
        "url": "https://www.ppda.go.ug/"
    },

    {
        "name": "Kenya",
        "region": "África",
        "type": "portal",
        "automatic": False,
        "url": "https://www.tenders.go.ke/"
    },

    {
        "name": "Tanzania",
        "region": "África",
        "type": "portal",
        "automatic": False,
        "url": "https://www.ppra.go.tz/"
    },

    {
        "name": "Mozambique",
        "region": "África",
        "type": "portal",
        "automatic": False,
        "url": "https://www.ufsa.gov.mz/"
    },

    {
        "name": "Morocco",
        "region": "África",
        "type": "portal",
        "automatic": False,
        "url": "https://www.marchespublics.gov.ma/"
    },

    {
        "name": "Oman",
        "region": "Médio Oriente",
        "type": "portal",
        "automatic": False,
        "url": "https://etendering.tenderboard.gov.om/"
    },

    {
        "name": "Saudi Arabia Etimad",
        "region": "Médio Oriente",
        "type": "portal",
        "automatic": False,
        "url": "https://tenders.etimad.sa/"
    },

    {
        "name": "UAE",
        "region": "Médio Oriente",
        "type": "portal",
        "automatic": False,
        "url": "https://www.mof.gov.ae/"
    },

    {
        "name": "Qatar",
        "region": "Médio Oriente",
        "type": "portal",
        "automatic": False,
        "url": "https://monaqasat.mof.gov.qa/"
    },

    {
        "name": "SAM.gov",
        "region": "Américas",
        "type": "portal",
        "automatic": False,
        "url": "https://sam.gov/"
    },

    {
        "name": "ChileCompra",
        "region": "Américas",
        "type": "portal",
        "automatic": False,
        "url": "https://www.mercadopublico.cl/"
    },

    {
        "name": "Compras Brasil",
        "region": "Américas",
        "type": "portal",
        "automatic": False,
        "url": "https://www.gov.br/compras/"
    },

    {
        "name": "IDB",
        "region": "Américas",
        "type": "portal",
        "automatic": False,
        "url": "https://www.iadb.org/"
    },

    {
        "name": "Asian Development Bank",
        "region": "Ásia",
        "type": "portal",
        "automatic": False,
        "url": "https://www.adb.org/"
    },

    {
        "name": "Australia",
        "region": "Oceânia",
        "type": "portal",
        "automatic": False,
        "url": "https://www.tenders.gov.au/"
    },

    {
        "name": "New Zealand",
        "region": "Oceânia",
        "type": "portal",
        "automatic": False,
        "url": "https://www.gets.govt.nz/"
    },

    {
        "name": "Global Procurement",
        "region": "Global",
        "type": "portal",
        "automatic": False,
        "url": "https://www.devbusiness.un.org/"
    },
]


# ============================================================
# TERMOS DE PESQUISA
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
    "arqueológico",
    "arqueológica",
    "património cultural",
    "patrimonio cultural",
    "archéologie",
    "archéologique",
    "patrimoine culturel"
]


DIRECT_ARCHAEOLOGY_TERMS = [

    "archaeology",
    "archaeological",
    "archaeologic",
    "archaeological monitoring",
    "archaeological excavation",
    "archaeological services",
    "archaeological survey",
    "archaeological assessment",
    "archaeological investigation",
    "archaeological works",
    "archaeological study",
    "archaeological studies",
    "archaeological research",
    "archaeological watching brief",
    "archaeological watching",
    "archaeological evaluation",
    "archaeological impact assessment",
    "archaeological fieldwork",
    "archaeological supervision",
    "archaeological consultancy",
    "archaeological consultant",
    "archaeologist",
    "archaeologists",

    "archéologie",
    "archéologique",
    "archéologiques",

    "arqueologia",
    "arqueológico",
    "arqueológica",
    "arqueológicos",
    "arqueológicas",
    "serviços de arqueologia",
    "servicos de arqueologia",
    "escavação arqueológica",
    "escavacao arqueologica",

    "património arqueológico",
    "patrimonio arqueologico"
]


HERITAGE_TERMS = [
    "cultural heritage",
    "heritage management",
    "heritage assessment",
    "heritage conservation",
    "heritage protection",
    "historic environment",
    "historical heritage",
    "built heritage",
    "archaeological heritage",
    "heritage impact assessment",
    "chance finds",
    "chance find",
    "cultural property",
    "cultural resources",
    "monument",
    "unesco",
    "património cultural",
    "patrimonio cultural",
    "património histórico",
    "patrimonio historico",
    "patrimoine culturel",
    "patrimoine historique"
]


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


ARCHAEOLOGY_CPVS = {
    "71351914",
    "71351910",
    "71351900",
    "71351720",
    "71351811",
    "45112450"
}


NON_ARCHAEOLOGY_CPV_PREFIXES = {
    "720",
    "480",
    "500",
    "600",
    "630",
    "640",
    "650",
    "660",
    "700",
    "730",
    "750",
    "790",
    "800",
    "850",
    "900",
    "920",
    "980"
}


# ============================================================
# TED
# ============================================================

TED_FIELDS = [
    "publication-number",
    "publication-date",
    "notice-title",
    "official-language",
    "buyer-name",
    "buyer-country",
    "classification-cpv",
    "notice-type",
    "deadline",
    "deadline-date-lot",
    "deadline-receipt-request",
    "deadline-receipt-tender-date-lot",
    "deadline-receipt-tender-time-lot",
    "description-proc",
    "description-lot"
]


# ============================================================
# PAÍSES
# ============================================================

COUNTRY_NAMES = {

    # Europa
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

    # África
    "MA": "Marrocos",
    "DZ": "Argélia",
    "TN": "Tunísia",
    "EG": "Egipto",
    "ZA": "África do Sul",
    "MZ": "Moçambique",
    "AO": "Angola",
    "KE": "Quénia",
    "UG": "Uganda",
    "TZ": "Tanzânia",

    # Américas
    "US": "Estados Unidos",
    "CA": "Canadá",
    "MX": "México",
    "BR": "Brasil",
    "CL": "Chile",
    "CO": "Colômbia",
    "AR": "Argentina",

    # Médio Oriente
    "SA": "Arábia Saudita",
    "AE": "Emirados Árabes Unidos",
    "QA": "Qatar",
    "OM": "Omã",

    # Ásia
    "IN": "Índia",
    "CN": "China",
    "JP": "Japão",
    "KR": "Coreia do Sul",

    # Oceânia
    "AU": "Austrália",
    "NZ": "Nova Zelândia"
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
    "EGY": "Egipto",
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

    "SAU": "Arábia Saudita",
    "ARE": "Emirados Árabes Unidos",
    "QAT": "Qatar",
    "OMN": "Omã",

    "IND": "Índia",
    "CHN": "China",
    "JPN": "Japão",
    "KOR": "Coreia do Sul",

    "AUS": "Austrália",
    "NZL": "Nova Zelândia"
}


# ============================================================
# UTILITÁRIOS
# ============================================================

def today_utc():
    return date.today()


def cutoff_date():
    return today_utc() - timedelta(days=PERIOD_DAYS)


def flatten(value):
    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, (int, float, bool)):
        return str(value)

    if isinstance(value, list):
        return " ".join(flatten(x) for x in value)

    if isinstance(value, dict):
        return " ".join(
            f"{k} {flatten(v)}"
            for k, v in value.items()
        )

    return str(value)


def repair_mojibake(text):
    if not isinstance(text, str):
        return text

    if "Ã" not in text and "Â" not in text and "â" not in text:
        return text

    try:
        repaired = text.encode("latin1").decode("utf-8")
        return repaired
    except Exception:
        return text


def repair_structure(value):
    if isinstance(value, str):
        return repair_mojibake(value)

    if isinstance(value, list):
        return [repair_structure(x) for x in value]

    if isinstance(value, dict):
        return {
            k: repair_structure(v)
            for k, v in value.items()
        }

    return value


def clean_query(term):
    if term is None:
        return ""

    term = str(term).strip()

    term = re.sub(r"\s+", " ", term)

    return term


def normalize_text(text):
    text = repair_mojibake(flatten(text))

    text = unicodedata.normalize(
        "NFKD",
        text
    )

    text = "".join(
        c for c in text
        if not unicodedata.combining(c)
    )

    return text.lower()


def build_ted_query(term):

    term = clean_query(term)

    if not term:
        return ""

    if " " not in term:
        return f"FT~{term}"

    escaped = term.replace('"', '\\"')

    return f'FT~"{escaped}"'


def choose_multilingual_text(value):

    if isinstance(value, str):
        return value

    if isinstance(value, list):

        for item in value:

            if isinstance(item, dict):

                for key in [
                    "text",
                    "value",
                    "content",
                    "title"
                ]:
                    if item.get(key):
                        return item[key]

            elif isinstance(item, str):
                return item

    if isinstance(value, dict):

        for key in [
            "text",
            "value",
            "content",
            "title"
        ]:
            if value.get(key):
                return value[key]

        for key, val in value.items():

            if isinstance(val, str):
                return val

    return flatten(value)


def clean_ted_title(title, official_language=""):

    title = choose_multilingual_text(title)

    title = repair_mojibake(title)

    title = html.unescape(title)

    title = re.sub(
        r"\s+",
        " ",
        title
    ).strip()

    if not title:
        return ""

    # Tentativa de separar títulos TED concatenados
    title = re.sub(
        r"\s+(?:EN|FR|DE|ES|PT|IT|NL|PL|EL|BG|RO|CS|SK|HU)\s*[:\-]\s*",
        " | ",
        title,
        flags=re.I
    )

    if len(title) > 600:
        title = title[:597] + "..."

    return title


def parse_date(value):

    if value is None:
        return ""

    if isinstance(value, datetime):
        return value.date().isoformat()

    if isinstance(value, date):
        return value.isoformat()

    value = str(value).strip()

    if not value:
        return ""

    # ISO
    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).date().isoformat()
    except Exception:
        pass

    # YYYY-MM-DD
    match = re.search(
        r"\b(\d{4}-\d{2}-\d{2})\b",
        value
    )

    if match:
        return match.group(1)

    # DD/MM/YYYY
    match = re.search(
        r"\b(\d{2})/(\d{2})/(\d{4})\b",
        value
    )

    if match:
        return (
            f"{match.group(3)}-"
            f"{match.group(2)}-"
            f"{match.group(1)}"
        )

    return ""


def find_date_in_structure(value):

    if isinstance(value, str):
        parsed = parse_date(value)

        if parsed:
            return parsed

        return ""

    if isinstance(value, list):

        for item in value:

            result = find_date_in_structure(item)

            if result:
                return result

        return ""

    if isinstance(value, dict):

        preferred_keys = [
            "deadline",
            "deadline-date-lot",
            "deadline-receipt-request",
            "deadline-receipt-tender-date-lot",
            "date",
            "publication-date"
        ]

        for key in preferred_keys:

            if key in value:

                result = find_date_in_structure(
                    value[key]
                )

                if result:
                    return result

        for val in value.values():

            result = find_date_in_structure(val)

            if result:
                return result

    return ""


def extract_country(notice):

    candidates = [
        notice.get("buyer-country"),
        notice.get("buyerCountry"),
        notice.get("country"),
        notice.get("countryCode")
    ]

    for value in candidates:

        if value:

            value = flatten(value).strip().upper()

            if value in COUNTRY_NAMES:
                return COUNTRY_NAMES[value]

            if value in COUNTRY_NAMES_3:
                return COUNTRY_NAMES_3[value]

            if len(value) == 2:
                return COUNTRY_NAMES.get(
                    value,
                    value
                )

            if len(value) == 3:
                return COUNTRY_NAMES_3.get(
                    value,
                    value
                )

            return repair_mojibake(value)

    return ""


def extract_cpvs(notice):

    cpvs = []

    def collect(value):

        if value is None:
            return

        if isinstance(value, str):

            matches = re.findall(
                r"\b\d{8}\b",
                value
            )

            cpvs.extend(matches)

        elif isinstance(value, list):

            for item in value:
                collect(item)

        elif isinstance(value, dict):

            for key, val in value.items():

                if (
                    "cpv" in key.lower()
                    or "classification" in key.lower()
                ):
                    collect(val)

    collect(notice.get("classification-cpv"))

    collect(notice.get("classificationCpv"))

    collect(notice.get("cpv"))

    collect(notice.get("cpvs"))

    result = []

    for cpv in cpvs:

        cpv = cpv[:8]

        if cpv not in result:
            result.append(cpv)

    return result


def extract_deadline(notice):

    keys = [
        "deadline",
        "deadline-date-lot",
        "deadline-receipt-request",
        "deadline-receipt-tender-date-lot"
    ]

    for key in keys:

        if notice.get(key):

            result = find_date_in_structure(
                notice[key]
            )

            if result:
                return result

    return ""


# ============================================================
# CLASSIFICAÇÃO
# ============================================================

def classify_result(
    title,
    description,
    cpvs,
    source=""
):

    text = normalize_text(
        f"{title} {description}"
    )

    cpv_direct = False

    for cpv in cpvs:

        cpv = str(cpv)[:8]

        if cpv in ARCHAEOLOGY_CPVS:
            cpv_direct = True
            break

    direct = any(
        normalize_text(term) in text
        for term in DIRECT_ARCHAEOLOGY_TERMS
    )

    heritage = any(
        normalize_text(term) in text
        for term in HERITAGE_TERMS
    )

    major = any(
        normalize_text(term) in text
        for term in MAJOR_PROJECT_TERMS
    )

    # --------------------------------------------------------
    # REGRA FUNDAMENTAL DO RADAR
    #
    # Um grande projecto sozinho NÃO é arqueologia.
    # Só entra se houver evidência arqueológica/patrimonial.
    # --------------------------------------------------------

    if cpv_direct:

        return "Arqueologia direta", 100

    if direct:

        if major:
            return (
                "Arqueologia direta / grande projeto",
                95
            )

        return "Arqueologia direta", 90

    if heritage:

        if major:
            return (
                "Património / grande projeto",
                75
            )

        return (
            "Património / potencial arqueológico",
            65
        )

    # NÃO devolver major sozinho.
    return "Outro", 0


# ============================================================
# CONVERSÃO DE RESULTADOS
# ============================================================

def make_result(
    title="",
    buyer="",
    country="",
    published="",
    deadline="",
    cpvs=None,
    description="",
    category="Outro",
    score=0,
    source="",
    url=""
):

    cpvs = cpvs or []

    return {
        "title": repair_mojibake(
            html.unescape(str(title or "")).strip()
        ),
        "buyer": repair_mojibake(
            html.unescape(str(buyer or "")).strip()
        ),
        "country": repair_mojibake(
            str(country or "").strip()
        ),
        "date": parse_date(published),
        "deadline": parse_date(deadline),
        "cpv": cpvs,
        "category": repair_mojibake(category),
        "score": score,
        "source": repair_mojibake(source),
        "url": url or "",
        "description": repair_mojibake(
            html.unescape(
                str(description or "")
            ).strip()
        )
    }


def notice_to_result(notice):

    title = (
        notice.get("notice-title")
        or notice.get("noticeTitle")
        or ""
    )

    official_language = (
        notice.get("official-language")
        or notice.get("officialLanguage")
        or ""
    )

    title = clean_ted_title(
        title,
        official_language
    )

    buyer = (
        notice.get("buyer-name")
        or notice.get("buyerName")
        or ""
    )

    country = extract_country(notice)

    cpvs = extract_cpvs(notice)

    deadline = extract_deadline(notice)

    publication_date = (
        notice.get("publication-date")
        or notice.get("publicationDate")
        or ""
    )

    description = " ".join([
        flatten(
            notice.get("description-proc")
            or notice.get("descriptionProc")
            or ""
        ),
        flatten(
            notice.get("description-lot")
            or notice.get("descriptionLot")
            or ""
        )
    ])

    category, score = classify_result(
        title,
        description,
        cpvs,
        "TED"
    )

    if category == "Outro":
        return None

    publication_number = (
        notice.get("publication-number")
        or notice.get("publicationNumber")
        or ""
    )

    url = ""

    if publication_number:

        url = (
            "https://ted.europa.eu/en/"
            "notice/-/detail/"
            f"{publication_number}"
        )

    return make_result(
        title=title,
        buyer=buyer,
        country=country,
        published=publication_date,
        deadline=deadline,
        cpvs=cpvs,
        description=description,
        category=category,
        score=score,
        source="TED — Europa",
        url=url
    )


# ============================================================
# TED API
# ============================================================

def query_ted(term):

    query = build_ted_query(term)

    if not query:

        return {
            "ok": False,
            "source": "TED",
            "term": term,
            "count": 0,
            "results": [],
            "error": "query vazia"
        }

    payload = {
        "query": query,
        "fields": TED_FIELDS,
        "page": 1,
        "limit": PAGE_SIZE,
        "scope": "ACTIVE",
        "checkQuerySyntax": False,
        "paginationMode": "PAGE_NUMBER"
    }

    last_error = ""

    for attempt in range(3):

        try:

            response = requests.post(
                TED_URL,
                json=payload,
                timeout=REQUEST_TIMEOUT
            )

            if response.status_code != 200:

                last_error = (
                    f"HTTP {response.status_code}: "
                    f"{response.text[:500]}"
                )

                time.sleep(1)

                continue

            data = response.json()

            notices = (
                data.get("notices")
                or data.get("results")
                or []
            )

            results = []

            for notice in notices:

                if not isinstance(notice, dict):
                    continue

                result = notice_to_result(notice)

                if result:
                    results.append(result)

            return {
                "ok": True,
                "source": "TED",
                "term": term,
                "query": query,
                "count": len(results),
                "raw_count": len(notices),
                "results": results
            }

        except Exception as exc:

            last_error = str(exc)

            time.sleep(1)

    return {
        "ok": False,
        "source": "TED",
        "term": term,
        "query": query,
        "count": 0,
        "results": [],
        "error": last_error
    }


# ============================================================
# WORLD BANK
# ============================================================

def query_world_bank(term):

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

        if response.status_code != 200:

            return {
                "ok": False,
                "source": "World Bank Procurement",
                "term": term,
                "count": 0,
                "results": [],
                "error": f"HTTP {response.status_code}"
            }

        data = response.json()

        raw = (
            data.get("procnotices")
            or data.get("notices")
            or data.get("results")
            or []
        )

        if isinstance(raw, dict):

            raw = list(raw.values())

        results = []

        for item in raw:

            if not isinstance(item, dict):
                continue

            title = (
                item.get("project_name")
                or item.get("projectName")
                or item.get("title")
                or item.get("notice_title")
                or item.get("noticeTitle")
                or ""
            )

            description = " ".join([
                flatten(
                    item.get("description")
                    or item.get("project_description")
                    or ""
                ),
                flatten(
                    item.get("procurement_method")
                    or ""
                )
            ])

            buyer = (
                item.get("buyer")
                or item.get("borrower")
                or item.get("agency")
                or ""
            )

            country = (
                item.get("country")
                or item.get("country_name")
                or ""
            )

            published = (
                item.get("publication_date")
                or item.get("publicationDate")
                or item.get("date")
                or ""
            )

            deadline = (
                item.get("deadline")
                or item.get("submission_deadline")
                or ""
            )

            url = (
                item.get("url")
                or item.get("notice_url")
                or item.get("project_url")
                or ""
            )

            category, score = classify_result(
                title,
                description,
                [],
                "World Bank Procurement"
            )

            # Muito importante:
            # projectos genéricos deixam de aparecer.
            if category == "Outro":
                continue

            results.append(
                make_result(
                    title=title,
                    buyer=buyer,
                    country=country,
                    published=published,
                    deadline=deadline,
                    cpvs=[],
                    description=description,
                    category=category,
                    score=score,
                    source="World Bank Procurement",
                    url=url
                )
            )

        return {
            "ok": True,
            "source": "World Bank Procurement",
            "term": term,
            "count": len(results),
            "raw_count": len(raw),
            "results": results
        }

    except Exception as exc:

        return {
            "ok": False,
            "source": "World Bank Procurement",
            "term": term,
            "count": 0,
            "results": [],
            "error": str(exc)
        }


# ============================================================
# ÁFRICA DO SUL — OCDS / eTENDERS
# ============================================================

def extract_ocds_text(value):

    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, list):
        return " ".join(
            extract_ocds_text(x)
            for x in value
        )

    if isinstance(value, dict):
        return " ".join(
            extract_ocds_text(v)
            for v in value.values()
        )

    return str(value)


def ocds_release_to_result(release):

    if not isinstance(release, dict):
        return None

    tender = release.get("tender") or {}
    buyer_data = release.get("buyer") or {}
    parties = release.get("parties") or []

    title = (
        tender.get("title")
        or release.get("title")
        or ""
    )

    description = (
        tender.get("description")
        or ""
    )

    buyer = (
        buyer_data.get("name")
        or ""
    )

    if not buyer and isinstance(parties, list):

        for party in parties:

            if not isinstance(party, dict):
                continue

            roles = party.get("roles") or []

            if "buyer" in roles:

                buyer = (
                    party.get("name")
                    or ""
                )

                break

    country = "África do Sul"

    published = (
        release.get("date")
        or tender.get("datePublished")
        or ""
    )

    deadline = (
        tender.get("tenderPeriod", {}).get("endDate")
        or ""
    )

    url = (
        release.get("url")
        or ""
    )

    cpvs = []

    items = tender.get("items") or []

    for item in items:

        classification = (
            item.get("classification")
            or {}
        )

        code = classification.get("id")

        if code:
            cpvs.append(str(code))

    category, score = classify_result(
        title,
        description,
        cpvs,
        "South Africa eTenders — OCDS"
    )

    if category == "Outro":
        return None

    return make_result(
        title=title,
        buyer=buyer,
        country=country,
        published=published,
        deadline=deadline,
        cpvs=cpvs,
        description=description,
        category=category,
        score=score,
        source="South Africa eTenders — OCDS",
        url=url
    )


def query_south_africa(term):

    try:

        # O endpoint OCDS é público.
        # A pesquisa local é feita sobre os releases
        # devolvidos pelo feed.

        response = requests.get(
            SOUTH_AFRICA_OCDS_URL,
            params={
                "page": 1,
                "pageSize": 100
            },
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code != 200:

            return {
                "ok": False,
                "source": "South Africa eTenders — OCDS",
                "term": term,
                "count": 0,
                "results": [],
                "error": (
                    f"HTTP {response.status_code}"
                )
            }

        data = response.json()

        releases = []

        if isinstance(data, dict):

            releases = (
                data.get("releases")
                or data.get("results")
                or data.get("data")
                or []
            )

        elif isinstance(data, list):

            releases = data

        wanted = normalize_text(term)

        results = []

        for release in releases:

            if not isinstance(release, dict):
                continue

            release_text = normalize_text(
                extract_ocds_text(release)
            )

            # Pesquisa textual interna
            # para evitar trazer todo o feed.
            if wanted not in release_text:
                continue

            result = ocds_release_to_result(
                release
            )

            if result:
                results.append(result)

        return {
            "ok": True,
            "source": "South Africa eTenders — OCDS",
            "term": term,
            "count": len(results),
            "raw_count": len(releases),
            "results": results
        }

    except Exception as exc:

        return {
            "ok": False,
            "source": "South Africa eTenders — OCDS",
            "term": term,
            "count": 0,
            "results": [],
            "error": str(exc)
        }


# ============================================================
# SECOP II — COLÔMBIA
# ============================================================

def query_colombia_secop(term):

    try:

        # O dataset SECOP II contém dezenas de campos.
        # A pesquisa é feita através da API Socrata.

        wanted = normalize_text(term)

        # A API permite full-text search através de $q.
        params = {
            "$limit": 100,
            "$q": term
        }

        response = requests.get(
            COLOMBIA_SECOP_URL,
            params=params,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code != 200:

            return {
                "ok": False,
                "source": "SECOP II — Colômbia",
                "term": term,
                "count": 0,
                "results": [],
                "error": (
                    f"HTTP {response.status_code}"
                )
            }

        data = response.json()

        if not isinstance(data, list):
            data = []

        results = []

        for item in data:

            if not isinstance(item, dict):
                continue

            title = (
                item.get(
                    "nombre_del_procedimiento"
                )
                or item.get(
                    "nombre_procedimiento"
                )
                or ""
            )

            description = (
                item.get(
                    "descripci_n_del_procedimiento"
                )
                or item.get(
                    "descripcion_del_procedimiento"
                )
                or ""
            )

            # Segurança adicional:
            # mesmo que Socrata devolva resultados
            # pouco relacionados, verificamos localmente.

            text = normalize_text(
                f"{title} {description}"
            )

            if wanted not in text:

                # procurar também nos restantes campos
                complete = normalize_text(
                    flatten(item)
                )

                if wanted not in complete:
                    continue

            buyer = (
                item.get("entidad")
                or ""
            )

            country = "Colômbia"

            published = (
                item.get(
                    "fecha_de_publicacion_del"
                )
                or item.get(
                    "fecha_de_publicacion_del_proceso"
                )
                or item.get(
                    "fecha_de_ultima_publicaci"
                )
                or ""
            )

            deadline = (
                item.get(
                    "fecha_de_recepcion_de_respuestas"
                )
                or item.get(
                    "fecha_de_apertura_de_respuesta"
                )
                or ""
            )

            process_id = (
                item.get(
                    "id_del_proceso"
                )
                or ""
            )

            url = ""

            if process_id:

                url = (
                    "https://www.datos.gov.co/"
                    "Gastos-Gubernamentales/"
                    "SECOP-II-Procesos-de-Contrataci-n/"
                    "p6dx-8zbt"
                )

            category, score = classify_result(
                title,
                description,
                [],
                "SECOP II — Colômbia"
            )

            if category == "Outro":
                continue

            results.append(
                make_result(
                    title=title,
                    buyer=buyer,
                    country=country,
                    published=published,
                    deadline=deadline,
                    cpvs=[],
                    description=description,
                    category=category,
                    score=score,
                    source="SECOP II — Colômbia",
                    url=url
                )
            )

        return {
            "ok": True,
            "source": "SECOP II — Colômbia",
            "term": term,
            "count": len(results),
            "raw_count": len(data),
            "results": results
        }

    except Exception as exc:

        return {
            "ok": False,
            "source": "SECOP II — Colômbia",
            "term": term,
            "count": 0,
            "results": [],
            "error": str(exc)
        }


# ============================================================
# DEDUPLICAÇÃO
# ============================================================

def deduplicate_results(results):

    unique = {}

    for result in results:

        title = normalize_text(
            result.get("title", "")
        )

        buyer = normalize_text(
            result.get("buyer", "")
        )

        country = normalize_text(
            result.get("country", "")
        )

        key = (
            title[:250],
            buyer[:150],
            country
        )

        if key not in unique:

            unique[key] = result

        else:

            existing = unique[key]

            # Manter a versão com maior score
            if (
                result.get("score", 0)
                >
                existing.get("score", 0)
            ):
                unique[key] = result

    return list(unique.values())


# ============================================================
# REGIÕES
# ============================================================

REGION_COUNTRIES = {

    "Europa": {
        normalize_text(v)
        for k, v in COUNTRY_NAMES.items()
        if k in {
            "PT", "ES", "FR", "DE", "IT", "NL",
            "BE", "IE", "AT", "PL", "CZ", "SK",
            "HU", "RO", "BG", "GR", "SE", "FI",
            "DK", "NO", "CH", "UK"
        }
    },

    "África": {
        normalize_text(v)
        for k, v in COUNTRY_NAMES.items()
        if k in {
            "MA", "DZ", "TN", "EG", "ZA",
            "MZ", "AO", "KE", "UG", "TZ"
        }
    },

    "Américas": {
        normalize_text(v)
        for k, v in COUNTRY_NAMES.items()
        if k in {
            "US", "CA", "MX", "BR",
            "CL", "CO", "AR"
        }
    },

    "Médio Oriente": {
        normalize_text(v)
        for k, v in COUNTRY_NAMES.items()
        if k in {
            "SA", "AE", "QA", "OM"
        }
    },

    "Ásia": {
        normalize_text(v)
        for k, v in COUNTRY_NAMES.items()
        if k in {
            "IN", "CN", "JP", "KR"
        }
    },

    "Oceânia": {
        normalize_text(v)
        for k, v in COUNTRY_NAMES.items()
        if k in {
            "AU", "NZ"
        }
    }
}


def region_matches(country, region):

    if not region:
        return True

    if not country:
        return True

    normalized = normalize_text(country)

    allowed = REGION_COUNTRIES.get(
        region,
        set()
    )

    return normalized in allowed


# ============================================================
# PRAZO
# ============================================================

def is_expired(deadline):

    if not deadline:
        return False

    try:

        value = datetime.strptime(
            deadline,
            "%Y-%m-%d"
        ).date()

        return value < today_utc()

    except Exception:
        return False


# ============================================================
# PESQUISA PRINCIPAL
# ============================================================

@app.get("/api/search")
def search(
    q: str = Query(
        "",
        description="Termo de pesquisa"
    ),
    region: str = Query(
        "",
        description="Região"
    ),
    category: str = Query(
        "",
        description="Categoria"
    )
):

    started = time.time()

    query = clean_query(q)

    # --------------------------------------------------------
    # MODO AUTOMÁTICO
    # --------------------------------------------------------

    automatic_mode = (
        not query
        or normalize_text(query)
        in {
            "archaeology",
            "arqueologia"
        }
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
            "archaeological assessment",
            "archéologie",
            "arqueologia"
        ]

    else:

        search_terms = [query]

    # Evitar duplicações
    search_terms = list(
        dict.fromkeys(search_terms)
    )

    # --------------------------------------------------------
    # EXECUÇÃO PARALELA
    # --------------------------------------------------------

    jobs = []

    for term in search_terms:

        jobs.append(
            (
                "TED",
                term,
                query_ted
            )
        )

        jobs.append(
            (
                "World Bank",
                term,
                query_world_bank
            )
        )

        # Fontes regionais automáticas.
        # Para reduzir tráfego, estas duas fontes
        # são pesquisadas apenas no modo automático
        # ou quando a pesquisa corresponde a arqueologia.

        if automatic_mode:

            jobs.append(
                (
                    "South Africa",
                    term,
                    query_south_africa
                )
            )

            jobs.append(
                (
                    "Colombia",
                    term,
                    query_colombia_secop
                )
            )

    all_results = []

    diagnostics = []

    with ThreadPoolExecutor(
        max_workers=12
    ) as executor:

        future_map = {}

        for source_name, term, function in jobs:

            future = executor.submit(
                function,
                term
            )

            future_map[future] = (
                source_name,
                term
            )

        for future in as_completed(
            future_map
        ):

            source_name, term = (
                future_map[future]
            )

            try:

                result = future.result()

                if not isinstance(result, dict):
                    continue

                diagnostics.append({

                    "source": result.get(
                        "source",
                        source_name
                    ),

                    "term": term,

                    "ok": result.get(
                        "ok",
                        False
                    ),

                    "count": result.get(
                        "count",
                        0
                    ),

                    "raw_count": result.get(
                        "raw_count",
                        0
                    ),

                    "error": result.get(
                        "error",
                        ""
                    )
                })

                all_results.extend(
                    result.get(
                        "results",
                        []
                    )
                )

            except Exception as exc:

                diagnostics.append({

                    "source": source_name,
                    "term": term,
                    "ok": False,
                    "count": 0,
                    "error": str(exc)

                })

    # --------------------------------------------------------
    # DEDUPLICAÇÃO
    # --------------------------------------------------------

    results = deduplicate_results(
        all_results
    )

    # --------------------------------------------------------
    # REGIÃO
    # --------------------------------------------------------

    if region:

        results = [
            result
            for result in results
            if region_matches(
                result.get("country", ""),
                region
            )
        ]

    # --------------------------------------------------------
    # CATEGORIA
    # --------------------------------------------------------

    if category:

        results = [
            result
            for result in results
            if normalize_text(
                result.get("category", "")
            )
            ==
            normalize_text(category)
        ]

    # --------------------------------------------------------
    # RETIRAR PRAZOS EXPIRADOS
    # --------------------------------------------------------

    results = [
        result
        for result in results
        if not is_expired(
            result.get("deadline", "")
        )
    ]

    # --------------------------------------------------------
    # REPARAR TEXTO
    # --------------------------------------------------------

    for result in results:

        for key in [
            "title",
            "buyer",
            "country",
            "category",
            "description"
        ]:

            result[key] = repair_mojibake(
                result.get(key, "")
            )

    # --------------------------------------------------------
    # ORDENAÇÃO
    # --------------------------------------------------------

    results.sort(
        key=lambda x: (
            x.get("score", 0),
            x.get("date", "")
        ),
        reverse=True
    )

    # --------------------------------------------------------
    # ESTATÍSTICAS POR REGIÃO
    # --------------------------------------------------------

    regions = {}

    for result in results:

        country = result.get(
            "country",
            ""
        )

        found_region = "Global"

        for region_name, countries in (
            REGION_COUNTRIES.items()
        ):

            if normalize_text(country) in countries:

                found_region = region_name
                break

        regions[found_region] = (
            regions.get(found_region, 0)
            + 1
        )

    # --------------------------------------------------------
    # FONTES AUTOMÁTICAS
    # --------------------------------------------------------

    automatic_sources = [
        source
        for source in SOURCES
        if source.get("automatic")
    ]

    automatic_source_names = [
        source["name"]
        for source in automatic_sources
    ]

    elapsed = round(
        time.time() - started,
        2
    )

    return {
        "ok": True,

        "query": (
            query
            if query
            else "archaeology"
        ),

        "automatic_mode": automatic_mode,

        "region": region,

        "category": category,

        "results": results,

        "count": len(results),

        "sources": len(SOURCES),

        "automatic_sources": len(
            automatic_sources
        ),

        "automatic_source_names":
            automatic_source_names,

        "portal_count": len([
            s for s in SOURCES
            if not s.get("automatic")
        ]),

        "regions": regions,

        "diagnostics": diagnostics,

        "searched_at": date.today().isoformat(),

        "elapsed_seconds": elapsed
    }


# ============================================================
# TESTE TED POR PAÍS
# ============================================================

@app.get("/api/test-ted-country")
def test_ted_country(
    country: str = "MAR"
):

    country = country.strip().upper()

    test_query = (
        f'FT~"works" '
        f'AND buyer-country={country}'
    )

    payload = {

        "query": test_query,

        "fields": TED_FIELDS,

        "page": 1,

        "limit": 10,

        "scope": "ACTIVE",

        "checkQuerySyntax": False,

        "paginationMode":
            "PAGE_NUMBER"
    }

    try:

        response = requests.post(
            TED_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT
        )

        return {
            "ok": (
                response.status_code
                == 200
            ),

            "status_code":
                response.status_code,

            "query":
                test_query,

            "response":
                response.json()
        }

    except Exception as exc:

        return {
            "ok": False,
            "query": test_query,
            "error": str(exc)
        }


# ============================================================
# TESTE TED MINIMAL
# ============================================================

@app.get("/api/test-ted-minimal")
def test_ted_minimal():

    test_query = "FT~archaeological"

    payload = {

        "query": test_query,

        "fields": [
            "publication-number",
            "publication-date",
            "notice-title"
        ],

        "page": 1,

        "limit": 10,

        "scope": "ACTIVE",

        "checkQuerySyntax": False,

        "paginationMode":
            "PAGE_NUMBER"
    }

    try:

        response = requests.post(
            TED_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT
        )

        return {
            "ok": (
                response.status_code
                == 200
            ),

            "status_code":
                response.status_code,

            "query":
                test_query,

            "response":
                response.json()
        }

    except Exception as exc:

        return {
            "ok": False,
            "query": test_query,
            "error": str(exc)
        }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    automatic_sources = [
        source
        for source in SOURCES
        if source.get("automatic")
    ]

    return {

        "ok": True,

        "service":
            "Arqueologia Radar",

        "version":
            "2.0",

        "sources":
            len(SOURCES),

        "automatic_sources":
            len(automatic_sources),

        "date":
            date.today().isoformat()

    }


# ============================================================
# PÁGINA PRINCIPAL
# ============================================================

@app.get("/")
def root():

    file = BASE_DIR / "index.html"

    if file.exists():

        return FileResponse(
            file
        )

    return JSONResponse({

        "ok": True,

        "service":
            "Arqueologia Radar",

        "message":
            "index.html não encontrado"

    })


# ============================================================
# APP.JS
# ============================================================

@app.get("/app.js")
def app_js():

    file = BASE_DIR / "app.js"

    if file.exists():

        return FileResponse(
            file,
            media_type="application/javascript"
        )

    return JSONResponse({

        "ok": False,

        "error":
            "app.js não encontrado"

    })


# ============================================================
# MANIFEST
# ============================================================

@app.get("/manifest.json")
def manifest():

    file = BASE_DIR / "manifest.json"

    if file.exists():

        return FileResponse(
            file,
            media_type="application/manifest+json"
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
