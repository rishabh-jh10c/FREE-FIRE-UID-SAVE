document.addEventListener('DOMContentLoaded', () => {

    // 1. Password Blur Reveal on Dashboard
    const pwReveals = document.querySelectorAll('.pw-reveal');
    pwReveals.forEach(element => {
        element.addEventListener('click', function() {
            this.classList.toggle('unblur');
            if(this.classList.contains('unblur')) {
                setTimeout(() => {
                    this.classList.remove('unblur');
                }, 10000); // 10 second auto re-hide
            }
        });
    });

    // 2. Add/Edit Form: Show Unban Timer field if Status is Banned or Blacklisted
    const statusSelect = document.getElementById('statusSelect');
    const unbanTimeGrp = document.getElementById('unbanTimeGrp');
    if (statusSelect && unbanTimeGrp) {
        const toggleTimerGroup = () => {
            if (statusSelect.value === 'Banned' || statusSelect.value === 'Blacklisted') {
                unbanTimeGrp.style.display = 'block';
            } else {
                unbanTimeGrp.style.display = 'none';
            }
        };
        statusSelect.addEventListener('change', toggleTimerGroup);
        toggleTimerGroup(); // Initial check on load
    }

    // 3. Live Countdown Timer Execution
    const timers = document.querySelectorAll('.countdown');
    
    const updateCountdowns = () => {
        const now = new Date().getTime();

        timers.forEach(timer => {
            const unbanStr = timer.getAttribute('data-unban');
            // '2026-04-10T12:00:00'
            // To ensure correct parsing, we treat it logically
            const unbanDate = new Date(unbanStr).getTime();
            
            const distance = unbanDate - now;

            if (distance < 0) {
                timer.innerHTML = "ACCOUNT READY (Unbanned)!";
                timer.style.color = "var(--neon-green)";
            } else {
                const days = Math.floor(distance / (1000 * 60 * 60 * 24));
                const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
                const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
                const seconds = Math.floor((distance % (1000 * 60)) / 1000);

                // Format string to be nice
                let display = '';
                if(days > 0) display += days + "d ";
                display += hours + "h " + minutes + "m " + seconds + "s";
                
                timer.innerHTML = display;
            }
        });
    }

    if (timers.length > 0) {
        // Run immediately, then every second
        updateCountdowns();
        setInterval(updateCountdowns, 1000);
    }
    
    // Auto-dim flash messages
    const flashes = document.querySelectorAll('.flash');
    flashes.forEach(flash => {
        setTimeout(() => {
            flash.style.opacity = '0';
            setTimeout(() => { flash.remove(); }, 500);
        }, 5000); // Hide after 5 seconds
    });

    // 4. Remember Me Functionality for Login
    const loginForm = document.getElementById('loginForm');
    if (loginForm) {
        const emailInput = document.getElementById('loginEmail');
        const passInput = document.getElementById('loginPassword');
        const rememberCheckbox = document.getElementById('rememberMe');

        // Check local storage on load
        if (localStorage.getItem('vaultRememberedEmail') && localStorage.getItem('vaultRememberedPassword')) {
            emailInput.value = localStorage.getItem('vaultRememberedEmail');
            passInput.value = localStorage.getItem('vaultRememberedPassword');
            rememberCheckbox.checked = true;
        }

        // Save/Remove on form submit
        loginForm.addEventListener('submit', () => {
            if (rememberCheckbox.checked) {
                localStorage.setItem('vaultRememberedEmail', emailInput.value);
                localStorage.setItem('vaultRememberedPassword', passInput.value);
            } else {
                localStorage.removeItem('vaultRememberedEmail');
                localStorage.removeItem('vaultRememberedPassword');
            }
        });

        // Toggle Password Visibility
        const togglePassword = document.getElementById('togglePassword');
        if (togglePassword && passInput) {
            togglePassword.addEventListener('click', function () {
                const type = passInput.getAttribute('type') === 'password' ? 'text' : 'password';
                passInput.setAttribute('type', type);
                this.textContent = type === 'password' ? 'Show' : 'Hide';
                this.style.color = type === 'password' ? 'var(--neon-blue)' : 'var(--neon-pink)';
            });
        }
    }

    // 5. Custom Delete Modal Logic
    const cancelBtn = document.getElementById('cancelDeleteBtn');
    const confirmBtn = document.getElementById('confirmDeleteBtn');
    const deleteModal = document.getElementById('deleteModal');

    if (cancelBtn) {
        cancelBtn.addEventListener('click', () => {
            if (deleteModal) deleteModal.classList.remove('active');
            accountToDelete = null;
        });
    }

    if (confirmBtn) {
        confirmBtn.addEventListener('click', () => {
            if (accountToDelete) {
                const form = document.getElementById('deleteForm-' + accountToDelete);
                if (form) {
                    // Show some quick visual feedback
                    confirmBtn.textContent = 'Deleting...';
                    confirmBtn.style.opacity = '0.7';
                    confirmBtn.style.pointerEvents = 'none';
                    form.submit();
                }
            }
        });
    }
});

let accountToDelete = null;
function openDeleteModal(accId) {
    accountToDelete = accId;
    const modal = document.getElementById('deleteModal');
    if (modal) {
        modal.classList.add('active');
    }
}
