from common.qeia import Raw as rawQeia
import pandas as pd

class Filtered:
    qeia: dict[str, dict[str, int]] = {}

    def __init__(self, rawQeia: rawQeia, eligibility: list[str]):
        for option in rawQeia.raw:
            priorities = rawQeia.raw[option]
            
            if option.upper() in eligibility:
                self.qeia[option] = priorities


    def createOutputTableRow(self):
        row = {}
        
        for option in self.qeia:
            row[option] = self.qeia[option]

        return pd.DataFrame.from_dict(row).transpose()