from logging.config import fileConfig as logging_fileConfig
from traceback import print_exc as traceback_print_exc
from xml.sax import make_parser as xml_sax_make_parser
from logging import getLogger as logging_getLogger
from socket import socket, AF_INET, SOCK_STREAM
from xml.sax import handler as xml_sax_handler
from socket import error as socket_error
from configparser import ConfigParser
from actuator import Actuator
from threading import Thread
from mdp import ClusterMDP
from time import sleep
from sys import stdout
from uuid import uuid4


class XMLHandler(xml_sax_handler.ContentHandler):
    def __init__(self):
        super().__init__()
        self.metrics = {}
        self.host = ''

    def startElement(self, tag, attr):
        if tag == 'HOST':
            self.host = attr.get('NAME')
            if self.host not in self.metrics:
                self.metrics[self.host] = {}
                self.metrics[self.host]['shards'] = {}

        elif tag == 'METRIC':
            name = attr.get('NAME')
            val = attr.get('VAL')
            ty = attr.get('TYPE')
            if ty == 'double' or ty == 'float':
                val = float(val)
            elif ty == 'uint32' or ty == 'int32':
                val = int(val)

            if name[0:5] == 'shard':
                split = name.split('_', 1)
                if split[0] not in self.metrics[self.host]['shards']:
                    self.metrics[self.host]['shards'][split[0]] = {}
                self.metrics[self.host]['shards'][split[0]][split[1]] = val
            else:
                self.metrics[self.host][name] = val


class Monitor:
    def __init__(self, ganglia_host='127.0.0.1', conf_file='monitor.conf'):
        logging_fileConfig('logging.conf')
        self.logger = logging_getLogger('monitor')
        self.conf = self._read_conf_file(conf_file)

        self.actuator = Actuator()

        states = [str(x) for x in range(1, 11)]
        start_state = str(self.actuator.current_shard_number())

        if start_state not in set(states):
            self.logger.critical("Start state '{}' not in {}, terminating".format(start_state, states))
            exit(1)

        self.mdp = ClusterMDP(start_state, states)

        self.ganglia_host = ganglia_host
        self.ganglia_port = 8651
        
        self.handler = XMLHandler()
        self.parser = xml_sax_make_parser()
        self.parser.setContentHandler(self.handler)

    def get_metrics(self):
        try:
            s = socket(AF_INET, SOCK_STREAM)
            s.connect((self.ganglia_host, self.ganglia_port))
            self.parser.parse(s.makefile('r'))
            s.close()
            self.logger.info('Fresh metrics acquired')

        except socket_error as e:
            self.logger.error(e)
            return None

        metrics = self.handler.metrics
        for host in self.conf['ignore_hosts']:
            if host in metrics:
                del metrics[host]

        return metrics

    def decide_action(self, metrics):
        self.mdp.calc_reward(metrics, self.conf['thresholds_add'], self.conf['thresholds_remove'])
        return self.mdp.solve()

    def monitor(self):
        while True:
            try:
                self._monitor()
            except Exception as e:
                self.logger.critical(e)
                traceback_print_exc(file=stdout)

    def _monitor(self):
        self.logger.info('Monitoring started')
        cached_metrics = self.get_metrics()
        # self.logger.debug('Initial Metrics:\n' + self._human_readable_metrics(cached_metrics))

        while True:
            sleep(10)
            current_metrics = self.get_metrics()

            for host, dct in current_metrics.items():
                for shard, shard_dct in dct['shards'].items():
                    for m in self.conf['delta_metrics']:
                        shard_dct[m] -= cached_metrics[host]['shards'][shard][m]
            # self.logger.debug('Metrics:\n' + self._human_readable_metrics(current_metrics))

            action = self.decide_action(current_metrics)
            action_uuid = uuid4().hex[:5]
            self.logger.info("Action '{}' [{}] decided".format(action, action_uuid))

            # run actuator in parallel threads, so as not to block monitoring
            def thread_actuator_func():
                local_action = action
                local_action_uuid = action_uuid
                try:
                    ok = self.actuator.exec_cmds_of_type(local_action, local_action_uuid, dry_run=False)
                    status_msg = 'succeeded' if ok else 'failed'
                    self.logger.info("Action '{}' [{}] {}".format(local_action, local_action_uuid, status_msg))
                    self.mdp.commit_action_result(ok, local_action)
                except Exception as e:
                    self.logger.warning("Action '{}' [{}] aborted -- {}".format(local_action, local_action_uuid, e))

            # avoid thread creation cost in case of 'nop' action or busy actuator
            if action != 'nop' and self.actuator.is_available:
                Thread(target=thread_actuator_func).start()
            else:
                status = 'succeeded' if action == 'nop' else 'aborted -- busy actuator'
                self.logger.info("Action '{}' [{}] {}".format(action, action_uuid, status))

            cached_metrics = current_metrics

    def _read_conf_file(self, conf_file):
        cfg = ConfigParser(interpolation=None, allow_no_value=True)
        cfg.read(conf_file)
        thr_sects = ['thresholds_add', 'thresholds_remove']
        other_sects = ['ignore_hosts']
        dct1 = {s: {k: float(v) for k, v in cfg.items(s)} for s in thr_sects}
        dct2 = {s: {k: v for k, v in cfg.items(s)} for s in other_sects}
        dct = {**dct1, **dct2, 'delta_metrics': set(cfg.options('delta_metrics'))}
        return dct

    def _human_readable_metrics(self, metrics):
        def format_dict(dct, start_spaces):
            res = ""
            spaces = ' ' * start_spaces
            for k, v in dct.items():
                if start_spaces == 0:
                    res += '\n'
                if isinstance(v, dict):
                    v = format_dict(v, start_spaces + 1)
                    res += '{}{}:\n{}'.format(spaces, k, v)
                else:
                    res += '{}{}: {}\n'.format(spaces, k, v)
            return res

        return format_dict(metrics, 0)


if __name__ == '__main__':
    Monitor().monitor()
