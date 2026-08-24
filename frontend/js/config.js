/* ==========================================================================
   THE LEDGER — CONFIGURATION & CONSTANTS
   ========================================================================== */
window.APP_CONFIG = {
  APP_NAME: "ExpenseFlow Pro",
  APP_EDITION: "The Ledger",
  API_BASE: (() => {
    // On Render, API is served from same origin
    if (window.location.hostname && window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1") {
      return window.location.origin + "/api/v1";
    }
    // Local development
    const host = window.location.hostname || "127.0.0.1";
    if (window.location.origin.includes(":8081")) return window.location.origin + "/api/v1";
    return `http://${host}:8081/api/v1`;
  })(),
  DEFAULT_CURRENCY: "INR",
  DEFAULT_CURRENCY_SYMBOL: "₹",
  STORAGE_KEY: "expenseflow_ledger_store_v5",

  DEFAULT_CATEGORIES: [
    { id: "cat-software", name: "Software & SaaS", icon: "☁️", color: "#7C93B0", budget: 45000 },
    { id: "cat-travel", name: "Travel & Fuel", icon: "✈️", color: "#C9A467", budget: 25000 },
    { id: "cat-food", name: "Meals & Dining", icon: "🍽️", color: "#A98F63", budget: 15000 },
    { id: "cat-rent", name: "Rent & Coworking", icon: "🏢", color: "#9A8C7A", budget: 60000 },
    { id: "cat-payroll", name: "Payroll & Payouts", icon: "👥", color: "#8A7CA6", budget: 150000 },
    { id: "cat-equipment", name: "Equipment & Hardware", icon: "📦", color: "#B08968", budget: 20000 },
    { id: "cat-health", name: "Health & Care", icon: "🩺", color: "#C97B84", budget: 10000 },
    { id: "cat-entertainment", name: "Entertainment", icon: "🎬", color: "#8A7CA6", budget: 8000 },
    { id: "cat-income", name: "Client Retainers", icon: "💰", color: "#5FAE82", budget: 0 },
  ],

  DEFAULT_TRANSACTIONS: []
};
