/* ==========================================================================
   IN-APP UPDATE CHECK
   Compares this APK's versionCode with /health/app-version from the API.
   ========================================================================== */
window.APP_UPDATER = {
  STORAGE_PREFIX: "expenseflow_dismissed_update_",

  currentCode() {
    const code = window.APP_CONFIG && window.APP_CONFIG.APP_VERSION_CODE;
    return Number.isFinite(Number(code)) ? Number(code) : 1;
  },

  currentName() {
    return (window.APP_CONFIG && window.APP_CONFIG.APP_VERSION) || "1.0.0";
  },

  async check() {
    try {
      const info = window.APP_API && window.APP_API.getAppVersion
        ? await window.APP_API.getAppVersion()
        : null;
      if (!info || !info.version_code) return;
      if (Number(info.version_code) <= this.currentCode()) return;

      const dismissed = localStorage.getItem(this.STORAGE_PREFIX + info.version_code);
      if (dismissed && !info.force_update) return;

      this.show(info);
    } catch (err) {
      console.warn("[Updater] Version check skipped:", err && err.message);
    }
  },

  show(info) {
    this.remove();

    const notes = Array.isArray(info.release_notes)
      ? info.release_notes.filter(Boolean)
      : [];
    const notesHtml = notes.length
      ? `<ul class="app-update-notes">${notes.map((n) => `<li>${this.escape(n)}</li>`).join("")}</ul>`
      : "";
    const laterBtn = info.force_update
      ? ""
      : `<button type="button" class="btn-brass-secondary" id="appUpdateLater">Later</button>`;

    const overlay = document.createElement("div");
    overlay.id = "appUpdateOverlay";
    overlay.className = "app-update-overlay";
    overlay.innerHTML = `
      <div class="app-update-dialog" role="dialog" aria-labelledby="appUpdateTitle">
        <div class="app-update-badge">Update available</div>
        <h2 id="appUpdateTitle">${this.escape(info.release_name || "ExpenseFlow Pro")}</h2>
        <p class="app-update-meta">Version ${this.escape(info.latest_version || "")} is ready. You have ${this.escape(this.currentName())}.</p>
        ${notesHtml}
        <div class="app-update-actions">
          ${laterBtn}
          <button type="button" class="btn-brass-primary" id="appUpdateNow">Update now</button>
        </div>
      </div>
    `;
    document.body.appendChild(overlay);

    const later = overlay.querySelector("#appUpdateLater");
    if (later) {
      later.addEventListener("click", () => {
        localStorage.setItem(this.STORAGE_PREFIX + info.version_code, "1");
        this.remove();
      });
    }

    overlay.querySelector("#appUpdateNow").addEventListener("click", () => {
      this.openDownload(info.apk_url || info.web_url);
    });
  },

  openDownload(url) {
    if (!url) return;
    const opened = window.open(url, "_system");
    if (!opened) {
      window.location.href = url;
    }
  },

  remove() {
    const existing = document.getElementById("appUpdateOverlay");
    if (existing) existing.remove();
  },

  escape(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }
};
