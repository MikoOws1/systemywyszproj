from flask import Flask, render_template, request
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import re
import sqlite3
import matplotlib
matplotlib.use('Agg')  # Wymuszenie backendu non-GUI
import matplotlib.pyplot as plt
import io
from nltk.sentiment import SentimentIntensityAnalyzer
from wordcloud import WordCloud
import base64
import nltk
nltk.download('vader_lexicon')



# Initialize Flask app
app = Flask(__name__)

# Configure SQLite database
DATABASE = 'airlines_reviews.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Load and preprocess the data
def load_data():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM airlines_reviews", conn)
    conn.close()

    # Remove "N/A" values
    df.replace("N/A", "", inplace=True)

    # Clean titles
    df['Tytul_opinii'] = df['Tytul_opinii'].apply(
        lambda x: re.sub(r'\b[A-Za-z ]+ customer review', "", x, flags=re.IGNORECASE)
    )

    # Remove quotation marks from titles
    df['Tytul_opinii'] = df['Tytul_opinii'].str.replace('"', '')

    # Combine columns for full-text search
    df['Combined'] = df['Tytul_opinii'] + " " + df['Tresc_opinii']

    return df

# Global data frame
data = load_data()

# Extract unique values for dropdown filters
def get_filter_options():
    airlines = data['Linia_lotnicza'].dropna().unique().tolist()
    airplane_classes = data['Samolot'].dropna().unique().tolist()
    trip_types = data['Typ_podrozy'].dropna().unique().tolist()
    routes = data['Trasa'].dropna().unique().tolist()
    return {
        'airlines': airlines,
        'airplane_classes': airplane_classes,
        'trip_types': trip_types,
        'routes': routes
    }

filter_options = get_filter_options()

# Home route
@app.route("/")
def home():
    return render_template("index.html")

# Search route
@app.route("/search", methods=["GET", "POST"])
def search():
    results = []
    selected_metric = "cosine"  # Default similarity metric

    # Default form values
    query = ""
    metric = "cosine"
    limit = 10
    scope = "combined"
    verified = ""
    recommendation = ""
    airline = ""
    date_range = ""
    airplane_class = ""
    trip_type = ""
    travel_date_range = ""
    route = ""

    if request.method == "POST":
        # Retrieve form data
        query = request.form.get("query")
        metric = request.form.get("metric")
        limit = int(request.form.get("limit", 10))
        scope = request.form.get("scope", "combined")
        verified = request.form.get("verified")
        recommendation = request.form.get("recommendation")
        airline = request.form.get("airline")
        date_range = request.form.get("date_range")
        airplane_class = request.form.get("airplane_class")
        trip_type = request.form.get("trip_type")
        travel_date_range = request.form.get("travel_date_range")
        route = request.form.get("route")

        # Work on a copy of the data
        data_copy = data.copy()

        # Apply filters
        if verified:
            data_copy = data_copy[data_copy['Podroz_zweryfikowana'] == int(verified)]

        if recommendation:
            data_copy = data_copy[data_copy['Rekomendacja'].str.lower() == recommendation.lower()]

        if airline:
            data_copy = data_copy[data_copy['Linia_lotnicza'] == airline]

        if date_range:
            try:
                start_date, end_date = date_range.split(" to ")
                data_copy = data_copy[(data_copy['Data_publikacji'] >= start_date) & (data_copy['Data_publikacji'] <= end_date)]
            except ValueError:
                pass  # Invalid date range, skip filtering

        if airplane_class:
            data_copy = data_copy[data_copy['Samolot'] == airplane_class]

        if trip_type:
            data_copy = data_copy[data_copy['Typ_podrozy'] == trip_type]

        if travel_date_range:
            try:
                start_date, end_date = travel_date_range.split(" to ")
                data_copy = data_copy[(data_copy['Data_podrozy'] >= start_date) & (data_copy['Data_podrozy'] <= end_date)]
            except ValueError:
                pass  # Invalid travel date range, skip filtering

        if route:
            data_copy = data_copy[data_copy['Trasa'] == route]

        # Filter data based on scope
        if scope == "title":
            corpus = data_copy['Tytul_opinii']
        elif scope == "content":
            corpus = data_copy['Tresc_opinii']
        else:
            corpus = data_copy['Combined']
        
        # Calculate TF-IDF with stop words
        tfidf = TfidfVectorizer(stop_words='english')
        tfidf_matrix = tfidf.fit_transform(corpus)

        # Query vector
        query_vec = tfidf.transform([query])

        # Calculate similarity
        if metric == "cosine":
            similarities = cosine_similarity(query_vec, tfidf_matrix).flatten()
            selected_metric = "cosine"
        elif metric == "jaccard":
            similarities = [
                jaccard_similarity(query, doc) for doc in corpus
            ]
            selected_metric = "jaccard"
        
        # Sort results by similarity
        data_copy["Similarity"] = similarities
        data_copy = data_copy[data_copy["Similarity"] > 0]
        results = data_copy.sort_values(by="Similarity", ascending=False).head(limit).to_dict(orient="records")

    return render_template("search.html", results=results, metric=selected_metric, query=query, limit=limit, scope=scope, verified=verified, recommendation=recommendation, airline=airline, date_range=date_range, airplane_class=airplane_class, trip_type=trip_type, travel_date_range=travel_date_range, route=route, filter_options=filter_options)

