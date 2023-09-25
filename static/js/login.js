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
				window.location = "/";
			}
			else{
				let input = document.querySelector(`#login-area input[name='${answer.target}']`)
				if (input){
					input.setCustomValidity(answer.reason);
					input.reportValidity();
					input.onkeydown = _=> input.setCustomValidity('');
				}
				else{
					alert(answer.reason)
				}
			}
		}
	}
	xhr.send(JSON.stringify({'username': username, 'password': password}))
}
