import logging
import uuid
from pathlib import Path
import logging.handlers


class Logger:
    def __init__(self,logger_name,console_level=logging.INFO,file_level=logging.DEBUG):
        self.logger_name = logger_name
        self.console_level = console_level
        self.file_level = file_level
        self.logger=self._setup_logger()


    def _setup_logger(self):
        LOG_DIR = Path("Logs")
        LOG_DIR.mkdir(exist_ok=True)

        logger = logging.getLogger(self.logger_name)
        logger.setLevel(logging.DEBUG)


        if logger.handlers:
            logger.handlers.clear()

        module_dir = LOG_DIR / self.logger_name
        module_dir.mkdir(parents=True, exist_ok=True)

        log_file = module_dir / f"{self.logger_name}.log"

        formatter = logging.Formatter(
            '%(asctime)s %(message)s  <%(levelname)s> '
        )


        # 控制台输出
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.console_level)
        console_handler.setFormatter(formatter)

        # 文件输出
        file_handler = logging.handlers.TimedRotatingFileHandler(
            filename=log_file,
            when='midnight',
            interval=1,
            backupCount=7,
            encoding='utf-8',
            delay=False
        )
        file_handler.setLevel(self.file_level)
        file_handler.setFormatter(formatter)

        # 装载 handler
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger

    def start_debug(self,text,format_str:str='=',format_num:int=20):
        self.debug(f"start:{format_str*format_num}\n{text}")

    def info(self,text):
        self.logger.info(text)

    def debug(self,text):
        self.logger.debug(text)

    def warning(self,text):
        self.logger.warning(text)

    def orchestrator_step(self,trace_id:uuid,
                          process:str,
                          params:any,
                          output:any=None,
                          ):
        self.start_debug(
            f"<{trace_id}> [orchestrator_step]>>[{process}]\n"
            f"params:{params}\n"
            f"output:{output}"
        )