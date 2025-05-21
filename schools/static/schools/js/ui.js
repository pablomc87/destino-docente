// UI-related functions
export const showLoading = () => {
    $('#loading').removeClass('d-none');
    $('#result').addClass('d-none');
};

export const hideLoading = () => {
    $('#loading').addClass('d-none');
};

export const showError = (message) => {
    const errorDiv = $('#error');
    errorDiv.text(message);
    errorDiv.removeClass('d-none');
    hideLoading();
};

export const hideError = () => {
    $('#error').addClass('d-none');
};

export const disableSearchForm = () => {
    $('#searchForm input, #searchForm select, #searchForm button').prop('disabled', true);
};

export const enableSearchForm = () => {
    $('#searchForm input, #searchForm select, #searchForm button').prop('disabled', false);
};

export const saveScrollPosition = (schoolId) => {
    sessionStorage.setItem('scrollPosition', window.scrollY);
    sessionStorage.setItem('lastViewedSchool', schoolId);
};

export const restoreScrollPosition = () => {
    const scrollPosition = sessionStorage.getItem('scrollPosition');
    const lastViewedSchool = sessionStorage.getItem('lastViewedSchool');
    
    if (scrollPosition && lastViewedSchool) {
        window.scrollTo(0, parseInt(scrollPosition));
        sessionStorage.removeItem('scrollPosition');
        sessionStorage.removeItem('lastViewedSchool');
    }
}; 