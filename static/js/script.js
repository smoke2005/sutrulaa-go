const chatBox = document.getElementById("chat-box");
const userInput = document.getElementById("user-input");

function addMessage(text, sender = "bot") {
  const bubble = document.createElement("div");
  bubble.classList.add("bubble", sender);
  bubble.innerText = text;
  chatBox.appendChild(bubble);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function addTypingIndicator() {
  const bubble = document.createElement("div");
  bubble.classList.add("bubble", "bot");
  bubble.id = "typing";
  bubble.innerText = "Paadhai is typing...";
  chatBox.appendChild(bubble);
  chatBox.scrollTop = chatBox.scrollHeight;
}

function removeTypingIndicator() {
  const typing = document.getElementById("typing");
  if (typing) chatBox.removeChild(typing);
}

function sendMessage() {
  const userMessage = document.getElementById('user-input').value;
  
  // Add user message to chat
  addMessage(userMessage, 'user');
  
  // Show typing indicator
  addTypingIndicator();
  
  fetch('/chatbot', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ message: userMessage })
  })
  .then(response => response.json())
  .then(data => {
    removeTypingIndicator();
    addMessage(data.reply);  // Add bot response to chat
    document.getElementById('user-input').value = '';  // Clear input
  })
  .catch(error => {
    removeTypingIndicator();
    addMessage('Error connecting to chatbot', 'bot');
    console.error('Error:', error);
  });
}

// 🎙️ Speech Recognition (Web Speech API)
document.getElementById("voice-btn").addEventListener("click", () => {
  const recognition = new window.webkitSpeechRecognition();
  recognition.lang = "ta-IN"; // or "ta-IN" for Tamil
  recognition.start();

  recognition.onresult = function(event) {
    userInput.value = event.results[0][0].transcript;
  };
});
