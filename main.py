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
app = FastAPI(title="Arqueologia Radar", version="2.8.2")

REQUEST_TIMEOUT = 20
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
    "prospecção arqueológica", "sondagem arqueológica", "archäologie", "archäologisch",
    "archäologische ausgrabung", "archeologie", "archeologisch", "archeologia",
    "archeologico", "scavo archeologico", "indagine archeologica", "arkeologi",
    "arkeologisk", "arkeologinen", "arheologie", "arheologic",
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
ARCHAEOLOGY_CPVS = {"71351914", "71351910", "71351900", "71351720", "71351811", "71351730"}
FAST_TED_TERMS = ["archaeology", "archaeological", "cultural heritage", "arqueologia"]
WORLD_BANK_TERMS = ["archaeology", "archaeological", "cultural heritage", "heritage"]
SECOP_TERMS = ["archaeology", "archaeological", "arqueologia", "heritage"]
BRAZIL_TERMS = ["arqueologia", "arqueológico", "arqueológica", "arqueológicos", "arqueológicas", "serviços arqueológicos", "serviços de arqueologia", "patrimônio", "património", "patrimônio cultural", "patrimônio histórico", "património cultural", "património histórico"]
# PNCP exige o código de modalidade na consulta por publicação. Códigos válidos
# mais comuns; a consulta é executada uma vez por modalidade e os resultados são filtrados localmente.
PNCP_MODALITIES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 99, 100]

