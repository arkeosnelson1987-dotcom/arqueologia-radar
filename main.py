from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from pathlib import Path
from datetime import date, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
import time
import html
import re
import requests
import unicodedata

BASE_DIR = Path(__file__).resolve().parent
app = FastAPI(title="Arqueologia Radar", version="2.7.0")

REQUEST_TIMEOUT = 30
PERIOD_DAYS = 365
PAGE_SIZE = 250

TED_URL = "https://api.ted.europa.eu/v3/notices/search"
WORLD_BANK_URL = "https://search.worldbank.org/api/v2/procnotices"
SECOP_URL = "https://www.datos.gov.co/resource/p6dx-8zbt.json"
BRAZIL_URL = "https://dadosabertos.compras.gov.br/modulo-contratacoes/1_consultarContratacoes_PNCP_14133"

SOURCES = [
    {"name":"TED — Europa","type":"api","automatic":True,"url":"https://ted.europa.eu/"},
    {"name":"World Bank Procurement","type":"api","automatic":True,"url":"https://projects.worldbank.org/"},
    {"name":"SECOP II — Colômbia","type":"api","automatic":True,"url":"https://www.datos.gov.co/"},
    {"name":"PNCP — Brasil","type":"api","automatic":True,"url":"https://www.gov.br/pncp/"},
    {"name":"South Africa eTenders","type":"portal","automatic":False,"url":"https://www.etenders.gov.za/"},
    {"name":"African Development Bank","type":"portal","automatic":False,"url":"https://www.afdb.org/"},
    {"name":"SAM.gov","type":"portal","automatic":False,"url":"https://sam.gov/"},
    {"name":"BASE Portugal","type":"portal","automatic":False,"url":"https://www.base.gov.pt/"},
    {"name":"Espanha","type":"portal","automatic":False,"url":"https://contrataciondelestado.es/"},
    {"name":"UNDB","type":"portal","automatic":False,"url":"https://devbusiness.un.org/"},
    {"name":"UNGM","type":"portal","automatic":False,"url":"https://www.ungm.org/"},
    {"name":"EBRD","type":"portal","automatic":False,"url":"https://www.ebrd.com/"},
    {"name":"EIB","type":"portal","automatic":False,"url":"https://www.eib.org/"},
    {"name":"Oman","type":"portal","automatic":False,"url":"https://etendering.tenderboard.gov.om/"},
    {"name":"Saudi Etimad","type":"portal","automatic":False,"url":"https://tenders.etimad.sa/"},
    {"name":"UAE","type":"portal","automatic":False,"url":"https://mof.gov.ae/"},
    {"name":"Qatar","type":"portal","automatic":False,"url":"https://monaqasat.mof.gov.qa/"},
    {"name":"Morocco","type":"portal","automatic":False,"url":"https://www.marchespublics.gov.ma/"},
    {"name":"Uganda","type":"portal","automatic":False,"url":"https://www.ppda.go.ug/"},
    {"name":"Kenya","type":"portal","automatic":False,"url":"https://tenders.go.ke/"},
    {"name":"Tanzania","type":"portal","automatic":False,"url":"https://www.ppra.go.tz/"},
    {"name":"Mozambique","type":"portal","automatic":False,"url":"https://www.ufsa.gov.mz/"},
    {"name":"ChileCompra","type":"portal","automatic":False,"url":"https://www.mercadopublico.cl/"},
    {"name":"IDB","type":"portal","automatic":False,"url":"https://www.iadb.org/"},
    {"name":"ADB","type":"portal","automatic":False,"url":"https://www.adb.org/"},
    {"name":"AusTender","type":"portal","automatic":False,"url":"https://www.tenders.gov.au/"},
    {"name":"NZ GETS","type":"portal","automatic":False,"url":"https://www.gets.govt.nz/"},
    {"name":"Redeia","type":"portal","automatic":False,"url":"https://www.ree.es/"},
]

