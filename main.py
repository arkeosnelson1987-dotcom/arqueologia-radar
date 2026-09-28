from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import date
from pathlib import Path
import requests
import re
import time

ROOT = Path(__file__).resolve().parent

app = FastAPI(title="Arqueologia Radar")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# FONTES
# ============================================================

SOURCES = [
    ("TED", "Europa", "https://ted.europa.eu/en/search", "api"),
    ("World Bank Procurement", "Global",
     "https://projects.worldbank.org/en/projects-operations/procurement", "portal"),
    ("African Development Bank", "África",
     "https://www.afdb.org/en/documents/category/general-procurement-notices", "portal"),
    ("AfDB Specific Procurement", "África",
     "https://www.afdb.org/en/documents/category/specific-procurement-notices", "portal"),
    ("SAM.gov", "Américas",
     "https://sam.gov/opportunities", "portal"),
    ("BASE Portugal", "Europa",
     "https://www.base.gov.pt/", "portal"),
    ("Contratación Pública España", "Europa",
     "https://contrataciondelestado.es/", "portal"),
    ("UN Development Business", "Global",
     "https://devbusiness.un.org/", "portal"),
    ("UNGM", "Global",
     "https://www.ungm.org/Public/Notice", "portal"),
    ("EBRD Procurement", "Europa",
     "https://www.ebrd.com/work-with-us/procurement.html", "portal"),
    ("EIB Procurement", "Europa",
     "https://www.eib.org/en/projects/procurement/index.htm", "portal"),
    ("Oman Tender Board", "Médio Oriente",
     "https://etendering.tenderboard.gov.om/", "portal"),
    ("Saudi Etimad", "Médio Oriente",
     "https://portal.etimad.sa/", "portal"),
    ("UAE Federal Procurement", "Médio Oriente",
     "https://procurement.gov.ae/", "portal"),
    ("Qatar Monaqasat", "Médio Oriente",
     "https://monaqasat.mof.gov.qa/", "portal"),
    ("Morocco Marchés Publics", "África",
     "https://www.marchespublics.gov.ma/", "portal"),
    ("South Africa eTenders", "África",
     "https://www.etenders.gov.za/", "portal"),
    ("Uganda eGP", "África",
     "https://egpuganda.go.ug/", "portal"),
    ("Kenya PPIP", "África",
     "https://tenders.go.ke/", "portal"),
    ("Tanzania NeST", "África",
     "https://nest.go.tz/", "portal"),
    ("Mozambique UFSA", "África",
     "https://www.ufsa.gov.mz/", "portal"),
    ("ChileCompra", "Américas",
     "https://www.mercadopublico.cl/", "portal"),
    ("Colombia SECOP", "Américas",
     "https://www.colombiacompra.gov.co/secop", "portal"),
    ("Brasil Compras.gov", "Américas",
     "https://www.gov.br/compras/", "portal"),
    ("IDB Procurement", "Américas",
     "https://www.iadb.org/en/how-we-work/procurement", "portal"),
    ("Asian Development Bank", "Ásia-Pacífico",
     "https://www.adb.org/work-with-us/procurement", "portal"),
    ("Australia AusTender", "Ásia-Pacífico",
     "https://www.tenders.gov.au/", "portal"),
    ("New Zealand GETS", "Ásia-Pacífico",
     "https://www.gets.govt.nz/", "portal"),
]


# ============================================================
# TERMOS
# ============================================================

ARCH = [
    "archaeology",
    "archaeological",
    "excavation",
    "rescue archaeology",
    "preventive archaeology",
    "archaeological monitoring",
    "archaeological survey",
    "archaeological assessment",
    "cultural heritage",
    "historic environment",
    "chance finds",
    "heritage management",
    "unesco",
    "monument",
    "archaeological investigation",
    "archaeological works",
    "archaeological services",
]

MAJOR = [
    "railway",
    "rail",
    "road",
    "highway",
    "mine",
    "mining",
    "copper",
    "lithium",
    "oil",
    "gas",
    "lng",
    "pipeline",
    "airport",
    "port",
    "dam",
    "hydroelectric",
    "solar",
    "wind",
    "energy",
    "refinery",
    "corridor",
    "metro",
    "subway",
    "transmission line",
    "power line",
]


# ============================================================
# TED
# ============================================================

