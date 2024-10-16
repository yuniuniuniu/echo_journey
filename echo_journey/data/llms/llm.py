import abc

class LLM(abc.ABC):

    @abc.abstractmethod
    def acommit(self, X, y):
        pass

    @abc.abstractmethod
    def commit(self, X, y):
        pass

    @abc.abstractmethod
    def get_config_name(self):
        pass


def merge_deltas(original, delta):
    """
    Pushes the delta into the original and returns that.

    Great for reconstructing OpenAI streaming responses -> complete message objects.
    """

    for key, value in delta.items():
        if isinstance(value, dict):
            if key not in original:
                original[key] = value
            else:
                merge_deltas(original[key], value)
        else:
            if key in original:
                original[key] += value
            else:
                original[key] = value
    return original
