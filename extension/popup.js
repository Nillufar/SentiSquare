document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('importBtn');
  btn.addEventListener('click', async () => {
    try {
      const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
      const current = tabs[0];
      if (!current || !current.url) {
        alert('No active tab URL available');
        return;
      }

      const pageUrl = current.url;
      // Copy the URL to the clipboard immediately
      try {
        await navigator.clipboard.writeText(pageUrl);
      } catch (e) {
        // clipboard write can fail if permissions are restricted; ignore
      }
      // Open the SentiSquare import page in a new tab
      const importPage = 'http://localhost:8000/import/';
      const created = await chrome.tabs.create({ url: importPage });
      const tabId = created.id;

  // Try to inject the URL into the import form after the page loads.
      // We'll retry a few times in case the page is still loading.
      let attempts = 0;
      const maxAttempts = 12;

      const tryInject = async () => {
        try {
          await chrome.scripting.executeScript({
            target: { tabId },
            func: (url) => {
              try {
                const el = document.getElementById('url');
                if (el) {
                  el.value = url;
                  el.focus();
                }
                return true;
              } catch (e) {
                return false;
              }
            },
            args: [pageUrl]
          });
          // close the popup after successful injection
          window.close();
        } catch (e) {
          attempts++;
          if (attempts < maxAttempts) {
            setTimeout(tryInject, 500);
          } else {
            alert('Could not inject into the import page. Make sure SentiSquare is running at http://localhost:8000 and that the import page is reachable.');
          }
        }
      };

      setTimeout(tryInject, 500);
    } catch (err) {
      alert('Error: ' + err.message);
    }
  });
});
