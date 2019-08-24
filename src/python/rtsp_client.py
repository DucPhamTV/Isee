import socket


SERVER_IP = "192.168.1.13"
SERVER_PORT = 554
PATH = "onvif1"
RTSP_FIRST_LINE = "{command} rtsp://{host}:{port}/{path} RTSP/1.0\r\n"
RTSP_HEADER = "{}: {}\r\n"
def option_request(host=SERVER_IP, port=SERVER_PORT, path=PATH):
    msg = RTSP_FIRST_LINE.format(
        command="OPTIONS",
        host=host,
        port=port,
        path=path
    )
    msg += RTSP_HEADER.format("CSeq", 1)
    msg += RTSP_HEADER.format("User-Agent", "Isee v1.0")
    msg += '\r\n'
    return bytearray(msg, 'utf-8')

if __name__ == "__main__":
    # Create control socket
    control_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    control_sock.connect((SERVER_IP, SERVER_PORT))
    message = option_request()
    print(message)
    control_sock.send(message)
    data = control_sock.recv(1024)
    print(data)
