from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from datetime import date, timedelta
from pathlib import Path

import requests
import re
import json
import html
import unicodedata


# ============================================================
# CONFIGURAÇÃO
# ============================================================

ROOT = Path(__file__).resolve().parent

app = FastAPI(title="Arqueologia Radar")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TED_URL = "https://api.ted.europa.eu/v3/notices/search"

RESULTS_DAYS = 365

REQUEST_TIMEOUT = 30


# ============================================================
# PORTAIS
# ============================================================

SOURCES = [
    {
        "name": "TED – Tenders Electronic Daily",
        "region": "Europa",
        "url": "https://ted.europa.eu/",
        "mode": "api",
    },
    {
        "name": "Portugal – BASE",
        "region": "Europa",
        "url": "https://www.base.gov.pt/",
        "mode": "portal",
    },
    {
        "name": "Portugal – Diário da República",
        "region": "Europa",
        "url": "https://diariodarepublica.pt/",
        "mode": "portal",
    },
    {
        "name": "Espanha – Plataforma de Contratación",
        "region": "Europa",
        "url": "https://contrataciondelestado.es/",
        "mode": "portal",
    },
    {
        "name": "França – BOAMP",
        "region": "Europa",
        "url": "https://www.boamp.fr/",
        "mode": "portal",
    },
    {
        "name": "França – PLACE",
        "region": "Europa",
        "url": "https://www.marches-publics.gouv.fr/",
        "mode": "portal",
    },
    {
        "name": "Itália – Acquisti in rete PA",
        "region": "Europa",
        "url": "https://www.acquistinretepa.it/",
        "mode": "portal",
    },
    {
        "name": "Alemanha – Bund.de",
        "region": "Europa",
        "url": "https://www.service.bund.de/",
        "mode": "portal",
    },
    {
        "name": "Países Baixos – TenderNed",
        "region": "Europa",
        "url": "https://www.tenderned.nl/",
        "mode": "portal",
    },
    {
        "name": "Bélgica – e-Procurement",
        "region": "Europa",
        "url": "https://www.publicprocurement.be/",
        "mode": "portal",
    },
    {
        "name": "Irlanda – eTenders",
        "region": "Europa",
        "url": "https://www.etenders.gov.ie/",
        "mode": "portal",
    },
    {
        "name": "Reino Unido – Find a Tender",
        "region": "Europa",
        "url": "https://www.find-tender.service.gov.uk/",
        "mode": "portal",
    },
    {
        "name": "Noruega – Doffin",
        "region": "Europa",
        "url": "https://www.doffin.no/",
        "mode": "portal",
    },
    {
        "name": "Suécia – Mercell",
        "region": "Europa",
        "url": "https://www.mercell.com/",
        "mode": "portal",
    },
    {
        "name": "Dinamarca – Udbud",
        "region": "Europa",
        "url": "https://www.udbud.dk/",
        "mode": "portal",
    },
    {
        "name": "Finlândia – Hilma",
        "region": "Europa",
        "url": "https://www.hankintailmoitukset.fi/",
        "mode": "portal",
    },
    {
        "name": "Áustria – ANKÖ",
        "region": "Europa",
        "url": "https://www.ankoe.at/",
        "mode": "portal",
    },
    {
        "name": "Polónia – BZP",
        "region": "Europa",
        "url": "https://ezamowienia.gov.pl/",
        "mode": "portal",
    },
    {
        "name": "República Checa – NEN",
        "region": "Europa",
        "url": "https://nen.nipez.cz/",
        "mode": "portal",
    },
    {
        "name": "Roménia – SICAP",
        "region": "Europa",
        "url": "https://www.e-licitatie.ro/",
        "mode": "portal",
    },
    {
        "name": "Croácia – EOJN",
        "region": "Europa",
        "url": "https://eojn.hr/",
        "mode": "portal",
    },
    {
        "name": "Eslovénia – e-JN",
        "region": "Europa",
        "url": "https://ejn.gov.si/",
        "mode": "portal",
    },
    {
        "name": "Estónia – Riigihanked",
        "region": "Europa",
        "url": "https://riigihanked.riik.ee/",
        "mode": "portal",
    },
    {
        "name": "Lituânia – CVP IS",
        "region": "Europa",
        "url": "https://viesiejipirkimai.lt/",
        "mode": "portal",
    },
    {
        "name": "Letónia – EIS",
        "region": "Europa",
        "url": "https://www.eis.gov.lv/",
        "mode": "portal",
    },
    {
        "name": "Grécia – Promitheus",
        "region": "Europa",
        "url": "https://www.promitheus.gov.gr/",
        "mode": "portal",
    },
    {
        "name": "Malta – ePPS",
        "region": "Europa",
        "url": "https://www.etenders.gov.mt/",
        "mode": "portal",
    },
    {
        "name": "Banco Mundial – Procurement",
        "region": "Internacional",
        "url": "https://projects.worldbank.org/en/projects-operations/procurement",
        "mode": "portal",
    },
]


