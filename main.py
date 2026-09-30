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
    version="1.0.0"
)
TED_URL = "https://api.ted.europa.eu/v3/notices/search"
WORLD_BANK_URL = "https://search.worldbank.org/api/v2/procnotices"
PERIOD_DAYS = 365
# TED aceita até 250 resultados por página.
PAGE_SIZE = 250
# Número máximo de páginas por termo.
# 4 x 250 = 1.000 avisos por termo.
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
# Termos adicionais pesquisados automaticamente.
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
# Países por região.
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
def clean_text(value):
    """
    Extrai texto de estruturas TED multilíngues.
    Dá preferência a português, depois inglês.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return fix_mojibake(html.unescape(value)).strip()
    if isinstance(value, list):
        parts = []
        for item in value:
            txt = clean_text(item)
            if txt:
                parts.append(txt)
        return " ".join(parts).strip()
    if isinstance(value, dict):
        # Preferência linguística
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
                txt = clean_text(value[lang])
                if txt:
                    return txt
        # Caso não exista idioma preferido
        for item in value.values():
            txt = clean_text(item)
            if txt:
                return txt
    return fix_mojibake(str(value)).strip()
def mojibake_score(text):
    """
    Mede sinais típicos de texto mal descodificado.
    """
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
    return sum(text.count(x) for x in markers)
def fix_mojibake(value):
    """
    Corrige UTF-8 interpretado incorretamente como Latin-1/Windows-1252.
    Tenta várias passagens e só aceita uma transformação se melhorar
    claramente o texto.
    """
    if value is None:
        return ""
    text = str(value)
    # Primeiro tenta algumas substituições muito comuns.
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
        text = text.replace(old, new)
    # Corrige sucessivas camadas de UTF-8 -> Latin-1.
    for _ in range(3):
        before = text
        try:
            candidate = before.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            break
        if mojibake_score(candidate) < mojibake_score(before):
            text = candidate
        else:
            break
    return html.unescape(text)
def parse_date(value):
    """
    Converte datas TED para date.
    Aceita:
      YYYY-MM-DD
      YYYY-MM-DDTHH:MM:SS
      YYYY-MM-DD+02:00
      YYYYMMDD
    """
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
    # YYYYMMDD
    m = re.search(r"\b(\d{4})(\d{2})(\d{2})\b", text)
    if m:
        try:
            return date(
                int(m.group(1)),
                int(m.group(2)),
                int(m.group(3))
            )
        except ValueError:
            pass
    # YYYY-MM-DD
    m = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if m:
        try:
            return date(
                int(m.group(1)),
                int(m.group(2)),
                int(m.group(3))
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
    """
    Procura todas as datas existentes numa estrutura TED.
    """
    found = []
    if value is None:
        return found
    if isinstance(value, (str, int, float)):
        text = str(value)
        patterns = [
            r"\b\d{4}-\d{2}-\d{2}\b",
            r"\b\d{8}\b",
        ]
        for pattern in patterns:
            for match in re.findall(pattern, text):
                d = parse_date(match)
                if d:
                    found.append(d)
        return found
    if isinstance(value, list):
        for item in value:
            found.extend(extract_all_dates(item))
        return found
    if isinstance(value, dict):
        for item in value.values():
            found.extend(extract_all_dates(item))
        return found
    return found
def extract_deadline(notice):
    """
    Extrai o prazo mais relevante de um aviso TED.
    É dada prioridade a deadline-date-lot e deadline.
    Se houver vários lotes, escolhe a data futura mais próxima.
    """
    candidates = []
    for field in [
        "deadline-date-lot",
        "deadline",
        "deadline-date-part",
    ]:
        if field in notice:
            candidates.extend(
                extract_all_dates(notice.get(field))
            )
    # Remove duplicados
    candidates = sorted(set(candidates))
    today = today_utc()
    future = [
        d for d in candidates
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
            result.extend(extract_cpvs(item))
        return result
    if isinstance(value, dict):
        for item in value.values():
            result.extend(extract_cpvs(item))
        return result
    text = str(value)
    codes = re.findall(r"\b\d{8}\b", text)
    for code in codes:
        if code not in result:
            result.append(code)
    return result
def extract_country(value):
    if value is None:
        return ""
    if isinstance(value, list):
        for item in value:
            result = extract_country(item)
            if result:
                return result
        return ""
    if isinstance(value, dict):
        for item in value.values():
            result = extract_country(item)
            if result:
                return result
        return ""
    return str(value).strip().upper()
def normalise_search_term(term):
    """
    Limita e limpa o termo introduzido pelo utilizador.
    """
    term = (term or "").strip()
    if not term:
        return "archaeology"
    # Evita que uma query introduzida no campo possa quebrar
    # a sintaxe TED.
    term = term.replace('"', " ")
    term = re.sub(r"\s+", " ", term)
    return term[:120]
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
def classify_notice(title, cpvs, notice_type=""):
    text = f"{title} {notice_type}".lower()
    direct_hits = sum(
        1 for term in DIRECT_TERMS
        if term.lower() in text
    )
    heritage_hits = sum(
        1 for term in HERITAGE_TERMS
        if term.lower() in text
    )
    construction_hits = sum(
        1 for term in CONSTRUCTION_TERMS
        if term.lower() in text
    )
    noise_hits = sum(
        1 for term in NOISE_TERMS
        if term.lower() in text
    )
    # CPV específicos de arqueologia / património.
    archaeology_cpvs = {
        "71351914",  # Archaeological services
        "71351910",  # Archaeological services
        "71351811",  # Topographical services
        "71351720",  # Geophysical surveys
        "71351920",  # Historical site services
    }
    cpv_hits = sum(
        1 for cpv in cpvs
        if cpv in archaeology_cpvs
    )
    if direct_hits or cpv_hits:
        return "Arqueologia direta"
    if heritage_hits and (
        construction_hits or "archaeological" in text
    ):
        return "Património cultural"
    if construction_hits and heritage_hits:
        return "Grande projeto / potencial subcontratação"
    if heritage_hits:
        return "Património cultural"
    return "Grande projeto / potencial subcontratação"
def calculate_score(title, cpvs, category, deadline):
    """
    Pontuação interna de relevância.
    Não representa qualquer avaliação oficial do concurso.
    """
    text = title.lower()
    score = 0
    direct = sum(
        1 for term in DIRECT_TERMS
        if term.lower() in text
    )
    heritage = sum(
        1 for term in HERITAGE_TERMS
        if term.lower() in text
    )
    construction = sum(
        1 for term in CONSTRUCTION_TERMS
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
        1 for cpv in cpvs
        if cpv in archaeology_cpvs
    )
    score += min(direct * 30, 60)
    score += min(cpv_hits * 30, 40)
    score += min(heritage * 15, 30)
    if category == "Arqueologia direta":
        score += 25
    elif category == "Património cultural":
        score += 10
    elif category == "Grande projeto / potencial subcontratação":
        score += 5
    if construction and (direct or heritage):
        score += 10
    # Reduz resultados claramente genéricos.
    noise = sum(
        1 for term in NOISE_TERMS
        if term.lower() in text
    )
    score -= min(noise * 12, 35)
    # Prazo futuro aumenta ligeiramente a utilidade prática.
    if deadline:
        days_left = (deadline - today_utc()).days
        if days_left >= 30:
            score += 5
        elif days_left >= 7:
            score += 3
        elif days_left >= 0:
            score += 1
    return max(0, min(100, score))
# ============================================================
# TED
# ============================================================
def build_ted_query(term):
    """
    Query TED estável:
    - título contém o termo
    - publicação nos últimos 365 dias
    - ordenação por data descendente
    A filtragem temporal é feita no próprio TED, reduzindo
    drasticamente o volume de dados transferidos.
    """
    cutoff = cutoff_date().strftime("%Y%m%d")
    return (
        f'notice-title~("{term}") '
        f'AND publication-date>={cutoff} '
        f'SORT BY publication-date DESC'
    )
def ted_request(query, page):
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
    """
    Pesquisa um termo no TED.
    Faz várias páginas apenas quando necessário.
    """
    term = normalise_search_term(term)
    query = build_ted_query(term)
    notices = []
    total = 0
    for page in range(1, MAX_PAGES_PER_TERM + 1):
        try:
            data = ted_request(query, page)
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
        page_notices = data.get("notices", [])
        if page == 1:
            total = int(
                data.get("totalNoticeCount", 0) or 0
            )
        if not isinstance(page_notices, list):
            page_notices = []
        notices.extend(page_notices)
        # Não há mais resultados.
        if len(page_notices) < PAGE_SIZE:
            break
        # Já recolhemos todos os resultados.
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
    """
    Pesquisa oportunidades de procurement no World Bank.
    """
    try:
        params = {
            "qterm": term,
            "rows": 100,
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

        return {
            "term": term,
            "ok": True,
            "error": "",
            "count": len(data.get("procnotices", [])),
            "notices": data.get("procnotices", []),
        }

    except Exception as exc:
        return {
            "term": term,
            "ok": False,
            "error": str(exc),
            "count": 0,
            "notices": [],
        }
# ============================================================
# NORMALIZAÇÃO DE AVISOS
# ============================================================
def notice_to_result(notice):
    publication_number = clean_text(
        notice.get("publication-number")
    )
    publication_raw = notice.get("publication-date")
    publication = parse_date(publication_raw)
    if not publication:
        return None
    # Segurança adicional: só últimos 365 dias.
    if publication < cutoff_date():
        return None
    title = clean_text(
        notice.get("notice-title")
    )
    if not title:
        return None
    buyer = clean_text(
        notice.get("buyer-name")
    )
    country = extract_country(
        notice.get("buyer-country")
    )
    cpvs = extract_cpvs(
        notice.get("classification-cpv")
    )
    notice_type = clean_text(
        notice.get("notice-type")
    )
    deadline = extract_deadline(notice)
    # Eliminar avisos expirados.
    #
    # Se TED não fornecer prazo, o aviso continua visível,
    # porque existem avisos de contratação em que o prazo
    # não está disponível no campo devolvido pela API.
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
    # Rejeita resultados demasiado genéricos.
    #
    # Exceção: CPV arqueológico conhecido.
    text = title.lower()
    relevant_words = (
        DIRECT_TERMS +
        HERITAGE_TERMS
    )
    has_relevant_term = any(
        term.lower() in text
        for term in relevant_words
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
    if not has_relevant_term and not has_archaeology_cpv:
        return None
    # Elimina resultados com relevância muito baixa.
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
        "date_display": publication.strftime("%d/%m/%Y"),
        "country": country,
        "buyer": buyer,
        "deadline": (
            deadline.strftime("%d/%m/%Y")
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
# FILTROS
# ============================================================
def apply_region_filter(results, region):
    region = (region or "").strip()
    if not region:
        return results
    allowed = REGIONS.get(region)
    if not allowed:
        return results
    return [
        item
        for item in results
        if item.get("country") in allowed
    ]
def apply_category_filter(results, category):
    category = (category or "").strip()
    if not category:
        return results
    return [
        item
        for item in results
        if item.get("category") == category
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
    response.headers["Cache-Control"] = (
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
        "sources": 1,
        "api_sources": 1,
        "service": "Arqueologia Radar",
        "version": "1.0.0",
        "ted": TED_URL,
    }
@app.get("/api/sources")
def sources():
    """
    Mantém compatibilidade com o app.js.
    """
    return [
        {
            "name": "TED — Tenders Electronic Daily",
            "region": "Europa / internacional",
            "url": "https://ted.europa.eu/",
            "mode": "api",
        }
    ]
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
    user_term = normalise_search_term(q)
    # Junta o termo introduzido pelo utilizador com os termos
    # especializados do Radar.
    terms = []
    for term in [user_term] + DEFAULT_TERMS:
        term = normalise_search_term(term)
        if term and term.lower() not in {
            x.lower() for x in terms
        }:
            terms.append(term)
    # Evita chamadas excessivas.
    terms = terms[:12]
    diagnostics = []
    all_notices = []
    # Consultas paralelas para manter a aplicação rápida.
    with ThreadPoolExecutor(
        max_workers=min(8, len(terms))
    ) as executor:
        futures = {
            executor.submit(
                search_ted_term,
                term
            ): term
            for term in terms
        }
        for future in as_completed(futures):
            term = futures[future]
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
                "source": f"TED — {term}",
                "ok": result["ok"],
                "count": result["count"],
                "received": result["received"],
                "total": result["total"],
                "error": result.get("error", ""),
            })
            if result["ok"]:
                all_notices.extend(
                    result["notices"]
                )
    # ========================================================
    # DEDUPLICAÇÃO
    # ========================================================
    unique_notices = {}
    for notice in all_notices:
        number = clean_text(
            notice.get("publication-number")
        )
        if number:
            unique_notices[number] = notice
        else:
            # Fallback quando não existe publication-number.
            title = clean_text(
                notice.get("notice-title")
            )
            pub = clean_text(
                notice.get("publication-date")
            )
            key = f"{title}|{pub}"
            unique_notices[key] = notice
    # ========================================================
    # NORMALIZAÇÃO
    # ========================================================
    results = []
    for notice in unique_notices.values():
        try:
            item = notice_to_result(notice)
            if item:
                results.append(item)
        except Exception:
            # Um aviso malformado não deve impedir
            # a apresentação dos restantes.
            continue
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
    # ORDENAÇÃO
    # ========================================================
    def result_sort_key(item):
        deadline = item.get("deadline_iso") or "9999-12-31"
        return (
            -int(item.get("score", 0)),
            deadline,
            item.get("date", ""),
        )
    results.sort(
        key=result_sort_key
    )
    # Limite razoável para o interface.
    # Não limitar os resultados encontrados.
    # Todos os resultados válidos são enviados para o interface.
    # Ordenar diagnósticos pelo nome do termo.
    diagnostics.sort(
        key=lambda x: x["source"]
    )
    elapsed = (
        datetime.utcnow() - started
    ).total_seconds()
    return JSONResponse({
        "results": results,
        "diagnostics": diagnostics,
        "portal_count": 1,
        "api_count": 1,
        "searched_at": today_utc().isoformat(),
        "period_days": PERIOD_DAYS,
        "cutoff_date": cutoff_date().isoformat(),
        "query": user_term,
        "region": region,
        "category_filter": category,
        "result_count": len(results),
        "elapsed_seconds": round(elapsed, 2),
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
