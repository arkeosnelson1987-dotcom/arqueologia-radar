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
    version="2.5.1"
)

REQUEST_TIMEOUT = 30
PERIOD_DAYS = 365
PAGE_SIZE = 100

TED_URL = "https://api.ted.europa.eu/v3/notices/search"
WORLD_BANK_URL = "https://search.worldbank.org/api/v2/procnotices"
SECOP_URL = "https://www.datos.gov.co/resource/p6dx-8zbt.json"

# API oficial de dados abertos do Brasil / PNCP
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
        "country": "Europa",
        "region": "Europa",
        "automatic": True,
        "type": "api",
    },
    {
        "name": "World Bank Procurement",
        "country": "Global",
        "region": "Global",
        "automatic": True,
        "type": "api",
    },
    {
        "name": "SECOP II — Colômbia",
        "country": "Colômbia",
        "region": "América",
        "automatic": True,
        "type": "api",
    },
    {
        "name": "PNCP — Brasil",
        "country": "Brasil",
        "region": "América",
        "automatic": True,
        "type": "api",
    },
    {
        "name": "South Africa eTenders",
        "country": "África do Sul",
        "region": "África",
        "automatic": False,
        "type": "portal",
    },
    {
        "name": "African Development Bank",
        "country": "África",
        "region": "África",
        "automatic": False,
        "type": "portal",
    },
    {
        "name": "SAM.gov",
        "country": "Estados Unidos",
        "region": "América",
        "automatic": False,
        "type": "portal",
    },
    {
        "name": "BASE Portugal",
        "country": "Portugal",
        "region": "Europa",
        "automatic": False,
        "type": "portal",
    },
    {
        "name": "Contratación del Estado — Espanha",
        "country": "Espanha",
        "region": "Europa",
        "automatic": False,
        "type": "portal",
    },
    {
        "name": "UNDB",
        "country": "Global",
        "region": "Global",
        "automatic": False,
        "type": "portal",
    },
    {
        "name": "UNGM",
        "country": "Global",
        "region": "Global",
        "automatic": False,
        "type": "portal",
    },
    {
        "name": "EBRD",
        "country": "Europa/Ásia",
        "region": "Global",
        "automatic": False,
        "type": "portal",
    },
    {
        "name": "EIB",
        "country": "Europa",
        "region": "Europa",
        "automatic": False,
        "type": "portal",
    },
    {
        "name": "Oman Tender Board",
        "country": "Omã",
        "region": "Ásia",
        "automatic": False,
        "type": "portal",
    },
    {
        "name": "Etimad — Arábia Saudita",
        "country": "Arábia Saudita",
        "region": "Ásia",
        "automatic": False,
        "type": "portal",
    },
    {
        "name": "UAE Federal Procurement",
        "country": "Emirados Árabes Unidos",
        "region": "Ásia",
        "automatic": False,
        "type": "portal",
    },
    {
        "name": "Qatar Government Procurement",
        "country": "Qatar",
        "region": "Ásia",
        "automatic": False,
        "type": "portal",
    },
    {
        "name": "Maroc Marchés Publics",
        "country": "Marrocos",
        "region": "África",
        "automatic": False,
        "type": "portal",
    },
    {
        "name": "Uganda eGP",
        "country": "Uganda",
        "region": "África",
        "automatic": False,
        "type": "portal",
    },
    {
        "name": "Kenya Public Procurement",
        "country": "Quénia",
        "region": "África",
        "automatic": False,
        "type": "portal",
    },
    {
        "name": "Tanzania PPRA",
        "country": "Tanzânia",
        "region": "África",
        "automatic": False,
        "type": "portal",
    },
    {
        "name": "Mozambique Contratação Pública",
        "country": "Moçambique",
        "region": "África",
        "automatic": False,
        "type": "portal",
    },
    {
        "name": "ChileCompra",
        "country": "Chile",
        "region": "América",
        "automatic": False,
        "type": "portal",
    },
    {
        "name": "IDB",
        "country": "América Latina",
        "region": "América",
        "automatic": False,
        "type": "portal",
    },
    {
        "name": "ADB",
        "country": "Ásia",
        "region": "Ásia",
        "automatic": False,
        "type": "portal",
    },
    {
        "name": "AusTender",
        "country": "Austrália",
        "region": "Oceania",
        "automatic": False,
        "type": "portal",
    },
    {
        "name": "NZ GETS",
        "country": "Nova Zelândia",
        "region": "Oceania",
        "automatic": False,
        "type": "portal",
    },
    {
        "name": "Redeia / Red Eléctrica",
        "country": "Espanha",
        "region": "Europa",
        "automatic": False,
        "type": "portal",
    },
]

