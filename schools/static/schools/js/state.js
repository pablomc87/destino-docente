// State management functions
export const getTrackingState = () => {
    const state = sessionStorage.getItem('trackingState');
    return state ? JSON.parse(state) : {
        totalApiCalls: 0,
        placeSelected: false,
        totalResponseTimeMs: 0,
        lastInputTime: Date.now()
    };
};

export const setTrackingState = (state) => {
    sessionStorage.setItem('trackingState', JSON.stringify(state));
};

export const updateTrackingState = (updates) => {
    const state = getTrackingState();
    const newState = { ...state, ...updates };
    setTrackingState(newState);
    return newState;
};

export const resetSession = () => {
    setTrackingState({
        totalApiCalls: 0,
        placeSelected: false,
        totalResponseTimeMs: 0,
        lastInputTime: Date.now()
    });
}; 