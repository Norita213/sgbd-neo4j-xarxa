renderNav('comunitats');
document.getElementById('community-search-icon').innerHTML = icon('search', 18);

const personId = getUser()?.id;
const viewerQuery = personId ? `?${new URLSearchParams({ person_id: personId })}` : '';
const search = document.getElementById('community-search');
const status = document.getElementById('community-status');
const sections = document.getElementById('community-sections');
const yourCommunities = document.getElementById('your-communities');
const discoverCommunities = document.getElementById('discover-communities');
const detail = document.getElementById('community-detail');
const detailTitle = document.getElementById('community-detail-title');
const detailSummary = document.getElementById('community-detail-summary');
const detailMembers = document.getElementById('community-detail-members');

let communities = [];
let weeklyEvents = null;
let latestDetailRequest = 0;
const communitiesById = new Map();
const friendsByCommunity = new Map();
const nearbyZones = new Set();
const pendingJoins = new Set();

function communityPath(id) {
  return `/communities/${encodeURIComponent(id)}`;
}

function countLabel(count, singular, plural) {
  return `${count} ${count === 1 ? singular : plural}`;
}

function summary(community) {
  const members = countLabel(community.members, 'membre', 'membres');
  if (community.is_member) {
    if (!weeklyEvents) return members;
    const events = weeklyEvents.get(community.id) ?? 0;
    return `${members} · ${countLabel(events, 'quedada', 'quedades')} aquesta setmana`;
  }

  const parts = [community.activity, members];
  const friends = friendsByCommunity.get(community.id) ?? 0;
  if (friends) parts.push(countLabel(friends, 'amic teu', 'amics teus'));
  else if (nearbyZones.has(community.zone)) parts.push('a prop teu');
  return parts.filter(Boolean).join(' · ');
}

function communityInitials(name) {
  const connectors = ['de', 'del', 'dels', 'i', 'la', 'el', 'els', 'les'];
  const words = String(name ?? '').trim().split(/[\s\p{Pd}]+/u)
    .filter(word => word && !connectors.includes(word.toLowerCase()));
  return words.length < 2 ? initials(name) : (words[0][0] + words[1][0]).toUpperCase();
}

function communityCard(community) {
  const id = esc(community.id);
  const name = esc(community.name);
  const content = `
    <span class="avatar community-avatar ${avatarClass(community.name)}" aria-hidden="true">${esc(communityInitials(community.name))}</span>
    <span class="community-copy">
      <span class="community-name">${name}</span>
      <span class="community-meta" data-community-summary="${id}">${esc(summary(community))}</span>
    </span>`;
  const cardBody = community.id
    ? `<button class="community-card-content" type="button" data-open-community="${id}">${content}</button>`
    : `<div class="community-card-content">${content}</div>`;

  let joinButton = '';
  if (community.id && !community.is_member) {
    const pending = pendingJoins.has(community.id);
    joinButton = `
      <button class="btn btn-secondary btn-small community-join" type="button"
              data-join-community="${id}" aria-label="Unir-se a ${name}"${pending ? ' disabled' : ''}>
        ${pending ? 'Unint…' : 'Unir-se'}
      </button>`;
  }
  return `<li class="community-card">${cardBody}${joinButton}</li>`;
}

function searchText(value) {
  return value.normalize('NFD').replace(/\p{M}/gu, '').toLowerCase();
}

function renderCards(container, entries, layout, emptyMessage) {
  container.innerHTML = entries.length
    ? `<ul class="community-list ${layout}" role="list">${entries.map(communityCard).join('')}</ul>`
    : `<div class="empty">${esc(emptyMessage)}</div>`;
}

function renderCommunities() {
  const query = searchText(search.value.trim());
  const visible = communities.filter(community =>
    searchText([community.name, community.activity, community.zone].join(' ')).includes(query)
  );
  const yourEmpty = query ? 'Cap de les teves comunitats coincideix amb la cerca.' : 'Encara no formes part de cap comunitat.';
  renderCards(yourCommunities, visible.filter(community => community.is_member), 'community-grid',
    personId ? yourEmpty : 'Inicia sessió per veure les teves comunitats.');
  renderCards(discoverCommunities, visible.filter(community => !community.is_member), 'list',
    query ? 'No hi ha comunitats que coincideixin amb la cerca.' : 'Ara mateix no hi ha comunitats per descobrir.');
}

function updateSummaries() {
  for (const element of sections.querySelectorAll('[data-community-summary]')) {
    const community = communitiesById.get(element.dataset.communitySummary);
    if (community) element.textContent = summary(community);
  }
}

