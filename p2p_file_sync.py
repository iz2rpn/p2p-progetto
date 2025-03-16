import os
import socket
import threading
import hashlib
import time
import json
import logging
import sys
from collections import defaultdict
from typing import Dict, Set


class P2PFileSync:
    def __init__(
        self,
        shared_dir: str = "shared",  # Cartella condivisa per i file
        block_size: int = 1048576,  # 1MB
        multicast_group: str = "239.255.255.250",  # Indirizzo multicast per il discovery
        multicast_port: int = 5007,  # Porta multicast per il discovery
        peer_port: int = 5005,  # Porta TCP per le connessioni peer-to-peer
        sync_interval: int = 10,  # Intervallo di sincronizzazione in secondi
    ) -> None:
        """
        Inizializza il nodo P2P per la sincronizzazione dei file.

        Args:
            shared_dir (str): Cartella condivisa per i file. Default: "arcade_shared".
            block_size (int): Dimensione dei blocchi per il trasferimento file. Default: 1MB.
            multicast_group (str): Indirizzo multicast per il discovery. Default: '239.255.255.250'.
            multicast_port (int): Porta multicast per il discovery. Default: 5007.
            peer_port (int): Porta TCP per le connessioni peer-to-peer. Default: 5005.
            sync_interval (int): Intervallo di sincronizzazione in secondi. Default: 10.
        """
        # Inizializza il logger
        self.logger = self._setup_logger()  # Configura il logger

        # Configurazione directory e parametri
        self.shared_dir = self._setup_shared_dir(
            shared_dir
        )  # Configura la cartella condivisa
        self.block_size = block_size  # Dimensione dei blocchi per il trasferimento file
        self.multicast_group = multicast_group  # Indirizzo multicast per il discovery
        self.multicast_port = multicast_port  # Porta multicast per il discovery
        self.peer_port = peer_port  # Porta TCP per le connessioni peer-to-peer
        self.sync_interval = sync_interval  # Intervallo di sincronizzazione in secondi

        # Stato interno
        self.peers: Set[str] = set()  # Insieme di peer connessi
        self.file_registry: Dict[str, Dict] = defaultdict(
            dict
        )  # Registro dei file locali
        self.active = True  # Flag per l'attività del nodo
        self.local_ip = self._get_reliable_local_ip()  # Indirizzo IP locale
        self.synced_files: Set[str] = set()  # Insieme di file sincronizzati
        self.last_scan_time = 0  # Ultimo tempo di scansione
        self.scan_interval = 5  # Intervallo di scansione in secondi

        # Avvio servizi
        self._start_services()  # Avvia i servizi di rete
        self.logger.info(f"🚀 Nodo P2P avviato su {self.local_ip}")

    def _setup_logger(self) -> logging.Logger:
        """
        Configura e restituisce un logger per il nodo.

        Returns:
            logging.Logger: Istanza del logger configurato.
        """
        logger = logging.getLogger("P2PFileSync")
        logger.setLevel(
            logging.INFO
        )  # Livello di log, cambiare INFO in DEBUG per più dettagli.
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger.addHandler(ch)
        return logger

    def _setup_shared_dir(self, path: str) -> str:
        """
        Crea la cartella condivisa se non esiste e restituisce il percorso assoluto.

        Args:
            path (str): Percorso della cartella condivisa.

        Returns:
            str: Percorso assoluto della cartella condivisa.
        """
        os.makedirs(path, exist_ok=True)
        abs_path = os.path.abspath(path)
        self.logger.info(f"📁 Cartella condivisa: {abs_path}")

        # Verifica il contenuto della cartella
        files = os.listdir(abs_path)
        if not files:
            self.logger.warning("⚠️ La cartella condivisa è vuota!")
        else:
            self.logger.info(f"📂 Contenuto della cartella: {files}")

        return abs_path

    def _get_reliable_local_ip(self) -> str:
        """
        Ottiene l'IP locale in modo affidabile per LINUX e WINDOWS.

        Returns:
            str: Indirizzo IP locale.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(
                    ("10.255.255.255", 1)
                )  # Indirizzo non instradabile su Internet
                return s.getsockname()[0]
        except:
            try:
                return socket.gethostbyname(socket.gethostname())
            except:
                return "127.0.0.1"

    def _start_services(self) -> None:
        """Avvia tutti i servizi di rete in thread separati."""
        services = [
            self._listen_for_peers,  # Ascolta i peer
            self._start_tcp_server,  # Avvia il server TCP
            self._broadcast_presence,  # Annuncia la propria presenza
            self._sync_loop,  # Loop di sincronizzazione
        ]
        for service in services:
            threading.Thread(
                target=service, daemon=True
            ).start()  # Avvia il servizio in un thread

    def _listen_for_peers(self) -> None:
        """Ascolta i pacchetti multicast per rilevare nuovi peer."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
        sock.setsockopt(
            socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
        )  # Riutilizzo indirizzo

        # Configurazione specifica per OS
        if sys.platform.startswith("linux"):
            sock.bind((self.multicast_group, self.multicast_port))  # Linux
        else:
            sock.bind(("", self.multicast_port))  # Windows

        # Configurazione gruppo multicast
        mreq = socket.inet_aton(self.multicast_group) + socket.inet_aton(
            self.local_ip
        )  # Indirizzo
        sock.setsockopt(
            socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq
        )  # Aggiungi gruppo

        self.logger.debug("🎧 In ascolto per nuovi peer...")

        while self.active:
            try:
                data, addr = sock.recvfrom(1024)
                self.logger.debug(f"📩 Ricevuto pacchetto da {addr}: {data.decode()}")
                if data.decode() == "DISCOVER" and addr[0] != self.local_ip:
                    self._add_peer(addr[0])  # Aggiungi il peer
            except Exception as e:
                if self.active:
                    self.logger.error(f"❌ Errore multicast: {str(e)}")

    def _add_peer(self, peer_ip: str) -> None:
        """
        Aggiunge un nuovo peer alla lista e avvia la sincronizzazione.

        Args:
            peer_ip (str): Indirizzo IP del peer da aggiungere.
        """
        if peer_ip not in self.peers:
            self.peers.add(peer_ip)  # Aggiungi il peer
            self.logger.info(f"🆕 Nuovo peer rilevato: {peer_ip}")
            self._sync_with_peer(peer_ip)  # Sincronizza i file con il peer

    def _start_tcp_server(self) -> None:
        """Avvia il server TCP per gestire le connessioni in entrata."""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.bind(("0.0.0.0", self.peer_port))
            sock.listen(5)
            self.logger.debug(f"🔌 Server TCP in ascolto sulla porta {self.peer_port}")

            while self.active:
                try:
                    conn, addr = sock.accept()
                    self.logger.debug(f"🔗 Connessione TCP da {addr}")
                    threading.Thread(
                        target=self._handle_request, args=(conn, addr)
                    ).start()  # Gestisce la richiesta in un thread
                except Exception as e:
                    if self.active:
                        self.logger.error(f"❌ Errore server TCP: {str(e)}")

    def _handle_request(self, conn: socket.socket, addr: tuple) -> None:
        """
        Gestisce le richieste TCP in entrata.

        Args:
            conn (socket.socket): Socket della connessione.
            addr (tuple): Indirizzo del peer (IP, porta).
        """
        try:
            data = conn.recv(1024).decode()
            self.logger.debug(f"📨 Richiesta da {addr}: {data}")

            if data.startswith("LIST"):
                self._send_file_list(conn, addr)  # Invia la lista dei file
            elif data.startswith("PREPARE:"):
                self._handle_prepare(conn, data)  # Gestisce la preparazione
            elif data.startswith("CHUNK:"):
                self._handle_chunk(conn, data)  # Gestisce l'invio del blocco

        except Exception as e:
            self.logger.error(f"❌ Errore connessione con {addr[0]}: {str(e)}")
        finally:
            conn.close()

    def _send_file_list(self, conn: socket.socket, addr: tuple) -> None:
        """
        Invia la lista dei file disponibili al peer.

        Args:
            conn (socket.socket): Socket della connessione.
            addr (tuple): Indirizzo del peer (IP, porta).
        """
        try:
            file_list = self._get_local_file_list()  # Ottiene la lista dei file
            conn.send(
                json.dumps(file_list).encode()
            )  # Invia la lista come JSON. La struttura è da ridefinire
            self.logger.info(
                f"📄 Inviata lista file a {addr[0]}: {len(file_list)} file"
            )
        except Exception as e:
            self.logger.error(f"❌ Errore invio file list: {str(e)}")

    def _get_local_file_list(self) -> Dict[str, Dict]:
        """
        Restituisce la lista dei file locali con hash e dimensione.
        """
        current_time = time.time()
        if current_time - self.last_scan_time < self.scan_interval:
            return self.file_registry  # ritorna il registro se la scansione è recente.
        self.last_scan_time = current_time
        file_list = {}
        try:
            self.logger.debug(f"🔍 Scansione della cartella: {self.shared_dir}")
            for filename in os.listdir(self.shared_dir):
                filepath = os.path.join(self.shared_dir, filename)  # Percorso del file
                self.logger.debug(
                    f"🔍 Rilevato: {filename} (is_file: {os.path.isfile(filepath)})"
                )
                if os.path.isfile(filepath) and not filename.startswith(".tmp."):
                    file_list[filename] = {
                        "hash": self._calculate_hash(filepath),
                        "size": os.path.getsize(filepath),
                    }  # Calcola hash e dimensione
            self.logger.info(f"📄 Lista file locali: {len(file_list)} file")
        except Exception as e:
            self.logger.error(f"❌ Errore lettura cartella condivisa: {str(e)}")
        self.file_registry = file_list  # aggiorna il registro.
        return file_list

    def _handle_prepare(self, conn: socket.socket, data: str) -> None:
        """
        Gestisce la preparazione per ricevere un file.

        Args:
            conn (socket.socket): Socket della connessione.
            data (str): Dati della richiesta PREPARE.
        """
        try:
            _, filename, file_size = data.split(":")  # Estrae nome e dimensione
            file_size = int(file_size)

            # Crea un file temporaneo
            temp_file = os.path.join(self.shared_dir, f".tmp.{filename}")
            open(temp_file, "wb").close()  # Crea file vuoto

            # Conferma al mittente che siamo pronti
            conn.send(b"READY")
            self.logger.info(f"🛠️ Pronto a ricevere {filename} ({file_size} bytes)")

            # Ricevi i chunk. Chuck Norris non fa il debug del codice. Semplicemente lo fissa finché non si corregge da solo.
            received_size = 0
            with open(temp_file, "ab") as f:
                while received_size < file_size:
                    # Ricevi i dati del blocco (come byte)
                    block = conn.recv(min(self.block_size, file_size - received_size))
                    if not block:
                        break

                    f.write(block)
                    received_size += len(block)

            # Rinomina il file temporaneo
            final_path = os.path.join(self.shared_dir, filename)
            os.rename(temp_file, final_path)
            self.logger.info(f"🎉 File {filename} ricevuto correttamente")

        except Exception as e:
            self.logger.error(f"❌ Errore ricezione file: {str(e)}")
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def _handle_chunk(self, conn: socket.socket, data: str) -> None:
        """
        Gestisce l'invio di un blocco.

        Args:
            conn (socket.socket): Socket della connessione.
            data (str): Dati della richiesta CHUNK.
        """
        try:
            _, filename, block_num = data.split(":")
            block_num = int(block_num)
            filepath = os.path.join(self.shared_dir, filename)

            if os.path.exists(filepath):
                with open(filepath, "rb") as f:
                    f.seek(block_num * self.block_size)
                    block_data = f.read(self.block_size)
                    conn.send(block_data)  # Invia i dati binari
                    self.logger.debug(f"📤 Inviato blocco {block_num} di {filename}")
        except Exception as e:
            self.logger.error(f"❌ Errore invio blocco: {str(e)}")

    def _broadcast_presence(self) -> None:
        """Annuncia la propria presenza agli altri peer."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)

        self.logger.debug("📢 Annuncio la mia presenza...")

        while self.active:
            try:
                sock.sendto(
                    b"DISCOVER", (self.multicast_group, self.multicast_port)
                )  # Invia il pacchetto multicast per il discovery
                time.sleep(5)
            except Exception as e:
                if self.active:
                    self.logger.error(f"❌ Errore discovery: {str(e)}")

    def _sync_loop(self) -> None:
        """Esegue la sincronizzazione periodica con tutti i peer."""
        while self.active:
            try:
                for peer in list(self.peers):
                    self._sync_with_peer(peer)  # Sincronizza con il peer corrente
                time.sleep(self.sync_interval)
            except Exception as e:
                self.logger.error(f"❌ Errore durante la sincronizzazione: {str(e)}")

    def _sync_with_peer(self, peer_ip: str) -> None:
        """
        Sincronizza i file con un peer specifico.

        Args:
            peer_ip (str): Indirizzo IP del peer.
        """
        try:
            with socket.create_connection((peer_ip, self.peer_port), timeout=5) as sock:
                sock.settimeout(10)
                sock.send(
                    b"LIST"
                )  # Invia il comando LIST per ottenere la lista dei file
                peer_files = json.loads(
                    sock.recv(65536).decode()
                )  # Riceve la lista dei file come JSON
                self._process_peer_files(
                    peer_ip, peer_files
                )  # Elabora i file del peer ricevuti
        except Exception as e:
            self.logger.warning(f"⚠️ Errore sync con {peer_ip}: {str(e)}")

    def _process_peer_files(self, peer_ip: str, peer_files: Dict) -> None:
        """
        Elabora la lista dei file ricevuta da un peer.
        """
        local_files = self._get_local_file_list()  # Ottiene la lista dei file locali

        # Trova file mancanti o diversi
        for filename, info in peer_files.items():
            local_file = os.path.join(
                self.shared_dir, filename
            )  # Percorso del file locale
            if (
                not os.path.exists(local_file)
                or self._calculate_hash(local_file) != info["hash"]
            ):
                if (peer_ip, filename) not in self.synced_files:  # aggiunto controllo
                    self.logger.info(f"📥 File da sincronizzare: {filename}")
                    self._download_file(
                        peer_ip, filename, info["size"]
                    )  # Scarica il file dal peer
                    self.synced_files.add((peer_ip, filename))  # aggiunto
                else:
                    self.logger.debug(f"✅ File già sincronizzato: {filename}")
            else:
                self.logger.debug(f"✅ File già sincronizzato: {filename}")

        # Invia i nostri file mancanti al peer
        for filename, info in local_files.items():
            if (
                filename not in peer_files
                or peer_files[filename]["hash"] != info["hash"]
            ):
                if (peer_ip, filename) not in self.synced_files:  # aggiunto controllo
                    self.logger.info(f"📤 Invio file {filename} a {peer_ip}")
                    self._send_file_to_peer(peer_ip, filename)  # Invia il file al peer
                    self.synced_files.add((peer_ip, filename))  # aggiunto
                else:
                    self.logger.debug(f"✅ File già sincronizzato: {filename}")
            else:
                self.logger.debug(f"✅ File già sincronizzato: {filename}")

    def _send_file_to_peer(self, peer_ip: str, filename: str) -> None:
        """
        Invia un file completo a un peer.

        Args:
            peer_ip (str): Indirizzo IP del peer.
            filename (str): Nome del file da inviare.
        """
        try:
            filepath = os.path.join(self.shared_dir, filename)
            if not os.path.exists(filepath):
                self.logger.warning(f"⚠️ File {filename} non trovato")
                return

            file_size = os.path.getsize(filepath)

            with socket.create_connection(
                (peer_ip, self.peer_port), timeout=10
            ) as sock:
                sock.settimeout(15)

                # Invia comando di preparazione
                sock.send(
                    f"PREPARE:{filename}:{file_size}".encode()
                )  # Invia il comando PREPARE con nome e dimensione

                # Attendi conferma
                response = sock.recv(1024).decode()
                if response != "READY":
                    raise Exception("Peer non pronto a ricevere")

                # Invia i blocchi
                with open(filepath, "rb") as f:
                    block_num = 0
                    while True:
                        block = f.read(self.block_size)
                        if not block:
                            break

                        # Invia il comando CHUNK
                        sock.send(
                            f"CHUNK:{filename}:{block_num}".encode()
                        )  # Invia il comando CHUNK con nome e numero blocco. Non evoca Chuck Norris.

                        # Invia i dati del blocco
                        sock.send(block)

                        self.logger.debug(
                            f"📤 Inviato blocco {block_num} di {filename} a {peer_ip}"
                        )
                        block_num += 1

                self.logger.info(
                    f"🎉 File {filename} inviato correttamente a {peer_ip}"
                )
            self.synced_files.add((peer_ip, filename))
        except Exception as e:
            self.logger.error(f"❌ Errore invio file {filename} a {peer_ip}: {str(e)}")

    def _download_file(self, peer_ip: str, filename: str, file_size: int) -> None:
        """
        Scarica un file completo da un peer.

        Args:
            peer_ip (str): Indirizzo IP del peer.
            filename (str): Nome del file da scaricare.
            file_size (int): Dimensione del file.
        """
        try:
            temp_file = os.path.join(self.shared_dir, f".tmp.{filename}")
            blocks = (
                file_size + self.block_size - 1
            ) // self.block_size  # Calcola il numero di blocchi

            # Prepara il peer
            with socket.create_connection(
                (peer_ip, self.peer_port), timeout=10
            ) as sock:
                sock.settimeout(15)
                sock.send(
                    f"PREPARE:{filename}:{file_size}".encode()
                )  # Invia il comando PREPARE con nome e dimensione
                if sock.recv(1024).decode() != "READY":
                    raise Exception("Peer non pronto a ricevere")

            # Scarica i blocchi
            with open(temp_file, "wb") as f:
                for block in range(blocks):
                    if not self._download_block(peer_ip, filename, block, f):
                        self.logger.error(f"❌ Download interrotto: {filename}")
                        os.remove(
                            temp_file
                        )  # Rimuove il file temporaneo in caso di errore
                        return

            final_path = os.path.join(self.shared_dir, filename)
            os.rename(
                temp_file, final_path
            )  # Rinomina il file temporaneo in quello definitivo
            self.logger.info(f"🎉 File scaricato correttamente: {filename}")

        except Exception as e:
            self.logger.error(f"❌ Errore download {filename}: {str(e)}")
            if os.path.exists(temp_file):
                os.remove(temp_file)

    def _download_block(
        self, peer_ip: str, filename: str, block_num: int, file_handle
    ) -> bool:
        """
        Scarica un singolo blocco da un peer.

        Args:
            peer_ip (str): Indirizzo IP del peer.
            filename (str): Nome del file.
            block_num (int): Numero del blocco.
            file_handle: File handle per scrivere i dati.

        Returns:
            bool: True se il blocco è stato scaricato correttamente, False altrimenti.
        """
        try:
            with socket.create_connection(
                (peer_ip, self.peer_port), timeout=10
            ) as sock:
                sock.settimeout(15)
                request = f"CHUNK:{filename}:{block_num}"  # Comando CHUNK con nome e numero blocco
                sock.send(request.encode())

                received = 0
                while received < self.block_size:
                    data = sock.recv(
                        min(self.block_size - received, 4096)
                    )  # Riceve i dati del blocco
                    if not data:
                        break
                    file_handle.write(data)  # Scrive i dati nel file temporaneo
                    received += len(data)

                return received > 0
        except Exception as e:
            self.logger.warning(f"⚠️ Errore blocco {block_num} di {filename}: {str(e)}")
            return False

    def _calculate_hash(self, filepath: str) -> str:
        """
        Calcola l'hash SHA256 di un file.

        Args:
            filepath (str): Percorso del file.

        Returns:
            str: Hash SHA256 del file.
        """
        if not os.path.exists(filepath):
            return ""
        hasher = hashlib.sha256()
        with open(filepath, "rb") as f:
            while True:
                data = f.read(self.block_size)
                if not data:
                    break
                hasher.update(data)  # Aggiorna l'hash con i dati del blocco
        return hasher.hexdigest()

    def stop(self) -> None:
        """Arresta il servizio in modo pulito."""
        self.active = False
        self.logger.info("🛑 Servizio arrestato")
        logging.shutdown()  # Arresta il logger correttamente prima di esposioni nucleari


if __name__ == "__main__":
    node = P2PFileSync()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        node.stop()  # Arresta il nodo in caso di interruzione manuale perchè mi piace da matti questo errore

# Fine del codice
# --------------------------------------------------------------------------------------------------
# Non usare in produzione, potrebbe causare danni non sarò responsabile della distruzione del mondo.
# Questo codice è stato scritto da un pessimo programmatore, non è stato testato e non è sicuro.
# Non sapevo cosa stessi facendo, ma alla fine ho fatto qualcosa.
# Se non funziona, probabilmente è colpa tua.
# Se funziona, è solo fortuna.
# Non dirlo a nessuno, ma ho usato Python per scrivere questo codice.
# Se hai letto fin qui, complimenti! Sei un programmatore paziente.
# Sei uno dei pochi che ha letto l'intero codice.
# Sei un programmatore curioso, complimenti!
# Sei un grande! Grazie per il tuo tempo.
# Un programmatore è un organismo che trasforma caffè in codice.
# Da grandi poteri derivano grandi responsabilità.
# --------------------------------------------------------------------------------------------------
