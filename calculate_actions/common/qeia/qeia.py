import pandas as pd

class Option:
    priorityModifiers: dict[str, int]

    def __init__(self, priorityModifiers: dict[str, int]):
        self.priorityModifiers = priorityModifiers
    
    def getPriorityModifiers(self) -> dict[str, int]:
        return self.priorityModifiers

    def getPriorityModifier(self, priority: str) -> int:
        if priority in self.priorityModifiers:
            return self.priorityModifiers[priority]
        else:
            raise ValueError(f'Prioirity "{priority}" does not exist in the current QEIA option')

class QEIAMatrix:
    options: dict[str, Option]

    def __init__(self, matrix: dict[str, dict[str, int]]):
        self.options = {}
        for option in matrix:
            self.options[option] = Option(matrix[option])
    
    def getOption(self, option) -> Option:
        if option in self.options:
            return self.options[option]
        else:
            raise ValueError(f'Option "{option}" not in matrix')

    def getFilteredMatrix(self, eligible: list[str]):
        filteredMatrix: dict[str, dict[str, int]] = {}
        for option in self.options:
            if option.upper() in eligible:
                filteredMatrix[option] = self.options[option].getPriorityModifiers()
        
        return QEIAMatrix(filteredMatrix)

    def createOutputTableRow(self):
        """_summary_

        Returns:
            _type_: _description_
        """
        row = {}
        
        for option in self.options:
            row[option] = self.options[option].getPriorityModifiers()

        return pd.DataFrame.from_dict(row)
