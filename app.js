const $ = id => document.getElementById(id);
// ============================================================
// FUNÇÕES AUXILIARES
// ============================================================
const esc = s =>
  String(s ?? '').replace(/[&<>"]/g, c => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;'
  }[c]));
function cleanText(s) {
  if (!s) return '';
  const div = document.createElement('div');
  div.innerHTML = String(s);
  return (div.textContent || div.innerText || '')
    .replace(/\s+/g, ' ')
    .trim();
}
// ============================================================
// DIAGNÓSTICOS
// ============================================================
function diagnosticHtml(d) {
  if (d.ok) {
    return `
      <div class="diag ok">
        🟢 <b>${esc(d.source)}</b>:
        ${esc(d.count ?? 0)} resultados encontrados.
      </div>
    `;
  }
  return `
    <div class="diag error">
      🔴 <b>${esc(d.source)}</b>:
      não foi possível pesquisar.
      ${esc(d.error || 'Erro desconhecido.')}
    </div>
  `;
}
// ============================================================
// TIMEOUT
// ============================================================
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
// ============================================================
// FORMATAÇÃO DE DATAS
// ============================================================
function formatDate(value) {
  if (!value) return '';
  const text = String(value).trim();
  const match = text.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (match) {
    return `${match[3]}/${match[2]}/${match[1]}`;
  }
  return text;
}
// ============================================================
// CRIAÇÃO DE CADA RESULTADO
// ============================================================
function resultHtml(x) {
  const title =
    cleanText(x.title) ||
    'Concurso sem título';
  const source =
    cleanText(x.source);
  const date =
    formatDate(x.date);
  const deadline =
    formatDate(x.deadline);
  const country =
    cleanText(x.country);
  const buyer =
    cleanText(x.buyer);
  const category =
    cleanText(x.category);
  const cpv =
    cleanText(x.cpv);
  const description =
    cleanText(
      x.description ||
      x.notice_text ||
      x.summary ||
      ''
    );
  const url =
    x.url || '#';
  return `
    <article class="card">
      <div class="title">
        ${esc(title)}
      </div>
      <div class="meta">
        ${source
          ? `<b>Fonte:</b> ${esc(source)}`
          : ''
        }
        ${date
          ? ` · <b>Data:</b> ${esc(date)}`
          : ''
        }
      </div>
      ${country
        ? `
          <div class="meta">
            🌍 <b>País:</b> ${esc(country)}
          </div>
        `
        : ''
      }
      ${buyer
        ? `
          <div class="meta">
            🏛️ <b>Entidade:</b> ${esc(buyer)}
          </div>
        `
        : ''
      }
      ${deadline
        ? `
          <div class="meta deadline">
            ⏰ <b>Prazo:</b> ${esc(deadline)}
          </div>
        `
        : ''
      }
      ${cpv
        ? `
          <div class="meta">
            <b>CPV:</b> ${esc(cpv)}
          </div>
        `
        : ''
      }
      ${category
        ? `
          <div class="badge">
            ${esc(category)}
          </div>
        `
        : ''
      }
      ${description
        ? `
          <div class="description">
            ${esc(description)}
          </div>
        `
        : ''
      }
      <p>
        <a
          href="${esc(url)}"
          target="_blank"
          rel="noopener"
        >
          Abrir concurso ↗
        </a>
      </p>
    </article>
  `;
}
// ============================================================
// PESQUISA PRINCIPAL
// ============================================================
async function go() {
  const qElement = $('q');
  const statusElement = $('status');
  const resultsElement = $('results');
  const diagnosticsElement = $('diagnostics');
  const regionElement = $('region');
  const categoryElement = $('category');
  if (!qElement || !statusElement || !resultsElement || !diagnosticsElement) {
    console.error(
      'Radar: elementos da página não encontrados.'
    );
    return;
  }
  const q =
    qElement.value.trim() ||
    'archaeology';
  statusElement.innerHTML =
    '🔎 <b>A pesquisar...</b> ' +
    'O Radar está a consultar as fontes automáticas.';
  resultsElement.innerHTML = '';
  diagnosticsElement.innerHTML = '';
  try {
    const p =
      new URLSearchParams({
        q,
        region:
          regionElement
            ? regionElement.value
            : '',
        category:
          categoryElement
            ? categoryElement.value
            : ''
      });
    const url =
      '/api/search?' +
      p.toString();
    console.log(
      'Radar: a consultar',
      url
    );
    const r =
      await fetchWithTimeout(
        url,
        {},
        60000
      );
    console.log(
      'Radar: resposta recebida',
      r.status
    );
    const text =
      await r.text();
    console.log(
      'Radar: resposta recebida, tamanho:',
      text.length
    );
    let j;
    try {
      j = JSON.parse(text);
    } catch (e) {
      throw new Error(
        'A API respondeu, mas o navegador não conseguiu interpretar a resposta.'
      );
    }
    if (!r.ok) {
      throw new Error(
        j.detail ||
        'Erro do servidor.'
      );
    }
    const results =
      Array.isArray(j.results)
        ? j.results
        : [];
    const diagnostics =
      Array.isArray(j.diagnostics)
        ? j.diagnostics
        : [];
    const okSources =
      diagnostics.filter(
        x => x.ok
      ).length;
    const errorSources =
      diagnostics.filter(
        x => !x.ok
      ).length;
    // ========================================================
    // ESTADO DA PESQUISA
    // ========================================================
    statusElement.innerHTML =
      `Pesquisa concluída: ` +
      `<b>${results.length}</b> resultados encontrados. ` +
      `Fontes automáticas consultadas: ` +
      `<b>${okSources}</b>.` +
      (
        errorSources
          ? ` <span class="red">` +
            `${errorSources} fonte(s) com erro.` +
            `</span>`
          : ''
      );
    // ========================================================
    // DIAGNÓSTICOS
    // ========================================================
    diagnosticsElement.innerHTML =
      diagnostics
        .map(diagnosticHtml)
        .join('');
    // ========================================================
    // RESULTADOS
    // ========================================================
    let h =
      results
        .map(resultHtml)
        .join('');
    // ========================================================
    // NENHUM RESULTADO
    // ========================================================
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
    // ========================================================
    // APRESENTAÇÃO
    // ========================================================
    resultsElement.innerHTML =
      h;
    // ========================================================
    // PORTAIS COMPLEMENTARES
    // ========================================================
    try {
      const sResponse =
        await fetchWithTimeout(
          '/api/sources',
          {},
          15000
        );
      if (sResponse.ok) {
        const s =
          await sResponse.json();
        resultsElement.innerHTML += `
          <section class="card">
            <div class="title">
              🌍 Portais oficiais complementares
            </div>
            <p>
              Estas fontes já estão catalogadas no Radar.
              Nesta versão, são apresentadas como portais de
              consulta; a pesquisa automática será integrada
              progressivamente.
            </p>
            <div class="sources">
              ${s.map(x => `
                <a
                  href="${esc(x.url)}"
                  target="_blank"
                  rel="noopener"
                >
                  <b>
                    ${esc(x.name)}
                  </b>
                  — ${esc(x.region)}
                  ${
                    x.mode === 'api'
                      ? ' 🟢 automática'
                      : ' 🔵 portal'
                  }
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
    console.error(
      'Radar:',
      e
    );
    if (e.name === 'AbortError') {
      statusElement.innerHTML = `
        <span class="red">
          🔴 A pesquisa demorou demasiado tempo a responder.
          A API do Radar não respondeu dentro de 60 segundos.
        </span>
      `;
    } else {
      statusElement.innerHTML = `
        <span class="red">
          🔴 Não foi possível concluir a pesquisa.
        </span>
      `;
      diagnosticsElement.innerHTML = `
        <div class="diag error">
          ${esc(e.message || e)}
        </div>
      `;
    }
  }
}
// ============================================================
// INICIALIZAÇÃO DO RADAR
// ============================================================
//
// IMPORTANTE:
// Esperamos que o HTML esteja completamente carregado antes
// de procurar o botão, a caixa de pesquisa e os filtros.
// Isto evita que o App.js seja executado antes dos elementos
// existirem na página.
// ============================================================
function initRadar() {
  const button = $('go');
  const searchBox = $('q');
  if (!button) {
    console.error(
      'Radar: botão de pesquisa #go não encontrado.'
    );
    return;
  }
  if (!searchBox) {
    console.error(
      'Radar: caixa de pesquisa #q não encontrada.'
    );
    return;
  }
  // ==========================================================
  // BOTÃO PESQUISAR
  // ==========================================================
  button.onclick = go;
  // ==========================================================
  // ENTER NA CAIXA DE PESQUISA
  // ==========================================================
  searchBox.addEventListener(
    'keydown',
    e => {
      if (e.key === 'Enter') {
        e.preventDefault();
        go();
      }
    }
  );
  console.log(
    'Radar: interface inicializada correctamente.'
  );
}
// ============================================================
// ARRANQUE
// ============================================================
if (document.readyState === 'loading') {
  document.addEventListener(
    'DOMContentLoaded',
    initRadar
  );
} else {
  initRadar();
}
