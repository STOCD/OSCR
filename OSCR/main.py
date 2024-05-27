from datetime import timedelta
import os

from .datamodels import LogLine, TreeItem
from .combat import Combat
from .iofunc import get_combat_log_data, reset_temp_folder, save_log, split_log_by_lines
from .parser import analyze_combat
from .utilities import datetime_to_display, to_datetime


class OSCR():

    version = '2024.05b270'

    def __init__(self, log_path: str = None, settings: dict = None):
        self.log_path = log_path
        self.combats: list[Combat] = list()
        self.combats_pointer = None
        self.excess_log_lines = list()
        self.combatlog_tempfiles = list()
        self.combatlog_tempfiles_pointer = None
        self._settings = {
            'combats_to_parse': 10,
            'seconds_between_combats': 100,
            'excluded_event_ids': ['Autodesc.Combatevent.Falling'],
            'graph_resolution': 0.2,
            'split_log_after': 480000,
            'templog_folder_path': f'{os.path.dirname(os.path.abspath(__file__))}/~temp_log_files'
        }
        if settings is not None:
            self._settings.update(settings)

    @property
    def analyzed_combats(self) -> list[str]:
        '''
        Contains tuple with available combats.
        '''
        res = list()
        for c in self.combats:
            if c.difficulty:
                res.append(f'{c.map} {c.difficulty} {datetime_to_display(c.start_time)}')
            else:
                res.append(f'{c.map} {datetime_to_display(c.start_time)}')
        return res

    @property
    def active_combat(self):
        '''
        Combat currently active (selected).
        '''
        if self.combats_pointer is not None:
            return self.combats[self.combats_pointer]
        else:
            return None

    @property
    def navigation_up(self) -> bool:
        '''
        Indicates whether newer combats are available, but not yet analyzed.
        '''
        if self.combatlog_tempfiles_pointer is None:
            return False
        return self.combatlog_tempfiles_pointer < len(self.combatlog_tempfiles) - 1

    @property
    def navigation_down(self) -> bool:
        '''
        Indicates whether older combats are available, but not yet analyzed.
        '''
        if len(self.excess_log_lines) > 0:
            return True
        if self.combatlog_tempfiles_pointer is None:
            return False
        return self.combatlog_tempfiles_pointer > 0

    def analyze_log_file(self, total_combats=None, extend=False, log_path=None):
        '''
        Analyzes the combat at self.log_path and replaces self.combats with the newly parsed
        combats.

        Parameters:
        - :param total_combats: holds the number of combats that should be in self.combats after
        the method is finished.
        - :param extend: extends the list of current combats to match the number of total_combats
        by analyzing excess_log_lines
        - :param log_path: specify log path different from self.log_path to be analyzed. Has no
        effect when parameter extend is True
        '''
        if self.log_path is None and log_path is None:
            raise AttributeError(
                    '"self.log_path" or parameter "log_path" must contain a path to a log file.')
        if total_combats is None:
            total_combats = self._settings['combats_to_parse']
        if extend:
            if total_combats <= len(self.combats):
                return
            log_lines = self.excess_log_lines
            self.excess_log_lines = list()
        else:
            if log_path is not None:
                log_lines = get_combat_log_data(log_path)
            else:
                log_lines = get_combat_log_data(self.log_path)
            log_lines.reverse()
            self.combats = list()
            self.excess_log_lines = list()

        combat_delta = timedelta(seconds=self._settings['seconds_between_combats'])
        last_log_time = to_datetime(log_lines[0].split('::')[0]) + 2 * combat_delta
        current_combat = Combat()

        for line_num, line in enumerate(log_lines):
            time_data, attack_data = line.split('::')
            log_time = to_datetime(time_data)
            if last_log_time - log_time > combat_delta:
                if len(current_combat.log_data) >= 20:
                    current_combat.start_time = last_log_time
                    self.combats.append(current_combat)
                current_combat = Combat()
                if len(self.combats) >= total_combats:
                    self.excess_log_lines = log_lines[line_num:]
                    return
            splitted_line = attack_data.split(',')
            current_line = LogLine(
                    log_time,
                    *splitted_line[:10],
                    float(splitted_line[10]),
                    float(splitted_line[11]),
            )
            last_log_time = log_time
            current_combat.log_data.appendleft(current_line)
            current_combat.analyze_last_line()
            if not current_combat.end_time:
                current_combat.end_time = last_log_time

        current_combat.start_time = last_log_time
        self.combats.append(current_combat)

    def analyze_massive_log_file(self, total_combats=None):
        '''
        Analyzes the combat at self.log_path and replaces self.combats with the newly parsed
        combats. Used to analyze log files larger than around 500000 lines. Wraps around
        self.analyze_log_file.

        Parameters:
        - :param total_combats: holds the number of combats that should be in self.combats after
        the method is finished.
        '''
        if self.log_path is None:
            raise AttributeError('"self.log_path" must contain a path to a log file.')
        temp_folder_path = self._settings['templog_folder_path']
        reset_temp_folder(temp_folder_path)
        self.combatlog_tempfiles = split_log_by_lines(
                self.log_path, temp_folder_path, approx_lines_per_file=480000)
        self.combatlog_tempfiles_pointer = len(self.combatlog_tempfiles) - 1
        self.analyze_log_file(
                total_combats, log_path=self.combatlog_tempfiles[self.combatlog_tempfiles_pointer])

    def navigate_log(self, direction: str = 'down'):
        '''
        Analyzes earlier combats when direction is "down"; loads earlier templog file if current
        file is exhausted; loads later combatlog file if direction is "up".

        Parameters:
        - :param direction: "down" and "up"

        :return: True when logfile was changed; False otherwise
        '''
        if direction == 'down' and self.navigation_down:
            if self.combatlog_tempfiles_pointer is None:
                total_combat_num = len(self.combats) + self._settings['combats_to_parse']
                self.analyze_log_file(total_combats=total_combat_num, extend=True)
                return False
            else:
                self.combatlog_tempfiles_pointer -= 1
                self.analyze_log_file(
                        log_path=self.combatlog_tempfiles[self.combatlog_tempfiles_pointer])
                return True
        elif direction == 'up' and self.navigation_up:
            self.combatlog_tempfiles_pointer += 1
            self.analyze_log_file(
                    log_path=self.combatlog_tempfiles[self.combatlog_tempfiles_pointer])
            return True

    def shallow_combat_analysis(self, combat_num: int) -> tuple[list, ...]:
        '''
        Analyzes combat from currently available combats in self.combat.

        Parameters:
        - :param combat_num: index of the combat in self.combats

        :return: tuple containing the overview table, DPS graph data and DMG graph data
        '''
        try:
            combat = self.combats[combat_num]
            combat.analyze_shallow(graph_resolution=self._settings['graph_resolution'])
            self.combats_pointer = combat_num
        except IndexError:
            raise AttributeError(
                    f'Combat #{combat_num} you are trying to analyze has not been isolated yet. '
                    f'Number of isolated combats: {len(self.combats)} -- Use '
                    'OSCR.analyze_log_file() with appropriate arguments first.')

    def full_combat_analysis(self, combat_num: int) -> tuple[TreeItem]:
        '''
        Analyzes combat
        '''
        try:
            combat = self.combats[combat_num]
        except IndexError:
            raise AttributeError(
                    f'Combat #{combat_num} you are trying to analyze has not been isolated yet.'
                    f'Number of isolated combats: {len(self.combats)} -- Use '
                    'OSCR.analyze_log_file() with appropriate arguments first.')
        dmg_out, dmg_in, heal_out, heal_in = analyze_combat(combat, self._settings)
        return dmg_out._root, dmg_in._root, heal_out._root, heal_in._root

    def export_combat(self, combat_num: int, path: str):
        '''
        Exports combat to new logfile

        Parameters:
        - :param combat_num: index of the combat in self.combats
        - :param path: path to export the log to, will overwrite existing files
        '''
        try:
            log_lines = self.combats[combat_num].log_data
        except IndexError:
            raise AttributeError(
                    f'Combat #{combat_num} you are trying to save has not been isolated yet.'
                    f'Number of isolated combats: {len(self.combats)} -- Use '
                    'OSCR.analyze_log_file() with appropriate arguments first.')
        save_log(path, log_lines, True)
