let currentLevel = 1;
let lives = 3;
let streak = 0;
let currentPhrases = [];
let remainingPhrases = []; // Track unused phrases per level

async function loadPhrases() {
    const response = await fetch(`/api/phrases/${currentLevel}`);
    currentPhrases = await response.json();
    remainingPhrases = [...currentPhrases]; // Reset for new level
    displayPhrase();
}


// Add at the top with other variables
const synth = window.speechSynthesis;


// Modify the displayPhrase function
// KEEP THIS displayPhrase FUNCTION (uses remainingPhrases)
function displayPhrase() {
    if (remainingPhrases.length === 0) {
        // All questions shown, complete level or reload
        completeLevel();
        return;
    }
    // Pick a random phrase from remainingPhrases
    const idx = Math.floor(Math.random() * remainingPhrases.length);
    const phrase = remainingPhrases[idx];
    remainingPhrases.splice(idx, 1); // Remove so it won't repeat

    document.getElementById('localPhrase').textContent = phrase.local;

    const utterance = new SpeechSynthesisUtterance(phrase.local);
    utterance.lang = 'ta-IN';
    utterance.rate = 0.8;

    document.getElementById('playAudio').onclick = () => {
        synth.cancel();
        synth.speak(utterance);
    };

    const options = generateOptions(phrase);
    const optionsContainer = document.getElementById('options');
    optionsContainer.innerHTML = '';

    options.forEach(option => {
        const button = document.createElement('button');
        button.className = 'option';
        button.textContent = option;
        button.onclick = (event) => checkAnswer(option, phrase.translation);
        optionsContainer.appendChild(button);
    });
}


function generateOptions(currentPhrase) {
    const options = [currentPhrase.translation];
    const otherPhrases = currentPhrases.filter(p => p.id !== currentPhrase.id);
    
    while (options.length < 4 && otherPhrases.length > 0) {
        const randomIndex = Math.floor(Math.random() * otherPhrases.length);
        options.push(otherPhrases[randomIndex].translation);
        otherPhrases.splice(randomIndex, 1);
    }
    
    return shuffleArray(options);
}


// Remove the second checkAnswer function and update the first one
function checkAnswer(selected, correct) {
    const selectedButton = event.target;
    
    if (selected === correct) {
        selectedButton.classList.add('correct');
        setTimeout(() => {
            selectedButton.classList.remove('correct');
            streak++;
            if (streak >= 5) {
                completeLevel();
            } else {
                displayPhrase();
            }
        }, 1000);
    } else {
        selectedButton.classList.add('incorrect');
        setTimeout(() => {
            selectedButton.classList.remove('incorrect');
            lives--;
            streak = 0;
            if (lives <= 0) {
                resetGame();
            } else {
                displayPhrase();
            }
        }, 1000);
    }
    updateUI();
}

async function completeLevel() {
    try {
        const response = await fetch('/api/complete_level', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ level: currentLevel })
        });
        
        if (!response.ok) {
            throw new Error('Failed to complete level');
        }
        
        const data = await response.json();
        if (data.badge) {
            showAchievement(data.badge);
        } else {
            // Force level progression if badge data is missing
            currentLevel++;
            streak = 0;
            loadPhrases();
        }
    } catch (error) {
        console.error('Level completion error:', error);
        // Force level progression on error
        currentLevel++;
        streak = 0;
        loadPhrases();
    }
}


function showAchievement(badge) {
    const badgeImage = document.getElementById('badgeImage');
    const badgeTitle = document.getElementById('badgeTitle');
    const modal = document.getElementById('achievementModal');
    const buttonContainer = document.getElementById('achievementButtons');
    
    badgeImage.src = `/static/images/${badge.image}`;
    badgeTitle.textContent = badge.title;
    
    // Add continue button
    buttonContainer.innerHTML = `
        <button onclick="downloadBadge()" class="badge-btn">Download Badge</button>
        <button onclick="shareToTravelLog()" class="badge-btn">Share to Travel Log</button>
        <button onclick="continueToNextLevel()" class="continue-btn">Continue to Next Level</button>
    `;
    
    modal.classList.remove('hidden');
    modal.classList.add('fade-in');
}

function continueToNextLevel() {
    const modal = document.getElementById('achievementModal');
    modal.classList.add('fade-out');
    
    setTimeout(() => {
        modal.classList.add('hidden');
        modal.classList.remove('fade-out');
        currentLevel++;
        streak = 0;
        loadPhrases();
        updateUI();
    }, 500);
}


function downloadBadge() {
    const badgeImg = document.getElementById('badgeImage');
    const link = document.createElement('a');
    link.href = badgeImg.src;
    link.download = `badge_level_${currentLevel}.png`;
    link.click();
}


function shareToTravelLog() {
    window.location.href = "/travellog";
}


function updateUI() {
    document.getElementById('currentLevel').textContent = currentLevel;
    document.getElementById('livesCount').textContent = lives;
    document.getElementById('streakCount').textContent = streak;
}


function resetGame() {
    currentLevel = 1;
    lives = 3;
    streak = 0;
    loadPhrases();
    updateUI();
}


function shuffleArray(array) {
    for (let i = array.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [array[i], array[j]] = [array[j], array[i]];
    }
    return array;
}


// Initialize game
loadPhrases();


// Remove the old audio event listener and add this initialization
document.addEventListener('DOMContentLoaded', () => {
    // Check for TTS support
    if (!synth) {
        console.warn('Text-to-speech not supported in this browser');
        document.getElementById('playAudio').style.display = 'none';
    }
});