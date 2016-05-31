#!/bin/bash

obj_dst=1;
obj_src=3;
message_type=2;

python ssnmqc.py --file scripts/test/getdevvals.json --dest $obj_dst --src $obj_src