# ============================================================
# TERMOS
# ============================================================

ARCHAEOLOGY_TERMS = [
    "archaeolog",
    "archaeological",
    "archaeology",
    "archaeologist",
    "excavat",
    "archéolog",
    "archaeologische",
    "archäolog",
    "archeolog",
    "arqueolog",
    "arqueología",
    "arqueologia",
    "archeologia",
    "archéologie",
    "archäologie",
    "heritage",
    "cultural heritage",
    "archaeological heritage",
    "historic heritage",
    "monument",
    "heritage assessment",
    "heritage impact",
    "cultural property",
    "historic environment",
    "archaeological monitoring",
    "archaeological survey",
    "archaeological investigation",
    "archaeological excavation",
    "archaeological evaluation",
    "watching brief",
    "rescue archaeology",
    "preventive archaeology",
    "underwater archaeology",
    "maritime archaeology",
    "industrial archaeology",
    "building archaeology",
    "landscape archaeology",
]

MAJOR_PROJECT_TERMS = [
    "railway",
    "rail",
    "high speed rail",
    "road",
    "motorway",
    "highway",
    "bridge",
    "tunnel",
    "airport",
    "port",
    "harbour",
    "harbor",
    "dam",
    "reservoir",
    "pipeline",
    "power line",
    "electricity",
    "substation",
    "wind farm",
    "solar farm",
    "photovoltaic",
    "offshore wind",
    "renewable energy",
    "energy infrastructure",
    "infrastructure",
    "construction",
    "urban development",
    "development project",
    "industrial park",
    "metro",
    "tram",
    "hydroelectric",
    "irrigation",
]


# ============================================================
# TED
#
# Máximo de 10 campos por página.
# ============================================================

TED_FIELDS = [
    "publication-number",
    "publication-date",
    "notice-title",
    "buyer-name",
    "buyer-country",
    "classification-cpv",
    "notice-type",
    "procedure-identifier",
    "deadline-receipt-tender-date-lot",
    "deadline-receipt-tender-time-lot",
]


# ============================================================
# TEXTO / CODIFICAÇÃO
# ============================================================

def repair_text(value):
    if value is None:
        return ""

    text = html.unescape(str(value))

    for _ in range(2):
        if not any(
            marker in text
            for marker in [
                "Ã", "Â", "â€", "ðŸ",
                "Ð", "Ñ", "Ä", "Å",
                "Ç", "È", "É", "Ê",
            ]
        ):
            break

        try:
            repaired = text.encode(
                "latin1"
            ).decode(
                "utf-8"
            )

            text = repaired

        except Exception:
            break

    return text.strip()


