const $ = id => document.getElementById(id);

const esc = s =>
  String(s ?? '').replace(/[&<>"]/g, c => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;'
  }[c]));

function diagnosticHtml(d) {
  if (d.ok) {
    return `<div class="diag ok">
      🟢 <b>${esc(d.source)}</b>: ${d.count} resultados encontrados.
    </div>`;
  }

  return `<div class="diag error">
    🔴 <b>${esc(d.source)}</b>: não foi possível pesquisar.
    ${esc(d.error || 'Erro desconhecido.')}
  </div>`;
}

async function fetchWithTimeout(url, options = {}, timeout = 60000) {
  const controller = new AbortController();

  const timer = setTimeout(() => {
    controller.abort();
  }, timeout);

  try {
    const response = await fetch(url, {
      ...options,
      signal: controller.signal,
      cache: 'no-store'
    });

    return response;
  } finally {
    clearTimeout(timer);
  }
}

async function go() {
  const q = $('q').value.trim() || 'archaeology';

  $('status').innerHTML =
    '🔎 <b>A pesquisar...</b> O Radar está a consultar as fontes automáticas.';

  $('results').innerHTML = '';
  $('diagnostics').innerHTML = '';

  try {
    const p = new URLSearchParams({
      q,
      region: $('region').value,
      category: $('category').value
    });

    const url = '/api/search?' + p.toString();

    console.log('Radar: a consultar', url);

    const r = await fetchWithTimeout(url, {}, 60000);

    console.log('Radar: resposta recebida', r.status);

    const text = await r.text();

    console.log('Radar: resposta recebida, tamanho:', text.length);

    let j;

    try {
      j = JSON.parse(text);
    } catch (e) {
      throw new Error(
        'A API respondeu, mas o navegador não conseguiu interpretar a resposta.'
      );
    }

    if (!r.ok) {
      throw new Error(j.detail || 'Erro do servidor.');
    }

    const results = Array.isArray(j.results) ? j.results : [];
    const diagnostics = Array.isArray(j.diagnostics) ? j.diagnostics : [];

    const okSources = diagnostics.filter(x => x.ok).length;
    const errorSources = diagnostics.filter(x => !x.ok).length;

    $('status').innerHTML =
      `Pesquisa concluída: <b>${results.length}</b> resultados encontrados. ` +
      `Fontes automáticas consultadas: <b>${okSources}</b>.` +
      (errorSources
        ? ` <span class="red">${errorSources} fonte(s) com erro.</span>`
        : '');

    $('diagnostics').innerHTML =
      diagnostics.map(diagnosticHtml).join('');

    let h = results.map(x => `
      <article class="card">
        <span class="score">${esc(x.score)}/100</span>

        <div class="title">${esc(x.title)}</div>

        <div class="meta">
          ${esc(x.source)}
          · ${esc(x.date)}
          ${x.country ? ' · ' + esc(x.country) : ''}
          ${x.buyer ? ' · ' + esc(x.buyer) : ''}
        </div>

        ${x.deadline
          ? `<div class="meta"><b>Prazo:</b> ${esc(x.deadline)}</div>`
          : ''}

        ${x.cpv
          ? `<div class="meta"><b>CPV:</b> ${esc(x.cpv)}</div>`
          : ''}

        <span class="badge">${esc(x.category)}</span>

        <p>
          <a href="${esc(x.url)}"
             target="_blank"
             rel="noopener">
             Abrir concurso ↗
          </a>
        </p>
      </article>
    `).join('');

    if (!h) {
      h = `
        <section class="card empty">
          <div class="title">
            Não foram encontrados resultados nesta pesquisa.
          </div>

          <p>
            Tenta pesquisar por
            <b>archaeology</b>,
            <b>excavation</b>,
            <b>cultural heritage</b>
            ou
            <b>archaeological monitoring</b>.
          </p>
        </section>
      `;
    }

    // Os resultados são apresentados imediatamente.
    // A consulta aos portais complementares é feita depois.
    $('results').innerHTML = h;

    try {
      const sResponse = await fetchWithTimeout(
        '/api/sources',
        {},
        15000
      );

      if (sResponse.ok) {
        const s = await sResponse.json();

        $('results').innerHTML += `
          <section class="card">
            <div class="title">
              🌍 Portais oficiais complementares
            </div>

            <p>
              Estas fontes já estão catalogadas no Radar.
              Nesta versão, são apresentadas como portais de consulta;
              a pesquisa automática será integrada progressivamente.
            </p>

            <div class="sources">
              ${s.map(x => `
                <a href="${esc(x.url)}"
                   target="_blank"
                   rel="noopener">
                  <b>${esc(x.name)}</b>
                  — ${esc(x.region)}
                  ${x.mode === 'api' ? '🟢 automática' : '🔵 portal'}
                </a>
              `).join('')}
            </div>
          </section>
        `;
      }
    } catch (sourcesError) {
      console.warn(
        'Não foi possível carregar os portais complementares:',
        sourcesError
      );
    }

  } catch (e) {
    console.error('Radar:', e);

    if (e.name === 'AbortError') {
      $('status').innerHTML =
        `<span class="red">
          🔴 A pesquisa demorou demasiado tempo a responder.
          A API do Radar não respondeu dentro de 60 segundos.
        </span>`;
    } else {
      $('status').innerHTML =
        `<span class="red">
          🔴 Não foi possível concluir a pesquisa.
        </span>`;

      $('diagnostics').innerHTML =
        `<div class="diag error">${esc(e.message || e)}</div>`;
    }
  }
}

$('go').onclick = go;

$('q').addEventListener('keydown', e => {
  if (e.key === 'Enter') {
    go();
  }
});
