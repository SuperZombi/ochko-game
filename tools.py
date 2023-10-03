import os
from flask_socketio import emit
import sqlite3
from threading import Timer
import json
import random

class User():
	CONTEXT = None
	def __init__(self, name, id_, avatar=None):
		self.name = name
		self.id = id_
		self.avatar = avatar if avatar else f"https://ui-avatars.com/api/?name={name}&length=1&color=fff&background=random&bold=true&format=svg&size=512"

	def __eq__(self, other):
		return self.id == other.id

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

	def remove(self, user_id):
		self.users = list(filter(lambda usr: usr.id != user_id, self.users))
		if len(self.users) == 0:
			del self.QUEUE[self.id]

	def timerEnd(self):
		if len(self.users) > 1:
			self.startGame()
		else:
			self.waitPlayers = False

	def startGame(self):
		del self.QUEUE[self.id]
		self.ActiveGames[self.id] = Game(self)


	def __repr__(self):
		return f"Room({self.users})"


class Game():
	cards = [6, 7, 8, 9, 10, 11, 12]
	def __init__(self, room):
		self.id = room.id
		self.init_users = room.users
		self.users = room.users

		for user in self.users:
			user.coins = 10
			user.score = 0
			opponents = [i for i in self.users if i.name != user.name]
			user.receive_message("game_created", {"opponents": serialize(opponents), "me": serialize(user)})

		self.current_first_user = random.choice(self.users)
		self.new_phase(True)

	def contains(self, user_to_find):
		filtered_users = filter(lambda user: user == user_to_find, self.users)
		found_user = next(filtered_users, None)
		return found_user if found_user else False

	def next_user(self, current_user):
		current_index = self.users.index(current_user)
		if current_index == len(self.users) - 1:
			return self.users[0]
		return self.users[current_index + 1]

	def new_phase(self, game_start=False):
		if not game_start:
			self.current_first_user = self.next_user(self.current_first_user)
			for user in self.users:
				user.coins += 1
				user.bid = 0

		self.current_card = random.choice(self.cards)
		self.current_user = self.current_first_user

		self.send_message("new_phase", {"current_card": self.current_card,
										"current_user": serialize(self.current_user),
										"users": serialize(self.users)})

		self.timer = Timer(30, self.switch_player)
		self.timer.start()

	def switch_player(self):
		if self.current_user.bid == 0:
			self.current_user.bid = -1
		if self.next_user(self.current_user) == self.current_first_user:
			return self.final_phase()

		self.current_user = self.next_user(self.current_user)
		self.send_message("switch_player", {"current_user": serialize(self.current_user)})

	def final_phase(self):
		user_winer = max(self.users, key=lambda user: user.bid)
		if user_winer.bid > 0 and user_winer.coins >= user_winer.bid:
			user_winer.coins -= user_winer.bid
			user_winer.score += self.current_card
			self.send_message("phase_result", {"winer": serialize(self.user_winer),
												"users": serialize(self.users)})
			if user_winer.score >= 30:
				self.finish_game(user_winer)
		self.new_phase()

	def event(self, data, from_user):
		if data['event'] == "make_bid":
			if self.current_user == from_user:
				if data['bid'] <= self.current_user.coins:
					self.current_user.bid = int(data['bid'])
					self.timer.cancel()
					self.send_message("user_bid", {"from_user": serialize(self.current_user), "bid": self.current_user.bid})
					self.switch_player()
					return {"successfully": True}
		return {"successfully": False}

	def finish_game(self, winer):
		# TODO
		pass

	def remove(self, user_id):
		target_user = self.contains(User("", user_id))
		if self.current_user.id == target_user.id:
			self.timer.cancel()
			self.switch_player()
		self.send_message("user_leave", {"from_user": serialize(target_user)})

	def send_message(self, event, message):
		for user in self.users:
			user.receive_message(event, message)


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

def get_user(db, kargs):
	condition = " AND ".join(map(lambda x: f"{x} = ?", kargs.keys()))
	result = db.execute(f'SELECT * FROM users WHERE ({condition})', tuple(kargs.values()))
	user = result.fetchone()
	if user:
		column_names = [column[0] for column in result.description]
		return dict(zip(column_names, user))
	return {}
