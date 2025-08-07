from abc import ABC, abstractmethod


class Database(ABC):
    @abstractmethod
    def create(self):
        ...

    @abstractmethod
    def fetch_one(self):
        ...

    @abstractmethod
    def fetch_many(self):
        ...

    @abstractmethod
    def update(self):
        ...

    @abstractmethod
    def delete(self):
        ...
