document.addEventListener('DOMContentLoaded', async function() {
    // Helper function to safely update element text
    function updateElementText(elementId, text) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = text;
        }
    }

    // Helper function to safely update element HTML
    function updateElementHTML(elementId, html) {
        const element = document.getElementById(elementId);
        if (element) {
            element.innerHTML = html;
        }
    }

    try {
        // Get school ID from URL
        const pathParts = window.location.pathname.split('/');
        const schoolId = pathParts[pathParts.length - 2];
        
        if (!schoolId) {
            updateElementText('schoolName', 'ID de centro no válido');
            updateElementText('schoolLocation', 'Por favor, vuelve a la página de búsqueda');
            return;
        }
        
        // Fetch school details
        const response = await fetch(`/api/schools/${schoolId}/`);
        if (!response.ok) {
            throw new Error(`Error ${response.status}: ${response.statusText}`);
        }
        const school = await response.json();
        
        // Update basic information
        updateElementText('schoolName', school.name || 'Nombre no disponible');
        updateElementText('schoolLocation', `${school.municipality || ''}, ${school.province || ''}`);
        updateElementText('centerType', school.center_type || 'No especificado');
        updateElementText('nature', school.nature || 'No especificado');
        updateElementText('autonomousCommunity', school.autonomous_community || 'No especificado');
        updateElementText('province', school.province || 'No especificado');
        updateElementText('municipality', school.municipality || 'No especificado');
        updateElementText('isConcerted', school.is_concerted ? 'Sí' : 'No');
        updateElementText('genericName', school.generic_name || 'No especificado');
        updateElementText('services', school.services || 'No especificado');
        
        // Update contact information
        updateElementText('address', school.address || 'No especificado');
        updateElementText('postalCode', school.postal_code || 'No especificado');
        updateElementText('phone', school.phone || 'No especificado');
        updateElementText('email', school.email || 'No especificado');
        // Update web link
        const webLink = document.getElementById('web');
        if (webLink) {
            if (school.website) {
                webLink.href = school.website;
                webLink.textContent = school.website;
            } else {
                webLink.textContent = 'No disponible';
                webLink.removeAttribute('href');
            }
        }

        // Initialize map if coordinates are available
        if (school.latitude && school.longitude) {
            const map = L.map('map').setView([school.latitude, school.longitude], 15);
            
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(map);

            L.marker([school.latitude, school.longitude])
                .addTo(map)
                .bindPopup(school.name)
                .openPopup();
        } else {
            // If no coordinates, show a message
            const mapDiv = document.getElementById('map');
            mapDiv.innerHTML = '<div class="alert alert-info">Ubicación no disponible</div>';
        }
        
        // Update studies
        const studiesContainer = document.getElementById('studiesList');
        if (studiesContainer) {
            if (school.studies && school.studies.length > 0) {
                studiesContainer.innerHTML = ''; // Clear existing content
                school.studies.forEach(study => {
                    const studyCard = document.createElement('div');
                    studyCard.className = 'col-md-6 col-lg-4';
                    studyCard.innerHTML = `
                        <div class="card study-card">
                            <div class="card-body">
                                <h5 class="card-title study-degree">${study.name || 'Sin nombre'}</h5>
                                ${study.degree ? `<p class="study-family">${study.degree}</p>` : ''}
                                ${study.modality ? `<p class="study-modality">${study.modality}</p>` : ''}
                            </div>
                        </div>
                    `;
                    studiesContainer.appendChild(studyCard);
                });
            } else {
                studiesContainer.innerHTML = '<div class="col-12"><p>No hay información disponible sobre los estudios impartidos.</p></div>';
            }
        }
        
        // Update services
        const servicesContainer = document.getElementById('services');
        if (servicesContainer) {
            if (school.services && Object.keys(school.services).length > 0) {
                servicesContainer.innerHTML = ''; // Clear existing content
                Object.entries(school.services).forEach(([key, value]) => {
                    const serviceBadge = document.createElement('span');
                    serviceBadge.className = 'service-badge other';  // Use a default style for all services
                    serviceBadge.textContent = value || key;
                    servicesContainer.appendChild(serviceBadge);
                });
            } else {
                servicesContainer.innerHTML = '<span class="text-muted">No hay servicios especificados</span>';
            }
        }
    } catch (error) {
        console.error('Error:', error);
        updateElementText('schoolName', 'Error al cargar los datos');
        updateElementText('schoolLocation', 'Por favor, intenta de nuevo más tarde');
    }
});