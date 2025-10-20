// Notification System
function showNotification(message, type = "info", duration = 5000) {
  const notificationCenter = document.getElementById("notification-center");
  if (!notificationCenter) return;

  const notification = document.createElement("div");
  notification.className = `notification ${type}`;

  let icon;
  switch (type) {
    case "success":
      icon = '<i class="fas fa-check-circle"></i>';
      break;
    case "error":
      icon = '<i class="fas fa-exclamation-circle"></i>';
      break;
    case "warning":
      icon = '<i class="fas fa-exclamation-triangle"></i>';
      break;
    default:
      icon = '<i class="fas fa-info-circle"></i>';
  }

  notification.innerHTML = `${icon}${message}`;
  notificationCenter.appendChild(notification);

  // Start fade out after duration
  setTimeout(() => {
    notification.style.opacity = "0";
    notification.style.transform = "translateX(100%)";
    setTimeout(() => notification.remove(), 300);
  }, duration);
}

// Link Account Modal
const linkAccountModal = document.getElementById("link-account-modal");
const linkAccountBtn = document.getElementById("link-account-btn");

if (linkAccountBtn) {
  linkAccountBtn.addEventListener("click", () => {
    linkAccountModal.style.display = "flex";
    document.body.style.overflow = "hidden";
  });
}

// Close modal
document.querySelectorAll(".close-modal").forEach((btn) => {
  btn.addEventListener("click", () => {
    linkAccountModal.style.display = "none";
    document.body.style.overflow = "";
  });
});

// Close when clicking outside
window.addEventListener("click", (e) => {
  if (e.target === linkAccountModal) {
    linkAccountModal.style.display = "none";
    document.body.style.overflow = "";
  }
});

// Link account function
function linkAccount(platform) {
  if (platform === "linkedin") {
    window.location.href = "/linkedin/login";
  } else if (platform === "meta") {
    window.location.href = "/meta/login";
  }
  // Add other platforms when implemented
}

// Disconnect account function
function disconnectAccount(platform, accountId) {
  const platformName =
    platform === "instagram"
      ? "Instagram"
      : platform === "facebook"
      ? "Facebook"
      : platform.charAt(0).toUpperCase() + platform.slice(1);

  if (
    confirm(`Are you sure you want to disconnect this ${platformName} account?`)
  ) {
    let endpoint;
    if (platform === "linkedin") {
      endpoint = "/linkedin/disconnect";
    } else if (platform === "facebook" || platform === "instagram") {
      endpoint = "/meta/disconnect";
    } else {
      return;
    }

    fetch(endpoint, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ account_id: accountId }),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          showNotification(`${platformName} account disconnected`, "success");
          setTimeout(() => location.reload(), 1000);
        } else {
          showNotification(
            data.error || `Failed to disconnect ${platformName} account`,
            "error"
          );
        }
      })
      .catch((error) => {
        showNotification("An error occurred while disconnecting", "error");
      });
  }
}

// Check for URL parameters to show notifications
document.addEventListener("DOMContentLoaded", () => {
  const params = new URLSearchParams(window.location.search);

  if (params.has("linkedin_success")) {
    showNotification("LinkedIn account linked successfully!", "success");
    cleanUrl();
  }

  if (params.has("meta_success")) {
    showNotification(
      "Facebook/Instagram accounts linked successfully!",
      "success"
    );
    cleanUrl();
  }

  if (params.has("facebook_disconnected")) {
    showNotification("Facebook account disconnected", "success");
    cleanUrl();
  }

  if (params.has("instagram_disconnected")) {
    showNotification("Instagram account disconnected", "success");
    cleanUrl();
  }

  if (params.has("error")) {
    showNotification(params.get("error"), "error");
    cleanUrl();
  }

  function cleanUrl() {
    window.history.replaceState({}, document.title, window.location.pathname);
  }
});

// Add this to your existing DOMContentLoaded event listener
document.addEventListener("DOMContentLoaded", function () {
  // User dropdown functionality
  const userAvatar = document.getElementById("userAvatar");
  const dropdownMenu = document.getElementById("dropdownMenu");
  const userMenu = document.querySelector(".user-menu");
  let hoverTimeout;
  // Sidebar toggle functionality
  const sidebarToggle = document.querySelector(".sidebar-toggle");
  const sidebar = document.querySelector(".sidebar");
  const mainContent = document.querySelector(".main-content");

  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener("click", function () {
      sidebar.classList.toggle("active");
      // Optional: Add overlay for mobile
      if (sidebar.classList.contains("active")) {
        document.body.classList.add("sidebar-open");
      } else {
        document.body.classList.remove("sidebar-open");
      }
    });

    // Close sidebar when clicking outside on mobile
    document.addEventListener("click", function (e) {
      if (window.innerWidth <= 768) {
        if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
          sidebar.classList.remove("active");
          document.body.classList.remove("sidebar-open");
        }
      }
    });

    // Handle window resize
    window.addEventListener("resize", function () {
      if (window.innerWidth > 768) {
        sidebar.classList.remove("active");
        document.body.classList.remove("sidebar-open");
      }
    });
  }
  // Show dropdown on hover
  userMenu.addEventListener("mouseenter", function () {
    clearTimeout(hoverTimeout);
    dropdownMenu.classList.add("show");
  });

  // Hide dropdown on mouse leave with slight delay
  userMenu.addEventListener("mouseleave", function () {
    hoverTimeout = setTimeout(() => {
      dropdownMenu.classList.remove("show");
    }, 200); // 200ms delay to prevent flickering
  });

  // Toggle dropdown on avatar click (for mobile/touch devices)
  userAvatar.addEventListener("click", function (e) {
    e.stopPropagation();
    dropdownMenu.classList.toggle("show");
  });

  // Close dropdown when clicking outside
  document.addEventListener("click", function (e) {
    if (!userMenu.contains(e.target)) {
      dropdownMenu.classList.remove("show");
    }
  });

  // Close dropdown when pressing Escape key
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") {
      dropdownMenu.classList.remove("show");
    }
  });

  // Close dropdown when clicking on a dropdown item
  dropdownMenu.addEventListener("click", function () {
    dropdownMenu.classList.remove("show");
  });
  
});

