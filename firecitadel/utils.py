from types import SimpleNamespace
import tweepy
import io

import requests, json
import os, time, logging


from langchain.memory import ConversationBufferMemory, ChatMessageHistory
from langchain.schema import SystemMessage
from langchain.chat_models import ChatOpenAI
from langchain.agents import initialize_agent, AgentType, Tool
from langchain.chains import LLMChain

from langchain.prompts.chat import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder
)

from dotenv import load_dotenv
load_dotenv()


from types import SimpleNamespace

# LOAD SECRETS

key_names = ["STABLE_DIFFUSION_API_KEY",
             "OPENAI_API_KEY",
             "TWITTER_CONSUMER_KEY",
             "TWITTER_CONSUMER_SECRET",
             "TWITTER_ACCESS_TOKEN",
             "TWITTER_ACCESS_TOKEN_SECRET",
             "TWITTER_BEARER_TOKEN",
            ]
SECRETS = SimpleNamespace(
            **{key : os.environ[key] for key in key_names}
          )



# TWITTER 

def get_tweepy_client():
    "Returns a tweepy client for Twitter's API v2 given a bearer_token"
    return tweepy.Client(
        bearer_token = SECRETS.TWITTER_BEARER_TOKEN,
        consumer_key=SECRETS.TWITTER_CONSUMER_KEY,
        consumer_secret=SECRETS.TWITTER_CONSUMER_SECRET,
        access_token=SECRETS.TWITTER_ACCESS_TOKEN,
        access_token_secret=SECRETS.TWITTER_ACCESS_TOKEN_SECRET
    )

def get_tweepy_API():
    # Authenticate to Twitter
    auth = tweepy.OAuthHandler(
        consumer_key=SECRETS.TWITTER_CONSUMER_KEY,
        consumer_secret=SECRETS.TWITTER_CONSUMER_SECRET,
        access_token=SECRETS.TWITTER_ACCESS_TOKEN,
        access_token_secret=SECRETS.TWITTER_ACCESS_TOKEN_SECRET)

    # Create API object
    api = tweepy.API(auth)
    
    return api


def upload_image_to_twitter(url, api):
    r = requests.get(url)
    b = io.BytesIO(r.content)
    b.seek(0)
    fp = io.BufferedReader(b)
    return api.media_upload(filename = url, file = fp)


# DREAMBOOTH

def post_request(url, payload):
    headers = {'Content-Type': 'application/json'}
    payload["key"] = SECRETS.STABLE_DIFFUSION_API_KEY
    
    r = requests.request("POST", url, headers=headers, data=json.dumps(payload))
    r.raise_for_status() # Check for HTTP errors
    r_json = r.json()
    if r_json["status"] == "error" :
        logging.error(r_json)
        raise Exception(r_json)
    return r_json



def fetch_image(image_id):
    url = f"https://stablediffusionapi.com/api/v3/fetch/{image_id}"
    return post_request(url, {})

        
NEGATIVE_PROMPT = "painting, extra fingers, mutated hands, poorly drawn hands, poorly drawn face, deformed, ugly, blurry, bad anatomy, bad proportions, extra limbs, cloned face, skinny, glitchy, double torso, extra arms, extra hands, mangled fingers, missing lips, sexual, sex, boobs, porn, cleavage, ugly face, distorted face, extra legs, anime"
  
MODELS = SimpleNamespace(
        MIDJOURNEY = "midjourney",
        STABLE_DIFFUSION = "sdxl",
        DREAM_SHAPER = "dream-shaper-8797",
)

def text_to_image(prompt, height = 1024, width = 1024, samples = 1, model = MODELS.DREAM_SHAPER, negative_prompt = None, wait = True):
    url = "https://stablediffusionapi.com/api/v4/dreambooth"
    payload = {
        "prompt": prompt,
        "model_id": model,
        "negative_prompt": negative_prompt,
        "width": width,
        "height": height,
        "samples": samples,
    }
    try:
        r = post_request(url, payload)
        image_id = r['id']
        while r["status"] == "processing" and wait:
            wait_seconds = 10 #r["eta"]
            logging.warning(f"Image {image_id} not ready. Sleeping {wait_seconds} seconds")
            time.sleep(wait_seconds)
            r = fetch_image(image_id)
        return r["output"]
    except Exception as e:
        logging.error(e)
        raise e
        


# OPENAI

import openai
openai.api_key = SECRETS.OPENAI_API_KEY

def create_storyteller_chain(temperature=1.2):

    llm = ChatOpenAI(temperature=temperature)
    
    system_message =\
    """You are being asked to write exciting stories with different styles and environments. Stories should be very short, with two sentences at most. 
    Sentences should be complete. Use words which are easy to understand. You should end the story with a climax.
    """
    
    system_message_prompt = SystemMessagePromptTemplate.from_template(system_message)
    human_template = "Write a story with a {style} style and in a {environment} environment"
    human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)
    
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    
    
    chat_prompt = ChatPromptTemplate.from_messages(
        [system_message_prompt,
         #MessagesPlaceholder(variable_name="chat_history"),
         human_message_prompt
        ])
    
    chain = LLMChain(
        llm=llm,
        prompt=chat_prompt,
        verbose=False,
        #memory = memory,
    )
    return chain


def create_imagedescription_chain(temperature= 1.2):
    
    img_input_llm = ChatOpenAI(
                           model = "gpt-4",
                           temperature= temperature,
                          )

    story_description_prompt = ChatPromptTemplate.from_template("""
    Describe the following scene in detail as if it was a picture, without any emotions.
    Do not write a story.
    Use many adjectives and focus on describing properly the place and the characters.
    Capture as much style as possible.
    Forget names and the plot of the scene.
    Do it in at most 100 words.
    
    Scene:
    {story}
    """)
    
    img_chain = LLMChain(
        llm=img_input_llm,
        prompt=story_description_prompt,
    )
    return img_chain

