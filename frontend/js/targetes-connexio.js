export function connectionIdentity(person) {
  return `<div class="connection-identity">
    <span class="avatar ${avatarClass(person.name)}" aria-hidden="true">${esc(initials(person.name))}</span>
    <div class="event-body">
      <strong class="event-title">${esc(person.name)}</strong>
      ${person.zone ? `<span class="event-meta">${esc(person.zone)}</span>` : ''}
    </div>
  </div>`;
}