# ============================================================
# TERMOS DE ARQUEOLOGIA
# ============================================================

DIRECT_TERMS = [
    # Inglês
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
    "archaeological works",
    "archaeological work",

    # Francês
    "archéologie",
    "archéologique",
    "archéologue",
    "fouilles archéologiques",

    # Português
    "arqueologia",
    "arqueológico",
    "arqueológica",
    "arqueólogo",
    "arqueóloga",
    "escavação arqueológica",
    "escavações arqueológicas",
    "acompanhamento arqueológico",
    "monitorização arqueológica",
    "prospeção arqueológica",
    "prospecção arqueológica",
    "avaliação arqueológica",
    "trabalhos arqueológicos",
    "serviços arqueológicos",
    "consultoria arqueológica",
    "consultor arqueológico",
    "arqueólogo coordenador",

    # Espanhol
    "arqueología",
    "arqueológico",
    "arqueológica",
    "arqueólogo",
    "arqueóloga",
    "excavación arqueológica",
    "excavaciones arqueológicas",
    "seguimiento arqueológico",
    "prospección arqueológica",
    "prospeccion arqueologica",
    "evaluación arqueológica",
    "trabajos arqueológicos",
    "servicios arqueológicos",

    # Alemão
    "archäologie",
    "archäologisch",
    "archäologe",
    "archäologin",

    # Neerlandês
    "archeologie",
    "archeologisch",
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
    "heritage conservation",
    "heritage management",
    "património cultural",
    "patrimonio cultural",
    "avaliação patrimonial",
    "avaliacao patrimonial",
    "impacte patrimonial",
    "impacto patrimonial",
    "patrimoine culturel",
    "patrimoine archéologique",
    "patrimoine historique",
    "heritage conservation",
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

    "ferrovia",
    "ferroviário",
    "rodovia",
    "autoestrada",
    "mineração",
    "oleoduto",
    "gasoduto",
    "aeroporto",
    "porto",
    "barragem",
    "energia",
    "linha elétrica",
    "infraestrutura",
    "construção",

    "chemin de fer",
    "autoroute",
    "mine",
    "pipeline",
    "aéroport",
    "port",
    "barrage",
    "énergie",
    "infrastructure",
    "construction",
]

SUPPORT_EXCLUSIONS = [
    "photographer",
    "photography",
    "photographic",
    "architect",
    "architecture design",
    "legal expert",
    "legal services",
    "lawyer",
    "attorney",
    "social media",
    "communication designer",
    "graphic designer",
    "designer",
    "communications",
    "public relations",
    "marketing",
    "media coordinator",
    "signboards",
    "office equipment",
    "computer",
    "information technology",
    "software",
    "website",
    "printing",
    "vehicle",
    "furniture",
    "stationery",
    "training",
    "catering",
    "security",
    "cleaning",
]

ARCHAEOLOGY_CPVS = {
    "71351914",
    "71351910",
    "71351900",
    "71351720",
    "71351811",
    "71351730",
}

GENERAL_EXCAVATION_CPV = {
    "45112450"
}

# ============================================================
# PAÍSES / REGIÕES
# ============================================================

COUNTRY_MAP = {
    # Europa
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
    "GB": "Reino Unido",
    "UK": "Reino Unido",

    # África
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
    "SN": "Senegal",
    "CI": "Costa do Marfim",
    "CM": "Camarões",
    "RW": "Ruanda",
    "BW": "Botsuana",
    "NA": "Namíbia",
    "ZM": "Zâmbia",
    "ZW": "Zimbabué",
    "AO": "Angola",
    "CV": "Cabo Verde",

    # América
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
    "BO": "Bolívia",
    "EC": "Equador",
    "PA": "Panamá",
    "CR": "Costa Rica",
    "GT": "Guatemala",
    "DO": "República Dominicana",

    # Ásia / Médio Oriente
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
    "PH": "Filipinas",
    "SG": "Singapura",
    "NP": "Nepal",
    "KZ": "Cazaquistão",
    "UZ": "Uzbequistão",
    "AZ": "Azerbaijão",
    "AM": "Arménia",
    "GE": "Geórgia",

    # Oceania
    "AU": "Austrália",
    "NZ": "Nova Zelândia",
    "FJ": "Fiji",
}

