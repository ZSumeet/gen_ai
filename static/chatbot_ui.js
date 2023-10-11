const conversationContainer = document.getElementById('conversation-container');
const userInput = document.getElementById('user-input');
const sendButton = document.getElementById('send-button');
const clearButton = document.getElementById('clear-button');
const modeSwitcher = document.getElementById('modeSwitcher');

let conversation = [];

// prompt in the conversation container
function displayPrompt(message) {
    const promptContainer = document.createElement('div');
    promptContainer.className = 'prompt-container';
    promptContainer.textContent = message;
    conversationContainer.appendChild(promptContainer);
    conversationContainer.scrollTop = conversationContainer.scrollHeight;
}

function displayResponse(message) {
    const responseContainer = document.createElement('div');
    responseContainer.className = 'response-container';

    // Splitting at newline, as formatted in Python
    const lines = message.split('\n');
    for (let line of lines) {
        if(line.trim().length > 0) { // check if not an empty string
            const p = document.createElement('p');
            p.textContent = line.trim();
            responseContainer.appendChild(p);
        }
    }

    conversationContainer.appendChild(responseContainer);
    conversationContainer.scrollTop = conversationContainer.scrollHeight;
}
function handleUserInput(event) {
    const message = userInput.value.trim();
    if (message !== '') {
        // Check if Enter key or send button clicked
        if (event.key === 'Enter' || event.target === sendButton) {
            event.preventDefault();

            // Add user's message to conversation
            conversation.push(message); 
            displayPrompt(message);

            userInput.value = '';

            // Convert entire conversation to a JSON string
            const messageJsonString = JSON.stringify(conversation);
            //const messageJsonString = JSON.stringify(message);
           
            console.log("Sending chat history:", messageJsonString);

            // Generate response from the server
            fetch('/generate_response', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: 'message=' + encodeURIComponent(messageJsonString),
            })
            .then(response => response.json())
            .then(data => {
                if (typeof data.response !== 'string') {
                    console.error("Received unexpected data format:", data.response);
                    return;
                }
                console.log("Received response:", data);
                if (data.error) {
                    console.error("Backend Error:", data.error);
                    displayResponse("Error: " + data.error);
                } else {
                    const response = data.response;

                    // Display the response
                    if (response !== '') {
                        conversation.push(response); // Add bot's message to conversation
                        displayResponse(response);
                    }
                }
            })

            .catch(error => {
                console.error('Error:', error);
            });
        }
    }
}

// Event listener for send button click
sendButton.addEventListener('click', handleUserInput);

// Event listener for Enter key press
userInput.addEventListener('keydown', handleUserInput);

// Event listener for clear button click
clearButton.addEventListener('click', () => {
    conversation = [];
    conversationContainer.innerHTML = '';
    console.log("Cleared chat history from the web UI"); 

    fetch('/clear_chat_history', {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.status !== 'success') {
            console.error("Backend Error:", data.error);
        } else {
            console.log("Server chat history cleared");
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
});

// Event listener for HF to OAI
modeSwitcher.addEventListener('change', (event) => {
    const mode = event.target.checked ? "OAI" : "HF";
    fetch('/set_mode', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: 'mode=' + mode,
    })
    .then(response => response.json())
    .then(data => {
        if (data.status !== 'success') {
            console.error("Backend Error:", data.error);
        } else {
            console.log("Mode set to", mode);
        }
    })
    .catch(error => {
        console.error('Error:', error);
    });
});

// Display initial greeting message
window.onload = () => {
    displayResponse('Hello! How can I assist you?');
};
