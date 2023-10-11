import os, json, random, logging
from dotenv import load_dotenv

import os
from langchain.llms.huggingface_endpoint import HuggingFaceEndpoint
from langchain.agents import create_sql_agent, Tool, AgentExecutor, ConversationalAgent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase

from langchain.agents.agent_types import AgentType
from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferWindowMemory
from langchain.llms import OpenAI
from langchain.chains import LLMChain
from langchain.llms import LlamaCpp

import gradio as gr


script_dir = os.path.dirname(os.path.realpath(__file__))
# Change the working directory to the script's directory
os.chdir(script_dir)
load_dotenv("env.txt")

LLAMA2_PATH = os.getenv("LLAMA2_PATH")


llm_hf = HuggingFaceEndpoint(
            endpoint_url=os.getenv("HUGGINGFACE_ENDPOINT"),
            huggingfacehub_api_token=os.getenv("HUGGINGFACEHUB_API_TOKEN"),
        )

llm_openai = ChatOpenAI(temperature = 0)


try:
    llm_llama = LlamaCpp(
                model_path=LLAMA2_PATH,
                temperature=0,
                max_tokens=200,
                streaming = False,
                n_ctx = 1000
                )
except:
    pass

# Set the LLM variable to either HuggingFace's Llama model or ChatGPT
llm = llm_openai

# Check if the file exists
if not os.path.isfile("doctors.db"):
    raise FileNotFoundError(f"The doctors.db database does not exist.")
    
#Load Database
db = SQLDatabase.from_uri("sqlite:///doctors.db")
toolkit = SQLDatabaseToolkit(db=db,llm=llm)

#Instantiate SQL Agent
sql_executor = create_sql_agent(
    llm=llm,
    toolkit=toolkit,
    verbose=True,
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    top_k = 10000
)

#Define tools
tools = [
    Tool(
        name="Doctors Database System",
        func=sql_executor.run,
        return_direct=True,
        description="useful to give information about doctors names, specialities and locations. Input should be a fully formed question.",
    )
]

# Create Agent chain with access to tools. The agent can casually speak about anything and will query the database when asked about doctors.
prefix = """You are a helpful assistant. 
Have a normal conversation with a human. 
You can offer to answer questions about a database with doctor information.
You have access to the following tools:"""
suffix = """Begin!"

{chat_history}
Question: {input}
{agent_scratchpad}"""

prompt = ConversationalAgent.create_prompt(
    tools,
    prefix=prefix,
    suffix=suffix,
    input_variables=["input", "chat_history", "agent_scratchpad"],
)

memory = ConversationBufferWindowMemory(memory_key="chat_history", k = 2)
agent = ConversationalAgent(llm_chain=LLMChain(llm=llm, prompt=prompt), verbose=True)

agent_chain = AgentExecutor.from_agent_and_tools(
    agent=agent, tools=tools, verbose=False, memory=memory
)



def inference(message, history):
    return agent_chain.run(message)
        

(gr.ChatInterface(
    inference,
    chatbot=gr.Chatbot(height=400),
    textbox=gr.Textbox(placeholder="Ask me anything!", container=False, scale=7),
    description="This is an LLM to interact with a Doctor DB",
    title="Doctor DB",
    examples=["What is the total amount of money invested by the doctors specialized in Urology which live in Ohio"],
    retry_btn="Retry",
    clear_btn="Clear",
    undo_btn = None,
)
 .queue()
 .launch()
)