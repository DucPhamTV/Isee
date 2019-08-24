import socket
import argparse


RTSP_FIRST_LINE = "{command} rtsp://{host}:{port}/{path} RTSP/1.0\r\n"
RTSP_HEADER = "{}: {}\r\n"


def parse_input():
    parser = argparse.ArgumentParser()
    parser.add_argument("server_ip", help="RTSP server ip address")
    parser.add_argument("--control_port", default=554, type=int,
                        help="RTSP control port, default value 554")
    parser.add_argument("--path", default="onvif1", help="path to media file")
    return parser.parse_args()


class RTSPClient(object):
    def __init__(self, server_ip, server_port, path):
        self.server_ip = server_ip
        self.server_port = server_port
        self.path = path
        self.control_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.streaming_sock = None
        self.cseq = 1

    def connect(self):
        self.control_sock.connect((self.server_ip, self.server_port))

    def _send(self, data):
        print("Sending %s" % data)
        self.control_sock.send(data)
        data = self.control_sock.recv(1024)
        self.cseq += 1
        return data

    def _generate_first_line(self, command):
        return RTSP_FIRST_LINE.format(
           command=command,
           host=self.server_ip,
           port=self.server_port,
           path=self.path,
        )

    def option_request(self):
        msg = self._generate_first_line("OPTIONS")
        msg += RTSP_HEADER.format("CSeq", self.cseq)
        msg += RTSP_HEADER.format("User-Agent", "Isee v1.0")
        msg += '\r\n'
        return self._send(bytearray(msg, 'utf-8'))

    def describe_request(self):
        msg = self._generate_first_line("DESCRIBE")
        msg += RTSP_HEADER.format("CSeq", self.cseq)
        msg += RTSP_HEADER.format("User-Agent", "Isee v1.0")
        msg += RTSP_HEADER.format("Accept", "application/sdp")
        msg += '\r\n'
        return self._send(bytearray(msg, 'utf-8'))


if __name__ == "__main__":
    args = parse_input()
    client = RTSPClient(args.server_ip, args.control_port, args.path)
    client.connect()
    response = client.option_request()
    print(response)
    response = client.describe_request()
    print(response)
