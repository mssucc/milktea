// api/index.js
import axios from 'axios';

const BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: BASE_URL,
  timeout: 30000, // 30 seconds timeout for AI responses
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for adding auth tokens if needed
apiClient.interceptors.request.use(
  (config) => {
    // You can add authentication tokens here if needed
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    console.error('API Error:', error);

    // Handle different error types
    let message;
    if (error.response) {
      // Server responded with error status
      message = error.response.data?.detail || error.response.data?.message || 'Server error';
      message = `API Error: ${message}`;
    } else if (error.request) {
      // Request made but no response
      message = 'Network error: No response from server';
    } else {
      // Something else happened
      message = `Request error: ${error.message}`;
    }

    // Create new error with original error attached
    const newError = new Error(message);
    newError.originalError = error;
    newError.isAxiosError = error.isAxiosError;
    if (error.response) newError.response = error.response;
    if (error.request) newError.request = error.request;
    if (error.code) newError.code = error.code;
    if (error.config) newError.config = error.config;

    throw newError;
  }
);

// Chat API

export const sendChatMessageStream = async ({ message, session_id, system_prompt, api_key, base_url, model }) => {
  const baseURL = apiClient.defaults.baseURL || import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

  const response = await fetch(`${baseURL}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message,
      session_id,
      system_prompt,
      api_key,
      base_url,
      model
    })
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Stream request failed: ${response.status} ${response.statusText} - ${errorText}`);
  }

  return response.body; // Returns ReadableStream
};

export const getSessionMessages = async (session_id, limit = 100) => {
  return apiClient.get(`/sessions/${session_id}/messages`, {
    params: { limit }
  });
};

export const listSessions = async (limit = 100) => {
  // Use shorter timeout for session list (it's a quick query)
  return apiClient.get('/sessions', { params: { limit }, timeout: 5000 });
};

export const deleteSession = async (session_id) => {
  return apiClient.delete(`/sessions/${session_id}`);
};

// Graph API
export const fetchGraph = async (sessionId) => {
  return apiClient.get(`/graph/${sessionId}`);
};

export const fetchGlobalGraph = async (limit = 100) => {
  return apiClient.get('/graph/global', { params: { limit } });
};

export const checkNeo4jStatus = async () => {
  return apiClient.get('/neo4j-status');
};

export const diagnoseSessionGraph = async (sessionId) => {
  return apiClient.get(`/graph/diagnostics/${sessionId}`);
};

export const reanalyzeSessionGraph = async (sessionId, limit = 50, api_key = null, base_url = null, model = null) => {
  // Use longer timeout for reanalysis which may process many messages
  return apiClient.post(`/graph/${sessionId}/reanalyze`, {
    limit,
    api_key,
    base_url,
    model
  }, { timeout: 120000 }); // 120 seconds timeout for reanalysis
};

// Review API
export const fetchReview = async (sessionId, api_key = null, base_url = null, model = null, recent_days = 3, top_n_recent = 3, max_questions = 10) => {
  try {
    const response = await apiClient.post(`/review/${sessionId}`, {
      api_key,
      base_url,
      model,
      recent_days,
      top_n_recent,
      max_questions
    }, { timeout: 30000 }); // 30 seconds timeout for initial response

    // Check response status
    if (response.status === 202) {
      // Review generation started, return task info for polling
      return {
        status: 'pending',
        taskInfo: response.data,
        sessionId: sessionId
      };
    } else if (response.status === 200) {
      // Cached review available
      return {
        status: 'completed',
        data: response.data,
        sessionId: sessionId
      };
    } else {
      throw new Error(`Unexpected response status: ${response.status}`);
    }
  } catch (error) {
    // Handle axios error structure
    if (error.response) {
      const status = error.response.status;
      const data = error.response.data;

      if (status === 202) {
        // Actually got 202 but axios treated it as error (shouldn't happen with proper config)
        return {
          status: 'pending',
          taskInfo: data,
          sessionId: sessionId
        };
      }

      throw new Error(data.detail || `API error: ${status}`);
    }
    throw error;
  }
};

// New review API functions for async processing
export const pollReviewStatus = async (sessionId) => {
  return apiClient.get(`/review/${sessionId}/status`, { timeout: 5000 });
};

