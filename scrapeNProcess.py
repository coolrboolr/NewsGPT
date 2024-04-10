import os

import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from prisma import Prisma
from prisma.models import Article
import feedparser
import praw

if os.environ.get('OPENAI_API_KEY') is None:
    # pull in openai key securely
    with open('pass/OPENAI_API_KEY', 'r') as f:
        os.environ['OPENAI_API_KEY'] = f.read()
        print('OPENAI_API_KEY is imported from local store')

if os.environ.get('REDDIT_API') is None:
    # pull in reddit
    with open('pass/REDDIT_API', 'r') as f1:
        os.environ['REDDIT_API'] = f1.read()
        print('REDDIT_API is imported from local store')

if os.environ.get('REDDIT_PASS') is None:
    # pull in reddit
    with open('pass/REDDIT_PASS', 'r') as f1:
        os.environ['REDDIT_PASS'] = f1.read()
        print('REDDIT_PASS is imported from local store')

# set up openai client to be used for chat completion
openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
print('OpenAI client created')

# set up reddit parser
reddit = praw.Reddit(
    client_id='hR4QiXaef7FinpNaKJ6A4g',
    client_secret=os.environ.get('REDDIT_API'),
    user_agent='NewsGPT',
    username='coolrboolr456',
    password=os.environ.get('REDDIT_PASS')
)
print('Reddit client created')

cat = {'world_news'     : 'world_news', 
       'bbc_world'      : 'https://feeds.bbci.co.uk/news/world/rss.xml', 
       'bbc_business'   : 'https://feeds.bbci.co.uk/news/business/rss.xml'}


# pull top articles for /r/worldnews and then get the urls for the bodies be parsed
def scrape_worldnews():
    articles = []
    for submission in reddit.subreddit('worldnews').hot(limit=12):  # Adjust limit as needed
        if 'www.reddit.com' not in submission.url:  #remove the internal reddit links
            url = submission.url

            r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
            soup = BeautifulSoup(r.content, 'html.parser')
            article_body_raw = soup.text.replace('\n', '')
            #cleaning non utf8 characters
            article_body = article_body_raw.encode('utf-8', 'ignore').decode('utf-8')

            if len(article_body) > 1000:
                articles.append({
                    'title': submission.title,
                    'url': submission.url,
                    'body': article_body,
                    'category' : 'world_news'
                })
            else:
                print(
                    'Too short - body scrape needs revision Title : '
                    f'{submission.title}\nurl: {submission.url}'
                )

        else:
            print(f'Just reddit links - internal discussion usually: {submission.title}')
    return articles


def scrape_rss(cat_key):
    url = cat[cat_key]
    feed = feedparser.parse(url)
    articles = []
    # Loop through the first 10 entries
    for entry in feed.entries[:10]:
        title = entry.title
        url = entry.link

        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(r.content, 'html.parser')
        article_body_raw = soup.text.replace('\n', '')
        #cleaning non utf8 characters
        article_body = article_body_raw.encode('utf-8', 'ignore').decode('utf-8')

        if len(article_body) > 1000:
            articles.append({
                'title': title,
                'url': url,
                'body': article_body,
                'category' : cat_key
            })
            print(f'pulled article from rss feed at {url}')
        else:
            print(f'Too short - body scrape needs revision Title : {title}\nurl: {url}')

    return articles


# process all the article bodies into better short headlines
def summarize_article(article_content):
    print(f"Summarizing article: {article_content.replace('\n','')[:50]}...")
    response = openai_client.chat.completions.create(
        messages=[{
            'role': 'system',
            'content':
                'You are an expert researcher, use your knowledge about the world to accurately '
                'and precisely distill the article below. Your goal is ensure the reader knows '
                'exactly what the article is about by it\'s new headline',
        }, {
            'role': 'user',
            'content':
                'Create a new headline for the article below. '
                f'Use less than 14 words.\n\narticle: {article_content}',
        }],
        model='gpt-3.5-turbo',
    )
    if not (new_headline := response.choices[0].message.content):
        raise RuntimeError('No response from ChatGPT')
    if (new_headline[0] == '"') and (new_headline[-1] == '"'):
        new_headline = new_headline[1:-1]

    print(f'Generated summary: {new_headline}')
    return new_headline


# pull all the articles and then use summarize article to process the new headlines
def fetch_and_process_articles(cat_key='world_news'):
    if cat_key == 'world_news':
        scraped_articles = scrape_worldnews()
    else:
        scraped_articles = scrape_rss(cat_key)
    print('pulled in articles')
    processed_articles = []

    for article in scraped_articles:
        #if the article is present in the db (search by url) then used the the stored headline
        existing_article = Article.prisma().find_unique({'url': article['url']})

        if existing_article and existing_article.headline:
            print(f'Existing article found')
            print(f'Title: {existing_article.title}')
            print(f'Headline: {existing_article.headline}')

            print('Found an existing article and headline, populating without call')
            processed_articles.append({
                'title': article['title'],
                'url': article['url'],
                'body': article['body'],
                'headline': existing_article.headline,
            })
        else:  # otherwise run the openai call and bring in a headline to be stored
            print('No headline found, running call')
            summary = summarize_article(article['body'])
            # Saving the original so we can compare for now, eventually add a summary of the article as well
            processed_articles.append({
                'title': article['title'],
                'url': article['url'],
                'body': article['body'],
                'headline': summary,
            })
            if existing_article:  # if there was just an article but no headline, update the record
                print('There was an existing article but no headline, updating current line')
                existing_article.headline = summary
            else:  # if this is a completely new article then add the record to the db
                try:
                    print('Net new article, storing in db as new line')
                    Article.prisma().create({
                        'title': article['title'],
                        'url': article['url'],
                        'body': article['body'],
                        'headline': summary,
                    })
                except Exception as e:
                    print(f'Failed adding {article["title"]} due to exception:\n{e}')

    return processed_articles


if __name__ == '__main__':
    print('Running fetch and process')
    p = Prisma(auto_register=True)
    p.connect()
    for key in cat.keys():
        fetch_and_process_articles(cat[key])
    p.disconnect()
    #rss_feed = 'https://feeds.bbci.co.uk/news/world/rss.xml'
    #a = scrape_rss(rss_feed)
    #print(a)
