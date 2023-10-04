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
		"password"            TEXT NOT NULL,
		"room_id"             INTEGER
	);
''', commit=True)


@app.route('/')
def index():
	username = request.cookies.get("username")
	password = request.cookies.get('password')
	if not username or not password:
		return redirect("/login")

	user_info = get_user(DB, {"name": username})
	return render_template('index.html', username=user_info["name"])


@app.route('/register', methods=['POST'])
def register_user():
	username = request.json.get('username')
	password = request.json.get('password')

	if not username or not password:
		return jsonify({'successfully': False, 'reason': 'Both username and password are required'})

	existing_user = get_user(DB, {"name": username})
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

	user = get_user(DB, {"name": username, "password": hashed_password})
	if user:
		resp = make_response(jsonify({'successfully': True}))
		resp.set_cookie('username', username)
		resp.set_cookie('password', hashed_password)
		return resp
	else:
		return jsonify({'successfully': False, 'reason': 'Invalid username or password'})


@socketio.on('connect')
def search_game():
	username = request.cookies.get("username")
	password = request.cookies.get('password')

	if not username or not password:
		raise ConnectionRefusedError('Unauthorized!')

	user = get_user(DB, {"name": username, "password": password})
	if not user:
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

	DB.execute('UPDATE users SET room_id = ? WHERE (name = ? AND password = ?)', (room_id, username, password), commit=True)
	emit("connected", room_id, room=request.sid)


@socketio.on('disconnect')
def disconnect():
	username = request.cookies.get("username")
	password = request.cookies.get('password')

	user = get_user(DB, {"name": username, "password": password})
	if user:
		DB.execute('UPDATE users SET room_id = NULL WHERE (name = ? AND password = ?)', (username, password), commit=True)
		room = Room.QUEUE.get(user["room_id"])
		if room:
			room.remove(request.sid)
		else:
			room = Room.ActiveGames.get(user["room_id"])
			if room:
				room.remove(request.sid)


@socketio.on('event')
def game_event(data):
	username = request.cookies.get("username")
	password = request.cookies.get('password')
	if not username or not password:
		raise ConnectionRefusedError('Unauthorized!')

	user = get_user(DB, {"name": username, "password": password})
	if not user:
		raise ConnectionRefusedError('Unauthorized!')

	result = {"successfully": False, 'reason': "Room does not exist!"}

	room = Room.ActiveGames[data['room']]
	if room:
		user = User(username, request.sid)
		user_exists = room.contains(user)
		if user_exists:
			result = room.event(data, from_user=user_exists)

	return result


if __name__ == '__main__':
	socketio.run(app, debug=True)
	# print("Running...")
	# socketio.run(app, host='0.0.0.0', port=80)
