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

    def __init__(self, log_path, start_callback=None, update_callback=None):
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
        '''
        if not (os.path.exists(log_path) and os.path.isfile(log_path)):
            raise FileNotFoundError('Invalid Logpath')
        self._active = Event()
        self._lock = Lock()
        self._players = dict()
        self._current_timestamp = 0
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

    def __del__(self):
        """
        Stops all active threads when the object is garbage-collected.
        """
        self.stop()

    def start(self):
        """
        Initiates the parsing process.
        """
        self.start_callback()
        analyzer_thread = Thread(target=self.analyze, args=())
        analyzer_thread.start()
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
        total_attacks_in = 0
        with self._lock:
            player_copy = deepcopy(self._players)
            timestamp = self._current_timestamp
            for player in self._players.values():
                total_attacks_in += player['attacks_in_buffer']
                player['attacks_in_buffer'] = 0
                player['base_damage_buffer'] = 0
                player['damage_buffer'] = 0
        output = dict()
        for player, player_data in player_copy.items():
            combat_time = timestamp - player_data['combat_start']
            try:
                dps = player_data['damage'] / combat_time
            except ZeroDivisionError:
                dps = 0
            try:
                debuff = (player_data['damage_buffer'] / player_data['base_damage_buffer']) - 1
            except ZeroDivisionError:
                debuff = 0
            try:
                attacks_in_share = player_data['attacks_in_buffer'] / total_attacks_in
            except ZeroDivisionError:
                attacks_in_share = 0
            try:
                hps = player_data['heal'] / combat_time
            except ZeroDivisionError:
                hps = 0
            output[player] = {
                'dps': f'{dps:,.2f}',
                'combat_time': f'{combat_time:.1f}s',
                'local_debuff': f'{debuff * 100:.2f}%',
                'local_attacks_in_share': f'{attacks_in_share * 100:.2f}%',
                'hps': f'{hps:,.2f}'
            }
        self.update_callback(output)

    def analyze(self):
        """
        Analyzes the log continuously until LiveParser.stop() is called. Clears existing data first
        when called.
        """
        self._players = dict()
        with open(self.log_path, 'r', encoding='utf-8') as logfile:
            logfile.seek(0, 2)
            self._active.set()
            while self._active.is_set():
                line = logfile.readline()
                if not line:
                    time.sleep(0.5)
                    continue
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
                magnitude = abs(magnitude)
                magnitude2 = abs(magnitude2)

                # ignore self damage and damage from unknown sources
                try:
                    attacker_handle = attack_data[1].split(' ')[1][:-1]
                    target_handle = attack_data[5].split(' ')[1][:-1]
                except IndexError:
                    if not is_heal:
                        continue

                if player_attacks:
                    if attacker_handle not in self._players:
                        with self._lock:
                            self._players[attacker_handle] = {
                                'damage': 0,
                                'combat_start': None,
                                'base_damage_buffer': 0,
                                'damage_buffer': 0,
                                'heal': 0,
                                'attacks_in_buffer': 0
                            }
                            if not is_heal and attack_data[5] != '*':
                                self._players[attacker_handle]['combat_start'] = timestamp
                    if not is_heal:
                        with self._lock:
                            self._current_timestamp = timestamp
                            self._players[attacker_handle]['damage'] += magnitude
                            self._players[attacker_handle]['damage_buffer'] += magnitude
                            self._players[attacker_handle]['base_damage_buffer'] += magnitude2
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
                                'attacks_in_buffer': 0
                            }
                    with self._lock:
                        self._players[target_handle]['attacks_in_buffer'] += 1