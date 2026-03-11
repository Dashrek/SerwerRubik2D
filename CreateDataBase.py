import sqlite3
import csv
import hashlib
import time

def import_ranking_from_csv(file_path):
    """Importuje przykłady z pliku CSV do tabeli Ranking_Gry."""
    conn = create_connection()
    if conn is None:
        return

    cursor = conn.cursor()
    try:
        with open(file_path, mode='r', encoding='utf-8') as f:
            # LibreOffice w polskiej wersji często używa średnika (;) jako separatora
            reader = csv.reader(f, delimiter=';')

            for row in reader:
                # Oczekiwany format linii: punkty; word; to_word; time; length
                if len(row) == 5:
                    cursor.execute("""
                                   INSERT INTO Ranking_Gry
                                       (punkty, slowo_startowe, slowo_docelowe, czas_wykonania, dlugosc_linii)
                                   VALUES (?, ?, ?, ?, ?)
                                   """, (row, row[1], row[2], row[3], row[4]))

        conn.commit()
        print(f"Pomyślnie zaimportowano dane z pliku: {file_path}")
    except Exception as e:
        print(f"Błąd podczas odczytu pliku CSV: {e}")
    finally:
        conn.close()
def create_connection(db_file="rubik_game.db"):
    """Inicjuje połączenie z bazą danych z obsługą kluczy obcych."""
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    except sqlite3.Error as e:
        print(f"Błąd połączenia: {e}")
    return conn
def setup_database():
    """Tworzy strukturę bazy danych dostosowaną do progresywnego systemu zadań."""
    conn = create_connection()
    if conn is not None:
        cursor = conn.cursor()

        # Tabela 1: Dane kont (zintegrowane z Projekt_It)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Gracze (
                id_uzytkownika INTEGER PRIMARY KEY AUTOINCREMENT,
                nazwa TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                hash_hasla TEXT NOT NULL
            );
        """)

        # Tabela 2: Biblioteka zadań (pobierana z CSV)
        cursor.execute("""
                       CREATE TABLE IF NOT EXISTS Zadania
                       (
                           id_zadania INTEGER PRIMARY KEY AUTOINCREMENT,
                           punkty INTEGER NOT NULL,
                           slowo_startowe TEXT NOT NULL,
                           slowo_docelowe TEXT NOT NULL,
                           dlugosc_linii INTEGER NOT NULL,
                           czas_wykonania TEXT DEFAULT ""
                       );
                       """)

        # Tabela 3: Aktualny stan i postęp gracza (id gracza; aktualne zadanie)
        # Cascade usuwa postępy, gdy gracz zostanie usunięty.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Stan_Gracza (
                id_uzytkownika INTEGER PRIMARY KEY,
                id_aktualnego_zadania INTEGER DEFAULT 1,
                suma_punktow INTEGER DEFAULT 0,
                FOREIGN KEY (id_uzytkownika) REFERENCES Gracze(id_uzytkownika) ON DELETE CASCADE,
                FOREIGN KEY (id_aktualnego_zadania) REFERENCES Zadania(id_zadania)
            );
        """)

        conn.commit()
        conn.close()
        print("Baza danych z systemem zadań została utworzona.")
def add_task_from_cmd(input_string):
    """Format: punkty;start;docelowe;dlugosc;czas"""
    conn = create_connection()
    if conn is None: return
    cursor = conn.cursor()
    try:
        data = [item.strip() for item in input_string.split(';')]
        if len(data) == 5:
            cursor.execute("""
                INSERT INTO Zadania (punkty, slowo_startowe, slowo_docelowe, dlugosc_linii, czas_wykonania)
                VALUES (?, ?, ?, ?, ?)
            """, (int(data[0]), data[2], data[3], int(data[1]), data[4]))
            conn.commit()
            print("Zadanie z czasem dodane.")
    except Exception as e:
        print(f"Błąd: {e}")
    finally:
        conn.close()
def register_user(nickname, email, plain_password):
    """
    Rejestruje użytkownika: hashuje hasło i zapisuje do bazy.
    Zwraca: id_uzytkownika, -1 (zajęty nick), -2 (zajęty email), -3 (oba).
    """
    conn = create_connection()
    if conn is None: return -4

    # Generowanie hasha z hasła (SHA-256)
    # W PHP robi to password_hash(), tutaj używamy hashlib
    password_hash = hashlib.sha256(plain_password.encode()).hexdigest()

    cursor = conn.cursor()
    try:
        # Sprawdzenie unikalności (bez zmian)
        cursor.execute("SELECT 1 FROM Gracze WHERE nazwa = ?", (nickname,))
        nick_taken = cursor.fetchone() is not None
        cursor.execute("SELECT 1 FROM Gracze WHERE email = ?", (email,))
        email_taken = cursor.fetchone() is not None

        if nick_taken and email_taken: return -3
        if nick_taken: return -1
        if email_taken: return -2

        # Zapisanie hasha zamiast jawnego hasła
        cursor.execute("""
                       INSERT INTO Gracze (nazwa, email, hash_hasla)
                       VALUES (?, ?, ?)
                       """, (nickname, email, password_hash))

        user_id = cursor.lastrowid

        # Inicjalizacja stanu (Tabela 3)
        cursor.execute("""
                       INSERT INTO Stan_Gracza (id_uzytkownika, id_aktualnego_zadania, suma_punktow)
                       VALUES (?, 1, 0)
                       """, (user_id,))

        conn.commit()
        return user_id
    finally:
        conn.close()
