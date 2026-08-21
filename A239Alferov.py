#!/usr/bin/env python3
# -*- coding: utf-8 -*-

#
# SPDX-License-Identifier: GPL-3.0
#
# GNU Radio Python Flow Graph
# Title: 239Alferov
# Author: N6RFM
# GNU Radio version: 3.10.9.2

from PyQt5 import Qt
from gnuradio import qtgui
from PyQt5 import QtCore
from gnuradio import analog
import math
from gnuradio import audio
from gnuradio import blocks
from gnuradio import filter
from gnuradio.filter import firdes
from gnuradio import gr
from gnuradio.fft import window
import sys
import signal
from PyQt5 import Qt
from argparse import ArgumentParser
from gnuradio.eng_arg import eng_float, intx
from gnuradio import eng_notation
from gnuradio import overflow_monitor
import gpredict
import osmosdr
import time
import satellites
import satellites.components.datasinks
import satellites.utils.config
import satellites.core
import sip



class A239Alferov(gr.top_block, Qt.QWidget):

    def __init__(self, filter_width=20000, freq=436.272e6, gpredict_port=4531, kiss_port=8100, nfreq=436.272e6, offset=50e3, port=7355):
        gr.top_block.__init__(self, "239Alferov", catch_exceptions=True)
        Qt.QWidget.__init__(self)
        self.setWindowTitle("239Alferov")
        qtgui.util.check_set_qss()
        try:
            self.setWindowIcon(Qt.QIcon.fromTheme('gnuradio-grc'))
        except BaseException as exc:
            print(f"Qt GUI: Could not set Icon: {str(exc)}", file=sys.stderr)
        self.top_scroll_layout = Qt.QVBoxLayout()
        self.setLayout(self.top_scroll_layout)
        self.top_scroll = Qt.QScrollArea()
        self.top_scroll.setFrameStyle(Qt.QFrame.NoFrame)
        self.top_scroll_layout.addWidget(self.top_scroll)
        self.top_scroll.setWidgetResizable(True)
        self.top_widget = Qt.QWidget()
        self.top_scroll.setWidget(self.top_widget)
        self.top_layout = Qt.QVBoxLayout(self.top_widget)
        self.top_grid_layout = Qt.QGridLayout()
        self.top_layout.addLayout(self.top_grid_layout)

        self.settings = Qt.QSettings("GNU Radio", "A239Alferov")

        try:
            geometry = self.settings.value("geometry")
            if geometry:
                self.restoreGeometry(geometry)
        except BaseException as exc:
            print(f"Qt GUI: Could not restore geometry: {str(exc)}", file=sys.stderr)

        ##################################################
        # Parameters
        ##################################################
        self.filter_width = filter_width
        self.freq = freq
        self.gpredict_port = gpredict_port
        self.kiss_port = kiss_port
        self.nfreq = nfreq
        self.offset = offset
        self.port = port

        ##################################################
        # Variables
        ##################################################
        self.samp_rate = samp_rate = 2.5e6
        self.BFO = BFO = 0

        ##################################################
        # Blocks
        ##################################################

        self._BFO_range = qtgui.Range(-5000, 5000, 100, 0, 200)
        self._BFO_win = qtgui.RangeWidget(self._BFO_range, self.set_BFO, "'BFO'", "counter_slider", float, QtCore.Qt.Horizontal)
        self.top_layout.addWidget(self._BFO_win)
        self.satellites_telemetry_submit_0 = satellites.components.datasinks.telemetry_submit("SatNOGS", norad=64881, port='0', url = '', config=satellites.utils.config.open_config(), options="")
        self.satellites_satellite_decoder_0 = satellites.core.gr_satellites_flowgraph(file = '/home/bob/gr-satellites/python/satyaml/239Alferov.yml', samp_rate = 50000, grc_block = True, iq = True, options = '')
        self.satellites_print_timestamp_0 = satellites.print_timestamp('%Y-%m-%d %H:%M:%S', True)
        self.satellites_kiss_file_sink_0_0 = satellites.components.datasinks.kiss_file_sink('/home/bob/Desktop/239Alferov_noPDU2KISS.kss', append = True, options="")
        self.satellites_hexdump_sink_0 = satellites.components.datasinks.hexdump_sink(options="")
        self.rational_resampler_xxx_0 = filter.rational_resampler_fff(
                interpolation=48000,
                decimation=50000,
                taps=[],
                fractional_bw=0)
        self.qtgui_waterfall_sink_x_0 = qtgui.waterfall_sink_c(
            1024, #size
            window.WIN_BLACKMAN_hARRIS, #wintype
            0, #fc
            50000, #bw
            '239Alferov', #name
            1, #number of inputs
            None # parent
        )
        self.qtgui_waterfall_sink_x_0.set_update_time(0.10)
        self.qtgui_waterfall_sink_x_0.enable_grid(False)
        self.qtgui_waterfall_sink_x_0.enable_axis_labels(True)



        labels = ['', '', '', '', '',
                  '', '', '', '', '']
        colors = [0, 0, 0, 0, 0,
                  0, 0, 0, 0, 0]
        alphas = [1.0, 1.0, 1.0, 1.0, 1.0,
                  1.0, 1.0, 1.0, 1.0, 1.0]

        for i in range(1):
            if len(labels[i]) == 0:
                self.qtgui_waterfall_sink_x_0.set_line_label(i, "Data {0}".format(i))
            else:
                self.qtgui_waterfall_sink_x_0.set_line_label(i, labels[i])
            self.qtgui_waterfall_sink_x_0.set_color_map(i, colors[i])
            self.qtgui_waterfall_sink_x_0.set_line_alpha(i, alphas[i])

        self.qtgui_waterfall_sink_x_0.set_intensity_range(-140, 10)

        self._qtgui_waterfall_sink_x_0_win = sip.wrapinstance(self.qtgui_waterfall_sink_x_0.qwidget(), Qt.QWidget)

        self.top_layout.addWidget(self._qtgui_waterfall_sink_x_0_win)
        self.overflow_monitor_overflow_tag_monitor_0 = overflow_monitor.overflow_tag_monitor('alferov', samp_rate, '/home/bob/Desktop', 'pass_log.csv')
        self.osmosdr_source_1 = osmosdr.source(
            args="numchan=" + str(1) + " " + 'driver=airspy,serial=466c64c8323184c7,soapy=0'
        )
        self.osmosdr_source_1.set_time_unknown_pps(osmosdr.time_spec_t())
        self.osmosdr_source_1.set_sample_rate(samp_rate)
        self.osmosdr_source_1.set_biast(False)
        self.osmosdr_source_1.set_setting("gains", 'sensitivity')
        self.osmosdr_source_1.set_center_freq((nfreq-offset), 0)
        self.osmosdr_source_1.set_freq_corr(0, 0)
        self.osmosdr_source_1.set_dc_offset_mode(0, 0)
        self.osmosdr_source_1.set_iq_balance_mode(0, 0)
        self.osmosdr_source_1.set_gain_mode(False, 0)
        self.osmosdr_source_1.set_gain(21, 0)
        self.osmosdr_source_1.set_if_gain(15, 0)
        self.osmosdr_source_1.set_bb_gain(15, 0)
        self.osmosdr_source_1.set_antenna('', 0)
        self.osmosdr_source_1.set_bandwidth(0, 0)
        self.low_pass_filter_0 = filter.fir_filter_ccf(
            50,
            firdes.low_pass(
                1,
                samp_rate,
                25000,
                6000,
                window.WIN_HAMMING,
                6.76))
        self.gpredict_doppler_0 = gpredict.doppler('127.0.0.1', gpredict_port, False)
        self.gpredict_MsgPairToVar_0 = gpredict.MsgPairToVar(self.set_freq)
        self.blocks_multiply_xx_1 = blocks.multiply_vcc(1)
        self.audio_sink_0 = audio.sink(48000, "", True)
        self.analog_sig_source_x_0_0 = analog.sig_source_c(2500000, analog.GR_COS_WAVE, (-(freq-nfreq+offset)+BFO), 1, 0, 0)
        self.analog_quadrature_demod_cf_0 = analog.quadrature_demod_cf((50000/(2*3.14159265*4800)))


        ##################################################
        # Connections
        ##################################################
        self.msg_connect((self.gpredict_doppler_0, 'freq'), (self.gpredict_MsgPairToVar_0, 'inpair'))
        self.msg_connect((self.satellites_print_timestamp_0, 'out'), (self.satellites_hexdump_sink_0, 'in'))
        self.msg_connect((self.satellites_print_timestamp_0, 'out'), (self.satellites_kiss_file_sink_0_0, 'in'))
        self.msg_connect((self.satellites_print_timestamp_0, 'out'), (self.satellites_telemetry_submit_0, 'in'))
        self.msg_connect((self.satellites_satellite_decoder_0, 'out'), (self.satellites_print_timestamp_0, 'in'))
        self.connect((self.analog_quadrature_demod_cf_0, 0), (self.rational_resampler_xxx_0, 0))
        self.connect((self.analog_sig_source_x_0_0, 0), (self.blocks_multiply_xx_1, 1))
        self.connect((self.blocks_multiply_xx_1, 0), (self.low_pass_filter_0, 0))
        self.connect((self.low_pass_filter_0, 0), (self.analog_quadrature_demod_cf_0, 0))
        self.connect((self.low_pass_filter_0, 0), (self.qtgui_waterfall_sink_x_0, 0))
        self.connect((self.low_pass_filter_0, 0), (self.satellites_satellite_decoder_0, 0))
        self.connect((self.osmosdr_source_1, 0), (self.overflow_monitor_overflow_tag_monitor_0, 0))
        self.connect((self.overflow_monitor_overflow_tag_monitor_0, 0), (self.blocks_multiply_xx_1, 0))
        self.connect((self.rational_resampler_xxx_0, 0), (self.audio_sink_0, 0))


    def closeEvent(self, event):
        self.settings = Qt.QSettings("GNU Radio", "A239Alferov")
        self.settings.setValue("geometry", self.saveGeometry())
        self.stop()
        self.wait()

        event.accept()

    def get_filter_width(self):
        return self.filter_width

    def set_filter_width(self, filter_width):
        self.filter_width = filter_width

    def get_freq(self):
        return self.freq

    def set_freq(self, freq):
        self.freq = freq
        self.analog_sig_source_x_0_0.set_frequency((-(self.freq-self.nfreq+self.offset)+self.BFO))

    def get_gpredict_port(self):
        return self.gpredict_port

    def set_gpredict_port(self, gpredict_port):
        self.gpredict_port = gpredict_port

    def get_kiss_port(self):
        return self.kiss_port

    def set_kiss_port(self, kiss_port):
        self.kiss_port = kiss_port

    def get_nfreq(self):
        return self.nfreq

    def set_nfreq(self, nfreq):
        self.nfreq = nfreq
        self.analog_sig_source_x_0_0.set_frequency((-(self.freq-self.nfreq+self.offset)+self.BFO))
        self.osmosdr_source_1.set_center_freq((self.nfreq-self.offset), 0)

    def get_offset(self):
        return self.offset

    def set_offset(self, offset):
        self.offset = offset
        self.analog_sig_source_x_0_0.set_frequency((-(self.freq-self.nfreq+self.offset)+self.BFO))
        self.osmosdr_source_1.set_center_freq((self.nfreq-self.offset), 0)

    def get_port(self):
        return self.port

    def set_port(self, port):
        self.port = port

    def get_samp_rate(self):
        return self.samp_rate

    def set_samp_rate(self, samp_rate):
        self.samp_rate = samp_rate
        self.low_pass_filter_0.set_taps(firdes.low_pass(1, self.samp_rate, 25000, 6000, window.WIN_HAMMING, 6.76))
        self.osmosdr_source_1.set_sample_rate(self.samp_rate)

    def get_BFO(self):
        return self.BFO

    def set_BFO(self, BFO):
        self.BFO = BFO
        self.analog_sig_source_x_0_0.set_frequency((-(self.freq-self.nfreq+self.offset)+self.BFO))



