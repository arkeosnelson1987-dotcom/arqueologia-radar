
from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from pathlib import Path
from datetime import date, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import html
import re
import time
import unicodedata
import requests

BASE_DIR = Path(__file__).resolve().parent
APP_VERSION = "2.8.8"
app = FastAPI(title="Arqueologia Radar", version=APP_VERSION)

REQUEST_TIMEOUT = 15
PERIOD_DAYS = 365
PAGE_SIZE = 250

TED_URL = "https://api.ted.europa.eu/v3/notices/search"
WORLD_BANK_URL = "https://search.worldbank.org/api/v2/procnotices"
SECOP_URL = "https://www.datos.gov.co/resource/p6dx-8zbt.json"
PNCP_BASE_URL = "https://pncp.gov.br/api/consulta/v1"

SOURCES = [
    {"name": "TED — Europa", "type": "api", "automatic": True, "url": "https://ted.europa.eu/"},
    {"name": "World Bank Procurement", "type": "api", "automatic": True, "url": "https://projects.worldbank.org/"},
    {"name": "SECOP II — Colômbia", "type": "api", "automatic": True, "url": "https://www.datos.gov.co/"},
    {"name": "PNCP — Brasil", "type": "api", "automatic": True, "url": "https://pncp.gov.br/"},
    {"name": "South Africa eTenders", "type": "portal", "automatic": False, "url": "https://www.etenders.gov.za/"},
    {"name": "African Development Bank", "type": "portal", "automatic": False, "url": "https://www.afdb.org/"},
    {"name": "SAM.gov", "type": "portal", "automatic": False, "url": "https://sam.gov/"},
    {"name": "BASE Portugal", "type": "portal", "automatic": False, "url": "https://www.base.gov.pt/"},
    {"name": "Espanha", "type": "portal", "automatic": False, "url": "https://contrataciondelestado.es/"},
    {"name": "UNDB", "type": "portal", "automatic": False, "url": "https://devbusiness.un.org/"},
    {"name": "UNGM", "type": "portal", "automatic": False, "url": "https://www.ungm.org/"},
    {"name": "EBRD", "type": "portal", "automatic": False, "url": "https://www.ebrd.com/"},
    {"name": "EIB", "type": "portal", "automatic": False, "url": "https://www.eib.org/"},
    {"name": "Oman", "type": "portal", "automatic": False, "url": "https://etendering.tenderboard.gov.om/"},
    {"name": "Saudi Etimad", "type": "portal", "automatic": False, "url": "https://tenders.etimad.sa/"},
    {"name": "UAE", "type": "portal", "automatic": False, "url": "https://mof.gov.ae/"},
    {"name": "Qatar", "type": "portal", "automatic": False, "url": "https://monaqasat.mof.gov.qa/"},
    {"name": "Morocco", "type": "portal", "automatic": False, "url": "https://www.marchespublics.gov.ma/"},
    {"name": "Uganda", "type": "portal", "automatic": False, "url": "https://www.ppda.go.ug/"},
    {"name": "Kenya", "type": "portal", "automatic": False, "url": "https://tenders.go.ke/"},
    {"name": "Tanzania", "type": "portal", "automatic": False, "url": "https://www.ppra.go.tz/"},
    {"name": "Mozambique", "type": "portal", "automatic": False, "url": "https://www.ufsa.gov.mz/"},
    {"name": "ChileCompra", "type": "portal", "automatic": False, "url": "https://www.mercadopublico.cl/"},
    {"name": "IDB", "type": "portal", "automatic": False, "url": "https://www.iadb.org/"},
    {"name": "ADB", "type": "portal", "automatic": False, "url": "https://www.adb.org/"},
    {"name": "AusTender", "type": "portal", "automatic": False, "url": "https://www.tenders.gov.au/"},
    {"name": "NZ GETS", "type": "portal", "automatic": False, "url": "https://www.gets.govt.nz/"},
    {"name": "Redeia", "type": "portal", "automatic": False, "url": "https://www.ree.es/"},
]

DIRECT_TERMS = [
    "archaeology", "archaeological", "archaeologist", "archaeologists",
    "archaeological excavation", "archaeological monitoring", "archaeological survey",
    "archaeological investigation", "archaeological services", "archaeological assessment",
    "archaeological fieldwork", "watching brief", "archéologie", "archéologique",
    "archéologue", "fouille archéologique", "surveillance archéologique",
    "diagnostic archéologique", "arqueologia", "arqueológico", "arqueóloga", "arqueólogo",
    "escavação arqueológica", "acompanhamento arqueológico", "prospeção arqueológica",
    "prospecção arqueológica", "sondagem arqueológica", "serviços arqueológicos",
    "serviço arqueológico", "servicios arqueologicos", "servicio arqueologico",
    "excavacion arqueologica", "excavación arqueológica", "seguimiento arqueologico",
    "prospeccion arqueologica", "prospección arqueológica", "arqueologia preventiva",
    "archäologie", "archäologisch", "archäologische ausgrabung",
    "archeologie", "archeologisch", "archeologia", "archeologico",
    "scavo archeologico", "indagine archeologica", "arkeologi", "arkeologisk",
    "arkeologinen", "arheologie", "arheologic",
]

HERITAGE_TERMS = [
    "cultural heritage", "heritage", "historic environment", "historical environment",
    "built heritage", "archaeological heritage", "historic site", "historical site",
    "monument", "monuments", "unesco", "cultural property", "patrimoine culturel",
    "patrimoine", "monument historique", "site historique", "património cultural",
    "patrimônio cultural", "patrimonio cultural", "património", "monumento",
    "sítio arqueológico", "sitio arqueologico", "kulturerbe", "kulturelles erbe",
    "cultureel erfgoed", "patrimonio storico", "beni culturali", "kulturarv",
]

MAJOR_PROJECT_TERMS = [
    "railway", "rail", "road", "highway", "bridge", "tunnel", "airport", "port",
    "mining", "mine", "pipeline", "gas pipeline", "oil pipeline", "energy", "power",
    "substation", "transmission line", "construction", "infrastructure", "water supply",
    "dam", "ferroviaire", "route", "autoroute", "pont", "aéroport", "énergie",
    "ferrovia", "rodovia", "estrada", "ponte", "túnel", "aeroporto", "porto",
    "mineração", "oleoduto", "gasoduto", "energia", "construção", "infraestrutura",
]

