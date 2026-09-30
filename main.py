from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from pathlib import Path
from datetime import date, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


TED_URL = "https://api.ted.europa.eu/v3/notices/search"

WORLD_BANK_URL = (
    "https://search.worldbank.org/api/v2/procnotices"
)

REQUEST_TIMEOUT = 25

PERIOD_DAYS = 365

PAGE_SIZE = 250

MAX_PAGES_PER_TERM = 4


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
    "deadline",
]


# ============================================================
# TERMOS PRINCIPAIS
# ============================================================

DEFAULT_TERMS = [
    "archaeology",
    "archaeological",
    "excavation",
    "cultural heritage",
    "archaeological monitoring",
    "archaeological excavation",
    "archaeological services",
    "arqueologia",
    "património cultural",
    "patrimonio cultural",
]


# ============================================================
# REGIÕES
# ============================================================

REGIONS = {

    "Europa": {
        "ALB", "AND", "AUT", "BEL", "BGR", "BIH",
        "BLR", "CHE", "CYP", "CZE", "DEU", "DNK",
        "ESP", "EST", "FIN", "FRA", "GBR", "GRC",
        "HRV", "HUN", "IRL", "ISL", "ITA", "LIE",
        "LTU", "LUX", "LVA", "MCO", "MDA", "MKD",
        "MLT", "MNE", "NLD", "NOR", "POL", "PRT",
        "ROU", "RUS", "SMR", "SRB", "SVK", "SVN",
        "SWE", "UKR", "VAT", "XKX"
    },

    "África": {
        "DZA", "AGO", "BEN", "BWA", "BFA", "BDI",
        "CPV", "CMR", "CAF", "TCD", "COM", "COD",
        "COG", "CIV", "DJI", "EGY", "GNQ", "ERI",
        "SWZ", "ETH", "GAB", "GMB", "GHA", "GIN",
        "GNB", "GNQ", "KEN", "LSO", "LBR", "LBY",
        "MDG", "MWI", "MLI", "MRT", "MUS", "MAR",
        "MOZ", "NAM", "NER", "NGA", "RWA", "STP",
        "SEN", "SYC", "SLE", "SOM", "ZAF", "SSD",
        "SDN", "TZA", "TGO", "TUN", "UGA", "ZMB",
        "ZWE"
    },

    "Médio Oriente": {
        "ARE", "BHR", "IRN", "IRQ", "ISR", "JOR",
        "KWT", "LBN", "OMN", "PSE", "QAT", "SAU",
        "SYR", "TUR", "YEM"
    },

    "Américas": {
        "ARG", "BHS", "BLZ", "BOL", "BRA", "BRB",
        "CAN", "CHL", "COL", "CRI", "CUB", "DMA",
        "DOM", "ECU", "GRD", "GTM", "GUY", "HND",
        "HTI", "JAM", "KNA", "LCA", "MEX", "NIC",
        "PAN", "PER", "PRY", "SLV", "SUR", "TTO",
        "URY", "USA", "VEN"
    },

    "Ásia-Pacífico": {
        "AFG", "ARM", "AUS", "AZE", "BGD", "BTN",
        "BRN", "KHM", "CHN", "FJI", "GEO", "IDN",
        "IND", "JPN", "KAZ", "KGZ", "LAO", "LKA",
        "MDV", "MNG", "MYS", "NPL", "NZL", "PAK",
        "PHL", "PRK", "KOR", "SGP", "THA", "TJK",
        "TKM", "TLS", "UZB", "VNM"
    }
}


# ============================================================
# MAPA DE PAÍSES
# ============================================================

