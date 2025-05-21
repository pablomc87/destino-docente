// Function to save search results to local storage
export const saveSearchResults = (data, searchParams) => {
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
export const loadLastSearchResults = () => {
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
export const displaySearchResults = (data) => {
    // Update results count
    $('#resultsNumber').text(data.total_count);
    
    const schoolCardsDiv = $('#schoolCards');
    schoolCardsDiv.empty();
    
    if (data.schools && data.schools.length > 0) {
        data.schools.forEach(school => {
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
                card.find('.walking-time').text(school.travel_times.walking || 'No disponible');
                card.find('.driving-time').text(school.travel_times.driving || 'No disponible');
                card.find('.bicycling-time').text(school.travel_times.bicycling || 'No disponible');
                card.find('.transit-time').text(school.travel_times.transit || 'No disponible');
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
    } else {
        $('#noResults').removeClass('d-none');
        $('#locationInfo').addClass('d-none');
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