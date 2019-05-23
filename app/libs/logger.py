# logger.py

import datetime
import os
import traceback
from fluent import event
from fluent import sender

from app.config import config


class Logger:
    """
    Logger library for logging to console, file and logstash
    """
    access_file = os.path.abspath(config.ACCESS_LOG_PATH)
    event_file = os.path.abspath(config.EVENT_LOG_PATH)
    error_file = os.path.abspath(config.ERROR_LOG_PATH)

    sender.setup('application', host=config.FLUENTD_HOST, port=config.FLUENTD_PORT)

    @staticmethod
    def debug(module_name, action, status, msg, extra_data={}, stash=False, file=False, console=True):
        Logger.log(module_name, action, "DEBUG", status, msg, extra_data=extra_data,
                   stash=stash, file=file, console=console)

    @staticmethod
    def warn(module_name, action, status, msg, extra_data={}, stash=False, file=False, console=True):
        Logger.log(module_name, action, "WARN", status, msg, extra_data=extra_data,
                   stash=stash, file=file, console=console)

    @staticmethod
    def error(module_name, action, status, msg, extra_data={}, stash=False, file=False, console=True):
        Logger.log(module_name, action, "ERROR", status, msg, extra_data=extra_data,
                   stash=stash, file=file, console=console)

    @staticmethod
    def info(module_name, action, status, msg, extra_data={}, stash=False, file=False, console=True):
        Logger.log(module_name, action, "INFO", status, msg, extra_data=extra_data,
                   stash=stash, file=file, console=console)

    @staticmethod
    def log(module_name, action, log_level, status, msg, extra_data={}, stash=False, file=False, console=True):
        """
        Writes log depending on param

        :param module_name:
        :param action:
        :param log_level:
        :param status:
        :param msg:
        :param extra_data:
        :param stash:
        :param file:
        :param console:
        :return:
        """

        if stash is True:
            # Logger.stash_log(module_name, action, log_level, status, msg, extra_data)
            pass

        if file is True:
            Logger.log_to_file(module_name, action, log_level, status, msg, extra_data)

        if console is True:
            Logger.log_to_console(module_name, action, log_level, status, msg, extra_data)

        # Log to Fluentd
        event.Event('application.gh.sso.engine', {
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S.%f"),
            'action': action,
            'log_level': log_level,
            'message': msg,
            'extra_data': str(extra_data)
        })

    @staticmethod
    def log_to_console(module_name, action, log_level, status, msg, extra_data={}):
        """
        Writes log to console

        :param module_name:
        :param action:
        :param log_level:
        :param status:
        :param msg:
        :param extra_data:
        :return:
        """
        # Get time
        today = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S:%f")
        # Form message
        # if type(extra_data) == type({}):
        #     extra_data["module_name"] = module_name
        log_msg = "{} | {} | {} | {} | {} | {} | {} | {} | {}".format(today, config.LOGSTASH_APPLICATION_NAME,
                                                                      config.LOGSTASH_CHANNEL, module_name, action,
                                                                      log_level, status, msg, str(extra_data))
        # Print to screen
        print(log_msg)

    @staticmethod
    def log_to_file(module_name, action, log_level, status, msg, extra_data={}):
        """
        Writes log to file and screen

        :param module_name:
        :param action:
        :param log_level:
        :param status:
        :param msg:
        :param extra_data:
        :return:
        """

        try:
            # Get time
            today = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S:%f")
            log_msg = "{} | {} | {} | {} | {} | {} | {} | {} | {}".format(today, config.LOGSTASH_APPLICATION_NAME,
                                                                          config.LOGSTASH_CHANNEL, module_name, action,
                                                                          log_level, status, msg, extra_data)

            # Get file
            if log_level == "ERROR":
                filename = Logger.error_file
            elif log_level == "EVENT":
                filename = Logger.event_file
            elif log_level == "ACCESS":
                filename = Logger.access_file
            else:
                Logger.log_to_console(module_name, action, log_level, status, msg, extra_data=extra_data)
                return

            os.makedirs(os.path.dirname(filename), exist_ok=True)

            with open(filename, "a") as f:
                f.write(log_msg)
        except Exception as e:
            Logger.log_to_console(__name__, action, "ERROR", str(e), traceback.print_exc())
            # raise e