Goals
* Pull interesting bits of information from the ALIX APU based firewall
* Be as light-weight on the firewall as possible
* Make visualizations easy

Currently used parts
* Python with python-statsd from pypi
* statsd - https://github.com/etsy/statsd - for metrics collection and publishing
* Influxdb - http://influxdb.com/ - data storage
* Grafana - http://grafana.org/ - easy visualization
* iptaccount - apt-get install xtables-addons-common

Code
* bw.py -- Reads from /proc/net/dev every second and pushes results to statsd