COUNTRY_NAMES = {

    "portugal": "PRT",
    "portugal continental": "PRT",

    "spain": "ESP",
    "españa": "ESP",
    "espana": "ESP",
    "espanha": "ESP",

    "france": "FRA",
    "frança": "FRA",
    "franca": "FRA",

    "germany": "DEU",
    "alemanha": "DEU",
    "deutschland": "DEU",

    "italy": "ITA",
    "italia": "ITA",

    "netherlands": "NLD",
    "países baixos": "NLD",
    "paises baixos": "NLD",

    "belgium": "BEL",
    "bélgica": "BEL",
    "belgica": "BEL",

    "ireland": "IRL",
    "irlanda": "IRL",

    "united kingdom": "GBR",
    "reino unido": "GBR",

    "malta": "MLT",

    "greece": "GRC",
    "grécia": "GRC",
    "grecia": "GRC",

    "poland": "POL",
    "polónia": "POL",
    "polonia": "POL",

    "romania": "ROU",
    "roménia": "ROU",
    "romenia": "ROU",

    "croatia": "HRV",
    "croácia": "HRV",
    "croacia": "HRV",

    "austria": "AUT",
    "áustria": "AUT",
    "austria": "AUT",

    "switzerland": "CHE",
    "suíça": "CHE",
    "suica": "CHE",

    "sweden": "SWE",
    "suécia": "SWE",
    "suecia": "SWE",

    "norway": "NOR",
    "noruega": "NOR",

    "denmark": "DNK",
    "dinamarca": "DNK",

    "finland": "FIN",
    "finlândia": "FIN",
    "finlandia": "FIN",

    "iceland": "ISL",
    "islândia": "ISL",
    "islandia": "ISL",

    "czech republic": "CZE",
    "czechia": "CZE",
    "república checa": "CZE",
    "republica checa": "CZE",

    "hungary": "HUN",
    "hungria": "HUN",

    "bulgaria": "BGR",
    "búlgaro": "BGR",
    "bulgaro": "BGR",

    "slovakia": "SVK",
    "eslováquia": "SVK",
    "eslovaquia": "SVK",

    "slovenia": "SVN",
    "eslovénia": "SVN",
    "eslovenia": "SVN",

    "serbia": "SRB",
    "sérvia": "SRB",
    "servia": "SRB",

    "north macedonia": "MKD",
    "macedónia do norte": "MKD",
    "macedonia do norte": "MKD",

    "albania": "ALB",
    "albânia": "ALB",
    "albania": "ALB",

    "bosnia and herzegovina": "BIH",
    "bósnia e herzegovina": "BIH",
    "bosnia e herzegovina": "BIH",

    "montenegro": "MNE",

    "moldova": "MDA",

    "ukraine": "UKR",
    "ucrânia": "UKR",
    "ucrania": "UKR",

    "russia": "RUS",
    "rússia": "RUS",
    "russia": "RUS",

    "morocco": "MAR",
    "marrocos": "MAR",

    "algeria": "DZA",
    "argélia": "DZA",
    "argelia": "DZA",

    "tunisia": "TUN",
    "tunísia": "TUN",
    "tunisia": "TUN",

    "egypt": "EGY",
    "egito": "EGY",

    "libya": "LBY",
    "líbia": "LBY",
    "libia": "LBY",

    "senegal": "SEN",

    "ghana": "GHA",
    "gana": "GHA",

    "nigeria": "NGA",
    "nigéria": "NGA",
    "nigeria": "NGA",

    "kenya": "KEN",
    "quénia": "KEN",
    "quenia": "KEN",

    "tanzania": "TZA",
    "tanzânia": "TZA",
    "tanzania": "TZA",

    "uganda": "UGA",

    "rwanda": "RWA",
    "ruanda": "RWA",

    "south africa": "ZAF",
    "áfrica do sul": "ZAF",
    "africa do sul": "ZAF",

    "mozambique": "MOZ",
    "moçambique": "MOZ",
    "mocambique": "MOZ",

    "angola": "AGO",

    "cape verde": "CPV",
    "cabo verde": "CPV",

    "guinea-bissau": "GNB",
    "guiné-bissau": "GNB",
    "guine-bissau": "GNB",

    "sao tome and principe": "STP",
    "são tomé e príncipe": "STP",
    "sao tome e principe": "STP",

    "united states": "USA",
    "united states of america": "USA",
    "estados unidos": "USA",

    "canada": "CAN",
    "canadá": "CAN",
    "canada": "CAN",

    "mexico": "MEX",
    "méxico": "MEX",
    "mexico": "MEX",

    "brazil": "BRA",
    "brasil": "BRA",

    "argentina": "ARG",
    "chile": "CHL",
    "colombia": "COL",
    "colômbia": "COL",
    "colombia": "COL",

    "peru": "PER",
    "uruguay": "URY",
    "uruguai": "URY",

    "venezuela": "VEN",

    "israel": "ISR",
    "jordania": "JOR",
    "jordânia": "JOR",

    "saudi arabia": "SAU",
    "arábia saudita": "SAU",
    "arabia saudita": "SAU",

    "united arab emirates": "ARE",
    "emirados árabes unidos": "ARE",
    "emirados arabes unidos": "ARE",

    "qatar": "QAT",
    "iraq": "IRQ",
    "iraque": "IRQ",

    "iran": "IRN",
    "irão": "IRN",
    "irao": "IRN",

    "lebanon": "LBN",
    "líbano": "LBN",
    "libano": "LBN",

    "jordan": "JOR",
    "jordânia": "JOR",
    "jordania": "JOR",

    "turkey": "TUR",
    "türkiye": "TUR",
    "turquia": "TUR",

    "india": "IND",
    "índia": "IND",
    "india": "IND",

    "china": "CHN",
    "japan": "JPN",
    "japão": "JPN",
    "japao": "JPN",

    "south korea": "KOR",
    "coreia do sul": "KOR",

    "australia": "AUS",
    "austrália": "AUS",
    "australia": "AUS",

    "new zealand": "NZL",
    "nova zelândia": "NZL",
    "nova zelandia": "NZL"
}


