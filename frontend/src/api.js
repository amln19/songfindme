// Centralized API configuration
export const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const apiEndpoints = {
  register: `${API_URL}/register`,
  login: `${API_URL}/token`,
  addSong: `${API_URL}/add-song`,
  identify: `${API_URL}/identify`,
  history: `${API_URL}/history`,
  health: `${API_URL}/health`,
};