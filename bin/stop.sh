#!/bin/sh
BASE=`dirname $0`/../
cd $BASE
if [ `whoami` = vagrant ] || [ `whoami` = root ]; then
	make frontend-stop
else
	make vagrant-halt
fi
