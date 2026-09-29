from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from datetime import date, datetime, timedelta
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

REQUEST_TIMEOUT = 45


# ============================================================
# PORTAIS COMPLEMENTARES
# ============================================================

# O TED é a única fonte automática nesta versão.
# Os restantes portais ficam catalogados para consulta.
# A integração automática será acrescentada progressivamente.

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
# TERMOS DE PESQUISA / CLASSIFICAÇÃO
# ============================================================

ARCHAEOLOGY_TERMS = [
    "archaeolog",
    "archaeological",
    "archaeology",
    "archaeologist",
    "archaeologists",
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
    "archäologie",
    "archäolog",
    "heritage",
    "cultural heritage",
    "archaeological heritage",
    "historic heritage",
    "monuments",
    "monument",
    "heritage assessment",
    "heritage impact",
    "cultural property",
    "cultural assets",
    "historic environment",
    "archaeological monitoring",
    "archaeological survey",
    "archaeological investigation",
    "archaeological excavation",
    "archaeological evaluation",
    "watching brief",
    "archaeological watching",
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
    "gas pipeline",
    "water pipeline",
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
    "housing development",
    "industrial park",
    "metro",
    "tram",
    "hydroelectric",
    "irrigation",
]


# ============================================================
# TED FIELDS
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
    "deadline",
    "deadline-date-lot",
    "deadline-date-part",
]


# ============================================================
# UTILITÁRIOS
# ============================================================

def repair_text(value):
    """
    Corrige alguns casos de mojibake que podem surgir
    quando texto UTF-8 é interpretado como Windows-1252/Latin-1.
    """

    if value is None:
        return ""

    if not isinstance(value, str):
        return str(value)

    text = html.unescape(value)

    # Corrigir apenas quando há fortes indícios de mojibake.
    bad_markers = (
        "Ã",
        "Â",
        "â€",
        "ðŸ",
        "Ð",
        "Ñ",
        "Ä",
        "Å",
        "Ç",
        "È",
        "É",
        "Ê",
        "Ë",
        "Î",
        "Ï",
        "Ô",
        "Õ",
        "Ö",
        "Ø",
        "Ù",
        "Ú",
        "Ü",
        "Ý",
    )

    if any(marker in text for marker in bad_markers):
        try:
            repaired = text.encode("latin1").decode("utf-8")

            # Só aceitar se a transformação reduzir sinais de corrupção.
            old_bad = sum(text.count(x) for x in bad_markers)
            new_bad = sum(repaired.count(x) for x in bad_markers)

            if new_bad <= old_bad:
                text = repaired
        except Exception:
            pass

    return text.strip()


def flatten(value):
    """
    Transforma estruturas TED em texto simples.
    """

    if value is None:
        return ""

    if isinstance(value, str):
        return repair_text(value)

    if isinstance(value, (int, float, bool)):
        return str(value)

    if isinstance(value, list):
        parts = []

        for item in value:
            part = flatten(item)

            if part:
                parts.append(part)

        return " | ".join(parts)

    if isinstance(value, dict):
        preferred = [
            "value",
            "text",
            "content",
            "name",
            "label",
            "date",
            "id",
        ]

        for key in preferred:
            if key in value:
                result = flatten(value[key])

                if result:
                    return result

        parts = []

        for key, item in value.items():
            result = flatten(item)

            if result:
                parts.append(result)

        return " | ".join(parts)

    return str(value)


def clean_query(q):
    q = repair_text(q or "").strip()

    q = re.sub(r"\s+", " ", q)

    return q


def normalise_key(value):
    """
    Normalização para deduplicação.
    """

    value = repair_text(value or "").lower()

    value = unicodedata.normalize(
        "NFKD",
        value,
    )

    value = "".join(
        c for c in value
        if not unicodedata.combining(c)
    )

    value = re.sub(r"[^a-z0-9]+", " ", value)

    value = re.sub(r"\s+", " ", value).strip()

    return value


