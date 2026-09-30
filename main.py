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

WORLD_BANK_URL = (
    "https://search.worldbank.org/api/v2/procnotices"
)

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
# TERMOS DE PESQUISA
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
        "AUT", "BEL", "BGR", "HRV", "CYP", "CZE", "DNK",
        "EST", "FIN", "FRA", "DEU", "GRC", "HUN", "IRL",
        "ITA", "LVA", "LTU", "LUX", "MLT", "NLD", "POL",
        "PRT", "ROU", "SVK", "SVN", "ESP", "SWE",
        "ISL", "NOR", "CHE", "GBR", "ALB", "AND", "BIH",
        "LIE", "MCO", "MNE", "MKD", "SRB", "SMR", "TUR",
        "VAT", "XKX"
    },

    "África": {
        "DZA", "AGO", "BEN", "BWA", "BFA", "BDI", "CMR",
        "CPV", "CAF", "TCD", "COM", "COG", "COD", "CIV",
        "DJI", "EGY", "GNQ", "ERI", "SWZ", "ETH", "GAB",
        "GMB", "GHA", "GIN", "GNB", "KEN", "LSO", "LBR",
        "LBY", "MDG", "MWI", "MLI", "MRT", "MUS", "MAR",
        "MOZ", "NAM", "NER", "NGA", "RWA", "STP", "SEN",
        "SYC", "SLE", "SOM", "ZAF", "SSD", "SDN", "TZA",
        "TGO", "TUN", "UGA", "ZMB", "ZWE"
    },

    "Médio Oriente": {
        "ISR", "JOR", "LBN", "PSE", "SYR", "IRQ", "IRN",
        "SAU", "ARE", "QAT", "KWT", "BHR", "OMN", "YEM"
    },

    "Américas": {
        "CAN", "USA", "MEX", "GTM", "BLZ", "HND", "SLV",
        "NIC", "CRI", "PAN", "CUB", "DOM", "HTI", "JAM",
        "BHS", "BRB", "TTO", "COL", "VEN", "GUY", "SUR",
        "ECU", "PER", "BOL", "PRY", "CHL", "ARG", "URY",
        "BRA"
    },

    "Ásia-Pacífico": {
        "CHN", "JPN", "KOR", "PRK", "IND", "PAK", "BGD",
        "LKA", "NPL", "BTN", "MMR", "THA", "VNM", "KHM",
        "LAO", "MYS", "SGP", "IDN", "PHL", "BRN", "TLS",
        "AUS", "NZL", "FJI", "PNG", "WSM", "TON", "VUT",
        "SLB", "KAZ", "UZB", "TKM", "KGZ", "TJK", "MNG"
    }
}


# ============================================================
# UTILITÁRIOS
# ============================================================

def today_utc():
    return date.today()


def cutoff_date():
    return today_utc() - timedelta(days=PERIOD_DAYS)


def strip_html(value):
    """
    Remove HTML dos textos devolvidos pelos portais.
    """

    if value is None:
        return ""

    text = str(value)

    text = html.unescape(text)

    text = re.sub(
        r"(?i)<br\s*/?>",
        "\n",
        text
    )

    text = re.sub(
        r"(?i)</p\s*>",
        "\n",
        text
    )

    text = re.sub(
        r"(?i)</li\s*>",
        "\n",
        text
    )

    text = re.sub(
        r"<[^>]+>",
        " ",
        text
    )

    text = re.sub(
        r"[ \t]+",
        " ",
        text
    )

    text = re.sub(
        r"\n\s*\n+",
        "\n",
        text
    )

    return text.strip()


def clean_text(value):

    if value is None:
        return ""

    if isinstance(value, str):

        text = strip_html(value)

        return fix_mojibake(
            text
        ).strip()

    if isinstance(value, list):

        parts = []

        for item in value:

            txt = clean_text(item)

            if txt:
                parts.append(txt)

        return " ".join(parts).strip()

    if isinstance(value, dict):

        preferred = [
            "por",
            "pt",
            "eng",
            "en",
            "spa",
            "es",
            "fra",
            "fr",
            "deu",
            "de",
        ]

        for lang in preferred:

            if lang in value:

                txt = clean_text(
                    value[lang]
                )

                if txt:
                    return txt

        for item in value.values():

            txt = clean_text(item)

            if txt:
                return txt

    return fix_mojibake(
        str(value)
    ).strip()


def mojibake_score(text):

    markers = [
        "Ã",
        "Â",
        "â€",
        "â€“",
        "â€”",
        "â€œ",
        "â€",
        "â€™",
        "Ð",
        "Ñ",
        "�",
    ]

    return sum(
        text.count(x)
        for x in markers
    )


