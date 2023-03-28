
import hashlib
import sys
import json
import socket

from PyQt6.QtWidgets import (
    QMainWindow, QApplication, QPushButton,
    QLabel, QWidget, QTextEdit, QLineEdit,
    QHBoxLayout, QVBoxLayout
)
from PyQt6 import QtCore
from PyQt6.QtCore import Qt, QThread, QObject


# Intermediate Media - User Defined Data Type
class OrderMsg:
    def __init__(self, worker_count, worker_id, client_id, raw_text):
        self.worker_count = worker_count
        self.worker_id = worker_id
        self.client_id = client_id
        self.raw_text = raw_text


class Sender(QObject):

    def __init__(self, sock):
        super(Sender, self).__init__()

        self.sock = sock

    @QtCore.pyqtSlot(str)
    def work(self, msg):
        print(msg)


class Receiver(QObject):

    signal_order_msg = QtCore.pyqtSignal(OrderMsg)
    signal_start_mining = QtCore.pyqtSignal(bool)
    signal_stop_mining = QtCore.pyqtSignal(bool)

    def __init__(self, sock: socket.socket):
        super(Receiver, self).__init__()

        self.sock = sock

    @QtCore.pyqtSlot(bool)
    def work(self):

        while True:
            data = self.sock.recv(1024).decode('utf-8')
            print('Server\'s command: --', data, '--')
            if data is None or data == '':
                self.sock.close()
                print('Connection break.')
                exit(0)
            data = json.loads(data)
            if data['command_type'] == 1:
                order_msg = OrderMsg(data['worker_count'], data['worker_id'], data['client_id'], data['raw_text'])
                self.signal_start_mining.emit(True)
                self.signal_order_msg.emit(order_msg)
            elif data['command_type'] == 2:
                print('Send stopping command...')
                self.signal_stop_mining.emit(True)


class Miner(QObject):

    def __init__(self, sock: socket.socket):
        super(Miner, self).__init__()

        self.working = False

        self.sock = sock

    @QtCore.pyqtSlot(OrderMsg)
    def work(self, order_msg: OrderMsg):
        # Param #
        difficulty = 6

        difficulty_number = ''
        for i in range(difficulty):
            difficulty_number += '0'

        step = 0
        worker_count = order_msg.worker_count
        worker_id = order_msg.worker_id
        client_id = order_msg.client_id
        raw_text = order_msg.raw_text
        h = hashlib.sha256()

        while self.working:
            nonce = worker_id + worker_count * step
            combine_text = str(raw_text) + str(nonce)
            h.update(combine_text.encode('utf-8'))
            gold_hash = h.hexdigest()
            step += 1
            if gold_hash[0: difficulty] == difficulty_number:
                print(gold_hash)
                print('Successful mining!')
                # Send back to master
                reply_command = json.dumps(self.json_generator(1, gold_hash, client_id))
                self.sock.send(reply_command.encode('utf-8'))
                break
            else:
                continue

        print('Mining Stop.', 'Step usage:', step)

    @QtCore.pyqtSlot(bool)
    def get_start_signal(self):
        self.working = True

    def json_generator(self, command_type, gold_hash, client_id):
        # command_type:
        #   1: return gold hash
        #   2: disconnection
        command = {
            'command_type': command_type,
            'gold_hash': gold_hash,
            'client_id': client_id
        }
        return command


class Client(QObject):

    signal_sender_msg = QtCore.pyqtSignal(str)
    signal_receiver_working = QtCore.pyqtSignal(bool)

    def __init__(self, addr, port):
        super(Client, self).__init__()

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.addr = addr
        self.port = port
        self.state = False  # non-active

        # Bind Sender & Receiver & Miner
        self.sender = Sender(self.sock)
        self.receiver = Receiver(self.sock)
        self.miner = Miner(self.sock)
        # - connections
        self.signal_sender_msg.connect(self.sender.work)
        self.signal_receiver_working.connect(self.receiver.work)
        self.receiver.signal_order_msg.connect(self.miner.work)
        self.receiver.signal_start_mining.connect(self.miner.get_start_signal)
        self.receiver.signal_stop_mining.connect(self.stop)
        # - s
        self.thread_sender = QThread()
        self.sender.moveToThread(self.thread_sender)
        self.thread_sender.start()
        # - r
        self.thread_receiver = QThread()
        self.receiver.moveToThread(self.thread_receiver)
        self.thread_receiver.start()
        # - m
        self.thread_miner = QThread()
        self.miner.moveToThread(self.thread_miner)
        self.thread_miner.start()

        # Do connection
        self.connect_server()
        # Do receive
        self.signal_receiver_working.emit(True)

    @QtCore.pyqtSlot(bool)
    def stop(self):
        # Restart thread
        self.thread_miner.quit()
        self.miner.working = False
        print('Miner current state:', self.miner.working)
        self.thread_miner.start()
        print('OK, I stop now.')

    def connect_server(self):

        try:
            print('Start connect to server...')
            self.sock.connect((self.addr, self.port))
            self.state = True
        except socket.error as err:
            print('Client: socket connection error:', err)
        finally:
            print('Connection successful!')

    def send_msg(self, msg):
        self.signal_sender_msg.emit(msg)


class ClientWindow(QMainWindow):

    def __init__(self, name):
        super(ClientWindow, self).__init__()

        self.setWindowTitle("Client" + name)

        self.main_widget = QWidget()

        self.main_layout = QVBoxLayout()

        # Load Client Object
        self.client = Client('127.0.0.1', 8848)

        # self.mining_state = QLabel('Inactive.')
        # self.main_layout.addWidget(self.mining_state)

        self.main_widget.setLayout(self.main_layout)

        self.setCentralWidget(self.main_widget)

        self.show()


if __name__ == '__main__':

    app = QApplication(sys.argv)
    window = ClientWindow(sys.argv[1])
    app.exec()
