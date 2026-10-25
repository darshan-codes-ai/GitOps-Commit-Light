/**
 * Centralized API Client for GitOps Commit Light Local Backend
 * 
 * Communicates with the local FastAPI / uvicorn backend service.
 * Supports environment variable configuration via VITE_API_URL
 * with graceful offline detection and fallback.
 */

const API_BASE_URL = (import.meta.env.VITE_API_URL || 'http://localhost:8000').replace(/\/+$/, '');

/**
 * Generic request helper with timeout and standardized error handling.
 */
async function request(endpoint, options = {}) {
  const url = `${API_BASE_URL}${endpoint}`;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 6000);

  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        ...(options.headers || {}),
      },
    });

    clearTimeout(timeoutId);

    if (!res.ok) {
      let errData = {};
      try {
        errData = await res.json();
      } catch {
        errData = { detail: res.statusText };
      }
      return {
        success: false,
        status: res.status,
        error: errData.detail || errData.message || `Request failed with HTTP ${res.status}`,
        data: errData,
      };
    }

    const data = await res.json();
    return {
      success: true,
      status: res.status,
      data,
    };
  } catch (err) {
    clearTimeout(timeoutId);
    const isOffline = err.name === 'AbortError' || err.message?.includes('Failed to fetch') || err.message?.includes('NetworkError');
    return {
      success: false,
      isOffline,
      error: isOffline ? 'Backend server unreachable at ' + API_BASE_URL : err.message,
      data: null,
    };
  }
}

export const apiClient = {
  getBaseUrl: () => API_BASE_URL,

  /**
   * Healthcheck to detect whether the local Python backend server is running.
   */
  checkHealth: async () => {
    return await request('/api/health');
  },

  /**
   * Retrieve dynamic KPI metrics directly from the backend event store.
   */
  getStats: async () => {
    return await request('/api/stats');
  },

  /**
   * Retrieve all simulated events from the backend.
   */
  getEvents: async () => {
    return await request('/api/events');
  },

  /**
   * Retrieve messages published to the mock MQTT broker.
   */
  getMqttMessages: async () => {
    return await request('/api/mqtt/messages');
  },

  /**
   * Simulate a GitHub push webhook via backend lambda_function handler.
   */
  simulatePush: async (formData) => {
    return await request('/api/simulate', {
      method: 'POST',
      body: JSON.stringify(formData),
    });
  },

  /**
   * Reset backend event store (action: 'restore' to restore seed events, 'clear' to empty).
   */
  resetEvents: async (action = 'restore') => {
    return await request('/api/reset', {
      method: 'POST',
      body: JSON.stringify({ action }),
    });
  },
};

export default apiClient;

