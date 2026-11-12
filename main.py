from fastapi import FastAPI, Query
from fastapi.responses import FileResponse, Response
from pathlib import Path
from datetime import date, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import html
import json
import re
import time
import unicodedata
import requests
import threading

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="Arqueologia Radar", version="2.9.7")

REQUEST_TIMEOUT = 20
PERIOD_DAYS = 365
PAGE_SIZE = 250

TED_URL = "https://api.ted.europa.eu/v3/notices/search"
WORLD_BANK_URL = "https://search.worldbank.org/api/v2/procnotices"
SECOP_URL = "https://www.datos.gov.co/resource/p6dx-8zbt.json"
PNCP_BASE_URL = "https://pncp.gov.br/api/consulta/v1"
ECUADOR_API_URL = "https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/api/search_ocds"

SOURCES = [
    {"name": "TED — Europa", "type": "api", "automatic": True, "url": "https://ted.europa.eu/"},
    {"name": "World Bank Procurement", "type": "api", "automatic": True, "url": "https://projects.worldbank.org/"},
    {"name": "SECOP II — Colômbia", "type": "api", "automatic": True, "url": "https://www.datos.gov.co/"},
    {"name": "PNCP — Brasil", "type": "api", "automatic": True, "url": "https://pncp.gov.br/"},
    {"name": "South Africa eTenders", "type": "portal", "automatic": False, "url": "https://www.etenders.gov.za/"},
    {"name": "African Development Bank — Procurement Notices", "type": "portal", "automatic": False, "url": "https://www.afdb.org/en/projects-and-operations/procurement"},
    {"name": "SAM.gov", "type": "portal", "automatic": False, "url": "https://sam.gov/"},
    {"name": "BASE Portugal", "type": "portal", "automatic": False, "url": "https://www.base.gov.pt/"},
    {"name": "Espanha", "type": "portal", "automatic": False, "url": "https://contrataciondelestado.es/"},
    {"name": "UNDB", "type": "portal", "automatic": False, "url": "https://devbusiness.un.org/"},
    {"name": "UNGM", "type": "portal", "automatic": False, "url": "https://www.ungm.org/"},
    {"name": "EBRD — ECEPP Procurement Portal", "type": "portal", "automatic": False, "url": "https://ecepp.ebrd.com/"},
    {"name": "EIB — Project Procurement", "type": "portal", "automatic": False, "url": "https://www.eib.org/en/about/procurement/project-procurement"},
    {"name": "Oman", "type": "portal", "automatic": False, "url": "https://etendering.tenderboard.gov.om/"},
    {"name": "Saudi Etimad", "type": "portal", "automatic": False, "url": "https://tenders.etimad.sa/"},
    {"name": "UAE", "type": "portal", "automatic": False, "url": "https://mof.gov.ae/"},
    {"name": "Qatar", "type": "portal", "automatic": False, "url": "https://monaqasat.mof.gov.qa/"},
    {"name": "Morocco", "type": "portal", "automatic": False, "url": "https://www.marchespublics.gov.ma/"},
    {"name": "Uganda", "type": "portal", "automatic": False, "url": "https://www.ppda.go.ug/"},
    {"name": "Kenya", "type": "portal", "automatic": False, "url": "https://tenders.go.ke/"},
    {"name": "Tanzânia — NeST e-Procurement", "type": "portal", "automatic": False, "url": "https://nest.go.tz/"},
    {"name": "Mozambique", "type": "portal", "automatic": False, "url": "https://www.ufsa.gov.mz/"},
    {"name": "ChileCompra", "type": "portal", "automatic": False, "url": "https://www.mercadopublico.cl/"},
    {"name": "IDB — Procurement Notices", "type": "portal", "automatic": False, "url": "https://www.iadb.org/en/how-we-can-work-together/procurement/procurement-projects/procurement-notices"},
    {"name": "ADB — Project Procurement Opportunities", "type": "portal", "automatic": False, "url": "https://www.adb.org/business/project-procurement/business-opportunities"},
    {"name": "AusTender", "type": "portal", "automatic": False, "url": "https://www.tenders.gov.au/"},
    {"name": "NZ GETS", "type": "portal", "automatic": False, "url": "https://www.gets.govt.nz/"},
    {"name": "Redeia", "type": "portal", "automatic": False, "url": "https://www.ree.es/"},
    # Portais nacionais adicionais para expansão mundial (consulta manual nesta versão)
    {"name": "Reino Unido — Find a Tender", "type": "portal", "automatic": False, "url": "https://www.find-tender.service.gov.uk/"},
    {"name": "Reino Unido — Contracts Finder", "type": "portal", "automatic": False, "url": "https://www.contractsfinder.service.gov.uk/"},
    {"name": "França — PLACE", "type": "portal", "automatic": False, "url": "https://www.marches-publics.gouv.fr/"},
    {"name": "Alemanha — Bund.de concursos", "type": "portal", "automatic": False, "url": "https://www.service.bund.de/"},
    {"name": "Itália — Acquisti in Rete", "type": "portal", "automatic": False, "url": "https://www.acquistinretepa.it/"},
    {"name": "Países Baixos — TenderNed", "type": "portal", "automatic": False, "url": "https://www.tenderned.nl/"},
    {"name": "Bélgica — e-Procurement", "type": "portal", "automatic": False, "url": "https://www.publicprocurement.be/"},
    {"name": "Irlanda — eTenders", "type": "portal", "automatic": False, "url": "https://www.etenders.gov.ie/"},
    {"name": "Polónia — e-Zamówienia", "type": "portal", "automatic": False, "url": "https://ezamowienia.gov.pl/"},
    {"name": "Canadá — CanadaBuys", "type": "portal", "automatic": False, "url": "https://canadabuys.canada.ca/"},
    {"name": "Índia — Central Public Procurement Portal", "type": "portal", "automatic": False, "url": "https://eprocure.gov.in/"},
    {"name": "Japão — Government Procurement", "type": "portal", "automatic": False, "url": "https://www.jetro.go.jp/en/database/procurement/"},
    {"name": "Coreia do Sul — KONEPS", "type": "portal", "automatic": False, "url": "https://www.pps.go.kr/eng/"},
    {"name": "Singapura — GeBIZ", "type": "portal", "automatic": False, "url": "https://www.gebiz.gov.sg/"},
    {"name": "Malásia — ePerolehan", "type": "portal", "automatic": False, "url": "https://www.eperolehan.gov.my/"},
    {"name": "Filipinas — PhilGEPS", "type": "portal", "automatic": False, "url": "https://www.philgeps.gov.ph/"},
    {"name": "Indonésia — LPSE", "type": "portal", "automatic": False, "url": "https://lpse.lkpp.go.id/"},
    {"name": "Paquistão — PPRA", "type": "portal", "automatic": False, "url": "https://ppra.gov.pk/"},
    {"name": "Bangladesh — e-GP", "type": "portal", "automatic": False, "url": "https://www.eprocure.gov.bd/"},
    {"name": "Sri Lanka — Government Procurement", "type": "portal", "automatic": False, "url": "https://www.promise.lk/"},
    {"name": "México — Compras MX", "type": "portal", "automatic": False, "url": "https://comprasmx.buengobierno.gob.mx/"},
    {"name": "Argentina — COMPR.AR", "type": "portal", "automatic": False, "url": "https://comprar.gob.ar/"},
    {"name": "Peru — SEACE (buscador público)", "type": "portal", "automatic": False, "url": "https://prod2.seace.gob.pe/seacebus-uiwd-pub/buscadorPublico/buscadorPublico.xhtml"},
    {"name": "Uruguai — Compras Estatales", "type": "portal", "automatic": False, "url": "https://www.comprasestatales.gub.uy/"},
    {"name": "Costa Rica — SICOP", "type": "portal", "automatic": False, "url": "https://www.sicop.go.cr/"},
    {"name": "Panamá — PanamaCompra", "type": "portal", "automatic": False, "url": "https://www.panamacompra.gob.pa/"},
    {"name": "Gana — GHANEPS", "type": "portal", "automatic": False, "url": "https://www.ghaneps.gov.gh/"},
    {"name": "Nigéria — Bureau of Public Procurement", "type": "portal", "automatic": False, "url": "https://www.bpp.gov.ng/"},
    {"name": "Ruanda — Umucyo", "type": "portal", "automatic": False, "url": "https://www.umucyo.gov.rw/"},
    {"name": "Zâmbia — ZPPA", "type": "portal", "automatic": False, "url": "https://www.zppa.org.zm/"},
    {"name": "Botswana — PPADB", "type": "portal", "automatic": False, "url": "https://www.ppadb.co.bw/"},
    {"name": "Namíbia — eProcurement", "type": "portal", "automatic": False, "url": "https://eprocurement.gov.na/"},
    {"name": "Turquia — EKAP", "type": "portal", "automatic": False, "url": "https://ekap.kik.gov.tr/"},
    {"name": "Israel — Government Procurement", "type": "portal", "automatic": False, "url": "https://mr.gov.il/"},
    {"name": "Jordânia — JONEPS", "type": "portal", "automatic": False, "url": "https://www.joneps.gov.jo/"},
    {"name": "Cazaquistão — Public Procurement", "type": "portal", "automatic": False, "url": "https://goszakup.gov.kz/"},
    {"name": "Austrália — AusTender", "type": "portal", "automatic": False, "url": "https://www.tenders.gov.au/"},
    {"name": "Nova Zelândia — GETS", "type": "portal", "automatic": False, "url": "https://www.gets.govt.nz/"},
    # China — portais públicos centrais e locais
    {"name": "China — China Government Procurement Network", "type": "portal", "automatic": False, "url": "https://www.ccgp.gov.cn/"},
    {"name": "China — Shanghai Government Procurement", "type": "portal", "automatic": False, "url": "https://www.zfcg.sh.gov.cn/"},
    {"name": "China — Beijing Government Procurement", "type": "portal", "automatic": False, "url": "https://www.ccgp-beijing.gov.cn/"},
    # Médio Oriente — portais oficiais nacionais e regionais
    {"name": "Arábia Saudita — Etimad", "type": "portal", "automatic": False, "url": "https://tenders.etimad.sa/"},
    {"name": "Emirados Árabes Unidos — Digital Procurement Platform", "type": "portal", "automatic": False, "url": "https://mof.gov.ae/en/public-finance/government-procurement/digital-procurement-platform/"},
    {"name": "Dubai — eSupply", "type": "portal", "automatic": False, "url": "https://esupply.dubai.gov.ae/"},
    {"name": "Qatar — Monaqasat", "type": "portal", "automatic": False, "url": "https://monaqasat.mof.gov.qa/"},
    {"name": "Omã — Tender Board eTendering", "type": "portal", "automatic": False, "url": "https://etendering.tenderboard.gov.om/"},
    {"name": "Bahrain — Tender Board", "type": "portal", "automatic": False, "url": "https://www.tenderboard.gov.bh/"},
    {"name": "Kuwait — Central Agency for Public Tenders", "type": "portal", "automatic": False, "url": "https://capt.gov.kw/"},
    {"name": "Jordânia — JONEPS", "type": "portal", "automatic": False, "url": "https://www.joneps.gov.jo/"},
    {"name": "Egito — Government Tenders Portal", "type": "portal", "automatic": False, "url": "https://etenders.gov.eg/"},
    {"name": "Iraque — Ministry of Planning", "type": "portal", "automatic": False, "url": "https://mop.gov.iq/"},
    {"name": "Líbano — Public Procurement Authority", "type": "portal", "automatic": False, "url": "https://www.ppa.gov.lb/"},
    {"name": "Israel — Government Procurement Administration", "type": "portal", "automatic": False, "url": "https://mr.gov.il/"},
    {"name": "Turquia — EKAP", "type": "portal", "automatic": False, "url": "https://ekap.kik.gov.tr/"},
    {"name": "Chipre — eProcurement", "type": "portal", "automatic": False, "url": "https://www.eprocurement.gov.cy/"},
    # Expansão mundial — novos portais oficiais nacionais (consulta manual)
    {"name": "Paraguai — DNCP / SICP", "type": "portal", "automatic": False, "url": "https://www.contrataciones.gov.py/"},
    {"name": "Bolívia — SICOES", "type": "portal", "automatic": False, "url": "https://www.sicoes.gob.bo/"},
    {"name": "Equador — SERCOP Contrataciones Abiertas OCDS", "type": "api", "automatic": True, "url": "https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/datos-abiertos/api"},
    {"name": "Guatemala — Guatecompras", "type": "portal", "automatic": False, "url": "https://www.guatecompras.gt/"},
    {"name": "Honduras — Honducompras", "type": "portal", "automatic": False, "url": "https://honducompras.gob.hn/"},
    {"name": "El Salvador — COMPRASAL", "type": "portal", "automatic": False, "url": "https://unac.mh.gob.sv/comprasalweb/"},
    {"name": "República Dominicana — DataCompras / DGCP", "type": "portal", "automatic": False, "url": "https://datosabiertos.dgcp.gob.do/"},
    {"name": "Nicarágua — SISCAE / NicaraguaCompra", "type": "portal", "automatic": False, "url": "https://www.gestion.nicaraguacompra.gob.ni/"},
    {"name": "Trindade e Tobago — ProcureTT", "type": "portal", "automatic": False, "url": "https://procurett.oprtt.org/"},
    {"name": "Tunísia — TUNEPS", "type": "portal", "automatic": False, "url": "https://www.tuneps.tn/"},
    {"name": "Costa do Marfim — SIGOMAP", "type": "portal", "automatic": False, "url": "https://www.sigomap.gouv.ci/"},
    {"name": "Camarões — ARMP / Marchés Publics", "type": "portal", "automatic": False, "url": "https://armp.cm/public/"},
    {"name": "Zimbabué — PRAZ eGP", "type": "portal", "automatic": False, "url": "https://www.praz.org.zw/egp/"},
    {"name": "Angola — Portal de Compras Públicas", "type": "portal", "automatic": False, "url": "https://compraspublicas.minfin.gov.ao/ComprasPublicas/"},
    {"name": "Vietname — VNEPS", "type": "portal", "automatic": False, "url": "https://muasamcong.mof.gov.vn/en/"},
    {"name": "Nepal — National e-GP", "type": "portal", "automatic": False, "url": "https://beta.bolpatra.gov.np/"},
    {"name": "Etiópia — Electronic Government Procurement", "type": "portal", "automatic": False, "url": "https://egp.gov.et/"},
    {"name": "Hong Kong — Procurement and Contract Management System", "type": "portal", "automatic": False, "url": "https://pcms2.gld.gov.hk/"},
    {"name": "Brunei — State Tender Board / Pelita Brunei", "type": "portal", "automatic": False, "url": "https://www.mof.gov.bn/divisions/state-tender-board-downloads.aspx"},
    {"name": "Tailândia — e-GP", "type": "portal", "automatic": False, "url": "https://www.gprocurement.go.th/new_index.html"},
]

