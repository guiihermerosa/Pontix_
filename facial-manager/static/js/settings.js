/**
 * settings.js — lógica da página de configurações
 * Um único DOMContentLoaded; carregamento de abas via showTab() em app.js
 */

/* ------------------------------------------------------------------ */
/* Init                                                                 */
/* ------------------------------------------------------------------ */
document.addEventListener('DOMContentLoaded', () => {

  /* --- Forms de sistema e sync ------------------------------------ */
  const form = document.getElementById('systemSettingsForm');
  if (form) form.addEventListener('submit', async e => {
    e.preventDefault();
    const btn = form.querySelector('[type=submit]');
    btn.classList.add('loading'); btn.disabled = true;
    const fd   = new FormData(form);
    const data = Object.fromEntries(fd.entries());
    if (!data.device_password)  delete data.device_password;
    if (!data.company_logo_b64) delete data.company_logo_b64;
    try {
      const r = await fetch('/api/settings', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      const d = await r.json();
      if (r.ok) showToast('Configurações salvas!', 'success');
      else showToast(d.detail || 'Erro ao salvar.', 'error');
    } catch { showToast('Erro de comunicação.', 'error'); }
    finally { btn.classList.remove('loading'); btn.disabled = false; }
  });

  const syncForm = document.getElementById('syncSettingsForm');
  if (syncForm) syncForm.addEventListener('submit', async e => {
    e.preventDefault();
    const btn = syncForm.querySelector('[type=submit]');
    btn.classList.add('loading'); btn.disabled = true;
    const fd   = new FormData(syncForm);
    const data = Object.fromEntries(fd.entries());
    try {
      const r = await fetch('/api/settings', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      const d = await r.json();
      if (r.ok) showToast('Configurações de sync salvas!', 'success');
      else showToast(d.detail || 'Erro.', 'error');
    } catch { showToast('Erro de comunicação.', 'error'); }
    finally { btn.classList.remove('loading'); btn.disabled = false; }
  });

  /* --- Form de integração Resend ---------------------------------- */
  const intForm = document.getElementById('integrationForm');
  if (intForm) intForm.addEventListener('submit', async e => {
    e.preventDefault();
    const btn = intForm.querySelector('[type=submit]');
    btn.classList.add('loading'); btn.disabled = true;
    const fd   = new FormData(intForm);
    const data = Object.fromEntries(fd.entries());
    if (!data.resend_api_key) delete data.resend_api_key;
    try {
      const r = await fetch('/api/email/integration', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      const d = await r.json();
      if (r.ok) { showToast('Integração salva!', 'success'); loadIntegration(); }
      else showToast(d.detail || 'Erro ao salvar.', 'error');
    } catch { showToast('Erro de comunicação.', 'error'); }
    finally { btn.classList.remove('loading'); btn.disabled = false; }
  });

  /* --- Form de agendamento --------------------------------------- */
  const schForm = document.getElementById('scheduleForm');
  if (schForm) schForm.addEventListener('submit', async e => {
    e.preventDefault();
    const btn = schForm.querySelector('[type=submit]');
    btn.classList.add('loading'); btn.disabled = true;
    const fd   = new FormData(schForm);
    const data = {
      email_send_day:     parseInt(fd.get('email_send_day')) || 1,
      email_send_enabled: fd.get('email_send_enabled') === 'true',
    };
    try {
      const r = await fetch('/api/email/schedule', {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data),
      });
      const d = await r.json();
      if (r.ok) showToast('Agendamento salvo!', 'success');
      else showToast(d.detail || 'Erro.', 'error');
    } catch { showToast('Erro de comunicação.', 'error'); }
    finally { btn.classList.remove('loading'); btn.disabled = false; }
  });

  /* --- Inits de página ------------------------------------------- */
  loadDevLocal();
  loadLogoPreview();
  maskCnpj();

  // Preenche ano/mês atual no painel de envio
  const today  = new Date();
  const srYear  = document.getElementById('sr_year');
  const srMonth = document.getElementById('sr_month');
  if (srYear)  srYear.value  = today.getFullYear();
  if (srMonth) srMonth.value = today.getMonth() + 1;
});


/* ------------------------------------------------------------------ */
/* Teste de conexão                                                     */
/* ------------------------------------------------------------------ */
async function testConnection() {
  const result = document.getElementById('connectionResult');
  result.textContent = 'Testando…';
  result.className = 'connection-result';
  const body = {};
  const hostEl    = document.getElementById('s_host');
  const portEl    = document.getElementById('s_port');
  const passEl    = document.getElementById('s_password');
  const timeoutEl = document.getElementById('s_timeout');
  if (hostEl?.value)    body.device_host     = hostEl.value.trim();
  if (portEl?.value)    body.device_port     = portEl.value;
  if (passEl?.value)    body.device_password = passEl.value;
  if (timeoutEl?.value) body.device_timeout  = timeoutEl.value;
  try {
    const r = await fetch('/api/settings/test-connection', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    const d = await r.json();
    if (d.connected) {
      result.className = 'connection-result success';
      result.textContent = `✓ Conectado · IP: ${d.host} · ${d.response_time_ms ? Math.round(d.response_time_ms) + ' ms' : ''}`;
      showToast('Pontix conectado!', 'success');
    } else {
      result.className = 'connection-result error';
      result.textContent = `✕ ${d.error || 'Offline'}`;
      showToast('Dispositivo offline: ' + (d.error || ''), 'error');
    }
  } catch (e) {
    result.className = 'connection-result error';
    result.textContent = '✕ Falha na comunicação com o servidor';
    showToast('Erro: ' + e.message, 'error');
  }
}


/* ------------------------------------------------------------------ */
/* Device — configurações locais                                        */
/* ------------------------------------------------------------------ */
async function loadDevLocal() {
  const el = document.getElementById('devLocalContent');
  if (!el) return;
  el.innerHTML = '<p class="text-muted text-sm">Carregando…</p>';
  try {
    const r = await fetch('/api/device/local-settings');
    if (!r.ok) throw new Error((await r.json()).detail);
    const d = await r.json();
    let data = (d?.data && typeof d.data === 'object' && !Array.isArray(d.data)) ? d.data : d;
    renderJsonAsForm('devLocalContent', data, 'local_');
  } catch (e) { el.innerHTML = `<p class="text-danger text-sm">Erro: ${e.message}</p>`; }
}

async function saveDevLocal() {
  try {
    const data = collectFormValues('devLocalContent', 'local_');
    const r = await fetch('/api/device/local-settings', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!r.ok) throw new Error((await r.json()).detail);
    showToast('Configurações locais salvas no device!', 'success');
  } catch (e) { showToast('Erro: ' + e.message, 'error'); }
}

async function loadDevIdentify() {
  const el = document.getElementById('devIdentifyContent');
  el.innerHTML = '<p class="text-muted text-sm">Carregando…</p>';
  try {
    const r = await fetch('/api/device/identify-settings');
    if (!r.ok) throw new Error((await r.json()).detail);
    const d = await r.json();
    renderJsonAsForm('devIdentifyContent', (d?.data && typeof d.data === 'object') ? d.data : d, 'id_');
  } catch (e) { el.innerHTML = `<p class="text-danger text-sm">Erro: ${e.message}</p>`; }
}

async function saveDevIdentify() {
  try {
    const data = collectFormValues('devIdentifyContent', 'id_');
    const r = await fetch('/api/device/identify-settings', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!r.ok) throw new Error((await r.json()).detail);
    showToast('Configurações de reconhecimento salvas!', 'success');
  } catch (e) { showToast('Erro: ' + e.message, 'error'); }
}

async function loadDevAccess() {
  const el = document.getElementById('devAccessContent');
  el.innerHTML = '<p class="text-muted text-sm">Carregando…</p>';
  try {
    const r = await fetch('/api/device/access-control');
    if (!r.ok) throw new Error((await r.json()).detail);
    const d = await r.json();
    renderJsonAsForm('devAccessContent', (d?.data && typeof d.data === 'object') ? d.data : d, 'ac_');
  } catch (e) { el.innerHTML = `<p class="text-danger text-sm">Erro: ${e.message}</p>`; }
}

async function saveDevAccess() {
  try {
    const data = collectFormValues('devAccessContent', 'ac_');
    const r = await fetch('/api/device/access-control', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!r.ok) throw new Error((await r.json()).detail);
    showToast('Controle de acesso salvo!', 'success');
  } catch (e) { showToast('Erro: ' + e.message, 'error'); }
}

async function loadDevShifts() {
  const el = document.getElementById('devShiftsContent');
  el.innerHTML = '<p class="text-muted text-sm">Carregando…</p>';
  try {
    const r = await fetch('/api/device/shifts');
    if (!r.ok) throw new Error((await r.json()).detail);
    const d = await r.json();
    const shifts = d.data || [];
    if (!shifts.length) { el.innerHTML = '<p class="text-muted text-sm">Nenhuma jornada encontrada.</p>'; return; }
    let html = '<div class="table-wrapper"><table class="table"><thead><tr><th>#</th><th>Nome</th><th>T1 Ent</th><th>T1 Saí</th><th>T2 Ent</th><th>T2 Saí</th><th>T3 Ent</th><th>T3 Saí</th><th>Cruzamento</th><th>Ações</th></tr></thead><tbody>';
    for (const s of shifts) {
      html += `<tr>
        <td>${s.shift_no}</td>
        <td><input class="form-input" style="min-width:90px" value="${_esc(s.shift_name)}"
                   onchange="updateShiftField(${s.shift_no},'shift_name',this.value)"/></td>
        <td><input class="form-input" style="width:70px" type="time" value="${s.shift_t1}"
                   onchange="updateShiftField(${s.shift_no},'shift_t1',this.value)"/></td>
        <td><input class="form-input" style="width:70px" type="time" value="${s.shift_t2}"
                   onchange="updateShiftField(${s.shift_no},'shift_t2',this.value)"/></td>
        <td><input class="form-input" style="width:70px" type="time" value="${s.shift_t3}"
                   onchange="updateShiftField(${s.shift_no},'shift_t3',this.value)"/></td>
        <td><input class="form-input" style="width:70px" type="time" value="${s.shift_t4}"
                   onchange="updateShiftField(${s.shift_no},'shift_t4',this.value)"/></td>
        <td><input class="form-input" style="width:70px" type="time" value="${s.shift_t5}"
                   onchange="updateShiftField(${s.shift_no},'shift_t5',this.value)"/></td>
        <td><input class="form-input" style="width:70px" type="time" value="${s.shift_t6}"
                   onchange="updateShiftField(${s.shift_no},'shift_t6',this.value)"/></td>
        <td><input class="form-input" style="width:70px" type="time" value="${s.shift_across_t}"
                   onchange="updateShiftField(${s.shift_no},'shift_across_t',this.value)"/></td>
        <td><button class="btn btn-primary btn-sm" onclick="saveShift(${s.shift_no})">Salvar</button></td>
      </tr>`;
    }
    html += '</tbody></table></div>';
    // guarda dados em memória para edição
    window._shiftsData = {};
    for (const s of shifts) window._shiftsData[s.shift_no] = { ...s };
    el.innerHTML = html;
  } catch (e) { el.innerHTML = `<p class="text-danger text-sm">Erro: ${e.message}</p>`; }
}

function updateShiftField(shiftNo, field, value) {
  if (!window._shiftsData) window._shiftsData = {};
  if (!window._shiftsData[shiftNo]) window._shiftsData[shiftNo] = { shift_no: shiftNo };
  window._shiftsData[shiftNo][field] = value;
}

async function saveShift(shiftNo) {
  const data = window._shiftsData?.[shiftNo];
  if (!data) { showToast('Dados do turno não encontrados.', 'error'); return; }
  try {
    const r = await fetch(`/api/device/shifts/${shiftNo}`, {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const d = await r.json();
    if (r.ok) showToast(`Turno ${shiftNo} salvo!`, 'success');
    else showToast(d.detail || 'Erro ao salvar turno.', 'error');
  } catch (e) { showToast('Erro: ' + e.message, 'error'); }
}

async function loadDevRules() {
  const el = document.getElementById('devRulesContent');
  el.innerHTML = '<p class="text-muted text-sm">Carregando…</p>';
  try {
    const r = await fetch('/api/device/law-rules');
    if (!r.ok) throw new Error((await r.json()).detail);
    const d = await r.json();
    renderJsonAsForm('devRulesContent', (d?.data && typeof d.data === 'object') ? d.data : d, 'rule_');
  } catch (e) { el.innerHTML = `<p class="text-danger text-sm">Erro: ${e.message}</p>`; }
}

async function saveDevRules() {
  try {
    const data = collectFormValues('devRulesContent', 'rule_');
    const r = await fetch('/api/device/law-rules', {
      method: 'PUT', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!r.ok) throw new Error((await r.json()).detail);
    showToast('Regras trabalhistas salvas!', 'success');
  } catch (e) { showToast('Erro: ' + e.message, 'error'); }
}

async function loadDevHolidays() {
  const el = document.getElementById('devHolidaysContent');
  el.innerHTML = '<p class="text-muted text-sm">Carregando…</p>';
  try {
    const r = await fetch('/api/device/holidays');
    if (!r.ok) throw new Error((await r.json()).detail);
    const d = await r.json();
    const holidays = d.data || [];
    const active = holidays.filter(h => h.openHolidayName);
    if (!active.length) { el.innerHTML = '<p class="text-muted text-sm">Nenhum feriado configurado no device.</p>'; return; }
    let html = '<div class="table-wrapper"><table class="table"><thead><tr><th>#</th><th>Nome</th><th>Início</th><th>Fim</th><th>Calendário</th></tr></thead><tbody>';
    for (const h of active) {
      html += `<tr><td>${h.openHolidayNum}</td><td>${_esc(h.openHolidayName)}</td>
               <td>${h.openHolidayStart}</td><td>${h.openHolidayEnd}</td>
               <td>${h.gregorian_calendar ? 'Gregoriano' : 'Lunar'}</td></tr>`;
    }
    html += '</tbody></table></div>';
    el.innerHTML = html;
  } catch (e) { el.innerHTML = `<p class="text-danger text-sm">Erro: ${e.message}</p>`; }
}


/* ------------------------------------------------------------------ */
/* Rede                                                                 */
/* ------------------------------------------------------------------ */
async function loadNetworkInfo() {
  const el = document.getElementById('networkContent');
  el.innerHTML = '<p class="text-muted text-sm">Carregando…</p>';
  try {
    const [ip, wifi] = await Promise.all([
      fetch('/api/device/network/ip').then(r => r.json()),
      fetch('/api/device/network/wifi').then(r => r.json()),
    ]);
    const fields = { ...ip, ...wifi };
    let html = '<div class="form-grid">';
    for (const [k, v] of Object.entries(fields)) {
      if (typeof v === 'object') continue;
      html += `<div class="form-group"><label>${k.replace(/_/g,' ')}</label>
               <input class="form-input" value="${_esc(String(v ?? ''))}" readonly /></div>`;
    }
    html += '</div>';
    el.innerHTML = html;
  } catch (e) { el.innerHTML = `<p class="text-danger text-sm">Erro: ${e.message}</p>`; }
}

async function scanWifi() {
  const el = document.getElementById('wifiContent');
  el.innerHTML = '<p class="text-muted text-sm">Escaneando…</p>';
  try {
    const r = await fetch('/api/device/network/wifi-scan');
    if (!r.ok) throw new Error((await r.json()).detail);
    const networks = await r.json();
    if (!networks.length) { el.innerHTML = '<p class="text-muted text-sm">Nenhuma rede encontrada.</p>'; return; }
    let html = '<div class="table-wrapper"><table class="table"><thead><tr><th>SSID</th><th>Sinal</th><th>Segurança</th><th>Canal</th></tr></thead><tbody>';
    for (const n of networks) {
      html += `<tr><td>${_esc(n.ssid)}</td><td>${n.strength} dBm</td><td>${_esc(n.encryption)}</td><td>${n.channel}</td></tr>`;
    }
    html += '</tbody></table></div>';
    el.innerHTML = html;
  } catch (e) { el.innerHTML = `<p class="text-danger text-sm">Erro: ${e.message}</p>`; }
}

async function loadServerSettings() {
  const el = document.getElementById('serverContent');
  el.innerHTML = '<p class="text-muted text-sm">Carregando…</p>';
  try {
    const r = await fetch('/api/device/server-settings');
    if (!r.ok) throw new Error((await r.json()).detail);
    const d = await r.json();
    let html = '<div class="form-grid">';
    for (const [k, v] of Object.entries(d)) {
      if (typeof v === 'object') continue;
      html += `<div class="form-group"><label>${k.replace(/_/g,' ')}</label>
               <input class="form-input" value="${_esc(String(v ?? ''))}" readonly /></div>`;
    }
    html += '</div>';
    el.innerHTML = html;
  } catch (e) { el.innerHTML = `<p class="text-danger text-sm">Erro: ${e.message}</p>`; }
}


/* ------------------------------------------------------------------ */
/* Logs de sincronização                                               */
/* ------------------------------------------------------------------ */
async function loadSyncLogs() {
  const el = document.getElementById('syncLogsContent');
  el.innerHTML = '<p class="text-muted text-sm">Carregando…</p>';
  try {
    const r = await fetch('/api/sync/logs?page_size=20');
    const d = await r.json();
    if (!d.items?.length) { el.innerHTML = '<p class="text-muted text-sm">Nenhum log de sync ainda.</p>'; return; }
    let html = '<div class="table-wrapper"><table class="table"><thead><tr><th>Início</th><th>Duração</th><th>Status</th><th>Func.</th><th>Marc.</th><th>Erros</th><th>Resumo</th></tr></thead><tbody>';
    for (const log of d.items) {
      const start    = log.started_at ? new Date(log.started_at).toLocaleString('pt-BR') : '—';
      const duration = log.started_at && log.finished_at
        ? Math.round((new Date(log.finished_at) - new Date(log.started_at)) / 1000) + 's' : '—';
      const badge    = log.success ? 'badge-success' : 'badge-danger';
      html += `<tr>
        <td class="text-sm">${start}</td><td class="text-sm">${duration}</td>
        <td><span class="badge ${badge}">${log.success ? 'OK' : 'ERRO'}</span></td>
        <td>${log.employees_synced}</td><td>${log.attendance_synced}</td><td>${log.errors_count}</td>
        <td class="text-sm text-muted">${_esc(log.summary || '—')}</td>
      </tr>`;
    }
    html += '</tbody></table></div>';
    el.innerHTML = html;
  } catch (e) { el.innerHTML = `<p class="text-danger text-sm">Erro: ${e.message}</p>`; }
}


/* ------------------------------------------------------------------ */
/* Empresa — logo                                                       */
/* ------------------------------------------------------------------ */
async function loadLogoPreview() {
  try {
    const r = await fetch('/api/settings/company-logo');
    if (!r.ok) return;
    const d = await r.json();
    if (d.company_logo_b64) showLogoPreview(d.company_logo_b64);
  } catch { /* silencioso */ }
}

function showLogoPreview(b64) {
  const src  = b64.startsWith('data:') ? b64 : `data:image/png;base64,${b64}`;
  const img  = document.getElementById('logoPreviewImg');
  const box  = document.getElementById('logoPreviewBox');
  const upld = document.getElementById('logoUploadBox');
  if (!img || !box || !upld) return;
  img.src = src;
  box.style.display  = 'block';
  upld.style.display = 'none';
}

function hideLogoPreview() {
  const box  = document.getElementById('logoPreviewBox');
  const upld = document.getElementById('logoUploadBox');
  const name = document.getElementById('logoFileName');
  if (box)  box.style.display  = 'none';
  if (upld) upld.style.display = 'block';
  if (name) name.textContent   = '';
  const hidden = document.getElementById('s_logo_b64_hidden');
  if (hidden) hidden.value = '';
}

function handleLogoUpload(input) {
  const file = input.files[0];
  if (!file) return;
  if (file.size > 500 * 1024) { showToast('Logo muito grande (máx 500 KB).', 'error'); input.value = ''; return; }
  const nameEl = document.getElementById('logoFileName');
  if (nameEl) nameEl.textContent = file.name;
  const reader = new FileReader();
  reader.onload = e => {
    const b64 = e.target.result;
    let hidden = document.getElementById('s_logo_b64_hidden');
    if (!hidden) {
      hidden = document.createElement('input');
      hidden.type = 'hidden'; hidden.id = 's_logo_b64_hidden'; hidden.name = 'company_logo_b64';
      document.getElementById('systemSettingsForm')?.appendChild(hidden);
    }
    hidden.value = b64;
    showLogoPreview(b64);
    showToast('Logo carregado — salve as configurações para confirmar.', 'success');
  };
  reader.readAsDataURL(file);
}

async function removeLogo() {
  try {
    const r = await fetch('/api/settings/company-logo', { method: 'DELETE' });
    if (!r.ok) throw new Error((await r.json()).detail);
    hideLogoPreview();
    showToast('Logo removido.', 'success');
  } catch (e) { showToast('Erro ao remover logo: ' + e.message, 'error'); }
}

function maskCnpj() {
  const el = document.getElementById('s_company_cnpj');
  if (!el) return;
  el.addEventListener('input', () => {
    let v = el.value.replace(/\D/g, '').slice(0, 14);
    if (v.length > 12) v = v.replace(/^(\d{2})(\d{3})(\d{3})(\d{4})(\d{0,2})/, '$1.$2.$3/$4-$5');
    else if (v.length > 8) v = v.replace(/^(\d{2})(\d{3})(\d{3})(\d{0,4})/, '$1.$2.$3/$4');
    else if (v.length > 5) v = v.replace(/^(\d{2})(\d{3})(\d{0,3})/, '$1.$2.$3');
    else if (v.length > 2) v = v.replace(/^(\d{2})(\d{0,3})/, '$1.$2');
    el.value = v;
  });
}


/* ================================================================== */
/* TAB: Integrações — Resend                                          */
/* ================================================================== */
async function loadIntegration() {
  try {
    const r = await fetch('/api/email/integration');
    if (!r.ok) return;
    const d = await r.json();
    const hint = document.getElementById('apiKeyHint');
    if (hint) {
      hint.textContent = d.resend_api_key_set
        ? `✓ Chave definida (${d.resend_api_key_hint})` : 'Nenhuma chave configurada';
      hint.style.color = d.resend_api_key_set ? '#059669' : '#6b7280';
    }
    const fromName  = document.getElementById('i_from_name');
    const fromEmail = document.getElementById('i_from_email');
    if (fromName  && d.resend_from_name)  fromName.value  = d.resend_from_name;
    if (fromEmail && d.resend_from_email) fromEmail.value = d.resend_from_email;
  } catch { /* silencioso */ }
}

function toggleApiKeyVisibility() {
  const inp = document.getElementById('i_api_key');
  if (!inp) return;
  inp.type = inp.type === 'password' ? 'text' : 'password';
}

async function sendTestEmail() {
  const emailEl  = document.getElementById('i_test_email');
  const resultEl = document.getElementById('testEmailResult');
  const btn      = document.getElementById('testEmailBtn');
  if (!emailEl?.value.trim()) { showToast('Informe um email para teste.', 'error'); return; }
  btn.classList.add('loading'); btn.disabled = true;
  resultEl.innerHTML = '<span class="text-muted text-sm">Enviando…</span>';
  try {
    const r = await fetch('/api/email/test', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: emailEl.value.trim() }),
    });
    const d = await r.json();
    if (d.success) {
      resultEl.innerHTML = `<span style="color:#059669">✓ ${_esc(d.message)}</span>`;
      showToast('Email de teste enviado!', 'success');
    } else {
      resultEl.innerHTML = `<span style="color:#dc2626">✕ ${_esc(d.error || 'Falha no envio')}</span>`;
      showToast('Falha: ' + (d.error || 'verifique a API key'), 'error');
    }
  } catch (e) {
    resultEl.innerHTML = `<span style="color:#dc2626">✕ Erro de comunicação</span>`;
    showToast('Erro: ' + e.message, 'error');
  } finally { btn.classList.remove('loading'); btn.disabled = false; }
}


/* ================================================================== */
/* TAB: Destinatários                                                  */
/* ================================================================== */
async function loadRecipients() {
  const el = document.getElementById('recipientsTable');
  if (!el) return;
  el.innerHTML = '<p class="text-muted text-sm">Carregando…</p>';
  try {
    const r = await fetch('/api/email/recipients');
    if (!r.ok) throw new Error((await r.json()).detail);
    const list = await r.json();
    if (!list.length) {
      el.innerHTML = '<p class="text-muted text-sm">Nenhum destinatário cadastrado. Clique em "+ Adicionar".</p>';
      return;
    }
    const roleColors = { owner: '#7c3aed', accounting: '#0369a1', other: '#374151' };
    let html = `<div class="table-wrapper"><table class="table">
      <thead><tr><th>Nome</th><th>Email</th><th>Tipo</th><th style="text-align:center">Ativo</th><th style="text-align:center">Ações</th></tr></thead><tbody>`;
    for (const rec of list) {
      const color  = roleColors[rec.role] || '#374151';
      const toggle = rec.active
        ? `<button class="btn btn-sm" style="background:#ecfdf5;color:#059669;border:1px solid #a7f3d0"
                   onclick="toggleRecipient(${rec.id})">✓ Ativo</button>`
        : `<button class="btn btn-sm" style="background:#fef2f2;color:#dc2626;border:1px solid #fecaca"
                   onclick="toggleRecipient(${rec.id})">✕ Inativo</button>`;
      html += `<tr id="rec-row-${rec.id}">
        <td>${_esc(rec.name)}</td>
        <td class="text-sm">${_esc(rec.email)}</td>
        <td><span style="font-size:12px;font-weight:600;color:${color}">${_esc(rec.role_label)}</span></td>
        <td style="text-align:center">${toggle}</td>
        <td style="text-align:center">
          <button class="btn btn-ghost btn-sm" style="color:#dc2626"
                  onclick="deleteRecipient(${rec.id},'${_esc(rec.email)}')">🗑</button>
        </td></tr>`;
    }
    html += '</tbody></table></div>';
    el.innerHTML = html;
  } catch (e) { el.innerHTML = `<p class="text-danger text-sm">Erro: ${e.message}</p>`; }
}

function openAddRecipient() {
  document.getElementById('addRecipientPanel')?.classList.remove('hidden');
  document.getElementById('r_name')?.focus();
}

function closeAddRecipient() {
  document.getElementById('addRecipientPanel')?.classList.add('hidden');
  document.getElementById('addRecipientForm')?.reset();
}

async function submitAddRecipient(e) {
  e.preventDefault();
  const btn  = e.target.querySelector('[type=submit]');
  btn.classList.add('loading'); btn.disabled = true;
  const data = {
    name:  document.getElementById('r_name').value.trim(),
    email: document.getElementById('r_email').value.trim(),
    role:  document.getElementById('r_role').value,
  };
  try {
    const r = await fetch('/api/email/recipients', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    const d = await r.json();
    if (r.ok) { showToast('Destinatário adicionado!', 'success'); closeAddRecipient(); loadRecipients(); }
    else showToast(d.detail || 'Erro ao salvar.', 'error');
  } catch { showToast('Erro de comunicação.', 'error'); }
  finally { btn.classList.remove('loading'); btn.disabled = false; }
}

async function toggleRecipient(id) {
  try {
    const r = await fetch(`/api/email/recipients/${id}/toggle`, { method: 'PATCH' });
    if (r.ok) loadRecipients();
    else showToast((await r.json()).detail || 'Erro.', 'error');
  } catch { showToast('Erro de comunicação.', 'error'); }
}

async function deleteRecipient(id, email) {
  if (!confirm(`Remover ${email}?`)) return;
  try {
    const r = await fetch(`/api/email/recipients/${id}`, { method: 'DELETE' });
    if (r.ok) { showToast('Destinatário removido.', 'success'); loadRecipients(); }
    else showToast((await r.json()).detail || 'Erro.', 'error');
  } catch { showToast('Erro de comunicação.', 'error'); }
}


/* ================================================================== */
/* TAB: Relatórios por Email                                           */
/* ================================================================== */
async function loadSchedule() {
  try {
    const r = await fetch('/api/email/schedule');
    if (!r.ok) return;
    const d = await r.json();
    const dayEl = document.getElementById('sc_day');
    const enaEl = document.getElementById('sc_enabled');
    if (dayEl) dayEl.value = d.email_send_day;
    if (enaEl) enaEl.value = d.email_send_enabled ? 'true' : 'false';
  } catch { /* silencioso */ }
}

async function sendReportNow() {
  const btn      = document.getElementById('sendReportBtn');
  const resultEl = document.getElementById('sendReportResult');
  const month    = parseInt(document.getElementById('sr_month')?.value);
  const year     = parseInt(document.getElementById('sr_year')?.value);
  btn.classList.add('loading'); btn.disabled = true;
  resultEl.innerHTML = '<span class="text-muted text-sm">Enviando relatório…</span>';
  try {
    const r = await fetch('/api/email/send-report', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ month, year }),
    });
    const d = await r.json();
    if (d.success) {
      const tos = (d.sent_to || []).join(', ');
      resultEl.innerHTML = `<div style="color:#059669;font-size:13px">
        ✓ ${_esc(d.message)}<br><span style="color:#6b7280">Enviado para: ${_esc(tos)}</span></div>`;
      showToast(d.message, 'success');
    } else {
      const errs = (d.errors || []).map(_esc).join(' | ');
      resultEl.innerHTML = `<div style="color:#dc2626;font-size:13px">
        ✕ ${_esc(d.message || 'Falha no envio')}<br><span style="color:#6b7280">${errs}</span></div>`;
      showToast(d.message || 'Falha no envio', 'error');
    }
  } catch (e) {
    resultEl.innerHTML = `<span style="color:#dc2626">✕ Erro: ${_esc(e.message)}</span>`;
    showToast('Erro: ' + e.message, 'error');
  } finally { btn.classList.remove('loading'); btn.disabled = false; }
}


/* ================================================================== */
/* runSyncNow — disparo manual do ciclo de sync                        */
/* ================================================================== */
async function runSyncNow() {
  const btn = document.getElementById('syncNowBtn');
  if (btn) { btn.classList.add('loading'); btn.disabled = true; }
  try {
    const r = await fetch('/api/sync/run-now', { method: 'POST' });
    const d = await r.json();
    showToast(d.summary || 'Sincronização concluída.', d.success ? 'success' : 'error');
  } catch (e) { showToast('Erro: ' + e.message, 'error'); }
  finally { if (btn) { btn.classList.remove('loading'); btn.disabled = false; } }
}


/* ================================================================== */
/* Utilitário — escape HTML                                            */
/* ================================================================== */
function _esc(str) {
  return String(str ?? '')
    .replace(/&/g,'&amp;').replace(/</g,'&lt;')
    .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
