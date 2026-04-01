chrome.runtime.sendMessage({ type: 'getStatus' }, (data) => {
  const statusEl = document.getElementById('status');
  const statsEl = document.getElementById('stats');

  if (data?.connected) {
    statusEl.className = 'status connected';
    statusEl.textContent = '✅ Connected — Token captured';
  } else {
    statusEl.className = 'status disconnected';
    statusEl.textContent = '❌ No token — Open Google Labs';
  }

  const tokenAge = data?.tokenAge ? `${Math.round(data.tokenAge / 60000)}m ago` : '—';
  statsEl.innerHTML = `
    <div class="stat"><span class="label">Token age</span><span class="value">${tokenAge}</span></div>
    <div class="stat"><span class="label">Requests</span><span class="value">${data?.requestCount || 0}</span></div>
    <div class="stat"><span class="label">Last error</span><span class="value">${data?.lastError || '—'}</span></div>
  `;
});
