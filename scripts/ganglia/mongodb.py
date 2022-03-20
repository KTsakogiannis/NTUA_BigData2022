from subprocess import Popen, PIPE
from bson import json_util
from time import time
import logging
import logging.handlers
import socket
import json
import re

MAX_DATA_AGE = 5    # seconds

server_name = ''
conn_pair = ('', 0)
descriptors = []
last_data = {}
logger = None


def get_command(cmd_name):
    global conn_pair

    cmds = {
        'server_status': 'db.serverStatus()',
        'repl_status': 'rs.status()'
    }

    host, port = conn_pair
    args = [
        'mongo',
        '--host', host,
        '--port', str(port),
        '--quiet', '--eval',
        'JSON.stringify({})'.format(cmds[cmd_name])
    ]

    return args


def get_response(cmd):
    p = Popen(cmd,
        bufsize=16384,
        close_fds=True,
        stdout=PIPE,
        stderr=PIPE
    )

    res, err = p.communicate()
    if err:
        ok = False
        data = err
    else:
        ok = True
        # remove objects
        data = re.sub('(?:NumberLong|ISODate|ObjectId)\((.*)\)', r'\1', res)
        data = re.sub('(?:Timestamp)\((.*)\)', r'"(\1)"', data)
        data = json.loads(data, object_hook=json_util.object_hook)
    return ok, data


def metric_init(params):
    """
    Skeleton metric descriptor:
    {
        'name': '',
        'call_back': '',
        'time_max': max_data_age,
        'value_type': '',
        'units': '',
        'slope': 'both',
        'format': '',
        'description': '',
        'groups': GROUPS
        }
    """
    global server_name, conn_pair, descriptors, logger

    server_name = params['server_name'] if 'server_name' in params else 'mongod_server'
    TIME_MAX = 60
    GROUPS = server_name

    logger = logging.getLogger("gmond-mongod-{}".format(server_name))
    logger.setLevel(logging.INFO)

    slh = logging.handlers.SysLogHandler(
        '/dev/log',
        facility=logging.handlers.SysLogHandler.LOG_SYSLOG,
        socktype=socket.SOCK_DGRAM
    )
    slh.setLevel(logging.INFO)
    short_format = logging.Formatter('%(name)s: %(message)s')
    slh.setFormatter(short_format)
    logger.addHandler(slh)
    logger.debug("metric_init called with arg: {}".format(params))

    host, port, max_data_age = 'localhost', 27017, TIME_MAX
    try:
        if 'host' in params:
            host = params['host']
        if 'port' in params:
            port = int(params['port'])
        if 'time_max' in params:
            max_data_age = int(params['time_max'])
    except TypeError as e:
        logger.error("error: {}".format(e))

    conn_pair = (host, port)

    try:

        descriptors = [
            {
                'name': server_name + '_mongodb_conn_current',
                'call_back': metric_handler,
                'time_max': max_data_age,
                'value_type': 'int',
                'units': 'Connections',
                'slope': 'both',
                'format': '%i',
                'description': 'Current Connections',
                'groups': GROUPS
            },
            {
                'name': server_name + '_mongodb_conn_available',
                'call_back': metric_handler,
                'time_max': max_data_age,
                'value_type': 'int',
                'units': 'Connections',
                'slope': 'both',
                'format': '%i',
                'description': 'Current Available Connections',
                'groups': GROUPS
            },
            {
                'name': server_name + '_mongodb_conn_total',
                'call_back': metric_handler,
                'time_max': max_data_age,
                'value_type': 'int',
                'units': 'Connections',
                'slope': 'both',
                'format': '%i',
                'description': 'Current Total Connections',
                'groups': GROUPS
            },
            {
                'name': server_name + '_mongodb_net_bytes_in',
                'call_back': metric_handler,
                'time_max': max_data_age,
                'value_type': 'int',
                'units': 'Bytes/Sec',
                'slope': 'positive',
                'format': '%i',
                'description': 'Bytes Received',
                'groups': GROUPS
            },
            {
                'name': server_name + '_mongodb_net_bytes_out',
                'call_back': metric_handler,
                'time_max': max_data_age,
                'value_type': 'int',
                'units': 'Bytes/Sec',
                'slope': 'positive',
                'format': '%i',
                'description': 'Bytes Sent',
                'groups': GROUPS
            },
            {
                'name': server_name + '_mongodb_op_count_insert',
                'call_back': metric_handler,
                'time_max': max_data_age,
                'value_type': 'int',
                'units': 'Operations/sec',
                'slope': 'positive',
                'format': '%i',
                'description': 'Oplog Inserts/sec',
                'groups': GROUPS
            },
            {
                'name': server_name + '_mongodb_op_count_query',
                'call_back': metric_handler,
                'time_max': max_data_age,
                'value_type': 'int',
                'units': 'Operations/sec',
                'slope': 'positive',
                'format': '%i',
                'description': 'Oplog Queries/sec',
                'groups': GROUPS
            },
            {
                'name': server_name + '_mongodb_op_count_update',
                'call_back': metric_handler,
                'time_max': max_data_age,
                'value_type': 'int',
                'units': 'Operations/sec',
                'slope': 'positive',
                'format': '%i',
                'description': 'Oplog Updates/sec',
                'groups': GROUPS
            },
            {
                'name': server_name + '_mongodb_op_count_delete',
                'call_back': metric_handler,
                'time_max': max_data_age,
                'value_type': 'int',
                'units': 'Operations/sec',
                'slope': 'positive',
                'format': '%i',
                'description': 'Oplog Deletes/sec',
                'groups': GROUPS
            },
            {
                'name': server_name + '_mongodb_op_count_getmore',
                'call_back': metric_handler,
                'time_max': max_data_age,
                'value_type': 'int',
                'units': 'Operations/sec',
                'slope': 'positive',
                'format': '%i',
                'description': 'Oplog Getmore/sec',
                'groups': GROUPS
            },
            {
                'name': server_name + '_mongodb_op_count_command',
                'call_back': metric_handler,
                'time_max': max_data_age,
                'value_type': 'int',
                'units': 'Operations/sec',
                'slope': 'positive',
                'format': '%i',
                'description': 'Oplog Commands/sec',
                'groups': GROUPS
            },
            {
                'name': server_name + '_mongodb_mem_resident',
                'call_back': metric_handler,
                'time_max': max_data_age,
                'value_type': 'int',
                'units': 'KB',
                'slope': 'both',
                'format': '%i',
                'description': 'Memory Resident',
                'groups': GROUPS
            },
            {
                'name': server_name + '_mongodb_mem_virtual',
                'call_back': metric_handler,
                'time_max': max_data_age,
                'value_type': 'int',
                'units': 'KB',
                'slope': 'both',
                'format': '%i',
                'description': 'Memory Virtual',
                'groups': GROUPS
            }
        ]

        return descriptors
    except Exception as e:
        logger.exception("metric_init exception: {}".format(e))