COUNTRY_MAP = {
"PT":"Portugal","ES":"Espanha","FR":"França","DE":"Alemanha","IT":"Itália","NL":"Países Baixos",
"BE":"Bélgica","LU":"Luxemburgo","IE":"Irlanda","GB":"Reino Unido","UK":"Reino Unido","CH":"Suíça",
"AT":"Áustria","PL":"Polónia","CZ":"Chéquia","SK":"Eslováquia","HU":"Hungria","RO":"Roménia",
"BG":"Bulgária","GR":"Grécia","HR":"Croácia","SI":"Eslovénia","SE":"Suécia","NO":"Noruega",
"DK":"Dinamarca","FI":"Finlândia","EE":"Estónia","LV":"Letónia","LT":"Lituânia","MT":"Malta",
"CY":"Chipre","IS":"Islândia","MA":"Marrocos","DZ":"Argélia","TN":"Tunísia","EG":"Egito",
"ZA":"África do Sul","KE":"Quénia","UG":"Uganda","TZ":"Tanzânia","MZ":"Moçambique","GH":"Gana",
"NG":"Nigéria","SN":"Senegal","ET":"Etiópia","US":"Estados Unidos","CA":"Canadá","MX":"México",
"BR":"Brasil","AR":"Argentina","CL":"Chile","CO":"Colômbia","PE":"Peru","UY":"Uruguai",
"PY":"Paraguai","BO":"Bolívia","EC":"Equador","CN":"China","JP":"Japão","KR":"Coreia do Sul",
"IN":"Índia","ID":"Indonésia","MY":"Malásia","TH":"Tailândia","VN":"Vietname","PH":"Filipinas",
"AU":"Austrália","NZ":"Nova Zelândia","SA":"Arábia Saudita","AE":"Emirados Árabes Unidos",
"QA":"Qatar","OM":"Omã","TR":"Turquia","UA":"Ucrânia","RU":"Rússia","PK":"Paquistão",
"BD":"Bangladesh","LK":"Sri Lanka","NP":"Nepal","KH":"Camboja","LA":"Laos","MM":"Myanmar",
"CI":"Costa do Marfim","CM":"Camarões","AO":"Angola","ZW":"Zimbabué","ZM":"Zâmbia","BW":"Botswana",
"NA":"Namíbia","RW":"Ruanda","CD":"República Democrática do Congo","CR":"Costa Rica","PA":"Panamá",
"GT":"Guatemala","DO":"República Dominicana","JM":"Jamaica","VE":"Venezuela","GY":"Guiana",
"SR":"Suriname","KZ":"Cazaquistão","UZ":"Uzbequistão","AZ":"Azerbaijão","GE":"Geórgia","AM":"Arménia",
"IL":"Israel","JO":"Jordânia","LB":"Líbano","IQ":"Iraque","IR":"Irão","KW":"Kuwait","BH":"Barém",
"FJ":"Fiji","PG":"Papua-Nova Guiné"
}
ISO3_MAP = {
"PT":"PRT","ES":"ESP","FR":"FRA","DE":"DEU","IT":"ITA","NL":"NLD","BE":"BEL","LU":"LUX","IE":"IRL",
"GB":"GBR","UK":"GBR","CH":"CHE","AT":"AUT","PL":"POL","CZ":"CZE","SK":"SVK","HU":"HUN",
"RO":"ROU","BG":"BGR","GR":"GRC","HR":"HRV","SI":"SVN","SE":"SWE","NO":"NOR","DK":"DNK",
"FI":"FIN","EE":"EST","LV":"LVA","LT":"LTU","MT":"MLT","CY":"CYP","IS":"ISL","MA":"MAR",
"DZ":"DZA","TN":"TUN","EG":"EGY","ZA":"ZAF","KE":"KEN","UG":"UGA","TZ":"TZA","MZ":"MOZ",
"GH":"GHA","NG":"NGA","SN":"SEN","ET":"ETH","US":"USA","CA":"CAN","MX":"MEX","BR":"BRA",
"AR":"ARG","CL":"CHL","CO":"COL","PE":"PER","UY":"URY","PY":"PRY","BO":"BOL","EC":"ECU",
"CN":"CHN","JP":"JPN","KR":"KOR","IN":"IND","ID":"IDN","MY":"MYS","TH":"THA","VN":"VNM",
"PH":"PHL","AU":"AUS","NZ":"NZL","SA":"SAU","AE":"ARE","QA":"QAT","OM":"OMN","TR":"TUR",
"UA":"UKR","RU":"RUS","PK":"PAK","BD":"BGD","LK":"LKA","NP":"NPL","KH":"KHM","LA":"LAO",
"MM":"MMR","CI":"CIV","CM":"CMR","AO":"AGO","ZW":"ZWE","ZM":"ZMB","BW":"BWA","NA":"NAM",
"RW":"RWA","CD":"COD","CR":"CRI","PA":"PAN","GT":"GTM","DO":"DOM","JM":"JAM","VE":"VEN",
"GY":"GUY","SR":"SUR","KZ":"KAZ","UZ":"UZB","AZ":"AZE","GE":"GEO","AM":"ARM","IL":"ISR",
"JO":"JOR","LB":"LBN","IQ":"IRQ","IR":"IRN","KW":"KWT","BH":"BHR","FJ":"FJI","PG":"PNG"
}
REGION_COUNTRIES = {
"Europa":{"PT","ES","FR","DE","IT","NL","BE","LU","IE","GB","UK","CH","AT","PL","CZ","SK","HU","RO","BG","GR","HR","SI","SE","NO","DK","FI","EE","LV","LT","MT","CY","IS","TR","UA","RU"},
"África":{"MA","DZ","TN","EG","ZA","KE","UG","TZ","MZ","GH","NG","SN","ET","CI","CM","AO","ZW","ZM","BW","NA","RW","CD"},
"América":{"US","CA","MX","BR","AR","CL","CO","PE","UY","PY","BO","EC","CR","PA","GT","DO","JM","VE","GY","SR"},
"Ásia":{"CN","JP","KR","IN","ID","MY","TH","VN","PH","SA","AE","QA","OM","PK","BD","LK","NP","KH","LA","MM","KZ","UZ","AZ","GE","AM","IL","JO","LB","IQ","IR","KW","BH"},
"Oceania":{"AU","NZ","FJ","PG"}
}
TED_FIELDS = ["publication-number", "publication-date", "notice-title", "buyer-name",
              "organisation-country-buyer", "buyer-country", "classification-cpv",
              "description-proc", "description-glo", "deadline-date-lot"]
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "ArqueologiaRadar/2.8.2", "Accept": "application/json"})


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
        return " ".join(str(item) for item in flatten_values(value) if item not in (None, "")).strip()
    return html.unescape(str(value)).strip()


def normalize_for_search(value):
    text = unicodedata.normalize("NFKD", normalize_text(value))
    text = "".join(char for char in text if not unicodedata.combining(char)).lower()
    return re.sub(r"\s+", " ", text).strip()


