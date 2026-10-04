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
# ARQUEOLOGIA RADAR
# Versão 2.4 - pesquisa global consolidada
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Arqueologia Radar",
    version="2.4"
)

REQUEST_TIMEOUT = 30
PERIOD_DAYS = 365
PAGE_SIZE = 100

TED_URL = "https://api.ted.europa.eu/v3/notices/search"

WORLD_BANK_URL = (
    "https://search.worldbank.org/api/v2/procnotices"
)

SOUTH_AFRICA_URL = (
    "https://ocds-api.etenders.gov.za/api/OCDSReleases"
)

SECOP_URL = (
    "https://www.datos.gov.co/resource/p6dx-8zbt.json"
)

# ============================================================
# NOMES SEGUROS DAS FONTES
# ============================================================

TED_SOURCE = (
    "TED " + chr(0x2014) + " Europa"
)

SECOP_SOURCE = (
    "SECOP II " + chr(0x2014) + " Col"
    + chr(0x00f4) + "mbia"
)

SOUTH_AFRICA_SOURCE = (
    "South Africa eTenders " + chr(0x2014) + " OCDS"
)

# ============================================================
# FONTES
# ============================================================

SOURCES = [
    {
        "name": TED_SOURCE,
        "region": "Europa",
        "country": "UE",
        "url": "https://ted.europa.eu/",
        "type": "api",
        "automatic": True,
    },
    {
        "name": "World Bank Procurement",
        "region": "Global",
        "country": "",
        "url": "https://projects.worldbank.org/en/projects-operations/procurement",
        "type": "api",
        "automatic": True,
    },
    {
        "name": SOUTH_AFRICA_SOURCE,
        "region": "\u00c1frica",
        "country": "\u00c1frica do Sul",
        "url": "https://www.etenders.gov.za/",
        "type": "api",
        "automatic": False,
    },
    {
        "name": SECOP_SOURCE,
        "region": "Am\u00e9rica",
        "country": "Col\u00f4mbia",
        "url": "https://www.colombiacompra.gov.co/",
        "type": "api",
        "automatic": True,
    },

    # --------------------------------------------------------
    # PORTAIS / FONTES DE REFERÊNCIA
    # --------------------------------------------------------

    {
        "name": "AfDB " + chr(0x2014) + " African Development Bank",
        "region": "\u00c1frica",
        "country": "",
        "url": "https://www.afdb.org/en/projects-and-operations/procurement",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "SAM.gov " + chr(0x2014) + " Estados Unidos",
        "region": "Am\u00e9rica",
        "country": "EUA",
        "url": "https://sam.gov/content/opportunities",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "BASE " + chr(0x2014) + " Portugal",
        "region": "Europa",
        "country": "Portugal",
        "url": "https://www.base.gov.pt/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "Contrataci\u00f3n del Estado " + chr(0x2014) + " Espanha",
        "region": "Europa",
        "country": "Espanha",
        "url": "https://contrataciondelestado.es/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "UNDB " + chr(0x2014) + " United Nations Development Business",
        "region": "Global",
        "country": "",
        "url": "https://devbusiness.un.org/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "UNGM " + chr(0x2014) + " United Nations Global Marketplace",
        "region": "Global",
        "country": "",
        "url": "https://www.ungm.org/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "EBRD " + chr(0x2014) + " European Bank for Reconstruction and Development",
        "region": "Europa / \u00c1sia",
        "country": "",
        "url": "https://www.ebrd.com/work-with-us/procurement.html",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "EIB " + chr(0x2014) + " European Investment Bank",
        "region": "Europa",
        "country": "",
        "url": "https://www.eib.org/en/projects/procurement/index.htm",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "Oman " + chr(0x2014) + " Tender Board",
        "region": "\u00c1sia",
        "country": "Om\u00e3",
        "url": "https://etendering.tenderboard.gov.om/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "Etimad " + chr(0x2014) + " Ar\u00e1bia Saudita",
        "region": "\u00c1sia",
        "country": "Ar\u00e1bia Saudita",
        "url": "https://tenders.etimad.sa/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "UAE " + chr(0x2014) + " Federal Procurement",
        "region": "\u00c1sia",
        "country": "Emirados \u00c1rabes Unidos",
        "url": "https://mof.gov.ae/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "Qatar " + chr(0x2014) + " Government Procurement",
        "region": "\u00c1sia",
        "country": "Qatar",
        "url": "https://monaqasat.mof.gov.qa/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "Maroc " + chr(0x2014) + " March\u00e9s Publics",
        "region": "\u00c1frica",
        "country": "Marrocos",
        "url": "https://www.marchespublics.gov.ma/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "Uganda " + chr(0x2014) + " eGP",
        "region": "\u00c1frica",
        "country": "Uganda",
        "url": "https://egpuganda.go.ug/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "Kenya " + chr(0x2014) + " Public Procurement",
        "region": "\u00c1frica",
        "country": "Qu\u00e9nia",
        "url": "https://www.treasury.go.ke/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "Tanzania " + chr(0x2014) + " PPRA",
        "region": "\u00c1frica",
        "country": "Tanz\u00e2nia",
        "url": "https://www.ppra.go.tz/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "Mo\u00e7ambique " + chr(0x2014) + " Contrata\u00e7\u00e3o P\u00fablica",
        "region": "\u00c1frica",
        "country": "Mo\u00e7ambique",
        "url": "https://www.ufsa.gov.mz/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "ChileCompra",
        "region": "Am\u00e9rica",
        "country": "Chile",
        "url": "https://www.mercadopublico.cl/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "Brasil " + chr(0x2014) + " Compras.gov.br",
        "region": "Am\u00e9rica",
        "country": "Brasil",
        "url": "https://www.gov.br/compras/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "IDB " + chr(0x2014) + " Inter-American Development Bank",
        "region": "Am\u00e9rica",
        "country": "",
        "url": "https://www.iadb.org/en/how-we-work/working-us/procurement",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "ADB " + chr(0x2014) + " Asian Development Bank",
        "region": "\u00c1sia",
        "country": "",
        "url": "https://www.adb.org/work-with-us/procurement",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "AusTender " + chr(0x2014) + " Austr\u00e1lia",
        "region": "\u00c1sia / Oce\u00e2nia",
        "country": "Austr\u00e1lia",
        "url": "https://www.tenders.gov.au/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "NZ GETS " + chr(0x2014) + " Nova Zel\u00e2ndia",
        "region": "\u00c1sia / Oce\u00e2nia",
        "country": "Nova Zel\u00e2ndia",
        "url": "https://www.gets.govt.nz/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "Red El\u00e9ctrica / Redeia",
        "region": "Europa",
        "country": "Espanha",
        "url": "https://www.ree.es/",
        "type": "portal",
        "automatic": False,
    },
]

# ============================================================
# CPV
# ============================================================

ARCHAEOLOGY_CPVS = {
    "71351914",
    "71351910",
    "71351900",
    "71351720",
    "71351811",
    "71351730",
}

GENERAL_EXCAVATION_CPV = {
    "45112450",
}

# ============================================================
# TERMOS ARQUEOLÓGICOS DIRETOS
# ============================================================

