// Toggle sidebar on mobile
document
  .querySelector(".sidebar-toggle")
  .addEventListener("click", function () {
    document.querySelector(".sidebar").classList.toggle("active");
  });

// Highlight active menu item based on current URL
document.addEventListener("DOMContentLoaded", function () {
  const currentUrl = window.location.pathname + window.location.hash;
  const menuLinks = document.querySelectorAll(".sidebar-menu a");

  menuLinks.forEach((link) => {
    const linkUrl = link.getAttribute("href");

    // Check if link URL matches current URL
    if (
      currentUrl.includes(linkUrl) ||
      (linkUrl === "#company-profile" && currentUrl.includes("/company/"))
    ) {
      link.classList.add("active");
    }

    // Special case for hash links when on the same page
    if (window.location.hash && linkUrl === window.location.hash) {
      link.classList.add("active");
    }
  });
});

// Handle menu clicks and scroll-based active states
document.addEventListener("DOMContentLoaded", function () {
  const menuLinks = document.querySelectorAll(".sidebar-menu a");
  let lastClickTime = 0;
  const CLICK_OVERRIDE_DURATION = 1000; // 1 second

  // Handle menu clicks
  menuLinks.forEach((link) => {
    link.addEventListener("click", function (e) {
      lastClickTime = Date.now();
      // Remove active class from all links
      menuLinks.forEach((l) => l.classList.remove("active"));
      // Add active class to clicked link
      this.classList.add("active");
    });
  });

  // Intersection observer for scroll-based activation
  const observer = new IntersectionObserver(
    (entries) => {
      // Don't update if user just clicked a menu item
      if (Date.now() - lastClickTime < CLICK_OVERRIDE_DURATION) {
        return;
      }

      // Get all currently intersecting sections
      const intersectingSections = entries.filter(
        (entry) => entry.isIntersecting
      );

      if (intersectingSections.length > 0) {
        // Sort by intersection ratio and position (top sections first)
        intersectingSections.sort((a, b) => {
          const aTop = a.target.offsetTop;
          const bTop = b.target.offsetTop;
          const scrollTop =
            window.pageYOffset || document.documentElement.scrollTop;

          // If we're near the top, prioritize sections closer to top
          if (scrollTop < 100) {
            return aTop - bTop;
          }

          // Otherwise, prioritize by intersection ratio
          return b.intersectionRatio - a.intersectionRatio;
        });

        const topSection = intersectingSections[0];
        const sectionId = topSection.target.id;

        // Remove active class from all links
        menuLinks.forEach((link) => link.classList.remove("active"));

        // Special handling for Strategies section
        if (sectionId === "Strategies") {
          const strategiesLink = document.querySelector(
            '.sidebar-menu a[href*="#Strategies"]'
          );
          if (strategiesLink) {
            strategiesLink.classList.add("active");
          }
        } else {
          // Find and activate the corresponding menu link for other sections
          const matchingLink = document.querySelector(
            `.sidebar-menu a[href="#${sectionId}"]`
          );
          if (matchingLink) {
            matchingLink.classList.add("active");
          }
        }
      }
    },
    {
      threshold: [0.1, 0.3, 0.5],
      rootMargin: "-50px 0px -50px 0px", // Adjust when sections are considered "active"
    }
  );

  // Observe all sections that have corresponding menu links
  document.querySelectorAll("[id]").forEach((section) => {
    const sectionId = section.id;
    // Check if there's a menu link for this section (including the special Strategies case)
    const menuLink =
      document.querySelector(`.sidebar-menu a[href="#${sectionId}"]`) ||
      (sectionId === "Strategies" &&
        document.querySelector('.sidebar-menu a[href*="#Strategies"]'));
    if (menuLink) {
      observer.observe(section);
    }
  });
});
document.addEventListener("DOMContentLoaded", function () {
  // New dropdown functionality
  const userAvatar = document.getElementById("userAvatar");
  const dropdownMenu = document.getElementById("dropdownMenu");
  const userMenu = document.querySelector(".user-menu");

  if (userAvatar && dropdownMenu) {
    // Toggle dropdown on avatar click
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

    // Close dropdown when clicking on a dropdown item (for navigation)
    const dropdownItems = dropdownMenu.querySelectorAll(".dropdown-item");
    dropdownItems.forEach((item) => {
      item.addEventListener("click", function () {
        dropdownMenu.classList.remove("show");
      });
    });

    // Handle hover behavior on desktop (optional - works alongside click)
    if (window.innerWidth > 768) {
      userMenu.addEventListener("mouseenter", function () {
        dropdownMenu.classList.add("show");
      });

      userMenu.addEventListener("mouseleave", function () {
        // Small delay to allow moving to dropdown
        setTimeout(() => {
          if (!userMenu.matches(":hover")) {
            dropdownMenu.classList.remove("show");
          }
        }, 100);
      });
    }
  }
});

