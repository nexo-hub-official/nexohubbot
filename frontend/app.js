const statusElement = document.getElementById("status");

const loadStatus = async () => {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const payload = await response.json();
    statusElement.textContent = payload.ok ? "Online ✅" : "Offline ❌";
  } catch (_error) {
    statusElement.textContent = "Unavailable ❌";
  }
};

loadStatus();
