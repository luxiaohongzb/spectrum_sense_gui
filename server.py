import binascii
import queue
import socket
import struct
import ctypes
import time


class SizedCache:
    def __init__(self, maxsize):
        self.maxsize = maxsize
        self.cache = queue.Queue(maxsize=self.maxsize)
        self.format = struct.Struct(
            '>' + 'b' + 'b' + maxsize * 'Hf' + 'b')  # 1字节起始字节 + 1字节命令字段 + 2字节unsigned short序号+ 4字节 float功率值+1字节结束字节

    def put(self, data):
        if self.cache.full():
            return 0
        self.cache.put(data)
        # print("put" + str(data))

    def full(self):
        return self.cache.full()

    def flush(self):
        s = self.format
        buff = ctypes.create_string_buffer(s.size)
        _data = ()
        print(s.size)
        while not self.cache.empty():
            _data = (*_data, *self.cache.get())
        s.pack_into(buff, 0,0b00001100,0b00010010, *_data, 0b00001100)

        print("已清空！")
        return buff


if __name__ == '__main__':
    so = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # 绑定端口:
    cache = SizedCache(10)
    while True:
        if cache.full():
            data = cache.flush()
            time.sleep(1)
            so.sendto(data, ('127.0.0.1', 9999))
        cache.put((1, -15.3))

    # print(s.size)
    # data = s.pack(1, 1, 10000, 20, 1)
    # print('原始值:', data)
    # print('占用字节:', s.size)
    # print('打包结果:', binascii.hexlify(data))
    # 发送数据:

    # # 接收数据:
    # so.close()