DIRECT_TERMS = [
    "archaeology",
    "archaeological",
    "archaeologist",
    "archaeologists",
    "archaeological excavation",
    "archaeological excavations",
    "archaeological monitoring",
    "archaeological survey",
    "archaeological investigation",
    "archaeological investigations",
    "archaeological services",
    "archaeological assessment",
    "archaeological fieldwork",
    "archaeological watching brief",
    "archaeological supervision",
    "archaeological coordinator",
    "archaeological consultancy",
    "archaeological consultant",
    "archaeological work",
    "archaeological works",

    "arch\u00e9ologie",
    "arch\u00e9ologique",
    "arch\u00e9ologue",
    "fouilles arch\u00e9ologiques",

    "arqueologia",
    "arqueol\u00f3gico",
    "arqueol\u00f3gica",
    "arque\u00f3logo",
    "arque\u00f3loga",
    "escava\u00e7\u00e3o arqueol\u00f3gica",
    "acompanhamento arqueol\u00f3gico",
    "monitoriza\u00e7\u00e3o arqueol\u00f3gica",
    "prospe\u00e7\u00e3o arqueol\u00f3gica",
    "prospec\u00e7\u00e3o arqueol\u00f3gica",
    "avalia\u00e7\u00e3o arqueol\u00f3gica",
    "trabalhos arqueol\u00f3gicos",
    "servi\u00e7os arqueol\u00f3gicos",
    "consultoria arqueol\u00f3gica",
    "consultor arqueol\u00f3gico",
    "arque\u00f3logo coordenador",

    "arch\u00e4ologie",
    "arch\u00e4ologisch",
    "arch\u00e4ologe",

    "archeologie",
    "archeologisch",
]

# ============================================================
# FUNÇÕES / SERVIÇOS DE APOIO
# ============================================================

ARCHAEOLOGY_SUPPORT_EXCLUSIONS = [
    "photographer",
    "photography",
    "photographic",
    "architect",
    "architecture design",
    "architectural design",
    "legal expert",
    "legal services",
    "lawyer",
    "attorney",
    "social media",
    "communication designer",
    "graphic designer",
    "designer",
    "communications",
    "communication",
    "public relations",
    "marketing",
    "media coordinator",
    "signboards",
    "signboard",
    "reflective signboards",
    "supply of signboards",
    "office equipment",
    "computer equipment",
    "information technology",
    "software",
    "website",
    "printing",
    "printing services",
    "vehicle",
    "vehicles",
    "furniture",
    "stationery",
    "training",
    "catering",
    "security services",
    "cleaning services",
]

# ============================================================
# TERMOS DE PATRIMÓNIO
# ============================================================

HERITAGE_TERMS = [
    "cultural heritage",
    "heritage assessment",
    "heritage impact assessment",
    "historic environment",
    "historical environment",
    "built heritage",
    "archaeological heritage",
    "heritage management",
    "chance finds",

    "patrim\u00f3nio cultural",
    "patrimonio cultural",
    "avalia\u00e7\u00e3o patrimonial",
    "impacte patrimonial",
    "impacto patrimonial",

    "patrimoine culturel",
    "patrimoine arch\u00e9ologique",
    "patrimoine historique",

    "heritage conservation",
    "heritage management",
]

# ============================================================
# GRANDES INFRAESTRUTURAS
# ============================================================

MAJOR_PROJECT_TERMS = [
    "railway",
    "rail",
    "road",
    "highway",
    "motorway",
    "mine",
    "mining",
    "oil",
    "gas",
    "pipeline",
    "airport",
    "port",
    "dam",
    "hydropower",
    "energy",
    "power line",
    "transmission line",
    "corridor",
    "metro",
    "subway",
    "wind farm",
    "solar farm",
    "photovoltaic",
    "infrastructure",
    "construction",
    "industrial",

    "ferroviaire",
    "route",
    "autoroute",
    "a\u00e9roport",
    "port",
    "barrage",
    "\u00e9nergie",
    "infrastructure",

    "ferrovia",
    "rodovia",
    "aeroporto",
    "porto",
    "barragem",
    "energia",
]

# ============================================================
# MAPAS DE PAÍSES
# ============================================================

COUNTRY_MAP = {
    "PT": "Portugal",
    "ES": "Espanha",
    "FR": "Fran\u00e7a",
    "DE": "Alemanha",
    "IT": "It\u00e1lia",
    "BE": "B\u00e9lgica",
    "NL": "Pa\u00edses Baixos",
    "LU": "Luxemburgo",
    "IE": "Irlanda",
    "AT": "\u00c1ustria",
    "PL": "Pol\u00f3nia",
    "CZ": "Ch\u00e9quia",
    "SK": "Eslov\u00e1quia",
    "HU": "Hungria",
    "RO": "Rom\u00e9nia",
    "BG": "Bulg\u00e1ria",
    "HR": "Cro\u00e1cia",
    "SI": "Eslov\u00e9nia",
    "SE": "Su\u00e9cia",
    "FI": "Finl\u00e2ndia",
    "DK": "Dinamarca",
    "EE": "Est\u00f3nia",
    "LV": "Let\u00f3nia",
    "LT": "Litu\u00e2nia",
    "GR": "Gr\u00e9cia",
    "CY": "Chipre",
    "MT": "Malta",
    "NO": "Noruega",
    "IS": "Isl\u00e2ndia",
    "CH": "Su\u00ed\u00e7a",
    "UK": "Reino Unido",
    "GB": "Reino Unido",

    "MA": "Marrocos",
    "DZ": "Arg\u00e9lia",
    "TN": "Tun\u00edsia",
    "EG": "Egito",
    "ZA": "\u00c1frica do Sul",
    "KE": "Qu\u00e9nia",
    "UG": "Uganda",
    "TZ": "Tanz\u00e2nia",
    "MZ": "Mo\u00e7ambique",
    "NG": "Nig\u00e9ria",
    "GH": "Gana",
    "ET": "Eti\u00f3pia",

    "US": "Estados Unidos",
    "CA": "Canad\u00e1",
    "MX": "M\u00e9xico",
    "BR": "Brasil",
    "CL": "Chile",
    "CO": "Col\u00f4mbia",
    "PE": "Peru",
    "AR": "Argentina",
    "UY": "Uruguai",
    "PY": "Paraguai",

    "SA": "Ar\u00e1bia Saudita",
    "AE": "Emirados \u00c1rabes Unidos",
    "QA": "Qatar",
    "OM": "Om\u00e3",
    "JO": "Jord\u00e2nia",
    "IL": "Israel",
    "TR": "Turquia",
    "IN": "\u00cdndia",
    "PK": "Paquist\u00e3o",
    "BD": "Bangladesh",
    "LK": "Sri Lanka",
    "CN": "China",
    "JP": "Jap\u00e3o",
    "KR": "Coreia do Sul",
    "ID": "Indon\u00e9sia",
    "MY": "Mal\u00e1sia",
    "TH": "Tail\u00e2ndia",
    "VN": "Vietname",

    "AU": "Austr\u00e1lia",
    "NZ": "Nova Zel\u00e2ndia",
}