export const regenerateReview = async (sessionId, api_key = null, base_url = null, model = null, recent_days = 3, top_n_recent = 3, max_questions = 10) => {
  return apiClient.post(`/review/${sessionId}/regenerate`, {
    api_key,
    base_url,
    model,
    recent_days,
    top_n_recent,
    max_questions
  }, { timeout: 30000 });
};

export const fetchReviewQuestions = async (sessionId) => {
  return apiClient.get(`/review/${sessionId}/questions`);
};

export const markReviewCompleted = async (sessionId, reviewItemId) => {
  return apiClient.post(`/review/${sessionId}/complete`, { review_item_id: reviewItemId });
};

// Integrated review progress API
export const fetchIntegratedReviewProgress = async (days) => {
  return apiClient.get(`/review/integrated/progress?days=${days}`);
};

export const saveIntegratedReviewProgress = async (days, learnedCards, completedQuizzes) => {
  return apiClient.post('/review/integrated/progress', {
    days,
    learned_cards: learnedCards,
    completed_quizzes: completedQuizzes
  });
};

// Integrated review API functions
export const fetchIntegratedReview = async (limit = 10, days = 7, forceRefresh = false, api_key = null, base_url = null, model = null) => {
  try {
    const response = await apiClient.post('/review/integrated/overview', {
      limit,
      days,
      force_refresh: forceRefresh,
      api_key,
      base_url,
      model
    }, { timeout: 15000 }); // 15 seconds timeout for integrated review

    // Note: apiClient interceptors return response.data, not the full response object.
    // So `response` here is actually the data from the server.
    // The server returns either:
    // 1. For 200 OK: IntegratedReviewResponse data (with aggregated_summary, etc.)
    // 2. For 202 Accepted: {message, regenerating_sessions, task_ids, ...}

    // Check if this is a 202 Accepted response (regeneration triggered)
    if (response.message && (response.regenerating_sessions || response.sessions_triggered || response.status === 'generating')) {
      // This is a 202 response (regeneration started)
      return {
        status: 'regenerating',
        taskInfo: response,
        message: response.message || 'Review regeneration started'
      };
    } else if (response.aggregated_summary !== undefined) {
      // This is a 200 response with integrated review data
      return {
        status: 'completed',
        data: response,
        message: 'Integrated review data loaded'
      };
    } else {
      // Unexpected response format
      console.warn('Unexpected integrated review response format:', response);
      throw new Error(`Unexpected response format from integrated review endpoint`);
    }
  } catch (error) {
    // Handle axios error structure
    if (error.response) {
      const status = error.response.status;
      const data = error.response.data;

      if (status === 202) {
        // Actually got 202 but axios treated it as error (shouldn't happen with proper config)
        return {
          status: 'regenerating',
          taskInfo: data,
          message: 'Review regeneration started'
        };
      }

      throw new Error(data.detail || `API error: ${status}`);
    }
    throw error;
  }
};

export const getSessionsWithReviews = async () => {
  return apiClient.get('/review/integrated/sessions', { timeout: 5000 });
};

// Model API
export const getAvailableModels = async () => {
  return apiClient.get('/models');
};

export const getCurrentModel = async () => {
  return apiClient.get('/models/current');
};

export const switchModel = async (model_name, base_url) => {
  return apiClient.post('/models/switch', { model_name, base_url });
};

export const searchModels = async (query) => {
  return apiClient.get('/models/search', { params: { query } });
};

export const getOllamaModels = async () => {
  return apiClient.get('/models/ollama/available');
};

// Test API configuration
export const testApiConfig = async ({ api_key, base_url, model }) => {
  try {
    // Try a simple completion request
    const response = await fetch(`${base_url}/chat/completions`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': api_key ? `Bearer ${api_key}` : undefined
      },
      body: JSON.stringify({
        model: model,
        messages: [{ role: 'user', content: 'Hi' }],
        max_tokens: 5
      })
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error?.message || `HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return {
      success: true,
      message: '连接成功！API 配置正常工作。',
      model: data.model
    };
  } catch (error) {
    return {
      success: false,
      message: error.message || '连接失败，请检查配置。'
    };
  }
};

// Default export
export default apiClient;