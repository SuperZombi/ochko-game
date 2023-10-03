window.onload = _=>{
	window.addEventListener("scroll", _=>{
		if (window.scrollY >= 200){
			document.querySelector("#wrapper").classList.add("scrolled")
		} else{
			document.querySelector("#wrapper").classList.remove("scrolled")
		}
	})
	// main_game({"me": {"name": "User 1"},
	// 		   "opponents": [{"name": "User 2"}, {"name": "User 3"}, {"name": "User 4"}]
	// })
}

var timer;
var socket;
var ROOM_ID;
var gameFounded = false;
function search_game(){
	document.querySelector("#search_animation").classList.remove("hidden")
	timer = searchTimer()

	document.querySelector("#game-searcher").onsubmit = _=>{
		document.querySelector("#search_animation").classList.add("hidden")
		clearTimeout(timer)
		document.querySelector("#game-searcher").onsubmit = _=>{search_game();return false;}
		document.querySelector("#game-searcher [type=submit]").innerHTML = "Search Game"
		socket.disconnect()
		return false;
	}
	document.querySelector("#game-searcher [type=submit]").innerHTML = "Cancel"

	socket = io.connect(location.protocol + '//' + document.domain + ':' + location.port);
	socket.on('connected', function(queue_id) {
		ROOM_ID = queue_id
	});
	socket.on('game_created', function(users) {
		gameFounded = true;
		main_game(users)
	});
}

function searchTimer(){
	function secondsToStr(seconds) {
		const minutes = Math.floor(seconds / 60);
		const remainingSeconds = seconds % 60;
		const mm = String(minutes).padStart(2, '0');
		const ss = String(remainingSeconds).padStart(2, '0');
		return mm + ':' + ss;
	}

	let time = 0;
	let el = document.querySelector("#search_timer")
	el.innerHTML = secondsToStr(time)
	return setInterval(_=>{
		time++;
		el.innerHTML = secondsToStr(time)
	}, 1000)
}

function main_game(users){
	document.querySelector("#profile-area").classList.add("hide")
	document.querySelector("#game-area").classList.remove("hide")
	add_user(users.me)
	users.opponents.forEach(add_user)
}

function add_user(user){
	let el = document.createElement("div")
	el.className = "player"
	el.setAttribute("name", user.name)
	el.innerHTML = `
		<div class="player-info">
			<img src="${user.avatar}">
			<span>${user.name}</span>
		</div>
		<div class="player-cards" value="0" max="30"></div>
		<div class="player-dibs" value="10"></div>
	`
	document.querySelector("#game-area").appendChild(el)

	let bid = document.createElement("div")
	bid.className = "player-bid"
	document.querySelector("#game-area #table").appendChild(bid)

	el.cards = val=>{el.querySelector(".player-cards").setAttribute("value", val)}
	el.dibs = val=>{el.querySelector(".player-dibs").setAttribute("value", val)}
	el.bid = val=>{
		if (val == 0){bid.innerHTML = ""}
		if (val == -1){bid.innerHTML = "X"}
		else{bid.innerHTML = val}
	}

	let playerTurnAnimation;
	el.playerTurn = _=>{
		bid.classList.add("waiting")
		bid.innerHTML = "..."

		let full_seconds = 30;
		function renderTimer(remaining){
			let percent = (remaining * 100) / (full_seconds * 1000);
			bid.style.setProperty('--percent', percent + "%");
			if (remaining > 0){
				playerTurnAnimation = setTimeout(_=>{
					renderTimer(remaining - 50)
				}, 50)
			}
		}
		renderTimer(full_seconds * 1000)
	}
	el.playerTurnStop = _=>{
		if (playerTurnAnimation){
			clearTimeout(playerTurnAnimation)
			bid.classList.remove("waiting")
			bid.innerHTML = ""
			bid.style.removeProperty('--percent');
		}
	}
}
