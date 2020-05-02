
import cv2
import pickle
import socket
import sys


if __name__ == '__main__':
	print("Starting client")

	# Get connection properties
	SERVER_IP = sys.argv[1]
	SERVER_PORT = int(sys.argv[2])
	BUFFER_SIZE = 32768

	# Create socket
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	# Send message to server
	capture = cv2.VideoCapture(0)
	while True:
		ret, frame = capture.read()

		result, jpg = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 50])

		cv2.imshow('frame', frame)
		s.sendto(pickle.dumps(jpg), (SERVER_IP, SERVER_PORT))

		cv2.waitKey(15)

	# capture.release()
	# cv2.destroyAllWindows()
