from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from datetime import date
from pathlib import Path
import requests
import re
import time

ROOT = Path(__file__).resolve().parent.parent
app = FastAPI(title='Arqueologia Radar')
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

SOURCES = [
    ('TED','Europa','https://ted.europa.eu/en/search','api'),
    ('World Bank Procurement','Global','https://projects.worldbank.org/en/projects-operations/procurement','portal'),
    ('African Development Bank','África','https://www.afdb.org/en/documents/category/general-procurement-notices','portal'),
    ('AfDB Specific Procurement','África','https://www.afdb.org/en/documents/category/specific-procurement-notices','portal'),
    ('SAM.gov','Américas','https://sam.gov/opportunities','portal'),
    ('BASE Portugal','Europa','https://www.base.gov.pt/','portal'),
    ('Contratación Pública España','Europa','https://contrataciondelestado.es/','portal'),
    ('UN Development Business','Global','https://devbusiness.un.org/','portal'),
    ('UNGM','Global','https://www.ungm.org/Public/Notice','portal'),
    ('EBRD Procurement','Europa','https://www.ebrd.com/work-with-us/procurement.html','portal'),
    ('EIB Procurement','Europa','https://www.eib.org/en/projects/procurement/index.htm','portal'),
    ('Oman Tender Board','Médio Oriente','https://etendering.tenderboard.gov.om/','portal'),
    ('Saudi Etimad','Médio Oriente','https://portal.etimad.sa/','portal'),
    ('UAE Federal Procurement','Médio Oriente','https://procurement.gov.ae/','portal'),
    ('Qatar Monaqasat','Médio Oriente','https://monaqasat.mof.gov.qa/','portal'),
    ('Morocco Marchés Publics','África','https://www.marchespublics.gov.ma/','portal'),
    ('South Africa eTenders','África','https://www.etenders.gov.za/','portal'),
    ('Uganda eGP','África','https://egpuganda.go.ug/','portal'),
    ('Kenya PPIP','África','https://tenders.go.ke/','portal'),
    ('Tanzania NeST','África','https://nest.go.tz/','portal'),
    ('Mozambique UFSA','África','https://www.ufsa.gov.mz/','portal'),
    ('ChileCompra','Américas','https://www.mercadopublico.cl/','portal'),
    ('Colombia SECOP','Américas','https://www.colombiacompra.gov.co/secop','portal'),
    ('Brasil Compras.gov','Américas','https://www.gov.br/compras/','portal'),
    ('IDB Procurement','Américas','https://www.iadb.org/en/how-we-work/procurement','portal'),
    ('Asian Development Bank','Ásia-Pacífico','https://www.adb.org/work-with-us/procurement','portal'),
    ('Australia AusTender','Ásia-Pacífico','https://www.tenders.gov.au/','portal'),
    ('New Zealand GETS','Ásia-Pacífico','https://www.gets.govt.nz/','portal'),
]

ARCH = [
    'archaeology', 'archaeological', 'excavation', 'rescue archaeology',
    'preventive archaeology', 'archaeological monitoring', 'archaeological survey',
    'archaeological assessment', 'cultural heritage', 'historic environment',
    'chance finds', 'heritage management', 'unesco', 'monument',
    'archaeological investigation', 'archaeological works', 'archaeological services'
]

MAJOR = [
    'railway', 'rail', 'road', 'highway', 'mine', 'mining', 'copper', 'lithium',
    'oil', 'gas', 'lng', 'pipeline', 'airport', 'port', 'dam', 'hydroelectric',
    'solar', 'wind', 'energy', 'refinery', 'corridor', 'metro', 'subway',
    'transmission line', 'power line'
]

TED_FIELDS = [
    'publication-number',
    'publication-date',
    'notice-title',
    'buyer-name',
    'buyer-country',
    'classification-cpv',
    'notice-type',
    'deadline-receipt-tender-date-lot',
]

TED_URL = 'https://api.ted.europa.eu/v3/notices/search'


def flatten(value):
    """Converte valores TED (listas/dicionários multilíngues) em texto simples."""
    if value is None:
        return ''
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return ' | '.join(flatten(v) for v in value if flatten(v))
    if isinstance(value, dict):
        # TED costuma devolver campos multilingues, por exemplo {"eng": ["..."]}
        preferred = ['eng', 'en', 'por', 'pt', 'spa', 'es', 'fra', 'fr']
        for key in preferred:
            if key in value and flatten(value[key]):
                return flatten(value[key])
        return ' | '.join(flatten(v) for v in value.values() if flatten(v))
    return str(value)


def clean_query(text):
    # Evita que aspas/backslashes introduzidos pelo utilizador alterem a sintaxe TED.
    return re.sub(r'["\\]', ' ', text).strip()