# ============================================================
# FUNÇÕES DE TEXTO
# ============================================================

def today_utc():
    return date.today()


def cutoff_date():
    return today_utc() - timedelta(
        days=PERIOD_DAYS
    )


def strip_html(value):
    if value is None:
        return ""

    value = str(value)

    value = html.unescape(value)

    value = re.sub(
        r"<[^>]+>",
        " ",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def fix_mojibake(value):

    if value is None:
        return ""

    value = str(value)

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
        "Ã“": "Ó",
        "Ãš": "Ú",
        "Â": "",
    }

    for old, new in replacements.items():
        value = value.replace(
            old,
            new
        )

    return value


def clean_text(value):

    value = strip_html(value)

    value = fix_mojibake(value)

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def normalise_search_term(value):

    value = clean_text(value)

    value = unicodedata.normalize(
        "NFKD",
        value
    )

    value = "".join(
        c for c in value
        if not unicodedata.combining(c)
    )

    return value.lower().strip()


# ============================================================
# DATAS
# ============================================================

def parse_date(value):

    if not value:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    value = str(value).strip()

    value = value[:10]

    formats = [
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%Y/%m/%d",
        "%d-%m-%Y",
    ]

    for fmt in formats:

        try:
            return datetime.strptime(
                value,
                fmt
            ).date()

        except Exception:
            pass

    return None


def extract_all_dates(value):

    dates = []

    if not value:
        return dates

    if isinstance(value, list):

        for item in value:
            dates.extend(
                extract_all_dates(item)
            )

        return dates

    if isinstance(value, dict):

        for item in value.values():
            dates.extend(
                extract_all_dates(item)
            )

        return dates

    text = str(value)

    patterns = [
        r"\d{4}-\d{2}-\d{2}",
        r"\d{2}/\d{2}/\d{4}",
        r"\d{2}-\d{2}-\d{4}",
    ]

    for pattern in patterns:

        for match in re.findall(
            pattern,
            text
        ):

            parsed = parse_date(
                match
            )

            if parsed:
                dates.append(parsed)

    return dates