DIRECT_TERMS = [
    "archaeology","archaeological","archaeologist","archaeological excavation",
    "archaeological monitoring","archaeological survey","archaeological investigation",
    "archaeological services","archaeological assessment","archaeological fieldwork",
    "watching brief","archéologie","archéologique","archéologue",
    "fouille archéologique","surveillance archéologique","diagnostic archéologique",
    "arqueologia","arqueológico","arqueóloga","arqueólogo","escavação arqueológica",
    "acompanhamento arqueológico","prospeção arqueológica","prospecção arqueológica",
    "sondagem arqueológica","archäologie","archäologisch","archäologische ausgrabung",
    "archeologie","archeologisch",
]

HERITAGE_TERMS = [
    "cultural heritage","heritage","historic environment","historical environment",
    "built heritage","archaeological heritage","historic site","historical site",
    "monument","monuments","unesco","cultural property","patrimoine culturel",
    "patrimoine","monument historique","site historique","património cultural",
    "patrimônio cultural","património","patrimonio cultural","monumento",
    "sítio arqueológico","sitio arqueologico","kulturerbe","kulturelles erbe",
    "cultureel erfgoed",
]

MAJOR_PROJECT_TERMS = [
    "railway","rail","road","highway","bridge","tunnel","airport","port","mining",
    "mine","pipeline","gas pipeline","oil pipeline","energy","power","substation",
    "transmission line","construction","infrastructure","water supply","dam",
    "ferroviaire","route","autoroute","pont","tunnel","aéroport","port","mine",
    "pipeline","énergie","construction","infrastructure","ferrovia","rodovia",
    "estrada","ponte","túnel","aeroporto","porto","mineração","oleoduto",
    "gasoduto","energia","construção","infraestrutura",
]

ARCHAEOLOGY_CPVS = ["71351914","71351910","71351900","71351720","71351811","71351730"]

# Apenas os termos de maior rendimento: muito menos chamadas TED.
FAST_TED_TERMS = ["archaeology","archaeological","cultural heritage","arqueologia"]
WORLD_BANK_TERMS = ["archaeology","archaeological","cultural heritage","heritage"]
SECOP_TERMS = ["archaeology","archaeological","arqueologia","heritage"]
BRAZIL_TERMS = ["archaeology","archaeological","arqueologia"]

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
"QA":"Qatar","OM":"Omã"}

ISO3_MAP = {
"PT":"PRT","ES":"ESP","FR":"FRA","DE":"DEU","IT":"ITA","NL":"NLD","BE":"BEL","LU":"LUX","IE":"IRL",
"GB":"GBR","UK":"GBR","CH":"CHE","AT":"AUT","PL":"POL","CZ":"CZE","SK":"SVK","HU":"HUN",
"RO":"ROU","BG":"BGR","GR":"GRC","HR":"HRV","SI":"SVN","SE":"SWE","NO":"NOR","DK":"DNK",
"FI":"FIN","EE":"EST","LV":"LVA","LT":"LTU","MT":"MLT","CY":"CYP","IS":"ISL","MA":"MAR",
"DZ":"DZA","TN":"TUN","EG":"EGY","ZA":"ZAF","KE":"KEN","UG":"UGA","TZ":"TZA","MZ":"MOZ",
"GH":"GHA","NG":"NGA","SN":"SEN","ET":"ETH","US":"USA","CA":"CAN","MX":"MEX","BR":"BRA",
"AR":"ARG","CL":"CHL","CO":"COL","PE":"PER","UY":"URY","PY":"PRY","BO":"BOL","EC":"ECU",
"CN":"CHN","JP":"JPN","KR":"KOR","IN":"IND","ID":"IDN","MY":"MYS","TH":"THA","VN":"VNM",
"PH":"PHL","AU":"AUS","NZ":"NZL","SA":"SAU","AE":"ARE","QA":"QAT","OM":"OMN"}

