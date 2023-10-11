import json
import re
import requests
import math
import pandas as pd
import openai
openai.api_key = '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'

class HF_TG_inference():
    def __init__(self, model_config, default_context: str=None):
        self.chat_stub = default_context
        self.MODEL_URL = model_config['model_url']
        self.MODEL_NAME = model_config['model_name']
        self.MODEL_PARAMETERS = model_config['model_params']
        self.PROMPT_TEMPLATE = model_config['prompt_template']
        self.MAX_ITERATIONS = model_config['max_iterations']
        self.MAX_INPUT = model_config['max_input']
    

    def get_openai_response(self, input_1: str = '', input_2: str = ''): 
        response = openai.ChatCompletion.create(
            # model="gpt-4",
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": input_1},
                {"role": "user", "content": self.PROMPT_TEMPLATE.format(input_1='', input_2=input_2)}
            ],
            max_tokens=4096-self.MAX_INPUT,
            stop=None,
            temperature=0.1
        )
        return response.choices[0]['message']['content'].strip()
    
    def get_response(self, input_1: str = '', input_2: str = ''):
        token_overflow = self.quick_token_check(input_1, input_2)
        if token_overflow > 0:
            input_1, input_2 = self.quick_truncate(input_1, input_2, token_overflow)
        prompt = self.PROMPT_TEMPLATE.format(input_1=input_1, input_2=input_2)
        response = self.get_inference_loop(prompt)
        return response 

    def quick_token_check(self, input_1: str, input_2: str):
        #estimate tokens = 2*word_count. Testing shows actual ratio of 1.3 to 1.5:1
        prompt = self.PROMPT_TEMPLATE.format(input_1=input_1, input_2=input_2)
        prompt_words = prompt.split()
        return max(0, len(prompt_words) - self.MAX_INPUT//1.8)

    def quick_truncate(self, input_1: str, input_2: str, token_overflow: int):
        # Only truncation of input_1 is supported at this time
        input_1_words = input_1.split()
        return ' '.join(input_1_words[:-1*token_overflow*1.555]), input_2
    
    def get_inference_loop(self, prompt: str):
        generated_text = []
        end_found = False
        while not end_found:
            response = self.get_inference(prompt+' '.join(generated_text))
            try:
                if re.search('\S',response) is not None and re.search('(\n\n\n)',response) is None:
                    response = response.strip()
                    if re.search('(\s+\S+$)',response) is not None:
                        response = response[:re.search('(\s+\S+$)',response).span()[0]]
                else:
                    end_found = True
                if re.search('\[INST\]',response) is not None:
                    response = response[:re.search('(\[INST\])',response).span()[0]]
                    end_found = True
                response = response.strip()
                user_search = re.search('User', response)
                # bot is asking itself questions, truncate to knock that shit off
                if user_search:
                    response = response[:user_search.span()[0]]
                    end_found = True
                response = response.replace('>>CONTEXT<<','').replace('>>SUMMARY<<','').replace('>>ABSTRACT<<','')
                generated_text.append(response)
                if len(generated_text) >= self.MAX_ITERATIONS:
                    end_found = True
            except:
                generated_text.append(f"ERROR: Recieved type {response}")
                end_found = True
        return ' '.join(generated_text)
    
    def get_inference(self, prompt: str):
        headers = {
	        "Authorization": f"Bearer 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",
	        "Content-Type": "application/json"
        }
        payload = {
            'inputs': prompt,
            'parameters': self.MODEL_PARAMETERS
        }
        response = requests.request("POST",self.MODEL_URL, headers=headers, data=json.dumps(payload) )
        try:
            output = response.json()[0]['generated_text']
        except:
            output = response
        return output

class Summarizer(HF_TG_inference):
    def __init__(self, model_name: str, model_url: str, model_max_input: int):
        self.GENERATION_MODE = 'HF'
        self.model_config = {
            'model_name':model_name,
            'model_url':model_url,
            'max_input':model_max_input,
            'max_iterations': 2,
            'model_params':{
                        "temperature": 0.7,
                        "repetition_penalty": 1.9,
                        "top_k": 50,
                        "top_p": 0.7,
                        "max_new_tokens": 512,
                        "do_sample": False,
                        "length_penalty": 5.0,
                        "return_full_text": False,
                        "num_beams": 2
                        },
            'prompt_template_HF': """Provide a summary of the below context including project and client name (if the client name is known), problem statement, detailed business requirements, technologies used, deliverables and outcome. Do not include Agile or team information. Do not copy the original, use it as a reference. Do not add any data that is not found in the below context. Summary should be {input_2} words long, do not ask questions, and never repeat information.

            Source: "{input_1}"\n
            Summary:""",

            'prompt_template_OAI': """\nSummarize the above, excluding Agile or team information, with a maximum {input_2} tokens.{input_1}"""
        }
        self.model_config['prompt_template'] = self.model_config[f'prompt_template_{self.GENERATION_MODE}']
        super().__init__(self.model_config)
    
    def set_mode(self, generation_mode):
        self.GENERATION_MODE = generation_mode
        self.PROMPT_TEMPLATE = self.model_config[f'prompt_template_{self.GENERATION_MODE}']

    def get_summary(self, context: str, max_summary_len: int):
        padding = 20
        context_split = context.split()
        word_count = len(context_split)
        chunks_needed = math.ceil( word_count/ (self.MAX_INPUT//2 - padding))
        # split text
        if chunks_needed > 1 and len(context.split('____') >= chunks_needed):
            chunks = context.split('____')
        else:
            padding_total = (chunks_needed)*padding
            chunk_size = math.ceil((word_count + padding) / chunks_needed)
            chunks = [' '.join(context_split[(chunk_size-padding)*i:(chunk_size-padding)*i + chunk_size]) for i in range(chunks_needed)]
        # summarize chunks
        summaries = []
        for chunk in chunks:
            if self.GENERATION_MODE == 'HF':
                chunk_summary = super().get_response(context,  max_summary_len // chunks_needed)
            else:
                chunk_summary = super().get_openai_response(context,  max_summary_len // chunks_needed)
            summaries.append(chunk_summary)
        return ' '.join(summaries)

class Chat(HF_TG_inference):
    def __init__(self, model_name: str, model_url: str, model_max_input: int):
        self.GENERATION_MODE = 'HF'
        self.model_config = {
            'model_name':model_name,
            'model_url':model_url,
            'max_input':model_max_input,
            'max_iterations': 6,
            'model_params':{
                            "temperature": 0.1,
                            "repetition_penalty": 1.7,
                            "top_k": 50,
                            "top_p": 0.4,
                            "max_new_tokens": 128,
                            "do_sample": True,
                            "length_penalty": 0.1,
                            "return_full_text": False,
                            "num_beams": 20
                        },
            'prompt_template_HF': """The following is a conversation between a User and a helpful, intelligent corporate AI Assistant working for Atyeti, a professional services and staffing company. If the User asks about something not in the context the Assistant will only reply 'I do not have information on that' and end the conversation. 
            Context:{input_1}
            Current conversation:
            {input_2}
            Assistant:""",

            'prompt_template_OAI': """The following is a conversation between a User and a helpful, intelligent corporate AI Assistant working for Atyeti, a professional services and staffing company. If the User asks about something not in the context the Assistant will only reply 'I do not have information on that' and end the conversation. 
            Context:{input_1}
            Current conversation:
            {input_2}
            Assistant:"""
        }
        self.model_config['prompt_template'] = self.model_config[f'prompt_template_{self.GENERATION_MODE}']
        super().__init__(self.model_config)
        
    def set_mode(self, generation_mode):
        self.GENERATION_MODE = generation_mode
        self.PROMPT_TEMPLATE = self.model_config[f'prompt_template_{self.GENERATION_MODE}']

    def get_response(self, context: str, chat_history: str):
        if self.GENERATION_MODE == 'HF':
            return super().get_response(context, chat_history)
        else:
            return super().get_openai_response(context, chat_history)

class CaseBot():
    def __init__(self):
        self.GENERATION_MODE = 'HF'
        model_name = "tiiuae/falcon-7b-instruct"
        model_url = "https://lwi42mm4lagb1h7x.us-east-1.aws.endpoints.huggingface.cloud"
        model_max_input = 2048
        self.chatbot = Chat(model_name, model_url, model_max_input)
        self.summarizer = Summarizer(model_name, model_url, model_max_input)
        
    def set_mode(self, generation_mode):
        self.GENERATION_MODE = generation_mode
        self.chatbot.set_mode(generation_mode)
        self.summarizer.set_mode(generation_mode)
    
    def get_response(self, chat_history: str):
        chat_history = self.format_chat_history(chat_history)
        context = self.get_context(chat_history)
        context, chat_history = self.make_prompt_fit(context, chat_history)
        return self.chatbot.get_response(context, chat_history)
    
    def get_context(self, chat_history: str):
        last_inquiry = re.split('Assistant:?|User:?',chat_history)[-1]
        stripped_history = chat_history.replace('User:','').replace('Assistant:','')
        payload = pd.DataFrame(
            [
                ['',
                '',
                stripped_history, 
                99999, 
                1,
                'search']
            ], 
            columns=[
                "client_name",
                "project_name",
                "input_text", 
                "max_output_tokens", 
                "max_retrieval_bound",
                "task"])
        response = requests.request(
            method="POST",
            headers = {'Authorization': f'Bearer dapi8a6c45fb36f0fe293bf857f5cf34def6', 'Content-Type': 'application/json'},
            url="https://6858999327397679.9.gcp.databricks.com/model/encoderMonitor/Production/invocations",
            data=json.dumps({"dataframe_split": payload.to_dict(orient='split')}, allow_nan=True),
        )
        if response.status_code != 200:
            raise Exception(f'Request failed with status {response.status_code}, {response.text}')
        response_str = response.json()['predictions'][0][0]
        return response_str.replace('[','<').replace(']','>')
    
    def make_prompt_fit(self, context: str, chat_history: str):
        # make sure prompt fits into the chat model
        token_overflow = self.chatbot.quick_token_check(context, chat_history)
        while token_overflow > 0:
            # preserve latest chat request
            chat_history_split = re.split('User:?|Assistant:?',chat_history)
            if chat_history_split[0] == '':
                chat_history_split.remove('')
            old_chat_history = '\n'.join(chat_history_split[:-1])
            chat_question = chat_history_split[-1:]
            # get relative size
            input_ratio = len(old_chat_history.split()) / (len(old_chat_history.split()) + len(context.split()))
            # shorten inputs proportionally to fit
            chat_history = self.summarizer.get_summary(old_chat_history, math.ceil(len(old_chat_history.split()) - input_ratio*token_overflow))+'\nUser:'+chat_question
            context = self.summarizer.get_summary(context, math.ceil(len(context.split()) - (1.0-input_ratio)*token_overflow))
        return context, chat_history


    def format_chat_history(self, chat_history: str):
        # model specific formatting: adjust when changing the model
        chat_history = chat_history.replace('AI:','Assistant:')
        chat_history = chat_history.replace('HUMAN:','User:')
        return chat_history



