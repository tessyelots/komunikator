import socket
import threading
import time
import os
import struct
import math
import binascii
import random


def keep_alive(vysielac_socket, prijimac_address, cas):
    global zmena
    try:    
        while True:
            vysielac_socket.sendto(str.encode("2"), prijimac_address)
            vysielac_socket.settimeout(30)
            ack, address = vysielac_socket.recvfrom(1500)
            ack = ack.decode()
            
            #ak prijimac vyziadal swap
            if ack[0] == "3":
                print("\n prisla zmena, stlac hocico \n")
                zmena = True
                vysielac_socket.close()
            time.sleep(cas)
    except:
        print("\n Zatvaram spojenie \n")
        vysielac_socket.close()
        time.sleep(1)
        return

#funkcia prijimaca beziaca sa samostatnom threade pocuva swap
def listen_swap():
    global zmena
    swap = input("napis 'y' ak chces vykonat zmenu vysielania\n")
    if swap == 'y':
        zmena = True

#funkcia, ktora vytvara alebo zatvara thread
def swap_thread(on):
    global thread1
    if on and thread1 == None:
        thread1 = threading.Thread(target=listen_swap, args=())
        thread1.start()
    elif not on:
        thread1.join()
        thread1 = None

def vysielac_login():
    global zmena
    while True:
        try:
            #vytvorenie socketu vysielaca
            vysielac_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            zmena = False
            address = input("Input IP address of server (localhost): ")
            port = input("Input port: ")
            prijimac_address = (address, int(port))
            
            #poslanie inicializacnej spravy
            vysielac_socket.sendto(str.encode("1"), prijimac_address)
            data, address = vysielac_socket.recvfrom(1500)
            data = data.decode()
            if data == "1":
                print("Connected to address:", prijimac_address)
                
                #vytvorenie threadu pre keep alive
                thread = threading.Thread(target=keep_alive, args=(vysielac_socket, prijimac_address, 5))
                thread.start()
                swap = False
                
                #zavolanie hlavnej funkcie vysielaca
                swap = vysielac(vysielac_socket, prijimac_address)
                if swap or zmena:
                    thread.join()
                    break
        
        except KeyboardInterrupt:
            print("vypinam program")
            thread.join()
            return
        except:
            print("Connection not working try again")
            continue
    
    #vymena role
    if swap or zmena:
        prijimac_login()

def vysielac(vysielac_socket, prijimac_address):
    global zmena
    try:
        while True:
            urob = input("Zadaj 4 ak chces poslat text, 5 ak chces poslat subor, 3 ak chces zmenit vysielanie: ")
            
            #ukoncenie funkcie ak bol swap
            if zmena:
                return True
            
            #poslanie textu
            if urob == "4":
                sprava = input("napis text: ")
                fragment_size = int(input("zadaj max. velkost fragmentu (max 1453): "))
                
                #vypocet poctu fragmentov
                sprava = str.encode(sprava)
                pocet_fragmentov = math.ceil(len(sprava)/fragment_size)
                print("pocet fragmentov: ", pocet_fragmentov)
                
                #poslanie informacneho packetu
                vysielac_socket.sendto(struct.pack("c", str.encode("4")) + struct.pack("H", pocet_fragmentov), prijimac_address)
                vysielac_socket.settimeout(30)
                data, address = vysielac_socket.recvfrom(1500)
                data = data.decode()
                
                if data == "1":
                    cislo_fragmentu = 1
                    
                    #fragmentacia textu
                    while len(sprava) != 0:
                        fragmentovana_sprava = sprava[:fragment_size]
                        
                        #vytvorenie hlavicky bez crc a vypocet crc
                        header = struct.pack("c", str.encode("6")) + struct.pack("H", cislo_fragmentu)
                        crc = binascii.crc_hqx(header + fragmentovana_sprava, 0)
                        
                        #vnesenie chyby
                        if random.randint(0, 1) == 1:
                            crc += 1
                        
                        #vytvorenie hlavicky s crc a poslanie packetu
                        header = struct.pack("c", str.encode("6")) + struct.pack("HH", cislo_fragmentu, crc)
                        vysielac_socket.sendto(header + fragmentovana_sprava, prijimac_address)
                        data, address = vysielac_socket.recvfrom(1500)
                        data = data.decode()
                        
                        #ak pride ack, zvys cislo fragmentu a zahod poslane data
                        if data == "1":
                            cislo_fragmentu += 1
                            sprava = sprava[fragment_size:]
            
            #poslanie suboru
            elif urob == "5":
                name = input("napis nazov suboru: ")
                fragment_size = int(input("zadaj max. velkost fragmentu (max 1453): "))
                
                #otvorenie suboru a vypisanie absolutnej cesty a 
                file = open(name, "rb")
                file_size = os.path.getsize(name)
                print("absolutna cesta k vybranemu suboru: ", os.path.abspath(name))
                print("velkost suboru: ",file_size)
                
                #vypocet poctu fragmentov
                pocet_fragmentov = math.ceil(file_size/fragment_size)
                print("pocet fragmentov: ", pocet_fragmentov)
                sprava = file.read()
                
                #poslanie informacneho packetu
                vysielac_socket.sendto(struct.pack("c", str.encode("5")) + struct.pack("H", pocet_fragmentov) + str.encode(os.path.basename(name)), prijimac_address)
                vysielac_socket.settimeout(30)
                data, address = vysielac_socket.recvfrom(1500)
                data = data.decode()
                
                if data == "1":
                    cislo_fragmentu = 1
                    
                    #fragmentacia suboru
                    while len(sprava) != 0:
                        fragmentovana_sprava = sprava[:fragment_size]
                        
                        #vytvorenie hlavicky bez crc a vypocet crc
                        header = struct.pack("c", str.encode("7")) + struct.pack("H", cislo_fragmentu)
                        crc = binascii.crc_hqx(header + fragmentovana_sprava, 0)
                        
                        #vnesenie chyby
                        if random.randint(0, 1) == 1:
                            crc += 1
                        
                        #vytvorenie hlavicky s crc a poslanie packetu
                        header = struct.pack("c", str.encode("7")) + struct.pack("HH", cislo_fragmentu, crc)
                        vysielac_socket.sendto(header + fragmentovana_sprava, prijimac_address)
                        data, address = vysielac_socket.recvfrom(1500)
                        data = data.decode()
                        
                        #ak pride ack, zvys cislo fragmentu a zahod poslane data
                        if data == "1":
                            cislo_fragmentu += 1
                            sprava = sprava[fragment_size:]
            
            #uzivatel vysiadal swap
            elif urob == "3":
                vysielac_socket.sendto(str.encode("3"), prijimac_address)
                data, address = vysielac_socket.recvfrom(1500)
                data = data.decode()
                if data == "1":
                    vysielac_socket.close()
                    return True

    except (socket.timeout, socket.gaierror, KeyboardInterrupt):
        print("Zatvaram spojenie")
        vysielac_socket.close()
        time.sleep(1)
        return