def extract_deadline(data):

    possible_keys = [
        "deadline",
        "deadline-date",
        "deadline-date-lot",
        "submission_date",
        "deadline_date",
        "bid_submission_date",
        "closing_date",
        "closingdate",
    ]

    for key in possible_keys:

        if key in data:

            value = data.get(key)

            dates = extract_all_dates(
                value
            )

            if dates:

                future_dates = [
                    d for d in dates
                    if d >= today_utc()
                ]

                if future_dates:
                    return min(
                        future_dates
                    ).isoformat()

                return max(
                    dates
                ).isoformat()

    return ""


# ============================================================
# CPV
# ============================================================

def extract_cpvs(data):

    values = []

    for key in [
        "classification-cpv",
        "cpv",
        "cpvs",
        "classification",
    ]:

        value = data.get(key)

        if not value:
            continue

        if isinstance(value, list):

            values.extend(
                str(x)
                for x in value
            )

        elif isinstance(value, dict):

            values.extend(
                str(x)
                for x in value.values()
            )

        else:

            values.append(
                str(value)
            )

    text = " ".join(values)

    cpvs = re.findall(
        r"\b\d{8}\b",
        text
    )

    return list(
        dict.fromkeys(cpvs)
    )


# ============================================================
# PAÍS
# ============================================================

def extract_country(data):

    for key in [
        "buyer-country",
        "country",
        "buyer_country",
        "country-code",
        "country_code",
    ]:

        value = data.get(key)

        if not value:
            continue

        if isinstance(value, dict):

            for subkey in [
                "code",
                "country",
                "name",
                "value",
            ]:

                if value.get(subkey):
                    value = value.get(
                        subkey
                    )
                    break

        if isinstance(value, list):

            if value:
                value = value[0]

        value = clean_text(value)

        if value:
            return value

    return ""


def country_to_iso3(value):

    if not value:
        return ""

    value = clean_text(
        value
    )

    upper = value.upper()

    if re.fullmatch(
        r"[A-Z]{3}",
        upper
    ):
        return upper

    iso2 = {
        "PT": "PRT",
        "ES": "ESP",
        "FR": "FRA",
        "DE": "DEU",
        "IT": "ITA",
        "BE": "BEL",
        "NL": "NLD",
        "IE": "IRL",
        "GB": "GBR",
        "MT": "MLT",
        "GR": "GRC",
        "PL": "POL",
        "RO": "ROU",
        "HR": "HRV",
        "AT": "AUT",
        "CH": "CHE",
        "SE": "SWE",
        "NO": "NOR",
        "DK": "DNK",
        "FI": "FIN",
        "IS": "ISL",
        "HU": "HUN",
        "BG": "BGR",
        "SK": "SVK",
        "SI": "SVN",
        "RS": "SRB",
        "ME": "MNE",
        "UA": "UKR",
        "RU": "RUS",

        "MA": "MAR",
        "DZ": "DZA",
        "TN": "TUN",
        "EG": "EGY",
        "LY": "LBY",
        "SN": "SEN",
        "GH": "GHA",
        "NG": "NGA",
        "KE": "KEN",
        "TZ": "TZA",
        "UG": "UGA",
        "RW": "RWA",
        "ZA": "ZAF",
        "MZ": "MOZ",
        "AO": "AGO",
        "CV": "CPV",
        "GW": "GNB",
        "ST": "STP",

        "US": "USA",
        "CA": "CAN",
        "MX": "MEX",
        "BR": "BRA",
        "AR": "ARG",
        "CL": "CHL",
        "CO": "COL",
        "PE": "PER",
        "UY": "URY",
        "VE": "VEN",

        "IL": "ISR",
        "JO": "JOR",
        "SA": "SAU",
        "AE": "ARE",
        "IQ": "IRQ",
        "IR": "IRN",
        "LB": "LBN",
        "TR": "TUR",

        "IN": "IND",
        "CN": "CHN",
        "JP": "JPN",
        "KR": "KOR",
        "AU": "AUS",
        "NZ": "NZL",
    }

    if upper in iso2:
        return iso2[upper]

    normalised = normalise_search_term(
        value
    )

    return COUNTRY_NAMES.get(
        normalised,
        ""
    )


