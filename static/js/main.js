/* =========================================================
   Payvora – Main JavaScript
   ========================================================= */

document.addEventListener('DOMContentLoaded', () => {

  /* ---------- Theme Toggle ---------- */
  const themeBtn = document.getElementById('themeToggle');
  const body = document.body;
  const savedTheme = localStorage.getItem('pv_theme') || 'dark';
  if (savedTheme === 'light') body.classList.add('light-mode');
  updateThemeIcon();

  if (themeBtn) {
    themeBtn.addEventListener('click', () => {
      body.classList.toggle('light-mode');
      const theme = body.classList.contains('light-mode') ? 'light' : 'dark';
      localStorage.setItem('pv_theme', theme);
      updateThemeIcon();
    });
  }
  function updateThemeIcon() {
    if (!themeBtn) return;
    const isLight = body.classList.contains('light-mode');
    themeBtn.textContent = isLight ? '🌙' : '☀️';
    themeBtn.title = isLight ? 'Switch to Dark Mode' : 'Switch to Light Mode';
  }

  /* ---------- Mobile Sidebar Toggle ---------- */
  const hamburger = document.getElementById('hamburger');
  const sidebar = document.getElementById('sidebar');
  const overlay = document.getElementById('sidebarOverlay');

  if (hamburger && sidebar && overlay) {
    hamburger.addEventListener('click', () => {
      sidebar.classList.toggle('open');
      overlay.classList.toggle('active');
    });
    overlay.addEventListener('click', () => {
      sidebar.classList.remove('open');
      overlay.classList.remove('active');
    });
  }

  /* ---------- Auto-dismiss alerts ---------- */
  const alerts = document.querySelectorAll('.alert');
  alerts.forEach(alert => {
    setTimeout(() => {
      alert.style.transition = 'opacity 0.4s ease, transform 0.4s ease';
      alert.style.opacity = '0';
      alert.style.transform = 'translateY(-8px)';
      setTimeout(() => alert.remove(), 400);
    }, 4500);
  });

  /* ---------- Network auto-detect ---------- */
  const phoneInputs = document.querySelectorAll('[data-autodetect-network]');
  phoneInputs.forEach(input => {
    const targetId = input.dataset.autodetectNetwork;
    const networkDisplay = document.getElementById(targetId);
    if (!networkDisplay) return;
    input.addEventListener('input', () => {
      const net = detectNetwork(input.value);
      if (net) {
        networkDisplay.textContent = net;
        networkDisplay.className = 'detected-network badge-network active';
      } else {
        networkDisplay.textContent = 'Unknown';
        networkDisplay.className = 'detected-network badge-network';
      }
    });
  });

  function detectNetwork(phone) {
    phone = phone.replace(/\D/g, '');
    if (phone.startsWith('0')) phone = phone.substring(1);
    const full = '0' + phone.substring(0, 9);
    const prefix = full.substring(0, 4);
    const mtn = ['0703','0706','0803','0806','0810','0813','0814','0816','0903','0906','0913','0916'];
    const airtel = ['0701','0708','0802','0808','0812','0901','0902','0904','0907','0912'];
    const glo = ['0705','0805','0807','0811','0815','0905','0915'];
    const mobile9 = ['0809','0817','0818','0909','0908'];
    if (mtn.includes(prefix)) return 'MTN';
    if (airtel.includes(prefix)) return 'Airtel';
    if (glo.includes(prefix)) return 'Glo';
    if (mobile9.includes(prefix)) return '9mobile';
    return null;
  }

  /* ---------- Data plan card selector ---------- */
  const planCards = document.querySelectorAll('.plan-card');
  const planIdInput = document.getElementById('selected_plan_id');
  const planPriceDisplay = document.getElementById('plan_price_display');
  const buyBtn = document.getElementById('buy_data_btn');

  planCards.forEach(card => {
    card.addEventListener('click', () => {
      planCards.forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      const planId = card.dataset.planId;
      const planPrice = card.dataset.planPrice;
      const planName = card.dataset.planName;
      if (planIdInput) planIdInput.value = planId;
      if (planPriceDisplay) planPriceDisplay.textContent = `₦${parseFloat(planPrice).toLocaleString('en-NG', {minimumFractionDigits: 2})}`;
      if (buyBtn) {
        buyBtn.disabled = false;
        buyBtn.textContent = `Buy – ₦${parseFloat(planPrice).toLocaleString('en-NG', {minimumFractionDigits: 0})}`;
      }
    });
  });

  /* ---------- Airtime quick-amount buttons ---------- */
  const airtimeAmounts = document.querySelectorAll('.airtime-quick');
  const airtimeInput = document.getElementById('airtime_amount');
  airtimeAmounts.forEach(btn => {
    btn.addEventListener('click', () => {
      airtimeAmounts.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      if (airtimeInput) airtimeInput.value = btn.dataset.amount;
    });
  });

  /* ---------- TV Package selector ---------- */
  const tvPackages = document.querySelectorAll('.tv-package');
  const tvAmountInput = document.getElementById('tv_amount');
  const tvPackageInput = document.getElementById('tv_package_name');
  tvPackages.forEach(pkg => {
    pkg.addEventListener('click', () => {
      tvPackages.forEach(p => p.classList.remove('selected'));
      pkg.classList.add('selected');
      if (tvAmountInput) tvAmountInput.value = pkg.dataset.price;
      if (tvPackageInput) tvPackageInput.value = pkg.dataset.name;
    });
  });

  /* ---------- Provider tab toggle (TV) ---------- */
  const providerTabs = document.querySelectorAll('.provider-tab');
  providerTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      providerTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
      const provider = tab.dataset.provider;
      document.querySelectorAll('.packages-group').forEach(g => {
        g.style.display = g.dataset.provider === provider ? 'grid' : 'none';
      });
      document.getElementById('tv_provider').value = provider;
    });
  });

  /* ---------- Simulated Paystack Checkout ---------- */
  const payBtn = document.getElementById('payNowBtn');
  const failBtn = document.getElementById('failPaymentBtn');
  const checkoutForm = document.getElementById('checkoutForm');
  const checkoutOutcome = document.getElementById('checkoutOutcome');

  if (payBtn && checkoutForm) {
    payBtn.addEventListener('click', (e) => {
      e.preventDefault();
      const cardNumber = document.getElementById('cardNumber')?.value?.replace(/\s/g,'') || '';
      const expiry = document.getElementById('cardExpiry')?.value || '';
      const cvv = document.getElementById('cardCvv')?.value || '';
      if (cardNumber.length < 16 || !expiry || cvv.length < 3) {
        showCheckoutError('Please fill in all card details correctly.');
        return;
      }
      // Simulate processing
      payBtn.disabled = true;
      payBtn.innerHTML = '<span class="spinner"></span> Processing...';
      setTimeout(() => {
        checkoutOutcome.value = 'success';
        checkoutForm.submit();
      }, 2200);
    });
  }
  if (failBtn && checkoutForm) {
    failBtn.addEventListener('click', (e) => {
      e.preventDefault();
      checkoutOutcome.value = 'fail';
      checkoutForm.submit();
    });
  }

  function showCheckoutError(msg) {
    let err = document.getElementById('checkoutError');
    if (!err) {
      err = document.createElement('div');
      err.id = 'checkoutError';
      err.className = 'alert alert-error';
      checkoutForm.prepend(err);
    }
    err.textContent = msg;
  }

  /* ---------- Card number formatter ---------- */
  const cardNumberInput = document.getElementById('cardNumber');
  if (cardNumberInput) {
    cardNumberInput.addEventListener('input', (e) => {
      let val = e.target.value.replace(/\D/g, '').substring(0, 16);
      val = val.replace(/(.{4})/g, '$1 ').trim();
      e.target.value = val;
    });
  }

  /* ---------- Expiry formatter ---------- */
  const expiryInput = document.getElementById('cardExpiry');
  if (expiryInput) {
    expiryInput.addEventListener('input', (e) => {
      let val = e.target.value.replace(/\D/g, '').substring(0, 4);
      if (val.length >= 3) val = val.substring(0,2) + '/' + val.substring(2);
      e.target.value = val;
    });
  }

  /* ---------- Checkout tabs ---------- */
  const checkoutTabs = document.querySelectorAll('.checkout-tab');
  checkoutTabs.forEach(tab => {
    tab.addEventListener('click', () => {
      checkoutTabs.forEach(t => t.classList.remove('active'));
      tab.classList.add('active');
    });
  });

  /* ---------- Counter animations ---------- */
  const counters = document.querySelectorAll('[data-count]');
  const observerOpts = { threshold: 0.5 };
  const counterObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        animateCount(entry.target);
        counterObserver.unobserve(entry.target);
      }
    });
  }, observerOpts);
  counters.forEach(el => counterObserver.observe(el));

  function animateCount(el) {
    const target = parseFloat(el.dataset.count);
    const prefix = el.dataset.prefix || '';
    const suffix = el.dataset.suffix || '';
    const duration = 1800;
    const step = 16;
    const increment = target / (duration / step);
    let current = 0;
    const timer = setInterval(() => {
      current += increment;
      if (current >= target) { current = target; clearInterval(timer); }
      el.textContent = prefix + (Number.isInteger(target) ? Math.floor(current).toLocaleString() : current.toFixed(1)) + suffix;
    }, step);
  }

  /* ---------- Exam quantity → price calculation ---------- */
  const examSelect = document.getElementById('exam_type');
  const examQty = document.getElementById('exam_qty');
  const examTotal = document.getElementById('exam_total_display');
  const examUnitPrice = document.getElementById('exam_unit_price');

  function updateExamTotal() {
    if (!examSelect || !examQty || !examTotal || !examUnitPrice) return;
    const selected = examSelect.options[examSelect.selectedIndex];
    const price = parseFloat(selected?.dataset?.price || 0);
    const qty = parseInt(examQty.value || 1);
    const total = price * qty;
    examTotal.textContent = '₦' + total.toLocaleString('en-NG', {minimumFractionDigits: 2});
    if (examUnitPrice) examUnitPrice.value = price;
  }
  if (examSelect) examSelect.addEventListener('change', updateExamTotal);
  if (examQty) examQty.addEventListener('input', updateExamTotal);
  updateExamTotal();

  /* ---------- Copy referral link ---------- */
  const copyRefBtn = document.getElementById('copyRefLink');
  if (copyRefBtn) {
    copyRefBtn.addEventListener('click', () => {
      const link = document.getElementById('refLink')?.textContent?.trim();
      if (link) {
        navigator.clipboard.writeText(link).then(() => {
          copyRefBtn.textContent = '✅ Copied!';
          setTimeout(() => copyRefBtn.textContent = '📋 Copy', 2000);
        });
      }
    });
  }

  /* ---------- Fund wallet quick-amount buttons ---------- */
  const fundAmounts = document.querySelectorAll('.fund-quick');
  const fundInput = document.getElementById('fund_amount');
  fundAmounts.forEach(btn => {
    btn.addEventListener('click', () => {
      fundAmounts.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      if (fundInput) fundInput.value = btn.dataset.amount;
    });
  });

});