def parse_date(value):
    """
    Converte datas TED para date.
    """

    if not value:
        return None

    text = flatten(value).strip()

    # ISO date/time
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

    # DD/MM/YYYY
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

    # YYYYMMDD
    match = re.search(
        r"\b(\d{4})(\d{2})(\d{2})\b",
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

    return None


def format_date(value):
    parsed = parse_date(value)

    if not parsed:
        return repair_text(value)

    return parsed.strftime("%d/%m/%Y")


def first_non_empty(data, keys):
    for key in keys:

        if key not in data:
            continue

        value = flatten(data.get(key))

        if value:
            return value

    return ""


def extract_notice_number(notice):
    return first_non_empty(
        notice,
        [
            "publication-number",
            "publicationNumber",
            "notice-publication-number",
        ],
    )


def extract_procedure_id(notice):
    return first_non_empty(
        notice,
        [
            "procedure-identifier",
            "procedureIdentifier",
            "procedure-id",
        ],
    )


def extract_publication_date(notice):
    return first_non_empty(
        notice,
        [
            "publication-date",
            "publicationDate",
            "notice-publication-date",
        ],
    )


def extract_deadline(notice):
    """
    TED disponibiliza o campo 'deadline-date-lot'
    e também o campo agregado 'deadline'.

    Tentamos primeiro os campos específicos e depois
    o agregado.
    """

    value = first_non_empty(
        notice,
        [
            "deadline-date-lot",
            "deadline-date-part",
            "deadline",
        ],
    )

    return value


def extract_title(notice):
    return first_non_empty(
        notice,
        [
            "notice-title",
            "title",
        ],
    )


def extract_buyer(notice):
    return first_non_empty(
        notice,
        [
            "buyer-name",
            "buyerName",
            "organisation-name-buyer",
            "organization-name-buyer",
        ],
    )


def extract_country(notice):
    return first_non_empty(
        notice,
        [
            "buyer-country",
            "buyerCountry",
            "country",
        ],
    )


def extract_cpv(notice):
    return first_non_empty(
        notice,
        [
            "classification-cpv",
            "classificationCpv",
            "cpv",
        ],
    )


def extract_notice_type(notice):
    return first_non_empty(
        notice,
        [
            "notice-type",
            "noticeType",
            "form-type",
        ],
    )


def build_ted_query(q):
    q = clean_query(q)

    if not q:
        q = "archaeology"

    return f"FT~({q})"


# ============================================================
# CLASSIFICAÇÃO
# ============================================================

def contains_term(text, terms):
    normalized = normalise_key(text)

    for term in terms:
        term_normalized = normalise_key(term)

        if term_normalized and term_normalized in normalized:
            return True

    return False


def classify_result(title, buyer, cpv):
    text = " ".join(
        [
            title or "",
            buyer or "",
            cpv or "",
        ]
    )

    archaeology = contains_term(
        text,
        ARCHAEOLOGY_TERMS,
    )

    major = contains_term(
        text,
        MAJOR_PROJECT_TERMS,
    )

    # CPV específico para arqueologia.
    cpv_normalized = normalise_key(cpv)

    if "71351914" in cpv_normalized:
        return "Arqueologia direta"

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
    """
    Pontuação de relevância.
    Não representa qualidade da entidade contratante:
    é apenas uma prioridade interna do Radar.
    """

    text = " ".join(
        [
            title or "",
            buyer or "",
            cpv or "",
        ]
    )

    score = 20

    normalized = normalise_key(text)

    if "71351914" in normalise_key(cpv):
        score += 45

    if contains_term(
        normalized,
        [
            "archaeological excavation",
            "archaeological monitoring",
            "archaeological survey",
            "archaeological evaluation",
            "archaeological investigation",
        ],
    ):
        score += 20

    elif contains_term(
        normalized,
        ARCHAEOLOGY_TERMS,
    ):
        score += 12

    if category == "Acompanhamento arqueológico":
        score += 12

    elif category == "Arqueologia direta":
        score += 15

    elif category == "Arqueologia / Património":
        score += 8

    elif category == "Grande projeto / potencial subcontratação":
        score += 5

    publication = parse_date(publication_date)

    if publication:
        age = (date.today() - publication).days

        if age <= 30:
            score += 15

        elif age <= 90:
            score += 10

        elif age <= RESULTS_DAYS:
            score += 5

    deadline_date = parse_date(deadline)

    if deadline_date:
        days_to_deadline = (
            deadline_date - date.today()
        ).days

        if 0 <= days_to_deadline <= 14:
            score += 15

        elif 14 < days_to_deadline <= 30:
            score += 10

        elif 30 < days_to_deadline <= 90:
            score += 5

    return min(score, 100)


# ============================================================
# ESTADO
# ============================================================

def determine_status(
    publication_date,
    deadline,
):
    publication = parse_date(publication_date)
    deadline_date = parse_date(deadline)

    today = date.today()

    if deadline_date:

        if deadline_date < today:
            return "Prazo terminado"

        if deadline_date == today:
            return "Prazo termina hoje"

        days = (
            deadline_date - today
        ).days

        if days <= 7:
            return "Prazo termina em breve"

        if days <= 30:
            return "Em prazo"

        return "Em prazo"

    if publication:
        age = (
            today - publication
        ).days

        if age <= RESULTS_DAYS:
            return "Publicação recente"

        return "Ativo — publicação anterior"

    return "Estado não identificado"


# ============================================================
# URL TED
# ============================================================

def build_ted_url(publication_number):
    if not publication_number:
        return "https://ted.europa.eu/"

    return (
        "https://ted.europa.eu/en/notice/-/detail/"
        + publication_number
    )


# ============================================================
# TED
# ============================================================

def search_ted(q):
    expert_query = build_ted_query(q)

    body = {
        "query": expert_query,

        "fields": TED_FIELDS,

        "limit": 250,

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
                "Accept": "application/json",
                "Content-Type": "application/json",
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

        if not isinstance(notices, list):
            notices = []

        results = []

        recent_cutoff = (
            date.today()
            - timedelta(days=RESULTS_DAYS)
        )

        skipped_irrelevant = 0
        skipped_old_without_deadline = 0

        for notice in notices:

            if not isinstance(notice, dict):
                continue

            title = extract_title(notice)
            buyer = extract_buyer(notice)
            country = extract_country(notice)
            cpv = extract_cpv(notice)
            notice_type = extract_notice_type(notice)

            publication_number = extract_notice_number(
                notice
            )

            procedure_id = extract_procedure_id(
                notice
            )

            publication_date = extract_publication_date(
                notice
            )

            deadline = extract_deadline(
                notice
            )

            publication_parsed = parse_date(
                publication_date
            )

            deadline_parsed = parse_date(
                deadline
            )

            # ------------------------------------------------
            # Confirmar que existe relevância arqueológica.
            # ------------------------------------------------

            searchable_text = " ".join(
                [
                    title,
                    buyer,
                    country,
                    cpv,
                    notice_type,
                ]
            )

            is_archaeological = contains_term(
                searchable_text,
                ARCHAEOLOGY_TERMS,
            )

            is_archaeological_cpv = (
                "71351914"
                in normalise_key(cpv)
            )

            if not (
                is_archaeological
                or is_archaeological_cpv
            ):
                skipped_irrelevant += 1
                continue

            # ------------------------------------------------
            # Não eliminamos automaticamente concursos
            # antigos que o TED classifica como ACTIVE.
            #
            # Mas guardamos a informação para mostrar
            # ao utilizador que a publicação é antiga.
            # ------------------------------------------------

            if (
                publication_parsed
                and publication_parsed < recent_cutoff
                and not deadline_parsed
            ):
                skipped_old_without_deadline += 1

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

            # ------------------------------------------------
            # Chave de deduplicação
            #
            # Primeiro usamos o procedure-identifier.
            # Quando não existe, usamos publication-number.
            # Em último recurso usamos título + comprador.
            # ------------------------------------------------

            if procedure_id:
                dedup_key = (
                    "procedure:"
                    + normalise_key(procedure_id)
                )

            elif publication_number:
                dedup_key = (
                    "publication:"
                    + normalise_key(publication_number)
                )

            else:
                dedup_key = (
                    "title:"
                    + normalise_key(title)
                    + "|buyer:"
                    + normalise_key(buyer)
                )

            results.append(
                {
                    "title": repair_text(title),

                    "source": "TED",

                    "date": format_date(
                        publication_date
                    ),

                    "publication_date": (
                        publication_parsed.isoformat()
                        if publication_parsed
                        else ""
                    ),

                    "deadline": format_date(
                        deadline
                    ),

                    "deadline_date": (
                        deadline_parsed.isoformat()
                        if deadline_parsed
                        else ""
                    ),

                    "status": status,

                    "country": repair_text(
                        country
                    ),

                    "buyer": repair_text(
                        buyer
                    ),

                    "cpv": repair_text(
                        cpv
                    ),

                    "notice_type": repair_text(
                        notice_type
                    ),

                    "publication_number": (
                        publication_number
                    ),

                    "procedure_id": (
                        procedure_id
                    ),

                    "category": category,

                    "score": score,

                    "url": build_ted_url(
                        publication_number
                    ),

                    "_dedup_key": dedup_key,
                }
            )

        # ====================================================
        # DEDUPLICAÇÃO
        # ====================================================

        unique = {}

        for result in results:

            key = result["_dedup_key"]

            if key not in unique:
                unique[key] = result
                continue

            old = unique[key]

            # Preferimos o aviso mais recente.
            new_date = parse_date(
                result.get("date")
            )

            old_date = parse_date(
                old.get("date")
            )

            replace = False

            if new_date and old_date:

                if new_date > old_date:
                    replace = True

                elif (
                    new_date == old_date
                    and result["score"] > old["score"]
                ):
                    replace = True

            elif new_date and not old_date:
                replace = True

            elif (
                result["score"]
                > old["score"]
            ):
                replace = True

            if replace:
                unique[key] = result

        results = list(unique.values())

        # ====================================================
        # ORDENAR
        #
        # Primeiro relevância.
        # Depois prazo.
        # Depois publicação.
        # ====================================================

        def sort_key(item):

            deadline_date = parse_date(
                item.get("deadline")
            )

            publication_date = parse_date(
                item.get("date")
            )

            # Prazo futuro recebe prioridade.
            if deadline_date:
                deadline_rank = (
                    1
                    if deadline_date >= date.today()
                    else 0
                )
            else:
                deadline_rank = 0

            deadline_timestamp = (
                deadline_date.toordinal()
                if deadline_date
                else 0
            )

            publication_timestamp = (
                publication_date.toordinal()
                if publication_date
                else 0
            )

            return (
                item["score"],
                deadline_rank,
                deadline_timestamp,
                publication_timestamp,
            )

        results.sort(
            key=sort_key,
            reverse=True,
        )

        # Retirar chave interna.
        for result in results:
            result.pop(
                "_dedup_key",
                None,
            )

        diagnostics = {
            "source": "TED",
            "ok": True,
            "count": len(results),
            "total": data.get(
                "totalNoticeCount"
            ),
            "query": expert_query,
            "period_days": RESULTS_DAYS,
            "from_date": recent_cutoff.isoformat(),
            "active_scope": True,
            "skipped_irrelevant": skipped_irrelevant,
            "old_active_without_deadline":
                skipped_old_without_deadline,
        }

        return results, diagnostics

    except requests.exceptions.Timeout:

        return [], {
            "source": "TED",
            "ok": False,
            "count": 0,
            "total": None,
            "query": expert_query,
            "error": (
                "O TED demorou demasiado tempo "
                "a responder."
            ),
        }

    except requests.exceptions.RequestException as exc:

        return [], {
            "source": "TED",
            "ok": False,
            "count": 0,
            "total": None,
            "query": expert_query,
            "error": (
                "Erro de comunicação com o TED: "
                + str(exc)
            ),
        }

    except Exception as exc:

        return [], {
            "source": "TED",
            "ok": False,
            "count": 0,
            "total": None,
            "query": expert_query,
            "error": (
                "Erro ao processar resposta TED: "
                + str(exc)
            ),
        }


# ============================================================
# API — SOURCES
# ============================================================

@app.get("/api/sources")
def api_sources():

    return SOURCES


# ============================================================
# API — SEARCH
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

    q = clean_query(q)

    if not q:
        q = "archaeology"

    results, ted_diagnostic = search_ted(q)

    # --------------------------------------------------------
    # Filtros do interface
    # --------------------------------------------------------

    if region:

        region_normalized = normalise_key(
            region
        )

        results = [
            result
            for result in results
            if region_normalized
            in normalise_key(
                result.get(
                    "country",
                    "",
                )
            )
            or region_normalized
            == "europa"
        ]

    if category:

        category_normalized = normalise_key(
            category
        )

        filtered = []

        for result in results:

            result_category = normalise_key(
                result.get(
                    "category",
                    "",
                )
            )

            if (
                category_normalized
                in result_category
                or result_category
                in category_normalized
            ):
                filtered.append(result)

        results = filtered

    return {
        "results": results,

        "diagnostics": [
            ted_diagnostic
        ],

        "portal_count": len(
            SOURCES
        ),

        "api_count": sum(
            1
            for source in SOURCES
            if source.get("mode") == "api"
        ),

        "searched_at": date.today().isoformat(),
    }


# ============================================================
# API — HEALTH
# ============================================================

@app.get("/api/health")
def api_health():

    return {
        "ok": True,
        "sources": len(SOURCES),
        "api_sources": sum(
            1
            for source in SOURCES
            if source.get("mode") == "api"
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
