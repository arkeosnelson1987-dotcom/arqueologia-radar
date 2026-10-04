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
# ARQUEOLOGIA RADAR - v2.5 GLOBAL
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Arqueologia Radar",
    version="2.5"
)

REQUEST_TIMEOUT = 30
PERIOD_DAYS = 365
PAGE_SIZE = 100

# ============================================================
# ENDPOINTS
# ============================================================

TED_URL = "https://api.ted.europa.eu/v3/notices/search"

WORLD_BANK_URL = (
    "https://search.worldbank.org/api/v2/procnotices"
)

SECOP_URL = (
    "https://www.datos.gov.co/resource/p6dx-8zbt.json"
)

# PNCP / Brasil
BRAZIL_URL = (
    "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
)

# ============================================================
# FONTES
# ============================================================

TED_SOURCE = "TED " + chr(0x2014) + " Europa"
WORLD_BANK_SOURCE = "World Bank Procurement"
SECOP_SOURCE = "SECOP II " + chr(0x2014) + " Colombia"
BRAZIL_SOURCE = "Brasil " + chr(0x2014) + " PNCP"

SOUTH_AFRICA_SOURCE = "South Africa eTenders " + chr(0x2014) + " OCDS"

SOURCES = [
    {"name": TED_SOURCE, "region": "Europa", "automatic": True},
    {"name": WORLD_BANK_SOURCE, "region": "Global", "automatic": True},
    {"name": SECOP_SOURCE, "region": "América", "automatic": True},
    {"name": BRAZIL_SOURCE, "region": "América", "automatic": True},

    {"name": SOUTH_AFRICA_SOURCE, "region": "África", "automatic": False},

    {"name": "AfDB " + chr(0x2014) + " African Development Bank", "region": "África", "automatic": False},
    {"name": "SAM.gov " + chr(0x2014) + " Estados Unidos", "region": "América", "automatic": False},
    {"name": "BASE " + chr(0x2014) + " Portugal", "region": "Europa", "automatic": False},
    {"name": "Contratación del Estado " + chr(0x2014) + " Espanha", "region": "Europa", "automatic": False},
    {"name": "UNDB " + chr(0x2014) + " United Nations Development Business", "region": "Global", "automatic": False},
    {"name": "UNGM " + chr(0x2014) + " United Nations Global Marketplace", "region": "Global", "automatic": False},
    {"name": "EBRD " + chr(0x2014) + " European Bank for Reconstruction and Development", "region": "Europa/Ásia", "automatic": False},
    {"name": "EIB " + chr(0x2014) + " European Investment Bank", "region": "Europa", "automatic": False},
    {"name": "Oman Tender Board", "region": "Ásia", "automatic": False},
    {"name": "Etimad " + chr(0x2014) + " Saudi Arabia", "region": "Ásia", "automatic": False},
    {"name": "UAE Federal Procurement", "region": "Ásia", "automatic": False},
    {"name": "Qatar Government Procurement", "region": "Ásia", "automatic": False},
    {"name": "Maroc Marchés Publics", "region": "África", "automatic": False},
    {"name": "Uganda eGP", "region": "África", "automatic": False},
    {"name": "Kenya Public Procurement", "region": "África", "automatic": False},
    {"name": "Tanzania PPRA", "region": "África", "automatic": False},
    {"name": "Mozambique Contratação Pública", "region": "África", "automatic": False},
    {"name": "ChileCompra", "region": "América", "automatic": False},
    {"name": "Brasil Compras.gov.br", "region": "América", "automatic": True},
    {"name": "IDB " + chr(0x2014) + " Inter-American Development Bank", "region": "América", "automatic": False},
    {"name": "ADB " + chr(0x2014) + " Asian Development Bank", "region": "Ásia", "automatic": False},
    {"name": "AusTender", "region": "Oceânia", "automatic": False},
    {"name": "NZ GETS", "region": "Oceânia", "automatic": False},
    {"name": "Red Eléctrica / Redeia", "region": "Europa", "automatic": False},
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
    "45112450"
}

# ============================================================
# TERMOS DIRECTOS DE ARQUEOLOGIA
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
    "archaeological works",

    # Francês
    "archeologie",
    "archeologique",
    "archeologue",
    "fouilles archeologiques",

    # Português
    "arqueologia",
    "arqueologico",
    "arqueologica",
    "arqueologo",
    "arqueologa",
    "escavacao arqueologica",
    "acompanhamento arqueologico",
    "monitorizacao arqueologica",
    "monitoramento arqueologico",
    "prospeccao arqueologica",
    "prospecao arqueologica",
    "avaliacao arqueologica",
    "trabalhos arqueologicos",
    "servicos arqueologicos",
    "consultoria arqueologica",
    "consultor arqueologico",
    "arqueologia preventiva",
    "arqueologo coordenador",
    "patrimonio arqueologico",

    # Espanhol
    "arqueologia",
    "arqueologia preventiva",
    "arqueologo",
    "arqueologa",
    "arqueologico",
    "arqueologica",
    "excavacion arqueologica",
    "excavaciones arqueologicas",
    "seguimiento arqueologico",
    "monitoreo arqueologico",
    "prospeccion arqueologica",
    "prospeccion arqueologica",
    "supervision arqueologica",
    "servicios arqueologicos",
    "evaluacion arqueologica",
    "patrimonio arqueologico",

    # Alemão
    "archaologie",
    "archaologisch",
    "archaologe",

    # Neerlandês
    "archeologie",
    "archeologisch",
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
    "heritage conservation",
    "heritage management plan",
    "cultural property",
    "cultural resources",

    "patrimonio cultural",
    "patrimonio arqueologico",
    "avaliacao patrimonial",
    "impacte patrimonial",
    "impacto patrimonial",

    "patrimoine culturel",
    "patrimoine archeologique",
    "patrimoine historique",

    "kulturerbe",
    "archaeologisches erbe",
]

