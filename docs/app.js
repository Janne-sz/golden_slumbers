const fmt = new Intl.NumberFormat('sv-SE', { maximumFractionDigits: 2 });
const stockholmDateTime = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Stockholm', year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', timeZoneName: 'short' });
const stockholmTime = new Intl.DateTimeFormat('sv-SE', { timeZone: 'Europe/Stockholm', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' });
const pct = value => value == null ? '—' : `${value >= 0 ? '+' : ''}${fmt.format(value)}%`;
const signedClass = value => value == null ? '' : value >= 0 ? 'positive' : 'negative';

function dataTime(indicators) {
  if (!indicators.as_of) return 'Data saknas';
  if (!indicators.as_of.includes('T')) return `Data från ${indicators.as_of}`;
  return `Data från ${stockholmDateTime.format(new Date(indicators.as_of))}`;
}

function metric(label, value, extraClass = '') {
  return `<div class="metric ${extraClass}"><dt>${label}</dt><dd>${value}</dd></div>`;
}

function previousCloseLabel(date) {
  if (!date) return 'Sedan<br>föregående<br>stängning';
  const weekdays = ['Sö', 'Må', 'Ti', 'On', 'To', 'Fr', 'Lö'];
  const [year, month, day] = date.slice(0, 10).split('-');
  const weekday = weekdays[new Date(`${year}-${month}-${day}T12:00:00Z`).getUTCDay()];
  return `Sedan<br>stängningen<br>${weekday} ${day}/${month}`;
}

function intradayMetric(change) {
  const label = change?.reference_timestamp ? `Sedan<br>${stockholmTime.format(new Date(change.reference_timestamp))}` : 'Sedan<br>—';
  return metric(label, pct(change?.change_pct), signedClass(change?.change_pct));
}

function card(row, target, gold = false) {
  const i = row.indicators;
  const article = document.createElement('article');
  article.className = `card severity-${row.severity}${gold ? ' gold-card' : ''}`;
  const changes = i.intraday_changes || {};
  const ath = i.ath_drawdown_pct == null ? '' : `<dl class="ath-row">${metric(`Sedan ATH (${i.ath_date})`, `−${fmt.format(i.ath_drawdown_pct)}%`, 'ath')}</dl>`;
  article.innerHTML = `
    <div class="card-title"><span class="dot"></span><strong>${row.ticker}</strong><span class="level">${i.available ? (row.severity ? `Nivå ${row.severity}` : 'Ingen varning') : 'Data saknas'}</span></div>
    <p class="name">${row.name}</p>
    <p class="price">${i.available ? `${fmt.format(i.last_price)} ${row.price_unit || ''}`.trim() : '—'}</p>
    <dl class="primary">${metric('Sedan peak', i.available ? `−${fmt.format(i.trailing_drawdown_pct)}%` : '—', 'drawdown')}</dl>
    <dl class="secondary changes">${metric(previousCloseLabel(i.previous_close_date), pct(i.daily_change_pct), signedClass(i.daily_change_pct))}${intradayMetric(changes['1h'])}${intradayMetric(changes['2h'])}${intradayMetric(changes['4h'])}</dl>
    ${ath}
    <p class="meta">${row.breadth_floor_applied ? 'Sektorlarm påverkar nivån' : dataTime(i)}</p>`;
  target.append(article);
}

async function start() {
  const response = await fetch(`./data/latest_status.json?v=${Date.now()}`, { cache: 'no-store' });
  if (!response.ok) throw Error('Statusfilen kunde inte hämtas');
  const data = await response.json();
  document.querySelector('#updated').textContent = data.generated_at ? `Senast beräknad ${stockholmDateTime.format(new Date(data.generated_at))}` : 'Väntar på första datainsamlingen';
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
async function refreshApp() {
  const button = document.querySelector('#refresh');
  button.disabled = true;
  button.textContent = 'Uppdaterar …';
  try {
    const registration = await navigator.serviceWorker?.getRegistration();
    await registration?.update();
  } finally {
    window.location.replace(`${window.location.pathname}?refresh=${Date.now()}`);
  }
}
document.querySelector('#refresh').addEventListener('click', refreshApp);
start().catch(error => { document.querySelector('#updated').textContent = `Status ej tillgänglig: ${error.message}`; });
