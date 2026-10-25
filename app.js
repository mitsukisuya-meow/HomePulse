(() => {
  document.querySelectorAll('[data-toggle-password]').forEach(button => {
    button.addEventListener('click', () => {
      const input = document.getElementById(button.dataset.togglePassword);
      if (!input) return;
      const show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      button.textContent = show ? 'Hide' : 'Show';
      button.setAttribute('aria-label', `${show ? 'Hide' : 'Show'} password`);
    });
  });
  document.querySelectorAll('[data-menu-toggle]').forEach(button => {
    button.addEventListener('click', () => {
      const nav = document.querySelector('[data-nav]');
      if (!nav) return;
      const open = nav.classList.toggle('open');
      button.setAttribute('aria-expanded', String(open));
    });
  });
  document.querySelectorAll('[data-dismiss]').forEach(button => button.addEventListener('click', () => button.closest('.flash')?.remove()));
  document.querySelectorAll('form[data-validate]').forEach(form => {
    form.addEventListener('submit', event => {
      const password = form.querySelector('#password');
      const confirm = form.querySelector('#confirm_password');
      const error = form.querySelector('[data-password-error]');
      if (password && confirm && password.value !== confirm.value) {
        event.preventDefault();
        if (error) error.textContent = 'Passwords do not match.';
        confirm.setCustomValidity('Passwords do not match.');
        confirm.reportValidity();
        return;
      }
      if (confirm) confirm.setCustomValidity('');
      if (!form.checkValidity()) { event.preventDefault(); form.reportValidity(); }
    });
    const confirm = form.querySelector('#confirm_password');
    if (confirm) confirm.addEventListener('input', () => {
      const password = form.querySelector('#password');
      const error = form.querySelector('[data-password-error]');
      const mismatch = confirm.value && confirm.value !== password.value;
      confirm.setCustomValidity(mismatch ? 'Passwords do not match.' : '');
      if (error) error.textContent = mismatch ? 'Passwords do not match.' : '';
    });
  });
})();
