import requests
from bs4 import BeautifulSoup
import csv

def scrape_airline_reviews(base_url, output_file, max_reviews):
    # Nagłówki HTTP dla requests
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    review_data = []
    page = 1

    while len(review_data) < max_reviews:
        url = f"{base_url}page/{page}/"
        response = requests.get(url, headers=headers)
        
        if response.status_code != 200:
            print(f"Błąd pobierania strony: {response.status_code}")
            break

        soup = BeautifulSoup(response.content, 'html.parser')

        # Znajdź wszystkie sekcje z opiniami
        reviews = soup.find_all('article', class_='comp_media-review-rated')

        if not reviews:
            print("Brak więcej opinii do przetworzenia.")
            break

        for review in reviews:
            if len(review_data) >= max_reviews:
                break

            # Pobieranie danych szczegółowych
            title = review.find('h2', class_='text_header').text.strip() if review.find('h2', class_='text_header') else 'Brak tytułu'
            body = review.find('div', class_='text_content').text.strip() if review.find('div', class_='text_content') else 'Brak treści'
            
            # Sprawdź obecność "Trip Verified"
            trip_verified = "yes" if "Trip Verified" in body else "no"
            body = body.replace("✅ Trip Verified |", "").strip()

            rating = review.find('span', itemprop='ratingValue').text.strip() if review.find('span', itemprop='ratingValue') else 'Brak oceny'
            author = review.find('span', itemprop='name').text.strip() if review.find('span', itemprop='name') else 'Anonim'
            date_published = review.find('time', itemprop='datePublished')['datetime'] if review.find('time', itemprop='datePublished') else 'Brak daty'
            recommendation = review.find('td', class_='review-value rating-yes').text.strip() if review.find('td', class_='review-value rating-yes') else (
                review.find('td', class_='review-value rating-no').text.strip() if review.find('td', class_='review-value rating-no') else 'N/A'
            )

            # Szczegóły lotu i oceny
            flight_details = {
                'Aircraft': 'N/A',
                'Type Of Traveller': 'N/A',
                'Route': 'N/A',
                'Date Flown': 'N/A',
                'Seat Comfort': 'N/A',
                'Food & Beverages': 'N/A',
                'Ground Service': 'N/A',
                'Cabin Staff Service': 'N/A',
                'Value For Money': 'N/A'
            }
            for row in review.find_all('tr'):
                header = row.find('td', class_='review-rating-header')
                value = row.find('td', class_='review-value')
                stars = row.find('td', class_='review-rating-stars')

                if header and value:
                    flight_details[header.text.strip()] = value.text.strip()
                elif header and stars:
                    flight_details[header.text.strip()] = len(stars.find_all('span', class_='star fill'))

            # Dodaj dane do listy
            review_data.append({
                'Tytuł opinii': title,
                'Treść opinii': body,
                'Trip Verified': trip_verified,
                'Ocena (10)': rating,
                'Autor': author,
                'Data publikacji': date_published,
                'Rekomendacja': recommendation,
                'Samolot': flight_details.get('Aircraft', 'N/A'),
                'Typ podróży': flight_details.get('Type Of Traveller', 'N/A'),
                'Trasa': flight_details.get('Route', 'N/A'),
                'Data podróży': flight_details.get('Date Flown', 'N/A'),
                'Ocena siedzenia': flight_details.get('Seat Comfort', 'N/A'),
                'Ocena jedzenia': flight_details.get('Food & Beverages', 'N/A'),
                'Ocena ground staffu': flight_details.get('Ground Service', 'N/A'),
                'Ocena cabin staff': flight_details.get('Cabin Staff Service', 'N/A'),
                'Value for money': flight_details.get('Value For Money', 'N/A')
            })

        print(f"Przetworzono stronę {page}, zebrano {len(review_data)} opinii.")
        page += 1

    # Zapisz dane do pliku CSV
    with open(output_file, mode='w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'Tytuł opinii', 'Treść opinii', 'Trip Verified', 'Ocena (10)', 'Autor', 'Data publikacji', 'Rekomendacja',
            'Samolot', 'Typ podróży', 'Trasa', 'Data podróży',
            'Ocena siedzenia', 'Ocena jedzenia', 'Ocena ground staffu', 'Ocena cabin staff', 'Value for money'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(review_data)

    print(f'Zapisano {len(review_data)} opinii do pliku {output_file}.')

# Wywołanie funkcji
def main():
    base_url = "https://www.airlinequality.com/airline-reviews/air-france/"
    output_file = "air_france_reviews.csv"
    max_reviews = 50  # Ustaw maksymalną liczbę opinii do pobrania
    scrape_airline_reviews(base_url, output_file, max_reviews)

if __name__ == "__main__":
    main()
