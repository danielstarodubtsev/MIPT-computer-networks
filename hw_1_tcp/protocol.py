import socket
import math

def InsertMsg(buffer: list, cur):
    for i in range(len(buffer)):
        if (buffer[i][0] == cur[0]):
            return
        if (buffer[i][0] > cur[0]):
            buffer.insert(i, cur)
            return

    buffer.append(cur)

def int32tobytes(x: int) -> bytes:
    return bytes([(x >> 24) & ((1 << 8) - 1), (x >> 16) & ((1 << 8) - 1), (x >> 8) & ((1 << 8) - 1), (x >> 0) & ((1 << 8) - 1)])

def bytestoint32(b: bytes) -> int:
    return (int(b[0]) << 24) + (int(b[1]) << 16) + (int(b[2]) << 8) + (int(b[3]) << 0)

def int8tobytes(x: int) -> bytes:
    return bytes([x])

def bytestoint8(b: bytes) -> int:
    return int(b[0])

class UDPBasedProtocol:
    def __init__(self, *, local_addr, remote_addr):
        self.udp_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.remote_addr = remote_addr
        self.udp_socket.bind(local_addr)

    def sendto(self, data):
        return self.udp_socket.sendto(data, self.remote_addr)

    def recvfrom(self, n):
        msg, addr = self.udp_socket.recvfrom(n)
        return msg

    def close(self):
        self.udp_socket.close()


class MyTCPProtocol(UDPBasedProtocol):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.send_index = -1
        self.receive_index = 0

        self.default_timeout = 0.011
        self.default_timeout2 = 0.6
        self.current_timeout = self.default_timeout
        self.long_timeout = 100
        self.attempts = 5

        self.packet_size = 60000
        self.buffer = []

    def set_timeout(self, timeout: float) -> None:
        self.udp_socket.settimeout(timeout)

    def send(self, data: bytes):
        iterations = math.ceil(len(data) / self.packet_size)
        self.current_timeout = self.default_timeout if iterations == 1 else self.default_timeout2

        for cur_iter in range(iterations):
            cur_data = data[cur_iter * self.packet_size : min((cur_iter + 1) * self.packet_size, len(data))]
            self.send_index += 1
            success = False

            while not success:
                self.sendto(int8tobytes(1) + int32tobytes(self.send_index) + cur_data)
                self.set_timeout(self.current_timeout)

                for _ in range(1 if cur_iter < iterations - 1 else self.attempts):
                    try:
                        receive = self.recvfrom(5 + self.packet_size)

                        if (bytestoint8(receive[0:1]) & 1) != 0:
                            InsertMsg(self.buffer, (bytestoint32(receive[1:5]), receive[5:]))
                            self.sendto(int8tobytes(0) + receive[1:5])
                        elif (bytestoint8(receive[0:1]) & 1) == 0 and self.send_index == bytestoint32(receive[1:5]):
                            success = True
                            break
                    except TimeoutError:
                        break

        return len(data)

    def recv(self, n: int):
        while len(self.buffer) > 0 and self.buffer[0][0] < self.receive_index:
            self.buffer.pop(0)
        
        if len(self.buffer) > 0 and self.buffer[0][0] == self.receive_index:
            self.receive_index += 1
            return self.buffer.pop(0)[1]

        self.set_timeout(self.long_timeout)
        result_data = bytes()

        while n > 0:
            success = False

            while not success:
                cur_data = self.recvfrom(min(self.packet_size, n) + 5)
                cur_seq = bytestoint32(cur_data[1:5])

                if (cur_seq == self.receive_index) and (bytestoint8(cur_data[0:1]) & 1) == 1:
                    self.receive_index += 1

                    for _ in range(1 if n > self.packet_size else self.attempts):
                        self.sendto(int8tobytes(0) + int32tobytes(cur_seq))

                    success = True
                    result_data += cur_data[5:]
                    n -= self.packet_size
                elif (cur_seq < self.receive_index) and (bytestoint8(cur_data[0:1]) & 1) == 1:
                    self.sendto(int8tobytes(0) + int32tobytes(cur_seq))

        return result_data

    def close(self):
        super().close()

