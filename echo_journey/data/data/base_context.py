import abc


class BaseContext(abc.ABC):
    @abc.abstractmethod
    def get_original_messages(self, X, y):
        pass

    @abc.abstractmethod
    def build_with(self, X, y):
        pass

    @abc.abstractmethod
    def travel_with_generator(self, X, y):
        pass

    @abc.abstractmethod
    def travel_with_callback(self, X, y):
        pass

    @abc.abstractmethod
    def deal_with_user_input(self, X, y):
        pass

    @abc.abstractmethod
    def get_visible_msgs(self, X, y):
        pass