def metric_cleanup():
    global logger
    logger.debug("metric_cleanup called")


def metric_handler(name):
    global server_name, last_data, logger

    now = time()
    data = 0
    try:
        if not last_data or last_data['timestamp'] < (now - MAX_DATA_AGE):
            ok, resp = get_response(get_command('server_status'))

            if not ok:
                raise Exception(resp)

            server_status = resp
            last_data = {
                'timestamp': now,
                'server_status': server_status
            }
        else:
            # using cached data
            server_status = last_data['server_status']

        descriptor_dict = {
            'conn_current':     ('connections', 'current'),
            'conn_available':   ('connections', 'available'),
            'conn_total':       ('connections', 'totalCreated'),
            'net_bytes_in':     ('network', 'bytesIn'),
            'net_bytes_out':    ('network', 'bytesOut'),
            'op_count_insert':  ('opcounters', 'insert'),
            'op_count_query':   ('opcounters', 'query'),
            'op_count_update':  ('opcounters', 'update'),
            'op_count_delete':  ('opcounters', 'delete'),
            'op_count_getmore': ('opcounters', 'getmore'),
            'op_count_command': ('opcounters', 'command'),
            'mem_resident':     ('mem', 'resident'),
            'mem_virtual':      ('mem', 'virtual'),
        }
        offset = len(server_name + '_mongodb_')
        desc_key = name[offset:]
        k1, k2 = descriptor_dict[desc_key]
        data = server_status[k1][k2]

        logger.debug("metric_handler returning: name={} val={}".format(name, data))
        return data

    except Exception as e:
        logger.exception("metric_handler exception: {}".format(e))
        if __name__ == '__main__':
            print "Exception:", e
        return 0


if __name__ == '__main__':
    from time import sleep
    from datetime import datetime
    from sys import argv

    if len(argv) != 2:
        print "Usage:", argv[0], "<local_mongod_port>"
        exit(1)

    metrics = ['conn_current', 'conn_available', 'conn_total', 'net_bytes_in', 'net_bytes_out',
               'op_count_insert', 'op_count_query', 'op_count_update', 'op_count_delete',
               'op_count_getmore', 'op_count_command', 'mem_resident', 'mem_virtual']

    metric_init({'time_max': '5', 'server_name': 'svr', 'port': argv[1]})

    while True:
        print "--- {}".format(datetime.ctime(datetime.utcnow()))
        for m in metrics:
            print "{}: {}".format(m, metric_handler('svr_mongodb_' + m))
        sleep(1)
