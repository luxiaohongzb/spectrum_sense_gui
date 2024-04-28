#!/usr/bin/env python
#
# Copyright 2005,2007,2011 Free Software Foundation, Inc.
#
# This file is part of GNU Radio
#
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
#
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
#
import socket
#from udp_server import *
import json
from operator import le
from re import X
import numpy as np
import matplotlib.pyplot as plt
from gnuradio import gr, eng_notation
from gnuradio import blocks
from gnuradio import audio
from gnuradio import filter
from gnuradio import fft
from gnuradio import uhd
from gnuradio.eng_option import eng_option
from optparse import OptionParser
import sys
import math
import struct
import threading
from datetime import datetime
import time
import os


# sys.stderr.write("Warning: this may have issues on some machines+Python version combinations to seg fault due to the callback in bin_statitics.\n\n")

class ThreadClass(threading.Thread):
    def run(self):
        return


class tune(gr.feval_dd):
    """
    This class allows C++ code to callback into python.
    """

    def __init__(self, tb):
        gr.feval_dd.__init__(self)
        self.tb = tb

    def eval(self, ignore):
        """
        This method is called from blocks.bin_statistics_f when it wants
        to change the center frequency.  This method tunes the front
        end to the new center frequency, and returns the new frequency
        as its result.
        """

        try:
            # We use this try block so that if something goes wrong
            # from here down, at least we'll have a prayer of knowing
            # what went wrong.  Without this, you get a very
            # mysterious:
            #
            #   terminate called after throwing an instance of
            #   'Swig::DirectorMethodException' Aborted
            #
            # message on stderr.  Not exactly helpful ;)

            new_freq = self.tb.set_next_freq()

            # wait until msgq is empty before continuing
            while (self.tb.msgq.full_p()):
                # print "msgq full, holding.."
                time.sleep(0.1)

            return new_freq

        except Exception as e:
            print("tune: Exception: "+str(e))


class parse_msg(object):
    def __init__(self, msg):
        self.center_freq = msg.arg1()
        self.vlen = int(msg.arg2())
        assert (msg.length() == self.vlen * gr.sizeof_float)

        # FIXME consider using NumPy array
        t = msg.to_string()
        self.raw_data = t
        self.data = struct.unpack('%df' % (self.vlen,), t)


