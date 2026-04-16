
import os
import re
import json
import sqlite3
from math import log
from difflib import SequenceMatcher
from functools import wraps
from datetime import datetime

import requests
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, g, flash
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, 'instance', 'app.db')
HUGGINGFACE_API_URL = os.environ.get('HUGGINGFACE_API_URL', 'https://api-inference.huggingface.co/models/google/flan-t5-base')
HUGGINGFACE_API_TOKEN = os.environ.get('HUGGINGFACE_API_TOKEN', '')
MAX_FREE_BOTS = int(os.environ.get('MAX_FREE_BOTS', '1'))
MAX_FAQ_ENTRIES = int(os.environ.get('MAX_FAQ_ENTRIES', '50'))

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-me-in-production')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('FLASK_ENV') == 'production'


def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    os.makedirs(os.path.join(BASE_DIR, 'instance'), exist_ok=True)
    db = sqlite3.connect(DATABASE)
    db.executescript(
        '''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS chatbots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            business_name TEXT NOT NULL,
            faq_data TEXT NOT NULL,
            chat_count INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        );
        '''
    )
    db.commit()
    db.close()


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get('user_id'):
            return redirect(url_for('login_page'))
        return view_func(*args, **kwargs)
    return wrapped


def current_user():
    user_id = session.get('user_id')
    if not user_id:
        return None
    return get_db().execute('SELECT id, email FROM users WHERE id = ?', (user_id,)).fetchone()


def normalize_text(text):
    return re.sub(r'[^a-z0-9\s]', ' ', text.lower()).strip()


def tokenize(text):
    return [t for t in normalize_text(text).split() if len(t) > 1]


def keyword_similarity(message, question, answer):
    msg_tokens = set(tokenize(message))
    faq_tokens = set(tokenize(question + ' ' + answer))
    if not msg_tokens or not faq_tokens:
        return 0.0
    overlap = len(msg_tokens & faq_tokens) / max(len(msg_tokens), 1)
    ratio = SequenceMatcher(None, normalize_text(message), normalize_text(question)).ratio()
    return (overlap * 0.7) + (ratio * 0.3)


def faq_match(message, faq_items):
    best_item = None
    best_score = 0.0
    for item in faq_items:
        score = keyword_similarity(message, item.get('question', ''), item.get('answer', ''))
        if score > best_score:
            best_score = score
            best_item = item
    return best_item, best_score


def ask_huggingface(business_name, faq_items, message):
    faq_context = '\n'.join([f"Q: {f.get('question','')}\nA: {f.get('answer','')}" for f in faq_items[:10]])
    prompt = (
        f"You are a helpful support chatbot for {business_name}. "
        f"Answer clearly and concisely using the business context and FAQs when relevant. "
        f"If the answer is uncertain, say so politely and suggest contacting the business.\n\n"
        f"FAQs:\n{faq_context}\n\n"
        f"User question: {message}\nAnswer:"
    )

    if not HUGGINGFACE_API_TOKEN:
        return "I couldn't find an exact FAQ match. Please add a Hugging Face API token to enable AI fallback responses."

    headers = {
        'Authorization': f'Bearer {HUGGINGFACE_API_TOKEN}',
        'Content-Type': 'application/json'
    }
    payload = {
        'inputs': prompt,
        'parameters': {
            'max_new_tokens': 120,
            'temperature': 0.4,
            'return_full_text': False
        }
    }

    try:
        response = requests.post(HUGGINGFACE_API_URL, headers=headers, json=payload, timeout=20)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, list) and data and 'generated_text' in data[0]:
            return data[0]['generated_text'].strip()
        if isinstance(data, dict) and data.get('generated_text'):
            return data['generated_text'].strip()
        return "I don't have a confident answer right now. Please contact the business for more details."
    except requests.RequestException:
        return "I couldn't reach the AI service right now. Please try again in a moment."


def serialize_bot(row):
    faq_data = json.loads(row['faq_data']) if row['faq_data'] else []
    return {
        'id': row['id'],
        'name': row['name'],
        'business_name': row['business_name'],
        'faq_data': faq_data,
        'chat_count': row['chat_count'],
        'created_at': row['created_at'],
        'embed_code': f'<script src="{{{{BASE_URL}}}}/static/js/chatbot.js" data-id="{row["id"]}"></script>'
    }


@app.context_processor
def inject_globals():
    return {
        'app_name': 'EmbedBot',
        'base_url': os.environ.get('BASE_URL', 'http://localhost:5000')
    }


@app.route('/')
def index():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    return render_template('index.html')


@app.get('/signup')
def signup_page():
    return render_template('signup.html')