ARCHAEOLOGY_CPVS = {
    "71351914", "71351910", "71351900",
    "71351720", "71351811", "71351730"
}

FAST_TED_TERMS = [
    "archaeology", "archaeological", "cultural heritage", "arqueologia"
]
WORLD_BANK_TERMS = ["archaeology", "cultural heritage"]
SECOP_TERMS = [
    "archaeology", "archaeological", "arqueologia", "arqueología",
    "servicios arqueologicos", "patrimonio cultural", "heritage"
]
BRAZIL_TERMS = [
    "arqueologia", "arqueológico", "arqueológica", "arqueológicos",
    "arqueológicas", "serviços arqueológicos", "serviços de arqueologia",
    "patrimônio", "património", "patrimônio cultural", "patrimônio histórico",
    "património cultural", "património histórico"
]

PNCP_MODALITIES = [1, 3]

COUNTRY_MAP = {
    "PT":"Portugal","ES":"Espanha","FR":"França","DE":"Alemanha","IT":"Itália",
    "NL":"Países Baixos","BE":"Bélgica","LU":"Luxemburgo","IE":"Irlanda",
    "GB":"Reino Unido","UK":"Reino Unido","CH":"Suíça","AT":"Áustria",
    "PL":"Polónia","CZ":"Chéquia","SK":"Eslováquia","HU":"Hungria",
    "RO":"Roménia","BG":"Bulgária","GR":"Grécia","HR":"Croácia",
    "SI":"Eslovénia","SE":"Suécia","NO":"Noruega","DK":"Dinamarca",
    "FI":"Finlândia","EE":"Estónia","LV":"Letónia","LT":"Lituânia",
    "MT":"Malta","CY":"Chipre","IS":"Islândia","MA":"Marrocos",
    "DZ":"Argélia","TN":"Tunísia","EG":"Egito","ZA":"África do Sul",
    "KE":"Quénia","UG":"Uganda","TZ":"Tanzânia","MZ":"Moçambique",
    "GH":"Gana","NG":"Nigéria","SN":"Senegal","ET":"Etiópia",
    "US":"Estados Unidos","CA":"Canadá","MX":"México","BR":"Brasil",
    "AR":"Argentina","CL":"Chile","CO":"Colômbia","PE":"Peru",
    "UY":"Uruguai","PY":"Paraguai","BO":"Bolívia","EC":"Equador",
    "CN":"China","JP":"Japão","KR":"Coreia do Sul","IN":"Índia",
    "ID":"Indonésia","MY":"Malásia","TH":"Tailândia","VN":"Vietname",
    "PH":"Filipinas","AU":"Austrália","NZ":"Nova Zelândia",
    "SA":"Arábia Saudita","AE":"Emirados Árabes Unidos","QA":"Qatar",
    "OM":"Omã","TR":"Turquia","UA":"Ucrânia","RU":"Rússia",
    "PK":"Paquistão","BD":"Bangladesh","LK":"Sri Lanka","NP":"Nepal",
    "KH":"Camboja","LA":"Laos","MM":"Myanmar","CI":"Costa do Marfim",
    "CM":"Camarões","AO":"Angola","ZW":"Zimbabué","ZM":"Zâmbia",
    "BW":"Botswana","NA":"Namíbia","RW":"Ruanda",
    "CD":"República Democrática do Congo","CR":"Costa Rica","PA":"Panamá",
    "GT":"Guatemala","DO":"República Dominicana","JM":"Jamaica",
    "VE":"Venezuela","GY":"Guiana","SR":"Suriname","KZ":"Cazaquistão",
    "UZ":"Uzbequistão","AZ":"Azerbaijão","GE":"Geórgia","AM":"Arménia",
    "IL":"Israel","JO":"Jordânia","LB":"Líbano","IQ":"Iraque",
    "IR":"Irão","KW":"Kuwait","BH":"Barém","FJ":"Fiji",
    "PG":"Papua-Nova Guiné"
}

ISO3_MAP = {
    "PT":"PRT","ES":"ESP","FR":"FRA","DE":"DEU","IT":"ITA","NL":"NLD",
    "BE":"BEL","LU":"LUX","IE":"IRL","GB":"GBR","UK":"GBR","CH":"CHE",
    "AT":"AUT","PL":"POL","CZ":"CZE","SK":"SVK","HU":"HUN","RO":"ROU",
    "BG":"BGR","GR":"GRC","HR":"HRV","SI":"SVN","SE":"SWE","NO":"NOR",
    "DK":"DNK","FI":"FIN","EE":"EST","LV":"LVA","LT":"LTU","MT":"MLT",
    "CY":"CYP","IS":"ISL","MA":"MAR","DZ":"DZA","TN":"TUN","EG":"EGY",
    "ZA":"ZAF","KE":"KEN","UG":"UGA","TZ":"TZA","MZ":"MOZ","GH":"GHA",
    "NG":"NGA","SN":"SEN","ET":"ETH","US":"USA","CA":"CAN","MX":"MEX",
    "BR":"BRA","AR":"ARG","CL":"CHL","CO":"COL","PE":"PER","UY":"URY",
    "PY":"PRY","BO":"BOL","EC":"ECU","CN":"CHN","JP":"JPN","KR":"KOR",
    "IN":"IND","ID":"IDN","MY":"MYS","TH":"THA","VN":"VNM","PH":"PHL",
    "AU":"AUS","NZ":"NZL","SA":"SAU","AE":"ARE","QA":"QAT","OM":"OMN",
    "TR":"TUR","UA":"UKR","RU":"RUS","PK":"PAK","BD":"BGD","LK":"LKA",
    "NP":"NPL","KH":"KHM","LA":"LAO","MM":"MMR","CI":"CIV","CM":"CMR",
    "AO":"AGO","ZW":"ZWE","ZM":"ZMB","BW":"BWA","NA":"NAM","RW":"RWA",
    "CD":"COD","CR":"CRI","PA":"PAN","GT":"GTM","DO":"DOM","JM":"JAM",
    "VE":"VEN","GY":"GUY","SR":"SUR","KZ":"KAZ","UZ":"UZB","AZ":"AZE",
    "GE":"GEO","AM":"ARM","IL":"ISR","JO":"JOR","LB":"LBN","IQ":"IRQ",
    "IR":"IRN","KW":"KWT","BH":"BHR","FJ":"FJI","PG":"PNG"
}

