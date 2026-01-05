'use strict';

document.getElementById("logoutBtn").addEventListener("click",function(){
    console.log("ログアウト処理開始");
    if (confirm("ログアウトしますか？")){
        localStorage.removeItem("idToken");
        localStorage.removeItem("accessToken");
        localStorage.removeItem("refreshToken");
        // window.alert("ログアウトしました");
        window.location.href = "index.html";
    }
})