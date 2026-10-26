#one place for the llm and the settings
#every node file imports from here so we never create the model twice

from dotenv import load_dotenv
from langchain_groq import ChatGroq

load_dotenv()

#low temperature for scoring and classifying, a bit higher for writing
llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0.1)

writer_llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0.5)

MAX_ATTEMPTS = 3          # max writer tries before we hand the draft to the human
MAX_HUMAN_ROUNDS = 2      # max times the human can reject before we escalate
