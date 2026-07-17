#--
# Running ptext.py examples:
#
time python ptext.py -F datasets/data/slo/ringaraja_clanki/text/ -E ".*stats.*" -W 1 -d 20 -w datasets/data/slo/ringaraja_clanki/gen/data
time python ptext.py -F datasets/data/slo/ringaraja_forum/text/ -E ".*stats.*" -W 1 -d 20 -w datasets/data/slo/ringaraja_forum/gen/data
time python ptext.py -F datasets/data/slo/wikipedia/text/ -E ".*stats.*" -W 1 -d 20 -w datasets/data/slo/wikipedia/gen/data
