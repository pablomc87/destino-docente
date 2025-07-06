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

const resetSession = () => {
    setTrackingState({
        totalApiCalls: 0,
        placeSelected: false,
        totalResponseTimeMs: 0,
        lastInputTime: Date.now()
    });
}; 

// Constants
const API_CALLS_THRESHOLD = 10;
const TRACKING_INTERVAL = 60000; // 1 minute

let lastTrackingTime = Date.now();

// Add this mapping at the top or before its use
const regionMainWordToOfficial = {
    'madrid': 'COMUNIDAD DE MADRID',
    'valencia': 'COMUNIDAD VALENCIANA',
    'navarra': 'COMUNIDAD FORAL DE NAVARRA',
    'baleares': 'COMUNIDAD AUTÓNOMA DE LAS ISLAS BALEARES',
    'canarias': 'COMUNIDAD AUTÓNOMA DE CANARIAS',
    'mancha': 'COMUNIDAD AUTÓNOMA DE CASTILLA-LA MANCHA',
    'león': 'COMUNIDAD AUTÓNOMA DE CASTILLA Y LEÓN',
    'cataluña': 'COMUNIDAD AUTÓNOMA DE CATALUÑA',
    'catalunya': 'COMUNIDAD AUTÓNOMA DE CATALUÑA',
    'galicia': 'COMUNIDAD AUTÓNOMA DE GALICIA',
    'rioja': 'COMUNIDAD AUTÓNOMA DE LA RIOJA',
    'vasco': 'COMUNIDAD AUTÓNOMA DEL PAÍS VASCO',
    'euskadi': 'COMUNIDAD AUTÓNOMA DEL PAÍS VASCO',
    'murcia': 'COMUNIDAD AUTÓNOMA DE MURCIA',
    'extremadura': 'COMUNIDAD AUTÓNOMA DE EXTREMADURA',
    'cantabria': 'COMUNIDAD AUTÓNOMA DE CANTABRIA',
    'asturias': 'COMUNIDAD AUTÓNOMA DE ASTURIAS',
    'aragon': 'COMUNIDAD AUTÓNOMA DE ARAGÓN',
    'aragón': 'COMUNIDAD AUTÓNOMA DE ARAGÓN',
    'andalucía': 'COMUNIDAD AUTÓNOMA DE ANDALUCÍA',
    'ceuta': 'CIUDAD AUTÓNOMA DE CEUTA',
    'melilla': 'CIUDAD AUTÓNOMA DE MELILLA'
};

function getOfficialRegion(regionStr) {
    if (!regionStr) return '';
    const n = regionStr.trim().toLowerCase();
    for (const mainWord in regionMainWordToOfficial) {
        if (n.includes(mainWord)) {
            return regionMainWordToOfficial[mainWord];
        }
    }
    return '';
}

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

// Function to save search results to local storage
const saveSearchResults = (data, searchParams) => {
    try {
        localStorage.setItem('lastSearchResults', JSON.stringify({
            timestamp: Date.now(),
            data: data,
            params: searchParams
        }));
    } catch (error) {
        console.error('Error saving search results:', error);
    }
};

// Function to load last search results
const loadLastSearchResults = () => {
    try {
        const savedResults = localStorage.getItem('lastSearchResults');
        if (savedResults) {
            const { timestamp, data, params } = JSON.parse(savedResults);
            // Check if results are less than 24 hours old
            if (Date.now() - timestamp < 24 * 60 * 60 * 1000) {
                return { data, params };
            }
        }
    } catch (error) {
        console.error('Error loading saved results:', error);
    }
    return null;
};

// Function to display search results
// Global variables for client-side pagination
let allSearchResults = [];
let currentPage = 1;
let itemsPerPage = 10;