class my_top_block(gr.top_block):

    def __init__(self):
        gr.top_block.__init__(self)

        usage = "usage: %prog [options] min_freq max_freq"
        parser = OptionParser(option_class=eng_option, usage=usage)
        parser.add_option("-a", "--args", type="string", default="",
                          help="UHD device device address args [default=%default]")
        parser.add_option("", "--spec", type="string", default=None,
                          help="Subdevice of UHD device where appropriate")
        parser.add_option("-A", "--antenna", type="string", default='TX/RX',
                          help="select Rx Antenna where appropriate")
        parser.add_option("-s", "--samp-rate", type="eng_float", default=10e6,
                          help="set sample rate [default=%default]")
        parser.add_option("-g", "--gain", type="eng_float", default=None,
                          help="set gain in dB (default is midpoint)")
        parser.add_option("", "--tune-delay", type="eng_float",
                          default=4.1e-2, metavar="SECS",
                          help="time to delay (in seconds) after changing frequency [default=%default]")
        parser.add_option("", "--dwell-delay", type="eng_float",
                          default=4.096e-4, metavar="SECS",
                          help="time to dwell (in seconds) at a given frequency [default=%default]")
        parser.add_option("-b", "--channel-bandwidth", type="eng_float",
                          default=976.5625, metavar="Hz",
                          help="channel bandwidth of fft bins in Hz [default=%default]")
        parser.add_option("-l", "--lo-offset", type="eng_float",
                          default=0, metavar="Hz",
                          help="lo_offset in Hz [default=%default]")
        parser.add_option("-q", "--squelch-threshold", type="eng_float",
                          default=None, metavar="dB",
                          help="squelch threshold in dB [default=%default]")
        parser.add_option("-F", "--fft-size", type="int", default=1024,
                          help="specify number of FFT bins [default=%default]")
        parser.add_option("", "--real-time", action="store_true", default=True,
                          help="Attempt to enable real-time scheduling")

        (options, args) = parser.parse_args()
        if len(args) != 2:
            parser.print_help()
            sys.exit(1)

        self.channel_bandwidth = options.channel_bandwidth

        self.min_freq = eng_notation.str_to_num(args[0])
        self.max_freq = eng_notation.str_to_num(args[1])

        if self.min_freq > self.max_freq:
            # swap them
            self.min_freq, self.max_freq = self.max_freq, self.min_freq

        if not options.real_time:
            realtime = False
        else:
            # Attempt to enable realtime scheduling
            r = gr.enable_realtime_scheduling()
            if r == gr.RT_OK:
                realtime = True
            else:
                realtime = False
                print("Note: failed to enable realtime scheduling")


        # build graph
        self.u = uhd.usrp_source(device_addr=options.args,
                                 stream_args=uhd.stream_args('fc32'))

        # Set the subdevice spec
        if (options.spec):
            self.u.set_subdev_spec(options.spec, 0)

        # Set the antenna
        if (options.antenna):
            self.u.set_antenna(options.antenna, 0)
        #

        self.u.set_samp_rate(options.samp_rate)
        self.usrp_rate = usrp_rate = self.u.get_samp_rate()

        self.lo_offset = options.lo_offset

        if options.fft_size is None:
            self.fft_size = int(self.usrp_rate / self.channel_bandwidth)
        else:
            self.fft_size = options.fft_size

        self.squelch_threshold = options.squelch_threshold

        s2v = blocks.stream_to_vector(gr.sizeof_gr_complex, self.fft_size)
        mywindow = filter.window.blackmanharris(self.fft_size)
        ffter = fft.fft_vcc(self.fft_size, True, mywindow, True)
        # power = 0
        # for tap in mywindow:
        #     power += tap*tap

        c2mag = blocks.complex_to_mag_squared(self.fft_size)

        # FIXME the log10 primitive is dog slow
        # log = blocks.nlog10_ff(10, self.fft_size,
        #                       -20*math.log10(self.fft_size)-10*math.log10(power/self.fft_size))

        # Set the freq_step to 75% of the actual data throughput.
        # This allows us to discard the bins on both ends of the spectrum.
        self.overlap = 0.75
        self.freq_step = self.overlap * self.usrp_rate
        self.min_center_freq = self.min_freq + (self.freq_step / 2)
        nsteps = math.ceil((self.max_freq - self.min_freq) / self.freq_step)
        self.nsteps = nsteps
        self.max_center_freq = self.min_center_freq + (nsteps * self.freq_step)

        self.next_freq = self.min_center_freq

        tune_delay = max(0, int(round(options.tune_delay * usrp_rate / self.fft_size)))  # in fft_frames
        # dwell_delay = max(1, int(round(options.dwell_delay * usrp_rate / self.fft_size))) # in fft_frames 400 frame
        dwell_delay = 50
        self.msgq = gr.msg_queue(1)
        self._tune_callback = tune(self)  # hang on to this to keep it from being GC'd
        stats = blocks.bin_statistics_f(self.fft_size, self.msgq,
                                        self._tune_callback, tune_delay,
                                        dwell_delay)

        # FIXME leave out the log10 until we speed it up
        # self.connect(self.u, s2v, ffter, c2mag, log, stats)
        self.connect(self.u, s2v, ffter, c2mag, stats)

        if options.gain is None:
            # if no gain was specified, use the mid-point in dB
            g = self.u.get_gain_range()
            options.gain = float(g.start() + g.stop()) / 2.0

        self.set_gain(options.gain)
        print("gain ="+str(options.gain))

    def set_next_freq(self):
        target_freq = self.next_freq
        self.next_freq = self.next_freq + self.freq_step
        if self.next_freq > self.max_center_freq:
            print("exit")
            # os._exit(0)
            self.next_freq = self.min_center_freq

        if not self.set_freq(target_freq):
            print("Failed to set frequency to ", +str(target_freq))
            sys.exit(1)

        return target_freq

    def set_freq(self, target_freq):
        """
        Set the center frequency we're interested in.

        Args:
            target_freq: frequency in Hz
        @rypte: bool
        """

        r = self.u.set_center_freq(uhd.tune_request(target_freq, rf_freq=(target_freq + self.lo_offset),
                                                    rf_freq_policy=uhd.tune_request.POLICY_MANUAL))
        if r:
            return True

        return False

    def set_gain(self, gain):
        self.u.set_gain(gain)

    def nearest_freq(self, freq, channel_bandwidth):
        freq = round(freq / channel_bandwidth, 0) * channel_bandwidth
        return freq


