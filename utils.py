import queue

class SizedCache:
    def __init__(self, maxsize):
        self.maxsize = maxsize
        self.cache = queue.Queue(maxsize=self.maxsize)

    def put(self, data):
        if self.cache.full():
            self.flush()
        self.cache.put(data)

    def flush(self):
        while not self.cache.empty():
            data = self.cache.get()
            # 处理数据，这里只是简单打印
            print("处理数据:", data)
        print(self.cache.empty())
if __name__ == '__main__':

    # 使用示例
    cache = SizedCache(1)  # 指定缓存大小为3
    cache.put((1, 1, 10000, 20, 1))
    cache.put((1, 1, 10000, 20, 1))
    cache.put((1, 1, 10000, 20, 1))
    cache.put((1, 1, 10000, 20, 1))  # 缓存已满，此时会将数据送出

