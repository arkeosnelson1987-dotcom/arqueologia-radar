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
# Versão 2.1 - pesquisa global consolidada
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Arqueologia Radar",
    version="2.1"
)

REQUEST_TIMEOUT = 30
PERIOD_DAYS = 365
PAGE_SIZE = 100

TED_URL = "https://api.ted.europa.eu/v3/notices/search"
WORLD_BANK_URL = "https://search.worldbank.org/api/v2/procnotices"

SOUTH_AFRICA_URL = (
    "https://ocds-api.etenders.gov.za/api/OCDSReleases"
)

SECOP_URL = (
    "https://www.datos.gov.co/resource/p6dx-8zbt.json"
)

# ============================================================
# FONTES
# ============================================================

SOURCES = [
    {
        "name": "TED — Europa",
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
        "name": "South Africa eTenders — OCDS",
        "region": "África",
        "country": "África do Sul",
        "url": "https://www.etenders.gov.za/",
        "type": "api",
        "automatic": True,
    },
    {
        "name": "SECOP II — Colômbia",
        "region": "América",
        "country": "Colômbia",
        "url": "https://www.colombiacompra.gov.co/",
        "type": "api",
        "automatic": True,
    },

    # --------------------------------------------------------
    # PORTAIS / FONTES DE REFERÊNCIA
    # --------------------------------------------------------

    {
        "name": "AfDB — African Development Bank",
        "region": "África",
        "country": "",
        "url": "https://www.afdb.org/en/projects-and-operations/procurement",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "SAM.gov — Estados Unidos",
        "region": "América",
        "country": "EUA",
        "url": "https://sam.gov/content/opportunities",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "BASE — Portugal",
        "region": "Europa",
        "country": "Portugal",
        "url": "https://www.base.gov.pt/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "Contratación del Estado — Espanha",
        "region": "Europa",
        "country": "Espanha",
        "url": "https://contrataciondelestado.es/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "UNDB — United Nations Development Business",
        "region": "Global",
        "country": "",
        "url": "https://devbusiness.un.org/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "UNGM — United Nations Global Marketplace",
        "region": "Global",
        "country": "",
        "url": "https://www.ungm.org/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "EBRD — European Bank for Reconstruction and Development",
        "region": "Europa / Ásia",
        "country": "",
        "url": "https://www.ebrd.com/work-with-us/procurement.html",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "EIB — European Investment Bank",
        "region": "Europa",
        "country": "",
        "url": "https://www.eib.org/en/projects/procurement/index.htm",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "Oman — Tender Board",
        "region": "Ásia",
        "country": "Omã",
        "url": "https://etendering.tenderboard.gov.om/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "Etimad — Arábia Saudita",
        "region": "Ásia",
        "country": "Arábia Saudita",
        "url": "https://tenders.etimad.sa/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "UAE — Federal Procurement",
        "region": "Ásia",
        "country": "Emirados Árabes Unidos",
        "url": "https://mof.gov.ae/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "Qatar — Government Procurement",
        "region": "Ásia",
        "country": "Qatar",
        "url": "https://monaqasat.mof.gov.qa/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "Maroc — Marchés Publics",
        "region": "África",
        "country": "Marrocos",
        "url": "https://www.marchespublics.gov.ma/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "Uganda — eGP",
        "region": "África",
        "country": "Uganda",
        "url": "https://egpuganda.go.ug/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "Kenya — Public Procurement",
        "region": "África",
        "country": "Quénia",
        "url": "https://www.treasury.go.ke/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "Tanzania — PPRA",
        "region": "África",
        "country": "Tanzânia",
        "url": "https://www.ppra.go.tz/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "Moçambique — Contratação Pública",
        "region": "África",
        "country": "Moçambique",
        "url": "https://www.ufsa.gov.mz/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "ChileCompra",
        "region": "América",
        "country": "Chile",
        "url": "https://www.mercadopublico.cl/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "Brasil — Compras.gov.br",
        "region": "América",
        "country": "Brasil",
        "url": "https://www.gov.br/compras/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "IDB — Inter-American Development Bank",
        "region": "América",
        "country": "",
        "url": "https://www.iadb.org/en/how-we-work/working-us/procurement",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "ADB — Asian Development Bank",
        "region": "Ásia",
        "country": "",
        "url": "https://www.adb.org/work-with-us/procurement",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "AusTender — Austrália",
        "region": "Ásia / Oceânia",
        "country": "Austrália",
        "url": "https://www.tenders.gov.au/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "NZ GETS — Nova Zelândia",
        "region": "Ásia / Oceânia",
        "country": "Nova Zelândia",
        "url": "https://www.gets.govt.nz/",
        "type": "portal",
        "automatic": False,
    },
    {
        "name": "Red Eléctrica / Redeia",
        "region": "Europa",
        "country": "Espanha",
        "url": "https://www.ree.es/",
        "type": "portal",
        "automatic": False,
    },
]

