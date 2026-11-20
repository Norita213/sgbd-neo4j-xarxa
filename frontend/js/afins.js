const user = requireUser();
renderNav('afins');

const filters = document.getElementById('activity-filters');
const list = document.getElementById('recommendations');
const retry = document.getElementById('retry');
const weekdays = [...DOW_SHORT.slice(1), DOW_SHORT[0]];
let selectedActivity = '';
let latestRequest = 0;

// Franges en comú, compactes: les hores seguides s'ajunten ("18–22 h") i els
// dies amb les mateixes hores van junts -> "Ds, Dg · 08–22 h"
function formatSharedSlots(slots) {
  const hoursByDay = new Map();
  for (const { day, hour } of slots) {
    if (!hoursByDay.has(day)) hoursByDay.set(day, []);
    hoursByDay.get(day).push(hour);
  }
  const pad = hour => String(hour).padStart(2, '0');
  const daysByRanges = new Map();
  for (const day of weekdays) {
    const hours = [...new Set(hoursByDay.get(day) || [])].sort((a, b) => a - b);
    if (!hours.length) continue;
    const ranges = [];
    for (let i = 0; i < hours.length; i++) {
      const start = hours[i];
      let end = start + 1;
      while (i + 1 < hours.length && hours[i + 1] === end) { end++; i++; }
      ranges.push(`${pad(start)}–${pad(end)} h`);
    }
    const key = ranges.join(', ');
    if (!daysByRanges.has(key)) daysByRanges.set(key, []);
    daysByRanges.get(key).push(day);
  }
  return [...daysByRanges].map(([ranges, days]) => `${days.join(', ')} · ${ranges}`);
}

const MAX_SLOT_LINES = 3;

function slotsBlock(lines) {
  if (!lines.length) return '';
  const shown = lines.slice(0, MAX_SLOT_LINES);
  const extra = lines.length - shown.length;
  return `
    <div class="slot-list">
      <span class="slot-label">${icon('clock', 14)}Hores lliures en comú</span>
      ${shown.map(line => `<span>${esc(line)}</span>`).join('')}
      ${extra > 0 ? `<span class="muted">+${extra} ${extra === 1 ? 'franja més' : 'franges més'}</span>` : ''}
    </div>`;
}

function personCard(person) {
  const name = person.age == null ? person.name : `${person.name}, ${person.age}`;
  const activities = person.activities.map(activity => `<span class="chip">${esc(activity)}</span>`).join('');
  const sharedSlots = formatSharedSlots(person.shared_slots);
  return `
    <article class="event-card person-card">
      <span class="avatar ${avatarClass(person.name)}" aria-hidden="true">${esc(initials(person.name))}</span>
      <div class="event-body">
        <h2 class="event-title" style="margin: 0; overflow-wrap: anywhere">${esc(name)}</h2>
        <div class="event-meta">${esc(person.zone)}${person.nearby_zone ? ' · Zona propera' : ''}</div>
        <div class="event-tags">
          ${activities}
          ${person.connected ? '<span>Ja hi tens connexió</span>' : ''}
        </div>
        ${slotsBlock(sharedSlots)}
      </div>
    </article>`;
}

function updateFilterSelection() {
  for (const button of filters.querySelectorAll('button')) {
    const active = button.dataset.activity === selectedActivity;
    button.classList.toggle('btn-primary', active);
    button.classList.toggle('btn-secondary', !active);
    button.setAttribute('aria-pressed', String(active));
  }
}

function renderFilters(people) {
  const activities = [...new Set(people.flatMap(person => person.activities))];
  activities.sort((first, second) => first.localeCompare(second, 'ca'));
  const buttons = ['', ...activities].map(activity => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn btn-small';
    button.dataset.activity = activity;
    button.textContent = activity || 'Totes';
    return button;
  });
  filters.replaceChildren(...buttons);
  filters.hidden = !activities.length;
  updateFilterSelection();
}

async function loadRecommendations() {
  const request = ++latestRequest;
  const query = new URLSearchParams({ include_connected: 'true' });
  if (selectedActivity) query.set('activity', selectedActivity);
  retry.hidden = true;
  list.innerHTML = '<div class="empty">Carregant…</div>';
  try {
    const people = await api(`/persons/${encodeURIComponent(user.id)}/recommendations?${query}`);
    if (request !== latestRequest) return;
    if (!selectedActivity) renderFilters(people);
    list.innerHTML = people.length
      ? people.map(personCard).join('')
      : '<div class="empty">Ara mateix no hi ha persones afins amb aquests criteris.</div>';
  } catch (err) {
    if (request !== latestRequest) return;
    list.innerHTML = `<div class="error">${esc(err.message)}</div>`;
    retry.hidden = false;
  }
}

filters.addEventListener('click', event => {
  const button = event.target.closest('button[data-activity]');
  if (!button || button.dataset.activity === selectedActivity) return;
  selectedActivity = button.dataset.activity;
  updateFilterSelection();
  loadRecommendations();
});
retry.addEventListener('click', loadRecommendations);
loadRecommendations();
