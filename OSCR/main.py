from collections.abc import Callable
from datetime import timedelta, datetime
from multiprocessing import Event, Process, Queue
from multiprocessing.pool import Pool
import os
from queue import Empty as EmptyException

from .combat import Combat
from .constants import BANNED_ABILITIES
from .datamodels import LogLine, TreeItem
from .detection import Detection
from .iofunc import extract_bytes, reset_temp_folder
from .oscr_read_file_backwards import ReadFileBackwards
from .parser import analyze_combat
from .utilities import datetime_to_display, get_entity_name, to_datetime


def _f(*args, **kwargs):
    pass


def raise_error(error: BaseException):
    raise error


class OSCR:

    version = '2025.7.10.0'
    __version__ = '1.0'

    def __init__(self, log_path: str = '', settings: dict = None):
        self.log_path = log_path
        self.combats: list[Combat] = list()
        self.bytes_consumed: int = 0  # -1 would mean entire log has been consumed
        self.combat_analyzed_callback: Callable[[Combat], None] = _f
        self.error_callback: Callable[[BaseException], None] = raise_error
        self._settings = {
            "combats_to_parse": 10,
            "seconds_between_combats": 100,
            "combat_min_lines": 20,
            "excluded_event_ids": ["Autodesc.Combatevent.Falling"],
            "graph_resolution": 0.2,
            "templog_folder_path": f"{os.path.dirname(os.path.abspath(__file__))}/~temp_log_files",
        }
        self._pool = None
        self._queue = None

        if settings is not None:
            self._settings.update(settings)
        reset_temp_folder(self._settings['templog_folder_path'])

    def __del__(self):
        if isinstance(self._pool, Pool):
            self._pool.terminate()

    @property
    def analyzed_combats(self) -> list[str]:
        """
        Contains tuple with available combats.
        """
        res = list()
        for c in self.combats:
            if c.difficulty:
                res.append(
                    f"{c.map} ({c.difficulty} Difficulty) at {datetime_to_display(c.start_time)}"
                )
            else:
                res.append(f"{c.map} {datetime_to_display(c.start_time)}")
        return res

    def reset_parser(self):
        """
        Resets the parser to default state. Removes stored combats, logfile data and log path.
        """
        self.log_path = ''
        self.combats = list()
        self.bytes_consumed = 0
        self.combats_pointer = None

    @staticmethod
    def _analyze_log_file(
            log_path: str, total_combats: int, first_combat_id: int, offset: int, settings: dict,
            combat_handler: Callable[[Combat], None] = _f,
            error_handler: Callable[[BaseException], None] = raise_error):
        """
        (Internal Function) Reads a logfile, isolates combats and calls `combat_handler` for each
        combat as soon as it has been found.

        Parameters:
        - :param log_path: log path to be analyzed; overwrites `self.log_path`
        - :param total_combats: stops isolating combats when combat id reaches `total_combats`
        - :param first_combat_id: id that the first found combat gets; id is incremented per combat
        - :param offset: offset in bytes from the end of the logfile
        - :param settings: contains settings for parser; uses keys "seconds_between_combats" and
        "graph_resolution"
        - :param combat_handler: Called once for each analyzed combat as soon as the combats
        analyzation is complete
        - :param error_handler: Called when an error occurs during logfile analyzation

        :return: -1 if entire file has been consumed; otherwise next byte to analyze counted from
        the end of the file
        """
        combat_delta = timedelta(seconds=settings['seconds_between_combats'])
        combat_id = first_combat_id
        current_combat = Combat(settings['graph_resolution'], combat_id, log_path)
        log_consumed = True
        try:
            with ReadFileBackwards(log_path, offset) as backwards_file:
                if len(backwards_file.top) <= 2:
                    last_log_time = datetime.now() + timedelta(days=1)
                else:
                    last_log_time = to_datetime(backwards_file.top.split('::')[0])
                current_combat.end_time = last_log_time
                current_combat.file_pos[1] = backwards_file.filesize - offset
                for line in backwards_file:
                    if len(line) <= 2:
                        continue
                    time_data, attack_data = line.split('::')
                    splitted_line = attack_data.split(',')
                    if splitted_line[6] in BANNED_ABILITIES:
                        continue
                    log_time = to_datetime(time_data)
                    if last_log_time - log_time > combat_delta:
                        current_file_position = backwards_file.filesize - (
                                backwards_file.get_bytes_read(True) + offset)
                        if len(current_combat.log_data) >= settings['combat_min_lines']:
                            current_combat.start_time = last_log_time
                            current_combat.file_pos[0] = current_file_position
                            combat_handler(current_combat)
                            combat_id += 1
                        if combat_id >= total_combats:
                            log_consumed = False
                            new_offset = backwards_file.get_bytes_read(True) + offset
                            break
                        current_combat = Combat(settings['graph_resolution'], combat_id, log_path)
                        current_combat.end_time = log_time
                        current_combat.file_pos[1] = current_file_position
                    current_line = LogLine(
                        log_time,
                        *splitted_line[:10],
                        float(splitted_line[10]),
                        float(splitted_line[11]),
                    )
                    last_log_time = log_time
                    current_combat.log_data.appendleft(current_line)
            if log_consumed:
                if len(current_combat.log_data) >= settings['combat_min_lines']:
                    current_combat.start_time = log_time
                    current_combat.file_pos[0] = 0
                    combat_handler(current_combat)
                new_offset = -1
        except BaseException as e:
            if 'line' in locals():
                e.args = (*e.args, line)
            else:
                e.args = (*e.args, 'Error before loop!')
            error_handler(e)
            return 0
        return new_offset

    def analyze_log_file(
            self, log_path: str = '', max_combats: int = -1, offset: int = -1,
            result_handler: Callable[[Combat], None] = _f):
        """
        Analyzes log file in `self.log_file` and appends analyzed combats to `self.combats`.
        (Can cause duplicate combats to appear, use `self.reset_parser` if analyzing new log file.)

        Parameters:
        - :param log_path: log path to be analyzed; overwrites `self.log_path`
        - :param max_combats: maximum number of combats to analyze
        - :param offset: offset in bytes from the end of the logfile
        - :param result_handler: Called once for each analyzed combat as soon as the combats
        analyzation is complete
        """

        if log_path != '':
            self.log_path = log_path
        elif self.log_path == '':
            raise AttributeError(
                '"self.log_path" or parameter "log_path" must contain a path to a log file.'
            )
        if self.bytes_consumed < 0:
            return
        next_combat_id = len(self.combats)
        if max_combats < 0:
            max_combats = self._settings['combats_to_parse']
        total_combats = len(self.combats) + max_combats
        self.combats.extend([None] * max_combats)
        if offset < 0:
            offset = self.bytes_consumed
        if result_handler is not _f:
            self.combat_analyzed_callback = result_handler
        self.bytes_consumed = OSCR._analyze_log_file(
                self.log_path, total_combats, next_combat_id, offset, self._settings,
                self.analyze_new_combat, self.error_callback)
        self.combats = [combat for combat in self.combats if combat is not None]

    def analyze_log_file_mp(
            self, log_path: str = '', max_combats: int = -1, offset: int = -1,
            result_handler: Callable[[Combat], None] = _f):
        """
        Analyzes log file in `self.log_file` and appends analyzed combats to `self.combats`.
        (Can cause duplicate combats to appear, use `self.reset_parser` if analyzing new log file.)
        Blocks until given number of combats have been isolated.

        Parameters:
        - :param log_path: log path to be analyzed; overwrites `self.log_path`
        - :param max_combats: maximum number of combats to analyze
        - :param offset: offset in bytes from the end of the logfile
        - :param result_handler: Called once for each analyzed combat as soon as the combats
        analyzation is complete
        """
        if log_path != '':
            self.log_path = log_path
        elif self.log_path == '':
            raise AttributeError(
                '"self.log_path" or parameter "log_path" must contain a path to a log file.'
            )
        if self.bytes_consumed < 0:
            return
        next_combat_id = len(self.combats)
        if max_combats < 0:
            max_combats = self._settings['combats_to_parse']
        total_combats = len(self.combats) + max_combats
        self.combats.extend([None] * max_combats)
        if offset < 0:
            offset = self.bytes_consumed
        if result_handler is not _f:
            self.combat_analyzed_callback = result_handler
        self._pool = Pool(4)
        self._queue = Queue()
        args = (self._queue, self.log_path, total_combats, next_combat_id, offset, self._settings)
        logfile_process = Process(target=OSCR._analyze_file_helper, args=args)
        logfile_process.start()
        combats_isolated_num = 0
        while True:
            try:
                data = self._queue.get(timeout=15)
            except EmptyException:
                break
            if isinstance(data, int):
                self.bytes_consumed = data
                for _ in range(max_combats - combats_isolated_num):
                    self.combats.pop()
                break
            if isinstance(data, BaseException):
                self._pool.terminate()
                self.error_callback(data)
                break
            else:
                combats_isolated_num += 1
                self._pool.apply_async(
                        analyze_combat, args=(data,), callback=self.handle_analyzed_result,
                        error_callback=self.error_callback)
        self._pool.close()

    @staticmethod
    def _analyze_file_helper(queue, log_path, total_combats, first_combat_id, offset, settings):
        """
        Helper method to put return value of function into queue to be sent to main process. Wraps
        `_analyze_log_file`.
        """
        queue.put(OSCR._analyze_log_file(
                log_path, total_combats, first_combat_id, offset, settings,
                lambda combat: queue.put(combat), lambda error: queue.put(error)))

    def analyze_new_combat(self, combat: Combat):
        """
        Analyzes isolated combat, puts it into `self.combats` and calls the combat analyzed callback
        """
        analyze_combat(combat)
        self.combats[combat.id] = combat
        self.combat_analyzed_callback(combat)

    def handle_analyzed_result(self, result_combat: Combat):
        """
        puts analyzed combat into `self.combats` and calls the combat analyzed callback
        """
        self.combats[result_combat.id] = result_combat
        self.combat_analyzed_callback(result_combat)

    def isolate_combats(self, path: str, max_combats: int = -1) -> list[tuple]:
        """
        Returns list of combats in logfile at given `path`.

        Parameters:
        - :param path: path to the logfile
        - :param max_combats: maximum number of combats to isolate

        :return: tuple(number of combat in file, map, date, time, difficulty, byte_start, byte_end)
        """
        combat_delta = timedelta(seconds=self._settings['seconds_between_combats'])
        combat_id = 0
        current_map_and_difficulty = ['Combat', '']
        map_identifiers = set(Detection.MAP_IDENTIFIERS_EXISTENCE.keys())
        combats = list()
        current_end_bytes = -1
        current_line_num = 0
        try:
            with ReadFileBackwards(path) as backwards_file:
                if len(backwards_file.top) <= 2:
                    llt = datetime.now() + timedelta(days=1)
                else:
                    llt = to_datetime(backwards_file.top.split('::')[0])
                current_end_bytes = backwards_file.filesize
                for line in backwards_file:
                    if len(line) <= 2:
                        continue
                    time_data, attack_data = line.split('::')
                    splitted_line = attack_data.split(',')
                    log_time = to_datetime(time_data)
                    if llt - log_time > combat_delta:
                        current_file_position = backwards_file.filesize - (
                                backwards_file.get_bytes_read(True))
                        if current_line_num >= self.settings['combat_min_lines']:
                            combats.append((
                                combat_id,
                                current_map_and_difficulty[0],
                                f'{llt.year}-{llt.month:02d}-{llt.day:02d}',
                                f'{llt.hour:02d}:{llt.minute:02d}:{llt.second:02d}',
                                current_map_and_difficulty[1],
                                current_file_position,
                                current_end_bytes))
                            combat_id += 1
                        if combat_id >= max_combats > 0:
                            return combats
                        current_map_and_difficulty = ['Combat', '']
                        current_end_bytes = current_file_position
                        current_line_num = 0
                    if get_entity_name(splitted_line[5]) in map_identifiers:
                        m = Detection.MAP_IDENTIFIERS_EXISTENCE[get_entity_name(splitted_line[5])]
                        current_map_and_difficulty[0] = m['map']
                        if m['difficulty'] != 'Any':
                            current_map_and_difficulty[1] = m['difficulty']
                    current_line_num += 1
                    llt = log_time
            if current_line_num >= self.settings['combat_min_lines']:
                combats.append((
                    combat_id,
                    current_map_and_difficulty[0],
                    f'{llt.year}-{llt.month:02d}-{llt.day:02d}',
                    f'{llt.hour:02d}:{llt.minute:02d}:{llt.second:02d}',
                    current_map_and_difficulty[1],
                    backwards_file.filesize - backwards_file.get_bytes_read(),
                    current_end_bytes))
        except BaseException as e:
            if 'line' in locals():
                e.args = (*e.args, line)
            else:
                e.args = (*e.args, 'Error before loop!')
            self.error_callback(e)
            return tuple()
        return combats

    def export_combat(self, combat_num: int, path: str):
        """
        Exports combat to new logfile

        Parameters:
        - :param combat_num: index of the combat in self.combats
        - :param path: path to export the log to, will overwrite existing files
        """
        try:
            combat = self.combats[combat_num]
        except IndexError:
            raise AttributeError(
                f"Combat #{combat_num} you are trying to save has not been isolated yet."
                f"Number of isolated combats: {len(self.combats)} -- Use "
                "OSCR.analyze_log_file() with appropriate arguments first.")
        extract_bytes(combat.log_file, path, combat.file_pos[0], combat.file_pos[1])
