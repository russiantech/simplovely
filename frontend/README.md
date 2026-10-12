# SimplyLovely web (Flask, server-rendered shell)

Serves HTML only; all data is fetched from the API in the browser.

```bash
pip install -r requirements.txt
cp .env.example .env
APP_ENV=development python app.py          # http://localhost:5002  (API expected on :5001)
pytest tests && node tests/base_config.test.js
```

The API URL is decided **once**, on the server (`web/__init__.py: api_base_for_host`) and injected as
`window.APP_CONFIG.API_BASE` by `templates/incs/metas.html`. Set `API_BASE_URL` to override it.
`simplylovely.ng`, `www.` and any subdomain use the production API; `localhost`/`127.0.0.1` use port 5001.
