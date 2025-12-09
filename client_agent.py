# Run this in your standard terminal/VS Code
import socket

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect(('localhost', 9999))

print("Sending command...")
client.send("EXTRUDE".encode())

# Wait for Blender to reply
response = client.recv(1024).decode()
print(f"Blender said: {response}")

client.close()
