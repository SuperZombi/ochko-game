window.onload = _=>{
	window.addEventListener("scroll", _=>{
		if (window.scrollY >= 200){
			document.querySelector("#wrapper").classList.add("scrolled")
		} else{
			document.querySelector("#wrapper").classList.remove("scrolled")
		}
	})
	let bid_input = document.querySelector("#bid-maker input")
	document.querySelectorAll("#bid-maker .controls span").forEach(control=>{
		control.onclick = _=>{
			let action = control.getAttribute("action")
			let current = parseInt(bid_input.value)
			if (action == "up"){
				bid_input.stepUp();
			}
			else if (action == "down"){
				bid_input.stepDown();
			}
		}
	})
	document.querySelector("#bid-maker #confirm").onclick = _=>{
		let value = parseInt(bid_input.value)
		if (value == parseInt(document.querySelector("#bid-maker input").getAttribute("min"))){
			socket.emit("event", {event: "make_bid", "bid": -1})
		} else{
			socket.emit("event", {event: "make_bid", "bid": value})
		}
	}
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
	socket.on('new_phase', function(data) {
		document.querySelector("#current-card .card").setAttribute("value", data.current_card)
		data.users.forEach(user=>{
			let el = document.querySelector(`#game-area .player[name="${user.name}"]`)
			el.score(user.score)
			el.dibs(user.coins)
			el.bid(0)
		})
		document.querySelector("#bid-maker").classList.add("hide")
		document.querySelector("#bid-maker input").setAttribute("min", 0)
		document.querySelector("#bid-maker input").value = 0

		let el = document.querySelector(`#game-area .player[name="${data.current_user.name}"]`)
		el.playerTurn()
		if (el.getAttribute("me")){
			let input = document.querySelector("#bid-maker input")
			input.setAttribute("max", data.current_user.coins)
			document.querySelector("#bid-maker").classList.remove("hide")
		}
	});
	socket.on('switch_player', function(data) {
		document.querySelector("#bid-maker").classList.add("hide")
		let el = document.querySelector(`#game-area .player[name="${data.current_user.name}"]`)
		el.playerTurn()
		if (el.getAttribute("me")){
			let input = document.querySelector("#bid-maker input")
			input.setAttribute("max", data.current_user.coins)
			document.querySelector("#bid-maker").classList.remove("hide")
		}
	});
	socket.on('user_bid', function(data) {
		let el = document.querySelector(`#game-area .player[name="${data.from_user.name}"]`)
		el.playerTurnStop()
		el.bid(data.bid)
		if (data.bid > 0){
			document.querySelector("#bid-maker input").setAttribute("min", data.bid)
			document.querySelector("#bid-maker input").value = data.bid
		}
	});
	socket.on('phase_result', function(data) {
		// console.log(data)
	});
	socket.on('game_end', function(data) {
		// console.log(data)
		alert("Winer: " + data.winer)
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
	let div = add_user(users.me)
	div.setAttribute("me", true)
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
		<div class="player-cards" value="${user.score}" max="30"></div>
		<div class="player-dibs" value="${user.coins}"></div>
	`
	document.querySelector("#game-area").appendChild(el)

	let bid = document.createElement("div")
	bid.className = "player-bid"
	document.querySelector("#game-area #table").appendChild(bid)

	el.score = val=>{el.querySelector(".player-cards").setAttribute("value", val)}
	el.dibs = val=>{el.querySelector(".player-dibs").setAttribute("value", val)}
	el.bid = val=>{
		if (val == 0){bid.innerHTML = ""}
		else if (val == -1){bid.innerHTML = "X"}
		else{bid.innerHTML = val}
	}

	let playerTurnAnimation;
	el.playerTurn = function(full_seconds=20){
		let start_time = new Date().getTime()
		let target_time = start_time + (full_seconds * 1000)
		bid.classList.add("waiting")
		bid.innerHTML = "..."
		function renderTimer(){
			let current_time = new Date().getTime()
			if (current_time <= target_time){
				let remaining = target_time - current_time;
				let percent = (remaining * 100) / (full_seconds * 1000);
				bid.style.setProperty('--percent', percent + "%");
				playerTurnAnimation = window.requestAnimationFrame(renderTimer)
			}
		}
		window.requestAnimationFrame(renderTimer)
	}
	el.playerTurnStop = _=>{
		if (playerTurnAnimation){
			window.cancelAnimationFrame(playerTurnAnimation);
		}
		bid.classList.remove("waiting")
		bid.innerHTML = ""
		bid.style.removeProperty('--percent');
	}
	return el
}