# Remove repeated portal URLs so each official source appears only once in the catalogue.
_seen_source_urls = set()
_unique_sources = []
for _source in SOURCES:
    _source_url = _source.get("url", "").rstrip("/").lower()
    if _source_url and _source_url not in _seen_source_urls:
        _seen_source_urls.add(_source_url)
        _unique_sources.append(_source)
SOURCES = _unique_sources

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
    "archäologie", "archäologisch",
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
WORLD_BANK_TERMS = ["archaeology", "cultural heritage"]
SECOP_TERMS = ["archaeology", "archaeological", "arqueologia", "arqueología", "servicios arqueologicos", "patrimonio cultural", "heritage"]
BRAZIL_TERMS = ["arqueologia", "arqueológico", "arqueológica", "arqueológicos", "arqueológicas", "serviços arqueológicos", "serviços de arqueologia", "patrimônio", "património", "patrimônio cultural", "patrimônio histórico", "património cultural", "património histórico"]
# PNCP exige o código de modalidade na consulta por publicação. Códigos válidos
# mais comuns; a consulta é executada uma vez por modalidade e os resultados são filtrados localmente.
PNCP_MODALITIES = [1, 3]
# Evita repetir pedidos ao PNCP durante 15 minutos após um HTTP 429.
PNCP_COOLDOWN_SECONDS = 900
PNCP_COOLDOWN_UNTIL = 0.0
PNCP_COOLDOWN_LOCK = threading.Lock()

