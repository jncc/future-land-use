import numpy as np
import pandas as pd

class Option:
    """Helper class to contain Priority modifiers for use in QEIAMatrix class,
    stores a dict of priority modifiers for use with a weighted priority score
    table
    """
    priorityModifiers: dict[str, np.floating]

    def __init__(self, priorityModifiers: dict[str, np.floating]):
        """Generates an Option for use in a QEIAMatrix Object

        Args:
            priorityModifiers (dict[str, int]): Pairs of priority names and score
            modifiers in a dict structure
        """
        self.priorityModifiers = priorityModifiers

    def getPriorityModifiers(self) -> dict[str, np.floating]:
        """Return the priority score modifiers for this Option

        Returns:
            dict[str, int]: The priority score modifiers for this Option
        """
        return self.priorityModifiers

    def getPriorityModifier(self, priority: str) -> np.floating:
        """Return a specific priority score modifer if it exists

        Args:
            priority (str): The key for the required priority

        Raises:
            ValueError: If the key does not exist

        Returns:
            int: The priority modifier for the requested priority
        """
        if priority in self.priorityModifiers:
            return self.priorityModifiers[priority]
        else:
            raise ValueError(f'Prioirity "{priority}" does not exist in the current QEIA option')

class QEIAMatrix:
    """Helper class for QEIA Matrixes, stores a dict of string, Option pairs that
    detail the priority modifiers for different options
    """
    options: dict[str, Option]

    def __init__(self, matrix: dict[str, dict[str, np.floating]]):
        """Generates a QEIAMatrix object to use when calcuating priority scores

        Args:
            matrix (dict[str, dict[str, np.floating]]): A config dict that contains 
            option[str], (priority[str], modifier[np.floating]) for this matrix
        """
        self.options = {}
        for option in matrix:
            self.options[option] = Option(matrix[option])
    
    def getOption(self, option) -> Option:
        """Returns an option if it exists in this objects dict

        Args:
            option (_type_): The name of the option required

        Raises:
            ValueError: If the option name does not exist

        Returns:
            Option: The matching Option object
        """
        if option in self.options:
            return self.options[option]
        else:
            raise ValueError(f'Option "{option}" not in matrix')

    def getFilteredMatrix(self, eligible: list[str]):
        """Filters the current matrix by a list of eligible options

        Args:
            eligible (list[str]): A list of required option names to filter
            by

        Returns:
            QEIAMatrix: A new QEIAMatrix object filtered by the input 
            eligibility list
        """
        filteredMatrix: dict[str, dict[str, int]] = {}
        for option in self.options:
            if option in eligible:
                filteredMatrix[option] = self.options[option].getPriorityModifiers()
        
        return QEIAMatrix(filteredMatrix)

    def createDataFrame(self) -> pd.DataFrame:
        """Returns a Pandas dataframe representation of this QEIAMatrix

        Returns:
            pd.DataFrame: A dataframe representation of this QEIAMatrix object
        """
        row = {}
        
        for option in self.options:
            row[option] = self.options[option].getPriorityModifiers()

        return pd.DataFrame.from_dict(row)
