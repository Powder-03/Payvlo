/**
 * Centralized API Client for Payvlo Commerce Node & SaaS Portal
 */
const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

function getHeaders() {
  const token = localStorage.getItem('payvlo_token');
  const headers = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export const api = {
  // Auth
  async signup(data) {
    const res = await fetch(`${API_BASE}/api/v1/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Signup failed');
    }
    return res.json();
  },

  async login(email, password) {
    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Invalid email or password');
    }
    return res.json();
  },

  async getMe() {
    const res = await fetch(`${API_BASE}/api/v1/auth/me`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Session expired');
    return res.json();
  },

  // User / Buyer Address Book
  async getAddresses() {
    const res = await fetch(`${API_BASE}/api/v1/auth/addresses`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch addresses');
    return res.json();
  },

  async saveAddress(addressData) {
    const res = await fetch(`${API_BASE}/api/v1/auth/addresses`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(addressData),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to save address');
    }
    return res.json();
  },

  async deleteAddress(addressId) {
    const res = await fetch(`${API_BASE}/api/v1/auth/addresses/${addressId}`, {
      method: 'DELETE',
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to delete address');
    return res.json();
  },

  // MCP API Key
  async getApiKey() {
    const res = await fetch(`${API_BASE}/api/v1/auth/api-key`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to generate API Key');
    return res.json();
  },

  // Merchant Store Operations
  async getMyStore() {
    const res = await fetch(`${API_BASE}/api/v1/merchants/my-store`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch store details');
    return res.json();
  },

  async getMyStoreOrders() {
    const res = await fetch(`${API_BASE}/api/v1/merchants/my-store/orders`, {
      headers: getHeaders(),
    });
    if (!res.ok) throw new Error('Failed to fetch store orders');
    return res.json();
  },

  async applyStore(storeData) {
    const res = await fetch(`${API_BASE}/api/v1/merchants/apply`, {
      method: 'POST',
      headers: getHeaders(),
      body: JSON.stringify(storeData),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to connect store');
    }
    return res.json();
  },

  async syncStore() {
    const res = await fetch(`${API_BASE}/api/v1/merchants/my-store/sync`, {
      method: 'POST',
      headers: getHeaders(),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to sync catalog');
    }
    return res.json();
  },

  // Public Catalog & MCP Calls
  async getPublicCatalog(merchantId) {
    const url = merchantId
      ? `${API_BASE}/api/v1/merchants/catalog?merchant_id=${merchantId}`
      : `${API_BASE}/api/v1/merchants/catalog`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to load catalog');
    return res.json();
  },

  async callMcp(toolName, args) {
    const res = await fetch(`${API_BASE}/mcp/call`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: toolName, arguments: args }),
    });
    return res.json();
  },
};
