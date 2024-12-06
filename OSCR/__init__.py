from .constants import HEAL_TREE_HEADER, LIVE_TABLE_HEADER, TABLE_HEADER, TREE_HEADER
from .datamodels import TreeItem
from .iofunc import split_log_by_combat, split_log_by_lines, repair_logfile
from .liveparser import LiveParser
from .main import OSCR

__all__ = (
        'HEAL_TREE_HEADER', 'LIVE_TABLE_HEADER', 'LiveParser', 'OSCR', 'repair_logfile',
        'split_log_by_combat', 'split_log_by_lines', 'TABLE_HEADER', 'TREE_HEADER', 'TreeItem')

# configure multiprocessing
if __name__ == 'OSCR':
    from multiprocessing import freeze_support, set_start_method
    freeze_support()
    set_start_method('spawn')
    del freeze_support
    del set_start_method