def argument_parser():
    parser = ArgumentParser()
    parser.add_argument(
        "--filter-width", dest="filter_width", type=eng_float, default=eng_notation.num_to_str(float(20000)),
        help="Set FM filter width [default=%(default)r]")
    parser.add_argument(
        "-f", "--freq", dest="freq", type=eng_float, default=eng_notation.num_to_str(float(436.272e6)),
        help="Set frequency [default=%(default)r]")
    parser.add_argument(
        "--gpredict-port", dest="gpredict_port", type=intx, default=4531,
        help="Set GPredict port [default=%(default)r]")
    parser.add_argument(
        "-k", "--kiss-port", dest="kiss_port", type=intx, default=8100,
        help="Set kiss_port [default=%(default)r]")
    parser.add_argument(
        "--nfreq", dest="nfreq", type=eng_float, default=eng_notation.num_to_str(float(436.272e6)),
        help="Set Nominal Frequency [default=%(default)r]")
    parser.add_argument(
        "--offset", dest="offset", type=eng_float, default=eng_notation.num_to_str(float(50e3)),
        help="Set centre frequency offset [default=%(default)r]")
    parser.add_argument(
        "--port", dest="port", type=intx, default=7355,
        help="Set port [default=%(default)r]")
    return parser


def main(top_block_cls=A239Alferov, options=None):
    if options is None:
        options = argument_parser().parse_args()

    qapp = Qt.QApplication(sys.argv)

    tb = top_block_cls(filter_width=options.filter_width, freq=options.freq, gpredict_port=options.gpredict_port, kiss_port=options.kiss_port, nfreq=options.nfreq, offset=options.offset, port=options.port)

    tb.start()

    tb.show()

    def sig_handler(sig=None, frame=None):
        tb.stop()
        tb.wait()

        Qt.QApplication.quit()

    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    timer = Qt.QTimer()
    timer.start(500)
    timer.timeout.connect(lambda: None)

    qapp.exec_()

if __name__ == '__main__':
    main()
