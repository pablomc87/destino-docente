$(document).ready(function() {
    let map;
    let marker;
    let lastGeocodeRequest = null;

    // Initialize map
    function initMap() {
        map = L.map('map').setView([40.4168, -3.7038], 6); // Center of Spain
        
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(map);

        // Add marker
        marker = L.marker([40.4168, -3.7038], {
            draggable: true
        }).addTo(map);

        // Update coordinates when marker is dragged
        marker.on('dragend', function() {
            const position = marker.getLatLng();
            $('#latitude').val(position.lat);
            $('#longitude').val(position.lng);
        });
    }

    // Geocode address and update map
    function updateMapLocation() {
        const community = $('#autonomous_community').val();
        const province = $('#province').val();
        const municipality = $('#municipality').val();
        const postalCode = $('#postal_code').val();
        const address = $('#address').val();

        // Build address string based on available information
        let addressString = '';
        if (address) addressString += address + ', ';
        if (municipality) addressString += municipality + ', ';
        if (province) addressString += province + ', ';
        if (community) addressString += community + ', ';
        if (postalCode) addressString += postalCode + ', ';
        addressString += 'Spain';

        if (addressString === 'Spain') return; // Don't geocode if no location info

        // Cancel previous request if it exists
        if (lastGeocodeRequest) {
            lastGeocodeRequest.abort();
        }

        // Create new request
        lastGeocodeRequest = $.ajax({
            url: 'https://nominatim.openstreetmap.org/search',
            data: {
                q: addressString,
                format: 'json',
                limit: 1,
                countrycodes: 'es', // Limit to Spain
                addressdetails: 1,  // Get detailed address information
                'accept-language': 'es' // Get results in Spanish
            },
            success: function(results) {
                if (results && results[0]) {
                    const location = results[0];
                    const latLng = L.latLng(location.lat, location.lon);
                    
                    // Calculate precision score (higher = more precise)
                    let precision = 0;
                    if (address) precision += 3;      // Street address is most precise
                    if (postalCode) precision += 2;  // Postal code is very precise
                    if (municipality) precision += 2; // Municipality is quite precise
                    if (province) precision += 1;    // Province gives general area
                    if (community) precision += 1;   // Community gives broad area
                    
                    // Set zoom level based on precision score
                    let zoomLevel = 6; // Default zoom for Spain
                    if (precision >= 8) {
                        zoomLevel = 18; // Very precise (street + postal code + municipality)
                    } else if (precision >= 6) {
                        zoomLevel = 15; // Precise (postal code + municipality)
                    } else if (precision >= 4) {
                        zoomLevel = 12; // City level (municipality)
                    } else if (precision >= 2) {
                        zoomLevel = 9;  // Province level
                    } else if (precision >= 1) {
                        zoomLevel = 7;  // Autonomous community level
                    }

                    // If we have a street address, center on that
                    // Otherwise, center on the administrative area
                    let centerPoint = latLng;
                    if (!address) {
                        // Get the administrative center for the area
                        const adminLevel = location.addressdetails || {};
                        if (municipality && adminLevel.city) {
                            // Center on municipality
                            centerPoint = L.latLng(adminLevel.city.lat, adminLevel.city.lon);
                        } else if (province && adminLevel.state) {
                            // Center on province
                            centerPoint = L.latLng(adminLevel.state.lat, adminLevel.state.lon);
                        } else if (community && adminLevel.region) {
                            // Center on autonomous community
                            centerPoint = L.latLng(adminLevel.region.lat, adminLevel.region.lon);
                        }
                    }

                    // Set view with smooth animation
                    map.flyTo(centerPoint, zoomLevel, {
                        duration: 1, // Animation duration in seconds
                        easeLinearity: 0.25
                    });
                    
                    // Update marker position
                    marker.setLatLng(latLng);

                    // Update hidden fields
                    $('#latitude').val(location.lat);
                    $('#longitude').val(location.lng);
                }
            }
        });
    }

    // Initialize map
    initMap();

    // Add event listeners for location fields
    $('#autonomous_community, #province, #municipality, #postal_code, #address').on('change', function() {
        updateMapLocation();
    });

    // Initialize Select2 for studies
    $('#studies').select2({
        placeholder: 'Selecciona los estudios...',
        allowClear: true,
        width: '100%'
    });

    // Handle autonomous community change
    $('#autonomous_community').change(function() {
        const community = $(this).val();
        const provinceSelect = $('#province');
        
        if (community) {
            // Clear and add placeholder
            provinceSelect.empty().append('<option value="">Selecciona una provincia...</option>');
            
            // Add filtered provinces
            $('#provinceData div').each(function() {
                if ($(this).data('community') === community) {
                    const province = $(this).data('province');
                    provinceSelect.append(`<option value="${province}">${province}</option>`);
                }
            });
            
            provinceSelect.prop('disabled', false);
        } else {
            provinceSelect.empty().append('<option value="">Selecciona una provincia...</option>');
            provinceSelect.prop('disabled', true);
        }
    });

    // Handle nature change
    $('#nature').change(function() {
        const nature = $(this).val();
        const isConcertedToggle = $('#is_concerted');
        
        if (nature === 'Concertado') {
            isConcertedToggle.prop('checked', true);
            isConcertedToggle.prop('disabled', true);
        } else {
            isConcertedToggle.prop('disabled', false);
        }
    });

    // Prevent double submission
    let isSubmitting = false;
    $('#suggestionForm').on('submit', function(e) {
        e.preventDefault(); // Prevent the default form submission
        
        if (isSubmitting) {
            return;
        }
        isSubmitting = true;
        
        // Get current marker position
        const position = marker.getLatLng();
        $('#latitude').val(position.lat);
        $('#longitude').val(position.lng);
        
        const formData = new FormData(this);
        const data = Object.fromEntries(formData.entries());
        
        // Convert studies to array
        data.studies = $('#studies').val();
        
        // Ensure coordinates are included
        data.latitude = position.lat;
        data.longitude = position.lng;
        
        fetch('{% url "api:suggest_school" %}', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
            },
            body: JSON.stringify(data)
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => {
                    throw new Error(err.detail || 'Error al enviar la sugerencia');
                });
            }
            return response.json();
        })
        .then(data => {
            alert('Sugerencia enviada correctamente. Un administrador la revisará pronto.');
            window.location.href = '/';
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Error: ' + error.message);
        })
        .finally(() => {
            isSubmitting = false;
        });
    });
});