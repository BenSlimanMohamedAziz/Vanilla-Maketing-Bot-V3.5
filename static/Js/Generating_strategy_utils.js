class StrategyNotificationManager {
    constructor() {
        this.eventSource = null;
        this.notificationElement = null;
        this.checkInterval = null;
        this.pollInterval = null;
        this.statusCheckInterval = null;
        this.autoCheckInterval = null;
        this.failureCount = 0;
        this.maxFailures = 3;
        this.currentStrategyId = null;
        this.userCompanies = []; // Store user's companies
        this.init();
    }

    async init() {
        this.createNotificationElement();
        this.checkActiveGeneration();
        
        // Load user's companies first, then start auto-check
        await this.loadUserCompanies();
        this.startAutoGenerationCheck();
        
        window.addEventListener('storage', (e) => {
            if (e.key === 'strategy_generation') {
                this.handleStorageChange(e.newValue);
            }
        });

        this.checkInterval = setInterval(() => {
            this.checkActiveGeneration();
        }, 5000);
        
        window.addEventListener('beforeunload', () => {
            this.cleanup();
        });
    }

    // NEW: Load user's companies from backend
    async loadUserCompanies() {
        try {
            console.log('Loading user companies...');
            const response = await fetch('/get_user_companies');
            if (!response.ok) throw new Error('Failed to fetch companies');
            
            const data = await response.json();
            this.userCompanies = data.companies || [];
            console.log('Loaded companies:', this.userCompanies);
        } catch (error) {
            console.error('Error loading user companies:', error);
            this.userCompanies = [];
        }
    }

    // FIXED: Auto-generation check that works globally
    startAutoGenerationCheck() {
        // Check every 1 minute for auto-generation
        this.autoCheckInterval = setInterval(() => {
            this.checkAndAutoGenerateStrategy();
        }, 60 * 1000);
        
        // Also check immediately after companies are loaded
        setTimeout(() => {
            this.checkAndAutoGenerateStrategy();
        }, 5000);
    }

    // FIXED: Check ALL companies for auto-generation
    async checkAndAutoGenerateStrategy() {
        if (this.userCompanies.length === 0) {
            console.log('No companies found for user');
            return;
        }

        console.log(`Checking ${this.userCompanies.length} companies for auto-generation...`);

        for (const company of this.userCompanies) {
            try {
                console.log(`Checking company: ${company.name} (ID: ${company.id})`);
                
                // Get the last approved strategy date from backend
                const response = await fetch(`/get_last_approved_strategy_date/${company.id}`);
                if (!response.ok) {
                    console.log(`Failed to fetch strategy date for company ${company.id}`);
                    continue;
                }
                
                const data = await response.json();
                
                if (data.approved_date) {
                    const approvedDate = new Date(data.approved_date);
                    const currentDate = new Date();
                    
                    // Calculate month difference
                    const monthsDiff = (currentDate.getFullYear() - approvedDate.getFullYear()) * 12 + 
                                      (currentDate.getMonth() - approvedDate.getMonth());
                    
                    console.log(`Company ${company.name}: Last approved: ${approvedDate}, Months diff: ${monthsDiff}`);
                    
                    // If 1 month or more passed, auto-generate
                    if (monthsDiff >= 1) {
                        console.log(`Auto-generating new strategy for ${company.name} after 1 month`);
                        await this.startAutoGeneration(company.id, company.name);
                        break; // Only generate for one company at a time
                    }
                } else {
                    console.log(`No approved strategy found for ${company.name}`);
                }
            } catch (error) {
                console.error(`Error checking company ${company.id}:`, error);
            }
        }
    }

    // FIXED: Auto-generation starter
    async startAutoGeneration(companyId, companyName) {
        // Don't start if already generating
        const currentData = this.getGenerationData();
        if (currentData && currentData.status === 'generating') {
            console.log('Already generating strategy, skipping auto-generation');
            return;
        }
        
        this.showAutoGenerationNotification(companyName);
        
        // Start the actual generation using the existing method
        this.startGeneration(companyId);
    }

    // FIXED: Show auto-generation specific notification
    showAutoGenerationNotification(companyName) {
        // Create a special notification for auto-generation
        const autoNotif = document.createElement('div');
        autoNotif.className = 'auto-generation-notification';
        autoNotif.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-robot"></i>
                <span>Auto-generating monthly strategy for ${companyName}...</span>
            </div>
        `;
        
        // Add styles if not already present
        if (!document.querySelector('#autoGenStyles')) {
            const style = document.createElement('style');
            style.id = 'autoGenStyles';
            style.textContent = `
                .auto-generation-notification {
                    position: fixed;
                    top: 80px;
                    right: 20px;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 12px 16px;
                    border-radius: 8px;
                    box-shadow: 0 4px 15px rgba(0,0,0,0.2);
                    z-index: 9999;
                    animation: slideInRight 0.5s ease-out;
                    font-size: 14px;
                    max-width: 350px;
                }
                .auto-generation-notification .notification-content {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                }
                @keyframes slideInRight {
                    from { transform: translateX(100%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
                @keyframes slideOutRight {
                    from { transform: translateX(0); opacity: 1; }
                    to { transform: translateX(100%); opacity: 0; }
                }
            `;
            document.head.appendChild(style);
        }
        
        document.body.appendChild(autoNotif);
        
        // Remove after 5 seconds
        setTimeout(() => {
            if (autoNotif.parentNode) {
                autoNotif.style.animation = 'slideOutRight 0.5s ease-in';
                setTimeout(() => {
                    if (autoNotif.parentNode) {
                        autoNotif.parentNode.removeChild(autoNotif);
                    }
                }, 500);
            }
        }, 5000);
    }

    // Rest of your methods remain the same...
   /* startGeneration(companyId) {
        // Clear any existing intervals first
        this.cleanup();
        
        const generationData = {
            companyId: companyId,
            status: 'generating',
            startTime: Date.now(),
            currentStep: 'Initializing...',
            progress: 0,
            isAutoGenerated: true
        };
        
        localStorage.setItem('strategy_generation', JSON.stringify(generationData));
        this.failureCount = 0;
        
        // Show initial progress state
        this.updateProgress({
            progress: 0,
            currentStep: 'Starting automatic strategy generation...'
        });
        this.showNotification();
        
        // Start the generation process
        this.makeGenerationRequest(companyId);
    }*/

        // Also modify startGeneration to accept a parameter
    startGeneration(companyId, isManualGeneration = false) {
    // Clear any existing intervals first
    this.cleanup();
    
    const generationData = {
        companyId: companyId,
        status: 'generating',
        startTime: Date.now(),
        currentStep: 'Initializing...',
        progress: 0,
        isAutoGenerated: !isManualGeneration  // Set based on type
    };
    
    localStorage.setItem('strategy_generation', JSON.stringify(generationData));
    this.failureCount = 0;
    
    // Show initial progress state
    const stepText = isManualGeneration ? 
        'Starting strategy generation...' : 
        'Starting automatic monthly strategy generation...';
    
    this.updateProgress({
        progress: 0,
        currentStep: stepText
    });
    this.showNotification();
    
    // Pass the generation type to makeGenerationRequest
    this.makeGenerationRequest(companyId, isManualGeneration);
}

   /* async makeGenerationRequest(companyId) {
        try {
            console.log('Making generation request for company:', companyId);
            
            const response = await fetch(`/generate_strategy/${companyId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Generation failed');
            }
            
            console.log('Generation started successfully:', data);
            
            // Connect to SSE for progress updates
            this.connectSSE(companyId);
            
        } catch (error) {
            console.error('Generation request failed:', error);
            this.showErrorNotification('Failed to start generation: ' + error.message);
        }
    }*/

    async makeGenerationRequest(companyId, isManualGeneration = false) {
        try {
            console.log('makeGenerationRequest called - manual:', isManualGeneration);
            
            // If this is a manual generation, DON'T make API call - CompanyDetails.js already did it
            if (isManualGeneration) {
                console.log('Manual generation detected - skipping API call, connecting to SSE only');
                // Just connect to SSE to track progress
                this.connectSSE(companyId);
                return;
            }
            
            // Only make API call for auto-generations
            console.log('Auto-generation detected - making API call');
            const response = await fetch(`/generate_strategy/${companyId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (!data.success) {
                throw new Error(data.error || 'Generation failed');
            }
            
            console.log('Auto-generation started successfully:', data);
            
            // Connect to SSE for progress updates
            this.connectSSE(companyId);
            
        } catch (error) {
            console.error('Generation request failed:', error);
            this.showErrorNotification('Failed to start generation: ' + error.message);
        }
    }



    // ... include all your other existing methods (createNotificationElement, getGenerationData, checkActiveGeneration, etc.)
    // Make sure to include ALL the methods from your original class

    createNotificationElement() {
        // Your existing createNotificationElement method
        const html = `
            <div id="strategyNotification" class="strategy-notification">
                <div class="notification-content">
                    <div class="notification-header">
                        <span class="notification-title">
                            <i class="fas fa-magic"></i>
                            <span id="notifTitle">Generating Marketing Strategy</span>
                        </span>
                        <button class="notification-close" id="closeNotification">
                            <i class="fas fa-times"></i>
                        </button>
                    </div>
                    <div class="notification-body">
                        <div class="progress-container">
                            <div class="progress-bar" id="notificationProgressBar" style="width: 0%"></div>
                        </div>
                        <div class="status-text" id="statusText">
                            Chahbander is preparing your strategy...
                        </div>
                        <div class="step-indicator" id="stepIndicator">
                            Initializing...
                        </div>
                    </div>
                    <div class="notification-footer" id="notificationFooter">
                        <div class="loading-spinner-small"></div>
                        <span class="time-estimate">Estimated time: 5-15 minutes</span>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', html);
        this.notificationElement = document.getElementById('strategyNotification');

        document.getElementById('closeNotification').addEventListener('click', () => {
            this.hideNotification();
            const data = this.getGenerationData();
            if (data && (data.status === 'completed' || data.status === 'error')) {
                localStorage.removeItem('strategy_generation');
            }
        });
    }

    getGenerationData() {
        const data = localStorage.getItem('strategy_generation');
        return data ? JSON.parse(data) : null;
    }

    async checkActiveGeneration() {
        const generationData = this.getGenerationData();
        if (!generationData) return;

        const age = Date.now() - generationData.startTime;
        
        // Clear stale data (older than 5 minutes)
        if (age > 300000) {
            console.log('Clearing stale generation data');
            localStorage.removeItem('strategy_generation');
            this.hideNotification();
            return;
        }

        // Check if strategy status has changed to completed state
        if (generationData.status === 'completed' && generationData.strategyId) {
            this.currentStrategyId = generationData.strategyId;
            const strategyStatus = await this.checkStrategyStatus(generationData.strategyId);
            
            if (strategyStatus === 'approved' || strategyStatus === 'denied - archived') {
                // Strategy has been processed, remove notification
                localStorage.removeItem('strategy_generation');
                this.hideNotification();
                return;
            }
            
            // Strategy still pending action, show persistent notification
            this.showPersistentNotification(generationData);
            
            // Start periodic status checking
            if (!this.statusCheckInterval) {
                this.startStatusChecking(generationData.strategyId);
            }
        } else if (generationData.status === 'generating') {
            // Show normal progress notification for generating state
            this.restoreProgressState(generationData);
            
            // Verify server is still processing
            const isValid = await this.verifyGenerationStatus(generationData.companyId);
            if (!isValid) {
                this.showErrorNotification('Generation interrupted. Please try again.');
                return;
            }
            
            this.showNotification();
            if (!this.eventSource && !this.pollInterval) {
                this.connectSSE(generationData.companyId);
            }
        } else if (generationData.status === 'error') {
            this.showErrorNotification(generationData.error || 'Generation failed');
        }
    }

    // ... rest of your existing methods (checkStrategyStatus, startStatusChecking, etc.)

    // Make sure all your existing methods are here...
    async checkStrategyStatus(strategyId) {
        try {
            const response = await fetch(`/check_strategy_status_by_id/${strategyId}`);
            if (!response.ok) {
                throw new Error('Failed to check strategy status');
            }
            const data = await response.json();
            return data.status;
        } catch (error) {
            console.error('Error checking strategy status:', error);
            return null;
        }
    }

    startStatusChecking(strategyId) {
        this.statusCheckInterval = setInterval(async () => {
            const status = await this.checkStrategyStatus(strategyId);
            if (status === 'approved' || status === 'denied - archived') {
                // Strategy processed, clean up
                clearInterval(this.statusCheckInterval);
                this.statusCheckInterval = null;
                localStorage.removeItem('strategy_generation');
                this.hideNotification();
            }
        }, 10000);
    }

    showPersistentNotification(generationData) {
        this.notificationElement.classList.remove('success', 'error');
        this.notificationElement.classList.add('visible', 'persistent');
        
        this.updateNotificationContent(
            '<i class="fas fa-check-circle"></i> Strategy Ready',
            'Your marketing strategy has been generated successfully!',
            'Take action to complete the process',
            true
        );
        
        document.getElementById('notificationProgressBar').style.width = '100%';
    }

    restoreProgressState(data) {
        const progress = data.progress || 0;
        const progressBar = document.getElementById('notificationProgressBar');
        if (progressBar) {
            progressBar.style.width = `${progress}%`;
        }
        
        if (data.status === 'generating') {
            const stepIndicator = document.getElementById('stepIndicator');
            if (stepIndicator && data.currentStep) {
                stepIndicator.textContent = data.currentStep;
            }
            
            this.updateNotificationContent(
                'Generating Marketing Strategy',
                'Chahbander is preparing your strategy...',
                data.currentStep || 'Processing...',
                false
            );
        }
    }

    updateNotificationContent(title, statusText, stepText, isPersistent = false) {
        const titleElement = document.getElementById('notifTitle');
        const statusElement = document.getElementById('statusText');
        const stepElement = document.getElementById('stepIndicator');
        const footerElement = document.getElementById('notificationFooter');
        
        if (titleElement) titleElement.innerHTML = title;
        if (statusElement) statusElement.textContent = statusText;
        if (stepElement) stepElement.textContent = stepText;
        
        if (isPersistent) {
            this.notificationElement.classList.add('persistent');
            if (footerElement) {
                footerElement.innerHTML = `
                    <button class="btn btn-primary" id="viewStrategyBtn">
                        <i class="fas fa-eye"></i> View Strategy
                    </button>
                    <span class="time-estimate">Action Required</span>
                `;
                
                document.getElementById('viewStrategyBtn').addEventListener('click', () => {
                    if (this.currentStrategyId) {
                        this.viewStrategy(this.currentStrategyId);
                    }
                });
            }
        } else {
            this.notificationElement.classList.remove('persistent');
            if (footerElement) {
                footerElement.innerHTML = `
                    <div class="loading-spinner-small"></div>
                    <span class="time-estimate">Estimated time: 5-15 minutes</span>
                `;
            }
        }
    }

    async verifyGenerationStatus(companyId) {
        try {
            const response = await fetch(`/check_strategy_status/${companyId}`);
            if (!response.ok) {
                throw new Error('Server unavailable');
            }
            
            const data = await response.json();
            
            if (data.status === 'completed') {
                this.onComplete(data.strategy_id);
                return false;
            }
            
            if (data.status === 'unknown') {
                return false;
            }
            
            this.failureCount = 0;
            return true;
        } catch (error) {
            console.error('Verification failed:', error);
            this.failureCount++;
            
            if (this.failureCount >= this.maxFailures) {
                return false;
            }
            return true;
        }
    }

    connectSSE(companyId) {
        if (this.eventSource) {
            this.eventSource.close();
        }

        this.eventSource = new EventSource(`/strategy_progress/${companyId}`);

        this.eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.updateProgress(data);
                this.failureCount = 0;
            } catch (error) {
                console.error('Error parsing SSE data:', error);
            }
        };

        this.eventSource.addEventListener('complete', (event) => {
            try {
                const data = JSON.parse(event.data);
                this.onComplete(data.strategy_id);
            } catch (error) {
                console.error('Error parsing completion data:', error);
            }
        });

        this.eventSource.onerror = (error) => {
            console.error('SSE Error:', error);
            this.eventSource.close();
            this.eventSource = null;
            
            this.failureCount++;
            
            if (this.failureCount >= this.maxFailures) {
                this.showErrorNotification('Connection lost. Please refresh and try again.');
            } else {
                this.startPolling(companyId);
            }
        };
    }

    startPolling(companyId) {
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
        }

        this.pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/check_strategy_status/${companyId}`);
                
                if (!response.ok) {
                    throw new Error('Server unavailable');
                }
                
                const data = await response.json();
                
                if (data.status === 'completed') {
                    clearInterval(this.pollInterval);
                    this.pollInterval = null;
                    this.onComplete(data.strategy_id);
                } else if (data.status === 'error') {
                    clearInterval(this.pollInterval);
                    this.pollInterval = null;
                    this.showErrorNotification(data.error || 'Generation failed');
                } else if (data.status === 'unknown') {
                    clearInterval(this.pollInterval);
                    this.pollInterval = null;
                    this.showErrorNotification('Generation session lost');
                } else if (data.currentStep || data.progress !== undefined) {
                    this.updateProgress(data);
                    this.failureCount = 0;
                }
            } catch (error) {
                console.error('Polling error:', error);
                this.failureCount++;
                
                if (this.failureCount >= this.maxFailures) {
                    clearInterval(this.pollInterval);
                    this.pollInterval = null;
                    this.showErrorNotification('Server connection lost');
                }
            }
        }, 3000);
    }

    updateProgress(data) {
        const { progress, currentStep } = data;
        
        const progressBar = document.getElementById('notificationProgressBar');
        if (progressBar && progress !== undefined) {
            progressBar.style.width = `${progress}%`;
        }
        
        const stepIndicator = document.getElementById('stepIndicator');
        if (stepIndicator && currentStep) {
            stepIndicator.textContent = currentStep;
        }
        
        const generationData = this.getGenerationData();
        if (generationData) {
            generationData.currentStep = currentStep;
            generationData.progress = progress || generationData.progress || 0;
            localStorage.setItem('strategy_generation', JSON.stringify(generationData));
        }
    }

    onComplete(strategyId) {
        this.cleanup();

        const generationData = {
            status: 'completed',
            strategyId: strategyId,
            completedAt: Date.now()
        };
        localStorage.setItem('strategy_generation', JSON.stringify(generationData));

        this.showPersistentNotification(generationData);
        this.currentStrategyId = strategyId;
        this.startStatusChecking(strategyId);
    }

    showNotification() {
        this.notificationElement.classList.remove('success', 'error', 'persistent');
        this.notificationElement.classList.add('visible');
    }

    hideNotification() {
        this.notificationElement.classList.remove('visible');
    }

    showErrorNotification(message) {
        this.cleanup();
        
        const generationData = {
            status: 'error',
            error: message,
            timestamp: Date.now()
        };
        localStorage.setItem('strategy_generation', JSON.stringify(generationData));
        
        this.hideNotification();
        
        setTimeout(() => {
            this.notificationElement.classList.add('error', 'visible');
            document.getElementById('notifTitle').innerHTML = '<i class="fas fa-exclamation-circle"></i> Generation Failed';
            document.getElementById('statusText').textContent = message;
            document.getElementById('stepIndicator').style.display = 'none';
            
            const footer = document.getElementById('notificationFooter');
            footer.innerHTML = `
                <button class="btn btn-secondary" onclick="window.strategyNotification.dismissError()">
                    <i class="fas fa-times"></i> Dismiss
                </button>
            `;
        }, 300);
    }

    dismissError() {
        localStorage.removeItem('strategy_generation');
        this.hideNotification();
    }

    viewStrategy(strategyId) {
        window.location.href = `/strategy/${strategyId}`;
    }

    handleStorageChange(newValue) {
        if (!newValue) {
            this.hideNotification();
            this.cleanup();
            return;
        }

        const data = JSON.parse(newValue);
        if (data.status === 'generating') {
            this.restoreProgressState(data);
            this.showNotification();
            if (!this.eventSource && !this.pollInterval) {
                this.connectSSE(data.companyId);
            }
        } else if (data.status === 'completed') {
            this.showPersistentNotification(data);
            this.currentStrategyId = data.strategyId;
            this.startStatusChecking(data.strategyId);
        } else if (data.status === 'error') {
            this.showErrorNotification(data.error || 'Generation failed');
        }
    }

    cleanup() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
        if (this.statusCheckInterval) {
            clearInterval(this.statusCheckInterval);
            this.statusCheckInterval = null;
        }
        if (this.autoCheckInterval) {
            clearInterval(this.autoCheckInterval);
            this.autoCheckInterval = null;
        }
    }
}

// Initialize globally
window.strategyNotification = new StrategyNotificationManager();