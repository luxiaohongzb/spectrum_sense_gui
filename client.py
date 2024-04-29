import binascii
import socket
import struct
import ctypes
import math
import numpy as np
import matplotlib.pyplot as plt



def send_scanning_spectrum_msg(host,start_freq=2400,end_freq=3000):
    # 绑定端口:
    format1 =  struct.Struct(
            '>' + 'b' + 'H' + 'H' + 'b')  # 1字节起始字节 + 2字节short起始频率+2字节结束频率+1字节结束字节
    buff = ctypes.create_string_buffer(format1.size)
    format1.pack_into(buff,0,0b00001100,start_freq,end_freq, 0b00001100)
    print(print('打包结果:', binascii.hexlify(buff)))
    s.sendto(buff, host)

def find_max(x,y):
    max_index = np.argmax(y)
    max_x = x[max_index]
    max_y = y[max_index]
    return max_x,max_y


if __name__ == '__main__':

    start_freq =4000

    band_width =500   


    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print('Bind UDP on 9999...')
    # host_ip = socket.gethostbyname_ex(socket.gethostname())[-1][0]
    # print(host_ip)
    host = ('192.168.201.110', 9999)
    device_id = '192.168.201.253'
    s.bind(host)  
    send_scanning_spectrum_msg((device_id,9999),start_freq,start_freq+band_width)
    res = []
    ctn = start_freq
    size = 50
    format = struct.Struct(
         '>' + 'b' + 'b' + size* 'Hf' + 'b')  # 1字节起始字节 + 1字节命令字段 + 2字节unsigned short序号+ 4字节 float功率值+1字节结束字节
    while True:
        # 接收数据:

        if(ctn >=start_freq+band_width):
            break
        if(start_freq+band_width - ctn <= size):
               format = struct.Struct(
                '>' + 'b' + 'b' + (start_freq+band_width - ctn)* 'Hf' + 'b')  # 1字节起始字节 + 1字节命令字段 + 2字节unsigned short序号+ 4字节 float功率值+1字节结束字节
        data, addr = s.recvfrom(1024)
        #以太网最大分组长度为1500，ip20,udp8，最大1472，设定1024最大/packet

        print("receving from" + str(addr))

        (begin_flag,freq_dot_num,*_data,end_flag)= format.unpack_from(data)
        #频率增加
        print(_data)
        ctn = ctn + int(freq_dot_num)
        # (begin_flag,start_freq,end_freq,end_flag) 
        # ctn = int(freq)
        res =  [*res,*_data]
        # print(res)
        # print('原始二进制数据:', binascii.hexlify(data))
        # print("起始字节\t命令字段\t频点\t功率值\t结束字段")
    
    
    
    freq = [res[i] for i in range(len(res)) if i % 2 == 0]

    power = [res[i] for i in range(len(res)) if i % 2 != 0]
    max_x,max_y = find_max(freq,power)
    print("max freq value:"+str(max_y)+"db at "+str(max_x)+"MHz")
    # 标出最高点及其数值
    plt.scatter(max_x, max_y, color='red', label=f'Max freq ({max_x:.2f}, {max_y:.2f})')
    plt.legend()
    plt.xlabel("freq/MHz")
    plt.ylabel("power/dbm")
    plt.plot(freq,power)
    plt.show()