# ============================================================
# GRANDES PROJECTOS
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

    "ferrovia",
    "ferroviaria",
    "estrada",
    "autoestrada",
    "rodovia",
    "mina",
    "mineracao",
    "oleoduto",
    "gasoduto",
    "aeroporto",
    "porto",
    "barragem",
    "hidrica",
    "energia",
    "linha eletrica",
    "corredor",
    "metro",
    "infraestrutura",
    "construcao",

    "ferrocarril",
    "carretera",
    "autopista",
    "mineria",
    "oleoducto",
    "gasoducto",
    "aeropuerto",
    "puerto",
    "presa",
    "energia",
    "infraestructura",
    "construccion",
]

# ============================================================
# TERMOS DE SUPORTE QUE NÃO DEVEM SER CONFUNDIDOS COM ARQUEOLOGIA
# ============================================================

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
    "communications",
    "public relations",
    "marketing",
    "media coordinator",
    "signboards",
    "office supplies",
    "computer equipment",
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

    "archeologie",
    "archeologique",
    "archeologue",

    "arqueologia",
    "arqueologico",
    "arqueologica",
    "arqueologo",
    "escavacao arqueologica",
    "acompanhamento arqueologico",
    "monitorizacao arqueologica",
    "prospeccao arqueologica",

    "archaologie",
    "archaologisch",
]

AUTOMATIC_TERMS_WORLD_BANK = [
    "archaeology",
    "archaeological",
    "archaeologist",
    "archaeological excavation",
    "archaeological monitoring",
    "archaeological survey",
    "archaeological assessment",
    "archaeological fieldwork",
    "archaeological watching brief",
    "archaeological heritage",
    "heritage assessment",
    "heritage impact assessment",
    "cultural heritage",
    "historic environment",
    "chance finds",
    "heritage management",

    "archaeology railway",
    "archaeology road",
    "archaeology highway",
    "archaeology mine",
    "archaeology mining",
    "archaeology pipeline",
    "archaeology airport",
    "archaeology port",
    "archaeology dam",
    "archaeology hydropower",
    "archaeology energy",
    "archaeology construction",

    "arqueologia",
    "arqueologia preventiva",
    "arqueologico",
    "arqueologica",
    "arqueologo",
    "escavacao arqueologica",
    "acompanhamento arqueologico",
    "monitoramento arqueologico",
    "prospeccao arqueologica",
    "patrimonio arqueologico",

    "arqueologia carretera",
    "arqueologia carretera",
    "arqueologia ferrocarril",
    "arqueologia mineria",
    "arqueologia infraestructura",
]

AUTOMATIC_TERMS_SECOP = [
    "arqueologia",
    "arqueologia preventiva",
    "arqueologo",
    "arqueologa",
    "arqueologico",
    "arqueologica",
    "excavacion arqueologica",
    "excavaciones arqueologicas",
    "seguimiento arqueologico",
    "monitoreo arqueologico",
    "prospeccion arqueologica",
    "servicios arqueologicos",
    "evaluacion arqueologica",
    "patrimonio arqueologico",
    "archaeology",
    "archaeological",
    "archaeologist",
]

AUTOMATIC_TERMS_BRAZIL = [
    "arqueologia",
    "arqueologico",
    "arqueologica",
    "arqueologo",
    "arqueologa",
    "escavacao arqueologica",
    "escavacoes arqueologicas",
    "acompanhamento arqueologico",
    "monitoramento arqueologico",
    "prospeccao arqueologica",
    "avaliacao arqueologica",
    "servicos arqueologicos",
    "arqueologia preventiva",
    "patrimonio arqueologico",
    "gestao do patrimonio arqueologico",
    "programa de gestao do patrimonio arqueologico",
]

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
    "RS": "Sérvia",
    "BA": "Bósnia e Herzegovina",
    "ME": "Montenegro",
    "MK": "Macedónia do Norte",
    "AL": "Albânia",
    "XK": "Kosovo",
    "MD": "Moldávia",
    "UA": "Ucrânia",
    "BY": "Bielorrússia",
    "GE": "Geórgia",
    "AM": "Arménia",
    "AZ": "Azerbaijão",

    # África
    "MA": "Marrocos",
    "DZ": "Argélia",
    "TN": "Tunísia",
    "LY": "Líbia",
    "EG": "Egipto",
    "SD": "Sudão",
    "SS": "Sudão do Sul",
    "ET": "Etiópia",
    "ER": "Eritreia",
    "DJ": "Djibuti",
    "SO": "Somália",
    "KE": "Quénia",
    "UG": "Uganda",
    "TZ": "Tanzânia",
    "RW": "Ruanda",
    "BI": "Burundi",
    "CD": "República Democrática do Congo",
    "CG": "República do Congo",
    "GA": "Gabão",
    "CM": "Camarões",
    "CF": "República Centro-Africana",
    "TD": "Chade",
    "NG": "Nigéria",
    "GH": "Gana",
    "CI": "Costa do Marfim",
    "SN": "Senegal",
    "GM": "Gâmbia",
    "GN": "Guiné",
    "SL": "Serra Leoa",
    "LR": "Libéria",
    "BF": "Burkina Faso",
    "ML": "Mali",
    "NE": "Níger",
    "MR": "Mauritânia",
    "BJ": "Benim",
    "TG": "Togo",
    "GH": "Gana",
    "MZ": "Moçambique",
    "ZA": "África do Sul",
    "ZW": "Zimbabué",
    "ZM": "Zâmbia",
    "MW": "Malawi",
    "BW": "Botswana",
    "NA": "Namíbia",
    "AO": "Angola",
    "SZ": "Eswatini",
    "LS": "Lesoto",
    "MG": "Madagáscar",
    "MU": "Maurícia",
    "SC": "Seicheles",

    # América
    "US": "Estados Unidos",
    "CA": "Canadá",
    "MX": "México",
    "GT": "Guatemala",
    "BZ": "Belize",
    "HN": "Honduras",
    "SV": "El Salvador",
    "NI": "Nicarágua",
    "CR": "Costa Rica",
    "PA": "Panamá",
    "CU": "Cuba",
    "DO": "República Dominicana",
    "JM": "Jamaica",
    "HT": "Haiti",
    "CO": "Colômbia",
    "VE": "Venezuela",
    "GY": "Guiana",
    "SR": "Suriname",
    "GF": "Guiana Francesa",
    "BR": "Brasil",
    "EC": "Equador",
    "PE": "Peru",
    "BO": "Bolívia",
    "PY": "Paraguai",
    "CL": "Chile",
    "AR": "Argentina",
    "UY": "Uruguai",

    # Ásia / Médio Oriente
    "TR": "Turquia",
    "CY": "Chipre",
    "SY": "Síria",
    "LB": "Líbano",
    "IL": "Israel",
    "JO": "Jordânia",
    "IQ": "Iraque",
    "IR": "Irão",
    "SA": "Arábia Saudita",
    "AE": "Emirados Árabes Unidos",
    "QA": "Qatar",
    "BH": "Bahrein",
    "KW": "Kuwait",
    "OM": "Omã",
    "YE": "Iémen",
    "AF": "Afeganistão",
    "PK": "Paquistão",
    "IN": "Índia",
    "NP": "Nepal",
    "BD": "Bangladesh",
    "LK": "Sri Lanka",
    "CN": "China",
    "JP": "Japão",
    "KR": "Coreia do Sul",
    "KP": "Coreia do Norte",
    "MN": "Mongólia",
    "KZ": "Cazaquistão",
    "UZ": "Uzbequistão",
    "TM": "Turquemenistão",
    "KG": "Quirguistão",
    "TJ": "Tajiquistão",
    "AZ": "Azerbaijão",
    "AM": "Arménia",
    "GE": "Geórgia",
    "ID": "Indonésia",
    "MY": "Malásia",
    "TH": "Tailândia",
    "VN": "Vietname",
    "KH": "Camboja",
    "LA": "Laos",
    "MM": "Myanmar",
    "PH": "Filipinas",

    # Oceânia
    "AU": "Austrália",
    "NZ": "Nova Zelândia",
    "PG": "Papua-Nova Guiné",
    "FJ": "Fiji",
    "SB": "Ilhas Salomão",
    "VU": "Vanuatu",
    "WS": "Samoa",
    "TO": "Tonga",
]