REGION_COUNTRIES = {
    "Europa": {"PT","ES","FR","DE","IT","NL","BE","LU","IE","GB","UK","CH",
        "AT","PL","CZ","SK","HU","RO","BG","GR","HR","SI","SE","NO","DK",
        "FI","EE","LV","LT","MT","CY","IS","TR","UA","RU"},
    "África": {"MA","DZ","TN","EG","ZA","KE","UG","TZ","MZ","GH","NG","SN",
        "ET","CI","CM","AO","ZW","ZM","BW","NA","RW","CD"},
    "América": {"US","CA","MX","BR","AR","CL","CO","PE","UY","PY","BO","EC",
        "CR","PA","GT","DO","JM","VE","GY","SR"},
    "Ásia": {"CN","JP","KR","IN","ID","MY","TH","VN","PH","SA","AE","QA",
        "OM","PK","BD","LK","NP","KH","LA","MM","KZ","UZ","AZ","GE","AM",
        "IL","JO","LB","IQ","IR","KW","BH"},
    "Oceania": {"AU","NZ","FJ","PG"}
}

TED_FIELDS = [
    "publication-number", "publication-date", "notice-title", "buyer-name",
    "organisation-country-buyer", "buyer-country", "classification-cpv",
    "description-proc", "description-glo", "deadline-date-lot"
]

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": f"ArqueologiaRadar/{APP_VERSION}",
    "Accept": "application/json"
})


def flatten_values(value):
    if value is None:
        return []
    if isinstance(value, list):
        result = []
        for item in value:
            result.extend(flatten_values(item))
        return result
    if isinstance(value, dict):
        result = []
        for item in value.values():
            result.extend(flatten_values(item))
        return result
    return [value]


def normalize_text(value):
    if value is None:
        return ""
    if isinstance(value, (dict, list)):
        return " ".join(
            str(item) for item in flatten_values(value)
            if item not in (None, "")
        ).strip()
    return html.unescape(str(value)).strip()


def normalize_for_search(value):
    text = unicodedata.normalize("NFKD", normalize_text(value))
    text = "".join(
        char for char in text if not unicodedata.combining(char)
    ).lower()
    return re.sub(r"\s+", " ", text).strip()


def repair_mojibake(value):
    """Tenta corrigir UTF-8 interpretado como Latin-1/Windows-1252."""
    text = normalize_text(value)
    if not text:
        return text

    markers = ("Ã", "Â", "â€", "ðŸ", "Ãƒ", "Ã‚")

    def score(candidate):
        return (
            sum(candidate.count(marker) * 3 for marker in markers)
            + sum(1 for char in candidate if 0x80 <= ord(char) <= 0x9F)
        )

    # Só aceita uma conversão quando reduz os sinais de corrupção.
    for _ in range(3):
        old_score = score(text)
        candidates = []

        for encoding in ("cp1252", "latin-1"):
            try:
                candidate = text.encode(encoding).decode("utf-8")
            except (UnicodeEncodeError, UnicodeDecodeError):
                continue

            if candidate != text and score(candidate) < old_score:
                candidates.append((score(candidate), candidate))

        if not candidates:
            break

        text = min(candidates, key=lambda item: item[0])[1]

    # Correções explícitas para alguns casos comuns.
    replacements = {
        "Ã¡": "á", "Ã ": "à", "Ã¢": "â", "Ã£": "ã", "Ã¤": "ä",
        "Ã©": "é", "Ã¨": "è", "Ãª": "ê", "Ã­": "í", "Ã¬": "ì",
        "Ã³": "ó", "Ã²": "ò", "Ã´": "ô", "Ãµ": "õ", "Ãº": "ú",
        "Ã¹": "ù", "Ã§": "ç", "Ã‰": "É", "Ã€": "À", "Ã‚": "Â",
        "Ãƒ": "Ã", "Ã‡": "Ç", "Ã“": "Ó", "Ãš": "Ú", "Ã": "Á",
        "Ã": "Í", "Ã": "Ó", "Ã": "Ú", "Ã‰": "É",
        "â€“": "–", "â€”": "—", "â€œ": "“", "â€": "”",
        "â€˜": "‘", "â€™": "’", "Â ": " "
    }

    for old, replacement in replacements.items():
        text = text.replace(old, replacement)

    return text

