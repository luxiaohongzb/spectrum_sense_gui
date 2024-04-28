import binascii
import socket
import struct

print("hekk")

def send_scanning_spectrum_msg(host,start_freq=2e9,end_freq=4e9):
    # 绑定端口:
    format1 =  struct.Struct(
            '>' + 'b' + 'H' + 'H' + 'b')  # 1字节起始字节 + 2字节short起始频率+2字节结束频率+1字节结束字节   

    format1.pack_into(0b00001100,start_freq,end_freq, 0b00001100)
    s.sendto(data, host)


if __name__ == '__main__':
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    print('Bind UDP on 9999...')
    host = ('192.168.201.253', 9999)
    s.bind(host)  
    send_scanning_spectrum_msg(host)
    while True:
        # 接收数据:
        size = 1
        data, addr = s.recvfrom(1024)
        #以太网最大分组长度为1500，ip20,udp8，最大1472，设定1024最大/packet
        format = struct.Struct(
            '>' + 'b' + 'b' + size * 'Hf' + 'b')  # 1字节起始字节 + 1字节命令字段 + 2字节unsigned short序号+ 4字节 float功率值+1字节结束字节
        print("receving from" + str(addr))
        data_unpuck = format.unpack_from(data)
        print('原始二进制数据:', binascii.hexlify(data))
        print("起始字节\t命令字段\t频点\t功率值\t结束字段")
        print(data_unpuck)
