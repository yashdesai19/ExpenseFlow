/* ==========================================================================
   THE LEDGER — MOBILE CONTROLLER
   ========================================================================== */
window.APP_MOBILE = {
  activeTab: "home",
  activeTxType: "expense",
  selectedCatId: "cat-software",
  selectedMonthKey: window.APP_UTILS.getMonthKey(null),
  typeFilter: "all",
  searchQuery: "",
  editingTxId: null,

  init() {
    this.bindEvents();
    this.render();
    window.APP_STATE.subscribe(() => this.render());
  },

  bindEvents() {
    const searchInput = document.getElementById("lSearchQuery");
    if (searchInput) {
      searchInput.addEventListener("input", (e) => {
        this.searchQuery = e.target.value.toLowerCase().trim();
        this.render();
      });
    }
  },

  prevMonth() {
    if (this.selectedMonthKey === "all") {
      this.selectedMonthKey = window.APP_UTILS.getMonthKey(null);
    }
    this.selectedMonthKey = window.APP_UTILS.shiftMonth(this.selectedMonthKey, -1);
    this.render();
  },

  nextMonth() {
    if (this.selectedMonthKey === "all") {
      this.selectedMonthKey = window.APP_UTILS.getMonthKey(null);
    }
    this.selectedMonthKey = window.APP_UTILS.shiftMonth(this.selectedMonthKey, 1);
    this.render();
  },

  selectMonth(monthKey) {
    this.selectedMonthKey = monthKey;
    this.render();
  },

  toggleMonthDropdown() {
    if (this.selectedMonthKey === "all") {
      this.selectedMonthKey = window.APP_UTILS.getMonthKey(null);
    } else {
      this.selectedMonthKey = "all";
    }
    this.render();
  },

  handleFilterChange() {
    const typeSelect = document.getElementById("lTypeFilter");
    if (typeSelect) {
      this.typeFilter = typeSelect.value || "all";
    }
    this.render();
  },

  handleAuthAction() {
    if (window.APP_API && window.APP_API.isAuthenticated()) {
      window.APP_API.logout();
    } else {
      window.location.replace("auth.html");
    }
  },

  showTab(tabKey) {
    this.activeTab = tabKey;
    ["home", "transactions", "insights", "profile"].forEach(k => {
      const view = document.getElementById(`lView-${k}`);
      if (view) view.style.display = k === tabKey ? "flex" : "none";
      const btn = document.getElementById(`lTabBtn-${k}`);
      if (btn) btn.classList.toggle("active", k === tabKey);
    });

    const titles = { home: "Ledger", transactions: "Transactions", insights: "Insights", profile: "Profile" };
    const titleEl = document.getElementById("lHeaderTitle");
    if (titleEl) titleEl.textContent = titles[tabKey] || "Ledger";

    const body = document.getElementById("lScrollBody");
    if (body) body.scrollTo({ top: 0, behavior: "smooth" });
  },

  render() {
    const state = window.APP_STATE.data;
    const sym = state.currencySymbol;
    const exp = state.transactions.filter(t => t.type === "expense");
    const inc = state.transactions.filter(t => t.type === "income");
    const totalExp = exp.reduce((s, t) => s + t.amount, 0);
    const totalInc = inc.reduce((s, t) => s + t.amount, 0);
    const bal = totalInc - totalExp;

    // Hero Balances
    const heroBal = document.getElementById("lHeroBal");
    if (heroBal) heroBal.textContent = state.isMasked ? "•••••••" : window.APP_UTILS.formatMoney(bal, sym);
    const heroIn = document.getElementById("lHeroIncome");
    if (heroIn) heroIn.textContent = state.isMasked ? "•••••" : "+" + window.APP_UTILS.formatMoney(totalInc, sym);
    const heroOut = document.getElementById("lHeroSpent");
    if (heroOut) heroOut.textContent = state.isMasked ? "•••••" : "-" + window.APP_UTILS.formatMoney(totalExp, sym);

    // Top Category Pills
    const pillsContainer = document.getElementById("lTopCategoryPills");
    if (pillsContainer) {
      pillsContainer.innerHTML = state.categories.filter(c => c.name !== "Income").slice(0, 6).map(c => {
        const total = exp.filter(t => t.categoryId === c.id).reduce((s, t) => s + t.amount, 0);
        return `
          <div class="cat-pill-item" onclick="window.APP_MOBILE.showTab('insights')">
            <div class="cat-pill-icon">${c.icon}</div>
            <div style="font-size:11px; color:var(--text-muted); font-weight:600; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${c.name}</div>
            <div class="money" style="font-size:13px; font-weight:600;">${window.APP_UTILS.formatMoney(total, sym)}</div>
          </div>
        `;
      }).join("");
    }

    // AI Insights Box
    const insightsBox = document.getElementById("lInsightsText");
    if (insightsBox) {
      if (state.transactions.length === 0) {
        insightsBox.innerHTML = "• Welcome to ExpenseFlow Pro. Tap the <strong>+</strong> button below to record your first transaction.";
      } else {
        const topCat = state.categories.filter(c => c.name !== "Income").map(c => ({
          ...c,
          spent: exp.filter(t => t.categoryId === c.id).reduce((s, t) => s + t.amount, 0)
        })).sort((a, b) => b.spent - a.spent)[0];

        const netSavings = totalInc - totalExp;
        insightsBox.innerHTML = `
          • ${topCat && topCat.spent > 0 ? `<strong>${topCat.name}</strong> is your highest category at ${window.APP_UTILS.formatMoney(topCat.spent, sym)}.` : "All categories within budget."}<br>
          • Net liquid cashflow of <strong>${window.APP_UTILS.formatMoney(netSavings, sym)}</strong> recorded for this period.
        `;
      }
    }

    // Dynamic Hero Sparkline
    const heroSparkline = document.getElementById("lHeroSparkline");
    if (heroSparkline) {
      const paths = window.APP_UTILS.generateSparklinePaths(state.transactions, 260, 36, 4);
      heroSparkline.setAttribute("d", paths.linePath);
    }

    // Dynamic 6-Month Cashflow Trajectory Chart
    const linePathEl = document.getElementById("lInsightsLinePath");
    const areaPathEl = document.getElementById("lInsightsAreaPath");
    const statusLabel = document.getElementById("lChartStatusLabel");
    if (linePathEl && areaPathEl) {
      const paths = window.APP_UTILS.generateSparklinePaths(state.transactions, 360, 120, 12);
      linePathEl.setAttribute("d", paths.linePath);
      areaPathEl.setAttribute("d", paths.areaPath);
      if (statusLabel) {
        statusLabel.textContent = paths.isZero ? "Baseline Flat" : "Live Trajectory";
      }
    }

    // Recent Activity Feed (Latest 4)
    this.renderRecentActivity(state.transactions.slice(0, 4));

    // Month-Wise History & Filtered Transactions Feed
    const distinctMonths = window.APP_UTILS.getDistinctMonths(state.transactions);
    
    // Update Month Navigation Title
    const monthTitleEl = document.getElementById("lTxMonthTitle");
    if (monthTitleEl) {
      monthTitleEl.textContent = window.APP_UTILS.formatMonthName(this.selectedMonthKey);
    }
    const monthSubEl = document.getElementById("lTxMonthSubtitle");
    if (monthSubEl) {
      monthSubEl.textContent = this.selectedMonthKey === "all" ? "Showing All-Time History ▾" : "Tap to toggle all months ▾";
    }

    // Filter transactions by Month, Type, and Search Query
    let filteredTxs = [...state.transactions];
    if (this.selectedMonthKey && this.selectedMonthKey !== "all") {
      filteredTxs = filteredTxs.filter(t => window.APP_UTILS.getMonthKey(t.date) === this.selectedMonthKey);
    }
    if (this.typeFilter && this.typeFilter !== "all") {
      filteredTxs = filteredTxs.filter(t => t.type === this.typeFilter);
    }
    if (this.searchQuery) {
      const q = this.searchQuery;
      filteredTxs = filteredTxs.filter(t =>
        (t.description || "").toLowerCase().includes(q) ||
        (t.account || "").toLowerCase().includes(q) ||
        (t.categoryName || "").toLowerCase().includes(q) ||
        (t.notes || "").toLowerCase().includes(q)
      );
    }

    // Calculate Month Financial Metrics
    const mIn = filteredTxs.filter(t => t.type === "income").reduce((s, t) => s + t.amount, 0);
    const mOut = filteredTxs.filter(t => t.type === "expense").reduce((s, t) => s + t.amount, 0);
    const mNet = mIn - mOut;

    const mInEl = document.getElementById("lTxMonthInflow");
    if (mInEl) mInEl.textContent = "+" + window.APP_UTILS.formatMoney(mIn, sym);
    const mOutEl = document.getElementById("lTxMonthOutflow");
    if (mOutEl) mOutEl.textContent = "-" + window.APP_UTILS.formatMoney(mOut, sym);
    const mNetEl = document.getElementById("lTxMonthNet");
    if (mNetEl) {
      mNetEl.textContent = (mNet >= 0 ? "+" : "-") + window.APP_UTILS.formatMoney(Math.abs(mNet), sym);
      mNetEl.style.color = mNet >= 0 ? "var(--success)" : "var(--danger)";
    }

    // Month Quick-Filter Pills
    const monthPillsEl = document.getElementById("lMonthPillsRow");
    if (monthPillsEl) {
      monthPillsEl.innerHTML = `
        <button class="cat-picker-btn ${this.selectedMonthKey === "all" ? "active" : ""}" style="padding:6px 14px; height:auto; min-width:auto; border-radius:99px; border:1px solid var(--border);" onclick="window.APP_MOBILE.selectMonth('all')">
          <span style="font-size:11.5px; font-weight:700;">🌐 All Time (${state.transactions.length})</span>
        </button>
      ` + distinctMonths.map(m => `
        <button class="cat-picker-btn ${this.selectedMonthKey === m.key ? "active" : ""}" style="padding:6px 14px; height:auto; min-width:auto; border-radius:99px; border:1px solid var(--border);" onclick="window.APP_MOBILE.selectMonth('${m.key}')">
          <span style="font-size:11.5px; font-weight:700;">📅 ${m.label} (${m.count})</span>
        </button>
      `).join("");
    }

    // Render Grouped Feed
    this.renderGroupedTransactions(filteredTxs);

    // Insights Metrics
    const inVal = document.getElementById("lInsightIncomeVal");
    if (inVal) inVal.textContent = window.APP_UTILS.formatMoney(totalInc, sym);
    const outVal = document.getElementById("lInsightExpenseVal");
    if (outVal) outVal.textContent = window.APP_UTILS.formatMoney(totalExp, sym);

    // Category Share List
    const shareList = document.getElementById("lCategoryShareList");
    if (shareList) {
      const activeCatSpend = state.categories.filter(c => c.name !== "Income" && exp.some(t => t.categoryId === c.id));
      if (activeCatSpend.length === 0) {
        shareList.innerHTML = `
          <div style="text-align:center; padding:16px; color:var(--text-muted); font-size:12px;">
            Category share will appear as you record expenses.
          </div>
        `;
      } else {
        const totalSpendAll = totalExp || 1;
        shareList.innerHTML = activeCatSpend.map(c => {
          const total = exp.filter(t => t.categoryId === c.id).reduce((s, t) => s + t.amount, 0);
          const pct = Math.round((total / totalSpendAll) * 100);
          return `
            <div style="display:flex; justify-content:space-between; align-items:center; font-size:12.5px;">
              <div style="display:flex; align-items:center; gap:8px;">
                <span>${c.icon}</span>
                <span>${c.name}</span>
              </div>
              <div style="display:flex; gap:10px; align-items:center;">
                <span class="money" style="color:var(--text-sec);">${window.APP_UTILS.formatMoney(total, sym)}</span>
                <span class="money" style="font-weight:700; color:var(--accent);">${pct}%</span>
              </div>
            </div>
          `;
        }).join("");
      }
    }

    // Budgets & Category Management Container
    const budgetsContainer = document.getElementById("lBudgetsContainer");
    if (budgetsContainer) {
      budgetsContainer.innerHTML = state.categories.filter(c => c.name !== "Income").map(c => {
        const spent = exp.filter(t => t.categoryId === c.id).reduce((s, t) => s + t.amount, 0);
        const limit = c.budget || 25000;
        const pct = Math.min(Math.round((spent / limit) * 100), 100);
        const tone = pct >= 100 ? "var(--danger)" : pct >= 80 ? "var(--amber)" : "var(--accent)";
        return `
          <div class="l-card">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
              <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size:18px;">${c.icon}</span>
                <div>
                  <strong style="font-size:14px; display:block;">${c.name}</strong>
                  <span class="money" style="font-size:12px; color:var(--text-sec);">${window.APP_UTILS.formatMoney(spent, sym)} / ${window.APP_UTILS.formatMoney(limit, sym)}</span>
                </div>
              </div>
              <div style="display:flex; gap:6px;">
                <button class="btn-brass-icon" style="width:32px; height:32px; font-size:13px;" onclick="window.APP_MOBILE.openEditBudgetSheet('${c.id}', ${limit})" title="Edit Ceiling Limit">✏️</button>
                <button class="btn-brass-icon" style="width:32px; height:32px; font-size:13px; color:var(--danger);" onclick="window.APP_MOBILE.deleteCategoryConfirm('${c.id}')" title="Delete Category">🗑️</button>
              </div>
            </div>
            <div style="height:6px; background:var(--bg-elevated); border-radius:99px; overflow:hidden;">
              <div style="width:${pct}%; height:100%; background:${tone};"></div>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:11px; color:var(--text-muted); margin-top:4px;">
              <span>${pct}% of monthly ceiling</span>
              <span class="money">${window.APP_UTILS.formatMoney(Math.max(limit - spent, 0), sym)} remaining</span>
            </div>
          </div>
        `;
      }).join("");
    }

    // Category Grid in Add Sheet
    this.populateAddSheetCategories();

    // Profile Screen Info Bindings
    const pName = document.getElementById("lProfileName");
    if (pName && state.userProfile) pName.textContent = state.userProfile.name;
    const pBiz = document.getElementById("lProfileBusiness");
    if (pBiz && state.userProfile) pBiz.textContent = state.userProfile.business;
    const pEmail = document.getElementById("lProfileEmail");
    if (pEmail && state.userProfile) pEmail.textContent = state.userProfile.email;
    const pAvatar = document.getElementById("lProfileAvatar");
    if (pAvatar && state.userProfile) {
      const parts = (state.userProfile.name || "RM").split(" ");
      pAvatar.textContent = parts.length > 1 ? (parts[0][0] + parts[1][0]).toUpperCase() : parts[0].slice(0, 2).toUpperCase();
    }
    const lTopAvatar = document.getElementById("lTopHeaderAvatar");
    if (lTopAvatar && state.userProfile) {
      const parts = (state.userProfile.name || "RM").split(" ");
      lTopAvatar.textContent = parts.length > 1 ? (parts[0][0] + parts[1][0]).toUpperCase() : parts[0].slice(0, 2).toUpperCase();
    }

    const curText = document.getElementById("lActiveCurrencyText");
    if (curText) curText.textContent = `Active: ${state.currencyCode} (${state.currencySymbol})`;

    const curSelect = document.getElementById("lCurrencySelector");
    if (curSelect) curSelect.value = `${state.currencyCode}|${state.currencySymbol}`;

    const privToggle = document.getElementById("lPrivacyToggle");
    if (privToggle) privToggle.checked = state.isMasked;

    const mAuthTitle = document.getElementById("mAuthStatusTitle");
    const mAuthSub = document.getElementById("mAuthStatusSub");
    const mAuthBtn = document.getElementById("mAuthActionBtn");
    if (mAuthTitle && mAuthBtn) {
      if (window.APP_API && window.APP_API.isAuthenticated()) {
        const u = window.APP_API.getUser();
        mAuthTitle.textContent = u && u.full_name ? u.full_name : "Authenticated User";
        if (mAuthSub) mAuthSub.textContent = u && u.email ? u.email : "JWT Session Active";
        mAuthBtn.textContent = "Sign Out";
      } else {
        mAuthTitle.textContent = "Guest / Local Mode";
        if (mAuthSub) mAuthSub.textContent = "Not signed in to server";
        mAuthBtn.textContent = "Sign In / Register";
      }
    }
  },

  renderRecentActivity(list) {
    const container = document.getElementById("lRecentActivityFeed");
    if (!container) return;
    const state = window.APP_STATE.data;
    const sym = state.currencySymbol;

    if (!list || list.length === 0) {
      container.innerHTML = `
        <div style="text-align:center; padding:22px 10px; color:var(--text-muted); font-size:12.5px;">
          <div style="font-size:24px; margin-bottom:6px;">📜</div>
          <div>No transactions recorded yet</div>
          <div style="font-size:11.5px; margin-top:4px; color:var(--accent); font-weight:600; cursor:pointer;" onclick="window.APP_MOBILE.openAddSheet('expense')">+ Record your first expense</div>
        </div>
      `;
      return;
    }

    container.innerHTML = list.map(t => {
      const cat = state.categories.find(c => String(c.id) === String(t.categoryId)) || { name: t.categoryName || "General", icon: t.categoryIcon || "📜", color: "#8C8C8C" };
      const isInc = t.type === "income";
      return `
        <button class="tx-item-btn" onclick="window.APP_MOBILE.openDetail('${t.id}')">
          <div class="tx-icon-badge" style="background:${cat.color}20; color:${cat.color};">${cat.icon}</div>
          <div style="flex:1; min-width:0;">
            <div style="font-size:13.5px; font-weight:600; color:var(--text); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${t.description}</div>
            <div style="font-size:11.5px; color:var(--text-muted); margin-top:1px;">${cat.name} · ${t.date} · ${t.account}</div>
          </div>
          <div class="money" style="font-size:14px; font-weight:700; color:${isInc ? "var(--success)" : "var(--text)"};">
            ${isInc ? "+" : "-"}${window.APP_UTILS.formatMoney(t.amount, sym)}
          </div>
        </button>
      `;
    }).join("");
  },

  renderGroupedTransactions(list) {
    const container = document.getElementById("lGroupedTransactionsList");
    if (!container) return;
    const state = window.APP_STATE.data;
    const sym = state.currencySymbol;

    if (!list || !list.length) {
      container.innerHTML = `
        <div class="l-card" style="text-align:center; padding:36px 16px; color:var(--text-muted);">
          <div style="font-size:36px; margin-bottom:10px;">📅</div>
          <div style="font-size:15px; font-weight:600; color:var(--text);">No Records Found</div>
          <div style="font-size:12px; margin-top:6px; color:var(--text-muted);">No transactions recorded for ${window.APP_UTILS.formatMonthName(this.selectedMonthKey)}.</div>
          <div style="margin-top:14px;">
            <button class="btn-brass-primary" onclick="window.APP_MOBILE.openAddSheet('expense')">+ Record New Entry</button>
          </div>
        </div>
      `;
      return;
    }

    // If "all" is selected, group by Month first
    if (this.selectedMonthKey === "all") {
      const monthGroups = {};
      list.forEach(t => {
        const mKey = window.APP_UTILS.getMonthKey(t.date);
        if (!monthGroups[mKey]) monthGroups[mKey] = [];
        monthGroups[mKey].push(t);
      });

      const sortedMonths = Object.keys(monthGroups).sort((a, b) => b.localeCompare(a));
      container.innerHTML = sortedMonths.map(mKey => {
        const monthTxs = monthGroups[mKey];
        const monthIn = monthTxs.filter(t => t.type === "income").reduce((s, t) => s + t.amount, 0);
        const monthOut = monthTxs.filter(t => t.type === "expense").reduce((s, t) => s + t.amount, 0);
        const monthNet = monthIn - monthOut;

        // Group by Date inside this month
        const dayGroups = {};
        monthTxs.forEach(t => {
          if (!dayGroups[t.date]) dayGroups[t.date] = [];
          dayGroups[t.date].push(t);
        });

        return `
          <div style="display:flex; flex-direction:column; gap:10px;">
            <div class="l-card" style="padding:10px 14px; background:var(--card-alt); border-left:3px solid var(--accent); display:flex; justify-content:space-between; align-items:center;">
              <div>
                <strong style="font-family:var(--font-serif); font-size:15px;">📅 ${window.APP_UTILS.formatMonthName(mKey)}</strong>
                <div style="font-size:11px; color:var(--text-muted); margin-top:2px;">${monthTxs.length} transactions recorded</div>
              </div>
              <div style="text-align:right;">
                <div class="money" style="font-size:13px; font-weight:700; color:${monthNet >= 0 ? "var(--success)" : "var(--danger)"};">
                  ${monthNet >= 0 ? "+" : "-"}${window.APP_UTILS.formatMoney(Math.abs(monthNet), sym)}
                </div>
                <div style="font-size:10px; color:var(--text-muted);">In: +${window.APP_UTILS.formatMoney(monthIn, sym)} | Out: -${window.APP_UTILS.formatMoney(monthOut, sym)}</div>
              </div>
            </div>

            ${Object.keys(dayGroups).sort((a, b) => b.localeCompare(a)).map(dateStr => `
              <div class="l-card" style="padding:4px 14px;">
                <div style="font-size:11px; font-weight:700; color:var(--accent); text-transform:uppercase; letter-spacing:0.06em; padding:8px 0 4px; border-bottom:1px solid var(--border);">
                  ${dateStr}
                </div>
                ${dayGroups[dateStr].map(t => this.renderTxRow(t, state, sym)).join("")}
              </div>
            `).join("")}
          </div>
        `;
      }).join("");
      return;
    }

    // Specific Month: Group by Date
    const dayGroups = {};
    list.forEach(t => {
      if (!dayGroups[t.date]) dayGroups[t.date] = [];
      dayGroups[t.date].push(t);
    });

    const sortedDates = Object.keys(dayGroups).sort((a, b) => b.localeCompare(a));
    container.innerHTML = sortedDates.map(dateStr => {
      const dayTxs = dayGroups[dateStr];
      return `
        <div class="l-card" style="padding:4px 14px;">
          <div style="font-size:11px; font-weight:700; color:var(--accent); text-transform:uppercase; letter-spacing:0.06em; padding:10px 0 4px; border-bottom:1px solid var(--border);">
            ${dateStr}
          </div>
          ${dayTxs.map(t => this.renderTxRow(t, state, sym)).join("")}
        </div>
      `;
    }).join("");
  },

  renderTxRow(t, state, sym) {
    const cat = state.categories.find(c => String(c.id) === String(t.categoryId)) || { name: t.categoryName || "General", icon: t.categoryIcon || "📜", color: "#8C8C8C" };
    const isInc = t.type === "income";
    return `
      <button class="tx-item-btn" onclick="window.APP_MOBILE.openDetail('${t.id}')">
        <div class="tx-icon-badge" style="background:${cat.color}20; color:${cat.color};">${cat.icon}</div>
        <div style="flex:1; min-width:0;">
          <div style="font-size:13.5px; font-weight:600; color:var(--text); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${t.description}</div>
          <div style="font-size:11.5px; color:var(--text-muted); margin-top:1px;">${cat.name} · ${t.account}${t.notes ? ` · <em>"${t.notes}"</em>` : ""}</div>
        </div>
        <div class="money" style="font-size:14px; font-weight:700; color:${isInc ? "var(--success)" : "var(--text)"};">
          ${isInc ? "+" : "-"}${window.APP_UTILS.formatMoney(t.amount, sym)}
        </div>
      </button>
    `;
  },

  populateAddSheetCategories() {
    const grid = document.getElementById("lCatGrid");
    if (!grid) return;
    const state = window.APP_STATE.data;
    grid.innerHTML = state.categories.map(c => `
      <button class="cat-picker-btn ${c.id === this.selectedCatId ? "active" : ""}" type="button" onclick="window.APP_MOBILE.selectCategory('${c.id}')">
        <span style="font-size:18px;">${c.icon}</span>
        <span style="font-size:10.5px; color:var(--text-sec); white-space:nowrap; overflow:hidden; text-overflow:ellipsis; width:100%; text-align:center;">${c.name}</span>
      </button>
    `).join("") + `
      <button class="cat-picker-btn" type="button" onclick="window.APP_MOBILE.openNewCategorySheet()" style="border-style:dashed !important; border-color:var(--accent) !important; color:var(--accent);">
        <span style="font-size:18px;">➕</span>
        <span style="font-size:10.5px; font-weight:600; color:var(--accent); white-space:nowrap;">New</span>
      </button>
    `;

    const budgetCatSelect = document.getElementById("lBudgetCatSelect");
    if (budgetCatSelect) {
      budgetCatSelect.innerHTML = state.categories.filter(c => c.name !== "Income").map(c => `<option value="${c.id}">${c.name}</option>`).join("");
    }
  },

  selectCategory(id) {
    this.selectedCatId = id;
    this.populateAddSheetCategories();
  },

  setType(type) {
    this.activeTxType = type;
    const expBtn = document.getElementById("btnType-exp");
    const incBtn = document.getElementById("btnType-inc");
    if (expBtn && incBtn) {
      expBtn.classList.toggle("active", type === "expense");
      incBtn.classList.toggle("active", type === "income");
    }
    const catContainer = document.getElementById("lCatPickerContainer");
    if (catContainer) catContainer.style.display = type === "income" ? "none" : "block";
  },

  openAddSheet(presetType = "expense") {
    this.editingTxId = null;
    this.setType(presetType);
    document.getElementById("lInAmt").value = "";
    document.getElementById("lInDesc").value = "";
    document.getElementById("lInNotes").value = "";
    document.getElementById("lInDate").value = new Date().toISOString().slice(0, 10);
    document.getElementById("lSheetTitle").textContent = "New Entry";
    const overlay = document.getElementById("lAddSheetOverlay");
    if (overlay) overlay.classList.add("open");
  },

  openDetail(txId) {
    const state = window.APP_STATE.data;
    const tx = state.transactions.find(t => t.id === txId);
    if (!tx) return;
    this.editingTxId = txId;

    const cat = state.categories.find(c => c.id === tx.categoryId) || { name: "General", icon: "📜" };
    const detailContent = document.getElementById("lDetailContent");
    if (detailContent) {
      detailContent.innerHTML = `
        <div style="text-align:center; padding:12px 0 20px;">
          <div style="font-size:36px; margin-bottom:6px;">${cat.icon}</div>
          <h2 style="font-family:var(--font-serif); font-size:24px; font-weight:600;">${tx.description}</h2>
          <div class="money" style="font-size:32px; font-weight:700; color:${tx.type === "income" ? "var(--success)" : "var(--accent)"}; margin-top:8px;">
            ${tx.type === "income" ? "+" : "-"}${window.APP_UTILS.formatMoney(tx.amount, state.currencySymbol)}
          </div>
        </div>

        <div class="l-card" style="display:flex; flex-direction:column; gap:10px; font-size:13px;">
          <div style="display:flex; justify-content:space-between;">
            <span style="color:var(--text-muted);">Category</span>
            <strong>${cat.name}</strong>
          </div>
          <div style="display:flex; justify-content:space-between;">
            <span style="color:var(--text-muted);">Account</span>
            <strong>${tx.account}</strong>
          </div>
          <div style="display:flex; justify-content:space-between;">
            <span style="color:var(--text-muted);">Date</span>
            <strong>${tx.date}</strong>
          </div>
          ${tx.notes ? `
            <div style="border-top:1px solid var(--border); padding-top:8px; color:var(--text-sec); font-style:italic;">
              "${tx.notes}"
            </div>
          ` : ""}
        </div>
      `;
    }

    const overlay = document.getElementById("lDetailOverlay");
    if (overlay) overlay.classList.add("open");
  },

  deleteCurrentTx() {
    if (this.editingTxId) {
      window.APP_STATE.deleteTransaction(this.editingTxId);
      this.closeSheet('lDetailOverlay');
    }
  },

  saveEntry() {
    const amtInput = document.getElementById("lInAmt");
    const descInput = document.getElementById("lInDesc");
    const acctInput = document.getElementById("lInAcct");
    const dateInput = document.getElementById("lInDate");
    const notesInput = document.getElementById("lInNotes");

    const amt = parseFloat(amtInput ? amtInput.value : "0");
    const desc = descInput ? descInput.value.trim() : "";
    const acct = acctInput ? acctInput.value : "Business";
    const date = (dateInput && dateInput.value) ? dateInput.value : new Date().toISOString().slice(0, 10);
    const notes = notesInput ? notesInput.value.trim() : "";

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

    // Resolve category name from the selected category
    const state = window.APP_STATE.data;
    const catIdForTx = this.activeTxType === "income" ? "cat-income" : (this.selectedCatId || "cat-software");
    const selectedCat = state.categories.find(c => String(c.id) === String(catIdForTx));
    const catNameForTx = (selectedCat && selectedCat.name) || catIdForTx;

    const newTx = {
      id: "tx-" + Date.now(),
      date,
      description: desc,
      categoryId: catIdForTx,
      categoryName: catNameForTx,
      account: acct,
      type: this.activeTxType || "expense",
      amount: amt,
      notes
    };

    // 1. Add to centralized reactive state
    window.APP_STATE.addTransaction(newTx);

    // 2. Clear inputs
    if (amtInput) amtInput.value = "";
    if (descInput) descInput.value = "";
    if (notesInput) notesInput.value = "";

    // 3. Close bottom sheet
    this.closeSheet('lAddSheetOverlay');

    // 4. Force view render & ensure home view is visible
    this.render();
    this.showTab('home');
  },

  saveBudgetLimit() {
    const catId = document.getElementById("lBudgetCatSelect").value;
    const limit = parseFloat(document.getElementById("lBudgetLimitAmt").value);
    if (!limit || limit <= 0) {
      window.APP_UTILS.showToast("Please enter a valid budget limit");
      return;
    }
    window.APP_STATE.setCategoryBudget(catId, limit);
    this.closeSheet('lBudgetSheetOverlay');
  },

  openEditProfileSheet() {
    const state = window.APP_STATE.data;
    if (state.userProfile) {
      const nameIn = document.getElementById("lEditProfileName");
      if (nameIn) nameIn.value = state.userProfile.name;
      const bizIn = document.getElementById("lEditProfileBusiness");
      if (bizIn) bizIn.value = state.userProfile.business;
      const emailIn = document.getElementById("lEditProfileEmail");
      if (emailIn) emailIn.value = state.userProfile.email;
    }
    const overlay = document.getElementById("lEditProfileOverlay");
    if (overlay) overlay.classList.add("open");
  },

  saveProfileChanges() {
    const name = (document.getElementById("lEditProfileName").value || "").trim();
    const business = (document.getElementById("lEditProfileBusiness").value || "").trim();
    const email = (document.getElementById("lEditProfileEmail").value || "").trim();

    if (!name) {
      window.APP_UTILS.showToast("Please enter your name");
      return;
    }

    window.APP_STATE.updateProfile(name, business, email);
    this.closeSheet('lEditProfileOverlay');
    this.render();
  },

  changeCurrency(val) {
    if (!val) return;
    const [code, sym] = val.split("|");
    window.APP_STATE.setCurrency(code, sym);
  },

  openNewCategorySheet() {
    const nameIn = document.getElementById("lNewCatName");
    if (nameIn) nameIn.value = "";
    const iconIn = document.getElementById("lNewCatIcon");
    if (iconIn) iconIn.value = "📢";
    const budgetIn = document.getElementById("lNewCatBudget");
    if (budgetIn) budgetIn.value = "25000";

    const overlay = document.getElementById("lNewCategorySheetOverlay");
    if (overlay) overlay.classList.add("open");
  },

  selectNewCatEmoji(emoji) {
    const iconIn = document.getElementById("lNewCatIcon");
    if (iconIn) iconIn.value = emoji;
  },

  saveNewCategory() {
    const name = (document.getElementById("lNewCatName").value || "").trim();
    const icon = (document.getElementById("lNewCatIcon").value || "📁").trim();
    const budget = parseFloat(document.getElementById("lNewCatBudget").value || "25000");

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
    this.selectedCatId = newCat.id;
    this.closeSheet('lNewCategorySheetOverlay');
    this.render();
  },

  openEditBudgetSheet(categoryId, currentLimit) {
    const catSelect = document.getElementById("lBudgetCatSelect");
    if (catSelect) catSelect.value = categoryId;
    const limitIn = document.getElementById("lBudgetLimitAmt");
    if (limitIn) limitIn.value = currentLimit || 25000;
    const overlay = document.getElementById("lBudgetSheetOverlay");
    if (overlay) overlay.classList.add("open");
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

  closeSheet(overlayId) {
    const overlay = document.getElementById(overlayId);
    if (overlay) overlay.classList.remove("open");
  }
};