function countWeeklyEvents(events) {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const sunday = new Date(today);
  sunday.setDate(today.getDate() + 7 - (today.getDay() || 7));

  const counts = new Map();
  for (const event of events) {
    if (!event.community_id || !event.date) continue;
    const date = parseDate(event.date);
    if (date >= today && date <= sunday) {
      counts.set(event.community_id, (counts.get(event.community_id) ?? 0) + 1);
    }
  }
  return counts;
}

async function loadPersonalContext() {
  const personPath = `/persons/${encodeURIComponent(personId)}`;
  const [profile, zones, events, connections] = await Promise.all(
    [personPath, '/zones', '/events', `${personPath}/connections`].map(path => api(path).catch(() => null))
  );
  if (events) weeklyEvents = countWeeklyEvents(events);
  if (profile?.zone) {
    nearbyZones.add(profile.zone);
    const zone = zones?.find(item => item.name === profile.zone);
    for (const nearby of zone?.near ?? []) nearbyZones.add(nearby);
  }
  updateSummaries();

  const friends = new Set((connections ?? []).map(connection => connection.id).filter(Boolean));
  if (!friends.size) return;
  const discover = communities.filter(community => community.id && !community.is_member);
  for (let start = 0; start < discover.length; start += 6) {
    const batch = discover.slice(start, start + 6);
    await Promise.all(batch.map(async community => {
      const members = await api(`${communityPath(community.id)}/members`).catch(() => null);
      if (!members) return;
      const matching = new Set(members.map(member => member.id).filter(id => friends.has(id)));
      friendsByCommunity.set(community.id, matching.size);
    }));
    updateSummaries();
  }
}

async function joinCommunity(community, button) {
  if (!personId) {
    location.href = 'index.html';
    return;
  }
  if (community.is_member || pendingJoins.has(community.id)) return;
  pendingJoins.add(community.id);
  const restoreFocus = document.activeElement === button;
  button.disabled = true;
  button.textContent = 'Unint…';
  try {
    await api(`${communityPath(community.id)}/members/${encodeURIComponent(personId)}`, { method: 'POST' });
    community.is_member = true;
    community.members += 1;
    toast(`T’has unit a ${community.name}.`);
  } catch (err) {
    toast(err.message);
    return;
  } finally {
    pendingJoins.delete(community.id);
    renderCommunities();
    if (restoreFocus && document.activeElement === document.body) {
      const attribute = community.is_member ? 'data-open-community' : 'data-join-community';
      const next = sections.querySelector(`[${attribute}="${CSS.escape(community.id)}"]`);
      (next ?? search).focus();
    }
  }

  const updated = await api(`${communityPath(community.id)}${viewerQuery}`).catch(() => null);
  if (updated?.is_member) {
    community.members = updated.members;
    updateSummaries();
  }
}

async function showDetail(community) {
  const request = ++latestDetailRequest;
  detailTitle.textContent = community.name;
  detailSummary.textContent = [community.activity, community.zone, countLabel(community.members, 'membre', 'membres')]
    .filter(Boolean).join(' · ');
  detailMembers.className = 'empty';
  detailMembers.textContent = 'S’estan carregant els membres…';
  detail.showModal();

  try {
    const members = await api(`${communityPath(community.id)}/members`);
    if (!detail.open || request !== latestDetailRequest) return;
    if (!members.length) {
      detailMembers.textContent = 'Aquesta comunitat encara no té membres.';
      return;
    }
    detailMembers.className = '';
    detailMembers.innerHTML = `
      <ul class="info-box community-list" role="list">
        ${members.map(member => `<li class="info-row">${esc(member.name)}</li>`).join('')}
      </ul>`;
  } catch (err) {
    if (!detail.open || request !== latestDetailRequest) return;
    detailMembers.className = 'error';
    detailMembers.textContent = err.message;
  }
}

search.addEventListener('input', renderCommunities);
sections.addEventListener('click', event => {
  const button = event.target.closest('button[data-open-community], button[data-join-community]');
  if (!button) return;
  const community = communitiesById.get(button.dataset.openCommunity ?? button.dataset.joinCommunity);
  if (!community) return;
  if (button.dataset.openCommunity) showDetail(community);
  else joinCommunity(community, button);
});

async function loadCommunities() {
  try {
    communities = await api(`/communities${viewerQuery}`);
    for (const community of communities) {
      if (community.id) communitiesById.set(community.id, community);
    }
    renderCommunities();
    status.classList.add('hidden');
    sections.classList.remove('hidden');
    if (personId && communities.length) loadPersonalContext();
  } catch (err) {
    status.className = 'error';
    status.textContent = err.message;
  }
}

loadCommunities();