ISO3_MAP = {
    "PRT": "Portugal",
    "ESP": "Espanha",
    "FRA": "Fran\u00e7a",
    "DEU": "Alemanha",
    "ITA": "It\u00e1lia",
    "BEL": "B\u00e9lgica",
    "NLD": "Pa\u00edses Baixos",
    "LUX": "Luxemburgo",
    "IRL": "Irlanda",
    "AUT": "\u00c1ustria",
    "POL": "Pol\u00f3nia",
    "CZE": "Ch\u00e9quia",
    "SVK": "Eslov\u00e1quia",
    "HUN": "Hungria",
    "ROU": "Rom\u00e9nia",
    "BGR": "Bulg\u00e1ria",
    "HRV": "Cro\u00e1cia",
    "SVN": "Eslov\u00e9nia",
    "SWE": "Su\u00e9cia",
    "FIN": "Finl\u00e2ndia",
    "DNK": "Dinamarca",
    "EST": "Est\u00f3nia",
    "LVA": "Let\u00f3nia",
    "LTU": "Litu\u00e2nia",
    "GRC": "Gr\u00e9cia",
    "CYP": "Chipre",
    "MLT": "Malta",
    "NOR": "Noruega",
    "ISL": "Isl\u00e2ndia",
    "CHE": "Su\u00ed\u00e7a",
    "GBR": "Reino Unido",

    "MAR": "Marrocos",
    "DZA": "Arg\u00e9lia",
    "TUN": "Tun\u00edsia",
    "EGY": "Egito",
    "ZAF": "\u00c1frica do Sul",
    "KEN": "Qu\u00e9nia",
    "UGA": "Uganda",
    "TZA": "Tanz\u00e2nia",
    "MOZ": "Mo\u00e7ambique",
    "NGA": "Nig\u00e9ria",
    "GHA": "Gana",
    "ETH": "Eti\u00f3pia",

    "USA": "Estados Unidos",
    "CAN": "Canad\u00e1",
    "MEX": "M\u00e9xico",
    "BRA": "Brasil",
    "CHL": "Chile",
    "COL": "Col\u00f4mbia",
    "PER": "Peru",
    "ARG": "Argentina",
    "URY": "Uruguai",
    "PRY": "Paraguai",

    "SAU": "Ar\u00e1bia Saudita",
    "ARE": "Emirados \u00c1rabes Unidos",
    "QAT": "Qatar",
    "OMN": "Om\u00e3",
    "JOR": "Jord\u00e2nia",
    "ISR": "Israel",
    "TUR": "Turquia",
    "IND": "\u00cdndia",
    "PAK": "Paquist\u00e3o",
    "BGD": "Bangladesh",
    "LKA": "Sri Lanka",
    "CHN": "China",
    "JPN": "Jap\u00e3o",
    "KOR": "Coreia do Sul",
    "IDN": "Indon\u00e9sia",
    "MYS": "Mal\u00e1sia",
    "THA": "Tail\u00e2ndia",
    "VNM": "Vietname",

    "AUS": "Austr\u00e1lia",
    "NZL": "Nova Zel\u00e2ndia",
}

# ============================================================
# UTILITÁRIOS DE TEXTO
# ============================================================

def repair_mojibake(value):

    if not isinstance(value, str):
        return value

    current = value

    for _ in range(6):

        bad_markers = (
            "Ã",
            "Â",
            "â",
            "ð",
            "�",
            "MÃ",
            "ColÃ",
        )

        if not any(
            marker in current
            for marker in bad_markers
        ):
            break

        try:

            candidate = (
                current
                .encode("latin1")
                .decode("utf-8")
            )

        except (
            UnicodeEncodeError,
            UnicodeDecodeError
        ):
            break

        if candidate == current:
            break

        current = candidate

    replacements = {
        "â€”": "—",
        "â€“": "–",
        "â€˜": "‘",
        "â€™": "’",
        "â€œ": "“",
        "â€": "”",
        "â€¦": "…",
        "Â ": " ",
        "Ã´": "ô",
        "Ã´": "ô",
        "Ã³": "ó",
        "Ã©": "é",
        "Ãª": "ê",
        "Ã§": "ç",
        "Ã£": "ã",
        "Ã¡": "á",
        "Ãº": "ú",
        "Ã­": "í",
        "Ã¬": "ì",
        "Ã¨": "è",
        "Ã‰": "É",
        "Ãˆ": "È",
        "Ã€": "À",
        "Ã‚": "Â",
        "Ã”": "Ô",
        "Ã“": "Ó",
        "Ã‡": "Ç",
        "Ãƒ": "Ã",
        "Ãš": "Ú",
        "Ã": "Á",
        "Ã": "Í",
        "Ã‰": "É",
        "MÃˆS": "MÈS",
        "MÃˆs": "MÈs",
        "MÃ¨S": "MÈS",
        "MÃ¨s": "Mès",
    }

    for old, new in replacements.items():
        current = current.replace(
            old,
            new
        )

    return current


def choose_multilingual_text(value):

    if value is None:
        return ""

    if isinstance(value, str):
        return repair_mojibake(value)

    if isinstance(value, list):

        for item in value:

            if isinstance(item, dict):

                lang = normalize_text(
                    item.get("language")
                    or item.get("lang")
                    or item.get("language-code")
                    or ""
                )

                text_value = (
                    item.get("text")
                    or item.get("value")
                    or item.get("content")
                    or ""
                )

                if (
                    text_value
                    and lang in {
                        "eng",
                        "en",
                        "english",
                    }
                ):
                    return choose_multilingual_text(
                        text_value
                    )

        for item in value:

            result = choose_multilingual_text(
                item
            )

            if result:
                return result

        return ""

    if isinstance(value, dict):

        preferred_keys = [
            "eng",
            "en",
            "english",
            "fra",
            "fr",
            "fre",
            "deu",
            "de",
            "ita",
            "it",
            "spa",
            "es",
            "por",
            "pt",
        ]

        for key in preferred_keys:

            if key in value:

                result = choose_multilingual_text(
                    value[key]
                )

                if result:
                    return result

        for key in (
            "text",
            "value",
            "content",
            "title",
            "name",
            "description",
        ):

            if key in value:

                result = choose_multilingual_text(
                    value[key]
                )

                if result:
                    return result

        for item in value.values():

            result = choose_multilingual_text(
                item
            )

            if result:
                return result

        return ""

    return repair_mojibake(
        str(value)
    )


def normalize_text(value):

    if value is None:
        return ""

    value = choose_multilingual_text(
        value
    )

    value = repair_mojibake(
        value
    )

    value = html.unescape(
        value
    )

    value = unicodedata.normalize(
        "NFKD",
        value
    )

    value = "".join(
        c
        for c in value
        if not unicodedata.combining(c)
    )

    value = value.lower()

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def clean_text(value):

    value = choose_multilingual_text(
        value
    )

    value = repair_mojibake(
        value
    )

    value = html.unescape(
        value
    )

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

    return repair_mojibake(
        value.strip()
    )


# ============================================================
# DATAS
# ============================================================

def cutoff_date():

    return date.today() - timedelta(
        days=PERIOD_DAYS
    )


def parse_date(value):

    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    value = choose_multilingual_text(
        value
    ).strip()

    if not value:
        return None

    match = re.search(
        r"\d{4}-\d{2}-\d{2}",
        value
    )

    if match:
        value = match.group(0)

    else:
        value = value[:10]

    for fmt in (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
    ):

        try:

            return datetime.strptime(
                value,
                fmt
            ).date()

        except Exception:
            pass

    return None


def date_string(value):

    d = parse_date(
        value
    )

    if d:
        return d.isoformat()

    return ""


# ============================================================
# PESQUISA RECURSIVA DE CAMPOS
# ============================================================

def recursive_values(obj):

    if isinstance(obj, dict):

        for key, value in obj.items():

            yield key, value

            for nested_key, nested_value in recursive_values(
                value
            ):
                yield nested_key, nested_value

    elif isinstance(obj, list):

        for item in obj:

            for nested_key, nested_value in recursive_values(
                item
            ):
                yield nested_key, nested_value


def first_value_recursive(
    row,
    exact_keys=None,
    key_fragments=None
):

    exact_keys = exact_keys or []
    key_fragments = key_fragments or []

    exact_keys_normalized = {
        normalize_key_name(x)
        for x in exact_keys
    }

    for key, value in recursive_values(row):

        key_n = normalize_key_name(
            key
        )

        if key_n in exact_keys_normalized:

            if value not in (
                None,
                "",
                [],
                {},
            ):
                return value

    for key, value in recursive_values(row):

        key_n = normalize_key_name(
            key
        )

        if any(
            fragment in key_n
            for fragment in key_fragments
        ):

            if value not in (
                None,
                "",
                [],
                {},
            ):
                return value

    return ""


def normalize_key_name(value):

    value = str(
        value or ""
    )

    value = repair_mojibake(
        value
    )

    value = value.lower()

    value = re.sub(
        r"[^a-z0-9]+",
        "_",
        value
    )

    return value.strip("_")


# ============================================================
# PAÍSES
# ============================================================