def main_loop(tb):
    def bin_freq(i_bin, center_freq):
        # hz_per_bin = tb.usrp_rate / tb.fft_size
        freq = center_freq - (tb.usrp_rate / 2) + (tb.channel_bandwidth * i_bin)
        # print "freq original:",freq
        # freq = nearest_freq(freq, tb.channel_bandwidth)
        # print "freq rounded:",freq
        return freq

    bin_start = int(tb.fft_size * ((1 - 0.75) / 2))
    bin_stop = int(tb.fft_size - bin_start)
    #cache = SizedCache(10)
    #data_save = {}
    data_plot = []
    center_freq = 0
    #data_plot = []
    # rawFile = open('rawData', 'w' + 'a')
    # processedFile = open('processedData', 'w' + 'a')
    # jsonFile = open("data.json", "w+")
    # so = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while center_freq < tb.max_center_freq:

        m = parse_msg(tb.msgq.delete_head())
        data_with_no_overlap = m.data[bin_start:bin_stop]
        # cacluate the real dbm
        power_real = map(lambda i: 10 * math.log10(i / (tb.fft_size ** 2) + 10), m.data)
        print("scanning " + str(m.center_freq) + "Hz...")
        center_freq = m.center_freq
        data_save.update({center_freq: power_real})
        # if cache.full():
        #     data = cache.flush()
        #     time.sleep(1)
        #     so.sendto(data, (' 192.168.91.1', 9999))
        # cache.put((int((math.ceil(center_freq / 1e6))), power_real))

    #     data_plot.extend(map(lambda i:10*math.log10((i/(tb.fft_size**2)))+10,data_with_no_overlap))

    #     time_now = str(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time())))
    #     #cacluate the real dbm

    #     power_db = 10*math.log10(np.sum(m.data)*(1.0/tb.fft_size)) +10

    #     rawFile.write(time_now+ " center_freq:" + str(m.center_freq) +"Hz"+ " " +str(power_db)+ "db\n")

    #     rawFile.flush()

    #     threshold = -25
    #     if power_db >threshold:
    #         processedFile.write( time_now + " center_freq:" + str(center_freq) +"Hz"+ " " +"power:" + str(power_db)+"db " +"threshold:" + str(threshold) + "db\n")
    #         processedFile.flush()
    #     # for i_bin in range(bin_start, bin_stop):

    #     #     center_freq = m.center_freq
    #     #     freq = bin_freq(i_bin, center_freq)
    #     #     #noise_floor_db = -174 + 10*math.log10(tb.channel_bandwidth)
    #     #     noise_floor_db = 10*math.log10(min(m.data)/tb.usrp_rate)
    #     #     power_db = 10*math.log10(m.data[i_bin]/tb.usrp_rate) - noise_floor_db
    #     #     threshold = 10 + noise_floor_db

    #     #     if (power_db > threshold) and (freq >= tb.min_freq) and (freq <= tb.max_freq):
    #     #         processedFile.write( str(time.time()) + " " + str(center_freq) + " " + str(freq) + " " + str(power_db)  + " " +str(noise_floor_db) + " " + str(threshold) + "\n")
    # json.dump(data_save, jsonFile)
    # x = np.linspace(tb.min_freq, tb.max_center_freq+(tb.freq_step/2), (tb.nsteps+1)*tb.fft_size*(tb.overlap))
    # plt.plot(x,data_plot)
    # plt.xlabel("frequency/GHz")
    # plt.ylabel("GAIN/db")
    # plt.show()
    # plt.savefig('result.png')


if __name__ == '__main__':
    t = ThreadClass()
    t.start()
    start_time = time.time()
    tb = my_top_block()
    try:
        tb.start()
        main_loop(tb)

    except KeyboardInterrupt:
        pass
    end_time = time.time()

    execution_time = end_time - start_time

    print("execution time:" + str(execution_time))