def flatten(value):
    if value is None:
        return ""

    if isinstance(value, str):
        return repair_text(value)

    if isinstance(value, (int, float, bool)):
        return str(value)

    if isinstance(value, list):
        return " | ".join(
            x for x in
            [flatten(item) for item in value]
            if x
        )

    if isinstance(value, dict):

        for key in [
            "value",
            "text",
            "content",
            "name",
            "label",
            "date",
            "id",
        ]:
            if key in value:
                result = flatten(value[key])

                if result:
                    return result

        return " | ".join(
            x for x in
            [flatten(item) for item in value.values()]
            if x
        )

    return str(value)


def normalise_key(value):
    text = repair_text(value).lower()

    text = unicodedata.normalize(
        "NFKD",
        text,
    )

    text = "".join(
        c for c in text
        if not unicodedata.combining(c)
    )

    text = re.sub(
        r"[^a-z0-9]+",
        " ",
        text,
    )

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


# ============================================================
# TÍTULO TED
# ============================================================

def clean_ted_title(title, query=""):
    """
    O TED devolve o notice-title com várias versões linguísticas.

    Exemplo:
    Malta – Archaeological services – ...
    Malta – Servicios arqueológicos – ...
    Malta – Services archéologiques – ...

    Preferimos a versão inglesa.
    """

    title = repair_text(title)

    if not title:
        return ""

    parts = [
        repair_text(part)
        for part in title.split("|")
    ]

    parts = [
        part.strip()
        for part in parts
        if part.strip()
    ]

    # Procurar explicitamente a versão inglesa.
    english_markers = [
        "archaeological services",
        "archaeological monitoring",
        "archaeological excavation",
        "archaeological survey",
        "archaeological investigation",
        "archaeological evaluation",
        "cultural heritage",
        "heritage services",
        "archaeology",
    ]

    for part in parts:
        normalized = normalise_key(part)

        if any(
            marker in normalized
            for marker in [
                normalise_key(x)
                for x in english_markers
            ]
        ):
            return part

    # Se a pesquisa foi feita por uma expressão inglesa,
    # tentar encontrar essa expressão no título.
    q = normalise_key(query)

    if q:
        query_words = [
            word
            for word in q.split()
            if len(word) > 3
        ]

        for part in parts:

            normalized = normalise_key(part)

            if query_words and all(
                word in normalized
                for word in query_words
            ):
                return part

    # Último recurso:
    # escolher a primeira versão disponível.
    return parts[0] if parts else title


# ============================================================
# DATAS
# ============================================================

def parse_date(value):
    if not value:
        return None

    text = flatten(value)

    match = re.search(
        r"(\d{4})-(\d{2})-(\d{2})",
        text,
    )

    if match:
        try:
            return date(
                int(match.group(1)),
                int(match.group(2)),
                int(match.group(3)),
            )
        except Exception:
            pass

    match = re.search(
        r"(\d{2})/(\d{2})/(\d{4})",
        text,
    )

    if match:
        try:
            return date(
                int(match.group(3)),
                int(match.group(2)),
                int(match.group(1)),
            )
        except Exception:
            pass

    return None


def format_date(value):
    parsed = parse_date(value)

    if not parsed:
        return ""

    return parsed.strftime("%d/%m/%Y")


def first_value(data, keys):
    for key in keys:

        if key not in data:
            continue

        value = flatten(data[key])

        if value:
            return value

    return ""


# ============================================================
# CLASSIFICAÇÃO
# ============================================================

def contains_term(text, terms):
    normalized = normalise_key(text)

    return any(
        normalise_key(term) in normalized
        for term in terms
    )


def classify_result(
    title,
    buyer,
    cpv,
):
    text = " ".join([
        title,
        buyer,
        cpv,
    ])

    cpv_clean = normalise_key(cpv)

    if "71351914" in cpv_clean:
        return "Arqueologia direta"

    archaeology = contains_term(
        text,
        ARCHAEOLOGY_TERMS,
    )

    major = contains_term(
        text,
        MAJOR_PROJECT_TERMS,
    )

    if archaeology and major:
        return "Acompanhamento arqueológico"

    if archaeology:
        return "Arqueologia / Património"

    if major:
        return "Grande projeto / potencial subcontratação"

    return "Outro"


