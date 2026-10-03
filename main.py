from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from pathlib import Path
from datetime import date, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
import re
import html
import unicodedata
import time


# ============================================================
# CONFIGURAÇÃO
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI(
    title="Arqueologia Radar",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PERIOD_DAYS = 365
PAGE_SIZE = 100
REQUEST_TIMEOUT = 30


# ============================================================
# FONTES API
# ============================================================

TED_URL = "https://api.ted.europa.eu/v3/notices/search"

WORLD_BANK_URL = "https://search.worldbank.org/api/v2/procnotices"


# ============================================================
# FONTES DO RADAR
# ============================================================

SOURCES = [

    # EUROPA
    {
        "name": "TED",
        "region": "Europa",
        "mode": "api",
        "url": "https://ted.europa.eu/"
    },

    {
        "name": "BASE Portugal",
        "region": "Portugal",
        "mode": "portal",
        "url": "https://www.base.gov.pt/"
    },

    {
        "name": "Contratación Pública España",
        "region": "Espanha",
        "mode": "portal",
        "url": "https://contrataciondelestado.es/"
    },

    # GLOBAL
    {
        "name": "World Bank Procurement",
        "region": "Global",
        "mode": "api",
        "url": "https://projects.worldbank.org/en/projects-operations/procurement"
    },

    {
        "name": "UNDB",
        "region": "Global",
        "mode": "portal",
        "url": "https://devbusiness.un.org/"
    },

    {
        "name": "UNGM",
        "region": "Global",
        "mode": "portal",
        "url": "https://www.ungm.org/"
    },

    {
        "name": "EBRD",
        "region": "Global",
        "mode": "portal",
        "url": "https://www.ebrd.com/"
    },

    {
        "name": "EIB",
        "region": "Global",
        "mode": "portal",
        "url": "https://www.eib.org/"
    },

    # ÁFRICA
    {
        "name": "African Development Bank",
        "region": "África",
        "mode": "portal",
        "url": "https://www.afdb.org/"
    },

    {
        "name": "AfDB Procurement Notices",
        "region": "África",
        "mode": "portal",
        "url": "https://www.afdb.org/en/projects-and-operations/procurement"
    },

    {
        "name": "South Africa",
        "region": "África",
        "mode": "portal",
        "url": "https://www.etenders.gov.za/"
    },

    {
        "name": "Uganda",
        "region": "África",
        "mode": "portal",
        "url": "https://www.ppda.go.ug/"
    },

    {
        "name": "Kenya",
        "region": "África",
        "mode": "portal",
        "url": "https://www.tenders.go.ke/"
    },

    {
        "name": "Tanzania",
        "region": "África",
        "mode": "portal",
        "url": "https://www.ppra.go.tz/"
    },

    {
        "name": "Mozambique",
        "region": "África",
        "mode": "portal",
        "url": "https://www.ufsa.gov.mz/"
    },

    {
        "name": "Morocco",
        "region": "África",
        "mode": "portal",
        "url": "https://www.marchespublics.gov.ma/"
    },

    # MÉDIO ORIENTE
    {
        "name": "Oman",
        "region": "Médio Oriente",
        "mode": "portal",
        "url": "https://etendering.tenderboard.gov.om/"
    },

    {
        "name": "Saudi Arabia Etimad",
        "region": "Médio Oriente",
        "mode": "portal",
        "url": "https://tenders.etimad.sa/"
    },

    {
        "name": "UAE",
        "region": "Médio Oriente",
        "mode": "portal",
        "url": "https://www.mof.gov.ae/"
    },

    {
        "name": "Qatar",
        "region": "Médio Oriente",
        "mode": "portal",
        "url": "https://monaqasat.mof.gov.qa/"
    },

    # AMÉRICAS
    {
        "name": "SAM.gov",
        "region": "Américas",
        "mode": "portal",
        "url": "https://sam.gov/"
    },

    {
        "name": "ChileCompra",
        "region": "Américas",
        "mode": "portal",
        "url": "https://www.mercadopublico.cl/"
    },

    {
        "name": "SECOP Colombia",
        "region": "Américas",
        "mode": "portal",
        "url": "https://www.colombiacompra.gov.co/"
    },

    {
        "name": "Compras Brasil",
        "region": "Américas",
        "mode": "portal",
        "url": "https://www.gov.br/compras/"
    },

    {
        "name": "IDB",
        "region": "Américas",
        "mode": "portal",
        "url": "https://www.iadb.org/"
    },

    # ÁSIA
    {
        "name": "Asian Development Bank",
        "region": "Ásia",
        "mode": "portal",
        "url": "https://www.adb.org/"
    },

    # OCEANIA
    {
        "name": "Australia",
        "region": "Oceânia",
        "mode": "portal",
        "url": "https://www.tenders.gov.au/"
    },

    {
        "name": "New Zealand",
        "region": "Oceânia",
        "mode": "portal",
        "url": "https://www.gets.govt.nz/"
    },

    # OUTROS
    {
        "name": "Global Procurement",
        "region": "Global",
        "mode": "portal",
        "url": "https://www.devbusiness.un.org/"
    }

]


# ============================================================
# TERMOS AUTOMÁTICOS DE ARQUEOLOGIA
# ============================================================

DEFAULT_TERMS = [

    "archaeology",
    "archaeological",
    "archaeological monitoring",
    "archaeological excavation",
    "archaeological services",
    "archaeological survey",
    "archaeological assessment",
    "archaeological investigation",
    "archaeological works",
    "excavation",
    "cultural heritage",
    "heritage",
    "historic environment",
    "chance finds",
    "heritage management",
    "unesco",
    "monument",
    "arqueologia",
    "património cultural",
    "patrimonio cultural"

]


# ============================================================
# TERMOS DE ARQUEOLOGIA DIRETA
# ============================================================

DIRECT_ARCHAEOLOGY_TERMS = [

    "archaeology",
    "archaeological",
    "archaeologic",
    "archaeological monitoring",
    "archaeological excavation",
    "archaeological services",
    "archaeological survey",
    "archaeological assessment",
    "archaeological investigation",
    "archaeological works",
    "archaeological study",
    "archaeological studies",
    "archaeological research",
    "archaeological watching brief",
    "archaeological watching",
    "archaeological evaluation",
    "archaeological impact assessment",
    "archaeological fieldwork",
    "archaeological supervision",
    "archaeological consultancy",
    "archaeological consultant",
    "archaeologist",
    "archaeologists",
    "archéologie",
    "archéologique",
    "arqueologia",
    "arqueológico",
    "arqueológica",
    "arqueológicos",
    "arqueológicas",
    "serviços de arqueologia",
    "servicos de arqueologia",
    "escavação arqueológica",
    "escavacao arqueologica"

]


# ============================================================
# CPV DE ARQUEOLOGIA
# ============================================================

ARCHAEOLOGY_CPVS = {

    "71351914",
    "71351910",
    "71351900",
    "71351720",
    "71351811",
    "45112450"

}


# ============================================================
# CPV DE SERVIÇOS NÃO ARQUEOLÓGICOS
# ============================================================

NON_ARCHAEOLOGY_CPV_PREFIXES = {

    "720",
    "480",
    "500",
    "600",
    "630",
    "640",
    "650",
    "660",
    "700",
    "730",
    "750",
    "790",
    "800",
    "850",
    "900",
    "920",
    "980"
}


# ============================================================
# GRANDES PROJETOS
# ============================================================

MAJOR_PROJECT_TERMS = [

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
    "power line"

]


# ============================================================
# CAMPOS TED
# ============================================================

TED_FIELDS = [

    "publication-number",
    "publication-date",
    "notice-title",
    "buyer-name",
    "buyer-country",
    "classification-cpv",
    "notice-type",

    # PRAZO PRINCIPAL
    "deadline",

    # PRAZOS ESPECÍFICOS
    "deadline-date-lot",
    "deadline-receipt-request",
    "deadline-receipt-tender-date-lot",
    "deadline-receipt-tender-time-lot",

    "description-proc",
    "description-lot"

]


# ============================================================
# MAPA DE PAÍSES
# ============================================================

COUNTRY_NAMES = {

    "PT": "Portugal",
    "ES": "Espanha",
    "FR": "França",
    "DE": "Alemanha",
    "IT": "Itália",
    "NL": "Países Baixos",
    "BE": "Bélgica",
    "IE": "Irlanda",
    "AT": "Áustria",
    "PL": "Polónia",
    "CZ": "Chéquia",
    "SK": "Eslováquia",
    "HU": "Hungria",
    "RO": "Roménia",
    "BG": "Bulgária",
    "GR": "Grécia",
    "SE": "Suécia",
    "FI": "Finlândia",
    "DK": "Dinamarca",
    "NO": "Noruega",
    "CH": "Suíça",
    "UK": "Reino Unido",

    "MA": "Marrocos",
    "DZ": "Argélia",
    "TN": "Tunísia",
    "EG": "Egito",
    "ZA": "África do Sul",
    "MZ": "Moçambique",
    "AO": "Angola",
    "KE": "Quénia",
    "UG": "Uganda",
    "TZ": "Tanzânia",

    "US": "Estados Unidos",
    "CA": "Canadá",
    "MX": "México",
    "BR": "Brasil",
    "CL": "Chile",
    "CO": "Colômbia",
    "AR": "Argentina",

    "AU": "Austrália",
    "NZ": "Nova Zelândia",

    "SA": "Arábia Saudita",
    "AE": "Emirados Árabes Unidos",
    "QA": "Qatar",
    "OM": "Omã",

    "IN": "Índia",
    "CN": "China",
    "JP": "Japão",
    "KR": "Coreia do Sul"

}


COUNTRY_NAMES_3 = {

    "PRT": "Portugal",
    "ESP": "Espanha",
    "FRA": "França",
    "DEU": "Alemanha",
    "ITA": "Itália",
    "NLD": "Países Baixos",
    "BEL": "Bélgica",
    "IRL": "Irlanda",
    "AUT": "Áustria",
    "POL": "Polónia",
    "CZE": "Chéquia",
    "SVK": "Eslováquia",
    "HUN": "Hungria",
    "ROU": "Roménia",
    "BGR": "Bulgária",
    "GRC": "Grécia",
    "SWE": "Suécia",
    "FIN": "Finlândia",
    "DNK": "Dinamarca",
    "NOR": "Noruega",
    "CHE": "Suíça",
    "GBR": "Reino Unido",

    "MAR": "Marrocos",
    "DZA": "Argélia",
    "TUN": "Tunísia",
    "EGY": "Egito",
    "ZAF": "África do Sul",
    "MOZ": "Moçambique",
    "AGO": "Angola",
    "KEN": "Quénia",
    "UGA": "Uganda",
    "TZA": "Tanzânia",

    "USA": "Estados Unidos",
    "CAN": "Canadá",
    "MEX": "México",
    "BRA": "Brasil",
    "CHL": "Chile",
    "COL": "Colômbia",
    "ARG": "Argentina",

    "AUS": "Austrália",
    "NZL": "Nova Zelândia",

    "SAU": "Arábia Saudita",
    "ARE": "Emirados Árabes Unidos",
    "QAT": "Qatar",
    "OMN": "Omã",

    "IND": "Índia",
    "CHN": "China",
    "JPN": "Japão",
    "KOR": "Coreia do Sul"

}


# ============================================================
# FUNÇÕES GERAIS
# ============================================================

def today_utc():

    return datetime.utcnow().date()


def cutoff_date():

    return today_utc() - timedelta(
        days=PERIOD_DAYS
    )


def flatten(value):

    if value is None:
        return ""

    if isinstance(value, list):

        return " ".join(
            flatten(item)
            for item in value
        )

    if isinstance(value, dict):

        return " ".join(
            flatten(item)
            for item in value.values()
        )

    return str(value)


# ============================================================
# CORREÇÃO DE CODIFICAÇÃO
# ============================================================

def repair_mojibake(value):

    if value is None:
        return ""

    if not isinstance(value, str):
        return value

    text = value

    suspicious = (
        "Ã" in text
        or "Â" in text
        or "â€" in text
        or "â€“" in text
        or "â€”" in text
        or "â€™" in text
        or "Å" in text
        or "Ð" in text
        or "Ñ" in text
        or "Î" in text
        or "Ï" in text
        or "Ä" in text
    )

    if not suspicious:
        return text

    try:

        repaired = text.encode(
            "latin1"
        ).decode(
            "utf-8"
        )

        return repaired

    except Exception:

        return text


def repair_structure(value):

    if isinstance(value, str):

        return repair_mojibake(
            value
        )

    if isinstance(value, list):

        return [
            repair_structure(item)
            for item in value
        ]

    if isinstance(value, dict):

        return {
            key: repair_structure(item)
            for key, item in value.items()
        }

    return value


def clean_query(value):

    if value is None:
        return ""

    value = str(value).strip()

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value


def normalize_text(value):

    value = flatten(value)

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
        char
        for char in value
        if not unicodedata.combining(
            char
        )
    )

    return value.lower()


