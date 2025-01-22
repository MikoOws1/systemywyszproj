import pandas as pd
import sqlite3

def combine_csv_to_sqlite(file_paths, db_name, table_name):
    # Ujednolicenie kolumn i łączenie plików w jeden DataFrame
    combined_data = pd.DataFrame()

    for file_path in file_paths:
        try:
            print(f"Przetwarzanie pliku: {file_path}")
            df = pd.read_csv(file_path)
            combined_data = pd.concat([combined_data, df], ignore_index=True)
        except Exception as e:
            print(f"Błąd podczas przetwarzania pliku {file_path}: {e}")

    # Sprawdź, czy dane zostały załadowane
    if combined_data.empty:
        print("Brak danych do zapisania w bazie.")
        return
    
    # Połączenie z bazą SQLite
    conn = sqlite3.connect(db_name)

    # Wstawienie danych do tabeli
    combined_data.to_sql(table_name, conn, if_exists='replace', index=False)

    print(f"Dane zostały pomyślnie zapisane do tabeli '{table_name}' w bazie danych '{db_name}'.")
    
    # Zamknięcie połączenia z bazą danych
    conn.close()

if __name__ == "__main__":
    # Lista plików do scalenia (podaj pełne ścieżki, jeśli pliki są w innym folderze)
    file_paths = [
        "air_france_reviews.csv",
        "aircanada_reviews.csv",
        "americanairlines_reviews.csv",
        "BA_reviews.csv",
        "cathay_pacific_reviews.csv",
        "delta_air_lines_reviews.csv",
        "emirates_reviews.csv",
        "klm_reviews.csv",
        "lufthansa_reviews.csv",
        "qantas_reviews.csv",
        "qatar_reviews.csv",
        "Southwest_reviews.csv",
        "swiss_reviews.csv",
        "thai_reviews.csv",
        "United_reviews.csv"
    ]
    
    # Nazwa bazy SQLite
    db_name = "airlines_reviews.db"
    # Nazwa tabeli w bazie danych
    table_name = "airlines_reviews"
    
    # Uruchomienie funkcji
    combine_csv_to_sqlite(file_paths, db_name, table_name)
