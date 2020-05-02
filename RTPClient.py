
import cv2
import pickle
import socket
import sys
import threading
import time

from Feedback import Feedback


# RTCP Header + Payload
#  -----------------------------------------------------------------------
#  |0 1 2 3 4 5 6 7 | 0 1 2 3 4 5 6 7 | 0 1 2 3 4 5 6 7 | 0 1 2 3 4 5 6 7|
#  |Ver|P|    RC    |  Payload Type   |              Length              |
#  |                           SSRC Identifier                           |
#  |         Packet Loss Rate         |      Packet Delayed Rate         |
#  -----------------------------------------------------------------------


# RTP Header
#  _______________________________________________________________________
#  |0 1 2 3 4 5 6 7 | 0 1 2 3 4 5 6 7 | 0 1 2 3 4 5 6 7 | 0 1 2 3 4 5 6 7|
#  |Ver|P|X|   CC   | M| Payload Type |         Sequence Number          |
#  |                              Timestamp                              |
#  |                           SSRC Identifier                           |
#  |                           CSRC Identifiers                          |
#  |                           Extension Headers                         |
#  |                               Payload                               |
#  -----------------------------------------------------------------------

MIN_PERIOD = 20
period = 20  # In milliseconds


def init_connection(address, port):

	# Create IPv4 + TCP socket
	rtcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	rtcp_socket.connect((address, port))

	init_message = rtcp_socket.recv(4096)
	return int.from_bytes(init_message[:2], 'big'), rtcp_socket


def get_image(capture):
	result0, raw = capture.read()
	result1, jpg = cv2.imencode('.jpg', raw, [int(cv2.IMWRITE_JPEG_QUALITY), 50])
	cv2.imshow('Client', raw)
	cv2.waitKey(1)

	return jpg


def send_video(address, port, init_seq_num):
	MAX_SEQ_NUM = 2**16
	sequenceNumber = init_seq_num
	timestamp = 0
	global period

	# RTP header fields
	headerContent = b'\x80\x00'  # V, P, X, CC, M, PT fields
	headerSeqNum = sequenceNumber.to_bytes(2, 'big')
	headerTimestamp = timestamp.to_bytes(4, 'big')
	headerSsrc = b'\x00\x00\x00\x00'

	# Create socket
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

	# Send message to server
	initTime = time.time()
	capture = cv2.VideoCapture(0)
	while True:
		image = get_image(capture)

		timestamp = int((time.time() - initTime) * 1000)
		headerTimestamp = timestamp.to_bytes(4, 'big')
		header = headerContent + headerSeqNum + headerTimestamp + headerSsrc
		payload = pickle.dumps(image)
		s.sendto(header + payload, (address, port))

		# Prepare header values for next frame
		sequenceNumber = (sequenceNumber + 1) % MAX_SEQ_NUM
		headerSeqNum = sequenceNumber.to_bytes(2, 'big')

		time.sleep(period / 1000)

	# capture.release()
	# cv2.destroyAllWindows()


def read_rtcp_packet(rtcp_socket):
	packet = rtcp_socket.recv(4096)

	rate_packet_loss = int.from_bytes(packet[9:11], 'big') / 10000
	rate_packet_late = int.from_bytes(packet[11:13], 'big') / 10000
	return Feedback(rate_packet_loss, rate_packet_late)


def main(args):
	print("Starting client")
	SERVER_IP = args[1]
	SERVER_RTP_PORT = int(args[2])
	SERVER_RTCP_PORT = SERVER_RTP_PORT + 1
	global MIN_PERIOD
	global period

	init_seq_num, rtcp_socket = init_connection(SERVER_IP, SERVER_RTCP_PORT)
	rtp_thread = threading.Thread(target=send_video, args=(SERVER_IP, SERVER_RTP_PORT, init_seq_num))
	rtp_thread.start()

	# while true, receive rtcp. if message == 'terminated', stop
	while True:
		feedback = read_rtcp_packet(rtcp_socket)

		# Adjust packet frequency to maximize quality of stream
		if feedback.rate_packet_loss > 0.1:
			period += 2
		else:
			period = max(period - 1, MIN_PERIOD)

		print("Packet loss rate: ", feedback.rate_packet_loss)
		print("Packet late rate: ", feedback.rate_packet_late)
		print("---------------------------")


if __name__ == '__main__':
	main(sys.argv)
