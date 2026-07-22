/**
 * login.js — Logika halaman Login Konselor
 *
 * Handles:
 * - Redirect ke riwayat.html jika sudah ada token di sessionStorage
 * - Submit form login → POST /login → simpan token → redirect
 * - Toggle show/hide password
 * - Tampil pesan error jika 401
 */

(() => {
  'use strict';

  const TOKEN_KEY = 'konselor_token';
  const DASHBOARD_URL = '/riwayat.html';

  // ─── Jika sudah login, langsung ke dashboard ────────────────────
  if (sessionStorage.getItem(TOKEN_KEY)) {
    window.location.replace(DASHBOARD_URL);
  }

  // ─── DOM Elements ───────────────────────────────────────────────
  const form        = document.getElementById('loginForm');
  const inputUser   = document.getElementById('inputUsername');
  const inputPw     = document.getElementById('inputPassword');
  const btnLogin    = document.getElementById('btnLogin');
  const btnText     = document.getElementById('btnLoginText');
  const btnSpinner  = document.getElementById('btnLoginSpinner');
  const errorBox    = document.getElementById('loginError');
  const errorText   = document.getElementById('loginErrorText');
  const btnTogglePw = document.getElementById('btnTogglePw');
  const iconEye     = document.getElementById('iconEye');
  const iconEyeOff  = document.getElementById('iconEyeOff');


  // ─── Toggle Password Visibility ─────────────────────────────────
  btnTogglePw.addEventListener('click', () => {
    const isHidden = inputPw.type === 'password';
    inputPw.type    = isHidden ? 'text' : 'password';
    iconEye.style.display    = isHidden ? 'none' : '';
    iconEyeOff.style.display = isHidden ? '' : 'none';
    btnTogglePw.setAttribute('aria-label',
      isHidden ? 'Sembunyikan password' : 'Tampilkan password'
    );
  });


  // ─── Show / Hide Error ──────────────────────────────────────────
  function showError(msg) {
    errorText.textContent = msg;
    errorBox.style.display = 'flex';
    // Reset animation
    errorBox.classList.remove('shake-reset');
    void errorBox.offsetWidth; // reflow
    errorBox.classList.add('shake-reset');
  }

  function hideError() {
    errorBox.style.display = 'none';
  }


  // ─── Loading State ──────────────────────────────────────────────
  function setLoading(loading) {
    btnLogin.disabled     = loading;
    btnText.style.display = loading ? 'none' : '';
    btnSpinner.style.display = loading ? '' : 'none';
  }


  // ─── Form Submit ────────────────────────────────────────────────
  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    hideError();

    const username = inputUser.value.trim();
    const password = inputPw.value;

    if (!username || !password) {
      showError('Username dan password wajib diisi.');
      return;
    }

    setLoading(true);

    try {
      const response = await fetch('/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      if (response.ok) {
        const data = await response.json();
        sessionStorage.setItem(TOKEN_KEY, data.access_token);
        // Redirect ke dashboard
        window.location.replace(DASHBOARD_URL);
      } else if (response.status === 401) {
        showError('Username atau password salah. Silakan coba lagi.');
        inputPw.value = '';
        inputUser.focus();
      } else {
        showError('Terjadi kesalahan pada server. Coba beberapa saat lagi.');
      }
    } catch (err) {
      console.error('Login error:', err);
      showError('Tidak dapat terhubung ke server. Periksa koneksi Anda.');
    } finally {
      setLoading(false);
    }
  });

  // ─── Clear error saat user mengetik ─────────────────────────────
  inputUser.addEventListener('input', hideError);
  inputPw.addEventListener('input', hideError);

  // ─── Focus username saat halaman load ───────────────────────────
  inputUser.focus();

})();