ISO3_MAP = {
    "PRT": "PT", "ESP": "ES", "FRA": "FR", "DEU": "DE",
    "ITA": "IT", "BEL": "BE", "NLD": "NL", "LUX": "LU",
    "IRL": "IE", "AUT": "AT", "POL": "PL", "CZE": "CZ",
    "SVK": "SK", "HUN": "HU", "ROU": "RO", "BGR": "BG",
    "HRV": "HR", "SVN": "SI", "SWE": "SE", "FIN": "FI",
    "DNK": "DK", "EST": "EE", "LVA": "LV", "LTU": "LT",
    "GRC": "GR", "CYP": "CY", "MLT": "MT", "NOR": "NO",
    "ISL": "IS", "CHE": "CH", "GBR": "GB", "SRB": "RS",

    "MAR": "MA", "DZA": "DZ", "TUN": "TN", "EGY": "EG",
    "ZAF": "ZA", "KEN": "KE", "UGA": "UG", "TZA": "TZ",
    "MOZ": "MZ", "NGA": "NG", "GHA": "GH", "ETH": "ET",
    "SEN": "SN", "CIV": "CI", "MLI": "ML", "NER": "NE",
    "BFA": "BF", "CMR": "CM", "COD": "CD", "COG": "CG",
    "AGO": "AO", "NAM": "NA", "BWA": "BW", "ZMB": "ZM",
    "ZWE": "ZW", "MWI": "MW", "MDG": "MG",

    "USA": "US", "CAN": "CA", "MEX": "MX", "COL": "CO",
    "BRA": "BR", "CHL": "CL", "PER": "PE", "ARG": "AR",
    "URY": "UY", "PRY": "PY", "BOL": "BO", "ECU": "EC",
    "CRI": "CR", "PAN": "PA", "GTM": "GT",

    "SAU": "SA", "ARE": "AE", "QAT": "QA", "OMN": "OM",
    "JOR": "JO", "ISR": "IL", "TUR": "TR", "IND": "IN",
    "PAK": "PK", "BGD": "BD", "LKA": "LK", "CHN": "CN",
    "JPN": "JP", "KOR": "KR", "IDN": "ID", "MYS": "MY",
    "THA": "TH", "VNM": "VN", "PHL": "PH",

    "AUS": "AU", "NZL": "NZ", "PNG": "PG", "FJI": "FJ",
]

REGION_COUNTRIES = {
    "Europa": {
        "PT","ES","FR","DE","IT","BE","NL","LU","IE","AT","PL","CZ",
        "SK","HU","RO","BG","HR","SI","SE","FI","DK","EE","LV","LT",
        "GR","CY","MT","NO","IS","CH","GB","RS","BA","ME","MK","AL",
        "XK","MD","UA","BY","GE","AM","AZ"
    },

    "África": {
        "MA","DZ","TN","LY","EG","SD","SS","ET","ER","DJ","SO","KE",
        "UG","TZ","RW","BI","CD","CG","GA","CM","CF","TD","NG","GH",
        "CI","SN","GM","GN","SL","LR","BF","ML","NE","MR","BJ","TG",
        "MZ","ZA","ZW","ZM","MW","BW","NA","AO","SZ","LS","MG","MU","SC"
    },

    "América": {
        "US","CA","MX","GT","BZ","HN","SV","NI","CR","PA","CU","DO",
        "JM","HT","CO","VE","GY","SR","GF","BR","EC","PE","BO","PY",
        "CL","AR","UY"
    },

    "Ásia": {
        "TR","SY","LB","IL","JO","IQ","IR","SA","AE","QA","BH","KW",
        "OM","YE","AF","PK","IN","NP","BD","LK","CN","JP","KR","KP",
        "MN","KZ","UZ","TM","KG","TJ","AZ","AM","GE","ID","MY","TH",
        "VN","KH","LA","MM","PH","CY"
    },

    "Oceânia": {
        "AU","NZ","PG","FJ","SB","VU","WS","TO"
    }
}

