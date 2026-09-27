const API = 'https://arqueologia-radar.onrender.com';

const $ = id => document.getElementById(id);

const esc = s =>
  String(s ?? '').replace(/[&<>"]/g, c => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;'
  }[c]));

async function go() {
  const q = $('q').value.trim() || 'archaeology';

  $('status').innerHTML = '🔎 A pesquisar agora…';
  $('results').innerHTML = '';

  try {
    const params = new URLSearchParams({
      q: q,
      limit: '50'
    });

    const response = await fetch(
      `${API}/api/opportunities?${params.toString()}`
    );

    if (!response.ok) {
      throw new Error('Erro do servidor');
    }

    const data = await response.json();

    if (data.error) {
      throw new Error(data.error);
    }

    const results = data.results || [];

    $('status').innerHTML =
      `Pesquisa concluída: <b>${results.length}</b> resultados encontrados.`;

    if (!results.length) {
      $('results').innerHTML = `
        <section class="card">
          <div class="title">Nenhum resultado encontrado</div>
          <p>Tenta outra expressão, por exemplo:
          <b>archaeology</b>, <b>archaeological</b> ou
          <b>cultural heritage</b>.</p>
        </section>`;
      return;
    }

    $('results').innerHTML = results.map(x => `
      <article class="card">
        <span class="score">${esc(x.relevance)}/100</span>

        <div class="title">
          ${esc(x.title || 'Sem título')}
        </div>

        <div class="meta">
          ${esc(x.source || 'TED')}
          ${x.country ? ' · ' + esc(x.country) : ''}
          ${x.deadline ? ' · Prazo: ' + esc(x.deadline) : ''}
        </div>

        ${x.buyer ? `
          <div class="meta">
            Entidade: ${esc(x.buyer)}
          </div>` : ''}

        <span class="badge">
          Arqueologia
        </span>

        ${x.description ? `
          <p>${esc(x.description)}</p>` : ''}

        ${x.url ? `
          <p>
            <a href="${esc(x.url)}"
               target="_blank"
               rel="noopener">
              Abrir concurso ↗️
            </a>
          </p>` : ''}
      </article>
    `).join('');

  } catch (error) {
    console.error(error);

    $('status').innerHTML =
      '❌ Não foi possível contactar o servidor Radar.';

    $('results').innerHTML = `
      <section class="card">
        <div class="title">Erro de ligação</div>
        <p>
          O servidor está online, mas a pesquisa não conseguiu obter
          resultados. Vamos verificar a ligação ao TED.
        </p>
      </section>`;
  }
}

$('go').onclick = go;
