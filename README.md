# JobHuntAI

Scrapes public job boards (Remotive, Arbeitnow, The Muse, Jobicy) and company career sites (Microsoft, Google, Greenhouse-hosted companies) for roles matching your CV, then rewrites your CV and cover letter
for each job, keeping the tone of your original cover letter.

```
python -m jobhunt      # then open http://127.0.0.1:8765  (no dependencies, Python 3.9+)
python -m unittest discover -s tests -t .
```

UI: paste/load your CV and original cover letter, enter a location, choose in-person / remote / hybrid, and either
generate optimised documents (with a link to the job page) or "auto-apply", which generates the package, saves it to
`~/.jobhuntai/applications/` and opens the job page. Submitting third-party application forms is not automated.

AI providers: local servers (Ollama, LM Studio, llama.cpp) are auto-detected. Online providers (OpenAI, Claude,
Gemini, Grok, GitHub Copilot/Models) take an API key in the Settings menu, stored in `~/.jobhuntai/settings.json`
(mode 600) and never sent back to the browser. Set `JOBHUNT_HOME` to change the directory.

Country search: if the location is a country or a known city (e.g. `Ireland`, `Dublin`), country-aware sources are
queried for that country and results are filtered to it automatically.

PDF: CV and cover letter can be loaded from `.pdf` files (text-based PDFs; scanned images are not supported) and
generated documents can be downloaded as PDF. Auto-apply also saves `-cv.pdf` and `-cover-letter.pdf` files.

Job log: every search appends new jobs (date found, country, remote/hybrid/local, URL) to `~/.jobhuntai/jobs.csv`.
Shortcut: the "Job log (CSV)" link in the UI (`http://127.0.0.1:8765/jobs.csv`), or `python -m jobhunt --jobs-csv` to print the file path.
