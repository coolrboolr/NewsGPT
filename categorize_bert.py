from prisma import Prisma
from bertopic import BERTopic
import numpy as np
import spacy
from nltk.corpus import stopwords
import code

# Initialize Prisma Client
client = Prisma()
client.connect()

# Initialize BERTopic
topic_model = BERTopic()


# Load SpaCy model for lemmatization
nlp = spacy.load("en_core_web_sm")

# Load NLTK stopwords
stop_words = set(stopwords.words('english'))

def fetch_articles(cat = ''):
    # Fetch articles without categories from the database
    return client.article.find_many(
        where={
            'category': cat,
        },
        
    )

def preprocess_text(text):
    doc = nlp(text)
    lemmatized = [token.lemma_ for token in doc if token.is_alpha and token.lower_ not in stop_words]
    return ' '.join(lemmatized)

def generate_category_title(topic_model, topic_num, max_length=45):
    topic_words = topic_model.get_topic(topic_num)
    if topic_words:
        words = [word for word, _ in topic_words[:5]]  # Get top 5 words
        title = ' '.join(words)
        if len(title) > max_length:
            title = title[:max_length].rsplit(' ', 1)[0]  # Truncate to the last full word within the limit
        return title
    return f"Category_{topic_num}"

def perform_topic_modeling(docs):
    # Preprocess the documents
    preprocessed_docs = [preprocess_text(doc) for doc in docs]

    # Perform topic modeling on the documents
    topics, probs = topic_model.fit_transform(preprocessed_docs)
    
    # Generate category names from topics
    topic_info = topic_model.get_topic_info()
    topic_names = {}
    for topic_num in topic_info['Topic']:
        if topic_num != -1:  # Ignore outliers
            category_title = generate_category_title(topic_model, topic_num)
            topic_names[topic_num] = category_title
    
    return topics, probs, topic_names

def update_article_category(article_id, category):
    # Update article category in the database
    client.article.update(
        where={
            'id': article_id,
        },
        data={
            'category': category,
        }
    )

def main():
    articles = fetch_articles()
    if not articles:
        print("No articles need updating.")
        return

    # Extract bodies for topic modeling
    docs = [article.body for article in articles]
    
    # Fit the model if it hasn't been fitted or load if already trained
    topics, probs = topic_model.fit_transform(docs)

    # Update categories based on most probable topic
    for article, topic in zip(articles, topics):
        category = f"Category_{topic}"
        update_article_category(article['id'], category)

    print("Article categories updated.")

if __name__ == "__main__":
    try: 
        #main()
        print('hi!')
        a = fetch_articles('world_news')
        docs = [article.body for article in a]
        topics, probs, topic_names = perform_topic_modeling(docs)
        print("Article categories updated.")
        #code.interact(local=locals())
    except Exception as e: 
        print(f'Failed\n\n{e}')
        client.disconnect()
        raise

# Close the database connection
client.disconnect()
