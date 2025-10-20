        // Sidebar toggle functionality
        document.addEventListener('DOMContentLoaded', function() {
            const sidebarToggle = document.querySelector('.sidebar-toggle');
            const sidebar = document.querySelector('.sidebar');
            
            // Toggle sidebar on button click
            sidebarToggle.addEventListener('click', function() {
                sidebar.classList.toggle('active');
            });
            
            // Close sidebar when clicking outside on mobile
            document.addEventListener('click', function(event) {
                if (window.innerWidth <= 992 && 
                    !sidebar.contains(event.target) && 
                    !sidebarToggle.contains(event.target)) {
                    sidebar.classList.remove('active');
                }
            });
                // User dropdown functionality
    const userAvatar = document.getElementById('userAvatar');
    const dropdownMenu = document.getElementById('dropdownMenu');
    const userMenu = document.querySelector('.user-menu');
    let hoverTimeout;
    
    // Show dropdown on hover
    userMenu.addEventListener('mouseenter', function() {
        clearTimeout(hoverTimeout);
        dropdownMenu.classList.add('show');
    });
    
    // Hide dropdown on mouse leave with slight delay
    userMenu.addEventListener('mouseleave', function() {
        hoverTimeout = setTimeout(() => {
            dropdownMenu.classList.remove('show');
        }, 200); // 200ms delay to prevent flickering
    });
    
    // Toggle dropdown on avatar click (for mobile/touch devices)
    userAvatar.addEventListener('click', function(e) {
        e.stopPropagation();
        dropdownMenu.classList.toggle('show');
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!userMenu.contains(e.target)) {
            dropdownMenu.classList.remove('show');
        }
    });
    
    // Close dropdown when pressing Escape key
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            dropdownMenu.classList.remove('show');
        }
    });
    
    // Close dropdown when clicking on a dropdown item
    dropdownMenu.addEventListener('click', function() {
        dropdownMenu.classList.remove('show');
    });
            // Run greeting function
            updateGreeting();
            setInterval(updateGreeting, 60000);
        });

// Social Media Analytics Dashboard
document.addEventListener('DOMContentLoaded', function() {
    // Initialize analytics dashboard
    initAnalyticsDashboard();
});

function initAnalyticsDashboard() {
    // Platform toggle functionality
    const toggleButtons = document.querySelectorAll('.toggle-btn');
    const analyticsSections = document.querySelectorAll('.platform-analytics');
    const linkedinPeriodSelect = document.getElementById('linkedin-period');
    const refreshLinkedinBtn = document.getElementById('refresh-linkedin');

    // Facebook period selector
    const facebookPeriodSelect = document.getElementById('facebook-period');
    const refreshFacebookBtn = document.getElementById('refresh-facebook');

    if (facebookPeriodSelect) {
        facebookPeriodSelect.addEventListener('change', function() {
            loadFacebookData(parseInt(this.value));
        });
    }
    
    if (refreshFacebookBtn) {
        refreshFacebookBtn.addEventListener('click', function() {
            const selectedDays = parseInt(facebookPeriodSelect.value);
            loadFacebookData(selectedDays);
        });
    }

    if (linkedinPeriodSelect) {
        linkedinPeriodSelect.addEventListener('change', function() {
            loadLinkedInData(parseInt(this.value));
        });
    }

    if (refreshLinkedinBtn) {
        refreshLinkedinBtn.addEventListener('click', function() {
            const selectedDays = parseInt(linkedinPeriodSelect.value);
            loadLinkedInData(selectedDays);
        });
    }
    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const platform = this.dataset.platform;
            
            // Update active button
            toggleButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            
            // Show corresponding analytics
            analyticsSections.forEach(section => {
                section.classList.remove('active');
                if (section.id === `${platform}-analytics`) {
                    section.classList.add('active');
                    
                    // Load data for this platform if not already loaded
                    if (!section.dataset.loaded) {
                        loadPlatformData(platform);
                        section.dataset.loaded = true;
                    }
                }
            });
        });
    });
    
    // Instagram period selector
    const instagramPeriodSelect = document.getElementById('instagram-period');
    const refreshInstagramBtn = document.getElementById('refresh-instagram');
    
    if (instagramPeriodSelect) {
        instagramPeriodSelect.addEventListener('change', function() {
            loadInstagramData(parseInt(this.value));
        });
    }
    
    if (refreshInstagramBtn) {
        refreshInstagramBtn.addEventListener('click', function() {
            const selectedDays = parseInt(instagramPeriodSelect.value);
            loadInstagramData(selectedDays);
        });
    }
    
    // Load Facebook data by default
    loadPlatformData('facebook');
    document.getElementById('facebook-analytics').dataset.loaded = true;
}

