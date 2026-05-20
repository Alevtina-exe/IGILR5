import logging


def get_logger(name=None):
    """Получить логгер для модуля."""
    if name is None:
        name = __name__
    return logging.getLogger(f'cinema.{name}')


class LoggerMixin:
    """Миксин для добавления логирования в классы."""

    @property
    def logger(self):
        if not hasattr(self, '_logger'):
            self._logger = logging.getLogger(
                f'cinema.{self.__class__.__module__}.{self.__class__.__name__}'
            )
        return self._logger