def country_from_code(value):

    value = choose_multilingual_text(
        value
    ).strip().upper()

    if value in COUNTRY_MAP:
        return COUNTRY_MAP[value]

    if value in ISO3_MAP:
        return ISO3_MAP[value]

    return repair_mojibake(
        value
    )


def extract_country(item):

    candidates = [
        item.get("buyer-country"),
        item.get("buyerCountry"),
        item.get("country"),
        item.get("country-code"),
        item.get("buyer_country"),
        item.get("countryCode"),
        item.get("country_code"),
        item.get("countryname"),
        item.get("country_name"),
    ]

    for candidate in candidates:

        text = choose_multilingual_text(
            candidate
        ).strip()

        if not text:
            continue

        code = text.upper()

        if code in COUNTRY_MAP:
            return COUNTRY_MAP[code]

        if code in ISO3_MAP:
            return ISO3_MAP[code]

        return repair_mojibake(
            text
        )

    return ""


# ============================================================
# IDENTIFICAÇÃO DE PAÍS EM TEXTO
# ============================================================

COUNTRY_TEXT_PATTERNS = {
    "afghanistan": "Afeganistão",
    "serbia": "Sérvia",
    "pakistan": "Paquistão",
    "india": "Índia",
    "bangladesh": "Bangladesh",
    "nepal": "Nepal",
    "morocco": "Marrocos",
    "algeria": "Argélia",
    "tunisia": "Tunísia",
    "egypt": "Egito",
    "south africa": "África do Sul",
    "kenya": "Quénia",
    "uganda": "Uganda",
    "tanzania": "Tanzânia",
    "mozambique": "Moçambique",
    "nigeria": "Nigéria",
    "ghana": "Gana",
    "ethiopia": "Etiópia",
    "colombia": "Colômbia",
    "brazil": "Brasil",
    "chile": "Chile",
    "peru": "Peru",
    "argentina": "Argentina",
    "mexico": "México",
    "canada": "Canadá",
    "united states": "Estados Unidos",
    "usa": "Estados Unidos",
    "portugal": "Portugal",
    "spain": "Espanha",
    "france": "França",
    "germany": "Alemanha",
    "italy": "Itália",
    "netherlands": "Países Baixos",
    "belgium": "Bélgica",
    "ireland": "Irlanda",
    "poland": "Polónia",
    "romania": "Roménia",
    "bulgaria": "Bulgária",
    "croatia": "Croácia",
    "greece": "Grécia",
    "norway": "Noruega",
    "switzerland": "Suíça",
    "united kingdom": "Reino Unido",
    "saudi arabia": "Arábia Saudita",
    "united arab emirates": "Emirados Árabes Unidos",
    "qatar": "Qatar",
    "oman": "Omã",
    "jordan": "Jordânia",
    "turkey": "Turquia",
    "china": "China",
    "japan": "Japão",
    "south korea": "Coreia do Sul",
    "indonesia": "Indonésia",
    "malaysia": "Malásia",
    "thailand": "Tailândia",
    "vietnam": "Vietname",
    "australia": "Austrália",
    "new zealand": "Nova Zelândia",
}


def country_from_text(*values):

    text = " ".join(
        clean_text(value)
        for value in values
        if value
    )

    text_n = normalize_text(
        text
    )

    if not text_n:
        return ""

    for pattern, country in COUNTRY_TEXT_PATTERNS.items():

        pattern_n = normalize_text(
            pattern
        )

        if pattern_n in text_n:
            return country

    return ""


# ============================================================
# REGIÕES
# ============================================================

def region_from_country(country):

    n = normalize_text(
        country
    )

    europe = {
        "portugal",
        "espanha",
        "franca",
        "alemanha",
        "italia",
        "belgica",
        "paises baixos",
        "luxemburgo",
        "irlanda",
        "austria",
        "polonia",
        "chequia",
        "eslovaquia",
        "hungria",
        "romenia",
        "bulgaria",
        "croacia",
        "eslovenia",
        "suecia",
        "finlandia",
        "dinamarca",
        "estonia",
        "letonia",
        "lituania",
        "grecia",
        "chipre",
        "malta",
        "noruega",
        "islandia",
        "suica",
        "reino unido",
        "servia",
    }

    africa = {
        "marrocos",
        "argelia",
        "tunisia",
        "egito",
        "africa do sul",
        "quenia",
        "uganda",
        "tanzania",
        "mocambique",
        "nigeria",
        "gana",
        "etiopia",
    }

    america = {
        "estados unidos",
        "canada",
        "mexico",
        "brasil",
        "chile",
        "colombia",
        "peru",
        "argentina",
        "uruguai",
        "paraguai",
    }

    asia = {
        "arabia saudita",
        "emirados arabes unidos",
        "qatar",
        "oma",
        "jordania",
        "israel",
        "turquia",
        "india",
        "paquistao",
        "bangladesh",
        "sri lanka",
        "china",
        "japao",
        "coreia do sul",
        "indonesia",
        "malasia",
        "tailandia",
        "vietname",
        "afeganistao",
    }

    oceania = {
        "australia",
        "nova zelandia",
    }

    if n in europe:
        return "Europa"

    if n in africa:
        return "África"

    if n in america:
        return "América"

    if n in asia:
        return "Ásia"

    if n in oceania:
        return "Oceânia"

    return "Global"


# ============================================================
# CPV
# ============================================================

def normalize_cpvs(value):

    result = []

    if value is None:
        return result

    if isinstance(value, str):

        values = re.findall(
            r"\d{8}",
            value
        )

    elif isinstance(value, list):

        values = []

        for item in value:

            values.extend(
                re.findall(
                    r"\d{8}",
                    choose_multilingual_text(
                        item
                    )
                )
            )

    elif isinstance(value, dict):

        values = []

        for item in value.values():

            values.extend(
                re.findall(
                    r"\d{8}",
                    choose_multilingual_text(
                        item
                    )
                )
            )

    else:

        values = re.findall(
            r"\d{8}",
            str(value)
        )

    for cpv in values:

        if cpv not in result:
            result.append(cpv)

    return result


# ============================================================
# TERMOS NORMALIZADOS
# ============================================================

DIRECT_TERMS_NORMALIZED = [
    normalize_text(x)
    for x in DIRECT_TERMS
]

HERITAGE_TERMS_NORMALIZED = [
    normalize_text(x)
    for x in HERITAGE_TERMS
]

MAJOR_TERMS_NORMALIZED = [
    normalize_text(x)
    for x in MAJOR_PROJECT_TERMS
]

SUPPORT_EXCLUSIONS_NORMALIZED = [
    normalize_text(x)
    for x in ARCHAEOLOGY_SUPPORT_EXCLUSIONS
]


def contains_any(text, terms):

    text = normalize_text(
        text
    )

    for term in terms:

        if term and term in text:
            return True

    return False


# ============================================================
# MODO DA PESQUISA
# ============================================================

def get_search_mode(query):

    q = normalize_text(
        query
    )

    if not q:
        return "direct"

    direct = set(
        DIRECT_TERMS_NORMALIZED
    )

    heritage = set(
        HERITAGE_TERMS_NORMALIZED
    )

    if q in direct:
        return "direct"

    if q in heritage:
        return "heritage"

    return "specific"


# ============================================================
# CLASSIFICAÇÃO
# ============================================================