ISO3_MAP = {
    "PT": "PRT",
    "ES": "ESP",
    "FR": "FRA",
    "DE": "DEU",
    "IT": "ITA",
    "GB": "GBR",
    "UK": "GBR",
    "IE": "IRL",
    "NL": "NLD",
    "BE": "BEL",
    "MA": "MAR",
    "DZ": "DZA",
    "TN": "TUN",
    "EG": "EGY",
    "ZA": "ZAF",
    "KE": "KEN",
    "UG": "UGA",
    "TZ": "TZA",
    "MZ": "MOZ",
    "NG": "NGA",
    "GH": "GHA",
    "ET": "ETH",
    "US": "USA",
    "CA": "CAN",
    "MX": "MEX",
    "BR": "BRA",
    "CL": "CHL",
    "CO": "COL",
    "PE": "PER",
    "AR": "ARG",
    "UY": "URY",
    "PY": "PRY",
    "SA": "SAU",
    "AE": "ARE",
    "QA": "QAT",
    "OM": "OMN",
    "JO": "JOR",
    "IL": "ISR",
    "TR": "TUR",
    "IN": "IND",
    "PK": "PAK",
    "BD": "BGD",
    "LK": "LKA",
    "CN": "CHN",
    "JP": "JPN",
    "KR": "KOR",
    "ID": "IDN",
    "MY": "MYS",
    "TH": "THA",
    "VN": "VNM",
    "PH": "PHL",
    "AU": "AUS",
    "NZ": "NZL",
}

REGION_COUNTRIES = {
    "Europa": {
        "PT", "ES", "FR", "DE", "IT", "BE", "NL", "LU",
        "IE", "AT", "PL", "CZ", "SK", "HU", "RO", "BG",
        "HR", "SI", "SE", "FI", "DK", "EE", "LV", "LT",
        "GR", "CY", "MT", "NO", "IS", "CH", "GB", "UK"
    },
    "África": {
        "MA", "DZ", "TN", "EG", "ZA", "KE", "UG", "TZ",
        "MZ", "NG", "GH", "ET", "SN", "CI", "CM", "RW",
        "BW", "NA", "ZM", "ZW", "AO", "CV"
    },
    "América": {
        "US", "CA", "MX", "BR", "CL", "CO", "PE", "AR",
        "UY", "PY", "BO", "EC", "PA", "CR", "GT", "DO"
    },
    "Ásia": {
        "SA", "AE", "QA", "OM", "JO", "IL", "TR", "IN",
        "PK", "BD", "LK", "CN", "JP", "KR", "ID", "MY",
        "TH", "VN", "PH", "SG", "NP", "KZ", "UZ", "AZ",
        "AM", "GE"
    },
    "Oceania": {
        "AU", "NZ", "FJ"
    },
}

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
    "archéologie",
    "archéologique",
    "archéologue",
    "fouilles archéologiques",
    "arqueologia",
    "arqueológico",
    "arqueológica",
    "arqueólogo",
    "escavação arqueológica",
    "acompanhamento arqueológico",
    "prospeção arqueológica",
    "avaliação arqueológica",
    "trabalhos arqueológicos",
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
    "archaeological survey",
    "archaeological assessment",
    "archaeological coordinator",
    "archaeological consultancy",
]

AUTOMATIC_TERMS_SECOP = [
    "arqueologia",
    "arqueológico",
    "arqueológica",
    "arqueólogo",
    "arqueóloga",
    "archaeology",
    "archaeological",
    "archaeologist",
]

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def normalize_text(value):
    if value is None:
        return ""

    text = html.unescape(str(value))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_for_search(value):
    text = normalize_text(value).lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        char for char in text
        if not unicodedata.combining(char)
    )
    return text


def repair_mojibake(value):
    if value is None:
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
        "Ãª": "ê",
        "Ã´": "ô",
        "Ã¼": "ü",
        "Ã€": "À",
        "Ã": "Á",
        "Ã‰": "É",
        "Ã": "Í",
        "Ã“": "Ó",
        "Ãš": "Ú",
        "Ã‡": "Ç",
        "Ã‘": "Ñ",
        "â€”": "—",
        "â€“": "–",
        "â€œ": "“",
        "â€": "”",
        "â€˜": "‘",
        "â€™": "’",
        "â€¦": "…",
    }

    for _ in range(3):
        changed = False

        try:
            candidate = text.encode("latin1").decode("utf-8")
            if candidate != text:
                text = candidate
                changed = True
        except Exception:
            pass

        for bad, good in replacements.items():
            if bad in text:
                text = text.replace(bad, good)
                changed = True

        if not changed:
            break

    return text


def parse_date(value):
    if not value:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    text = str(value).strip()

    candidates = [
        text,
        text[:10],
    ]

    for candidate in candidates:
        try:
            return datetime.fromisoformat(
                candidate.replace("Z", "+00:00")
            ).date()
        except Exception:
            pass

        try:
            return date.fromisoformat(candidate)
        except Exception:
            pass

    match = re.search(
        r"(20\d{2})[-/](\d{1,2})[-/](\d{1,2})",
        text
    )

    if match:
        try:
            return date(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
            )
        except Exception:
            return None

    return None


