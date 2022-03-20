from logging import getLogger as logging_getLogger
from configparser import ConfigParser
from json import loads as json_loads
from subprocess import Popen, PIPE


class Actuator:
    def __init__(self, conf_file='actuator.conf'):
        self.logger = logging_getLogger(__name__)
        self.is_available = True
        cfg = ConfigParser()
        cfg.read(conf_file)
        self.conf = {k: v for s in cfg.sections() for k, v in cfg.items(s)}
        self.conf['base_shard_port'] = int(self.conf['base_shard_port'])
        self.conf['repl_set_members'] = int(self.conf['repl_set_members'])
        self.conf['shard_hosts'] = self.conf['shard_hosts'].split(' ')

    def _get_port(self, repl_set_no, server_no):
        rs_offs = self.conf['repl_set_members'] * (repl_set_no - 1)
        svr_offs = server_no - 1
        return self.conf['base_shard_port'] + rs_offs + svr_offs

    def _get_server_no(self, port, repl_set_no):
        rs_offs = self.conf['repl_set_members'] * (repl_set_no - 1)
        return port - self.conf['base_shard_port'] - rs_offs + 1

    def _current_shard_dicts(self):
        cmd = [
            'mongo',
            'admin',
            '--quiet',
            '--host', self.conf['mongos_conn'],
            '--eval',
            'JSON.stringify(db.adminCommand({ listShards: 1 })["shards"])'
        ]
        p = Popen(cmd, stdout=PIPE, stderr=PIPE)
        res, err = p.communicate()

        try:
            data = json_loads(res) if res else []
        except Exception as e:
            self.logger.error("{}, result: {}".format(e, res))
            data = []

        return data

    def _to_be_added_repl_set(self):
        shard_dicts = self._current_shard_dicts()
        shard_hosts = [d['host'] for d in shard_dicts]

        max_repl_set_no = 0
        host_dicts = {h: 0 for h in self.conf['shard_hosts']}  # host: number of mongod processes

        for hstr in shard_hosts:
            rset, rsvrs = hstr.split('/')
            rsvrs = rsvrs.split(',')
            offset = len('ShardReplSet')
            repl_set_no = int(rset[offset:])

            max_repl_set_no = max(repl_set_no, max_repl_set_no)
            for rsvr in rsvrs:
                host = rsvr.split(':')[0]
                host_dicts[host] += 1

        repl_set_no = max_repl_set_no + 1
        server_hosts = even_bucket_fill(host_dicts, self.conf['repl_set_members'])
        info_dicts = []

        for server_no, host in enumerate(server_hosts, 1):
            port = self._get_port(repl_set_no, server_no)
            info_dict = {
                'repl_set_no': str(repl_set_no),
                'server_no': str(server_no),
                'host': host,
                'port': str(port)
            }
            info_dicts.append(info_dict)

        return info_dicts

    def _to_be_removed_repl_set(self):
        shard_dicts = self._current_shard_dicts()
        shard_hosts = [d['host'] for d in shard_dicts]
        info_dicts = []

        # choose max_repl_set_no N extracting it from ShardReplSetN/h1:p1,h2:p2,...
        offset = len('ShardReplSet')
        max_repl_set_str = max(shard_hosts, key=lambda h: int(h.split('/')[0][offset:]))

        rset, rsvrs = max_repl_set_str.split('/')
        rsvrs = rsvrs.split(',')
        repl_set_no = int(rset[offset:])

        for rsvr in rsvrs:
            host, port_str = rsvr.split(':')
            server_no = self._get_server_no(int(port_str), repl_set_no)
            info_dict = {
                'repl_set_no': str(repl_set_no),
                'server_no': str(server_no),
                'host': host,
                'port': port_str,
            }
            info_dicts.append(info_dict)

        return info_dicts

    def _get_add_repl_set_cmds(self):
        cmds = []
        shard_info_dicts = self._to_be_added_repl_set()

        # start shard commands
        for dct in shard_info_dicts:
            cmd = [
                self.conf['start_shard_sh'],
                '-m', self.conf['scripts_dir'],
                '-d', self.conf['mongodb_dir'],
                '-r', dct['repl_set_no'],
                '-s', dct['server_no'],
                '-h', dct['host'],
                '-p', dct['port']
            ]
            cmds.append(cmd)

        # add shard command
        repl_svrs_str = '|'.join([d['host'] + ':' + d['port'] for d in shard_info_dicts])
        repl_set_no = shard_info_dicts[0]['repl_set_no']
        cmd = [
            self.conf['add_shard_sh'],
            '-c', self.conf['mongos_conn'],
            '-r', repl_set_no,
            '-s', repl_svrs_str
        ]
        cmds.append(cmd)

        return cmds

    def _get_rmv_repl_set_cmds(self):
        cmds = []
        shard_info_dicts = self._to_be_removed_repl_set()

        # remove shard command
        repl_set_no = shard_info_dicts[0]['repl_set_no']
        cmd = [
            self.conf['rmv_shard_sh'],
            '-c', self.conf['mongos_conn'],
            '-r', repl_set_no
        ]
        cmds.append(cmd)

        # stop shard commands
        for dct in shard_info_dicts:
            cmd = [
                self.conf['stop_shard_sh'],
                '-r', dct['repl_set_no'],
                '-s', dct['server_no'],
                '-h', dct['host'],
                '-p', dct['port']
            ]
            cmds.append(cmd)

        # restart ganglia command
        shard_hosts_str = '|'.join(self.conf['shard_hosts'])
        cmd = [
            self.conf['restart_ganglia_sh'],
            '-h', shard_hosts_str
        ]
        cmds.append(cmd)
        return cmds

    def current_shard_number(self):
        shard_dicts = self._current_shard_dicts()
        shard_hosts = [d['host'] for d in shard_dicts]
        return len(shard_hosts)

    def exec_cmds_of_type(self, cmd_type, cmd_uuid='uuid', dry_run=False):
        def format_msg(msg):
            return "Action '{}' [{}] {}".format(cmd_type, cmd_uuid, msg)

        get_cmd_dct = {
            'add': self._get_add_repl_set_cmds,
            'rmv': self._get_rmv_repl_set_cmds,
        }

        if cmd_type not in get_cmd_dct:
            raise Exception('cmd_type not one of: add, rmv')

        if not self.is_available:
            raise Exception(__name__ + ' is busy')

        cmds = get_cmd_dct[cmd_type]()

        self.is_available = False
        self.logger.info(format_msg('starting'))

        for cmd in cmds:
            cmd_str = ' '.join(cmd)
            self.logger.info(format_msg('Command: {}'.format(cmd_str)))

            if not dry_run:
                p = Popen(cmd, stdout=PIPE, stderr=PIPE, encoding='utf-8')
                res, err = p.communicate()

                if res != '':
                    self.logger.info(format_msg("Output:\n{}".format(res)))

                if err != '':
                    # break on first command failure
                    self.logger.error(format_msg("Errors:\n{}".format(err)))
                    break

        # validate if commands succeeded by checking next same command
        next_first_cmd = get_cmd_dct[cmd_type]()[0]
        ok = next_first_cmd != cmds[0]

        self.is_available = True
        return ok


