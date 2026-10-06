from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from pathlib import Path
from datetime import date, datetime, timedelta
import time
import html
import re
import requests
import unicodedata


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Arqueologia Radar",
    version="2.6.0",
)

REQUEST_TIMEOUT = 30
PERIOD_DAYS = 365

# TED permite até 250 resultados por página.
PAGE_SIZE = 250

TED_URL = "https://api.ted.europa.eu/v3/notices/search"

WORLD_BANK_URL = (
    "https://search.worldbank.org/api/v2/procnotices"
)

SECOP_URL = (
    "https://www.datos.gov.co/resource/p6dx-8zbt.json"
)

BRAZIL_URL = (
    "https://dadosabertos.compras.gov.br/"
    "modulo-contratacoes/1_consultarContratacoes_PNCP_14133"
)


# ============================================================
# FONTES
# ============================================================

SOURCES = [
    {
        "name": "TED — Europa",
        "type": "api",
        "automatic": True,
        "url": "https://ted.europa.eu/",
    },
    {
        "name": "World Bank Procurement",
        "type": "api",
        "automatic": True,
        "url": "https://projects.worldbank.org/",
    },
    {
        "name": "SECOP II — Colômbia",
        "type": "api",
        "automatic": True,
        "url": "https://www.datos.gov.co/",
    },
    {
        "name": "PNCP — Brasil",
        "type": "api",
        "automatic": True,
        "url": "https://www.gov.br/pncp/",
    },

    {
        "name": "South Africa eTenders",
        "type": "portal",
        "automatic": False,
        "url": "https://www.etenders.gov.za/",
    },
    {
        "name": "African Development Bank",
        "type": "portal",
        "automatic": False,
        "url": "https://www.afdb.org/",
    },
    {
        "name": "SAM.gov",
        "type": "portal",
        "automatic": False,
        "url": "https://sam.gov/",
    },
    {
        "name": "BASE Portugal",
        "type": "portal",
        "automatic": False,
        "url": "https://www.base.gov.pt/",
    },
    {
        "name": "Espanha",
        "type": "portal",
        "automatic": False,
        "url": "https://contrataciondelestado.es/",
    },
    {
        "name": "UNDB",
        "type": "portal",
        "automatic": False,
        "url": "https://devbusiness.un.org/",
    },
    {
        "name": "UNGM",
        "type": "portal",
        "automatic": False,
        "url": "https://www.ungm.org/",
    },
    {
        "name": "EBRD",
        "type": "portal",
        "automatic": False,
        "url": "https://www.ebrd.com/",
    },
    {
        "name": "EIB",
        "type": "portal",
        "automatic": False,
        "url": "https://www.eib.org/",
    },
    {
        "name": "Oman",
        "type": "portal",
        "automatic": False,
        "url": "https://etendering.tenderboard.gov.om/",
    },
    {
        "name": "Saudi Etimad",
        "type": "portal",
        "automatic": False,
        "url": "https://tenders.etimad.sa/",
    },
    {
        "name": "UAE",
        "type": "portal",
        "automatic": False,
        "url": "https://mof.gov.ae/",
    },
    {
        "name": "Qatar",
        "type": "portal",
        "automatic": False,
        "url": "https://monaqasat.mof.gov.qa/",
    },
    {
        "name": "Morocco",
        "type": "portal",
        "automatic": False,
        "url": "https://www.marchespublics.gov.ma/",
    },
    {
        "name": "Uganda",
        "type": "portal",
        "automatic": False,
        "url": "https://www.ppda.go.ug/",
    },
    {
        "name": "Kenya",
        "type": "portal",
        "automatic": False,
        "url": "https://tenders.go.ke/",
    },
    {
        "name": "Tanzania",
        "type": "portal",
        "automatic": False,
        "url": "https://www.ppra.go.tz/",
    },
    {
        "name": "Mozambique",
        "type": "portal",
        "automatic": False,
        "url": "https://www.ufsa.gov.mz/",
    },
    {
        "name": "ChileCompra",
        "type": "portal",
        "automatic": False,
        "url": "https://www.mercadopublico.cl/",
    },
    {
        "name": "IDB",
        "type": "portal",
        "automatic": False,
        "url": "https://www.iadb.org/",
    },
    {
        "name": "ADB",
        "type": "portal",
        "automatic": False,
        "url": "https://www.adb.org/",
    },
    {
        "name": "AusTender",
        "type": "portal",
        "automatic": False,
        "url": "https://www.tenders.gov.au/",
    },
    {
        "name": "NZ GETS",
        "type": "portal",
        "automatic": False,
        "url": "https://www.gets.govt.nz/",
    },
    {
        "name": "Redeia",
        "type": "portal",
        "automatic": False,
        "url": "https://www.ree.es/",
    },
]


# ============================================================
# TERMOS
# ============================================================

DIRECT_TERMS = [
    "archaeology",
    "archaeological",
    "archaeologist",
    "archaeological excavation",
    "archaeological monitoring",
    "archaeological survey",
    "archaeological investigation",
    "archaeological services",
    "archaeological assessment",
    "archaeological fieldwork",
    "watching brief",

    "archéologie",
    "archéologique",
    "archéologue",
    "fouille archéologique",
    "surveillance archéologique",
    "diagnostic archéologique",

    "arqueologia",
    "arqueológico",
    "arqueóloga",
    "arqueólogo",
    "escavação arqueológica",
    "acompanhamento arqueológico",
    "prospeção arqueológica",
    "prospecção arqueológica",
    "sondagem arqueológica",

    "archäologie",
    "archäologisch",
    "archäologische ausgrabung",

    "archeologie",
    "archeologisch",
]