def calculate_score(
    title,
    buyer,
    cpv,
    publication_date,
    deadline,
    category,
):
    score = 20

    text = " ".join([
        title,
        buyer,
        cpv,
    ])

    cpv_clean = normalise_key(cpv)

    if "71351914" in cpv_clean:
        score += 45

    if contains_term(
        text,
        [
            "archaeological monitoring",
            "archaeological excavation",
            "archaeological survey",
            "archaeological investigation",
            "archaeological evaluation",
        ],
    ):
        score += 20

    elif contains_term(
        text,
        ARCHAEOLOGY_TERMS,
    ):
        score += 12

    if category == "Arqueologia direta":
        score += 15

    elif category == "Acompanhamento arqueológico":
        score += 12

    elif category == "Arqueologia / Património":
        score += 8

    publication = parse_date(
        publication_date
    )

    if publication:

        age = (
            date.today()
            - publication
        ).days

        if age <= 30:
            score += 15

        elif age <= 90:
            score += 10

        elif age <= RESULTS_DAYS:
            score += 5

    deadline_date = parse_date(
        deadline
    )

    if deadline_date:

        days = (
            deadline_date
            - date.today()
        ).days

        if 0 <= days <= 14:
            score += 15

        elif 14 < days <= 30:
            score += 10

        elif 30 < days <= 90:
            score += 5

    return min(
        score,
        100,
    )


# ============================================================
# ESTADO
# ============================================================

def determine_status(
    publication_date,
    deadline,
):
    today = date.today()

    deadline_date = parse_date(
        deadline
    )

    publication = parse_date(
        publication_date
    )

    if deadline_date:

        days = (
            deadline_date
            - today
        ).days

        if days < 0:
            return "Prazo terminado"

        if days == 0:
            return "Prazo termina hoje"

        if days <= 7:
            return "Prazo termina em breve"

        return "Em prazo"

    if publication:

        age = (
            today
            - publication
        ).days

        if age <= RESULTS_DAYS:
            return "Publicação recente"

        return "Ativo — publicação anterior"

    return "Estado não identificado"


# ============================================================
# TED QUERY
# ============================================================

def build_ted_query(q):
    q = repair_text(
        q or ""
    ).strip()

    if not q:
        q = "archaeology"

    return f"FT~({q})"


# ============================================================
# TED URL
# ============================================================

def build_ted_url(
    publication_number
):
    if not publication_number:
        return "https://ted.europa.eu/"

    return (
        "https://ted.europa.eu/en/notice/-/detail/"
        + publication_number
    )


# ============================================================
# PESQUISA TED
# ============================================================

