from flask import Flask, render_template, request, redirect, abort, jsonify
from flask_cors import CORS
from flask_socketio import SocketIO, emit, ConnectionRefusedError
import hashlib
import time
import re
import json
from threading import Timer
import sqlite3

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
CORS(app)
socketio = SocketIO(app)

with sqlite3.connect('database/users.db') as conn:
	DB = conn.cursor()
	DB.execute('''
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


def serialize(arr):
	return json.loads(json.dumps(arr, default=lambda cls: cls.json()))


@app.route('/')
def index():
	return render_template('index.html')


@app.route('/register', methods=['POST'])
def register_user():
	username = request.json.get('username')
	password = request.json.get('password')

	if not username or not password:
		return jsonify({'successfully': False, 'reason': 'Both username and password are required'})

	DB.execute('SELECT * FROM users WHERE name = ?', (username,))
	existing_user = DB.fetchone()
	
	if existing_user:
		return jsonify({'successfully': False, 'target': "username", 'reason': 'Username already exists'})

	hashed_password = hashlib.md5(password.encode('utf-8')).hexdigest()

	DB.execute('INSERT INTO users (name, password) VALUES (?, ?)', (username, hashed_password))
	conn.commit()
	return jsonify({'successfully': True})
	
	
@app.route('/login', methods=['POST'])
def login():
	username = request.json.get('username')
	password = request.json.get('password')

	if not username or not password:
		return jsonify({'successfully': False, 'reason': 'Both username and password are required'})

	hashed_password = hashlib.md5(password.encode('utf-8')).hexdigest()

	DB.execute('SELECT * FROM users WHERE name = ? AND password = ?', (username, hashed_password))
	user = DB.fetchone()
	if user:
		column_names = [column[0] for column in DB.description]
		user_info = dict(zip(column_names, user))
		return jsonify({'successfully': True, 'data': user_info})
	else:
		return jsonify({'successfully': False, 'reason': 'Invalid username or password'})


QUEUE = {}
ActiveGames = {}


@socketio.on('connect')
def search_game():
	username = request.cookies.get("username")
	password = request.cookies.get('password')

	if not username or not password:
		raise ConnectionRefusedError('Unauthorized!')

	user = User(username, request.sid)

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

if __name__ == '__main__':
	socketio.run(app, debug=True)
	# print("Running...")
	# socketio.run(app, host='0.0.0.0', port=80)