# Proteção da API do Equador contra excesso de pedidos (HTTP 429).
# Mantém pelo menos 3 segundos entre pedidos e suspende novas consultas
# durante 15 minutos depois de uma resposta 429.
ECUADOR_REQUEST_INTERVAL = 3.0
ECUADOR_COOLDOWN_SECONDS = 900
ECUADOR_LAST_REQUEST_AT = 0.0
ECUADOR_COOLDOWN_UNTIL = 0.0
ECUADOR_REQUEST_LOCK = threading.Lock()

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
"FJ":"Fiji","PG":"Papua-Nova Guiné","NI":"Nicarágua","TT":"Trindade e Tobago","HK":"Hong Kong","BN":"Brunei"
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
"JO":"JOR","LB":"LBN","IQ":"IRQ","IR":"IRN","KW":"KWT","BH":"BHR","FJ":"FJI","PG":"PNG","NI":"NIC","TT":"TTO","HK":"HKG","BN":"BRN"
}
REGION_COUNTRIES = {
"Europa":{"PT","ES","FR","DE","IT","NL","BE","LU","IE","GB","UK","CH","AT","PL","CZ","SK","HU","RO","BG","GR","HR","SI","SE","NO","DK","FI","EE","LV","LT","MT","CY","IS","TR","UA","RU"},
"África":{"MA","DZ","TN","EG","ZA","KE","UG","TZ","MZ","GH","NG","SN","ET","CI","CM","AO","ZW","ZM","BW","NA","RW","CD"},
"América":{"US","CA","MX","BR","AR","CL","CO","PE","UY","PY","BO","EC","CR","PA","GT","DO","JM","VE","GY","SR","NI","TT"},
"Ásia":{"CN","JP","KR","IN","ID","MY","TH","VN","PH","SA","AE","QA","OM","PK","BD","LK","NP","KH","LA","MM","KZ","UZ","AZ","GE","AM","IL","JO","LB","IQ","IR","KW","BH","HK"},
"Oceania":{"AU","NZ","FJ","PG","BN"}
}
TED_FIELDS = ["publication-number", "publication-date", "notice-title", "buyer-name",
              "organisation-country-buyer", "buyer-country", "classification-cpv",
              "description-proc", "description-glo", "deadline-date-lot"]
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "ArqueologiaRadar/2.9.7", "Accept": "application/json"})


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
    """Corrige texto UTF-8 interpretado como Latin-1/Windows-1252, sem reescrever texto válido."""
    text = normalize_text(value)
    if not text:
        return text

    markers = ("Ã", "Â", "â€", "ðŸ", "Ãƒ", "Ã‚")

    def score(candidate):
        # Penaliza sequências típicas de mojibake e controlos C1 que surgem em texto corrompido.
        return sum(candidate.count(marker) * 3 for marker in markers) + sum(
            1 for char in candidate if 0x80 <= ord(char) <= 0x9F
        )

    # Converte sequências de caracteres Latin-1/Windows-1252 em blocos, para que
    # um apóstrofo tipográfico ou outro carácter fora do Latin-1 não impeça a reparação.
    for _ in range(3):
        old_score = score(text)
        candidates = []
        for encoding in ("cp1252", "latin-1"):
            pieces = []
            run = []
            for char in text:
                try:
                    char.encode(encoding)
                    run.append(char)
                except UnicodeEncodeError:
                    if run:
                        chunk = "".join(run)
                        try:
                            pieces.append(chunk.encode(encoding).decode("utf-8"))
                        except UnicodeError:
                            pieces.append(chunk)
                        run = []
                    pieces.append(char)
            if run:
                chunk = "".join(run)
                try:
                    pieces.append(chunk.encode(encoding).decode("utf-8"))
                except UnicodeError:
                    pieces.append(chunk)
            candidate = "".join(pieces)
            if candidate != text and score(candidate) < old_score:
                candidates.append((score(candidate), candidate))
        if not candidates:
            break
        text = min(candidates, key=lambda item: item[0])[1]

    # Casos frequentes que incluem bytes de controlo C1 e não são recuperados por cp1252.
    replacements = {
        "Ã": "Í", "Ã": "Í", "Ã": "Ó", "Ã": "Ú",
        "Ã": "Á", "Ã": "É", "Ã": "Í", "Ã": "Ó",
        "Ã¡": "á", "Ã ": "à", "Ã¢": "â", "Ã£": "ã", "Ã¤": "ä",
        "Ã©": "é", "Ã¨": "è", "Ãª": "ê", "Ã­": "í", "Ã¬": "ì",
        "Ã³": "ó", "Ã²": "ò", "Ã´": "ô", "Ãµ": "õ", "Ãº": "ú",
        "Ã¹": "ù", "Ã§": "ç", "Ã‰": "É", "Ã€": "À", "Ã‚": "Â",
        "Ãƒ": "Ã", "Ã‡": "Ç", "Ã“": "Ó", "Ãš": "Ú", "Ã": "Á",
        "Ã•": "Õ", "â€“": "–", "â€”": "—", "â€œ": "“", "â€": "”",
        "â€˜": "‘", "â€™": "’", "Â ": " ",
    }
    for old, replacement in replacements.items():
        text = text.replace(old, replacement)
    return text


