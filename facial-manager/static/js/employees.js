/**
 * employees.js — lógica da página de funcionários
 */

let _editingId = null;

/* ------------------------------------------------------------------ */
/* Abrir / fechar modal                                                 */
/* ------------------------------------------------------------------ */
function openNewEmployeeModal() {
  _editingId = null;
  document.getElementById('modalTitle').textContent = 'Novo Funcionário';
  document.getElementById('employeeForm').reset();
  document.getElementById('empId').value = '';
  document.getElementById('f_userid').readOnly = false;
  openModal('employeeModal');
}

async function editEmployee(id) {
  try {
    const emp = await fetch(`/api/employees/${id}`).then(r => r.json());
    _editingId = id;
    document.getElementById('modalTitle').textContent = 'Editar Funcionário';
    document.getElementById('empId').value     = id;
    document.getElementById('f_userid').value     = emp.userid;
    document.getElementById('f_userid').readOnly  = true;
    document.getElementById('f_name').value       = emp.name || '';
    document.getElementById('f_department').value = emp.department;
    document.getElementById('f_schedule').value   = emp.schedule;
    document.getElementById('f_role').value       = emp.role;
    document.getElementById('f_card').value       = emp.access_card_number || '';
    document.getElementById('f_pass_times').value = emp.pass_times;
    document.getElementById('f_password').value   = '';
    openModal('employeeModal');
  } catch {
    showToast('Erro ao carregar funcionário.', 'error');
  }
}

/* ------------------------------------------------------------------ */
/* Salvar (criar ou editar)                                             */
/* ------------------------------------------------------------------ */
async function saveEmployee() {
  const btn = document.getElementById('saveEmployeeBtn');
  btn.classList.add('loading');
  btn.disabled = true;

  try {
    const photo = document.getElementById('f_photo').files[0];

    if (photo) {
      // Com foto — usa multipart
      const formData = new FormData();
      formData.append('userid',             document.getElementById('f_userid').value.trim());
      formData.append('name',               document.getElementById('f_name').value.trim());
      formData.append('department',         document.getElementById('f_department').value);
      formData.append('schedule',           document.getElementById('f_schedule').value);
      formData.append('role',               document.getElementById('f_role').value);
      formData.append('access_card_number', document.getElementById('f_card').value.trim());
      formData.append('pass_times',         document.getElementById('f_pass_times').value);
      formData.append('userpassword',       document.getElementById('f_password').value);
      formData.append('photo',              photo);

      const url = _editingId ? `/api/employees/${_editingId}` : '/api/employees/with-photo';
      const method = _editingId ? 'PUT' : 'POST';

      if (_editingId) {
        // PUT não aceita multipart — envia JSON e a foto separadamente
        await saveEmployeeJson();
        return;
      }

      const r = await fetch(url, { method, body: formData });
      const d = await r.json();
      if (!r.ok) throw new Error(d.detail || d.message || 'Erro');
      const msg = d.synced
        ? 'Funcionário cadastrado e sincronizado com o device!'
        : `Funcionário cadastrado. ${d.sync_detail ? '⚠ Sync: ' + d.sync_detail : 'Será sincronizado no próximo ciclo.'}`;
      showToast(msg, d.synced ? 'success' : 'warning');
      closeModal('employeeModal');
      setTimeout(() => location.reload(), 1400);

    } else {
      await saveEmployeeJson();
    }

  } catch (e) {
    showToast(e.message || 'Erro ao salvar.', 'error');
  } finally {
    btn.classList.remove('loading');
    btn.disabled = false;
  }
}

