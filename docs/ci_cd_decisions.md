# CI/CD Decisions & Tradeoffs

**Tooling**: *GitHub Actions* for CI/CD and *GHCR* for the container registry.

* Native to GitHub: quick setup, no external server like Jenkins required.
* Permissions via `GITHUB_TOKEN` with `packages: write` avoid PAT management.
* GHCR keeps images near the repo, supports fine-grained visibility.

**Triggers**

* **CI**: on every `push` and `pull_request` — lint + test.
* **CD**: on `push` to `main` and tags `v*` — build & push with `:latest` and `:<git-sha>`.

**Pipeline**

* CI: checkout → Python setup → pip cache → install → lint (ruff) → test (pytest) → upload JUnit.
* CD: checkout → compute image name → detect Dockerfile → build → GHCR login → push → optional webhook.

**Challenges & Mitigations**

* *Secrets*: use repo secrets for `DEPLOY_WEBHOOK_URL`. No PAT needed for GHCR; ensure `packages: write`.
* *Heterogeneous repos*: dynamic detection of Dockerfile/requirements to avoid hardcoding `sample_app/`.
* *Caching*: pip cache speeds up CI.
* *Flaky tests*: fail fast with `--maxfail=1`.
* *Image size*: use `python:3.11-slim` images, pin versions.
