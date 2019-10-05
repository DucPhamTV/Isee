import argparse
import requests as rq
import socket


def parse_input():
    parser = argparse.ArgumentParser()
    parser.add_argument('ip', help="IP address you want to scan")
    parser.add_argument('--startport', help="start from port")
    parser.add_argument('--endport', help="end port")

    return parser.parse_args()

if __name__ == '__main__':
    args = parse_input()

    for i in range(int(args.startport), int(args.endport)):
        try:
#            response = rq.get("http://{0}:{1}".format(args.ip, i), timeout=2)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((args.ip, i))
            sock.close()

            print(f"****************Port {i} succeed!*******************")
        except Exception as e:
            #print(f"Port {i} failed {e}")
            pass