def prijimac_login():
    global zmena
    
    #vytvorenie socketu prijimaca a bind na zadany port
    prijimac_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    zmena = False
    port = input("Input port: ")
    prijimac_socket.bind(("", int(port)))
    
    #ked pride inicializacna sprava posli ack
    data, address = prijimac_socket.recvfrom(1500)
    prijimac_socket.sendto(str.encode("1"), address)
    print("Established connection from address:", address)

    #zavolanie hlavnej funkcie prijimaca
    swap = False
    swap = prijimac(prijimac_socket, address)
    
    #vymena role
    if swap or zmena:
        swap_thread(False)
        prijimac_socket.close()
        vysielac_login()
    else:
        swap_thread(False)
        prijimac_socket.close()

def prijimac(prijimac_socket, address):
    global zmena
    try:
        
        #ak nepride keep alive
        prijimac_socket.settimeout(30)

        #hlavny loop, ktory rozlisuje prichadzajuce packety
        while True:
            #zapnutie inputu na swap
            swap_thread(True)
            data, address = prijimac_socket.recvfrom(1500)
            typ = struct.unpack("c", data[:1])

            #ak pride keep alive
            if typ[0].decode() == "2":
                print("prislo keep alive")

                #ak prijimac vyziadal swap, daj to vediet vysielacu
                if zmena:
                    prijimac_socket.sendto(str.encode("3"), address)
                    return True
                
                #odpoved na keep alive
                else:
                    prijimac_socket.sendto(str.encode("1"), address)
            
            #ak vysielac vyziadal swap, ukoncenie funkcie
            elif typ[0].decode() == "3":
                prijimac_socket.sendto(str.encode("1"), address)
                print("prisla zmena vysielania stlac ENTER")
                return True
            
            #ak prisiel informacny packet text
            elif typ[0].decode() == "4":
                pocet_fragmentov = struct.unpack("H", data[1:3])
                print("pocet fragmentov ", pocet_fragmentov[0])
                prijimac_socket.sendto(str.encode("1"), address)

                #loop na spracovanie suboru
                cela_sprava = []
                while True:
                    data, address = prijimac_socket.recvfrom(1500)
                    typ = struct.unpack("c", data[:1])

                    #ak pride keep alive
                    if typ[0].decode() == "2":
                        print("prislo keep alive1")
                        prijimac_socket.sendto(str.encode("1"), address)
                        data, address = prijimac_socket.recvfrom(1500)
                    
                    #rozbalenie hlavicky
                    cislo_fragmentu, crc = struct.unpack("HH", data[1:5])

                    #data
                    ciastocna_sprava = data[5:]

                    #vytvorenie hlavicky bez crc
                    header = struct.pack("c", str.encode("6")) + struct.pack("H", cislo_fragmentu)

                    #kontrola crc
                    crc1 = binascii.crc_hqx(header + ciastocna_sprava, 0)
                    #ak je crc spravne, append dat do celej spravy
                    if crc == crc1:
                        print("prisiel fragment cislo "+str(cislo_fragmentu)+" s velkostou "+str(len(data)))
                        cela_sprava.append(ciastocna_sprava)
                        prijimac_socket.sendto(str.encode("1"), address)
                        if cislo_fragmentu == pocet_fragmentov[0]:
                            break
                    #ak je packet poskodeny
                    else:
                        print("fragment cislo "+str(cislo_fragmentu)+" bol zly")
                        prijimac_socket.sendto(str.encode("2"), address)
                
                #premena bajtov na string
                text = ""
                for i in range(len(cela_sprava)):
                    cela_sprava[i] = cela_sprava[i].decode()
                    text += cela_sprava[i]
                print("prisla textova sprava: "+text)
            
            #ak prisiel informacny packet subor
            elif typ[0].decode() == "5":
                pocet_fragmentov = struct.unpack("H", data[1:3])
                name = data[3:]
                print("nazov suboru: ", name.decode())
                print("pocet fragmentov ", pocet_fragmentov[0])
                prijimac_socket.sendto(str.encode("1"), address)

                #loop na spracovanie suboru
                cela_sprava = []
                while True:
                    data, address = prijimac_socket.recvfrom(1500)
                    typ = struct.unpack("c", data[:1])

                    #ak pride keep alive
                    if typ[0].decode() == "2":
                        print("prislo keep alive1")
                        prijimac_socket.sendto(str.encode("1"), address)
                        data, address = prijimac_socket.recvfrom(1500)
                    
                    #rozbalenie hlavicky
                    cislo_fragmentu, crc = struct.unpack("HH", data[1:5])

                    #data
                    ciastocna_sprava = data[5:]

                    #vytvorenie hlavicky bez crc
                    header = struct.pack("c", str.encode("7")) + struct.pack("H", cislo_fragmentu)

                    #kontrola crc
                    crc1 = binascii.crc_hqx(header + ciastocna_sprava, 0)
                    #ak je crc spravne, append dat do celej spravy
                    if crc == crc1:
                        print("prisiel fragment cislo "+str(cislo_fragmentu)+" s velkostou "+str(len(data)))
                        cela_sprava.append(ciastocna_sprava)
                        prijimac_socket.sendto(str.encode("1"), address)
                        if cislo_fragmentu == pocet_fragmentov[0]:
                            break
                    #ak je packet poskodeny
                    else:
                        print("fragment cislo "+str(cislo_fragmentu)+" bol zly")
                        prijimac_socket.sendto(str.encode("2"), address)

                print("stlac ENTER")
                #vypnutie inputu na swap
                swap_thread(False)
                #pouzivatel zada miesto ulozenia suboru
                print("Zadaj absolutnu cestu k adresaru, do ktoreho sa subor ulozi. Alebo stlac ENTER a subor sa ulozi do rovnakeho priecinka ako main.py")
                cesta = input()
                
                #ak nezada miesto, ulozenie k main.py
                if cesta == "":
                    file = open(name.decode(), "wb")
                else:
                    try:
                        file = open(cesta+"\\"+name.decode(), "wb")
                    except FileNotFoundError:
                        print("zle zadana cesta, ukladam do priecinka k main.py")
                        file = open(name.decode(), "wb")
                        cesta = ""
                
                #vytvorenie suboru
                for fragment in cela_sprava:
                    file.write(fragment)
                file.close()

                #vypisanie informacii o ulozenom subore
                if cesta == "":
                    print("absolutna cesta k prijatemu suboru: ", os.path.abspath(name.decode()))
                    print("velkost prijateho suboru: ", os.path.getsize(name.decode()))
                else:
                    print("absolutna cesta k prijatemu suboru: ", os.path.abspath(cesta+"\\"+name.decode()))
                    print("velkost prijateho suboru: ", os.path.getsize(cesta+"\\"+name.decode()))
                print("pocet prijatych fragmentov: ", pocet_fragmentov[0])
                
    except socket.timeout:
        print("Vysielac nekomunikuje, zatvaram spojenie")
        prijimac_socket.close()
        return

#uvodny input pri zapnuti programu
zmena = False
thread1 = None
user = input("Zadaj 1 ak ides prijimat, 2 ak ides vysielat: ")
if user == '1':
    prijimac_login()
elif user == '2':
    vysielac_login()