# ============================================================
# CLASSIFICAÇÃO
# ============================================================

ARCHAEOLOGY_KEYWORDS = [
    "archaeology",
    "archaeological",
    "archaeologist",
    "excavation",
    "excavations",
    "archaeological monitoring",
    "archaeological excavation",
    "archaeological services",
    "cultural heritage",
    "heritage",
    "archaeological heritage",
    "arqueologia",
    "arqueológico",
    "arqueologica",
    "escavação",
    "escavacao",
    "património cultural",
    "patrimonio cultural",
]


ARCHAEOLOGY_CPVS = {
    "71351914",
    "71351720",
    "71351811",
    "45112450",
}


def classify_result(
    title,
    description="",
    cpvs=None
):

    cpvs = cpvs or []

    text = normalise_search_term(
        f"{title} {description}"
    )

    direct = any(
        keyword in text
        for keyword in [
            "archaeology",
            "archaeological",
            "archaeologist",
            "excavation",
            "archaeological monitoring",
            "archaeological excavation",
            "archaeological services",
            "arqueologia",
            "arqueologico",
            "arqueologica",
            "escavacao",
            "escavacao arqueologica",
        ]
    )

    heritage = any(
        keyword in text
        for keyword in [
            "cultural heritage",
            "heritage",
            "archaeological heritage",
            "patrimonio cultural",
        ]
    )

    cpv_match = any(
        cpv in ARCHAEOLOGY_CPVS
        for cpv in cpvs
    )

    if direct:

        category = "Arqueologia direta"

        score = 90

        if cpv_match:
            score = 95

    elif heritage or cpv_match:

        category = "Património / Arqueologia"

        score = 70

    else:

        category = "Relevante"

        score = 30

    return category, min(
        score,
        100
    )


# ============================================================
# QUERY TED
# ============================================================

def build_ted_query(term):

    cutoff = cutoff_date().strftime(
        "%Y%m%d"
    )

    return (
        f'FT~"{term}" '
        f'AND publication-date>={cutoff} '
        f'SORT BY publication-date DESC'
    )


# ============================================================
# CONVERTER AVISO TED
# ============================================================

def notice_to_result(notice):

    title = clean_text(
        notice.get(
            "notice-title",
            ""
        )
    )

    if isinstance(
        notice.get("notice-title"),
        dict
    ):

        title = clean_text(
            notice["notice-title"].get(
                "text",
                ""
            )
        )

    if not title:
        return None

    description = clean_text(
        notice.get(
            "description",
            ""
        )
    )

    cpvs = extract_cpvs(
        notice
    )

    country = extract_country(
        notice
    )

    publication_date = parse_date(
        notice.get(
            "publication-date"
        )
    )

    if (
        publication_date
        and publication_date < cutoff_date()
    ):
        return None

    deadline = extract_deadline(
        notice
    )

    if deadline:

        deadline_date = parse_date(
            deadline
        )

        if (
            deadline_date
            and deadline_date < today_utc()
        ):
            return None

    category, score = classify_result(
        title,
        description,
        cpvs
    )

    text = normalise_search_term(
        f"{title} {description}"
    )

    relevant = (
        any(
            normalise_search_term(
                term
            ) in text
            for term in DEFAULT_TERMS
        )
        or any(
            cpv in ARCHAEOLOGY_CPVS
            for cpv in cpvs
        )
    )

    if not relevant:
        return None

    publication_number = clean_text(
        notice.get(
            "publication-number",
            ""
        )
    )

    url = ""

    if publication_number:

        url = (
            "https://ted.europa.eu/"
            "en/notice/-/detail/"
            + publication_number
        )

    return {
        "title": title,
        "description": description,
        "source": "TED",
        "date": (
            publication_date.isoformat()
            if publication_date
            else ""
        ),
        "deadline": deadline,
        "country": country,
        "buyer": clean_text(
            notice.get(
                "buyer-name",
                ""
            )
        ),
        "cpv": ", ".join(cpvs),
        "category": category,
        "score": score,
        "url": url,
    }


