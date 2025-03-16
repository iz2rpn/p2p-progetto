# P2P File Synchronization - Un progetto didattico

Questo è un progetto didattico che ha come obiettivo quello di comprendere come funziona un sistema di sincronizzazione file peer-to-peer (P2P). In questo caso, è stato sviluppato un nodo P2P che permette di sincronizzare file tra diversi dispositivi, senza l'uso di server centralizzati, utilizzando solo librerie standard di Python.

## Caratteristiche principali
- **Sincronizzazione dei file tra peer:** Il nodo permette la sincronizzazione dei file locali tra i dispositivi che partecipano alla rete P2P.
- **Scoperta automatica dei peer:** I peer nella rete si scoprono automaticamente attraverso un meccanismo di broadcast multicast.
- **Supporto per trasferimento file:** I file vengono trasferiti a blocchi per una gestione ottimizzata della banda.
- **No moduli esterni:** Il progetto non ha bisogno di librerie di terze parti, utilizzando solo le librerie standard di Python.
- **Sincronizzazione automatica:** I file vengono periodicamente sincronizzati tra i peer, assicurando che tutti i dispositivi abbiano gli stessi file aggiornati.

## Come funziona

1. **Scoperta dei Peer**  
   Ogni nodo invia un pacchetto multicast per annunciare la sua presenza alla rete. Gli altri peer ricevono questo annuncio e si aggiungono automaticamente alla lista dei peer.

2. **Sincronizzazione dei File**  
   Ogni peer ha una cartella condivisa dove vengono sincronizzati i file. Quando un nuovo peer si connette, si sincronizza con i peer esistenti per avere gli stessi file. I file vengono trasferiti in blocchi.

3. **Trasferimento dei Dati**  
   I dati vengono trasferiti tramite connessioni TCP, dove i file vengono divisi in blocchi e inviati ai peer in modo che possano essere ricostruiti localmente.

4. **Intervallo di Sincronizzazione**  
   Il nodo sincronizza automaticamente i file con gli altri peer a intervalli regolari per assicurarsi che tutti i file siano allineati.

## Come avviare il nodo

1. **Clona il repository**  
   Per prima cosa, clona questo repository:

   ```bash
   git clone https://github.com/iz2rpn/p2p-file-sync.git
   cd p2p-file-sync
   ```

## Esegui il nodo P2P

Per avviare il nodo, esegui lo script Python:

```bash
python p2p_file_sync.py
```

Assicurati di avere i permessi necessari per l'apertura delle porte di rete e che non ci siano firewall che bloccano il traffico multicast.

## Monitoraggio dei Peer e File
Durante l'esecuzione, vedrai i log sulla console che indicano lo stato del nodo, i peer rilevati e i file sincronizzati.

## Funzionalità aggiuntive
Sincronizzazione automatica della cartella "shared": La cartella di condivisione viene creata automaticamente se non esiste.

- Verifica dell'integrità dei file: Ogni file trasferito viene verificato tramite il calcolo dell'hash per assicurarsi che i dati non siano corrotti durante il trasferimento.

## Tecnologie utilizzate
- Python 3: Il progetto è sviluppato con Python 3 e non richiede l'installazione di moduli esterni. Le librerie standard di Python sono sufficienti.

- Socket (TCP/UDP): Utilizzo di socket per la gestione delle comunicazioni tra peer.

- Multicast: Utilizzo di UDP multicast per la scoperta dei peer nella rete.

## Contribuire
Se desideri contribuire al progetto, sentiti libero di fare una fork e inviare una pull request. Per qualsiasi bug o richiesta di funzionalità, apri un issue nel repository.

## Avviso
Questo progetto è stato realizzato a scopo didattico per capire come funzionano i sistemi P2P e non è destinato a un uso in produzione. Potrebbe non essere adatto per ambienti con elevato traffico di rete o requisiti di alta affidabilità.

## Licenza
Apache License
Version 2.0, January 2004

Copyright (c) [2025] [Pietro Marchetta]


