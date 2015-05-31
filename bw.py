#!/usr/bin/env python2.7

from time import sleep
from statsd import StatsClient

class BWReader(object):
    def __init__(self):
        self.last_vals = self.read_proc_net_dev()

    def read_proc_net_dev(self):
        try:
            stats = open("/proc/net/dev", "r").readlines()
            column_lines = stats[1]
            _, inCols, outCols = column_lines.split("|")
            inCols = map(lambda cnt: "in_"+cnt, inCols.split())
            outCols = map(lambda cnt: "out_"+cnt, outCols.split())
            allCols = inCols + outCols
            interfaces = {}
            for line in stats[2:]:
                if line.find(":") < 0: continue
                iface, data = line.split(":")
                face_info = dict(zip(allCols, data.split()))
                interfaces[iface.strip()] = face_info
            return interfaces
        except IOError as e:
            print "Unable to open /proc/net/dev due to error {0!r}".format(e)
        except FileNotFound as e:
            print "File Not Found /proc/net/dev due to error {0!r}".format(e)

    def calc_bw(self):
        self.change = dict()
        self.current = self.read_proc_net_dev()
        for key in self.current.keys():
            self.change[key] = dict()
            for stat in self.current[key].keys():
                print "{}.{} == {} - {}".format(
                    key,
                    stat,
                    int(self.current[key][stat]),
                    int(self.last_vals[key].get(stat, 0)))
                try:
                    self.change[key][stat] = int(self.current[key][stat]) - int(self.last_vals[key].get(stat, 0))
                except ValueError:
                    self.change[key][stat] = int(self.current[key][stat])
        self.last_vals = self.current
        return self.change

bwr = BWReader()
statsd = StatsClient(host='10.0.42.28',
             port=8125,
             prefix='firewall',
             maxudpsize=512)

while 1:
    stats = bwr.calc_bw()
    scounter = 0
    for interface in stats.keys():
        for stat in stats[interface].keys():
            statsd.gauge("{}.{}".format(interface, stat), stats[interface][stat])
            scounter += 1
    statsd.gauge("bw.published_stats", scounter)
    statsd.counter("bw.publish_sessions")
    sleep(1)