# ============================================================
# LIMPEZA DOS TÍTULOS TED
# ============================================================

def choose_multilingual_text(value):

    """
    Quando o TED devolve um campo multilingue como dicionário,
    escolhe primeiro o inglês e depois outras línguas disponíveis.
    """

    if value is None:
        return ""

    if isinstance(value, dict):

        preferred_keys = [
            "eng",
            "en",
            "por",
            "pt",
            "fra",
            "fr",
            "spa",
            "es"
        ]

        for key in preferred_keys:

            if key in value:

                selected = choose_multilingual_text(
                    value.get(key)
                )

                if selected:
                    return selected

        for item in value.values():

            selected = choose_multilingual_text(
                item
            )

            if selected:
                return selected

        return ""

    if isinstance(value, list):

        for item in value:

            selected = choose_multilingual_text(
                item
            )

            if selected:
                return selected

        return ""

    return str(value)


def clean_ted_title(title):

    # --------------------------------------------------------
    # 1. Se o TED devolver estrutura multilingue,
    #    escolher uma língua individual.
    # --------------------------------------------------------

    title = choose_multilingual_text(
        title
    )

    title = repair_mojibake(
        title
    )

    title = html.unescape(
        title
    )

    title = re.sub(
        r"\s+",
        " ",
        title
    ).strip()

    if not title:
        return ""

    # --------------------------------------------------------
    # 2. O TED pode devolver uma cadeia contendo todas
    #    as traduções consecutivamente.
    #
    #    Exemplo:
    #
    #    França – ... – Fouilles archéologiques ...
    #    France – ... – Fouilles archéologiques ...
    #
    #    Nesse caso procuramos partes repetidas.
    # --------------------------------------------------------

    parts = re.split(
        r"\s+–\s+|\s+-\s+",
        title
    )

    parts = [
        part.strip()
        for part in parts
        if part.strip()
    ]

    if len(parts) >= 6:

        candidates = []

        for part in parts:

            clean_part = re.sub(
                r"\s+",
                " ",
                part
            ).strip()

            if len(clean_part) < 12:
                continue

            candidates.append(
                clean_part
            )

        # ----------------------------------------------------
        # Procurar partes que aparecem várias vezes.
        # Normalmente é o verdadeiro título do concurso.
        # ----------------------------------------------------

        repetitions = {}

        for candidate in candidates:

            normalized = normalize_text(
                candidate
            )

            repetitions.setdefault(
                normalized,
                {
                    "count": 0,
                    "text": candidate
                }
            )

            repetitions[
                normalized
            ]["count"] += 1

        repeated = [

            item

            for item in repetitions.values()

            if item["count"] >= 2

        ]

        if repeated:

            repeated.sort(

                key=lambda item: (
                    item["count"],
                    len(item["text"])
                ),

                reverse=True

            )

            selected = repeated[0]["text"]

            # Evitar escolher apenas o nome genérico
            # "Archaeological services" quando existe
            # um título mais específico.

            generic_titles = {

                "archaeological services",
                "servicios arqueologicos",
                "services archeologiques",
                "servizi archeologici",
                "servicos arqueologicos",
                "servicos de arheologie",
                "servicii de arheologie",
                "archaeologische untersuchungen",
                "archeologische diensten",
                "arheologisk services",
                "arkeologiska tjanster",
                "uslugi archeologiczne",
                "arheologicke sluzby",
                "archaeological service"

            }

            if normalize_text(
                selected
            ) not in generic_titles:

                return selected

            # Se o primeiro resultado repetido for genérico,
            # procurar outro título repetido mais específico.

            for item in repeated[1:]:

                candidate = item["text"]

                if normalize_text(
                    candidate
                ) not in generic_titles:

                    return candidate

            return selected

    # --------------------------------------------------------
    # 3. Fallback:
    #    manter apenas os primeiros segmentos.
    # --------------------------------------------------------

    simple_parts = re.split(
        r"\s+–\s+",
        title
    )

    if len(simple_parts) >= 4:

        # Procurar o primeiro segmento suficientemente
        # comprido depois do nome do país/serviço.

        for part in simple_parts:

            part = part.strip()

            if len(part) >= 25:

                return part

        return " – ".join(
            simple_parts[:3]
        )

    return title