def cutoff_date():
    return date.today() - timedelta(days=PERIOD_DAYS)


def recent_enough(result):
    d = parse_date(result.get("date"))

    if not d:
        d = parse_date(result.get("deadline"))

    if not d:
        return True

    return d >= cutoff_date()


def flatten_values(value):
    output = []

    if isinstance(value, dict):
        for key, item in value.items():
            output.extend(flatten_values(item))

    elif isinstance(value, list):
        for item in value:
            output.extend(flatten_values(item))

    elif value is not None:
        output.append(str(value))

    return output


def recursive_find(data, fragments):
    if not isinstance(data, (dict, list)):
        return ""

    fragments = [
        normalize_for_search(fragment)
        for fragment in fragments
    ]

    if isinstance(data, dict):
        for key, value in data.items():
            key_norm = normalize_for_search(key)

            if any(fragment in key_norm for fragment in fragments):
                if not isinstance(value, (dict, list)):
                    return str(value)

            found = recursive_find(value, fragments)

            if found:
                return found

    elif isinstance(data, list):
        for item in data:
            found = recursive_find(item, fragments)

            if found:
                return found

    return ""


def first_value(data, keys):
    if not isinstance(data, dict):
        return ""

    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]

    return ""


def country_from_text(*values):
    text = normalize_for_search(" ".join(
        str(value)
        for value in values
        if value
    ))

    for code, name in COUNTRY_MAP.items():
        name_norm = normalize_for_search(name)

        if name_norm and name_norm in text:
            return code

        if code.lower() in text.split():
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
            return COUNTRY_MAP.get(iso2, "")

    return ""


def region_from_country(code):
    if not code:
        return "Global"

    code = str(code).upper().strip()

    for region, countries in REGION_COUNTRIES.items():
        if code in countries:
            return region

    return "Global"


def cpv_values(value):
    values = flatten_values(value)

    result = []

    for item in values:
        matches = re.findall(r"\b\d{8}\b", item)

        for match in matches:
            result.append(match)

    return list(dict.fromkeys(result))


def has_direct_archaeology(title, description, buyer="", cpvs=None):
    text = normalize_for_search(
        f"{title} {description}"
    )

    return any(
        normalize_for_search(term) in text
        for term in DIRECT_TERMS
    )


def has_heritage(title, description):
    text = normalize_for_search(
        f"{title} {description}"
    )

    return any(
        normalize_for_search(term) in text
        for term in HERITAGE_TERMS
    )


def has_major_project(title, description):
    text = normalize_for_search(
        f"{title} {description}"
    )

    return any(
        normalize_for_search(term) in text
        for term in MAJOR_PROJECT_TERMS
    )


def classify_result(
    title,
    description,
    buyer="",
    cpvs=None,
    search_mode="direct",
):
    title = normalize_text(title)
    description = normalize_text(description)
    buyer = normalize_text(buyer)

    cpvs = cpvs or []

    direct = has_direct_archaeology(
        title,
        description,
        buyer,
        cpvs,
    )

    heritage = has_heritage(
        title,
        description,
    )

    major_project = has_major_project(
        title,
        description,
    )

    combined = normalize_for_search(
        f"{title} {description}"
    )

    archaeology_cpv = any(
        cpv in ARCHAEOLOGY_CPVS
        for cpv in cpvs
    )

    support_only = any(
        term in combined
        for term in SUPPORT_EXCLUSIONS
    )

    # Regra principal:
    # CPV sozinho nunca transforma um concurso em arqueologia.
    if search_mode == "direct":
        if direct:
            if support_only and not direct:
                return "Outro"

            return "Arqueologia direta"

        return "Outro"

    if search_mode == "heritage":
        if direct:
            return "Arqueologia direta"

        if heritage and major_project:
            return "Património / grandes projetos"

        if heritage:
            return "Património cultural"

        return "Outro"

    if direct:
        return "Arqueologia direta"

    if archaeology_cpv and (heritage or major_project):
        return "Arqueologia / património"

    if heritage and major_project:
        return "Património / grandes projetos"

    if heritage:
        return "Património cultural"

    return "Outro"


