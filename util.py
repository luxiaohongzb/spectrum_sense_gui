import binascii
import socket
import struct
import ctypes
import math
import numpy as np
import matplotlib.pyplot as plt
import socket

from datetime import datetime
import time
def find_max(x,y):
    max_index = np.argmax(y)
    max_x = x[max_index]
    max_y = y[max_index]
    return max_x,max_y


def is_socketed_connected(so):
     try: 
        
        remote_addr = so.getpeername()
        print(remote_addr)
        return True
     except socket.error:
        return False

def read_second_byte(data):
    try:
        # 解包数据，从第二个字节开始读取一个无符号整数
        second_byte = struct.unpack('!B', data[1:2])[0]
        return second_byte
    except struct.error as e:
        print(f"Error reading second byte: {e}")
        return None
def get_ip():
    addrs = socket.getaddrinfo(socket.gethostname(),None)
    addr_list = []
    for item in addrs:
        if ':' not in item[4][0]:
            addr_list.append(item[4][0])

    return addr_list

def send_scanning_spectrum_msg(device_addr,start_freq=2400,end_freq=3000):
    so = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # 绑定端口:
    format1 =  struct.Struct(
            '>' + 'b' + 'H' + 'H' + 'b')  # 1字节起始字节 + 2字节short起始频率+2字节结束频率+1字节结束字节
    buff = ctypes.create_string_buffer(format1.size)
    format1.pack_into(buff,0,0b00001100,start_freq,end_freq, 0b00001100)
    # print(print('打包结果:', binascii.hexlify(buff)))
    so.sendto(buff, device_addr)

def find_max(x,y):
    max_index = np.argmax(y)
    max_x = x[max_index]
    max_y = y[max_index]
    return max_x,max_y

def get_time():
 
    # 获取当前时间戳（秒精确到整数）
    current_time = int(time.time())

    # 使用 datetime.fromtimestamp() 方法将时间戳转换为标准时间
    formatted_time = datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')


    return formatted_time

if __name__ == '__main__':

    pass