def classify_result(
    title,
    description,
    cpvs,
    mode="specific"
):

    title_n = normalize_text(
        title
    )

    description_n = normalize_text(
        description
    )

    combined = (
        f"{title_n} {description_n}"
    ).strip()

    cpvs = set(
        normalize_cpvs(
            cpvs
        )
    )

    direct_text = contains_any(
        combined,
        DIRECT_TERMS_NORMALIZED
    )

    heritage_text = contains_any(
        combined,
        HERITAGE_TERMS_NORMALIZED
    )

    major = contains_any(
        combined,
        MAJOR_TERMS_NORMALIZED
    )

    support_exclusion = contains_any(
        combined,
        SUPPORT_EXCLUSIONS_NORMALIZED
    )

    cpv_direct = bool(
        cpvs.intersection(
            ARCHAEOLOGY_CPVS
        )
    )

    if mode == "direct":

        if not direct_text:
            return (
                "Outro",
                0
            )

        strong_archaeology = any(
            phrase in combined
            for phrase in [
                "archaeological excavation",
                "archaeological excavations",
                "archaeological monitoring",
                "archaeological survey",
                "archaeological investigation",
                "archaeological investigations",
                "archaeological services",
                "archaeological assessment",
                "archaeological fieldwork",
                "archaeological watching brief",
                "archaeological supervision",
                "archaeological coordinator",
                "archaeological consultancy",
                "archaeological consultant",
                "archaeological work",
                "archaeological works",
                "fouilles archeologiques",
                "escavacao arqueologica",
                "acompanhamento arqueologico",
                "monitorizacao arqueologica",
                "prospeccao arqueologica",
                "avaliacao arqueologica",
                "trabalhos arqueologicos",
                "servicos arqueologicos",
                "consultoria arqueologica",
                "consultor arqueologico",
                "arqueologo coordenador",
            ]
        )

        direct_professional = any(
            phrase in combined
            for phrase in [
                "archaeologist",
                "archaeologists",
                "archaeologue",
                "archeologue",
                "arqueologo",
                "arqueologa",
            ]
        )

        if (
            support_exclusion
            and not (
                strong_archaeology
                or direct_professional
            )
        ):
            return (
                "Outro",
                0
            )

        score = 100

        if cpv_direct:
            score += 10

        if major:
            score += 5

        return (
            "Arqueologia direta",
            min(score, 100)
        )

    if mode == "heritage":

        if direct_text:

            score = 100

            if cpv_direct:
                score += 10

            return (
                "Arqueologia direta",
                min(score, 100)
            )

        if heritage_text:

            score = 70

            if major:
                score += 10

            return (
                "Património / potencial arqueológico",
                min(score, 95)
            )

        return (
            "Outro",
            0
        )

    if mode == "specific":

        if direct_text:

            if (
                support_exclusion
                and not any(
                    phrase in combined
                    for phrase in [
                        "archaeological excavation",
                        "archaeological monitoring",
                        "archaeological survey",
                        "archaeological investigation",
                        "archaeological services",
                        "archaeological assessment",
                        "archaeological fieldwork",
                        "archaeological watching brief",
                        "archaeological supervision",
                        "archaeological coordinator",
                        "archaeological consultancy",
                        "archaeological consultant",
                        "archaeological work",
                        "archaeological works",
                        "archaeologist",
                        "archaeologists",
                        "arqueologo",
                        "arqueologa",
                        "arqueologia",
                        "trabalhos arqueologicos",
                        "servicos arqueologicos",
                    ]
                )
            ):
                return (
                    "Outro",
                    0
                )

            score = 100

            if cpv_direct:
                score += 10

            if major:
                score += 5

            return (
                "Arqueologia direta",
                min(score, 100)
            )

        if heritage_text:

            return (
                "Património / potencial arqueológico",
                70
            )

    return (
        "Outro",
        0
    )


# ============================================================
# RESULTADOS
# ============================================================

def normalize_result(result):

    if not isinstance(
        result,
        dict
    ):
        return None

    title = clean_text(
        result.get(
            "title",
            ""
        )
    )

    description = clean_text(
        result.get(
            "description",
            ""
        )
    )

    buyer = clean_text(
        result.get(
            "buyer",
            ""
        )
    )

    country = clean_text(
        result.get(
            "country",
            ""
        )
    )

    source = clean_text(
        result.get(
            "source",
            ""
        )
    )

    url = clean_text(
        result.get(
            "url",
            ""
        )
    )

    cpv = normalize_cpvs(
        result.get(
            "cpv",
            []
        )
    )

    category = clean_text(
        result.get(
            "category",
            ""
        )
    )

    score = result.get(
        "score",
        0
    )

    try:
        score = int(score)

    except Exception:
        score = 0

    return {
        "title": title,
        "buyer": buyer,
        "country": country,
        "date": date_string(
            result.get("date")
        ),
        "deadline": date_string(
            result.get("deadline")
        ),
        "cpv": cpv,
        "category": category,
        "score": score,
        "source": source,
        "url": url,
        "description": description,
    }


def recent_enough(result):

    d = parse_date(
        result.get(
            "date"
        )
    )

    # --------------------------------------------------------
    # CORREÇÃO 2.4:
    # Quando a fonte não fornece data de publicação,
    # utilizamos a deadline apenas para determinar se o
    # registo é antigo.
    #
    # A deadline NÃO é apresentada como data de publicação.
    # --------------------------------------------------------

    if not d:

        d = parse_date(
            result.get(
                "deadline"
            )
        )

    if not d:
        return True

    return d >= cutoff_date()


def dedupe_results(results):

    unique = {}

    for item in results:

        normalized = normalize_result(
            item
        )

        if not normalized:
            continue

        if not normalized["title"]:
            continue

        if not recent_enough(
            normalized
        ):
            continue

        key = (
            normalize_text(
                normalized["title"]
            ),
            normalize_text(
                normalized["buyer"]
            ),
            normalized["date"],
            normalized["country"],
        )

        if key in unique:

            if (
                normalized["score"]
                > unique[key]["score"]
            ):
                unique[key] = normalized

        else:
            unique[key] = normalized

    output = list(
        unique.values()
    )

    output.sort(
        key=lambda x: (
            -int(
                x.get(
                    "score",
                    0
                )
            ),
            x.get(
                "date",
                ""
            ),
        )
    )

    return output


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
    "deadline-date-lot",
    "deadline-receipt-tender-date-lot",
    "deadline-receipt-request-date-lot",
    "description-proc",
    "description-lot",
    "place-of-performance",
    "official-language",
]


def clean_ted_title(value):

    title = choose_multilingual_text(
        value
    )

    title = clean_text(
        title
    )

    title = re.sub(
        r"^\s*(?:[A-Za-z]{2,3})\s*[-:]\s*",
        "",
        title
    )

    return title.strip()


def ted_notice_to_result(
    notice,
    search_mode="direct"
):

    title = clean_ted_title(
        notice.get(
            "notice-title"
        )
        or notice.get(
            "title"
        )
        or ""
    )

    description = clean_text(
        notice.get(
            "description-proc"
        )
        or notice.get(
            "description-lot"
        )
        or notice.get(
            "description"
        )
        or ""
    )

    buyer = clean_text(
        notice.get(
            "buyer-name"
        )
        or notice.get(
            "buyer"
        )
        or ""
    )

    country = extract_country(
        notice
    )

    cpvs = normalize_cpvs(
        notice.get(
            "classification-cpv"
        )
        or notice.get(
            "cpv"
        )
        or []
    )

    pub_date = (
        notice.get(
            "publication-date"
        )
        or notice.get(
            "publicationDate"
        )
        or notice.get(
            "date"
        )
        or ""
    )

    deadline = (
        notice.get(
            "deadline-date-lot"
        )
        or notice.get(
            "deadline-receipt-tender-date-lot"
        )
        or notice.get(
            "deadline-receipt-request-date-lot"
        )
        or notice.get(
            "deadline"
        )
        or ""
    )

    category, score = classify_result(
        title,
        description,
        cpvs,
        mode=search_mode
    )

    publication_number = clean_text(
        notice.get(
            "publication-number"
        )
        or notice.get(
            "publicationNumber"
        )
        or ""
    )

    url = ""

    if publication_number:

        url = (
            "https://ted.europa.eu/en/notice/-/detail/"
            + publication_number
        )

    if not url:

        url = choose_multilingual_text(
            notice.get(
                "url"
            )
            or notice.get(
                "links"
            )
            or ""
        )

    return {
        "title": title,
        "buyer": buyer,
        "country": country,
        "date": date_string(
            pub_date
        ),
        "deadline": date_string(
            deadline
        ),
        "cpv": cpvs,
        "category": category,
        "score": score,
        "source": TED_SOURCE,
        "url": url,
        "description": description,
    }


