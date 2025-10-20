        // Add script to show the selected file name
        document.getElementById('logo').addEventListener('change', function() {
            const fileName = this.files[0] ? this.files[0].name : 'No file chosen';
            document.getElementById('fileName').textContent = fileName;
        });

        // Form step navigation functionality
        let currentStep = 1;
        const totalSteps = 5;
        
        function changeStep(step) {
            const steps = document.querySelectorAll('.step');
            
            // Hide current step
            steps[currentStep - 1].classList.remove('active');
            
            // Update current step
            currentStep += step;
            
            // Show new step
            steps[currentStep - 1].classList.add('active');
            
            // Update progress bar
            updateProgressBar();
            
            // Update navigation buttons
            updateNavigationButtons();
        }
        
        function updateProgressBar() {
            const progress = (currentStep / totalSteps) * 100;
            document.getElementById('progressBar').style.width = `${progress}%`;
            document.getElementById('stepIndicator').textContent = `Page ${currentStep} of ${totalSteps}`;
        }
        
        function updateNavigationButtons() {
            const prevBtn = document.getElementById('prevBtn');
            const nextBtn = document.getElementById('nextBtn');
            
            if (currentStep === 1) {
                prevBtn.style.display = 'none';
            } else {
                prevBtn.style.display = 'inline-block';
            }
            
            if (currentStep === totalSteps) {
                nextBtn.style.display = 'none';
            } else {
                nextBtn.style.display = 'inline-block';
            }
        }
        
        // Initialize form
        document.addEventListener('DOMContentLoaded', function() {
            updateProgressBar();
            updateNavigationButtons();
        });
        document.addEventListener('DOMContentLoaded', function() {
    // Read cookie function
    function getCookie(name) {
        const value = `; ${document.cookie}`;
        const parts = value.split(`; ${name}=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
    }
    
    // Display company name
    const companyName = getCookie('pending_company_name');
    if (companyName) {
        document.getElementById('displayCompanyName').textContent = companyName;
    } else {
        console.warn('Company name not found in cookies');
        // Optional: Redirect to signup if name is missing
        // window.location.href = '/signup_page';
    }
});

// Add website validation
// Add website validation
document.addEventListener('DOMContentLoaded', function() {
    const websiteInput = document.getElementById('website');
    const websiteError = document.getElementById('website-error');
    
    if (websiteInput && websiteError) {
        // Validate on form submission
        const form = document.getElementById('companyForm');
        if (form) {
            form.addEventListener('submit', function(e) {
                const websiteValue = websiteInput.value.trim();
                
                if (websiteValue && !isValidWebsite(websiteValue)) {
                    e.preventDefault();
                    showError(websiteInput, websiteError, 'Please enter a valid website URL (example.com) or LinkedIn profile (linkedin.com/in/username)');
                    websiteInput.focus();
                } else {
                    hideError(websiteError);
                    // Remove any invalid styling if field is valid
                    websiteInput.classList.remove('invalid');
                    // Remove the checkmark background image if it exists
                    websiteInput.style.backgroundImage = 'none';
                    // Reset border color
                    websiteInput.style.borderColor = '';
                }
            });
        }
        
        // Validate on input blur (when user leaves the field)
        websiteInput.addEventListener('blur', function() {
            const websiteValue = websiteInput.value.trim();
            
            if (websiteValue && !isValidWebsite(websiteValue)) {
                showError(websiteInput, websiteError, 'Please enter a valid website URL (example.com) or LinkedIn profile (linkedin.com/in/username)');
            } else {
                hideError(websiteError);
                // Remove any invalid styling if field is valid
                websiteInput.classList.remove('invalid');
                // Remove the checkmark background image if it exists
                websiteInput.style.backgroundImage = 'none';
                // Reset border color
                websiteInput.style.borderColor = '';
            }
        });
        
        // Clear error when user starts typing again
        websiteInput.addEventListener('input', function() {
            const websiteValue = websiteInput.value.trim();
            
            if (!websiteValue) {
                // If field is empty, clear everything
                hideError(websiteError);
                websiteInput.classList.remove('invalid');
                websiteInput.style.backgroundImage = 'none';
                websiteInput.style.borderColor = '';
            } else {
                // Only hide error but don't show checkmark until valid
                hideError(websiteError);
                websiteInput.classList.remove('invalid');
                websiteInput.style.backgroundImage = 'none';
                websiteInput.style.borderColor = '';
                
                // If input becomes valid while typing, show the checkmark and green border
                if (isValidWebsite(websiteValue)) {
                    websiteInput.style.backgroundImage = "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='%234bb543' viewBox='0 0 16 16'%3E%3Cpath d='M12.736 3.97a.733.733 0 0 1 1.047 0c.286.289.29.756.01 1.05L7.88 12.01a.733.733 0 0 1-1.065.02L3.217 8.384a.757.757 0 0 1 0-1.06.733.733 0 0 1 1.047 0l3.052 3.093 5.4-6.425a.247.247 0 0 1 .02-.022Z'/%3E%3C/svg%3E\")";
                }
            }
        });
    }
    
    function isValidWebsite(url) {
        if (!url) return true; // Empty is allowed
        
        // Remove any protocol prefix and convert to lowercase
        const cleanUrl = url.toLowerCase().replace(/^(https?:\/\/)?(www\.)?/, '');
        
        // Regular website validation (domain.tld)
        const websitePattern = /^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?)*\.[a-z]{2,}(\/.*)?$/;
        
        // LinkedIn profile validation
        const linkedinPattern1 = /^linkedin\.com\/in\/[a-z0-9\-_]{3,100}(\/.*)?$/; // linkedin.com/in/username
        const linkedinPattern2 = /^linkedin\.com\/company\/[a-z0-9\-_]{3,100}(\/.*)?$/; // linkedin.com/company/companyname
        
        return websitePattern.test(cleanUrl) || 
               linkedinPattern1.test(cleanUrl) || 
               linkedinPattern2.test(cleanUrl);
    }
    
    function showError(input, errorElement, message) {
        errorElement.textContent = message;
        errorElement.style.display = 'block';
        errorElement.classList.add('show');
        input.classList.add('invalid');
        
        // Show error icon instead of checkmark
        input.style.backgroundImage = "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='%23f44336' viewBox='0 0 16 16'%3E%3Cpath d='M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5zm.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2z'/%3E%3C/svg%3E\")";
        
        // Override the green border with red border for invalid inputs
        input.style.borderColor = '#f44336';
        
        // Apply shake animation to match your existing validation
        applyShakeAnimation(input);
        applyShakeAnimation(errorElement);
    }
    
    function hideError(errorElement) {
        errorElement.textContent = '';
        errorElement.style.display = 'none';
        errorElement.classList.remove('show');
    }
    
    function applyShakeAnimation(element) {
        if (!element) return;
        
        // Remove existing animation to allow it to be retriggered
        element.classList.remove('shake-animation');
        
        // Force browser to recognize the removal
        void element.offsetWidth;
        
        // Add the animation class back
        element.classList.add('shake-animation');
        
        // Remove the class after animation completes
        setTimeout(() => {
            element.classList.remove('shake-animation');
        }, 820);
    }
});

// Add phone number validation with proper icon placement
document.addEventListener('DOMContentLoaded', function() {
    const phoneInput = document.getElementById('phone_number');
    const phoneError = document.getElementById('phone_number-error');
    
    if (phoneInput && phoneError) {
        // Validate on form submission
        const form = document.getElementById('companyForm');
        if (form) {
            form.addEventListener('submit', function(e) {
                if (!validatePhoneField()) {
                    e.preventDefault();
                    phoneInput.focus();
                }
            });
        }
        
        // Real-time validation
        phoneInput.addEventListener('input', validatePhoneField);
        phoneInput.addEventListener('blur', validatePhoneField);
    }
    
    function validatePhoneField() {
        const value = phoneInput.value.trim();
        let isValid = true;
        
        // Phone validation pattern - MUST start with + and country code
        const phonePattern = /^\+[1-9]{1}[0-9]{0,3}[-.\s]?\(?[0-9]{1,4}?\)?[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,9}$/;
        
        if (!value) {
            showError('Phone number is required');
            isValid = false;
        } else if (!value.startsWith('+')) {
            showError('Phone number must start with country code (e.g., +1)');
            isValid = false;
        } else if (!phonePattern.test(value)) {
            showError('Please enter a valid international phone number (e.g., +1 555-123-4567)');
            isValid = false;
        } else {
            hideError();
        }
        
        return isValid;
    }
    
    function showError(message) {
        phoneError.textContent = message;
        phoneError.style.display = 'block';
        phoneError.classList.add('show');
        phoneInput.classList.add('invalid');
        
        // Red border and proper warning icon placement
        phoneInput.style.borderColor = '#f44336';
        phoneInput.style.backgroundImage = "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='%23f44336' viewBox='0 0 16 16'%3E%3Cpath d='M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5zm.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2z'/%3E%3C/svg%3E\")";
        phoneInput.style.backgroundRepeat = 'no-repeat';
        phoneInput.style.backgroundPosition = 'right 12px center';
        phoneInput.style.backgroundSize = '16px';
        phoneInput.style.paddingRight = '40px'; // Make space for the icon
        
        applyShakeAnimation(phoneInput);
        applyShakeAnimation(phoneError);
    }
    
    function hideError() {
        phoneError.textContent = '';
        phoneError.style.display = 'none';
        phoneError.classList.remove('show');
        phoneInput.classList.remove('invalid');
        
        // Reset border and background
        phoneInput.style.borderColor = '';
        phoneInput.style.backgroundImage = 'none';
        phoneInput.style.paddingRight = '12px'; // Reset padding
        
        // Add green checkmark if valid
        const value = phoneInput.value.trim();
        const phonePattern = /^\+[1-9]{1}[0-9]{0,3}[-.\s]?\(?[0-9]{1,4}?\)?[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,9}$/;
        
        if (value && phonePattern.test(value)) {
            phoneInput.style.backgroundImage = "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='%234bb543' viewBox='0 0 16 16'%3E%3Cpath d='M12.736 3.97a.733.733 0 0 1 1.047 0c.286.289.29.756.01 1.05L7.88 12.01a.733.733 0 0 1-1.065.02L3.217 8.384a.757.757 0 0 1 0-1.06.733.733 0 0 1 1.047 0l3.052 3.093 5.4-6.425a.247.247 0 0 1 .02-.022Z'/%3E%3C/svg%3E\")";
            phoneInput.style.backgroundRepeat = 'no-repeat';
            phoneInput.style.backgroundPosition = 'right 12px center';
            phoneInput.style.backgroundSize = '16px';
            phoneInput.style.paddingRight = '40px';
        }
    }
    
    function applyShakeAnimation(element) {
        if (!element) return;
        
        element.classList.remove('shake-animation');
        void element.offsetWidth;
        element.classList.add('shake-animation');
        
        setTimeout(() => {
            element.classList.remove('shake-animation');
        }, 820);
    }
});

// Add slogan field validation
document.addEventListener('DOMContentLoaded', function() {
    const sloganInput = document.getElementById('slogan');
    const sloganError = document.getElementById('slogan-error');
    
    if (sloganInput && sloganError) {
        // Validate on form submission
        const form = document.getElementById('companyForm');
        if (form) {
            form.addEventListener('submit', function(e) {
                if (!validateSloganField()) {
                    e.preventDefault();
                    sloganInput.focus();
                }
            });
        }
        
        // Real-time validation
        sloganInput.addEventListener('input', validateSloganField);
        sloganInput.addEventListener('blur', validateSloganField);
    }
    
    function validateSloganField() {
        const value = sloganInput.value.trim();
        let isValid = true;
        
        if (!value) {
            showSloganError('Company slogan is required');
            isValid = false;
        } else {
            hideSloganError();
        }
        
        return isValid;
    }
    
    function showSloganError(message) {
        sloganError.textContent = message;
        sloganError.style.display = 'block';
        sloganError.classList.add('show');
        sloganInput.classList.add('invalid');
        
        // Red border and warning icon
        sloganInput.style.borderColor = '#f44336';
        sloganInput.style.backgroundImage = "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='%23f44336' viewBox='0 0 16 16'%3E%3Cpath d='M8.982 1.566a1.13 1.13 0 0 0-1.96 0L.165 13.233c-.457.778.091 1.767.98 1.767h13.713c.889 0 1.438-.99.98-1.767L8.982 1.566zM8 5c.535 0 .954.462.9.995l-.35 3.507a.552.552 0 0 1-1.1 0L7.1 5.995A.905.905 0 0 1 8 5zm.002 6a1 1 0 1 1 0 2 1 1 0 0 1 0-2z'/%3E%3C/svg%3E\")";
        sloganInput.style.backgroundRepeat = 'no-repeat';
        sloganInput.style.backgroundPosition = 'right 12px center';
        sloganInput.style.backgroundSize = '16px';
        sloganInput.style.paddingRight = '40px';
        
        applyShakeAnimation(sloganInput);
        applyShakeAnimation(sloganError);
    }
    
    function hideSloganError() {
        sloganError.textContent = '';
        sloganError.style.display = 'none';
        sloganError.classList.remove('show');
        sloganInput.classList.remove('invalid');
        
        // Reset styling
        sloganInput.style.borderColor = '';
        sloganInput.style.backgroundImage = 'none';
        sloganInput.style.paddingRight = '12px';
        
        // Add green checkmark if valid
        const value = sloganInput.value.trim();
        if (value) {
            sloganInput.style.backgroundImage = "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' fill='%234bb543' viewBox='0 0 16 16'%3E%3Cpath d='M12.736 3.97a.733.733 0 0 1 1.047 0c.286.289.29.756.01 1.05L7.88 12.01a.733.733 0 0 1-1.065.02L3.217 8.384a.757.757 0 0 1 0-1.06.733.733 0 0 1 1.047 0l3.052 3.093 5.4-6.425a.247.247 0 0 1 .02-.022Z'/%3E%3C/svg%3E\")";
            sloganInput.style.backgroundRepeat = 'no-repeat';
            sloganInput.style.backgroundPosition = 'right 12px center';
            sloganInput.style.backgroundSize = '16px';
            sloganInput.style.paddingRight = '40px';
        }
    }
});



/* *************************** Add for social Liking ///////////////////////////////// */

// Social account linking for edit company form
let linkedAccounts = new Set();
let newSelectedPlatforms = [];
let userLinkedAccounts = {};

// Platform mapping for OAuth
const platformOAuthMap = {
    'LinkedIn': 'linkedin',
    'Facebook': 'facebook',
    'Instagram': 'instagram',
    'YouTube': 'google',
    'TikTok': 'tiktok',
    'WhatsApp': 'whatsapp',
    'Telegram': 'telegram',
    'Snapchat': 'snapchat',
    'Threads': 'threads',
    'X': 'x'
};

// Get user's existing linked accounts
async function getUserLinkedAccounts() {
    try {
        const response = await fetch('/get_user_linked_accounts');
        const data = await response.json();
        return data.linked_accounts || [];
    } catch (error) {
        console.error('Error fetching linked accounts:', error);
        return [];
    }
}

// Get newly selected platforms that aren't linked
function getNewlySelectedPlatforms() {
    const currentPlatforms = '{{ company.preferred_platforms }}'.split(',');
    const newlySelected = [];
    const channelCheckboxes = document.querySelectorAll('input[name="channels"]:checked');
    
    channelCheckboxes.forEach(checkbox => {
        const platform = checkbox.value;
        // Check if this platform is newly selected (not in current platforms)
        if (!currentPlatforms.includes(platform)) {
            newlySelected.push(platform);
        }
    });
    
    return newlySelected;
}

// Check if newly selected platforms are already linked
async function checkNewPlatformsLinkStatus() {
    const newlySelected = getNewlySelectedPlatforms();
    
    if (newlySelected.length === 0) {
        return true; // No new platforms selected
    }
    
    // Get user's existing linked accounts
    const existingAccounts = await getUserLinkedAccounts();
    userLinkedAccounts = {};
    existingAccounts.forEach(account => {
        userLinkedAccounts[account.platform] = account;
    });
    
    // Filter out platforms that are already linked
    newSelectedPlatforms = newlySelected.filter(platform => {
        const platformKey = platformOAuthMap[platform]?.toLowerCase();
        return !userLinkedAccounts[platformKey];
    });
    
    return newSelectedPlatforms.length === 0; // Return true if all new platforms are already linked
}

// Show social linking modal for new platforms
async function showSocialLinkingModal() {
    // Populate the modal with new platforms that need linking
    const container = document.getElementById('selectedPlatformsContainer');
    container.innerHTML = '';
    
    newSelectedPlatforms.forEach(platform => {
        const platformKey = platformOAuthMap[platform]?.toLowerCase();
        
        const platformCard = document.createElement('div');
        platformCard.className = `platform-card ${platformKey}`;
        platformCard.dataset.platform = platform;
        
        platformCard.innerHTML = `
            <div class="platform-icon">
                <i class="fab fa-${platformKey}"></i>
            </div>
            <div class="platform-name">${platform}</div>
            <div class="platform-status">Click to connect</div>
            <div class="checkmark">✓</div>
        `;
        
        platformCard.addEventListener('click', () => connectPlatform(platform));
        container.appendChild(platformCard);
    });
    
    // Reset linking state
    linkedAccounts.clear();
    updateProceedButton();
    updateLinkingProgress();
    
    // Show modal
    document.getElementById('socialLinkingModal').style.display = 'block';
}

// Connect platform (opens OAuth window)
function connectPlatform(platform) {
    const platformCard = document.querySelector(`.platform-card[data-platform="${platform}"]`);
    const platformKey = platformOAuthMap[platform]?.toLowerCase();
    
    // Check if already connected
    if (linkedAccounts.has(platform)) {
        return;
    }
    
    // Show connecting status
    platformCard.querySelector('.platform-status').textContent = 'Connecting...';
    platformCard.style.opacity = '0.7';
    
    // Determine OAuth endpoint based on platform
    let oauthEndpoint;
    
    switch (platformKey) {
        case 'linkedin':
            oauthEndpoint = '/linkedin/login?source=edit';
            break;
        case 'facebook':
        case 'instagram':
            oauthEndpoint = '/meta/login?source=edit';
            break;
        default:
            // For platforms not yet implemented
            setTimeout(() => {
                platformCard.querySelector('.platform-status').textContent = 'Coming Soon';
                platformCard.style.opacity = '1';
            }, 1000);
            return;
    }
    
    // Open OAuth window
    const oauthWindow = window.open(
        oauthEndpoint,
        `${platform} OAuth`,
        'width=600,height=700,scrollbars=yes'
    );
    
    // Check for OAuth completion
    const checkOAuthCompletion = setInterval(() => {
        if (oauthWindow.closed) {
            clearInterval(checkOAuthCompletion);
            checkPlatformConnection(platform, platformCard);
        }
    }, 1000);
}

// Check if platform was successfully connected
async function checkPlatformConnection(platform, platformCard) {
    try {
        // Refresh linked accounts
        const existingAccounts = await getUserLinkedAccounts();
        const platformKey = platformOAuthMap[platform]?.toLowerCase();
        const isNowConnected = existingAccounts.some(account => account.platform === platformKey);
        
        if (isNowConnected) {
            platformCard.classList.add('connected');
            platformCard.querySelector('.platform-status').textContent = 'Connected';
            platformCard.style.opacity = '1';
            
            linkedAccounts.add(platform);
            updateProceedButton();
            updateLinkingProgress();
        } else {
            platformCard.querySelector('.platform-status').textContent = 'Failed - Click to retry';
            platformCard.style.opacity = '1';
        }
    } catch (error) {
        platformCard.querySelector('.platform-status').textContent = 'Error - Click to retry';
        platformCard.style.opacity = '1';
    }
}

// Update proceed button state
function updateProceedButton() {
    const proceedBtn = document.getElementById('proceedToSaveBtn');
    const allConnected = newSelectedPlatforms.every(platform => linkedAccounts.has(platform));
    
    proceedBtn.disabled = !allConnected;
    
    if (allConnected) {
        proceedBtn.innerHTML = '<i class="fas fa-save"></i> Save Changes';
    } else {
        const connectedCount = linkedAccounts.size;
        const totalCount = newSelectedPlatforms.length;
        proceedBtn.innerHTML = `<i class="fas fa-link"></i> Connect ${totalCount - connectedCount} More to Save`;
    }
}

// Update linking progress
function updateLinkingProgress() {
    const progressBar = document.getElementById('linkingProgressBar');
    const progressText = document.getElementById('progressText');
    const connectedCount = linkedAccounts.size;
    const totalCount = newSelectedPlatforms.length;
    const progress = (connectedCount / totalCount) * 100;
    
    progressBar.style.width = `${progress}%`;
    progressText.textContent = `${connectedCount} of ${totalCount} connected`;
}

// Modal event handlers
function setupModalHandlers() {
    const modal = document.getElementById('socialLinkingModal');
    const closeBtn = modal.querySelector('.close-modal');
    const skipBtn = document.getElementById('skipLinkingBtn');
    const proceedBtn = document.getElementById('proceedToSaveBtn');
    
    // Close modal
    closeBtn.addEventListener('click', () => {
        modal.style.display = 'none';
    });
    
    // Skip linking and submit form
    skipBtn.addEventListener('click', () => {
        modal.style.display = 'none';
        submitForm();
    });
    
    // Proceed to save after linking
    proceedBtn.addEventListener('click', () => {
        modal.style.display = 'none';
        submitForm();
    });
    
    // Close modal when clicking outside
    window.addEventListener('click', (event) => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
}

// Submit the form
function submitForm() {
    const form = document.getElementById('companyForm');
    form.submit();
}

// Override form submission
document.addEventListener('DOMContentLoaded', function() {
    setupModalHandlers();
    
    const form = document.getElementById('companyForm');
    const saveBtn = document.getElementById('saveBtn');
    
    // Replace the save button click handler
    saveBtn.addEventListener('click', async function(e) {
        e.preventDefault();
        
        // First validate the form
        let isFormValid = true;
        // Check if there are new platforms that need linking
        const allNewPlatformsLinked = await checkNewPlatformsLinkStatus();
        
        if (!allNewPlatformsLinked && newSelectedPlatforms.length > 0) {
            // Show modal to link new platforms
            showSocialLinkingModal();
        } else {
            // All new platforms are already linked or no new platforms, submit form
            submitForm();
        }
    });
});