from logging import getLogger as logging_getLogger
from json import dumps
from operator import gt as operator_gt
from operator import lt as operator_lt


class MDP:
    def __init__(self, curr_state, actlist, transitions=None, reward=None, states=None, gamma=0.9):
        self.logger = logging_getLogger('mdp')
        
        if not (0 < gamma <= 1):
            raise ValueError('An MDP must have 0 < gamma <= 1')

        # collect states from transitions table if not passed.
        self.states = states or self.get_states_from_transitions(transitions)

        self.state_to_move = None
        self.curr_state = curr_state
        self.actlist = actlist
        self.action = None
        self.transitions = transitions or {}
        self.gamma = gamma

        self.reward = reward or {s: 0 for s in self.states}

        # self.check_consistency()

    def R(self, state):
        """Return a numeric reward for this state."""
        return self.reward[state]

    def T(self, state, action):
        """Transition model. From a state and an action, return a list
        of (probability, result-state) pairs."""

        if not self.transitions:
            raise ValueError('Transition model is missing')
        else:
            return self.transitions[state][action]

    def get_states_from_transitions(self, transitions):
        if isinstance(transitions, dict):
            s1 = set(transitions.keys())
            s2 = set(tr[1] for actions in transitions.values()
                     for effects in actions.values()
                     for tr in effects)
            return s1.union(s2)
        else:
            return None

    def check_consistency(self):

        # check that all states in transitions are valid
        assert set(self.states) == self.get_states_from_transitions(self.transitions)

        # check that init is a valid state
        assert self.curr_state in self.states

        # check reward for each state
        assert set(self.reward.keys()) == set(self.states)

        # check that probability distributions for all actions sum to 1
        for s1, actions in self.transitions.items():
            for a in actions.keys():
                s = 0
                for o in actions[a]:
                    s += o[0]
                assert abs(s - 1) < 0.001

    def value_iteration(self, epsilon=0.001):
        """Solving an MDP by value iteration."""

        self.logger.debug('value iteration started')
        U1 = {s: 0 for s in self.states}
        R, T, gamma = self.R, self.T, self.gamma
        while True:
            U = U1.copy()
            delta = 0
            for s in self.states:
                U1[s] = R(s) + gamma * max(sum(p * U[s1] for (p, s1) in T(s, a))
                                           for a in self.actlist[s])
                delta = max(delta, abs(U1[s] - U[s]))
            if delta <= epsilon * (1 - gamma) / gamma:
                self.logger.debug('value iteration done')
                return U

    def best_policy(self, U):
        """Given an MDP and a utility function U, determine the best policy,
        as a mapping from state to action."""

        pi = {}
        for s in self.states:
            pi[s] = max(self.actlist[s], key=lambda a: sum(p * U[s1] for (p, s1) in self.T(s, a)))
        
        return pi

    def solve(self):
        return self.best_policy(self.value_iteration())[self.curr_state]


class ClusterMDP(MDP):
    def __init__(self, curr_state, states, transitions=None, reward=None, gamma=0.8):
        states.sort(key=int)
        actlist = {}
        for i in range(len(states)):
            actlist[states[i]] = ['nop']
            
            if i+1 < len(states):
                if i-1 > -1:
                    actlist[states[i]] += ['rmv', 'add']
                else:
                    actlist[states[i]] += ['add']
            else:
                actlist[states[i]] += ['rmv']

        super().__init__(curr_state, actlist, transitions, reward, states, gamma)
        self.logger.info('Initial state of {} shard(s)'.format(curr_state))

        self.action_stats = {'#add': 100, '#rmv': 100, 'ok_add': 99, 'ok_rmv': 99}
        self.calc_transitions(self.action_stats['ok_add'] / self.action_stats['#add'],
                              self.action_stats['ok_rmv'] / self.action_stats['#rmv'])

    def calc_reward_aux(self, metrics, thresholds, action='add', delta=0.01):
        index = self.states.index(self.curr_state)
        if action == 'add':
            next_index = index + 1
            nop = False
            weight = 2.5
        else:
            next_index = index - 1
            nop = True
            weight = 0.8

        if next_index < 0 or next_index > len(self.states)-1:
            return

        def violation_check(shard, value, threshold, comp_func, nop):
            if comp_func(value, threshold):
                self.logger.debug(shard + ' violated ' + t + ', voted for ' + action)
                self.reward[self.states[next_index]] += delta * weight
            elif nop:
                self.reward[self.states[index]] += delta

        for t in thresholds:
            for host, dct in metrics.items():
                for shard, shard_dct in dct['shards'].items():
                    metric_name = t[:-3]
                    value = dct[metric_name] if metric_name in dct else shard_dct[metric_name]
                    comp_func = operator_lt if t[-3:] == '_lo' else operator_gt
                    violation_check(shard, value, thresholds[t], comp_func, nop)

    def normalize_reward(self, delta=0.02):
        l = [self.reward[k] for k in self.reward]
        M = max(l)
        m = min(l)

        if M == m:
            return

        for k in self.reward:
            self.reward[k] = delta * (self.reward[k]-m)/(M-m)

    def reset_reward(self):
        index = self.states.index(self.curr_state)

        self.reward[self.states[index]] = 0
        if index-1 > -1:
            self.reward[self.states[index-1]] = 0

        if index+2 < len(self.states):
            self.reward[self.states[index+1]] = 0

    def calc_reward(self, metrics, thresholds_add, thresholds_rmv):
        # self.normalize_reward()
        self.reset_reward()
        self.calc_reward_aux(metrics, thresholds_add, action='add')
        self.calc_reward_aux(metrics, thresholds_rmv, action='rmv')

        reward_dict = dumps({int(x):self.reward[x] for x in self.reward.keys()}, sort_keys=True)
        self.logger.debug('state {}, rewards {}'.format(self.curr_state, reward_dict))

    def calc_transitions(self, add_p, rmv_p):
        for i in range(len(self.states)):
            self.transitions[self.states[i]] = {}

        for i in range(len(self.states)):
            self.transitions[self.states[i]]['nop'] = [(1.0, self.states[i])]

            if i+1 < len(self.states):
                if i-1 > -1:
                    self.transitions[self.states[i]]['add'] = [(1.0-add_p, self.states[i]), (add_p, self.states[i+1])]
                    self.transitions[self.states[i]]['rmv'] = [(rmv_p, self.states[i-1]), (1.0-rmv_p, self.states[i])]
                else:
                    self.transitions[self.states[i]]['add'] = [(1.0-add_p, self.states[i]), (add_p, self.states[i+1])]
            else:
                self.transitions[self.states[i]]['rmv'] = [(rmv_p, self.states[i-1]), (1.0-rmv_p, self.states[i])]

        self.logger.debug('calculated new transitions')

    def commit_action_result(self, ok, action):
        index = self.states.index(self.curr_state)

        if action == 'add':
            next_index = index + 1
        elif action == 'rmv':
            next_index = index - 1
        else:
            next_index = index

        if next_index < 0 or next_index > len(self.states)-1:
            raise Exception('transition to invalid state')

        if action != 'nop':
            self.action_stats['#'+action] += 1
            if ok:
                self.curr_state = self.states[next_index]
                self.logger.info('Transition to new state of {} shards'.format(self.curr_state))
                self.action_stats['ok_'+action] += 1
            self.calc_transitions(self.action_stats['ok_add'] / self.action_stats['#add'],
                                  self.action_stats['ok_rmv'] / self.action_stats['#rmv'])
