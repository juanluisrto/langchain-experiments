import os, json, random, logging
from dotenv import load_dotenv

import weaviate

from langchain.agents import AgentType, initialize_agent
from langchain.chat_models import ChatOpenAI
from langchain.tools import  Tool

from langchain.schema import SystemMessage
from langchain.agents import OpenAIFunctionsAgent
from langchain.prompts import MessagesPlaceholder
from langchain.agents import AgentExecutor, OpenAIFunctionsAgent
from langchain.chains.conversation.memory import ConversationBufferMemory
from langchain.chat_models import ChatOpenAI

import gradio as gr

load_dotenv()


def find_videos_about_topic(message):

    try:
        #initialize client
        wv_client = get_wv_client()
        
        ask = {
          "question": message,
          "properties": ["text"],
        }
        
        result = (
          wv_client.query
          .get("MKBHD_Video", ["url", "title",  "_additional {certainty}"])
          .with_ask(ask)
          .with_limit(1)
          .do()
        )
    
        candidate = result['data']['Get']['MKBHD_Video'][0]
        certainty = candidate["_additional"]["certainty"]
        
        if certainty > 0.9:
            return dict(
                title = candidate["title"],
                url = candidate["url"]
            )
            
        else:
            return "I don't have a video about that unfortunately"
    except Exception as e:
        logging.error(e)
        return "I cannot remember at the moment"

    
def get_wv_client():
    "Returns weaviate client"
    auth_config = weaviate.AuthApiKey(api_key=os.environ["WEAVIATE_API_KEY"])
    return weaviate.Client(
        url = os.environ["WEAVIATE_ENDPOINT"],  
        auth_client_secret=weaviate.AuthApiKey(api_key=os.environ["WEAVIATE_API_KEY"]),
        additional_headers = {
            "X-OpenAI-Api-Key": os.environ["OPENAI_API_KEY"]
        }
    )

llm = ChatOpenAI(temperature=0)

tools = [
    Tool.from_function(
        func=find_videos_about_topic,
        name="find_video",
        description="useful for when the user asks you about specific videos in your channel"
    ),
]

system_message = SystemMessage(content = """You are Marques Brownlee, MKBHD, a well-known YouTuber and tech reviewer. 
You are chatting with a fan in an informal tone. Don't talk like an assistant, do not offer your help all the time.
""")


MEMORY_KEY = "chat_history"
prompt = OpenAIFunctionsAgent.create_prompt(
    system_message=system_message,
    extra_prompt_messages=[MessagesPlaceholder(variable_name=MEMORY_KEY)]
)

memory = ConversationBufferMemory(memory_key=MEMORY_KEY, return_messages=True, ai_prefix = "MKBHD")


agent = OpenAIFunctionsAgent(
    llm=llm, 
    tools=tools, 
    prompt=prompt, 
    agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION
)

agent_executor = AgentExecutor(agent=agent, tools=tools, memory=memory, verbose=True)



def inference(message, history):
    return agent_executor.run(message)
        

gr.ChatInterface(
    inference,
    chatbot=gr.Chatbot(height=400),
    textbox=gr.Textbox(placeholder="Chat with me about my content!", container=False, scale=7),
    description="This is an LLM fine-tuned on MKBHD's video transcripts",
    title="MKBHD Virtual Assistant",
    examples=["Do you have a video about the latest Apple event?", "What can I watch about electric cars?"],
    retry_btn="Retry",
    clear_btn="Clear",
    undo_btn = None,
).queue().launch()