# Analytics route
@app.route("/analytics", methods=["GET", "POST"])
def analytics():
    airlines = filter_options['airlines']
    selected_airline = ""
    include_sentiment = False
    summary = {}
    sentiment_chart = None
    chart_data = None

    if request.method == "POST":
        selected_airline = request.form.get("airline")
        include_sentiment = request.form.get("sentiment") == "on"

        # Filter data for the selected airline
        filtered_data = data[data['Linia_lotnicza'] == selected_airline]

        # Calculate averages for numeric columns
        summary = {
            "Avg Seat Rating": filtered_data['Ocena_siedzenia'].astype(float).mean(),
            "Avg Food Rating": filtered_data['Ocena_jedzenia'].astype(float).mean(),
            "Avg Ground Service Rating": filtered_data['Ocena_oblsugi_naziemnej'].astype(float).mean(),
            "Avg Cabin Crew Rating": filtered_data['Ocena_cabin_crew'].astype(float).mean(),
            "Avg Value for Money": filtered_data['Jakosc_do_ceny'].astype(float).mean(),
        }

        # Clean and calculate 'Avg Overall Rating'
        filtered_data.loc[:, 'Ocena_ogolna'] = pd.to_numeric(filtered_data['Ocena_ogolna'], errors='coerce')
        summary["Avg Overall Rating"] = (filtered_data['Ocena_ogolna'].mean())/2
        # Generate bar chart for averages (scale to 5)
        labels = ["Seat Rating", "Food Rating", "Ground Service", "Cabin Crew", "Value for Money", "Overall Rating"]
        values = [
            summary["Avg Seat Rating"],
            summary["Avg Food Rating"],
            summary["Avg Ground Service Rating"],
            summary["Avg Cabin Crew Rating"],
            summary["Avg Value for Money"],
            summary["Avg Overall Rating"],  # Dodanie Overall Rating do wykresu
        ]

        # Kolory dla każdego słupka
        colors = ["skyblue", "orange", "green", "red", "purple", "gold"]

        plt.figure(figsize=(10, 6))
        plt.bar(labels, values, color=colors)
        plt.title(f"Average Ratings for {selected_airline}")
        plt.ylabel("Rating (out of 5)")
        plt.ylim(0, 5)  # Force scaling to 5
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()

        img = io.BytesIO()
        plt.savefig(img, format="png")
        img.seek(0)
        chart_data = base64.b64encode(img.getvalue()).decode()
        plt.close()

        # Sentiment analysis
        if include_sentiment:
            sia = SentimentIntensityAnalyzer()
            positive, neutral, negative = 0, 0, 0

            for review in filtered_data['Tresc_opinii'].dropna():
                sentiment = sia.polarity_scores(review)
                if sentiment['compound'] > 0.05:
                    positive += 1
                elif sentiment['compound'] < -0.05:
                    negative += 1
                else:
                    neutral += 1

            # Generate pie chart for sentiment analysis
            sentiment_labels = ["Positive", "Neutral", "Negative"]
            sentiment_values = [positive, neutral, negative]

            plt.figure(figsize=(6, 6))
            plt.pie(sentiment_values, labels=sentiment_labels, autopct="%1.1f%%", colors=["green", "grey", "red"])
            plt.title(f"Sentiment Analysis for {selected_airline}")

            sentiment_img = io.BytesIO()
            plt.savefig(sentiment_img, format="png")
            sentiment_img.seek(0)
            sentiment_chart = base64.b64encode(sentiment_img.getvalue()).decode()
            plt.close()

    return render_template(
        "analytics.html",
        airlines=airlines,
        selected_airline=selected_airline,
        summary=summary,
        chart_data=chart_data,
        sentiment_chart=sentiment_chart
    )

@app.route("/wordcloud", methods=["GET", "POST"])
def wordcloud():
    airlines = filter_options['airlines']  # Lista dostępnych linii lotniczych
    selected_airline = None
    cloud_image = None

    if request.method == "POST":
        selected_airline = request.form.get("airline")

        # Filtruj dane według wybranej linii lotniczej lub użyj wszystkich opinii
        if selected_airline:
            filtered_data = data[data['Linia_lotnicza'] == selected_airline]
        else:
            filtered_data = data

        # Połącz oczyszczone tytuły i treści opinii
        corpus = filtered_data['Tytul_opinii'] + " " + filtered_data['Tresc_opinii']
        corpus = corpus.dropna().tolist()

        # Przygotowanie TF-IDF z usunięciem stop-słów
        vectorizer = TfidfVectorizer(stop_words="english", max_features=1000)
        tfidf_matrix = vectorizer.fit_transform(corpus)

        # Pobranie słów i ich wag
        words = vectorizer.get_feature_names_out()
        weights = tfidf_matrix.sum(axis=0).A1  # Sumuj wagi dla każdego słowa

        # Utworzenie słownika słów z wagami
        word_weights = dict(zip(words, weights))

        # Generowanie chmury słów
        wordcloud = WordCloud(
            width= 1200,
            height=600,
            background_color="white",
            colormap="viridis"
        ).generate_from_frequencies(word_weights)

        # Konwertowanie chmury na obraz
        img = io.BytesIO()
        wordcloud.to_image().save(img, format="PNG")
        img.seek(0)
        cloud_image = base64.b64encode(img.getvalue()).decode()

    return render_template(
        "wordcloud.html",
        airlines=airlines,
        selected_airline=selected_airline,
        cloud_image=cloud_image
    )


def jaccard_similarity(query, document):
    query_set = set(query.split())
    document_set = set(document.split())
    return len(query_set & document_set) / len(query_set | document_set)

if __name__ == "__main__":
    app.run(debug=True)
