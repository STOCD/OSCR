from copy import deepcopy
import os
import time
from threading import Event, Lock, Thread, Timer
from types import FunctionType, BuiltinFunctionType, MethodType

from .utilities import to_datetime

CALLABLE = (FunctionType, BuiltinFunctionType, MethodType)


def _f(*args, **kwargs):
    return


class LiveParser():
    '''
    OSCR's realtime parser
    '''

    def __init__(self, log_path, start_callback=None, update_callback=None, settings: dict = None):
        '''
        Creates LiveParser Instance.

        Parameters:
        - :param log_path: path to combatlog that is being analyzed
        - :param start_callback: function that is called immediately before the live parser starts
        to analyze the logfile initiated by the LiveParser.start() function; no arguments will be
        passed
        - :param update_callback: function that is called once every second when the parser is
        running; it will be passed a dictionary with the data acquired in the last second as
        positional argument
        - :param settings: contains settings
            - "seconds_between_combats": number of inactive seconds after which a new engagement
            resets the collected data
        '''
        if not (os.path.exists(log_path) and os.path.isfile(log_path)):
            raise FileNotFoundError('Invalid Logpath')
        self._active = Event()
        self._lock = Lock()
        self._players = dict()
        self._inactive_seconds = 0
        self._reset = False
        if isinstance(start_callback, CALLABLE):
            self.start_callback = start_callback
        else:
            self.start_callback = _f
        if isinstance(update_callback, CALLABLE):
            self.update_callback = update_callback
        else:
            self.update_callback = _f
        self._update_timer = Timer(interval=1, function=self.update_data)
        self.log_path = log_path
        self.settings = {
            'seconds_between_combats': 100
        }
        for key in self.settings:
            if key in settings:
                self.settings[key] = settings[key]

    def __del__(self):
        """
        Stops all active threads when the object is garbage-collected.
        """
        self.stop()

    def start(self):
        """
        Initiates the parsing process.
        """
        if not self._active.is_set():
            self.start_callback()
            analyzer_thread = Thread(target=self.analyze, args=())
            analyzer_thread.start()
            self._update_timer = Timer(interval=1, function=self.update_data)
            self._update_timer.start()

    def stop(self):
        """
        Terminates the parsing process. Already running threads might perform one more data
        iteration before the process ends.
        """
        self._active.clear()
        self._update_timer.cancel()

    def update_data(self):
        """
        Refines the data and executes the update_callback. Runs once per second when active.
        """
        if not self._active:
            return
        self._update_timer = Timer(interval=1, function=self.update_data)
        self._update_timer.start()
        if not self._players:
            return
        total_attacks_in = 0
        with self._lock:
            player_copy = deepcopy(self._players)
            for player in self._players.values():
                total_attacks_in += player['attacks_in_buffer']
                player['attacks_in_buffer'] = 0
                player['base_damage_buffer'] = 0
                player['damage_buffer'] = 0
        output = dict()
        for player, player_data in player_copy.items():
            if player_data['combat_start'] is not None:
                combat_time = player_data['combat_end'] - player_data['combat_start']
                try:
                    dps = player_data['damage'] / combat_time
                except ZeroDivisionError:
                    dps = 0
                try:
                    hps = player_data['heal'] / combat_time
                except ZeroDivisionError:
                    hps = 0
            else:
                dps = 0
                hps = 0
                combat_time = 0
            try:
                debuff = (player_data['damage_buffer'] / player_data['base_damage_buffer']) - 1
            except ZeroDivisionError:
                debuff = 0
            try:
                attacks_in_share = player_data['attacks_in_buffer'] / total_attacks_in
            except ZeroDivisionError:
                attacks_in_share = 0
            output[player] = {
                'dps': dps,
                'combat_time': combat_time,
                'local_debuff': debuff * 100,
                'local_attacks_in_share': attacks_in_share * 100,
                'hps': hps,
                'kills': player_data['kills'],
                'deaths': player_data['deaths']
            }
        self.update_callback(output)

    def analyze(self):
        """
        Analyzes the log continuously until LiveParser.stop() is called. Clears existing data first
        when called.
        """
        with self._lock:
            self._players = dict()
        self._reset = False
        with open(self.log_path, 'r', encoding='utf-8') as logfile:
            logfile.seek(0, 2)
            self._active.set()
            while self._active.is_set():
                line = logfile.readline()
                if not line:
                    time.sleep(0.5)
                    if self._reset:
                        continue
                    elif self._inactive_seconds >= self.settings['seconds_between_combats']:
                        self._inactive_seconds = 0
                        self._reset = True
                    else:
                        self._inactive_seconds += 0.5
                    continue
                if self._reset:
                    with self._lock:
                        self._players = dict()
                    self._reset = False
                self._inactive_seconds = 0
                time_data, attack_data = line.split('::')
                timestamp = to_datetime(time_data).timestamp()
                attack_data = attack_data.split(',')
                player_attacks = attack_data[1].startswith("P")
                player_attacked = attack_data[5].startswith("P") and not attack_data[2]
                if not player_attacks and not player_attacked:
                    continue
                magnitude = float(attack_data[10])
                magnitude2 = float(attack_data[11])
                is_shield = attack_data[8] == 'Shield'
                is_heal = (
                        (is_shield and magnitude < 0 and magnitude2 >= 0)
                        or attack_data[8] == 'HitPoints')
                is_kill = 'Kill' in attack_data[9]
                magnitude = abs(magnitude)
                magnitude2 = abs(magnitude2)

                # ignore self damage and damage from unknown sources
                try:
                    attacker_handle = attack_data[1].split('@', 2)[-1][:-1]
                    target_handle = attack_data[5].split('@', 2)[-1][:-1]
                except IndexError:
                    if not is_heal:
                        continue

                if player_attacks:
                    if attacker_handle not in self._players:
                        with self._lock:
                            self._players[attacker_handle] = {
                                'damage': 0,
                                'combat_start': None,
                                'combat_end': None,
                                'base_damage_buffer': 0,
                                'damage_buffer': 0,
                                'heal': 0,
                                'attacks_in_buffer': 0,
                                'kills': 0,
                                'deaths': 0
                            }
                            if not is_heal and attack_data[5] != '*':
                                self._players[attacker_handle]['combat_start'] = timestamp
                    if not is_heal and attack_data[5] != '*':
                        if self._players[attacker_handle]['combat_start'] is None:
                            self._players[attacker_handle]['combat_start'] = timestamp
                        self._players[attacker_handle]['combat_end'] = timestamp
                    if not is_heal:
                        with self._lock:
                            self._players[attacker_handle]['damage'] += magnitude
                            self._players[attacker_handle]['damage_buffer'] += magnitude
                            self._players[attacker_handle]['base_damage_buffer'] += magnitude2
                            if is_kill:
                                self._players[attacker_handle]['kills'] += 1
                    else:
                        with self._lock:
                            self._players[attacker_handle]['heal'] += magnitude
                if player_attacked and not is_shield:
                    if target_handle not in self._players:
                        with self._lock:
                            self._players[target_handle] = {
                                'damage': 0,
                                'combat_start': None,
                                'base_damage_buffer': 0,
                                'damage_buffer': 0,
                                'heal': 0,
                                'attacks_in_buffer': 0,
                                'kills': 0,
                                'deaths': 0
                            }
                    with self._lock:
                        self._players[target_handle]['attacks_in_buffer'] += 1
                        if is_kill:
                            self._players[target_handle]['deaths'] += 1
