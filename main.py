import socket
import threading
import CreateDataBase
commands={
    -1: "Użytkownik nie istnieje!",
    -2: "Błędne Hasło!",
    -4: "Błąd połączenia z bazą danych!"
}

def handle_client(conn, addr):
    while True:
        data = conn.recv(1024).decode().strip()
        if not data: break

        parts = data.split(';')
        cmd = parts

        if cmd == "LOGIN":
            # Wywołanie: result = db.check_login(parts[4], parts[5])
            conn.send(f"LOGIN_OK;{result}\n".encode())
        elif cmd == "GET_TASK":
            # Wywołanie: task = db.get_random_task()
            conn.send(f"TASK;{task['id']};{task['word']};{task['target']};{task['len']}\n".encode())
    conn.close()