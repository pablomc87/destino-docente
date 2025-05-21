import { getTrackingState, setTrackingState, updateTrackingState, resetSession } from './modules/state.js';
import { checkApiLimits, showApiLimitMessage, shouldTrack, trackApiCalls } from './modules/api-tracking.js';
import { saveSearchResults, loadLastSearchResults, displaySearchResults } from './modules/search-results.js';
import { showLoading, hideLoading, showError, hideError, disableSearchForm, enableSearchForm, saveScrollPosition, restoreScrollPosition } from './modules/ui.js';
import { initializePlaces, getPlaceDetails, getAutocomplete } from './modules/places.js';

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

// Initialize the page
$(document).ready(function() {
    // Reset tracking state on page load
    resetSession();

    // Initialize Google Places Autocomplete
    const autocomplete = initializePlaces();

    // Restore scroll position if returning from school details
    restoreScrollPosition();

    // Load last search results if available
    const lastResults = loadLastSearchResults();
    if (lastResults) {
        displaySearchResults(lastResults.data);
    }

    // Set initial address from URL parameter if present
    const urlParams = new URLSearchParams(window.location.search);
    const direccion = urlParams.get('direccion');
    if (direccion) {
        const decodedAddress = decodeURIComponent(direccion);
        $('#address').val(decodedAddress);
        
        // Create a geocoder to get place details
        const geocoder = new google.maps.Geocoder();
        geocoder.geocode({ address: decodedAddress }, (results, status) => {
            if (status === 'OK' && results[0]) {
                // Create a place object that matches the Places API format
                const place = {
                    geometry: results[0].geometry,
                    formatted_address: results[0].formatted_address,
                    address_components: results[0].address_components
                };
                
                // Set the place in the autocomplete
                getAutocomplete().set('place', place);
                
                // Update the region if available
                const placeDetails = getPlaceDetails(place);
                if (placeDetails.region) {
                    $('#region').val(placeDetails.region);
                }
            }
        });
    }

    // Handle input changes and count API calls
    $('#address').on('input', function() {
        if (this.value.trim()) {
            const state = getTrackingState();
            const newState = updateTrackingState({
                totalApiCalls: state.totalApiCalls + 1,
                lastInputTime: Date.now()
            });
            console.log('API call counted. New total:', newState.totalApiCalls);
            
            if (shouldTrack()) {
                trackApiCalls('input');
            }
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

    // Handle place selection
    getAutocomplete().addListener('place_changed', function() {
        const place = getAutocomplete().getPlace();
        if (place && place.geometry) {
            try {
                const placeDetails = getPlaceDetails(place);
                $('#region').val(placeDetails.region);
                const state = updateTrackingState({
                    placeSelected: true,
                    lastInputTime: Date.now()
                });
                console.log('Place selected. Current state:', state);
                
                // Track API calls when place is selected
                if (state.totalApiCalls > 0) {
                    console.log('Tracking API calls after place selection');
                    trackApiCalls('place_selected');
                }
            } catch (error) {
                console.error('Error processing place:', error);
                showError(error.message);
            }
        }
    });

    // Handle form submission
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
                showError('Por favor, selecciona una ubicación válida');
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

            // Show loading
            showLoading();
            hideError();

            // Make the search request
            const response = await $.ajax({
                url: '/api/nearest/',
                method: 'GET',
                data: {
                    address: placeDetails.address,
                    latitude: placeDetails.lat,
                    longitude: placeDetails.lng,
                    provinces: placeDetails.region ? [placeDetails.region] : [],
                    school_types: [
                        ...$('input[name="school_types"]:checked').map(function() {
                            return this.value;
                        }).get()
                    ]
                },
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            });

            // Track API call if needed
            if (shouldTrack()) {
                await trackApiCalls('search');
            }

            // Save and display results
            saveSearchResults(response, placeDetails);
            displaySearchResults(response);

        } catch (error) {
            console.error('Error during search:', error);
            showError(error.message || 'Ha ocurrido un error durante la búsqueda');
        } finally {
            hideLoading();
        }
    });

    // Handle clear search button
    $('#clearSearch').on('click', function() {
        const state = getTrackingState();
        if (state.totalApiCalls > 0) {
            console.log('Tracking API calls before clearing search');
            trackApiCalls('clear_search');
        }
        
        // Reset the form
        $('#searchForm')[0].reset();
        $('#address').val('');
        $('#result').addClass('d-none');
        hideError();
        
        // Clear localStorage
        localStorage.removeItem('lastSearchResults');
        
        // Reset tracking state
        resetSession();
        console.log('Search cleared and tracking state reset');
    });

    // Handle page unload
    $(window).on('beforeunload', function() {
        const state = getTrackingState();
        if (state.placeSelected && !state.hasTracked) {
            trackApiCalls('unload');
        }
    });
}); 