COUNTRY_TEXT_PATTERNS = {
    code: [
        name,
        unicodedata.normalize("NFKD", name).encode(
            "ascii", "ignore"
        ).decode("ascii")
    ]
    for code, name in COUNTRY_MAP.items()
}

# ============================================================
# NORMALIZAÇÃO
# ============================================================

def normalize_text(value):
    if value is None:
        return ""

    value = html.unescape(str(value))

    value = unicodedata.normalize(
        "NFKD",
        value
    ).encode(
        "ascii",
        "ignore"
    ).decode(
        "ascii"
    )

    value = value.lower()

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def repair_mojibake(value):
    if value is None:
        return value

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
        "Ã¶": "ö",
        "Ã±": "ñ",
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
        "Â ": " ",
        "Â": "",
    }

    for _ in range(3):
        changed = False

        for old, new in replacements.items():
            if old in text:
                text = text.replace(old, new)
                changed = True

        if not changed:
            break

    return text


# ============================================================
# DATAS
# ============================================================

def cutoff_date():
    return date.today() - timedelta(days=PERIOD_DAYS)


def parse_date(value):
    if not value:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    text = str(value).strip()

    if not text:
        return None

    text = text[:30]

    formats = [
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y%m%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(
                text,
                fmt
            ).date()
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
                int(match.group(3))
            )
        except Exception:
            pass

    return None


def recent_enough(result):
    d = parse_date(result.get("date"))

    if not d:
        d = parse_date(result.get("deadline"))

    if not d:
        return True

    return d >= cutoff_date()


# ============================================================
# PAÍSES / REGIÕES
# ============================================================

def country_from_code(value):
    if not value:
        return None

    code = str(value).strip().upper()

    if code in COUNTRY_MAP:
        return code

    if code in ISO3_MAP:
        return ISO3_MAP[code]

    return None


def country_from_text(*values):
    text = normalize_text(
        " ".join(
            str(v)
            for v in values
            if v
        )
    )

    for code, patterns in COUNTRY_TEXT_PATTERNS.items():
        for pattern in patterns:
            p = normalize_text(pattern)

            if p and re.search(
                r"\b" + re.escape(p) + r"\b",
                text
            ):
                return code

    return None


def region_from_country(code):
    if not code:
        return "Global"

    code = code.upper()

    for region, countries in REGION_COUNTRIES.items():
        if code in countries:
            return region

    return "Global"


# ============================================================
# TERMOS / CLASSIFICAÇÃO
# ============================================================

def contains_any(text, terms):
    normalized = normalize_text(text)

    for term in terms:
        t = normalize_text(term)

        if t and t in normalized:
            return True

    return False


def archaeology_evidence(title, description):
    text = normalize_text(
        f"{title} {description}"
    )

    for term in DIRECT_TERMS:
        t = normalize_text(term)

        if t and t in text:
            return True

    return False


def strong_archaeology_evidence(title, description):
    text = normalize_text(
        f"{title} {description}"
    )

    strong_terms = [
        "archaeologist",
        "archaeological excavation",
        "archaeological monitoring",
        "archaeological survey",
        "archaeological investigation",
        "archaeological fieldwork",
        "archaeological watching brief",
        "archaeological services",
        "arqueologo",
        "arqueologa",
        "escavacao arqueologica",
        "acompanhamento arqueologico",
        "monitorizacao arqueologica",
        "monitoramento arqueologico",
        "prospeccao arqueologica",
        "arqueologia preventiva",
        "excavacion arqueologica",
        "excavaciones arqueologicas",
        "seguimiento arqueologico",
        "monitoreo arqueologico",
        "prospeccion arqueologica",
        "servicios arqueologicos",
        "patrimonio arqueologico",
        "fouilles archeologiques",
        "archeologue",
        "archaeologe",
    ]

    return contains_any(
        text,
        strong_terms
    )


def classify_result(
    title,
    description="",
    cpv="",
    search_mode="direct"
):
    title = repair_mojibake(title or "")
    description = repair_mojibake(description or "")

    text = normalize_text(
        f"{title} {description}"
    )

    if search_mode == "heritage":
        if contains_any(
            text,
            HERITAGE_TERMS
        ):
            return "Património / Ambiente Histórico"

        if contains_any(
            text,
            DIRECT_TERMS
        ):
            return "Arqueologia direta"

        return "Outro"

    if search_mode == "project":
        if archaeology_evidence(
            title,
            description
        ):
            return "Arqueologia direta"

        return "Outro"

    # ========================================================
    # DIRECT
    # ========================================================

    direct = archaeology_evidence(
        title,
        description
    )

    if not direct:
        return "Outro"

    # Exclusões de suporte genérico.
    # Só eliminamos se não existir evidência forte.
    if contains_any(
        text,
        SUPPORT_EXCLUSIONS
    ):
        if not strong_archaeology_evidence(
            title,
            description
        ):
            return "Outro"

    return "Arqueologia direta"


# ============================================================
# UTILITÁRIOS JSON
# ============================================================

def first_value(row, keys):
    for key in keys:
        if isinstance(row, dict):
            value = row.get(key)

            if value not in (
                None,
                "",
                [],
                {}
            ):
                return value

    return None


def recursive_find(obj, fragments):
    if isinstance(obj, dict):

        for key, value in obj.items():

            key_norm = normalize_text(key)

            for fragment in fragments:
                if normalize_text(fragment) in key_norm:
                    if value not in (
                        None,
                        "",
                        [],
                        {}
                    ):
                        return value

            found = recursive_find(
                value,
                fragments
            )

            if found not in (
                None,
                "",
                [],
                {}
            ):
                return found

    elif isinstance(obj, list):

        for item in obj:

            found = recursive_find(
                item,
                fragments
            )

            if found not in (
                None,
                "",
                [],
                {}
            ):
                return found

    return None


