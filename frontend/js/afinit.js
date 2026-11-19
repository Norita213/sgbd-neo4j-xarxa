// =====================================================================
// AFINIT - utilitats comunes del frontend
//   - api(): crides al backend (FastAPI, al mateix servidor)
//   - sessió simulada: la persona que ha entrat es guarda al navegador
//   - navegació inferior, dates en català, avatars i escapament d'HTML
// =====================================================================

const API_BASE = ''; // el frontend el serveix el mateix FastAPI

async function api(path, options = {}) {
  const opts = { ...options, headers: { 'Content-Type': 'application/json', ...(options.headers || {}) } };
  if (opts.body && typeof opts.body !== 'string') opts.body = JSON.stringify(opts.body);
  let res;
  try {
    res = await fetch(API_BASE + path, opts);
  } catch {
    throw new Error("No s'ha pogut connectar amb el servidor.");
  }
  const data = res.status === 204 ? null : await res.json().catch(() => null);
  if (!res.ok) throw new Error(errorMessage(data, res.status));
  return data;
}

function errorMessage(data, status) {
  const detail = data && data.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail) && detail.length) {
    // Errors de validació de FastAPI: "Value error, ..." -> missatge net
    return detail.map(d => String(d.msg || '').replace(/^Value error, /, '')).join(' ');
  }
  return `Error del servidor (${status}).`;
}

// ---------- Sessió (login simulat: només correu) ----------
const SESSION_KEY = 'afinit.user';

function getUser() {
  try { return JSON.parse(localStorage.getItem(SESSION_KEY)); } catch { return null; }
}
function setUser(user) {
  try { localStorage.setItem(SESSION_KEY, JSON.stringify(user)); } catch { /* sense emmagatzematge */ }
}
function logout() {
  try { localStorage.removeItem(SESSION_KEY); } catch { /* res */ }
  location.href = 'index.html';
}
// A les pantalles que necessiten usuari: si no n'hi ha, cap al login
function requireUser() {
  const user = getUser();
  if (!user) { location.replace('index.html'); throw new Error('Sense sessió'); }
  return user;
}

// ---------- Tema fosc / clar (js/theme.js l'aplica en carregar) ----------
function getTheme() {
  return document.documentElement.getAttribute('data-theme') === 'light' ? 'light' : 'dark';
}
function setTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  try { localStorage.setItem('afinit.theme', theme); } catch { /* sense emmagatzematge */ }
}

// ---------- Utilitats ----------
function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, c =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

const DOW_SHORT = ['Dg', 'Dl', 'Dm', 'Dc', 'Dj', 'Dv', 'Ds'];          // Date.getDay(): 0 = diumenge
const DOW_LONG = ['Diumenge', 'Dilluns', 'Dimarts', 'Dimecres', 'Dijous', 'Divendres', 'Dissabte'];
const MONTH_SHORT = ['gen.', 'febr.', 'març', 'abr.', 'maig', 'juny', 'jul.', 'ag.', 'set.', 'oct.', 'nov.', 'des.'];
const MONTH_LONG = ['gener', 'febrer', 'març', 'abril', 'maig', 'juny', 'juliol', 'agost', 'setembre', 'octubre', 'novembre', 'desembre'];

function parseDate(iso) {
  const [y, m, d] = String(iso).split('-').map(Number);
  return new Date(y, m - 1, d);
}
function dateParts(iso) {
  const dt = parseDate(iso);
  return { dow: DOW_SHORT[dt.getDay()], num: dt.getDate(), mon: MONTH_SHORT[dt.getMonth()] };
}
// "Dijous 29 d'octubre"
function longDate(iso) {
  const dt = parseDate(iso);
  const month = MONTH_LONG[dt.getMonth()];
  const de = /^[aeiou]/.test(month) ? "d’" : 'de ';
  return `${DOW_LONG[dt.getDay()]} ${dt.getDate()} ${de}${month}`;
}
// "Dijous 29 d'oct."
function shortDate(iso) {
  const dt = parseDate(iso);
  const month = MONTH_SHORT[dt.getMonth()];
  const de = /^[aeiou]/.test(month) ? "d’" : 'de ';
  return `${DOW_LONG[dt.getDay()]} ${dt.getDate()} ${de}${month}`;
}

function initials(name) {
  return String(name || '?').trim().slice(0, 2).toUpperCase();
}
function avatarClass(name) {
  let h = 0;
  for (const ch of String(name || '')) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return 'c' + (h % 4);
}

function toast(message) {
  const el = document.createElement('div');
  el.className = 'toast';
  el.setAttribute('role', 'status');
  el.textContent = message;
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 2600);
}

