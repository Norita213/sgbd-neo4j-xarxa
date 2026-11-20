const communityId = new URLSearchParams(location.search).get('id');
const personId = getUser()?.id;
const viewer = personId ? `?${new URLSearchParams({ person_id: personId })}` : '';
const communityUrl = `/communities/${encodeURIComponent(communityId)}`;
const elements = {
  avatar: document.getElementById('community-avatar'),
  title: document.getElementById('community-title'),
  summary: document.getElementById('community-summary'),
  actions: document.getElementById('community-actions'),
  membership: document.getElementById('membership-status'),
  join: document.getElementById('join-community'),
  create: document.getElementById('create-event'),
  loading: document.getElementById('community-loading'),
  error: document.getElementById('community-error'),
  tabs: document.getElementById('community-tabs'),
  eventsTab: document.getElementById('events-tab'),
  membersTab: document.getElementById('members-tab'),
  eventsPanel: document.getElementById('community-events'),
  membersPanel: document.getElementById('community-members'),
};
const views = [
  { tab: elements.eventsTab, panel: elements.eventsPanel },
  { tab: elements.membersTab, panel: elements.membersPanel },
];
let community;
let membersRequest = 0;

document.getElementById('back').innerHTML = icon('back');

function showError(message) {
  elements.error.textContent = message;
  elements.error.classList.remove('hidden');
}

function renderCommunity() {
  const { activity, zone, members, is_member: isMember } = community;
  const name = community.name || 'Comunitat';
  document.title = `${name} · AFINIT`;
  elements.title.textContent = name;

  const words = name.trim().split(/[\s\p{Pd}]+/u)
    .filter(word => word && !/^(de|del|dels|i|la|el|els|les)$/i.test(word));
  elements.avatar.textContent = words.length < 2 ? initials(name) : initials(words[0][0] + words[1][0]);
  elements.avatar.className = `avatar community-avatar ${avatarClass(name)}`;

  const membersLabel = `${members} ${members === 1 ? 'membre' : 'membres'}`;
  elements.summary.textContent = [activity, zone, membersLabel].filter(Boolean).join(' · ');
  elements.summary.classList.remove('hidden');
  elements.membersTab.textContent = `Participants (${members})`;

  elements.membership.classList.toggle('hidden', !isMember);
  elements.join.classList.toggle('hidden', isMember);
  elements.create.classList.toggle('hidden', !isMember);
  elements.actions.classList.remove('hidden');
}

function selectView(selected) {
  for (const view of views) {
    const active = view === selected;
    view.tab.setAttribute('aria-selected', String(active));
    view.tab.tabIndex = active ? 0 : -1;
    view.panel.classList.toggle('hidden', !active);
  }
}

for (const view of views) {
  view.tab.addEventListener('click', () => selectView(view));
  view.tab.addEventListener('keydown', event => {
    if (!['ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(event.key)) return;
    event.preventDefault();
    let next = views.find(item => item !== view);
    if (event.key === 'Home') next = views[0];
    if (event.key === 'End') next = views[views.length - 1];
    selectView(next);
    next.tab.focus();
  });
}

function panelMessage(panel, message, className = 'empty') {
  panel.innerHTML = `<div class="${className}">${esc(message)}</div>`;
}

function communityEventCard(event) {
  let dateBadge = '<span class="date-badge undated-badge">Sense data</span>';
  if (event.date) {
    const { dow, num, mon } = dateParts(event.date);
    dateBadge = `<span class="date-badge"><span class="dow">${dow}</span><span class="num">${num}</span><span class="mon">${mon}</span></span>`;
  }
  const meta = [event.start_time, event.place || event.zone].filter(Boolean).join(' · ');
  const content = `
    ${dateBadge}
    <span class="event-body">
      <span class="event-title">${esc(event.title)}</span>
      ${meta ? `<span class="event-meta">${esc(meta)}</span>` : ''}
      <span class="event-tags">
        <span>${esc(peopleText(event))}</span>
        ${event.attending ? '<span class="chip">Hi vas</span>' : ''}
      </span>
    </span>`;
  return event.id
    ? `<a class="event-card" href="quedada.html?id=${encodeURIComponent(event.id)}">${content}</a>`
    : `<div class="event-card">${content}</div>`;
}

async function loadEvents() {
  panelMessage(elements.eventsPanel, 'S’estan carregant les quedades…');
  try {
    const events = await api(`${communityUrl}/events${viewer}`);
    elements.eventsTab.textContent = `Quedades (${events.length})`;
    if (events.length) elements.eventsPanel.innerHTML = events.map(communityEventCard).join('');
    else panelMessage(elements.eventsPanel, 'Aquesta comunitat encara no té cap quedada prevista.');
  } catch (err) {
    panelMessage(elements.eventsPanel, err.message, 'error');
  }
}

async function loadMembers() {
  const request = ++membersRequest;
  panelMessage(elements.membersPanel, 'S’estan carregant els participants…');
  try {
    const members = await api(`${communityUrl}/members`);
    if (request !== membersRequest) return;
    community.members = members.length;
    renderCommunity();
    if (!members.length) {
      panelMessage(elements.membersPanel, 'Aquesta comunitat encara no té membres.');
      return;
    }
    elements.membersPanel.innerHTML = `
      <ul class="community-list info-box" role="list">
        ${members.map(member => `
          <li class="info-row">
            <span class="avatar ${avatarClass(member.name)}" aria-hidden="true">${esc(initials(member.name))}</span>
            <div>
              <span class="main">${esc(member.name)}</span>
              ${member.zone ? `<span class="sub">${esc(member.zone)}</span>` : ''}
            </div>
          </li>`).join('')}
      </ul>`;
  } catch (err) {
    if (request === membersRequest) panelMessage(elements.membersPanel, err.message, 'error');
  }
}

elements.join.addEventListener('click', async () => {
  if (!personId) {
    location.href = 'index.html';
    return;
  }
  if (!community || community.is_member || elements.join.disabled) return;

  const restoreFocus = document.activeElement === elements.join;
  elements.error.classList.add('hidden');
  elements.join.disabled = true;
  elements.join.textContent = 'Unint…';
  try {
    await api(`${communityUrl}/members/${encodeURIComponent(personId)}`, { method: 'POST' });
    community.is_member = true;
    renderCommunity();
    if (restoreFocus && document.activeElement === document.body) elements.create.focus();
    loadMembers();
  } catch (err) {
    showError(err.message);
  } finally {
    elements.join.disabled = false;
    elements.join.textContent = 'Unir-se';
  }
});

async function loadCommunity() {
  try {
    if (!communityId) throw new Error('Tria una comunitat des del llistat.');
    community = await api(`${communityUrl}${viewer}`);
    elements.create.href = `nova-quedada.html?${new URLSearchParams({ community_id: community.id })}`;
    renderCommunity();
    elements.tabs.classList.remove('hidden');
    selectView(views[0]);
    loadEvents();
    loadMembers();
  } catch (err) {
    showError(err.message);
  } finally {
    elements.loading.classList.add('hidden');
  }
}

loadCommunity();