@app.post('/signup')
def signup():
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    if not email or not password:
        flash('Email and password are required.', 'error')
        return redirect(url_for('signup_page'))
    if len(password) < 8:
        flash('Password must be at least 8 characters.', 'error')
        return redirect(url_for('signup_page'))

    db = get_db()
    existing = db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone()
    if existing:
        flash('An account with that email already exists.', 'error')
        return redirect(url_for('signup_page'))

    password_hash = generate_password_hash(password)
    cursor = db.execute('INSERT INTO users (email, password_hash) VALUES (?, ?)', (email, password_hash))
    db.commit()
    session['user_id'] = cursor.lastrowid
    session['user_email'] = email
    return redirect(url_for('dashboard'))


@app.get('/login')
def login_page():
    return render_template('login.html')


@app.post('/login')
def login():
    email = request.form.get('email', '').strip().lower()
    password = request.form.get('password', '')
    user = get_db().execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
    if not user or not check_password_hash(user['password_hash'], password):
        flash('Invalid email or password.', 'error')
        return redirect(url_for('login_page'))

    session['user_id'] = user['id']
    session['user_email'] = user['email']
    return redirect(url_for('dashboard'))


@app.get('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


@app.get('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', user=current_user())


@app.get('/get-bots')
@login_required
def get_bots():
    rows = get_db().execute(
        'SELECT * FROM chatbots WHERE user_id = ? ORDER BY created_at DESC',
        (session['user_id'],)
    ).fetchall()
    return jsonify({'bots': [serialize_bot(row) for row in rows], 'limit': MAX_FREE_BOTS})


@app.post('/create-bot')
@login_required
def create_bot():
    data = request.get_json(silent=True) or request.form
    name = (data.get('name') or '').strip()
    business_name = (data.get('business_name') or '').strip()
    faq_entries = data.get('faq_entries') or data.get('faq_data') or []

    if isinstance(faq_entries, str):
        try:
            faq_entries = json.loads(faq_entries)
        except json.JSONDecodeError:
            faq_entries = []

    clean_faqs = []
    for entry in faq_entries[:MAX_FAQ_ENTRIES]:
        question = (entry.get('question') or '').strip()
        answer = (entry.get('answer') or '').strip()
        if question and answer:
            clean_faqs.append({'question': question, 'answer': answer})

    if not name or not business_name:
        return jsonify({'error': 'Chatbot name and business name are required.'}), 400

    db = get_db()
    count = db.execute('SELECT COUNT(*) AS total FROM chatbots WHERE user_id = ?', (session['user_id'],)).fetchone()['total']
    if count >= MAX_FREE_BOTS:
        return jsonify({'error': f'Free plan allows up to {MAX_FREE_BOTS} chatbot(s). Upgrade to create more.'}), 403

    cursor = db.execute(
        'INSERT INTO chatbots (user_id, name, business_name, faq_data) VALUES (?, ?, ?, ?)',
        (session['user_id'], name, business_name, json.dumps(clean_faqs))
    )
    db.commit()
    bot = db.execute('SELECT * FROM chatbots WHERE id = ?', (cursor.lastrowid,)).fetchone()
    return jsonify({'bot': serialize_bot(bot)}), 201


@app.get('/api/bot/<int:bot_id>')
def public_bot_config(bot_id):
    row = get_db().execute('SELECT id, name, business_name FROM chatbots WHERE id = ?', (bot_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Bot not found'}), 404
    return jsonify({'id': row['id'], 'name': row['name'], 'business_name': row['business_name']})


@app.post('/chat')
def chat():
    data = request.get_json(silent=True) or {}
    bot_id = data.get('chatbot_id')
    message = (data.get('message') or '').strip()
    if not bot_id or not message:
        return jsonify({'error': 'chatbot_id and message are required'}), 400

    row = get_db().execute('SELECT * FROM chatbots WHERE id = ?', (bot_id,)).fetchone()
    if not row:
        return jsonify({'error': 'Bot not found'}), 404

    faq_items = json.loads(row['faq_data']) if row['faq_data'] else []
    matched, score = faq_match(message, faq_items)
    if matched and score >= 0.35:
        reply = matched['answer']
        source = 'faq'
    else:
        reply = ask_huggingface(row['business_name'], faq_items, message)
        source = 'ai'

    get_db().execute('UPDATE chatbots SET chat_count = chat_count + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?', (bot_id,))
    get_db().commit()
    return jsonify({'reply': reply, 'source': source, 'bot_name': row['name']})


@app.cli.command('init-db')
def init_db_command():
    init_db()
    print('Initialized the database.')


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
