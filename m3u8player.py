#!usr/bin/env python
# -*- coding: utf-8 -*-
import os
import threading
import subprocess
import time
import m3u8

class M3U8Player(object):
    def __init__(self, factory = None):
        if factory == None:
            self.url = "http://devimages.apple.com/iphone/samples/bipbop/bipbopall.m3u8"
            self.command_of_player = "vlc"
        else:
            self.factory = factory
            self.url = factory.streaming_url
            self.command_of_player = factory.command_of_player
    
    def play(self):
        #print [self.command_of_player] + [self.proxifiedUrl],
        p = subprocess.Popen([self.command_of_player] + [self.proxifiedUrl],stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()
        self.factory.close()

    def close(self):
        self.factory.message_client.sendto(self.factory.auctioneerIP, ":".join(["CLOSE", str(self.auctioneerPort)]))

    def prepare2play(self):
        self.descriptor_list = get_urls_from_m3u8(self.url)
        self.rate_list = [x[1] for x in self.descriptor_list]
        self.max_rate = self.rate_list[-1]
        self.segment_duration = get_duration_from_m3u8(self.descriptor_list[0][0])
        
    def get_segment_number(self):
        return 1

    def get_buffer(self):
        return self.segment_duration

    def get_segment_duration(self):
        return self.segment_duration

    def get_segment_url(self, index, rate):
        # An O(n) search algorithm, could be optimized to O(log(n)).
        # However, len(self.descriptor_list) = O(1), the optimization seems unnecessary
        self.startTime = index * self.segment_duration
        for item in self.descriptor_list:
            if item[1] == rate:
                return item[0]

    def segment_received(self, index, data):
        self.proxifiedUrl = data
        self.auctioneerPort = data.split("/")[2].split(":")[1]
        self.play()

    def get_rate_list(self):
        return self.rate_list
    
    def get_max_rate(self):
        return self.max_rate
    
def get_urls_from_m3u8(url):
    playlist = m3u8.load(url)
    result = []
    if playlist.is_variant:
            for item in playlist.playlists:
                result += [(item.base_uri + item.uri, item.stream_info.bandwidth)]
    result = sorted(result, key = lambda x: x[1])
    return result

def get_duration_from_m3u8(url):
    return m3u8.load(url).target_duration

if __name__ == "__main__":
    player = M3U8Player()
    player.prepare2play()

        

