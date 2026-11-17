/* Спільні компоненти карт для покеру та Blackjack: 3D-карта з лицем і сорочкою. */
const CardUI = (() => {
  const key = c => c && c.r + '-' + c.s;
  const face = c => { const r = { 11: 'J', 12: 'Q', 13: 'K', 14: 'A' }[c.r] || c.r, s = '♠♥♦♣'[c.s];
    return `<div class="face${c.s == 1 || c.s == 2 ? ' r' : ''}"><span class="cr">${r}<br>${s}</span><span class="cs">${s}</span></div>`; };
  const mk = () => { const d = document.createElement('div'); d.className = 'card'; d.innerHTML = '<div class="in"><div class="back"></div></div>'; return d; };
  function setFace(el, c) {
    const box = el.firstChild, f = box.querySelector('.face');
    if (c) { if (el.dataset.k !== key(c)) { el.dataset.k = key(c); if (f) f.remove(); box.insertAdjacentHTML('afterbegin', face(c)); } }
    else if (f) { f.remove(); delete el.dataset.k; }
  }
  const flipUp = (el, ms) => { if (el.dataset.pend) return; el.dataset.pend = 1;
    setTimeout(() => { el.classList.add('up'); delete el.dataset.pend; }, FX.t(ms)); };
  return { key, face, mk, setFace, flipUp };
})();