def repair_mojibake(value):
    text = normalize_text(value)
    markers = ("Ã", "Â", "â€", "â€“", "â€”", "\x80", "\x8d")
    if not any(marker in text for marker in markers):
        return text
    for encoding in ("latin-1", "cp1252"):
        try:
            fixed = text.encode(encoding).decode("utf-8")
            old_count = sum(text.count(marker) for marker in ("Ã", "Â", "â€", "â€“", "â€”"))
            new_count = sum(fixed.count(marker) for marker in ("Ã", "Â", "â€", "â€“", "â€”"))
            if fixed != text and new_count < old_count:
                return fixed
        except (UnicodeEncodeError, UnicodeDecodeError):
            pass
    replacements = {"Ã¡":"á", "Ã©":"é", "Ã­":"í", "Ã³":"ó", "Ãº":"ú", "Ã£":"ã",
                    "Ãµ":"õ", "Ã§":"ç", "Ã€":"À", "Ã‰":"É", "Ã‡":"Ç", "â€“":"–",
                    "â€”":"—", "â€œ":"“", "â€":"”", "â€˜":"‘", "â€™":"’", "Â":""}
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
    text = str(value).strip().replace(" ", "")
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d+%H:%M", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S.%fZ", "%d/%m/%Y", "%Y/%m/%d", "%Y%m%d"):
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


def safe_first_text(data, keys):
    for item in flatten_values(first_value(data, keys)):
        text = normalize_text(item)
        if text:
            return text
    return ""


def country_from_text(value):
    text = normalize_for_search(value)
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
    return code


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
    normalized = normalize_for_search(text)
    return any(normalize_for_search(term) in normalized for term in terms)


def classify_result(title, description, cpvs, search_mode="direct"):
    title_text = normalize_text(title)
    description_text = normalize_text(description)
    combined = f"{title_text} {description_text}"
    title_direct = has_any_term(title_text, DIRECT_TERMS)
    description_direct = has_any_term(description_text, DIRECT_TERMS)
    cpv_direct = any(code in ARCHAEOLOGY_CPVS for code in cpvs)
    heritage = has_any_term(combined, HERITAGE_TERMS)
    major = has_any_term(combined, MAJOR_PROJECT_TERMS)

    # Prioridade à arqueologia expressa no título ou no CPV. Uma menção isolada
    # na descrição é mantida com pontuação inferior, para não a confundir com um serviço principal.
    if title_direct or cpv_direct:
        return "Arqueologia direta"
    if description_direct:
        return "Serviço com componente arqueológica"
    if search_mode != "direct" and heritage and major:
        return "Património / grandes projetos"
    if search_mode != "direct" and heritage:
        return "Património cultural"
    return ""


def make_result(title, description, buyer, country, source, url, published, deadline, cpvs, search_mode="direct"):
    title = repair_mojibake(title)
    description = repair_mojibake(description)
    buyer = repair_mojibake(buyer)
    country_text = repair_mojibake(country)
    code = country_from_text(country_text)
    classification = classify_result(title, description, cpvs, search_mode)
    if not classification:
        return None
    published_date = parse_date(published)
    deadline_date = parse_date(deadline)
    score = {"Arqueologia direta": 100, "Serviço com componente arqueológica": 78,
             "Património / grandes projetos": 62, "Património cultural": 50}.get(classification, 40)
    return {
        "title": title, "description": description, "buyer": buyer,
        "country": country_name(code) if code else country_text,
        "country_code": code, "region": region_from_country(code),
        "source": source, "url": normalize_text(url),
        "date": published_date.isoformat() if published_date else "",
        "deadline": deadline_date.isoformat() if deadline_date else "",
        "cpv": cpvs, "classification": classification, "score": score,
    }


def build_ted_query(term, country_code=None):
    today = date.today()
    start = today - timedelta(days=PERIOD_DAYS)
    parts = [f'FT~"{normalize_text(term)}"',
             f"publication-date>={start.strftime('%Y%m%d')}",
             f"publication-date<={today.strftime('%Y%m%d')}"]
    if country_code:
        parts.append(f"buyer-country={str(country_code).upper().strip()}")
    return " AND ".join(parts)


def _ted_post(query, limit=PAGE_SIZE):
    return SESSION.post(TED_URL, json={"query": query, "fields": TED_FIELDS, "page": 1,
                                      "limit": limit, "paginationMode": "PAGE_NUMBER"},
                        timeout=REQUEST_TIMEOUT, headers={"Content-Type": "application/json"})


