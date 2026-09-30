/**
 * app.js — utilitários globais do Pontix
 * Toast, Modal, Sidebar, Sync button, Device status
 */

/* ------------------------------------------------------------------ */
/* Toast                                                               */
/* ------------------------------------------------------------------ */
function showToast(message, type = 'info', duration = 3500) {
  const container = document.getElementById('toastContainer');
  if (!container) return;

  const icons = { success: '✓', error: '✕', info: 'ℹ', warning: '⚠' };
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `<span>${icons[type] || ''}</span><span>${message}</span>`;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transition = 'opacity .3s';
    setTimeout(() => toast.remove(), 300);
  }, duration);
}

/* ------------------------------------------------------------------ */
/* Modal                                                               */
/* ------------------------------------------------------------------ */
function openModal(id) {
  const modal   = document.getElementById(id);
  const overlay = document.getElementById('modalOverlay');
  if (!modal) return;
  modal.classList.add('open');
  overlay.classList.add('visible');
  document.body.style.overflow = 'hidden';
}

function closeModal(id) {
  const modal   = document.getElementById(id);
  const overlay = document.getElementById('modalOverlay');
  if (!modal) return;
  modal.classList.remove('open');
  overlay.classList.remove('visible');
  document.body.style.overflow = '';
}

// Fechar ao clicar no overlay
document.addEventListener('DOMContentLoaded', () => {
  const overlay = document.getElementById('modalOverlay');
  if (overlay) overlay.addEventListener('click', () => {
    document.querySelectorAll('.modal.open').forEach(m => closeModal(m.id));
  });

  // ESC fecha modal
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') document.querySelectorAll('.modal.open').forEach(m => closeModal(m.id));
  });
});

/* ------------------------------------------------------------------ */
/* Sidebar toggle (mobile)                                             */
/* ------------------------------------------------------------------ */
document.addEventListener('DOMContentLoaded', () => {
  const btn     = document.getElementById('sidebarToggle');
  const sidebar = document.getElementById('sidebar');
  if (!btn || !sidebar) return;

  btn.addEventListener('click', () => {
    sidebar.classList.toggle('open');
  });

  // Fecha ao clicar fora no mobile
  document.addEventListener('click', e => {
    if (window.innerWidth <= 768 &&
        sidebar.classList.contains('open') &&
        !sidebar.contains(e.target) &&
        !btn.contains(e.target)) {
      sidebar.classList.remove('open');
    }
  });
});

/* ------------------------------------------------------------------ */
/* Botão Sincronizar agora (topbar)                                    */
/* ------------------------------------------------------------------ */
document.addEventListener('DOMContentLoaded', () => {
  const btn  = document.getElementById('syncNowBtn');
  const icon = document.getElementById('syncIcon');
  if (!btn) return;

  btn.addEventListener('click', async () => {
    btn.classList.add('loading');
    btn.disabled = true;
    if (icon) icon.classList.add('spinning');

    try {
      const r = await fetch('/api/sync/run', { method: 'POST' });
      const d = await r.json();
      if (d.success) {
        showToast(d.summary || 'Sincronização concluída.', 'success');
      } else {
        showToast(d.summary || 'Sincronização com erros.', 'warning');
      }
    } catch {
      showToast('Falha ao comunicar com o servidor.', 'error');
    } finally {
      btn.classList.remove('loading');
      btn.disabled = false;
      if (icon) icon.classList.remove('spinning');
    }
  });
});

/* ------------------------------------------------------------------ */
/* Status do device na sidebar (polling leve)                          */
/* ------------------------------------------------------------------ */
async function updateSidebarStatus() {
  try {
    const d = await fetch('/api/device/status').then(r => r.json());
    const dot = document.getElementById('statusDot');
    const txt = document.getElementById('statusText');
    if (!dot) return;

    if (d.device_online) {
      dot.className = 'status-dot online';
      txt.textContent = d.device_response_time
        ? `Online · ${Math.round(d.device_response_time)} ms`
        : 'Online';
    } else {
      dot.className = 'status-dot offline';
      txt.textContent = 'Offline';
    }
  } catch { /* silencioso */ }
}

document.addEventListener('DOMContentLoaded', () => {
  updateSidebarStatus();
  setInterval(updateSidebarStatus, 20000);
});

