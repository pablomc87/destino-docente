import { initializePlaces, getAutocomplete, getPlaceDetails } from '/static/schools/js/places.js';
import { getTrackingState, updateTrackingState, resetSession } from '/static/schools/js/state.js';
import { checkApiLimits, showApiLimitMessage, shouldTrack, trackApiCalls } from '/static/schools/js/api-tracking.js';

// Function to get cookie value by name
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// Function to show message in the interface
function showMessage(message, type = 'danger') {
    const messageContainer = document.getElementById('messageContainer');
    messageContainer.textContent = message;
    messageContainer.className = `alert alert-${type} mb-3`;
    messageContainer.classList.remove('d-none');
}

// Function to hide message
function hideMessage() {
    const messageContainer = document.getElementById('messageContainer');
    messageContainer.classList.add('d-none');
}

// Initialize the page
$(document).ready(function() {
    // Reset tracking state on page load
    resetSession();

    // Initialize Google Places Autocomplete
    const autocomplete = initializePlaces();

    // Handle input changes and count API calls
    $('#address').on('input', function() {
        hideMessage(); // Hide any previous messages
        if (this.value.trim()) {
            const state = getTrackingState();
            const newState = updateTrackingState({
                totalApiCalls: state.totalApiCalls + 1,
                lastInputTime: Date.now()
            });
            
            if (shouldTrack()) {
                trackApiCalls('input');
            }
        }
    });

    // Handle place selection
    getAutocomplete().addListener('place_changed', function() {
        hideMessage(); // Hide any previous messages
        const place = getAutocomplete().getPlace();
        if (place && place.geometry) {
            try {
                const placeDetails = getPlaceDetails(place);
                const state = updateTrackingState({
                    placeSelected: true,
                    lastInputTime: Date.now()
                });
                
                if (state.totalApiCalls > 0) {
                    trackApiCalls('place_selected');
                }
            } catch (error) {
                console.error('Error processing place:', error);
                showMessage('Por favor, selecciona una ubicación válida');
            }
        }
    });

    // Form submission
    $('#searchForm').on('submit', async function(e) {
        e.preventDefault();
        
        try {
            // Check API limits
            const withinLimits = await checkApiLimits();
            if (!withinLimits) {
                showApiLimitMessage();
                return;
            }

            // Get selected place
            const place = getAutocomplete().getPlace();
            if (!place || !place.geometry) {
                const messageContainer = document.getElementById('messageContainer');
                messageContainer.textContent = 'Por favor, selecciona una ubicación válida';
                messageContainer.className = 'alert alert-danger mb-3';
                return;
            }

            // Get place details
            const placeDetails = getPlaceDetails(place);

            // Update tracking state
            const state = updateTrackingState({
                placeSelected: true,
                lastInputTime: Date.now()
            });
            console.log('Form submitted. Current state:', state);

            // Track API calls for form submission
            if (state.totalApiCalls > 0) {
                console.log('Tracking API calls after form submission');
                trackApiCalls('form_submit');
            }

            // Store the new address
            const searchData = {
                address: placeDetails.address,
                latitude: placeDetails.lat,
                longitude: placeDetails.lng
            };
            localStorage.setItem('lastSearch', JSON.stringify(searchData));
            
            // Redirect to find_nearest with the address
            window.location.href = `/buscar-cercanos/?direccion=${encodeURIComponent(placeDetails.address)}`;
        } catch (error) {
            console.error('Error during search:', error);
            const messageContainer = document.getElementById('messageContainer');
            messageContainer.textContent = error.message || 'Ha ocurrido un error durante la búsqueda';
            messageContainer.className = 'alert alert-danger mb-3';
        }
    });

    // Handle visibility changes
    document.addEventListener('visibilitychange', function() {
        const state = getTrackingState();
        console.log('Visibility changed. Current state:', state);
        
        if (document.visibilityState === 'hidden') {
            // User switched tabs or minimized window
            if (state.totalApiCalls > 0) {
                console.log('Tracking API calls before tab/window change');
                trackApiCalls('visibility_change');
            }
        }
    });

    // Handle time-based tracking
    setInterval(() => {
        const state = getTrackingState();
        if (state.totalApiCalls > 0) {
            console.log('Checking time-based tracking. Current state:', state);
            if (shouldTrack()) {
                console.log('Time-based tracking triggered');
                trackApiCalls('time_interval');
            }
        }
    }, 30000); // Check every 30 seconds

    // Handle page unload
    $(window).on('beforeunload', function() {
        const state = getTrackingState();
        if (state.totalApiCalls > 0) {
            trackApiCalls('unload');
        }
    });
}); 