const displaySearchResults = (data) => {
    // Store all results for client-side pagination
    if (data.schools && data.schools.length > 0) {
        allSearchResults = data.schools;
        currentPage = 1;
        console.log('Stored', allSearchResults.length, 'results for client-side pagination');
        console.log('First few schools:', allSearchResults.slice(0, 3).map(s => s.name));
    } else {
        console.log('No schools data received');
    }
    
    // Update results count
    $('#resultsNumber').text(data.total_count);
    
    const schoolCardsDiv = $('#schoolCards');
    schoolCardsDiv.empty();
    
    // Determine which schools to display
    let schoolsToDisplay = data.schools;
    
    if (allSearchResults && allSearchResults.length > itemsPerPage) {
        // For client-side pagination, show only first page initially
        schoolsToDisplay = allSearchResults.slice(0, itemsPerPage);
    }
    
    if (schoolsToDisplay && schoolsToDisplay.length > 0) {
        schoolsToDisplay.forEach(school => {
            // Clone the template
            const template = document.getElementById('schoolCardTemplate');
            const card = $(template.content.cloneNode(true));
            
            // Set school data
            card.find('.card-title').text(school.name);
            card.find('.badge').text(school.nature || 'No especificado');
            card.find('.location').text(`${school.municipality}, ${school.province}`);
            card.find('.distance').text(school.distance ? `${school.distance.toFixed(1)} km` : 'No disponible');
            
            // Set travel times
            if (school.travel_times) {
                const walkingTime = school.travel_times.walking || 'No disponible';
                const drivingTime = school.travel_times.driving || 'No disponible';
                const bicyclingTime = school.travel_times.bicycling || 'No disponible';
                const transitTime = school.travel_times.transit || 'No disponible';
                
                // Only show travel times section if at least one time is available
                const hasValidTimes = [walkingTime, drivingTime, bicyclingTime, transitTime].some(time => 
                    time && time !== 'No disponible' && time !== 'null' && time !== ''
                );
                
                if (hasValidTimes) {
                    card.find('.walking-time').text(walkingTime);
                    card.find('.driving-time').text(drivingTime);
                    card.find('.bicycling-time').text(bicyclingTime);
                    card.find('.transit-time').text(transitTime);
                    card.find('.travel-times-row').show();
                } else {
                    card.find('.travel-times-row').hide();
                }
            } else {
                card.find('.travel-times-row').hide();
            }
            
            // Set details link
            const detailsLink = card.find('.details-link');
            detailsLink.attr('href', `/centros/${school.id}/`);
            detailsLink.attr('onclick', `saveScrollPosition(${school.id})`);
            
            // Add school ID to card
            card.find('.result-card').attr('data-school-id', school.id);
            
            schoolCardsDiv.append(card);
        });
        
        // Show/hide location info
        if (data.search_criteria?.user_location) {
            $('#userLocation').text(data.search_criteria.address);
            $('#locationInfo').removeClass('d-none');
        } else {
            $('#locationInfo').addClass('d-none');
        }
        
        $('#noResults').addClass('d-none');
        
        // Handle pagination if available
        console.log('Pagination data:', data.paginator);
        console.log('All search results length:', allSearchResults.length);
        
        if (allSearchResults && allSearchResults.length > itemsPerPage) {
            // Client-side pagination for all results
            console.log('Setting up client-side pagination for', allSearchResults.length, 'schools');
            
            displayPagination({
                current_page: 1,
                total_pages: Math.ceil(allSearchResults.length / itemsPerPage),
                has_previous: false,
                has_next: allSearchResults.length > itemsPerPage,
                previous_page_number: null,
                next_page_number: 2
            }, data.search_criteria);
        } else {
            $('#paginationContainer').addClass('d-none');
        }
    } else {
        $('#noResults').removeClass('d-none');
        $('#locationInfo').addClass('d-none');
        $('#paginationContainer').addClass('d-none');
    }
    
    // Show results section
    $('#result').removeClass('d-none');
    
    // Calculate responsive scroll offset and duration
    const viewportHeight = window.innerHeight;
    const scrollOffset = Math.max(viewportHeight * 0.1, 40); // 10% of viewport height, minimum 40px
    const scrollDuration = Math.min(viewportHeight * 0.5, 800); // 0.5ms per pixel, maximum 800ms
    
    // Scroll to results with a smooth animation
    $('html, body').animate({
        scrollTop: $('#result').offset().top - scrollOffset
    }, scrollDuration);
};

