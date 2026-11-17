/* Навігація, вхід, WebSocket, панель керування, налаштування, правила та історія. */
const $ = id => document.getElementById(id);
let tok = localStorage.getItem('pk_tok'), ws = null, ME = '', shown = -1, retry = 0, cur = 'auth', hist = [];
const SCREENS = ['auth', 'hub', 'pmenu', 'lob', 'game', 'bj'];
const send = o => ws && ws.readyState === 1 && ws.send(JSON.stringify(o));
const esc = s => String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const toast = t => { $('toast').textContent = t; setTimeout(() => { if ($('toast').textContent === t) $('toast').textContent = ''; }, 4000); };
function show(id) {
  cur = id; SCREENS.forEach(x => $(x).hidden = x !== id);
  $('bHome').hidden = id === 'auth' || id === 'hub'; $('bRules').hidden = !['pmenu', 'lob', 'game', 'bj'].includes(id); $('bHist').hidden = id !== 'game' && id !== 'bj'; $('out').hidden = id === 'auth';
  FX.setLayer(id === 'bj' ? $('bjfx') : $('fxl')); if (id === 'bj') send({ t: 'bj_state' });
  if (id !== 'game') $('ct').hidden = true; window.scrollTo(0, 0);
}
const inTable = () => cur === 'lob' || cur === 'game';
/* ---- акаунти ---- */
async function api(p, b) {
  const r = await fetch('/api/' + p, { method: b ? 'POST' : 'GET', headers: { 'Content-Type': 'application/json' }, body: b ? JSON.stringify(b) : undefined });
  const j = await r.json(); if (!r.ok) throw j.detail || 'Помилка'; return j;
}
async function auth(k) {
  try { const j = await api(k, { name: $('un').value.trim(), password: $('pw').value }); tok = j.token; localStorage.setItem('pk_tok', tok); $('ae').textContent = ''; connect(); }
  catch (e) { $('ae').textContent = e; }
}
function logout() { tok = null; localStorage.removeItem('pk_tok'); if (ws) ws.close(); PT.reset(); show('auth'); }
async function refresh() {
  try { const l = await api('tables');
    $('tl').innerHTML = l.length ? l.map(t => `<div class="tb"><span>${t.code} · ${esc(t.host)} · ${t.n} гр.${t.bots ? ' + ' + t.bots + ' ботів' : ''}</span><button data-join="${t.code}">Увійти</button></div>`).join('') : '<div class="mu">Відкритих столів немає</div>'; } catch (e) {}
}
/* ---- зʼєднання ---- */
function connect() {
  if (!tok) return show('auth'); if (ws) { ws.onclose = null; ws.close(); }
  ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws');
  ws.onopen = () => { send({ t: 'auth', token: tok }); retry = 0; };
  ws.onmessage = e => on(JSON.parse(e.data));
  ws.onclose = () => { if (tok) { $('conn').hidden = false; setTimeout(connect, Math.min(1000 * ++retry, 5000)); } };
}
setInterval(() => send({ t: 'ping' }), 25000);
function on(m) {
  switch (m.t) {
    case 'authok': ME = m.name; $('who').textContent = ME; $('conn').hidden = true; $('log').innerHTML = ''; hist = []; PT.reset(); show('hub'); break;
    case 'autherr': logout(); break;
    case 'lobby': show('lob'); $('code').textContent = m.code;
      $('pl').innerHTML = m.players.map(n => `<div class="tb">${esc(n)}${n === m.host ? ' 👑' : ''}</div>`).join('') + (m.bots ? `<div class="tb">+ ${m.bots} ботів</div>` : '');
      $('st').hidden = m.host !== ME; $('wt').hidden = m.host === ME; break;
    case 'state': if (cur !== 'game') show('game'); draw(m); break;
    case 'log': addLog(m.m, m.c); break;
    case 'end': $('et').textContent = m.m; $('end').hidden = false; break;
    case 'left': $('log').innerHTML = ''; hist = []; PT.reset(); $('end').hidden = true; show('pmenu'); refresh(); break;
    case 'bj': BJ.update(m.view, m.events, m.init, m.rules); break;
    case 'err': toast(m.m);
  }
}
function addLog(t, c) {
  const d = document.createElement('div'); d.textContent = t; if (c) d.className = c; $('log').appendChild(d); $('log').scrollTop = 1e9;
  if (c === 'h' && t.startsWith('── Роздача')) hist.push({ t: t.replace(/─/g, '').trim(), l: [] });
  else if (c === 'w' && hist.length) hist[hist.length - 1].l.push(t);
}
/* ---- стіл ---- */
function draw(S) {
  PT.update(S);
  const mi = S.pl.findIndex(p => p.me), me = S.pl[mi];
  $('info').textContent = S.act ? '⏱ Ваш хід (45 с)' : S.wait && S.turn >= 0 ? 'Ходить ' + S.pl[S.turn].n : S.combo ? 'Ваша комбінація: ' + S.combo : (mi < 0 ? 'Ви спостерігаєте' : '');
  if (S.act) { if (S.tk !== shown) ctl(S); } else { shown = -1; $('ct').hidden = true; }
}
function ctl(S) {
  shown = S.tk; const a = S.act, t = S.tk;
  $('ct').hidden = false; $('bC').textContent = a.tc ? (a.tc === S.pl[S.turn].c ? 'Колл (олл-ін) ' : 'Колл ') + a.tc : 'Чек';
  $('rg').hidden = !a.r; const rs = $('rs'); rs.min = a.mn; rs.max = a.mx; rs.step = 1; rs.value = a.mn;
  const upd = () => $('bR').textContent = (+rs.value >= a.mx ? 'Олл-ін ' : a.cur ? 'Рейз до ' : 'Бет ') + rs.value;
  upd(); rs.oninput = upd;
  const set = v => { rs.value = Math.max(a.mn, Math.min(a.mx, v)); upd(); };
  $('q1').onclick = () => set(a.cur + Math.round((a.pt + a.tc) / 2)); $('q2').onclick = () => set(a.cur + a.pt + a.tc); $('q3').onclick = () => set(a.mx);
  const go = o => { $('ct').hidden = true; shown = t; FX.sound('click'); send({ t: 'act', tk: t, ...o }); };   // кнопки ховаються одразу: повторне натискання неможливе
  $('bF').onclick = () => go({ a: 'f' }); $('bC').onclick = () => go({ a: 'c' }); $('bR').onclick = () => go({ a: 'r', to: +rs.value });
}
/* ---- меню, модальні вікна ---- */
const leave = () => send({ t: 'leave' });
const modal = (title, html) => { $('mt').textContent = title; $('mb').innerHTML = html; $('modal').hidden = false; };
const RULES = `<ul><li><b>No-Limit Texas Hold'em</b>, 2–9 гравців, віртуальні фішки (без грошей).</li>
<li>Блайнди 10/20, подвоюються кожні 10 роздач. Дилер (D) переходить за годинниковою стрілкою; у грі 1 на 1 дилер — малий блайнд і ходить першим на префлопі.</li>
<li>Кожен отримує 2 закриті карти; далі флоп (3), тьорн (1), рівер (1) і вскриття.</li>
<li>Дії: Фолд, Чек, Колл, Бет/Рейз (не менше за попередній рейз), Олл-ін. Неповний олл-ін не відкриває торги знову для тих, хто вже ходив.</li>
<li>Є сайд-поти й розділ банку при нічиїй. Неподілена ставка повертається.</li>
<li>На хід — 45 секунд, потім за вас ходить бот.</li></ul>
<b>Комбінації (від сильної):</b><ul><li>Роял-флеш, Стріт-флеш, Каре, Фул-хаус, Флеш, Стріт, Трійка, Дві пари, Пара, Старша карта</li></ul>
<b>Боти:</b> 🛡 обережний, ⚖ збалансований, 🔥 агресивний.`;
document.addEventListener('click', e => {
  const b = e.target.closest('button'); if (!b) return; FX.sound('click');
  if (b.dataset.join) send({ t: 'join', code: b.dataset.join });
});
$('goPoker').onclick = () => { show('pmenu'); refresh(); };
$('goBj').onclick = () => show('bj'); $('bjMenu').onclick = () => show('hub');
$('pBack').onclick = () => show('hub');
$('bHome').onclick = () => { if (inTable()) { if (confirm('Вийти зі столу?')) leave(); } else show('hub'); };
$('bRules').onclick = () => cur === 'bj' ? modal('Правила Blackjack', '<ul>' + BJ.rules().map(x => '<li>' + esc(x) + '</li>').join('') + '</ul>') : modal('Правила покеру', RULES);
$('bHist').onclick = () => cur === 'bj' ? modal('Історія роздач', BJ.history().length ? [...BJ.history()].reverse().map(h => `<div><b>Раунд ${h.n}</b> · ставка ${h.bet} · ${h.net >= 0 ? '+' : '−'}${Math.abs(h.net)}<div class="mu">${h.hands.map(x => x.result).join(', ')}</div></div>`).join('') : '<div class="mu">Завершених роздач ще немає</div>') : modal('Історія роздач', hist.length ? [...hist].reverse().map(h => `<div><b>${esc(h.t)}</b>${h.l.map(x => '<div class="mu">' + esc(x) + '</div>').join('')}</div>`).join('') : '<div class="mu">Завершених роздач ще немає</div>');
$('mc').onclick = () => $('modal').hidden = true;
$('bSet').onclick = () => { $('sSnd').checked = FX.cfg.sound; $('sAn').value = FX.cfg.anim; $('set').hidden = false; };
$('sc').onclick = () => $('set').hidden = true;
$('sSnd').onchange = () => { FX.cfg.sound = $('sSnd').checked; FX.save(); $('bSnd').textContent = FX.cfg.sound ? '🔊' : '🔇'; };
$('sAn').onchange = () => { FX.cfg.anim = +$('sAn').value; FX.save(); };
$('bSnd').onclick = () => { FX.cfg.sound = !FX.cfg.sound; FX.save(); $('bSnd').textContent = FX.cfg.sound ? '🔊' : '🔇'; };
$('mk').onclick = () => send({ t: 'create', bots: +$('nb').value, stack: +$('stk').value, solo: false });
$('mkSolo').onclick = () => send({ t: 'create', bots: +$('nb').value || 3, stack: +$('stk').value, solo: true });
$('jn').onclick = () => send({ t: 'join', code: $('jc').value });
$('rf').onclick = refresh; $('st').onclick = () => send({ t: 'start' });
$('lv1').onclick = leave; $('lv2').onclick = leave; $('lv3').onclick = () => { $('end').hidden = true; leave(); };
$('again').onclick = () => { $('end').hidden = true; leave(); setTimeout(() => send({ t: 'create', bots: 3, stack: 1000, solo: true }), 250); };
$('out').onclick = logout;
$('pw').onkeydown = e => { if (e.key === 'Enter') auth('login'); };
$('login').onclick = () => auth('login'); $('reg').onclick = () => auth('register');
for (let i = 0; i <= 8; i++) $('nb').add(new Option(String(i), i, i === 2, i === 2));
FX.setLayer($('fxl')); FX.apply(); $('bSnd').textContent = FX.cfg.sound ? '🔊' : '🔇';
connect();