def safe_json(response):
    try:
        return response.json()
    except Exception:
        return {}


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
    "deadline",
    "description-proc",
    "description-lot",
]


def query_ted(
    term,
    diagnostics,
    search_mode="direct"
):
    try:
        query = f'FT~"{term}"'

        response = requests.get(
            TED_URL,
            params={
                "q": query,
                "fields": ",".join(TED_FIELDS),
                "page": 1,
                "limit": PAGE_SIZE,
            },
            timeout=REQUEST_TIMEOUT
        )

        diagnostics.append({
            "source": TED_SOURCE,
            "term": term,
            "status_code": response.status_code
        })

        if response.status_code != 200:
            return []

        data = safe_json(response)

        rows = (
            data.get("notices")
            or data.get("results")
            or []
        )

        results = []

        for row in rows:

            title = first_value(
                row,
                [
                    "notice-title",
                    "title",
                ]
            ) or ""

            description = first_value(
                row,
                [
                    "description-proc",
                    "description-lot",
                    "description",
                ]
            ) or ""

            buyer = first_value(
                row,
                [
                    "buyer-name",
                    "buyer",
                ]
            ) or ""

            country_raw = first_value(
                row,
                [
                    "buyer-country",
                    "country",
                ]
            )

            country = country_from_code(
                country_raw
            )

            if not country:
                country = country_from_text(
                    buyer,
                    title,
                    description
                )

            cpv = first_value(
                row,
                [
                    "classification-cpv",
                    "cpv",
                ]
            ) or ""

            publication_date = first_value(
                row,
                [
                    "publication-date",
                    "publicationDate",
                ]
            )

            deadline = first_value(
                row,
                [
                    "deadline-date-lot",
                    "deadline-receipt-tender-date-lot",
                    "deadline-receipt-request-date-lot",
                    "deadline",
                ]
            )

            item = {
                "title": repair_mojibake(title),
                "description": repair_mojibake(description),
                "buyer": repair_mojibake(buyer),
                "country": country,
                "country_name": COUNTRY_MAP.get(
                    country,
                    country or ""
                ),
                "region": region_from_country(
                    country
                ),
                "cpv": str(cpv),
                "date": publication_date,
                "deadline": deadline,
                "source": TED_SOURCE,
                "url": (
                    "https://ted.europa.eu/"
                ),
            }

            item["category"] = classify_result(
                item["title"],
                item["description"],
                item["cpv"],
                search_mode
            )

            if item["category"] == "Outro":
                continue

            if not recent_enough(item):
                continue

            results.append(item)

        return results

    except Exception as exc:

        diagnostics.append({
            "source": TED_SOURCE,
            "term": term,
            "error": str(exc)
        })

        return []


# ============================================================
# WORLD BANK
# ============================================================

WORLD_BANK_TITLE_KEYS = [
    "bid_description",
    "procurement_name",
    "notice_title",
    "title",
    "project_name",
]

WORLD_BANK_DESCRIPTION_KEYS = [
    "description",
    "bid_description",
    "procurement_description",
    "notice_description",
]

WORLD_BANK_BUYER_KEYS = [
    "borrower",
    "buyer",
    "agency",
    "procuring_entity",
    "client",
    "project_name",
]

WORLD_BANK_COUNTRY_KEYS = [
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
    "borrower_country",
]

WORLD_BANK_DATE_KEYS = [
    "publication_date",
    "publicationDate",
    "publicationdate",
    "notice_date",
    "noticeDate",
    "procurement_notice_date",
    "notice_publication_date",
    "notice_publicationdate",
    "bid_publication_date",
    "date",
    "published_date",
    "publishedDate",
    "post_date",
    "postdate",
    "posting_date",
    "posted_date",
    "created_date",
    "createdDate",
    "date_published",
    "datepublished",
    "invitation_date",
    "invitationdate",
    "published_on",
]

WORLD_BANK_DEADLINE_KEYS = [
    "submission_deadline",
    "submissionDeadline",
    "submissionDate",
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
    "contract_deadline",
    "contractDeadline",
]

WORLD_BANK_URL_KEYS = [
    "url",
    "notice_url",
    "web_url",
    "procurement_url",
    "link",
]


