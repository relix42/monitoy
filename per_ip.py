#!/usr/bin/env python2.7

from time import sleep
from statsd import StatsClient
import subprocess

class PerIP(object):
    def __init__(self):
        self.statsd = StatsClient(
            host='10.0.42.28',
            port=8125,
            prefix='firewall',
            maxudpsize=512)

    def run_command(self, command):
        p = subprocess.Popen(command,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT)
        return iter(p.stdout.readline, b'')

    def get_iptables_data(self, table):
        results = list()
        command = "/sbin/iptables -L {} -nvx".format(table)
        for line in self.run_command(command):
            results.append(line)
        res = dict()
        for line in results[2:]:
            result = line.split()
            if result[7] != '0.0.0.0/0':
                try:
                    res[result[7]]['out_packets'] = result[0]
                    res[result[7]]['out_bytes'] = result[1]
                except KeyError:
                    res[result[7]] = dict()
                    res[result[7]]['out_packets'] = result[0]
                    res[result[7]]['out_bytes'] = result[1]
            elif result[8] != '0.0.0.0/0':
                try:
                    res[result[8]]['in_packets'] = result[0]
                    res[result[8]]['in_bytes'] = result[1]
                except KeyError:
                    res[result[8]] = dict()
                    res[result[8]]['in_packets'] = result[0]
                    res[result[8]]['in_bytes'] = result[1]
        return res

    def post_stats(self, stats):
        for stat in stats.keys():
            for name in stats[stat]:
                self.statsd.gauge("{}.{}".format(stat, name), stats[stat][name])

perip = PerIP()

while 1:
    forwards = perip.get_iptables_data('FORWARD')
    inputs = perip.get_iptables_data('INPUT')
    outputs = perip.get_iptables_data('OUTPUT')
    locals = dict(inputs.items() + output.items())

    perip.post_stats(forwards)
    perip.post_stats(locals)
    sleep(1)
