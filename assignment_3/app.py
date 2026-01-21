from flask import Flask, request, jsonify, session
import sqlite3
from flask_cors import CORS
import hashlib

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to something more secure!
CORS(app)

# -- Database setup --
def get_db_connection():
    conn = sqlite3.connect('todo.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    with conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                description TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
    conn.close()

init_db()

# -- Auth routes --
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data['username']
    password = hash_password(data['password'])
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, password))
        return jsonify({'status': 'registered'})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Username already exists'}), 400
    finally:
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data['username']
    password = hash_password(data['password'])
    conn = get_db_connection()
    user = conn.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?", (username, password)).fetchone()
    conn.close()
    if user:
        session['user_id'] = user['id']
        return jsonify({'status': 'logged_in'})
    else:
        return jsonify({'error': 'Invalid credentials'}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return jsonify({'status': 'logged_out'})

# -- Task routes (protected) --
def require_login(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Not logged in'}), 403
        return func(*args, **kwargs)
    return wrapper

@app.route('/tasks', methods=['GET'])
@require_login
def get_tasks():
    user_id = session['user_id']
    conn = get_db_connection()
    tasks = conn.execute("SELECT * FROM tasks WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()
    return jsonify([dict(task) for task in tasks])

@app.route('/tasks', methods=['POST'])
@require_login
def add_task():
    user_id = session['user_id']
    data = request.json
    description = data['description']
    conn = get_db_connection()
    with conn:
        conn.execute("INSERT INTO tasks (user_id, description) VALUES (?, ?)", (user_id, description))
    conn.close()
    return jsonify({'status': 'task_added'})

@app.route('/tasks/<int:task_id>', methods=['DELETE'])
@require_login
def delete_task(task_id):
    user_id = session['user_id']
    conn = get_db_connection()
    with conn:
        conn.execute("DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id))
    conn.close()
    return jsonify({'status': 'task_deleted'})

@app.route('/tasks/<int:task_id>', methods=['PATCH'])
@require_login
def update_task(task_id):
    user_id = session['user_id']
    data = request.json
    completed = data['completed']
    conn = get_db_connection()
    with conn:
        conn.execute("UPDATE tasks SET completed = ? WHERE id = ? AND user_id = ?", (completed, task_id, user_id))
    conn.close()
    return jsonify({'status': 'task_updated'})

if __name__ == '__main__':
    app.run(debug=True)