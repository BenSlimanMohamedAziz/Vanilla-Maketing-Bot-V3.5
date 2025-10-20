document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("signupForm");
  const fields = [
    "full_name",
    "company_name",
    "email",
    "password",
    "confirm_password",
    "company_website",
    "company_phone", // Add phone field
  ];

  // Icônes œil pour montrer / cacher les mots de passe
  document.querySelectorAll(".toggle-password").forEach((icon) => {
    icon.addEventListener("click", function () {
      const target = document.getElementById(this.dataset.target);
      if (target.type === "password") {
        target.type = "text";
        this.classList.remove("fa-eye");
        this.classList.add("fa-eye-slash");
      } else {
        target.type = "password";
        this.classList.remove("fa-eye-slash");
        this.classList.add("fa-eye");
      }
    });
  });

  // Ajouter vérification en temps réel (input) et à la sortie du champ (blur)
  // Add real-time validation (input) and on blur
  fields.forEach((id) => {
    const input = document.getElementById(id);
    input.addEventListener("input", () => validateField(input));
    input.addEventListener("blur", () => validateField(input));
  });

  // Form submission handler
  form.addEventListener("submit", function (e) {
    e.preventDefault(); // Prevent default form submission

    let hasError = false;

    // Validate all fields first
    fields.forEach((id) => {
      const input = document.getElementById(id);
      if (!validateField(input)) {
        hasError = true;
      }
    });

    if (hasError) {
      form
        .querySelectorAll(".form-group")
        .forEach((group) => group.classList.add("shake"));
      setTimeout(() => {
        form
          .querySelectorAll(".form-group")
          .forEach((group) => group.classList.remove("shake"));
      }, 300);
      return;
    }

    // If validation passes, submit via AJAX
    const formData = new FormData(form);

    fetch("/signup", {
      method: "POST",
      body: formData,
    })
      .then((response) => {
        if (response.ok) {
          // If successful, redirect to plans page
          window.location.href = "/plan";
        } else if (response.status === 400) {
          // Handle validation errors
          return response.json().then((data) => {
            if (data.detail === "Email already registered") {
              const emailInput = document.getElementById("email");
              showError(
                emailInput,
                "A User with this E-mail is already registered. Please use a different email or login."
              );
              emailInput.classList.add("error-field");

              // Add shake animation to email field only
              const formGroup = emailInput.closest(".form-group");
              formGroup.classList.add("shake");
              setTimeout(() => {
                formGroup.classList.remove("shake");
              }, 300);
            } else {
              // Handle other validation errors
              alert(data.detail || "Validation error occurred");
            }
          });
        } else {
          throw new Error("Server error");
        }
      })
      .catch((error) => {
        console.error("Error:", error);
        alert("An error occurred. Please try again.");
      });
  });

  // Field validation function
  function validateField(input) {
    const id = input.id;
    const value = input.value.trim();
    let isValid = true;

    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    const nameRegex = /^[A-Za-z\s]{3,}$/;

    // Clear previous error styling
    input.classList.remove("error-field");

    switch (id) {
      case "full_name":
        if (!value) {
          showError(input, "Full name is required");
          isValid = false;
        } else if (!nameRegex.test(value)) {
          showError(
            input,
            "Enter a real full name (min 3 letters, no numbers)"
          );
          isValid = false;
        } else {
          hideError(input);
        }
        break;

      case "company_name":
        if (!value) {
          showError(input, "Company name is required");
          isValid = false;
        } else {
          hideError(input);
        }
        break;

      case "email":
        if (!value) {
          showError(input, "Email is required");
          isValid = false;
        } else if (!emailRegex.test(value)) {
          showError(input, "Not a valid email address");
          input.classList.add("error-field");
          isValid = false;
        } else {
          hideError(input);
        }
        break;

      case "password":
        if (!value) {
          showError(input, "Password is required");
          isValid = false;
        } else {
          hideError(input);
        }
        break;

      case "confirm_password":
        const password = document.getElementById("password").value.trim();
        if (!value) {
          showError(input, "Please confirm your password");
          isValid = false;
        } else if (value !== password) {
          showError(input, "Passwords do not match");
          isValid = false;
        } else {
          hideError(input);
        }
        break;

      case "company_website":
        if (value) {
          const websitePattern =
            /^(https?:\/\/)?([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}(\/.*)?$/;
          const linkedinPattern =
            /^(https?:\/\/)?(www\.)?linkedin\.com\/in\/.+$/;

          if (!websitePattern.test(value) && !linkedinPattern.test(value)) {
            showError(
              input,
              "Please enter a valid website (https://example.com or example.com) or LinkedIn (www.linkedin.com/in/profile)"
            );
            isValid = false;
          } else {
            hideError(input);
          }
        } else {
          hideError(input); // Optional field
        }
        break;

      case "company_phone":
        if (!value) {
          showError(input, "Phone number is required");
          isValid = false;
        } else {
          const phonePattern =
            /^\+?[0-9]{1,4}?[-.\s]?\(?[0-9]{1,4}?\)?[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,9}$/;

          if (!phonePattern.test(value)) {
            showError(
              input,
              "Please enter a valid phone number with country code"
            );
            isValid = false;
          } else {
            hideError(input);
          }
        }
        break;
    }

    return isValid;
  }

  // Show error under a field
  function showError(input, message) {
    const errorDiv = input.parentElement.nextElementSibling;
    if (errorDiv && errorDiv.classList.contains("error-message")) {
      errorDiv.textContent = message;
      errorDiv.style.display = "block";
      input.classList.add("error-field");
    }
  }

  // Hide error under a field
  function hideError(input) {
    const errorDiv = input.parentElement.nextElementSibling;
    if (errorDiv && errorDiv.classList.contains("error-message")) {
      errorDiv.textContent = "";
      errorDiv.style.display = "none";
      input.classList.remove("error-field");
    }
  }
});

