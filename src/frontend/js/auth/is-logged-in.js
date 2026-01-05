(function(){
    idToken = localStorage.getItem("idToken");

    if (!idToken) {
        window.alert("ログインしていません");
        window.location.href = "index.html";
    return;
    } 
})()
