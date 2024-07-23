from loguru import logger
import functools

def deprecated(func):
    """This is a decorator which can be used to mark functions
    as deprecated. It will result in a warning being emitted
    when the function is used."""

    @functools.wraps(func)
    def new_func(*args, **kwargs):
        logger.warning(
            "Call to deprecated function {} in file {} at line {}.".format(
                func.__name__,
                func.__code__.co_filename,
                func.__code__.co_firstlineno + 1
            )
        )
        return func(*args, **kwargs)
    return new_func

def log_variables(func):
    def wrapper(*args, **kwargs):
        local_vars = {}
        def tracer(frame, event, arg):
            if event == 'return':
                for var, value in frame.f_locals.items():
                    if var not in local_vars or local_vars[var] != value:
                        local_vars[var] = value
                        logger.trace(f"Variable {var} changed to {value} in {func.__name__}")
            return tracer
        import sys
        sys.settrace(tracer)
        try:
            result = func(*args, **kwargs)
        finally:
            sys.settrace(None)
        return result
    return wrapper

# use logger.catch to log exceptions

def log_entry_exit(func):
    def wrapper(*args, **kwargs):
        logger.info(f"Entering: {func.__name__} with args: {args}, kwargs: {kwargs}")
        result = func(*args, **kwargs)
        logger.info(f"Exiting: {func.__name__} with result: {result}")
        return result
    return wrapper