# ============================================================
# TERMOS
# ============================================================

DEFAULT_TERMS = [
    "archaeology",
    "archaeological",
    "archaeologist",
    "archaeological excavation",
    "archaeological monitoring",
    "archaeological survey",
    "archaeological investigation",
    "archaeological services",
    "cultural heritage",
    "heritage assessment",
    "heritage impact assessment",
    "historic environment",
    "chance finds",
    "archéologie",
    "archéologique",
    "fouilles archéologiques",
    "patrimoine culturel",
    "arqueologia",
    "arqueológico",
    "arqueológica",
    "escavação arqueológica",
    "acompanhamento arqueológico",
    "património cultural",
    "patrimonio cultural",
    "archäologie",
    "archäologisch",
]

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
    "infrastructures",
    "ferroviaire",
    "route",
    "autoroute",
    "mine",
    "pipeline",
    "aéroport",
    "port",
    "barrage",
    "énergie",
    "infrastructure",
    "ferrovia",
    "rodovia",
    "aeroporto",
    "porto",
    "barragem",
    "energia",
]

ARCHAEOLOGY_CPVS = {
    "71351914",
    "71351910",
    "71351900",
    "71351720",
    "71351811",
    "71351730",
}

# 45112450 = excavation work
# Não é considerado, isoladamente, um CPV arqueológico.
GENERAL_EXCAVATION_CPV = {
    "45112450",
}

# ============================================================
# MAPAS DE PAÍSES
# ============================================================

COUNTRY_MAP = {
    "PT": "Portugal",
    "ES": "Espanha",
    "FR": "França",
    "DE": "Alemanha",
    "IT": "Itália",
    "BE": "Bélgica",
    "NL": "Países Baixos",
    "LU": "Luxemburgo",
    "IE": "Irlanda",
    "AT": "Áustria",
    "PL": "Polónia",
    "CZ": "Chéquia",
    "SK": "Eslováquia",
    "HU": "Hungria",
    "RO": "Roménia",
    "BG": "Bulgária",
    "HR": "Croácia",
    "SI": "Eslovénia",
    "SE": "Suécia",
    "FI": "Finlândia",
    "DK": "Dinamarca",
    "EE": "Estónia",
    "LV": "Letónia",
    "LT": "Lituânia",
    "GR": "Grécia",
    "CY": "Chipre",
    "MT": "Malta",
    "NO": "Noruega",
    "IS": "Islândia",
    "CH": "Suíça",
    "UK": "Reino Unido",

    "MA": "Marrocos",
    "DZ": "Argélia",
    "TN": "Tunísia",
    "EG": "Egito",
    "ZA": "África do Sul",
    "KE": "Quénia",
    "UG": "Uganda",
    "TZ": "Tanzânia",
    "MZ": "Moçambique",
    "NG": "Nigéria",
    "GH": "Gana",
    "ET": "Etiópia",

    "US": "Estados Unidos",
    "CA": "Canadá",
    "MX": "México",
    "BR": "Brasil",
    "CL": "Chile",
    "CO": "Colômbia",
    "PE": "Peru",
    "AR": "Argentina",
    "UY": "Uruguai",
    "PY": "Paraguai",

    "SA": "Arábia Saudita",
    "AE": "Emirados Árabes Unidos",
    "QA": "Qatar",
    "OM": "Omã",
    "JO": "Jordânia",
    "IL": "Israel",
    "TR": "Turquia",
    "IN": "Índia",
    "PK": "Paquistão",
    "BD": "Bangladesh",
    "LK": "Sri Lanka",
    "CN": "China",
    "JP": "Japão",
    "KR": "Coreia do Sul",
    "ID": "Indonésia",
    "MY": "Malásia",
    "TH": "Tailândia",
    "VN": "Vietname",

    "AU": "Austrália",
    "NZ": "Nova Zelândia",
}

