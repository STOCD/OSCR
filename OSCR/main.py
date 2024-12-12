from collections.abc import Callable
from datetime import timedelta
from multiprocessing import Event, Process, Queue
from multiprocessing.pool import Pool
import os
from queue import Empty as EmptyException

from .combat import Combat
from .constants import BANNED_ABILITIES
from .datamodels import LogLine, TreeItem
from .oscr_read_file_backwards import ReadFileBackwards
from .iofunc import extract_bytes, get_combat_log_data, reset_temp_folder, split_log_by_lines
from .parser import analyze_combat
from .utilities import datetime_to_display, to_datetime


ignored_abilities = [
    "Electrical Overload",
]


def _f(*args, **kwargs):
    pass


def raise_error(error: BaseException):
    raise error


class OSCR:
    version = "2024.12.12.1"

    def __init__(self, log_path: str = '', settings: dict = None):
        self.log_path = log_path
        self.combats: list[Combat] = list()
        self.bytes_consumed: int = 0  # -1 would mean entire log has been consumed
        self.combat_analyzed_callback: Callable[[Combat], None] = _f
        self.error_callback: Callable[[BaseException], None] = raise_error
        self._settings = {
            "combats_to_parse": 10,
            "seconds_between_combats": 100,
            "excluded_event_ids": ["Autodesc.Combatevent.Falling"],
            "graph_resolution": 0.2,
            "split_log_after": 480000,
            "templog_folder_path": f"{os.path.dirname(os.path.abspath(__file__))}/~temp_log_files",
        }
        self._pool = None
        self._queue = None
        self._running = Event()

        # old
        self.combats_pointer = None
        self.excess_log_lines = list()
        self.combatlog_tempfiles = list()
        self.combatlog_tempfiles_pointer = None

        if settings is not None:
            self._settings.update(settings)

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

    @property
    def active_combat(self):
        """
        Combat currently active (selected).
        """
        if self.combats_pointer is not None:
            return self.combats[self.combats_pointer]
        else:
            return None

    @property
    def navigation_up(self) -> bool:
        """
        Indicates whether newer combats are available, but not yet analyzed.
        """
        if self.combatlog_tempfiles_pointer is None:
            return False
        return self.combatlog_tempfiles_pointer < len(self.combatlog_tempfiles) - 1

    @property
    def navigation_down(self) -> bool:
        """
        Indicates whether older combats are available, but not yet analyzed.
        """
        if len(self.excess_log_lines) > 0:
            return True
        if self.combatlog_tempfiles_pointer is None:
            return False
        return self.combatlog_tempfiles_pointer > 0

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
        combat_delta = timedelta(seconds=settings['seconds_between_combats'])
        combat_id = first_combat_id
        current_combat = Combat(settings['graph_resolution'], combat_id, log_path)
        log_consumed = True
        try:
            with ReadFileBackwards(log_path, offset) as backwards_file:
                last_log_time = to_datetime(backwards_file.top.split('::')[0])
                current_combat.end_time = last_log_time
                current_combat.file_pos[1] = backwards_file.filesize - offset
                for line in backwards_file:
                    if line == '':
                        continue
                    time_data, attack_data = line.split('::')
                    splitted_line = attack_data.split(',')
                    if splitted_line[6] in BANNED_ABILITIES:
                        continue
                    log_time = to_datetime(time_data)
                    if last_log_time - log_time > combat_delta:
                        current_file_position = backwards_file.filesize - (
                                backwards_file.get_bytes_read(True) + offset)
                        if len(current_combat.log_data) >= 20:
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
                        float(splitted_line[11])
                    )
                    last_log_time = log_time
                    current_combat.log_data.appendleft(current_line)
            if log_consumed:
                if len(current_combat.log_data) >= 20:
                    current_combat.start_time = log_time
                    current_combat.file_pos[1] = backwards_file.filesize - (
                            backwards_file.get_bytes_read(True) + offset)
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
        print('analyze MP')
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
        queue.put(OSCR._analyze_log_file(
                log_path, total_combats, first_combat_id, offset, settings,
                lambda combat: queue.put(combat), lambda error: queue.put(error)))

    def analyze_new_combat(self, combat: Combat):
        analyze_combat(combat)
        self.combats[combat.id] = combat
        self.combat_analyzed_callback(combat)

    def handle_analyzed_result(self, result_combat: Combat):
        self.combats[result_combat.id] = result_combat
        self.combat_analyzed_callback(result_combat)

    def analyze_log_file_old(self, total_combats=None, extend=False, log_path=None):
        """
        Analyzes the combat at self.log_path and replaces self.combats with the newly parsed
        combats.

        Parameters:
        - :param total_combats: holds the number of combats that should be in self.combats after
        the method is finished.
        - :param extend: extends the list of current combats to match the number of total_combats
        by analyzing excess_log_lines
        - :param log_path: specify log path different from self.log_path to be analyzed. Has no
        effect when parameter extend is True
        """
        if self.log_path is None and log_path is None:
            raise AttributeError(
                '"self.log_path" or parameter "log_path" must contain a path to a log file.'
            )
        if total_combats is None:
            total_combats = self._settings["combats_to_parse"]
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

        # Remove blank lines from beginning of the log.
        while True:
            if log_lines[0] == "\n":
                log_lines = log_lines[1:]
            else:
                break

        combat_delta = timedelta(seconds=self._settings["seconds_between_combats"])
        last_log_time = to_datetime(log_lines[0].split("::")[0]) + 2 * combat_delta
        current_combat = Combat(self._settings["graph_resolution"])

        try:
            for line_num, line in enumerate(log_lines):
                # Some Old logs from SCM have blank lines. Skip them.
                if line == "\n":
                    continue

                if "Rehona, Sister of the Qowat Milat" in line:
                    continue

                time_data, attack_data = line.split("::")
                splitted_line = attack_data.split(",")

                skip = False
                for ability in ignored_abilities:
                    if ability == splitted_line[6]:
                        print(
                            f"Detected ignored abilitiy {ability}, {splitted_line} skipping line"
                        )
                        skip = True
                        break

                if skip:
                    continue

                log_time = to_datetime(time_data)
                if last_log_time - log_time > combat_delta:
                    if len(current_combat.log_data) >= 20:
                        current_combat.start_time = last_log_time
                        # analyze_combat(current_combat, self._settings)
                        self.combats.append(current_combat)
                    current_combat = Combat(self._settings["graph_resolution"])
                    if len(self.combats) >= total_combats:
                        self.excess_log_lines = log_lines[line_num:]
                        return
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
        except Exception:
            raise Exception(f"Failed to read log with line: {line_num} \n\n{line}")
        except ValueError:
            raise Exception(f"Failed to read log with line: {line_num} \n\n{line}")

        current_combat.start_time = last_log_time
        # analyze_combat(current_combat, self._settings)
        self.combats.append(current_combat)

    def analyze_massive_log_file(self, total_combats=None):
        """
        Analyzes the combat at self.log_path and replaces self.combats with the newly parsed
        combats. Used to analyze log files larger than around 500000 lines. Wraps around
        self.analyze_log_file.

        Parameters:
        - :param total_combats: holds the number of combats that should be in self.combats after
        the method is finished.
        """
        if self.log_path is None:
            raise AttributeError('"self.log_path" must contain a path to a log file.')
        temp_folder_path = self._settings["templog_folder_path"]
        reset_temp_folder(temp_folder_path)
        self.combatlog_tempfiles = split_log_by_lines(
            self.log_path, temp_folder_path, approx_lines_per_file=480000
        )
        self.combatlog_tempfiles_pointer = len(self.combatlog_tempfiles) - 1
        self.analyze_log_file_old(
            total_combats,
            log_path=self.combatlog_tempfiles[self.combatlog_tempfiles_pointer],
        )

    def navigate_log(self, direction: str = "down"):
        """
        Analyzes earlier combats when direction is "down"; loads earlier templog file if current
        file is exhausted; loads later combatlog file if direction is "up".

        Parameters:
        - :param direction: "down" and "up"

        :return: True when logfile was changed; False otherwise
        """
        if direction == "down" and self.navigation_down:
            if self.combatlog_tempfiles_pointer is None:
                total_combat_num = (
                    len(self.combats) + self._settings["combats_to_parse"]
                )
                self.analyze_log_file_old(total_combats=total_combat_num, extend=True)
                return False
            else:
                self.combatlog_tempfiles_pointer -= 1
                self.analyze_log_file_old(
                    log_path=self.combatlog_tempfiles[self.combatlog_tempfiles_pointer]
                )
                return True
        elif direction == "up" and self.navigation_up:
            self.combatlog_tempfiles_pointer += 1
            self.analyze_log_file_old(
                log_path=self.combatlog_tempfiles[self.combatlog_tempfiles_pointer]
            )
            return True

    # def shallow_combat_analysis(self, combat_num: int) -> tuple[list, ...]:
    #     '''
    #     Analyzes combat from currently available combats in self.combat.

    #     Parameters:
    #     - :param combat_num: index of the combat in self.combats

    #     :return: tuple containing the overview table, DPS graph data and DMG graph data
    #     '''
    #     try:
    #         combat = self.combats[combat_num]
    #         combat.analyze_shallow(graph_resolution=self._settings['graph_resolution'])
    #         self.combats_pointer = combat_num
    #     except IndexError:
    #         raise AttributeError(
    #                 f'Combat #{combat_num} you are trying to analyze has not been isolated yet. '
    #                 f'Number of isolated combats: {len(self.combats)} -- Use '
    #                 'OSCR.analyze_log_file() with appropriate arguments first.')

    def full_combat_analysis(self, combat_num: int) -> tuple[TreeItem]:
        """
        Analyzes combat
        """
        try:
            combat = self.combats[combat_num]
            self.combats_pointer = combat_num
        except IndexError:
            raise AttributeError(
                f"Combat #{combat_num} you are trying to analyze has not been isolated yet."
                f"Number of isolated combats: {len(self.combats)} -- Use "
                "OSCR.analyze_log_file() with appropriate arguments first."
            )
        # dmg_out, dmg_in, heal_out, heal_in = analyze_combat(combat, self._settings)
        return analyze_combat(combat, self._settings)
        # return dmg_out._root, dmg_in._root, heal_out._root, heal_in._root

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
