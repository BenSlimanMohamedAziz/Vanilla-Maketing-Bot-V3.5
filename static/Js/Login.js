// Toggle password visibility
document.querySelector('.toggle-password').addEventListener('click', function() {
    const password = document.getElementById('password');
    if (password.type === "password") {
        password.type = "text";
        this.classList.remove("fa-eye");
        this.classList.add("fa-eye-slash");
    } else {
        password.type = "password";
        this.classList.remove("fa-eye-slash");
        this.classList.add("fa-eye");
    }
});

// Show/hide eye icon when typing
document.getElementById('password').addEventListener('input', function() {
    const eyeIcon = this.nextElementSibling;
    eyeIcon.style.display = this.value.length > 0 ? 'block' : 'none';
});

document.getElementById("loginForm").addEventListener("submit", function (e) {
    const email = document.getElementById("email");
    const password = document.getElementById("password");
    let hasError = false;

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (!email.value.trim()) {
        showError(email, "E-mail is required");
        hasError = true;
    } else if (!emailRegex.test(email.value.trim())) {
        showError(email, "Not a valid email address");
        email.classList.add("invalid-email");
        hasError = true;
    } else {
        hideError(email);
        email.classList.remove("invalid-email");
    }

    if (!password.value.trim()) {
        showError(password, "Password is required");
        hasError = true;
    } else {
        hideError(password);
    }

    if (hasError) {
        e.preventDefault();
        this.querySelectorAll(".form-group").forEach(group => group.classList.add("shake"));
        setTimeout(() => {
            this.querySelectorAll(".form-group").forEach(group => group.classList.remove("shake"));
        }, 300);
    }
});

function showError(input, message) {
    const errorDiv = input.parentElement.nextElementSibling;
    errorDiv.textContent = message;
    errorDiv.style.display = "block";
}

function hideError(input) {
    const errorDiv = input.parentElement.nextElementSibling;
    errorDiv.textContent = "";
    errorDiv.style.display = "none";
}

// Email blur verification (for instant feedback)
document.getElementById("email").addEventListener("blur", function () {
    const emailInput = this;
    const emailValue = emailInput.value.trim();
    const errorDiv = document.getElementById("email-error");

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

    if (emailValue && !emailRegex.test(emailValue)) {
        errorDiv.textContent = "Not a valid e-mail address";
        errorDiv.style.display = "block";
        emailInput.classList.add("invalid-email");
    } else {
        errorDiv.textContent = "";
        errorDiv.style.display = "none";
        emailInput.classList.remove("invalid-email");
    }
});

// Navbar Toggle
const menuToggle = document.getElementById('menu-toggle');
const navContainer = document.getElementById('nav-container');

menuToggle.addEventListener('click', () => {
    menuToggle.classList.toggle('active');
    navContainer.classList.toggle('active');
});

// Close menu when clicking on a link
const navLinks = document.querySelectorAll('.nav-links a, .auth-buttons a');
navLinks.forEach(link => {
    link.addEventListener('click', () => {
        menuToggle.classList.remove('active');
        navContainer.classList.remove('active');
    });
});

// Close menu when clicking outside
document.addEventListener('click', (e) => {
    if (!navContainer.contains(e.target) && !menuToggle.contains(e.target)) {
        menuToggle.classList.remove('active');
        navContainer.classList.remove('active');
    }
});

// Add scroll effect to header
window.addEventListener('scroll', () => {
    const header = document.querySelector('header');
    if (window.scrollY > 10) {
        header.style.padding = '1rem 5%';
        header.style.background = 'rgba(27, 34, 44, 0.98)';
    } else {
        header.style.padding = '1.5rem 5%';
        header.style.background = 'rgba(27, 34, 44, 0.95)';
    }
});


