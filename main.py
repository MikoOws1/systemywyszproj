import requests
from bs4 import BeautifulSoup
import csv
import time
import random

def load_proxies(proxy_file):
    formatted_proxies = []
    with open(proxy_file, 'r') as file:
        for line in file:
            parts = line.strip().split(":")
            if len(parts) == 4:
                host, port, username, password = parts
                formatted_proxies.append(f"http://{username}:{password}@{host}:{port}")
    return formatted_proxies

def get_proxy(proxies, attempt):
    return proxies[attempt % len(proxies)]

def scrape_airline_reviews(base_url, output_file, max_reviews, proxy_file):
    # Nagłówki HTTP dla requests
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    proxies = load_proxies(proxy_file)
    review_data = []
    page = 1
    attempt = 0

    while len(review_data) < max_reviews:
        url = f"{base_url}page/{page}/"
        proxy = get_proxy(proxies, attempt)
        try:
            response = requests.get(url, headers=headers, proxies={"http": proxy, "https": proxy}, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Błąd połączenia na stronie {page} z proxy {proxy}: {e}")
            attempt += 1
            if attempt >= 3:
                print("Przekroczono liczbę prób dla tej strony. Przechodzę dalej.")
                page += 1
                attempt = 0
            time.sleep(5)
            continue

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
            body_element = review.find('div', class_='text_content')
            body = body_element.text.strip() if body_element else 'Brak treści'
            unwanted_phrases = ["✅ Verified Review |", "✅ Trip Verified |", "Not Verified |", "❎ Unverified |"]
            for phrase in unwanted_phrases:
                body = body.replace(phrase, "").strip()

            # Sprawdź obecność "Trip Verified"
            trip_verified = "yes" if body_element and body_element.find('em', string='Trip Verified') else "no"

            rating = review.find('span', itemprop='ratingValue').text.strip() if review.find('span', itemprop='ratingValue') else 'Brak oceny'
            author = review.find('span', itemprop='name').text.strip() if review.find('span', itemprop='name') else 'Anonim'
            date_published = review.find('time', itemprop='datePublished')['datetime'] if review.find('time', itemprop='datePublished') else 'Brak daty'
            recommendation = review.find('td', class_='review-value rating-yes').text.strip() if review.find('td', class_='review-value rating-yes') else (
                review.find('td', class_='review-value rating-no').text.strip() if review.find('td', class_='review-value rating-no') else 'N/A'
            )

            # Szczegóły lotu i oceny
            flight_details = {
                'Samolot': 'N/A',
                'Typ_podrozy': 'N/A',
                'Trasa': 'N/A',
                'Data_podrozy': 'N/A',
                'Ocena_siedzenia': 'N/A',
                'Ocena_jedzenia': 'N/A',
                'Ocena_oblsugi_naziemnej': 'N/A',
                'Ocena_cabin_crew': 'N/A',
                'Jakosc_do_ceny': 'N/A'
            }
            for row in review.find_all('tr'):
                header = row.find('td', class_='review-rating-header')
                value = row.find('td', class_='review-value')
                stars = row.find('td', class_='review-rating-stars')

                if header and value:
                    header_text = header.text.strip().lower()
                    if 'type of traveller' in header_text:
                        flight_details['Typ_podrozy'] = value.text.strip()
                    elif 'seat type' in header_text:
                        flight_details['Samolot'] = value.text.strip()
                    elif 'route' in header_text:
                        flight_details['Trasa'] = value.text.strip()
                    elif 'date flown' in header_text:
                        flight_details['Data_podrozy'] = value.text.strip()
                elif header and stars:
                    header_text = header.text.strip().lower()
                    star_count = len(stars.find_all('span', class_='star fill'))
                    if 'seat comfort' in header_text:
                        flight_details['Ocena_siedzenia'] = star_count
                    elif 'cabin staff service' in header_text:
                        flight_details['Ocena_cabin_crew'] = star_count
                    elif 'food & beverages' in header_text:
                        flight_details['Ocena_jedzenia'] = star_count
                    elif 'ground service' in header_text:
                        flight_details['Ocena_oblsugi_naziemnej'] = star_count
                    elif 'value for money' in header_text:
                        flight_details['Jakosc_do_ceny'] = star_count

            # Pobierz nazwę linii lotniczej z URL
            airline_name = base_url.split('/')[4].replace('-', ' ').title()

            # Dodaj dane do listy
            review_data.append({
                'Tytul_opinii': title,
                'Tresc_opinii': body,
                'Podroz_zweryfikowana': 1 if trip_verified == 'yes' else 0,
                'Ocena_ogolna': rating,
                'Autor': author,
                'Data_publikacji': date_published,
                'Rekomendacja': recommendation,
                'Samolot': flight_details.get('Samolot', 'N/A'),
                'Typ_podrozy': flight_details.get('Typ_podrozy', 'N/A'),
                'Trasa': flight_details.get('Trasa', 'N/A'),
                'Data_podrozy': flight_details.get('Data_podrozy', 'N/A'),
                'Ocena_siedzenia': flight_details.get('Ocena_siedzenia', 'N/A'),
                'Ocena_jedzenia': flight_details.get('Ocena_jedzenia', 'N/A'),
                'Ocena_oblsugi_naziemnej': flight_details.get('Ocena_oblsugi_naziemnej', 'N/A'),
                'Ocena_cabin_crew': flight_details.get('Ocena_cabin_crew', 'N/A'),
                'Jakosc_do_ceny': flight_details.get('Jakosc_do_ceny', 'N/A'),
                'Linia_lotnicza': airline_name
            })

        print(f"Przetworzono stronę {page}, zebrano {len(review_data)} opinii.")
        page += 1

        # Dodanie opóźnienia między stronami
        time.sleep(5)

    # Zapisz dane do pliku CSV
    with open(output_file, mode='w', newline='', encoding='utf-8') as csvfile:
        fieldnames = [
            'Tytul_opinii', 'Tresc_opinii', 'Podroz_zweryfikowana', 'Ocena_ogolna', 'Autor', 'Data_publikacji', 'Rekomendacja',
            'Samolot', 'Typ_podrozy', 'Trasa', 'Data_podrozy',
            'Ocena_siedzenia', 'Ocena_jedzenia', 'Ocena_oblsugi_naziemnej', 'Ocena_cabin_crew', 'Jakosc_do_ceny', 'Linia_lotnicza'
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(review_data)

    print(f'Zapisano {len(review_data)} opinii do pliku {output_file}.')

# Wywołanie funkcji
def main():
    base_url = "https://www.airlinequality.com/airline-reviews/swiss-international-air-lines/"
    output_file = "swiss_reviews.csv"
    max_reviews = 1100  # Ustaw maksymalną liczbę opinii do pobrania
    proxy_file = "proxies.txt"  # Plik z listą proxy
    scrape_airline_reviews(base_url, output_file, max_reviews, proxy_file)

if __name__ == "__main__":
    main()
