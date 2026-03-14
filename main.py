import socket
import threading
from CreateDataBase import *


commands={
    -1: "Użytkownik nie istnieje!",
    -2: "Błędne Hasło!",
    -3: "Zły mail i hasło.",
    -4: "Błąd połączenia z bazą danych!",
    -5: "Zły mail.",
    -6: "Brak zadań lub błędne id.",
    -7: "Usunięto konto!"
}


def handle_client(conn, addr):
    print(f"[POŁĄCZENIE] Nowy gracz: {addr}")
    connected = True
    kontener_move =[]
    kontener_size=0
    end:bool = False
    user_id:str=""
    while connected:
        try:
            # Odbieranie danych (zgodnie z protokołem zakończonych \n)
            data = conn.recv(1024).decode('utf-8')
            if not data:
                break

            # Przetwarzanie wielu komend w jednym buforze
            messages = data.strip().split('\n')
            for msg in messages:
                parts = msg.split(';')
                cmd = parts[0]
                print(msg)
                if cmd == "LOGIN":
                    # LOGIN;nick;haslo -> LOGIN_OK;user_id lub LOGIN_ERROR
                    # res = login_user(parts[2], parts[3])
                    res=login_user(parts[1], parts[2])
                    if res in commands.keys():
                        conn.send(f"LOGIN_ERROR;{commands[res]}\n".encode())
                    else:
                        conn.send(f"LOGIN_OK;{res}\n".encode())
                        user_id=res# Przykład sukcesu

                elif cmd == "REGISTER":
                    # REGISTER;nick;email;haslo
                    res=register_user(parts[1], parts[2],parts[3])
                    if res in commands.keys():
                        conn.send(f"REGISTER_ERROR;{commands[res]}\n".encode())
                    else:
                        conn.send(f"REGISTER_OK;{res}\n".encode())

                elif cmd == "GET_TASK":
                    # TASK;id;start;target;size;points;time
                    res=get_current_task(parts[1])
                    if type(res)!=type(dict()):
                        if res in commands.keys():
                            conn.send(f"TASK_ERROR;{commands[res]}\n".encode())
                    else:
                        conn.send(f"TASK;{res["id_zadania"]};{res["word"]};{res["to_word"]};{res["length"]};{res["punkty"]};{res["time"]}\n".encode())
                elif cmd == "MOVES":
                    kontener_move=["" for _ in range(int(parts[1]))]
                    kontener_size=int(parts[1])-1
                elif cmd == "MOVE":
                    kontener_move[int(parts[1].split("|")[0])]=parts[1]
                    if int(parts[1].split("|")[0])==kontener_size:
                        end = True
                    if end==True:
                        for i in kontener_move:
                            if(i==""):
                                break
                        else:
                            k=verify_player_movements(user_id,kontener_move)
                            if k==True:
                                conn.send(f"SOLUTION_OK;{current_points(user_id)}\n".encode())
                                end=False


                elif cmd == "GET_RANKING":
                    # RANKING;pos:nick:pts;...;YOUR_POS:m:pts
                    if user_id!="":
                        conn.send(get_ranking(user_id).encode())
                elif cmd == "REGISTER_OUT":
                    # Protokół: REGISTER_OUT;id;haslo
                    # parts[2] to id, parts[3] to hasło
                    result = register_out(parts[1], parts[2])
                    conn.send(f"REGISTER_OUT;{commands[result] if result in commands.keys() else result}\n".encode())

                elif cmd == "LOGOUT":
                    conn.send("LOGOUT_OK\n".encode())
                    connected = False
                elif cmd=="LOGOUT_X":
                    user_id=""
                    kontener_move=[]
                    kontener_size=0
                    end=False
                    conn.send(f"LOGOUT_XOK;\n".encode())

        except Exception as e:
            print(f"[BŁĄD] {e}")
            break

    conn.close()
    print(f"[ROZŁĄCZONO] {addr}")
def start_server(ip="0.0.0.0", port=5555):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((ip, port))
    server.listen()
    print(f"[START] Serwer działa na {ip}:{port}")
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr))
        thread.start()

if __name__ == "__main__":
    start_server()