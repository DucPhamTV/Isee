import socket
import argparse
from collections import namedtuple
import hashlib
import os
import threading


RTSP_FIRST_LINE = "{command} rtsp://{host}:{port}/{path} RTSP/1.0\r\n"
RTSP_HEADER = "{}: {}\r\n"

Response = namedtuple("Response", ["code", "message", "headers"])


class AuthenticationError(Exception):
    pass


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
        self.session = None

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

    def _generate_first_line(self, command, path=None):
        return RTSP_FIRST_LINE.format(
           command=command,
           host=self.server_ip,
           port=self.server_port,
           path=path or self.path,
        )

    def initialize_streaming_socket(self):
        self.streaming_sock = socket.socket(
            socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        self.streaming_sock.bind(('', 0))

    def option_request(self):
        msg = self._generate_first_line("OPTIONS")
        msg += RTSP_HEADER.format("CSeq", self.cseq)
        msg += RTSP_HEADER.format("User-Agent", "Isee v1.0")
        if self.session:
            msg += RTSP_HEADER.format('Session', self.session)
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
        if self.session:
            msg += RTSP_HEADER.format('Session', self.session)
        msg += '\r\n'
        response = self._send(bytearray(msg, 'utf-8'))
        return self._parse_response(response)

    def setup_request(self, authen=None, track="track1"):
        self.initialize_streaming_socket()
        streaming_port = self.streaming_sock.getsockname()[1]
        print("Streaming port: %d" % streaming_port)
        msg = self._generate_first_line("SETUP", '/'.join([self.path, track]))
        msg += RTSP_HEADER.format("CSeq", self.cseq)
        if authen:
            msg += RTSP_HEADER.format("Authorization", authen)
        msg += RTSP_HEADER.format("User-Agent", "Isee v1.0")
        msg += RTSP_HEADER.format(
            "Transport", "RTP/AVP;unicast;client_port={}-{}".format(
                streaming_port, streaming_port + 1)
        )
        msg += '\r\n'
        response = self._send(bytearray(msg, 'utf-8'))
        result = self._parse_response(response)
        assert result.code == 200
        self.session = result.headers['Session'].split(';')[0]
        return result

    def play_request(self, authen=None):
        msg = self._generate_first_line("PLAY")
        msg += RTSP_HEADER.format("CSeq", self.cseq)
        if authen:
            msg += RTSP_HEADER.format("Authorization", authen)
        msg += RTSP_HEADER.format("User-Agent", "Isee v1.0")
        assert self.session is not None
        msg += RTSP_HEADER.format("Session", self.session)
        msg += RTSP_HEADER.format("Range", "npt=0.000-")
        msg += '\r\n'
        response = self._send(bytearray(msg, 'utf-8'))
        result = self._parse_response(response)
        return result

    def teardown_request(self, authen=None):
        msg = self._generate_first_line("TEARDOWN")
        msg += RTSP_HEADER.format("CSeq", self.cseq)
        if authen:
            msg += RTSP_HEADER.format("Authorization", authen)
        msg += RTSP_HEADER.format("User-Agent", "Isee v1.0")
        assert self.session is not None
        msg += RTSP_HEADER.format("Session", self.session)
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


def capture(sock):
    counter = 500
    with open('dump_data.txt', 'wb') as output:
        while True:
            data, _ = sock.recvfrom(4096)
            output.write(data)
            print(".")
            counter -= 1
            if counter == 0:
                break


if __name__ == "__main__":
    args = parse_input()
    client = RTSPClient(args.server_ip, args.control_port, args.path)
    client.connect()
    response = client.option_request()
    assert response.code == 200
    describe_response = client.describe_request()
    authen_str = None
    if describe_response.code == 401:
        print("Server requires authentication")
        password = os.environ['MYPW']
        authen_str = client.authenticate(
            describe_response, "admin", password, "DESCRIBE")
        print("Generate authentication : %s" % authen_str)
        response = client.describe_request(authen_str)
        if response.code != 200:
            raise AuthenticationError("Incorrect username or password!")
    authen_str = client.authenticate(
        describe_response, "admin", password, "SETUP")
    response = client.setup_request(authen_str, 'track1')
    assert response.code == 200
    x = threading.Thread(target=capture, args=(client.streaming_sock,))
    x.start()
    authen_str = client.authenticate(
        describe_response, "admin", password, "PLAY")
    response = client.play_request(authen_str)
    print("Playing ......")
    x.join()
    authen_str = client.authenticate(
        describe_response, "admin", password, "TEARDOWN")
    response = client.teardown_request(authen_str)
