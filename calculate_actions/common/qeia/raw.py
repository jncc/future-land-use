class Raw:
    raw: dict[str, dict[str, int]]

    def __init__(self, qeiaConfigObject: dict[str, dict[str, int]]):
        raw = {}
        priorityCount: int = 0

        for option in qeiaConfigObject:
            optionConfig = {}

            if priorityCount == 0:
                priorityCount = len(qeiaConfigObject[option].keys())
            else:
                if priorityCount != len(qeiaConfigObject[option].keys()):
                    raise ValueError(f'Priority list for {option} was {len(qeiaConfigObject[option].keys())} expected it to be {priorityCount}')

            for priority in qeiaConfigObject[option]:
                if isinstance(qeiaConfigObject[option][priority], int):
                    optionConfig[priority] = qeiaConfigObject[option][priority]
                else:
                    raise ValueError(f'Priority {priority} for {option} was not an int')
                
            raw[option] = optionConfig
        
        self.raw = raw
