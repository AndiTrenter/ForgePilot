import axios from "axios";

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

export const api = {
  // Projects
  getProjects: () => axios.get(`${API}/projects`),
  createProject: (data) => axios.post(`${API}/projects`, data),
  getProject: (id) => axios.get(`${API}/projects/${id}`),
  deleteProject: (id) => axios.delete(`${API}/projects/${id}`),
  
  // Messages & Agents
  getMessages: (projectId) => axios.get(`${API}/projects/${projectId}/messages`),
  getAgents: (projectId) => axios.get(`${API}/projects/${projectId}/agents`),
  getLogs: (projectId) => axios.get(`${API}/projects/${projectId}/logs`),
  getRoadmap: (projectId) => axios.get(`${API}/projects/${projectId}/roadmap`),
  
  // Files
  getFiles: (projectId, path = "") => axios.get(`${API}/projects/${projectId}/files`, { params: { path } }),
  saveFile: (projectId, path, content) => axios.put(`${API}/projects/${projectId}/files`, { path, content }),
  
  // GitHub
  importGitHub: (data) => axios.post(`${API}/github/import`, data),
  commitGitHub: (data) => axios.post(`${API}/github/commit`, data),
  getGitHubRepos: () => axios.get(`${API}/github/repos`),
  getGitHubBranches: (repo) => axios.get(`${API}/github/branches`, { params: { repo } }),
  
  // Preview
  getPreviewInfo: (projectId) => axios.get(`${API}/projects/${projectId}/preview-info`),
  pushToGitHub: (projectId) => axios.post(`${API}/projects/${projectId}/push`),
};

export { API, BACKEND_URL };
