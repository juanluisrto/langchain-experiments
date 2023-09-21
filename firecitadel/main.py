import json, logging, random


# Configure the root logger to log at the "INFO" level
logging.basicConfig(level=logging.INFO)

from urllib.parse import urlparse, parse_qs
from flask import redirect
import functions_framework

from utils import *

@functions_framework.http
def dream_story(request):
    # Extract the "style" and "environment" parameters if present
    style, environment = extract_parameters_from_url(request.url)

    with open("templates.json", "r+") as fp:
        templates = json.load(fp)
        styles = templates["styles"]
        environments = templates["environments"]
    if style is None:
        style = random.choice(styles)
    if environment is None:
        environment = random.choice(environments)
    logging.info(f"Generating image with {style} style, in a {environment} environment")
    
    story_chain = create_storyteller_chain()
    
    def more_than_n_characters(text, n = 280):
        return len(text) > n
    
    # Generate Story
    cant_be_tweeted = True
    while cant_be_tweeted:
        story = story_chain.run({"style" : style, "environment" : environment})
        if cant_be_tweeted := more_than_n_characters(story):
            logging.warning(f"The story has {len(story)} characters. Trying again")
        else:
            logging.info(f"Story: {story}")
        
    # We skip this step since the story is good enough to generate images
    #
    # Generate Description of the story
    #
    #img_chain = create_imagedescription_chain()
    #img_description = img_chain.run(story)
    #logging.info(f"Scene description: {img_description}")
    
    
    # Generate image
    image_urls = text_to_image(story, model = MODELS.STABLE_DIFFUSION, negative_prompt=NEGATIVE_PROMPT)
    url = image_urls[0]
    
    logging.info(f"Generated image: {url}")
    
    
    # Upload image and publish tweet
    
    tw_client = get_tweepy_client()
    api = get_tweepy_API()
    
    media = upload_image_to_twitter(url, api)
    
    tweet_response = tw_client.create_tweet(
        text = story,
        media_ids = [media.media_id]
    )
    tweet_url = f"https://twitter.com/firecitadel/status/{tweet_response.data['id']}"
    return redirect(tweet_url)

def extract_parameters_from_url(url):
    # Parse the URL
    parsed_url = urlparse(url)

    # Get the query parameters as a dictionary
    query_params = parse_qs(parsed_url.query)

    # Extract the "style" and "environment" parameters if present
    style = query_params.get('style', [None])[0]
    environment = query_params.get('environment', [None])[0]

    return style, environment