// Update the loadPlatformData function
async function loadPlatformData(platform) {
    if (platform === 'facebook') {
        const selectedDays = parseInt(document.getElementById('facebook-period').value) || 30;
        await loadFacebookData(selectedDays);
    } else if (platform === 'instagram') {
        const selectedDays = parseInt(document.getElementById('instagram-period').value) || 14;
        await loadInstagramData(selectedDays);
    } else if (platform === 'linkedin') {
        const selectedDays = parseInt(document.getElementById('linkedin-period').value) || 30;
        await loadLinkedInData(selectedDays);
    }
}

// Update the loadFacebookData function to accept days parameter
async function loadFacebookData(days = 30) {
    try {
        setLoadingState('facebook', true);
        
        // Update period selector if needed
        const periodSelect = document.getElementById('facebook-period');
        if (periodSelect && parseInt(periodSelect.value) !== days) {
            periodSelect.value = days;
        }
        
        const response = await fetch(`/get_facebook_analytics?days=${days}`);
        const data = await response.json();
        
        if (data.error) {
            console.error('Error loading Facebook data:', data.error);
            showErrorState('facebook', data.error);
            return;
        }
        
        updateFacebookUI(data, days);
        renderFacebookCharts(data);
        
    } catch (error) {
        console.error('Failed to load Facebook analytics:', error);
        showErrorState('facebook', 'Failed to load data');
    } finally {
        setLoadingState('facebook', false);
    }
}

async function loadInstagramData(days = 14) {
    try {
        setLoadingState('instagram', true);
        
        // Add loading animation to refresh button
        const refreshBtn = document.getElementById('refresh-instagram');
        if (refreshBtn) {
            refreshBtn.classList.add('loading');
        }
        
        const response = await fetch(`/get_instagram_analytics?days=${days}`);
        const data = await response.json();
        
        if (data.error) {
            console.error('Error loading Instagram data:', data.error);
            showErrorState('instagram', data.error);
            return;
        }
        
        updateInstagramUI(data);
        renderInstagramCharts(data);
        
    } catch (error) {
        console.error('Failed to load Instagram analytics:', error);
        showErrorState('instagram', 'Failed to load data');
    } finally {
        setLoadingState('instagram', false);
        
        // Remove loading animation from refresh button
        const refreshBtn = document.getElementById('refresh-instagram');
        if (refreshBtn) {
            refreshBtn.classList.remove('loading');
        }
    }
}

// Update the updateFacebookUI function
function updateFacebookUI(data, days = 30) {
    document.getElementById('fb-total-fans').textContent = formatNumber(data.page_fans);
    document.getElementById('fb-total-impressions').textContent = formatNumber(data.page_impressions);
    document.getElementById('fb-total-engagement').textContent = formatNumber(data.page_engagement);
    document.getElementById('fb-growth-rate').textContent = `${data.growth_rate}%`;
    
    // Update the period indicators
    document.getElementById('fb-period-days').textContent = days;
    document.getElementById('fb-engagement-days').textContent = days;
}

function updateInstagramUI(data) {
    // Update main metrics
    document.getElementById('ig-total-followers').textContent = formatNumber(data.followers_count);
    document.getElementById('ig-total-views').textContent = formatNumber(data.total_views);
    document.getElementById('ig-accounts-reached').textContent = formatNumber(data.accounts_reached);
    document.getElementById('ig-growth-rate').textContent = `${data.growth_rate}%`;
    
    // Update Instagram-specific insights
    document.getElementById('ig-profile-views').textContent = formatNumber(data.profile_views);
    
    // Update content breakdown
    if (data.content_breakdown) {
        document.getElementById('ig-stories-percent').textContent = `${data.content_breakdown.stories_percentage}%`;
        document.getElementById('ig-posts-percent').textContent = `${data.content_breakdown.posts_percentage}%`;
    }
}
async function loadLinkedInData(days = 30) {
    try {
        setLoadingState('linkedin', true);
        
        const refreshBtn = document.getElementById('refresh-linkedin');
        if (refreshBtn) {
            refreshBtn.classList.add('loading');
        }
        
        const response = await fetch(`/get_linkedin_analytics?days=${days}`);
        const data = await response.json();
        
        if (data.error) {
            console.error('Error loading LinkedIn data:', data.error);
            showErrorState('linkedin', data.error);
            return;
        }
        
        updateLinkedInUI(data);
        renderLinkedInCharts(data);
        
    } catch (error) {
        console.error('Failed to load LinkedIn analytics:', error);
        showErrorState('linkedin', 'Failed to load data');
    } finally {
        setLoadingState('linkedin', false);
        
        const refreshBtn = document.getElementById('refresh-linkedin');
        if (refreshBtn) {
            refreshBtn.classList.remove('loading');
        }
    }
}

