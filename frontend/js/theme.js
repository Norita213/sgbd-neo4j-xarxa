// Aplica el tema (fosc o clar) abans de pintar la pàgina, per evitar un parpelleig.
// Va al <head> de totes les pàgines. Per defecte: fosc.
(function () {
  var theme = 'dark';
  try { theme = localStorage.getItem('afinit.theme') || 'dark'; } catch (e) { /* sense emmagatzematge */ }
  document.documentElement.setAttribute('data-theme', theme);
})();
