// State management functions
const getTrackingState = () => {
    const state = sessionStorage.getItem('trackingState');
    return state ? JSON.parse(state) : {
        totalApiCalls: 0,
        placeSelected: false,
        totalResponseTimeMs: 0,
        lastInputTime: Date.now()
    };
};

const setTrackingState = (state) => {
    sessionStorage.setItem('trackingState', JSON.stringify(state));
};

const updateTrackingState = (updates) => {
    const state = getTrackingState();
    const newState = { ...state, ...updates };
    setTrackingState(newState);
    return newState;
};

const API_CALLS_THRESHOLD = 10;
const TRACKING_INTERVAL = 60000; // 1 minute

let lastTrackingTime = Date.now();

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

// Function to check API limits
async function checkApiLimits() {
    try {
        console.log('Checking API limits...');
        const response = await fetch('/api/check-limits/');
        const data = await response.json();
        console.log('API limits response:', data);
        
        if (!data.within_limits) {
            console.warn('API limits reached:', data);
            showApiLimitMessage();
            return false;
        }
        
        // Store max schools limit
        window.maxSchoolsPerSearch = data.max_schools || 10;
        
        // If user has unlimited API calls, remove any existing limit message
        if (data.unlimited_api_calls) {
            const limitMessage = document.getElementById('apiLimitMessage');
            if (limitMessage) {
                limitMessage.style.display = 'none';
            }
        }
        
        return true;
    } catch (error) {
        console.error('Error checking API limits:', error);
        // If we can't check limits, allow the request but log the error
        return true;
    }
}

// Function to show API limit message
const showApiLimitMessage = () => {
    console.log('Showing API limit message');
    const messageDiv = document.getElementById('apiLimitMessage');
    if (messageDiv) {
        messageDiv.style.display = 'block';
        // Disable the form
        const form = document.getElementById('searchForm');
        if (form) {
            form.querySelectorAll('input, select, button').forEach(el => {
                el.disabled = true;
            });
        }
    }
};

// Function to check if we should track
const shouldTrack = () => {
    const state = getTrackingState();
    const now = Date.now();
    const shouldTrack = state.totalApiCalls >= API_CALLS_THRESHOLD || 
                       (now - state.lastInputTime >= TRACKING_INTERVAL);
    
    console.log('Checking if should track:', {
        totalApiCalls: state.totalApiCalls,
        threshold: API_CALLS_THRESHOLD,
        timeSinceLastInput: now - state.lastInputTime,
        trackingInterval: TRACKING_INTERVAL,
        shouldTrack: shouldTrack
    });
    
    return shouldTrack;
};

// Function to track API calls
const trackApiCalls = (source) => {
    const state = getTrackingState();
    console.log('trackApiCalls called with source:', source);
    console.log('Current tracking state:', {
        totalApiCalls: state.totalApiCalls,
        placeSelected: state.placeSelected,
        totalResponseTimeMs: state.totalResponseTimeMs,
        lastInputTime: new Date(state.lastInputTime).toISOString()
    });

    if (state.totalApiCalls > 0) {
        console.log('Making tracking request to /api/track-google-api/');
        
        const xhr = new XMLHttpRequest();
        xhr.open('POST', '/api/track-google-api/', false);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('X-CSRFToken', getCookie('csrftoken'));
        
        const trackingData = {
            api_type: 'places',
            endpoint: 'session_summary',
            method: 'GET',
            total_calls: state.totalApiCalls,
            place_selected: state.placeSelected,
            response_time: state.totalResponseTimeMs,
            source: source
        };
        
        console.log('Sending tracking data:', trackingData);
        
        try {
            xhr.send(JSON.stringify(trackingData));
            console.log('Tracking request completed with status:', xhr.status);
            if (xhr.status === 200) {
                console.log('Successfully tracked API calls in database');
                // Reset API calls counter after successful tracking
                updateTrackingState({
                    totalApiCalls: 0,
                    totalResponseTimeMs: 0
                });
                console.log('Reset API calls counter to 0');
            } else {
                console.error('Failed to track API calls. Status:', xhr.status, 'Response:', xhr.responseText);
            }
        } catch (error) {
            console.error('Error during tracking request:', error);
        }
    } else {
        console.log('Skipping tracking because totalApiCalls is 0');
    }
}; 

const resetSession = () => {
    setTrackingState({
        totalApiCalls: 0,
        placeSelected: false,
        totalResponseTimeMs: 0,
        lastInputTime: Date.now()
    });
}; 

let autocomplete = null;

const initializePlaces = () => {
    const input = document.getElementById('address');
    if (!input) return;

    autocomplete = new google.maps.places.Autocomplete(input, {
        componentRestrictions: { country: 'es' },
        fields: ['address_components', 'geometry', 'formatted_address'],
        types: ['address']
    });

    return autocomplete;
};

const getPlaceDetails = (place) => {
    if (!place || !place.geometry) {
        throw new Error('No se ha seleccionado una ubicación válida');
    }

    const addressComponents = place.address_components || [];
    let region = '';
    let province = '';

    for (const component of addressComponents) {
        if (component.types.includes('administrative_area_level_1')) {
            region = component.long_name;
        }
        if (component.types.includes('administrative_area_level_2')) {
            province = component.long_name;
        }
    }

    return {
        lat: place.geometry.location.lat(),
        lng: place.geometry.location.lng(),
        address: place.formatted_address,
        region,
        province
    };
};

const getAutocomplete = () => autocomplete; 

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

function initializeIndexMain() {
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
}

$(document).ready(function () {
    if (window.__destinoDocenteMapsKeyMissing) {
        console.warn('GOOGLE_MAPS_API_KEY is not set; map features are disabled.');
        return;
    }
    const start = () => initializeIndexMain();
    if (window.google && window.google.maps && window.google.maps.places) {
        start();
    } else {
        window.addEventListener('destino-docente:maps-ready', start, { once: true });
    }
});