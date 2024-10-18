import requests
from google.cloud import datastore, storage
from newsapi import NewsApiClient
from datetime import datetime
import json
import matplotlib.pyplot as plt

#google cloud project ID and bucket name
PROJECT_ID = 'linear-listener-436516-c9'
BUCKET_NAME = 'news_4099'

#initialize the datastore and storage clients
datastore_client = datastore.Client(project=PROJECT_ID)
storage_client = storage.Client(project=PROJECT_ID)

#news API key
NEWS_API_KEY = '20ba84b32c674632bab001f2eb292c73'

#initialize news client
newsapi = NewsApiClient(api_key=NEWS_API_KEY)


######
###### Space for app engine connection (using placeholder sentiment score for now)
######def call_app_engine_sentiment(text):
    #"""Send the article's text to App Engine for sentiment scoring."""
    #response = requests.post(SENTIMENT_API_URL, json={'text': text})

    #if response.status_code == 200:
        #sentiment_score = response.json().get('sentiment_score', 0)
        #return sentiment_score
    #else:
        #print(f"Error: Failed to get sentiment score, status code: {response.status_code}")
        #return 0

#sentiment_score = call_vm_sentiment(article['content'] or article['description'] or '')

#SENTIMENT_API_URL = 'http://<your-vm-ip>:<port>/path_running'
#external IP of VM: 34.69.122.74

def fetch_news(topic):
    articles = newsapi.get_everything(q=topic, language='en', sort_by='publishedAt', page_size=5)
    #check if any articles are found
    if not articles['articles']:
        print(f"No news found for the topic: {topic}")
        return []

    return articles['articles']

def upload_to_bucket(bucket_name, content, destination_blob_name):
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    
    blob.upload_from_string(content, content_type='application/json')
    print(f"Uploaded file to {destination_blob_name} in {bucket_name} bucket.")

def upload_image_to_bucket(bucket_name, file_path, destination_blob_name):
    #upload plot image to bucket
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(destination_blob_name)
    
    blob.upload_from_filename(file_path)
    print(f"Uploaded image to {destination_blob_name} in {bucket_name} bucket.")

#store news data
def store_news_data(article, topic, sequential_num):
    #create with kind 'newsData'
    entity = datastore.Entity(datastore_client.key('newsData'))

    sentiment_score = 0  #placeholder sentiment score

    #prepare file name for storage
    date = datetime.now().strftime('%Y-%m-%d')
    file_name = f"news_{topic}_{date}_{sequential_num}.json"

    #store the article content in the bucket
    article_content = json.dumps(article)
    upload_to_bucket(BUCKET_NAME, article_content, file_name)

    #set the properties of the entity with news data and sentiment
    entity.update({
        'topic': topic,                              #news topic
        'title': article['title'],                   #news article title
        'description': article['description'],       #short description
        'sentiment_score': round(sentiment_score, 2),#placeholder sentiment score
        'url': article['url'],                       #URL
        'published_at': article['publishedAt'],      #publish date
        'file_name': file_name,                      #stored file's name in the bucket
        'timestamp': datetime.utcnow()               #timestamp
    })

    #save entity to datastore
    datastore_client.put(entity)
    print(f"Stored article and sentiment for: {article['title']}")

def retrieve_news_data():
    #retrieve
    query = datastore_client.query(kind='newsData')
    results = query.fetch()

    #store data for graphing
    dates = []
    sentiment_scores = []

    #prepare for plotting
    for entity in results:
        print(f"{entity['published_at']} - {entity['title']}")
        print(f"Sentiment Score: {entity['sentiment_score']}, URL: {entity['url']}")
        print(f"Description: {entity['description']}\n")
        
        #append the date and sentiment score for graphing
        dates.append(entity['published_at'])
        sentiment_scores.append(entity['sentiment_score'])

    return dates, sentiment_scores

def plot_sentiment(dates, sentiment_scores):
    #plot sentiment scores
    if not dates or not sentiment_scores:
        print("No data available to plot.")
        return

    #plot setup
    plt.figure(figsize=(10, 6))
    plt.plot(dates, sentiment_scores, marker='o')
    plt.title('Sentiment Analysis over Time for Webster Bank (WBS)')
    plt.xlabel('Date')
    plt.ylabel('Sentiment Score')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()

    #save the plot as png
    image_filename = "sentiment_plot.png"
    plt.savefig(image_filename)
    print(f"Plot saved as {image_filename}")

    #upload the plot to the bucket
    upload_image_to_bucket(BUCKET_NAME, image_filename, image_filename)

if __name__ == '__main__':
    news_topic = 'WBS'  #Webster Bank ticker

    #fetch
    news_articles = fetch_news(news_topic)

    #store in the bucket and datastore
    for i, article in enumerate(news_articles):
        store_news_data(article, news_topic, i)

    #retrieve and display all stored news data
    dates, sentiment_scores = retrieve_news_data()

    #plot the sentiment scores (placeholders for now)
    plot_sentiment(dates, sentiment_scores)
