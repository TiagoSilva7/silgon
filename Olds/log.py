
import logging


logging.basicConfig(
                    level=logging.INFO,
                    format="{asctime}s - {levelname}s - {message}s", 
                    datefmt='%d-%b-%y %H:%M:%S',
                    style="{",
                    filename='Logging_message - %{asctime}.log',
                    filemode="w",
                    )


logging.debug("Debug")
logging.warning("Warning")
logging.critical("Critical")
logging.error("Error")
logging.info("Info")