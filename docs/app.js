const fmt = new Intl.NumberFormat('sv-SE', { maximumFractionDigits: 2 });
const pct = value => value == null ? '—' : `${value >= 0 ? '+' : ''}${fmt.format(value)}%`;
const signedClass = value => value == null ? '' : value >= 0 ? 'positive' : 'negative';

function dataTime(indicators) {
  if (!indicators.as_of) return 'Data saknas';
  return `Data från ${indicators.as_of.replace('T', ' ').replace('Z', ' UTC')}`;
}

function metric(label, value, extraClass = '') {
  return `<div class="metric ${extraClass}"><dt>${label}</dt><dd>${value}</dd></div>`;
}

function card(row, target, gold = false) {
  const i = row.indicators;
  const article = document.createElement('article');
  article.className = `card severity-${row.severity}${gold ? ' gold-card' : ''}`;
  const hourly = i.data_is_stale
    ? metric('Senaste avläsning', dataTime(i), 'stale')
    : metric('Senaste timme', pct(i.hourly_change_pct), `${signedClass(i.hourly_change_pct)} ${i.hourly_move_highlight ? 'highlight' : ''}`);
  const ath = i.ath_drawdown_pct == null ? '' : metric(`Sedan ATH (${i.ath_date})`, `−${fmt.format(i.ath_drawdown_pct)}%`, 'ath');
  article.innerHTML = `
    <div class="card-title"><span class="dot"></span><strong>${row.ticker}</strong><span class="level">${i.available ? (row.severity ? `Nivå ${row.severity}` : 'Ingen varning') : 'Data saknas'}</span></div>
    <p class="name">${row.name}</p>
    <p class="price">${i.available ? `${fmt.format(i.last_price)} ${row.price_unit || ''}`.trim() : '—'}</p>
    <dl class="primary">${metric('Sedan peak', i.available ? `−${fmt.format(i.trailing_drawdown_pct)}%` : '—', 'drawdown')}</dl>
    <dl class="secondary">${metric('Sedan föregående stängning', pct(i.daily_change_pct), signedClass(i.daily_change_pct))}${hourly}${ath}</dl>
    <p class="meta">${row.breadth_floor_applied ? 'Sektorlarm påverkar nivån' : dataTime(i)}</p>`;
  target.append(article);
}

async function start() {
  const response = await fetch(`./data/latest_status.json?v=${Date.now()}`, { cache: 'no-store' });
  if (!response.ok) throw Error('Statusfilen kunde inte hämtas');
  const data = await response.json();
  document.querySelector('#updated').textContent = data.generated_at ? `Senast beräknad ${data.generated_at.replace('T', ' ').replace('Z', ' UTC')}` : 'Väntar på första datainsamlingen';
  const breadth = document.querySelector('#breadth');
  if (data.breadth?.active) {
    breadth.hidden = false;
    breadth.textContent = `Sektorlarm: ${data.breadth.count} aktier faller kraftigt${data.breadth.confirmed_by_gold ? ' – guldpriset bekräftar rörelsen.' : '.'}`;
  }
  for (const row of data.instruments || []) {
    if (row.role === 'gold_confirmation') card(row, document.querySelector('#gold-price'), true);
    else if (row.kind === 'watchlist') card(row, document.querySelector('#watchlist'));
    else card(row, document.querySelector('#reference-list'));
  }
  const count = (data.instruments || []).filter(row => row.kind === 'watchlist' && row.severity >= 3).length;
  if ('setAppBadge' in navigator) navigator.setAppBadge(count).catch(() => {});
}
start().catch(error => { document.querySelector('#updated').textContent = `Status ej tillgänglig: ${error.message}`; });
