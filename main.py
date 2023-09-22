from flask import Flask, render_template, request, redirect, abort
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import hashlib
import time
import re
import json
from threading import Timer

app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False
CORS(app)
socketio = SocketIO(app)


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


if __name__ == '__main__':
	socketio.run(app, debug=True)
	# print("Running...")
	# socketio.run(app, host='0.0.0.0', port=80)