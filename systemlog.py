import credentials
import logging
from logging.handlers import SMTPHandler, RotatingFileHandler

# Base global variables
emailAlert = True
logFile = 'debug.log'

# Logs host-specific configuration
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Adds screen logging, for INFO level messages and above
streamHandle = logging.StreamHandler()
streamHandle.setLevel(logging.INFO)
streamHandle.setFormatter(logging.Formatter('%(message)s'))
logger.addHandler(streamHandle)

# Adds file logging, for INFO level messages and above
fileHandle = RotatingFileHandler(logFile, maxBytes=1000000, backupCount=5, encoding='utf-8')
fileHandle.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s: %(message)s', datefmt='%d-%b-%y %H:%M:%S'))
fileHandle.setLevel(logging.INFO)
logger.addHandler(fileHandle)

# Register email alerts for CRITICAL messages
if emailAlert:
    emailEngine = logging.handlers.SMTPHandler(
        mailhost=(credentials.gmail['hostname'], credentials.gmail['port']),
        fromaddr=credentials.gmail['username'],
        toaddrs=[credentials.gmail['username']],
        subject='Update about Interesting Ukraine',
        credentials=(credentials.gmail['username'], credentials.gmail['password']),  # app specific password
        secure=()
        )
    emailEngine.setLevel(logging.CRITICAL)
    emailEngine.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s: %(message)s', datefmt='%d-%b-%y %H:%M:%S'))
    logger.addHandler(emailEngine)