def even_bucket_fill(init_bucket_dict, balls):
    """
    Evenly fill the semi-filled buckets in init_bucket_dict with the given balls.
    :param: init_bucket_dict: dictionary of the form {bucket_tag: int number of balls}
    :param: balls: int number of balls to add to the buckets
    :return: list of the resulting bucket_tags for every ball given
    """

    bucket_dict = dict(init_bucket_dict)  # local copy
    asc_bucket_tags = sorted(bucket_dict.keys(), key=lambda k: bucket_dict[k])

    def get_diff_with_next(idx):
        max_idx = len(asc_bucket_tags) - 1
        if idx >= max_idx:
            return 0

        key = asc_bucket_tags[idx]
        next_key = asc_bucket_tags[idx + 1]

        return bucket_dict[next_key] - bucket_dict[key]

    def equal_fill_with_next(idx, balls):
        ball_tags = []
        rem_balls = balls

        # fill bucket at idx with balls to reach the next bucket
        diff = get_diff_with_next(idx)
        if diff > 0:
            add_balls = min(diff, balls)
            tag = asc_bucket_tags[idx]
            bucket_dict[tag] += add_balls
            ball_tags = [tag] * add_balls
            rem_balls -= add_balls

        return rem_balls, ball_tags

    def find_equal_level_idx(idx):
        max_idx = len(asc_bucket_tags) - 1
        if idx >= max_idx:
            return max_idx

        level = bucket_dict[asc_bucket_tags[idx]]
        for res_idx, tag in enumerate(asc_bucket_tags[idx+1:], idx+1):
            lvl = bucket_dict[tag]
            if lvl > level:
                return res_idx - 1

        # nothing returned so all buckets above idx have equal level
        return max_idx

    def asc_cyclic_fill(idx, balls):
        ball_tags = []
        rem_balls = balls
        max_idx = len(asc_bucket_tags) - 1

        # levels uniformly distributed at buckets if idx on last or further
        # else levels = height difference of current with next bucket
        levels = rem_balls / (max_idx + 1) if idx >= max_idx else get_diff_with_next(idx)

        while rem_balls > 0 and levels > 0:
            add_balls = min(rem_balls, idx + 1)
            for i in range(add_balls):
                tag = asc_bucket_tags[i]
                bucket_dict[tag] += 1
                ball_tags.append(tag)
            rem_balls -= add_balls
            levels -= 1

        return rem_balls, ball_tags

    rem_balls = balls   # remaining balls to be added
    res_ball_tags = []  # list with bucket tags for each ball
    start_idx = 0       # starting bucket index for each loop

    # fill starting bucket up to next level
    rem_balls, ball_buckets = equal_fill_with_next(start_idx, rem_balls)
    res_ball_tags.extend(ball_buckets)

    while rem_balls > 0:
        # fill equal levels cyclic
        start_idx = find_equal_level_idx(start_idx)
        rem_balls, ball_buckets = asc_cyclic_fill(start_idx, rem_balls)
        res_ball_tags.extend(ball_buckets)

    return res_ball_tags


if __name__ == '__main__':
    from argparse import ArgumentParser
    from logging.config import fileConfig

    fileConfig('logging.conf')

    parser = ArgumentParser()
    parser.add_argument('cmd_type', choices=['add', 'rmv'], help="mutually exclusive cmd_type set")
    parser.add_argument('--dry-run', action='store_true', help="output command without executing")
    args = parser.parse_args()

    actuator = Actuator()
    ok = actuator.exec_cmds_of_type(args.cmd_type, 'uuid', args.dry_run)
    print("Successful execution: {}".format(ok))
    print("Current Shards: {}".format(actuator.current_shard_number()))
