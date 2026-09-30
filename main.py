from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
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
    version="1.1.0"
)

TED_URL = "https://api.ted.europa.eu/v3/notices/search"
WORLD_BANK_URL = "https://search.worldbank.org/api/v2/procnotices"

PERIOD_DAYS = 365
PAGE_SIZE = 250
MAX_PAGES_PER_TERM = 4
REQUEST_TIMEOUT = 25

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
# TERMOS
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
        "SWE", "TUR", "UKR", "VAT", "XKX"
    },

    "África": {
        "DZA", "AGO", "BEN", "BWA", "BFA", "BDI",
        "CMR", "CPV", "CAF", "TCD", "COM", "COG",
        "COD", "CIV", "DJI", "EGY", "GNQ", "ERI",
        "SWZ", "ETH", "GAB", "GMB", "GHA", "GIN",
        "GNB", "KEN", "LSO", "LBR", "LBY", "MDG",
        "MWI", "MLI", "MRT", "MUS", "MAR", "MOZ",
        "NAM", "NER", "NGA", "RWA", "STP", "SEN",
        "SYC", "SLE", "SOM", "ZAF", "SSD", "SDN",
        "TZA", "TGO", "TUN", "UGA", "ZMB", "ZWE"
    },

    "Médio Oriente": {
        "ARE", "BHR", "IRN", "IRQ", "ISR", "JOR",
        "KWT", "LBN", "OMN", "PSE", "QAT", "SAU",
        "SYR", "YEM"
    },

    "Américas": {
        "ARG", "BOL", "BRA", "CAN", "CHL", "COL",
        "CRI", "CUB", "DOM", "ECU", "GTM", "GUY",
        "HND", "HTI", "JAM", "MEX", "NIC", "PAN",
        "PER", "PRY", "SLV", "SUR", "TTO", "URY",
        "USA", "VEN"
    },

    "Ásia-Pacífico": {
        "AFG", "ARM", "AUS", "AZE", "BGD", "BTN",
        "BRN", "CHN", "FJI", "GEO", "IDN", "IND",
        "JPN", "KAZ", "KGZ", "KHM", "KIR", "KOR",
        "LAO", "LKA", "MHL", "MMR", "MNG", "MYS",
        "NPL", "NZL", "PAK", "PHL", "PLW", "PNG",
        "PRK", "SLB", "THA", "TJK", "TKM", "TLS",
        "TON", "TUV", "UZB", "VNM", "VUT", "WSM"
    }
}


# ============================================================
# FUNÇÕES GERAIS
# ============================================================

def today_utc():
    return date.today()


def cutoff_date():
    return today_utc() - timedelta(days=PERIOD_DAYS)


def strip_html(value):
    if value is None:
        return ""

    value = str(value)

    value = re.sub(
        r"<[^>]+>",
        " ",
        value
    )

    value = html.unescape(value)

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def fix_mojibake(value):
    if not value:
        return value

    replacements = {
        "Ã¡": "á",
        "Ã ": "à",
        "Ã£": "ã",
        "Ã§": "ç",
        "Ã©": "é",
        "Ãª": "ê",
        "Ã­": "í",
        "Ã³": "ó",
        "Ã´": "ô",
        "Ãº": "ú",
        "Ã¼": "ü",
        "Ã‰": "É",
        "ÃŠ": "Ê",
        "Ã“": "Ó",
        "Ãš": "Ú",
        "Â": "",
        "â€“": "–",
        "â€”": "—",
        "â€œ": "“",
        "â€": "”",
        "â€˜": "‘",
        "â€™": "’",
        "â€¦": "…",
    }

    for old, new in replacements.items():
        value = value.replace(old, new)

    return value


def clean_text(value):
    return fix_mojibake(
        strip_html(value)
    )


