/* ==========================================================================
   THE LEDGER — DESKTOP WORKSPACE CONTROLLER
   ========================================================================== */
window.APP_DESKTOP = {
  activeView: "dashboard",

  init() {
    this.bindEvents();
    this.render();
    window.APP_STATE.subscribe(() => this.render());
  },

  bindEvents() {
    // Search input filtering
    const searchInput = document.getElementById("dSearchInput");
    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        const q = e.target.value.toLowerCase().trim();
        const state = window.APP_STATE.data;
        const filtered = state.transactions.filter(t => 
          t.description.toLowerCase().includes(q) || 
          t.account.toLowerCase().includes(q) ||
          (t.notes && t.notes.toLowerCase().includes(q))
        );
        this.renderTableRows(filtered);
      });
    }

    // Global Command+K / Ctrl+K listener
    window.addEventListener("keydown", (e) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        this.openAddModal();
      }
    });
  },

  handleAuthAction() {
    if (window.APP_API && window.APP_API.isAuthenticated()) {
      window.APP_API.logout();
    } else {
      window.location.replace("auth.html");
    }
  },

  switchView(viewName, btn) {
    this.activeView = viewName;
    ["dashboard", "ledger", "budgets", "analytics", "settings"].forEach(v => {
      const sec = document.getElementById(`dViewSec-${v}`);
      if (sec) sec.style.display = v === viewName ? (v === "dashboard" ? "flex" : "block") : "none";
      const navBtn = document.getElementById(`dNav-${v}`);
      if (navBtn) navBtn.classList.toggle("active", v === viewName);
    });
    if (btn) btn.classList.add("active");
    const canvas = document.querySelector(".desktop-main-canvas");
    if (canvas) canvas.scrollTo({ top: 0, behavior: "smooth" });
  },

  render() {
    const state = window.APP_STATE.data;
    const sym = state.currencySymbol;
    const exp = state.transactions.filter(t => t.type === "expense");
    const inc = state.transactions.filter(t => t.type === "income");
    const totalExp = exp.reduce((s, t) => s + t.amount, 0);
    const totalInc = inc.reduce((s, t) => s + t.amount, 0);
    const balance = totalInc - totalExp;
    const savingsRatio = totalInc ? Math.round(((totalInc - totalExp) / totalInc) * 100) : 0;

    // KPI Deck
    const balEl = document.getElementById("dTotalBalance");
    if (balEl) balEl.textContent = state.isMasked ? "•••••••" : window.APP_UTILS.formatMoney(balance, sym);
    const inEl = document.getElementById("dTotalIncome");
    if (inEl) inEl.textContent = state.isMasked ? "•••••" : "+" + window.APP_UTILS.formatMoney(totalInc, sym);
    const outEl = document.getElementById("dTotalSpent");
    if (outEl) outEl.textContent = state.isMasked ? "•••••" : "-" + window.APP_UTILS.formatMoney(totalExp, sym);
    const savEl = document.getElementById("dSavingsRate");
    if (savEl) savEl.textContent = `${savingsRatio}%`;

    // Dynamic 6-Month Cashflow Trajectory Chart (Desktop)
    const dLine = document.getElementById("dDashboardLinePath");
    const dArea = document.getElementById("dDashboardAreaPath");
    if (dLine && dArea) {
      const paths = window.APP_UTILS.generateSparklinePaths(state.transactions, 600, 180, 20);
      dLine.setAttribute("d", paths.linePath);
      dArea.setAttribute("d", paths.areaPath);
    }

    // Category Ceilings (Dashboard Card)
    const meterEl = document.getElementById("dCategoryBudgetList");
    if (meterEl) {
      meterEl.innerHTML = state.categories.slice(0, 5).map(c => {
        const spent = exp.filter(t => t.categoryId === c.id).reduce((s, t) => s + t.amount, 0);
        const limit = c.budget || 25000;
        const pct = Math.min(Math.round((spent / limit) * 100), 100);
        return `
          <div>
            <div style="display:flex; justify-content:space-between; font-size:12.5px; margin-bottom:4px;">
              <span>${c.icon} ${c.name}</span>
              <span class="money" style="color:var(--text-sec);">${window.APP_UTILS.formatMoney(spent, sym)} / ${window.APP_UTILS.formatMoney(limit, sym)} (${pct}%)</span>
            </div>
            <div style="height:6px; background:var(--bg-elevated); border-radius:99px; overflow:hidden;">
              <div style="width:${pct}%; height:100%; background:${pct >= 100 ? "var(--danger)" : "var(--accent)"};"></div>
            </div>
          </div>
        `;
      }).join("");
    }

    // Full Budgets & Category Management Grid
    const fullBudgetsEl = document.getElementById("dFullBudgetsList");
    if (fullBudgetsEl) {
      fullBudgetsEl.innerHTML = state.categories.filter(c => c.name !== "Income").map(c => {
        const spent = exp.filter(t => t.categoryId === c.id).reduce((s, t) => s + t.amount, 0);
        const limit = c.budget || 25000;
        const pct = Math.min(Math.round((spent / limit) * 100), 100);
        return `
          <div style="background:var(--bg-elevated); padding:18px; border-radius:16px; border:1px solid var(--border); box-shadow:var(--shadow-sm);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
              <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size:20px;">${c.icon}</span>
                <strong style="font-size:15px;">${c.name}</strong>
              </div>
              <div style="display:flex; align-items:center; gap:8px;">
                <span class="money" style="font-weight:700; color:${pct >= 100 ? "var(--danger)" : "var(--accent)"};">${pct}%</span>
                <button class="btn-brass-icon" style="width:28px; height:28px; font-size:12px; color:var(--danger);" onclick="window.APP_DESKTOP.deleteCategoryConfirm('${c.id}')" title="Delete Category">🗑️</button>
              </div>
            </div>
            <div style="height:8px; background:var(--card); border-radius:99px; overflow:hidden; margin-bottom:8px;">
              <div style="width:${pct}%; height:100%; background:${pct >= 100 ? "var(--danger)" : "var(--accent)"};"></div>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:12px; color:var(--text-muted);">
              <span>${window.APP_UTILS.formatMoney(spent, sym)} spent</span>
              <span>Ceiling: ${window.APP_UTILS.formatMoney(limit, sym)}</span>
            </div>
          </div>
        `;
      }).join("");
    }

    // Analytics Distribution List
    const distEl = document.getElementById("dAnalyticsDistList");
    if (distEl) {
      const totalSpend = totalExp || 1;
      distEl.innerHTML = state.categories.filter(c => c.name !== "Income").map(c => {
        const spent = exp.filter(t => t.categoryId === c.id).reduce((s, t) => s + t.amount, 0);
        if (!spent) return "";
        const pct = Math.round((spent / totalSpend) * 100);
        return `
          <div style="display:flex; justify-content:space-between; align-items:center; font-size:13px;">
            <span>${c.icon} ${c.name}</span>
            <div><span class="money">${window.APP_UTILS.formatMoney(spent, sym)}</span> <strong style="color:var(--accent); margin-left:8px;">${pct}%</strong></div>
          </div>
        `;
      }).join("");
    }

    // Tables
    this.renderTableRows(state.transactions);
    this.renderFullLedgerTable(state.transactions);

    // Populate Category Dropdown
    const catSelect = document.getElementById("dInCat");
    if (catSelect) {
      catSelect.innerHTML = state.categories.map(c => `<option value="${c.id}">${c.name}</option>`).join("");
    }

    // Dynamic Profile Inputs Binding
    if (state.userProfile) {
      const nameIn = document.getElementById("dProfileNameInput");
      if (nameIn && !nameIn.matches(":focus")) nameIn.value = state.userProfile.name;
      const bizIn = document.getElementById("dProfileBizInput");
      if (bizIn && !bizIn.matches(":focus")) bizIn.value = state.userProfile.business;
      const emailIn = document.getElementById("dProfileEmailInput");
      if (emailIn && !emailIn.matches(":focus")) emailIn.value = state.userProfile.email;
    }

    const curLabel = document.getElementById("dActiveCurLabel");
    if (curLabel) curLabel.textContent = `Active: ${state.currencyCode} (${state.currencySymbol})`;

    const curSelect = document.getElementById("dCurrencySelect");
    if (curSelect) curSelect.value = `${state.currencyCode}|${state.currencySymbol}`;

    const authBtnText = document.getElementById("dAuthBtnText");
    if (authBtnText) {
      if (window.APP_API && window.APP_API.isAuthenticated()) {
        const u = window.APP_API.getUser();
        const shortName = u && u.full_name ? u.full_name.split(" ")[0] : "Account";
        authBtnText.textContent = `👋 ${shortName} (Sign Out)`;
      } else {
        authBtnText.textContent = "🔑 Sign In";
      }
    }
  },

  saveProfileChanges() {
    const name = (document.getElementById("dProfileNameInput").value || "").trim();
    const biz = (document.getElementById("dProfileBizInput").value || "").trim();
    const email = (document.getElementById("dProfileEmailInput").value || "").trim();

    if (!name) {
      window.APP_UTILS.showToast("Please enter your name");
      return;
    }

    window.APP_STATE.updateProfile(name, biz, email);
    this.render();
  },

  changeCurrency(val) {
    if (!val) return;
    const [code, sym] = val.split("|");
    window.APP_STATE.setCurrency(code, sym);
  },

  renderTableRows(list) {
    const tableBody = document.getElementById("dTransactionTableBody");
    if (!tableBody) return;
    const state = window.APP_STATE.data;
    const sym = state.currencySymbol;

    tableBody.innerHTML = list.slice(0, 8).map(t => {
      const cat = state.categories.find(c => String(c.id) === String(t.categoryId)) || { name: t.categoryName || "General", icon: t.categoryIcon || "📜" };
      const isInc = t.type === "income";
      return `
        <tr>
          <td class="money" style="color:var(--text-muted);">${t.date}</td>
          <td><strong>${t.description}</strong></td>
          <td><span>${cat.icon} ${cat.name}</span></td>
          <td><span style="background:var(--bg-elevated); padding:3px 8px; border-radius:6px; font-size:12px;">${t.account}</span></td>
          <td style="text-align:right;" class="money">
            <strong style="color:${isInc ? "var(--success)" : "var(--text)"};">${isInc ? "+" : "-"}${window.APP_UTILS.formatMoney(t.amount, sym)}</strong>
          </td>
        </tr>
      `;
    }).join("");
  },

  renderFullLedgerTable(list) {
    const tableBody = document.getElementById("dFullLedgerTableBody");
    if (!tableBody) return;
    const state = window.APP_STATE.data;
    const sym = state.currencySymbol;

    if (!list || list.length === 0) {
      tableBody.innerHTML = `
        <tr>
          <td colspan="5" style="text-align:center; padding:32px; color:var(--text-muted);">
            No transactions found for this period.
          </td>
        </tr>
      `;
      return;
    }

    tableBody.innerHTML = list.map(t => {
      const cat = state.categories.find(c => String(c.id) === String(t.categoryId)) || { name: t.categoryName || "General", icon: t.categoryIcon || "📜" };
      const isInc = t.type === "income";
      return `
        <tr>
          <td class="money" style="color:var(--text-muted);">${t.date}</td>
          <td><strong>${t.description}</strong></td>
          <td><span>${cat.icon} ${cat.name}</span></td>
          <td><span style="background:var(--bg-elevated); padding:3px 8px; border-radius:6px; font-size:12px;">${t.account}</span></td>
          <td style="text-align:right;" class="money">
            <strong style="color:${isInc ? "var(--success)" : "var(--text)"};">${isInc ? "+" : "-"}${window.APP_UTILS.formatMoney(t.amount, sym)}</strong>
          </td>
        </tr>
      `;
    }).join("");
  },

  filterLedger(type, btn) {
    document.querySelectorAll(".desktop-filter-strip .d-pill").forEach(p => p.classList.remove("active"));
    if (btn) btn.classList.add("active");

    const state = window.APP_STATE.data;
    const filtered = state.transactions.filter(t => {
      if (type === "all") return true;
      if (type === "expense") return t.type === "expense";
      if (type === "income") return t.type === "income";
      if (type === "Business" || type === "Personal") return t.account === type;
      return true;
    });
    this.renderFullLedgerTable(filtered);
  },

  openAddModal() {
    const modal = document.getElementById("dModalOverlay");
    if (modal) {
      document.getElementById("dInAmt").value = "";
      document.getElementById("dInDesc").value = "";
      document.getElementById("dInDate").value = new Date().toISOString().slice(0, 10);
      modal.classList.add("open");
    }
  },

  closeModal() {
    const modal = document.getElementById("dModalOverlay");
    if (modal) modal.classList.remove("open");
  },

  saveTransaction() {
    const amtInput = document.getElementById("dInAmt");
    const descInput = document.getElementById("dInDesc");
    const acctInput = document.getElementById("dInAcct");
    const catInput = document.getElementById("dInCat");
    const dateInput = document.getElementById("dInDate");

    const amt = parseFloat(amtInput ? amtInput.value : "0");
    const desc = descInput ? descInput.value.trim() : "";
    const acct = acctInput ? acctInput.value : "Business";
    const cat = catInput ? catInput.value : "";
    const date = (dateInput && dateInput.value) ? dateInput.value : new Date().toISOString().slice(0, 10);

    // Resolve category name from select for proper backend sync
    const state = window.APP_STATE.data;
    const catSelect = catInput;
    let catName = cat;
    if (catSelect) {
      const selectedOption = catSelect.options ? catSelect.options[catSelect.selectedIndex] : null;
      if (selectedOption) catName = selectedOption.textContent || cat;
    }

    if (!amt || isNaN(amt) || amt <= 0) {
      window.APP_UTILS.showToast("Please enter a valid positive amount");
      if (amtInput) amtInput.focus();
      return;
    }
    if (!desc) {
      window.APP_UTILS.showToast("Please enter a description / merchant");
      if (descInput) descInput.focus();
      return;
    }

    const newTx = {
      id: "tx-" + Date.now(),
      date,
      description: desc,
      categoryId: cat,
      categoryName: catName,
      account: acct,
      type: "expense",
      amount: amt,
      notes: ""
    };

    window.APP_STATE.addTransaction(newTx);
    if (amtInput) amtInput.value = "";
    if (descInput) descInput.value = "";
    this.closeModal();
    this.render();
  },

  openNewCatModal() {
    const nameIn = document.getElementById("dNewCatName");
    if (nameIn) nameIn.value = "";
    const iconIn = document.getElementById("dNewCatIcon");
    if (iconIn) iconIn.value = "📢";
    const budgetIn = document.getElementById("dNewCatBudget");
    if (budgetIn) budgetIn.value = "25000";

    const modal = document.getElementById("dNewCatModalOverlay");
    if (modal) modal.classList.add("open");
  },

  closeNewCatModal() {
    const modal = document.getElementById("dNewCatModalOverlay");
    if (modal) modal.classList.remove("open");
  },

  selectNewCatEmoji(emoji) {
    const iconIn = document.getElementById("dNewCatIcon");
    if (iconIn) iconIn.value = emoji;
  },

  saveNewCategory() {
    const name = (document.getElementById("dNewCatName").value || "").trim();
    const icon = (document.getElementById("dNewCatIcon").value || "📁").trim();
    const budget = parseFloat(document.getElementById("dNewCatBudget").value || "25000");

    if (!name) {
      window.APP_UTILS.showToast("Please enter a category name");
      return;
    }

    const newCat = {
      id: "cat-" + Date.now(),
      name,
      icon,
      color: "#A9793F",
      budget: budget > 0 ? budget : 25000
    };

    window.APP_STATE.addCategory(newCat);
    this.closeNewCatModal();
    this.render();

    const catSelect = document.getElementById("dInCat");
    if (catSelect) catSelect.value = newCat.id;
  },

  deleteCategoryConfirm(categoryId) {
    const state = window.APP_STATE.data;
    const cat = state.categories.find(c => c.id === categoryId);
    if (!cat) return;
    if (confirm(`Are you sure you want to delete category "${cat.name}"?`)) {
      window.APP_STATE.deleteCategory(categoryId);
      this.render();
    }
  },

  exportCSV() {
    const state = window.APP_STATE.data;
    const rows = [["Date", "Description", "Category", "Account", "Type", "Amount"]].concat(
      state.transactions.map(t => [t.date, t.description, t.categoryId, t.account, t.type, t.amount])
    );
    window.APP_UTILS.downloadCSV(`ExpenseFlow_Desktop_${new Date().toISOString().slice(0,10)}.csv`, rows);
  }
};