def fix_mojibake(value):

    if value is None:
        return ""

    text = str(value)

    replacements = {
        "â€“": "–",
        "â€”": "—",
        "â€œ": "“",
        "â€": "”",
        "â€™": "’",
        "â€¦": "…",
        "Â ": " ",
        "Â": "",
    }

    for old, new in replacements.items():

        text = text.replace(
            old,
            new
        )

    for _ in range(3):

        before = text

        try:

            candidate = (
                before
                .encode("latin1")
                .decode("utf-8")
            )

        except (
            UnicodeEncodeError,
            UnicodeDecodeError
        ):

            break

        if (
            mojibake_score(candidate)
            < mojibake_score(before)
        ):

            text = candidate

        else:

            break

    return html.unescape(text)


def parse_date(value):

    if value is None:
        return None

    if isinstance(value, list):

        for item in value:

            result = parse_date(item)

            if result:
                return result

        return None

    if isinstance(value, dict):

        for item in value.values():

            result = parse_date(item)

            if result:
                return result

        return None

    text = str(value).strip()

    # YYYY-MM-DD
    match = re.search(
        r"\b(\d{4})-(\d{2})-(\d{2})\b",
        text
    )

    if match:

        try:

            return date(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3))
            )

        except ValueError:
            pass

    # YYYYMMDD
    match = re.search(
        r"\b(\d{4})(\d{2})(\d{2})\b",
        text
    )

    if match:

        try:

            return date(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3))
            )

        except ValueError:
            pass

    # ISO com timestamp
    match = re.search(
        r"\b(\d{4})-(\d{2})-(\d{2})T",
        text
    )

    if match:

        try:

            return date(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3))
            )

        except ValueError:
            pass

    return None


def format_date(value):

    d = parse_date(value)

    if not d:
        return ""

    return d.strftime("%d/%m/%Y")


def extract_all_dates(value):

    found = []

    if value is None:
        return found

    if isinstance(
        value,
        (str, int, float)
    ):

        text = str(value)

        patterns = [
            r"\b\d{4}-\d{2}-\d{2}\b",
            r"\b\d{8}\b",
        ]

        for pattern in patterns:

            for match in re.findall(
                pattern,
                text
            ):

                d = parse_date(match)

                if d:
                    found.append(d)

        return found

    if isinstance(value, list):

        for item in value:

            found.extend(
                extract_all_dates(item)
            )

        return found

    if isinstance(value, dict):

        for item in value.values():

            found.extend(
                extract_all_dates(item)
            )

        return found

    return found


def extract_deadline(notice):

    candidates = []

    for field in [
        "deadline-date-lot",
        "deadline",
        "deadline-date-part",
    ]:

        if field in notice:

            candidates.extend(
                extract_all_dates(
                    notice.get(field)
                )
            )

    candidates = sorted(
        set(candidates)
    )

    today = today_utc()

    future = [
        d
        for d in candidates
        if d >= today
    ]

    if future:
        return future[0]

    if candidates:
        return candidates[-1]

    return None


def extract_cpvs(value):

    result = []

    if value is None:
        return result

    if isinstance(value, list):

        for item in value:

            result.extend(
                extract_cpvs(item)
            )

        return result

    if isinstance(value, dict):

        for item in value.values():

            result.extend(
                extract_cpvs(item)
            )

        return result

    text = str(value)

    codes = re.findall(
        r"\b\d{8}\b",
        text
    )

    for code in codes:

        if code not in result:
            result.append(code)

    return result


def extract_country(value):

    if value is None:
        return ""

    if isinstance(value, list):

        for item in value:

            result = extract_country(
                item
            )

            if result:
                return result

        return ""

    if isinstance(value, dict):

        for key in [
            "code",
            "country_code",
            "iso3",
            "iso_code",
            "value",
            "name",
        ]:

            if key in value:

                result = extract_country(
                    value[key]
                )

                if result:
                    return result

        for item in value.values():

            result = extract_country(
                item
            )

            if result:
                return result

        return ""

    text = str(value).strip()

    if re.fullmatch(
        r"[A-Za-z]{3}",
        text
    ):
        return text.upper()

    return text


def normalise_search_term(term):

    term = (
        term or ""
    ).strip()

    if not term:
        return "archaeology"

    term = term.replace(
        '"',
        " "
    )

    term = re.sub(
        r"\s+",
        " ",
        term
    )

    return term[:120]


# ============================================================
# TÍTULOS WORLD BANK
# ============================================================