def query_ted(term, diagnostics=None, search_mode="direct", country_code=None):
    if diagnostics is None:
        diagnostics = []
    query = build_ted_query(term, country_code)
    time.sleep(0.08)
    diagnostic = {"source": "TED — Europa", "term": term, "method": "POST", "query": query,
                  "period_start": cutoff_date().isoformat(), "period_end": date.today().isoformat(),
                  "country_code": country_code or ""}
    try:
        response = _ted_post(query)
        diagnostic["status_code"] = response.status_code
        if response.status_code == 429:
            diagnostic["error"] = "Limite de chamadas TED (429); foi feita uma tentativa adicional"
            time.sleep(1.2)
            response = _ted_post(query)
            diagnostic["retry_status_code"] = response.status_code
        if response.status_code != 200:
            diagnostic["error"] = f"HTTP {response.status_code}: {response.text[:500]}"
            diagnostics.append(diagnostic)
            return []
        payload = response.json()
        notices = payload.get("notices", [])
        if isinstance(notices, dict):
            notices = list(notices.values())
        results = []
        for notice in notices:
            if not isinstance(notice, dict):
                continue
            title = safe_first_text(notice, ["notice-title", "title"])
            description = safe_first_text(notice, ["description-proc", "description-glo", "description"])
            buyer = safe_first_text(notice, ["buyer-name", "buyer"])
            country = safe_first_text(notice, ["organisation-country-buyer", "buyer-country", "country"])
            published = safe_first_text(notice, ["publication-date", "publicationDate"])
            deadline = safe_first_text(notice, ["deadline-date-lot", "deadline-date"])
            number = safe_first_text(notice, ["publication-number", "publicationNumber"])
            cpvs = cpv_values(first_value(notice, ["classification-cpv", "cpv", "CPV"]))
            if not recent_enough(published):
                continue
            result = make_result(title, description, buyer, country, "TED — Europa",
                                 f"https://ted.europa.eu/en/notice/{number}" if number else "",
                                 published, deadline, cpvs, search_mode)
            if result:
                results.append(result)
        diagnostic["returned_notices"] = len(notices)
        diagnostic["accepted_results"] = len(results)
        diagnostics.append(diagnostic)
        return results
    except Exception as exc:
        diagnostic["error"] = str(exc)
        diagnostics.append(diagnostic)
        return []


def query_world_bank(term, diagnostics=None, search_mode="direct"):
    if diagnostics is None:
        diagnostics = []
    diagnostic = {"source": "World Bank Procurement", "term": term, "method": "GET"}
    try:
        response = SESSION.get(WORLD_BANK_URL, params={"qterm": term, "rows": 100, "format": "json"},
                               timeout=REQUEST_TIMEOUT)
        diagnostic["status_code"] = response.status_code
        if response.status_code != 200:
            diagnostic["error"] = f"HTTP {response.status_code}: {response.text[:300]}"
            diagnostics.append(diagnostic)
            return []
        payload = response.json()
        notices = payload.get("procurements") or payload.get("notices") or payload.get("results") or []
        if isinstance(notices, dict):
            notices = list(notices.values())
        output = []
        for item in notices:
            if not isinstance(item, dict):
                continue
            title = first_value(item, ["project_name", "title", "notice_title", "procurement_name", "contract_description"])
            description = first_value(item, ["description", "short_description", "procurement_description", "contract_description"])
            buyer = first_value(item, ["borrower", "buyer", "client", "country_name"])
            country = first_value(item, ["countrycode", "country_code", "country"])
            published = first_value(item, ["publication_date", "published_date", "notice_date", "date"])
            deadline = first_value(item, ["deadline", "submission_deadline", "bid_deadline"])
            url = first_value(item, ["url", "notice_url", "procurement_url", "link"])
            cpvs = cpv_values(first_value(item, ["cpv", "cpvs", "classification"]))
            result = make_result(title, description, buyer, country, "World Bank Procurement",
                                 url, published, deadline, cpvs, search_mode)
            if result and recent_enough(result["date"]):
                output.append(result)
        diagnostic["accepted_results"] = len(output)
        diagnostics.append(diagnostic)
        return output
    except Exception as exc:
        diagnostics.append({**diagnostic, "error": str(exc)})
        return []


