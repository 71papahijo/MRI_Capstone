import socket, sys
sys.path.append("../marcos_client")
import server_comms as sc

s = socket.socket(); s.connect(("169.254.44.172", 11111))
reply = sc.command({'halt_and_reset': 0}, s)
print(reply[0][4]['halt_and_reset'])   # True means the FSM is back to idle
s.close()