# Introduction of log

## auction.log

auction event entry.

### auction broadcast
format
```
#A auctioneer_peer auction_index
timestamp(second)
segments capacity(mbps) cti cda cwda
```
example
```
#A A 0
13.6212248802
3 0.279 0.15 0.15 0.01
```

### auction decision
format
```
#D auctioneer_peer bidder_peer auction_index
timestamp
segments bitrate payment
```

example
```
#D A B 0
5.88063812256
3 0.296698570251 52.483137373
```

### bid
format
```
#B bidder_peer auction_peer auction_index
timestamp 
segments buffer_size(seconds)
rate1, rate2, ..., ratek(mbps)
price1, price2, ..., pricek
```

example
```
#B B A 0
41.7679789066
3 0.0
0.507960319519 0.507960319519 0.507960319519
23.6364384564 46.6957243367 69.1778576411
```

### transport
format
```
#T from_peer to_peer
timestamp(finished time!)
segment_index(from 0 to ..) segment_size(mb) transport_duration(sconds)
```
example
```
#T A B
69.7660508156
3 0.732047080994 2.04561901093
```

## play.log

todo...