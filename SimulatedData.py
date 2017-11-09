"""Example program to demonstrate how to send a multi-channel time series to
LSL."""

import time
import numpy as np
from random import random as rand

from pylsl import StreamInfo, StreamOutlet

# first create a new stream info (here we set the name to BioSemi,
# the content-type to EEG, 8 channels, 100 Hz, and float-valued data) The
# last value would be the serial number of the device or some other more or
# less locally unique identifier for the stream as far as available (you
# could also omit it but interrupted connections wouldn't auto-recover)
info = StreamInfo('OpenViBE Stream - Band Pass Filtered', 'EEG', 16, 125, 'float32', 'myuid34234')

chns = info.desc().append_child("channels")
for label in ["P4", "C4", "T6", "CP2", "FC2", "POz", "Pz", "PO4", "FC1", "PO3", "Cz", "Oz", "T5", "P3", "C3", "CP1"]:
    ch = chns.append_child("channel")
    ch.append_child_value("label", label)
    ch.append_child_value("unit", "microvolts")
    ch.append_child_value("type", "EEG")
info.desc().append_child_value("manufacturer", "BioSemi")
cap = info.desc().append_child("cap")
cap.append_child_value("name", "EasyCap")
cap.append_child_value("size", "54")
cap.append_child_value("labelscheme", "10-20")


# next make an outlet
outlet = StreamOutlet(info)

print("now sending data...")
i = 1.0
while True:
    # make a new random 8-channel sample; this is converted into a
    # pylsl.vectorf (the data type that is expected by push_sample)
    alpha = np.sin(2*np.pi*10 * (i/125))*40
    beta = np.sin(2*np.pi*20 * (i/125))*10
    delta = np.sin(2*np.pi*2 * (i/125))*4
    gamma = np.sin(2*np.pi*35 * (i/125))*20
    theta = np.sin(2*np.pi*6 * (i/125))*20
    mysample = [rand(), rand(), rand(), rand(), rand(), rand(), rand(), rand(), rand(), rand(), rand(), rand(), rand(), rand(), rand(), rand()]
    mysample = map(lambda sample: sample*50 - 25 + alpha + beta + delta + gamma + theta, mysample)
    # mysample = map(lambda sample: alpha + beta, mysample)

    # now send it and wait for a bit
    outlet.push_sample(mysample)
    # if i == 125:
    #     i = 1.0
    # else:
    #     i = i + 1
    i = i + 1

    time.sleep(0.008)