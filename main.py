from flask import Flask, render_template, request, redirect, abort
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import hashlib
import time
import re
import json
from threading import Timer

from flask import request, jsonify
import sqlite3
import bcrypt

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
CORS(app)
socketio = SocketIO(app)

with sqlite3.connect('database/users.db') as conn:
	c = conn.cursor()
	c.execute('''
		CREATE TABLE IF NOT EXISTS "users" (
			"id"                  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
			"name"                TEXT NOT NULL,
			"password"            TEXT NOT NULL
		);
	''')
	conn.commit()


class User():
	def __init__(self, name, id_, icon):
		self.name = name
		self.id = id_
		self.icon = icon if icon else f"https://ui-avatars.com/api/?name={name}&length=1&color=fff&background=random&bold=true&format=svg&size=512"

	def receive_message(self, event, message):
		with app.app_context():
			emit(event, message, namespace='/', room=self.id)

	def __repr__(self):
		return f"{self.name}"

	def json(self):
		ignore = ['id']
		return {key: value for key, value in vars(self).items() if key not in ignore}

class Room():
	def __init__(self, id_):
		self.id = id_
		self.users = []
		self.waitPlayers = True
		self.timer = Timer(30, self.timerEnd)
		self.timer.start()

	def add(self, user):
		self.users.append(user)
		if len(self.users) == 4:
			self.timer.cancel()
			self.startGame()
		elif not self.waitPlayers:
			self.startGame()

	def remove(self, condition):
		self.users = list(filter(condition, self.users))
		if len(self.users) == 0:
			del QUEUE[self.id]

	def timerEnd(self):
		if len(self.users) > 1:
			self.startGame()
		else:
			self.waitPlayers = False

	def startGame(self):
		del QUEUE[self.id]
		new_room = Room(self.id)
		for user in self.users:
			new_room.add(user)
			user.receive_message("game_created", serialize(self.users))
		ActiveGames[self.id] = new_room


	def __repr__(self):
		return f"Room({self.users})"


QUEUE = {}
ActiveGames = {}


def serialize(arr):
	return json.loads(json.dumps(arr, default=lambda cls: cls.json()))


@app.route('/')
def index():
	return render_template('index.html')
    
@app.route('/register', methods=['GET'])
def show_registration_form():
    return render_template('register.html')

@socketio.on('connect')
def search_game():
	username = request.args.get('username')
	if not username:
		raise ConnectionRefusedError('Unauthorized!')

	icon = request.headers.get("icon")
	user = User(username, request.sid, icon=icon)

	if len(QUEUE) == 0:
		room_id = hashlib.md5(str(int(time.time())).encode('utf-8')).hexdigest()
		room = Room(room_id)
		room.add(user)
		QUEUE[room_id] = room
	else:
		room_id = list(QUEUE.keys())[0]
		room = QUEUE[room_id]
		room.add(user)

	emit("connected", room_id, room=request.sid)


@socketio.on('leave_queue')
def leave_queue(room_id):
	room = QUEUE[room_id]
	if room:
		room.remove(lambda user: user.id != request.sid)

@app.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()

    if 'username' not in data or 'password' not in data:
        return jsonify({'successfully': 'Both username and password are required'}), 400

    username = data['username']
    password = data['password']

    c.execute('SELECT * FROM users WHERE name = ?', (username,))
    existing_user = c.fetchone()
    
    if existing_user:
        return jsonify({'successfully': 'Username already exists'}), 409

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    c.execute('INSERT INTO users (name, password) VALUES (?, ?)', (username, hashed_password))
    conn.commit()

    return jsonify({'successfully': true}), 201
    
    
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()

    if not data:
        return jsonify({'successfully': 'Invalid JSON data in the request'}), 400

    if 'username' not in data or 'password' not in data:
        return jsonify({'successfully': 'Both username and password are required'}), 400

    username = data['username']
    password = data['password']

    # Проверка введенных данных и выполнение входа
    c.execute('SELECT * FROM users WHERE name = ? AND password = ?', (username,password,))
    user = c.fetchone()

    if user:
        login_user(user)
        return jsonify({'Successfully': true}), 200
    else:
        return jsonify({'successfully': 'Invalid username or password'}), 401

if __name__ == '__main__':
	socketio.run(app, debug=True)
	# print("Running...")
	# socketio.run(app, host='0.0.0.0', port=80)