def query_secop(term, diagnostics=None, search_mode="direct"):
    if diagnostics is None:
        diagnostics = []
    diagnostic = {"source": "SECOP II — Colômbia", "term": term, "method": "GET"}
    try:
        response = SESSION.get(SECOP_URL, params={"$limit": 1000, "$q": term}, timeout=REQUEST_TIMEOUT)
        diagnostic["status_code"] = response.status_code
        if response.status_code != 200:
            diagnostic["error"] = f"HTTP {response.status_code}: {response.text[:300]}"
            diagnostics.append(diagnostic)
            return []
        payload = response.json()
        if not isinstance(payload, list):
            diagnostics.append({**diagnostic, "error": "A API não devolveu uma lista"})
            return []
        output = []
        normalized_term = normalize_for_search(term)
        for item in payload:
            if not isinstance(item, dict):
                continue
            title = first_value(item, ["descripcion_del_proceso", "nombre_del_procedimiento", "titulo", "description"])
            description = first_value(item, ["descripcion", "description", "objeto"])
            combined = normalize_for_search(f"{title or ''} {description or ''}")
            if normalized_term not in combined:
                continue
            buyer = first_value(item, ["nombre_entidad", "entidad", "buyer"])
            published = first_value(item, ["fecha_de_publicacion", "fecha_publicacion", "fecha_de_ultima_publicacion"])
            deadline = first_value(item, ["fecha_de_recepcion_de_respuestas", "fecha_de_cierre", "fecha_cierre"])
            url = first_value(item, ["urlproceso", "url"])
            cpvs = cpv_values(first_value(item, ["codigo_principal_de_categoria", "codigo_unspsc", "cpv"]))
            result = make_result(title, description, buyer, "CO", "SECOP II — Colômbia",
                                 url, published, deadline, cpvs, search_mode)
            if result and recent_enough(result["date"]):
                output.append(result)
        diagnostic["returned_items"] = len(payload)
        diagnostic["accepted_results"] = len(output)
        diagnostics.append(diagnostic)
        return output
    except Exception as exc:
        diagnostics.append({**diagnostic, "error": str(exc)})
        return []


def query_brazil(term, diagnostics=None, search_mode="direct"):
    """Consulta anúncios publicados no PNCP em modalidades válidas e filtra termos localmente."""
    if diagnostics is None:
        diagnostics = []
    output = []
    # A pesquisa mundial genérica deve reconhecer os termos em português do Brasil.
    normalized_term = normalize_for_search(term)
    if normalized_term in {"archaeology", "archaeological", "arqueologia", "cultural heritage", "heritage"}:
        search_terms = [normalize_for_search(item) for item in BRAZIL_TERMS]
    else:
        search_terms = [normalized_term]

    # Evita chamadas desnecessárias: as modalidades são consultadas uma vez por pesquisa.
    for modality in PNCP_MODALITIES:
        diagnostic = {"source": "PNCP — Brasil", "term": term, "method": "GET", "modality": modality}
        try:
            params = {
                "dataInicial": cutoff_date().strftime("%Y%m%d"),
                "dataFinal": date.today().strftime("%Y%m%d"),
                "codigoModalidadeContratacao": modality,
                "pagina": 1,
                "tamanhoPagina": 10,
            }
            response = SESSION.get(f"{PNCP_BASE_URL}/contratacoes/publicacao", params=params,
                                  timeout=REQUEST_TIMEOUT)
            diagnostic["status_code"] = response.status_code
            if response.status_code != 200:
                diagnostic["error"] = f"HTTP {response.status_code}: {response.text[:250]}"
                diagnostics.append(diagnostic)
                # O PNCP aplica limitação temporária (HTTP 429). Não insistir
                # nas restantes modalidades na mesma pesquisa: evita agravar o bloqueio.
                if response.status_code == 429:
                    diagnostics.append({
                        "source": "PNCP — Brasil", "term": term, "method": "GET",
                        "status": "interrompido",
                        "reason": "HTTP 429 — limite de pedidos; restantes modalidades não consultadas"
                    })
                    break
                continue
            payload = response.json()
            items = payload.get("data", []) if isinstance(payload, dict) else payload
            if not isinstance(items, list):
                diagnostic["error"] = "Formato de resposta inesperado"
                diagnostics.append(diagnostic)
                continue
            accepted = 0
            for item in items:
                if not isinstance(item, dict):
                    continue
                title = first_value(item, ["objetoCompra", "objeto", "descricao", "description"])
                description = first_value(item, ["informacaoComplementar", "objetoCompra", "objeto", "descricao", "description"])
                searchable = normalize_for_search(f"{title or ''} {description or ''}")
                if not any(search_term and search_term in searchable for search_term in search_terms):
                    continue
                buyer = first_value(item, ["orgaoEntidade", "nomeUnidadeCompradora", "razaoSocial", "nomeOrgao"])
                published = first_value(item, ["dataPublicacaoPncp", "dataPublicacao", "dataInclusao"])
                deadline = first_value(item, ["dataEncerramentoProposta", "dataAberturaProposta", "dataFimVigencia"])
                url = first_value(item, ["linkSistemaOrigem", "linkProcessoEletronico", "url", "uri"])
                control_number = first_value(item, ["numeroControlePNCP"])
                if not url and control_number:
                    url = "https://pncp.gov.br/app/editais/" + str(control_number)
                cpvs = cpv_values(first_value(item, ["codigoItem", "codigoCatmat", "cpv"]))
                result = make_result(title, description, buyer, "BR", "PNCP — Brasil", url,
                                     published, deadline, cpvs, search_mode)
                if result and recent_enough(result["date"]):
                    output.append(result)
                    accepted += 1
            diagnostic["returned_items"] = len(items)
            diagnostic["accepted_results"] = accepted
            diagnostics.append(diagnostic)
        except Exception as exc:
            diagnostics.append({**diagnostic, "error": str(exc)})
    return output


