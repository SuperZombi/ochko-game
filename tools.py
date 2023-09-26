import os
from flask_socketio import emit
import sqlite3
from threading import Timer
import json

class User():
	CONTEXT = None
	def __init__(self, name, id_, avatar=None):
		self.name = name
		self.id = id_
		self.avatar = avatar if avatar else f"https://ui-avatars.com/api/?name={name}&length=1&color=fff&background=random&bold=true&format=svg&size=512"

	def receive_message(self, event, message):
		with self.CONTEXT:
			emit(event, message, namespace='/', room=self.id)

	def __repr__(self):
		return f"{self.name}"

	def json(self):
		ignore = ['id']
		return {key: value for key, value in vars(self).items() if key not in ignore}

class Room():
	QUEUE = {}
	ActiveGames = {}

	def __init__(self, id_):
		self.id = id_
		self.users = []
		self.waitPlayers = True
		self.timer = Timer(5, self.timerEnd)
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
			del self.QUEUE[self.id]

	def timerEnd(self):
		if len(self.users) > 1:
			self.startGame()
		else:
			self.waitPlayers = False

	def startGame(self):
		del self.QUEUE[self.id]
		for user in self.users:
			opponents = [i for i in self.users if i.name != user.name]
			user.receive_message("game_created", {"opponents": serialize(opponents), "me": serialize(user)})
		self.ActiveGames[self.id] = self


	def __repr__(self):
		return f"Room({self.users})"


def serialize(arr):
	return json.loads(json.dumps(arr, default=lambda cls: cls.json()))


class Database():
	def __init__(self, path):
		folder = os.path.dirname(path)
		if folder and not os.path.exists(folder):
			os.makedirs(folder)

		self.conn = sqlite3.connect(path)

	def execute(self, command, args=None, commit=False):
		cursor = self.conn.cursor()
		cursor.execute(command, args or ())
		if commit:
			self.conn.commit()
		return cursor

def get_user(db, username):
	result = db.execute('SELECT * FROM users WHERE name = ?', (username,))
	user = result.fetchone()
	column_names = [column[0] for column in result.description]
	return dict(zip(column_names, user))
