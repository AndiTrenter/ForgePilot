import axios from "axios";

// API Base URL - uses relative path for production (nginx proxy) 
// or falls back to REACT_APP_BACKEND_URL for development
const getApiBase = () => {
  // In production (Docker), use relative /api path (nginx proxies to backend)
  // In development, use REACT_APP_BACKEND_URL if set
  const envUrl = process.env.REACT_APP_BACKEND_URL;
  
  // If running in production mode (no dev server), use relative path
  if (process.env.NODE_ENV === 'production') {
    return '/api';
  }
  
  // For development, use env variable or fallback to relative
  if (envUrl) {
    return `${envUrl}/api`;
  }
  
  // Default: relative path (works with nginx proxy)
  return '/api';
};

const API = getApiBase();

// Configure axios defaults
axios.defaults.timeout = 30000;

// Create axios instance with interceptors for better error handling
const apiClient = axios.create({
  baseURL: API,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.code === 'ERR_NETWORK') {
      console.error('Network error - Backend nicht erreichbar');
    }
    return Promise.reject(error);
  }
);

export const api = {
  // Projects
  getProjects: () => apiClient.get('/projects'),
  createProject: (data) => apiClient.post('/projects', data),
  getProject: (id) => apiClient.get(`/projects/${id}`),
  deleteProject: (id) => apiClient.delete(`/projects/${id}`),
  
  // Messages & Agents
  getMessages: (projectId) => apiClient.get(`/projects/${projectId}/messages`),
  getAgents: (projectId) => apiClient.get(`/projects/${projectId}/agents`),
  getLogs: (projectId) => apiClient.get(`/projects/${projectId}/logs`),
  getRoadmap: (projectId) => apiClient.get(`/projects/${projectId}/roadmap`),
  
  // Files
  getFiles: (projectId, path = "") => apiClient.get(`/projects/${projectId}/files`, { params: { path } }),
  saveFile: (projectId, path, content) => apiClient.put(`/projects/${projectId}/files`, { path, content }),
  
  // GitHub
  importGitHub: (data) => apiClient.post('/github/import', data),
  getGitHubRepos: () => apiClient.get('/github/repos'),
  getGitHubBranches: (repo) => apiClient.get('/github/branches', { params: { repo } }),
  
  // Preview
  getPreviewInfo: (projectId) => apiClient.get(`/projects/${projectId}/preview-info`),
  pushToGitHub: (projectId) => apiClient.post(`/projects/${projectId}/push`),
  
  // Settings
  getSettings: () => apiClient.get('/settings'),
  updateSettings: (data) => apiClient.put('/settings', data),
  deleteOpenAIKey: () => apiClient.delete('/settings/openai-key'),
  deleteGitHubToken: () => apiClient.delete('/settings/github-token'),
  
  // LLM Status
  getLLMStatus: () => apiClient.get('/llm/status'),
  refreshLLMStatus: () => apiClient.post('/llm/refresh'),
  
  // Ollama (legacy)
  getOllamaStatus: () => apiClient.get('/ollama/status'),
  enableOllama: (model) => apiClient.post('/ollama/enable', null, { params: { model } }),
  
  // Update System
  getUpdateStatus: () => apiClient.get('/update/status'),
  checkForUpdates: () => apiClient.post('/update/check'),
  installUpdate: (version) => apiClient.post('/update/install', null, { params: { target_version: version } }),
  rollbackUpdate: () => apiClient.post('/update/rollback'),
  
  // Health & Version
  getHealth: () => apiClient.get('/health'),
  getVersion: () => apiClient.get('/version'),
  
  // API info
  getApiInfo: () => apiClient.get('/'),
};

export { API };
export default api;
