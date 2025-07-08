function getUserIdFromURL() {
  const urlParams = new URLSearchParams(window.location.search);
  return urlParams.get('user_id');
}

function showSurvey() {
  const userId = getUserIdFromURL();
  if (!userId) {
    alert("请先登录！");
    return;
  }

  const iframe = document.getElementById("survey-iframe");
  iframe.src = "http://localhost:8000/survey/05ae6a6b-1a2b-48a4-a2f6-10efef7728f6?user_id=" + encodeURIComponent(userId);
  document.getElementById("survey-modal").style.display = "block";
}

function closeSurvey() {
  document.getElementById("survey-modal").style.display = "none";
}
