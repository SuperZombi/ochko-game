function login(){
	let form_action = document.querySelector("#login-area input[name='form_action']:checked").value
	let username = document.querySelector("#login-area input[name='username']").value.trim()
	let password = document.querySelector("#login-area input[name='password']").value.trim()

	let xhr = new XMLHttpRequest();
	xhr.open("POST", `/${form_action}`)
	xhr.setRequestHeader('Content-type', 'application/json; charset=utf-8');
	xhr.onload = _=>{
		if (xhr.status == 200){
			let answer = JSON.parse(xhr.response);
			if (answer.successfully){
				setCookie('username', username)
				setCookie('password', password)
				document.querySelector("#login-area").classList.add("hide")
				document.querySelector("#game-searcher").classList.remove("hide")
				document.querySelector("#game-searcher #username").value = username
				console.log(answer.data)
			}
			else{
				let input = document.querySelector(`#login-area input[name='${answer.target}']`)
				if (input){
					input.setCustomValidity(answer.reason);
					input.reportValidity();
					setTimeout(()=>{input.setCustomValidity('')}, 3000)
				}
				else{
					alert(answer.reason)
				}
			}
		}
	}
	xhr.send(JSON.stringify({'username': username, 'password': password}))
}


var timer;
var socket;
var ROOM_ID;
var gameFounded = false;
function search_game(){
	let username = document.querySelector("#game-searcher #username").value.trim();
	if (username){
		document.querySelector("#search_animation").classList.remove("hidden")
		timer = searchTimer()

		document.querySelector("#game-searcher").onsubmit = _=>{
			document.querySelector("#search_animation").classList.add("hidden")
			clearTimeout(timer)
			document.querySelector("#game-searcher").onsubmit = _=>{search_game();return false;}
			document.querySelector("#game-searcher [type=submit]").innerHTML = "Search Game"
			socket.emit("leave_queue", ROOM_ID)
			setTimeout(_=>{socket.disconnect()}, 100)
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
}
window.onbeforeunload = _=> {
	if (socket && socket.connected){
		if (gameFounded){
			// socket.emit("leave_game", ROOM_ID)
		} else{
			socket.emit("leave_queue", ROOM_ID)
		}
	}
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
	document.querySelector("#game-searcher").classList.add("hide")
	document.querySelector("#main-area").classList.remove("hide")
	console.log(users)
}

function setCookie(name, value, options = {}) {
	let age_time = Math.floor(new Date().getTime() / 1000) + (365 * 24 * 60 * 60);
	options = {path: '/', 'max-age': age_time, ...options};
	let updatedCookie = name + "=" + value;
	for (let optionKey in options) {
		updatedCookie += "; " + optionKey;
		let optionValue = options[optionKey];
		updatedCookie += "=" + optionValue;
	}
	document.cookie = updatedCookie;
}
function deleteCookie(name){
	setCookie(name, "", {'max-age': -1})
}
function getCookie(name) {
	let cookie = {};
	document.cookie.split(';').forEach(function(el) {
		let [k,v] = el.split('=');
		cookie[k.trim()] = v;
	})
	return cookie[name];
}