# ============================================================
# TED — POST
# ============================================================

def query_ted(term):

    diagnostics = {
        "source": f"TED — {term}",
        "ok": False,
        "count": 0,
    }

    results = []

    try:

        query = build_ted_query(
            term
        )

        payload = {
            "query": query,
            "fields": TED_FIELDS,
            "page": 1,
            "limit": PAGE_SIZE,
            "paginationMode": "PAGE_NUMBER",
        }

        response = requests.post(
            TED_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

        notices = []

        if isinstance(
            data,
            dict
        ):

            if isinstance(
                data.get("notices"),
                list
            ):

                notices = data["notices"]

            elif isinstance(
                data.get("results"),
                list
            ):

                notices = data["results"]

            elif isinstance(
                data.get("data"),
                list
            ):

                notices = data["data"]

        elif isinstance(
            data,
            list
        ):

            notices = data

        for notice in notices:

            if not isinstance(
                notice,
                dict
            ):
                continue

            result = notice_to_result(
                notice
            )

            if result:

                results.append(
                    result
                )

        diagnostics["ok"] = True

        diagnostics["count"] = len(
            results
        )

        return results, diagnostics

    except Exception as exc:

        diagnostics["error"] = str(
            exc
        )

        return [], diagnostics


# ============================================================
# WORLD BANK
# ============================================================

def world_bank_title(item):

    possible_keys = [
        "project_name",
        "procurement_name",
        "title",
        "notice_title",
        "procurement_title",
        "contract_title",
    ]

    for key in possible_keys:

        value = item.get(
            key
        )

        if value:

            value = clean_text(
                value
            )

            value = re.sub(
                r"^\s*\d+\s*/\s*100\s*",
                "",
                value
            )

            if value:
                return value

    return ""


def world_bank_description(item):

    possible_keys = [
        "description",
        "short_description",
        "procurement_description",
        "notice_description",
        "project_description",
    ]

    values = []

    for key in possible_keys:

        value = item.get(
            key
        )

        if value:

            values.append(
                clean_text(value)
            )

    text = " ".join(
        x for x in values
        if x
    )

    text = re.sub(
        r"^\s*\d+\s*/\s*100\s*",
        "",
        text
    )

    return text.strip()


def world_bank_date(item):

    possible_keys = [
        "publication_date",
        "notice_date",
        "date",
        "published_date",
        "procurement_date",
    ]

    for key in possible_keys:

        parsed = parse_date(
            item.get(key)
        )

        if parsed:
            return parsed

    return None


def world_bank_url(item):

    for key in [
        "url",
        "notice_url",
        "procurement_url",
        "link",
        "notice_link",
    ]:

        value = item.get(
            key
        )

        if value:
            return str(value)

    return ""


def query_world_bank(term):

    diagnostics = {
        "source": f"World Bank — {term}",
        "ok": False,
        "count": 0,
    }

    results = []

    try:

        params = {
            "qterm": term,
            "format": "json",
            "rows": PAGE_SIZE,
        }

        response = requests.get(
            WORLD_BANK_URL,
            params=params,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

        records = []

        if isinstance(
            data,
            dict
        ):

            for key in [
                "procnotices",
                "results",
                "data",
                "records",
            ]:

                value = data.get(
                    key
                )

                if isinstance(
                    value,
                    list
                ):

                    records = value
                    break

                if isinstance(
                    value,
                    dict
                ):

                    for subkey in [
                        "rows",
                        "results",
                        "data",
                    ]:

                        if isinstance(
                            value.get(subkey),
                            list
                        ):

                            records = value[
                                subkey
                            ]

                            break

                    if records:
                        break

        elif isinstance(
            data,
            list
        ):

            records = data

        for item in records:

            if not isinstance(
                item,
                dict
            ):
                continue

            title = world_bank_title(
                item
            )

            description = (
                world_bank_description(
                    item
                )
            )

            if not title:
                continue

            pub_date = world_bank_date(
                item
            )

            if (
                pub_date
                and pub_date < cutoff_date()
            ):
                continue

            deadline = extract_deadline(
                item
            )

            if deadline:

                deadline_date = parse_date(
                    deadline
                )

                if (
                    deadline_date
                    and deadline_date < today_utc()
                ):
                    continue

            country = extract_country(
                item
            )

            cpvs = extract_cpvs(
                item
            )

            category, score = classify_result(
                title,
                description,
                cpvs
            )

            text = normalise_search_term(
                f"{title} {description}"
            )

            if not any(
                normalise_search_term(
                    x
                ) in text
                for x in DEFAULT_TERMS
            ):

                if not any(
                    cpv in ARCHAEOLOGY_CPVS
                    for cpv in cpvs
                ):
                    continue

            results.append({
                "title": title,
                "description": description,
                "source": "World Bank Procurement",
                "date": (
                    pub_date.isoformat()
                    if pub_date
                    else ""
                ),
                "deadline": deadline,
                "country": country,
                "buyer": clean_text(
                    item.get(
                        "buyer",
                        item.get(
                            "procuring_entity",
                            ""
                        )
                    )
                ),
                "cpv": ", ".join(cpvs),
                "category": category,
                "score": score,
                "url": world_bank_url(
                    item
                ),
            })

        diagnostics["ok"] = True

        diagnostics["count"] = len(
            results
        )

        return results, diagnostics

    except Exception as exc:

        diagnostics["error"] = str(
            exc
        )

        return [], diagnostics


# ============================================================
# FILTRO REGIONAL
# ============================================================

def apply_region_filter(
    results,
    region
):

    if not region:
        return results

    if region not in REGIONS:
        return results

    allowed = REGIONS[
        region
    ]

    filtered = []

    for result in results:

        country = result.get(
            "country",
            ""
        )

        country_code = country_to_iso3(
            country
        )

        if country_code in allowed:

            filtered.append(
                result
            )

    return filtered


# ============================================================
# FILTRO DE CATEGORIA
# ============================================================

def apply_category_filter(
    results,
    category
):

    if not category:
        return results

    if category.lower() in [
        "",
        "todas",
        "todos",
        "all",
    ]:
        return results

    filtered = []

    for result in results:

        if result.get(
            "category",
            ""
        ).lower() == category.lower():

            filtered.append(
                result
            )

    return filtered


# ============================================================
# DEDUPLICAÇÃO
# ============================================================

def deduplicate_results(
    results
):

    seen = set()

    output = []

    for result in results:

        key = (
            normalise_search_term(
                result.get(
                    "title",
                    ""
                )
            ),
            normalise_search_term(
                result.get(
                    "country",
                    ""
                )
            ),
            result.get(
                "date",
                ""
            ),
        )

        if key in seen:
            continue

        seen.add(
            key
        )

        output.append(
            result
        )

    return output


# ============================================================
# FONTES
# ============================================================

SOURCES = [

    {
        "name": "TED — Europa / Internacional",
        "region": "Europa / Internacional",
        "mode": "api",
        "url": "https://ted.europa.eu/"
    },

    {
        "name": "World Bank Procurement",
        "region": "Global",
        "mode": "api",
        "url": "https://projects.worldbank.org/en/projects-operations/procurement"
    },

    {
        "name": "African Development Bank",
        "region": "África",
        "mode": "portal",
        "url": "https://www.afdb.org/en/projects-and-operations/procurement"
    },

    {
        "name": "SAM.gov",
        "region": "Américas",
        "mode": "portal",
        "url": "https://sam.gov/content/opportunities"
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
]


# ============================================================
# ROTAS PRINCIPAIS
# ============================================================

@app.get("/")
def root():

    return FileResponse(
        BASE_DIR / "index.html"
    )


@app.get("/app.js")
def javascript():

    return FileResponse(
        BASE_DIR / "App.js",
        media_type="application/javascript"
    )


@app.get("/manifest.json")
def manifest():

    return FileResponse(
        BASE_DIR / "manifest.json"
    )


@app.get("/health")
@app.get("/api/health")
def health():

    return {
        "ok": True,
        "service": "Arqueologia Radar"
    }


@app.get("/api/sources")
def get_sources():

    return SOURCES


# ============================================================
# PESQUISA PRINCIPAL
# ============================================================

@app.get("/api/search")
def search(
    q: str = Query(
        "archaeology"
    ),
    region: str = Query(
        ""
    ),
    category: str = Query(
        ""
    )
):

    search_term = clean_text(
        q
    )

    if not search_term:
        search_term = "archaeology"

    terms = []

    terms.append(
        search_term
    )

    for term in DEFAULT_TERMS:

        if normalise_search_term(
            term
        ) != normalise_search_term(
            search_term
        ):

            terms.append(
                term
            )

    terms = list(
        dict.fromkeys(
            terms
        )
    )[:12]

    all_results = []

    diagnostics = []

    # --------------------------------------------------------
    # TED
    # --------------------------------------------------------

    max_workers = min(
        8,
        len(terms)
    )

    with ThreadPoolExecutor(
        max_workers=max_workers
    ) as executor:

        futures = {
            executor.submit(
                query_ted,
                term
            ): term
            for term in terms
        }

        for future in as_completed(
            futures
        ):

            try:

                results, diag = (
                    future.result()
                )

                all_results.extend(
                    results
                )

                diagnostics.append(
                    diag
                )

            except Exception as exc:

                term = futures[
                    future
                ]

                diagnostics.append({
                    "source": (
                        f"TED — {term}"
                    ),
                    "ok": False,
                    "count": 0,
                    "error": str(
                        exc
                    ),
                })

    # --------------------------------------------------------
    # WORLD BANK
    # --------------------------------------------------------

    for term in terms[:4]:

        results, diag = query_world_bank(
            term
        )

        all_results.extend(
            results
        )

        diagnostics.append(
            diag
        )

    # --------------------------------------------------------
    # DEDUPLICAÇÃO
    # --------------------------------------------------------

    all_results = deduplicate_results(
        all_results
    )

    # --------------------------------------------------------
    # FILTRO REGIONAL
    # --------------------------------------------------------

    all_results = apply_region_filter(
        all_results,
        region
    )

    # --------------------------------------------------------
    # FILTRO DE CATEGORIA
    # --------------------------------------------------------

    all_results = apply_category_filter(
        all_results,
        category
    )

    # --------------------------------------------------------
    # REMOVER PRAZOS EXPIRADOS
    # --------------------------------------------------------

    valid_results = []

    for result in all_results:

        deadline = result.get(
            "deadline",
            ""
        )

        if deadline:

            deadline_date = parse_date(
                deadline
            )

            if (
                deadline_date
                and deadline_date < today_utc()
            ):
                continue

        valid_results.append(
            result
        )

    all_results = valid_results

    # --------------------------------------------------------
    # ORDENAÇÃO
    # --------------------------------------------------------

    def sort_key(item):

        deadline = parse_date(
            item.get(
                "deadline"
            )
        )

        pub_date = parse_date(
            item.get(
                "date"
            )
        )

        deadline_value = (
            deadline
            or date.max
        )

        pub_date_value = (
            pub_date
            or date.min
        )

        return (
            item.get(
                "score",
                0
            ),
            deadline_value,
            pub_date_value,
        )

    all_results.sort(
        key=sort_key,
        reverse=True
    )

    # --------------------------------------------------------
    # RESPOSTA
    # --------------------------------------------------------

    return {
        "ok": True,
        "query": search_term,
        "region": region,
        "category": category,
        "results": all_results,
        "diagnostics": diagnostics,
        "portal_count": 2,
        "api_count": 2,
        "sources": 28,
        "searched_at": today_utc().isoformat(),
    }


# ============================================================
# ARRANQUE LOCAL
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000
    )
