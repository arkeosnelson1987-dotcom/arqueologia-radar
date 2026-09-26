from fastapi import FastAPI, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import requests, re, html
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
app=FastAPI(title='Arqueologia Radar')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['*'],allow_headers=['*'])

SOURCES=[
('TED','Europa','https://ted.europa.eu/en/search','api'),('World Bank Procurement','Global','https://projects.worldbank.org/en/projects-operations/procurement','portal'),('African Development Bank','África','https://www.afdb.org/en/documents/category/general-procurement-notices','portal'),('AfDB Specific Procurement','África','https://www.afdb.org/en/documents/category/specific-procurement-notices','portal'),('SAM.gov','Américas','https://sam.gov/opportunities','portal'),('BASE Portugal','Europa','https://www.base.gov.pt/','portal'),('Contratación Pública España','Europa','https://contrataciondelestado.es/','portal'),('UN Development Business','Global','https://devbusiness.un.org/','portal'),('UNGM','Global','https://www.ungm.org/Public/Notice','portal'),('EBRD Procurement','Europa','https://www.ebrd.com/work-with-us/procurement.html','portal'),('EIB Procurement','Europa','https://www.eib.org/en/projects/procurement/index.htm','portal'),('Oman Tender Board','Médio Oriente','https://etendering.tenderboard.gov.om/','portal'),('Saudi Etimad','Médio Oriente','https://portal.etimad.sa/','portal'),('UAE Federal Procurement','Médio Oriente','https://procurement.gov.ae/','portal'),('Qatar Monaqasat','Médio Oriente','https://monaqasat.mof.gov.qa/','portal'),('Morocco Marchés Publics','África','https://www.marchespublics.gov.ma/','portal'),('South Africa eTenders','África','https://www.etenders.gov.za/','portal'),('Uganda eGP','África','https://egpuganda.go.ug/','portal'),('Kenya PPIP','África','https://tenders.go.ke/','portal'),('Tanzania NeST','África','https://nest.go.tz/','portal'),('Mozambique UFSA','África','https://www.ufsa.gov.mz/','portal'),('ChileCompra','Américas','https://www.mercadopublico.cl/','portal'),('Colombia SECOP','Américas','https://www.colombiacompra.gov.co/secop','portal'),('Brasil Compras.gov','Américas','https://www.gov.br/compras/','portal'),('IDB Procurement','Américas','https://www.iadb.org/en/how-we-work/procurement','portal'),('Asian Development Bank','Ásia-Pacífico','https://www.adb.org/work-with-us/procurement','portal'),('Australia AusTender','Ásia-Pacífico','https://www.tenders.gov.au/','portal'),('New Zealand GETS','Ásia-Pacífico','https://www.gets.govt.nz/','portal')]

ARCH=['archaeology','archaeological','excavation','rescue archaeology','preventive archaeology','archaeological monitoring','archaeological survey','archaeological assessment','cultural heritage','historic environment','chance finds','heritage management','unesco','monument']
MAJOR=['railway','rail','road','highway','mine','mining','copper','lithium','oil','gas','lng','pipeline','airport','port','dam','hydroelectric','solar','wind','energy','refinery','corridor']

def classify(text):
    t=text.lower(); a=sum(x in t for x in ARCH); m=sum(x in t for x in MAJOR)
    if a>=2 or any(x in t for x in ARCH[:9]): return 'Arqueologia direta', min(100,60+a*5+m*2)
    if any(x in t for x in ARCH[9:]): return 'Património cultural', min(100,45+a*5+m*2)
    if m: return 'Grande projeto / potencial subcontratação', min(100,25+m*4)
    return 'Outro', 0

def ted(q):
    # TED expert syntax; query both title and description. API is public/anonymous.
    body={'query':f'(title~"{q}" OR description~"{q}")','fields':['publication-number','publication-date','notice-title','buyer-name','place-of-performance','links'],'page':1,'limit':100}
    r=requests.post('https://api.ted.europa.eu/v3/notices/search',json=body,timeout=30)
    r.raise_for_status(); data=r.json(); out=[]
    for n in data.get('notices',[]):
        title=n.get('notice-title') or n.get('title') or 'TED notice'; text=str(n)
        cat,score=classify(title+' '+text)
        links=n.get('links') or []
        url=links[0] if links and isinstance(links[0],str) else 'https://ted.europa.eu/'
        out.append({'title':title,'source':'TED','date':n.get('publication-date',''),'url':url,'category':cat,'score':score,'buyer':n.get('buyer-name','')})
    return out

@app.get('/api/sources')
def sources(): return [{'name':a,'region':b,'url':c,'mode':d} for a,b,c,d in SOURCES]

@app.get('/api/search')
def search(q: str=Query('archaeology'), region:str='', category:str=''):
    results=[]; errors=[]
    try: results.extend(ted(q))
    except Exception as e: errors.append('TED: '+str(e))
    if region: results=[x for x in results if region=='Europa' or x['source']!='TED']
    if category: results=[x for x in results if x['category']==category]
    results.sort(key=lambda x:(x.get('score',0),x.get('date','')),reverse=True)
    return {'results':results,'errors':errors,'portal_count':sum(1 for s in SOURCES if not region or s[1] in (region,'Global'))}

@app.get('/api/health')
def health(): return {'ok':True,'sources':len(SOURCES)}

@app.get('/')
def home(): return FileResponse(ROOT/'web/index.html')
@app.get('/app.js')
def js(): return FileResponse(ROOT/'web/app.js',media_type='application/javascript')
@app.get('/manifest.json')
def manifest(): return FileResponse(ROOT/'web/manifest.json',media_type='application/manifest+json')
