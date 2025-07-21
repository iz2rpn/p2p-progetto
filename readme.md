
# P2P File Synchronization – An Educational Project

This is an educational project aimed at understanding how a peer-to-peer (P2P) file synchronization system works. It implements a P2P node that enables file synchronization between multiple devices without the need for centralized servers, using only Python's standard libraries.

---

## Key Features

* **File synchronization between peers**: Each node keeps local files in sync with other nodes in the P2P network.
* **Automatic peer discovery**: Peers automatically discover each other using a multicast broadcast mechanism.
* **File transfer support**: Files are transferred in chunks to optimize bandwidth usage.
* **No external modules**: The project uses only Python’s standard library—no third-party dependencies.
* **Automatic synchronization**: Files are periodically synchronized to ensure that all devices stay up to date.

---

## How It Works

1. **Peer Discovery**
   Each node sends a multicast packet to announce its presence. Other peers receive the announcement and add the sender to their peer list.

2. **File Synchronization**
   Each peer has a shared folder used for synchronization. When a new peer joins, it synchronizes with existing peers to match the file set. Files are transferred in blocks.

3. **Data Transfer**
   Data is transferred over TCP connections. Files are split into chunks and sent so that they can be rebuilt on the receiving side.

4. **Synchronization Interval**
   The node synchronizes files at regular intervals to keep all peers aligned.

---

## How to Start a Node

1. **Clone the repository**

   ```bash
   git clone https://github.com/iz2rpn/p2p-file-sync.git
   cd p2p-file-sync
   ```

2. **Run the P2P node**

   ```bash
   python p2p_file_sync.py
   ```

Make sure you have the necessary permissions for opening network ports and that no firewalls are blocking multicast traffic.

---

## Peer and File Monitoring

While running, the node will display logs in the console showing its status, detected peers, and synchronized files.

---

## Additional Features

* **Automatic creation of the "shared" folder** if it doesn’t exist.
* **File integrity check** using hash verification to ensure files are not corrupted during transfer.

---

## Technologies Used

* **Python 3**: Built entirely with Python 3 using only the standard library.
* **Sockets (TCP/UDP)**: For peer communication.
* **Multicast (UDP)**: For peer discovery in the local network.

---

## Contributing

Feel free to fork this repository and submit a pull request if you'd like to contribute. For bugs or feature requests, please open an issue in the repository.

---

## Disclaimer

This project is for educational purposes only and is not intended for production use. It may not be suitable for high-traffic or high-reliability environments.

---

## License

Apache License
Version 2.0, January 2004
Copyright (c) \[2025] \[Pietro Marchetta]

---
