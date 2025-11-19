import logging

class ConditionalFormatter(logging.Formatter):
    """A logging formatter that can disable log formatting for single messages"""

    def format(self, record):
        if hasattr(record, 'simple') and record.simple:
            return record.getMessage()
        else:
            return logging.Formatter.format(self, record)