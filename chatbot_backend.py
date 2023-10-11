from flask import Flask, render_template, request, jsonify
import os
import requests
import numpy as np
import pandas as pd
import json
import re
from CaseBot import CaseBot

class ChatManager:
    def __init__(self):
        self.chat_history = []

    def user_input_preparation(self, user_input):
        if not isinstance(user_input, str):
            raise ValueError("Input should be a string")
        return user_input 

    def get_LLM_response(self): 
        chat_history_text = ""
        for message in self.chat_history:
            chat_type_prefix = 'Assistant:' if message['chat_type'] == 'AI' else 'User:'
            chat_history_text += chat_type_prefix + message['body']
        
        ai_response = chat_bot.get_response(chat_history_text)
        return ai_response


    def update_chat_history(self, chat_type, body):
        if chat_type not in ['AI', 'HUMAN']:
            raise ValueError('Error: incorrect message type')
        self.chat_history.append({'chat_type': chat_type, 'body': body})

    def process_user_input(self, user_input):
        cleaned_input = self.user_input_preparation(user_input)
        self.update_chat_history('HUMAN', cleaned_input)
        LLM_response = self.get_LLM_response()
        LLM_response = format_response(LLM_response)
        self.update_chat_history('AI', LLM_response)
        self.print_chat_history(LLM_response)
        return LLM_response

    def print_chat_history(self, response=None):
        for m in self.chat_history:
            print(f"{m['chat_type']}: {m['body']}")
            
def format_response(response):
    # Regular expression to match numbered items and their associated content.
    pattern = r'(\d+\.)\s*([^0-9]+)'
    matches = re.findall(pattern, response)

    # Extract and combine numbered items with their associated content.
    formatted_response = [f"{match[0]} {match[1].strip()}" for match in matches]

    # If there were no matches, simply return the original response.
    if not formatted_response:
        return response

    # Join all the formatted items using newline.
    return '\n'.join(formatted_response).strip()

app = Flask(__name__, template_folder='.')
chat_manager = ChatManager()
chat_bot = CaseBot()

@app.route('/')
def index():
    return render_template('index.html')

def validate_received_data(data):
    if not isinstance(data, list):
        raise ValueError("Expected a list of chat messages.")
    for item in data:
        if not isinstance(item, str):
            raise ValueError(f"Expected each chat message to be a string, but got {type(item)}")

@app.route('/generate_response', methods=['POST'])
def generate_response():
    try:
        message_list = json.loads(request.form['message'])
        validate_received_data(message_list)
        print("Received chat history:", message_list)
        if not message_list:
            return jsonify({'error': 'Empty message received.'})
        user_message = message_list[-1]
        response_data = chat_manager.process_user_input(user_message)
        print("Sending response:", response_data)
        return jsonify({'response': response_data})
    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"error": "Apologies! We are experiencing some issues, please try again later!"})



@app.route('/clear_chat_history', methods=['POST'])
def clear_chat_history():
    try:
        chat_manager.chat_history = [] 
        print("Server chat history cleared")  
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"error": "Apologies! We are experiencing some issues, please try again later!", "status": "error"})
    

@app.route('/set_mode', methods=['POST'])
def set_mode():
    try:
        mode = request.form['mode']
        if mode not in ['HF', 'OAI']:
            raise ValueError("Invalid mode.")
        print(f"Current Mode before setting: {chat_bot.GENERATION_MODE}")
        chat_bot.set_mode(mode)
        print(f"Current Mode after setting: {chat_bot.GENERATION_MODE}")
        print(f"***********************************Mode set to: {mode}")
        return jsonify({'status': 'success'})
    except Exception as e:
        print(f"Error occurred: {e}")
        return jsonify({"error": "Failed to set mode!", "status": "error"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8080)