REGION_COUNTRIES = {
"Europa":{"PT","ES","FR","DE","IT","NL","BE","LU","IE","GB","UK","CH","AT","PL","CZ","SK","HU","RO","BG","GR","HR","SI","SE","NO","DK","FI","EE","LV","LT","MT","CY","IS"},
"África":{"MA","DZ","TN","EG","ZA","KE","UG","TZ","MZ","GH","NG","SN","ET"},
"América":{"US","CA","MX","BR","AR","CL","CO","PE","UY","PY","BO","EC"},
"Ásia":{"CN","JP","KR","IN","ID","MY","TH","VN","PH","SA","AE","QA","OM"},
"Oceania":{"AU","NZ"}}

TED_FIELDS = ["publication-number","publication-date","notice-title","buyer-name",
"organisation-country-buyer","buyer-country","classification-cpv","description-proc",
"description-glo","deadline-date-lot"]

def flatten_values(value):
    if value is None: return []
    if isinstance(value,list):
        out=[]
        for x in value: out.extend(flatten_values(x))
        return out
    if isinstance(value,dict):
        out=[]
        for x in value.values(): out.extend(flatten_values(x))
        return out
    return [value]

def normalize_text(value):
    if value is None: return ""
    if isinstance(value,(dict,list)):
        return " ".join(str(x) for x in flatten_values(value) if x not in (None,"")).strip()
    return html.unescape(str(value)).strip()

def normalize_for_search(value):
    text=unicodedata.normalize("NFKD",normalize_text(value))
    return re.sub(r"\s+"," ","".join(c for c in text if not unicodedata.combining(c)).lower()).strip()

def repair_mojibake(value):
    text=normalize_text(value)
    for old,new in {"Ã¡":"á","Ã©":"é","Ã­":"í","Ã³":"ó","Ãº":"ú","Ã£":"ã","Ãµ":"õ",
                    "Ã§":"ç","Ã€":"À","Ã‰":"É","Ã‡":"Ç","â€“":"–","â€”":"—",
                    "â€œ":"“","â€":"”","â€˜":"‘","â€™":"’","Â":""}.items():
        text=text.replace(old,new)
    return text

def parse_date(value):
    if value is None: return None
    if isinstance(value,datetime): return value.date()
    if isinstance(value,date): return value
    text=str(value).strip().replace(" ","")
    if not text: return None
    for fmt in ("%Y-%m-%d","%Y-%m-%d+%H:%M","%Y-%m-%dT%H:%M:%S",
                "%Y-%m-%dT%H:%M:%SZ","%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%S.%fZ","%d/%m/%Y","%Y/%m/%d"):
        try: return datetime.strptime(text,fmt).date()
        except Exception: pass
    try: return datetime.fromisoformat(text.replace("Z","+00:00")).date()
    except Exception: return None

def cutoff_date(): return date.today()-timedelta(days=PERIOD_DAYS)
def recent_enough(value):
    d=parse_date(value)
    return d is not None and d>=cutoff_date()

def recursive_find(data,keys):
    if isinstance(data,dict):
        for k in keys:
            if k in data and data[k] not in (None,"",[]): return data[k]
        for v in data.values():
            x=recursive_find(v,keys)
            if x not in (None,"",[]): return x
    elif isinstance(data,list):
        for v in data:
            x=recursive_find(v,keys)
            if x not in (None,"",[]): return x
    return None

def first_value(data,keys): return recursive_find(data,keys)

def safe_first_text(data,keys):
    for x in flatten_values(first_value(data,keys)):
        t=normalize_text(x)
        if t: return t
    return ""

def country_from_text(value):
    text=normalize_for_search(value)
    if not text: return ""
    if len(text)==2:
        for code in COUNTRY_MAP:
            if code.lower()==text: return code
    if len(text)==3:
        for code,iso3 in ISO3_MAP.items():
            if iso3.lower()==text: return code
    for code,name in COUNTRY_MAP.items():
        n=normalize_for_search(name)
        if n==text or (len(text)>2 and n in text): return code
    return ""

def country_iso3_from_text(value):
    return ISO3_MAP.get(country_from_text(value),"")

def country_name(code):
    code=str(code or "").upper().strip()
    if code in COUNTRY_MAP: return COUNTRY_MAP[code]
    for iso2,iso3 in ISO3_MAP.items():
        if code==iso3: return COUNTRY_MAP.get(iso2,code)
    return code