def query_ted(
    term,
    diagnostics,
    search_mode="direct"
):

    payload = {
        "query": f'FT~"{term}"',
        "pageSize": PAGE_SIZE,
        "scope": "ACTIVE",
        "fields": TED_FIELDS,
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

        response.raise_for_status()

        data = response.json()

        notices = data.get(
            "notices",
            []
        )

        results = []

        for notice in notices:

            item = ted_notice_to_result(
                notice,
                search_mode
            )

            if (
                not item
                or item["category"] == "Outro"
            ):
                continue

            if not recent_enough(
                item
            ):
                continue

            results.append(
                item
            )

        diagnostics.append({
            "source": "TED",
            "term": term,
            "ok": True,
            "count": len(results),
            "raw_count": len(notices),
            "error": "",
        })

        return results

    except Exception as exc:

        diagnostics.append({
            "source": "TED",
            "term": term,
            "ok": False,
            "count": 0,
            "raw_count": 0,
            "error": str(exc),
        })

        return []


# ============================================================
# WORLD BANK
# ============================================================

def first_value(row, keys):

    for key in keys:

        value = row.get(
            key
        )

        if value not in (
            None,
            "",
            [],
            {},
        ):
            return value

    return ""


def query_world_bank(
    term,
    diagnostics,
    search_mode="direct"
):

    try:

        params = {
            "qterm": term,
            "rows": 100,
            "format": "json",
        }

        response = requests.get(
            WORLD_BANK_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
            headers={
                "Accept": "application/json",
            },
        )

        response.raise_for_status()

        data = response.json()

        rows = []

        if isinstance(
            data,
            dict
        ):

            for key in (
                "procnotices",
                "notices",
                "results",
                "documents",
            ):

                value = data.get(
                    key
                )

                if isinstance(
                    value,
                    list
                ):

                    rows = value
                    break

                if isinstance(
                    value,
                    dict
                ):

                    rows = list(
                        value.values()
                    )
                    break

        results = []

        for row in rows:

            if not isinstance(
                row,
                dict
            ):
                continue

            title = clean_text(
                first_value(
                    row,
                    [
                        "bid_description",
                        "procurement_name",
                        "notice_title",
                        "title",
                        "project_name",
                    ]
                )
            )

            description = clean_text(
                first_value(
                    row,
                    [
                        "description",
                        "bid_description",
                        "procurement_description",
                        "notice_description",
                    ]
                )
            )

            buyer = clean_text(
                first_value(
                    row,
                    [
                        "borrower",
                        "buyer",
                        "agency",
                        "procuring_entity",
                        "client",
                        "project_name",
                    ]
                )
            )

            # ------------------------------------------------
            # PAÍS
            # ------------------------------------------------

            country_value = first_value(
                row,
                [
                    "country",
                    "countryname",
                    "country_name",
                    "countryCode",
                    "country_code",
                    "countrycode",
                    "country_iso",
                    "country_iso3",
                    "iso_country",
                    "iso3",
                    "iso3_code",
                ]
            )

            if not country_value:

                country_value = first_value_recursive(
                    row,
                    exact_keys=[
                        "country",
                        "countryname",
                        "country_name",
                        "countryCode",
                        "country_code",
                        "countrycode",
                        "country_iso",
                        "country_iso3",
                        "iso_country",
                        "iso3",
                        "iso3_code",
                    ],
                    key_fragments=[
                        "country",
                        "borrower_country",
                    ]
                )

            country = clean_text(
                country_value
            )

            if country:

                country = country_from_code(
                    country
                )

            # ------------------------------------------------
            # FALLBACK DO PAÍS
            # ------------------------------------------------

            if not country:

                country = country_from_text(
                    buyer,
                    title,
                    description,
                    clean_text(
                        first_value(
                            row,
                            [
                                "project_name",
                                "project",
                                "project_title",
                                "borrower",
                            ]
                        )
                    )
                )

            # ------------------------------------------------
            # CPV
            # ------------------------------------------------

            cpvs = normalize_cpvs(
                first_value(
                    row,
                    [
                        "cpv",
                        "classification-cpv",
                        "classification",
                    ]
                )
            )

            # ------------------------------------------------
            # DATA DE PUBLICAÇÃO
            # ------------------------------------------------

            pub_date = first_value(
                row,
                [
                    "publication_date",
                    "publicationDate",
                    "publicationdate",
                    "notice_date",
                    "noticeDate",
                    "procurement_notice_date",
                    "bid_publication_date",
                    "date",
                    "published_date",
                    "publishedDate",
                    "posting_date",
                    "posted_date",
                    "created_date",
                    "createdDate",
                ]
            )

            if not pub_date:

                pub_date = first_value_recursive(
                    row,
                    exact_keys=[
                        "publication_date",
                        "publicationDate",
                        "publicationdate",
                        "notice_date",
                        "noticeDate",
                        "procurement_notice_date",
                        "bid_publication_date",
                        "published_date",
                        "publishedDate",
                        "posting_date",
                        "posted_date",
                    ],
                    key_fragments=[
                        "publication",
                        "published",
                        "posting",
                        "posted",
                    ]
                )

            # ------------------------------------------------
            # PRAZO
            # ------------------------------------------------

            deadline = first_value(
                row,
                [
                    "submission_deadline",
                    "submissionDeadline",
                    "deadline",
                    "deadline_date",
                    "bid_submission_deadline",
                    "closing_date",
                    "closingDate",
                    "submission_date",
                    "procurement_deadline",
                    "bid_deadline",
                ]
            )

            if not deadline:

                deadline = first_value_recursive(
                    row,
                    exact_keys=[
                        "submission_deadline",
                        "submissionDeadline",
                        "deadline",
                        "deadline_date",
                        "bid_submission_deadline",
                        "closing_date",
                        "closingDate",
                        "submission_date",
                        "procurement_deadline",
                        "bid_deadline",
                    ],
                    key_fragments=[
                        "deadline",
                        "closing",
                        "submission",
                    ]
                )

            category, score = classify_result(
                title,
                description,
                cpvs,
                mode=search_mode
            )

            if category == "Outro":
                continue

            # ------------------------------------------------
            # URL
            # ------------------------------------------------

            url_value = first_value(
                row,
                [
                    "url",
                    "notice_url",
                    "web_url",
                    "procurement_url",
                    "link",
                ]
            )

            if not url_value:

                url_value = first_value_recursive(
                    row,
                    exact_keys=[
                        "url",
                        "notice_url",
                        "web_url",
                        "procurement_url",
                        "link",
                    ],
                    key_fragments=[
                        "url",
                    ]
                )

            item = {
                "title": title,
                "buyer": buyer,
                "country": country,
                "date": date_string(
                    pub_date
                ),
                "deadline": date_string(
                    deadline
                ),
                "cpv": cpvs,
                "category": category,
                "score": score,
                "source": "World Bank Procurement",
                "url": clean_text(
                    url_value
                ),
                "description": description,
            }

            # ------------------------------------------------
            # FILTRO TEMPORAL
            #
            # Se a data de publicação estiver vazia mas a
            # deadline for antiga, recent_enough() elimina
            # correctamente o resultado.
            # ------------------------------------------------

            if recent_enough(
                item
            ):
                results.append(
                    item
                )

        diagnostics.append({
            "source": "World Bank Procurement",
            "term": term,
            "ok": True,
            "count": len(results),
            "raw_count": len(rows),
            "error": "",
        })

        return results

    except Exception as exc:

        diagnostics.append({
            "source": "World Bank Procurement",
            "term": term,
            "ok": False,
            "count": 0,
            "raw_count": 0,
            "error": str(exc),
        })

        return []


# ============================================================
# SOUTH AFRICA
# ============================================================

def query_south_africa(
    term,
    diagnostics,
    search_mode="direct"
):

    try:

        response = requests.get(
            SOUTH_AFRICA_URL,
            params={
                "page": 1,
                "pageSize": 100,
            },
            timeout=10,
            headers={
                "Accept": "application/json",
            },
        )

        response.raise_for_status()

        data = response.json()

        releases = []

        if isinstance(
            data,
            dict
        ):

            if isinstance(
                data.get("releases"),
                list
            ):
                releases = data[
                    "releases"
                ]

            elif isinstance(
                data.get("results"),
                list
            ):
                releases = data[
                    "results"
                ]

            elif isinstance(
                data.get("data"),
                list
            ):
                releases = data[
                    "data"
                ]

        elif isinstance(
            data,
            list
        ):

            releases = data

        results = []

        term_n = normalize_text(
            term
        )

        for release in releases:

            if not isinstance(
                release,
                dict
            ):
                continue

            tender = release.get(
                "tender",
                {}
            )

            if not isinstance(
                tender,
                dict
            ):
                tender = {}

            title = clean_text(
                tender.get("title")
                or release.get("title")
                or ""
            )

            description = clean_text(
                tender.get("description")
                or release.get("description")
                or ""
            )

            text = normalize_text(
                f"{title} {description}"
            )

            if (
                term_n
                and term_n not in text
            ):
                continue

            classification = tender.get(
                "classification",
                {}
            )

            cpvs = normalize_cpvs(
                classification.get("id")
                if isinstance(
                    classification,
                    dict
                )
                else classification
            )

            buyer = release.get(
                "buyer",
                {}
            )

            if isinstance(
                buyer,
                dict
            ):

                buyer_name = clean_text(
                    buyer.get(
                        "name",
                        ""
                    )
                )

            else:

                buyer_name = clean_text(
                    buyer
                )

            date_value = (
                release.get("date")
                or tender.get("date")
                or release.get(
                    "publishedDate"
                )
                or ""
            )

            deadline = tender.get(
                "tenderPeriod",
                {}
            )

            if not isinstance(
                deadline,
                dict
            ):
                deadline = {}

            deadline_value = deadline.get(
                "end",
                ""
            )

            category, score = classify_result(
                title,
                description,
                cpvs,
                mode=search_mode
            )

            if category == "Outro":
                continue

            item = {
                "title": title,
                "buyer": buyer_name,
                "country": "África do Sul",
                "date": date_string(
                    date_value
                ),
                "deadline": date_string(
                    deadline_value
                ),
                "cpv": cpvs,
                "category": category,
                "score": score,
                "source": SOUTH_AFRICA_SOURCE,
                "url": clean_text(
                    release.get("url")
                    or release.get("id")
                    or ""
                ),
                "description": description,
            }

            if recent_enough(
                item
            ):
                results.append(
                    item
                )

        diagnostics.append({
            "source": SOUTH_AFRICA_SOURCE,
            "term": term,
            "ok": True,
            "count": len(results),
            "raw_count": len(releases),
            "error": "",
        })

        return results

    except Exception as exc:

        diagnostics.append({
            "source": SOUTH_AFRICA_SOURCE,
            "term": term,
            "ok": False,
            "count": 0,
            "raw_count": 0,
            "error": str(exc),
        })

        return []


# ============================================================
# SECOP II - COLÔMBIA
# ============================================================

def query_secop(
    term,
    diagnostics,
    search_mode="direct"
):

    try:

        params = {
            "$limit": 1000,
            "$q": term,
        }

        response = requests.get(
            SECOP_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
            headers={
                "Accept": "application/json",
            },
        )

        response.raise_for_status()

        data = response.json()

        if not isinstance(
            data,
            list
        ):
            data = []

        results = []

        term_n = normalize_text(
            term
        )

        for row in data:

            if not isinstance(
                row,
                dict
            ):
                continue

            title = clean_text(
                row.get(
                    "nombre_del_procedimiento"
                )
                or row.get(
                    "objeto_del_contrato"
                )
                or row.get(
                    "descripcion_del_proceso"
                )
                or row.get("title")
                or ""
            )

            description = clean_text(
                row.get(
                    "descripcion_del_proceso"
                )
                or row.get(
                    "objeto_del_contrato"
                )
                or ""
            )

            combined = normalize_text(
                f"{title} {description}"
            )

            if (
                term_n
                and term_n not in combined
            ):
                continue

            buyer = clean_text(
                row.get(
                    "entidad"
                )
                or row.get(
                    "nombre_entidad"
                )
                or ""
            )

            cpvs = normalize_cpvs(
                row.get(
                    "codigo_principal_de_producto"
                )
                or row.get(
                    "codigo_unspsc"
                )
                or ""
            )

            date_value = (
                row.get(
                    "fecha_de_publicacion"
                )
                or row.get(
                    "fecha_publicacion"
                )
                or row.get(
                    "fecha_de_publicacion_del_proceso"
                )
                or ""
            )

            deadline = (
                row.get(
                    "fecha_de_recepcion_de_ofertas"
                )
                or row.get(
                    "fecha_de_cierre"
                )
                or ""
            )

            category, score = classify_result(
                title,
                description,
                cpvs,
                mode=search_mode
            )

            if category == "Outro":
                continue

            item = {
                "title": title,
                "buyer": buyer,
                "country": "Col\u00f4mbia",
                "date": date_string(
                    date_value
                ),
                "deadline": date_string(
                    deadline
                ),
                "cpv": cpvs,
                "category": category,
                "score": score,
                "source": SECOP_SOURCE,
                "url": clean_text(
                    row.get("url")
                    or row.get("link")
                    or ""
                ),
                "description": description,
            }

            if recent_enough(
                item
            ):
                results.append(
                    item
                )

        diagnostics.append({
            "source": SECOP_SOURCE,
            "term": term,
            "ok": True,
            "count": len(results),
            "raw_count": len(data),
            "error": "",
        })

        return results

    except Exception as exc:

        diagnostics.append({
            "source": SECOP_SOURCE,
            "term": term,
            "ok": False,
            "count": 0,
            "raw_count": 0,
            "error": str(exc),
        })

        return []


# ============================================================
# TERMOS AUTOMÁTICOS
# ============================================================

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
    "archaeological watching brief",

    "arch\u00e9ologie",
    "arch\u00e9ologique",
    "fouilles arch\u00e9ologiques",

    "arqueologia",
    "arqueol\u00f3gico",
    "arqueol\u00f3gica",
    "escava\u00e7\u00e3o arqueol\u00f3gica",
    "acompanhamento arqueol\u00f3gico",

    "arch\u00e4ologie",
    "arch\u00e4ologisch",
]

