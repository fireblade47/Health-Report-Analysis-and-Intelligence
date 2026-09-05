const report = document.querySelector("#report");
const fileInput = document.querySelector("#report-file");
const provider = document.querySelector("#provider");
const model = document.querySelector("#model");
const analyzeButton = document.querySelector("#analyze");
const status = document.querySelector("#status");
const results = document.querySelector("#results");

const defaultModels = { groq: "qwen/qwen3.8-27b", gemini: "gemini-2.5-flash" };

if (window.location.protocol === "file:") {
  showStatus(
    "This page must be opened through the local app server. Run `uv run python 2_health_analysis/html_app/app.py`, then open http://127.0.0.1:8000.",
    true,
  );
  analyzeButton.disabled = true;
}

provider.addEventListener("change", () => { model.value = defaultModels[provider.value]; });

fileInput.addEventListener("change", async () => {
  const [file] = fileInput.files;
  if (!file) return;
  try {
    report.value = await file.text();
    showStatus(`Loaded ${file.name}.`, false);
  } catch {
    showStatus("Could not read that file. Please use a UTF-8 .txt report.", true);
  }
});

analyzeButton.addEventListener("click", async () => {
  if (!report.value.trim()) return showStatus("Paste or upload a blood report before analysing it.", true);
  if (!model.value.trim()) return showStatus("Enter a model name.", true);

  analyzeButton.disabled = true;
  showStatus("Extracting test values and preparing the diet summary…", false);
  results.hidden = true;
  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ report: report.value, provider: provider.value, model: model.value }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Analysis could not be completed.");
    renderMarkdown(document.querySelector("#test-results"), data.extracted_values);
    renderMarkdown(document.querySelector("#diet-plan"), data.diet_plan);
    results.hidden = false;
    showStatus("Analysis complete.", false);
  } catch (error) {
    showStatus(error.message || "Analysis could not be completed.", true);
  } finally {
    analyzeButton.disabled = false;
  }
});

function showStatus(message, isError) {
  status.textContent = message;
  status.classList.toggle("error", isError);
}

function escapeHtml(value) {
  return value.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

function renderMarkdown(element, markdown) {
  // Minimal renderer: escapes all model output before adding a small safe Markdown subset.
  const lines = markdown.replaceAll("\r", "").split("\n");
  let html = "";
  let listOpen = false;
  for (let index = 0; index < lines.length; index += 1) {
    const line = escapeHtml(lines[index]);
    const next = lines[index + 1] || "";
    if (/^\|.*\|$/.test(line) && /^\|\s*:?-+/.test(next)) {
      const headers = line.split("|").slice(1, -1).map(cell => `<th>${cell.trim()}</th>`).join("");
      const rows = [];
      index += 2;
      while (index < lines.length && /^\|.*\|$/.test(lines[index])) {
        rows.push(`<tr>${lines[index].split("|").slice(1, -1).map(cell => `<td>${escapeHtml(cell.trim())}</td>`).join("")}</tr>`);
        index += 1;
      }
      index -= 1;
      html += `<table><thead><tr>${headers}</tr></thead><tbody>${rows.join("")}</tbody></table>`;
    } else if (line.startsWith("## ")) {
      html += `<h2>${line.slice(3)}</h2>`;
    } else if (/^[-*] /.test(line)) {
      if (!listOpen) { html += "<ul>"; listOpen = true; }
      html += `<li>${line.slice(2)}</li>`;
    } else {
      if (listOpen) { html += "</ul>"; listOpen = false; }
      if (line.trim()) html += `<p>${line}</p>`;
    }
  }
  if (listOpen) html += "</ul>";
  element.innerHTML = html;
}