def automatic_search(query, diagnostics, country_code=None):
    normalized_query = normalize_for_search(query)
    mode = "direct"
    broad_search = normalized_query in {"", "arqueologia", "archaeology", "archaeological"}
    if broad_search:
        ted_terms = FAST_TED_TERMS
        wb_terms = WORLD_BANK_TERMS
        secop_terms = SECOP_TERMS
        brazil_term = "archaeology"  # query_brazil expande para os termos brasileiros
    else:
        ted_terms = [query]
        wb_terms = [query]
        secop_terms = [query]
        brazil_term = query

    results = []
    # TED sequencial para respeitar limites e evitar picos de pedidos.
    for term in ted_terms:
        results.extend(query_ted(term, diagnostics, mode, country_code))

    # PNCP apenas uma vez por pesquisa; a função percorre modalidades oficiais válidas.
    jobs = [(query_world_bank, term, mode) for term in wb_terms]
    jobs += [(query_secop, term, mode) for term in secop_terms]
    jobs += [(query_brazil, brazil_term, mode)]
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = [executor.submit(fn, term, diagnostics, job_mode) for fn, term, job_mode in jobs]
        for future in as_completed(futures):
            try:
                results.extend(future.result())
            except Exception as exc:
                diagnostics.append({"source": "automatic", "error": str(exc)})
    return mode, results


def filter_results(results, country="", region=""):
    code = country_from_text(country)
    normalized_country = normalize_for_search(country)
    normalized_region = normalize_for_search(region)
    if normalized_country:
        results = [item for item in results if
                   normalize_for_search(item.get("country", "")) == normalized_country or
                   normalize_for_search(item.get("country_code", "")) == normalized_country or
                   (code and item.get("country_code") == code)]
    if normalized_region:
        results = [item for item in results if normalize_for_search(item.get("region", "")) == normalized_region]
    return results


def deduplicate_results(results):
    seen = set()
    output = []
    for item in results:
        url = normalize_for_search(item.get("url", "")).rstrip("/")
        if url:
            key = ("url", url)
        else:
            key = ("text", normalize_for_search(item.get("title", "")),
                   normalize_for_search(item.get("buyer", "")),
                   normalize_for_search(item.get("country_code", "")),
                   normalize_for_search(item.get("source", "")))
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def sort_results(results):
    return sorted(results, key=lambda item: (int(item.get("score", 0)), item.get("date", "")), reverse=True)


@app.get("/")
def index():
    return FileResponse(BASE_DIR / "index.html")


@app.get("/app.js")
def app_js():
    return FileResponse(BASE_DIR / "app.js", media_type="application/javascript")


@app.get("/manifest.json")
def manifest():
    return FileResponse(BASE_DIR / "manifest.json", media_type="application/json")


