/* ==========================================================================
   THE LEDGER — MAIN APPLICATION BOOTSTRAPPER
   ========================================================================== */
window.addEventListener("DOMContentLoaded", async () => {
  // 1. Auth Guard: Ensure user is signed in so all data permanently saves to PostgreSQL
  if (!window.APP_API.isAuthenticated() && !window.location.pathname.endsWith("auth.html")) {
    console.log("[App] No active session found. Redirecting to login...");
    window.location.replace("auth.html");
    return;
  }

  // 2. Sync live database data & state
  await window.APP_STATE.init();

  // 3. Sync logged-in user profile if token is available
  if (window.APP_API.isAuthenticated()) {
    try {
      const user = await window.APP_API.getMe();
      if (user && user.full_name) {
        window.APP_STATE.updateProfile(user.full_name, "Enterprise Account", user.email);
        window.APP_STATE.data.userId = user.id;
        localStorage.setItem(window.APP_API.USER_KEY, JSON.stringify(user));
      }
    } catch (e) {
      console.warn("[App] Auth profile sync skipped:", e.message);
    }
  }

  // 3. Determine and initialize active controller
  if (document.querySelector(".desktop-workspace")) {
    window.APP_DESKTOP.init();
  } else if (document.querySelector(".ledger-shell")) {
    window.APP_MOBILE.init();
    // Initialize Groups module (non-blocking)
    if (window.APP_GROUPS) {
      // Store the current user's ID in state for balance lookups
      try {
        const storedUser = localStorage.getItem(window.APP_API.USER_KEY);
        if (storedUser) {
          const parsed = JSON.parse(storedUser);
          window.APP_STATE.data.userId = parsed.id;
        }
      } catch (_) {}
      window.APP_GROUPS.init().catch(e => console.warn("[Groups] Init error:", e));
    }
  }

  // 4. Attempt async backend handshake + in-app update check
  try {
    const health = await window.APP_API.getHealth();
    if (health) {
      console.log("[App] Backend connected:", health);
    }
  } catch (e) {
    console.log("[App] Working in offline/local storage mode");
  }

  if (window.APP_UPDATER) {
    window.APP_UPDATER.check();
  }
});
