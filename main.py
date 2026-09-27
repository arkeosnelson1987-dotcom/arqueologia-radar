from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
import httpx

app = FastAPI(title='Arqueologia Radar API', version='1.0')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_methods=['*'], allow_headers=['*'])

TED_API = 'https://api.ted.europa.eu/v3/notices/search'

FIELDS = [
    'publication-number', 'notice-title', 'buyer-name', 'publication-date',
    'deadline-date', 'place-of-performance', 'estimated-value', 'notice-type'
]

@app.get('/api/health')
async def health():
    return {'status': 'ok', 'service': 'arqueologia-radar'}

@app.get('/api/opportunities')
async def opportunities(q: str = Query('archaeology'), limit: int = Query(20, ge=1, le=100)):
    # TED Search API is public and does not require an API key.
    body = {
        'query': q,
        'fields': FIELDS,
        'page': 1,
        'limit': limit,
        'scope': 'ACTIVE',
        'checkQuerySyntax': True,
        'paginationMode': 'PAGE_NUMBER'
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(TED_API, json=body)
            r.raise_for_status()
            data = r.json()
        return {'source': 'TED', 'count': data.get('totalNoticeCount', 0), 'results': data.get('notices', data.get('results', []))}
    except Exception as exc:
        return {'source': 'TED', 'count': 0, 'results': [], 'error': 'NÃ£o foi possÃ­vel consultar o TED neste momento.', 'detail': str(exc)}

