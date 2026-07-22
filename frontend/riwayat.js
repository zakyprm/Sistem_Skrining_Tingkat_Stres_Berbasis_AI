/**
 * riwayat.js — Dashboard Riwayat Konselor
 *
 * Handles:
 * - Auth guard: redirect ke login.html jika tidak ada token (sessionStorage)
 * - Fetching riwayat data dari GET /riwayat dengan Authorization header
 * - Fetching ringkasan dari GET /ringkasan dengan Authorization header
 * - Redirect ke login.html jika mendapat response 401
 * - Tombol Logout: hapus token + redirect ke login.html
 * - Rendering summary cards, tabel, dan pagination
 * - Filter rentang tanggal (BR-14)
 * - Pagination navigation
 */

(() => {
  'use strict';

  // ─── Konstanta ────────────────────────────────────────────────
  const API_BASE   = '';
  const PAGE_SIZE  = 15;
  const TOKEN_KEY  = 'konselor_token';
  const LOGIN_URL  = '/login.html';

  // ─── Auth Guard ──────────────────────────────────────────────
  // Cek token saat halaman dimuat — redirect jika tidak ada
  const token = sessionStorage.getItem(TOKEN_KEY);
  if (!token) {
    window.location.replace(LOGIN_URL);
  }

  // Helper: headers dengan Bearer token
  function authHeaders() {
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  }

  // Handler untuk response 401 — hapus token dan redirect
  function handleUnauthorized() {
    sessionStorage.removeItem(TOKEN_KEY);
    window.location.replace(LOGIN_URL);
  }


  // ─── State ───────────────────────────────────────────────────
  let currentOffset = 0;
  let totalRecords  = 0;
  let currentFilter = {
    tanggal_mulai: null,
    tanggal_selesai: null,
  };

  // ─── DOM Elements ─────────────────────────────────────────────
  const els = {
    // Summary cards
    countNormal: document.getElementById('countNormal'),
    countSedang: document.getElementById('countSedang'),
    countTinggi: document.getElementById('countTinggi'),
    totalCount:  document.getElementById('totalCount'),

    // Filter
    filterMulai:    document.getElementById('filterMulai'),
    filterSelesai:  document.getElementById('filterSelesai'),
    btnApplyFilter: document.getElementById('btnApplyFilter'),
    btnResetFilter: document.getElementById('btnResetFilter'),

    // Table
    tableBody:    document.getElementById('tableBody'),
    tableLoading: document.getElementById('tableLoading'),
    emptyState:   document.getElementById('emptyState'),
    tableInfo:    document.getElementById('tableInfo'),

    // Pagination
    pagination: document.getElementById('pagination'),
    btnPrev:    document.getElementById('btnPrev'),
    btnNext:    document.getElementById('btnNext'),
    pageInfo:   document.getElementById('pageInfo'),

    // Logout
    btnLogout: document.getElementById('btnLogout'),
  };


  // ─── Logout ──────────────────────────────────────────────────
  if (els.btnLogout) {
    els.btnLogout.addEventListener('click', () => {
      sessionStorage.removeItem(TOKEN_KEY);
      window.location.replace(LOGIN_URL);
    });
  }


  // ─── Fetch Ringkasan ─────────────────────────────────────────
  async function fetchRingkasan() {
    try {
      const params = new URLSearchParams();
      if (currentFilter.tanggal_mulai)   params.set('tanggal_mulai', currentFilter.tanggal_mulai);
      if (currentFilter.tanggal_selesai) params.set('tanggal_selesai', currentFilter.tanggal_selesai);

      const url = `${API_BASE}/ringkasan${params.toString() ? '?' + params.toString() : ''}`;
      const response = await fetch(url, { headers: authHeaders() });

      if (response.status === 401) { handleUnauthorized(); return; }
      if (!response.ok) throw new Error('Gagal mengambil ringkasan');

      const data = await response.json();
      renderRingkasan(data);
    } catch (error) {
      console.error('Error fetching ringkasan:', error);
      renderRingkasan({ Normal: '-', Sedang: '-', Tinggi: '-', total: '-' });
    }
  }


  // ─── Fetch Riwayat ───────────────────────────────────────────
  async function fetchRiwayat() {
    showLoading(true);

    try {
      const params = new URLSearchParams({
        limit:  PAGE_SIZE.toString(),
        offset: currentOffset.toString(),
      });
      if (currentFilter.tanggal_mulai)   params.set('tanggal_mulai', currentFilter.tanggal_mulai);
      if (currentFilter.tanggal_selesai) params.set('tanggal_selesai', currentFilter.tanggal_selesai);

      const url = `${API_BASE}/riwayat?${params.toString()}`;
      const response = await fetch(url, { headers: authHeaders() });

      if (response.status === 401) { handleUnauthorized(); return; }
      if (!response.ok) throw new Error('Gagal mengambil riwayat');

      const data = await response.json();
      totalRecords = data.total;
      renderTable(data.data);
      renderPagination();
      updateTableInfo();
    } catch (error) {
      console.error('Error fetching riwayat:', error);
      showEmpty(true);
    } finally {
      showLoading(false);
    }
  }


  // ─── Render Ringkasan ────────────────────────────────────────
  function renderRingkasan(data) {
    animateCount(els.countNormal, data.Normal);
    animateCount(els.countSedang, data.Sedang);
    animateCount(els.countTinggi, data.Tinggi);
    els.totalCount.innerHTML = `Total: <strong>${data.total}</strong> klasifikasi`;
  }

  function animateCount(el, target) {
    if (typeof target !== 'number') {
      el.textContent = target;
      return;
    }

    const duration = 600;
    const start    = performance.now();
    const startVal = parseInt(el.textContent) || 0;

    function tick(now) {
      const elapsed  = now - start;
      const progress = Math.min(elapsed / duration, 1);
      // Ease out cubic
      const eased   = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(startVal + (target - startVal) * eased);
      el.textContent = current;

      if (progress < 1) {
        requestAnimationFrame(tick);
      }
    }

    requestAnimationFrame(tick);
  }


  // ─── Render Table ────────────────────────────────────────────
  function renderTable(rows) {
    if (!rows || rows.length === 0) {
      els.tableBody.innerHTML = '';
      showEmpty(true);
      return;
    }

    showEmpty(false);

    els.tableBody.innerHTML = rows.map((row, idx) => {
      const no         = currentOffset + idx + 1;
      const labelLower = row.label.toLowerCase();
      const maxConf    = Math.max(row.confidence_normal, row.confidence_sedang, row.confidence_tinggi);
      const confPercent = (maxConf * 100).toFixed(1);
      const timestamp  = formatTimestamp(row.timestamp);

      return `
        <tr>
          <td>${no}</td>
          <td class="timestamp-text">${timestamp}</td>
          <td>
            <span class="label-badge label-badge-${labelLower}">
              ${row.label}
            </span>
          </td>
          <td class="confidence-text">${confPercent}%</td>
        </tr>
      `;
    }).join('');
  }


  // ─── Render Pagination ───────────────────────────────────────
  function renderPagination() {
    const currentPage = Math.floor(currentOffset / PAGE_SIZE) + 1;
    const totalPages  = Math.max(1, Math.ceil(totalRecords / PAGE_SIZE));

    els.btnPrev.disabled = currentOffset <= 0;
    els.btnNext.disabled = currentOffset + PAGE_SIZE >= totalRecords;
    els.pageInfo.textContent = `Halaman ${currentPage} dari ${totalPages}`;

    // Show/hide pagination
    els.pagination.style.display = totalRecords > PAGE_SIZE ? 'flex' : 'none';
  }


  // ─── Update Table Info ───────────────────────────────────────
  function updateTableInfo() {
    if (totalRecords === 0) {
      els.tableInfo.textContent = '';
      return;
    }
    const start = currentOffset + 1;
    const end   = Math.min(currentOffset + PAGE_SIZE, totalRecords);
    els.tableInfo.textContent = `${start}–${end} dari ${totalRecords}`;
  }


  // ─── Loading/Empty States ────────────────────────────────────
  function showLoading(show) {
    els.tableLoading.style.display = show ? 'flex' : 'none';
    if (show) {
      els.tableBody.innerHTML = '';
      showEmpty(false);
    }
  }

  function showEmpty(show) {
    els.emptyState.style.display = show ? 'block' : 'none';
  }


  // ─── Format Timestamp ───────────────────────────────────────
  function formatTimestamp(ts) {
    if (!ts) return '-';
    try {
      const date    = new Date(ts);
      const day     = date.getDate().toString().padStart(2, '0');
      const month   = (date.getMonth() + 1).toString().padStart(2, '0');
      const year    = date.getFullYear();
      const hours   = date.getHours().toString().padStart(2, '0');
      const minutes = date.getMinutes().toString().padStart(2, '0');
      return `${day}/${month}/${year} ${hours}:${minutes}`;
    } catch {
      return ts;
    }
  }


  // ─── Event Handlers ─────────────────────────────────────────
  // Apply filter
  els.btnApplyFilter.addEventListener('click', () => {
    currentFilter.tanggal_mulai   = els.filterMulai.value || null;
    currentFilter.tanggal_selesai = els.filterSelesai.value || null;
    currentOffset = 0;
    fetchAll();
  });

  // Reset filter
  els.btnResetFilter.addEventListener('click', () => {
    els.filterMulai.value         = '';
    els.filterSelesai.value       = '';
    currentFilter.tanggal_mulai   = null;
    currentFilter.tanggal_selesai = null;
    currentOffset = 0;
    fetchAll();
  });

  // Pagination
  els.btnPrev.addEventListener('click', () => {
    if (currentOffset > 0) {
      currentOffset = Math.max(0, currentOffset - PAGE_SIZE);
      fetchRiwayat();
    }
  });

  els.btnNext.addEventListener('click', () => {
    if (currentOffset + PAGE_SIZE < totalRecords) {
      currentOffset += PAGE_SIZE;
      fetchRiwayat();
    }
  });


  // ─── Fetch All Data ─────────────────────────────────────────
  function fetchAll() {
    fetchRingkasan();
    fetchRiwayat();
  }


  // ─── Initial Load ───────────────────────────────────────────
  fetchAll();

})();
