import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QTextEdit, QPushButton, QLineEdit, QLabel,QHBoxLayout,QComboBox
from PyQt5.QtCore import Qt
import socket
import struct
import numpy as np
import queue
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5 import QtCore, QtGui, QtWidgets
from util import send_scanning_spectrum_msg,read_second_byte,get_ip,is_socketed_connected,find_max
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
class DataReceiver(QThread):
    dataReceived = pyqtSignal(list)
    msg_printer =  pyqtSignal(str)
    end_signal = pyqtSignal(int)
    def __init__(self,socket):
        super().__init__()
        self.s = socket
        self.ctn = 0 
        print()
    def set_socket(self,so):
        self.s = so
    def set_ctn(self,ctn):
        self.ctn = ctn
    def get_ctn(self):
        return self.ctn
    def so_change_signal_handler(self):
        pass
    def run(self):
        s = self.s
    
        while True:
            try:
               # 接收数据:
                # if(ctn >=start_freq+band_width):
                #     break
                # if(start_freq+band_width - ctn <= size):

                data, addr = s.recvfrom(1024)
                size = read_second_byte(data)
                self.set_ctn(size + self.get_ctn())
                format = struct.Struct(
                 '>' + 'b' + 'b' + size* 'Hf' + 'b')  # 1字节起始字节 + 1字节命令字段 + 2字节unsigned short序号+ 4字节 float功率值+1字节结束字节
                (begin_flag,freq_dot_num,*_data,end_flag)= format.unpack_from(data)
                self.msg_printer.emit(f"Received from {addr}")
                self.dataReceived.emit(_data)
                #以太网最大分组长度为1500，ip20,udp8，最大1472，设定1024最大/packet
                print("receving from" + str(addr))  
        
                self.end_signal.emit(self.get_ctn())
            except socket.error:
                pass

