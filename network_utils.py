import socket
def initialize_network_connection(IP_ADDRESS, PORT_ID):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((IP_ADDRESS, PORT_ID))
    return s