def login_user(identifier, plain_password):
    """
    Standardowe logowanie: porównuje hash wpisanego hasła z bazą.
    Zwraca: id_uzytkownika (sukces), -1 (brak gracza), -2 (błędne hasło).
    """
    conn = create_connection()
    if conn is None: return -4
    cursor = conn.cursor()

    try:
        # Szukanie użytkownika w tabeli Gracze [1], [2]
        cursor.execute("SELECT id_uzytkownika, hash_hasla FROM Gracze WHERE nazwa = ? OR email = ?", (identifier, identifier))
        row = cursor.fetchone()

        if row is None:
            return -1 # Użytkownik nie istnieje

        user_id, stored_hash = row

        # Generujemy hash z wpisanego hasła do porównania
        current_attempt_hash = hashlib.sha256(plain_password.encode()).hexdigest()

        if current_attempt_hash == stored_hash:
            return user_id # Sukces: Hasło poprawne
        else:
            return -2 # Błąd: Hasło niepoprawne

    finally:
        conn.close()


def get_current_task(user_id):
    """
    Pobiera dane aktualnego zadania dla gracza o podanym ID.
    Zwraca słownik z danymi zadania lub None, jeśli gracz ukończył wszystkie zadania.
    """
    conn = create_connection()
    if conn is None: return None
    cursor = conn.cursor()

    try:
        # 1. Łączymy tabelę Stan_Gracza z tabelą Zadania, aby pobrać szczegóły
        cursor.execute("""
                       SELECT Z.punkty, Z.slowo_startowe, Z.slowo_docelowe, Z.dlugosc_linii, Z.czas_wykonania
                       FROM Stan_Gracza S
                                JOIN Zadania Z ON S.id_aktualnego_zadania = Z.id_zadania
                       WHERE S.id_uzytkownika = ?
                       """, (user_id,))

        row = cursor.fetchone()

        if row:
            return {
                "punkty": row,
                "word": row[3],  # Zmienna word w game::start
                "to_word": row[4],  # Zmienna to_word w game::start
                "length": row[2],  # Zmienna length w game::start
                "time": row[5]  # Zmienne timek/timer w game::start
            }
        return None  # Brak kolejnych zadań lub błędne ID

    finally:
        conn.close()


def verify_player_movements(user_id, moves_list):
    """
    Weryfikuje, czy lista ruchów (.s_str()) prowadzi do ułożenia zadania.
    Zwraca True i przyznaje punkty, lub False przy błędzie.
    """
    # 1. Pobierz dane aktualnego zadania dla gracza
    task = get_current_task(user_id)
    if not task:
        return False

    current_word = list(task['word'])
    target_word = task['to_word']
    line_length = task['length']
    grid = [current_word[i:i + length] for i in range(0, len(current_word), length)]
    # 2. Odtwarzanie ruchów (Emulator logiki z C++)
    for move in moves_list:
        # Przykładowa interpretacja move (np. "R1" - przesunięcie wiersza 1 w prawo)
        current_word = apply_logic_move(grid, move, line_length)
    current_word=[]
    for i in grid:
        current_word+=i
    current_word="".join(current_word)
    # 3. Sprawdzenie wyniku
    if current_word == target_word:
        # Jeśli się zgadza, zaktualizuj postęp gracza
        return complete_task(user_id, task['punkty'])

    return False


def apply_logic_move(state, move_str, length):
    """
    Tu implementujesz logikę przesunięć, którą masz w lambdach w C++.
    state: lista znaków słowa
    move_str: dane z obiektu moved.s_str()
    """
    move_str=move_str[:-1].split("|")
    x:int=int(move_str[2])
    y:int=int(move_str[3])
    if (move_str[1]=="r"):
        state[x][y],state[x+1][y],state[x+1][y+1],state[x][y+1]=state[x][y+1],state[x][y],state[x+1][y],state[x+1][y+1]
    elif (move_str[1]=="l"):
        state[x][y], state[x + 1][y], state[x + 1][y + 1], state[x][y + 1] =state[x+1][y],state[x+1][y+1],state[x][y+1],state[x][y]
    return state



def complete_task(user_id, points_to_add):
    conn = create_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
                       UPDATE Stan_Gracza
                       SET id_aktualnego_zadania = id_aktualnego_zadania + 1,
                           suma_punktow          = suma_punktow + ?
                       WHERE id_uzytkownika = ?
                       """, (points_to_add, user_id))
        conn.commit()
        return True
    except:
        return False
    finally:
        conn.close()
if __name__ != '__main__':
    setup_database()