# ============================================================
# DATAS
# ============================================================

def parse_date(value):

    if not value:
        return None

    if isinstance(value, date):
        return value

    if isinstance(value, dict):

        for item in value.values():

            result = parse_date(
                item
            )

            if result:
                return result

        return None

    if isinstance(value, list):

        for item in value:

            result = parse_date(
                item
            )

            if result:
                return result

        return None

    value = str(value).strip()

    if not value:
        return None

    try:

        return datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00"
            )
        ).date()

    except Exception:
        pass

    match = re.search(
        r"\d{4}-\d{2}-\d{2}",
        value
    )

    if match:

        try:

            return datetime.strptime(
                match.group(0),
                "%Y-%m-%d"
            ).date()

        except Exception:
            pass

    try:

        return datetime.strptime(
            value[:10],
            "%Y-%m-%d"
        ).date()

    except Exception:
        pass

    try:

        return datetime.strptime(
            value[:10],
            "%d/%m/%Y"
        ).date()

    except Exception:
        pass

    return None


# ============================================================
# EXTRAIR DATA DE ESTRUTURAS TED
# ============================================================

def find_date_in_structure(value):

    if value is None:
        return ""

    if isinstance(value, dict):

        preferred_keys = [

            "date",
            "value",
            "date-value",
            "deadline",
            "deadline-date",
            "deadlineDate",
            "deadline-date-lot",
            "deadlineDateLot",
            "deadline-receipt-tender-date-lot",
            "deadlineReceiptTenderDateLot"

        ]

        for key in preferred_keys:

            if key in value:

                found = find_date_in_structure(
                    value.get(key)
                )

                if found:
                    return found

        for item in value.values():

            found = find_date_in_structure(
                item
            )

            if found:
                return found

        return ""

    if isinstance(value, list):

        for item in value:

            found = find_date_in_structure(
                item
            )

            if found:
                return found

        return ""

    text = str(value)

    match = re.search(
        r"\d{4}-\d{2}-\d{2}",
        text
    )

    if match:

        return match.group(0)

    match = re.search(
        r"\d{2}/\d{2}/\d{4}",
        text
    )

    if match:

        return match.group(0)

    return ""


