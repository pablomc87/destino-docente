document.addEventListener('DOMContentLoaded', function() {
    // Handle form submission
    const filterForm = document.getElementById('filterForm');
    const autonomousCommunitySelect = document.getElementById('autonomousCommunity');
    const provinceSelect = document.getElementById('province');
    const municipalitySelect = document.getElementById('municipality');

    // Function to show loading state
    function setLoading(select, isLoading) {
        select.disabled = isLoading;
        if (isLoading) {
            select.classList.add('is-loading');
        } else {
            select.classList.remove('is-loading');
        }
    }

    // Function to handle fetch with timeout
    async function fetchWithTimeout(url, options = {}, timeout = 5000) {
        console.log('Fetching:', url);
        const controller = new AbortController();
        const id = setTimeout(() => controller.abort(), timeout);
        
        try {
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });
            clearTimeout(id);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            console.log('Fetch response:', data);
            return data;
        } catch (error) {
            clearTimeout(id);
            console.error('Fetch error:', error);
            throw error;
        }
    }

    // Handle autonomous community change
    autonomousCommunitySelect.addEventListener('change', async function() {
        const community = this.value;
        console.log('Selected community:', community);
        
        if (community) {
            setLoading(provinceSelect, true);
            try {
                const provinces = await fetchWithTimeout(
                    `/api/provinces/?comunidad_autonoma=${encodeURIComponent(community)}`
                );
                provinceSelect.innerHTML = '<option value="">Todas</option>';
                provinces.forEach(province => {
                    provinceSelect.innerHTML += `<option value="${province}">${province}</option>`;
                });
            } catch (error) {
                console.error('Error fetching provinces:', error);
                alert('Error al cargar las provincias. Por favor, intenta de nuevo.');
            } finally {
                setLoading(provinceSelect, false);
            }
        } else {
            provinceSelect.innerHTML = '<option value="">Todas</option>';
        }
        
        // Reset municipality select
        municipalitySelect.innerHTML = '<option value="">Todos</option>';
    });

    // Handle province change
    provinceSelect.addEventListener('change', async function() {
        const province = this.value;
        console.log('Selected province:', province);
        
        if (province) {
            setLoading(municipalitySelect, true);
            try {
                const municipalities = await fetchWithTimeout(
                    `/api/municipalities/?provincia=${encodeURIComponent(province)}`
                );
                municipalitySelect.innerHTML = '<option value="">Todos</option>';
                municipalities.forEach(municipality => {
                    municipalitySelect.innerHTML += `<option value="${municipality}">${municipality}</option>`;
                });
            } catch (error) {
                console.error('Error fetching municipalities:', error);
                alert('Error al cargar los municipios. Por favor, intenta de nuevo.');
            } finally {
                setLoading(municipalitySelect, false);
            }
        } else {
            municipalitySelect.innerHTML = '<option value="">Todos</option>';
        }
    });

    // Handle form submission
    filterForm.addEventListener('submit', function(e) {
        e.preventDefault();
        console.log('Form submitted');
        
        // Get all form data
        const formData = new FormData(filterForm);
        const params = new URLSearchParams(formData);
        console.log('Form data:', Object.fromEntries(formData));
        
        // Submit the form
        window.location.href = filterForm.action + '?' + params.toString();
    });

    // Handle reset button
    filterForm.querySelector('button[type="reset"]').addEventListener('click', function() {
        console.log('Form reset');
        // Reset all selects to their default state
        autonomousCommunitySelect.value = '';
        provinceSelect.innerHTML = '<option value="">Todas</option>';
        municipalitySelect.innerHTML = '<option value="">Todos</option>';
    });
});