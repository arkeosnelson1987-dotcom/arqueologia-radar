from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx
app=FastAPI(title='Arqueologia Radar API',version='1.1')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['*'],allow_headers=['*'])
TED='https://api.ted.europa.eu/v3/notices/search'
TERMS=['archaeolog','archéolog','arqueolog','cultural heritage','heritage management','chance finds','excavation','archaeological survey','archaeological monitoring','preventive archaeology']
def score(t): return min(100,sum(15 for x in TERMS if x in t.lower()))
@app.get('/api/health')
def health(): return {'status':'ok','service':'arqueologia-radar'}
@app.get('/api/opportunities')
async def opportunities(q:str=Query('archaeology'),limit:int=Query(50,ge=1,le=100)):
    try:
        async with httpx.AsyncClient(timeout=30) as c:
            r=await c.post(TED,json={'query':q,'page':1,'limit':limit}); r.raise_for_status(); data=r.json()
        notices=data.get('notices',data.get('results',[])); out=[]
        for n in notices[:limit]:
            title=n.get('title') or n.get('publicationNumber') or 'Aviso TED'
            if isinstance(title,dict): title=next(iter(title.values()),'Aviso TED')
            out.append({'title':str(title),'description':'','source':'TED','date':n.get('publicationDate',''),'buyer':'','url':'','relevance':score(str(title)+' '+str(n)),'category':'Arqueologia direta'})
        return {'count':len(out),'results':out}
    except Exception as e: return {'count':0,'results':[],'error':'Falha na consulta TED','detail':str(e)}
