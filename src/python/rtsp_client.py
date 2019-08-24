import socket
import argparse
from collections import namedtuple
import hashlib
import os


RTSP_FIRST_LINE = "{command} rtsp://{host}:{port}/{path} RTSP/1.0\r\n"
RTSP_HEADER = "{}: {}\r\n"

Response = namedtuple("Response", ["code", "message", "headers"])


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

    def _parse_response(self, data):
        """Parse response without SDP"""
        lines = data.decode("utf-8").split("\r\n\r\n")[0].split("\r\n")
        first_line = lines[0]
        protocol, code, message = first_line.split(maxsplit=2)
        assert protocol == "RTSP/1.0", "Unknown protocol %s" % protocol
        headers = dict(line.split(": ", maxsplit=1) for line in lines[1:])
        return Response(int(code), message, headers)

    def _send(self, data):
        print("Sending %s" % data)
        self.control_sock.send(data)
        response = self.control_sock.recv(1024)
        self.cseq += 1
        print("Received %s" % response)
        return response

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
        response = self._send(bytearray(msg, 'utf-8'))
        return self._parse_response(response)

    def describe_request(self, authen=None):
        msg = self._generate_first_line("DESCRIBE")
        msg += RTSP_HEADER.format("CSeq", self.cseq)
        if authen:
            msg += RTSP_HEADER.format("Authorization", authen)
        msg += RTSP_HEADER.format("User-Agent", "Isee v1.0")
        msg += RTSP_HEADER.format("Accept", "application/sdp")
        msg += '\r\n'
        response = self._send(bytearray(msg, 'utf-8'))
        return self._parse_response(response)

    def generate_auth_string(
        self, username, password, realm, method, uri, nonce
    ):
        m1_str = username + ":" + realm + ":" + password
        m1 = hashlib.md5(m1_str.encode("utf-8")).hexdigest()
        m2_str = method + ":" + uri
        m2 = hashlib.md5(m2_str.encode('utf-8')).hexdigest()
        response_str = m1 + ":" + nonce + ":" + m2
        response = hashlib.md5(response_str.encode('utf-8')).hexdigest()
        authen_str = 'Digest '
        authen_str += 'username="' + username + '", '
        authen_str += 'realm="' + realm + '", '
        authen_str += 'algorithm="MD5", '
        authen_str += 'nonce="' + nonce + '", '
        authen_str += 'uri="' + uri + '", '
        authen_str += 'response="' + response + '"'
        return authen_str

    def authenticate(self, response, username, password, method):
        uri = self._generate_first_line(method).split()[1]
        digest = response.headers['WWW-Authenticate'].split('"')
        assert "Digest" in digest[0]
        realm, nonce = digest[1], digest[3]
        return self.generate_auth_string(
            username, password, realm, method, uri, nonce)


if __name__ == "__main__":
    args = parse_input()
    client = RTSPClient(args.server_ip, args.control_port, args.path)
    client.connect()
    response = client.option_request()
    response = client.describe_request()
    if response.code == 401:
        print("Server requires authentication")
        password = os.environ['MYPW']
        authen_str = client.authenticate(
            response, "admin", password, "DESCRIBE")
        print("Generate authentication : %s" % authen_str)
        response = client.describe_request(authen_str)