// Function to display pagination
const displayPagination = (paginator, searchCriteria) => {
    console.log('displayPagination called with:', { paginator, searchCriteria });
    const paginationContainer = $('#paginationContainer');
    const paginationList = $('#paginationList');
    
    paginationContainer.removeClass('d-none');
    paginationList.empty();
    
    // Previous button
    if (paginator.has_previous) {
        const prevLi = $('<li class="page-item"></li>');
        const prevLink = $('<a class="page-link" href="#" aria-label="Anterior"></a>');
        prevLink.html('<span aria-hidden="true">&laquo;</span>');
        prevLink.click(function(e) {
            e.preventDefault();
            loadPageClientSide(paginator.previous_page_number);
        });
        prevLi.append(prevLink);
        paginationList.append(prevLi);
    }
    
    // Page numbers
    for (let i = 1; i <= paginator.total_pages; i++) {
        if (i === 1 || i === paginator.total_pages || 
            (i >= paginator.current_page - 2 && i <= paginator.current_page + 2)) {
            const li = $('<li class="page-item"></li>');
            
            if (i === paginator.current_page) {
                li.addClass('active');
                li.html(`<span class="page-link">${i}</span>`);
            } else {
                const link = $(`<a class="page-link" href="#">${i}</a>`);
                link.click(function(e) {
                    e.preventDefault();
                    loadPageClientSide(i);
                });
                li.append(link);
            }
            paginationList.append(li);
        } else if (i === paginator.current_page - 3 || i === paginator.current_page + 3) {
            const li = $('<li class="page-item disabled"></li>');
            li.html('<span class="page-link">...</span>');
            paginationList.append(li);
        }
    }
    
    // Next button
    if (paginator.has_next) {
        const nextLi = $('<li class="page-item"></li>');
        const nextLink = $('<a class="page-link" href="#" aria-label="Siguiente"></a>');
        nextLink.html('<span aria-hidden="true">&raquo;</span>');
        nextLink.click(function(e) {
            e.preventDefault();
            loadPageClientSide(paginator.next_page_number);
        });
        nextLi.append(nextLink);
        paginationList.append(nextLi);
    }
};