def search_ted(q):

    expert_query = build_ted_query(
        q
    )

    body = {
        "query": expert_query,

        "fields": TED_FIELDS,

        # 100 em vez de 250:
        # suficiente para o Radar e mais rápido.
        "limit": 100,

        "scope": "ACTIVE",

        "paginationMode": "PAGE_NUMBER",

        "page": 1,

        "checkQuerySyntax": False,
    }

    try:

        response = requests.post(
            TED_URL,
            json=body,
            headers={
                "Accept":
                    "application/json",

                "Content-Type":
                    "application/json",
            },
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        raw = response.content.decode(
            "utf-8",
            errors="replace",
        )

        data = json.loads(raw)

        notices = data.get(
            "notices",
            [],
        )

        if not isinstance(
            notices,
            list,
        ):
            notices = []

        results = []

        recent_cutoff = (
            date.today()
            - timedelta(
                days=RESULTS_DAYS
            )
        )

        skipped_irrelevant = 0

        for notice in notices:

            if not isinstance(
                notice,
                dict,
            ):
                continue

            raw_title = first_value(
                notice,
                [
                    "notice-title",
                    "title",
                ],
            )

            title = clean_ted_title(
                raw_title,
                q,
            )

            buyer = first_value(
                notice,
                [
                    "buyer-name",
                    "buyerName",
                ],
            )

            country = first_value(
                notice,
                [
                    "buyer-country",
                    "buyerCountry",
                    "country",
                ],
            )

            cpv = first_value(
                notice,
                [
                    "classification-cpv",
                    "classificationCpv",
                    "cpv",
                ],
            )

            notice_type = first_value(
                notice,
                [
                    "notice-type",
                    "noticeType",
                ],
            )

            publication_number = first_value(
                notice,
                [
                    "publication-number",
                    "publicationNumber",
                ],
            )

            procedure_id = first_value(
                notice,
                [
                    "procedure-identifier",
                    "procedureIdentifier",
                ],
            )

            publication_date = first_value(
                notice,
                [
                    "publication-date",
                    "publicationDate",
                ],
            )

            # CAMPO CORRETO PARA O PRAZO
            deadline = first_value(
                notice,
                [
                    "deadline-receipt-tender-date-lot",
                    "deadline-date-lot",
                    "deadline-date-part",
                    "deadline",
                ],
            )

            # =================================================
            # RELEVÂNCIA ARQUEOLÓGICA
            # =================================================

            searchable = " ".join([
                title,
                buyer,
                country,
                cpv,
                notice_type,
            ])

            archaeology_match = contains_term(
                searchable,
                ARCHAEOLOGY_TERMS,
            )

            archaeology_cpv = (
                "71351914"
                in normalise_key(cpv)
            )

            if not (
                archaeology_match
                or archaeology_cpv
            ):
                skipped_irrelevant += 1
                continue

            # =================================================
            # CLASSIFICAÇÃO
            # =================================================

            category = classify_result(
                title,
                buyer,
                cpv,
            )

            status = determine_status(
                publication_date,
                deadline,
            )

            score = calculate_score(
                title,
                buyer,
                cpv,
                publication_date,
                deadline,
                category,
            )

            # =================================================
            # DEDUPLICAÇÃO
            # =================================================

            if procedure_id:

                dedup_key = (
                    "procedure:"
                    + normalise_key(
                        procedure_id
                    )
                )

            elif publication_number:

                dedup_key = (
                    "publication:"
                    + normalise_key(
                        publication_number
                    )
                )

            else:

                dedup_key = (
                    normalise_key(title)
                    + "|"
                    + normalise_key(buyer)
                )

            results.append({
                "title": title,

                "source": "TED",

                "date": format_date(
                    publication_date
                ),

                "publication_date":
                    (
                        parse_date(
                            publication_date
                        ).isoformat()
                        if parse_date(
                            publication_date
                        )
                        else ""
                    ),

                "deadline": format_date(
                    deadline
                ),

                "deadline_date":
                    (
                        parse_date(
                            deadline
                        ).isoformat()
                        if parse_date(
                            deadline
                        )
                        else ""
                    ),

                "status": status,

                "country":
                    repair_text(country),

                "buyer":
                    repair_text(buyer),

                "cpv":
                    repair_text(cpv),

                "notice_type":
                    repair_text(
                        notice_type
                    ),

                "publication_number":
                    publication_number,

                "procedure_id":
                    procedure_id,

                "category":
                    category,

                "score":
                    score,

                "url":
                    build_ted_url(
                        publication_number
                    ),

                "_dedup_key":
                    dedup_key,
            })

        # ====================================================
        # DEDUPLICAÇÃO
        # ====================================================

        unique = {}

        for result in results:

            key = result[
                "_dedup_key"
            ]

            if key not in unique:
                unique[key] = result
                continue

            old = unique[key]

            new_date = parse_date(
                result["date"]
            )

            old_date = parse_date(
                old["date"]
            )

            if (
                new_date
                and (
                    not old_date
                    or new_date > old_date
                )
            ):
                unique[key] = result

            elif (
                new_date == old_date
                and result["score"]
                > old["score"]
            ):
                unique[key] = result

        results = list(
            unique.values()
        )

        # ====================================================
        # ORDENAÇÃO
        # ====================================================

        def ranking(item):

            deadline = parse_date(
                item["deadline"]
            )

            publication = parse_date(
                item["date"]
            )

            future_deadline = 0

            if deadline:
                if deadline >= date.today():
                    future_deadline = 1

            deadline_value = (
                deadline.toordinal()
                if deadline
                else 0
            )

            publication_value = (
                publication.toordinal()
                if publication
                else 0
            )

            return (
                item["score"],
                future_deadline,
                deadline_value,
                publication_value,
            )

        results.sort(
            key=ranking,
            reverse=True,
        )

        for result in results:
            result.pop(
                "_dedup_key",
                None,
            )

        diagnostic = {
            "source": "TED",

            "ok": True,

            "count": len(results),

            "total":
                data.get(
                    "totalNoticeCount"
                ),

            "query":
                expert_query,

            "period_days":
                RESULTS_DAYS,

            "from_date":
                recent_cutoff.isoformat(),

            "active_scope":
                True,

            "returned":
                len(notices),

            "skipped_irrelevant":
                skipped_irrelevant,
        }

        return results, diagnostic

    except requests.exceptions.Timeout:

        return [], {
            "source": "TED",
            "ok": False,
            "count": 0,
            "total": None,
            "query": expert_query,
            "error":
                "O TED demorou demasiado tempo a responder.",
        }

    except requests.exceptions.RequestException as exc:

        return [], {
            "source": "TED",
            "ok": False,
            "count": 0,
            "total": None,
            "query": expert_query,
            "error":
                "Erro de comunicação com o TED: "
                + str(exc),
        }

    except Exception as exc:

        return [], {
            "source": "TED",
            "ok": False,
            "count": 0,
            "total": None,
            "query": expert_query,
            "error":
                "Erro ao processar a resposta TED: "
                + str(exc),
        }


# ============================================================
# API SOURCES
# ============================================================

@app.get("/api/sources")
def api_sources():
    return SOURCES


# ============================================================
# API SEARCH
# ============================================================

@app.get("/api/search")
def api_search(
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

    q = repair_text(
        q or ""
    ).strip()

    if not q:
        q = "archaeology"

    results, diagnostic = search_ted(
        q
    )

    # ========================================================
    # FILTRO DE CATEGORIA
    # ========================================================

    if category:

        wanted = normalise_key(
            category
        )

        results = [
            result
            for result in results
            if wanted
            in normalise_key(
                result["category"]
            )
        ]

    # ========================================================
    # REGIÃO
    #
    # O TED devolve códigos de país.
    # Para já, o filtro Europa inclui os resultados TED.
    # ========================================================

    if region:

        if normalise_key(region) != "europa":
            results = []

    return {
        "results":
            results,

        "diagnostics":
            [diagnostic],

        "portal_count":
            len(SOURCES),

        "api_count":
            sum(
                1
                for source in SOURCES
                if source["mode"] == "api"
            ),

        "searched_at":
            date.today().isoformat(),
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def api_health():

    return {
        "ok": True,

        "sources":
            len(SOURCES),

        "api_sources":
            sum(
                1
                for source in SOURCES
                if source["mode"] == "api"
            ),
    }


# ============================================================
# FRONTEND
# ============================================================

@app.get("/")
def root():

    return FileResponse(
        ROOT / "index.html"
    )


@app.get("/app.js")
def javascript():

    return FileResponse(
        ROOT / "app.js",
        media_type="application/javascript",
    )


@app.get("/manifest.json")
def manifest():

    return FileResponse(
        ROOT / "manifest.json",
        media_type="application/manifest+json",
    )
