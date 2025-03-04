class Raw:
    raw: dict[str, dict[str, int]]

    def __init__(self, qeiaConfigObject: any):
        raw = {}

        for option in qeiaConfigObject:
            optionConfig = {}

            for priority in qeiaConfigObject[option]:
                if isinstance(qeiaConfigObject[option][priority], int):
                    optionConfig[priority] = qeiaConfigObject[option][priority]
                else:
                    raise ValueError(f'Priority {priority} for {option} was not an int')
                
            raw[option] = optionConfig
        
        self.raw = raw
