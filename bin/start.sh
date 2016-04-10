#!/bin/bash
BASE=`dirname $0`/../
cd $BASE
if [ `whoami` = vagrant ] || [ `whoami` = root ]; then
	make frontend-start
else
	make vagrant-up
fi