TED_URL = "https://api.ted.europa.eu/v3/notices/search"

TED_FIELDS = [
    "publication-number",
    "publication-date",
    "notice-title",
    "buyer-name",
    "buyer-country",
    "classification-cpv",
    "notice-type",
]


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def repair_text(value):
    """
    Corrige casos de texto que tenham sido interpretados
    com a codificação errada, por exemplo:
    'archÃ©ologiques' -> 'archéologiques'
    'Malta â€“' -> 'Malta –'
    """

    if not isinstance(value, str):
        return value

    # Só tentamos reparar quando aparecem padrões típicos
    # de UTF-8 interpretado como Latin-1/Windows-1252.
    suspicious = (
        "Ã", "Â", "â", "ð", "Ð", "Ñ", "Ä", "Å",
        "Æ", "Ç", "Ë", "Î", "Ï", "Š", "™"
    )

    if not any(char in value for char in suspicious):
        return value

    try:
        repaired = value.encode("latin1").decode("utf-8")

        # Só aceitamos a reparação se realmente melhorar
        # os padrões suspeitos.
        old_count = sum(value.count(x) for x in suspicious)
        new_count = sum(repaired.count(x) for x in suspicious)

        if new_count < old_count:
            return repaired

    except (UnicodeEncodeError, UnicodeDecodeError):
        pass

    return value


def flatten(value):

    if value is None:
        return ""

    if isinstance(value, str):
        return repair_text(value)

    if isinstance(value, (int, float)):
        return str(value)

    if isinstance(value, list):

        values = []

        for item in value:

            text = flatten(item)

            if text:
                values.append(text)

        return " | ".join(values)

    if isinstance(value, dict):

        preferred = [
            "eng",
            "en",
            "por",
            "pt",
            "spa",
            "es",
            "fra",
            "fr",
        ]

        for key in preferred:

            if key in value:

                text = flatten(value[key])

                if text:
                    return text

        values = []

        for item in value.values():

            text = flatten(item)

            if text:
                values.append(text)

        return " | ".join(values)

    return str(value)


def clean_query(text):

    text = str(text or "").strip()

    text = re.sub(r'["\\]', " ", text)

    return text


# ============================================================
# CONSTRUIR CONSULTA TED
# ============================================================

def build_ted_query(q):

    q = clean_query(q)

    if not q:
        q = "archaeology"

    return f'FT~("{q}")'


# ============================================================
# CLASSIFICAÇÃO
# ============================================================

def classify(text):

    t = text.lower()

    archaeology_matches = [
        word for word in ARCH
        if word in t
    ]

    major_matches = [
        word for word in MAJOR
        if word in t
    ]

    a = len(archaeology_matches)
    m = len(major_matches)

    if a >= 2:

        return (
            "Arqueologia direta",
            min(100, 60 + a * 5 + m * 2)
        )

    if a >= 1:

        return (
            "Património cultural",
            min(100, 45 + a * 5 + m * 2)
        )

    if m:

        return (
            "Grande projeto / potencial subcontratação",
            min(100, 25 + m * 4)
        )

    return "Outro", 0


# ============================================================
# PESQUISA TED
# ============================================================

