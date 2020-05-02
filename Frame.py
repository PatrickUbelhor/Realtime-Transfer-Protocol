
class Frame:

	def __init__(self, seqNum, timestamp, image):
		self.seqNum = seqNum
		self.timestamp = timestamp
		self.image = image


	def getSeqNum(self):
		return self.seqNum


	def getTimestamp(self):
		return self.timestamp


	def getImage(self):
		return self.image
