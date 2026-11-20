const user = requireUser();
renderNav('afins');

const filters = document.getElementById('activity-filters');
const list = document.getElementById('recommendations');
const retry = document.getElementById('retry');
const weekdays = [...DOW_SHORT.slice(1), DOW_SHORT[0]];
const weekdayList = new Intl.ListFormat('ca', { type: 'conjunction' });
const connectionStates = new Map();
let selectedActivity = '';
let latestRequest = 0;

// Agrupem les hores consecutives i els dies que comparteixen les mateixes franges.
function formatSharedSlots(slots) {
  const hoursByDay = new Map();
  for (const { day, hour } of slots) {
    if (!hoursByDay.has(day)) hoursByDay.set(day, []);
    hoursByDay.get(day).push(hour);
  }
  const formatHour = hour => String(hour).padStart(2, '0') + ':00';
  const groups = new Map();
  for (const day of weekdays) {
    const hours = [...new Set(hoursByDay.get(day) || [])].sort((a, b) => a - b);
    if (!hours.length) continue;
    const ranges = [];
    for (let i = 0; i < hours.length; i++) {
      const start = hours[i];
      let end = start + 1;
      while (i + 1 < hours.length && hours[i + 1] === end) { end++; i++; }
      ranges.push(`${formatHour(start)}–${formatHour(end)}`);
    }
    const key = ranges.join(', ');
    if (!groups.has(key)) groups.set(key, { days: [], ranges });
    groups.get(key).days.push(DOW_LONG[DOW_SHORT.indexOf(day)].toLocaleLowerCase('ca'));
  }
  return [...groups.values()];
}

function slotsBlock(groups) {
  if (!groups.length) return '';
  return `
    <div class="slot-list">
      <span class="slot-label">${icon('clock', 14)}Hores lliures en comú</span>
      <ul class="slot-groups" role="list">
        ${groups.map(({ days, ranges }) => {
          const label = weekdayList.format(days);
          return `
            <li class="slot-group">
              <span class="slot-days">${esc(label[0].toLocaleUpperCase('ca') + label.slice(1))}</span>
              <div class="slot-hours">
                ${ranges.map(range => `<span class="slot-hour">${esc(range)}</span>`).join('')}
              </div>
            </li>`;
        }).join('')}
      </ul>
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
        </div>
        ${slotsBlock(sharedSlots)}
        ${person.id ? `
          <div class="event-tags" data-connection-id="${esc(person.id)}" data-name="${esc(person.name)}">
            ${connectionAction(person.id, person.name, person.connected)}
          </div>` : ''}
      </div>
    </article>`;
}

function connectionAction(id, name, connected = false) {
  const state = connectionStates.get(id);
  if (connected || state === 'connected') return '<span class="chip">Connectats</span>';
  const busy = state === 'pending';
  return `<button class="btn btn-small btn-secondary" type="button" data-connect
    aria-label="${busy ? 'Connectant amb' : 'Connectar amb'} ${esc(name)}"${busy ? ' disabled' : ''}>
    ${busy ? 'Connectant…' : 'Connectar'}
  </button>`;
}

function updateConnectionActions(id) {
  for (const action of list.querySelectorAll('[data-connection-id]')) {
    if (action.dataset.connectionId === id) {
      action.innerHTML = connectionAction(id, action.dataset.name);
    }
  }
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
list.addEventListener('click', async event => {
  const button = event.target.closest('button[data-connect]');
  if (!button) return;
  const { connectionId: id } = button.closest('[data-connection-id]').dataset;
  if (connectionStates.has(id)) return;

  connectionStates.set(id, 'pending');
  updateConnectionActions(id);
  try {
    await api(`/persons/${encodeURIComponent(user.id)}/connections/${encodeURIComponent(id)}`, { method: 'POST' });
    connectionStates.set(id, 'connected');
  } catch (err) {
    connectionStates.delete(id);
    toast(err.message);
  } finally {
    updateConnectionActions(id);
  }
});
retry.addEventListener('click', loadRecommendations);
loadRecommendations();
