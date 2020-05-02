
class Feedback:

	def __init__(self, rate_packet_loss, rate_packet_late):
		self.rate_packet_loss = rate_packet_loss
		self.rate_packet_late = rate_packet_late


	def get_rate_packet_loss(self):
		return self.rate_packet_loss


	def get_rate_packet_late(self):
		return self.rate_packet_late