AUTOMATIC_TERMS_WORLD_BANK = [
    "archaeology",
    "archaeological",
    "archaeologist",
    "archaeological excavation",
    "archaeological monitoring",
    "archaeological survey",
    "archaeological assessment",
    "archaeological coordinator",
    "archaeological consultancy",
]

AUTOMATIC_TERMS_SECOP = [
    "arqueologia",
    "arqueol\u00f3gico",
    "arqueol\u00f3gica",
    "arque\u00f3logo",
    "arque\u00f3loga",
    "escava\u00e7\u00e3o arqueol\u00f3gica",
    "acompanhamento arqueol\u00f3gico",
    "prospe\u00e7\u00e3o arqueol\u00f3gica",
    "prospec\u00e7\u00e3o arqueol\u00f3gica",
    "archaeology",
    "archaeological",
    "archaeologist",
]


def is_global_archaeology_query(
    query
):

    mode = get_search_mode(
        query
    )

    return mode in {
        "direct",
        "heritage",
    }


# ============================================================
# PESQUISA AUTOMÁTICA GLOBAL
# ============================================================

def automatic_search(
    query,
    diagnostics
):

    search_mode = get_search_mode(
        query
    )

    if search_mode == "direct":

        ted_terms = (
            AUTOMATIC_TERMS_TED
        )

        world_bank_terms = (
            AUTOMATIC_TERMS_WORLD_BANK
        )

        secop_terms = (
            AUTOMATIC_TERMS_SECOP
        )

    elif search_mode == "heritage":

        ted_terms = [
            query
        ]

        world_bank_terms = [
            query
        ]

        secop_terms = [
            query
        ]

    else:

        ted_terms = [
            query
        ]

        world_bank_terms = [
            query
        ]

        secop_terms = [
            query
        ]

    jobs = []

    for term in ted_terms:

        jobs.append(
            (
                "TED",
                term,
                search_mode
            )
        )

    for term in world_bank_terms:

        jobs.append(
            (
                "WORLD_BANK",
                term,
                search_mode
            )
        )

    for term in secop_terms:

        jobs.append(
            (
                "SECOP",
                term,
                search_mode
            )
        )

    results = []

    def run_job(job):

        source, term, mode = job

        if source == "TED":

            return query_ted(
                term,
                diagnostics,
                mode
            )

        if source == "WORLD_BANK":

            return query_world_bank(
                term,
                diagnostics,
                mode
            )

        if source == "SECOP":

            return query_secop(
                term,
                diagnostics,
                mode
            )

        return []

    with ThreadPoolExecutor(
        max_workers=8
    ) as executor:

        futures = [
            executor.submit(
                run_job,
                job
            )
            for job in jobs
        ]

        for future in as_completed(
            futures
        ):

            try:

                value = future.result()

                if value:
                    results.extend(
                        value
                    )

            except Exception:
                pass

    return results