// Function to load a specific page (client-side pagination)
const loadPageClientSide = (page) => {
    if (!allSearchResults || allSearchResults.length === 0) {
        console.error('No search results available for client-side pagination');
        return;
    }
    
    currentPage = page;
    const startIndex = (page - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const pageResults = allSearchResults.slice(startIndex, endIndex);
    
    // Update results display
    const schoolCardsDiv = $('#schoolCards');
    schoolCardsDiv.empty();
    
    pageResults.forEach(school => {
        // Clone the template
        const template = document.getElementById('schoolCardTemplate');
        const card = $(template.content.cloneNode(true));
        
        // Set school data
        card.find('.card-title').text(school.name);
        card.find('.badge').text(school.nature || 'No especificado');
        card.find('.location').text(`${school.municipality}, ${school.province}`);
        card.find('.distance').text(school.distance ? `${school.distance.toFixed(1)} km` : 'No disponible');
        
        // Set travel times
        if (school.travel_times) {
            const walkingTime = school.travel_times.walking || 'No disponible';
            const drivingTime = school.travel_times.driving || 'No disponible';
            const bicyclingTime = school.travel_times.bicycling || 'No disponible';
            const transitTime = school.travel_times.transit || 'No disponible';
            
            // Only show travel times section if at least one time is available
            const hasValidTimes = [walkingTime, drivingTime, bicyclingTime, transitTime].some(time => 
                time && time !== 'No disponible' && time !== 'null' && time !== ''
            );
            
            if (hasValidTimes) {
                card.find('.walking-time').text(walkingTime);
                card.find('.driving-time').text(drivingTime);
                card.find('.bicycling-time').text(bicyclingTime);
                card.find('.transit-time').text(transitTime);
                card.find('.travel-times-row').show();
            } else {
                card.find('.travel-times-row').hide();
            }
        } else {
            card.find('.travel-times-row').hide();
        }
        
        // Set details link
        const detailsLink = card.find('.details-link');
        detailsLink.attr('href', `/centros/${school.id}/`);
        detailsLink.attr('onclick', `saveScrollPosition(${school.id})`);
        
        // Add school ID to card
        card.find('.result-card').attr('data-school-id', school.id);
        
        schoolCardsDiv.append(card);
    });
    
    // Update pagination
    updatePaginationClientSide();
    
    // Scroll to results
    const viewportHeight = window.innerHeight;
    const scrollOffset = Math.max(viewportHeight * 0.1, 40);
    const scrollDuration = Math.min(viewportHeight * 0.5, 800);
    
    $('html, body').animate({
        scrollTop: $('#result').offset().top - scrollOffset
    }, scrollDuration);
};

// Function to update pagination controls (client-side)
const updatePaginationClientSide = () => {
    const totalPages = Math.ceil(allSearchResults.length / itemsPerPage);
    const paginationContainer = $('#paginationContainer');
    const paginationList = $('#paginationList');
    
    paginationContainer.removeClass('d-none');
    paginationList.empty();
    
    // Previous button
    if (currentPage > 1) {
        const prevLi = $('<li class="page-item"></li>');
        const prevLink = $('<a class="page-link" href="#" aria-label="Anterior"></a>');
        prevLink.html('<span aria-hidden="true">&laquo;</span>');
        prevLink.click(function(e) {
            e.preventDefault();
            loadPageClientSide(currentPage - 1);
        });
        prevLi.append(prevLink);
        paginationList.append(prevLi);
    }
    
    // Page numbers
    for (let i = 1; i <= totalPages; i++) {
        if (i === 1 || i === totalPages || 
            (i >= currentPage - 2 && i <= currentPage + 2)) {
            const li = $('<li class="page-item"></li>');
            
            if (i === currentPage) {
                li.addClass('active');
                li.html(`<span class="page-link">${i}</span>`);
            } else {
                const link = $(`<a class="page-link" href="#">${i}</a>`);
                link.click(function(e) {
                    e.preventDefault();
                    loadPageClientSide(i);
                });
                li.append(link);
            }
            paginationList.append(li);
        } else if (i === currentPage - 3 || i === currentPage + 3) {
            const li = $('<li class="page-item disabled"></li>');
            li.html('<span class="page-link">...</span>');
            paginationList.append(li);
        }
    }
    
    // Next button
    if (currentPage < totalPages) {
        const nextLi = $('<li class="page-item"></li>');
        const nextLink = $('<a class="page-link" href="#" aria-label="Siguiente"></a>');
        nextLink.html('<span aria-hidden="true">&raquo;</span>');
        nextLink.click(function(e) {
            e.preventDefault();
            loadPageClientSide(currentPage + 1);
        });
        nextLi.append(nextLink);
        paginationList.append(nextLi);
    }
};

// Keep the original loadPage function for backward compatibility
const loadPage = (page, searchCriteria) => {
    console.warn('loadPage called - this should not happen with client-side pagination');
    loadPageClientSide(page);
}; 

// UI-related functions
const showLoading = () => {
    $('#loading').removeClass('d-none');
    $('#result').addClass('d-none');
};

const hideLoading = () => {
    $('#loading').addClass('d-none');
};

const showError = (message) => {
    const errorDiv = $('#error');
    errorDiv.text(message);
    errorDiv.removeClass('d-none');
    hideLoading();
};

const hideError = () => {
    $('#error').addClass('d-none');
};

const disableSearchForm = () => {
    $('#searchForm input, #searchForm select, #searchForm button').prop('disabled', true);
};

const enableSearchForm = () => {
    $('#searchForm input, #searchForm select, #searchForm button').prop('disabled', false);
};

const saveScrollPosition = (schoolId) => {
    sessionStorage.setItem('scrollPosition', window.scrollY);
    sessionStorage.setItem('lastViewedSchool', schoolId);
};

const restoreScrollPosition = () => {
    const scrollPosition = sessionStorage.getItem('scrollPosition');
    const lastViewedSchool = sessionStorage.getItem('lastViewedSchool');
    
    if (scrollPosition && lastViewedSchool) {
        window.scrollTo(0, parseInt(scrollPosition));
        sessionStorage.removeItem('scrollPosition');
        sessionStorage.removeItem('lastViewedSchool');
    }
}; 

// Google Places integration
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
        
        // Create a geocoder request to get place details
        const geocoder = new google.maps.Geocoder();
        geocoder.geocode({ address: decodedAddress }, (results, status) => {
            if (status === 'OK' && results[0]) {
                // Create a place object that matches the Autocomplete format
                const place = {
                    geometry: results[0].geometry,
                    address_components: results[0].address_components,
                    formatted_address: results[0].formatted_address
                };
                
                // Set the place in the Autocomplete
                autocomplete.set('place', place);

                // Find and set the autonomous community
                const addressComponents = results[0].address_components;
                for (const component of addressComponents) {
                    if (component.types.includes('administrative_area_level_1')) {
                        let community = component.long_name;
                        
                        // Map special cases
                        const communityMap = {
                            'Comunidad de Madrid': 'Madrid',
                            'Comunidad Valenciana': 'Comunidad Valenciana',
                            'Comunidad Foral de Navarra': 'Navarra',
                            'Comunidad Autónoma de las Islas Baleares': 'Islas Baleares',
                            'Comunidad Autónoma de Canarias': 'Canarias',
                            'Comunidad Autónoma de Castilla-La Mancha': 'Castilla-La Mancha',
                            'Comunidad Autónoma de Castilla y León': 'Castilla y León',
                            'Comunidad Autónoma de Cataluña': 'Cataluña',
                            'Comunidad Autónoma de Galicia': 'Galicia',
                            'Comunidad Autónoma de La Rioja': 'La Rioja',
                            'Comunidad Autónoma del País Vasco': 'País Vasco',
                            'Comunidad Autónoma de Murcia': 'Murcia',
                            'Comunidad Autónoma de Extremadura': 'Extremadura',
                            'Comunidad Autónoma de Cantabria': 'Cantabria',
                            'Comunidad Autónoma de Asturias': 'Asturias',
                            'Comunidad Autónoma de Aragón': 'Aragón',
                            'Comunidad Autónoma de Andalucía': 'Andalucía'
                        };
                        
                        community = communityMap[community] || community;
                        $('#region').val(community);
                        break;
                    }
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
                const officialRegion = getOfficialRegion(placeDetails.region);
                if (officialRegion) {
                    $('#region').val(officialRegion);
                    console.log('Region set to official value:', officialRegion);
                } else {
                    $('#region').val('');
                    console.log('No matching region found for:', placeDetails.region);
                }
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

            // Check for advanced filters (dashboard only)
            let advancedFilters = null;
            try {
                const storedFilters = sessionStorage.getItem('advancedFilters');
                if (storedFilters) {
                    advancedFilters = JSON.parse(storedFilters);
                    console.log('Advanced filters found:', advancedFilters);
                }
            } catch (error) {
                console.warn('Error parsing advanced filters:', error);
            }

            // Make the search request
            const ajaxData = {
                address: placeDetails.address,
                latitude: placeDetails.lat,
                longitude: placeDetails.lng,
                autonomous_communities: $('#region').val() ? [$('#region').val()] : [],
            };

            // Separate ownership types and education levels
            const ownershipTypes = [];
            const educationLevels = [];
            
            $('input[name="school_types"]:checked').each(function() {
                const value = this.value;
                if (['public', 'private', 'concertado'].includes(value)) {
                    ownershipTypes.push(value);
                } else if (['infantil', 'primaria', 'secundaria', 'bachillerato', 'fp'].includes(value)) {
                    educationLevels.push(value);
                }
            });

            // Add ownership types if any are selected
            if (ownershipTypes.length > 0) {
                ajaxData.ownership_types = ownershipTypes;
                console.log('Ownership types:', ownershipTypes);
            }

            // Add education levels if any are selected
            if (educationLevels.length > 0) {
                ajaxData.education_levels = educationLevels;
                console.log('Education levels:', educationLevels);
            }

            // Add advanced school type filters if available
            let advancedSchoolTypes = [];
            
            // Check for advanced school types from sessionStorage (dashboard)
            if (advancedFilters && advancedFilters.advancedSchoolTypes && advancedFilters.advancedSchoolTypes.length > 0) {
                advancedSchoolTypes = advancedFilters.advancedSchoolTypes;
                console.log('Advanced school types from sessionStorage:', advancedSchoolTypes);
            }
            
            // Also check for advanced school types from form elements (if available)
            const selectedAdvancedTypes = document.querySelectorAll('#selectedAdvancedTypes .badge-advanced-type');
            if (selectedAdvancedTypes.length > 0) {
                const formAdvancedTypes = Array.from(selectedAdvancedTypes).map(badge => badge.textContent.trim());
                advancedSchoolTypes = advancedSchoolTypes.concat(formAdvancedTypes);
                console.log('Advanced school types from form:', formAdvancedTypes);
            }
            
            // Add advanced school types if any are found
            if (advancedSchoolTypes.length > 0) {
                ajaxData.advanced_school_types = advancedSchoolTypes;
                console.log('Final advanced school type filters:', advancedSchoolTypes);
            }

            console.log('AJAX data being sent:', ajaxData);

            // Add travel times parameter only if checkbox is explicitly checked
            const travelTimesCheckbox = document.getElementById('include_travel_times');
            
            if (travelTimesCheckbox && travelTimesCheckbox.checked) {
                ajaxData.include_travel_times = 'true';
                console.log('Including travel times in search - checkbox is checked');
            } else {
                console.log('Travel times checkbox is not checked - not including travel times');
            }

            // Add parameter to get all results at once for client-side pagination
            ajaxData.all_results = 'true';

            const response = await $.ajax({
                url: '/api/nearest/',
                method: 'GET',
                data: ajaxData,
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
            
            // Show premium disclaimer if travel times were included and user is not authenticated
            const checkboxForDisclaimer = document.getElementById('include_travel_times');
            if (checkboxForDisclaimer && checkboxForDisclaimer.checked) {
                const cardBody = checkboxForDisclaimer.closest('.card-body');
                const isAuthenticated = cardBody.getAttribute('data-user-authenticated') === 'true';
                
                if (!isAuthenticated) {
                    // Show premium disclaimer in results area
                    const resultsDiv = document.getElementById('result');
                    const disclaimerDiv = document.createElement('div');
                    disclaimerDiv.className = 'alert alert-warning mb-3';
                    disclaimerDiv.innerHTML = `
                        <i class="fas fa-star me-2"></i>
                        <strong>Función Premium:</strong> Has utilizado la función de tiempos de viaje en tu búsqueda gratuita. 
                        Para obtener más centros con tiempos de viaje, <a href="/usuarios/registrarse/" class="alert-link">regístrate</a> 
                        o <a href="/usuarios/conectarse/" class="alert-link">inicia sesión</a>.
                    `;
                    
                    // Insert disclaimer at the top of results
                    const resultsCount = document.getElementById('resultsCount');
                    if (resultsCount) {
                        resultsCount.parentNode.insertBefore(disclaimerDiv, resultsCount);
                    }
                }
            }

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