def make_result(
    title,
    description,
    buyer,
    country,
    source,
    url="",
    published=None,
    deadline=None,
    cpvs=None,
    search_mode="direct",
):
    title = repair_mojibake(normalize_text(title))
    description = repair_mojibake(normalize_text(description))
    buyer = repair_mojibake(normalize_text(buyer))

    cpvs = cpvs or []

    classification = classify_result(
        title,
        description,
        buyer,
        cpvs,
        search_mode,
    )

    if classification == "Outro":
        return None

    country = country or ""

    country_display = country_name(country)

    if not country_display:
        country_display = country

    region = region_from_country(country)

    return {
        "title": title or "Sem título",
        "description": description,
        "buyer": buyer,
        "country": country_display,
        "country_code": country,
        "region": region,
        "source": source,
        "url": url or "",
        "date": published or "",
        "deadline": deadline or "",
        "cpv": cpvs,
        "classification": classification,
        "score": 100 if classification == "Arqueologia direta" else 70,
    }


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
]


def query_ted(term, diagnostics=None, search_mode="direct"):
    results = []

    params = {
        "q": f'FT~"{term}"',
        "page": 1,
        "limit": PAGE_SIZE,
        "fields": ",".join(TED_FIELDS),
    }

    try:
        response = requests.get(
            TED_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

        if diagnostics is not None:
            diagnostics.append({
                "source": "TED — Europa",
                "term": term,
                "status_code": response.status_code,
            })

        if response.status_code != 200:
            return results

        data = response.json()

        notices = data.get("notices", [])

        if isinstance(notices, dict):
            notices = list(notices.values())

        if not isinstance(notices, list):
            return results

        for notice in notices:
            if not isinstance(notice, dict):
                continue

            title = first_value(
                notice,
                [
                    "notice-title",
                    "notice-title-lot",
                    "title",
                ],
            )

            description = first_value(
                notice,
                [
                    "description-proc",
                    "description-lot",
                    "description",
                ],
            )

            buyer = first_value(
                notice,
                [
                    "buyer-name",
                    "buyer",
                ],
            )

            country = first_value(
                notice,
                [
                    "buyer-country",
                    "country",
                ],
            )

            cpvs = cpv_values(
                first_value(
                    notice,
                    [
                        "classification-cpv",
                        "cpv",
                    ],
                )
            )

            published = first_value(
                notice,
                [
                    "publication-date",
                    "publicationDate",
                ],
            )

            deadline = first_value(
                notice,
                [
                    "deadline-date-lot",
                    "deadline-receipt-tender-date-lot",
                    "deadline-receipt-request-date-lot",
                ],
            )

            publication_number = first_value(
                notice,
                [
                    "publication-number",
                ],
            )

            url = ""

            if publication_number:
                url = (
                    "https://ted.europa.eu/en/notice/"
                    + str(publication_number)
                )

            result = make_result(
                title,
                description,
                buyer,
                country,
                "TED — Europa",
                url,
                published,
                deadline,
                cpvs,
                search_mode,
            )

            if result and recent_enough(result):
                results.append(result)

    except Exception as exc:
        if diagnostics is not None:
            diagnostics.append({
                "source": "TED — Europa",
                "term": term,
                "error": str(exc),
            })

    return results


# ============================================================
# WORLD BANK
# ============================================================

def query_world_bank(
    term,
    diagnostics=None,
    search_mode="direct",
):
    results = []

    params = {
        "qterm": term,
        "rows": PAGE_SIZE,
        "format": "json",
    }

    try:
        response = requests.get(
            WORLD_BANK_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

        if diagnostics is not None:
            diagnostics.append({
                "source": "World Bank Procurement",
                "term": term,
                "status_code": response.status_code,
            })

        if response.status_code != 200:
            return results

        data = response.json()

        rows = []

        if isinstance(data, dict):
            for key in [
                "procnotices",
                "notices",
                "results",
                "documents",
            ]:
                value = data.get(key)

                if isinstance(value, list):
                    rows.extend(value)

                elif isinstance(value, dict):
                    rows.extend(value.values())

        if not rows and isinstance(data, list):
            rows = data

        for row in rows:
            if not isinstance(row, dict):
                continue

            title = first_value(
                row,
                [
                    "bid_description",
                    "procurement_name",
                    "notice_title",
                    "title",
                    "project_name",
                ],
            )

            description = first_value(
                row,
                [
                    "description",
                    "bid_description",
                    "procurement_description",
                    "notice_description",
                ],
            )

            buyer = first_value(
                row,
                [
                    "borrower",
                    "buyer",
                    "agency",
                    "procuring_entity",
                    "client",
                    "project_name",
                ],
            )

            country = first_value(
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
                ],
            )

            if not country:
                country = recursive_find(
                    row,
                    [
                        "country",
                        "borrower_country",
                    ],
                )

            if not country:
                country = country_from_text(
                    buyer,
                    title,
                    description,
                )

            if country:
                country = str(country).upper().strip()

                if len(country) == 3:
                    reverse = {
                        value: key
                        for key, value in ISO3_MAP.items()
                    }
                    country = reverse.get(country, country)

            cpvs = cpv_values(
                first_value(
                    row,
                    [
                        "cpv",
                        "classification-cpv",
                        "classification",
                    ],
                )
            )

            published = first_value(
                row,
                [
                    "publication_date",
                    "publicationDate",
                    "publicationdate",
                    "notice_date",
                    "noticeDate",
                    "notice_publication_date",
                    "notice_publicationdate",
                    "procurement_notice_date",
                    "bid_publication_date",
                    "date",
                    "published_date",
                    "publishedDate",
                    "date_published",
                    "datepublished",
                    "posting_date",
                    "posted_date",
                    "post_date",
                    "postdate",
                    "created_date",
                    "createdDate",
                    "invitation_date",
                    "invitationdate",
                    "published_on",
                ],
            )

            if not published:
                published = recursive_find(
                    row,
                    [
                        "publication",
                        "published",
                        "posting",
                        "posted",
                        "invitation",
                    ],
                )

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
                    "proposal_deadline",
                    "proposalDeadline",
                    "tender_deadline",
                    "tenderDeadline",
                    "submissionDate",
                ],
            )

            if not deadline:
                deadline = recursive_find(
                    row,
                    [
                        "deadline",
                        "closing",
                        "submission",
                    ],
                )

            url = first_value(
                row,
                [
                    "url",
                    "notice_url",
                    "web_url",
                    "procurement_url",
                    "link",
                ],
            )

            result = make_result(
                title,
                description,
                buyer,
                country,
                "World Bank Procurement",
                url,
                published,
                deadline,
                cpvs,
                search_mode,
            )

            if result and recent_enough(result):
                results.append(result)

    except Exception as exc:
        if diagnostics is not None:
            diagnostics.append({
                "source": "World Bank Procurement",
                "term": term,
                "error": str(exc),
            })

    return results