def region_from_country(code):
    code=str(code or "").upper().strip()
    for iso2,iso3 in ISO3_MAP.items():
        if code==iso3: code=iso2; break
    for region,countries in REGION_COUNTRIES.items():
        if code in countries: return region
    return ""

def cpv_values(value):
    out=[]
    for x in flatten_values(value):
        out.extend(re.findall(r"\b\d{8}\b",normalize_text(x)))
    return list(dict.fromkeys(out))

def has_direct_archaeology(text):
    n=normalize_for_search(text)
    return any(normalize_for_search(t) in n for t in DIRECT_TERMS)

def has_heritage(text):
    n=normalize_for_search(text)
    return any(normalize_for_search(t) in n for t in HERITAGE_TERMS)

def has_major_project(text):
    n=normalize_for_search(text)
    return any(normalize_for_search(t) in n for t in MAJOR_PROJECT_TERMS)

def classify_result(title,description,cpvs,search_mode="direct"):
    text=f"{normalize_text(title)} {normalize_text(description)}"
    direct=has_direct_archaeology(text)
    heritage=has_heritage(text)
    major=has_major_project(text)
    cpv_direct=any(c in ARCHAEOLOGY_CPVS for c in cpvs)
    if search_mode=="direct":
        return "Arqueologia direta" if (direct or cpv_direct) else ""
    if direct: return "Arqueologia direta"
    if heritage and major: return "Património / grandes projetos"
    if heritage: return "Património cultural"
    if cpv_direct: return "Arqueologia direta"
    return ""

def make_result(title,description,buyer,country,source,url,published,deadline,cpvs,search_mode="direct"):
    title=repair_mojibake(title); description=repair_mojibake(description); buyer=repair_mojibake(buyer)
    code=country_from_text(country)
    classification=classify_result(title,description,cpvs,search_mode)
    if not classification: return None
    pd=parse_date(published); dd=parse_date(deadline)
    return {"title":title,"description":description,"buyer":buyer,
            "country":country_name(code),"country_code":code,"region":region_from_country(code),
            "source":source,"url":url or "","date":pd.isoformat() if pd else "",
            "deadline":dd.isoformat() if dd else "","cpv":cpvs,
            "classification":classification,
            "score":100 if classification=="Arqueologia direta" else 70}

def build_ted_query(term,country_code=None):
    today=date.today(); start=today-timedelta(days=PERIOD_DAYS)
    parts=[f'FT~"{normalize_text(term)}"',
           f"publication-date>={start.strftime('%Y%m%d')}",
           f"publication-date<={today.strftime('%Y%m%d')}"]
    if country_code: parts.append(f"buyer-country={str(country_code).upper().strip()}")
    return " AND ".join(parts)

def _ted_post(query):
    return requests.post(TED_URL,json={"query":query,"fields":TED_FIELDS,"page":1,
        "limit":PAGE_SIZE,"paginationMode":"PAGE_NUMBER"},timeout=REQUEST_TIMEOUT,
        headers={"Accept":"application/json","Content-Type":"application/json"})

