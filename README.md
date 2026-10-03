# JobHuntAI

Scrapes public job boards (Remotive, Arbeitnow) for roles matching your CV, then rewrites your CV and cover letter
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
