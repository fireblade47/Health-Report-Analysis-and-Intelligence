# HTML Blood Work Analyzer

This is a browser-based version of `../blood_work_analysis.ipynb`. The page is
plain HTML, CSS, and JavaScript; `app.py` is a small local server that keeps LLM
API keys on your machine and exposes the analysis endpoint.

## Run it

Add one provider key to the project-root `.env` file:

```env
GROQ_API_KEY=your_key
# or
GOOGLE_API_KEY=your_key
```

Then run, from the repository root:

```bash
uv run python 2_health_analysis/html_app/app.py
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in a browser; do not double-click
`index.html`, since it needs the local Python server for analysis. Press `Ctrl+C` in the
terminal to stop the server.

The application is educational only and is not medical advice.
