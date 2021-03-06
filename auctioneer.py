#!usr/bin/env python
import threading
import time
import argparse
import setting
import message
import transport
import log
import socket
import subprocess
from Queue import Queue
from auctioneer_core import AuctioneerCore
from twisted.internet import reactor
from twisted.web import proxy, server

""" Auctioneer(Downloader)
Description:
	Auctioneers also role of downloaders. They broadcast auctions when idle.
Life Cycle:
	idle --> auction | waiting--> decide | timeout--> receive tasks --> downloading tasks -> idle --> ...
	                 --> not yet | timeout --> idle --> ...
"""
class AuctionProtocol(message.Protocol):

	def __init__(self, factory):
		self.factory = factory
	''' auction server callback '''
	def data_received(self, data, ip):
		# parse instruction
		try:
			inst, info = data.split(':',1)
		except:
			return
		# divide instructions
		if inst == 'BID':
			self.factory.receive_bid(ip, info)
		elif inst == 'TASK':
			self.factory.receive_task(ip, info)
		elif inst == 'CLOSE':
                        self.factory.open_servers[int(info)].kill()

class TransportProtocol(transport.Protocol):

	def __init__(self, factory):
		self.factory = factory
	''' downloader sending callback '''
	def send_successed(self, index):
		pass

	def send_failed(self, index):
		print '[task failed]No.', index