// Navbar Toggle
const menuToggle = document.getElementById("menu-toggle");
const navContainer = document.getElementById("nav-container");

menuToggle.addEventListener("click", () => {
  menuToggle.classList.toggle("active");
  navContainer.classList.toggle("active");
});

// Close menu when clicking on a link
const navLinks = document.querySelectorAll(".nav-links a, .auth-buttons a");
navLinks.forEach((link) => {
  link.addEventListener("click", () => {
    menuToggle.classList.remove("active");
    navContainer.classList.remove("active");
  });
});

// Close menu when clicking outside
document.addEventListener("click", (e) => {
  if (!navContainer.contains(e.target) && !menuToggle.contains(e.target)) {
    menuToggle.classList.remove("active");
    navContainer.classList.remove("active");
  }
});

// Add scroll effect to header
window.addEventListener("scroll", () => {
  const header = document.querySelector("header");
  if (window.scrollY > 10) {
    header.style.padding = "1rem 5%";
    header.style.background = "rgba(27, 34, 44, 0.98)";
  } else {
    header.style.padding = "1.5rem 5%";
    header.style.background = "rgba(27, 34, 44, 0.95)";
  }
});

document.addEventListener("DOMContentLoaded", function () {
  const passwordInputs = document.querySelectorAll(".password-field input");

  passwordInputs.forEach((input) => {
    // Show/hide eye icon based on input content
    input.addEventListener("input", function () {
      const eyeIcon = this.nextElementSibling;
      if (this.value.length > 0) {
        eyeIcon.style.display = "block";
      } else {
        eyeIcon.style.display = "none";
      }
    });
  });
});
document.addEventListener("DOMContentLoaded", function () {
  // When form is submitted, copy password to hidden field
  document.getElementById("signupForm").addEventListener("submit", function () {
    document.getElementById("password-hidden").value =
      document.getElementById("password").value;
  });
});
