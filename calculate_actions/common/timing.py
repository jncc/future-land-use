import time

def startTimers():
    return (time.time(), time.process_time())

def endTimers(startWallTime: time, startProcessTime: time, scaleVal: int = 1000):
    endWallTime = time.time()
    endProcessTime = time.process_time()

    return (((endWallTime - startWallTime) * scaleVal), ((endProcessTime - startProcessTime) * scaleVal))