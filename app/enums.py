from enum import Enum


class SortOrder(str, Enum):
    DESC = "DESC"
    ASC = "ASC"

    def __str__(self):
        return self.value


class StorageType(str, Enum):
    POSTGRES = "PostgreSQL"
    MONGO = "MongoDB"
    REDIS = "Redis"
    CLICKHOUSE = "ClickHouse"

    def __str__(self):
        return self.value