HERITAGE_TERMS = [
    "cultural heritage",
    "heritage",
    "historic environment",
    "historical environment",
    "built heritage",
    "archaeological heritage",
    "historic site",
    "historical site",
    "monument",
    "monuments",
    "unesco",
    "cultural property",

    "patrimoine culturel",
    "patrimoine",
    "monument historique",
    "site historique",

    "património cultural",
    "patrimônio cultural",
    "património",
    "patrimonio cultural",
    "monumento",
    "sítio arqueológico",
    "sitio arqueologico",

    "kulturerbe",
    "kulturelles erbe",

    "cultureel erfgoed",
]


MAJOR_PROJECT_TERMS = [
    "railway",
    "rail",
    "road",
    "highway",
    "bridge",
    "tunnel",
    "airport",
    "port",
    "mining",
    "mine",
    "pipeline",
    "gas pipeline",
    "oil pipeline",
    "energy",
    "power",
    "substation",
    "transmission line",
    "construction",
    "infrastructure",
    "water supply",
    "dam",

    "ferroviaire",
    "route",
    "autoroute",
    "pont",
    "tunnel",
    "aéroport",
    "port",
    "mine",
    "pipeline",
    "énergie",
    "construction",
    "infrastructure",

    "ferrovia",
    "rodovia",
    "estrada",
    "ponte",
    "túnel",
    "aeroporto",
    "porto",
    "mineração",
    "oleoduto",
    "gasoduto",
    "energia",
    "construção",
    "infraestrutura",
]


SUPPORT_EXCLUSIONS = [
    "photography",
    "photographic",
    "architect",
    "architecture services",
    "legal services",
    "marketing",
    "advertising",
    "software",
    "printing",
]


ARCHAEOLOGY_CPVS = [
    "71351914",
    "71351910",
    "71351900",
    "71351720",
    "71351811",
    "71351730",
]

GENERAL_EXCAVATION_CPV = "45112450"


AUTOMATIC_TERMS_TED = [
    "archaeology",
    "archaeological",
    "archaeologist",
    "archaeological excavation",
    "archaeological monitoring",
    "archaeological survey",
    "archaeological investigation",
    "archaeological services",
    "archaeological assessment",
    "archaeological fieldwork",
    "watching brief",

    "archéologie",
    "archéologique",
    "archéologue",
    "fouille archéologique",
    "surveillance archéologique",
    "diagnostic archéologique",

    "arqueologia",
    "arqueológico",
    "escavação arqueológica",
    "acompanhamento arqueológico",
    "prospeção arqueológica",
    "prospecção arqueológica",

    "archäologie",
    "archäologisch",

    "archeologie",
    "archeologisch",
]


AUTOMATIC_TERMS_WORLD_BANK = [
    "archaeology",
    "archaeological",
    "archaeologist",
    "archaeological excavation",
    "archaeological monitoring",
    "cultural heritage",
    "heritage",
    "arqueologia",
    "patrimonio cultural",
]


AUTOMATIC_TERMS_SECOP = [
    "archaeology",
    "archaeological",
    "archaeologist",
    "archaeological excavation",
    "archaeological monitoring",
    "cultural heritage",
    "heritage",
    "arqueologia",
    "arqueológico",
]


AUTOMATIC_TERMS_BRAZIL = [
    "archaeology",
    "archaeological",
    "archaeologist",
    "arqueologia",
    "arqueológico",
]


# ============================================================
# PAÍSES
# ============================================================

COUNTRY_MAP = {
    "PT": "Portugal",
    "ES": "Espanha",
    "FR": "França",
    "DE": "Alemanha",
    "IT": "Itália",
    "NL": "Países Baixos",
    "BE": "Bélgica",
    "LU": "Luxemburgo",
    "IE": "Irlanda",
    "GB": "Reino Unido",
    "UK": "Reino Unido",
    "CH": "Suíça",
    "AT": "Áustria",
    "PL": "Polónia",
    "CZ": "Chéquia",
    "SK": "Eslováquia",
    "HU": "Hungria",
    "RO": "Roménia",
    "BG": "Bulgária",
    "GR": "Grécia",
    "HR": "Croácia",
    "SI": "Eslovénia",
    "SE": "Suécia",
    "NO": "Noruega",
    "DK": "Dinamarca",
    "FI": "Finlândia",
    "EE": "Estónia",
    "LV": "Letónia",
    "LT": "Lituânia",
    "MT": "Malta",
    "CY": "Chipre",
    "IS": "Islândia",

    "MA": "Marrocos",
    "DZ": "Argélia",
    "TN": "Tunísia",
    "EG": "Egito",
    "ZA": "África do Sul",
    "KE": "Quénia",
    "UG": "Uganda",
    "TZ": "Tanzânia",
    "MZ": "Moçambique",
    "GH": "Gana",
    "NG": "Nigéria",
    "SN": "Senegal",
    "ET": "Etiópia",

    "US": "Estados Unidos",
    "CA": "Canadá",
    "MX": "México",
    "BR": "Brasil",
    "AR": "Argentina",
    "CL": "Chile",
    "CO": "Colômbia",
    "PE": "Peru",
    "UY": "Uruguai",
    "PY": "Paraguai",
    "BO": "Bolívia",
    "EC": "Equador",

    "CN": "China",
    "JP": "Japão",
    "KR": "Coreia do Sul",
    "IN": "Índia",
    "ID": "Indonésia",
    "MY": "Malásia",
    "TH": "Tailândia",
    "VN": "Vietname",
    "PH": "Filipinas",
    "AU": "Austrália",
    "NZ": "Nova Zelândia",

    "SA": "Arábia Saudita",
    "AE": "Emirados Árabes Unidos",
    "QA": "Qatar",
    "OM": "Omã",
}