# ============================================================
# SECOP II — COLÔMBIA
# ============================================================

def query_secop(
    term,
    diagnostics=None,
    search_mode="direct",
):
    results = []

    params = {
        "$limit": 1000,
        "$q": term,
    }

    try:
        response = requests.get(
            SECOP_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

        if diagnostics is not None:
            diagnostics.append({
                "source": "SECOP II — Colômbia",
                "term": term,
                "status_code": response.status_code,
            })

        if response.status_code != 200:
            return results

        rows = response.json()

        if not isinstance(rows, list):
            return results

        for row in rows:
            if not isinstance(row, dict):
                continue

            title = first_value(
                row,
                [
                    "nombre_del_procedimiento",
                    "objeto_del_contrato",
                    "descripcion_del_proceso",
                    "title",
                ],
            )

            description = first_value(
                row,
                [
                    "descripcion_del_proceso",
                    "objeto_del_contrato",
                ],
            )

            search_text = normalize_for_search(
                f"{title} {description}"
            )

            if normalize_for_search(term) not in search_text:
                continue

            buyer = first_value(
                row,
                [
                    "entidad",
                    "nombre_entidad",
                ],
            )

            cpvs = cpv_values(
                first_value(
                    row,
                    [
                        "codigo_principal_de_producto",
                        "codigo_unspsc",
                    ],
                )
            )

            published = first_value(
                row,
                [
                    "fecha_de_publicacion",
                    "fecha_publicacion",
                    "fecha_de_publicacion_del_proceso",
                ],
            )

            deadline = first_value(
                row,
                [
                    "fecha_de_recepcion_de_ofertas",
                    "fecha_de_cierre",
                ],
            )

            url = first_value(
                row,
                [
                    "urlproceso",
                    "url",
                    "link",
                ],
            )

            result = make_result(
                title,
                description,
                buyer,
                "CO",
                "SECOP II — Colômbia",
                url,
                published,
                deadline,
                cpvs,
                search_mode,
            )

            if result and recent_enough(result):
                results.append(result)

    except Exception as exc:
        if diagnostics is not None:
            diagnostics.append({
                "source": "SECOP II — Colômbia",
                "term": term,
                "error": str(exc),
            })

    return results


# ============================================================
# PNCP — BRASIL
# ============================================================

BRAZIL_MODALITIES = [
    4,   # Concorrência internacional
    5,   # Pregão
    6,   # Dispensa
    7,   # Inexigibilidade
    12,  # Credenciamento
]

BRAZIL_MAX_PAGES = 1


def brazil_date(value):
    if isinstance(value, datetime):
        value = value.date()

    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")

    return str(value)


def query_brazil(
    term,
    diagnostics=None,
    search_mode="direct",
):
    results = []

    start = cutoff_date()
    end = date.today()

    for modality in BRAZIL_MODALITIES:
        for page in range(1, BRAZIL_MAX_PAGES + 1):

            params = {
                "dataPublicacaoPncpInicial": brazil_date(start),
                "dataPublicacaoPncpFinal": brazil_date(end),
                "codigoModalidade": modality,
                "pagina": page,
                "tamanhoPagina": 50,
            }

            try:
                response = requests.get(
                    BRAZIL_URL,
                    params=params,
                    timeout=REQUEST_TIMEOUT,
                )

                if diagnostics is not None:
                    diagnostics.append({
                        "source": "PNCP — Brasil",
                        "term": term,
                        "modality": modality,
                        "page": page,
                        "status_code": response.status_code,
                    })

                if response.status_code != 200:
                    continue

                data = response.json()

                rows = []

                if isinstance(data, dict):
                    for key in [
                        "resultado",
                        "resultados",
                        "data",
                        "items",
                    ]:
                        value = data.get(key)

                        if isinstance(value, list):
                            rows.extend(value)

                elif isinstance(data, list):
                    rows = data

                for row in rows:
                    if not isinstance(row, dict):
                        continue

                    title = first_value(
                        row,
                        [
                            "objetoCompra",
                            "objeto",
                            "descricao",
                            "titulo",
                        ],
                    )

                    description = first_value(
                        row,
                        [
                            "objetoCompra",
                            "descricao",
                        ],
                    )

                    text = normalize_for_search(
                        f"{title} {description}"
                    )

                    if normalize_for_search(term) not in text:
                        continue

                    buyer = first_value(
                        row,
                        [
                            "orgaoEntidadeRazaoSocial",
                            "unidadeOrgaoNomeUnidade",
                            "razaoSocial",
                        ],
                    )

                    state = first_value(
                        row,
                        [
                            "unidadeOrgaoUfSigla",
                            "uf",
                        ],
                    )

                    published = first_value(
                        row,
                        [
                            "dataPublicacaoPncp",
                            "dataInclusaoPncp",
                            "dataAtualizacaoPncp",
                        ],
                    )

                    deadline = first_value(
                        row,
                        [
                            "dataEncerramentoPropostaPncp",
                            "dataAberturaPropostaPncp",
                        ],
                    )

                    number = first_value(
                        row,
                        [
                            "numeroControlePNCP",
                        ],
                    )

                    url = ""

                    if number:
                        url = (
                            "https://pncp.gov.br/app/"
                            "editais/"
                            + str(number)
                        )

                    result = make_result(
                        title,
                        description,
                        buyer,
                        "BR",
                        "PNCP — Brasil",
                        url,
                        published,
                        deadline,
                        [],
                        search_mode,
                    )

                    if result and state:
                        result["state"] = state

                    if result and recent_enough(result):
                        results.append(result)

            except Exception as exc:
                if diagnostics is not None:
                    diagnostics.append({
                        "source": "PNCP — Brasil",
                        "term": term,
                        "modality": modality,
                        "page": page,
                        "error": str(exc),
                    })

    return results


# ============================================================
# PESQUISA AUTOMÁTICA
# ============================================================

def automatic_search(query, diagnostics):
    query_norm = normalize_for_search(query)

    if query_norm in {
        "",
        "arqueologia",
        "archaeology",
        "archaeological",
    }:
        mode = "direct"

        jobs = []

        for term in AUTOMATIC_TERMS_TED:
            jobs.append((
                "TED — Europa",
                query_ted,
                term,
                mode,
            ))

        for term in AUTOMATIC_TERMS_WORLD_BANK:
            jobs.append((
                "World Bank Procurement",
                query_world_bank,
                term,
                mode,
            ))

        for term in AUTOMATIC_TERMS_SECOP:
            jobs.append((
                "SECOP II — Colômbia",
                query_secop,
                term,
                mode,
            ))

        for term in [
            "archaeology",
            "archaeological",
            "archaeologist",
            "arqueologia",
            "arqueológico",
        ]:
            jobs.append((
                "PNCP — Brasil",
                query_brazil,
                term,
                mode,
            ))

    else:
        mode = "direct"

        jobs = [
            (
                "TED — Europa",
                query_ted,
                query,
                mode,
            ),
            (
                "World Bank Procurement",
                query_world_bank,
                query,
                mode,
            ),
            (
                "SECOP II — Colômbia",
                query_secop,
                query,
                mode,
            ),
            (
                "PNCP — Brasil",
                query_brazil,
                query,
                mode,
            ),
        ]

    results = []

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = []

        for source_name, function, term, mode in jobs:
            futures.append(
                executor.submit(
                    function,
                    term,
                    diagnostics,
                    mode,
                )
            )

        for future in as_completed(futures):
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

    if country:
        country_norm = normalize_for_search(country)

        filtered = [
            result
            for result in filtered
            if (
                country_norm
                in normalize_for_search(
                    result.get("country", "")
                )
                or country.upper()
                == result.get("country_code", "").upper()
            )
        ]

    if region:
        region_norm = normalize_for_search(region)

        filtered = [
            result
            for result in filtered
            if normalize_for_search(
                result.get("region", "")
            ) == region_norm
        ]

    return filtered


def deduplicate_results(results):
    seen = set()
    output = []

    for result in results:
        key = (
            normalize_for_search(
                result.get("title", "")
            ),
            normalize_for_search(
                result.get("buyer", "")
            ),
            normalize_for_search(
                result.get("source", "")
            ),
        )

        if key in seen:
            continue

        seen.add(key)
        output.append(result)

    return output


# ============================================================
# ROTAS
# ============================================================

@app.get("/")
def home():
    return FileResponse(
        BASE_DIR / "index.html"
    )


@app.get("/app.js")
def javascript():
    return FileResponse(
        BASE_DIR / "App.js",
        media_type="application/javascript",
    )


@app.get("/manifest.json")
def manifest():
    return FileResponse(
        BASE_DIR / "manifest.json",
        media_type="application/manifest+json",
    )


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
        "version": "2.5.1",
        "period_days": PERIOD_DAYS,
        "sources": len(SOURCES),
        "automatic_sources": len(
            automatic_sources
        ),
        "automatic_source_names": automatic_sources,
        "date": date.today().isoformat(),
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
    started = datetime.now()

    diagnostics = []

    try:
        search_mode, results = automatic_search(
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

        results.sort(
            key=lambda item: (
                -int(item.get("score", 0)),
                item.get("date", ""),
            ),
            reverse=False,
        )

        source_counts = {}

        for result in results:
            source = result.get(
                "source",
                "Desconhecida",
            )

            source_counts[source] = (
                source_counts.get(source, 0)
                + 1
            )

        regions = {}

        for result in results:
            region_name = result.get(
                "region",
                "Global",
            )

            regions[region_name] = (
                regions.get(region_name, 0)
                + 1
            )

        elapsed = (
            datetime.now() - started
        ).total_seconds()

        return {
            "ok": True,
            "query": q,
            "search_mode": search_mode,
            "automatic_mode": True,
            "country": country,
            "region": region,
            "results": results,
            "count": len(results),
            "source_counts": source_counts,
            "regions": regions,
            "diagnostics": diagnostics,
            "searched_at": datetime.now().isoformat(),
            "period_days": PERIOD_DAYS,
            "cutoff_date": cutoff_date().isoformat(),
            "elapsed": round(elapsed, 2),
        }

    except Exception as exc:
        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": str(exc),
                "query": q,
                "diagnostics": diagnostics,
            },
        )


