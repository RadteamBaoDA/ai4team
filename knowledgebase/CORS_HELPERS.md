Knowledgebase CORS helpers

This folder contains helper scripts and documentation for generating a safe CORS `map` block inside `kb.conf` at deploy time.

Files
- `kb.conf` — Nginx server configuration. The CORS map block is marked with `# CORS-MAP-START` / `# CORS-MAP-END` and is intended to be updated by the generator scripts.
- `generate_kb_cors.sh` — Bash script that reads `ALLOW_CORG_ORIGIN` (comma-separated origins) and `CORS_ALLOW_CUSTM_SCHEME` (semicolon-separated custom schemes) and rewrites `kb.conf` in-place.
- `generate_kb_cors.ps1` — PowerShell equivalent for Windows environments.

Environment variables
- `ALLOW_CORG_ORIGIN` (comma-separated)
  - Example: `https://knowledgebase.ai4team.vn,https://app.example.com,http://localhost:3000`
  - These are the origins (including scheme) that will be allowed via CORS.

- `CORS_ALLOW_CUSTM_SCHEME` (semicolon-separated) — optional
  - Example: `app;file;electron;my-custom-scheme`
  - When present the generator will add map entries that match the custom-scheme origins like `app://`, `file://`, etc. The config includes a toggle `CORS_ALLOW_CUSTOM_SCHEME` which you should set to `1` in the deployed `kb.conf` only if you intend to allow these schemes.
  - WARNING: custom-scheme origins widen the allowed origin surface; only enable if you trust the clients.

Usage examples

Bash (Linux server or CI job):

```bash
# from d:/Project/ai4team/knowledgebase or provide absolute path to kb.conf
export ALLOW_CORG_ORIGIN="https://knowledgebase.ai4team.vn,https://app.example.com,http://localhost:3000"
export CORS_ALLOW_CUSTM_SCHEME="app;file;electron;my-custom-scheme"
./generate_kb_cors.sh ./kb.conf

# test nginx config and reload (on the server where nginx is running)
sudo nginx -t && sudo systemctl reload nginx
```

PowerShell (Windows server or CI job):

```powershell
$env:ALLOW_CORG_ORIGIN = "https://knowledgebase.ai4team.vn,https://app.example.com,http://localhost:3000"
$env:CORS_ALLOW_CUSTM_SCHEME = "app;file;electron;my-custom-scheme"
.\generate_kb_cors.ps1 -KbConf .\kb.conf

# test nginx config and reload on the server (adapt for your host)
nginx -t
# then reload/restart nginx as appropriate for your system
```

CI example (GitHub Actions)

This example creates `kb.conf.generated` artifact for review; in your real pipeline you would push the generated file to the host or build an image.

```yaml
name: Generate KB CORS
on: [workflow_dispatch]
jobs:
  generate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Generate kb.conf
        env:
          ALLOW_CORG_ORIGIN: ${{ secrets.ALLOW_CORG_ORIGIN }}
          CORS_ALLOW_CUSTM_SCHEME: ${{ secrets.CORS_ALLOW_CUSTM_SCHEME }}
        run: |
          cd knowledgebase
          ./generate_kb_cors.sh kb.conf
      - name: Upload generated config
        uses: actions/upload-artifact@v4
        with:
          name: kb-conf-generated
          path: knowledgebase/kb.conf
```

Security notes
- Keep your origin allowlists in secrets or your deployment system rather than committed in version control.
- Do not enable `CORS_ALLOW_CUSTOM_SCHEME` unless required and trusted.

Next steps (optional)
- Write the generated config to a separate preview file (`kb.conf.generated`) instead of replacing in-place.
- Add a simple unit test harness for the generator scripts.
- Add a CI job that validates `nginx -t` on the generated config inside a container.
