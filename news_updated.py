import requests
from google.cloud import datastore, storage
from newsapi import NewsApiClient
from datetime import datetime
import json
import matplotlib.pyplot as plt
from sentiment import analyze_sentiment  #import sentiment analysis from sentiment.py

#ID and bucket
PROJECT_ID = 'linear-listener-436516-c9'
BUCKET_NAME = 'news_4099'

#datastore and storage clients
datastore_client = datastore.Client(project=PROJECT_ID)
storage_client = storage.Client(project=PROJECT_ID)

#news API key
NEWS_API_KEY = '20ba84b32c674632bab001f2eb292c73'

#news client
newsapi = NewsApiClient(api_key=NEWS_API_KEY)

#fetch news function
def fetch_news(topic):
    articles = newsapi.get_everything(q=topic, language='en', sort_by='publishedAt', page_size=5)
    if not articles['articles']:
        print(f"No news found for the topic: {topic}")
        return []
    return articles['articles']

#upload news content to bucket
def upload_to_bucket(bucket_name, content, destination_blob_name):
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_string(content, content_type='application/json')
    print(f"Uploaded file to {destination_blob_name} in {bucket_name} bucket.")

#upload image to bucket
def upload_image_to_bucket(bucket_name, file_path, destination_blob_name):
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    blob.upload_from_filename(file_path)
    print(f"Uploaded image to {destination_blob_name} in {bucket_name} bucket.")

#store news and sentiment score
def store_news_data(article, topic, sequential_num):
    entity = datastore.Entity(datastore_client.key('newsData'))
    sentiment_score = analyze_sentiment(article['content'] or article['description'] or '')

    #prepare file name
    date = datetime.now().strftime('%Y-%m-%d')
    file_name = f"news_{topic}_{date}_{sequential_num}.json"
    
    #upload article content to bucket
    article_content = json.dumps(article)
    upload_to_bucket(BUCKET_NAME, article_content, file_name)

    #set properties of entity
    entity.update({
        'topic': topic,
        'title': article['title'],
        'description': article['description'],
        'sentiment_score': sentiment_score,
        'url': article['url'],
        'published_at': article['publishedAt'],
        'file_name': file_name,
        'timestamp': datetime.utcnow()
    })

    #save entity to datastore
    datastore_client.put(entity)
    print(f"Stored article and sentiment for: {article['title']}")

    #upload scored version of the file
    scored_file_name = f"scored_{file_name}"
    upload_to_bucket(BUCKET_NAME, json.dumps({'sentiment_score': sentiment_score}), scored_file_name)

#retrieve news data and sentiment scores from datastore
def retrieve_news_data():
    query = datastore_client.query(kind='newsData')
    results = query.fetch()

    dates = []
    sentiment_scores = []

    for entity in results:
        print(f"{entity['published_at']} - {entity['title']}")
        print(f"Sentiment Score: {entity['sentiment_score']}, URL: {entity['url']}")
        print(f"Description: {entity['description']}\n")
        dates.append(entity['published_at'])
        sentiment_scores.append(entity['sentiment_score'])

    return dates, sentiment_scores

#plot sentiment analysis
def plot_sentiment(dates, sentiment_scores):
    if not dates or not sentiment_scores:
        print("No data available")
        return

    plt.figure(figsize=(10, 6))
    plt.plot(dates, sentiment_scores, marker='o')
    plt.title('Sentiment Analysis for Webster Bank (WBS)')
    plt.xlabel('Date')
    plt.ylabel('Sentiment Score')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()

    image_filename = "sentiment.png"
    plt.savefig(image_filename)
    print(f"Plot saved as {image_filename}")

    #upload the plot to the bucket
    upload_image_to_bucket(BUCKET_NAME, image_filename, image_filename)

if __name__ == '__main__':
    news_topic = 'WBS'  #webster bank ticker

    #fetch news articles
    news_articles = fetch_news(news_topic)

    #store articles and sentiment scores
    for i, article in enumerate(news_articles):
        store_news_data(article, news_topic, i)

    #retrieve stored news data and sentiment scores for plotting
    dates, sentiment_scores = retrieve_news_data()

    #plot the sentiment scores
    plot_sentiment(dates, sentiment_scores)