# ============================================================
# TESTES TED
# ============================================================

@app.get("/api/test-ted-country")
def test_ted_country(
    country: str = Query(
        default="MAR"
    ),
    term: str = Query(
        default="archaeology"
    ),
):
    diagnostics = []

    query = (
        f'FT~"{term}" '
        f'AND buyer-country={country.upper()}'
    )

    try:
        response = requests.get(
            TED_URL,
            params={
                "q": query,
                "page": 1,
                "limit": 10,
                "fields": ",".join(
                    TED_FIELDS
                ),
            },
            timeout=REQUEST_TIMEOUT,
        )

        data = {}

        try:
            data = response.json()
        except Exception:
            data = {
                "text": response.text[:2000]
            }

        return {
            "ok": response.status_code == 200,
            "status_code": response.status_code,
            "query": query,
            "response": data,
        }

    except Exception as exc:
        return {
            "ok": False,
            "query": query,
            "error": str(exc),
        }


@app.get("/api/test-ted-minimal")
def test_ted_minimal(
    term: str = Query(
        default="archaeology"
    ),
):
    query = f'FT~"{term}"'

    try:
        response = requests.get(
            TED_URL,
            params={
                "q": query,
                "page": 1,
                "limit": 10,
            },
            timeout=REQUEST_TIMEOUT,
        )

        try:
            data = response.json()
        except Exception:
            data = {
                "text": response.text[:2000]
            }

        return {
            "ok": response.status_code == 200,
            "status_code": response.status_code,
            "query": query,
            "response": data,
        }

    except Exception as exc:
        return {
            "ok": False,
            "query": query,
            "error": str(exc),
        }