ISO3_MAP = {
    "PT": "PRT",
    "ES": "ESP",
    "FR": "FRA",
    "DE": "DEU",
    "IT": "ITA",
    "NL": "NLD",
    "BE": "BEL",
    "LU": "LUX",
    "IE": "IRL",
    "GB": "GBR",
    "UK": "GBR",
    "CH": "CHE",
    "AT": "AUT",
    "PL": "POL",
    "CZ": "CZE",
    "SK": "SVK",
    "HU": "HUN",
    "RO": "ROU",
    "BG": "BGR",
    "GR": "GRC",
    "HR": "HRV",
    "SI": "SVN",
    "SE": "SWE",
    "NO": "NOR",
    "DK": "DNK",
    "FI": "FIN",
    "EE": "EST",
    "LV": "LVA",
    "LT": "LTU",
    "MT": "MLT",
    "CY": "CYP",
    "IS": "ISL",

    "MA": "MAR",
    "DZ": "DZA",
    "TN": "TUN",
    "EG": "EGY",
    "ZA": "ZAF",
    "KE": "KEN",
    "UG": "UGA",
    "TZ": "TZA",
    "MZ": "MOZ",
    "GH": "GHA",
    "NG": "NGA",
    "SN": "SEN",
    "ET": "ETH",

    "US": "USA",
    "CA": "CAN",
    "MX": "MEX",
    "BR": "BRA",
    "AR": "ARG",
    "CL": "CHL",
    "CO": "COL",
    "PE": "PER",
    "UY": "URY",
    "PY": "PRY",
    "BO": "BOL",
    "EC": "ECU",

    "CN": "CHN",
    "JP": "JPN",
    "KR": "KOR",
    "IN": "IND",
    "ID": "IDN",
    "MY": "MYS",
    "TH": "THA",
    "VN": "VNM",
    "PH": "PHL",
    "AU": "AUS",
    "NZ": "NZL",

    "SA": "SAU",
    "AE": "ARE",
    "QA": "QAT",
    "OM": "OMN",
}


REGION_COUNTRIES = {
    "Europa": {
        "PT", "ES", "FR", "DE", "IT", "NL", "BE", "LU",
        "IE", "GB", "UK", "CH", "AT", "PL", "CZ", "SK",
        "HU", "RO", "BG", "GR", "HR", "SI", "SE", "NO",
        "DK", "FI", "EE", "LV", "LT", "MT", "CY", "IS",
    },

    "África": {
        "MA", "DZ", "TN", "EG", "ZA", "KE", "UG", "TZ",
        "MZ", "GH", "NG", "SN", "ET",
    },

    "América": {
        "US", "CA", "MX", "BR", "AR", "CL", "CO", "PE",
        "UY", "PY", "BO", "EC",
    },

    "Ásia": {
        "CN", "JP", "KR", "IN", "ID", "MY", "TH", "VN",
        "PH", "SA", "AE", "QA", "OM",
    },

    "Oceania": {
        "AU", "NZ",
    },
}


# ============================================================
# FUNÇÕES GERAIS
# ============================================================

def normalize_text(value):
    if value is None:
        return ""

    if isinstance(value, dict):
        values = flatten_values(value)
        return " ".join(
            str(item)
            for item in values
            if item not in (None, "")
        ).strip()

    if isinstance(value, list):
        return " ".join(
            str(item)
            for item in value
            if item not in (None, "")
        ).strip()

    text = str(value)

    text = html.unescape(text)

    return text.strip()


def normalize_for_search(value):
    text = normalize_text(value)

    text = unicodedata.normalize(
        "NFKD",
        text,
    )

    text = "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )

    text = text.lower()

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


