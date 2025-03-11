'''
DESCRIPTION:
    Maya logger
USAGE:
    # Get a debug logger for more verbose output
    log = getMayaLogger(level=logging.DEBUG)

    # Change the logging level to reduce the amount of messages
    log.setLevel(logging.WARN)

    # Mute all logging output
    log = getMayaLogger(type='NIL')
'''

import logging
from maya.utils import MayaGuiLogHandler


FORMAT = '%(levelname)s:%(name)s - %(message)s'
FORMAT_DATE = '%m-%d-%y %H:%M'

# Intialized loggers
_LOGGERS = {}


class NilHandler(logging.Handler):
    def emit(self, *args, **kwargs):
        pass


class MayaFormatter(logging.Formatter):
    '''
    DESCRIPTION:
        This class is a log formatter for a MayaGuiLogHandler designed
        to align with the output of Maya's MGlobal.display* commands, eg

        # Error: critical message
        # Error: error message
        # Warning: warning message
        # Info: info message
        # Debug:line debug message

    .. note::
       Other log levels fallback to the format passed in

    :param str fmt: Fallback string format
    :param str datefmt: Fallback string date format
    '''
    LEVEL_FORMATS = {
        logging.CRITICAL: '%(name)s - %(message)s',
        logging.ERROR: '%(name)s - %(message)s',
        logging.WARN: '%(name)s - %(message)s',
        logging.INFO: 'Info: %(name)s - %(message)s',
        logging.DEBUG: 'Debug: %(name)s:%(lineno)d - %(message)s',
    }

    def __init__(self, fmt=None, datefmt=None):

        self._level_formatters = {}
        for level, format in self.LEVEL_FORMATS.items():
            self._level_formatters[level] = logging.Formatter(fmt=format, datefmt=datefmt)

        super(MayaFormatter, self).__init__(fmt=fmt, datefmt=datefmt)

    def format(self, record):

        formatter = self._level_formatters.get(record.levelno)
        if formatter:
            return formatter.format(record)

        return super(MayaFormatter, self).format(record)


def getMayaLogger(name=None, logType='MAYA', level=logging.NOTSET):
    '''
    DESCRIPTION:
        Get a Maya logger or nil logger (muted log output).

    :param str name: The name of the logger. If no name is specified,
        a default of ENCORE_MAYA_LOGGER is used if the logType is MAYA else
        a default of NIL is used.
    :param str logType: MAYA or NIL are supported. If the logType is
        MAYA, the logger will have a handler added which outputs to
        the maya script editor. If the logType is NIL, the logger
        will have a handler added which mutes all output. If the logType
        is not supported, then a default python logger is returned.
    :param int level: The logging level. Defaults to `logging.NOTSET`.
    '''
    if not name:
        name = 'ENCORE_MAYA_LOGGER' if logType == 'MAYA' else 'NIL'

    # Return an initialized logger
    logger = _LOGGERS.get(name, None)
    if logger:
        return logger

    logger = logging.getLogger(name)
    if logType == 'NIL':
        if not logger.handlers:
            logger.addHandler(NilHandler())
        logger.propagate = False
        _LOGGERS[name] = logger

    # Create a maya log handler that outputs to the script editor
    elif logType == 'MAYA':
        handler = MayaGuiLogHandler()
        logger.addHandler(handler)
        logger.setLevel(level)

        # Disable propagation otherwise we'll get double output
        logger.propagate = False

        # Create a maya formatter to align with script editor output
        formatter = MayaFormatter(fmt=FORMAT, datefmt=FORMAT_DATE)
        handler.setFormatter(formatter)

        # Add to initialized loggers
        _LOGGERS[name] = logger

    return logger
