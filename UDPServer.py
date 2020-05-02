
import cv2
import pickle
import socket
import sys


if __name__ == '__main__':

	BUFFER_SIZE = 32768
	PORT_NUMBER = int(sys.argv[1])
	print("Starting server on port", PORT_NUMBER)

	# Initialize socket
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.bind(("", PORT_NUMBER))

	# Listen for incoming datagrams
	while True:
		datagram = s.recvfrom(BUFFER_SIZE)

		message = pickle.loads(datagram[0])
		address = datagram[1]

		frame = cv2.imdecode(message, 1)
		cv2.imshow('frame', frame)
		cv2.waitKey(1)