class UDPReceiver(QMainWindow):
    so_change_signal = pyqtSignal(int)
    def __init__(self):
        super().__init__()
        self.device_addr = ("192.168.201.253",9999)
        self.initUI()
        self.receiver_thread = DataReceiver(self.get_socket())
        self.receiver_thread.msg_printer.connect(self.updateText)
        self.receiver_thread.end_signal.connect(self.hendle_end_signal)
        self.receiver_thread.dataReceived.connect(self.update_data)
        self.receiver_thread.start()
        self.plot_freq = []
        self.plot_power = []
    def initUI(self):
        self.setWindowTitle('频谱感知调试程序by闸北陆小洪')
        self.setGeometry(100, 100, 800, 600)
        
        layout = QVBoxLayout()

    
        text_monitor_layer=  QHBoxLayout()

        input_layout = QHBoxLayout()
        self.data_edit = QTextEdit()
        self.data_edit.setMaximumHeight(500)
        self.log_edit = QTextEdit()
        self.log_edit.setMaximumHeight(500)
        # self.text_edit.setFixedHeight(200)
        text_monitor_layer.addWidget(self.data_edit)
        text_monitor_layer.addWidget(self.log_edit)
        self.plot_widget = PlotWidget()
        layout.addWidget(self.plot_widget)



        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        self.addr_label = QLabel("本地主机地址")
        input_layout.addWidget(self.addr_label)
        self.addr_combobox = QComboBox()
        self.addr_combobox.setEditable(True)
        # self.combobox.view().setSelectionMode(QComboBox.mu)
        self.addr_combobox.addItems(get_ip())
        self.addr_combobox.setCurrentIndex(2)
        input_layout.addWidget(self.addr_combobox)

      

        self.master_aadr_label = QLabel("主控地址")    
        input_layout.addWidget(self.master_aadr_label)
        self.master_aadr = QLineEdit()
        self.master_aadr.setText('192.168.201.253')
        input_layout.addWidget(self.master_aadr)





        self.udp_connect_btn = QPushButton("打开")
        self.udp_connect_btn.clicked.connect(self.initSocket)
        input_layout.addWidget(self.udp_connect_btn)
        
        self.freq_start_label = QLabel("Freq_Start")
        input_layout.addWidget(self.freq_start_label)
        self.freq_start_input = QLineEdit()
        self.freq_start_input.setText('300')
        input_layout.addWidget(self.freq_start_input)

        self.freq_end_label = QLabel("Freq_End")    
        input_layout.addWidget(self.freq_end_label)
        self.freq_end_input = QLineEdit()
        self.freq_end_input.setText('400')
        input_layout.addWidget(self.freq_end_input)

        self.send_button = QPushButton("Send Data")
        self.send_button.clicked.connect(self.sendData)
        input_layout.addWidget(self.send_button)
        layout.addLayout(text_monitor_layer)   
        layout.addLayout(input_layout)    

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
    

        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def updateText(self, data):
        self.log_edit.append(data)
    def get_freq_range(self):
        return  int(self.freq_start_input.text()), int(self.freq_end_input.text())
    def hendle_end_signal(self,ctn):
        freq_bandwidth = self.get_freq_range()[1] - self.get_freq_range()[0]
        max_x,max_y = self.plot_widget.updatePlot(self.plot_freq,self.plot_power)
        self.logger_write("max freq value:"+str(max_y)+"db at "+str(max_x)+"MHz")
        if(ctn>=freq_bandwidth):
            #清空数据
            self.plot_freq = []
            self.plot_power = []
            self.receiver_thread.set_ctn(0)
            self.plot_widget.clearPlot()
    def sendData(self):
        # self.initSocket((self.addr_combobox.currentText(),9999))
        try:
            (start_freq,end_freq) = self.get_freq_range()
            send_scanning_spectrum_msg(self.device_addr, start_freq,end_freq)
        except Exception as e:  
            self.log_edit.append("Error: Invalid input" +str(e))

    def initSocket(self):
        self.so_change_signal.emit(1)
        # self.get_socket().close()
        host = (self.addr_combobox.currentText(),9999)
        print(host)
        try:    

            # if(is_socketed_connected(self.get_socket())):
            #      self.get_socket().close()
            # self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.bind(host)  # 绑定到本地地址和端口
            # self.udp_socket.listen(5)
        except Exception as e:
            print(e)
            self.log_edit.append("Error:"+ str(e))
            self.udp_socket.close()
            print(self.udp_socket.getpeername())
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        #self.udp_socket.setblocking(False)  # 将 socket 设置为非阻塞模式
    def get_socket(self):
        return self.udp_socket
    def update_data(self,data_list):      
        self.data_edit.append(str(data_list))
        _freq = [data_list[i] for i in range(len(data_list)) if i % 2 == 0]
        _power = [data_list[i] for i in range(len(data_list)) if i % 2 != 0]
        self.plot_freq = [*self.plot_freq,*_freq] 
        self.plot_power = [*self.plot_power,*_power]

    #     try:
    #         data, addr = self.udp_socket.recvfrom(1024)
    #         self.text_edit.append(f"Received from {addr}: {data.decode('ISO-8859-1')}")
    #         # 在这里更新图形
    #         # 这里仅作示例，假设收到的数据是频率和功率的一对值
    #         frequency, power = map(float, data.decode().split(','))
    #         self.plot_widget.updatePlot(frequency, power)
    #     except socket.error:
    #         pass
    def logger_write(self,msg):
        self.log_edit.append(msg)
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.close()

    def closeEvent(self, event):
        self.udp_socket.close()
        event.accept()

class PlotWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        self.setLayout(layout)

        self.ax.set_xlabel('Frequency/MHz')
        self.ax.set_ylabel('Power/dbm')

        self.line, = self.ax.plot([], [], 'r-')  # 创建空的折线

    def updatePlot(self, frequency, power):
        # 清除之前的图形
        self.clearPlot()

        # 更新折线
        # self.line.set_xdata(np.append(self.line.get_xdata(),1))
        # self.line.set_ydata(np.append(self.line.get_ydata(), 1))
        self.ax.plot(frequency, power)
        max_x,max_y = find_max(frequency,power)
        print("max freq value:"+str(max_y)+"db at "+str(max_x)+"MHz")
        # 标出最高点及其数值
        plt.scatter(max_x, max_y, color='red', label=f'Max freq ({max_x:.2f}, {max_y:.2f})')
        plt.legend()
        # 重新绘制
        self.canvas.draw()
        return max_x,max_y
    def clearPlot(self):
        self.ax.clear()
        self.ax.set_xlabel('Frequency')
        self.ax.set_ylabel('Power')

if __name__ == '__main__':
    app = QApplication(sys.argv)
        # 设置全局字体大小为12
    font = QFont("Arial", 12)
    app.setFont(font)
    receiver = UDPReceiver()
    receiver.show()
    
    #timer = app.createTimer(receiver.receiveData, 100)  # 100ms 定时器，用于周期性检查是否有数据到达
    
    sys.exit(app.exec_())