def parse_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value

    # Algumas APIs devolvem datas como timestamp Unix (segundos ou milissegundos).
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            number = float(value)
            if number >= 100000000000:  # milissegundos
                number /= 1000.0
            if number >= 1000000000:
                return datetime.fromtimestamp(number, tz=__import__("datetime").timezone.utc).date()
            if number.is_integer() and len(str(int(number))) == 8:
                return datetime.strptime(str(int(number)), "%Y%m%d").date()
        except (ValueError, TypeError, OverflowError, OSError):
            return None

    text = str(value).strip()
    if not text:
        return None
    # Valores numéricos em texto: AAAAMMDD ou timestamp Unix.
    if re.fullmatch(r"\d{8}", text):
        try:
            return datetime.strptime(text, "%Y%m%d").date()
        except ValueError:
            pass
    if re.fullmatch(r"\d{10,13}(?:\.0+)?", text):
        try:
            number = float(text)
            if number >= 100000000000:
                number /= 1000.0
            return datetime.fromtimestamp(number, tz=__import__("datetime").timezone.utc).date()
        except (ValueError, TypeError, OverflowError, OSError):
            pass

    # Não remover espaços antes de interpretar datas ISO com hora.
    candidates = [text, text.replace(" ", "T", 1) if " " in text else text]
    formats = (
        "%Y-%m-%d", "%Y-%m-%d+%H:%M", "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z", "%d/%m/%Y", "%d-%m-%Y",
        "%m/%d/%Y", "%Y/%m/%d", "%Y%m%d",
    )
    for candidate in candidates:
        for fmt in formats:
            try:
                return datetime.strptime(candidate, fmt).date()
            except (ValueError, TypeError):
                continue
        try:
            return datetime.fromisoformat(candidate.replace("Z", "+00:00")).date()
        except (ValueError, TypeError):
            pass
        # Algumas respostas usam AAAA-MM-DD+02:00 sem separador T.
        match = re.match(r"^(\d{4}-\d{2}-\d{2})(?:[+-]\d{2}:?\d{2})?$", candidate)
        if match:
            try:
                return date.fromisoformat(match.group(1))
            except ValueError:
                pass
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

    # Fornecimentos/equipamentos que apenas mencionam um laboratório arqueológico
    # não devem ser promovidos a serviços arqueológicos diretos.
    supply_terms = (
        "equipamiento", "equipos", "equipo", "suministro", "suministros",
        "material de laboratorio", "chemical products", "laboratory equipment",
        "fornecimento", "equipamento", "equipamentos", "produtos quimicos",
        "material de laboratorio", "suministro de materiales", "suministro de equipos",
        "suministro de bienes", "compra de equipos", "adquisicion de equipos",
        "supply of equipment", "purchase of equipment", "supply of materials",
        "equipment purchase", "laboratory supplies", "materiales de laboratorio"
    )
    supply_only = has_any_term(title_norm, supply_terms)

    # Não apresentar aquisições de bens como serviços arqueológicos só porque o título
    # menciona arqueologia. Se a descrição explicitar um serviço, pode continuar a ser aceite.
    if title_direct and not supply_only:
        return "Arqueologia direta"
    if title_direct and supply_only:
        if description_direct and has_any_term(description_norm, (
            "excavation", "excavacion", "excavación", "excavacao", "escavação",
            "monitoring", "seguimiento arqueologico", "acompanhamento arqueológico",
            "archaeological services", "servicios arqueologicos", "serviços arqueológicos",
            "prospeccion arqueologica", "prospeção arqueológica", "fieldwork"
        )):
            return "Serviço com componente arqueológica"
        return ""
    if description_direct and not supply_only:
        return "Serviço com componente arqueológica"
    if cpv_direct and (description_direct or (search_mode != "direct" and heritage)):
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
             "Património / grandes projetos": 62, "Património cultural": 50, "Fornecimento relacionado com arqueologia": 35}.get(classification, 40)
    return {
        "title": title, "description": description, "buyer": buyer,
        "country": country_name(code) if code else country_text,
        "country_code": code, "region": region_from_country(code),
        "source": repair_mojibake(source), "url": repair_mojibake(url),
        "date": published_date.isoformat() if published_date else "",
        "deadline": deadline_date.isoformat() if deadline_date else "",
        "cpv": cpvs, "classification": classification, "score": score,
        "date_status": "Data de publicação confirmada" if published_date else "Data de publicação não fornecida pela fonte",
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


def _world_bank_scalar_fields(data, prefix=""):
    """Recolhe campos escalares da resposta do Banco Mundial, incluindo estruturas aninhadas."""
    found = []
    if isinstance(data, dict):
        for key, value in data.items():
            path = f"{prefix}.{key}" if prefix else str(key)
            if isinstance(value, (dict, list)):
                found.extend(_world_bank_scalar_fields(value, path))
            elif value not in (None, ""):
                found.append((path.lower(), normalize_text(value)))
    elif isinstance(data, list):
        for index, value in enumerate(data):
            found.extend(_world_bank_scalar_fields(value, f"{prefix}[{index}]"))
    return found


def query_world_bank(term, diagnostics=None, search_mode="direct"):
    """Consulta avisos do Banco Mundial e tolera variações nos nomes dos campos."""
    if diagnostics is None:
        diagnostics = []
    diagnostic = {"source": "World Bank Procurement", "term": term, "method": "GET"}
    try:
        params = {
            "qterm": term, "rows": 200, "os": 0, "format": "json",
            "srt": "noticedate desc,id asc",
        }
        response = SESSION.get(WORLD_BANK_URL, params=params, timeout=(8, 25))
        diagnostic["status_code"] = response.status_code
        if response.status_code != 200:
            diagnostic["error"] = f"HTTP {response.status_code}: {response.text[:300]}"
            diagnostics.append(diagnostic)
            return []

        payload = response.json()
        notices = (payload.get("procnotices") or payload.get("procurements") or
                   payload.get("notices") or payload.get("results") or payload.get("data") or [])
        if isinstance(notices, dict):
            nested = (notices.get("procnotice") or notices.get("procurement") or
                      notices.get("notice") or notices.get("results"))
            notices = nested if nested is not None else list(notices.values())
        if isinstance(notices, dict):
            notices = list(notices.values())
        if not isinstance(notices, list):
            notices = []

        diagnostic["response_keys"] = list(payload.keys()) if isinstance(payload, dict) else []
        diagnostic["sample_item_keys"] = list(notices[0].keys())[:35] if notices and isinstance(notices[0], dict) else []
        diagnostic["sample_date_fields"] = []
        for sample in notices[:3]:
            if isinstance(sample, dict):
                diagnostic["sample_date_fields"].append({
                    str(key): value for key, value in sample.items()
                    if "date" in str(key).lower() or "time" in str(key).lower()
                })
        output = []
        missing_date = 0
        missing_title = 0
        for item in notices:
            if not isinstance(item, dict):
                continue

            title = first_value(item, [
                "bid_description", "title", "notice_title", "procurement_title",
                "project_name", "procurement_name", "contract_description",
                "notice_description", "description"
            ])
            description = first_value(item, [
                "description", "short_description", "procurement_description",
                "contract_description", "bid_description", "notice_description",
                "project_description", "scope_of_work", "goods_services"
            ])
            buyer = first_value(item, [
                "contact_organization", "borrower", "buyer", "client",
                "implementing_agency", "organization", "agency"
            ])
            country = first_value(item, [
                "country_code", "countrycode", "country_name", "borrower_country",
                "project_country", "country"
            ])
            published = first_value(item, [
                "publication_date", "notice_date", "published_date", "noticedate",
                "submission_date", "created_date", "date_published", "date",
                "noticeDate", "publishedDate", "publicationDate", "publish_date",
                "createdOn", "date_created", "noticePublicationDate"
            ])
            deadline = first_value(item, [
                "deadline_date", "submission_deadline_date", "submission_deadline",
                "bid_deadline", "deadline", "closing_date"
            ])
            url = first_value(item, ["url", "source_url", "notice_url", "procurement_url", "link"])
            notice_id = first_value(item, ["id", "notice_id", "procurement_id"])
            if not url and notice_id:
                url = f"https://projects.worldbank.org/en/projects-operations/procurement-detail/{notice_id}"
            cpvs = cpv_values(first_value(item, ["cpv", "cpvs", "classification"]))

            # A API muda ocasionalmente os nomes dos campos. Se os campos conhecidos
            # não existirem, procura texto em campos cujo nome sugira título/descrição.
            scalar_fields = _world_bank_scalar_fields(item)
            if not parse_date(published):
                date_values = [value for key, value in scalar_fields
                               if any(token in key for token in ("date", "noticedate", "published", "created"))]
                published = next((value for value in date_values if parse_date(value)), published)
            if not title:
                candidates = [value for key, value in scalar_fields
                              if any(word in key for word in ("title", "description", "procurement", "bid", "project"))]
                if not candidates:
                    term_norm = normalize_for_search(term)
                    candidates = [value for _, value in scalar_fields
                                  if term_norm and term_norm in normalize_for_search(value)]
                title = max(candidates, key=len) if candidates else ""
            if not description:
                description = " ".join(value for key, value in scalar_fields
                                        if any(word in key for word in ("description", "scope", "detail")))
            if not country:
                country = first_value(item, ["country", "country_name", "borrower_country", "project_country"])

            if not title and not description:
                missing_title += 1
                continue

            result = make_result(title, description, buyer, country,
                                 "World Bank Procurement", url, published,
                                 deadline, cpvs, search_mode)
            if not result:
                continue

            if result["date"] and not recent_enough(result["date"]):
                continue
            if not result["date"]:
                # Não descartar avisos relevantes apenas porque o fornecedor omitiu
                # a data no campo esperado; assinalar claramente a data por confirmar.
                missing_date += 1
                result["date_unconfirmed"] = True
                result["date_status"] = "Data de publicação desconhecida — confirmar no portal"
                result["score"] = max(25, result["score"] - 15)
            output.append(result)

        diagnostic["returned_items"] = len(notices)
        diagnostic["accepted_results"] = len(output)
        diagnostic["unknown_date_results"] = missing_date
        diagnostic["items_without_title_or_description"] = missing_title
        diagnostic["useful_results"] = len(output) > 0
        if not output:
            diagnostic["note"] = (
                "A API respondeu, mas não foi possível identificar avisos relevantes "
                "nos campos devolvidos; verificar a estrutura da resposta."
            )
        diagnostics.append(diagnostic)
        return output
    except Exception as exc:
        diagnostics.append({**diagnostic, "error": str(exc)})
        return []

def query_secop(term, diagnostics=None, search_mode="direct"):
    """Pesquisa SECOP II com os campos conhecidos e normalização de chaves/acentos."""
    if diagnostics is None:
        diagnostics = []
    diagnostic = {"source": "SECOP II — Colômbia", "term": term, "method": "GET"}
    try:
        response = SESSION.get(SECOP_URL, params={"$limit": 500, "$q": term}, timeout=(5, 18))
        diagnostic["status_code"] = response.status_code
        if response.status_code in (500, 502, 503, 504):
            diagnostic["retry"] = "Uma repetição após erro temporário do servidor"
            time.sleep(1.0)
            response = SESSION.get(SECOP_URL, params={"$limit": 500, "$q": term}, timeout=(5, 18))
            diagnostic["retry_status_code"] = response.status_code
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
        secop_terms = [normalize_for_search(t) for t in SECOP_TERMS + [
            "servicios arqueologicos", "servicio de arqueologia", "seguimiento arqueologico",
            "prospeccion arqueologica", "excavacion arqueologica", "patrimonio cultural"]]
        for item in payload:
            if not isinstance(item, dict):
                continue
            # O Socrata tem nomes de campos com variantes/acentos; a procura recursiva
            # usa todas as chaves disponíveis e estas variantes explícitas.
            title = first_value(item, ["nombre_del_procedimiento", "nombre_del_proceso",
                "descripcion_del_proceso", "descripci_n_del_procedimiento",
                "descripción_del_procedimiento", "objeto_del_contrato", "objeto_a_contratar",
                "nombre_procedimiento", "titulo", "title", "description"])
            description = first_value(item, ["descripci_n_del_procedimiento", "descripcion_del_proceso",
                "descripcion_del_procedimiento", "descripción_del_procedimiento", "descripcion",
                "objeto", "objeto_del_contrato", "objeto_a_contratar", "detalle_del_objeto_a_contratar",
                "description", "justificacion"])
            if not title and description:
                title = description
            title = repair_mojibake(title)
            description = repair_mojibake(description)
            combined = normalize_for_search(f"{title or ''} {description or ''}")
            # A API devolve pesquisa textual ampla. Só aceitar se o próprio registo
            # contiver linguagem arqueológica/patrimonial relevante.
            if not any(t and t in combined for t in secop_terms):
                continue
            buyer = first_value(item, ["nombre_entidad", "entidad", "nombre_de_la_entidad",
                "nombre_entidad_compradora", "razon_social", "buyer"])
            published = first_value(item, ["fecha_de_publicacion", "fecha_publicacion",
                "fecha_de_ultima_publicacion", "fecha_de_publicacion_del_proceso",
                "fecha_publicacion_proceso", "fecha_de_publicacion_del_proceso",
                "fecha_publicacion_proceso", "fecha_creacion", "fecha_de_creacion",
                "published_date", "publication_date", "created_at"])
            if not parse_date(published):
                date_values = [value for key, value in _world_bank_scalar_fields(item)
                               if "fecha" in key or "date" in key or "created" in key]
                published = next((value for value in date_values if parse_date(value)), published)
            deadline = first_value(item, ["fecha_de_recepcion_de_respuestas", "fecha_de_cierre",
                "fecha_cierre", "fecha_de_fin", "fecha_de_presentacion_de_ofertas"])
            url = first_value(item, ["urlproceso", "url", "url_del_proceso", "enlace_proceso",
                "url_proceso", "link"])
            cpvs = cpv_values(first_value(item, ["codigo_principal_de_categoria", "codigo_unspsc", "cpv"]))
            result = make_result(title, description, buyer, "CO", "SECOP II — Colombia",
                                 url, published, deadline, cpvs, search_mode)
            if result and recent_enough(result["date"]):
                output.append(result)
            elif result and not result["date"]:
                # Mantém o registo para transparência, mas assinala a ausência de data
                # e reduz fortemente a pontuação para não o confundir com oportunidade recente.
                result["date_status"] = "Data de publicação desconhecida — confirmar no portal"
                result["score"] = max(20, result["score"] - 25)
                result["date_unconfirmed"] = True
                output.append(result)
        diagnostic["returned_items"] = len(payload)
        diagnostic["sample_date_fields"] = [
            {str(key): value for key, value in item.items()
             if "fecha" in str(key).lower() or "date" in str(key).lower()}
            for item in payload[:3] if isinstance(item, dict)
        ]
        diagnostic["accepted_results"] = len(output)
        diagnostic["unknown_date_results"] = sum(1 for item in output if item.get("date_unconfirmed"))
        diagnostic["relevance_terms"] = len(secop_terms)
        diagnostic["useful_results"] = len(output) > 0
        if not output:
            diagnostic["note"] = "A API respondeu, mas não devolveu resultados relevantes dentro dos filtros."
        diagnostics.append(diagnostic)
        return output
    except Exception as exc:
        diagnostics.append({**diagnostic, "error": str(exc)})
        return []



def _ecuador_get(params):
    """Executa um pedido ao SERCOP com espaçamento e bloqueio global."""
    global ECUADOR_LAST_REQUEST_AT, ECUADOR_COOLDOWN_UNTIL
    with ECUADOR_REQUEST_LOCK:
        now = time.monotonic()
        remaining = ECUADOR_COOLDOWN_UNTIL - now
        if remaining > 0:
            return None, remaining

        wait_for = ECUADOR_REQUEST_INTERVAL - (now - ECUADOR_LAST_REQUEST_AT)
        if wait_for > 0:
            time.sleep(wait_for)

        response = SESSION.get(
            ECUADOR_API_URL,
            params=params,
            timeout=(8, 22)
        )
        ECUADOR_LAST_REQUEST_AT = time.monotonic()
        if response.status_code == 429:
            ECUADOR_COOLDOWN_UNTIL = time.monotonic() + ECUADOR_COOLDOWN_SECONDS
        return response, 0.0


def query_ecuador(term, diagnostics=None, search_mode="direct"):
    """Consulta a API oficial OCDS do Equador sem exceder os limites do servidor."""
    if diagnostics is None:
        diagnostics = []

    normalized = normalize_for_search(term)
    if (normalized in {"", "archaeology", "archaeological", "arqueologia", "cultural heritage", "heritage"}
            or "archaeolog" in normalized or "arqueolog" in normalized):
        search_terms = ["arqueologia", "arqueologico", "arqueológica"]
    else:
        search_terms = [term]

    output = []
    today = date.today()
    years = sorted({today.year, (today - timedelta(days=PERIOD_DAYS)).year})
    stop_all = False

    for search_term in search_terms:
        if stop_all:
            break
        for year in years:
            diagnostic = {
                "source": "Equador — SERCOP Contrataciones Abiertas OCDS",
                "term": search_term,
                "year": year,
                "method": "GET"
            }
            returned = 0
            accepted = 0
            pages_checked = 0
            try:
                # Uma página por combinação termo/ano nesta fase: reduz a carga
                # sem alterar a validação local dos registos recebidos.
                for page in (1,):
                    response, cooldown_remaining = _ecuador_get(
                        {"year": year, "search": search_term, "page": page}
                    )
                    if response is None:
                        diagnostic["skipped_due_to_cooldown"] = True
                        diagnostic["cooldown_remaining_seconds"] = int(cooldown_remaining)
                        diagnostic["note"] = "Consulta adiada para respeitar o limite temporário da API do Equador."
                        stop_all = True
                        break

                    diagnostic["status_code"] = response.status_code
                    if response.status_code == 429:
                        diagnostic["error"] = "HTTP 429: limite de pedidos atingido; consultas suspensas durante 15 minutos."
                        diagnostic["cooldown_seconds"] = ECUADOR_COOLDOWN_SECONDS
                        stop_all = True
                        break
                    if response.status_code != 200:
                        diagnostic["error"] = f"HTTP {response.status_code}: {response.text[:250]}"
                        break

                    payload = response.json()
                    items = payload.get("data", []) if isinstance(payload, dict) else []
                    if not isinstance(items, list):
                        diagnostic["error"] = "Formato de resposta inesperado na API OCDS do Equador"
                        break

                    returned += len(items)
                    pages_checked += 1
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        title = first_value(item, ["title", "tender_title", "name"])
                        description = first_value(item, ["description", "tender_description", "objeto"])
                        if not title:
                            title = description
                        buyer = first_value(item, ["buyerName", "buyer_name", "buyer"])
                        if isinstance(buyer, dict):
                            buyer = first_value(buyer, ["name", "legalName"])
                        published = first_value(item, ["date", "publishedDate", "publication_date"])
                        ocid = first_value(item, ["ocid", "id"])
                        url = ("https://datosabiertos.compraspublicas.gob.ec/PLATAFORMA/api/record?ocid=" + str(ocid)) if ocid else "https://datosabiertos.compraspublicas.gob.ec/"
                        searchable = normalize_for_search(f"{title or ''} {description or ''}")
                        if not any(x in searchable for x in ("arqueologia", "arqueologico", "arqueologica", "arqueologicas", "arqueologicos")):
                            continue
                        result = make_result(title, description, buyer, "EC",
                                             "Equador — SERCOP Contrataciones Abiertas OCDS",
                                             url, published, "", [], search_mode)
                        if not result:
                            continue
                        if result["date"] and not recent_enough(result["date"]):
                            continue
                        if not result["date"]:
                            result["date_unconfirmed"] = True
                            result["date_status"] = "Data de publicação desconhecida — confirmar no portal"
                            result["score"] = max(20, result["score"] - 20)
                        output.append(result)
                        accepted += 1

                diagnostic["returned_items"] = returned
                diagnostic["pages_checked"] = pages_checked
                diagnostic["accepted_results"] = accepted
                diagnostic["useful_results"] = accepted > 0
                if not diagnostic.get("error") and not diagnostic.get("skipped_due_to_cooldown") and not accepted:
                    diagnostic["note"] = "A API respondeu, mas não devolveu resultados arqueológicos nesta página."
                diagnostics.append(diagnostic)

            except Exception as exc:
                diagnostic["returned_items"] = returned
                diagnostic["pages_checked"] = pages_checked
                diagnostic["accepted_results"] = accepted
                diagnostic["error"] = str(exc)
                diagnostics.append(diagnostic)

            if stop_all:
                break

    return output


def query_brazil(term, diagnostics=None, search_mode="direct"):
    """Consulta o PNCP com proteção contra limites temporários de pedidos."""
    global PNCP_COOLDOWN_UNTIL
    if diagnostics is None:
        diagnostics = []

    with PNCP_COOLDOWN_LOCK:
        remaining = PNCP_COOLDOWN_UNTIL - time.monotonic()
    if remaining > 0:
        diagnostics.append({
            "source": "PNCP — Brasil", "term": term, "method": "GET",
            "skipped_due_to_rate_limit": True,
            "note": f"Consulta adiada devido a HTTP 429 anterior; nova tentativa em aproximadamente {int(remaining)} segundos."
        })
        return []

    output = []
    normalized_term = normalize_for_search(term)

    if normalized_term in {
        "archaeology", "archaeological", "arqueologia",
        "cultural heritage", "heritage"
    }:
        search_terms = [
            normalize_for_search(item) for item in BRAZIL_TERMS
        ]
    else:
        search_terms = [normalized_term]

    PNCP_PAGE_SIZE = 10
    PNCP_MAX_PAGES = 2

    rate_limited = False
    for modality_index, modality in enumerate(PNCP_MODALITIES):
        if modality_index:
            time.sleep(1.2)
        diagnostic = {
            "source": "PNCP — Brasil",
            "term": term,
            "method": "GET",
            "modality": modality
        }

        returned = 0
        accepted = 0
        pages_checked = 0
        total_pages_reported = None

        try:
            for page in range(1, PNCP_MAX_PAGES + 1):
                if pages_checked:
                    time.sleep(0.6)
                params = {
                    "dataInicial": cutoff_date().strftime("%Y%m%d"),
                    "dataFinal": date.today().strftime("%Y%m%d"),
                    "codigoModalidadeContratacao": modality,
                    "pagina": page,
                    "tamanhoPagina": PNCP_PAGE_SIZE,
                }

                try:
                    response = SESSION.get(
                        f"{PNCP_BASE_URL}/contratacoes/publicacao",
                        params=params,
                        timeout=(8, 22)
                    )
                except requests.exceptions.RequestException:
                    response = SESSION.get(
                        f"{PNCP_BASE_URL}/contratacoes/publicacao",
                        params=params,
                        timeout=(8, 28)
                    )

                diagnostic["status_code"] = response.status_code

                if response.status_code != 200:
                    diagnostic["error"] = (
                        f"HTTP {response.status_code}: "
                        f"{response.text[:250]}"
                    )
                    if response.status_code == 429:
                        with PNCP_COOLDOWN_LOCK:
                            PNCP_COOLDOWN_UNTIL = time.monotonic() + PNCP_COOLDOWN_SECONDS
                        diagnostic["note"] = (
                            "Limite de pedidos do PNCP atingido. As restantes modalidades "
                            "foram suspensas e a fonte ficará em pausa durante 15 minutos."
                        )
                        rate_limited = True
                    break

                payload = response.json()

                page_items = (
                    payload.get("data", [])
                    if isinstance(payload, dict)
                    else payload
                )

                if not isinstance(page_items, list):
                    diagnostic["error"] = (
                        "Formato de resposta inesperado"
                    )
                    break

                returned += len(page_items)
                pages_checked += 1

                if isinstance(payload, dict):
                    reported = payload.get("totalPaginas")
                    if reported is not None:
                        try:
                            total_pages_reported = int(reported)
                        except (TypeError, ValueError):
                            total_pages_reported = None

                for item in page_items:
                    if not isinstance(item, dict):
                        continue

                    title = first_value(
                        item,
                        ["objetoCompra", "objeto", "descricao", "description"]
                    )

                    description = first_value(
                        item,
                        [
                            "informacaoComplementar",
                            "objetoCompra",
                            "objeto",
                            "descricao",
                            "description"
                        ]
                    )

                    searchable = normalize_for_search(
                        f"{title or ''} {description or ''}"
                    )

                    if not any(
                        search_term and search_term in searchable
                        for search_term in search_terms
                    ):
                        continue

                    buyer_data = first_value(
                        item,
                        [
                            "orgaoEntidade",
                            "nomeUnidadeCompradora",
                            "razaoSocial",
                            "nomeOrgao"
                        ]
                    )

                    if isinstance(buyer_data, dict):
                        buyer = first_value(
                            buyer_data,
                            ["razaoSocial", "nome", "nomeOrgao"]
                        )
                    else:
                        buyer = buyer_data

                    published = first_value(
                        item,
                        [
                            "dataPublicacaoPncp",
                            "dataPublicacao",
                            "dataInclusao"
                        ]
                    )

                    deadline = first_value(
                        item,
                        [
                            "dataEncerramentoProposta",
                            "dataAberturaProposta",
                            "dataFimVigencia"
                        ]
                    )

                    url = first_value(
                        item,
                        [
                            "linkSistemaOrigem",
                            "linkProcessoEletronico",
                            "url",
                            "uri"
                        ]
                    )

                    control_number = first_value(
                        item,
                        ["numeroControlePNCP"]
                    )

                    if not url and control_number:
                        url = (
                            "https://pncp.gov.br/app/editais/"
                            + str(control_number)
                        )

                    cpvs = cpv_values(
                        first_value(
                            item,
                            ["codigoItem", "codigoCatmat", "cpv"]
                        )
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
                        cpvs,
                        search_mode
                    )

                    if result and (
                        recent_enough(result["date"])
                        or not result["date"]
                    ):
                        if not result["date"]:
                            result["date_status"] = (
                                "Data de publicação não fornecida pela fonte"
                            )
                            result["score"] = max(
                                25, result["score"] - 15
                            )

                        output.append(result)
                        accepted += 1

                if not page_items:
                    break

                if (
                    total_pages_reported is not None
                    and page >= total_pages_reported
                ):
                    break

            diagnostic["returned_items"] = returned
            diagnostic["pages_checked"] = pages_checked
            diagnostic["total_pages_reported"] = total_pages_reported
            diagnostic["page_size"] = PNCP_PAGE_SIZE
            diagnostic["accepted_results"] = accepted
            diagnostic["useful_results"] = accepted > 0

            if accepted == 0 and not diagnostic.get("error"):
                diagnostic["note"] = (
                    "A API respondeu, mas as páginas consultadas "
                    "não continham avisos arqueológicos relevantes."
                )

            diagnostics.append(diagnostic)
            if rate_limited:
                break

        except Exception as exc:
            diagnostics.append({
                **diagnostic,
                "returned_items": returned,
                "pages_checked": pages_checked,
                "error": str(exc)
            })

    return output


def automatic_search(query, diagnostics, country_code=None):
    normalized_query = normalize_for_search(query)
    mode = "direct"
    broad_search = normalized_query in {"", "arqueologia", "archaeology", "archaeological"}
    if broad_search:
        ted_terms = FAST_TED_TERMS
        # Menos consultas repetidas por pesquisa geral; mantém diversidade linguística.
        wb_terms = ["archaeology"]
        secop_terms = ["archaeology", "arqueologia", "servicios arqueologicos"]
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
    # SECOP é consultado sequencialmente para evitar picos concorrentes no Socrata.
    for term in secop_terms:
        results.extend(query_secop(term, diagnostics, mode))

    jobs = [(query_world_bank, term, mode) for term in wb_terms]
    jobs += [(query_brazil, brazil_term, mode)]
    if country_code in (None, "ECU"):
        jobs += [(query_ecuador, brazil_term, mode)]
    with ThreadPoolExecutor(max_workers=3) as executor:
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


def json_ascii_response(payload):
    # Escapes non-ASCII characters so names with accents remain readable even
    # in clients that mis-detect the JSON response encoding.
    return Response(content=json.dumps(payload, ensure_ascii=False), media_type="application/json; charset=utf-8")


@app.get("/health")
def health():
    return json_ascii_response({"ok": True, "version": "2.9.7", "sources": len(SOURCES),
            "api_sources": sum(1 for source in SOURCES if source.get("automatic")),
            "manual_portals": sum(1 for source in SOURCES if not source.get("automatic")),
            "period_days": PERIOD_DAYS, "ted_page_size": PAGE_SIZE,
            "ted_fast_terms": FAST_TED_TERMS, "pncp_modalities": PNCP_MODALITIES})


@app.get("/api/sources")
def api_sources():
    return json_ascii_response({"sources": SOURCES, "count": len(SOURCES),
            "automatic": sum(1 for source in SOURCES if source.get("automatic")),
            "manual": sum(1 for source in SOURCES if not source.get("automatic"))})


@app.get("/api/search")
def api_search(q: str = Query(default="archaeology"),
              country: str = Query(default=""), region: str = Query(default="")):
    diagnostics = []
    try:
        iso3 = country_iso3_from_text(country)
        mode, results = automatic_search(q, diagnostics, iso3 or None)
        results = deduplicate_results(results)
        results = filter_results(results, country, region)
        # Última camada de reparação para garantir que a resposta JSON sai em UTF-8 legível.
        for item in results:
            for field in ("title", "description", "buyer", "country", "region", "source", "url", "date_status"):
                if isinstance(item.get(field), str):
                    item[field] = repair_mojibake(item[field])
        results = sort_results(results)
        source_names = sorted({repair_mojibake(item.get("source", "")) for item in results if item.get("source")})
        regions = sorted({repair_mojibake(item.get("region", "")) for item in results if item.get("region")})
        automatic_source_names = {"TED — Europa", "World Bank Procurement", "SECOP II — Colômbia", "PNCP — Brasil", "Equador — SERCOP Contrataciones Abiertas OCDS"}
        successful_diagnostics = [d for d in diagnostics if d.get("status_code") == 200]
        failed_diagnostics = [d for d in diagnostics if d.get("error") or (d.get("status_code") not in (None, 200))]
        consulted_automatic_sources = sorted({d.get("source") for d in successful_diagnostics if d.get("source") in automatic_source_names})
        failed_automatic_sources = sorted({d.get("source") for d in failed_diagnostics if d.get("source") in automatic_source_names})
        return json_ascii_response({"ok": True, "version": "2.9.7", "query": q, "mode": mode,
                "results": results, "count": len(results), "sources": source_names,
                "source_count": len(source_names), "regions": regions, "diagnostics": diagnostics,
                "automatic_sources_consulted": consulted_automatic_sources,
                "automatic_sources_count": len(consulted_automatic_sources),
                "automatic_sources_failed": failed_automatic_sources,
                "automatic_sources_failed_count": len(failed_automatic_sources)})
    except Exception as exc:
        return json_ascii_response({"ok": False, "version": "2.9.7", "error": str(exc),
                "error_type": type(exc).__name__, "query": q, "diagnostics": diagnostics})


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
