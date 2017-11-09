import socket
import sys, os
import cryptography
import random
import string
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

try:
    command = sys.argv[1]
    filename = sys.argv[2]
    hostnamePort = sys.argv[3]
    hostname = hostnamePort.split(":", 1)[0]
    port = int(hostnamePort.split(":", 2)[1])
    cipher = sys.argv[4]
    key = sys.argv[5]
except:
    print("must state command, filename, host:port, cipher, and key")
    print("exiting...")
    sys.exit()

# make sure correct cipher has been entered
if (cipher != "null") and (cipher != "aes128") and (cipher != "aes256"):
    print("bad cipher \"", cipher, "\"")
    print("exiting...")
    sys.exit()

clientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
clientSocket.connect((hostname, port))



# used this for nonce: https://www.technologycake.com/others/generate-random-string-python/1342/
nonce = "".join(random.choice(string.ascii_letters+string.digits) for x in range(16))

# TODO: Make the length parsed from command line
kdf = PBKDF2HMAC (algorithm=hashes.SHA256(), length=16, salt=(bytes(nonce, "utf-8")), iterations=100000, backend=default_backend())
IV = kdf.derive(bytes(key+nonce+"IV", "UTF-8"))
kdf = PBKDF2HMAC (algorithm=hashes.SHA256(), length=16, salt=(bytes(nonce, "utf-8")), iterations=100000, backend=default_backend())
SK = kdf.derive(bytes(key+nonce+"SK", "UTF-8"))

# first message, send only cipher and nonce
clientSocket.send(bytearray(cipher+";"+nonce, "UTF-8"))
a = clientSocket.recv(1024)

# send requests to server
clientSocket.send(bytearray(command+";"+filename, "UTF-8"))


cipher = Cipher(algorithms.AES(SK), modes.CBC(IV), backend=default_backend())
decryptor = cipher.decryptor()

# respond to challenge
challenge = clientSocket.recv(1024)



cipher = Cipher(algorithms.AES(SK), modes.CBC(IV), backend=default_backend())
decryptor = cipher.decryptor()
answer = decryptor.update(challenge) + decryptor.finalize()
clientSocket.send(answer)


# get whether key is right or wrong
result = (clientSocket.recv(1024)).decode("utf-8")
if result == "OK":
    print("Key is OK")
else:
    print("Error: Wrong key")
    os._exit(1)


##         ##
# uploading #
##         ##
# read from standard input and send to the server
if command == "write":
    try:
        with open(filename, "rb") as f:
            clientSocket.send(bytearray("OK", "utf-8"))
            clientSocket.recv(1024)
            print("Got the OK from server, time to upload")
            line = sys.stdin.buffer.read(1024)
            while line:
                clientSocket.send(line)
                print("Sending", repr(line))
                line = sys.stdin.buffer.read(1024)
        f.close()
    except FileNotFoundError:
        clientSocket.send(bytearray("file not found", "utf-8"))
        print("Error, file \"" + filename + "\" not found")
    clientSocket.close()

##           ##
# downloading #
##           ##
# ask server to send contents of a file called filename
# write results to standard output
# may have to use two recv loops, one to determine size...
elif command == "read":
    try:
        # check if server allows downloading
        response = (clientSocket.recv(1024)).decode("utf-8")
        if "error" in response:
            print(response)
            clientSocket.close()
            sys.exit()
        elif response == "OK":
            print("server said " + response + ". Starting to download")
            clientSocket.send(bytearray("OK", "utf-8"))
        else:
            print("error")
            clientSocket.close()
            sys.exit()
        with open(filename, "wb") as f:
            data = clientSocket.recv(1024)
            while data:
                print("receiving and downloading data", repr(data))
                f.write(data)
                data = clientSocket.recv(1024)
                print(data)
        f.close()
        print("finished downloading")
    except FileNotFoundError:
        print("Error, file \"" + filename + "\" not found")
    clientSocket.close()            # close connection

else:
    print("bad command \"", command, "\"")
    clientSocket.close()