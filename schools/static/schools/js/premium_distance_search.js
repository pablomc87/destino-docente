document.addEventListener('DOMContentLoaded', function() {
    const searchForm = document.getElementById('searchForm');
    const resultsDiv = document.getElementById('results');
    const resultsBody = document.getElementById('resultsBody');
    const resultCount = document.getElementById('resultCount');
    const calculateTravelTimesBtn = document.getElementById('calculateTravelTimes');
    const typeList = document.getElementById('typeList');
    const selectedTypes = document.getElementById('selectedTypes');
    const typeSelectTrigger = document.getElementById('typeSelectTrigger');
    const addressInput = document.getElementById('address');
    const errorMessage = document.getElementById('errorMessage');
    const errorText = document.getElementById('errorText');
    
    let selectedSchools = [];
    let selectedSchoolTypes = new Set();
    let autocomplete;
    let currentSearchHistoryId = null;  // Store the current search history ID
    
    // Function to show error message
    function showError(message) {
        errorText.textContent = message;
        errorMessage.style.display = 'block';
        // Scroll to error message
        errorMessage.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    
    // Function to hide error message
    function hideError() {
        errorMessage.style.display = 'none';
    }
    
    // Initialize Google Places Autocomplete
    function initAutocomplete() {
        autocomplete = new google.maps.places.Autocomplete(addressInput, {
            componentRestrictions: { country: 'es' },
            fields: ['address_components', 'geometry', 'formatted_address'],
            types: ['address']
        });
        
        // Prevent form submission on enter key
        addressInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
            }
        });
    }
    
    // Initialize autocomplete when Google Maps API is loaded
    if (typeof google !== 'undefined' && google.maps && google.maps.places) {
        initAutocomplete();
    } else {
        // If Google Maps API is not loaded yet, wait for it
        window.initAutocomplete = initAutocomplete;
    }
    
    // Handle dropdown toggle
    typeSelectTrigger.addEventListener('click', function() {
        typeList.classList.toggle('show');
        typeSelectTrigger.classList.toggle('active');
    });
    
    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!e.target.closest('.type-list-container')) {
            typeList.classList.remove('show');
            typeSelectTrigger.classList.remove('active');
        }
    });
    
    // Handle school type selection
    typeList.addEventListener('click', function(e) {
        const option = e.target.closest('.type-option');
        if (!option) return;
        
        const value = option.dataset.value;
        if (selectedSchoolTypes.has(value)) {
            // Deselect
            selectedSchoolTypes.delete(value);
            option.classList.remove('selected');
            removeTypeTag(value);
        } else {
            // Select
            selectedSchoolTypes.add(value);
            option.classList.add('selected');
            addTypeTag(value);
        }
    });
    
    function addTypeTag(value) {
        const tag = document.createElement('div');
        tag.className = 'type-tag';
        tag.dataset.value = value;
        tag.textContent = value;
        selectedTypes.appendChild(tag);
        
        // Add click handler for the entire tag
        tag.addEventListener('click', function() {
            selectedSchoolTypes.delete(value);
            tag.remove();
            typeList.querySelector(`[data-value="${value}"]`).classList.remove('selected');
        });
    }
    
    function removeTypeTag(value) {
        const tag = selectedTypes.querySelector(`[data-value="${value}"]`);
        if (tag) tag.remove();
    }
    
    searchForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        hideError();
        
        const address = addressInput.value;
        const autonomousCommunity = document.getElementById('autonomous_community').value;
        
        if (!address) {
            showError('Por favor, introduce una dirección válida');
            return;
        }
        
        try {
            // Show loading state
            searchForm.querySelector('button[type="submit"]').disabled = true;
            searchForm.querySelector('button[type="submit"]').innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Buscando...';
            
            // Get coordinates using Google Maps Geocoding API
            const geocoder = new google.maps.Geocoder();
            const geocodeResult = await new Promise((resolve, reject) => {
                geocoder.geocode({ address: address }, (results, status) => {
                    if (status === 'OK') {
                        resolve(results[0]);
                    } else {
                        reject(new Error('No se pudo encontrar la ubicación'));
                    }
                });
            });
            
            const location = geocodeResult.geometry.location;
            const latitude = location.lat();
            const longitude = location.lng();
            
            // Build autonomous communities array
            const autonomousCommunities = autonomousCommunity ? [autonomousCommunity] : [];
            
            // Build school types array
            const schoolTypes = Array.from(selectedSchoolTypes);
            
            // Make API request to profile_search endpoint
            const response = await fetch(`/api/profile/search/?address=${encodeURIComponent(address)}&latitude=${latitude}&longitude=${longitude}&autonomous_communities=${autonomousCommunities.join(',')}&school_types=${schoolTypes.join(',')}&include_travel_times=false`);
            
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Error en la búsqueda');
            }
            
            if (!data.schools || data.schools.length === 0) {
                showError('No se encontraron centros con datos de ubicación que coincidan con tus criterios');
                return;
            }
            
            // Store the search history ID
            currentSearchHistoryId = data.search_history_id;
            
            // Display results
            displayResults(data.schools);
            selectedSchools = data.schools;
            calculateTravelTimesBtn.style.display = 'block';
            
        } catch (error) {
            showError(error.message || 'Ha ocurrido un error al realizar la búsqueda');
        } finally {
            // Reset loading state
            searchForm.querySelector('button[type="submit"]').disabled = false;
            searchForm.querySelector('button[type="submit"]').innerHTML = 'Buscar Centros';
        }
    });
    
    calculateTravelTimesBtn.addEventListener('click', async function() {
        // Get selected schools
        const selectedCheckboxes = document.querySelectorAll('.school-checkbox:checked');
        if (selectedCheckboxes.length === 0) {
            showError('No hay centros seleccionados para calcular tiempos de viaje.');
            return;
        }
        
        try {
            // Show loading state
            calculateTravelTimesBtn.disabled = true;
            calculateTravelTimesBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Calculando...';
            
            const address = addressInput.value;
            const autonomousCommunity = document.getElementById('autonomous_community').value;
            const autonomousCommunities = autonomousCommunity ? [autonomousCommunity] : [];
            const schoolTypes = Array.from(selectedSchoolTypes);
            
            // Get coordinates
            const geocoder = new google.maps.Geocoder();
            const geocodeResult = await new Promise((resolve, reject) => {
                geocoder.geocode({ address: address }, (results, status) => {
                    if (status === 'OK') {
                        resolve(results[0]);
                    } else {
                        reject(new Error('No se pudo encontrar la ubicación'));
                    }
                });
            });
            
            const location = geocodeResult.geometry.location;
            const latitude = location.lat();
            const longitude = location.lng();
            
            // Get selected school IDs
            const selectedSchoolIds = Array.from(selectedCheckboxes).map(checkbox => checkbox.dataset.schoolId);
            
            // Make API request with travel times and search history ID
            const url = new URL('/api/profile/search/', window.location.origin);
            url.searchParams.append('address', address);
            url.searchParams.append('latitude', latitude);
            url.searchParams.append('longitude', longitude);
            url.searchParams.append('autonomous_communities', autonomousCommunities.join(','));
            url.searchParams.append('school_types', schoolTypes.join(','));
            url.searchParams.append('include_travel_times', 'true');
            url.searchParams.append('school_ids', selectedSchoolIds.join(','));
            if (currentSearchHistoryId) {
                url.searchParams.append('search_history_id', currentSearchHistoryId);
            }
            
            const response = await fetch(url);
            const data = await response.json();
            
            if (!response.ok) {
                throw new Error(data.error || 'Error al calcular los tiempos de viaje');
            }
            
            // Update results with travel times
            updateResultsWithTravelTimes(data.schools);
            
        } catch (error) {
            showError(error.message || 'Ha ocurrido un error al calcular los tiempos de viaje');
        } finally {
            // Reset loading state
            calculateTravelTimesBtn.disabled = false;
            calculateTravelTimesBtn.innerHTML = 'Calcular Tiempos de Viaje';
        }
    });
    
    function displayResults(schools) {
        resultsBody.innerHTML = '';
        resultCount.textContent = schools.length;
        
        schools.forEach(school => {
            const row = document.createElement('tr');
            row.setAttribute('data-school-id', school.id);
            row.innerHTML = `
                <td>
                    <div class="form-check">
                        <input class="form-check-input school-checkbox" type="checkbox" checked data-school-id="${school.id}">
                    </div>
                </td>
                <td>
                    <div class="d-flex justify-content-between align-items-start">
                        <div>
                            <a href="/centros/${school.id}/" target="_blank" class="fw-bold">${school.name}</a>
                            <br>
                            <small class="text-muted">
                                ${school.center_type} - ${school.nature}<br>
                                ${school.address}, ${school.municipality}<br>
                                ${school.phone}
                            </small>
                        </div>
                    </div>
                </td>
                <td>
                    <span class="badge bg-primary">${school.distance.toFixed(1)} km</span>
                </td>
                <td>
                    <div class="d-flex justify-content-between">
                        <div class="text-center" style="width: 25%;">
                            <span class="walking-time">-</span>
                        </div>
                        <div class="text-center" style="width: 25%;">
                            <span class="driving-time">-</span>
                        </div>
                        <div class="text-center" style="width: 25%;">
                            <span class="bicycling-time">-</span>
                        </div>
                        <div class="text-center" style="width: 25%;">
                            <span class="transit-time">-</span>
                        </div>
                    </div>
                </td>
            `;
            resultsBody.appendChild(row);
        });
        
        resultsDiv.style.display = 'block';
    }
    
    function updateResultsWithTravelTimes(schools) {
        // Get selected school IDs
        const selectedSchoolIds = Array.from(document.querySelectorAll('.school-checkbox:checked'))
            .map(checkbox => checkbox.dataset.schoolId);
        
        // Filter schools to only include selected ones
        const selectedSchools = schools.filter(school => selectedSchoolIds.includes(school.id.toString()));
        
        selectedSchools.forEach(school => {
            const row = resultsBody.querySelector(`tr[data-school-id="${school.id}"]`);
            if (row && school.travel_times) {
                const walkingTime = row.querySelector('.walking-time');
                const drivingTime = row.querySelector('.driving-time');
                const bicyclingTime = row.querySelector('.bicycling-time');
                const transitTime = row.querySelector('.transit-time');

                if (walkingTime) walkingTime.textContent = school.travel_times.walking;
                if (drivingTime) drivingTime.textContent = school.travel_times.driving;
                if (bicyclingTime) bicyclingTime.textContent = school.travel_times.bicycling;
                if (transitTime) transitTime.textContent = school.travel_times.transit;
            }
        });
    }
    
    function formatDuration(seconds) {
        if (!seconds) return 'No disponible';
        if (seconds < 60) {
            return `${seconds}s`;
        }
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = seconds % 60;
        return `${minutes}m ${remainingSeconds}s`;
    }

    // Add event listeners for checkbox functionality
    document.getElementById('selectAllSchools').addEventListener('change', function(e) {
        const checkboxes = document.querySelectorAll('.school-checkbox');
        checkboxes.forEach(checkbox => {
            checkbox.checked = e.target.checked;
        });
    });

    document.getElementById('unselectAllSchools').addEventListener('click', function() {
        const checkboxes = document.querySelectorAll('.school-checkbox');
        checkboxes.forEach(checkbox => {
            checkbox.checked = false;
        });
        document.getElementById('selectAllSchools').checked = false;
    });

    // Update select all checkbox when individual checkboxes change
    resultsBody.addEventListener('change', function(e) {
        if (e.target.classList.contains('school-checkbox')) {
            const allCheckboxes = document.querySelectorAll('.school-checkbox');
            const allChecked = Array.from(allCheckboxes).every(checkbox => checkbox.checked);
            document.getElementById('selectAllSchools').checked = allChecked;
        }
    });

    async function calculateTravelTimes() {
        const selectedSchools = document.querySelectorAll('input[name="school_ids"]:checked');
        if (selectedSchools.length === 0) {
            showError('Por favor, selecciona al menos un centro para calcular los tiempos de viaje');
            return;
        }

        const schoolIds = Array.from(selectedSchools).map(checkbox => checkbox.value);
        const url = new URL('/api/profile/search/', window.location.origin);
        url.searchParams.append('address', document.getElementById('address').value);
        url.searchParams.append('latitude', document.getElementById('latitude').value);
        url.searchParams.append('longitude', document.getElementById('longitude').value);
        url.searchParams.append('include_travel_times', 'true');
        schoolIds.forEach(id => url.searchParams.append('school_ids', id));

        try {
            const response = await fetch(url);
            if (!response.ok) {
                const data = await response.json();
                throw new Error(data.error || 'Error al calcular los tiempos de viaje');
            }

            const data = await response.json();
            const resultsTable = document.getElementById('resultsTable');
            const tbody = resultsTable.querySelector('tbody');

            // Update travel times for selected schools
            data.schools.forEach(school => {
                const row = tbody.querySelector(`tr[data-school-id="${school.id}"]`);
                if (row) {
                    const travelTimesCell = row.querySelector('.travel-times');
                    if (school.travel_times) {
                        travelTimesCell.innerHTML = `
                            <div class="travel-time-item">
                                <i class="fas fa-car"></i>
                                <span>${school.travel_times.car || 'N/A'}</span>
                            </div>
                            <div class="travel-time-item">
                                <i class="fas fa-bus"></i>
                                <span>${school.travel_times.public_transport || 'N/A'}</span>
                            </div>
                            <div class="travel-time-item">
                                <i class="fas fa-walking"></i>
                                <span>${school.travel_times.walking || 'N/A'}</span>
                            </div>
                            <div class="travel-time-item">
                                <i class="fas fa-bicycle"></i>
                                <span>${school.travel_times.bicycle || 'N/A'}</span>
                            </div>
                        `;
                    } else {
                        travelTimesCell.innerHTML = '<span class="text-muted">No disponible</span>';
                    }
                }
            });

            // Show success message
            const successMessage = document.createElement('div');
            successMessage.className = 'alert alert-success mt-3';
            successMessage.innerHTML = '<i class="fas fa-check-circle"></i> Tiempos de viaje calculados correctamente';
            resultsTable.parentNode.insertBefore(successMessage, resultsTable.nextSibling);
            setTimeout(() => successMessage.remove(), 3000);

        } catch (error) {
            showError(error.message);
        }
    }
}); 