def parse_date(value):

    if not value:
        return None

    value = str(value).strip()

    formats = [
        "%Y-%m-%d",
        "%Y%m%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%fZ",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(
                value[:26],
                fmt
            ).date()
        except Exception:
            pass

    try:
        return datetime.fromisoformat(
            value.replace("Z", "+00:00")
        ).date()
    except Exception:
        return None


def extract_all_dates(value):

    if not value:
        return []

    if isinstance(value, list):
        values = value
    else:
        values = [value]

    result = []

    for item in values:

        if isinstance(item, dict):
            for v in item.values():
                d = parse_date(v)

                if d:
                    result.append(d)

        else:
            d = parse_date(item)

            if d:
                result.append(d)

    return result


def extract_deadline(notice):

    possible_fields = [
        "deadline",
        "deadline-date-lot",
        "deadline_date",
        "submission_date",
        "closing_date",
        "closingdate",
        "bid_submission_date",
    ]

    dates = []

    for field in possible_fields:

        value = notice.get(field)

        dates.extend(
            extract_all_dates(value)
        )

    if not dates:
        return None

    return min(dates)


def extract_cpvs(notice):

    value = notice.get(
        "classification-cpv"
    )

    if not value:
        value = notice.get("cpv")

    if not value:
        return []

    if isinstance(value, list):
        values = value
    else:
        values = [value]

    result = []

    for item in values:

        if isinstance(item, dict):

            for v in item.values():

                matches = re.findall(
                    r"\b\d{8}\b",
                    str(v)
                )

                result.extend(matches)

        else:

            matches = re.findall(
                r"\b\d{8}\b",
                str(item)
            )

            result.extend(matches)

    return list(
        dict.fromkeys(result)
    )


def extract_country(value):

    if not value:
        return ""

    if isinstance(value, list):

        if not value:
            return ""

        value = value[0]

    if isinstance(value, dict):

        for key in [
            "code",
            "country-code",
            "country_code",
            "value",
            "name"
        ]:

            if value.get(key):
                return str(
                    value[key]
                ).strip()

        return ""

    return str(value).strip()


def normalise_search_term(term):

    term = clean_text(term)

    term = re.sub(
        r"\s+",
        " ",
        term
    )

    return term.strip()


# ============================================================
# CLASSIFICAÇÃO
# ============================================================

def classify_result(
    title,
    description="",
    cpvs=None
):

    text = (
        f"{title} "
        f"{description}"
    ).lower()

    cpvs = cpvs or []

    archaeology_words = [
        "archaeolog",
        "archaeological",
        "archaeology",
        "excavation",
        "excavations",
        "heritage",
        "cultural heritage",
        "archaeological monitoring",
        "archaeological excavation",
        "arqueologia",
        "arqueológico",
        "arqueológica",
        "património",
        "patrimonio",
    ]

    direct_words = [
        "archaeological excavation",
        "archaeological monitoring",
        "archaeological services",
        "archaeology",
        "archaeological",
        "excavation",
        "arqueologia",
        "arqueológico",
        "arqueológica",
    ]

    direct = any(
        word in text
        for word in direct_words
    )

    relevant = any(
        word in text
        for word in archaeology_words
    )

    archaeological_cpvs = {
        "71351914",
        "71351720",
        "71351811",
        "45112450",
    }

    has_archaeological_cpv = any(
        cpv in archaeological_cpvs
        for cpv in cpvs
    )

    if direct or has_archaeological_cpv:
        category = "Arqueologia direta"
    elif relevant:
        category = "Património / Arqueologia"
    else:
        category = "Relevante"

    score = 0

    if direct:
        score += 60

    if has_archaeological_cpv:
        score += 30

    if relevant:
        score += 20

    if "cultural heritage" in text:
        score += 10

    if "monitoring" in text:
        score += 10

    if "excavation" in text:
        score += 10

    score = min(
        score,
        100
    )

    return category, score


# ============================================================
# WORLD BANK
# ============================================================

def world_bank_title(notice):

    title = ""

    for field in [
        "project_name",
        "notice_title",
        "title",
        "procurement_name",
        "contract_name",
    ]:

        value = notice.get(field)

        if value:
            title = clean_text(value)
            break

    if not title:

        title = clean_text(
            notice.get("notice_text", "")
        )

    title = re.sub(
        r"^\s*100\s*/\s*100\s*",
        "",
        title,
        flags=re.I
    )

    title = re.sub(
        r"^\s*100/100\s*",
        "",
        title,
        flags=re.I
    )

    return title[:220].strip()


def world_bank_notice_to_result(notice):

    title = world_bank_title(
        notice
    )

    if not title:
        return None

    description = clean_text(
        notice.get(
            "notice_text",
            notice.get(
                "description",
                ""
            )
        )
    )

    country_raw = (
        notice.get("country")
        or notice.get("country_name")
        or notice.get("country_code")
        or ""
    )

    country = extract_country(
        country_raw
    )

    country_names = {
        "Tanzania": "TZA",
        "United Republic of Tanzania": "TZA",
        "Mozambique": "MOZ",
        "Kenya": "KEN",
        "Ghana": "GHA",
        "Nigeria": "NGA",
        "South Africa": "ZAF",
        "Uganda": "UGA",
        "Rwanda": "RWA",
        "Senegal": "SEN",
        "Morocco": "MAR",
        "Tunisia": "TUN",
        "Egypt": "EGY",
        "Ethiopia": "ETH",
        "Zambia": "ZMB",
        "Zimbabwe": "ZWE",
        "Malawi": "MWI",
        "Mali": "MLI",
        "Niger": "NER",
        "Cameroon": "CMR",
        "Gabon": "GAB",
        "Guinea": "GIN",
        "Sierra Leone": "SLE",
        "Liberia": "LBR",
        "Benin": "BEN",
        "Burkina Faso": "BFA",
        "Botswana": "BWA",
        "Namibia": "NAM",
        "Angola": "AGO",
        "Algeria": "DZA",
        "Libya": "LBY",
        "Mauritius": "MUS",
        "Madagascar": "MDG",
        "Sao Tome and Principe": "STP",
        "São Tomé and Príncipe": "STP",
    }

    country_code = country

    if country in country_names:
        country_code = country_names[country]

    if len(country) == 2:
        iso2 = {
            "TZ": "TZA",
            "MZ": "MOZ",
            "KE": "KEN",
            "GH": "GHA",
            "NG": "NGA",
            "ZA": "ZAF",
            "UG": "UGA",
            "RW": "RWA",
            "SN": "SEN",
            "MA": "MAR",
            "TN": "TUN",
            "EG": "EGY",
            "ET": "ETH",
            "ZM": "ZMB",
            "ZW": "ZWE",
            "MW": "MWI",
            "ML": "MLI",
            "NE": "NER",
            "CM": "CMR",
            "GA": "GAB",
            "GN": "GIN",
            "SL": "SLE",
            "LR": "LBR",
            "BJ": "BEN",
            "BF": "BFA",
            "BW": "BWA",
            "NA": "NAM",
            "AO": "AGO",
            "DZ": "DZA",
            "LY": "LBY",
            "MU": "MUS",
            "MG": "MDG",
            "ST": "STP",
        }

        country_code = iso2.get(
            country.upper(),
            country.upper()
        )

    publication_date = None

    for field in [
        "publication_date",
        "publication-date",
        "date",
        "published_date",
    ]:

        d = parse_date(
            notice.get(field)
        )

        if d:
            publication_date = d
            break

    if not publication_date:
        publication_date = today_utc()

    deadline = None

    for field in [
        "submission_date",
        "deadline_date",
        "bid_submission_date",
        "closing_date",
        "closingdate",
    ]:

        d = parse_date(
            notice.get(field)
        )

        if d:
            deadline = d
            break

    if deadline and deadline < today_utc():
        return None

    cpvs = extract_cpvs(
        notice
    )

    category, score = classify_result(
        title,
        description,
        cpvs
    )

    url = (
        notice.get("url")
        or notice.get("notice_url")
        or notice.get("procurement_url")
        or ""
    )

    buyer = (
        notice.get("buyer")
        or notice.get("agency")
        or notice.get("organization")
        or notice.get("borrower")
        or ""
    )

    return {
        "title": title,
        "description": description,
        "source": "World Bank",
        "country": country_code,
        "buyer": clean_text(buyer),
        "date": publication_date.isoformat(),
        "deadline": (
            deadline.isoformat()
            if deadline
            else ""
        ),
        "category": category,
        "score": score,
        "cpv": ", ".join(cpvs),
        "url": url,
    }


def query_world_bank():

    diagnostics = {
        "source": "World Bank",
        "ok": False,
        "count": 0,
    }

    results = []

    try:

        response = requests.get(
            WORLD_BANK_URL,
            params={
                "format": "json",
                "rows": PAGE_SIZE,
            },
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

        notices = []

        if isinstance(data, list):
            notices = data

        elif isinstance(data, dict):

            for key in [
                "procnotices",
                "notices",
                "results",
                "data",
            ]:

                value = data.get(key)

                if isinstance(value, list):
                    notices = value
                    break

                if isinstance(value, dict):

                    for subkey in [
                        "notice",
                        "notices",
                        "results",
                        "data",
                    ]:

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

        for notice in notices:

            if not isinstance(
                notice,
                dict
            ):
                continue

            result = world_bank_notice_to_result(
                notice
            )

            if result:
                results.append(result)

        diagnostics["ok"] = True
        diagnostics["count"] = len(results)

        return results, diagnostics

    except Exception as exc:

        diagnostics["error"] = str(exc)

        return [], diagnostics


# ============================================================
# TED
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


def notice_to_result(notice):

    publication_date = parse_date(
        notice.get(
            "publication-date"
        )
    )

    if not publication_date:
        return None

    if publication_date < cutoff_date():
        return None

    title = clean_text(
        notice.get(
            "notice-title",
            ""
        )
    )

    if not title:
        return None

    buyer_country = extract_country(
        notice.get(
            "buyer-country"
        )
    )

    cpvs = extract_cpvs(
        notice
    )

    deadline = extract_deadline(
        notice
    )

    if deadline and deadline < today_utc():
        return None

    buyer = clean_text(
        notice.get(
            "buyer-name",
            ""
        )
    )

    description = clean_text(
        notice.get(
            "description",
            ""
        )
    )

    category, score = classify_result(
        title,
        description,
        cpvs
    )

    title_lower = title.lower()
    description_lower = description.lower()

    relevant = (
        any(
            term.lower() in title_lower
            or term.lower() in description_lower
            for term in DEFAULT_TERMS
        )
        or any(
            cpv in {
                "71351914",
                "71351720",
                "71351811",
                "45112450",
            }
            for cpv in cpvs
        )
    )

    if not relevant:
        return None

    if score < 20:
        return None

    publication_number = notice.get(
        "publication-number",
        ""
    )

    url = ""

    if publication_number:
        url = (
            "https://ted.europa.eu/"
            f"en/notice/{publication_number}"
        )

    return {
        "title": title,
        "description": description,
        "source": "TED",
        "country": buyer_country,
        "buyer": buyer,
        "date": publication_date.isoformat(),
        "deadline": (
            deadline.isoformat()
            if deadline
            else ""
        ),
        "category": category,
        "score": score,
        "cpv": ", ".join(cpvs),
        "url": url,
    }


def query_ted(term):

    diagnostics = {
        "source": f"TED — {term}",
        "ok": False,
        "count": 0,
    }

    results = []

    try:

        params = {
            "q": build_ted_query(term),
            "page": 1,
            "limit": PAGE_SIZE,
            "fields": ",".join(
                TED_FIELDS
            ),
        }

        response = requests.get(
            TED_URL,
            params=params,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

        notices = []

        if isinstance(data, dict):

            for key in [
                "notices",
                "results",
                "data",
            ]:

                value = data.get(key)

                if isinstance(value, list):
                    notices = value
                    break

        elif isinstance(data, list):

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
                results.append(result)

        diagnostics["ok"] = True
        diagnostics["count"] = len(results)

        return results, diagnostics

    except Exception as exc:

        diagnostics["error"] = str(exc)

        return [], diagnostics


# ============================================================
# FILTRO DE REGIÃO
# ============================================================

def apply_region_filter(
    results,
    region
):

    region = (
        region or ""
    ).strip()

    if not region:
        return results

    allowed = REGIONS.get(
        region
    )

    if not allowed:
        return results

    # --------------------------------------------------------
    # Nomes de países -> ISO3
    # --------------------------------------------------------

    country_names = {

        # África
        "Algeria": "DZA",
        "Angola": "AGO",
        "Benin": "BEN",
        "Botswana": "BWA",
        "Burkina Faso": "BFA",
        "Burundi": "BDI",
        "Cameroon": "CMR",
        "Cape Verde": "CPV",
        "Cabo Verde": "CPV",
        "Central African Republic": "CAF",
        "Chad": "TCD",
        "Comoros": "COM",
        "Republic of the Congo": "COG",
        "Congo": "COG",
        "Democratic Republic of the Congo": "COD",
        "Democratic Republic of Congo": "COD",
        "Côte d'Ivoire": "CIV",
        "Cote d'Ivoire": "CIV",
        "Ivory Coast": "CIV",
        "Djibouti": "DJI",
        "Egypt": "EGY",
        "Equatorial Guinea": "GNQ",
        "Eritrea": "ERI",
        "Eswatini": "SWZ",
        "Swaziland": "SWZ",
        "Ethiopia": "ETH",
        "Gabon": "GAB",
        "Gambia": "GMB",
        "The Gambia": "GMB",
        "Ghana": "GHA",
        "Guinea": "GIN",
        "Guinea-Bissau": "GNB",
        "Kenya": "KEN",
        "Lesotho": "LSO",
        "Liberia": "LBR",
        "Libya": "LBY",
        "Madagascar": "MDG",
        "Malawi": "MWI",
        "Mali": "MLI",
        "Mauritania": "MRT",
        "Mauritius": "MUS",
        "Morocco": "MAR",
        "Mozambique": "MOZ",
        "Namibia": "NAM",
        "Niger": "NER",
        "Nigeria": "NGA",
        "Rwanda": "RWA",
        "Sao Tome and Principe": "STP",
        "São Tomé and Príncipe": "STP",
        "Senegal": "SEN",
        "Seychelles": "SYC",
        "Sierra Leone": "SLE",
        "Somalia": "SOM",
        "South Africa": "ZAF",
        "South Sudan": "SSD",
        "Sudan": "SDN",
        "Tanzania": "TZA",
        "United Republic of Tanzania": "TZA",
        "Togo": "TGO",
        "Tunisia": "TUN",
        "Uganda": "UGA",
        "Zambia": "ZMB",
        "Zimbabwe": "ZWE",

        # Europa
        "Portugal": "PRT",
        "Spain": "ESP",
        "France": "FRA",
        "Germany": "DEU",
        "Italy": "ITA",
        "Belgium": "BEL",
        "Netherlands": "NLD",
        "Ireland": "IRL",
        "United Kingdom": "GBR",
        "Austria": "AUT",
        "Switzerland": "CHE",
        "Poland": "POL",
        "Czechia": "CZE",
        "Czech Republic": "CZE",
        "Denmark": "DNK",
        "Sweden": "SWE",
        "Norway": "NOR",
        "Finland": "FIN",
        "Greece": "GRC",
        "Romania": "ROU",
        "Bulgaria": "BGR",
        "Croatia": "HRV",
        "Hungary": "HUN",
        "Slovakia": "SVK",
        "Slovenia": "SVN",
        "Lithuania": "LTU",
        "Latvia": "LVA",
        "Estonia": "EST",
        "Malta": "MLT",
        "Cyprus": "CYP",
        "Luxembourg": "LUX",
        "Iceland": "ISL",
        "Serbia": "SRB",
        "Montenegro": "MNE",
        "North Macedonia": "MKD",
        "Albania": "ALB",
        "Bosnia and Herzegovina": "BIH",
        "Moldova": "MDA",
        "Ukraine": "UKR",
        "Turkey": "TUR",
        "Türkiye": "TUR",
        "Russia": "RUS",
        "Andorra": "AND",
        "Liechtenstein": "LIE",
        "Monaco": "MCO",
        "San Marino": "SMR",
        "Vatican City": "VAT",
        "Belarus": "BLR",

        # Médio Oriente
        "United Arab Emirates": "ARE",
        "UAE": "ARE",
        "Bahrain": "BHR",
        "Iran": "IRN",
        "Iraq": "IRQ",
        "Israel": "ISR",
        "Jordan": "JOR",
        "Kuwait": "KWT",
        "Lebanon": "LBN",
        "Oman": "OMN",
        "Palestine": "PSE",
        "Qatar": "QAT",
        "Saudi Arabia": "SAU",
        "Syria": "SYR",
        "Yemen": "YEM",

        # Américas
        "Argentina": "ARG",
        "Bolivia": "BOL",
        "Brazil": "BRA",
        "Canada": "CAN",
        "Chile": "CHL",
        "Colombia": "COL",
        "Costa Rica": "CRI",
        "Cuba": "CUB",
        "Dominican Republic": "DOM",
        "Ecuador": "ECU",
        "Guatemala": "GTM",
        "Guyana": "GUY",
        "Honduras": "HND",
        "Haiti": "HTI",
        "Jamaica": "JAM",
        "Mexico": "MEX",
        "Nicaragua": "NIC",
        "Panama": "PAN",
        "Paraguay": "PRY",
        "Peru": "PER",
        "Suriname": "SUR",
        "Trinidad and Tobago": "TTO",
        "Uruguay": "URY",
        "United States": "USA",
        "United States of America": "USA",
        "Venezuela": "VEN",

        # Ásia-Pacífico
        "Afghanistan": "AFG",
        "Armenia": "ARM",
        "Australia": "AUS",
        "Azerbaijan": "AZE",
        "Bangladesh": "BGD",
        "Bhutan": "BTN",
        "Brunei": "BRN",
        "China": "CHN",
        "Fiji": "FJI",
        "Georgia": "GEO",
        "India": "IND",
        "Indonesia": "IDN",
        "Japan": "JPN",
        "Kazakhstan": "KAZ",
        "Kyrgyzstan": "KGZ",
        "Cambodia": "KHM",
        "Kiribati": "KIR",
        "Laos": "LAO",
        "Sri Lanka": "LKA",
        "Malaysia": "MYS",
        "Maldives": "MDV",
        "Marshall Islands": "MHL",
        "Micronesia": "FSM",
        "Mongolia": "MNG",
        "Myanmar": "MMR",
        "Nepal": "NPL",
        "New Zealand": "NZL",
        "Pakistan": "PAK",
        "Philippines": "PHL",
        "Palau": "PLW",
        "Papua New Guinea": "PNG",
        "North Korea": "PRK",
        "South Korea": "KOR",
        "Singapore": "SGP",
        "Solomon Islands": "SLB",
        "Tajikistan": "TJK",
        "Thailand": "THA",
        "Timor-Leste": "TLS",
        "Turkmenistan": "TKM",
        "Tonga": "TON",
        "Tuvalu": "TUV",
        "Uzbekistan": "UZB",
        "Vanuatu": "VUT",
        "Vietnam": "VNM",
        "Samoa": "WSM",
    }

    # --------------------------------------------------------
    # ISO2 -> ISO3
    # --------------------------------------------------------

    iso2_to_iso3 = {

        "DZ": "DZA",
        "AO": "AGO",
        "BJ": "BEN",
        "BW": "BWA",
        "BF": "BFA",
        "BI": "BDI",
        "CM": "CMR",
        "CV": "CPV",
        "CF": "CAF",
        "TD": "TCD",
        "KM": "COM",
        "CG": "COG",
        "CD": "COD",
        "CI": "CIV",
        "DJ": "DJI",
        "EG": "EGY",
        "GQ": "GNQ",
        "ER": "ERI",
        "SZ": "SWZ",
        "ET": "ETH",
        "GA": "GAB",
        "GM": "GMB",
        "GH": "GHA",
        "GN": "GIN",
        "GW": "GNB",
        "KE": "KEN",
        "LS": "LSO",
        "LR": "LBR",
        "LY": "LBY",
        "MG": "MDG",
        "MW": "MWI",
        "ML": "MLI",
        "MR": "MRT",
        "MU": "MUS",
        "MA": "MAR",
        "MZ": "MOZ",
        "NA": "NAM",
        "NE": "NER",
        "NG": "NGA",
        "RW": "RWA",
        "ST": "STP",
        "SN": "SEN",
        "SC": "SYC",
        "SL": "SLE",
        "SO": "SOM",
        "ZA": "ZAF",
        "SS": "SSD",
        "SD": "SDN",
        "TZ": "TZA",
        "TG": "TGO",
        "TN": "TUN",
        "UG": "UGA",
        "ZM": "ZMB",
        "ZW": "ZWE",

        "PT": "PRT",
        "ES": "ESP",
        "FR": "FRA",
        "DE": "DEU",
        "IT": "ITA",
        "BE": "BEL",
        "NL": "NLD",
        "IE": "IRL",
        "GB": "GBR",
        "AT": "AUT",
        "CH": "CHE",
        "PL": "POL",
        "CZ": "CZE",
        "DK": "DNK",
        "SE": "SWE",
        "NO": "NOR",
        "FI": "FIN",
        "GR": "GRC",
        "RO": "ROU",
        "BG": "BGR",
        "HR": "HRV",
        "HU": "HUN",
        "SK": "SVK",
        "SI": "SVN",
        "LT": "LTU",
        "LV": "LVA",
        "EE": "EST",
        "MT": "MLT",
        "CY": "CYP",
        "LU": "LUX",
        "IS": "ISL",
        "RS": "SRB",
        "ME": "MNE",
        "MK": "MKD",
        "AL": "ALB",
        "BA": "BIH",
        "MD": "MDA",
        "UA": "UKR",
        "TR": "TUR",
        "RU": "RUS",
        "AD": "AND",
        "LI": "LIE",
        "MC": "MCO",
        "SM": "SMR",
        "VA": "VAT",
        "BY": "BLR",

        "AE": "ARE",
        "BH": "BHR",
        "IR": "IRN",
        "IQ": "IRQ",
        "IL": "ISR",
        "JO": "JOR",
        "KW": "KWT",
        "LB": "LBN",
        "OM": "OMN",
        "PS": "PSE",
        "QA": "QAT",
        "SA": "SAU",
        "SY": "SYR",
        "YE": "YEM",

        "AR": "ARG",
        "BO": "BOL",
        "BR": "BRA",
        "CA": "CAN",
        "CL": "CHL",
        "CO": "COL",
        "CR": "CRI",
        "CU": "CUB",
        "DO": "DOM",
        "EC": "ECU",
        "GT": "GTM",
        "GY": "GUY",
        "HN": "HND",
        "HT": "HTI",
        "JM": "JAM",
        "MX": "MEX",
        "NI": "NIC",
        "PA": "PAN",
        "PY": "PRY",
        "PE": "PER",
        "SR": "SUR",
        "TT": "TTO",
        "UY": "URY",
        "US": "USA",
        "VE": "VEN",

        "AF": "AFG",
        "AM": "ARM",
        "AU": "AUS",
        "AZ": "AZE",
        "BD": "BGD",
        "BT": "BTN",
        "BN": "BRN",
        "CN": "CHN",
        "FJ": "FJI",
        "GE": "GEO",
        "IN": "IND",
        "ID": "IDN",
        "JP": "JPN",
        "KZ": "KAZ",
        "KG": "KGZ",
        "KH": "KHM",
        "KI": "KIR",
        "LA": "LAO",
        "LK": "LKA",
        "MY": "MYS",
        "MV": "MDV",
        "MH": "MHL",
        "FM": "FSM",
        "MN": "MNG",
        "MM": "MMR",
        "NP": "NPL",
        "NZ": "NZL",
        "PK": "PAK",
        "PH": "PHL",
        "PW": "PLW",
        "PG": "PNG",
        "KP": "PRK",
        "KR": "KOR",
        "SG": "SGP",
        "SB": "SLB",
        "TJ": "TJK",
        "TH": "THA",
        "TL": "TLS",
        "TM": "TKM",
        "TO": "TON",
        "TV": "TUV",
        "UZ": "UZB",
        "VU": "VUT",
        "VN": "VNM",
        "WS": "WSM",
    }

    filtered = []

    for item in results:

        raw_country = (
            item.get("country")
            or ""
        ).strip()

        if not raw_country:
            continue

        # Normalização básica
        country_upper = raw_country.upper()

        # Primeiro: já é ISO3?
        country_code = country_upper

        # Segundo: ISO2?
        if country_upper in iso2_to_iso3:

            country_code = iso2_to_iso3[
                country_upper
            ]

        # Terceiro: nome completo
        if raw_country in country_names:

            country_code = country_names[
                raw_country
            ]

        # Quarto: comparação sem acentos,
        # para casos como São Tomé / Sao Tome
        normalised_country = unicodedata.normalize(
            "NFKD",
            raw_country
        ).encode(
            "ascii",
            "ignore"
        ).decode(
            "ascii"
        ).lower()

        for name, iso3 in country_names.items():

            normalised_name = unicodedata.normalize(
                "NFKD",
                name
            ).encode(
                "ascii",
                "ignore"
            ).decode(
                "ascii"
            ).lower()

            if normalised_country == normalised_name:

                country_code = iso3
                break

        if country_code in allowed:

            filtered.append(item)

    return filtered


# ============================================================
# FILTRO DE CATEGORIA
# ============================================================

def apply_category_filter(
    results,
    category
):

    category = (
        category or ""
    ).strip()

    if not category:
        return results

    return [
        item
        for item in results
        if item.get("category")
        == category
    ]


# ============================================================
# DEDUPLICAÇÃO
# ============================================================

def deduplicate_results(results):

    seen = set()
    output = []

    for item in results:

        key = (
            item.get("source"),
            item.get("title", "").strip().lower(),
            item.get("date"),
        )

        if key in seen:
            continue

        seen.add(key)

        output.append(item)

    return output


# ============================================================
# API — SOURCES
# ============================================================

@app.get("/api/sources")
def sources():

    return [

        {
            "name": "TED",
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
# API — SEARCH
# ============================================================

@app.get("/api/search")
def search(

    q: str = Query(
        default="archaeology"
    ),

    region: str = Query(
        default=""
    ),

    category: str = Query(
        default=""
    ),
):

    user_term = normalise_search_term(
        q
    )

    terms = []

    if user_term:
        terms.append(
            user_term
        )

    for term in DEFAULT_TERMS:

        if term.lower() not in [
            x.lower()
            for x in terms
        ]:

            terms.append(term)

    terms = terms[:12]

    all_results = []
    diagnostics = []

    # --------------------------------------------------------
    # TED
    # --------------------------------------------------------

    with ThreadPoolExecutor(
        max_workers=min(
            8,
            len(terms)
        )
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

                results, diagnostic = (
                    future.result()
                )

                all_results.extend(
                    results
                )

                diagnostics.append(
                    diagnostic
                )

            except Exception as exc:

                diagnostics.append({
                    "source": f"TED — {futures[future]}",
                    "ok": False,
                    "count": 0,
                    "error": str(exc),
                })

    # --------------------------------------------------------
    # WORLD BANK
    # --------------------------------------------------------

    wb_results, wb_diagnostic = (
        query_world_bank()
    )

    all_results.extend(
        wb_results
    )

    diagnostics.append(
        wb_diagnostic
    )

    # --------------------------------------------------------
    # DEDUPLICAÇÃO
    # --------------------------------------------------------

    all_results = deduplicate_results(
        all_results
    )

    # --------------------------------------------------------
    # FILTROS
    # --------------------------------------------------------

    all_results = apply_region_filter(
        all_results,
        region
    )

    all_results = apply_category_filter(
        all_results,
        category
    )

    # --------------------------------------------------------
    # SEGURANÇA FINAL:
    # remover concursos expirados
    # --------------------------------------------------------

    today = today_utc()

    valid_results = []

    for item in all_results:

        deadline = parse_date(
            item.get("deadline")
        )

        if deadline and deadline < today:
            continue

        valid_results.append(
            item
        )

    all_results = valid_results

    # --------------------------------------------------------
    # ORDENAÇÃO
    # --------------------------------------------------------

    all_results.sort(
        key=lambda x: (
            x.get("score", 0),
            x.get("deadline") or "9999-12-31",
            x.get("date") or "",
        ),
        reverse=True
    )

    return JSONResponse({

        "ok": True,

        "query": user_term,

        "region": region,

        "category": category,

        "results": all_results,

        "diagnostics": diagnostics,

        "portal_count": 2,

        "api_count": 2,

        "sources": 28,

        "searched_at": today.isoformat(),

    })


# ============================================================
# FICHEIROS DA APLICAÇÃO
# ============================================================

@app.get("/")
def root():

    return FileResponse(
        BASE_DIR / "index.html"
    )


@app.get("/app.js")
def app_js():

    return FileResponse(
        BASE_DIR / "app.js"
    )


@app.get("/manifest.json")
def manifest():

    return FileResponse(
        BASE_DIR / "manifest.json"
    )


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return {
        "ok": True,
        "app": "Arqueologia Radar",
        "date": today_utc().isoformat(),
    }
