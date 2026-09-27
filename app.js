const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>\"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\\':'&#92;'}[c]));

function diagnosticHtml(d) {
  if (d.ok) {
    return `<div class="diag ok">🟢 <b>${esc(d.source)}</b>: ${d.count} resultados encontrados.</div>`;
  }
  return `<div class="diag error">🔴 <b>${esc(d.source)}</b>: não foi possível pesquisar. ${esc(d.error || 'Erro desconhecido.')}</div>`;
}

async function go() {
  const q = $('q').value.trim() || 'archaeology';
  $('status').innerHTML = '🔎 <b>A pesquisar...</b> O Radar está a consultar as fontes automáticas.';
  $('results').innerHTML = '';
  $('diagnostics').innerHTML = '';

  try {
    const p = new URLSearchParams({
      q,
      region: $('region').value,
      category: $('category').value
    });

    const r = await fetch('/api/search?' + p);
    const j = await r.json();

    if (!r.ok) throw new Error(j.detail || 'Erro do servidor.');

    const okSources = (j.diagnostics || []).filter(x => x.ok).length;
    const errorSources = (j.diagnostics || []).filter(x => !x.ok).length;

    $('status').innerHTML = `Pesquisa concluída: <b>${j.results.length}</b> resultados encontrados. ` +
      `Fontes automáticas consultadas: <b>${okSources}</b>.` +
      (errorSources ? ` <span class="red">${errorSources} fonte(s) com erro.</span>` : '');

    $('diagnostics').innerHTML = (j.diagnostics || []).map(diagnosticHtml).join('');

    let h = j.results.map(x => `
      <article class="card">
        <span class="score">${esc(x.score)}/100</span>
        <div class="title">${esc(x.title)}</div>
        <div class="meta">${esc(x.source)} · ${esc(x.date)}${x.country ? ' · ' + esc(x.country) : ''}${x.buyer ? ' · ' + esc(x.buyer) : ''}</div>
        ${x.deadline ? `<div class="meta"><b>Prazo:</b> ${esc(x.deadline)}</div>` : ''}
        ${x.cpv ? `<div class="meta"><b>CPV:</b> ${esc(x.cpv)}</div>` : ''}
        <span class="badge">${esc(x.category)}</span>
        <p><a href="${esc(x.url)}" target="_blank" rel="noopener">Abrir concurso ↗</a></p>
      </article>`).join('');

    if (!h) {
      h = `<section class="card empty"><div class="title">Não foram encontrados resultados nesta pesquisa.</div>
      <p>Tenta pesquisar por <b>archaeology</b>, <b>excavation</b>, <b>cultural heritage</b> ou <b>archaeological monitoring</b>.</p></section>`;
    }

    const s = await fetch('/api/sources').then(r => r.json());
    h += `<section class="card">
      <div class="title">🌍 Portais oficiais complementares</div>
      <p>Estas fontes já estão catalogadas no Radar. Nesta versão, são apresentadas como portais de consulta; a pesquisa automática será integrada progressivamente.</p>
      <div class="sources">${s.map(x => `<a href="${esc(x.url)}" target="_blank" rel="noopener"><b>${esc(x.name)}</b> — ${esc(x.region)} ${x.mode === 'api' ? '🟢 automática' : '🔵 portal'}</a>`).join('')}</div>
    </section>`;

    $('results').innerHTML = h;
  } catch (e) {
    $('status').innerHTML = `<span class="red">🔴 Não foi possível concluir a pesquisa.</span>`;
    $('diagnostics').innerHTML = `<div class="diag error">${esc(e.message || e)}</div>`;
  }
}

$('go').onclick = go;
$('q').addEventListener('keydown', e => { if (e.key === 'Enter') go(); });
