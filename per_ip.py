#!/usr/bin/env python2.7

from time import sleep
from statsd import StatsClient
import subprocess
import re

DHCP_LEASES_FILE = "/var/lib/dhcp/dnsmasq.leases"
HOSTS = "/etc/hosts"
# TABLES = ['INPUT', 'OUTPUT', 'FORWARD']
TABLES = ['FORWARD']
STATSD_HOST = '10.0.42.28'
STATSD_PORT = 8125
STATSD_PREFIX = 'zilch'

class PerIP(object):
    def __init__(self):
        self.statsd = StatsClient(
            host=STATSD_HOST,
            port=STATSD_PORT,
            prefix=STATSD_PREFIX,
            maxudpsize=512)
        self.last_vals = self.get_stats()
        sleep(5)

    def run_command(self, command):
        try:
            p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            return iter(p.stdout.readline, b'')
        except Exception as e:
            raise ValueError(command, e)

    def get_iptables_data(self, table):
        results = list()
        command = ['/sbin/iptables', '-L', table, '-nvx']
        #command = "/sbin/iptables -L {} -nvx".format(table)
        try:
            command_results = self.run_command(command)
        except ValueError as e:
            raise
        else:
            for line in command_results:
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

    def get_stats(self):
        stats = dict()
        for table in TABLES:
            stats.update(self.get_iptables_data(table))
        return stats

    def calc_stats(self):
        self.change = dict()
        self.current = self.get_stats()
        for key in self.current.keys():
            self.change[key] = dict()
            for stat in self.current[key].keys():
                # print "{}.{} == {} - {}".format(
                #    key,
                #    stat,
                #    int(self.current[key][stat]),
                #    int(self.last_vals[key].get(stat, 0)))
                try:
                    self.change[key][stat] = int(self.current[key][stat]) - int(self.last_vals[key].get(stat, 0))
                except ValueError:
                    self.change[key][stat] = int(self.current[key][stat])
        self.last_vals = self.current
        return self.change

    def post_stats(self, stats):
        names = self.get_current_leases()
        for stat in stats.keys():
            for name in stats[stat]:
                if stat in names.keys():
                    host = names[stat]['hostname'].replace(".", "_")
                elif stat == '10.0.42.1':
                    host = 'gateway'
                else:
                    host = stat.replace(".", "_")
                self.statsd.gauge("byHost.{}.{}".format(host, name), stats[stat][name])
                print "    Posting byHost.{}.{} = {}".format(host, name, stats[stat][name])

    def get_current_leases(self):
        fh = open(DHCP_LEASES_FILE, 'r')
        leases = dict()
        entries = fh.readlines()
        fh.close()
        for entry in entries:
            # Sample Entry
            # 0          1                 2           3        4
            # 1433393540 04:f7:e4:8c:c3:11 10.0.42.174 HOSTNAME 01:04:f7:e4:8c:c3:11
            parts = entry.split()
            leases[parts[2]] = dict()
            if parts[3] == "*":
                leases[parts[2]]['hostname'] = parts[1]
            else:
                leases[parts[2]]['hostname'] = parts[3]
            leases[parts[2]]['mac'] = parts[1]
        fh = open(HOSTS, 'r')
        hosts = fh.readlines()
        fh.close()
        for line in hosts:
            if len(re.sub('\s*', '', line)) and not line.startswith('#'):
                parts = line.split()
                # print parts
                leases[parts[0]] = dict()
                leases[parts[0]]['hostname'] = parts[1]
        return leases

perip = PerIP()

while 1:
    current = perip.calc_stats()
    perip.post_stats(current)

    print "Sleeping 5s"
    sleep(5)