document.addEventListener('DOMContentLoaded', function() {
    // Function to handle tag animations
    function initTagAnimations() {
        const tags = document.querySelectorAll('.tag');
        
        tags.forEach(tag => {
            // Add a slight delay for staggered animation
            const delay = Math.random() * 200;
            
            // Initial state for animation
            tag.style.opacity = '0';
            tag.style.transform = 'translateY(10px)';
            
            // Animate in
            setTimeout(() => {
                tag.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
                tag.style.opacity = '1';
                tag.style.transform = 'translateY(0)';
            }, delay);
            
            // Enhanced hover effect
            tag.addEventListener('mouseenter', function() {
                this.style.transform = 'translateY(-3px) scale(1.05)';
                this.style.boxShadow = '0 6px 12px rgba(0,0,0,0.15)';
            });
            
            tag.addEventListener('mouseleave', function() {
                this.style.transform = 'translateY(0) scale(1)';
                this.style.boxShadow = '0 2px 4px rgba(0,0,0,0.1)';
            });
        });
    }
    
    // Initialize tag animations
    initTagAnimations();
    
    // Handle responsive behavior for tags container
    function handleResponsiveTags() {
        const tagsContainers = document.querySelectorAll('.tags-container');
        const screenWidth = window.innerWidth;
        
        tagsContainers.forEach(container => {
            if (screenWidth < 480) {
                container.style.gap = '4px';
                const tags = container.querySelectorAll('.tag');
                tags.forEach(tag => {
                    tag.style.padding = '4px 8px';
                    tag.style.fontSize = '0.75rem';
                });
            } else {
                container.style.gap = '8px';
                const tags = container.querySelectorAll('.tag');
                tags.forEach(tag => {
                    tag.style.padding = '6px 12px';
                    tag.style.fontSize = '0.85rem';
                });
            }
        });
    }
    
    // Initial call and window resize listener
    handleResponsiveTags();
    window.addEventListener('resize', handleResponsiveTags);
});



//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
//////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////


// This to handle the strategy gen bg and notif ///

// Strategy Generation Handler
document.addEventListener('DOMContentLoaded', function() {
    const generateForm = document.querySelector('form[action*="/strategy/new/"]');
    
    if (generateForm) {
        generateForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Extract company ID from the action URL
            const actionUrl = this.getAttribute('action');
            const companyId = actionUrl.match(/\/strategy\/new\/(\d+)/)[1];
            
            startStrategyGeneration(companyId);
        });
    }
});

/*function startStrategyGeneration(companyId) {
    // Start notification
    if (window.strategyNotification) {
        window.strategyNotification.startGeneration(companyId);
    }
    
    // Make API call
    fetch(`/generate_strategy/${companyId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success) {
            throw new Error(data.error || 'Generation failed');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Failed to start generation: ' + error.message);
        localStorage.removeItem('strategy_generation');
        
        // Hide notification on error
        if (window.strategyNotification) {
            window.strategyNotification.hideNotification();
        }
    });
}*/

function startStrategyGeneration(companyId) {
    console.log('Starting strategy generation for company:', companyId);
    
    // Start notification - tell it this is MANUAL generation
    if (window.strategyNotification) {
        // Pass true to indicate manual generation
        window.strategyNotification.startGeneration(companyId, true);
    }
    
    // Make API call
    fetch(`/generate_strategy/${companyId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success) {
            throw new Error(data.error || 'Generation failed');
        }
        console.log('Generation started successfully');
    })
    .catch(error => {
        console.error('Error:', error);
        // Re-enable button and cleanup
        window.strategyGenerationInProgress = false;
        const submitButton = document.querySelector('form[action*="/strategy/new/"] button[type="submit"]');
        if (submitButton) {
            submitButton.disabled = false;
            submitButton.innerHTML = '<i class="fas fa-magic"></i> Generate New Strategy With Chahbander';
        }
        
        alert('Failed to start generation: ' + error.message);
        localStorage.removeItem('strategy_generation');
        
        // Hide notification on error
        if (window.strategyNotification) {
            window.strategyNotification.hideNotification();
        }
    });
}
