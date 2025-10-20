// Additional JavaScript for the edit strategy page
document.addEventListener("DOMContentLoaded", function () {
  // Add sidebar toggle functionality if not already in CompanyDetails.js
  //const sidebarToggle = document.querySelector(".sidebar-toggle");
  //const sidebar = document.querySelector(".sidebar");

  //if (sidebarToggle && sidebar) {
    //sidebarToggle.addEventListener("click", function () {
     // sidebar.classList.toggle("active");
   // });
//  }

  // User dropdown functionality
  const userAvatar = document.getElementById("userAvatar");
  const dropdownMenu = document.getElementById("dropdownMenu");

  if (userAvatar && dropdownMenu) {
    userAvatar.addEventListener("click", function (e) {
      e.stopPropagation();
      dropdownMenu.classList.toggle("active");
    });

    // Close dropdown when clicking elsewhere
    document.addEventListener("click", function () {
      dropdownMenu.classList.remove("active");
    });
  }

  // Auto-resize textarea as user types
  const textarea = document.getElementById("strategy-content");
  if (textarea) {
    textarea.addEventListener("input", function () {
      this.style.height = "auto";
      this.style.height = this.scrollHeight + "px";
    });

    // Trigger initial resize
    textarea.dispatchEvent(new Event("input"));
  }

  const backToTopButton = document.getElementById("backToTop");

  if (backToTopButton) {
    // Show/hide back to top button based on scroll position
    window.addEventListener("scroll", function () {
      if (window.pageYOffset > 300) {
        backToTopButton.classList.add("show");
      } else {
        backToTopButton.classList.remove("show");
      }
    });

    // Smooth scroll to top when clicked
    backToTopButton.addEventListener("click", function (e) {
      e.preventDefault();
      window.scrollTo({
        top: 0,
        behavior: "smooth",
      });
    });
  }
});
