import gzip
import io
import os

_81920 = io.DEFAULT_BUFFER_SIZE * 10


class ReadFileBackwards():
    """reads an utf-8 encoded text file and yields its lines backwards in a memory efficient way"""

    __slots__ = (
            '_buffer_size', '_file', '_path', '_offset', 'filesize', '_position', '_remainder',
            '_lines', '_iter_counter')

    def __init__(self, path: str, offset: int = 0, buffer_size: int = _81920):
        """
        Reads utf-8 encoded text file.

        Parameters:
        - :param path: path to the text file
        - :param offset: number of bytes to ignore from the end of the file
        - :param buffer_size: number of bytes to buffer
        """
        self._buffer_size = buffer_size
        self._file = None
        self._path = path
        self._offset = offset
        self.filesize = 0
        self._position = -1
        self._remainder = bytes()
        self._lines = None
        self._iter_counter = None

    @property
    def top(self):
        """next line, None if there is no next line"""
        try:
            return self._lines[-1 - self._iter_counter]
        except IndexError:
            return None

    @property
    def total_bytes_read(self):
        """
        Number of bytes read. -1 if file has not been opened yet or is still open.
        offset not included
        """
        if self._file is not None and self._file.closed:
            return self.filesize - self._position - self._offset
        else:
            return -1

    def open(self):
        """Openes the file. (usually done by the context manager)"""
        self.__enter__()

    def close(self):
        """Closes the file. (usually done by the context manager)"""
        self.__exit__()

    def get_bytes_read(self, ignore_last_line: bool = False):
        """
        Bytes read excluding offset and number of lines.
        """
        ignore_lines = 1 if ignore_last_line else 0
        not_consumed_bytes = self._calculate_not_consumed_bytes(ignore_lines)
        return self.filesize - self._position - not_consumed_bytes - self._offset

    def __enter__(self):
        self._file = open(self._path, 'rb')
        if self._file.read(2) == b'\x1f\x8b':
            self._file.close()
            self._file = gzip.open(self._path, 'rb')
        self._file.seek(0, os.SEEK_END)
        self.filesize = self._file.tell()
        self._position = self._file.seek(self.filesize - self._offset)
        self._lines = self._get_chunk()
        self._iter_counter = 0
        return self

    def __exit__(self, ex_type, ex_value, ex_traceback):
        self._file.close()
        if self._position > 0:
            self._position += self._calculate_not_consumed_bytes()

    def __iter__(self):
        return self

    def __next__(self):
        try:
            self._iter_counter += 1
            return self._lines[-self._iter_counter]
        except IndexError:
            next_chunk = self._get_chunk()
            if len(next_chunk) == 0:
                self._iter_counter = -1
                raise StopIteration()
            else:
                self._lines = next_chunk
                self._iter_counter = 1
                return self._lines[-1]

    def _get_chunk(self):
        new_position = self._position - self._buffer_size
        if new_position <= 0:
            self._file.seek(0, 0)
            # self._position contains the number of bytes *before* it, so reading that many bytes
            # returns everything from the beginning up to (not including) the byte at self.position
            new_text = (self._file.read(self._position) + self._remainder).decode('utf-8').strip()
            new_lines = new_text.splitlines(keepends=True)
            self._remainder = bytes()
            self._position = 0
        else:
            self._position = self._file.seek(new_position, 0)
            new_bytes = self._file.read(self._buffer_size) + self._remainder
            try:
                self._remainder, line_bytes = new_bytes.split(b'\n', 1)
                self._remainder += b'\n'
            except ValueError:
                self._remainder = bytes()
                line_bytes = new_bytes
            new_lines = line_bytes.decode('utf-8').splitlines(keepends=True)
        return new_lines

    def _calculate_not_consumed_bytes(self, ignore_lines: int = 0):
        if self._iter_counter == -1:
            return 0
        not_consumed = ''.join(self._lines[:ignore_lines - self._iter_counter])
        return len(self._remainder + not_consumed.encode('utf-8'))