function updateLinkedInUI(data) {
    document.getElementById('ln-connections').textContent = formatNumber(data.connections);
    document.getElementById('ln-profile-views').textContent = formatNumber(data.profile_views);
    document.getElementById('ln-post-impressions').textContent = formatNumber(data.post_impressions);
    document.getElementById('ln-engagement-rate').textContent = `${data.engagement_rate}%`;
    document.getElementById('ln-growth-rate').textContent = `${data.growth_rate}%`;
    
    // Update industry breakdown
    document.getElementById('ln-tech-percent').textContent = `${data.industry_data.tech}%`;
    document.getElementById('ln-finance-percent').textContent = `${data.industry_data.finance}%`;
}

function renderLinkedInCharts(data) {
    // Connections Growth Chart
    renderLinkedInChart(
        'ln-connections-chart',
        'Connections Growth',
        data.connections_data.labels,
        [{
            label: 'Connections',
            data: data.connections_data.values,
            borderColor: '#0077B5',
            backgroundColor: 'rgba(0, 119, 181, 0.1)',
            fill: true,
            tension: 0.3,
            pointRadius: 3,
            borderWidth: 2
        }],
        'Connections'
    );
    
    // Views & Impressions Chart
    renderLinkedInChart(
        'ln-views-impressions-chart',
        'Profile Views & Post Impressions',
        data.views_data.labels,
        [
            {
                label: 'Profile Views',
                data: data.views_data.values,
                borderColor: '#0077B5',
                backgroundColor: 'rgba(0, 119, 181, 0.15)',
                fill: true,
                tension: 0.3
            },
            {
                label: 'Post Impressions',
                data: data.impressions_data.values,
                borderColor: '#005885',
                backgroundColor: 'rgba(0, 88, 133, 0.15)',
                fill: true,
                tension: 0.3
            }
        ],
        'Count'
    );
}

function renderLinkedInChart(elementId, title, labels, datasets, yAxisLabel) {
    const ctx = document.getElementById(elementId).getContext('2d');
    
    if (window[`${elementId}Chart`]) {
        window[`${elementId}Chart`].destroy();
    }
    
    window[`${elementId}Chart`] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: title,
                    font: { size: 14, weight: 'bold' },
                    color: '#0077B5'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0, 119, 181, 0.9)',
                    titleColor: 'white',
                    bodyColor: 'white'
                },
                legend: {
                    position: 'bottom',
                    labels: { usePointStyle: true, padding: 20 }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: { display: true, text: yAxisLabel },
                    grid: { color: 'rgba(0, 119, 181, 0.1)' }
                },
                x: { grid: { display: false } }
            }
        }
    });
}
function renderFacebookCharts(data) {
    // Fans Growth Chart
    renderLineChart(
        'fb-fans-chart',
        'Fans Growth',
        data.fans_data.labels,
        [{
            label: 'Total Fans',
            data: data.fans_data.values,
            borderColor: '#4267B2',
            backgroundColor: 'rgba(66, 103, 178, 0.1)',
            fill: true,
            tension: 0.3
        }],
        'Fans Count'
    );
    
    // Impressions vs Engagement Chart
    renderDualAxisChart(
        'fb-engagement-chart',
        'Impressions vs Engagement',
        data.impressions_data.labels,
        [
            {
                label: 'Impressions',
                data: data.impressions_data.values,
                borderColor: '#8B9DC3',
                backgroundColor: 'rgba(139, 157, 195, 0.1)',
                yAxisID: 'y'
            },
            {
                label: 'Engagement',
                data: data.engagement_data.values,
                borderColor: '#3B5998',
                backgroundColor: 'rgba(59, 89, 152, 0.1)',
                yAxisID: 'y1'
            }
        ]
    );
    
    // Reach & Views Chart
    renderLineChart(
        'fb-reach-chart',
        'Reach & Views',
        data.reach_data.labels,
        [
            {
                label: 'Reach',
                data: data.reach_data.values,
                borderColor: '#1877F2',
                backgroundColor: 'rgba(24, 119, 242, 0.1)',
                fill: true
            },
            {
                label: 'Views',
                data: data.views_data.values,
                borderColor: '#42B883',
                backgroundColor: 'rgba(66, 184, 131, 0.1)',
                fill: true
            }
        ],
        'Count'
    );
}