/* ------------------------------------------------------------------ */
/* Tabs genérico                                                        */
/* ------------------------------------------------------------------ */
function showTab(panelId, btn) {
  // Desativa todos
  const tabsContainer = btn.closest('.tabs');
  tabsContainer.querySelectorAll('.tab').forEach(t => {
    t.classList.remove('active');
    t.setAttribute('aria-selected', 'false');
  });
  // Esconde todos os painéis irmãos
  const panels = document.querySelectorAll('.tab-panel');
  panels.forEach(p => p.classList.add('hidden'));

  // Ativa
  btn.classList.add('active');
  btn.setAttribute('aria-selected', 'true');
  const panel = document.getElementById(panelId);
  if (panel) panel.classList.remove('hidden');

  // Carrega dados sob demanda para cada aba que precisa
  if (panelId === 'tab-integrations' && typeof loadIntegration === 'function') loadIntegration();
  if (panelId === 'tab-recipients'   && typeof loadRecipients   === 'function') loadRecipients();
  if (panelId === 'tab-email-reports'&& typeof loadSchedule     === 'function') loadSchedule();
}

function showSubTab(panelId, btn) {
  const container = btn.closest('.tabs');
  container.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  btn.closest('.panel').querySelectorAll('.dev-panel').forEach(p => p.classList.add('hidden'));
  btn.classList.add('active');
  const panel = document.getElementById(panelId);
  if (panel) panel.classList.remove('hidden');
}

/* ------------------------------------------------------------------ */
/* Helpers gerais                                                       */
/* ------------------------------------------------------------------ */

/** Renderiza um objeto JSON como campos de formulário leve */
function renderJsonAsForm(containerId, data, prefix = '') {
  const container = document.getElementById(containerId);
  if (!container || data === null || data === undefined) return;

  // Se vier como string (double-encoded), parseia
  if (typeof data === 'string') {
    try { data = JSON.parse(data); } catch { /* mantém como string */ }
  }

  // Se ainda for string ou não for objeto iterável, exibe mensagem amigável
  if (typeof data !== 'object' || Array.isArray(data)) {
    container.innerHTML = `<p class="text-muted text-sm">Dados não disponíveis.</p>`;
    return;
  }

  let html = '<div class="form-grid">';
  for (const [key, val] of Object.entries(data)) {
    if (typeof val === 'object' && val !== null) continue; // skip nested
    const label = key.replace(/_/g, ' ');
    const inputType = typeof val === 'number' ? 'number' : 'text';
    const safeVal = String(val ?? '').replace(/"/g, '&quot;').replace(/</g, '&lt;');
    html += `
      <div class="form-group">
        <label for="${prefix}${key}">${label}</label>
        <input type="${inputType}" id="${prefix}${key}" name="${prefix}${key}"
               value="${safeVal}" class="form-input" />
      </div>`;
  }
  html += '</div>';
  container.innerHTML = html;
}

/** Coleta valores de um form container como objeto */
function collectFormValues(containerId, prefix = '') {
  const container = document.getElementById(containerId);
  if (!container) return {};
  const result = {};
  container.querySelectorAll('input, select, textarea').forEach(el => {
    const key = el.name.replace(prefix, '');
    result[key] = el.type === 'number' ? (parseFloat(el.value) || 0) : el.value;
  });
  return result;
}

/** Wrapper para chamadas fetch com feedback padrão */
async function apiCall(url, options = {}, successMsg = null, errorMsg = null) {
  try {
    const r = await fetch(url, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
    });
    if (!r.ok) {
      const err = await r.json().catch(() => ({ detail: r.statusText }));
      throw new Error(err.detail || r.statusText);
    }
    const data = await r.json();
    if (successMsg) showToast(successMsg, 'success');
    return data;
  } catch (e) {
    showToast(errorMsg || e.message, 'error');
    throw e;
  }
}

/** Sincronizar agora via API (usado em múltiplas páginas) */
async function runSyncNow() {
  showToast('Iniciando sincronização…', 'info', 2000);
  try {
    const d = await fetch('/api/sync/run', { method: 'POST' }).then(r => r.json());
    showToast(d.summary || 'Ciclo concluído.', d.success ? 'success' : 'warning');
  } catch { showToast('Erro ao sincronizar.', 'error'); }
}
