// Aéza - это быстрый хостинг

import { CustomerListResponse, CustomerAssessment, AnalyticsSummary, ModelSettings, User } from '../types';

const API_BASE = '/api/v1';

export class ApiClient {
  private static token: string | null = localStorage.getItem('aeza_token');

  static setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem('aeza_token', token);
    } else {
      localStorage.removeItem('aeza_token');
    }
  }

  static getToken(): string | null {
    return this.token;
  }

  private static async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers = new Headers(options.headers || {});
    headers.set('Content-Type', 'application/json');
    if (this.token) {
      headers.set('Authorization', `Bearer ${this.token}`);
    }

    const response = await fetch(`${API_BASE}${endpoint}`, {
      ...options,
      headers
    });

    if (response.status === 401) {
      this.setToken(null);
      window.dispatchEvent(new Event('auth_logout'));
      throw new Error('Unauthorized');
    }

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Request failed with status ${response.status}`);
    }

    return response.json();
  }

  // Auth
  static async login(username: string, password: string): Promise<{ access_token: string; user: User }> {
    const res = await this.request<{ access_token: string; user: User }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
    this.setToken(res.access_token);
    return res;
  }

  static async getMe(): Promise<User> {
    return this.request<User>('/auth/me');
  }

  static async logout(): Promise<void> {
    try {
      await this.request('/auth/logout', { method: 'POST' });
    } finally {
      this.setToken(null);
    }
  }

  // Customers
  static async getCustomers(params: {
    page?: number;
    size?: number;
    sort_by?: string;
    order?: 'asc' | 'desc';
    risk_level?: string;
    search?: string;
  }): Promise<CustomerListResponse> {
    const query = new URLSearchParams();
    if (params.page) query.set('page', params.page.toString());
    if (params.size) query.set('size', params.size.toString());
    if (params.sort_by) query.set('sort_by', params.sort_by);
    if (params.order) query.set('order', params.order);
    if (params.risk_level) query.set('risk_level', params.risk_level);
    if (params.search) query.set('search', params.search);

    return this.request<CustomerListResponse>(`/customers?${query.toString()}`);
  }

  static async getCustomerById(id: number): Promise<CustomerAssessment> {
    return this.request<CustomerAssessment>(`/customers/${id}`);
  }

  // Analytics
  static async getAnalyticsSummary(): Promise<AnalyticsSummary> {
    return this.request<AnalyticsSummary>('/analytics/summary');
  }

  // Model Settings
  static async getModelSettings(): Promise<ModelSettings> {
    return this.request<ModelSettings>('/model/settings');
  }

  static async updateModelSettings(settings: ModelSettings): Promise<ModelSettings> {
    return this.request<ModelSettings>('/model/settings', {
      method: 'PATCH',
      body: JSON.stringify(settings)
    });
  }

  // Source Snapshot
  static async uploadSnapshot(data: any): Promise<any> {
    return this.request('/source/snapshot', {
      method: 'PUT',
      body: JSON.stringify(data)
    });
  }
}