def build_ted_query(q):
    q = clean_query(q or 'archaeology')
    if not q:
        q = 'archaeology'

    # Para a pesquisa base, alargamos a procura a termos que frequentemente
    # aparecem em concursos arqueológicos mesmo quando não usam exactamente
    # a palavra "archaeology".
    if q.lower() in {'archaeology', 'arqueologia'}:
        terms = ARCH[:10]
        clauses = [f'FT~"{clean_query(term)}"' for term in terms]
        return '(' + ' OR '.join(clauses) + ') SORT BY publication-date DESC'

    return f'FT~"{q}" SORT BY publication-date DESC'


def classify(text):
    t = text.lower()
    a = sum(1 for x in ARCH if x in t)
    m = sum(1 for x in MAJOR if x in t)

    if a >= 2 or any(x in t for x in ARCH[:9]):
        return 'Arqueologia direta', min(100, 60 + a * 5 + m * 2)
    if any(x in t for x in ARCH[9:]):
        return 'Património cultural', min(100, 45 + a * 5 + m * 2)
    if m:
        return 'Grande projeto / potencial subcontratação', min(100, 25 + m * 4)
    return 'Outro', 0


def ted(q):
    expert_query = build_ted_query(q)
    body = {
        'query': expert_query,
        'fields': TED_FIELDS,
        'limit': 100,
        'scope': 'ACTIVE',
        'paginationMode': 'PAGE_NUMBER',
        'page': 1,
        'checkQuerySyntax': False,
    }

    headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'User-Agent': 'Arqueologia-Radar/1.0',
    }

    last_error = None
    for attempt in range(3):
        try:
            r = requests.post(TED_URL, json=body, headers=headers, timeout=35)
            if r.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                time.sleep(2 ** attempt)
                continue
            if not r.ok:
                detail = r.text[:600].replace('\n', ' ')
                raise RuntimeError(f'TED HTTP {r.status_code}: {detail}')
            data = r.json()
            break
        except Exception as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
            else:
                raise RuntimeError(str(last_error))

    notices = data.get('notices', data.get('results', [])) or []
    out = []

    for n in notices:
        publication_number = flatten(n.get('publication-number'))
        title = flatten(n.get('notice-title')) or 'Concurso TED'
        buyer = flatten(n.get('buyer-name'))
        country = flatten(n.get('buyer-country'))
        cpv = flatten(n.get('classification-cpv'))
        deadline = flatten(n.get('deadline-receipt-tender-date-lot'))
        notice_type = flatten(n.get('notice-type'))
        text = ' '.join([title, buyer, country, cpv, notice_type, flatten(n)])
        category, score = classify(text)

        if publication_number:
            url = f'https://ted.europa.eu/en/notice/-/detail/{publication_number}'
        else:
            url = 'https://ted.europa.eu/en/search'

        out.append({
            'title': title,
            'source': 'TED',
            'date': flatten(n.get('publication-date')),
            'deadline': deadline,
            'country': country,
            'buyer': buyer,
            'cpv': cpv,
            'notice_type': notice_type,
            'url': url,
            'category': category,
            'score': score,
        })

    return out, {
        'source': 'TED',
        'ok': True,
        'count': len(out),
        'query': expert_query,
        'total': data.get('totalNoticeCount', data.get('total-matching-notices')),
    }


@app.get('/api/sources')
def sources():
    return [{'name': a, 'region': b, 'url': c, 'mode': d} for a, b, c, d in SOURCES]


@app.get('/api/search')
def search(
    q: str = Query('archaeology'),
    region: str = '',
    category: str = ''
):
    results = []
    diagnostics = []

    try:
        ted_results, status = ted(q)
        results.extend(ted_results)
        diagnostics.append(status)
    except Exception as e:
        diagnostics.append({'source': 'TED', 'ok': False, 'count': 0, 'error': str(e)})

    # O filtro regional é aplicado aos resultados do TED com base no país do comprador.
    # As restantes fontes continuam apresentadas como portais, porque ainda não têm
    # conectores automáticos nesta versão.
    if region:
        # TED é europeu; para já, não fingimos que um resultado TED pertence às outras regiões.
        if region != 'Europa':
            results = []

    if category:
        results = [x for x in results if x['category'] == category]

    results.sort(key=lambda x: (x.get('score', 0), x.get('date', '')), reverse=True)

    return {
        'results': results,
        'diagnostics': diagnostics,
        'portal_count': sum(1 for s in SOURCES if s[3] == 'portal' and (not region or s[1] in (region, 'Global'))),
        'api_count': sum(1 for s in SOURCES if s[3] == 'api'),
        'searched_at': date.today().isoformat(),
    }


@app.get('/api/health')
def health():
    return {'ok': True, 'sources': len(SOURCES), 'api_sources': sum(1 for s in SOURCES if s[3] == 'api')}


@app.get('/')
def home():
    return FileResponse(ROOT / 'web/index.html')

@app.get('/app.js')
def js():
    return FileResponse(ROOT / 'web/app.js', media_type='application/javascript')


@app.get('/manifest.json')
def manifest():
    return FileResponse(ROOT / 'web/manifest.json', media_type='application/manifest+json')