def repair_mojibake(value):
    if not value:
        return ""

    text = str(value)

    replacements = {
        "Ã¡": "á",
        "Ã©": "é",
        "Ã­": "í",
        "Ã³": "ó",
        "Ãº": "ú",
        "Ã£": "ã",
        "Ãµ": "õ",
        "Ã§": "ç",
        "Ã€": "À",
        "Ã‰": "É",
        "Ã‡": "Ç",
        "â€“": "–",
        "â€”": "—",
        "â€œ": "“",
        "â€": "”",
        "â€˜": "‘",
        "â€™": "’",
        "Â": "",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    return text


def parse_date(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    text = str(value).strip()

    if not text:
        return None

    # Remove espaços e variantes comuns do TED.
    text = text.replace(" ", "")

    formats = [
        "%Y-%m-%d",
        "%Y-%m-%d+%H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%d/%m/%Y",
        "%Y/%m/%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(
                text,
                fmt,
            ).date()
        except Exception:
            pass

    try:
        return datetime.fromisoformat(
            text.replace("Z", "+00:00")
        ).date()
    except Exception:
        return None


def cutoff_date():
    return date.today() - timedelta(
        days=PERIOD_DAYS
    )


def recent_enough(value):
    parsed = parse_date(value)

    if parsed is None:
        return False

    return parsed >= cutoff_date()


def flatten_values(value):
    if value is None:
        return []

    if isinstance(value, list):
        output = []

        for item in value:
            output.extend(
                flatten_values(item)
            )

        return output

    if isinstance(value, dict):
        output = []

        # Para estruturas multilingues do TED,
        # damos preferência aos valores.
        for item in value.values():
            output.extend(
                flatten_values(item)
            )

        return output

    return [value]


def recursive_find(data, keys):
    if isinstance(data, dict):

        for key in keys:
            if key in data and data[key] not in (
                None,
                "",
                [],
            ):
                return data[key]

        for value in data.values():
            found = recursive_find(
                value,
                keys,
            )

            if found not in (
                None,
                "",
                [],
            ):
                return found

    elif isinstance(data, list):

        for item in data:
            found = recursive_find(
                item,
                keys,
            )

            if found not in (
                None,
                "",
                [],
            ):
                return found

    return None


def first_value(data, keys):
    return recursive_find(
        data,
        keys,
    )


def safe_first_text(data, keys):
    value = first_value(
        data,
        keys,
    )

    values = flatten_values(value)

    for item in values:
        text = normalize_text(item)

        if text:
            return text

    return ""


# ============================================================
# PAÍS / REGIÃO
# ============================================================

def country_from_text(value):
    text = normalize_for_search(value)

    if not text:
        return ""

    # Primeiro códigos ISO2 isolados.
    if len(text) == 2:
        for code in COUNTRY_MAP:
            if code.lower() == text:
                return code

    # Depois ISO3.
    if len(text) == 3:
        for code, iso3 in ISO3_MAP.items():
            if iso3.lower() == text:
                return code

    for code, name in COUNTRY_MAP.items():

        if normalize_for_search(name) == text:
            return code

        if (
            len(text) > 2
            and normalize_for_search(name) in text
        ):
            return code

    return ""


def country_name(code):
    if not code:
        return ""

    code = str(code).upper().strip()

    if code in COUNTRY_MAP:
        return COUNTRY_MAP[code]

    for iso2, iso3 in ISO3_MAP.items():
        if code == iso3:
            return COUNTRY_MAP.get(
                iso2,
                code,
            )

    return code


def region_from_country(code):
    if not code:
        return ""

    code = str(code).upper().strip()

    for region, countries in REGION_COUNTRIES.items():
        if code in countries:
            return region

    for iso2, iso3 in ISO3_MAP.items():
        if code == iso3:
            for region, countries in REGION_COUNTRIES.items():
                if iso2 in countries:
                    return region

    return ""


# ============================================================
# CPV
# ============================================================

def cpv_values(value):
    values = flatten_values(value)

    result = []

    for item in values:

        text = normalize_text(item)

        if not text:
            continue

        matches = re.findall(
            r"\b\d{8}\b",
            text,
        )

        result.extend(matches)

    return list(
        dict.fromkeys(result)
    )


# ============================================================
# CLASSIFICAÇÃO
# ============================================================

def has_direct_archaeology(text):
    normalized = normalize_for_search(text)

    for term in DIRECT_TERMS:

        if normalize_for_search(term) in normalized:
            return True

    return False


def has_heritage(text):
    normalized = normalize_for_search(text)

    for term in HERITAGE_TERMS:

        if normalize_for_search(term) in normalized:
            return True

    return False


def has_major_project(text):
    normalized = normalize_for_search(text)

    for term in MAJOR_PROJECT_TERMS:

        if normalize_for_search(term) in normalized:
            return True

    return False


def classify_result(
    title,
    description,
    cpvs,
    search_mode="direct",
):
    text = (
        normalize_text(title)
        + " "
        + normalize_text(description)
    )

    direct = has_direct_archaeology(text)
    heritage = has_heritage(text)
    major = has_major_project(text)

    cpv_direct = any(
        cpv in ARCHAEOLOGY_CPVS
        for cpv in cpvs
    )

    if search_mode == "direct":

        if direct:
            return "Arqueologia direta"

        if cpv_direct:
            return "Arqueologia direta"

        return ""

    if direct:
        return "Arqueologia direta"

    if heritage and major:
        return "Património / grandes projetos"

    if heritage:
        return "Património cultural"

    if cpv_direct:
        return "Arqueologia direta"

    return ""


# ============================================================
# CONSTRUÇÃO DE RESULTADOS
# ============================================================

def make_result(
    title,
    description,
    buyer,
    country,
    source,
    url,
    published,
    deadline,
    cpvs,
    search_mode="direct",
):
    title = repair_mojibake(
        normalize_text(title)
    )

    description = repair_mojibake(
        normalize_text(description)
    )

    buyer = repair_mojibake(
        normalize_text(buyer)
    )

    country = str(
        country or ""
    ).upper().strip()

    if len(country) == 3:
        country_name_value = country_name(country)
        country_code = country_from_text(country)
    else:
        country_code = country_from_text(country)
        country_name_value = country_name(
            country_code
        )

    classification = classify_result(
        title,
        description,
        cpvs,
        search_mode,
    )

    if not classification:
        return None

    score = (
        100
        if classification == "Arqueologia direta"
        else 70
    )

    published_date = parse_date(
        published
    )

    deadline_date = parse_date(
        deadline
    )

    return {
        "title": title,
        "description": description,
        "buyer": buyer,
        "country": country_name_value,
        "country_code": country_code,
        "region": region_from_country(
            country_code
        ),
        "source": source,
        "url": url or "",
        "date": (
            published_date.isoformat()
            if published_date
            else ""
        ),
        "deadline": (
            deadline_date.isoformat()
            if deadline_date
            else ""
        ),
        "cpv": cpvs,
        "classification": classification,
        "score": score,
    }


# ============================================================
# TED
# ============================================================

TED_FIELDS = [
    "publication-number",
    "publication-date",
    "notice-title",
    "buyer-name",
    "organisation-country-buyer",
    "buyer-country",
    "classification-cpv",
    "description-proc",
    "description-glo",
    "deadline-date-lot",
]


def build_ted_query(term):
    term = normalize_text(term)

    return f'FT~"{term}"'

def query_ted(
    term,
    diagnostics=None,
    search_mode="direct",
    country_code=None,
):
    if diagnostics is None:
        diagnostics = []

    # --------------------------------------------------------
    # PERÍODO
    # --------------------------------------------------------
    today = date.today()
    start_date = today - timedelta(days=PERIOD_DAYS)

    start_ted = start_date.strftime("%Y%m%d")
    end_ted = today.strftime("%Y%m%d")

    # --------------------------------------------------------
    # QUERY TED
    # --------------------------------------------------------
    query_parts = [
        f'FT~"{normalize_text(term)}"',
        f"publication-date>={start_ted}",
        f"publication-date<={end_ted}",
    ]

    # --------------------------------------------------------
    # PAÍS — OPCIONAL
    # --------------------------------------------------------
    if country_code:
        country_code = str(
            country_code
        ).strip().upper()

        if country_code:
            query_parts.append(
                f"buyer-country={country_code}"
            )
    else:
        country_code = ""

    query = " AND ".join(query_parts)

    payload = {
        "query": query,
        "fields": TED_FIELDS,
        "page": 1,
        "limit": PAGE_SIZE,
        "paginationMode": "PAGE_NUMBER",
    }

    time.sleep(0.20)

    try:

        response = requests.post(
            TED_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

        diagnostics.append({
            "source": "TED — Europa",
            "term": term,
            "method": "POST",
            "status_code": response.status_code,
            "query": query,
            "period_start": start_date.isoformat(),
            "period_end": today.isoformat(),
            "country_code": country_code,
        })

        if response.status_code == 429:

            diagnostics[-1]["error"] = (
                "TED rate limit (429)"
            )

            time.sleep(2)

            try:

                response = requests.post(
                    TED_URL,
                    json=payload,
                    timeout=REQUEST_TIMEOUT,
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                    },
                )

                diagnostics[-1]["retry_status_code"] = (
                    response.status_code
                )

            except Exception as retry_exc:

                diagnostics[-1]["retry_error"] = (
                    str(retry_exc)
                )

                return []

        if response.status_code != 200:

            diagnostics[-1]["error"] = (
                response.text[:1000]
            )

            return []

        data = response.json()

        notices = data.get(
            "notices",
            [],
        )

        if isinstance(
            notices,
            dict,
        ):
            notices = list(
                notices.values()
            )

        results = []

        for notice in notices:

            if not isinstance(
                notice,
                dict,
            ):
                continue

            title = safe_first_text(
                notice,
                [
                    "notice-title",
                    "title",
                ],
            )

            description = safe_first_text(
                notice,
                [
                    "description-proc",
                    "description-glo",
                    "description",
                    "short-description",
                    "notice-description",
                ],
            )

            buyer = safe_first_text(
                notice,
                [
                    "buyer-name",
                    "buyer",
                    "buyer-name-value",
                ],
            )

            country = safe_first_text(
                notice,
                [
                    "organisation-country-buyer",
                    "buyer-country",
                    "country",
                ],
            )

            published = safe_first_text(
                notice,
                [
                    "publication-date",
                    "publicationDate",
                ],
            )

            deadline = safe_first_text(
                notice,
                [
                    "deadline-date-lot",
                    "deadline-date",
                    "deadlineDate",
                ],
            )

            publication_number = safe_first_text(
                notice,
                [
                    "publication-number",
                    "publicationNumber",
                ],
            )

            cpvs = cpv_values(
                first_value(
                    notice,
                    [
                        "classification-cpv",
                        "cpv",
                        "CPV",
                    ],
                )
            )

            if not recent_enough(
                published
            ):
                continue

            url = ""

            if publication_number:

                url = (
                    "https://ted.europa.eu/en/notice/"
                    + str(publication_number)
                )

            result = make_result(
                title=title,
                description=description,
                buyer=buyer,
                country=country,
                source="TED — Europa",
                url=url,
                published=published,
                deadline=deadline,
                cpvs=cpvs,
                search_mode=search_mode,
            )

            if result is None:
                continue

            results.append(result)

        return results

    except Exception as exc:

        diagnostics.append({
            "source": "TED — Europa",
            "term": term,
            "method": "POST",
            "query": query,
            "error": str(exc),
        })

        return []


# ============================================================
# WORLD BANK
# ============================================================

def query_world_bank(
    term,
    diagnostics=None,
    search_mode="direct",
):
    if diagnostics is None:
        diagnostics = []

    try:

        params = {
            "qterm": term,
            "rows": PAGE_SIZE,
            "format": "json",
        }

        response = requests.get(
            WORLD_BANK_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

        diagnostics.append({
            "source": "World Bank Procurement",
            "term": term,
            "method": "GET",
            "status_code": response.status_code,
        })

        if response.status_code != 200:
            diagnostics[-1]["error"] = (
                response.text[:1000]
            )
            return []

        data = response.json()

        notices = (
            data.get("procurements")
            or data.get("notices")
            or data.get("results")
            or []
        )

        if isinstance(
            notices,
            dict,
        ):
            notices = list(
                notices.values()
            )

        results = []

        for item in notices:

            if not isinstance(
                item,
                dict,
            ):
                continue

            title = first_value(
                item,
                [
                    "project_name",
                    "title",
                    "notice_title",
                    "procurement_name",
                    "contract_description",
                ],
            )

            description = first_value(
                item,
                [
                    "description",
                    "short_description",
                    "procurement_description",
                    "contract_description",
                ],
            )

            buyer = first_value(
                item,
                [
                    "borrower",
                    "buyer",
                    "client",
                    "country_name",
                ],
            )

            country = first_value(
                item,
                [
                    "countrycode",
                    "country_code",
                    "country",
                ],
            )

            published = first_value(
                item,
                [
                    "publication_date",
                    "published_date",
                    "notice_date",
                    "date",
                ],
            )

            deadline = first_value(
                item,
                [
                    "deadline",
                    "submission_deadline",
                    "bid_deadline",
                ],
            )

            url = first_value(
                item,
                [
                    "url",
                    "notice_url",
                    "procurement_url",
                    "link",
                ],
            )

            cpvs = cpv_values(
                first_value(
                    item,
                    [
                        "cpv",
                        "cpvs",
                        "classification",
                    ],
                )
            )

            result = make_result(
                title=title,
                description=description,
                buyer=buyer,
                country=country,
                source="World Bank Procurement",
                url=url,
                published=published,
                deadline=deadline,
                cpvs=cpvs,
                search_mode=search_mode,
            )

            if result is None:
                continue

            if not recent_enough(
                result.get("date")
            ):
                continue

            results.append(result)

        return results

    except Exception as exc:

        diagnostics.append({
            "source": "World Bank Procurement",
            "term": term,
            "method": "GET",
            "error": str(exc),
        })

        return []


# ============================================================
# SECOP II — COLÔMBIA
# ============================================================

def query_secop(
    term,
    diagnostics=None,
    search_mode="direct",
):
    if diagnostics is None:
        diagnostics = []

    try:

        params = {
            "$limit": 1000,
            "$q": term,
        }

        response = requests.get(
            SECOP_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

        diagnostics.append({
            "source": "SECOP II — Colômbia",
            "term": term,
            "method": "GET",
            "status_code": response.status_code,
        })

        if response.status_code != 200:
            diagnostics[-1]["error"] = (
                response.text[:1000]
            )
            return []

        data = response.json()

        if not isinstance(
            data,
            list,
        ):
            return []

        results = []

        term_normalized = normalize_for_search(
            term
        )

        for item in data:

            if not isinstance(
                item,
                dict,
            ):
                continue

            title = first_value(
                item,
                [
                    "descripcion_del_proceso",
                    "nombre_del_procedimiento",
                    "titulo",
                    "description",
                ],
            )

            description = first_value(
                item,
                [
                    "descripcion",
                    "description",
                    "objeto",
                ],
            )

            combined = normalize_for_search(
                f"{title or ''} {description or ''}"
            )

            if term_normalized not in combined:
                continue

            buyer = first_value(
                item,
                [
                    "nombre_entidad",
                    "entidad",
                    "buyer",
                ],
            )

            published = first_value(
                item,
                [
                    "fecha_de_publicacion",
                    "fecha_publicacion",
                    "fecha_de_ultima_publicacion",
                ],
            )

            deadline = first_value(
                item,
                [
                    "fecha_de_recepcion_de_respuestas",
                    "fecha_de_cierre",
                    "fecha_cierre",
                ],
            )

            url = first_value(
                item,
                [
                    "urlproceso",
                    "url",
                ],
            )

            cpvs = cpv_values(
                first_value(
                    item,
                    [
                        "codigo_principal_de_categoria",
                        "codigo_unspsc",
                        "cpv",
                    ],
                )
            )

            result = make_result(
                title=title,
                description=description,
                buyer=buyer,
                country="CO",
                source="SECOP II — Colômbia",
                url=url,
                published=published,
                deadline=deadline,
                cpvs=cpvs,
                search_mode=search_mode,
            )

            if result is None:
                continue

            if not recent_enough(
                result.get("date")
            ):
                continue

            results.append(result)

        return results

    except Exception as exc:

        diagnostics.append({
            "source": "SECOP II — Colômbia",
            "term": term,
            "method": "GET",
            "error": str(exc),
        })

        return []


# ============================================================
# PNCP — BRASIL
# ============================================================

BRAZIL_MAX_PAGES = 1


def query_brazil(
    term,
    diagnostics=None,
    search_mode="direct",
):
    if diagnostics is None:
        diagnostics = []

    results = []

    modalities = [
        4,
        5,
        6,
        7,
        12,
    ]

    start_date = cutoff_date().isoformat()
    end_date = date.today().isoformat()

    for modality in modalities:

        for page in range(
            1,
            BRAZIL_MAX_PAGES + 1,
        ):

            params = {
                "dataInicial": start_date,
                "dataFinal": end_date,
                "codigoModalidadeContratacao": modality,
                "pagina": page,
                "tamanhoPagina": 50,
            }

            try:

                response = requests.get(
                    BRAZIL_URL,
                    params=params,
                    timeout=REQUEST_TIMEOUT,
                )

                diagnostics.append({
                    "source": "PNCP — Brasil",
                    "term": term,
                    "method": "GET",
                    "modality": modality,
                    "page": page,
                    "status_code": response.status_code,
                })

                if response.status_code != 200:
                    diagnostics[-1]["error"] = (
                        response.text[:1000]
                    )
                    continue

                data = response.json()

                items = (
                    data.get("data")
                    if isinstance(
                        data,
                        dict,
                    )
                    else data
                )

                if not isinstance(
                    items,
                    list,
                ):
                    continue

                term_normalized = normalize_for_search(
                    term
                )

                for item in items:

                    if not isinstance(
                        item,
                        dict,
                    ):
                        continue

                    title = first_value(
                        item,
                        [
                            "objetoCompra",
                            "objeto",
                            "descricao",
                            "description",
                        ],
                    )

                    description = first_value(
                        item,
                        [
                            "objetoCompra",
                            "objeto",
                            "descricao",
                            "description",
                        ],
                    )

                    combined = normalize_for_search(
                        f"{title or ''} "
                        f"{description or ''}"
                    )

                    if (
                        term_normalized
                        not in combined
                    ):
                        continue

                    buyer = first_value(
                        item,
                        [
                            "razaoSocial",
                            "nomeUnidadeCompradora",
                            "orgaoEntidade",
                        ],
                    )

                    published = first_value(
                        item,
                        [
                            "dataPublicacaoPncp",
                            "dataPublicacao",
                            "dataInclusao",
                        ],
                    )

                    deadline = first_value(
                        item,
                        [
                            "dataFimVigencia",
                            "dataEncerramento",
                            "dataAberturaProposta",
                        ],
                    )

                    url = first_value(
                        item,
                        [
                            "linkSistemaOrigem",
                            "linkProcessoEletronico",
                            "url",
                        ],
                    )

                    cpvs = cpv_values(
                        first_value(
                            item,
                            [
                                "codigoItem",
                                "codigoCatmat",
                                "cpv",
                            ],
                        )
                    )

                    result = make_result(
                        title=title,
                        description=description,
                        buyer=buyer,
                        country="BR",
                        source="PNCP — Brasil",
                        url=url,
                        published=published,
                        deadline=deadline,
                        cpvs=cpvs,
                        search_mode=search_mode,
                    )

                    if result is None:
                        continue

                    if not recent_enough(
                        result.get("date")
                    ):
                        continue

                    results.append(result)

            except Exception as exc:

                diagnostics.append({
                    "source": "PNCP — Brasil",
                    "term": term,
                    "method": "GET",
                    "modality": modality,
                    "page": page,
                    "error": str(exc),
                })

    return results


# ============================================================
# PESQUISA AUTOMÁTICA
# ============================================================

def automatic_search(
    query,
    diagnostics,
):
    query_norm = normalize_for_search(
        query
    )

    mode = "direct"

    # --------------------------------------------------------
    # TERMOS
    # --------------------------------------------------------

    if query_norm in {
        "",
        "arqueologia",
        "archaeology",
        "archaeological",
    }:

        ted_terms = AUTOMATIC_TERMS_TED

        world_bank_terms = AUTOMATIC_TERMS_WORLD_BANK

        secop_terms = AUTOMATIC_TERMS_SECOP

        brazil_terms = AUTOMATIC_TERMS_BRAZIL

    else:

        ted_terms = [query]

        world_bank_terms = [query]

        secop_terms = [query]

        brazil_terms = [query]

    results = []

    # --------------------------------------------------------
    # TED — SEQUENCIAL
    #
    # Muito importante:
    # não lançamos 20+ pedidos TED simultaneamente.
    # Isso estava a provocar 429.
    # --------------------------------------------------------

    for term in ted_terms:

        try:

            ted_results = query_ted(
                term,
                diagnostics,
                mode,
            )

            results.extend(
                ted_results
            )

        except Exception as exc:

            diagnostics.append({
                "source": "TED — Europa",
                "term": term,
                "error": str(exc),
            })

        # Pequena pausa entre chamadas TED.
        time.sleep(0.15)

    # --------------------------------------------------------
    # OUTRAS FONTES
    #
    # Estas podem continuar paralelas porque não são
    # a origem do problema de rate-limit TED.
    # --------------------------------------------------------

    jobs = []

    for term in world_bank_terms:

        jobs.append(
            (
                "World Bank Procurement",
                query_world_bank,
                term,
                mode,
            )
        )

    for term in secop_terms:

        jobs.append(
            (
                "SECOP II — Colômbia",
                query_secop,
                term,
                mode,
            )
        )

    for term in brazil_terms:

        jobs.append(
            (
                "PNCP — Brasil",
                query_brazil,
                term,
                mode,
            )
        )

    if jobs:

        from concurrent.futures import (
            ThreadPoolExecutor,
            as_completed,
        )

        with ThreadPoolExecutor(
            max_workers=4
        ) as executor:

            futures = []

            for (
                source_name,
                function,
                term,
                mode,
            ) in jobs:

                futures.append(
                    executor.submit(
                        function,
                        term,
                        diagnostics,
                        mode,
                    )
                )

            for future in as_completed(
                futures
            ):

                try:

                    results.extend(
                        future.result()
                    )

                except Exception as exc:

                    diagnostics.append({
                        "source": "automatic",
                        "error": str(exc),
                    })

    return mode, results


# ============================================================
# FILTROS
# ============================================================

def filter_results(
    results,
    country="",
    region="",
):
    filtered = results

    country_norm = normalize_for_search(
        country
    )

    region_norm = normalize_for_search(
        region
    )

    if country_norm:

        requested_code = country_from_text(
            country
        )

        filtered = [
            item
            for item in filtered
            if (
                normalize_for_search(
                    item.get("country", "")
                )
                == country_norm
                or normalize_for_search(
                    item.get("country_code", "")
                )
                == country_norm
                or (
                    requested_code
                    and item.get("country_code")
                    == requested_code
                )
            )
        ]

    if region_norm:

        filtered = [
            item
            for item in filtered
            if normalize_for_search(
                item.get("region", "")
            ) == region_norm
        ]

    return filtered


# ============================================================
# DEDUPLICAÇÃO
# ============================================================

def deduplicate_results(
    results
):
    seen = set()
    output = []

    for item in results:

        # Primeiro tentamos identificar pelo URL.
        url = normalize_for_search(
            item.get("url", "")
        )

        if url:
            key = (
                "url",
                url,
            )

        else:

            key = (
                "text",
                normalize_for_search(
                    item.get("title", "")
                ),
                normalize_for_search(
                    item.get("buyer", "")
                ),
                normalize_for_search(
                    item.get("country_code", "")
                ),
                normalize_for_search(
                    item.get("source", "")
                ),
            )

        if key in seen:
            continue

        seen.add(key)
        output.append(item)

    return output


# ============================================================
# ORDENAÇÃO
# ============================================================

def sort_results(results):

    def sort_key(item):

        score = int(
            item.get(
                "score",
                0,
            )
        )

        result_date = item.get(
            "date",
            "",
        )

        return (
            -score,
            result_date or "0000-00-00",
        )

    results.sort(
        key=sort_key,
        reverse=True,
    )

    return results


# ============================================================
# ROTAS PRINCIPAIS
# ============================================================

@app.get("/")
def index():
    return FileResponse(
        BASE_DIR / "index.html"
    )


@app.get("/app.js")
def app_js():
    return FileResponse(
        BASE_DIR / "app.js",
        media_type="application/javascript",
    )


@app.get("/manifest.json")
def manifest():
    return FileResponse(
        BASE_DIR / "manifest.json",
        media_type="application/json",
    )


@app.get("/health")
def health():
    return {
        "ok": True,
        "version": "2.6.0",
        "sources": len(SOURCES),
        "api_sources": sum(
            1
            for source in SOURCES
            if source.get("automatic")
        ),
        "period_days": PERIOD_DAYS,
        "ted_page_size": PAGE_SIZE,
    }


@app.get("/api/sources")
def api_sources():
    return {
        "sources": SOURCES,
        "count": len(SOURCES),
        "automatic": sum(
            1
            for source in SOURCES
            if source.get("automatic")
        ),
    }


@app.get("/api/search")
def api_search(
    q: str = Query(
        default="archaeology"
    ),
    country: str = Query(
        default=""
    ),
    region: str = Query(
        default=""
    ),
):
    diagnostics = []

    mode, results = automatic_search(
        q,
        diagnostics,
    )

    results = deduplicate_results(
        results
    )

    results = filter_results(
        results,
        country=country,
        region=region,
    )

    results = sort_results(
        results
    )

    source_names = sorted(
        set(
            item.get(
                "source",
                "",
            )
            for item in results
            if item.get("source")
        )
    )

    regions = sorted(
        set(
            item.get(
                "region",
                "",
            )
            for item in results
            if item.get("region")
        )
    )

    return {
        "ok": True,
        "query": q,
        "mode": mode,
        "results": results,
        "count": len(results),
        "sources": source_names,
        "source_count": len(source_names),
        "regions": regions,
        "diagnostics": diagnostics,
    }


# ============================================================
# TESTE TED MÍNIMO — POST
# ============================================================

@app.get("/api/test-ted-minimal")
def test_ted_minimal(
    term: str = Query(
        default="archaeology"
    )
):
    query = build_ted_query(
        term
    )

    payload = {
        "query": query,
        "fields": TED_FIELDS,
        "page": 1,
        "limit": 10,
        "paginationMode": "PAGE_NUMBER",
    }

    try:

        response = requests.post(
            TED_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

        try:
            data = response.json()
        except Exception:
            data = response.text[:5000]

        return {
            "ok": response.status_code == 200,
            "status_code": response.status_code,
            "method": "POST",
            "query": query,
            "response": data,
        }

    except Exception as exc:

        return {
            "ok": False,
            "method": "POST",
            "query": query,
            "error": str(exc),
        }
        
@app.get("/api/test-ted-portugal")
def test_ted_portugal(term: str = "archaeology"):
    diagnostics = []

    results = query_ted(
        term,
        diagnostics=diagnostics,
        search_mode="direct",
    )

    portugal_results = [
        r for r in results
        if r.get("country_code") == "PT"
    ]

    return {
        "ok": True,
        "term": term,
        "count_total": len(results),
        "count_portugal": len(portugal_results),
        "results_portugal": portugal_results[:10],
        "diagnostics": diagnostics,
    }

# ============================================================
# TESTE TED POR PAÍS — POST
# ============================================================

@app.get("/api/test-ted-search")
def test_ted_search(term: str = "archaeology"):
    diagnostics = []

    results = query_ted(
        term,
        diagnostics=diagnostics,
        search_mode="direct",
    )

    return {
        "ok": True,
        "term": term,
        "count": len(results),
        "results": results[:10],
        "diagnostics": diagnostics,
    }

@app.get("/api/test-ted-country")
def test_ted_country(
    term: str = Query(
        default="archaeology"
    ),
    country: str = Query(
        default="PRT"
    ),
):
    query = (
        f'FT~"{term}" '
        f'AND buyer-country={country}'
    )

    payload = {
        "query": query,
        "fields": TED_FIELDS,
        "page": 1,
        "limit": 10,
        "paginationMode": "PAGE_NUMBER",
    }

    try:

        response = requests.post(
            TED_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
        )

        try:
            data = response.json()
        except Exception:
            data = response.text[:5000]

        return {
            "ok": response.status_code == 200,
            "status_code": response.status_code,
            "method": "POST",
            "query": query,
            "response": data,
        }

    except Exception as exc:

        return {
            "ok": False,
            "method": "POST",
            "query": query,
            "error": str(exc),
        }
