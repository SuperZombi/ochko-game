from flask import Flask, render_template, request, redirect, abort, jsonify, make_response
from flask_cors import CORS
from flask_socketio import SocketIO, emit, ConnectionRefusedError
import hashlib
import time
import re
from tools import *

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
CORS(app)
socketio = SocketIO(app)
User.CONTEXT = app.app_context()

DB = Database('database/users.db')
DB.execute('''
	CREATE TABLE IF NOT EXISTS "users" (
		"id"                  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
		"name"                TEXT NOT NULL,
		"password"            TEXT NOT NULL
	);
''', commit=True)


@app.route('/')
def index():
	username = request.cookies.get("username")
	password = request.cookies.get('password')
	if not username or not password:
		return redirect("/login")

	return render_template('index.html', username=username)


@app.route('/register', methods=['POST'])
def register_user():
	username = request.json.get('username')
	password = request.json.get('password')

	if not username or not password:
		return jsonify({'successfully': False, 'reason': 'Both username and password are required'})

	existing_user = DB.execute('SELECT * FROM users WHERE name = ?', (username,)).fetchone()
	
	if existing_user:
		return jsonify({'successfully': False, 'target': "username", 'reason': 'Username already exists'})

	hashed_password = hashlib.md5(password.encode('utf-8')).hexdigest()

	DB.execute('INSERT INTO users (name, password) VALUES (?, ?)', (username, hashed_password), commit=True)
	
	resp = make_response(jsonify({'successfully': True}))
	resp.set_cookie('username', username)
	resp.set_cookie('password', hashed_password)
	return resp

	
@app.route('/login', methods=['GET'])
def login_html():
	return render_template("login.html")

@app.route('/login', methods=['POST'])
def login():
	username = request.json.get('username')
	password = request.json.get('password')

	if not username or not password:
		return jsonify({'successfully': False, 'reason': 'Both username and password are required'})

	hashed_password = hashlib.md5(password.encode('utf-8')).hexdigest()

	result = DB.execute('SELECT * FROM users WHERE name = ? AND password = ?', (username, hashed_password))
	user = result.fetchone()
	if user:
		column_names = [column[0] for column in result.description]
		user_info = dict(zip(column_names, user))

		resp = make_response(jsonify({'successfully': True}))
		resp.set_cookie('username', user_info.get("name"))
		resp.set_cookie('password', user_info.get("password"))
		return resp
	else:
		return jsonify({'successfully': False, 'reason': 'Invalid username or password'})


@socketio.on('connect')
def search_game():
	username = request.cookies.get("username")
	password = request.cookies.get('password')

	if not username or not password:
		raise ConnectionRefusedError('Unauthorized!')

	user = User(username, request.sid)

	if len(Room.QUEUE) == 0:
		room_id = hashlib.md5(str(int(time.time())).encode('utf-8')).hexdigest()
		room = Room(room_id)
		room.add(user)
		Room.QUEUE[room_id] = room
	else:
		room_id = list(Room.QUEUE.keys())[0]
		room = Room.QUEUE[room_id]
		room.add(user)

	emit("connected", room_id, room=request.sid)


@socketio.on('leave_queue')
def leave_queue(room_id):
	room = Room.QUEUE[room_id]
	if room:
		room.remove(lambda user: user.id != request.sid)

if __name__ == '__main__':
	socketio.run(app, debug=True)
	# print("Running...")
	# socketio.run(app, host='0.0.0.0', port=80)