# ============================================================
# PAÍS
# ============================================================

def extract_country(notice):

    value = (
        notice.get("buyer-country")
        or notice.get("buyerCountry")
        or notice.get("country")
        or ""
    )

    value = flatten(
        value
    ).strip()

    value = repair_mojibake(
        value
    )

    if not value:
        return ""

    upper = value.upper()

    if upper in COUNTRY_NAMES_3:
        return COUNTRY_NAMES_3[upper]

    if upper in COUNTRY_NAMES:
        return COUNTRY_NAMES[upper]

    parts = value.split()

    if len(parts) > 1:

        unique_parts = []

        for part in parts:

            clean_part = part.strip()

            if (
                clean_part
                and clean_part.upper()
                not in [
                    existing.upper()
                    for existing in unique_parts
                ]
            ):

                unique_parts.append(
                    clean_part
                )

        if len(unique_parts) == 1:

            unique_value = (
                unique_parts[0]
            )

            unique_upper = (
                unique_value.upper()
            )

            if unique_upper in COUNTRY_NAMES_3:

                return COUNTRY_NAMES_3[
                    unique_upper
                ]

            if unique_upper in COUNTRY_NAMES:

                return COUNTRY_NAMES[
                    unique_upper
                ]

            return unique_value

    return value


# ============================================================
# CPV
# ============================================================

def extract_cpvs(notice):

    values = []

    possible_fields = [

        notice.get(
            "classification-cpv"
        ),

        notice.get(
            "classificationCpv"
        ),

        notice.get(
            "cpv"
        ),

        notice.get(
            "cpvs"
        )

    ]

    for value in possible_fields:

        if not value:
            continue

        if isinstance(
            value,
            list
        ):

            values.extend(
                flatten(item)
                for item in value
            )

        else:

            values.append(
                flatten(value)
            )

    result = []

    for value in values:

        matches = re.findall(
            r"\d{8}",
            value
        )

        result.extend(
            matches
        )

    return list(
        dict.fromkeys(
            result
        )
    )


