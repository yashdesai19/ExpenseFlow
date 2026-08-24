/* ==========================================================================
   THE LEDGER — UTILITY FUNCTIONS & HELPERS
   ========================================================================== */
window.APP_UTILS = {
  /**
   * Formats a monetary amount into Indian standard format (₹8,42,650)
   */
  formatMoney: function(amount, symbol = "₹") {
    const n = Math.abs(Number(amount) || 0);
    return symbol + n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  },

  getCategoryIcon: function(icon, name = "") {
    const iconMap = {
      "utensils": "🍽️",
      "food": "🍽️",
      "dining": "🍽️",
      "meals": "🍽️",
      "car": "🚗",
      "transportation": "🚗",
      "travel": "✈️",
      "fuel": "⛽",
      "home": "🏠",
      "housing": "🏠",
      "rent": "🏢",
      "coworking": "🏢",
      "bolt": "⚡",
      "utilities": "⚡",
      "bills": "⚡",
      "film": "🎬",
      "entertainment": "🎬",
      "heart-pulse": "🩺",
      "healthcare": "🩺",
      "health": "🩺",
      "medical": "🏥",
      "shopping-bag": "🛍️",
      "shopping": "🛍️",
      "wallet": "💰",
      "income": "💰",
      "salary": "💰",
      "software": "☁️",
      "cloud": "☁️",
      "saas": "☁️",
      "payroll": "👥",
      "briefcase": "💼",
      "equipment": "📦",
      "hardware": "💻",
      "education": "🎓",
      "fitness": "🏋️",
      "coffee": "☕",
      "gaming": "🎮",
      "game": "🎮",
      "diamond": "💎"
    };

    if (!icon) return "📦";
    const str = String(icon).trim();
    if (str.length <= 4 && /\p{Extended_Pictographic}/u.test(str)) {
      return str;
    }

    const key = str.toLowerCase();
    if (iconMap[key]) return iconMap[key];

    const nameKey = String(name).toLowerCase();
    for (const k in iconMap) {
      if (nameKey.includes(k)) return iconMap[k];
    }
    return "📦";
  },

  /**
   * Shows a floating toast notification
   */
  showToast: function(message, duration = 2200) {
    let toastEl = document.getElementById("lToast");
    if (!toastEl) {
      toastEl = document.createElement("div");
      toastEl.id = "lToast";
      toastEl.className = "l-toast";
      document.body.appendChild(toastEl);
    }
    toastEl.textContent = message;
    toastEl.classList.add("show");
    setTimeout(() => toastEl.classList.remove("show"), duration);
  },

  /**
   * Downloads a CSV string as a file
   */
  downloadCSV: function(filename, rows) {
    const csvContent = rows.map(r => r.map(cell => {
      const str = String(cell == null ? "" : cell);
      return str.includes(",") || str.includes('"') || str.includes("\n") ? `"${str.replace(/"/g, '""')}"` : str;
    }).join(",")).join("\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
    this.showToast("CSV Export downloaded");
  },

  /**
   * Generates dynamic SVG line and area paths from transactions.
   * If transactions are empty or zero, returns a clean flat horizontal line!
   */
  generateSparklinePaths: function(transactions, width = 300, height = 80, padding = 15) {
    const baselineY = height - padding;
    if (!transactions || transactions.length === 0) {
      return {
        isZero: true,
        linePath: `M ${padding} ${baselineY} L ${width - padding} ${baselineY}`,
        areaPath: `M ${padding} ${baselineY} L ${width - padding} ${baselineY} L ${width - padding} ${height} L ${padding} ${height} Z`,
        points: [{ x: padding, y: baselineY }, { x: width - padding, y: baselineY }]
      };
    }

    // Sort transactions oldest to newest
    const sorted = [...transactions].sort((a, b) => new Date(a.date) - new Date(b.date));
    
    // Calculate running balance series
    let running = 0;
    const series = [{ date: sorted[0].date, balance: 0 }];
    sorted.forEach(t => {
      running += (t.type === "income" ? t.amount : -t.amount);
      series.push({ date: t.date, balance: running });
    });

    const balances = series.map(s => s.balance);
    const min = Math.min(...balances);
    const max = Math.max(...balances);
    
    if (min === max && min === 0) {
      return {
        isZero: true,
        linePath: `M ${padding} ${baselineY} L ${width - padding} ${baselineY}`,
        areaPath: `M ${padding} ${baselineY} L ${width - padding} ${baselineY} L ${width - padding} ${height} L ${padding} ${height} Z`,
        points: [{ x: padding, y: baselineY }, { x: width - padding, y: baselineY }]
      };
    }

    const range = (max - min) || 1;
    const innerW = width - (padding * 2);
    const innerH = height - (padding * 2);

    const points = series.map((s, i) => {
      const x = padding + (i / (series.length - 1)) * innerW;
      const y = (height - padding) - ((s.balance - min) / range) * innerH;
      return { x: Math.round(x * 10) / 10, y: Math.round(y * 10) / 10, balance: s.balance };
    });

    const linePath = points.map((p, i) => (i === 0 ? `M ${p.x} ${p.y}` : `L ${p.x} ${p.y}`)).join(" ");
    const lastX = points[points.length - 1].x;
    const firstX = points[0].x;
    const bottomY = height;
    const areaPath = `${linePath} L ${lastX} ${bottomY} L ${firstX} ${bottomY} Z`;

    return {
      isZero: false,
      linePath,
      areaPath,
      points
    };
  },

  /**
   * Returns Year-Month key "YYYY-MM" from date string (or current month if invalid)
   */
  getMonthKey: function(dateStr) {
    if (!dateStr) {
      const now = new Date();
      return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    }
    const str = String(dateStr).slice(0, 7);
    return /^\d{4}-\d{2}$/.test(str) ? str : this.getMonthKey(null);
  },

  /**
   * Formats "YYYY-MM" into readable "August 2026"
   */
  formatMonthName: function(yearMonthStr) {
    if (!yearMonthStr || yearMonthStr === "all") return "All Time";
    const [year, month] = yearMonthStr.split("-").map(Number);
    if (!year || !month) return yearMonthStr;
    const d = new Date(year, month - 1, 1);
    return d.toLocaleDateString("en-US", { month: "long", year: "numeric" });
  },

  /**
   * Shifts a "YYYY-MM" key by delta months (+1 or -1)
   */
  shiftMonth: function(yearMonthStr, delta = 0) {
    const current = this.getMonthKey(yearMonthStr);
    const [year, month] = current.split("-").map(Number);
    const d = new Date(year, month - 1 + delta, 1);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
  },

  /**
   * Computes distinct months from transactions list with financial summaries
   */
  getDistinctMonths: function(transactions = []) {
    const nowKey = this.getMonthKey(null);
    const map = {};

    // Ensure current month is always present
    map[nowKey] = { key: nowKey, label: this.formatMonthName(nowKey), inTotal: 0, outTotal: 0, count: 0 };

    transactions.forEach(t => {
      const k = this.getMonthKey(t.date);
      if (!map[k]) {
        map[k] = { key: k, label: this.formatMonthName(k), inTotal: 0, outTotal: 0, count: 0 };
      }
      map[k].count++;
      if (t.type === "income") {
        map[k].inTotal += Number(t.amount) || 0;
      } else {
        map[k].outTotal += Number(t.amount) || 0;
      }
    });

    return Object.values(map).sort((a, b) => b.key.localeCompare(a.key));
  }
};
