import logging
import sys
import os

from influxspeedtest.common.logfilters import SingleLevelFilter

# Logging
config_logging_level = os.getenv("LOG_LEVEL", "debug")
config_logging_level = config_logging_level.upper()

log = logging.getLogger(__name__)
log.setLevel(config_logging_level)
formatter = logging.Formatter('%(asctime)s - %(levelname)s: %(message)s')

general_handler = logging.StreamHandler(sys.stdout)
general_filter = SingleLevelFilter(logging.INFO, False)
general_handler.setFormatter(formatter)
general_handler.addFilter(general_filter)
log.addHandler(general_handler)

error_handler = logging.StreamHandler(sys.stderr)
error_filter = SingleLevelFilter(logging.WARNING)
error_handler.setFormatter(formatter)
error_handler.addFilter(error_filter)
log.addHandler(error_handler)

log.propagate = False