from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

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
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


TED_URL = "https://api.ted.europa.eu/v3/notices/search"

WORLD_BANK_URL = (
    "https://search.worldbank.org/api/v2/procnotices"
)

PERIOD_DAYS = 365
PAGE_SIZE = 100
REQUEST_TIMEOUT = 30


# ============================================================
# CPV ARQUEOLOGIA
# ============================================================

ARCHAEOLOGY_CPVS = {
    "71351914",
    "71351910",
    "71351900",
    "71351720",
    "71351811",
    "45112450",
}


# ============================================================
# TERMOS DE PESQUISA
# ============================================================

DEFAULT_TERMS = [
    "archaeology",
    "archaeological",
    "archaeological monitoring",
    "archaeological excavation",
    "archaeological services",
    "excavation",
    "cultural heritage",
    "heritage",
    "arqueologia",
    "património cultural",
    "patrimonio cultural",
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
    "deadline-receipt-tender-date-lot",
    "deadline-receipt-request-date-lot",
    "description-proc",
    "description-lot",
]


# ============================================================
# FONTES
# ============================================================

SOURCES = [
    {
        "name": "TED — Europa",
        "region": "Europa / Internacional",
        "type": "api",
    },
    {
        "name": "World Bank Procurement",
        "region": "Global",
        "type": "api",
    },
    {
        "name": "African Development Bank",
        "region": "África",
        "type": "portal",
    },
    {
        "name": "SAM.gov",
        "region": "Américas",
        "type": "portal",
    },
    {
        "name": "BASE Portugal",
        "region": "Portugal",
        "type": "portal",
    },
    {
        "name": "Contratación Pública España",
        "region": "Espanha",
        "type": "portal",
    },
]


# ============================================================
# UTILITÁRIOS
# ============================================================

def clean_text(value):

    if value is None:
        return ""

    if isinstance(value, (dict, list)):
        value = str(value)

    value = html.unescape(str(value))

    value = re.sub(
        r"<[^>]+>",
        " ",
        value
    )

    value = re.sub(
        r"\s+",
        " ",
        value
    )

    return value.strip()


def normalise_search_term(value):

    value = clean_text(value)

    value = unicodedata.normalize(
        "NFD",
        value
    )

    value = "".join(
        char
        for char in value
        if unicodedata.category(char) != "Mn"
    )

    return value.lower().strip()


def today_utc():

    return date.today()


def cutoff_date():

    return today_utc() - timedelta(
        days=PERIOD_DAYS
    )