# ============================================================
# DEADLINE
# ============================================================
def extract_deadline(notice):
    """
    Extrai a data limite de apresentação de propostas do TED/eForms.

    Prioridade:
    1. BT-131 / TenderSubmissionDeadlinePeriod
    2. deadline-date-lot
    3. deadline-receipt-tender-date-lot
    4. outros campos TED/eForms relacionados
    """

    if not isinstance(notice, (dict, list)):
        return ""

    # ------------------------------------------------------------
    # Procura recursivamente uma data dentro de uma estrutura.
    # ------------------------------------------------------------
    def find_date(value):
        if value is None:
            return ""

        if isinstance(value, str):
            value = value.strip()

            # ISO: 2026-10-27
            match = re.search(
                r"\b(20\d{2}-\d{2}-\d{2})(?:[T\s]|$)",
                value
            )

            if match:
                return match.group(1)

            # Também aceita data ISO com offset:
            # 2026-10-27+02:00
            match = re.search(
                r"\b(20\d{2}-\d{2}-\d{2})[+-]\d{2}:\d{2}\b",
                value
            )

            if match:
                return match.group(1)

            return ""

        if isinstance(value, dict):

            # Primeiro procurar explicitamente EndDate,
            # que é a estrutura oficial do BT-131.
            priority_keys = [
                "EndDate",
                "endDate",
                "end-date",
                "deadline",
                "deadlineDate",
                "deadline-date",
                "deadline-date-lot",
                "deadline-receipt-tender-date-lot",
                "deadlineReceiptTenderDateLot",
            ]

            for key in priority_keys:
                if key in value:
                    result = find_date(value[key])
                    if result:
                        return result

            # Depois pesquisar recursivamente.
            for key, item in value.items():
                result = find_date(item)
                if result:
                    return result

            return ""

        if isinstance(value, list):
            for item in value:
                result = find_date(item)
                if result:
                    return result

        return ""

    # ------------------------------------------------------------
    # 1. Estrutura oficial eForms:
    #
    # TenderSubmissionDeadlinePeriod
    #     EndDate
    #     EndTime
    #
    # ------------------------------------------------------------
    deadline_structures = [
        "TenderSubmissionDeadlinePeriod",
        "tenderSubmissionDeadlinePeriod",
        "tender-submission-deadline-period",
        "TenderSubmissionDeadline",
        "tenderSubmissionDeadline",
    ]

    def search_named_structure(value):

        if isinstance(value, dict):

            for key in deadline_structures:
                if key in value:
                    result = find_date(value[key])
                    if result:
                        return result

            for item in value.values():
                result = search_named_structure(item)
                if result:
                    return result

        elif isinstance(value, list):

            for item in value:
                result = search_named_structure(item)
                if result:
                    return result

        return ""

    deadline = search_named_structure(notice)

    if deadline:
        return deadline

    # ------------------------------------------------------------
    # 2. Campos TED/eForms conhecidos
    # ------------------------------------------------------------
    possible_fields = [
        "deadline-date-lot",
        "deadline-receipt-tender-date-lot",
        "deadline-receipt-request",
        "deadline-date",
        "deadline",
        "deadlineDate",
        "deadlineDateLot",
        "deadlineReceiptTenderDateLot",
        "deadlineReceiptRequest",
        "BT-131",
        "BT-131-Lot",
        "BT-131(d)-Lot",
    ]

    def search_fields(value):

        if isinstance(value, dict):

            for key in possible_fields:
                if key in value:
                    result = find_date(value[key])
                    if result:
                        return result

            for item in value.values():
                result = search_fields(item)
                if result:
                    return result

        elif isinstance(value, list):

            for item in value:
                result = search_fields(item)
                if result:
                    return result

        return ""

    deadline = search_fields(notice)

    if deadline:
        return deadline

    return ""


# ============================================================
# CLASSIFICAÇÃO
# ============================================================

def has_direct_archaeology_term(
    text
):

    normalized = normalize_text(
        text
    )

    for term in DIRECT_ARCHAEOLOGY_TERMS:

        term_normalized = normalize_text(
            term
        )

        if term_normalized in normalized:

            return True

    return False


def is_non_archaeology_cpv(
    cpvs
):

    for cpv in cpvs:

        cpv = str(cpv)

        if len(cpv) >= 3:

            if cpv[:3] in NON_ARCHAEOLOGY_CPV_PREFIXES:

                return True

    return False


def classify_result(
    title,
    description,
    cpvs
):

    title_text = normalize_text(
        title
    )

    description_text = normalize_text(
        description
    )

    combined_text = (
        title_text
        + " "
        + description_text
    )

    cpv_archaeology = any(

        cpv in ARCHAEOLOGY_CPVS

        for cpv in cpvs

    )

    if cpv_archaeology:

        direct_hits = 0

        for term in DIRECT_ARCHAEOLOGY_TERMS:

            if normalize_text(term) in combined_text:

                direct_hits += 1

        score = min(
            100,
            85 + direct_hits * 3
        )

        return (
            "Arqueologia direta",
            score
        )

    direct_hits = 0

    for term in DIRECT_ARCHAEOLOGY_TERMS:

        if normalize_text(term) in combined_text:

            direct_hits += 1

    if direct_hits:

        score = min(
            100,
            65 + direct_hits * 5
        )

        if is_non_archaeology_cpv(cpvs):

            title_has_archaeology = (
                has_direct_archaeology_term(
                    title_text
                )
            )

            if not title_has_archaeology:

                return (
                    "Património / potencial arqueológico",
                    min(
                        55,
                        score
                    )
                )

        return (
            "Arqueologia direta",
            score
        )

    heritage_terms = [

        "cultural heritage",
        "heritage",
        "historic environment",
        "chance finds",
        "heritage management",
        "patrimonio cultural",
        "patrimonio",
        "património cultural",
        "património",
        "monument",
        "unesco"

    ]

    heritage_hits = 0

    for term in heritage_terms:

        if normalize_text(term) in combined_text:

            heritage_hits += 1

    if heritage_hits:

        score = min(
            70,
            35 + heritage_hits * 5
        )

        return (
            "Património / potencial arqueológico",
            score
        )

    major_hits = 0

    for term in MAJOR_PROJECT_TERMS:

        if normalize_text(term) in combined_text:

            major_hits += 1

    if major_hits:

        score = min(
            65,
            25 + major_hits * 4
        )

        return (
            "Grande projeto / potencial subcontratação",
            score
        )

    return (
        "Outro",
        10
    )


# ============================================================
# QUERY TED
# ============================================================

