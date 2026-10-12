# SimplyLovely API (Flask)

```bash
python -m venv env && source env/bin/activate
pip install -r requirements.txt
cp .env.example .env            # fill in values
flask --app app create-admin    # first admin (also seeds roles, services, areas)
flask --app app seed            # idempotent reference data
APP_ENV=development python app.py
pytest                          # test suite
```

* Health check: `GET /api/health`
* Paystack webhook (set in the Paystack dashboard): `POST {API_PUBLIC_URL}/api/payment/webhook/paystack`
* Google OAuth redirect URI (Cloud Console → Credentials → Web client): `{API_PUBLIC_URL}/api/users/callback/google`
* `.env` is searched in the project root and `web/`; real environment variables always take precedence.
