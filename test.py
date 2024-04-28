import binascii
import socket
import struct
import ctypes
import math
import numpy as np
import matplotlib.pyplot as plt

def send_scanning_spectrum_msg(host,start_freq=1.4e9,end_freq=1.8e9):
    # 绑定端口:
    format1 =  struct.Struct(
            '>' + 'b' + 'H' + 'H' + 'b')  # 1字节起始字节 + 2字节short起始频率+2字节结束频率+1字节结束字节
    buff = ctypes.create_string_buffer(format1.size)
    format1.pack_into(buff,0,0b00001100,int((math.ceil(start_freq / 1e6))),int((end_freq/ 1e6)), 0b00001100)
    print(print('打包结果:', binascii.hexlify(buff)))
    s.sendto(buff, host)

if __name__ == '__main__':
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print('Bind UDP on 9999...')
    host_ip = socket.gethostbyname_ex(socket.gethostname())[-1][0]
    print(host_ip)
    host = (host_ip, 9999)
    device_id = '192.168.201.253'
    s.bind(host)  
    # send_scanning_spectrum_msg((device_id,9999))
    res = []

    start_freq = 0;
    freq = 0
    while True:
        # # 接收数据:
        size = 1
        # if(ctn >1600):
        #     break
        data, addr = s.recvfrom(1024)
        #以太网最大分组长度为1500，ip20,udp8，最大1472，设定1024最大/packet
        format = struct.Struct(
            '>' + 'b' + 'b' + size * 'Hf' + 'b')  # 1字节起始字节 + 1字节命令字段 + 2字节unsigned short序号+ 4字节 float功率值+1字节结束字节
        print("receving from" + str(addr))

        (flag1,cmd,freq,power,flag2) = format.unpack_from(data)

        if freq == 0:
            start_freq = int(freq)
            freq = start_freq
        ctn = int(freq)
        res.append(power)
        print('原始二进制数据:', binascii.hexlify(data))
        print("起始字节\t命令字段\t频点\t功率值\t结束字段")
        print( (flag1,cmd,freq,power,flag2) )
        freq = freq+1

    x =np.arange(start_freq, freq )
    plt.plot(x,res)
    plt.show()