def clean_ted_title(title):
    """
    Limpa títulos TED/eForms que possam vir com várias versões linguísticas.
    Mantém apenas uma versão curta e legível.
    """
    if title is None:
        return ""

    title = flatten(title)
    title = repair_mojibake(title)
    title = html.unescape(title)
    title = re.sub(r"\s+", " ", title).strip()

    if not title:
        return ""

    # Separadores típicos usados quando o TED devolve várias versões
    # linguísticas do mesmo título.
    parts = re.split(r"\s+[–—-]\s+", title)

    # Remove partes vazias
    parts = [p.strip() for p in parts if p.strip()]

    if len(parts) <= 2:
        return title

    # Detecta blocos repetidos do tipo:
    # País – Título
    # País – Título
    # País – Título
    #
    # Nestes casos ficamos com o último bloco, que normalmente
    # corresponde à versão principal devolvida pelo TED.
    country_title_candidates = []

    for i in range(0, len(parts) - 1, 2):
        country = parts[i].strip()
        subject = parts[i + 1].strip()

        if (
            len(country) <= 80
            and len(subject) >= 3
            and not re.search(r"\b(202[0-9]|20[0-9]{2})\b", country)
        ):
            country_title_candidates.append(
                f"{country} – {subject}"
            )

    if country_title_candidates:
        # Preferimos a última versão linguística.
        candidate = country_title_candidates[-1]

        if len(candidate) <= 220:
            return candidate

    # Caso o título não siga o padrão País – Título,
    # procurar blocos repetidos e conservar o último segmento
    # suficientemente informativo.
    long_parts = [p for p in parts if len(p) >= 10]

    if long_parts:
        candidate = long_parts[-1]

        if len(candidate) <= 220:
            return candidate

    # Última salvaguarda: limite de tamanho sem cortar no meio
    if len(title) > 220:
        return title[:217].rstrip() + "..."

    return title


# ============================================================
# CONVERTER AVISO TED EM RESULTADO
# ============================================================

def notice_to_result(
    notice
):

    notice = repair_structure(
        notice
    )

    publication_date = (
        notice.get(
            "publication-date"
        )
        or notice.get(
            "publicationDate"
        )
        or ""
    )

    parsed_date = parse_date(
        publication_date
    )

    if (
        parsed_date
        and parsed_date < cutoff_date()
    ):

        return None

    title = (
        notice.get(
            "notice-title"
        )
        or notice.get(
            "noticeTitle"
        )
        or ""
    )

    title = clean_ted_title(
        title
    )

    buyer = (
        notice.get(
            "buyer-name"
        )
        or notice.get(
            "buyerName"
        )
        or ""
    )

    country = extract_country(
        notice
    )

    cpvs = extract_cpvs(
        notice
    )

    description = " ".join(
        [
            flatten(
                notice.get(
                    "description-proc",
                    ""
                )
            ),
            flatten(
                notice.get(
                    "description-lot",
                    ""
                )
            )
        ]
    )

    category, score = classify_result(
        title,
        description,
        cpvs
    )

    publication_number = (
        notice.get(
            "publication-number"
        )
        or notice.get(
            "publicationNumber"
        )
        or ""
    )

    deadline = extract_deadline(
        notice
    )

    url = ""

    if publication_number:

        url = (
            "https://ted.europa.eu/"
            "en/notice/-/detail/"
            + str(
                publication_number
            )
        )

    return {

        "title":
            title,

        "buyer":
            flatten(
                buyer
            ),

        "country":
            country,

        "date":
            flatten(
                publication_date
            ),

        "deadline":
            flatten(
                deadline
            ),

        "cpv":
            cpvs,

        "category":
            category,

        "score":
            score,

        "source":
            "TED",

        "url":
            url,

        "publication_number":
            flatten(
                publication_number
            ),

        "description":
            flatten(
                description
            )

    }


# ============================================================
# PESQUISA TED
# ============================================================

def query_ted(
    term
):

    query = build_ted_query(
        term
    )

    payload = {

        "query": query,

        "fields": TED_FIELDS,

        "page": 1,

        "limit": PAGE_SIZE,

        "scope": "ACTIVE",

        "checkQuerySyntax": False,

        "paginationMode":
            "PAGE_NUMBER",

        "onlyLatestVersions":
            True

    }

    last_error = None

    for attempt in range(3):

        try:

            response = requests.post(
                TED_URL,
                json=payload,
                timeout=REQUEST_TIMEOUT
            )

            if response.status_code >= 400:

                error_text = response.text

                try:

                    error_json = (
                        response.json()
                    )

                except Exception:

                    error_json = None

                return [], {

                    "source":
                        "TED",

                    "term":
                        term,

                    "ok":
                        False,

                    "count":
                        0,

                    "query_sent":
                        query,

                    "status_code":
                        response.status_code,

                    "error":
                        error_text,

                    "error_json":
                        error_json

                }

            data = response.json()

            data = repair_structure(
                data
            )

            notices = (
                data.get(
                    "notices",
                    []
                )
            )

            results = []

            for notice in notices:

                result = notice_to_result(
                    notice
                )

                if result:

                    results.append(
                        result
                    )

            status = {

                "source":
                    "TED",

                "term":
                    term,

                "ok":
                    True,

                "count":
                    len(results),

                "query":
                    query

            }

            return results, status

        except Exception as exc:

            last_error = str(
                exc
            )

            time.sleep(
                1
            )

    return [], {

        "source":
            "TED",

        "term":
            term,

        "ok":
            False,

        "count":
            0,

        "query_sent":
            query,

        "error":
            last_error

    }


# ============================================================
# WORLD BANK
# ============================================================

