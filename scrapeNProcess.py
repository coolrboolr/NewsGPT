import requests
from bs4 import BeautifulSoup
from openai import OpenAI
import feedparser
import praw

# pull in openai key securely
with open('OPENAI_KEY', 'r') as f:
    __openai_key__ = f.read()

# pull in reddit 
with open('REDDIT_API', 'r') as f1:
    __reddit_api__ = f1.read()

# set up openai client to be used for chat completion
openai_client = OpenAI(
    # This is the default and can be omitted
    api_key=__openai_key__
)

# set up reddit parser
reddit = praw.Reddit(
    client_id='hR4QiXaef7FinpNaKJ6A4g',
    client_secret=__reddit_api__,
    user_agent='NewsGPT',
    username='coolrboolr456',
    password='Cr4zyeight'
)

# pull top articles for /r/worldnews and then get the urls for the bodies be parsed
def scrape_worldnews():
    articles = []
    for submission in reddit.subreddit('worldnews').hot(limit=10):  # Adjust limit as needed
        if 'www.reddit.com' not in submission.url: #remove the internal reddit links
            url = submission.url

            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(r.content,'html.parser')
            article_body = soup.text
            articles.append({
                'title': submission.title,
                'url': submission.url,
                'body': article_body
                
            })
        else:
            print(f'Just reddit links - internal discussion usually: {submission.title}')
    return articles

# process all the article bodies into better short headlines
def summarize_article(article_content):
    response = openai_client.chat.completions.create(
    messages=[
        {   'role': 'system', 
            'content': 'You are an expert researcher, use your knowledge about the world the accurate and precisely distill the article below. Your goal is ensure the reader knows exactly what the article is about by it\'s new headline'},
        {
            'role': 'user',
            'content': f'Create a new headline for the article below. Use less than 10 words. \n\narticle: {article_content}',
        }
    ],
    model='gpt-3.5-turbo',
)
    return response.choices[0].message.content

# pull all the articles and then use summarize article to process the new headlines
def fetch_and_process_articles():
    scraped_articles = scrape_worldnews()
    processed_articles = []
    for article in scraped_articles:
        # For simplicity, we're using the article title as content; in practice, fetch the article content
        summary = summarize_article(article['body'])
        processed_articles.append({'title': article['title'], 'url': article['url'], 'headline': summary,}) #saving the original so we can compare for now, eventually add a summary of the article as well
    return processed_articles

if __name__ == '__main__':
    print('pulled in fetch and process')
    #p_articles = fetch_and_process_articles() # test for interactive console