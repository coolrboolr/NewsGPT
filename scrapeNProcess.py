import os

import requests
from bs4 import BeautifulSoup
from openai import OpenAI
from prisma import Prisma
from prisma.models import Article
from prisma.types import ArticleCreateInput
import feedparser
import praw
import json

if os.environ.get('OPENAI_API_KEY') is None:
    # pull in openai key securely
    with open('pass/OPENAI_API_KEY', 'r') as f:
        os.environ['OPENAI_API_KEY'] = f.read()
        print('OPENAI_API_KEY is imported from local store')

# set up openai client to be used for chat completion
openai_client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))
print('OpenAI client created')

cat = {
    'world_news': {'source': None, 'category': None, 'keyword': None, 'country': 'us'},
    'bbc_world': {'source': 'bbc-news', 'category': None, 'keyword': None, 'country': None},
    'bbc_business': {'source': 'bbc-news', 'category': 'business', 'keyword': None, 'country': None},
    'cnn_latest': {'source': 'cnn', 'category': None, 'keyword': None, 'country': None},
}

def scrape_newsapi(cat_key) -> list[ArticleCreateInput]:
    config = cat.get(cat_key, {})
    source=config.get('source')
    category=config.get('category')
    keyword=config.get('keyword')
    country=config.get('country')
        
    base_url = "https://newsapi.org/v2/top-headlines?"
    params = []

    # Construct query based on provided filters
    if country:
        params.append(f"country={country}")
    if category:
        params.append(f"category={category}")
    if keyword:
        params.append(f"q={keyword}")
    if source:
        params.append(f"sources={source}")
    
    if not params:
        raise ValueError("You must provide at least one filter: country, category, keyword, or source.")

    # Combine parameters to form the final URL
    url = base_url + '&'.join(params)
    url += f"&apiKey={os.environ.get('NEWSAPIKEY')}"
    
    r = requests.get(url)
    feed = json.loads(r.text)['articles']
    articles: list[ArticleCreateInput] = []
    # Loop through the first 10 entries
    for entry in feed[:10]:
        title = entry['title']
        url = entry['url']
        published = entry['publishedAt']

        # Because you have the begining of the article with this \
        # method you can zone in on the element that has the body of the article
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
                'category': cat_key,
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
    
    scraped_articles = scrape_newsapi(cat_key)

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
                        'category': article['category'],
                    })
                except Exception as e:
                    print(f'Failed adding {article["title"]} due to exception:\n{e}')

    return processed_articles


if __name__ == '__main__':
    print('Running fetch and process')
    # p = Prisma(auto_register=False)
    # p.connect()
    # for key in cat.keys():
    #     fetch_and_process_articles(key)
    # p.disconnect()
    
    

    p = fetch_and_process_articles('bbc_world')
