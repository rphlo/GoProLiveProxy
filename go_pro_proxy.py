#!/usr/env/bin
import requests
import time
import re
import sys


DEFAULT_LIVE_URI = "http://10.5.5.9:8080/live/"
EXTINF_v3_RE = re.compile(r'\n#EXTINF\:'
                          r'(?P<duration>\d+(\.\d+)?),(?P<name>.*)\n'
                          r'(?P<filename>[^#\n]*)')
EXT_SEQ_RE = re.compile(r'\n#EXT-X-MEDIA-SEQUENCE\:(?P<seq_nb>\d+)?\n')


class StopRecording(Exception):
    pass


class GoProProxy(object):
    session = None
    last_ts = 0
    t0 = -1
    is_started = False

    def __init__(self, live_uri):
        self.live_uri = live_uri
        self.session = requests.Session()

    def download_video_routine(self):
        in_t = time.time()
        self.download_m3u()
        out_t = time.time()
        try:
            time.sleep(max(0, 2-(out_t-in_t)))
            return self.continue_recording
        except StopRecording:
            return False

    def record(self, output):
        self.continue_recording = True
        self.started =False
        self.output = output
        self.t0 = time.time()
        while self.download_video_routine():
            pass

    def stop_recording(self):
        self.continue_recording = False

    def download_m3u(self):
        try:
            resp = self.session.get(self.live_uri + "amba.m3u8")
        except:
            requests.exceptions.ConnectionError
        else:
            self.parse_m3u(resp.text)

    def parse_m3u(self, m3u_text):
        seq_nb = int(EXT_SEQ_RE.search(m3u_text).group('seq_nb'))
        for ii, x in enumerate(EXTINF_v3_RE.finditer(m3u_text)):
            ts_seq = seq_nb+ii
            filename = ''
            if ts_seq > self.last_ts:
                filename = x.group('filename')
                self.last_ts = ts_seq
                self.download_ts(filename, self.last_ts)
        self.prev_seq = seq_nb

    def download_ts(self, filename, seq_nb):
        url = self.live_uri + filename
        resp = self.session.get(url, stream=True)
        for chunk in resp.iter_content(chunk_size=1024):
            if chunk:
                if seq_nb % 2 == 0:
                    self.output.write(chunk)
                    self.output.flush()


if __name__ == "__main__":
    gopro = GoProProxy(DEFAULT_LIVE_URI)
    try:
        gopro.record(sys.stdout)
    except KeyboardInterrupt:
        gopro.stop_recording()
