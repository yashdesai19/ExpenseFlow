/* ==========================================================================
   THE LEDGER — ASYNC REST API CLIENT (WITH JWT AUTH)
   ========================================================================== */
window.APP_API = {
  baseUrl: window.APP_CONFIG.API_BASE,
  TOKEN_KEY: "expenseflow_auth_token",
  USER_KEY: "expenseflow_auth_user",

  getToken() {
    return localStorage.getItem(this.TOKEN_KEY);
  },

  getUser() {
    try {
      const u = localStorage.getItem(this.USER_KEY);
      return u ? JSON.parse(u) : null;
    } catch {
      return null;
    }
  },

  isAuthenticated() {
    return !!this.getToken();
  },

  logout() {
    try {
      localStorage.removeItem(this.TOKEN_KEY);
      localStorage.removeItem(this.USER_KEY);
      sessionStorage.clear();
    } catch (e) {
      console.warn("[Auth] Error clearing storage:", e);
    }
    window.location.replace("auth.html");
  },

  async request(endpoint, options = {}) {
    try {
      const token = this.getToken();
      const authHeaders = token ? { "Authorization": `Bearer ${token}` } : {};

      const res = await fetch(`${this.baseUrl}${endpoint}`, {
        headers: {
          "Content-Type": "application/json",
          ...authHeaders,
          ...options.headers
        },
        ...options
      });

      if (res.status === 401 && !endpoint.includes("/auth/")) {
        console.warn("[API] Token expired or invalid, redirecting to login...");
        localStorage.removeItem(this.TOKEN_KEY);
        localStorage.removeItem(this.USER_KEY);
        // Do not force redirect if working in local demo mode, but notify
        return null;
      }

      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      return await res.json();
    } catch (err) {
      console.warn(`[API] ${endpoint} request error:`, err.message);
      return null;
    }
  },

  async getHealth() {
    return await this.request("/health");
  },

  async getMe() {
    return await this.request("/auth/me");
  },

  async login(email, password) {
    const res = await fetch(`${this.baseUrl}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();
    if (res.ok && data.access_token) {
      localStorage.setItem(this.TOKEN_KEY, data.access_token);
      if (data.user) localStorage.setItem(this.USER_KEY, JSON.stringify(data.user));
    }
    return { ok: res.ok, data };
  },

  async register(full_name, email, password) {
    const res = await fetch(`${this.baseUrl}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ full_name, email, password })
    });
    const data = await res.json();
    return { ok: res.ok, data };
  },

  async getExpenses(limit = 100) {
    return await this.request(`/expenses?limit=${limit}`);
  },

  async createExpense(payload) {
    return await this.request("/expenses", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  async updateExpense(id, payload) {
    return await this.request(`/expenses/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    });
  },

  async deleteExpense(id) {
    return await this.request(`/expenses/${id}`, {
      method: "DELETE"
    });
  },

  async getCategories() {
    return await this.request("/categories");
  },

  async createCategory(payload) {
    return await this.request("/categories", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  async deleteCategory(id) {
    return await this.request(`/categories/${id}`, {
      method: "DELETE"
    });
  },

  async getDashboardSummary() {
    return await this.request("/dashboard/summary");
  },

  async getBudgets() {
    return await this.request("/budgets");
  }
};