class Auctioneer(object):

	def __init__(self, peername, auctioneer_params):
                self.open_servers = {}
		# propertys
		self.peername = peername
		self.delay = auctioneer_params['delay'] if auctioneer_params['delay'] > 1.0 else 1.0
		self.auctioneer_params = auctioneer_params
		# auction message server
		self.message_server  = message.MessageServer(
			setting.UDP_HOST, 
			setting.UDP_AUCTION_PORT, 
			AuctionProtocol(self))
		# auction sender
		self.message_client = message.MessageClient(
			self.auctioneer_params['broadcast'],
			setting.UDP_BID_PORT,
			message.Protocol())
		# transport center
		self.transport = transport.TransportClient(
			setting.TRP_PORT,
			TransportProtocol(self))
		# log center
		self.logger = log.LogClient(peername, self.auctioneer_params['broadcast'])
		self.logger.add_peer(peername)
		# algorithm core
		self.core = AuctioneerCore(self, self.auctioneer_params)

	""" Auctioneer Life Cycle"""
	def start(self):
		print self.peername, 'running...'
		# INIT
		self.running = 1
		self.transport_queue = Queue()
		self.bids = {}# bids {ip:bid}
		self.tasks = {}# tasks {ip:task number}
		self.auction_index = 0
		# launch
		self.message_server.start()
		self.message_client.start()
		threading.Thread(target=self.auction_loop).start() # join ignore
		

	def join(self):
		self.message_server.join()
		self.message_client.join()

	def close(self):
		self.message_server.close()
		self.message_client.close()
		self.running = 0


	def auction_loop(self):
		# timeout mechanism
		while self.running:
			try:
				ip,task = self.transport_queue.get(timeout=0.3)
			except:
				#Time out
				self.auction()
				time.sleep(0.1)
				self.decide_auction()
			else:
				if not ip in self.tasks or self.tasks[ip] <= 0:
					continue
				index, url = task.split(',',1)
				remoteAddress = url.split("/")[2]
				remoteHost = remoteAddress.split(":")[0]
				remotePort = 80 if len(remoteAddress.split(":")) == 1 else int(remoteAddress.split(":")[1])
				proxyPort = get_open_port()
                                p = subprocess.Popen(setting.HTTP_PROXY_COMMAND.split(" ") + [remoteHost, str(remotePort), str(proxyPort)],stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                                self.open_servers[proxyPort] = p
                                urlOverProxy = "http://" + socket.gethostbyname(socket.gethostname()) + ":" + str(proxyPort) + "/" + "/".join(url.split("/")[3:])

                                #size, duration = self.transport.transport(ip, index, url)
				size, duration = self.transport.transport_text(ip, urlOverProxy)
				size = float(size) / 1024 / 128 #bytes to mb
				#delay
				if self.delay > 1.0:
					#print 'delay', duration  * (self.delay - 1.0)
					time.sleep(duration * (self.delay - 1.0))
					duration = duration * self.delay
				capacity = size / duration if duration > 0 else self.auctioneer_params['capacity']
				self.core.estimate_capacity(capacity)
				self.tasks[ip] = self.tasks[ip] - 1
				#logging 
				self.logger.transport_complete(ip, index, size, duration)
				print '[task completed]No.', index,
				print ', size =', round(size,3), '(mb), capacity =', round(capacity,3), '(mbps), url = ', url,
				print ', at',time.strftime("%H:%M:%S")
			


	""" Auction Factory.
	auction : make an auction.
	receive_bid : receive a bid.
	"""
	def auction(self):
		# logging
		self.logger.auction_broadcast(self.peername, 
			self.auction_index,
			self.auctioneer_params['segment'], 
			self.core.capacity, 
			self.auctioneer_params['timecost'], 
			self.auctioneer_params['cellular'], 
			self.auctioneer_params['wifi'])
		# broadcast
		self.bids.clear()
		auction_info = self.core.auction_message(self.auction_index)
		self.message_client.broadcast(':'.join(['AUCTION', auction_info]))

	def receive_bid(self, ip, bid):
		index, bid_details = bid.split(',',1)
		if int(index) == self.auction_index:
			self.bids[ip] = bid_details

	def decide_auction(self):
		if not self.bids:#receive no bids
			return
		# finish one auction
		self.auction_index += 1 # TODO thread safe ,dict size change when iteration
		self.tasks.clear()
		# dict {ip : (segments, rate, payment)}
		allocs = self.core.select_bid(self.bids)
		# notify the winner
		for ip in allocs:
			self.tasks[ip] = allocs[ip][0]
			alloc_result =  ','.join([str(allocs[ip][0]), str(allocs[ip][1])])
			self.message_client.sendto(ip, ':'.join(['WIN', alloc_result]))
			# logging
			self.logger.auction_decide(self.peername, self.auction_index, ip, allocs[ip][0], allocs[ip][1], allocs[ip][2])
		# logging
		self.logger.decide_complete(self.peername)

	def receive_task(self, ip, task):
		self.transport_queue.put((ip,task))
		
def get_open_port():  
        import socket  
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
        s.bind(("",0))  
        s.listen(1)  
        port = s.getsockname()[1]  
        s.close()  
        return port

def parse_args():
	parser = argparse.ArgumentParser(description='Auctioneer')
	parser.add_argument('-p', '--peer', required=False, default='Peer', help='name of peer')
	parser.add_argument('-s', '--segment', type=int, default=setting.AUCTIONEER_SEG_NUM, help='segments per auction')
	parser.add_argument('-c', '--capacity', type=float, default=setting.AUCTIONEER_DEFAULT_CAPACITY, help='initial capacity')
	parser.add_argument('-t', '--timecost', type=float, default=setting.AUCTIONEER_COST_TI, help='rebuffer time cost coefficient')
	parser.add_argument('-l', '--lte', type=float, default=setting.AUCTIONEER_COST_DA, help='lte cost coefficient')
	parser.add_argument('-w', '--wifi', type=float, default=setting.AUCTIONEER_COST_WDA, help='WiFi cost coefficient')
	parser.add_argument('-d', '--delay', type=float, default=1.0, help='delay of data transport.')
	parser.add_argument('-a', '--broadcast', default=setting.UDP_BROADCAST, help='udp broadcast address')
	args = parser.parse_args()
	auctioneer_params = {}
	auctioneer_params['segment'] = args.segment
	auctioneer_params['capacity'] = args.capacity
	auctioneer_params['timecost'] = args.timecost
	auctioneer_params['cellular'] = args.lte
	auctioneer_params['wifi'] = args.wifi
	auctioneer_params['delay'] = args.delay
	auctioneer_params['broadcast'] = args.broadcast
	return args.peer, auctioneer_params

if __name__ == "__main__":
	peer, auctioneer_params = parse_args()
	auctioneer  = Auctioneer(peer, auctioneer_params)
	auctioneer.start()
	try:
		while True:
			command = raw_input().lower()
			if not command:
				break
			if command == 'exit':
				break
	except KeyboardInterrupt:
		pass
	auctioneer.close()
	auctioneer.join()