function renderInstagramCharts(data) {
    // Followers Growth Chart
    renderLineChart(
        'ig-followers-chart',
        'Followers Growth Trend',
        data.followers_data.labels,
        [{
            label: 'Followers',
            data: data.followers_data.values,
            borderColor: '#E4405F',
            backgroundColor: 'rgba(228, 64, 95, 0.1)',
            fill: true,
            tension: 0.4,
            pointBackgroundColor: '#E4405F',
            pointBorderColor: '#E4405F',
            pointRadius: 4
        }],
        'Followers Count'
    );
    
    // Views & Reach Chart
    renderLineChart(
        'ig-views-reach-chart',
        'Views & Reach Analytics',
        data.views_data.labels,
        [
            {
                label: 'Total Views',
                data: data.views_data.values,
                borderColor: '#F77737',
                backgroundColor: 'rgba(247, 119, 55, 0.1)',
                fill: true,
                tension: 0.3
            },
            {
                label: 'Accounts Reached',
                data: data.reach_data.values,
                borderColor: '#833AB4',
                backgroundColor: 'rgba(131, 58, 180, 0.1)',
                fill: true,
                tension: 0.3
            }
        ],
        'Count'
    );
    
    // Profile Activity Chart
    renderAreaChart(
        'ig-profile-activity-chart',
        'Profile Activity Overview',
        data.profile_activity_data.labels,
        [{
            label: 'Profile Views',
            data: data.profile_activity_data.values,
            borderColor: '#FD1D1D',
            backgroundColor: 'rgba(253, 29, 29, 0.2)',
            fill: true,
            tension: 0.4,
            pointBackgroundColor: '#FD1D1D',
            pointBorderColor: '#FD1D1D',
            pointRadius: 3
        }],
        'Profile Views'
    );
}

// Helper Functions
function setLoadingState(platform, isLoading) {
    const analyticsSection = document.getElementById(`${platform}-analytics`);
    if (isLoading) {
        analyticsSection.classList.add('loading-data');
    } else {
        analyticsSection.classList.remove('loading-data');
    }
}

function showErrorState(platform, message) {
    const analyticsSection = document.getElementById(`${platform}-analytics`);
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.innerHTML = `
        <i class="fas fa-exclamation-triangle"></i>
        <p>${message}</p>
        <button onclick="loadPlatformData('${platform}')">Retry</button>
    `;
    
    // Clear previous errors and add new one
    const existingErrors = analyticsSection.querySelectorAll('.error-message');
    existingErrors.forEach(error => error.remove());
    
    analyticsSection.appendChild(errorDiv);
}

function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

// Chart rendering functions
function renderLineChart(elementId, title, labels, datasets, yAxisLabel) {
    const ctx = document.getElementById(elementId).getContext('2d');
    
    // Destroy existing chart if it exists
    if (window[`${elementId}Chart`]) {
        window[`${elementId}Chart`].destroy();
    }
    
    window[`${elementId}Chart`] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: title,
                    font: {
                        size: 14,
                        weight: 'bold'
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: 'white',
                    bodyColor: 'white',
                    borderColor: datasets[0].borderColor,
                    borderWidth: 1
                },
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 20
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: yAxisLabel
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
}

function renderAreaChart(elementId, title, labels, datasets, yAxisLabel) {
    const ctx = document.getElementById(elementId).getContext('2d');
    
    // Destroy existing chart if it exists
    if (window[`${elementId}Chart`]) {
        window[`${elementId}Chart`].destroy();
    }
    
    window[`${elementId}Chart`] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: title,
                    font: {
                        size: 14,
                        weight: 'bold'
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(228, 64, 95, 0.9)',
                    titleColor: 'white',
                    bodyColor: 'white'
                },
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 20
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: yAxisLabel
                    },
                    grid: {
                        color: 'rgba(228, 64, 95, 0.1)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            elements: {
                line: {
                    fill: true
                }
            }
        }
    });
}