def query_ted(term,diagnostics=None,search_mode="direct",country_code=None):
    if diagnostics is None: diagnostics=[]
    query=build_ted_query(term,country_code)
    time.sleep(0.08)
    try:
        response=_ted_post(query)
        d={"source":"TED — Europa","term":term,"method":"POST","status_code":response.status_code,
           "query":query,"period_start":cutoff_date().isoformat(),
           "period_end":date.today().isoformat(),"country_code":country_code or ""}
        diagnostics.append(d)
        if response.status_code==429:
            d["error"]="TED rate limit (429)"
            time.sleep(1.5)
            response=_ted_post(query)
            d["retry_status_code"]=response.status_code
        if response.status_code!=200:
            d["error"]=response.text[:1000]
            return []
        data=response.json(); notices=data.get("notices",[])
        if isinstance(notices,dict): notices=list(notices.values())
        results=[]
        for notice in notices:
            if not isinstance(notice,dict): continue
            title=safe_first_text(notice,["notice-title","title"])
            description=safe_first_text(notice,["description-proc","description-glo","description"])
            buyer=safe_first_text(notice,["buyer-name","buyer"])
            country=safe_first_text(notice,["organisation-country-buyer","buyer-country","country"])
            published=safe_first_text(notice,["publication-date","publicationDate"])
            deadline=safe_first_text(notice,["deadline-date-lot","deadline-date"])
            number=safe_first_text(notice,["publication-number","publicationNumber"])
            cpvs=cpv_values(first_value(notice,["classification-cpv","cpv","CPV"]))
            if not recent_enough(published): continue
            result=make_result(title,description,buyer,country,"TED — Europa",
                f"https://ted.europa.eu/en/notice/{number}" if number else "",
                published,deadline,cpvs,search_mode)
            if result: results.append(result)
        d["returned_notices"]=len(notices); d["accepted_results"]=len(results)
        return results
    except Exception as exc:
        diagnostics.append({"source":"TED — Europa","term":term,"method":"POST","query":query,"error":str(exc)})
        return []

def query_world_bank(term,diagnostics=None,search_mode="direct"):
    if diagnostics is None: diagnostics=[]
    try:
        r=requests.get(WORLD_BANK_URL,params={"qterm":term,"rows":PAGE_SIZE,"format":"json"},timeout=REQUEST_TIMEOUT)
        diagnostics.append({"source":"World Bank Procurement","term":term,"method":"GET","status_code":r.status_code})
        if r.status_code!=200: return []
        data=r.json(); notices=data.get("procurements") or data.get("notices") or data.get("results") or []
        if isinstance(notices,dict): notices=list(notices.values())
        out=[]
        for item in notices:
            if not isinstance(item,dict): continue
            title=first_value(item,["project_name","title","notice_title","procurement_name","contract_description"])
            description=first_value(item,["description","short_description","procurement_description","contract_description"])
            buyer=first_value(item,["borrower","buyer","client","country_name"])
            country=first_value(item,["countrycode","country_code","country"])
            published=first_value(item,["publication_date","published_date","notice_date","date"])
            deadline=first_value(item,["deadline","submission_deadline","bid_deadline"])
            url=first_value(item,["url","notice_url","procurement_url","link"])
            cpvs=cpv_values(first_value(item,["cpv","cpvs","classification"]))
            x=make_result(title,description,buyer,country,"World Bank Procurement",url,published,deadline,cpvs,search_mode)
            if x and recent_enough(x["date"]): out.append(x)
        return out
    except Exception as exc:
        diagnostics.append({"source":"World Bank Procurement","term":term,"error":str(exc)})
        return []

def query_secop(term,diagnostics=None,search_mode="direct"):
    if diagnostics is None: diagnostics=[]
    try:
        r=requests.get(SECOP_URL,params={"$limit":1000,"$q":term},timeout=REQUEST_TIMEOUT)
        diagnostics.append({"source":"SECOP II — Colômbia","term":term,"method":"GET","status_code":r.status_code})
        if r.status_code!=200: return []
        data=r.json()
        if not isinstance(data,list): return []
        out=[]; tn=normalize_for_search(term)
        for item in data:
            if not isinstance(item,dict): continue
            title=first_value(item,["descripcion_del_proceso","nombre_del_procedimiento","titulo","description"])
            description=first_value(item,["descripcion","description","objeto"])
            if tn not in normalize_for_search(f"{title or ''} {description or ''}"): continue
            buyer=first_value(item,["nombre_entidad","entidad","buyer"])
            published=first_value(item,["fecha_de_publicacion","fecha_publicacion","fecha_de_ultima_publicacion"])
            deadline=first_value(item,["fecha_de_recepcion_de_respuestas","fecha_de_cierre","fecha_cierre"])
            url=first_value(item,["urlproceso","url"])
            cpvs=cpv_values(first_value(item,["codigo_principal_de_categoria","codigo_unspsc","cpv"]))
            x=make_result(title,description,buyer,"CO","SECOP II — Colômbia",url,published,deadline,cpvs,search_mode)
            if x and recent_enough(x["date"]): out.append(x)
        return out
    except Exception as exc:
        diagnostics.append({"source":"SECOP II — Colômbia","term":term,"error":str(exc)})
        return []

