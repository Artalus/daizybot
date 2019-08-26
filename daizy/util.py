import logging
import logging.handlers


def init_logger():
    logger = logging.getLogger('daizy')
    logger.setLevel(logging.DEBUG)
    ff = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh = logging.handlers.RotatingFileHandler("daizy.log", maxBytes=5*1024*1024, backupCount=2)
    fh.setFormatter(ff)
    logger.addHandler(fh)
    logger.addHandler(logging.StreamHandler())

def logger() -> logging.Logger:
    return logging.getLogger('daizy')
