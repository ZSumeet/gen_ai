# log into the app folder
cd app

# install the dependencies
pip install --no-cache-dir -r requirements.txt 

# run the app
python chatbot_backend.py

# note that this also works, but closing it will close the terminal window.  Need to troublesboot. 
exec gunicorn --bind :8080 --workers 1 --threads 8 --timeout 0 chatbot_backend:app 