def world_bank_title(value):
    """
    Obtém um título curto e limpo a partir do texto
    devolvido pelo World Bank.

    Alguns registos do World Bank não apresentam um
    campo de título separado e devolvem o anúncio inteiro
    em notice_text.
    """

    text = strip_html(value)

    if not text:
        return ""

    # Remove scores do tipo 100/100
    text = re.sub(
        r"^\s*\d{1,3}\s*/\s*100\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

    # Remove eventualmente scores repetidos
    text = re.sub(
        r"\b\d{1,3}\s*/\s*100\b",
        "",
        text,
        flags=re.IGNORECASE
    )

    # Normaliza espaços
    text = re.sub(
        r"\s+",
        " ",
        text
    ).strip()

    if not text:
        return ""

    # Alguns anúncios começam por expressões administrativas.
    # Tentamos encontrar um título útil.
    prefixes_to_remove = [
        "request for expressions of interest",
        "request for expression of interest",
        "invitation for bids",
        "invitation to bid",
        "request for bids",
        "procurement notice",
        "consultancy services",
    ]

    # Não eliminamos estas expressões automaticamente:
    # elas podem fazer parte do título real.
    # Apenas procuramos limitar o tamanho.

    if len(text) > 220:

        # Procurar primeiro ponto
        match = re.search(
            r"^(.{40,220}?)(?:\.\s+|\n|$)",
            text
        )

        if match:

            candidate = match.group(1).strip()

            if len(candidate) >= 40:
                text = candidate

        else:

            text = (
                text[:220]
                .rsplit(" ", 1)[0]
                .strip()
            )

    return text


# ============================================================
# CLASSIFICAÇÃO
# ============================================================

DIRECT_TERMS = [
    "archaeolog",
    "archaeological",
    "archaeology",
    "excavation",
    "archaeological excavation",
    "archaeological monitoring",
    "archaeological services",
    "archaeological survey",
    "archaeological investigation",
    "archaeological supervision",
    "archaeological watching",
    "archaeological fieldwork",
    "arqueologia",
    "arqueológico",
    "arqueologica",
    "escavação arqueológica",
    "escavações arqueológicas",
    "acompanhamento arqueológico",
    "trabalhos arqueológicos",
    "prospeção arqueológica",
    "prospecção arqueológica",
]

HERITAGE_TERMS = [
    "cultural heritage",
    "heritage conservation",
    "heritage management",
    "historic heritage",
    "architectural heritage",
    "archaeological heritage",
    "património cultural",
    "patrimonio cultural",
    "património arqueológico",
    "patrimonio arqueologico",
    "historic monument",
    "historical monument",
    "monument conservation",
]

CONSTRUCTION_TERMS = [
    "construction",
    "infrastructure",
    "road",
    "railway",
    "rail",
    "highway",
    "pipeline",
    "water",
    "energy",
    "wind farm",
    "solar farm",
    "development",
    "redevelopment",
    "building works",
    "construction works",
    "empreitada",
    "construção",
    "infraestrutura",
    "infra-estrutura",
    "estrada",
    "ferrovia",
    "linha ferroviária",
    "obra",
    "obras",
]

NOISE_TERMS = [
    "museum",
    "digital heritage",
    "data space",
    "research",
    "economic research",
    "satellite",
    "software",
    "leasing",
    "office",
    "equipment",
    "electrical",
    "lighting",
]


def classify_notice(
    title,
    cpvs,
    notice_type=""
):

    text = (
        f"{title} {notice_type}"
    ).lower()

    direct_hits = sum(
        1
        for term in DIRECT_TERMS
        if term.lower() in text
    )

    heritage_hits = sum(
        1
        for term in HERITAGE_TERMS
        if term.lower() in text
    )

    construction_hits = sum(
        1
        for term in CONSTRUCTION_TERMS
        if term.lower() in text
    )

    archaeology_cpvs = {
        "71351914",
        "71351910",
        "71351811",
        "71351720",
        "71351920",
    }

    cpv_hits = sum(
        1
        for cpv in cpvs
        if cpv in archaeology_cpvs
    )

    if direct_hits or cpv_hits:
        return "Arqueologia direta"

    if heritage_hits and (
        construction_hits
        or "archaeological" in text
    ):
        return "Património cultural"

    if construction_hits and heritage_hits:
        return (
            "Grande projeto / potencial subcontratação"
        )

    if heritage_hits:
        return "Património cultural"

    return (
        "Grande projeto / potencial subcontratação"
    )


def calculate_score(
    title,
    cpvs,
    category,
    deadline
):

    text = title.lower()

    score = 0

    direct = sum(
        1
        for term in DIRECT_TERMS
        if term.lower() in text
    )

    heritage = sum(
        1
        for term in HERITAGE_TERMS
        if term.lower() in text
    )

    construction = sum(
        1
        for term in CONSTRUCTION_TERMS
        if term.lower() in text
    )

    archaeology_cpvs = {
        "71351914",
        "71351910",
        "71351811",
        "71351720",
        "71351920",
    }

    cpv_hits = sum(
        1
        for cpv in cpvs
        if cpv in archaeology_cpvs
    )

    score += min(
        direct * 30,
        60
    )

    score += min(
        cpv_hits * 30,
        40
    )

    score += min(
        heritage * 15,
        30
    )

    if category == "Arqueologia direta":

        score += 25

    elif category == "Património cultural":

        score += 10

    else:

        score += 5

    if construction and (
        direct or heritage
    ):

        score += 10

    noise = sum(
        1
        for term in NOISE_TERMS
        if term.lower() in text
    )

    score -= min(
        noise * 12,
        35
    )

    if deadline:

        days_left = (
            deadline - today_utc()
        ).days

        if days_left >= 30:

            score += 5

        elif days_left >= 7:

            score += 3

        elif days_left >= 0:

            score += 1

    return max(
        0,
        min(100, score)
    )


# ============================================================
# TED
# ============================================================

def build_ted_query(term):

    cutoff = cutoff_date().strftime(
        "%Y%m%d"
    )

    return (
        f'notice-title~("{term}") '
        f'AND publication-date>={cutoff} '
        f'SORT BY publication-date DESC'
    )


def ted_request(
    query,
    page
):

    payload = {
        "query": query,
        "fields": TED_FIELDS,
        "page": page,
        "limit": PAGE_SIZE,
        "scope": "ACTIVE",
        "checkQuerySyntax": False,
        "paginationMode": "PAGE_NUMBER",
    }

    response = requests.post(
        TED_URL,
        json=payload,
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Arqueologia-Radar/1.0",
        },
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    return response.json()


def search_ted_term(term):

    term = normalise_search_term(
        term
    )

    query = build_ted_query(
        term
    )

    notices = []

    total = 0

    for page in range(
        1,
        MAX_PAGES_PER_TERM + 1
    ):

        try:

            data = ted_request(
                query,
                page
            )

        except Exception as exc:

            return {
                "term": term,
                "ok": False,
                "error": str(exc),
                "count": 0,
                "received": len(notices),
                "total": total,
                "notices": [],
            }

        page_notices = data.get(
            "notices",
            []
        )

        if page == 1:

            total = int(
                data.get(
                    "totalNoticeCount",
                    0
                ) or 0
            )

        if not isinstance(
            page_notices,
            list
        ):

            page_notices = []

        notices.extend(
            page_notices
        )

        if len(page_notices) < PAGE_SIZE:
            break

        if len(notices) >= total:
            break

    return {
        "term": term,
        "ok": True,
        "error": "",
        "count": len(notices),
        "received": len(notices),
        "total": total,
        "notices": notices,
    }


# ============================================================
# WORLD BANK
# ============================================================

def search_world_bank(term):

    try:

        params = {
            "qterm": term,
            "rows": 100,
            "os": 0,
            "format": "json",
        }

        response = requests.get(
            WORLD_BANK_URL,
            params=params,
            headers={
                "Accept": "application/json",
                "User-Agent": "Arqueologia-Radar/1.0",
            },
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        data = response.json()

        raw_notices = data.get(
            "procnotices",
            []
        )

        if isinstance(
            raw_notices,
            dict
        ):

            notices = list(
                raw_notices.values()
            )

        elif isinstance(
            raw_notices,
            list
        ):

            notices = raw_notices

        else:

            notices = []

        return {
            "term": term,
            "ok": True,
            "error": "",
            "count": len(notices),
            "total": int(
                data.get(
                    "total",
                    len(notices)
                ) or 0
            ),
            "notices": notices,
        }

    except Exception as exc:

        return {
            "term": term,
            "ok": False,
            "error": str(exc),
            "count": 0,
            "total": 0,
            "notices": [],
        }


# ============================================================
# NORMALIZAÇÃO TED
# ============================================================

def notice_to_result(notice):

    publication_number = clean_text(
        notice.get(
            "publication-number"
        )
    )

    publication = parse_date(
        notice.get(
            "publication-date"
        )
    )

    if not publication:
        return None

    if publication < cutoff_date():
        return None

    title = clean_text(
        notice.get(
            "notice-title"
        )
    )

    if not title:
        return None

    buyer = clean_text(
        notice.get(
            "buyer-name"
        )
    )

    country = extract_country(
        notice.get(
            "buyer-country"
        )
    )

    cpvs = extract_cpvs(
        notice.get(
            "classification-cpv"
        )
    )

    notice_type = clean_text(
        notice.get(
            "notice-type"
        )
    )

    deadline = extract_deadline(
        notice
    )

    if deadline and deadline < today_utc():
        return None

    category = classify_notice(
        title,
        cpvs,
        notice_type
    )

    score = calculate_score(
        title,
        cpvs,
        category,
        deadline
    )

    text = title.lower()

    has_relevant_term = any(
        term.lower() in text
        for term in (
            DIRECT_TERMS
            + HERITAGE_TERMS
        )
    )

    has_archaeology_cpv = any(
        cpv in {
            "71351914",
            "71351910",
            "71351811",
            "71351720",
            "71351920",
        }
        for cpv in cpvs
    )

    if (
        not has_relevant_term
        and not has_archaeology_cpv
    ):
        return None

    if score < 20:
        return None

    url = ""

    if publication_number:

        url = (
            "https://ted.europa.eu/pt/notice/-/detail/"
            + publication_number
        )

    return {
        "title": title,
        "source": "TED",
        "date": publication.isoformat(),
        "date_display": publication.strftime(
            "%d/%m/%Y"
        ),
        "country": country,
        "buyer": buyer,
        "deadline": (
            deadline.strftime(
                "%d/%m/%Y"
            )
            if deadline
            else ""
        ),
        "deadline_iso": (
            deadline.isoformat()
            if deadline
            else ""
        ),
        "cpv": ", ".join(cpvs),
        "category": category,
        "score": score,
        "url": url,
        "publication_number": publication_number,
        "notice_type": notice_type,
    }


# ============================================================
# NORMALIZAÇÃO WORLD BANK
# ============================================================

def world_bank_notice_to_result(
    notice
):

    if not isinstance(
        notice,
        dict
    ):
        return None

    # --------------------------------------------------------
    # ID
    # --------------------------------------------------------

    notice_id = clean_text(
        notice.get("id")
        or notice.get("notice_id")
        or notice.get("procurement_notice_id")
    )

    # --------------------------------------------------------
    # TÍTULO
    # --------------------------------------------------------

    # Primeiro tentamos campos que normalmente contêm
    # títulos reais.
    title = clean_text(
        notice.get("title")
        or notice.get("notice_title")
        or notice.get("display_title")
        or notice.get("bid_description")
    )

    # Só usamos notice_text como recurso secundário.
    # No World Bank este campo pode conter TODO o anúncio,
    # incluindo 100/100, HTML, descrição, requisitos, etc.
    if not title:

        title = world_bank_title(
            notice.get("notice_text")
            or notice.get("description")
            or ""
        )

    if not title:
        return None

    # Segurança adicional:
    # nunca deixar um score como título.
    title = re.sub(
        r"^\s*\d{1,3}\s*/\s*100\s*",
        "",
        title,
        flags=re.IGNORECASE
    ).strip()

    if not title:
        return None

    # --------------------------------------------------------
    # DESCRIÇÃO
    # --------------------------------------------------------

    description = strip_html(
        notice.get("notice_text")
        or notice.get("description")
        or ""
    )

    # Remove score do início da descrição
    description = re.sub(
        r"^\s*\d{1,3}\s*/\s*100\s*",
        "",
        description,
        flags=re.IGNORECASE
    ).strip()

    # --------------------------------------------------------
    # PAÍS
    # --------------------------------------------------------

    country_raw = (
        notice.get("country_code")
        or notice.get("project_ctry_code")
        or notice.get("country")
        or notice.get("project_ctry_name")
        or notice.get("country_name")
        or ""
    )

    country = extract_country(
        country_raw
    )

    country_name = clean_text(
        notice.get(
            "project_ctry_name"
        )
        or notice.get(
            "country_name"
        )
        or notice.get(
            "country"
        )
    )

    country_map = {
        "Afghanistan": "AFG",
        "Albania": "ALB",
        "Algeria": "DZA",
        "Angola": "AGO",
        "Argentina": "ARG",
        "Australia": "AUS",
        "Austria": "AUT",
        "Bangladesh": "BGD",
        "Belgium": "BEL",
        "Benin": "BEN",
        "Bolivia": "BOL",
        "Bosnia and Herzegovina": "BIH",
        "Botswana": "BWA",
        "Brazil": "BRA",
        "Bulgaria": "BGR",
        "Burkina Faso": "BFA",
        "Burundi": "BDI",
        "Cambodia": "KHM",
        "Cameroon": "CMR",
        "Canada": "CAN",
        "Cape Verde": "CPV",
        "Central African Republic": "CAF",
        "Chad": "TCD",
        "Chile": "CHL",
        "China": "CHN",
        "Colombia": "COL",
        "Comoros": "COM",
        "Congo": "COG",
        "Costa Rica": "CRI",
        "Croatia": "HRV",
        "Cyprus": "CYP",
        "Czech Republic": "CZE",
        "Democratic Republic of the Congo": "COD",
        "Denmark": "DNK",
        "Dominican Republic": "DOM",
        "Ecuador": "ECU",
        "Egypt": "EGY",
        "El Salvador": "SLV",
        "Eritrea": "ERI",
        "Estonia": "EST",
        "Eswatini": "SWZ",
        "Ethiopia": "ETH",
        "Fiji": "FJI",
        "Finland": "FIN",
        "France": "FRA",
        "Gabon": "GAB",
        "Gambia": "GMB",
        "Ghana": "GHA",
        "Greece": "GRC",
        "Guatemala": "GTM",
        "Guinea": "GIN",
        "Guinea-Bissau": "GNB",
        "Guyana": "GUY",
        "Haiti": "HTI",
        "Honduras": "HND",
        "Hungary": "HUN",
        "Iceland": "ISL",
        "India": "IND",
        "Indonesia": "IDN",
        "Iran": "IRN",
        "Iraq": "IRQ",
        "Ireland": "IRL",
        "Israel": "ISR",
        "Italy": "ITA",
        "Jamaica": "JAM",
        "Japan": "JPN",
        "Jordan": "JOR",
        "Kazakhstan": "KAZ",
        "Kenya": "KEN",
        "Kyrgyz Republic": "KGZ",
        "Laos": "LAO",
        "Latvia": "LVA",
        "Lebanon": "LBN",
        "Lesotho": "LSO",
        "Liberia": "LBR",
        "Libya": "LBY",
        "Lithuania": "LTU",
        "Luxembourg": "LUX",
        "Madagascar": "MDG",
        "Malawi": "MWI",
        "Malaysia": "MYS",
        "Maldives": "MDV",
        "Mali": "MLI",
        "Malta": "MLT",
        "Mauritania": "MRT",
        "Mauritius": "MUS",
        "Mexico": "MEX",
        "Moldova": "MDA",
        "Mongolia": "MNG",
        "Montenegro": "MNE",
        "Morocco": "MAR",
        "Mozambique": "MOZ",
        "Myanmar": "MMR",
        "Namibia": "NAM",
        "Nepal": "NPL",
        "Netherlands": "NLD",
        "New Zealand": "NZL",
        "Nicaragua": "NIC",
        "Niger": "NER",
        "Nigeria": "NGA",
        "North Macedonia": "MKD",
        "Norway": "NOR",
        "Pakistan": "PAK",
        "Panama": "PAN",
        "Papua New Guinea": "PNG",
        "Paraguay": "PRY",
        "Peru": "PER",
        "Philippines": "PHL",
        "Poland": "POL",
        "Portugal": "PRT",
        "Romania": "ROU",
        "Rwanda": "RWA",
        "Senegal": "SEN",
        "Serbia": "SRB",
        "Sierra Leone": "SLE",
        "Singapore": "SGP",
        "Slovak Republic": "SVK",
        "Slovenia": "SVN",
        "Solomon Islands": "SLB",
        "Somalia": "SOM",
        "South Africa": "ZAF",
        "South Korea": "KOR",
        "South Sudan": "SSD",
        "Spain": "ESP",
        "Sri Lanka": "LKA",
        "Sudan": "SDN",
        "Suriname": "SUR",
        "Sweden": "SWE",
        "Switzerland": "CHE",
        "Syria": "SYR",
        "Tajikistan": "TJK",
        "Tanzania": "TZA",
        "Thailand": "THA",
        "Timor-Leste": "TLS",
        "Togo": "TGO",
        "Tunisia": "TUN",
        "Türkiye": "TUR",
        "Turkey": "TUR",
        "Turkmenistan": "TKM",
        "Uganda": "UGA",
        "Ukraine": "UKR",
        "United Kingdom": "GBR",
        "United States": "USA",
        "United States of America": "USA",
        "Uruguay": "URY",
        "Uzbekistan": "UZB",
        "Vanuatu": "VUT",
        "Venezuela": "VEN",
        "Vietnam": "VNM",
        "Yemen": "YEM",
        "Zambia": "ZMB",
        "Zimbabwe": "ZWE",
    }

    if country_name in country_map:

        country = country_map[
            country_name
        ]

    # --------------------------------------------------------
    # DATA DE PUBLICAÇÃO
    # --------------------------------------------------------

    publication = None

    for field in [
        "publication_date",
        "publish_date",
        "publish_date_iso",
        "noticedate",
        "notice_date",
        "docdt",
        "date",
    ]:

        if field in notice:

            publication = parse_date(
                notice.get(field)
            )

            if publication:
                break

    # Não utilizar o prazo como data de publicação.
    # Se não existir data de publicação, usamos a data atual
    # apenas para evitar que o resultado seja descartado.
    if not publication:

        publication = today_utc()

    if publication < cutoff_date():
        return None

    # --------------------------------------------------------
    # PRAZO
    # --------------------------------------------------------

    deadline = None

    for field in [
        "submission_date",
        "deadline_date",
        "bid_submission_date",
        "closing_date",
        "closingdate",
    ]:

        if field not in notice:
            continue

        candidate = parse_date(
            notice.get(field)
        )

        if not candidate:
            continue

        if (
            deadline is None
            or candidate < deadline
        ):

            deadline = candidate

    # IMPORTANTE:
    # se o prazo já terminou, não mostrar o concurso.
    if deadline and deadline < today_utc():
        return None

    # --------------------------------------------------------
    # TIPO
    # --------------------------------------------------------

    notice_type = clean_text(
        notice.get(
            "notice_type"
        )
        or notice.get(
            "noticeType"
        )
        or notice.get(
            "procurement_method"
        )
    )

    # --------------------------------------------------------
    # SECTOR / CATEGORIA
    # --------------------------------------------------------

    sector = clean_text(
        notice.get(
            "sector"
        )
        or notice.get(
            "procurement_category"
        )
        or notice.get(
            "category"
        )
    )

    # --------------------------------------------------------
    # PROJECTO / ENTIDADE
    # --------------------------------------------------------

    buyer = clean_text(
        notice.get(
            "agency_name"
        )
        or notice.get(
            "implementing_agency"
        )
        or notice.get(
            "borrower"
        )
        or notice.get(
            "project_name"
        )
        or notice.get(
            "project"
        )
        or notice.get(
            "project_ctry_name"
        )
    )

    # --------------------------------------------------------
    # TEXTO PARA CLASSIFICAÇÃO
    # --------------------------------------------------------

    classification_text = (
        f"{title} "
        f"{description} "
        f"{sector} "
        f"{notice_type}"
    )

    category = classify_notice(
        classification_text,
        [],
        notice_type
    )

    score = calculate_score(
        classification_text,
        [],
        category,
        deadline
    )

    text_lower = classification_text.lower()

    relevant = any(
        term.lower() in text_lower
        for term in (
            DIRECT_TERMS
            + HERITAGE_TERMS
        )
    )

    if not relevant:
        return None

    # --------------------------------------------------------
    # URL
    # --------------------------------------------------------

    url = clean_text(
        notice.get(
            "url"
        )
        or notice.get(
            "notice_url"
        )
        or notice.get(
            "source_url"
        )
    )

    if not url and notice_id:

        url = (
            "https://projects.worldbank.org/"
            "en/projects-operations/"
            f"procurement-detail/{notice_id}"
        )

    # --------------------------------------------------------
    # RESULTADO NORMALIZADO
    # --------------------------------------------------------

    return {
        "title": title,
        "description": description,
        "source": "World Bank",
        "date": publication.isoformat(),
        "date_display": publication.strftime(
            "%d/%m/%Y"
        ),
        "country": country,
        "buyer": buyer,
        "deadline": (
            deadline.strftime(
                "%d/%m/%Y"
            )
            if deadline
            else ""
        ),
        "deadline_iso": (
            deadline.isoformat()
            if deadline
            else ""
        ),
        "cpv": "",
        "category": category,
        "score": score,
        "url": url,
        "publication_number": notice_id,
        "notice_type": notice_type,
        "sector": sector,
    }


# ============================================================
# FILTROS
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

    filtered = []

    for item in results:

        country = (
            item.get(
                "country"
            )
            or ""
        ).upper()

        if country in allowed:

            filtered.append(
                item
            )

    return filtered


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
        if item.get(
            "category"
        ) == category
    ]


# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/")
def home():

    return FileResponse(
        BASE_DIR / "index.html"
    )


@app.get("/app.js")
def javascript():

    response = FileResponse(
        BASE_DIR / "app.js",
        media_type="application/javascript"
    )

    response.headers[
        "Cache-Control"
    ] = (
        "no-cache, no-store, must-revalidate"
    )

    return response


@app.get("/manifest.json")
def manifest():

    return FileResponse(
        BASE_DIR / "manifest.json",
        media_type="application/manifest+json"
    )


@app.get("/api/health")
def health():

    return {
        "ok": True,
        "sources": 2,
        "api_sources": 2,
        "service": "Arqueologia Radar",
        "version": "1.1.0",
        "ted": TED_URL,
        "world_bank": WORLD_BANK_URL,
    }


@app.get("/api/sources")
def sources():

    return [
        {
            "name": "TED — Tenders Electronic Daily",
            "region": "Europa / internacional",
            "url": "https://ted.europa.eu/",
            "mode": "api",
        },
        {
            "name": "World Bank Procurement",
            "region": "Global",
            "url": (
                "https://projects.worldbank.org/"
            ),
            "mode": "api",
        },
    ]


# ============================================================
# PESQUISA
# ============================================================

@app.get("/api/search")
def search(
    q: str = Query(
        default="archaeology",
        max_length=120
    ),
    region: str = Query(
        default=""
    ),
    category: str = Query(
        default=""
    ),
):

    started = datetime.utcnow()

    user_term = normalise_search_term(
        q
    )

    terms = []

    for term in (
        [user_term]
        + DEFAULT_TERMS
    ):

        term = normalise_search_term(
            term
        )

        if not term:
            continue

        if term.lower() not in {
            x.lower()
            for x in terms
        }:

            terms.append(term)

    terms = terms[:12]

    diagnostics = []

    all_results = []

    # ========================================================
    # TED
    # ========================================================

    with ThreadPoolExecutor(
        max_workers=min(
            8,
            len(terms)
        )
    ) as executor:

        futures = {
            executor.submit(
                search_ted_term,
                term
            ): term
            for term in terms
        }

        for future in as_completed(
            futures
        ):

            term = futures[
                future
            ]

            try:

                result = future.result()

            except Exception as exc:

                result = {
                    "term": term,
                    "ok": False,
                    "error": str(exc),
                    "count": 0,
                    "received": 0,
                    "total": 0,
                    "notices": [],
                }

            diagnostics.append({
                "source": (
                    f"TED — {term}"
                ),
                "ok": result[
                    "ok"
                ],
                "count": result[
                    "count"
                ],
                "received": result[
                    "received"
                ],
                "total": result[
                    "total"
                ],
                "error": result.get(
                    "error",
                    ""
                ),
            })

            if result["ok"]:

                for notice in result[
                    "notices"
                ]:

                    try:

                        item = (
                            notice_to_result(
                                notice
                            )
                        )

                        if item:
                            all_results.append(
                                item
                            )

                    except Exception:
                        continue

    # ========================================================
    # WORLD BANK
    # ========================================================

    for term in terms:

        try:

            wb_result = (
                search_world_bank(
                    term
                )
            )

            diagnostics.append({
                "source": (
                    f"World Bank — {term}"
                ),
                "ok": wb_result[
                    "ok"
                ],
                "count": wb_result[
                    "count"
                ],
                "received": wb_result[
                    "count"
                ],
                "total": wb_result.get(
                    "total",
                    wb_result["count"]
                ),
                "error": wb_result.get(
                    "error",
                    ""
                ),
            })

            if wb_result["ok"]:

                for notice in (
                    wb_result[
                        "notices"
                    ]
                ):

                    try:

                        item = (
                            world_bank_notice_to_result(
                                notice
                            )
                        )

                        if item:

                            all_results.append(
                                item
                            )

                    except Exception:

                        continue

        except Exception as exc:

            diagnostics.append({
                "source": (
                    f"World Bank — {term}"
                ),
                "ok": False,
                "count": 0,
                "received": 0,
                "total": 0,
                "error": str(exc),
            })

    # ========================================================
    # DEDUPLICAÇÃO
    # ========================================================

    unique_results = {}

    for item in all_results:

        source = item.get(
            "source",
            ""
        )

        identifier = item.get(
            "publication_number",
            ""
        )

        title = item.get(
            "title",
            ""
        )

        date_value = item.get(
            "date",
            ""
        )

        if identifier:

            key = (
                f"{source}|"
                f"{identifier}"
            )

        else:

            key = (
                f"{source}|"
                f"{title}|"
                f"{date_value}"
            )

        unique_results[
            key
        ] = item

    results = list(
        unique_results.values()
    )

    # ========================================================
    # FILTROS
    # ========================================================

    results = apply_region_filter(
        results,
        region
    )

    results = apply_category_filter(
        results,
        category
    )

    # ========================================================
    # SEGURANÇA FINAL:
    # REMOVER PRAZOS JÁ EXPIRADOS
    # ========================================================

    today = today_utc()

    active_results = []

    for item in results:

        deadline_text = item.get(
            "deadline_iso",
            ""
        )

        if deadline_text:

            deadline = parse_date(
                deadline_text
            )

            if deadline and deadline < today:
                continue

        active_results.append(
            item
        )

    results = active_results

    # ========================================================
    # ORDENAÇÃO
    # ========================================================

    def result_sort_key(item):

        deadline = (
            item.get(
                "deadline_iso"
            )
            or "9999-12-31"
        )

        return (
            -int(
                item.get(
                    "score",
                    0
                )
            ),
            deadline,
            item.get(
                "date",
                ""
            ),
        )

    results.sort(
        key=result_sort_key
    )

    diagnostics.sort(
        key=lambda x: x[
            "source"
        ]
    )

    elapsed = (
        datetime.utcnow()
        - started
    ).total_seconds()

    return JSONResponse({
        "results": results,
        "diagnostics": diagnostics,
        "portal_count": 2,
        "api_count": 2,
        "searched_at": (
            today_utc().isoformat()
        ),
        "period_days": PERIOD_DAYS,
        "cutoff_date": (
            cutoff_date().isoformat()
        ),
        "query": user_term,
        "region": region,
        "category_filter": category,
        "result_count": len(results),
        "elapsed_seconds": round(
            elapsed,
            2
        ),
    })


# ============================================================
# EXECUÇÃO LOCAL
# ============================================================

if __name__ == "__main__":

    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,
    )
