import { connectionIdentity } from './targetes-connexio.js';

const user = requireUser();
renderNav('afins');
document.getElementById('back').innerHTML = icon('back');

const receivedList = document.getElementById('received-requests');
const sentList = document.getElementById('sent-requests');
const errorBox = document.getElementById('requests-error');
const retry = document.getElementById('requests-retry');
const requestsPath = `/persons/${encodeURIComponent(user.id)}/connection-requests`;
const noReceived = '<div class="empty">No tens sol·licituds rebudes pendents.</div>';

function requestCard(person, received) {
  return `<article class="event-card connection-card" data-request-id="${esc(person.id)}">
    ${connectionIdentity(person)}
    <div class="connection-buttons">
      ${received ? `
        <button class="btn btn-small btn-primary" type="button" data-request-action="accept">Acceptar</button>
        <button class="btn btn-small btn-secondary" type="button" data-request-action="reject">Rebutjar</button>
      ` : '<span class="chip">Pendent</span>'}
    </div>
  </article>`;
}

async function loadRequests() {
  retry.classList.add('hidden');
  errorBox.classList.add('hidden');
  receivedList.textContent = 'Carregant…';
  sentList.textContent = 'Carregant…';
  try {
    const { received, sent } = await api(requestsPath);
    receivedList.innerHTML = received.length ? received.map(person => requestCard(person, true)).join('') : noReceived;
    sentList.innerHTML = sent.length ? sent.map(person => requestCard(person, false)).join('')
      : '<div class="empty">No tens sol·licituds enviades pendents.</div>';
  } catch (error) {
    receivedList.textContent = '';
    sentList.textContent = '';
    errorBox.textContent = error.message;
    errorBox.classList.remove('hidden');
    retry.classList.remove('hidden');
  }
}

receivedList.addEventListener('click', async event => {
  const button = event.target.closest('button[data-request-action]');
  if (!button || button.disabled) return;
  const card = button.closest('[data-request-id]');
  const controls = card.querySelectorAll('button');
  const path = `${requestsPath}/${encodeURIComponent(card.dataset.requestId)}`;
  const accept = button.dataset.requestAction === 'accept';
  for (const control of controls) control.disabled = true;
  try {
    await api(accept ? path + '/accept' : path, { method: accept ? 'POST' : 'DELETE' });
    card.remove();
    if (!receivedList.children.length) receivedList.innerHTML = noReceived;
    document.getElementById('received-heading').focus({ preventScroll: true });
    toast(accept ? 'Sol·licitud acceptada.' : 'Sol·licitud rebutjada.');
  } catch (error) {
    for (const control of controls) control.disabled = false;
    button.focus();
    toast(error.message);
  }
});
retry.addEventListener('click', loadRequests);
loadRequests();
