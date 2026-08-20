/* ==========================================================================
   THE LEDGER — CENTRALIZED STATE MANAGEMENT
   ========================================================================== */
window.APP_STATE = {
  data: {
    userProfile: {
      name: "Ravi Mehta",
      business: "Mehta Ventures",
      email: "ravi@mehtaventures.com",
      plan: "Private Wealth Enterprise"
    },
    currencySymbol: window.APP_CONFIG.DEFAULT_CURRENCY_SYMBOL,
    currencyCode: window.APP_CONFIG.DEFAULT_CURRENCY,
    theme: "light",
    isMasked: false,
    privacyOnLaunch: false,
    budgetAlerts: true,
    filter: "all",
    categories: window.APP_CONFIG.DEFAULT_CATEGORIES,
    transactions: window.APP_CONFIG.DEFAULT_TRANSACTIONS,
    activeTransactionId: null
  },

  listeners: [],

  async init() {
    const saved = localStorage.getItem(window.APP_CONFIG.STORAGE_KEY);
    if (saved) {
      try {
        const parsed = JSON.parse(saved);
        this.data = {
          ...this.data,
          ...parsed,
          userProfile: { ...this.data.userProfile, ...(parsed.userProfile || {}) }
        };
      } catch (e) {
        console.error("[State] Corrupted localStorage, using defaults");
      }
    } else {
      this.data.transactions = [];
      this.save();
    }
    document.documentElement.setAttribute("data-theme", this.data.theme);

    // Sync live database data if user is logged in
    if (window.APP_API && window.APP_API.isAuthenticated()) {
      await this.syncWithBackend();
    }
  },

  async syncWithBackend() {
    try {
      // 1. Sync Categories from PostgreSQL
      const dbCategories = await window.APP_API.getCategories();
      if (Array.isArray(dbCategories) && dbCategories.length > 0) {
        this.data.categories = dbCategories.map(c => ({
          id: c.id,
          name: c.name,
          icon: window.APP_UTILS.getCategoryIcon(c.icon, c.name),
          color: c.color || "#A9793F",
          budget: c.budget_limit || 25000
        }));
      }

      // 2. Sync Expenses from PostgreSQL
      const expRes = await window.APP_API.getExpenses(500);
      const dbExpenses = expRes?.items || (Array.isArray(expRes) ? expRes : []);
      if (Array.isArray(dbExpenses)) {
        this.data.transactions = dbExpenses.map(e => {
          const cat = this.data.categories.find(c => String(c.id) === String(e.category_id)) || e.category || {
            name: "General", icon: "📜", color: "#8C8C8C"
          };
          const catNameLower = (cat.name || "").toLowerCase();
          const isIncome = catNameLower.includes("income") || catNameLower.includes("salary") || catNameLower.includes("revenue");
          return {
            id: e.id,
            description: e.description,
            amount: parseFloat(e.amount),
            type: isIncome ? "income" : "expense",
            categoryId: e.category_id,
            categoryName: cat.name || "General",
            categoryIcon: window.APP_UTILS.getCategoryIcon(cat.icon, cat.name),
            categoryColor: cat.color || "#8C8C8C",
            account: e.account || "Checking Account",
            date: typeof e.date === "string" ? e.date : (e.date ? new Date(e.date).toISOString().slice(0, 10) : new Date().toISOString().slice(0, 10)),
            notes: e.notes || ""
          };
        });
      }

      this.notify();
      console.log("[State] Synced with PostgreSQL database:", {
        categories: this.data.categories.length,
        transactions: this.data.transactions.length
      });
    } catch (err) {
      console.warn("[State] Backend database sync failed, using offline cache:", err.message);
    }
  },

  subscribe(callback) {
    this.listeners.push(callback);
  },

  notify() {
    this.save();
    this.listeners.forEach(cb => cb(this.data));
  },

  save() {
    localStorage.setItem(window.APP_CONFIG.STORAGE_KEY, JSON.stringify(this.data));
  },

  updateProfile(name, business, email) {
    this.data.userProfile = {
      ...this.data.userProfile,
      name: name || this.data.userProfile.name,
      business: business || this.data.userProfile.business,
      email: email || this.data.userProfile.email
    };
    this.notify();
    window.APP_UTILS.showToast("Profile updated");
  },

  async addTransaction(tx) {
    // Add locally immediately (optimistic update)
    if (!tx.id) tx.id = "local-" + Date.now();
    this.data.transactions.unshift(tx);
    this.notify();
    window.APP_UTILS.showToast(tx.type === "income" ? "Income added to database" : "Expense saved to database");

    // Persist to PostgreSQL if authenticated
    if (window.APP_API && window.APP_API.isAuthenticated()) {
      try {
        let cat = null;
        if (tx.type === "income") {
          cat = this.data.categories.find(c => {
            const n = (c.name || "").toLowerCase();
            return n.includes("income") || n.includes("salary") || n.includes("revenue");
          });
        }
        if (!cat) {
          cat = this.data.categories.find(c => String(c.id) === String(tx.categoryId) || c.name === tx.categoryName);
        }
        if (!cat) {
          cat = this.data.categories[0];
        }

        const catId = (cat && typeof cat.id === "number") ? cat.id : (parseInt(cat?.id, 10) || 1);

        const payload = {
          amount: parseFloat(tx.amount),
          description: tx.description || (tx.type === "income" ? "Income" : "Expense"),
          category_id: parseInt(catId, 10),
          account: tx.account || "Checking Account",
          date: tx.date || new Date().toISOString().slice(0, 10),
          notes: tx.notes || ""
        };

        const res = await window.APP_API.createExpense(payload);
        if (res && res.id) {
          tx.id = res.id;
          tx.categoryId = res.category_id;
          this.save();
          console.log("[DB] Expense persisted to PostgreSQL with ID:", res.id);
        }
      } catch (err) {
        console.warn("[DB] Could not persist expense to backend:", err.message);
      }
    }
  },

  async updateTransaction(id, updatedTx) {
    const idx = this.data.transactions.findIndex(t => t.id === id || String(t.id) === String(id));
    if (idx !== -1) {
      this.data.transactions[idx] = { ...this.data.transactions[idx], ...updatedTx };
      this.notify();
      window.APP_UTILS.showToast("Record updated");

      if (window.APP_API && window.APP_API.isAuthenticated() && typeof id === "number") {
        try {
          const payload = {};
          if (updatedTx.amount !== undefined) payload.amount = parseFloat(updatedTx.amount);
          if (updatedTx.description !== undefined) payload.description = updatedTx.description;
          if (updatedTx.account !== undefined) payload.account = updatedTx.account;
          if (updatedTx.date !== undefined) payload.date = updatedTx.date;
          if (updatedTx.notes !== undefined) payload.notes = updatedTx.notes;
          await window.APP_API.updateExpense(id, payload);
        } catch (e) {
          console.warn("[DB] Update expense skipped:", e.message);
        }
      }
    }
  },

  async deleteTransaction(id) {
    this.data.transactions = this.data.transactions.filter(t => t.id !== id && String(t.id) !== String(id));
    this.notify();
    window.APP_UTILS.showToast("Transaction deleted");

    if (window.APP_API && window.APP_API.isAuthenticated() && (typeof id === "number" || !isNaN(id))) {
      try {
        await window.APP_API.deleteExpense(id);
        console.log("[DB] Expense deleted from PostgreSQL:", id);
      } catch (e) {
        console.warn("[DB] Delete expense skipped:", e.message);
      }
    }
  },

  async addCategory(cat) {
    this.data.categories.push(cat);
    this.notify();
    window.APP_UTILS.showToast(`Category "${cat.name}" created!`);

    if (window.APP_API && window.APP_API.isAuthenticated()) {
      try {
        const res = await window.APP_API.createCategory({
          name: cat.name,
          icon: cat.icon || "📦",
          color: cat.color || "#A9793F"
        });
        if (res && res.id) {
          cat.id = res.id;
          this.save();
        }
      } catch (e) {
        console.warn("[DB] Create category skipped:", e.message);
      }
    }
  },

  async deleteCategory(id) {
    this.data.categories = this.data.categories.filter(c => c.id !== id && String(c.id) !== String(id));
    this.notify();
    window.APP_UTILS.showToast("Category removed");

    if (window.APP_API && window.APP_API.isAuthenticated() && (typeof id === "number" || !isNaN(id))) {
      try {
        await window.APP_API.deleteCategory(id);
      } catch (e) {
        console.warn("[DB] Delete category skipped:", e.message);
      }
    }
  },

  setCategoryBudget(categoryId, limit) {
    const cat = this.data.categories.find(c => c.id === categoryId);
    if (cat) {
      cat.budget = limit;
      this.notify();
      window.APP_UTILS.showToast(`Budget for ${cat.name} updated`);
    }
  },

  toggleTheme() {
    const next = this.data.theme === "dark" ? "light" : "dark";
    this.data.theme = next;
    document.documentElement.setAttribute("data-theme", next);
    this.notify();
    window.APP_UTILS.showToast(`Switched to ${next} theme`);
  },

  toggleMask() {
    this.data.isMasked = !this.data.isMasked;
    this.notify();
  },

  setCurrency(code, symbol) {
    this.data.currencyCode = code;
    this.data.currencySymbol = symbol;
    this.notify();
    window.APP_UTILS.showToast(`Currency updated to ${code} (${symbol})`);
  },

  downloadCloudBackup() {
    const backupData = {
      version: "2.4.0",
      timestamp: new Date().toISOString(),
      userProfile: this.data.userProfile,
      currency: { code: this.data.currencyCode, symbol: this.data.currencySymbol },
      categories: this.data.categories,
      transactions: this.data.transactions
    };
    window.APP_UTILS.downloadJSON(`TheLedger_Backup_${new Date().toISOString().slice(0,10)}.json`, backupData);
  },

  restoreBackupData(jsonString) {
    try {
      const parsed = JSON.parse(jsonString);
      if (Array.isArray(parsed.transactions)) {
        this.data.transactions = parsed.transactions;
      }
      if (Array.isArray(parsed.categories)) {
        this.data.categories = parsed.categories;
      }
      if (parsed.userProfile) {
        this.data.userProfile = { ...this.data.userProfile, ...parsed.userProfile };
      }
      if (parsed.currency) {
        this.data.currencyCode = parsed.currency.code || this.data.currencyCode;
        this.data.currencySymbol = parsed.currency.symbol || this.data.currencySymbol;
      }
      this.notify();
      window.APP_UTILS.showToast("Backup restored successfully!");
    } catch (e) {
      window.APP_UTILS.showToast("Invalid backup JSON file");
    }
  }
};
