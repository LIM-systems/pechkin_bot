from dotenv import load_dotenv
import os

load_dotenv()

TOKEN = os.getenv('TOKEN')
CHAT_ID = int(os.getenv('CHAT_ID'))

YA_API_URL = os.getenv('YA_API_URL')
YA_ORG_ID = int(os.getenv('YA_ORG_ID'))
YA_TOKEN = os.getenv('YA_TOKEN')

EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
EMAIL_SERVER = os.getenv('EMAIL_SERVER')
EMAIL_PORT = int(os.getenv('EMAIL_PORT'))