function renderDualAxisChart(elementId, title, labels, datasets) {
    const ctx = document.getElementById(elementId).getContext('2d');
    
    // Destroy existing chart if it exists
    if (window[`${elementId}Chart`]) {
        window[`${elementId}Chart`].destroy();
    }
    
    window[`${elementId}Chart`] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: title,
                    font: {
                        size: 14,
                        weight: 'bold'
                    }
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                },
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 20
                    }
                }
            },
            scales: {
                y: {
                    type: 'linear',
                    display: true,
                    position: 'left',
                    title: {
                        display: true,
                        text: datasets[0].label
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    }
                },
                y1: {
                    type: 'linear',
                    display: true,
                    position: 'right',
                    title: {
                        display: true,
                        text: datasets[1].label
                    },
                    grid: {
                        drawOnChartArea: false
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

function renderInstagramGradientChart(elementId, title, labels, datasets, yAxisLabel) {
    const ctx = document.getElementById(elementId).getContext('2d');
    
    // Create gradient for Instagram styling
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(228, 64, 95, 0.4)');
    gradient.addColorStop(0.5, 'rgba(247, 119, 55, 0.2)');
    gradient.addColorStop(1, 'rgba(131, 58, 180, 0.1)');
    
    // Update dataset background
    if (datasets[0]) {
        datasets[0].backgroundColor = gradient;
    }
    
    // Destroy existing chart if it exists
    if (window[`${elementId}Chart`]) {
        window[`${elementId}Chart`].destroy();
    }
    
    window[`${elementId}Chart`] = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: datasets
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                title: {
                    display: true,
                    text: title,
                    font: {
                        size: 14,
                        weight: 'bold'
                    },
                    color: '#E4405F'
                },
                tooltip: {
                    mode: 'index',
                    intersect: false,
                    backgroundColor: 'rgba(228, 64, 95, 0.9)',
                    titleColor: 'white',
                    bodyColor: 'white'
                },
                legend: {
                    position: 'bottom',
                    labels: {
                        usePointStyle: true,
                        padding: 20
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: yAxisLabel
                    },
                    grid: {
                        color: 'rgba(228, 64, 95, 0.1)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
}

// Instagram specific chart rendering
function renderInstagramCharts(data) {
    // Followers Growth Chart with Instagram gradient
    renderInstagramGradientChart(
        'ig-followers-chart',
        'Followers Growth Trend',
        data.followers_data.labels,
        [{
            label: 'Followers',
            data: data.followers_data.values,
            borderColor: '#E4405F',
            backgroundColor: 'rgba(228, 64, 95, 0.2)', // Will be overridden by gradient
            fill: true,
            tension: 0.4,
            pointBackgroundColor: '#E4405F',
            pointBorderColor: '#E4405F',
            pointRadius: 4,
            pointHoverRadius: 6,
            borderWidth: 3
        }],
        'Followers Count'
    );
    
    // Views & Reach Chart
    renderLineChart(
        'ig-views-reach-chart',
        'Views & Reach Analytics',
        data.views_data.labels,
        [
            {
                label: 'Total Views',
                data: data.views_data.values,
                borderColor: '#F77737',
                backgroundColor: 'rgba(247, 119, 55, 0.15)',
                fill: true,
                tension: 0.3,
                pointRadius: 3,
                borderWidth: 2
            },
            {
                label: 'Accounts Reached',
                data: data.reach_data.values,
                borderColor: '#833AB4',
                backgroundColor: 'rgba(131, 58, 180, 0.15)',
                fill: true,
                tension: 0.3,
                pointRadius: 3,
                borderWidth: 2
            }
        ],
        'Count'
    );
    
    // Profile Activity Chart
    renderAreaChart(
        'ig-profile-activity-chart',
        'Profile Activity Overview',
        data.profile_activity_data.labels,
        [{
            label: 'Profile Views',
            data: data.profile_activity_data.values,
            borderColor: '#FD1D1D',
            backgroundColor: 'rgba(253, 29, 29, 0.2)',
            fill: true,
            tension: 0.4,
            pointBackgroundColor: '#FD1D1D',
            pointBorderColor: '#FD1D1D',
            pointRadius: 3,
            borderWidth: 2
        }],
        'Profile Views'
    );
}

// Utility functions
function formatNumber(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
}

// Enhanced error handling
function handleApiError(platform, error) {
    console.error(`${platform} API Error:`, error);
    
    let errorMessage = 'Failed to load data';
    
    if (error.includes('token')) {
        errorMessage = 'Authentication error - please check access token';
    } else if (error.includes('rate limit')) {
        errorMessage = 'Rate limited - please try again in a few minutes';
    } else if (error.includes('network')) {
        errorMessage = 'Network error - please check your connection';
    }
    
    showErrorState(platform, errorMessage);
}

// Auto-refresh functionality
function startAutoRefresh(intervalMinutes = 30) {
    setInterval(() => {
        const activeSection = document.querySelector('.platform-analytics.active');
        if (activeSection) {
            const platform = activeSection.id.replace('-analytics', '');
            console.log(`Auto-refreshing ${platform} data...`);
            loadPlatformData(platform);
        }
    }, intervalMinutes * 60 * 1000);
}

// Initialize auto-refresh
startAutoRefresh(30); // Refresh every 30 minutes