BRAZIL_MODALITIES=[4,5,6,7,12]

def query_brazil(term,diagnostics=None,search_mode="direct"):
    if diagnostics is None: diagnostics=[]
    out=[]; tn=normalize_for_search(term)
    for modality in BRAZIL_MODALITIES:
        try:
            r=requests.get(BRAZIL_URL,params={"dataInicial":cutoff_date().isoformat(),
                "dataFinal":date.today().isoformat(),"codigoModalidadeContratacao":modality,
                "pagina":1,"tamanhoPagina":50},timeout=REQUEST_TIMEOUT)
            diagnostics.append({"source":"PNCP — Brasil","term":term,"method":"GET","modality":modality,"status_code":r.status_code})
            if r.status_code!=200: continue
            data=r.json(); items=data.get("data") if isinstance(data,dict) else data
            if not isinstance(items,list): continue
            for item in items:
                if not isinstance(item,dict): continue
                title=first_value(item,["objetoCompra","objeto","descricao","description"])
                if tn not in normalize_for_search(title): continue
                buyer=first_value(item,["razaoSocial","nomeUnidadeCompradora","orgaoEntidade"])
                published=first_value(item,["dataPublicacaoPncp","dataPublicacao","dataInclusao"])
                deadline=first_value(item,["dataFimVigencia","dataEncerramento","dataAberturaProposta"])
                url=first_value(item,["linkSistemaOrigem","linkProcessoEletronico","url"])
                cpvs=cpv_values(first_value(item,["codigoItem","codigoCatmat","cpv"]))
                x=make_result(title,title,buyer,"BR","PNCP — Brasil",url,published,deadline,cpvs,search_mode)
                if x and recent_enough(x["date"]): out.append(x)
        except Exception as exc:
            diagnostics.append({"source":"PNCP — Brasil","term":term,"modality":modality,"error":str(exc)})
    return out

def automatic_search(query,diagnostics,country_code=None):
    q=normalize_for_search(query)
    mode="direct"
    if q in {"","arqueologia","archaeology","archaeological"}:
        ted_terms=FAST_TED_TERMS; wb_terms=WORLD_BANK_TERMS
        secop_terms=SECOP_TERMS; brazil_terms=BRAZIL_TERMS
    else:
        ted_terms=[query]; wb_terms=[query]; secop_terms=[query]; brazil_terms=[query]
    results=[]
    for term in ted_terms:
        results.extend(query_ted(term,diagnostics,mode,country_code))
    jobs=[(query_world_bank,t,mode) for t in wb_terms]
    jobs += [(query_secop,t,mode) for t in secop_terms]
    jobs += [(query_brazil,t,mode) for t in brazil_terms]
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures=[executor.submit(fn,t,m,mode) for fn,t,mode in jobs]
        for f in as_completed(futures):
            try: results.extend(f.result())
            except Exception as exc: diagnostics.append({"source":"automatic","error":str(exc)})
    return mode,results

def filter_results(results,country="",region=""):
    code=country_from_text(country); cn=normalize_for_search(country); rn=normalize_for_search(region)
    if cn:
        results=[x for x in results if normalize_for_search(x.get("country",""))==cn or
                 normalize_for_search(x.get("country_code",""))==cn or
                 (code and x.get("country_code")==code)]
    if rn: results=[x for x in results if normalize_for_search(x.get("region",""))==rn]
    return results

def deduplicate_results(results):
    seen=set(); out=[]
    for x in results:
        url=normalize_for_search(x.get("url",""))
        key=("url",url) if url else ("text",normalize_for_search(x.get("title","")),
            normalize_for_search(x.get("buyer","")),normalize_for_search(x.get("country_code","")),
            normalize_for_search(x.get("source","")))
        if key in seen: continue
        seen.add(key); out.append(x)
    return out