ISO3_MAP = {
    "PRT": "Portugal",
    "ESP": "Espanha",
    "FRA": "França",
    "DEU": "Alemanha",
    "ITA": "Itália",
    "BEL": "Bélgica",
    "NLD": "Países Baixos",
    "LUX": "Luxemburgo",
    "IRL": "Irlanda",
    "AUT": "Áustria",
    "POL": "Polónia",
    "CZE": "Chéquia",
    "SVK": "Eslováquia",
    "HUN": "Hungria",
    "ROU": "Roménia",
    "BGR": "Bulgária",
    "HRV": "Croácia",
    "SVN": "Eslovénia",
    "SWE": "Suécia",
    "FIN": "Finlândia",
    "DNK": "Dinamarca",
    "EST": "Estónia",
    "LVA": "Letónia",
    "LTU": "Lituânia",
    "GRC": "Grécia",
    "CYP": "Chipre",
    "MLT": "Malta",
    "NOR": "Noruega",
    "ISL": "Islândia",
    "CHE": "Suíça",
    "GBR": "Reino Unido",

    "MAR": "Marrocos",
    "DZA": "Argélia",
    "TUN": "Tunísia",
    "EGY": "Egito",
    "ZAF": "África do Sul",
    "KEN": "Quénia",
    "UGA": "Uganda",
    "TZA": "Tanzânia",
    "MOZ": "Moçambique",
    "NGA": "Nigéria",
    "GHA": "Gana",
    "ETH": "Etiópia",

    "USA": "Estados Unidos",
    "CAN": "Canadá",
    "MEX": "México",
    "BRA": "Brasil",
    "CHL": "Chile",
    "COL": "Colômbia",
    "PER": "Peru",
    "ARG": "Argentina",
    "URY": "Uruguai",
    "PRY": "Paraguai",

    "SAU": "Arábia Saudita",
    "ARE": "Emirados Árabes Unidos",
    "QAT": "Qatar",
    "OMN": "Omã",
    "JOR": "Jordânia",
    "ISR": "Israel",
    "TUR": "Turquia",
    "IND": "Índia",
    "PAK": "Paquistão",
    "BGD": "Bangladesh",
    "LKA": "Sri Lanka",
    "CHN": "China",
    "JPN": "Japão",
    "KOR": "Coreia do Sul",
    "IDN": "Indonésia",
    "MYS": "Malásia",
    "THA": "Tailândia",
    "VNM": "Vietname",

    "AUS": "Austrália",
    "NZL": "Nova Zelândia",
}

# ============================================================
# UTILITÁRIOS DE TEXTO
# ============================================================

def normalize_text(value):
    if value is None:
        return ""

    if not isinstance(value, str):
        value = choose_multilingual_text(value)

    value = repair_mojibake(value)

    value = html.unescape(value)

    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        c for c in value
        if not unicodedata.combining(c)
    )

    value = value.lower()
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def repair_mojibake(value):
    """
    Corrige situações do tipo:
    Ã¡ -> á
    â€” -> —
    ItÃ¡lia -> Itália

    Tenta no máximo duas vezes para evitar alterar
    texto legítimo.
    """

    if not isinstance(value, str):
        return value

    current = value

    for _ in range(2):
        if not any(
            token in current
            for token in ("Ã", "Â", "â", "ð", "�")
        ):
            break

        try:
            candidate = current.encode(
                "latin1"
            ).decode("utf-8")
        except Exception:
            break

        if candidate == current:
            break

        current = candidate

    return current


def choose_multilingual_text(value):
    """
    Extrai texto real de estruturas TED multilingues.

    Aceita:
    - string
    - lista de strings
    - dict
    - lista de dicts
    """

    if value is None:
        return ""

    if isinstance(value, str):
        return repair_mojibake(value)

    if isinstance(value, list):
        # Primeiro procura objetos com language/text
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

                if text_value and lang in {
                    "eng",
                    "en",
                    "english",
                }:
                    return choose_multilingual_text(text_value)

        for item in value:
            result = choose_multilingual_text(item)
            if result:
                return result

        return ""

    if isinstance(value, dict):
        # TED costuma usar códigos linguísticos como chaves.
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
                result = choose_multilingual_text(value[key])
                if result:
                    return result

        # Estrutura language/text
        for key in (
            "text",
            "value",
            "content",
            "title",
            "name",
            "description",
        ):
            if key in value:
                result = choose_multilingual_text(value[key])
                if result:
                    return result

        # Último recurso: primeiro valor textual
        for item in value.values():
            result = choose_multilingual_text(item)
            if result:
                return result

        return ""

    return repair_mojibake(str(value))


def flatten(value):
    return choose_multilingual_text(value)