// ---------- Icones (traç, com a la maqueta) ----------
const ICONS = {
  back: '<path d="M15 18l-6-6 6-6"></path>',
  plus: '<path d="M12 5v14M5 12h14"></path>',
  check: '<path d="M20 6L9 17l-5-5"></path>',
  clock: '<circle cx="12" cy="12" r="9"></circle><path d="M12 7v5l3 2"></path>',
  pin: '<path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11z"></path><circle cx="12" cy="10" r="2.5"></circle>',
  user: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle>',
  users: '<path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M22 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path>',
  flag: '<path d="M5 21V4"></path><path d="M5 4h12l-2.5 4L17 12H5"></path>',
  calendar: '<rect x="3" y="4" width="18" height="18" rx="2"></rect><path d="M16 2v4M8 2v4M3 10h18"></path><path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01"></path>',
  share: '<circle cx="18" cy="5" r="3"></circle><circle cx="6" cy="12" r="3"></circle><circle cx="18" cy="19" r="3"></circle><path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4"></path>',
  profile: '<circle cx="12" cy="8" r="4"></circle><path d="M4 21v-1a6 6 0 0 1 6-6h4a6 6 0 0 1 6 6v1"></path>',
  logout: '<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><path d="M16 17l5-5-5-5"></path><path d="M21 12H9"></path>',
  moon: '<path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"></path>',
  sun: '<circle cx="12" cy="12" r="4"></circle><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"></path>',
};
function icon(name, size = 22, strokeWidth = 2) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="${strokeWidth}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICONS[name]}</svg>`;
}

// ---------- Navegació ----------
// Cada membre de l'equip canvia el seu 'href' quan tingui la pantalla feta.
const NAV_ITEMS = [
  { key: 'afins', label: 'Afins', icon: 'users', href: 'afins.html' },
  { key: 'quedades', label: 'Quedades', icon: 'flag', href: 'quedades.html' },
  { key: 'calendari', label: 'Calendari', icon: 'calendar', href: 'calendari.html' },
  { key: 'comunitats', label: 'Comunitats', icon: 'share', href: 'proximament.html?s=Comunitats' },
  { key: 'perfil', label: 'Perfil', icon: 'profile', href: 'perfil.html' },
];
// Logo (tres nodes connectats)
function brandMark(size = 30) {
  return `<svg width="${size}" height="${size}" viewBox="0 0 34 34" aria-hidden="true">
    <line x1="9" y1="10" x2="25" y2="12" stroke="var(--primary)" stroke-width="2"></line>
    <line x1="9" y1="10" x2="16" y2="25" stroke="var(--primary)" stroke-width="2"></line>
    <line x1="25" y1="12" x2="16" y2="25" stroke="var(--primary)" stroke-width="2"></line>
    <circle cx="9" cy="10" r="5" fill="var(--primary)"></circle>
    <circle cx="25" cy="12" r="4" fill="var(--accent)"></circle>
    <circle cx="16" cy="25" r="5" fill="var(--ink)"></circle>
  </svg>`;
}

// Navegació: barra inferior al mòbil i capçalera superior a l'ordinador.
// `mobile: false` -> només la capçalera (pantalles com el detall o el formulari,
// que al mòbil no porten barra inferior).
function renderNav(active, { mobile = true } = {}) {
  const links = NAV_ITEMS.map(item =>
    `<a href="${item.href}"${item.key === active ? ' aria-current="page"' : ''}>${icon(item.icon)}${item.label}</a>`
  ).join('');

  if (mobile) {
    const nav = document.createElement('nav');
    nav.className = 'bottom-nav';
    nav.setAttribute('aria-label', 'Navegació principal');
    nav.innerHTML = links;
    document.querySelector('.app').appendChild(nav);
  }

  const user = getUser();
  const header = document.createElement('header');
  header.className = 'site-header';
  header.innerHTML = `
    <div class="site-header-inner">
      <a class="site-brand" href="quedades.html">${brandMark()}<span>AFINIT</span></a>
      <nav class="site-nav" aria-label="Navegació principal">${links}</nav>
      <div class="site-actions">
        <a class="btn btn-primary btn-small" href="nova-quedada.html">${icon('plus', 18, 2.2)}Crear quedada</a>
        ${user ? `<a class="site-user" href="perfil.html" title="El teu perfil">
          <span class="avatar ${avatarClass(user.name)}">${esc(initials(user.name))}</span>
          <span class="site-user-name">${esc(user.name)}</span>
        </a>` : ''}
      </div>
    </div>`;
  document.body.prepend(header);
}

// ---------- Targetes de quedada ----------
function peopleText(ev) {
  let text = `${ev.participants} hi ${ev.participants === 1 ? 'va' : 'van'}`;
  if (ev.connections_attending > 0) {
    text += ` · ${ev.connections_attending} ${ev.connections_attending === 1 ? 'connexió teva' : 'connexions teves'}`;
  }
  return text;
}
function eventCard(ev) {
  const d = dateParts(ev.date);
  const place = ev.place ? ` · ${esc(ev.place)}` : ` · ${esc(ev.zone)}`;
  return `
    <a class="event-card" href="quedada.html?id=${encodeURIComponent(ev.id)}">
      <div class="date-badge"><span class="dow">${d.dow}</span><span class="num">${d.num}</span><span class="mon">${d.mon}</span></div>
      <div class="event-body">
        <span class="event-title">${esc(ev.title)}</span>
        <span class="event-meta">${esc(ev.start_time || '')}${place}</span>
        <div class="event-tags"><span class="chip">${esc(ev.activity)}</span><span>${peopleText(ev)}</span></div>
      </div>
    </a>`;
}
function attendingCard(ev) {
  const place = ev.place || ev.zone;
  return `
    <a class="attending-card" href="quedada.html?id=${encodeURIComponent(ev.id)}">
      <div class="check">${icon('check')}</div>
      <div class="info">
        <span>${esc(ev.title)}</span>
        <span>${shortDate(ev.date)} · ${esc(ev.start_time || '')} · ${esc(place)}</span>
      </div>
    </a>`;
}