def ted(q):

    expert_query = build_ted_query(q)

    body = {
        "query": expert_query,
        "fields": TED_FIELDS,
        "limit": 100,
        "scope": "ACTIVE",
        "paginationMode": "PAGE_NUMBER",
        "page": 1,

        # False = executar a pesquisa
        # True = apenas validar a sintaxe
        "checkQuerySyntax": False,
    }

    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "Arqueologia-Radar/1.0",
    }

    last_error = None

    for attempt in range(3):

        try:

            response = requests.post(
                TED_URL,
                json=body,
                headers=headers,
                timeout=35,
            )

            if response.status_code in (
                429,
                500,
                502,
                503,
                504,
            ) and attempt < 2:

                time.sleep(2 ** attempt)
                continue

            if not response.ok:

                detail = response.text[:2000]

                raise RuntimeError(
                    f"TED HTTP {response.status_code}: {detail}"
                )

            # ==================================================
            # CORREÇÃO DE CODIFICAÇÃO
            # ==================================================
            #
            # Forçamos UTF-8 na resposta do TED.
            # Depois usamos response.content para fazer
            # a descodificação diretamente.
            #

            try:

                data_text = response.content.decode("utf-8")

                import json

                data = json.loads(data_text)

            except (UnicodeDecodeError, ValueError):

                # Fallback para o mecanismo habitual do requests
                data = response.json()

            break

        except Exception as exc:

            last_error = exc

            if attempt < 2:

                time.sleep(2 ** attempt)

            else:

                raise RuntimeError(
                    str(last_error)
                )

    if not isinstance(data, dict):

        raise RuntimeError(
            "O TED devolveu uma resposta inesperada."
        )

    notices = data.get("notices")

    if notices is None:
        notices = []

    results = []

    for notice in notices:

        if not isinstance(notice, dict):
            continue

        publication_number = flatten(
            notice.get("publication-number")
        )

        title = (
            flatten(notice.get("notice-title"))
            or "Concurso TED"
        )

        buyer = flatten(
            notice.get("buyer-name")
        )

        country = flatten(
            notice.get("buyer-country")
        )

        cpv = flatten(
            notice.get("classification-cpv")
        )

        notice_type = flatten(
            notice.get("notice-type")
        )

        publication_date = flatten(
            notice.get("publication-date")
        )

        full_text = " ".join([
            title,
            buyer,
            country,
            cpv,
            notice_type,
            flatten(notice),
        ])

        category, score = classify(full_text)

        if publication_number:

            url = (
                "https://ted.europa.eu/en/notice/"
                f"-/detail/{publication_number}"
            )

        else:

            url = "https://ted.europa.eu/en/search"

        results.append({

            "title": title,
            "source": "TED",
            "date": publication_date,
            "deadline": "",
            "country": country,
            "buyer": buyer,
            "cpv": cpv,
            "notice_type": notice_type,
            "url": url,
            "category": category,
            "score": score,

        })

    total = data.get("totalNoticeCount")

    return results, {

        "source": "TED",
        "ok": True,
        "count": len(results),
        "total": total,
        "query": expert_query,

    }


# ============================================================
# FONTES
# ============================================================

@app.get("/api/sources")
def sources():

    return [
        {
            "name": name,
            "region": region,
            "url": url,
            "mode": mode,
        }

        for name, region, url, mode in SOURCES
    ]


# ============================================================
# PESQUISA
# ============================================================

@app.get("/api/search")
def search(
    q: str = Query("archaeology"),
    region: str = "",
    category: str = "",
):

    results = []

    diagnostics = []

    try:

        ted_results, status = ted(q)

        results.extend(ted_results)

        diagnostics.append(status)

    except Exception as exc:

        diagnostics.append({

            "source": "TED",
            "ok": False,
            "count": 0,
            "error": str(exc),

        })

    # ========================================================
    # FILTRO DE REGIÃO
    # ========================================================

    if region:

        if region != "Europa":

            results = []

    # ========================================================
    # FILTRO DE CATEGORIA
    # ========================================================

    if category:

        results = [
            result
            for result in results
            if result.get("category") == category
        ]

    # ========================================================
    # ORDENAÇÃO
    # ========================================================

    results.sort(
        key=lambda x: (
            x.get("score", 0),
            x.get("date", ""),
        ),
        reverse=True,
    )

    return {

        "results": results,

        "diagnostics": diagnostics,

        "portal_count": sum(
            1
            for source in SOURCES
            if source[3] == "portal"
            and (
                not region
                or source[1] in (
                    region,
                    "Global",
                )
            )
        ),

        "api_count": sum(
            1
            for source in SOURCES
            if source[3] == "api"
        ),

        "searched_at": date.today().isoformat(),

    }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/api/health")
def health():

    return {

        "ok": True,
        "sources": len(SOURCES),
        "api_sources": sum(
            1
            for source in SOURCES
            if source[3] == "api"
        ),

    }


# ============================================================
# PÁGINA PRINCIPAL
# ============================================================

@app.get("/")
def home():

    return FileResponse(
        ROOT / "index.html"
    )


# ============================================================
# JAVASCRIPT
# ============================================================

@app.get("/app.js")
def js():

    return FileResponse(
        ROOT / "app.js",
        media_type="application/javascript",
    )


# ============================================================
# MANIFEST
# ============================================================

@app.get("/manifest.json")
def manifest():

    return FileResponse(
        ROOT / "manifest.json",
        media_type="application/manifest+json",
    )