# ============================================================
# FILTROS
# ============================================================

def apply_filters(
    results,
    region="",
    category=""
):

    filtered = []

    region_n = normalize_text(
        region
    )

    category_n = normalize_text(
        category
    )

    for item in results:

        item_region = normalize_text(
            region_from_country(
                item.get(
                    "country",
                    ""
                )
            )
        )

        item_category = normalize_text(
            item.get(
                "category",
                ""
            )
        )

        if region_n:

            if item_region != region_n:
                continue

        if category_n:

            if category_n not in item_category:
                continue

        filtered.append(
            item
        )

    return filtered


# ============================================================
# ESTATÍSTICAS
# ============================================================

def build_regions(results):

    regions = {}

    for item in results:

        region = region_from_country(
            item.get(
                "country",
                ""
            )
        )

        regions[region] = (
            regions.get(
                region,
                0
            ) + 1
        )

    return dict(
        sorted(
            regions.items(),
            key=lambda x: (
                -x[1],
                x[0]
            )
        )
    )


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    automatic_sources = [
        clean_text(
            source["name"]
        )
        for source in SOURCES
        if source.get(
            "automatic"
        )
    ]

    return {
        "ok": True,
        "app": "Arqueologia Radar",
        "version": "2.4",
        "period_days": PERIOD_DAYS,
        "sources": len(
            SOURCES
        ),
        "automatic_sources": len(
            automatic_sources
        ),
        "automatic_source_names": (
            automatic_sources
        ),
        "date": date.today().isoformat(),
    }


# ============================================================
# TESTE TED - PAÍS
# ============================================================

@app.get(
    "/api/test-ted-country"
)
def test_ted_country(
    country: str = Query(
        "MAR",
        description="Código de país TED"
    ),
    term: str = Query(
        "archaeology"
    ),
):

    query = (
        f'FT~"{term}" '
        f'AND buyer-country='
        f'{country.upper()}'
    )

    payload = {
        "query": query,
        "pageSize": 10,
        "scope": "ACTIVE",
        "fields": TED_FIELDS,
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

        return {
            "ok": True,
            "status_code": (
                response.status_code
            ),
            "query": query,
            "response": response.json(),
        }

    except Exception as exc:

        return {
            "ok": False,
            "query": query,
            "error": str(exc),
        }


# ============================================================
# TESTE TED MÍNIMO
# ============================================================

@app.get(
    "/api/test-ted-minimal"
)
def test_ted_minimal(
    term: str = Query(
        "archaeology"
    )
):

    payload = {
        "query": f'FT~"{term}"',
        "pageSize": 10,
        "scope": "ACTIVE",
        "fields": [
            "publication-number",
            "publication-date",
            "notice-title",
            "buyer-name",
            "buyer-country",
        ],
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

        return {
            "ok": True,
            "status_code": (
                response.status_code
            ),
            "query": payload["query"],
            "response": response.json(),
        }

    except Exception as exc:

        return {
            "ok": False,
            "query": payload["query"],
            "error": str(exc),
        }


# ============================================================
# PESQUISA PRINCIPAL
# ============================================================

@app.get(
    "/api/search"
)
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
    ),
):

    started = datetime.now()

    query = clean_text(
        q
    )

    diagnostics = []

    search_mode = get_search_mode(
        query
    )

    automatic_mode = (
        search_mode
        in {
            "direct",
            "heritage",
        }
    )

    results = automatic_search(
        query,
        diagnostics
    )

    normalized_results = []

    for item in results:

        normalized = normalize_result(
            item
        )

        if not normalized:
            continue

        if (
            normalized.get(
                "category"
            )
            == "Outro"
        ):
            continue

        if not recent_enough(
            normalized
        ):
            continue

        normalized_results.append(
            normalized
        )

    normalized_results = dedupe_results(
        normalized_results
    )

    normalized_results = apply_filters(
        normalized_results,
        region=region,
        category=category,
    )

    regions = build_regions(
        normalized_results
    )

    elapsed = (
        datetime.now()
        - started
    ).total_seconds()

    automatic_source_names = [
        clean_text(
            source["name"]
        )
        for source in SOURCES
        if source.get(
            "automatic"
        )
    ]

    portal_count = len([
        source
        for source in SOURCES
        if not source.get(
            "automatic"
        )
    ])

    return {
        "ok": True,
        "query": query,
        "search_mode": search_mode,
        "automatic_mode": automatic_mode,
        "region": region,
        "category": category,
        "results": normalized_results,
        "count": len(
            normalized_results
        ),
        "sources": len(
            SOURCES
        ),
        "automatic_sources": len(
            automatic_source_names
        ),
        "automatic_source_names": (
            automatic_source_names
        ),
        "portal_count": portal_count,
        "regions": regions,
        "diagnostics": diagnostics,
        "searched_at": (
            date.today().isoformat()
        ),
        "period_days": PERIOD_DAYS,
        "cutoff_date": (
            cutoff_date().isoformat()
        ),
        "elapsed_seconds": round(
            elapsed,
            2
        ),
    }


# ============================================================
# FRONTEND
# ============================================================

@app.get("/")
def index():

    file_path = (
        BASE_DIR
        / "index.html"
    )

    if file_path.exists():

        return FileResponse(
            file_path,
            media_type="text/html"
        )

    return JSONResponse({
        "ok": True,
        "message": (
            "Arqueologia Radar online."
        )
    })


@app.get("/app.js")
def app_js():

    file_path = (
        BASE_DIR
        / "app.js"
    )

    if file_path.exists():

        return FileResponse(
            file_path,
            media_type="application/javascript"
        )

    return JSONResponse({
        "ok": False,
        "error": "app.js n\u00e3o encontrado."
    })


@app.get("/manifest.json")
def manifest():

    file_path = (
        BASE_DIR
        / "manifest.json"
    )

    if file_path.exists():

        return FileResponse(
            file_path,
            media_type="application/manifest+json"
        )

    return JSONResponse({
        "name": "Arqueologia Radar"
    })
