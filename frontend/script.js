/**
 * script.js — Frontend Logic untuk Klasifikasi Stres Santri
 * 
 * Handles:
 * - Input validation (FR-02)
 * - Word count tracking
 * - API call to POST /predict
 * - Loading state management (FR-03)
 * - Result rendering with level-specific visuals (FR-04)
 * - Auto-show rujukan card for "Tinggi" (FR-05)
 * - Error handling
 * - Form reset
 * - No localStorage/sessionStorage usage (FR-07)
 */

(() => {
  'use strict';

  // ─── Configuration ────────────────────────────────────────────
  const API_BASE = '';
  const MIN_WORDS = 10;

  // ─── DOM Elements ─────────────────────────────────────────────
  const els = {
    textarea: document.getElementById('inputTeks'),
    wordCounter: document.getElementById('wordCounter'),
    btnAnalisis: document.getElementById('btnAnalisis'),
    btnText: document.getElementById('btnText'),
    btnIcon: document.getElementById('btnIcon'),
    btnSpinner: document.getElementById('btnSpinner'),
    btnReset: document.getElementById('btnReset'),
    errorMessage: document.getElementById('errorMessage'),
    errorText: document.getElementById('errorText'),
    loadingOverlay: document.getElementById('loadingOverlay'),
    resultSection: document.getElementById('resultSection'),
    resultCard: document.getElementById('resultCard'),
    refleksiIconWrap: document.getElementById('refleksiIconWrap'),
    refleksiIcon: document.getElementById('refleksiIcon'),
    resultMessage: document.getElementById('resultMessage'),
    barNormal: document.getElementById('barNormal'),
    barSedang: document.getElementById('barSedang'),
    barTinggi: document.getElementById('barTinggi'),
    valNormal: document.getElementById('valNormal'),
    valSedang: document.getElementById('valSedang'),
    valTinggi: document.getElementById('valTinggi'),
    rujukanSection: document.getElementById('rujukanSection'),
    rujukanInternal: document.getElementById('rujukanInternal'),
    rujukanEksternal: document.getElementById('rujukanEksternal'),
  };


  // ─── SVG Icons per Level ──────────────────────────────────────
  const LEVEL_ICONS = {
    Normal: `
      <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
      <polyline points="22 4 12 14.01 9 11.01"></polyline>
    `,
    Sedang: `
      <circle cx="12" cy="12" r="10"></circle>
      <line x1="12" y1="8" x2="12" y2="12"></line>
      <line x1="12" y1="16" x2="12.01" y2="16"></line>
    `,
    Tinggi: `
      <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
      <line x1="12" y1="9" x2="12" y2="13"></line>
      <line x1="12" y1="17" x2="12.01" y2="17"></line>
    `,
  };


  // ─── Utility: Count Words ─────────────────────────────────────
  function countWords(text) {
    const trimmed = text.trim();
    if (!trimmed) return 0;
    return trimmed.split(/\s+/).length;
  }


  // ─── Word Counter Update ──────────────────────────────────────
  function updateWordCounter() {
    const count = countWords(els.textarea.value);
    els.wordCounter.textContent = `${count} kata`;

    // Visual feedback
    els.wordCounter.classList.remove('warning', 'valid');
    if (count > 0 && count < MIN_WORDS) {
      els.wordCounter.classList.add('warning');
    } else if (count >= MIN_WORDS) {
      els.wordCounter.classList.add('valid');
    }

    // Enable/disable button
    els.btnAnalisis.disabled = count < MIN_WORDS;
  }


  // ─── Show/Hide Error ─────────────────────────────────────────
  function showError(message) {
    els.errorText.textContent = message;
    els.errorMessage.classList.add('visible');
    
    // Auto-hide after 8 seconds
    setTimeout(() => hideError(), 8000);
  }

  function hideError() {
    els.errorMessage.classList.remove('visible');
  }


  // ─── Loading State (FR-03) ───────────────────────────────────
  function setLoading(isLoading) {
    if (isLoading) {
      els.btnAnalisis.disabled = true;
      els.btnText.textContent = 'Menganalisis…';
      els.btnIcon.style.display = 'none';
      els.btnSpinner.style.display = 'block';
      els.loadingOverlay.classList.add('visible');
      els.textarea.readOnly = true;
    } else {
      els.btnAnalisis.disabled = false;
      els.btnText.textContent = 'Analisis';
      els.btnIcon.style.display = 'block';
      els.btnSpinner.style.display = 'none';
      els.loadingOverlay.classList.remove('visible');
      els.textarea.readOnly = false;
      updateWordCounter(); // Re-check button state
    }
  }


  // ─── Render Result (FR-04, FR-05) ────────────────────────────
  function renderResult(data) {
    // Remove previous level classes
    els.resultCard.classList.remove('level-Normal', 'level-sedang', 'level-tinggi');

    // Add current level class
    const levelClass = `level-${data.label.toLowerCase()}`;
    els.resultCard.classList.add(levelClass);

    // Icon
    els.refleksiIcon.innerHTML = LEVEL_ICONS[data.label] || '';

    // Message
    els.resultMessage.textContent = data.pesan;

    // Confidence bars (animate with delay)
    requestAnimationFrame(() => {
      setTimeout(() => {
        const Normal = data.confidence.Normal * 100;
        const sedang = data.confidence.Sedang * 100;
        const tinggi = data.confidence.Tinggi * 100;

        els.barNormal.style.width = `${Normal}%`;
        els.barSedang.style.width = `${sedang}%`;
        els.barTinggi.style.width = `${tinggi}%`;

        els.valNormal.textContent = `${Normal.toFixed(1)}%`;
        els.valSedang.textContent = `${sedang.toFixed(1)}%`;
        els.valTinggi.textContent = `${tinggi.toFixed(1)}%`;
      }, 100);
    });

    // Rujukan (FR-05) — auto-show saat Tinggi
    if (data.tampilkan_rujukan && data.rujukan) {
      els.rujukanInternal.textContent = data.rujukan.kontak_internal;
      els.rujukanEksternal.textContent = data.rujukan.kontak_eksternal;
      els.rujukanSection.style.display = 'block';
    } else {
      els.rujukanSection.style.display = 'none';
    }

    // Show result section with animation
    els.resultSection.classList.add('visible');

    // Scroll to result smoothly
    setTimeout(() => {
      els.resultSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }, 200);
  }


  // ─── Reset Form ──────────────────────────────────────────────
  function resetForm() {
    els.textarea.value = '';
    updateWordCounter();
    hideError();
    
    // Hide result
    els.resultSection.classList.remove('visible');
    
    // Reset confidence bars
    els.barNormal.style.width = '0%';
    els.barSedang.style.width = '0%';
    els.barTinggi.style.width = '0%';
    els.valNormal.textContent = '0%';
    els.valSedang.textContent = '0%';
    els.valTinggi.textContent = '0%';
    
    // Hide rujukan
    els.rujukanSection.style.display = 'none';

    // Focus textarea
    els.textarea.focus();

    // Scroll to top
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }


  // ─── API Call ────────────────────────────────────────────────
  async function submitAnalysis() {
    const teks = els.textarea.value.trim();

    // Client-side validation
    if (!teks) {
      showError('Teks tidak boleh kosong.');
      return;
    }

    if (countWords(teks) < MIN_WORDS) {
      showError(`Teks terlalu pendek. Mohon tulis minimal ${MIN_WORDS} kata agar analisis lebih bermakna.`);
      return;
    }

    hideError();
    setLoading(true);

    // Hide previous result during loading
    els.resultSection.classList.remove('visible');

    try {
      const response = await fetch(`${API_BASE}/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ teks }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        const errorMsg = errorData?.detail || errorData?.error || `Server error (${response.status})`;
        throw new Error(errorMsg);
      }

      const data = await response.json();
      renderResult(data);

    } catch (error) {
      if (error.name === 'TypeError' && error.message.includes('fetch')) {
        showError(
          'Tidak dapat terhubung ke server. Pastikan backend sudah berjalan di localhost:8000.'
        );
      } else {
        showError(error.message || 'Terjadi kesalahan saat memproses. Silakan coba lagi.');
      }
    } finally {
      setLoading(false);
    }
  }


  // ─── Event Listeners ─────────────────────────────────────────
  // Word counter on input
  els.textarea.addEventListener('input', updateWordCounter);

  // Submit button
  els.btnAnalisis.addEventListener('click', submitAnalysis);

  // Keyboard shortcut: Ctrl+Enter to submit
  els.textarea.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter' && !els.btnAnalisis.disabled) {
      e.preventDefault();
      submitAnalysis();
    }
  });

  // Reset button
  els.btnReset.addEventListener('click', resetForm);


  // ─── Initial State ───────────────────────────────────────────
  updateWordCounter();

})();