def clean_text(value):
    value = choose_multilingual_text(value)
    value = repair_mojibake(value)
    value = html.unescape(value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


# ============================================================
# DATAS
# ============================================================

def cutoff_date():
    return date.today() - timedelta(days=PERIOD_DAYS)


def parse_date(value):
    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    value = choose_multilingual_text(value).strip()

    if not value:
        return None

    value = value[:10]

    for fmt in (
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d-%m-%Y",
        "%d/%m/%Y",
    ):
        try:
            return datetime.strptime(value, fmt).date()
        except Exception:
            pass

    return None


def date_string(value):
    d = parse_date(value)
    return d.isoformat() if d else ""


# ============================================================
# PAÍSES
# ============================================================

def country_from_code(value):
    value = choose_multilingual_text(value).strip().upper()

    if value in COUNTRY_MAP:
        return COUNTRY_MAP[value]

    if value in ISO3_MAP:
        return ISO3_MAP[value]

    return repair_mojibake(value)


def extract_country(item):
    candidates = [
        item.get("buyer-country"),
        item.get("buyerCountry"),
        item.get("country"),
        item.get("country-code"),
        item.get("buyer_country"),
    ]

    for candidate in candidates:
        text = choose_multilingual_text(candidate).strip()

        if not text:
            continue

        code = text.upper()

        if code in COUNTRY_MAP:
            return COUNTRY_MAP[code]

        if code in ISO3_MAP:
            return ISO3_MAP[code]

        return repair_mojibake(text)

    return ""


def region_from_country(country):
    n = normalize_text(country)

    europe = {
        "portugal", "espanha", "franca", "alemanha", "italia",
        "belgica", "paises baixos", "irlanda", "austria",
        "polonia", "chequia", "eslovaquia", "hungria",
        "romenia", "bulgaria", "croacia", "eslovenia",
        "suecia", "finlandia", "dinamarca", "estonia",
        "letonia", "lituania", "grecia", "chipre", "malta",
        "noruega", "islandia", "suica", "reino unido",
    }

    africa = {
        "marrocos", "argelia", "tunisia", "egito",
        "africa do sul", "quenia", "uganda", "tanzania",
        "mocambique", "nigeria", "gana", "etiopia",
    }

    america = {
        "estados unidos", "canada", "mexico", "brasil",
        "chile", "colombia", "peru", "argentina",
        "uruguai", "paraguai",
    }

    asia = {
        "arabia saudita", "emirados arabes unidos", "qatar",
        "oma", "jordania", "israel", "turquia", "india",
        "paquistao", "bangladesh", "sri lanka", "china",
        "japao", "coreia do sul", "indonesia", "malasia",
        "tailandia", "vietname",
    }

    oceania = {
        "australia", "nova zelandia",
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
        values = re.findall(r"\d{8}", value)
    elif isinstance(value, list):
        values = []
        for item in value:
            values.extend(
                re.findall(
                    r"\d{8}",
                    choose_multilingual_text(item)
                )
            )
    elif isinstance(value, dict):
        values = []
        for item in value.values():
            values.extend(
                re.findall(
                    r"\d{8}",
                    choose_multilingual_text(item)
                )
            )
    else:
        values = re.findall(r"\d{8}", str(value))

    for cpv in values:
        if cpv not in result:
            result.append(cpv)

    return result


# ============================================================
# CLASSIFICAÇÃO
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
    "archéologie",
    "archéologique",
    "fouilles archéologiques",
    "arqueologia",
    "arqueológico",
    "arqueológica",
    "escavação arqueológica",
    "acompanhamento arqueológico",
    "archäologie",
    "archäologisch",
]

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
    "património cultural",
    "patrimonio cultural",
    "avaliação patrimonial",
    "patrimoine culturel",
    "patrimoine archeologique",
    "patrimoine historique",
    "heritage",
]

MAJOR_TERMS_NORMALIZED = [
    normalize_text(x)
    for x in MAJOR_PROJECT_TERMS
]

DIRECT_TERMS_NORMALIZED = [
    normalize_text(x)
    for x in DIRECT_TERMS
]

HERITAGE_TERMS_NORMALIZED = [
    normalize_text(x)
    for x in HERITAGE_TERMS
]


def contains_any(text, terms):
    text = normalize_text(text)

    for term in terms:
        if term and term in text:
            return True

    return False


def classify_result(title, description, cpvs):
    """
    Regra fundamental:

    1. Texto explicitamente arqueológico:
       -> Arqueologia direta

    2. Património/heritage:
       -> Património / potencial arqueológico

    3. CPV arqueológico sozinho:
       -> NÃO basta.

    Isto evita falsos positivos como:
    "serviços de água" com dezenas de CPV,
    onde por acaso aparece 71351914.
    """

    title_n = normalize_text(title)
    description_n = normalize_text(description)

    combined = f"{title_n} {description_n}".strip()

    cpvs = set(normalize_cpvs(cpvs))

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

    cpv_direct = bool(
        cpvs.intersection(ARCHAEOLOGY_CPVS)
    )

    # --------------------------------------------------------
    # ARQUEOLOGIA DIRETA
    # --------------------------------------------------------

    if direct_text:
        score = 100

        if cpv_direct:
            score += 15

        if major:
            score += 10

        return (
            "Arqueologia direta",
            min(score, 100)
        )

    # --------------------------------------------------------
    # PATRIMÓNIO
    # --------------------------------------------------------

    if heritage_text:
        score = 70

        if cpv_direct:
            score += 15

        if major:
            score += 10

        return (
            "Património / potencial arqueológico",
            min(score, 95)
        )

    # --------------------------------------------------------
    # CPV ARQUEOLÓGICO ISOLADO
    # --------------------------------------------------------
    #
    # Não classificamos como arqueologia.
    # Evita falsos positivos.
    #

    return ("Outro", 0)


