import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# 🔐 API Key OpenAI
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# 🔗 Supabase connection URL para SQLAlchemy
SUPABASE_URL = "postgresql://postgres:EnteNova2025@db.gqhrbvusvcaytcbnusdx.supabase.co:5432/postgres?sslmode=require"