@app.get("/health")
def health():
    return {"ok": True, "version": "2.8.2", "sources": len(SOURCES),
            "api_sources": sum(1 for source in SOURCES if source.get("automatic")),
            "period_days": PERIOD_DAYS, "ted_page_size": PAGE_SIZE,
            "ted_fast_terms": FAST_TED_TERMS, "pncp_modalities": PNCP_MODALITIES}


@app.get("/api/sources")
def api_sources():
    return {"sources": SOURCES, "count": len(SOURCES),
            "automatic": sum(1 for source in SOURCES if source.get("automatic"))}


@app.get("/api/search")
def api_search(q: str = Query(default="archaeology"),
              country: str = Query(default=""), region: str = Query(default="")):
    diagnostics = []
    try:
        iso3 = country_iso3_from_text(country)
        mode, results = automatic_search(q, diagnostics, iso3 or None)
        results = deduplicate_results(results)
        results = filter_results(results, country, region)
        results = sort_results(results)
        source_names = sorted({item.get("source", "") for item in results if item.get("source")})
        regions = sorted({item.get("region", "") for item in results if item.get("region")})
        automatic_source_names = {"TED — Europa", "World Bank Procurement", "SECOP II — Colômbia", "PNCP — Brasil"}
        successful_diagnostics = [d for d in diagnostics if d.get("status_code") == 200]
        failed_diagnostics = [d for d in diagnostics if d.get("error") or (d.get("status_code") not in (None, 200))]
        consulted_automatic_sources = sorted({d.get("source") for d in successful_diagnostics if d.get("source") in automatic_source_names})
        failed_automatic_sources = sorted({d.get("source") for d in failed_diagnostics if d.get("source") in automatic_source_names})
        return {"ok": True, "version": "2.8.2", "query": q, "mode": mode,
                "results": results, "count": len(results), "sources": source_names,
                "source_count": len(source_names), "regions": regions, "diagnostics": diagnostics,
                "automatic_sources_consulted": consulted_automatic_sources,
                "automatic_sources_count": len(consulted_automatic_sources),
                "automatic_sources_failed": failed_automatic_sources,
                "automatic_sources_failed_count": len(failed_automatic_sources)}
    except Exception as exc:
        return {"ok": False, "version": "2.8.2", "error": str(exc),
                "error_type": type(exc).__name__, "query": q, "diagnostics": diagnostics}


@app.get("/api/test-ted-minimal")
def test_ted_minimal(term: str = Query(default="archaeology")):
    query = build_ted_query(term)
    try:
        response = _ted_post(query)
        try:
            payload = response.json()
        except Exception:
            payload = response.text[:3000]
        return {"ok": response.status_code == 200, "status_code": response.status_code,
                "method": "POST", "query": query, "response": payload}
    except Exception as exc:
        return {"ok": False, "method": "POST", "query": query, "error": str(exc)}


@app.get("/api/test-ted-portugal")
def test_ted_portugal(term: str = Query(default="archaeology")):
    diagnostics = []
    results = query_ted(term, diagnostics, "direct", "PRT")
    portugal_results = [item for item in results if item.get("country_code") == "PT"]
    return {"ok": True, "term": term, "count_total": len(results),
            "count_portugal": len(portugal_results), "results_portugal": portugal_results[:10],
            "diagnostics": diagnostics}


@app.get("/api/test-ted-search")
def test_ted_search(term: str = Query(default="archaeology")):
    diagnostics = []
    results = query_ted(term, diagnostics, "direct")
    return {"ok": True, "term": term, "count": len(results),
            "results": results[:10], "diagnostics": diagnostics}


@app.get("/api/test-ted-country")
def test_ted_country(term: str = Query(default="archaeology"), country: str = Query(default="PRT")):
    query = f'FT~"{term}" AND buyer-country={country}'
    try:
        response = SESSION.post(TED_URL, json={"query": query, "fields": TED_FIELDS,
                                  "page": 1, "limit": 10, "paginationMode": "PAGE_NUMBER"},
                                timeout=REQUEST_TIMEOUT, headers={"Content-Type": "application/json"})
        try:
            payload = response.json()
        except Exception:
            payload = response.text[:3000]
        return {"ok": response.status_code == 200, "status_code": response.status_code,
                "method": "POST", "query": query, "response": payload}
    except Exception as exc:
        return {"ok": False, "method": "POST", "query": query, "error": str(exc)}
