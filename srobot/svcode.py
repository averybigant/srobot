#!/usr/bin/python
#coding=utf-8
import os
import tempfile
import time

def show_vcode(raw_image, isuffix=".jpg"):
    tempf = tempfile.NamedTemporaryFile(suffix = isuffix)
    tempf.write(raw_image)
    tempf.flush()
    os.system("gnome-open %s" % tempf.name)
    time.sleep(1)
    tempf.close()