def sort_results(results):
    results.sort(key=lambda x:(-int(x.get("score",0)),x.get("date","0000-00-00")),reverse=True)
    return results

@app.get("/")
def index(): return FileResponse(BASE_DIR/"index.html")

@app.get("/app.js")
def app_js(): return FileResponse(BASE_DIR/"app.js",media_type="application/javascript")

@app.get("/manifest.json")
def manifest(): return FileResponse(BASE_DIR/"manifest.json",media_type="application/json")

@app.get("/health")
def health():
    return {"ok":True,"version":"2.7.0","sources":len(SOURCES),
            "api_sources":sum(1 for s in SOURCES if s.get("automatic")),
            "period_days":PERIOD_DAYS,"ted_page_size":PAGE_SIZE,
            "ted_fast_terms":FAST_TED_TERMS}

@app.get("/api/sources")
def api_sources():
    return {"sources":SOURCES,"count":len(SOURCES),
            "automatic":sum(1 for s in SOURCES if s.get("automatic"))}

@app.get("/api/search")
def api_search(
    q: str = Query(default="archaeology"),
    country: str = Query(default=""),
    region: str = Query(default="")
):
    diagnostics = []

    try:
        iso3 = country_iso3_from_text(country)

        mode, results = automatic_search(
            q,
            diagnostics,
            iso3 or None
        )

        results = deduplicate_results(results)

        results = filter_results(
            results,
            country,
            region
        )

        results = sort_results(results)

        source_names = sorted(
            set(
                x.get("source", "")
                for x in results
                if x.get("source")
            )
        )

        regions = sorted(
            set(
                x.get("region", "")
                for x in results
                if x.get("region")
            )
        )

        return {
            "ok": True,
            "query": q,
            "mode": mode,
            "results": results,
            "count": len(results),
            "sources": source_names,
            "source_count": len(source_names),
            "regions": regions,
            "diagnostics": diagnostics
        }

    except Exception as exc:
        return {
            "ok": False,
            "error": str(exc),
            "error_type": type(exc).__name__,
            "query": q,
            "diagnostics": diagnostics
        }

@app.get("/api/test-ted-minimal")
def test_ted_minimal(term:str=Query(default="archaeology")):
    query=build_ted_query(term)
    try:
        r=_ted_post(query)
        try: data=r.json()
        except Exception: data=r.text[:5000]
        return {"ok":r.status_code==200,"status_code":r.status_code,"method":"POST","query":query,"response":data}
    except Exception as exc: return {"ok":False,"method":"POST","query":query,"error":str(exc)}

@app.get("/api/test-ted-portugal")
def test_ted_portugal(term:str="archaeology"):
    d=[]; results=query_ted(term,d,"direct","PRT")
    pt=[x for x in results if x.get("country_code")=="PT"]
    return {"ok":True,"term":term,"count_total":len(results),"count_portugal":len(pt),
            "results_portugal":pt[:10],"diagnostics":d}

@app.get("/api/test-ted-search")
def test_ted_search(term:str="archaeology"):
    d=[]; results=query_ted(term,d,"direct")
    return {"ok":True,"term":term,"count":len(results),"results":results[:10],"diagnostics":d}

@app.get("/api/test-ted-country")
def test_ted_country(term:str=Query(default="archaeology"),country:str=Query(default="PRT")):
    query=f'FT~"{term}" AND buyer-country={country}'
    try:
        r=requests.post(TED_URL,json={"query":query,"fields":TED_FIELDS,"page":1,"limit":10,
            "paginationMode":"PAGE_NUMBER"},timeout=REQUEST_TIMEOUT,
            headers={"Accept":"application/json","Content-Type":"application/json"})
        try: data=r.json()
        except Exception: data=r.text[:5000]
        return {"ok":r.status_code==200,"status_code":r.status_code,"method":"POST","query":query,"response":data}
    except Exception as exc: return {"ok":False,"method":"POST","query":query,"error":str(exc)}
