from .assistant_content import AssistantContent

class AssistantMeta:
    def __init__(
        self,
        assistant_name,
        content=AssistantContent({}),
        id=None,
    ):
        self.assistant_name: str = assistant_name
        self.content: AssistantContent = content
        self.id = (
            id if id else (self.assistant_name)
        )

    def get_id(self):
        return self.id