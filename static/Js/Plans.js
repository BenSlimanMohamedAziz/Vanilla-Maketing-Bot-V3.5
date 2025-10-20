document.addEventListener('DOMContentLoaded', function() {
    // Modal elements
    const paymentModal = document.getElementById('payment-modal');
    const openPlusModal = document.getElementById('open-plus-modal');
    const openProModal = document.getElementById('open-pro-modal');
    const closeModal = document.querySelector('.close-modal');
    const selectedPlanInput = document.getElementById('selected-plan');
    const paymentAmount = document.getElementById('payment-amount');
    const paymentForm = document.getElementById('payment-form');
    
    // Open modal for Chahbander+
    openPlusModal.addEventListener('click', function() {
        selectedPlanInput.value = 'plus';
        paymentAmount.textContent = '50 TND';
        paymentModal.style.display = 'flex';
    });
    
    // Open modal for Pro
    openProModal.addEventListener('click', function() {
        selectedPlanInput.value = 'pro';
        paymentAmount.textContent = '100 TND';
        paymentModal.style.display = 'flex';
    });
    
    // Close modal
    closeModal.addEventListener('click', function() {
        paymentModal.style.display = 'none';
    });
    
    // Close modal when clicking outside
    window.addEventListener('click', function(event) {
        if (event.target === paymentModal) {
            paymentModal.style.display = 'none';
        }
    });
    
    // Set payment date (next month)
    const nextMonth = new Date();
    nextMonth.setMonth(nextMonth.getMonth() + 1);
    const options = { day: 'numeric', month: 'long', year: 'numeric' };
    document.getElementById('payment-date').textContent = nextMonth.toLocaleDateString('en-US', options);
    
    // Card validation
    const cardNumberInput = document.getElementById('card-number');
    const expiryInput = document.getElementById('expiry-date');
    const cvvInput = document.getElementById('cvv');
    
    cardNumberInput.addEventListener('input', function(e) {
        // Format card number with spaces
        let value = e.target.value.replace(/\s+/g, '');
        if (value.length > 0) {
            value = value.match(new RegExp('.{1,4}', 'g')).join(' ');
        }
        e.target.value = value;
        
        // Simple validation (just checks length for demo)
        const cardNumberError = document.getElementById('card-number-error');
        if (value.replace(/\s+/g, '').length < 16) {
            cardNumberError.textContent = 'Card number must be 16 digits';
            cardNumberError.style.display = 'block';
        } else {
            cardNumberError.style.display = 'none';
        }
    });
    
    expiryInput.addEventListener('input', function(e) {
        // Format expiry date
        let value = e.target.value.replace(/\D/g, '');
        if (value.length > 2) {
            value = value.substring(0, 2) + '/' + value.substring(2, 4);
        }
        e.target.value = value;
        
        // Simple validation
        const expiryError = document.getElementById('expiry-error');
        if (value.length < 5) {
            expiryError.textContent = 'Enter valid expiry date (MM/YY)';
            expiryError.style.display = 'block';
        } else {
            expiryError.style.display = 'none';
        }
    });
    
    cvvInput.addEventListener('input', function(e) {
        // Only allow numbers
        e.target.value = e.target.value.replace(/\D/g, '');
        
        // Simple validation
        const cvvError = document.getElementById('cvv-error');
        if (e.target.value.length < 3) {
            cvvError.textContent = 'CVV must be 3-4 digits';
            cvvError.style.display = 'block';
        } else {
            cvvError.style.display = 'none';
        }
    });
    
    // Add this to your payment form submission handler
    paymentForm.addEventListener('submit', function(e) {
        // Set the hidden card fields
        document.getElementById('card-type-hidden').value = document.getElementById('card-type').value;
        const cardNumber = document.getElementById('card-number').value.replace(/\s+/g, '');
        document.getElementById('card-number-hidden').value = cardNumber;
        
        // For demo, we'll just proceed
        // In a real app, you would validate all fields and process payment here
        return true;
    });
});