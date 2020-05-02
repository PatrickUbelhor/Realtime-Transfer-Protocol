
import cv2
import pickle
import socket
import sys
import threading
import time

from Frame import Frame

DELAY_IN_FRAMES = 5
UDP_BUFFER_SIZE = 32768
RTCP_PERIOD = 5  # In seconds
ready_to_receive = False
count = 0
count_missing_packets = 0
count_late_packets = 0
expected_seq_num = 0
buffer = []


def display(lock):
	initTime = time.time()

	while True:
		while len(buffer) < DELAY_IN_FRAMES:
			time.sleep(.02)

		lock.acquire()
		frame = buffer.pop(0)
		lock.release()

		delayTime = (frame.timestamp / 1000) - (time.time() - initTime)
		time.sleep(min(delayTime, 0))

		cv2.imshow('Server', frame.getImage())
		cv2.waitKey(1)


def read_datagram(datagram):
	packet = datagram[0]
	address = datagram[1]

	header = packet[:12]
	payload = pickle.loads(packet[12:])

	sequence_number = int.from_bytes(header[2:4], 'big')
	timestamp = int.from_bytes(header[4:8], 'big')
	image = cv2.imdecode(payload, 1)
	return Frame(sequence_number, timestamp, image)


def send_feedback(client):
	global count
	global count_missing_packets
	global count_late_packets

	# Define RTCP content
	header_meta = b'\x81\x00'  # Version 2, Padding 0, Report Count 1
	header_length = b'\x0C'    # 12 bytes
	header_ssrc = b'\x00\x00\x00\x00'  # SSRC 0

	rate_packet_loss = int((count_missing_packets / max(count, 1)) * 10000).to_bytes(2, 'big')
	rate_packet_late = int((count_late_packets / max(count, 1)) * 10000).to_bytes(2, 'big')

	# Reset statistics
	count = 0
	count_missing_packets = 0
	count_late_packets = 0

	# Construct and send RTCP packet
	rtcp_packet = header_meta + header_length + header_ssrc + rate_packet_loss + rate_packet_late
	client.sendall(rtcp_packet)


def receive_video(rtp_port):
	global count
	global count_missing_packets
	global count_late_packets
	global expected_seq_num
	global ready_to_receive
	global UDP_BUFFER_SIZE

	# Initialize socket
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	s.bind(("", rtp_port))
	ready_to_receive = True

	# Initialize threading stuff
	lock = threading.Lock()
	displayThread = threading.Thread(target=display, args=(lock,))

	# Initialize metrics

	# Listen for incoming datagrams
	while True:
		datagram = s.recvfrom(UDP_BUFFER_SIZE)
		frame = read_datagram(datagram)
		count += 1

		# Detect lost/out-of-order packets
		if frame.seqNum > expected_seq_num:
			print("Missing ", frame.seqNum - expected_seq_num, " packets!")
			count_missing_packets += frame.seqNum - expected_seq_num
			expected_seq_num = frame.seqNum
		elif frame.seqNum < expected_seq_num:
			print("Received out-of-order packet!")
			count_late_packets += 1
			count_missing_packets -= 1
			continue
		expected_seq_num += 1

		# Delayed start lets us do jitter compensation
		# Can't delay too many frames or we get lag
		if (not displayThread.is_alive()) and len(buffer) == DELAY_IN_FRAMES:
			displayThread.start()

		lock.acquire()
		buffer.append(frame)
		lock.release()


def main(args):
	RTP_PORT = int(args[1])
	RTCP_PORT = RTP_PORT + 1
	global RTCP_PERIOD
	global expected_seq_num

	# Initialize RTCP socket
	# This is how communication is started
	# During RTP comms, this connection will be used to send feedback
	rtcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	rtcp_socket.bind(("", RTCP_PORT))
	rtcp_socket.listen(1)
	print("Awaiting RTCP connection on port ", RTCP_PORT)

	client, address = rtcp_socket.accept()
	print("Received connection request. Starting RTP listener on port ", RTP_PORT)

	# Begin listening for RTP packets
	recv_thread = threading.Thread(target=receive_video, args=(RTP_PORT,))
	recv_thread.start()

	# Wait until RTP socket is ready
	while not ready_to_receive:
		time.sleep(0.001)

	# Send initial sequence number to start RTP
	client.sendall(expected_seq_num.to_bytes(2, 'big'))

	# Periodically send RTCP feedback
	while True:
		send_feedback(client)
		time.sleep(RTCP_PERIOD)


if __name__ == '__main__':
	main(sys.argv)
