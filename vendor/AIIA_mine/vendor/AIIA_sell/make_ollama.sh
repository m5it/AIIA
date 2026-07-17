#!/bin/bash

# working proxy:
# 82.165.198.169:10610
#--
ssh -D 11434 -f -C -q -N beatriz@192.168.1.34 -p 11434