def parse_date(value):

    if value is None:
        return None

    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    text = clean_text(value)

    if not text:
        return None

    text = text[:30]

    formats = [
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%d/%m/%Y",
        "%d-%m-%Y",
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
        r"(\d{4})-(\d{2})-(\d{2})",
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
            pass

    return None


def first_value(value):

    if value is None:
        return ""

    if isinstance(value, str):
        return value

    if isinstance(value, list):

        for item in value:

            result = first_value(item)

            if result:
                return result

        return ""

    if isinstance(value, dict):

        for key in [
            "text",
            "value",
            "content",
            "label",
            "name",
        ]:

            if key in value:

                result = first_value(
                    value[key]
                )

                if result:
                    return result

        for item in value.values():

            result = first_value(item)

            if result:
                return result

    return clean_text(value)


# ============================================================
# PAÍSES
# ============================================================

COUNTRY_MAP = {

    "PT": "Portugal",
    "PRT": "Portugal",
    "PORTUGAL": "Portugal",

    "ES": "Espanha",
    "ESP": "Espanha",
    "SPAIN": "Espanha",
    "ESPANHA": "Espanha",

    "FR": "França",
    "FRA": "França",
    "FRANCE": "França",
    "FRANCA": "França",

    "DE": "Alemanha",
    "DEU": "Alemanha",
    "GERMANY": "Alemanha",
    "ALEMANHA": "Alemanha",

    "IT": "Itália",
    "ITA": "Itália",
    "ITALY": "Itália",
    "ITALIA": "Itália",

    "NL": "Países Baixos",
    "NLD": "Países Baixos",
    "NETHERLANDS": "Países Baixos",

    "BE": "Bélgica",
    "BEL": "Bélgica",
    "BELGIUM": "Bélgica",

    "IE": "Irlanda",
    "IRL": "Irlanda",
    "IRELAND": "Irlanda",

    "AT": "Áustria",
    "AUT": "Áustria",
    "AUSTRIA": "Áustria",

    "GR": "Grécia",
    "GRC": "Grécia",
    "GREECE": "Grécia",

    "MT": "Malta",
    "MLT": "Malta",
    "MALTA": "Malta",

    "PL": "Polónia",
    "POL": "Polónia",
    "POLAND": "Polónia",

    "SE": "Suécia",
    "SWE": "Suécia",
    "SWEDEN": "Suécia",

    "DK": "Dinamarca",
    "DNK": "Dinamarca",
    "DENMARK": "Dinamarca",

    "FI": "Finlândia",
    "FIN": "Finlândia",
    "FINLAND": "Finlândia",

    "NO": "Noruega",
    "NOR": "Noruega",
    "NORWAY": "Noruega",

    "CZ": "Chéquia",
    "CZE": "Chéquia",
    "CZECHIA": "Chéquia",

    "RO": "Roménia",
    "ROU": "Roménia",
    "ROMANIA": "Roménia",

    "BG": "Bulgária",
    "BGR": "Bulgária",
    "BULGARIA": "Bulgária",

    "HR": "Croácia",
    "HRV": "Croácia",
    "CROATIA": "Croácia",

    "SI": "Eslovénia",
    "SVN": "Eslovénia",
    "SLOVENIA": "Eslovénia",

    "SK": "Eslováquia",
    "SVK": "Eslováquia",
    "SLOVAKIA": "Eslováquia",

    "HU": "Hungria",
    "HUN": "Hungria",
    "HUNGARY": "Hungria",

    "EE": "Estónia",
    "EST": "Estónia",
    "ESTONIA": "Estónia",

    "LV": "Letónia",
    "LVA": "Letónia",
    "LATVIA": "Letónia",

    "LT": "Lituânia",
    "LTU": "Lituânia",
    "LITHUANIA": "Lituânia",

    "LU": "Luxemburgo",
    "LUX": "Luxemburgo",

    "CY": "Chipre",
    "CYP": "Chipre",
    "CYPRUS": "Chipre",

    "IS": "Islândia",
    "ISL": "Islândia",
    "ICELAND": "Islândia",

    "CH": "Suíça",
    "CHE": "Suíça",
    "SWITZERLAND": "Suíça",

    "UK": "Reino Unido",
    "GB": "Reino Unido",
    "GBR": "Reino Unido",
    "UNITED KINGDOM": "Reino Unido",

    # África

    "DZ": "Argélia",
    "DZA": "Argélia",
    "ALGERIA": "Argélia",

    "AO": "Angola",
    "AGO": "Angola",

    "BJ": "Benim",
    "BEN": "Benim",
    "BENIN": "Benim",

    "BW": "Botsuana",
    "BWA": "Botsuana",
    "BOTSWANA": "Botsuana",

    "BF": "Burkina Faso",
    "BFA": "Burkina Faso",

    "BI": "Burundi",
    "BDI": "Burundi",

    "CM": "Camarões",
    "CMR": "Camarões",
    "CAMEROON": "Camarões",

    "CV": "Cabo Verde",
    "CPV": "Cabo Verde",
    "CAPE VERDE": "Cabo Verde",

    "CF": "República Centro-Africana",
    "CAF": "República Centro-Africana",

    "TD": "Chade",
    "TCD": "Chade",
    "CHAD": "Chade",

    "KM": "Comores",
    "COM": "Comores",

    "CG": "República do Congo",
    "COG": "República do Congo",

    "CD": "República Democrática do Congo",
    "COD": "República Democrática do Congo",

    "CI": "Costa do Marfim",
    "CIV": "Costa do Marfim",
    "IVORY COAST": "Costa do Marfim",

    "DJ": "Djibouti",
    "DJI": "Djibouti",

    "EG": "Egito",
    "EGY": "Egito",
    "EGYPT": "Egito",

    "GQ": "Guiné Equatorial",
    "GNQ": "Guiné Equatorial",

    "ER": "Eritreia",
    "ERI": "Eritreia",

    "SZ": "Essuatíni",
    "SWZ": "Essuatíni",
    "ESWATINI": "Essuatíni",

    "ET": "Etiópia",
    "ETH": "Etiópia",
    "ETHIOPIA": "Etiópia",

    "GA": "Gabão",
    "GAB": "Gabão",
    "GABON": "Gabão",

    "GM": "Gâmbia",
    "GMB": "Gâmbia",
    "GAMBIA": "Gâmbia",

    "GH": "Gana",
    "GHA": "Gana",
    "GHANA": "Gana",

    "GN": "Guiné",
    "GIN": "Guiné",
    "GUINEA": "Guiné",

    "GW": "Guiné-Bissau",
    "GNB": "Guiné-Bissau",

    "KE": "Quénia",
    "KEN": "Quénia",
    "KENYA": "Quénia",

    "LS": "Lesoto",
    "LSO": "Lesoto",
    "LESOTHO": "Lesoto",

    "LR": "Libéria",
    "LBR": "Libéria",
    "LIBERIA": "Libéria",

    "LY": "Líbia",
    "LBY": "Líbia",
    "LIBYA": "Líbia",

    "MG": "Madagáscar",
    "MDG": "Madagáscar",
    "MADAGASCAR": "Madagáscar",

    "MW": "Malawi",
    "MWI": "Malawi",

    "ML": "Mali",
    "MLI": "Mali",

    "MR": "Mauritânia",
    "MRT": "Mauritânia",
    "MAURITANIA": "Mauritânia",

    "MU": "Maurícia",
    "MUS": "Maurícia",
    "MAURITIUS": "Maurícia",

    "MA": "Marrocos",
    "MAR": "Marrocos",
    "MOROCCO": "Marrocos",

    "MZ": "Moçambique",
    "MOZ": "Moçambique",
    "MOZAMBIQUE": "Moçambique",

    "NA": "Namíbia",
    "NAM": "Namíbia",
    "NAMIBIA": "Namíbia",

    "NE": "Níger",
    "NER": "Níger",
    "NIGER": "Níger",

    "NG": "Nigéria",
    "NGA": "Nigéria",
    "NIGERIA": "Nigéria",

    "RW": "Ruanda",
    "RWA": "Ruanda",
    "RWANDA": "Ruanda",

    "ST": "São Tomé e Príncipe",
    "STP": "São Tomé e Príncipe",
    "SAO TOME AND PRINCIPE": "São Tomé e Príncipe",

    "SN": "Senegal",
    "SEN": "Senegal",
    "SENEGAL": "Senegal",

    "SC": "Seicheles",
    "SYC": "Seicheles",
    "SEYCHELLES": "Seicheles",

    "SL": "Serra Leoa",
    "SLE": "Serra Leoa",
    "SIERRA LEONE": "Serra Leoa",

    "SO": "Somália",
    "SOM": "Somália",
    "SOMALIA": "Somália",

    "ZA": "África do Sul",
    "ZAF": "África do Sul",
    "SOUTH AFRICA": "África do Sul",

    "SS": "Sudão do Sul",
    "SSD": "Sudão do Sul",
    "SOUTH SUDAN": "Sudão do Sul",

    "SD": "Sudão",
    "SDN": "Sudão",
    "SUDAN": "Sudão",

    "TZ": "Tanzânia",
    "TZA": "Tanzânia",
    "TANZANIA": "Tanzânia",

    "TG": "Togo",
    "TGO": "Togo",
    "TOGO": "Togo",

    "TN": "Tunísia",
    "TUN": "Tunísia",
    "TUNISIA": "Tunísia",

    "UG": "Uganda",
    "UGA": "Uganda",

    "ZM": "Zâmbia",
    "ZMB": "Zâmbia",
    "ZAMBIA": "Zâmbia",

    "ZW": "Zimbabué",
    "ZWE": "Zimbabué",
    "ZIMBABWE": "Zimbabué",
}


# ============================================================
# EXTRAÇÃO DE PAÍS
# ============================================================

def extract_country(item):

    possible_keys = [
        "buyer-country",
        "buyer_country",
        "country",
        "country-code",
        "country_code",
        "project_country",
        "procurement_country",
    ]

    for key in possible_keys:

        value = item.get(key)

        if value:

            text = first_value(value)

            if text:

                normalised = normalise_search_term(
                    text
                )

                upper = text.strip().upper()

                if upper in COUNTRY_MAP:
                    return COUNTRY_MAP[upper]

                for code, name in COUNTRY_MAP.items():

                    if normalise_search_term(code) == normalised:
                        return name

                return text.strip()

    return ""


# ============================================================
# CPV
# ============================================================

def extract_cpvs(item):

    values = []

    for key in [
        "classification-cpv",
        "classification_cpv",
        "cpv",
        "cpvs",
    ]:

        value = item.get(key)

        if value is None:
            continue

        if isinstance(value, list):

            values.extend(value)

        else:

            values.append(value)

    result = []

    for value in values:

        if isinstance(value, dict):

            text = " ".join(
                str(x)
                for x in value.values()
            )

        else:

            text = str(value)

        found = re.findall(
            r"\b\d{8}\b",
            text
        )

        for cpv in found:

            if cpv not in result:
                result.append(cpv)

    return result


# ============================================================
# DEADLINE
# ============================================================

def extract_deadline(item):

    possible_keys = [
        "deadline-receipt-tender-date-lot",
        "deadline-receipt-request-date-lot",
        "deadline",
        "deadline_date",
        "submission_deadline",
        "tender_deadline",
    ]

    for key in possible_keys:

        value = item.get(key)

        if value:

            text = first_value(value)

            if text:
                return text

    return ""


# ============================================================
# CLASSIFICAÇÃO
# ============================================================

def classify_result(
    title,
    description,
    cpvs
):

    text = normalise_search_term(
        f"{title} {description}"
    )

    direct_terms = [
        "archaeology",
        "archaeological",
        "archaeological excavation",
        "archaeological monitoring",
        "archaeological services",
        "arqueologia",
        "escavacao arqueologica",
        "acompanhamento arqueologico",
        "archaeological survey",
    ]

    heritage_terms = [
        "cultural heritage",
        "patrimonio cultural",
        "patrimonio",
        "heritage",
        "historical heritage",
        "archaeological heritage",
    ]

    excavation_terms = [
        "excavation",
        "escavacao",
        "excavation works",
    ]

    if any(
        term in text
        for term in direct_terms
    ):

        return "Arqueologia direta", 75

    if any(
        term in text
        for term in heritage_terms
    ):

        return "Património cultural", 60

    if any(
        term in text
        for term in excavation_terms
    ):

        return "Escavação / obra", 50

    if any(
        cpv in ARCHAEOLOGY_CPVS
        for cpv in cpvs
    ):

        return "Arqueologia / CPV", 65

    return "Relevante", 40


# ============================================================
# TED — QUERY
# ============================================================

def build_ted_query(term):

    return f'FT~"{term}"'


# ============================================================
# TED — TÍTULO
# ============================================================

def ted_title(notice):

    value = notice.get(
        "notice-title"
    )

    if value is None:

        for key in [
            "notice_title",
            "title",
            "title-proc",
        ]:

            if key in notice:
                value = notice.get(key)

                if value:
                    break

    if isinstance(value, dict):

        for language in [
            "eng",
            "por",
            "fra",
            "spa",
            "deu",
            "ita",
            "nld",
        ]:

            if language in value:

                result = clean_text(
                    value[language]
                )

                if result:
                    return result

        value = first_value(value)

    elif isinstance(value, list):

        for item in value:

            if isinstance(item, dict):

                for language in [
                    "eng",
                    "por",
                    "fra",
                    "spa",
                ]:

                    if language in item:

                        result = clean_text(
                            item[language]
                        )

                        if result:
                            return result

            else:

                result = clean_text(item)

                if result:
                    return result

    return clean_text(value)


# ============================================================
# TED — DESCRIÇÃO
# ============================================================

def ted_description(notice):

    values = []

    for key in [
        "description-proc",
        "description-lot",
        "description_proc",
        "description_lot",
        "description",
    ]:

        value = notice.get(key)

        if value:

            text = first_value(value)

            if text:
                values.append(text)

    return " ".join(values)


# ============================================================
# TED — CONVERSÃO
# ============================================================

def notice_to_result(notice):

    title = ted_title(
        notice
    )

    description = ted_description(
        notice
    )

    if not title:
        return None

    pub_date = parse_date(
        notice.get(
            "publication-date",
            notice.get(
                "publication_date"
            )
        )
    )

    if (
        pub_date
        and pub_date < cutoff_date()
    ):
        return None

    deadline = extract_deadline(
        notice
    )

    if deadline:

        deadline_date = parse_date(
            deadline
        )

        if (
            deadline_date
            and deadline_date < today_utc()
        ):
            return None

    country = extract_country(
        notice
    )

    cpvs = extract_cpvs(
        notice
    )

    category, score = classify_result(
        title,
        description,
        cpvs
    )

    text = normalise_search_term(
        f"{title} {description}"
    )

    relevant = any(
        normalise_search_term(
            term
        ) in text
        for term in DEFAULT_TERMS
    )

    if not relevant:

        relevant = any(
            cpv in ARCHAEOLOGY_CPVS
            for cpv in cpvs
        )

    if not relevant:
        return None

    publication_number = first_value(
        notice.get(
            "publication-number"
        )
    )

    url = ""

    if publication_number:

        url = (
            "https://ted.europa.eu/en/"
            "notice/-/detail/"
            + str(publication_number)
        )

    return {
        "title": title,
        "description": description,
        "source": "TED — Europa",
        "date": (
            pub_date.isoformat()
            if pub_date
            else ""
        ),
        "deadline": deadline,
        "country": country,
        "buyer": first_value(
            notice.get(
                "buyer-name"
            )
        ),
        "cpv": ", ".join(cpvs),
        "category": category,
        "score": score,
        "url": url,
    }


# ============================================================
# TED — PESQUISA
# ============================================================
def query_ted(term):
    diagnostics = {
        "source": f"TED — {term}",
        "ok": False,
        "count": 0,
        "query": "",
        "raw_count": 0,
        "ted_total": None,
        "ted_response_keys": [],
        "sample": ""
    }

    query = build_ted_query(term)
    diagnostics["query"] = query

    payload = {
        "query": query,
        "fields": TED_FIELDS,
        "page": 1,
        "limit": PAGE_SIZE,
        "scope": "ALL",
        "checkQuerySyntax": False,
        "paginationMode": "PAGE_NUMBER",
        "onlyLatestVersions": False
    }

    try:
        response = requests.post(
            TED_URL,
            json=payload,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()
        data = response.json()

        diagnostics["ted_response_keys"] = (
            list(data.keys())
            if isinstance(data, dict)
            else str(type(data))
        )

        diagnostics["ted_total"] = (
            data.get("totalNoticeCount")
            if isinstance(data, dict)
            else None
        )

        notices = []

        if isinstance(data, dict):

            for key in (
                "notices",
                "results",
                "data"
            ):

                value = data.get(key)

                if isinstance(value, list):
                    notices = value
                    break

                if isinstance(value, dict):

                    for subkey in (
                        "notices",
                        "results",
                        "data",
                        "rows"
                    ):

                        subvalue = value.get(
                            subkey
                        )

                        if isinstance(
                            subvalue,
                            list
                        ):
                            notices = subvalue
                            break

                    if notices:
                        break

        elif isinstance(data, list):

            notices = data

        diagnostics["raw_count"] = len(
            notices
        )

        if notices:

            diagnostics["sample"] = str(
                notices[0]
            )[:1000]

        else:

            diagnostics["sample"] = (
                "SEM AVISOS"
            )

        results = []

        for notice in notices:

            try:

                result = notice_to_result(
                    notice
                )

                if result:
                    results.append(
                        result
                    )

            except Exception:
                continue

        diagnostics["count"] = len(
            results
        )

        diagnostics["ok"] = True

        return results, diagnostics

    except Exception as exc:

        diagnostics["error"] = str(
            exc
        )

        return [], diagnostics

# ============================================================
# WORLD BANK
# ============================================================

def world_bank_title(item):

    possible_keys = [
        "project_name",
        "procurement_name",
        "title",
        "notice_title",
        "procurement_title",
        "contract_title",
    ]

    for key in possible_keys:

        value = item.get(
            key
        )

        if value:

            value = clean_text(
                value
            )

            value = re.sub(
                r"^\s*\d+\s*/\s*100\s*",
                "",
                value
            )

            if value:
                return value

    return ""


def world_bank_description(item):

    possible_keys = [
        "description",
        "short_description",
        "procurement_description",
        "notice_description",
        "project_description",
    ]

    values = []

    for key in possible_keys:

        value = item.get(
            key
        )

        if value:

            values.append(
                clean_text(value)
            )

    text = " ".join(
        x for x in values
        if x
    )

    text = re.sub(
        r"^\s*\d+\s*/\s*100\s*",
        "",
        text
    )

    return text.strip()


def world_bank_date(item):

    possible_keys = [
        "publication_date",
        "notice_date",
        "date",
        "published_date",
        "procurement_date",
    ]

    for key in possible_keys:

        parsed = parse_date(
            item.get(key)
        )

        if parsed:
            return parsed

    return None


def world_bank_url(item):

    for key in [
        "url",
        "notice_url",
        "procurement_url",
        "link",
        "notice_link",
    ]:

        value = item.get(
            key
        )

        if value:
            return str(value)

    return ""


def query_world_bank(term):

    diagnostics = {
        "source": f"World Bank — {term}",
        "ok": False,
        "count": 0,
    }

    results = []

    try:

        params = {
            "qterm": term,
            "format": "json",
            "rows": PAGE_SIZE,
        }

        response = requests.get(
            WORLD_BANK_URL,
            params=params,
            timeout=REQUEST_TIMEOUT
        )

        response.raise_for_status()

        data = response.json()

        records = []

        if isinstance(
            data,
            dict
        ):

            for key in [
                "procnotices",
                "results",
                "data",
                "records",
            ]:

                value = data.get(
                    key
                )

                if isinstance(
                    value,
                    list
                ):

                    records = value
                    break

                if isinstance(
                    value,
                    dict
                ):

                    for subkey in [
                        "rows",
                        "results",
                        "data",
                    ]:

                        if isinstance(
                            value.get(subkey),
                            list
                        ):

                            records = value[
                                subkey
                            ]

                            break

                    if records:
                        break

        elif isinstance(
            data,
            list
        ):

            records = data

        for item in records:

            if not isinstance(
                item,
                dict
            ):
                continue

            title = world_bank_title(
                item
            )

            description = (
                world_bank_description(
                    item
                )
            )

            if not title:
                continue

            pub_date = world_bank_date(
                item
            )

            if (
                pub_date
                and pub_date < cutoff_date()
            ):
                continue

            deadline = extract_deadline(
                item
            )

            if deadline:

                deadline_date = parse_date(
                    deadline
                )

                if (
                    deadline_date
                    and deadline_date < today_utc()
                ):
                    continue

            country = extract_country(
                item
            )

            cpvs = extract_cpvs(
                item
            )

            category, score = classify_result(
                title,
                description,
                cpvs
            )

            text = normalise_search_term(
                f"{title} {description}"
            )

            if not any(
                normalise_search_term(
                    x
                ) in text
                for x in DEFAULT_TERMS
            ):

                if not any(
                    cpv in ARCHAEOLOGY_CPVS
                    for cpv in cpvs
                ):
                    continue

            results.append({
                "title": title,
                "description": description,
                "source": "World Bank Procurement",
                "date": (
                    pub_date.isoformat()
                    if pub_date
                    else ""
                ),
                "deadline": deadline,
                "country": country,
                "buyer": clean_text(
                    item.get(
                        "buyer",
                        item.get(
                            "procuring_entity",
                            ""
                        )
                    )
                ),
                "cpv": ", ".join(cpvs),
                "category": category,
                "score": score,
                "url": world_bank_url(
                    item
                ),
            })

        diagnostics["ok"] = True

        diagnostics["count"] = len(
            results
        )

        return results, diagnostics

    except Exception as exc:

        diagnostics["error"] = str(
            exc
        )

        return [], diagnostics


# ============================================================
# FILTRO REGIONAL
# ============================================================

REGION_COUNTRIES = {

    "Europa": {
        "Portugal",
        "Espanha",
        "França",
        "Alemanha",
        "Itália",
        "Países Baixos",
        "Bélgica",
        "Irlanda",
        "Áustria",
        "Grécia",
        "Malta",
        "Polónia",
        "Suécia",
        "Dinamarca",
        "Finlândia",
        "Noruega",
        "Chéquia",
        "Roménia",
        "Bulgária",
        "Croácia",
        "Eslovénia",
        "Eslováquia",
        "Hungria",
        "Estónia",
        "Letónia",
        "Lituânia",
        "Luxemburgo",
        "Chipre",
        "Islândia",
        "Suíça",
        "Reino Unido",
    },

    "África": {
        "Argélia",
        "Angola",
        "Benim",
        "Botsuana",
        "Burkina Faso",
        "Burundi",
        "Camarões",
        "Cabo Verde",
        "República Centro-Africana",
        "Chade",
        "Comores",
        "República do Congo",
        "República Democrática do Congo",
        "Costa do Marfim",
        "Djibouti",
        "Egito",
        "Guiné Equatorial",
        "Eritreia",
        "Essuatíni",
        "Etiópia",
        "Gabão",
        "Gâmbia",
        "Gana",
        "Guiné",
        "Guiné-Bissau",
        "Quénia",
        "Lesoto",
        "Libéria",
        "Líbia",
        "Madagáscar",
        "Malawi",
        "Mali",
        "Mauritânia",
        "Maurícia",
        "Marrocos",
        "Moçambique",
        "Namíbia",
        "Níger",
        "Nigéria",
        "Ruanda",
        "São Tomé e Príncipe",
        "Senegal",
        "Seicheles",
        "Serra Leoa",
        "Somália",
        "África do Sul",
        "Sudão do Sul",
        "Sudão",
        "Tanzânia",
        "Togo",
        "Tunísia",
        "Uganda",
        "Zâmbia",
        "Zimbabué",
    },
}


def apply_region_filter(
    results,
    region
):

    if not region:
        return results

    region_normalised = (
        normalise_search_term(
            region
        )
    )

    if region_normalised in [
        "global",
        "todos",
        "todas",
        "all",
    ]:
        return results

    target_countries = None

    if region_normalised in [
        "africa",
        "áfrica",
    ]:

        target_countries = REGION_COUNTRIES[
            "África"
        ]

    elif region_normalised in [
        "europa",
    ]:

        target_countries = REGION_COUNTRIES[
            "Europa"
        ]

    elif region_normalised in [
        "portugal",
    ]:

        target_countries = {
            "Portugal"
        }

    elif region_normalised in [
        "espanha",
        "spain",
    ]:

        target_countries = {
            "Espanha"
        }

    elif region_normalised in [
        "americas",
        "américas",
        "america",
        "américa",
    ]:

        return [
            item
            for item in results
            if normalise_search_term(
                item.get(
                    "country",
                    ""
                )
            ) not in [
                "",
                "global",
                "international",
            ]
        ]

    if target_countries is None:
        return results

    normalised_targets = {
        normalise_search_term(
            country
        )
        for country in target_countries
    }

    filtered = []

    for item in results:

        country = normalise_search_term(
            item.get(
                "country",
                ""
            )
        )

        if country in normalised_targets:

            filtered.append(
                item
            )

    return filtered


# ============================================================
# FILTRO DE CATEGORIA
# ============================================================

def apply_category_filter(
    results,
    category
):

    if not category:
        return results

    category_normalised = (
        normalise_search_term(
            category
        )
    )

    if category_normalised in [
        "todos",
        "todas",
        "all",
    ]:
        return results

    filtered = []

    for item in results:

        item_category = normalise_search_term(
            item.get(
                "category",
                ""
            )
        )

        if (
            category_normalised
            in item_category
        ):

            filtered.append(
                item
            )

    return filtered


# ============================================================
# DEDUPLICAÇÃO
# ============================================================

def deduplicate_results(
    results
):

    seen = set()
    output = []

    for item in results:

        key = (
            normalise_search_term(
                item.get(
                    "title",
                    ""
                )
            ),
            normalise_search_term(
                item.get(
                    "country",
                    ""
                )
            ),
        )

        if key in seen:
            continue

        seen.add(key)

        output.append(
            item
        )

    return output


# ============================================================
# ROTAS PRINCIPAIS
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


@app.get("/api/sources")
def api_sources():

    return {
        "sources": len(SOURCES),
        "api_sources": sum(
            1
            for source in SOURCES
            if source["type"] == "api"
        ),
        "portal_count": sum(
            1
            for source in SOURCES
            if source["type"] == "portal"
        ),
        "items": SOURCES,
    }


# ============================================================
# PESQUISA PRINCIPAL
# ============================================================

@app.get("/api/search")
def api_search(
    q: str = Query(
        "archaeology"
    ),
    region: str = Query(
        ""
    ),
    category: str = Query(
        ""
    ),
):

    search_term = clean_text(
        q
    )

    if not search_term:

        search_terms = DEFAULT_TERMS

    else:

        search_terms = [
            search_term
        ]

        if normalise_search_term(
            search_term
        ) in [
            "archaeology",
            "arqueologia",
        ]:

            search_terms = DEFAULT_TERMS

    all_results = []
    diagnostics = []

    # --------------------------------------------------------
    # TED
    # --------------------------------------------------------

    with ThreadPoolExecutor(
        max_workers=6
    ) as executor:

        futures = {
            executor.submit(
                query_ted,
                term
            ): term

            for term in search_terms[:10]
        }

        for future in as_completed(
            futures
        ):

            try:

                results, diagnostic = (
                    future.result()
                )

                all_results.extend(
                    results
                )

                diagnostics.append(
                    diagnostic
                )

            except Exception as exc:

                diagnostics.append({
                    "source": (
                        "TED — "
                        + futures[future]
                    ),
                    "ok": False,
                    "count": 0,
                    "error": str(exc),
                })

    # --------------------------------------------------------
    # WORLD BANK
    # --------------------------------------------------------

    with ThreadPoolExecutor(
        max_workers=4
    ) as executor:

        futures = {
            executor.submit(
                query_world_bank,
                term
            ): term

            for term in search_terms[:4]
        }

        for future in as_completed(
            futures
        ):

            try:

                results, diagnostic = (
                    future.result()
                )

                all_results.extend(
                    results
                )

                diagnostics.append(
                    diagnostic
                )

            except Exception as exc:

                diagnostics.append({
                    "source": (
                        "World Bank — "
                        + futures[future]
                    ),
                    "ok": False,
                    "count": 0,
                    "error": str(exc),
                })

    # --------------------------------------------------------
    # DEDUPLICAR
    # --------------------------------------------------------

    all_results = deduplicate_results(
        all_results
    )

    # --------------------------------------------------------
    # FILTRO REGIONAL
    # --------------------------------------------------------

    all_results = apply_region_filter(
        all_results,
        region
    )

    # --------------------------------------------------------
    # FILTRO DE CATEGORIA
    # --------------------------------------------------------

    all_results = apply_category_filter(
        all_results,
        category
    )

    # --------------------------------------------------------
    # REMOVER PRAZOS EXPIRADOS
    # --------------------------------------------------------

    valid_results = []

    for item in all_results:

        deadline = item.get(
            "deadline"
        )

        if deadline:

            deadline_date = parse_date(
                deadline
            )

            if (
                deadline_date
                and deadline_date < today_utc()
            ):
                continue

        valid_results.append(
            item
        )

    all_results = valid_results

    # --------------------------------------------------------
    # ORDENAR
    # --------------------------------------------------------

    all_results.sort(
        key=lambda item: (
            item.get(
                "date",
                ""
            ),
            item.get(
                "score",
                0
            ),
        ),
        reverse=True
    )

    return {
        "ok": True,
        "query": search_term,
        "region": region,
        "category": category,
        "results": all_results,
        "count": len(all_results),
        "sources": len(SOURCES),
        "api_sources": sum(
            1
            for source in SOURCES
            if source["type"] == "api"
        ),
        "portal_count": sum(
            1
            for source in SOURCES
            if source["type"] == "portal"
        ),
        "diagnostics": diagnostics,
        "searched_at": today_utc().isoformat(),
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
            if source["type"] == "api"
        ),
        "portal_count": sum(
            1
            for source in SOURCES
            if source["type"] == "portal"
        ),
    }