async function saveEmployeeJson() {
  const payload = {
    userid:             document.getElementById('f_userid').value.trim(),
    name:               document.getElementById('f_name').value.trim(),
    department:         parseInt(document.getElementById('f_department').value) || 0,
    schedule:           parseInt(document.getElementById('f_schedule').value) || 0,
    role:               parseInt(document.getElementById('f_role').value) || 0,
    access_card_number: document.getElementById('f_card').value.trim(),
    pass_times:         parseInt(document.getElementById('f_pass_times').value),
    userpassword:       document.getElementById('f_password').value,
  };

  const url    = _editingId ? `/api/employees/${_editingId}` : '/api/employees';
  const method = _editingId ? 'PUT' : 'POST';

  const r = await fetch(url, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  const d = await r.json();
  if (!r.ok) throw new Error(d.detail || d.message || 'Erro');

  const label = _editingId ? 'atualizado' : 'cadastrado';
  const msg = d.synced
    ? `Funcionário ${label} e sincronizado com o device!`
    : `Funcionário ${label}. ${d.sync_detail ? '⚠ ' + d.sync_detail : 'Será sincronizado automaticamente.'}`;
  showToast(msg, d.synced ? 'success' : 'warning');
  closeModal('employeeModal');
  setTimeout(() => location.reload(), 1400);
}

/* ------------------------------------------------------------------ */
/* Sincronizar funcionário individual                                   */
/* ------------------------------------------------------------------ */
async function syncEmployee(id) {
  showToast('Sincronizando…', 'info', 1500);
  try {
    const r = await fetch(`/api/employees/${id}/sync`, { method: 'POST' });
    const d = await r.json();
    if (d.success) {
      showToast('Sincronizado com sucesso!', 'success');
      setTimeout(() => location.reload(), 1200);
    } else {
      showToast(d.message || 'Falha na sincronização.', 'error');
    }
  } catch { showToast('Erro de comunicação.', 'error'); }
}

/* ------------------------------------------------------------------ */
/* Importar todos do device                                             */
/* ------------------------------------------------------------------ */
document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('syncAllBtn');
  if (btn) btn.addEventListener('click', async () => {
    btn.classList.add('loading');
    btn.disabled = true;
    showToast('Importando funcionários do device…', 'info');
    try {
      const r = await fetch('/api/employees/sync-all', { method: 'POST' });
      const d = await r.json();
      showToast(
        `Importação concluída: ${d.imported} novos, ${d.updated} atualizados.`,
        d.errors?.length ? 'warning' : 'success'
      );
      setTimeout(() => location.reload(), 1500);
    } catch { showToast('Erro ao importar.', 'error'); }
    finally { btn.classList.remove('loading'); btn.disabled = false; }
  });

  const newBtn = document.getElementById('newEmployeeBtn');
  if (newBtn) newBtn.addEventListener('click', openNewEmployeeModal);

  // Filtro de busca em tempo real (client-side, tabela já carregada)
  const searchInput = document.getElementById('searchInput');
  const syncFilter  = document.getElementById('syncFilter');

  function filterTable() {
    const term   = (searchInput?.value || '').toLowerCase();
    const status = syncFilter?.value || '';
    document.querySelectorAll('#employeeTableBody tr[data-id]').forEach(row => {
      const text   = row.textContent.toLowerCase();
      const badges = row.querySelector('.badge');
      const badgeText = badges ? badges.textContent.trim().toUpperCase() : '';

      const matchSearch = !term || text.includes(term);
      const matchStatus = !status || badgeText.includes({
        PENDING: 'PENDENTE', SUCCESS: 'SINCRON', ERROR: 'ERRO'
      }[status] || status);

      row.style.display = (matchSearch && matchStatus) ? '' : 'none';
    });
  }

  searchInput?.addEventListener('input', filterTable);
  syncFilter?.addEventListener('change', filterTable);
});

/* ------------------------------------------------------------------ */
/* Preview de foto                                                      */
/* ------------------------------------------------------------------ */
function previewPhoto(input) {
  const file    = input.files[0];
  const preview = document.getElementById('photoPreview');
  const wrap    = document.getElementById('photoPreviewWrap');
  const ph      = document.getElementById('photoPlaceholder');

  if (!file) { removePhoto(); return; }

  const reader = new FileReader();
  reader.onload = e => {
    preview.src = e.target.result;
    wrap.style.display = 'flex';
    ph.style.display   = 'none';
  };
  reader.readAsDataURL(file);
}

function removePhoto() {
  const input   = document.getElementById('f_photo');
  const preview = document.getElementById('photoPreview');
  const wrap    = document.getElementById('photoPreviewWrap');
  const ph      = document.getElementById('photoPlaceholder');

  if (input)   { input.value = ''; }
  if (preview) { preview.src = ''; }
  if (wrap)    { wrap.style.display = 'none'; }
  if (ph)      { ph.style.display = 'flex'; }
}

// Drag & drop no upload area
document.addEventListener('DOMContentLoaded', () => {
  const area = document.getElementById('photoUploadArea');
  if (!area) return;

  area.addEventListener('dragover', e => {
    e.preventDefault();
    area.style.borderColor = 'var(--color-primary)';
    area.style.background  = 'var(--color-primary-lt)';
  });
  area.addEventListener('dragleave', () => {
    area.style.borderColor = '';
    area.style.background  = '';
  });
  area.addEventListener('drop', e => {
    e.preventDefault();
    area.style.borderColor = '';
    area.style.background  = '';
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
      const input = document.getElementById('f_photo');
      const dt    = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
      previewPhoto(input);
    }
  });
});
