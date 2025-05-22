document.addEventListener('DOMContentLoaded', function() {
    // Handle form submission
    const filterForm = document.getElementById('filterForm');
    filterForm.addEventListener('submit', function(e) {
        e.preventDefault();
        const formData = new FormData(filterForm);
        const params = new URLSearchParams(formData);
        window.location.href = '?' + params.toString();
    });

    // Handle province change
    const autonomousCommunitySelect = document.getElementById('autonomousCommunity');
    const provinceSelect = document.getElementById('province');
    
    autonomousCommunitySelect.addEventListener('change', function() {
        const community = this.value;
        if (community) {
            // Fetch provinces for selected community
            fetch(`/api/provinces/?comunidad_autonoma=${encodeURIComponent(community)}`)
                .then(response => response.json())
                .then(provinces => {
                    provinceSelect.innerHTML = '<option value="">Todas</option>';
                    provinces.forEach(province => {
                        provinceSelect.innerHTML += `<option value="${province}">${province}</option>`;
                    });
                });
        } else {
            provinceSelect.innerHTML = '<option value="">Todas</option>';
        }
    });

    // Handle municipality change
    const municipalitySelect = document.getElementById('municipality');
    
    provinceSelect.addEventListener('change', function() {
        const province = this.value;
        if (province) {
            // Fetch municipalities for selected province
            fetch(`/api/municipalities/?provincia=${encodeURIComponent(province)}`)
                .then(response => response.json())
                .then(municipalities => {
                    municipalitySelect.innerHTML = '<option value="">Todos</option>';
                    municipalities.forEach(municipality => {
                        municipalitySelect.innerHTML += `<option value="${municipality}">${municipality}</option>`;
                    });
                });
        } else {
            municipalitySelect.innerHTML = '<option value="">Todos</option>';
        }
    });
});