# ============================================================
# LIMPEZA DE RESULTADOS
# ============================================================

def normalize_result(result):
    if not isinstance(result, dict):
        return None

    title = clean_text(
        result.get("title", "")
    )

    description = clean_text(
        result.get("description", "")
    )

    buyer = clean_text(
        result.get("buyer", "")
    )

    country = clean_text(
        result.get("country", "")
    )

    source = clean_text(
        result.get("source", "")
    )

    url = clean_text(
        result.get("url", "")
    )

    cpv = normalize_cpvs(
        result.get("cpv", [])
    )

    category = clean_text(
        result.get("category", "")
    )

    score = result.get("score", 0)

    try:
        score = int(score)
    except Exception:
        score = 0

    return {
        "title": title,
        "buyer": buyer,
        "country": country,
        "date": date_string(result.get("date")),
        "deadline": date_string(result.get("deadline")),
        "cpv": cpv,
        "category": category,
        "score": score,
        "source": source,
        "url": url,
        "description": description,
    }


def recent_enough(result):
    """
    Mantém apenas resultados publicados nos últimos
    PERIOD_DAYS dias.

    Se não houver data, não eliminamos automaticamente,
    porque algumas fontes não disponibilizam a data.
    """

    d = parse_date(result.get("date"))

    if not d:
        return True

    return d >= cutoff_date()


