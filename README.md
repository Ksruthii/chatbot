



# EmbedBot SaaS

A production-ready MVP SaaS app built with Flask, SQLite, vanilla HTML/CSS/JS, and Hugging Face Inference API. Users can sign up, create FAQ-backed chatbots, preview them in a dashboard, and embed them into any website with a single script tag.

## Features

- Session-based signup/login with hashed passwords
- Protected dashboard
- Create and manage chatbots
- FAQ-first response engine with AI fallback
- Live preview panel in dashboard
- Embeddable floating chatbot widget
- SQLite schema ready for easy upgrade later
- Usage tracking with chat counters
- Free-plan limit hook and upgrade CTA

## Project Structure

- `app.py` - Flask app, routes, DB setup, AI chat logic
- `templates/` - Landing, auth, dashboard pages
- `static/css/styles.css` - Shared UI styling
- `static/js/app.js` - Dashboard logic
- `static/js/chatbot.js` - Embeddable widget
- `instance/app.db` - SQLite database file

## Local Setup

1. Create a virtual environment:
   - `python -m venv .venv`
   - `source .venv/bin/activate` on macOS/Linux or `.venv\\\\Scripts\\\\activate` on Windows
2. Install dependencies:
   - `pip install -r requirements.txt`
3. Set environment variables:
   - `export SECRET_KEY="replace-this"`
   - `export HUGGINGFACE_API_TOKEN="your_token"`
   - `export BASE_URL="http://localhost:5000"`
4. Initialize the database:
   - `flask --app app init-db`
5. Run the app:
   - `flask --app app run --debug`
6. Open `http://localhost:5000`

## Deployment on Render

1. Push the project to GitHub.
2. Create a new Render Web Service.
3. Connect the repository.
4. Use the included `render.yaml` or configure manually:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:app`
5. Add environment variables:
   - `SECRET_KEY`
   - `HUGGINGFACE_API_TOKEN`
   - `HUGGINGFACE_API_URL`
   - `BASE_URL`
   - `MAX_FREE_BOTS`
6. Redeploy and verify the embed script URL uses your deployed domain.

## Embed Script

Add this to any website:

```html
<script src="https://yourdomain.com/static/js/chatbot.js" data-id="CHATBOT_ID"></script>
```

The script injects a floating launcher, opens a chat panel, fetches bot info, and posts user messages to `/chat`.

## Notes for Production

- Replace SQLite with PostgreSQL for multi-instance deployments.
- Use CSRF protection such as Flask-WTF for hardened auth forms.
- Add rate limiting, audit logs, email verification, and billing later.
- Store secrets in Render environment variables only.

