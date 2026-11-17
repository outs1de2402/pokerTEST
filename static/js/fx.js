/* Анімації та звук. Повністю відокремлені від ігрової логіки: нічого не блокують і працюють без звуку. */
const FX = (() => {
  const KEY = 'pk_cfg'; const cfg = { sound: true, anim: 2 }; let ac = null, layer = null;
  try { Object.assign(cfg, JSON.parse(localStorage.getItem(KEY) || '{}')); } catch (e) {}
  const reduced = () => !!(window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches);
  const level = () => reduced() ? 0 : cfg.anim;                  // 0 вимкнено, 1 спрощено, 2 повні
  const apply = () => { document.body.classList.toggle('anim0', level() === 0); document.body.classList.toggle('anim1', level() === 1); };
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(cfg)); } catch (e) {} apply(); };
  const A = () => { if (!ac) { const C = window.AudioContext || window.webkitAudioContext; if (C) ac = new C(); } return ac; };
  addEventListener('pointerdown', () => { const a = A(); if (a && a.state === 'suspended') a.resume(); });
  function tone(f, d, type = 'sine', v = .07, t0 = 0) {
    try { const a = A(); if (!a) return; const o = a.createOscillator(), g = a.createGain(), t = a.currentTime + t0;
      o.type = type; o.frequency.value = f; g.gain.setValueAtTime(v, t); g.gain.exponentialRampToValueAtTime(.0001, t + d);
      o.connect(g); g.connect(a.destination); o.start(t); o.stop(t + d); } catch (e) {} }
  function noise(d, v = .1, f = 2500) {
    try { const a = A(); if (!a) return; const n = Math.floor(a.sampleRate * d), b = a.createBuffer(1, n, a.sampleRate), x = b.getChannelData(0);
      for (let i = 0; i < n; i++) x[i] = (Math.random() * 2 - 1) * (1 - i / n);
      const s = a.createBufferSource(), h = a.createBiquadFilter(), g = a.createGain(); h.type = 'highpass'; h.frequency.value = f; g.gain.value = v;
      s.buffer = b; s.connect(h); h.connect(g); g.connect(a.destination); s.start(); } catch (e) {} }
  const SND = {
    click: () => tone(520, .05, 'triangle', .05), deal: () => noise(.07, .12, 3000), flip: () => noise(.06, .09, 1800),
    chip: () => { tone(1900, .05, 'square', .03); tone(1300, .08, 'triangle', .05, .03); },
    turn: () => { tone(660, .1); tone(880, .14, 'sine', .06, .1); },
    lose: () => { tone(300, .22, 'sawtooth', .04); tone(200, .3, 'sawtooth', .04, .15); },
    win: () => [523, 659, 784, 1047].forEach((f, i) => tone(f, .28, 'triangle', .06, i * .1)) };
  const sound = n => { if (cfg.sound && SND[n]) SND[n](); };
  const t = ms => level() ? ms * (level() === 1 ? .4 : 1) : 0;
  const later = (fn, ms) => setTimeout(fn, ms);
  const CHIP = '<span class="chip" style="margin:0"></span>';

  /* карта «летить» від колоди до свого місця */
  function dealIn(el, from, delay = 0) {
    const l = level(); if (!l || !el.animate || !from) return;
    const a = from.getBoundingClientRect(), b = el.getBoundingClientRect();
    const dx = a.left + a.width / 2 - (b.left + b.width / 2), dy = a.top + a.height / 2 - (b.top + b.height / 2);
    el.animate([{ transform: `translate(${dx}px,${dy}px) scale(.5) rotate(-25deg)`, opacity: 0 }, { opacity: 1, offset: .2 }, { transform: 'none', opacity: 1 }],
      { duration: t(520), delay: t(delay), easing: 'cubic-bezier(.2,.8,.25,1)', fill: 'backwards' });
  }
  /* фішка летить з одного елемента в інший */
  function fly(from, to, html = CHIP, { dur = 550, delay = 0 } = {}) {
    if (!level() || !layer || !from || !to) return;
    const L = layer.getBoundingClientRect(), a = from.getBoundingClientRect(), b = to.getBoundingClientRect();
    const el = document.createElement('div'); el.className = 'fly'; el.innerHTML = html;
    el.style.left = (a.left + a.width / 2 - L.left) + 'px'; el.style.top = (a.top + a.height / 2 - L.top) + 'px'; layer.appendChild(el);
    if (!el.animate) { el.remove(); return; }
    const dx = b.left + b.width / 2 - (a.left + a.width / 2), dy = b.top + b.height / 2 - (a.top + a.height / 2);
    const an = el.animate([{ transform: 'translate(-50%,-50%) scale(1)', opacity: 0 }, { opacity: 1, offset: .15 },
      { transform: `translate(calc(-50% + ${dx}px),calc(-50% + ${dy}px)) scale(.85)`, opacity: 1 }],
      { duration: t(dur), delay: t(delay), easing: 'cubic-bezier(.25,.7,.2,1)', fill: 'both' });
    an.onfinish = () => el.remove(); an.oncancel = () => el.remove();
  }
  return { cfg, save, apply, level, sound, t, later, dealIn, fly, CHIP, setLayer: e => { layer = e; } };
})();
