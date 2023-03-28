
import sys
import json
import time
import socket

from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QPushButton,
    QLabel, QWidget, QTextEdit, QLineEdit,
    QHBoxLayout, QVBoxLayout
)
from PyQt6 import QtCore
from PyQt6.QtCore import Qt, QThread, QObject


class Receptionist(QObject):

    signal_connection = QtCore.pyqtSignal(socket.socket)

    def __init__(self, sock: socket.socket):
        super(Receptionist, self).__init__()

        self.sock = sock

    @QtCore.pyqtSlot(bool)
    def working(self):

        while True:
            print('Receptionist: I am waiting for new connection...')
            sock, addr = self.sock.accept()
            print('Receptionist: New connection', addr)  # -> (ipaddr, port)
            self.signal_connection.emit(sock)
            
            
class Receiver(QObject):

    signal_gold_hash = QtCore.pyqtSignal(str)
    
    def __init__(self, client_sock: socket.socket):
        super(Receiver, self).__init__()

        self.client_sock = client_sock

        self.client_id = str(client_sock.getpeername()[0]) + '-' + str(client_sock.getpeername()[1])

        self.working_statu = True

    @QtCore.pyqtSlot(bool)
    def work(self):
        if self.working_statu:
            print(self.client_id, 'I start to work')
            self.working_statu = False
            while True:
                # Wait the msg of this client
                data = self.client_sock.recv(1024).decode('utf-8')
                data = json.loads(data)
                if data['command_type'] == 1:
                    gold_hash = data['gold_hash']
                    print(data['client_id'], 'got gold hash:', gold_hash)
                    self.signal_gold_hash.emit(gold_hash)
                elif data['command_type'] == 2:
                    print(data['client_id'], 'I am disconnecting')
        else:
            print(self.client_id, 'I am working now!')


class Server(QObject):

    signal_receptionist_working = QtCore.pyqtSignal(bool)
    signal_clients_pool_dict = QtCore.pyqtSignal(dict)
    signal_receiver_working = QtCore.pyqtSignal(bool)
    signal_gold_hash = QtCore.pyqtSignal(str)

    def __init__(self, port, max_clients):
        super(Server, self).__init__()

        self.hostname = socket.gethostname()
        self.ip_address = socket.gethostbyname(self.hostname)
        self.port = port

        # Client Pool
        self.clients = dict()
        # Sub-server (receiver) pool
        self.receivers = dict()
        self.threads_r = dict()
        self.signal_usage = 0  # For the signal warehouse

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.ip_address, self.port))
        self.sock.listen(max_clients)

        # Create Receptionist
        self.receptionist = Receptionist(self.sock)
        # Linking work
        self.signal_receptionist_working.connect(self.receptionist.working)
        self.receptionist.signal_connection.connect(self.store_new_client)
        # New thread
        self.thread_receptionist = QThread()
        self.receptionist.moveToThread(self.thread_receptionist)
        self.thread_receptionist.start()
        # Let receptionist working
        self.signal_receptionist_working.emit(True)

    @QtCore.pyqtSlot(socket.socket)
    def store_new_client(self, sock: socket.socket):
        ipaddr = sock.getpeername()[0]
        port = sock.getpeername()[1]
        client_id = str(ipaddr) + '-' + str(port)
        self.clients[client_id] = sock
        self.signal_clients_pool_dict.emit(self.clients)

        # Provide service to new connected client #
        # - create new receiver (sub-server)
        self.receivers[client_id] = Receiver(sock)
        # - build connections
        self.receivers[client_id].signal_gold_hash.connect(self.get_gold_hash)
        self.signal_receiver_working.connect(self.receivers[client_id].work)
        # - create new thread
        self.threads_r[client_id] = QThread()
        self.receivers[client_id].moveToThread(self.threads_r[client_id])
        self.threads_r[client_id].start()
        # Let it work
        self.signal_receiver_working.emit(True)

    @QtCore.pyqtSlot(bool)
    def start_mining(self):
        print('Server: Start Mining!')
        my_workers = list(self.clients.keys())
        worker_id = 0
        for worker in my_workers:
            client_id = worker
            worker_addr, worker_port = str(worker).split('-')[0], str(worker).split('-')[1]
            worker_sock = self.clients.get(worker)
            # ---- Send start mining command ---- #
            mining_command = json.dumps(self.json_generator(
                1, worker_id, client_id, 'hello distributed computing system'))
            worker_sock.send(mining_command.encode('utf-8'))
            worker_id += 1

    @QtCore.pyqtSlot(str)
    def get_gold_hash(self, gold_hash):
        stop_mining_command = json.dumps(self.json_generator(2, None, None, None))
        my_workers = list(self.clients.keys())
        worker_id = 0
        for worker in my_workers:
            worker_sock = self.clients.get(worker)
            # ---- Send stop mining command ---- #
            worker_sock.send(stop_mining_command.encode('utf-8'))
            worker_id += 1
        print('Server:', 'gold hash:', gold_hash)
        self.signal_gold_hash.emit(gold_hash)

    def json_generator(self, command_type, worker_id, client_id, raw_text):
        # command_type:
        #   1: start
        #   2: stop
        command = {
            'command_type': command_type,
            'worker_count': len(self.clients),
            'worker_id': worker_id,
            'client_id': client_id,
            'raw_text': raw_text
        }
        return command

    def desc_basic_info(self):
        print('hostname:', self.hostname)
        print('ip address:', self.ip_address)


class ServerWindow(QMainWindow):

    signal_start_mining = QtCore.pyqtSignal(bool)

    def __init__(self):
        super(ServerWindow, self).__init__()

        self.setWindowTitle("Server")

        self.main_widget = QWidget()

        self.main_layout = QVBoxLayout()

        # Load Client Object
        self.server = Server(8848, 10)
        # Build linking
        self.server.signal_clients_pool_dict.connect(self.update_client_pool)
        self.signal_start_mining.connect(self.server.start_mining)
        self.server.signal_gold_hash.connect(self.display_gold_hash)
        # New thread
        self.thread_server = QThread()
        self.server.moveToThread(self.thread_server)
        self.thread_server.start()

        # Counter & Pool
        self.connected_client_count = QLabel('Available Worker: 0')
        self.connected_client_pool = QTextEdit()

        # Button
        self.start_mining_btn = QPushButton('Start Mining!')
        self.start_mining_btn.clicked.connect(self.start_mining)

        # Gold hash
        self.gold_hash_display = QLabel('Gold Hash:\nNone')

        # Display Widgets
        self.main_layout.addWidget(self.start_mining_btn)
        self.main_layout.addWidget(self.gold_hash_display)
        self.main_layout.addWidget(self.connected_client_count)
        self.main_layout.addWidget(self.connected_client_pool)

        self.main_widget.setLayout(self.main_layout)

        self.setCentralWidget(self.main_widget)

        self.show()

    @QtCore.pyqtSlot(dict)
    def update_client_pool(self, client_pool: dict):
        client_ids = list(client_pool.keys())
        client_pool_text = ''
        for client_id in client_ids:
            client_pool_text += client_id + '\n'
        self.connected_client_pool.setText(client_pool_text)
        self.connected_client_count.setText('Available Worker: ' + str(len(client_pool)))

    @QtCore.pyqtSlot(str)
    def display_gold_hash(self, gold_hash):
        self.gold_hash_display.setText('Gold Hash:\n' + gold_hash)

    def start_mining(self):
        self.signal_start_mining.emit(True)


if __name__ == '__main__':

    app = QApplication(sys.argv)
    window = ServerWindow()
    app.exec()
