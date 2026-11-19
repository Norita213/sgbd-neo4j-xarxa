const user = requireUser();
renderNav('afins');

const filters = document.getElementById('activity-filters');
const list = document.getElementById('recommendations');
const retry = document.getElementById('retry');
const weekdays = [...DOW_SHORT.slice(1), DOW_SHORT[0]];
let selectedActivity = '';
let latestRequest = 0;

function formatSharedSlots(slots) {
  const daysByHour = new Map();
  for (const { day, hour } of slots) {
    if (!daysByHour.has(hour)) daysByHour.set(hour, new Set());
    daysByHour.get(hour).add(day);
  }
  return [...daysByHour].sort(([first], [second]) => first - second).map(([hour, days]) => {
    const orderedDays = weekdays.filter(day => days.has(day));
    const start = String(hour).padStart(2, '0');
    const end = String(hour + 1).padStart(2, '0');
    return `${orderedDays.join(', ')} · ${start}–${end} h`;
  });
}

function personCard(person) {
  const name = person.age == null ? person.name : `${person.name}, ${person.age}`;
  const activities = person.activities.map(activity => `<span class="chip">${esc(activity)}</span>`).join('');
  const sharedSlots = formatSharedSlots(person.shared_slots);
  return `
    <article class="event-card">
      <span class="avatar ${avatarClass(person.name)}" aria-hidden="true">${esc(initials(person.name))}</span>
      <div class="event-body">
        <h2 class="event-title" style="margin: 0; overflow-wrap: anywhere">${esc(name)}</h2>
        <div class="event-meta">${esc(person.zone)}${person.nearby_zone ? ' · Zona propera' : ''}</div>
        <div class="event-tags">
          ${activities}
          ${person.connected ? '<span>Ja hi tens connexió</span>' : ''}
        </div>
        <div class="event-meta">${esc(sharedSlots.join(' / '))}</div>
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
