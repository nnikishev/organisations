from enum import Enum


class SortOrder(str, Enum):
    DESC = "DESC"
    ASC = "ASC"

    def __str__(self):
        return self.value
