/* Відображення покерного столу: розстановка місць, карти, фішки, анімації за різницею станів. Правил гри тут немає. */
const PT = (() => {
  const $ = id => document.getElementById(id);
  const STY = { cautious: '🛡', balanced: '⚖', aggressive: '🔥' };
  let prev = null, n = 0, seats = [], hno = -1, bslots = [], timerKey = '';
  const hue = s => { let h = 0; for (const c of s) h = (h * 31 + c.charCodeAt(0)) % 360; return h; };
  const { key, mk: mkCard, setFace, flipUp } = CardUI;

  function build(S) {
    const T = $('tbl'); T.querySelectorAll('.seat').forEach(e => e.remove()); seats = []; n = S.pl.length;
    const mr = Math.max(0, S.pl.findIndex(p => p.me)), rx = innerWidth < 700 ? 41 : 43;
    S.pl.forEach((p, i) => {
      const k = (i - mr + n) % n, a = Math.PI / 2 + 2 * Math.PI * k / n, el = document.createElement('div');
      el.className = 'seat' + (k === 0 ? ' me' : '');
      el.style.cssText = `left:${50 + rx * Math.cos(a)}%;top:${50 + 42 * Math.sin(a)}%;--bx:${(-Math.cos(a) * 86).toFixed(0)}px;--by:${(-Math.sin(a) * 66).toFixed(0)}px`;
      el.innerHTML = '<div class="cards"></div><div class="plate"><div class="av"></div><div class="who"><div class="nm"></div><div class="stk"></div></div><b class="dbtn">D</b></div><div class="act"></div><div class="timer"><i></i></div><div class="bet"></div>';
      T.appendChild(el);
      const q = s => el.querySelector(s);
      seats.push({ el, cards: q('.cards'), plate: q('.plate'), nm: q('.nm'), stk: q('.stk'), av: q('.av'), act: q('.act'), bet: q('.bet'), tm: q('.timer i') });
    });
  }
  function seat(i, p, S, fresh) {
    const sd = seats[i], el = sd.el, ord = (i - S.btn - 1 + n * 2) % n;
    sd.nm.textContent = p.n + (p.sty ? ' ' + STY[p.sty] : ''); sd.av.textContent = (p.n[0] || '?').toUpperCase();
    const h = hue(p.n); sd.av.style.background = `linear-gradient(135deg,hsl(${h} 55% 46%),hsl(${(h + 40) % 360} 55% 26%))`;
    sd.stk.textContent = p.c.toLocaleString('uk-UA');
    el.classList.toggle('fold', p.f && p.h.length > 0); el.classList.toggle('win', !!p.w);
    el.classList.toggle('turn', i === S.turn && S.wait); el.classList.toggle('dl', i === S.btn); el.classList.toggle('out', p.c === 0 && !p.h.length);
    const l = p.l || ''; sd.act.textContent = l;
    sd.act.className = 'act ' + (/^Фолд/.test(l) ? 'f' : /^(Чек|Колл)/.test(l) ? 'c' : /Олл/.test(l) ? 'a' : /^(Бет|Рейз)/.test(l) ? 'b' : '');
    /* ставка біля місця та рух фішок */
    const pp = prev && prev.hno === S.hno ? prev.pl[i] : null;
    sd.bet.innerHTML = p.b ? `<span class="chip"></span>${p.b}` : '';
    if (pp && p.b > pp.b) { FX.fly(sd.plate, sd.bet); FX.sound('chip'); }
    if (pp && pp.b > 0 && p.b === 0 && !S.pl.some(x => x.w)) { FX.fly(sd.bet, $('potc'), FX.CHIP, { delay: 80 }); FX.sound('chip'); }
    /* карти */
    const box = sd.cards; while (box.children.length > p.h.length) box.lastChild.remove();
    p.h.forEach((c, k) => {
      let c_el = box.children[k]; const isNew = !c_el, d = (k * n + ord) * 110;
      if (isNew) { c_el = mkCard(); box.appendChild(c_el); FX.dealIn(c_el, $('deck'), d); if (FX.level()) FX.later(() => FX.sound('deal'), FX.t(d)); }
      setFace(c_el, c);
      if (c && !c_el.classList.contains('up')) flipUp(c_el, isNew ? d + 420 : 0);
      if (!c) c_el.classList.remove('up');
    });
  }
  function board(S) {
    const have = bslots.filter(s => s.firstChild).length;
    S.bd.forEach((c, k) => {
      const sl = bslots[k]; let el = sl.firstChild;
      if (!el) { el = mkCard(); sl.appendChild(el); const d = (k - have) * 190; FX.dealIn(el, $('deck'), d); flipUp(el, d + 420); }
      setFace(el, c);
    });
    if (S.bd.length > have) { if (FX.level()) FX.sound('flip'); }
  }
  function hilite(S) {
    const wins = S.pl.filter(p => p.w && p.b5), set = new Set(wins.flatMap(p => p.b5.map(key)));
    const mark = (el, on, dim) => { el.classList.toggle('hl', on); el.classList.toggle('dim', dim); };
    bslots.forEach(sl => { const el = sl.firstChild; if (el) mark(el, set.has(el.dataset.k), set.size > 0 && !set.has(el.dataset.k)); });
    S.pl.forEach((p, i) => [...seats[i].cards.children].forEach(el => mark(el, !!(p.w && set.has(el.dataset.k)), false)));
  }
  function update(S) {
    if (!bslots.length) { const B = $('bd'); B.innerHTML = ''; for (let i = 0; i < 5; i++) { const d = document.createElement('div'); d.className = 'cslot'; B.appendChild(d); bslots.push(d); } }
    if (S.pl.length !== n || !seats.length) { build(S); prev = null; }
    const fresh = S.hno !== hno;
    if (fresh) { hno = S.hno; bslots.forEach(sl => sl.innerHTML = ''); seats.forEach(s => s.cards.innerHTML = ''); prev = prev && null; }
    S.pl.forEach((p, i) => seat(i, p, S, fresh)); board(S);
    const anyWin = S.pl.some(p => p.w), potEl = $('pot');
    const txt = anyWin ? '' : S.pot ? 'Банк: ' + S.pot.toLocaleString('uk-UA') : '';
    if (potEl.textContent !== txt) { potEl.textContent = txt; potEl.classList.add('bump'); setTimeout(() => potEl.classList.remove('bump'), 200); }
    if (prev && prev.hno === S.hno) S.pl.forEach((p, i) => { if (p.w && !prev.pl[i].w) {
      for (let k = 0; k < 3; k++) FX.fly($('potc'), seats[i].plate, FX.CHIP, { delay: k * 120, dur: 650 });
      FX.later(() => FX.sound(p.me ? 'win' : 'chip'), FX.t(300)); } });
    hilite(S);
    const tk = S.wait && S.turn >= 0 ? S.tk + '-' + S.turn : '';
    if (tk && tk !== timerKey) { const i = seats[S.turn].tm; i.style.animation = 'none'; void i.offsetWidth; i.style.animation = ''; if (S.act) FX.sound('turn'); }
    timerKey = tk; prev = S;
  }
  function reset() { prev = null; hno = -1; seats = []; n = 0; bslots = []; timerKey = ''; const T = $('tbl'); if (T) T.querySelectorAll('.seat').forEach(e => e.remove()); }
  return { update, reset };
})();
