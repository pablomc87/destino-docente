// Google Places integration
let autocomplete = null;

export const initializePlaces = () => {
    const input = document.getElementById('address');
    if (!input) return;

    autocomplete = new google.maps.places.Autocomplete(input, {
        componentRestrictions: { country: 'es' },
        fields: ['address_components', 'geometry', 'formatted_address'],
        types: ['address']
    });

    return autocomplete;
};

export const getPlaceDetails = (place) => {
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

export const getAutocomplete = () => autocomplete; 