def query_world_bank(
    term
):

    term = clean_query(
        term
    )

    params = {

        "qterm": term,

        "format": "json",

        "rows": PAGE_SIZE,

        "os": 0

    }

    try:

        response = requests.get(
            WORLD_BANK_URL,
            params=params,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

        data = repair_structure(
            data
        )

        results = []

        notices = []

        if isinstance(
            data,
            dict
        ):

            for key in (
                "procnotices",
                "notices",
                "results"
            ):

                value = data.get(
                    key
                )

                if isinstance(
                    value,
                    list
                ):

                    notices = value

                    break

                if isinstance(
                    value,
                    dict
                ):

                    notices = list(
                        value.values()
                    )

                    break

        for notice in notices:

            if not isinstance(
                notice,
                dict
            ):

                continue

            title = (
                notice.get(
                    "project_name"
                )
                or notice.get(
                    "notice_title"
                )
                or notice.get(
                    "title"
                )
                or ""
            )

            buyer = (
                notice.get(
                    "borrower"
                )
                or notice.get(
                    "buyer"
                )
                or notice.get(
                    "country"
                )
                or ""
            )

            description = (
                notice.get(
                    "description"
                )
                or notice.get(
                    "notice_description"
                )
                or ""
            )

            country = (
                notice.get(
                    "country"
                )
                or ""
            )

            deadline = (
                notice.get(
                    "submission_deadline"
                )
                or notice.get(
                    "deadline"
                )
                or ""
            )

            publication_date = (
                notice.get(
                    "publication_date"
                )
                or notice.get(
                    "date"
                )
                or ""
            )

            category, score = classify_result(
                title,
                description,
                []
            )

            # ====================================================
            # FILTRO WORLD BANK
            #
            # O World Bank devolve muitos projetos gerais.
            # Só mantemos resultados com alguma relação
            # identificável com arqueologia ou património.
            # ====================================================

            if category == "Outro":

                continue

            results.append({

                "title":
                    flatten(title),

                "buyer":
                    flatten(buyer),

                "country":
                    flatten(country),

                "date":
                    flatten(
                        publication_date
                    ),

                "deadline":
                    flatten(deadline),

                "cpv": [],

                "category":
                    category,

                "score":
                    score,

                "source":
                    "World Bank Procurement",

                "url":
                    "https://projects.worldbank.org/"
                    "en/projects-operations/"
                    "procurement",

                "publication_number":
                    "",

                "description":
                    flatten(description)

            })

        return results, {

            "source":
                "World Bank Procurement",

            "term":
                term,

            "ok":
                True,

            "count":
                len(results)

        }

    except Exception as exc:

        return [], {

            "source":
                "World Bank Procurement",

            "term":
                term,

            "ok":
                False,

            "count":
                0,

            "error":
                str(exc)

        }


# ============================================================
# DEDUPLICAÇÃO
# ============================================================

def deduplicate_results(
    results
):

    unique = {}

    for result in results:

        key = (

            normalize_text(
                result.get(
                    "title",
                    ""
                )
            ),

            normalize_text(
                result.get(
                    "buyer",
                    ""
                )
            ),

            normalize_text(
                result.get(
                    "country",
                    ""
                )
            )

        )

        if key not in unique:

            unique[key] = result

        else:

            if (
                result.get(
                    "score",
                    0
                )
                >
                unique[key].get(
                    "score",
                    0
                )
            ):

                unique[key] = result

    return list(
        unique.values()
    )


# ============================================================
# FILTRO DE REGIÃO
# ============================================================

def region_matches(
    result,
    region
):

    if not region:

        return True

    region = normalize_text(
        region
    )

    country = normalize_text(
        result.get(
            "country",
            ""
        )
    )

    mapping = {

        "europa": [
            "portugal",
            "espanha",
            "franca",
            "alemanha",
            "italia",
            "paises baixos",
            "belgica",
            "irlanda",
            "austria",
            "polonia",
            "chequia",
            "eslovaquia",
            "hungria",
            "romenia",
            "bulgaria",
            "grecia",
            "suecia",
            "finlandia",
            "dinamarca",
            "noruega",
            "suica",
            "reino unido"
        ],

        "africa": [
            "marrocos",
            "argelia",
            "tunisia",
            "egito",
            "africa do sul",
            "mocambique",
            "angola",
            "quenia",
            "uganda",
            "tanzania"
        ],

        "americas": [
            "estados unidos",
            "canada",
            "mexico",
            "brasil",
            "chile",
            "colombia",
            "argentina"
        ],

        "medio oriente": [
            "arabia saudita",
            "emirados arabes unidos",
            "qatar",
            "oma"
        ],

        "asia": [
            "india",
            "china",
            "japao",
            "coreia do sul"
        ],

        "oceania": [
            "australia",
            "nova zelandia"
        ]

    }

    countries = mapping.get(
        region,
        []
    )

    return any(
        country_name in country
        for country_name in countries
    )


# ============================================================
# ENDPOINT SEARCH
# ============================================================

@app.get("/api/search")
def search(
    q: str = Query(
        "archaeology"
    ),
    region: str = "",
    category: str = ""
):

    results = []

    diagnostics = []

    user_query = clean_query(
        q
    )

    automatic_mode = (
        not user_query
        or user_query.lower()
        == "archaeology"
    )

    if automatic_mode:

        search_terms = [

            "archaeological excavation",
            "archaeological monitoring",
            "archaeological services",
            "archaeology",
            "archaeological",
            "excavation",
            "cultural heritage",
            "heritage",
            "archaeological survey",
            "archaeological assessment"

        ]

        world_bank_terms = [

            "archaeology",
            "archaeological",
            "cultural heritage",
            "archaeological excavation"

        ]

    else:

        search_terms = [
            user_query
        ]

        world_bank_terms = [
            user_query
        ]

    # --------------------------------------------------------
    # REMOVER TERMOS DUPLICADOS
    # --------------------------------------------------------

    clean_terms = []

    for term in search_terms:

        if term.lower() not in [
            x.lower()
            for x in clean_terms
        ]:

            clean_terms.append(
                term
            )

    clean_world_bank_terms = []

    for term in world_bank_terms:

        if term.lower() not in [
            x.lower()
            for x in clean_world_bank_terms
        ]:

            clean_world_bank_terms.append(
                term
            )

    # --------------------------------------------------------
    # EXECUÇÃO EM PARALELO
    # --------------------------------------------------------

    tasks = []

    with ThreadPoolExecutor(
        max_workers=10
    ) as executor:

        for term in clean_terms:

            tasks.append(
                executor.submit(
                    query_ted,
                    term
                )
            )

        for term in clean_world_bank_terms:

            tasks.append(
                executor.submit(
                    query_world_bank,
                    term
                )
            )

        for future in as_completed(
            tasks
        ):

            try:

                task_results, status = (
                    future.result()
                )

                results.extend(
                    task_results
                )

                diagnostics.append(
                    status
                )

            except Exception as exc:

                diagnostics.append({

                    "source":
                        "API",

                    "ok":
                        False,

                    "count":
                        0,

                    "error":
                        str(exc)

                })

    # --------------------------------------------------------
    # DEDUPLICAÇÃO
    # --------------------------------------------------------

    results = deduplicate_results(
        results
    )

    # --------------------------------------------------------
    # FILTRO DE REGIÃO
    # --------------------------------------------------------

    if region:

        results = [

            result

            for result in results

            if region_matches(
                result,
                region
            )

        ]

    # --------------------------------------------------------
    # FILTRO DE CATEGORIA
    # --------------------------------------------------------

    if category:

        results = [

            result

            for result in results

            if result.get(
                "category"
            )
            == category

        ]

    # --------------------------------------------------------
    # REMOVER DEADLINES EXPIRADOS
    # --------------------------------------------------------

    filtered_results = []

    today = today_utc()

    for result in results:

        deadline_text = result.get(
            "deadline",
            ""
        )

        deadline_date = parse_date(
            deadline_text
        )

        if deadline_date:

            if deadline_date < today:

                continue

        filtered_results.append(
            result
        )

    results = filtered_results

    # --------------------------------------------------------
    # ORDENAÇÃO
    # --------------------------------------------------------

    def result_date(
        result
    ):

        parsed = parse_date(
            result.get(
                "date",
                ""
            )
        )

        if parsed:

            return parsed

        return date.min

    results.sort(

        key=lambda item: (

            result_date(item),

            item.get(
                "score",
                0
            )

        ),

        reverse=True

    )

    # --------------------------------------------------------
    # CONTADORES
    # --------------------------------------------------------

    api_count = sum(

        1

        for source in SOURCES

        if source["mode"]
        == "api"

    )

    portal_count = sum(

        1

        for source in SOURCES

        if source["mode"]
        == "portal"

        and (

            not region

            or source["region"]
            in (
                region,
                "Global"
            )

        )

    )

    # --------------------------------------------------------
    # RESPOSTA
    # --------------------------------------------------------

    return {

        "ok":
            True,

        "query":
            q,

        "region":
            region,

        "category":
            category,

        "results":
            results,

        "count":
            len(results),

        "sources":
            len(SOURCES),

        "api_sources":
            api_count,

        "portal_count":
            portal_count,

        "diagnostics":
            diagnostics,

        "searched_at":
            today_utc().isoformat()

    }


# ============================================================
# TESTE TED - MARROCOS
# ============================================================

@app.get("/api/test-ted-country")
def test_ted_country():

    test_query = (
        'FT~"works" '
        'AND buyer-country=MAR'
    )

    payload = {

        "query":
            test_query,

        "fields":
            TED_FIELDS,

        "page":
            1,

        "limit":
            PAGE_SIZE,

        "scope":
            "ACTIVE",

        "checkQuerySyntax":
            False,

        "paginationMode":
            "PAGE_NUMBER",

        "onlyLatestVersions":
            True

    }

    try:

        response = requests.post(

            TED_URL,

            json=payload,

            timeout=REQUEST_TIMEOUT

        )

        return {

            "ok":
                True,

            "status_code":
                response.status_code,

            "query":
                test_query,

            "response":
                response.json()

        }

    except Exception as exc:

        return {

            "ok":
                False,

            "query":
                test_query,

            "error":
                str(exc)

        }


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return {

        "ok":
            True,

        "service":
            "Arqueologia Radar",

        "sources":
            len(SOURCES),

        "api_sources":
            sum(
                1
                for source in SOURCES
                if source["mode"]
                == "api"
            ),

        "date":
            today_utc().isoformat()

    }


# ============================================================
# RAIZ
# ============================================================

@app.get("/")
def root():

    index_file = (
        BASE_DIR
        / "index.html"
    )

    if index_file.exists():

        return FileResponse(
            index_file
        )

    return JSONResponse({

        "ok":
            True,

        "message":
            "Arqueologia Radar"

    })


# ============================================================
# APP.JS
# ============================================================

@app.get("/app.js")
def app_js():

    app_file = (
        BASE_DIR
        / "app.js"
    )

    if app_file.exists():

        return FileResponse(
            app_file,
            media_type=
                "application/javascript"
        )

    return JSONResponse({

        "ok":
            False,

        "error":
            "app.js não encontrado"

    })


# ============================================================
# MANIFEST
# ============================================================

@app.get("/manifest.json")
def manifest():

    manifest_file = (
        BASE_DIR
        / "manifest.json"
    )

    if manifest_file.exists():

        return FileResponse(
            manifest_file,
            media_type=
                "application/json"
        )

    return JSONResponse({

        "name":
            "Arqueologia Radar",

        "short_name":
            "Radar",

        "start_url":
            "/",

        "display":
            "standalone"

    })
