import { getTrackingState, updateTrackingState } from './state.js';

// Constants
export const API_CALLS_THRESHOLD = 10;
export const TRACKING_INTERVAL = 60000; // 1 minute

let lastTrackingTime = Date.now();

// Function to get cookie value by name
export function getCookie(name) {
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
export async function checkApiLimits() {
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
export const showApiLimitMessage = () => {
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
export const shouldTrack = () => {
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
export const trackApiCalls = (source) => {
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