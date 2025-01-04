def send_data_to_server(socket, data):
    socket.send(data.encode() if isinstance(data, str) else data)