def query_world_bank(
    term,
    diagnostics,
    search_mode="direct"
):
    try:

        response = requests.get(
            WORLD_BANK_URL,
            params={
                "qterm": term,
                "rows": 100,
                "format": "json",
            },
            timeout=REQUEST_TIMEOUT
        )

        diagnostics.append({
            "source": WORLD_BANK_SOURCE,
            "term": term,
            "status_code": response.status_code
        })

        if response.status_code != 200:
            return []

        data = safe_json(response)

        rows = []

        for key in (
            "procnotices",
            "notices",
            "results",
            "documents"
        ):
            value = data.get(key)

            if isinstance(value, list):
                rows.extend(value)

            elif isinstance(value, dict):
                for subvalue in value.values():
                    if isinstance(subvalue, list):
                        rows.extend(subvalue)

        if not rows and isinstance(data, list):
            rows = data

        results = []

        for row in rows:

            title = first_value(
                row,
                WORLD_BANK_TITLE_KEYS
            ) or ""

            description = first_value(
                row,
                WORLD_BANK_DESCRIPTION_KEYS
            ) or ""

            buyer = first_value(
                row,
                WORLD_BANK_BUYER_KEYS
            ) or ""

            country_raw = first_value(
                row,
                WORLD_BANK_COUNTRY_KEYS
            )

            if not country_raw:
                country_raw = recursive_find(
                    row,
                    [
                        "country",
                        "borrower_country"
                    ]
                )

            country = country_from_code(
                country_raw
            )

            if not country:
                country = country_from_text(
                    buyer,
                    title,
                    description,
                    row.get("project_name"),
                    row.get("borrower")
                )

            cpv = first_value(
                row,
                [
                    "cpv",
                    "classification-cpv",
                    "classification"
                ]
            ) or ""

            publication_date = first_value(
                row,
                WORLD_BANK_DATE_KEYS
            )

            if not publication_date:
                publication_date = recursive_find(
                    row,
                    [
                        "publication",
                        "published",
                        "posting",
                        "posted"
                    ]
                )

            deadline = first_value(
                row,
                WORLD_BANK_DEADLINE_KEYS
            )

            if not deadline:
                deadline = recursive_find(
                    row,
                    [
                        "deadline",
                        "closing",
                        "submission"
                    ]
                )

            url = first_value(
                row,
                WORLD_BANK_URL_KEYS
            )

            item = {
                "title": repair_mojibake(
                    title
                ),
                "description": repair_mojibake(
                    description
                ),
                "buyer": repair_mojibake(
                    buyer
                ),
                "country": country,
                "country_name": COUNTRY_MAP.get(
                    country,
                    country or ""
                ),
                "region": region_from_country(
                    country
                ),
                "cpv": str(cpv),
                "date": publication_date,
                "deadline": deadline,
                "source": WORLD_BANK_SOURCE,
                "url": url or "",
            }

            item["category"] = classify_result(
                item["title"],
                item["description"],
                item["cpv"],
                search_mode
            )

            if item["category"] == "Outro":
                continue

            if not recent_enough(item):
                continue

            results.append(item)

        return results

    except Exception as exc:

        diagnostics.append({
            "source": WORLD_BANK_SOURCE,
            "term": term,
            "error": str(exc)
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

        response = requests.get(
            SECOP_URL,
            params={
                "$limit": 1000,
                "$q": term,
            },
            timeout=REQUEST_TIMEOUT
        )

        diagnostics.append({
            "source": SECOP_SOURCE,
            "term": term,
            "status_code": response.status_code
        })

        if response.status_code != 200:
            return []

        data = safe_json(response)

        if not isinstance(data, list):
            return []

        results = []

        for row in data:

            title = first_value(
                row,
                [
                    "nombre_del_procedimiento",
                    "objeto_del_contrato",
                    "descripcion_del_proceso",
                    "title",
                ]
            ) or ""

            description = first_value(
                row,
                [
                    "descripcion_del_proceso",
                    "objeto_del_contrato",
                ]
            ) or ""

            buyer = first_value(
                row,
                [
                    "entidad",
                    "nombre_entidad",
                ]
            ) or ""

            cpv = first_value(
                row,
                [
                    "codigo_principal_de_producto",
                    "codigo_unspsc",
                ]
            ) or ""

            publication_date = first_value(
                row,
                [
                    "fecha_de_publicacion",
                    "fecha_publicacion",
                    "fecha_de_publicacion_del_proceso",
                ]
            )

            deadline = first_value(
                row,
                [
                    "fecha_de_recepcion_de_ofertas",
                    "fecha_de_cierre",
                ]
            )

            url = first_value(
                row,
                [
                    "urlproceso",
                    "link",
                    "url",
                ]
            )

            combined = normalize_text(
                f"{title} {description}"
            )

            # Garantia adicional para o SECOP:
            # o termo pesquisado tem de aparecer no texto.
            if normalize_text(term) not in combined:
                continue

            item = {
                "title": repair_mojibake(
                    title
                ),
                "description": repair_mojibake(
                    description
                ),
                "buyer": repair_mojibake(
                    buyer
                ),
                "country": "CO",
                "country_name": "Colombia",
                "region": "América",
                "cpv": str(cpv),
                "date": publication_date,
                "deadline": deadline,
                "source": SECOP_SOURCE,
                "url": url or "",
            }

            item["category"] = classify_result(
                item["title"],
                item["description"],
                item["cpv"],
                search_mode
            )

            if item["category"] == "Outro":
                continue

            if not recent_enough(item):
                continue

            results.append(item)

        return results

    except Exception as exc:

        diagnostics.append({
            "source": SECOP_SOURCE,
            "term": term,
            "error": str(exc)
        })

        return []


# ============================================================
# BRASIL - PNCP
# ============================================================

# A API PNCP exige modalidade.
# Estes códigos cobrem as modalidades mais relevantes para
# serviços, concursos e contratação pública de arqueologia.
BRAZIL_MODALITIES = [
    4,   # Concorrência internacional
    5,   # Pregão
    6,   # Dispensa
    7,   # Inexigibilidade
    8,   # Concurso
    12,  # Credenciamento
]

BRAZIL_MAX_PAGES = 3


def brazil_date(value):
    if isinstance(value, date):
        return value.strftime("%Y%m%d")

    return value.strftime(
        "%Y%m%d"
    )


def extract_brazil_rows(data):
    if isinstance(data, list):
        return data

    if not isinstance(data, dict):
        return []

    for key in (
        "data",
        "resultado",
        "resultados",
        "items",
        "content",
        "contratacoes",
    ):
        value = data.get(key)

        if isinstance(value, list):
            return value

    return []


def query_brazil(
    term,
    diagnostics,
    search_mode="direct"
):
    """
    PNCP não permite, nesta rota, uma pesquisa textual simples.
    Por isso consultamos as modalidades relevantes e filtramos
    localmente pelo objeto da contratação.

    A API oficial exige data inicial, data final, modalidade e página.
    """

    results = []

    try:

        start = cutoff_date()
        end = date.today()

        for modality in BRAZIL_MODALITIES:

            for page in range(
                1,
                BRAZIL_MAX_PAGES + 1
            ):

                response = requests.get(
                    BRAZIL_URL,
                    params={
                        "dataInicial": brazil_date(start),
                        "dataFinal": brazil_date(end),
                        "codigoModalidadeContratacao": modality,
                        "pagina": page,
                        "tamanhoPagina": 50,
                    },
                    timeout=REQUEST_TIMEOUT
                )

                diagnostics.append({
                    "source": BRAZIL_SOURCE,
                    "term": term,
                    "modality": modality,
                    "page": page,
                    "status_code": response.status_code
                })

                if response.status_code != 200:
                    break

                data = safe_json(response)

                rows = extract_brazil_rows(
                    data
                )

                if not rows:
                    break

                for row in rows:

                    if not isinstance(
                        row,
                        dict
                    ):
                        continue

                    title = first_value(
                        row,
                        [
                            "objetoCompra",
                            "objeto",
                            "descricao",
                            "titulo",
                        ]
                    ) or ""

                    description = first_value(
                        row,
                        [
                            "objetoCompra",
                            "descricao",
                            "descricaoObjeto",
                        ]
                    ) or ""

                    organ = row.get(
                        "orgaoEntidade"
                    )

                    if isinstance(
                        organ,
                        dict
                    ):
                        buyer = first_value(
                            organ,
                            [
                                "razaoSocial",
                                "nome",
                            ]
                        ) or ""
                    else:
                        buyer = first_value(
                            row,
                            [
                                "orgaoEntidadeRazaoSocial",
                                "nomeOrgao",
                                "orgao",
                            ]
                        ) or ""

                    unit = row.get(
                        "unidadeOrgao"
                    )

                    uf = ""

                    municipality = ""

                    if isinstance(
                        unit,
                        dict
                    ):
                        uf = first_value(
                            unit,
                            [
                                "ufSigla",
                                "uf",
                            ]
                        ) or ""

                        municipality = first_value(
                            unit,
                            [
                                "municipioNome",
                                "nomeMunicipio",
                            ]
                        ) or ""

                    if not uf:
                        uf = first_value(
                            row,
                            [
                                "unidadeOrgaoUfSigla",
                                "uf",
                            ]
                        ) or ""

                    publication_date = first_value(
                        row,
                        [
                            "dataPublicacaoPncp",
                            "dataInclusaoPncp",
                            "dataAtualizacaoPncp",
                        ]
                    )

                    deadline = first_value(
                        row,
                        [
                            "dataEncerramentoPropostaPncp",
                            "dataAberturaPropostaPncp",
                        ]
                    )

                    number = first_value(
                        row,
                        [
                            "numeroControlePNCP",
                            "numeroControlePncp",
                        ]
                    )

                    text = normalize_text(
                        f"{title} {description}"
                    )

                    # Filtragem textual local.
                    if normalize_text(term) not in text:
                        continue

                    item = {
                        "title": repair_mojibake(
                            title
                        ),
                        "description": repair_mojibake(
                            description
                        ),
                        "buyer": repair_mojibake(
                            buyer
                        ),
                        "country": "BR",
                        "country_name": "Brasil",
                        "region": "América",
                        "cpv": "",
                        "date": publication_date,
                        "deadline": deadline,
                        "source": BRAZIL_SOURCE,
                        "url": (
                            "https://pncp.gov.br/app/editais"
                            if not number
                            else (
                                "https://pncp.gov.br/app/editais/"
                                + str(number)
                            )
                        ),
                        "uf": uf,
                        "municipality": municipality,
                        "pncp": number or "",
                    }

                    item["category"] = classify_result(
                        item["title"],
                        item["description"],
                        item["cpv"],
                        search_mode
                    )

                    if item["category"] == "Outro":
                        continue

                    if not recent_enough(item):
                        continue

                    results.append(item)

    except Exception as exc:

        diagnostics.append({
            "source": BRAZIL_SOURCE,
            "term": term,
            "error": str(exc)
        })

    return results


# ============================================================
# PESQUISA AUTOMÁTICA
# ============================================================

def automatic_search(
    query,
    diagnostics
):
    query_norm = normalize_text(
        query
    )

    # --------------------------------------------------------
    # MODOS
    # --------------------------------------------------------

    if query_norm in (
        "",
        "archaeology",
        "arqueologia",
        "archaeological",
        "arqueologico",
        "arqueologica",
        "archaeologist",
        "arqueologo",
    ):
        search_mode = "direct"

        ted_terms = AUTOMATIC_TERMS_TED
        world_bank_terms = AUTOMATIC_TERMS_WORLD_BANK
        secop_terms = AUTOMATIC_TERMS_SECOP
        brazil_terms = AUTOMATIC_TERMS_BRAZIL

    elif any(
        term in query_norm
        for term in HERITAGE_TERMS
    ):
        search_mode = "heritage"

        ted_terms = [query]
        world_bank_terms = [query]
        secop_terms = [query]
        brazil_terms = [query]

    elif any(
        term in query_norm
        for term in MAJOR_PROJECT_TERMS
    ):
        search_mode = "project"

        # Só procuramos projectos juntamente com arqueologia.
        ted_terms = [
            f"archaeological {query}",
            f"archaeology {query}",
            f"arqueologia {query}",
        ]

        world_bank_terms = [
            f"archaeology {query}",
            f"archaeological {query}",
            f"arqueologia {query}",
        ]

        secop_terms = [
            f"arqueologia {query}",
            f"arqueologico {query}",
        ]

        brazil_terms = [
            f"arqueologia {query}",
            f"arqueologico {query}",
        ]

    else:
        search_mode = "direct"

        ted_terms = [query]
        world_bank_terms = [query]
        secop_terms = [query]
        brazil_terms = [query]

    jobs = []

    for term in ted_terms:
        jobs.append(
            (
                "ted",
                term,
                search_mode
            )
        )

    for term in world_bank_terms:
        jobs.append(
            (
                "worldbank",
                term,
                search_mode
            )
        )

    for term in secop_terms:
        jobs.append(
            (
                "secop",
                term,
                search_mode
            )
        )

    for term in brazil_terms:
        jobs.append(
            (
                "brazil",
                term,
                search_mode
            )
        )

    all_results = []

    # ========================================================
    # CONCORRÊNCIA
    # ========================================================

    with ThreadPoolExecutor(
        max_workers=8
    ) as executor:

        future_map = {}

        for source, term, mode in jobs:

            if source == "ted":
                future = executor.submit(
                    query_ted,
                    term,
                    diagnostics,
                    mode
                )

            elif source == "worldbank":
                future = executor.submit(
                    query_world_bank,
                    term,
                    diagnostics,
                    mode
                )

            elif source == "secop":
                future = executor.submit(
                    query_secop,
                    term,
                    diagnostics,
                    mode
                )

            else:
                future = executor.submit(
                    query_brazil,
                    term,
                    diagnostics,
                    mode
                )

            future_map[future] = (
                source,
                term
            )

        for future in as_completed(
            future_map
        ):

            try:
                values = future.result()

                if values:
                    all_results.extend(
                        values
                    )

            except Exception as exc:

                source, term = future_map[
                    future
                ]

                diagnostics.append({
                    "source": source,
                    "term": term,
                    "error": str(exc)
                })

    # ========================================================
    # DEDUPLICAÇÃO
    # ========================================================

    unique = {}

    for item in all_results:

        key = (
            normalize_text(
                item.get("title", "")
            ),
            item.get("source", ""),
            item.get("country", ""),
        )

        if key not in unique:
            unique[key] = item

    results = list(
        unique.values()
    )

    # ========================================================
    # ORDENAÇÃO
    # ========================================================

    def sort_key(item):

        d = parse_date(
            item.get("date")
        )

        archaeology = (
            0
            if item.get("category")
            == "Arqueologia direta"
            else 1
        )

        return (
            archaeology,
            -(d.toordinal() if d else 0),
        )

    results.sort(
        key=sort_key
    )

    return results, search_mode


# ============================================================
# ENDPOINT / HEALTH
# ============================================================

@app.get(
    "/health"
)
def health():

    automatic = [
        source["name"]
        for source in SOURCES
        if source["automatic"]
    ]

    return {
        "ok": True,
        "app": "Arqueologia Radar",
        "version": "2.5",
        "period_days": PERIOD_DAYS,
        "sources": len(SOURCES),
        "automatic_sources": len(automatic),
        "automatic_source_names": automatic,
        "date": date.today().isoformat(),
    }


# ============================================================
# API SEARCH
# ============================================================

@app.get(
    "/api/search"
)
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

        results, search_mode = automatic_search(
            q,
            diagnostics
        )

        # ----------------------------------------------------
        # FILTRO PAÍS
        # ----------------------------------------------------

        country_filter = country.strip().upper()

        if country_filter:

            country_filter = country_from_code(
                country_filter
            ) or country_filter

            results = [
                item
                for item in results
                if item.get("country")
                == country_filter
            ]

        # ----------------------------------------------------
        # FILTRO REGIÃO
        # ----------------------------------------------------

        region_filter = region.strip()

        if region_filter:

            results = [
                item
                for item in results
                if normalize_text(
                    item.get("region", "")
                )
                == normalize_text(
                    region_filter
                )
            ]

        # ----------------------------------------------------
        # ESTATÍSTICAS
        # ----------------------------------------------------

        source_counts = {}

        for item in results:

            source = item.get(
                "source",
                "Desconhecida"
            )

            source_counts[source] = (
                source_counts.get(
                    source,
                    0
                ) + 1
            )

        regions = {}

        for item in results:

            r = item.get(
                "region",
                "Global"
            )

            regions[r] = (
                regions.get(
                    r,
                    0
                ) + 1
            )

        elapsed = (
            datetime.now()
            - started
        ).total_seconds()

        return {
            "ok": True,
            "query": q,
            "search_mode": search_mode,
            "automatic_mode": True,
            "country_filter": country_filter,
            "region_filter": region_filter,
            "results": results,
            "count": len(results),
            "source_counts": source_counts,
            "regions": regions,
            "diagnostics": diagnostics,
            "searched_at": datetime.now().isoformat(),
            "period_days": PERIOD_DAYS,
            "cutoff_date": cutoff_date().isoformat(),
            "elapsed": round(
                elapsed,
                2
            ),
        }

    except Exception as exc:

        return JSONResponse(
            status_code=500,
            content={
                "ok": False,
                "error": str(exc),
                "query": q,
                "diagnostics": diagnostics,
            }
        )


# ============================================================
# TESTE TED / PAÍS
# ============================================================

@app.get(
    "/api/test-ted-country"
)
def test_ted_country(
    country: str = Query(
        default="MAR"
    ),
    term: str = Query(
        default="archaeology"
    )
):
    diagnostics = []

    country_code = (
        country_from_code(country)
        or country.upper()
    )

    query = (
        f'FT~"{term}" '
        f'AND buyer-country={country_code}'
    )

    try:

        response = requests.get(
            TED_URL,
            params={
                "q": query,
                "fields": ",".join(
                    TED_FIELDS
                ),
                "page": 1,
                "limit": 10,
            },
            timeout=REQUEST_TIMEOUT
        )

        return {
            "ok": True,
            "status_code": response.status_code,
            "query": query,
            "response": safe_json(
                response
            ),
        }

    except Exception as exc:

        return {
            "ok": False,
            "error": str(exc),
            "query": query,
        }


# ============================================================
# TESTE TED MINIMAL
# ============================================================

@app.get(
    "/api/test-ted-minimal"
)
def test_ted_minimal(
    term: str = Query(
        default="archaeology"
    )
):
    query = (
        f'FT~"{term}"'
    )

    try:

        response = requests.get(
            TED_URL,
            params={
                "q": query,
                "page": 1,
                "limit": 10,
            },
            timeout=REQUEST_TIMEOUT
        )

        data = safe_json(
            response
        )

        return {
            "ok": True,
            "status_code": response.status_code,
            "query": query,
            "totalNoticeCount": (
                data.get(
                    "totalNoticeCount"
                )
                if isinstance(
                    data,
                    dict
                )
                else None
            ),
            "response": data,
        }

    except Exception as exc:

        return {
            "ok": False,
            "error": str(exc),
            "query": query,
        }


# ============================================================
# ROTAS FRONTEND
# ============================================================

@app.get("/")
def root():
    return FileResponse(
        BASE_DIR / "index.html"
    )


@app.get("/app.js")
def app_js():
    return FileResponse(
        BASE_DIR / "app.js",
        media_type="application/javascript"
    )


@app.get("/manifest.json")
def manifest():
    return FileResponse(
        BASE_DIR / "manifest.json",
        media_type="application/json"
    )
