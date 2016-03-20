#!/bin/bash

obj_dst=1;
obj_src=3;
message_type=7;

python ssnmqc.py --file scripts/test/loadprefs.ini --type $message_type --dest $obj_dst
