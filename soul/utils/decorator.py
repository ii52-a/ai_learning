from functools import wraps

from soul.utils.logger import Logger


def catch_and_log(logger:Logger,default_return=None,reraise=False):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    logger.exception("Exception occurred: {}".format(e))
                    if reraise:
                        raise
                    else:
                        return default_return
        return wrapper


    return decorator