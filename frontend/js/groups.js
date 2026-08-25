/* ==========================================================================
   THE LEDGER — GROUPS MODULE (APP_GROUPS)
   Handles all Groups, Group Expenses, Balances & Settlements UI logic.
   ========================================================================== */
window.APP_GROUPS = {
  /* ---- State ---- */
  currentGroupId: null,
  currentGroup: null,
  currentMembers: [],
  currentBalances: null,
  currentSettlements: [],
  currentExpenses: [],
  currentDetailTab: "activity",
  currentSplitMethod: "equal",
  categories: [],

  /* ================================================================
     INITIALISATION
     ================================================================ */
  async init() {
    // Pre-load categories once for all group expense sheets
    try {
      this.categories = await window.APP_API.getCategories();
    } catch (e) { /* non-fatal */ }
  },

  /* ================================================================
     SHEET HELPERS
     ================================================================ */
  openSheet(id) {
    const el = document.getElementById(id);
    if (el) {
      el.classList.add("open");
      el.style.display = "flex";
    }
  },

  closeGroupSheet(id) {
    const el = document.getElementById(id);
    if (el) {
      el.classList.remove("open");
      el.style.display = "none";
    }
  },

  toast(msg, type = "info") {
    const t = document.getElementById("lToast");
    if (!t) return;
    t.textContent = msg;
    t.style.background = type === "error" ? "var(--danger)" : "var(--accent)";
    t.style.display = "block";
    t.style.opacity = "1";
    setTimeout(() => { t.style.opacity = "0"; setTimeout(() => { t.style.display = "none"; }, 400); }, 2800);
  },

  fmt(amount) {
    const sym = (window.APP_STATE && window.APP_STATE.data && window.APP_STATE.data.currencySymbol) || "₹";
    return window.APP_UTILS ? window.APP_UTILS.formatMoney(Math.abs(parseFloat(amount) || 0), sym) : `${sym}${Math.abs(parseFloat(amount)||0).toLocaleString("en-IN")}`;
  },

  getMyUserId() {
    return window.APP_STATE && window.APP_STATE.data && window.APP_STATE.data.userId;
  },

  todayStr() {
    return new Date().toISOString().split("T")[0];
  },

  /* ================================================================
     GROUPS LIST VIEW
     ================================================================ */
  async loadGroupsList() {
    this.showSubview("list");
    const container = document.getElementById("lGroupsList");
    if (!container) return;

    container.innerHTML = `<div style="text-align:center; padding:32px 0; color:var(--text-muted); font-size:13px;">Loading groups…</div>`;

    try {
      const groups = await window.APP_API.getGroups();

      // Compute net balance summaries across all groups
      let totalOwed = 0, totalOwe = 0;
      const myId = this.getMyUserId();

      if (groups.length === 0) {
        container.innerHTML = `
          <div style="text-align:center; padding:40px 16px;">
            <div style="font-size:36px; margin-bottom:12px;">🤝</div>
            <div style="font-size:15px; font-weight:600; color:var(--text); margin-bottom:6px;">No Groups Yet</div>
            <div style="font-size:12.5px; color:var(--text-muted); line-height:1.5;">Create a group for your trip, roommates, or any shared expenses.</div>
          </div>`;
        this.updateNetSummary(0, 0);
        return;
      }

      // Load balances for each group (in parallel)
      const balanceResults = await Promise.allSettled(
        groups.map(g => window.APP_API.getGroupBalances(g.id))
      );

      const cards = groups.map((g, i) => {
        let myNetBalance = 0;
        const balRes = balanceResults[i];
        if (balRes.status === "fulfilled" && balRes.value && balRes.value.balances) {
          const myBal = balRes.value.balances.find(b => b.user_id === myId);
          if (myBal) myNetBalance = parseFloat(myBal.net_balance) || 0;
        }

        if (myNetBalance > 0) totalOwed += myNetBalance;
        else if (myNetBalance < 0) totalOwe += Math.abs(myNetBalance);

        const balColor = myNetBalance > 0 ? "var(--success)" : myNetBalance < 0 ? "var(--danger)" : "var(--text-muted)";
        const balLabel = myNetBalance > 0 ? `You are owed ${this.fmt(myNetBalance)}` :
                         myNetBalance < 0 ? `You owe ${this.fmt(myNetBalance)}` : "All settled";
        const memberCount = g.members ? g.members.length : 0;

        return `
          <div class="l-card" style="display:flex; align-items:center; gap:12px; padding:14px 16px; cursor:pointer; transition:transform var(--trans-fast);"
               onclick="window.APP_GROUPS.openGroupDetail(${g.id})"
               onmousedown="this.style.transform='scale(0.98)'" onmouseup="this.style.transform=''" ontouchstart="this.style.transform='scale(0.98)'" ontouchend="this.style.transform=''">
            <div style="width:46px; height:46px; border-radius:14px; background:linear-gradient(135deg, var(--accent-soft), var(--card-alt)); display:flex; align-items:center; justify-content:center; font-size:22px; flex-shrink:0; border:1px solid var(--border);">${g.icon || "🤝"}</div>
            <div style="flex:1; min-width:0;">
              <div style="font-size:14.5px; font-weight:700; color:var(--text); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${g.name}</div>
              <div style="font-size:11.5px; color:var(--text-muted); margin-top:2px;">${memberCount} member${memberCount !== 1 ? "s" : ""}</div>
            </div>
            <div style="text-align:right; flex-shrink:0;">
              <div style="font-size:13px; font-weight:700; font-family:var(--font-mono); color:${balColor};">${myNetBalance !== 0 ? this.fmt(myNetBalance) : ""}</div>
              <div style="font-size:10.5px; color:${balColor}; font-weight:600; margin-top:2px;">${balLabel}</div>
            </div>
          </div>`;
      });

      container.innerHTML = cards.join("");
      this.updateNetSummary(totalOwed, totalOwe);

    } catch (err) {
      container.innerHTML = `<div style="text-align:center; padding:24px; color:var(--danger); font-size:13px;">Failed to load groups. Please try again.</div>`;
    }
  },

  updateNetSummary(owed, owe) {
    const owedEl = document.getElementById("lGrpTotalOwed");
    const oweEl = document.getElementById("lGrpTotalOwe");
    if (owedEl) owedEl.textContent = this.fmt(owed);
    if (oweEl) oweEl.textContent = this.fmt(owe);
  },

  /* ================================================================
     GROUP DETAIL VIEW
     ================================================================ */
  async openGroupDetail(groupId) {
    this.currentGroupId = groupId;
    this.currentDetailTab = "activity";
    this.showSubview("detail");

    // Reset tabs
    ["activity", "balances", "members"].forEach(t => {
      const btn = document.getElementById(`lGrpTab-${t}`);
      if (btn) btn.classList.toggle("active", t === "activity");
    });
    const actDiv = document.getElementById("lGrpActivity");
    const balDiv = document.getElementById("lGrpBalances");
    const memDiv = document.getElementById("lGrpMembers");
    if (actDiv) { actDiv.style.display = "flex"; actDiv.innerHTML = `<div style="text-align:center; padding:20px 0; color:var(--text-muted); font-size:13px;">Loading…</div>`; }
    if (balDiv) balDiv.style.display = "none";
    if (memDiv) memDiv.style.display = "none";

    try {
      const [group, expenses, balData, settlements] = await Promise.all([
        window.APP_API.getGroup(groupId),
        window.APP_API.getGroupExpenses(groupId),
        window.APP_API.getGroupBalances(groupId),
        window.APP_API.getGroupSettlements(groupId),
      ]);

      this.currentGroup = group;
      this.currentMembers = group.members || [];
      this.currentBalances = balData;
      this.currentSettlements = settlements || [];
      this.currentExpenses = expenses || [];

      // Update header
      const iconEl = document.getElementById("lGrpDetailIcon");
      const nameEl = document.getElementById("lGrpDetailName");
      const countEl = document.getElementById("lGrpDetailMemberCount");
      if (iconEl) iconEl.textContent = group.icon || "🤝";
      if (nameEl) nameEl.textContent = group.name;
      if (countEl) countEl.textContent = `${this.currentMembers.length} member${this.currentMembers.length !== 1 ? "s" : ""}`;

      // Update my balance card
      this.renderMyBalCard();

      // Render activity feed
      this.renderActivityFeed();

    } catch (err) {
      this.toast("Failed to load group details", "error");
    }
  },

  renderMyBalCard() {
    const card = document.getElementById("lGrpMyBalCard");
    if (!card) return;

    const myId = this.getMyUserId();
    const bal = this.currentBalances && this.currentBalances.balances
      ? this.currentBalances.balances.find(b => b.user_id === myId)
      : null;

    if (!bal) {
      card.innerHTML = `<div style="color:var(--text-muted); font-size:13px;">No transactions yet.</div>`;
      return;
    }

    const net = parseFloat(bal.net_balance) || 0;
    const color = net > 0 ? "var(--success)" : net < 0 ? "var(--danger)" : "var(--text-muted)";
    const label = net > 0 ? "you are owed" : net < 0 ? "you owe" : "you are settled up";

    card.innerHTML = `
      <div style="font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:0.08em; color:${color}; margin-bottom:4px;">Your Balance</div>
      <div class="money" style="font-size:22px; font-weight:700; color:${color};">${net !== 0 ? this.fmt(net) : "₹0"}</div>
      <div style="font-size:12px; color:var(--text-muted); margin-top:3px;">${label}</div>`;
  },

  renderActivityFeed() {
    const container = document.getElementById("lGrpActivity");
    if (!container) return;

    // Merge expenses and settlements into one feed sorted by date (newest first)
    const feed = [
      ...this.currentExpenses.map(e => ({ ...e, _type: "expense" })),
      ...this.currentSettlements.map(s => ({ ...s, _type: "settlement" })),
    ].sort((a, b) => {
      const da = new Date(a.date || a.created_at);
      const db = new Date(b.date || b.created_at);
      return db - da;
    });

    if (feed.length === 0) {
      container.innerHTML = `
        <div style="text-align:center; padding:40px 16px;">
          <div style="font-size:32px; margin-bottom:8px;">📋</div>
          <div style="font-size:13px; color:var(--text-muted);">No activity yet. Add the first expense!</div>
        </div>`;
      return;
    }

    container.innerHTML = feed.map(item => {
      if (item._type === "expense") return this.renderExpenseCard(item);
      return this.renderSettlementCard(item);
    }).join("");
  },

  renderExpenseCard(expense) {
    const myId = this.getMyUserId();
    const myPart = expense.participants ? expense.participants.find(p => p.user_id === myId) : null;
    const myShare = myPart ? parseFloat(myPart.owed_amount) : 0;
    const paidBy = expense.payments && expense.payments[0] ? expense.payments[0].full_name || expense.payments[0].payer_name || "Someone" : "Someone";
    const myPaid = expense.payments ? expense.payments.filter(p => p.user_id === myId).reduce((s, p) => s + parseFloat(p.amount), 0) : 0;

    let shareLabel = "";
    let shareColor = "var(--text-muted)";
    if (myPaid > 0 && myShare > 0) {
      const net = myPaid - myShare;
      shareLabel = net > 0 ? `You lent ${this.fmt(net)}` : net < 0 ? `You owe ${this.fmt(net)}` : "You're settled";
      shareColor = net > 0 ? "var(--success)" : net < 0 ? "var(--danger)" : "var(--text-muted)";
    } else if (myPaid > 0) {
      shareLabel = `You paid ${this.fmt(myPaid)}`;
      shareColor = "var(--success)";
    } else if (myShare > 0) {
      shareLabel = `You owe ${this.fmt(myShare)}`;
      shareColor = "var(--danger)";
    }

    return `
      <div class="l-card" style="padding:12px 14px; display:flex; gap:12px; align-items:flex-start;">
        <div style="width:38px; height:38px; border-radius:10px; background:var(--accent-soft); display:flex; align-items:center; justify-content:center; font-size:17px; flex-shrink:0; border:1px solid var(--border);">💸</div>
        <div style="flex:1; min-width:0;">
          <div style="font-size:13.5px; font-weight:700; color:var(--text); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${expense.description}</div>
          <div style="font-size:11.5px; color:var(--text-muted); margin-top:2px;">${paidBy} paid · ${expense.date || ""}</div>
        </div>
        <div style="text-align:right; flex-shrink:0;">
          <div class="money" style="font-size:14px; font-weight:700; color:var(--text);">${this.fmt(expense.amount)}</div>
          <div style="font-size:10.5px; font-weight:600; color:${shareColor}; margin-top:2px;">${shareLabel}</div>
        </div>
      </div>`;
  },

  renderSettlementCard(s) {
    const myId = this.getMyUserId();
    const isMyPay = s.payer_id === myId;
    const isMyReceive = s.receiver_id === myId;
    let label = `${s.payer_name || "?"} paid ${s.receiver_name || "?"}`;
    if (isMyPay) label = `You paid ${s.receiver_name || "?"}`;
    else if (isMyReceive) label = `${s.payer_name || "?"} paid you`;

    return `
      <div class="l-card" style="padding:12px 14px; display:flex; gap:12px; align-items:flex-start; opacity:0.85;">
        <div style="width:38px; height:38px; border-radius:10px; background:var(--success-soft); display:flex; align-items:center; justify-content:center; font-size:17px; flex-shrink:0; border:1px solid var(--border);">✅</div>
        <div style="flex:1; min-width:0;">
          <div style="font-size:13px; font-weight:700; color:var(--success);">Settlement</div>
          <div style="font-size:11.5px; color:var(--text-muted); margin-top:2px;">${label} · ${s.date || ""}</div>
          ${s.notes ? `<div style="font-size:11px; color:var(--text-muted); margin-top:2px; font-style:italic;">"${s.notes}"</div>` : ""}
        </div>
        <div style="text-align:right; flex-shrink:0;">
          <div class="money" style="font-size:14px; font-weight:700; color:var(--success);">${this.fmt(s.amount)}</div>
          <button onclick="window.APP_GROUPS.deleteSettlement(${s.id})"
                  style="font-size:10px; color:var(--danger); background:none; border:none; cursor:pointer; margin-top:4px; padding:0;">Reverse</button>
        </div>
      </div>`;
  },

  switchDetailTab(tab) {
    this.currentDetailTab = tab;
    ["activity", "balances", "members"].forEach(t => {
      const btn = document.getElementById(`lGrpTab-${t}`);
      if (btn) btn.classList.toggle("active", t === tab);
    });

    const actDiv = document.getElementById("lGrpActivity");
    const balDiv = document.getElementById("lGrpBalances");
    const memDiv = document.getElementById("lGrpMembers");

    if (actDiv) actDiv.style.display = tab === "activity" ? "flex" : "none";
    if (balDiv) balDiv.style.display = tab === "balances" ? "flex" : "none";
    if (memDiv) memDiv.style.display = tab === "members" ? "flex" : "none";

    if (tab === "balances") this.renderBalancesTab();
    if (tab === "members") this.renderMembersTab();
  },

  renderBalancesTab() {
    const container = document.getElementById("lGrpBalances");
    if (!container || !this.currentBalances) return;

    const { balances, simplified_debts } = this.currentBalances;

    let html = `<div style="font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; color:var(--accent); margin-bottom:8px;">Member Balances</div>`;

    if (balances && balances.length > 0) {
      html += balances.map(b => {
        const net = parseFloat(b.net_balance);
        const color = net > 0 ? "var(--success)" : net < 0 ? "var(--danger)" : "var(--text-muted)";
        const label = net > 0 ? "gets back" : net < 0 ? "owes" : "settled";
        return `
          <div class="l-card" style="padding:12px 14px; display:flex; justify-content:space-between; align-items:center;">
            <div style="display:flex; align-items:center; gap:10px;">
              <div style="width:34px; height:34px; border-radius:10px; background:linear-gradient(135deg, var(--accent-soft), var(--card-alt)); display:flex; align-items:center; justify-content:center; font-size:14px; font-weight:700; color:var(--accent); border:1px solid var(--border);">${(b.full_name || b.email || "?")[0].toUpperCase()}</div>
              <div>
                <div style="font-size:13px; font-weight:600; color:var(--text);">${b.full_name || b.email}</div>
                <div style="font-size:11px; color:var(--text-muted);">${label}</div>
              </div>
            </div>
            <div class="money" style="font-size:15px; font-weight:700; color:${color};">${net !== 0 ? this.fmt(net) : "Settled"}</div>
          </div>`;
      }).join("");
    }

    if (simplified_debts && simplified_debts.length > 0) {
      html += `<div style="font-size:12px; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; color:var(--accent); margin:12px 0 8px;">Suggested Payments</div>`;
      html += simplified_debts.map(s => `
        <div class="l-card" style="padding:12px 14px; display:flex; justify-content:space-between; align-items:center; background:var(--success-soft);">
          <div style="font-size:13px; color:var(--text);">${s.from_user_name} → ${s.to_user_name}</div>
          <div class="money" style="font-size:14px; font-weight:700; color:var(--success);">${this.fmt(s.amount)}</div>
        </div>`).join("");
    }

    container.innerHTML = html;
  },

  renderMembersTab() {
    const container = document.getElementById("lGrpMembers");
    if (!container) return;

    const myId = this.getMyUserId();
    const isOwner = this.currentGroup && this.currentGroup.owner_id === myId;

    if (this.currentMembers.length === 0) {
      container.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-muted); font-size:13px;">No members.</div>`;
      return;
    }

    container.innerHTML = this.currentMembers.map(m => `
      <div class="l-card" style="padding:12px 14px; display:flex; align-items:center; gap:10px;">
        <div style="width:36px; height:36px; border-radius:10px; background:linear-gradient(135deg, var(--accent), var(--accent-bright)); display:flex; align-items:center; justify-content:center; font-size:14px; font-weight:700; color:#1A1408;">${(m.full_name || m.email || "?")[0].toUpperCase()}</div>
        <div style="flex:1; min-width:0;">
          <div style="font-size:13px; font-weight:600; color:var(--text); white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${m.full_name || m.email}</div>
          <div style="font-size:11px; color:var(--text-muted);">${m.role === "admin" ? "Admin" : "Member"}</div>
        </div>
        ${(isOwner && m.user_id !== this.currentGroup.owner_id) ? `
          <button onclick="window.APP_GROUPS.removeMember(${m.user_id})"
                  style="font-size:11px; color:var(--danger); background:var(--danger-soft); border:none; border-radius:8px; padding:4px 8px; cursor:pointer;">Remove</button>` : ""}
      </div>`).join("");
  },

  /* ================================================================
     SUBVIEW NAVIGATION
     ================================================================ */
  showSubview(name) {
    ["list", "detail"].forEach(n => {
      const el = document.getElementById(`lGrpSubview-${n}`);
      if (el) el.style.display = n === name ? "flex" : "none";
    });
  },

  goToGroupsList() {
    this.currentGroupId = null;
    this.currentGroup = null;
    this.showSubview("list");
    document.getElementById("lHeaderTitle") && (document.getElementById("lHeaderTitle").textContent = "Groups");
    this.loadGroupsList();
  },

  /* ================================================================
     CREATE GROUP
     ================================================================ */
  openCreateGroupSheet() {
    const nameEl = document.getElementById("lGrpNameInput");
    const iconEl = document.getElementById("lGrpIconInput");
    if (nameEl) nameEl.value = "";
    if (iconEl) iconEl.value = "🤝";
    this.openSheet("lCreateGroupOverlay");
  },

  selectGrpIcon(emoji) {
    const iconEl = document.getElementById("lGrpIconInput");
    if (iconEl) iconEl.value = emoji;
  },

  async createGroup() {
    const name = (document.getElementById("lGrpNameInput") || {}).value?.trim();
    const icon = (document.getElementById("lGrpIconInput") || {}).value?.trim() || "🤝";
    if (!name) { this.toast("Please enter a group name", "error"); return; }

    try {
      const group = await window.APP_API.createGroup({ name, icon });
      this.closeGroupSheet("lCreateGroupOverlay");
      this.toast(`Group "${group.name}" created!`);
      this.loadGroupsList();
    } catch (err) {
      this.toast(err.message || "Failed to create group", "error");
    }
  },

  /* ================================================================
     GROUP SETTINGS
     ================================================================ */
  openGroupSettings() {
    if (!this.currentGroup) return;
    const nameEl = document.getElementById("lGrpEditName");
    const iconEl = document.getElementById("lGrpEditIcon");
    if (nameEl) nameEl.value = this.currentGroup.name || "";
    if (iconEl) iconEl.value = this.currentGroup.icon || "🤝";
    this.openSheet("lGroupSettingsOverlay");
  },

  async saveGroupSettings() {
    const name = (document.getElementById("lGrpEditName") || {}).value?.trim();
    const icon = (document.getElementById("lGrpEditIcon") || {}).value?.trim() || "🤝";
    if (!name) { this.toast("Group name cannot be empty", "error"); return; }

    try {
      const updated = await window.APP_API.updateGroup(this.currentGroupId, { name, icon });
      this.currentGroup = { ...this.currentGroup, name: updated.name, icon: updated.icon };
      const nameEl = document.getElementById("lGrpDetailName");
      const iconEl = document.getElementById("lGrpDetailIcon");
      if (nameEl) nameEl.textContent = updated.name;
      if (iconEl) iconEl.textContent = updated.icon;
      this.closeGroupSheet("lGroupSettingsOverlay");
      this.toast("Group updated!");
    } catch (err) {
      this.toast(err.message || "Failed to update group", "error");
    }
  },

  async confirmDeleteGroup() {
    if (!confirm(`Delete "${this.currentGroup?.name}"? This cannot be undone.`)) return;
    try {
      await window.APP_API.deleteGroup(this.currentGroupId);
      this.closeGroupSheet("lGroupSettingsOverlay");
      this.toast("Group deleted.");
      this.goToGroupsList();
    } catch (err) {
      this.toast(err.message || "Failed to delete group", "error");
    }
  },

  /* ================================================================
     MEMBERS
     ================================================================ */
  openAddMemberSheet() {
    const el = document.getElementById("lAddMemberEmail");
    if (el) el.value = "";
    this.closeGroupSheet("lGroupSettingsOverlay");
    this.openSheet("lAddMemberOverlay");
  },

  async addMember() {
    const email = (document.getElementById("lAddMemberEmail") || {}).value?.trim();
    if (!email) { this.toast("Please enter an email address", "error"); return; }

    try {
      await window.APP_API.addGroupMember(this.currentGroupId, email);
      this.closeGroupSheet("lAddMemberOverlay");
      this.toast("Member added!");
      await this.openGroupDetail(this.currentGroupId);
    } catch (err) {
      this.toast(err.message || "Failed to add member", "error");
    }
  },

  async removeMember(userId) {
    if (!confirm("Remove this member from the group?")) return;
    try {
      await window.APP_API.removeGroupMember(this.currentGroupId, userId);
      this.toast("Member removed.");
      await this.openGroupDetail(this.currentGroupId);
    } catch (err) {
      this.toast(err.message || "Failed to remove member", "error");
    }
  },

  /* ================================================================
     ADD GROUP EXPENSE
     ================================================================ */
  openAddGroupExpenseSheet() {
    if (!this.currentGroupId) return;

    // Set defaults
    const dateEl = document.getElementById("lGrpExpDate");
    const amtEl = document.getElementById("lGrpExpAmt");
    const descEl = document.getElementById("lGrpExpDesc");
    if (dateEl) dateEl.value = this.todayStr();
    if (amtEl) amtEl.value = "";
    if (descEl) descEl.value = "";

    // Populate category dropdown
    const catSel = document.getElementById("lGrpExpCategory");
    if (catSel && this.categories.length > 0) {
      catSel.innerHTML = this.categories
        .filter(c => c.name !== "Income")
        .map(c => `<option value="${c.id}">${c.icon || ""} ${c.name}</option>`)
        .join("");
    }

    // Populate paid-by selector
    const paidBySel = document.getElementById("lGrpExpPaidBy");
    if (paidBySel) {
      paidBySel.innerHTML = this.currentMembers.map(m =>
        `<option value="${m.user_id}" ${m.user_id === this.getMyUserId() ? "selected" : ""}>${m.full_name || m.email}</option>`
      ).join("");
    }

    // Build participant rows
    this.setSplitMethod("equal");

    this.openSheet("lAddGroupExpenseOverlay");
  },

  setSplitMethod(method) {
    this.currentSplitMethod = method;
    ["equal", "exact", "percentage"].forEach(m => {
      const btn = document.getElementById(`lGrpSplitBtn-${m}`);
      if (btn) btn.classList.toggle("active", m === method);
    });
    this.renderParticipantRows();
  },

  renderParticipantRows() {
    const container = document.getElementById("lGrpParticipantsContainer");
    if (!container) return;
    const method = this.currentSplitMethod;

    container.innerHTML = this.currentMembers.map(m => {
      let inputHtml = "";
      if (method === "equal") {
        inputHtml = `<input type="checkbox" checked data-uid="${m.user_id}" style="accent-color:var(--accent); width:18px; height:18px; cursor:pointer;">`;
      } else if (method === "exact") {
        inputHtml = `<input type="number" step="0.01" placeholder="0.00" data-uid="${m.user_id}" class="l-input" style="width:100px; padding:6px 8px; font-size:12.5px; text-align:right;">`;
      } else if (method === "percentage") {
        inputHtml = `<div style="display:flex; align-items:center; gap:4px;"><input type="number" step="1" min="0" max="100" placeholder="0" data-uid="${m.user_id}" class="l-input" style="width:70px; padding:6px 8px; font-size:12.5px; text-align:right;"><span style="font-size:12px; color:var(--text-muted);">%</span></div>`;
      }

      return `
        <div style="display:flex; align-items:center; justify-content:space-between; padding:8px 0; border-bottom:1px solid var(--border);">
          <div style="display:flex; align-items:center; gap:8px;">
            <div style="width:30px; height:30px; border-radius:8px; background:linear-gradient(135deg, var(--accent-soft), var(--card-alt)); display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:700; color:var(--accent);">${(m.full_name || m.email || "?")[0].toUpperCase()}</div>
            <span style="font-size:13px; color:var(--text);">${m.full_name || m.email}</span>
          </div>
          ${inputHtml}
        </div>`;
    }).join("");
  },

  async saveGroupExpense() {
    const amount = parseFloat((document.getElementById("lGrpExpAmt") || {}).value) || 0;
    const description = (document.getElementById("lGrpExpDesc") || {}).value?.trim();
    const date = (document.getElementById("lGrpExpDate") || {}).value;
    const categoryId = parseInt((document.getElementById("lGrpExpCategory") || {}).value) || 1;
    const paidById = parseInt((document.getElementById("lGrpExpPaidBy") || {}).value);
    const method = this.currentSplitMethod;

    if (!amount || amount <= 0) { this.toast("Please enter a valid amount", "error"); return; }
    if (!description) { this.toast("Please add a description", "error"); return; }

    // Build payments array (single payer for now)
    const payments = [{ user_id: paidById, amount }];

    // Build participants array
    const container = document.getElementById("lGrpParticipantsContainer");
    let participants = [];

    if (method === "equal") {
      const checkboxes = container ? container.querySelectorAll("input[type=checkbox]") : [];
      checkboxes.forEach(cb => {
        if (cb.checked) {
          participants.push({ user_id: parseInt(cb.dataset.uid), share_value: 1 });
        }
      });
    } else {
      const inputs = container ? container.querySelectorAll("input[type=number]") : [];
      inputs.forEach(inp => {
        const val = parseFloat(inp.value) || 0;
        if (val > 0) participants.push({ user_id: parseInt(inp.dataset.uid), share_value: val });
      });
    }

    if (participants.length === 0) { this.toast("Select at least one participant", "error"); return; }

    try {
      await window.APP_API.createGroupExpense(this.currentGroupId, {
        category_id: categoryId,
        amount,
        description,
        date,
        split_method: method,
        payments,
        participants,
      });
      this.closeGroupSheet("lAddGroupExpenseOverlay");
      this.toast("Expense added!");
      await this.openGroupDetail(this.currentGroupId);
    } catch (err) {
      this.toast(err.message || "Failed to add expense", "error");
    }
  },

  /* ================================================================
     SETTLE UP
     ================================================================ */
  openSettleUpSheet() {
    if (!this.currentGroupId) return;

    // Pre-fill suggestions from simplified settlements
    const suggestions = this.currentBalances && this.currentBalances.simplified_debts
      ? this.currentBalances.simplified_debts
      : [];

    const suggestContainer = document.getElementById("lSettleSuggestions");
    if (suggestContainer) {
      if (suggestions.length === 0) {
        suggestContainer.innerHTML = `<div style="text-align:center; padding:8px 0; color:var(--success); font-size:13px; font-weight:600;">✅ All settled up!</div>`;
      } else {
        suggestContainer.innerHTML = suggestions.map(s => `
          <div class="l-card" style="padding:12px 14px; background:var(--success-soft); border-color:var(--success); display:flex; justify-content:space-between; align-items:center;">
            <div>
              <div style="font-size:13px; font-weight:600; color:var(--text);">${s.from_user_name || s.from_user_id} → ${s.to_user_name || s.to_user_id}</div>
              <div style="font-size:11px; color:var(--text-muted); margin-top:2px;">Suggested</div>
            </div>
            <div style="display:flex; flex-direction:column; align-items:flex-end; gap:6px;">
              <div class="money" style="font-size:14px; font-weight:700; color:var(--success);">${this.fmt(s.amount)}</div>
              <button onclick="window.APP_GROUPS.prefillSettlement(${s.from_user_id}, ${s.to_user_id}, ${s.amount})"
                      style="font-size:11px; background:var(--success); color:#fff; border:none; border-radius:8px; padding:4px 10px; cursor:pointer;">Use This</button>
            </div>
          </div>`).join("");
      }
    }

    // Populate member dropdowns
    const memberOptions = this.currentMembers.map(m =>
      `<option value="${m.user_id}">${m.full_name || m.email}</option>`
    ).join("");

    const payerSel = document.getElementById("lSettlePayerSelect");
    const receiverSel = document.getElementById("lSettleReceiverSelect");
    if (payerSel) payerSel.innerHTML = memberOptions;
    if (receiverSel) receiverSel.innerHTML = memberOptions;

    // Default payer = me
    const myId = this.getMyUserId();
    if (payerSel) payerSel.value = myId;

    const dateEl = document.getElementById("lSettleDateInput");
    if (dateEl) dateEl.value = this.todayStr();
    const amtEl = document.getElementById("lSettleAmountInput");
    if (amtEl) amtEl.value = "";
    const notesEl = document.getElementById("lSettleNotesInput");
    if (notesEl) notesEl.value = "";

    this.openSheet("lSettleUpOverlay");
  },

  prefillSettlement(fromId, toId, amount) {
    const payerSel = document.getElementById("lSettlePayerSelect");
    const receiverSel = document.getElementById("lSettleReceiverSelect");
    const amtEl = document.getElementById("lSettleAmountInput");
    if (payerSel) payerSel.value = fromId;
    if (receiverSel) receiverSel.value = toId;
    if (amtEl) amtEl.value = parseFloat(amount).toFixed(2);
  },

  async recordSettlement() {
    const payerId = parseInt((document.getElementById("lSettlePayerSelect") || {}).value);
    const receiverId = parseInt((document.getElementById("lSettleReceiverSelect") || {}).value);
    const amount = parseFloat((document.getElementById("lSettleAmountInput") || {}).value) || 0;
    const date = (document.getElementById("lSettleDateInput") || {}).value;
    const notes = (document.getElementById("lSettleNotesInput") || {}).value?.trim() || null;

    if (!amount || amount <= 0) { this.toast("Enter a valid amount", "error"); return; }
    if (payerId === receiverId) { this.toast("Payer and receiver must be different", "error"); return; }

    try {
      await window.APP_API.createGroupSettlement(this.currentGroupId, {
        payer_id: payerId,
        receiver_id: receiverId,
        amount,
        date,
        notes,
      });
      this.closeGroupSheet("lSettleUpOverlay");
      this.toast("Payment recorded!");
      await this.openGroupDetail(this.currentGroupId);
    } catch (err) {
      this.toast(err.message || "Failed to record settlement", "error");
    }
  },

  async deleteSettlement(settlementId) {
    if (!confirm("Reverse this settlement payment?")) return;
    try {
      await window.APP_API.deleteGroupSettlement(this.currentGroupId, settlementId);
      this.toast("Settlement reversed.");
      await this.openGroupDetail(this.currentGroupId);
    } catch (err) {
      this.toast(err.message || "Failed to reverse settlement", "error");
    }
  },
};