def dedupe_results(results):
    unique = {}
    output = []

    for item in results:
        normalized = normalize_result(item)

        if not normalized:
            continue

        if not normalized["title"]:
            continue

        if not recent_enough(normalized):
            continue

        key = (
            normalize_text(normalized["title"]),
            normalize_text(normalized["buyer"]),
            normalized["date"],
            normalized["country"],
        )

        if key in unique:
            old = unique[key]

            if normalized["score"] > old["score"]:
                unique[key] = normalized

            continue

        unique[key] = normalized
        output.append(normalized)

    output = list(unique.values())

    output.sort(
        key=lambda x: (
            -int(x.get("score", 0)),
            x.get("date", ""),
        ),
        reverse=False
    )

    # Ordenação final: score maior e data mais recente
    output.sort(
        key=lambda x: (
            -int(x.get("score", 0)),
            x.get("date", ""),
        ),
        reverse=True
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
    title = choose_multilingual_text(value)
    title = clean_text(title)

    title = re.sub(
        r"^\s*(?:[A-Za-z]{2,3})\s*[-:]\s*",
        "",
        title
    )

    return title.strip()


def ted_notice_to_result(notice):
    title = clean_ted_title(
        notice.get("notice-title")
        or notice.get("title")
        or ""
    )

    description = clean_text(
        notice.get("description-proc")
        or notice.get("description-lot")
        or notice.get("description")
        or ""
    )

    buyer = clean_text(
        notice.get("buyer-name")
        or notice.get("buyer")
        or ""
    )

    country = extract_country(notice)

    cpvs = normalize_cpvs(
        notice.get("classification-cpv")
        or notice.get("cpv")
        or []
    )

    pub_date = (
        notice.get("publication-date")
        or notice.get("publicationDate")
        or notice.get("date")
        or ""
    )

    deadline = (
        notice.get("deadline-date-lot")
        or notice.get("deadline-receipt-tender-date-lot")
        or notice.get("deadline-receipt-request-date-lot")
        or notice.get("deadline")
        or ""
    )

    category, score = classify_result(
        title,
        description,
        cpvs
    )

    publication_number = (
        notice.get("publication-number")
        or notice.get("publicationNumber")
        or ""
    )

    publication_number = clean_text(
        publication_number
    )

    url = ""

    if publication_number:
        url = (
            "https://ted.europa.eu/en/notice/-/detail/"
            + publication_number
        )

    if not url:
        url = choose_multilingual_text(
            notice.get("url")
            or notice.get("links")
            or ""
        )

    return {
        "title": title,
        "buyer": buyer,
        "country": country,
        "date": date_string(pub_date),
        "deadline": date_string(deadline),
        "cpv": cpvs,
        "category": category,
        "score": score,
        "source": "TED — Europa",
        "url": url,
        "description": description,
    }


def query_ted(term, diagnostics):
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

        notices = data.get("notices", [])

        results = []

        for notice in notices:
            item = ted_notice_to_result(notice)

            if not item:
                continue

            if item["category"] == "Outro":
                continue

            if not recent_enough(item):
                continue

            results.append(item)

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

def query_world_bank(term, diagnostics):
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

        if isinstance(data, dict):
            for key in (
                "procnotices",
                "notices",
                "results",
                "documents",
            ):
                value = data.get(key)

                if isinstance(value, list):
                    rows = value
                    break

                if isinstance(value, dict):
                    rows = list(value.values())
                    break

        results = []

        for row in rows:
            if not isinstance(row, dict):
                continue

            title = clean_text(
                row.get("bid_description")
                or row.get("project_name")
                or row.get("procurement_name")
                or row.get("notice_title")
                or row.get("title")
                or ""
            )

            description = clean_text(
                row.get("description")
                or row.get("bid_description")
                or ""
            )

            buyer = clean_text(
                row.get("borrower")
                or row.get("project_name")
                or row.get("buyer")
                or ""
            )

            country = clean_text(
                row.get("country")
                or row.get("countryname")
                or ""
            )

            cpvs = normalize_cpvs(
                row.get("cpv")
                or row.get("classification-cpv")
                or []
            )

            pub_date = (
                row.get("publication_date")
                or row.get("publicationDate")
                or row.get("date")
                or row.get("notice_date")
                or ""
            )

            deadline = (
                row.get("submission_deadline")
                or row.get("deadline")
                or ""
            )

            category, score = classify_result(
                title,
                description,
                cpvs
            )

            if category == "Outro":
                continue

            item = {
                "title": title,
                "buyer": buyer,
                "country": country,
                "date": date_string(pub_date),
                "deadline": date_string(deadline),
                "cpv": cpvs,
                "category": category,
                "score": score,
                "source": "World Bank Procurement",
                "url": clean_text(
                    row.get("url")
                    or row.get("notice_url")
                    or row.get("web_url")
                    or ""
                ),
                "description": description,
            }

            if recent_enough(item):
                results.append(item)

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
# SOUTH AFRICA eTENDERS / OCDS
# ============================================================

def query_south_africa(term, diagnostics):
    try:
        response = requests.get(
            SOUTH_AFRICA_URL,
            params={
                "page": 1,
                "pageSize": 100,
            },
            timeout=REQUEST_TIMEOUT,
            headers={
                "Accept": "application/json",
            },
        )

        response.raise_for_status()

        data = response.json()

        releases = []

        if isinstance(data, dict):
            if isinstance(data.get("releases"), list):
                releases = data["releases"]

            elif isinstance(data.get("results"), list):
                releases = data["results"]

            elif isinstance(data.get("data"), list):
                releases = data["data"]

        elif isinstance(data, list):
            releases = data

        results = []

        term_n = normalize_text(term)

        for release in releases:
            if not isinstance(release, dict):
                continue

            tender = release.get("tender", {})
            if not isinstance(tender, dict):
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

            if term_n and term_n not in text:
                continue

            classification = tender.get(
                "classification",
                {}
            )

            cpvs = normalize_cpvs(
                classification.get("id")
                if isinstance(classification, dict)
                else classification
            )

            buyer = release.get("buyer", {})

            if isinstance(buyer, dict):
                buyer_name = clean_text(
                    buyer.get("name", "")
                )
            else:
                buyer_name = clean_text(buyer)

            date_value = (
                release.get("date")
                or tender.get("date")
                or release.get("publishedDate")
                or ""
            )

            deadline = (
                tender.get("tenderPeriod", {})
                if isinstance(
                    tender.get("tenderPeriod", {}),
                    dict
                )
                else {}
            )

            deadline_value = deadline.get(
                "end",
                ""
            )

            category, score = classify_result(
                title,
                description,
                cpvs
            )

            if category == "Outro":
                continue

            item = {
                "title": title,
                "buyer": buyer_name,
                "country": "África do Sul",
                "date": date_string(date_value),
                "deadline": date_string(deadline_value),
                "cpv": cpvs,
                "category": category,
                "score": score,
                "source": "South Africa eTenders — OCDS",
                "url": clean_text(
                    release.get("url")
                    or release.get("id")
                    or ""
                ),
                "description": description,
            }

            if recent_enough(item):
                results.append(item)

        diagnostics.append({
            "source": "South Africa eTenders — OCDS",
            "term": term,
            "ok": True,
            "count": len(results),
            "raw_count": len(releases),
            "error": "",
        })

        return results

    except Exception as exc:
        diagnostics.append({
            "source": "South Africa eTenders — OCDS",
            "term": term,
            "ok": False,
            "count": 0,
            "raw_count": 0,
            "error": str(exc),
        })

        return []


# ============================================================
# SECOP II — COLÔMBIA
# ============================================================

def query_secop(term, diagnostics):
    try:
        params = {
            "$limit": 100,
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

        if not isinstance(data, list):
            data = []

        results = []

        term_n = normalize_text(term)

        for row in data:
            if not isinstance(row, dict):
                continue

            title = clean_text(
                row.get("nombre_del_procedimiento")
                or row.get("objeto_del_contrato")
                or row.get("descripcion_del_proceso")
                or row.get("title")
                or ""
            )

            description = clean_text(
                row.get("descripcion_del_proceso")
                or row.get("objeto_del_contrato")
                or ""
            )

            combined = normalize_text(
                f"{title} {description}"
            )

            if term_n and term_n not in combined:
                continue

            buyer = clean_text(
                row.get("entidad")
                or row.get("nombre_entidad")
                or ""
            )

            country = "Colômbia"

            cpvs = normalize_cpvs(
                row.get("codigo_principal_de_producto")
                or row.get("codigo_unspsc")
                or ""
            )

            date_value = (
                row.get("fecha_de_publicacion")
                or row.get("fecha_publicacion")
                or ""
            )

            deadline = (
                row.get("fecha_de_recepcion_de_ofertas")
                or row.get("fecha_de_cierre")
                or ""
            )

            category, score = classify_result(
                title,
                description,
                cpvs
            )

            if category == "Outro":
                continue

            item = {
                "title": title,
                "buyer": buyer,
                "country": country,
                "date": date_string(date_value),
                "deadline": date_string(deadline),
                "cpv": cpvs,
                "category": category,
                "score": score,
                "source": "SECOP II — Colômbia",
                "url": clean_text(
                    row.get("url")
                    or row.get("link")
                    or ""
                ),
                "description": description,
            }

            if recent_enough(item):
                results.append(item)

        diagnostics.append({
            "source": "SECOP II — Colômbia",
            "term": term,
            "ok": True,
            "count": len(results),
            "raw_count": len(data),
            "error": "",
        })

        return results

    except Exception as exc:
        diagnostics.append({
            "source": "SECOP II — Colômbia",
            "term": term,
            "ok": False,
            "count": 0,
            "raw_count": 0,
            "error": str(exc),
        })

        return []


# ============================================================
# PESQUISA AUTOMÁTICA GLOBAL
# ============================================================

AUTOMATIC_TERMS = [
    "archaeology",
    "archaeological",
    "archaeological excavation",
    "archaeological monitoring",
    "cultural heritage",
    "heritage assessment",
    "historic environment",
    "chance finds",
    "archéologie",
    "archéologique",
    "fouilles archéologiques",
    "patrimoine culturel",
    "arqueologia",
    "arqueológico",
    "arqueológica",
    "escavação arqueológica",
    "acompanhamento arqueológico",
    "archäologie",
    "archäologisch",
]


def is_global_archaeology_query(query):
    q = normalize_text(query)

    if not q:
        return True

    direct_queries = {
        "archaeology",
        "archaeological",
        "archaeologist",
        "archaeological excavation",
        "archaeological monitoring",
        "archaeological survey",
        "archaeological investigation",
        "archaeological services",
        "archéologie",
        "archéologique",
        "fouilles archéologiques",
        "arqueologia",
        "arqueologico",
        "arqueologica",
        "arqueológico",
        "arqueológica",
        "escavacao arqueologica",
        "acompanhamento arqueologico",
        "patrimonio cultural",
        "patrimonio",
        "cultural heritage",
        "heritage",
        "archaeologie",
        "archaologisch",
        "archaeologisch",
    }

    return q in direct_queries


def automatic_search(query, diagnostics):
    """
    Pesquisa global.

    Se o utilizador pesquisar directamente por arqueologia,
    são pesquisadas várias formulações linguísticas.

    Se fizer uma pesquisa específica, é utilizada essa pesquisa.
    """

    if is_global_archaeology_query(query):
        terms = AUTOMATIC_TERMS
    else:
        terms = [query]

    jobs = []

    # TED
    for term in terms:
        jobs.append(
            ("TED", term)
        )

    # World Bank
    for term in terms:
        jobs.append(
            ("WORLD_BANK", term)
        )

    # South Africa
    for term in terms:
        jobs.append(
            ("SOUTH_AFRICA", term)
        )

    # Colombia
    for term in terms:
        jobs.append(
            ("SECOP", term)
        )

    results = []

    def run_job(job):
        source, term = job

        if source == "TED":
            return query_ted(
                term,
                diagnostics
            )

        if source == "WORLD_BANK":
            return query_world_bank(
                term,
                diagnostics
            )

        if source == "SOUTH_AFRICA":
            return query_south_africa(
                term,
                diagnostics
            )

        if source == "SECOP":
            return query_secop(
                term,
                diagnostics
            )

        return []

    # --------------------------------------------------------
    # Execução paralela
    # --------------------------------------------------------

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

        for future in as_completed(futures):
            try:
                value = future.result()

                if value:
                    results.extend(value)

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

    region_n = normalize_text(region)
    category_n = normalize_text(category)

    for item in results:
        item_region = normalize_text(
            region_from_country(
                item.get("country", "")
            )
        )

        item_category = normalize_text(
            item.get("category", "")
        )

        if region_n:
            if item_region != region_n:
                continue

        if category_n:
            if category_n not in item_category:
                continue

        filtered.append(item)

    return filtered


# ============================================================
# ESTATÍSTICAS
# ============================================================

def build_regions(results):
    regions = {}

    for item in results:
        region = region_from_country(
            item.get("country", "")
        )

        regions[region] = (
            regions.get(region, 0) + 1
        )

    return dict(
        sorted(
            regions.items(),
            key=lambda x: (-x[1], x[0])
        )
    )


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():
    automatic_sources = [
        source["name"]
        for source in SOURCES
        if source.get("automatic")
    ]

    return {
        "ok": True,
        "app": "Arqueologia Radar",
        "version": "2.1",
        "period_days": PERIOD_DAYS,
        "sources": len(SOURCES),
        "automatic_sources": len(
            automatic_sources
        ),
        "automatic_source_names": automatic_sources,
        "date": date.today().isoformat(),
    }


# ============================================================
# TESTE TED - PAÍS
# ============================================================

@app.get("/api/test-ted-country")
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
        f'AND buyer-country={country.upper()}'
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
            "status_code": response.status_code,
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

@app.get("/api/test-ted-minimal")
def test_ted_minimal(
    term: str = Query("archaeology")
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
            "status_code": response.status_code,
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
    ),
):
    started = datetime.now()

    query = clean_text(q)

    diagnostics = []

    automatic_mode = is_global_archaeology_query(
        query
    )

    # --------------------------------------------------------
    # Pesquisa automática
    # --------------------------------------------------------

    if automatic_mode:
        results = automatic_search(
            query,
            diagnostics
        )

    else:
        # Pesquisa específica:
        # mesmo motor global, mas com o termo indicado.
        results = automatic_search(
            query,
            diagnostics
        )

    # --------------------------------------------------------
    # Normalização
    # --------------------------------------------------------

    normalized_results = []

    for item in results:
        normalized = normalize_result(item)

        if not normalized:
            continue

        # Nunca mostrar "Outro"
        if normalized.get("category") == "Outro":
            continue

        # Regra dos últimos 365 dias
        if not recent_enough(normalized):
            continue

        normalized_results.append(
            normalized
        )

    # --------------------------------------------------------
    # Duplicados
    # --------------------------------------------------------

    normalized_results = dedupe_results(
        normalized_results
    )

    # --------------------------------------------------------
    # Filtros
    # --------------------------------------------------------

    normalized_results = apply_filters(
        normalized_results,
        region=region,
        category=category,
    )

    # --------------------------------------------------------
    # Regiões
    # --------------------------------------------------------

    regions = build_regions(
        normalized_results
    )

    elapsed = (
        datetime.now() - started
    ).total_seconds()

    automatic_source_names = [
        source["name"]
        for source in SOURCES
        if source.get("automatic")
    ]

    portal_count = len([
        source
        for source in SOURCES
        if not source.get("automatic")
    ])

    return {
        "ok": True,
        "query": query,
        "automatic_mode": automatic_mode,
        "region": region,
        "category": category,
        "results": normalized_results,
        "count": len(normalized_results),
        "sources": len(SOURCES),
        "automatic_sources": len(
            automatic_source_names
        ),
        "automatic_source_names": automatic_source_names,
        "portal_count": portal_count,
        "regions": regions,
        "diagnostics": diagnostics,
        "searched_at": date.today().isoformat(),
        "period_days": PERIOD_DAYS,
        "cutoff_date": cutoff_date().isoformat(),
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
    file_path = BASE_DIR / "index.html"

    if file_path.exists():
        return FileResponse(
            file_path,
            media_type="text/html"
        )

    return JSONResponse({
        "ok": True,
        "message": "Arqueologia Radar online."
    })


@app.get("/app.js")
def app_js():
    file_path = BASE_DIR / "app.js"

    if file_path.exists():
        return FileResponse(
            file_path,
            media_type="application/javascript"
        )

    return JSONResponse({
        "ok": False,
        "error": "app.js não encontrado."
    })


@app.get("/manifest.json")
def manifest():
    file_path = BASE_DIR / "manifest.json"

    if file_path.exists():
        return FileResponse(
            file_path,
            media_type="application/manifest+json"
        )

    return JSONResponse({
        "name": "Arqueologia Radar"
    })
