/* Blackjack: стіл, анімації та керування. Правила й розрахунки лишаються на сервері (blackjack.py). */
const BJ = (() => {
  const $ = id => document.getElementById(id);
  const { key, mk, setFace, flipUp } = CardUI;
  const RES = { blackjack: ['Blackjack', 'bj'], win: ['Win', 'w'], push: ['Push', 'p'], lose: ['Lose', 'l'], bust: ['Bust', 'l'] };
  const NAMES = { hit: 'Hit', stand: 'Stand', double: 'Double', split: 'Split' };
  const TIPS = { hit: 'Взяти ще одну карту', stand: 'Зупинитись і віддати хід', double: 'Подвоїти ставку й взяти рівно одну карту', split: 'Розділити пару на дві окремі руки' };
  const CHIPS = [10, 50, 100, 500, 1000];
  const fmt = n => Number(n).toLocaleString('uk-UA');
  let lastRound = -1, view = null, bet = 0, lastBet = 0, rules = [], balShown = null, timers = [];
  const later = (fn, ms) => timers.push(setTimeout(fn, ms));
  const lock = b => document.querySelectorAll('#bjact button,#bjtray button').forEach(x => x.disabled = b);
  const act = o => { lock(true); send(o); };                       // кнопки блокуються до відповіді сервера: повторні натискання неможливі

  function addHand() {
    const d = document.createElement('div'); d.className = 'bjh';
    d.innerHTML = '<div class="hc"></div><div class="ht"></div><div class="hb"></div><div class="hr"></div>'; $('bjh').appendChild(d); return d;
  }
  /* Приводить карти в контейнері до стану сервера; нові карти повертає для анімації. */
  function sync(box, cards, meta, fresh, hidden) {
    while (box.children.length > cards.length) box.lastChild.remove();
    cards.forEach((c, i) => {
      let el = box.children[i];
      if (el && c && el.dataset.k && el.dataset.k !== key(c)) { const n = mk(); box.replaceChild(n, el); el = n; fresh.push({ el, ...meta, idx: i }); }
      else if (!el) { el = mk(); box.appendChild(el); fresh.push({ el, ...meta, idx: i }); }
      setFace(el, c);
    });
  }
  const tot = h => h.bust ? 'Перебір ' + h.total : h.bj ? 'Blackjack' : (h.soft && !h.done && h.total < 21 ? `${h.total - 10} / ${h.total}` : String(h.total));

  function update(v, events, init, rl) {
    view = v; if (rl) rules = rl; timers.forEach(clearTimeout); timers = [];
    const anim = !init && FX.level() > 0 && events && events.length > 0;
    if (v.round !== lastRound) { $('dcards').innerHTML = ''; $('bjh').innerHTML = ''; lastRound = v.round; }
    $('bjact').innerHTML = ''; $('bjact').hidden = true; $('bjtray').hidden = true;        // керування з'являється після анімації
    const H = $('bjh'); while (H.children.length < v.hands.length) addHand(); while (H.children.length > v.hands.length) H.lastChild.remove();
    const fresh = [];
    v.hands.forEach((h, i) => { sync(H.children[i].firstChild, h.cards, { to: 'p', hand: i }, fresh); H.children[i].querySelector('.hb').innerHTML = `<span class="chip"></span>${fmt(h.bet)}`; });
    const dc = $('dcards'), holeBefore = dc.children[1] && !dc.children[1].classList.contains('up');
    sync(dc, v.dealer.cards, { to: 'd', hand: 0 }, fresh);
    /* порядок анімації — за подіями сервера */
    const groups = {}; fresh.forEach(f => (groups[f.to + f.hand] = groups[f.to + f.hand] || []).push(f));
    const order = []; (events || []).filter(e => e.e === 'card').forEach(e => { const f = (groups[(e.to === 'dealer' ? 'd0' : 'p' + e.hand)] || []).shift(); if (f) order.push(f); });
    Object.values(groups).forEach(g => g.forEach(f => order.push(f)));
    const hole = dc.children[1], holeShow = !!(hole && v.dealer.cards[1] && !hole.classList.contains('up'));
    let t = 0, flipT = null;
    for (const f of order) {
      if (f.to === 'd' && f.idx >= 2 && flipT === null && holeShow) { flipT = t; t += 450; }
      f.delay = t; if (anim) t += 260;
    }
    if (holeShow && flipT === null) { flipT = t; t += anim ? 450 : 0; }
    order.forEach(f => {
      if (anim) { FX.dealIn(f.el, $('bjshoe'), f.delay); FX.later(() => FX.sound('deal'), FX.t(f.delay)); }
      if (f.el.dataset.k && !(f.to === 'd' && f.idx === 1)) flipUp(f.el, anim ? f.delay + 420 : 0);
    });
    if (holeShow) { flipUp(hole, anim ? flipT : 0); if (anim) FX.later(() => FX.sound('flip'), FX.t(flipT)); }
    later(() => finish(v, events, anim), FX.t(t) + (anim ? 250 : 0));
  }
  function finish(v, events, anim) {
    const H = $('bjh');
    v.hands.forEach((h, i) => {
      const el = H.children[i]; if (!el) return;
      el.classList.toggle('act', v.active === i); const ht = el.querySelector('.ht');
      ht.textContent = tot(h); ht.className = 'ht' + (h.bust ? ' bad' : h.bj ? ' bj' : '');
      const r = el.querySelector('.hr');
      if (h.result) { const [txt, c] = RES[h.result]; r.className = 'hr show ' + c; r.textContent = txt + (h.net > 0 ? ' +' + fmt(h.net) : h.net < 0 ? ' −' + fmt(-h.net) : ''); } else r.className = 'hr';
    });
    const d = v.dealer; $('dtot').textContent = !d.cards.length ? '' : d.cards.includes(null) ? d.total + ' + ?' : d.bj ? 'Blackjack' : d.total > 21 ? 'Перебір ' + d.total : String(d.total);
    setBal(v.balance);
    if (anim && v.phase === 'done' && v.hands.some(h => h.result)) {
      const res = v.hands.map(h => h.result), wins = res.some(r => r === 'win' || r === 'blackjack');
      FX.sound(wins ? 'win' : res.every(r => r === 'lose' || r === 'bust') ? 'lose' : 'chip');
      v.hands.forEach((h, i) => { const b = H.children[i] && H.children[i].querySelector('.hb');
        if (h.net > 0) { FX.fly($('dcards'), b); FX.fly($('dcards'), b, FX.CHIP, { delay: 120 }); } else if (h.net < 0) FX.fly(b, $('dcards')); });
    }
    controls(v);
  }
  function setBal(n) {
    const el = $('bjBal'), from = balShown == null ? n : balShown; balShown = n;
    if (!FX.level() || from === n) { el.textContent = fmt(n); return; }
    const t0 = performance.now(), step = now => { const k = Math.min(1, (now - t0) / 500); el.textContent = fmt(Math.round(from + (n - from) * k)); if (k < 1) requestAnimationFrame(step); };
    requestAnimationFrame(step);
  }
  function controls(v) {
    const A = $('bjact'), playing = v.phase === 'player'; A.hidden = !playing; $('bjtray').hidden = playing;
    if (playing) {
      ['hit', 'stand', 'double', 'split'].filter(a => v.actions.includes(a)).forEach(a => {
        const b = document.createElement('button'); b.textContent = NAMES[a]; b.title = TIPS[a]; b.className = a === 'hit' || a === 'stand' ? 'p' : ''; b.onclick = () => { FX.sound('click'); act({ t: 'bj_act', a }); }; A.appendChild(b); });
      $('bjInfo').textContent = v.hands.length > 1 ? `Ваш хід — рука ${v.active + 1} з ${v.hands.length}` : 'Ваш хід';
    } else {
      if (bet > v.balance || bet < v.min_bet) bet = Math.min(lastBet, v.balance) || 0;
      renderBet(); lock(false); $('bjDeal').disabled = !(bet >= v.min_bet && bet <= v.balance);
      $('bjInfo').textContent = v.broke ? 'Фішки закінчились — натисніть New Game' : v.phase === 'done' ? 'Раунд завершено. Змініть ставку або натисніть Deal' : 'Оберіть ставку й натисніть Deal';
      $('bjNew').classList.toggle('p', !!v.broke);
    }
  }
  const renderBet = () => { $('bjbetamt').textContent = fmt(bet); $('bjDeal').disabled = !(view && bet >= view.min_bet && bet <= view.balance); };

  /* ---- ставки ---- */
  CHIPS.forEach(c => { const b = document.createElement('button'); b.className = 'cchip c' + c; b.textContent = c; b.setAttribute('aria-label', 'Фішка ' + c);
    b.onclick = () => { if (!view || view.phase === 'player') return; const n = Math.min(bet + c, view.max_bet, view.balance); if (n === bet) return; bet = n; FX.sound('chip'); FX.fly(b, $('bjbet')); renderBet(); };
    $('bjchips').appendChild(b); });
  $('bjClear').onclick = () => { bet = 0; renderBet(); };
  $('bjRepeat').onclick = () => { if (view) { bet = Math.min(lastBet, view.balance, view.max_bet); renderBet(); } };
  $('bjDeal').onclick = () => { if (!view || !(bet >= view.min_bet && bet <= view.balance)) return; lastBet = bet; FX.sound('click'); act({ t: 'bj_deal', bet }); };
  $('bjNew').onclick = () => { if (confirm('Почати нову гру? Баланс повернеться до 1000 фішок.')) { bet = lastBet = 0; lastRound = -1; balShown = null; act({ t: 'bj_new' }); } };
  return { update, rules: () => rules, history: () => (view ? view.history : []) };
})();