def parse_date(value):
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    text = str(value).strip().replace(" ", "")
    if not text:
        return None

    for fmt in (
        "%Y-%m-%d", "%Y-%m-%d+%H:%M", "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%fZ", "%d/%m/%Y", "%Y/%m/%d", "%Y%m%d"
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except (ValueError, TypeError):
            continue

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except (ValueError, TypeError):
        return None


def cutoff_date():
    return date.today() - timedelta(days=PERIOD_DAYS)


def recent_enough(value):
    parsed = parse_date(value)
    return parsed is not None and cutoff_date() <= parsed <= date.today() + timedelta(days=1)


def recursive_find(data, keys):
    if isinstance(data, dict):
        for key in keys:
            if key in data and data[key] not in (None, "", []):
                return data[key]
        for value in data.values():
            found = recursive_find(value, keys)
            if found not in (None, "", []):
                return found
    elif isinstance(data, list):
        for value in data:
            found = recursive_find(value, keys)
            if found not in (None, "", []):
                return found
    return None


def first_value(data, keys):
    return recursive_find(data, keys)



def safe_first_text(data, keys=None):
    if keys is None:
        value = data
    else:
        value = first_value(data, keys)

    for item in flatten_values(value):
        text = repair_mojibake(item)
        if text:
            return text
    return ""


def country_from_text(value):
    text = normalize_for_search(repair_mojibake(value))
    if not text:
        return ""

    if len(text) == 2 and text.upper() in COUNTRY_MAP:
        return text.upper()

    if len(text) == 3:
        for code, iso3 in ISO3_MAP.items():
            if iso3.lower() == text:
                return code

    for code, name in COUNTRY_MAP.items():
        normalized_name = normalize_for_search(name)
        if normalized_name == text or (len(text) > 2 and normalized_name in text):
            return code

    return ""


def country_iso3_from_text(value):
    return ISO3_MAP.get(country_from_text(value), "")


def country_name(code):
    code = str(code or "").upper().strip()
    if code in COUNTRY_MAP:
        return COUNTRY_MAP[code]

    for iso2, iso3 in ISO3_MAP.items():
        if code == iso3:
            return COUNTRY_MAP.get(iso2, code)

    return repair_mojibake(code)


def region_from_country(code):
    code = str(code or "").upper().strip()

    for iso2, iso3 in ISO3_MAP.items():
        if code == iso3:
            code = iso2
            break

    for region, countries in REGION_COUNTRIES.items():
        if code in countries:
            return region

    return ""


def cpv_values(value):
    output = []
    for item in flatten_values(value):
        output.extend(re.findall(r"\b\d{8}\b", normalize_text(item)))
    return list(dict.fromkeys(output))


def has_any_term(text, terms):
    normalized = normalize_for_search(repair_mojibake(text))
    return any(normalize_for_search(term) in normalized for term in terms)


def classify_result(title, description, cpvs, search_mode="direct"):
    title_text = repair_mojibake(title)
    description_text = repair_mojibake(description)

    title_norm = normalize_for_search(title_text)
    description_norm = normalize_for_search(description_text)
    combined = f"{title_norm} {description_norm}"

    title_direct = has_any_term(title_norm, DIRECT_TERMS)
    description_direct = has_any_term(description_norm, DIRECT_TERMS)
    cpv_direct = any(code in ARCHAEOLOGY_CPVS for code in cpvs)
    heritage = has_any_term(combined, HERITAGE_TERMS)
    major = has_any_term(combined, MAJOR_PROJECT_TERMS)

    supply_terms = (
        "equipamiento", "equipos", "equipo", "suministro", "suministros",
        "material de laboratorio", "chemical products", "laboratory equipment",
        "fornecimento", "equipamento", "equipamentos", "produtos quimicos",
        "suministro de materiales", "suministro de equipos", "suministro de bienes",
        "compra de equipos", "adquisicion de equipos", "supply of equipment",
        "purchase of equipment", "supply of materials", "equipment purchase",
        "laboratory supplies", "materiales de laboratorio"
    )
    supply_only = has_any_term(title_norm, supply_terms)

    # Termos de obras ou empreendimentos de grande dimensão.
    # Se a arqueologia surgir apenas como componente de um contrato mais amplo,
    # não classificar automaticamente como serviço arqueológico direto.
    construction_terms = (
        "construction of", "construction works", "works for", "works contract",
        "road construction", "railway construction", "bridge construction",
        "construction of a road", "construction of railway",
        "obra de construção", "empreitada de construção", "empreitada de obras",
        "construção da estrada", "construção de estrada", "construção de linha",
        "construção de ferrovia", "obras de infraestrutura",
        "projeto de construção", "proyecto de construccion", "obras de construccion",
        "construccion de carretera", "construccion de ferrocarril",
        "travaux de construction", "construction d'une route",
        "travaux routiers", "travaux ferroviaires"
    )
    major_contract_title = has_any_term(title_norm, construction_terms)

    explicit_service_terms = (
        "archaeological services", "archaeological monitoring",
        "archaeological excavation", "archaeological survey",
        "archaeological assessment", "archaeological investigation",
        "archaeological fieldwork", "watching brief",
        "serviços arqueológicos", "serviços de arqueologia",
        "acompanhamento arqueológico", "escavação arqueológica",
        "prospeção arqueológica", "prospecção arqueológica",
        "sondagem arqueológica", "servicios arqueologicos",
        "servicio de arqueologia", "seguimiento arqueologico",
        "excavacion arqueologica", "excavación arqueológica",
        "prospeccion arqueologica", "surveillance archéologique",
        "fouille archéologique", "diagnostic archéologique"
    )
    explicit_service = has_any_term(title_norm, explicit_service_terms)

    # Bens e equipamentos não são serviços arqueológicos.
    if title_direct and supply_only:
        if description_direct and has_any_term(description_norm, explicit_service_terms):
            return "Serviço com componente arqueológica"
        return ""

    # Um título que identifica claramente um serviço arqueológico mantém
    # prioridade, mesmo que a descrição mencione obras ou infraestrutura.
    if title_direct and explicit_service:
        return "Arqueologia direta"

    # Contrato de construção amplo com referência acessória à arqueologia.
    if title_direct and major and major_contract_title and not explicit_service:
        return "Serviço com componente arqueológica"

    if title_direct:
        if major and major_contract_title and not explicit_service:
            return "Serviço com componente arqueológica"
        return "Arqueologia direta"

    if description_direct and not supply_only:
        if major and major_contract_title and not explicit_service:
            return "Serviço com componente arqueológica"
        return "Serviço com componente arqueológica"

    if cpv_direct and (description_direct or (search_mode != "direct" and heritage)):
        return "Serviço com componente arqueológica"

    if search_mode != "direct" and heritage and major:
        return "Património / grandes projetos"

    if search_mode != "direct" and heritage:
        return "Património cultural"

    return ""


def make_result(title, description, buyer, country, source, url,
                published, deadline, cpvs, search_mode="direct"):
    title = repair_mojibake(title)
    description = repair_mojibake(description)
    buyer = repair_mojibake(buyer)
    country_text = repair_mojibake(country)
    source = repair_mojibake(source)
    url = repair_mojibake(url)

    code = country_from_text(country_text)
    classification = classify_result(title, description, cpvs, search_mode)

    if not classification:
        return None

    published_date = parse_date(published)
    deadline_date = parse_date(deadline)

    score = {
        "Arqueologia direta": 100,
        "Serviço com componente arqueológica": 78,
        "Património / grandes projetos": 62,
        "Património cultural": 50,
        "Fornecimento relacionado com arqueologia": 35
    }.get(classification, 40)

    return {
        "title": title,
        "description": description,
        "buyer": buyer,
        "country": country_name(code) if code else country_text,
        "country_code": code,
        "region": region_from_country(code),
        "source": source,
        "url": url,
        "date": published_date.isoformat() if published_date else "",
        "deadline": deadline_date.isoformat() if deadline_date else "",
        "cpv": cpvs,
        "classification": classification,
        "score": score,
        "date_status": (
            "Data de publicação confirmada"
            if published_date
            else "Data de publicação não fornecida pela fonte"
        ),
    }


def build_ted_query(term, country_code=None):
    today = date.today()
    start = today - timedelta(days=PERIOD_DAYS)

    parts = [
        f'FT~"{normalize_text(term)}"',
        f"publication-date>={start.strftime('%Y%m%d')}",
        f"publication-date<={today.strftime('%Y%m%d')}"
    ]

    if country_code:
        parts.append(f"buyer-country={str(country_code).upper().strip()}")

    return " AND ".join(parts)

# ============================================================
# PARTE 3 DE 3 — APIs AUTOMÁTICAS, FILTROS E ENDPOINTS
# Versão 2.8.8
# Colocar imediatamente depois da Parte 2
# ============================================================

def diagnostic(source, **kwargs):
    """Cria um registo de diagnóstico sem interromper a pesquisa."""
    result = {"source": repair_mojibake(source)}
    result.update(kwargs)
    return result


def result_text(item):
    """Obtém texto pesquisável de um resultado."""
    fields = (
        "title", "notice-title", "titulo", "description",
        "description_text", "buyer", "buyer-name",
        "organization", "organismo", "summary", "texto"
    )
    values = []
    for field in fields:
        value = item.get(field)
        if value:
            values.append(safe_first_text(value))
    return " ".join(values)


def make_api_result(
    title,
    description="",
    url="",
    country="",
    published="",
    deadline="",
    source="",
    cpv=None,
    score=0,
    category="",
    extra=None
):
    """Normaliza resultados provenientes das APIs."""
    title = repair_mojibake(title)
    description = repair_mojibake(description)
    country = country_name(country) if country else ""
    cpv = cpv or []

    combined_text = normalize_for_search(
        f"{title} {description} {' '.join(cpv)}"
    )
    category = category or classify_result(
        title=title,
        description=description,
        cpv=cpv,
        search_mode="all"
    )

    result = {
        "title": title or "Título não disponível",
        "description": description,
        "url": url or "",
        "country": country or "Não identificado",
        "published": str(published or ""),
        "deadline": str(deadline or ""),
        "source": repair_mojibake(source),
        "cpv": cpv,
        "score": score,
        "category": category,
        "text": combined_text,
    }

    if extra:
        result.update(extra)

    return result


# ============================================================
# TED — EUROPA
# ============================================================

def _ted_post(query, fields=None, limit=PAGE_SIZE):
    """Executa uma pesquisa na API TED."""
    payload = {
        "query": query,
        "fields": fields or TED_FIELDS,
        "page": 1,
        "limit": limit,
        "paginationMode": "PAGE_NUMBER",
    }

    last_error = None

    for attempt in range(3):
        try:
            response = SESSION.post(
                TED_URL,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )

            if response.status_code == 429 and attempt < 2:
                time.sleep(2 * (attempt + 1))
                continue

            response.raise_for_status()
            return response.json(), response.status_code, query

        except Exception as exc:
            last_error = str(exc)
            if attempt < 2:
                time.sleep(1 + attempt)

    raise RuntimeError(last_error or "Erro desconhecido na API TED")


def query_ted(term, country_code="", diagnostics=None):
    """Pesquisa concursos TED no período definido."""
    diagnostics = diagnostics if diagnostics is not None else []
    accepted = []
    total_returned = 0
    queries = []

    term = repair_mojibake(term).strip()
    if not term:
        return accepted

    query_terms = [term]

    for search_term in query_terms:
        query_parts = [f'FT~"{search_term}"']

        if country_code:
            query_parts.append(f'buyer-country={country_code}')

        query = " AND ".join(query_parts)
        queries.append(query)

        try:
            data, status_code, used_query = _ted_post(query)
            notices = data.get("notices", []) if isinstance(data, dict) else []
            total_returned += len(notices)

            for notice in notices:
                title = safe_first_text(
                    notice.get("notice-title")
                    or notice.get("title")
                    or notice.get("official-title")
                )

                description = safe_first_text(
                    notice.get("description")
                    or notice.get("notice-description")
                    or notice.get("object-description")
                )

                buyer = safe_first_text(
                    notice.get("buyer-name")
                    or notice.get("buyer")
                )

                published = (
                    notice.get("publication-date")
                    or notice.get("publicationDate")
                    or notice.get("date")
                    or ""
                )

                deadline = (
                    notice.get("deadline-date")
                    or notice.get("deadline")
                    or ""
                )

                notice_country = safe_first_text(
                    notice.get("buyer-country")
                    or notice.get("organisation-country-buyer")
                    or notice.get("country")
                    or country_code
                )

                notice_id = (
                    notice.get("publication-number")
                    or notice.get("notice-number")
                    or notice.get("id")
                    or ""
                )

                links = notice.get("links") or {}
                url = ""

                if isinstance(links, dict):
                    html_links = links.get("html") or {}
                    if isinstance(html_links, dict):
                        url = (
                            html_links.get("ENG")
                            or html_links.get("MUL")
                            or next(iter(html_links.values()), "")
                        )
                    elif isinstance(html_links, str):
                        url = html_links

                if not url and notice_id:
                    url = f"https://ted.europa.eu/en/notice/{notice_id}"

                cpv = cpv_values(
                    notice.get("classification-cpv")
                    or notice.get("cpv")
                    or []
                )

                if not recent_enough(published):
                    continue

                category = classify_result(
                    title=title,
                    description=description,
                    cpv=cpv,
                    search_mode="all",
                )

                if not category:
                    continue

                combined = normalize_for_search(
                    f"{title} {description} {buyer} {' '.join(cpv)}"
                )

                if not has_any_term(
                    combined,
                    FAST_TED_TERMS
                    + WORLD_BANK_TERMS
                    + SECOP_TERMS
                    + BRAZIL_TERMS
                ) and not any(
                    code in cpv for code in (
                        "71351914", "71351910", "71351900",
                        "71351720", "71351811", "71351730",
                        "45112450"
                    )
                ):
                    continue

                score = 100 if category == "Arqueologia direta" else 70

                accepted.append(
                    make_api_result(
                        title=title,
                        description=description,
                        url=url,
                        country=notice_country,
                        published=published,
                        deadline=deadline,
                        source="TED — Europa",
                        cpv=cpv,
                        score=score,
                        category=category,
                        extra={
                            "buyer": buyer,
                            "notice_id": notice_id,
                            "search_term": search_term,
                        },
                    )
                )

            diagnostics.append(
                diagnostic(
                    "TED — Europa",
                    status_code=status_code,
                    query=used_query,
                    returned=len(notices),
                    accepted=len(accepted),
                    total_notice_count=data.get("totalNoticeCount", 0),
                    period_days=PERIOD_DAYS,
                    country_code=country_code or "",
                    error=None,
                )
            )

        except Exception as exc:
            diagnostics.append(
                diagnostic(
                    "TED — Europa",
                    status_code=None,
                    query=query,
                    returned=0,
                    accepted=0,
                    period_days=PERIOD_DAYS,
                    country_code=country_code or "",
                    error=repair_mojibake(str(exc)),
                )
            )

    return deduplicate_results(accepted)


# ============================================================
# WORLD BANK — PROCUREMENT
# ============================================================

def query_world_bank(term, diagnostics=None):
    """Pesquisa oportunidades de contratação do Banco Mundial."""
    diagnostics = diagnostics if diagnostics is not None else []
    accepted = []

    params = {
        "format": "json",
        "rows": 100,
        "qterm": term,
    }

    try:
        response = SESSION.get(
            WORLD_BANK_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        items = []

        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            for key in (
                "procnotices", "procurementNotices", "notices",
                "rows", "data", "results"
            ):
                value = data.get(key)
                if isinstance(value, list):
                    items = value
                    break
                if isinstance(value, dict):
                    items = list(value.values())
                    break

        for item in items:
            if not isinstance(item, dict):
                continue

            title = safe_first_text(
                item.get("project_name")
                or item.get("bid_description")
                or item.get("notice_title")
                or item.get("title")
                or item.get("procurement_name")
            )

            description = safe_first_text(
                item.get("project_description")
                or item.get("description")
                or item.get("bid_description")
                or item.get("procurement_description")
            )

            published = (
                item.get("submission_date")
                or item.get("publication_date")
                or item.get("notice_date")
                or item.get("published_date")
                or ""
            )

            deadline = (
                item.get("notice_status")
                or item.get("deadline")
                or item.get("closing_date")
                or ""
            )

            combined = normalize_for_search(
                f"{title} {description} {term}"
            )

            if not has_any_term(
                combined,
                WORLD_BANK_TERMS + FAST_TED_TERMS
            ):
                continue

            if published and not recent_enough(published):
                continue

            url = (
                item.get("url")
                or item.get("notice_url")
                or item.get("project_url")
                or item.get("link")
                or ""
            )

            country = (
                item.get("country_name")
                or item.get("country")
                or item.get("borrower_country")
                or ""
            )

            category = classify_result(
                title=title,
                description=description,
                cpv=[],
                search_mode="all",
            )

            if not category:
                continue

            score = 100 if category == "Arqueologia direta" else 70

            accepted.append(
                make_api_result(
                    title=title,
                    description=description,
                    url=url,
                    country=country,
                    published=published,
                    deadline=deadline,
                    source="World Bank Procurement",
                    score=score,
                    category=category,
                    extra={
                        "search_term": term,
                        "date_unconfirmed": not bool(published),
                    },
                )
            )

        diagnostics.append(
            diagnostic(
                "World Bank Procurement",
                status_code=response.status_code,
                returned=len(items),
                accepted=len(accepted),
                search_term=term,
                error=None,
            )
        )

    except Exception as exc:
        diagnostics.append(
            diagnostic(
                "World Bank Procurement",
                status_code=None,
                returned=0,
                accepted=0,
                search_term=term,
                error=repair_mojibake(str(exc)),
            )
        )

    return deduplicate_results(accepted)


# ============================================================
# SECOP II — COLÔMBIA
# ============================================================

def query_secop(term, diagnostics=None):
    """Pesquisa contratos publicados no SECOP II."""
    diagnostics = diagnostics if diagnostics is not None else []
    accepted = []

    params = {
        "$limit": 1000,
        "$q": term,
    }

    try:
        response = SESSION.get(
            SECOP_URL,
            params=params,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, list):
            data = []

        for item in data:
            if not isinstance(item, dict):
                continue

            title = safe_first_text(
                item.get("nombre_del_procedimiento")
                or item.get("nombre_del_procedimiento_de_contratacion")
                or item.get("descripcion_del_proceso")
                or item.get("objeto_del_contrato")
                or item.get("nombre_entidad")
            )

            description = safe_first_text(
                item.get("descripcion_del_procedimiento")
                or item.get("descripcion_del_proceso")
                or item.get("objeto_del_contrato")
                or item.get("detalle_del_proceso")
            )

            combined = normalize_for_search(
                f"{title} {description} {term}"
            )

            if not has_any_term(
                combined,
                SECOP_TERMS + FAST_TED_TERMS
            ):
                continue

            published = (
                item.get("fecha_de_publicacion_del")
                or item.get("fecha_publicacion")
                or item.get("fecha_de_publicacion")
                or item.get("fecha")
                or ""
            )

            if published and not recent_enough(published):
                continue

            url = (
                item.get("urlproceso")
                or item.get("url_proceso")
                or item.get("link")
                or ""
            )

            if not url:
                process_id = (
                    item.get("id_del_procedimiento")
                    or item.get("id")
                    or ""
                )
                if process_id:
                    url = (
                        "https://www.contratos.gov.co/"
                        f"consultas/detalleProceso.do?numConstancia={process_id}"
                    )

            country = "Colômbia"

            category = classify_result(
                title=title,
                description=description,
                cpv=[],
                search_mode="all",
            )

            if not category:
                continue

            score = 100 if category == "Arqueologia direta" else 70
            if not published:
                score = max(0, score - 10)

            accepted.append(
                make_api_result(
                    title=title,
                    description=description,
                    url=url,
                    country=country,
                    published=published,
                    deadline=(
                        item.get("fecha_de_recepcion_de")
                        or item.get("fecha_limite")
                        or ""
                    ),
                    source="SECOP II — Colômbia",
                    score=score,
                    category=category,
                    extra={
                        "search_term": term,
                        "date_unconfirmed": not bool(published),
                    },
                )
            )

        diagnostics.append(
            diagnostic(
                "SECOP II — Colômbia",
                status_code=response.status_code,
                returned=len(data),
                accepted=len(accepted),
                search_term=term,
                error=None,
            )
        )

    except Exception as exc:
        diagnostics.append(
            diagnostic(
                "SECOP II — Colômbia",
                status_code=None,
                returned=0,
                accepted=0,
                search_term=term,
                error=repair_mojibake(str(exc)),
            )
        )

    return deduplicate_results(accepted)


# ============================================================
# PNCP — BRASIL
# ============================================================

def query_brazil(term, diagnostics=None):
    """Pesquisa contratações no Portal Nacional de Contratações Públicas."""
    diagnostics = diagnostics if diagnostics is not None else []
    accepted = []

    start_date = (date.today() - timedelta(days=PERIOD_DAYS)).strftime("%Y%m%d")
    end_date = date.today().strftime("%Y%m%d")

    expanded_terms = [term]
    if normalize_for_search(term) in (
        "archaeology", "archaeological", "arqueologia"
    ):
        expanded_terms.extend(
            ["archaeology", "archaeological", "arqueologia"]
        )

    expanded_terms = list(dict.fromkeys(expanded_terms))

    for search_term in expanded_terms:
        for modalidade in (1, 3):
            params = {
                "dataInicial": start_date,
                "dataFinal": end_date,
                "codigoModalidadeContratacao": modalidade,
                "pagina": 1,
                "tamanhoPagina": 50,
                "codigoPais": "BR",
                "texto": search_term,
            }

            try:
                url = (
                    f"{PNCP_BASE_URL}/contratos"
                )

                response = SESSION.get(
                    url,
                    params=params,
                    timeout=REQUEST_TIMEOUT,
                )

                # Algumas versões da API podem não aceitar todos os
                # parâmetros. Mantemos o erro registado para diagnóstico.
                response.raise_for_status()
                data = response.json()

                items = []
                if isinstance(data, list):
                    items = data
                elif isinstance(data, dict):
                    for key in (
                        "data", "items", "resultado", "results",
                        "contratos", "content"
                    ):
                        value = data.get(key)
                        if isinstance(value, list):
                            items = value
                            break

                for item in items:
                    if not isinstance(item, dict):
                        continue

                    title = safe_first_text(
                        item.get("objeto")
                        or item.get("objetoContratacao")
                        or item.get("informacaoComplementar")
                        or item.get("descricao")
                        or item.get("nome")
                    )

                    description = safe_first_text(
                        item.get("informacaoComplementar")
                        or item.get("descricao")
                        or item.get("objeto")
                        or ""
                    )

                    combined = normalize_for_search(
                        f"{title} {description} {search_term}"
                    )

                    if not has_any_term(
                        combined,
                        BRAZIL_TERMS + FAST_TED_TERMS
                    ):
                        continue

                    published = (
                        item.get("dataPublicacaoPncp")
                        or item.get("dataPublicacao")
                        or item.get("dataInclusao")
                        or item.get("dataAssinatura")
                        or ""
                    )

                    if published and not recent_enough(published):
                        continue

                    url = (
                        item.get("linkSistemaOrigem")
                        or item.get("url")
                        or item.get("link")
                        or ""
                    )

                    if not url:
                        control_id = (
                            item.get("numeroControlePNCP")
                            or item.get("id")
                            or ""
                        )
                        if control_id:
                            url = (
                                "https://pncp.gov.br/app/editais/"
                                f"{control_id}"
                            )

                    category = classify_result(
                        title=title,
                        description=description,
                        cpv=[],
                        search_mode="all",
                    )

                    if not category:
                        continue

                    score = (
                        100 if category == "Arqueologia direta" else 70
                    )
                    if not published:
                        score = max(0, score - 10)

                    accepted.append(
                        make_api_result(
                            title=title,
                            description=description,
                            url=url,
                            country="Brasil",
                            published=published,
                            deadline=(
                                item.get("dataEncerramentoProposta")
                                or item.get("dataFimVigencia")
                                or ""
                            ),
                            source="PNCP — Brasil",
                            score=score,
                            category=category,
                            extra={
                                "search_term": search_term,
                                "modality": modalidade,
                                "date_unconfirmed": not bool(published),
                            },
                        )
                    )

                diagnostics.append(
                    diagnostic(
                        "PNCP — Brasil",
                        status_code=response.status_code,
                        returned=len(items),
                        accepted=len(accepted),
                        search_term=search_term,
                        modalidade=modalidade,
                        error=None,
                    )
                )

            except Exception as exc:
                diagnostics.append(
                    diagnostic(
                        "PNCP — Brasil",
                        status_code=None,
                        returned=0,
                        accepted=0,
                        search_term=search_term,
                        modalidade=modalidade,
                        error=repair_mojibake(str(exc)),
                    )
                )

    return deduplicate_results(accepted)


# ============================================================
# PESQUISA AUTOMÁTICA — AS QUATRO APIS
# ============================================================

def automatic_search(query, country_code="", diagnostics=None):
    diagnostics = diagnostics if diagnostics is not None else []
    results = []

    query = repair_mojibake(query).strip()
    if not query:
        return results

    ted_terms = list(dict.fromkeys(FAST_TED_TERMS))
    world_bank_terms = list(dict.fromkeys(WORLD_BANK_TERMS))
    secop_terms = list(dict.fromkeys(SECOP_TERMS))
    brazil_terms = list(dict.fromkeys(BRAZIL_TERMS))

    # TED é executado separadamente para manter o filtro de país.
    for term in ted_terms:
        results.extend(
            query_ted(
                term,
                country_code=country_code,
                diagnostics=diagnostics,
            )
        )

    # As restantes APIs são executadas em paralelo.
    tasks = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        for term in world_bank_terms:
            tasks.append(
                executor.submit(
                    query_world_bank, term, diagnostics
                )
            )

        for term in secop_terms:
            tasks.append(
                executor.submit(
                    query_secop, term, diagnostics
                )
            )

        for term in brazil_terms:
            tasks.append(
                executor.submit(
                    query_brazil, term, diagnostics
                )
            )

        for future in as_completed(tasks):
            try:
                results.extend(future.result())
            except Exception as exc:
                diagnostics.append(
                    diagnostic(
                        "Pesquisa automática",
                        error=repair_mojibake(str(exc)),
                    )
                )

    return deduplicate_results(results)


# ============================================================
# FILTROS, ORDENAÇÃO E DUPLICADOS
# ============================================================

def filter_results(
    results,
    query="",
    country="",
    category="",
    region="",
):
    filtered = []

    query_norm = normalize_for_search(query)
    country_norm = normalize_for_search(country)
    category_norm = normalize_for_search(category)
    region_norm = normalize_for_search(region)

    for item in results:
        searchable = normalize_for_search(
            " ".join(
                str(item.get(key, "") or "")
                for key in (
                    "title", "description", "country", "source",
                    "category", "buyer", "text"
                )
            )
        )

        if query_norm and not all(
            word in searchable for word in query_norm.split()
        ):
            # Não rejeitar resultados automáticos só porque o termo
            # introduzido pelo utilizador não aparece literalmente.
            if not any(
                term in searchable
                for term in (
                    FAST_TED_TERMS
                    + WORLD_BANK_TERMS
                    + SECOP_TERMS
                    + BRAZIL_TERMS
                )
            ):
                continue

        if country_norm:
            item_country = normalize_for_search(
                item.get("country", "")
            )
            if country_norm not in item_country:
                continue

        if category_norm:
            item_category = normalize_for_search(
                item.get("category", "")
            )
            if category_norm not in item_category:
                continue

        if region_norm:
            item_region = normalize_for_search(
                region_from_country(item.get("country", ""))
            )
            if region_norm not in item_region:
                continue

        filtered.append(item)

    return filtered


def deduplicate_results(results):
    seen = set()
    unique = []

    for item in results:
        title = normalize_for_search(item.get("title", ""))
        country = normalize_for_search(item.get("country", ""))
        source = normalize_for_search(item.get("source", ""))
        url = normalize_for_search(item.get("url", ""))

        key = url or f"{title}|{country}|{source}"

        if not key.strip("|"):
            key = f"{title}|{country}"

        if key in seen:
            continue

        seen.add(key)
        unique.append(item)

    return unique


def sort_results(results):
    """Ordena primeiro por relevância e depois pela data."""
    def sort_key(item):
        score = item.get("score", 0) or 0
        published = parse_date(item.get("published", ""))
        timestamp = published.toordinal() if published else 0
        return score, timestamp

    return sorted(results, key=sort_key, reverse=True)


# ============================================================
# ENDPOINTS
# ============================================================

@app.get("/health")
def health():
    return {
        "ok": True,
        "version": APP_VERSION,
        "period_days": PERIOD_DAYS,
        "page_size": PAGE_SIZE,
    }


@app.get("/api/sources")
def api_sources():
    cleaned_sources = []

    for source in SOURCES:
        cleaned = dict(source)
        if "name" in cleaned:
            cleaned["name"] = repair_mojibake(cleaned["name"])
        cleaned_sources.append(cleaned)

    automatic_count = sum(
        1 for source in cleaned_sources
        if source.get("automatic")
    )

    return {
        "ok": True,
        "version": APP_VERSION,
        "sources": cleaned_sources,
        "count": len(cleaned_sources),
        "automatic": automatic_count,
    }


@app.get("/api/search")
def api_search(
    q: str = Query(default="archaeology"),
    country: str = Query(default=""),
    region: str = Query(default=""),
    category: str = Query(default=""),
    source: str = Query(default="all"),
    limit: int = Query(default=250, ge=1, le=1000),
):
    diagnostics = []

    try:
        query = repair_mojibake(q).strip()
        country_code = ""

        if country:
            country_code = country_iso3_from_text(country)

        if source in ("all", "automatic", "auto"):
            results = automatic_search(
                query=query,
                country_code=country_code,
                diagnostics=diagnostics,
            )
        else:
            results = []

        results = filter_results(
            results,
            query=query,
            country=country,
            category=category,
            region=region,
        )

        results = sort_results(deduplicate_results(results))

        return {
            "ok": True,
            "version": APP_VERSION,
            "query": query,
            "count": len(results),
            "results": results[:limit],
            "sources_count": len(SOURCES),
            "automatic_sources_count": sum(
                1 for item in SOURCES
                if item.get("automatic")
            ),
            "diagnostics": diagnostics,
        }

    except Exception as exc:
        return {
            "ok": False,
            "version": APP_VERSION,
            "query": q,
            "count": 0,
            "results": [],
            "diagnostics": diagnostics,
            "error": repair_mojibake(str(exc)),
        }


@app.get("/api/test-ted-minimal")
def test_ted_minimal():
    diagnostics = []
    results = query_ted(
        "archaeology",
        diagnostics=diagnostics,
    )

    return {
        "ok": True,
        "version": APP_VERSION,
        "count": len(results),
        "results": results[:10],
        "diagnostics": diagnostics,
    }


@app.get("/api/test-ted-portugal")
def test_ted_portugal():
    diagnostics = []
    results = query_ted(
        "archaeology",
        country_code="PRT",
        diagnostics=diagnostics,
    )

    return {
        "ok": True,
        "version": APP_VERSION,
        "country_code": "PRT",
        "count": len(results),
        "results": results[:20],
        "diagnostics": diagnostics,
    }


@app.get("/api/test-ted-search")
def test_ted_search(
    q: str = Query(default="archaeology"),
):
    diagnostics = []
    results = query_ted(
        repair_mojibake(q),
        diagnostics=diagnostics,
    )

    return {
        "ok": True,
        "version": APP_VERSION,
        "query": repair_mojibake(q),
        "count": len(results),
        "results": results[:20],
        "diagnostics": diagnostics,
    }


@app.get("/api/test-ted-country")
def test_ted_country(
    country_code: str = Query(default="PRT"),
    q: str = Query(default="archaeology"),
):
    diagnostics = []
    results = query_ted(
        repair_mojibake(q),
        country_code=country_code.strip().upper(),
        diagnostics=diagnostics,
    )

    return {
        "ok": True,
        "version": APP_VERSION,
        "query": repair_mojibake(q),
        "country_code": country_code.strip().upper(),
        "count": len(results),
        "results": results[:20],
        "diagnostics": diagnostics,
    }
