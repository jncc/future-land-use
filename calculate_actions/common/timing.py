import time

def startTimers() -> tuple[float, float]:
    """Starts a Wall and Process Timer

    Returns:
        tuple[float, float]: A tuple containing the (wall, process) timer values
    """
    return (time.time(), time.process_time())

def endTimers(startWallTime: float, startProcessTime: float, scaleVal: int = 1000) -> tuple[float, float]:
    """Returns the total execution time for wall and process timers given a start
    wall and process time value

    Args:
        startWallTime (float): The start Walltime value
        startProcessTime (float): The start Process time value
        scaleVal (int, optional): A scaling value for the time outputs. Defaults to 1000 (milliseconds).

    Returns:
        tuple[float, float]: A tuple containing the scaled time values
    """
    endWallTime = time.time()
    endProcessTime = time.process_time()

    return (((endWallTime - startWallTime) * scaleVal), ((endProcessTime - startProcessTime) * scaleVal))