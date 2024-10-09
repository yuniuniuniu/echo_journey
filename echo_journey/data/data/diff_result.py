from dataclasses import dataclass

from data.utils import get_latest_commit_id


@dataclass
class DiffResult:
    name: str
    branch: str
    assistant_version: str
    cur_history_version: str
    diff_name: str
    diff_branch: str
    diff_assistant_version: str
    diff_history_version: str
    diff_url: str
    diff_link: str
    diff_text: str

    def to_table(self):
        return [
            self.name + " " + self.branch + " " + self.assistant_version,
            self.cur_history_version,
            self.diff_name + " " + self.diff_branch + " " + self.diff_assistant_version,
            self.diff_history_version,
            self.diff_link,
        ]

    def to_string(self):
        return f"{self.name}--{self.branch}--{self.assistant_version}--{self.cur_history_version} to {self.diff_name}--{self.diff_branch}--{self.diff_assistant_version}--{self.diff_history_version}"

    @classmethod
    def build_from_assistant(
        cls, context, diff_context, diff_history_version, diff_url, diff_text
    ):
        diff_result = DiffResult(
            name=context.assistant_name,
            branch=context.branch,
            assistant_version=context.assistant_version,
            cur_history_version=get_latest_commit_id(
                context.assistant_meta_store_root()
            ),
            diff_name=diff_context.assistant_name,
            diff_branch=diff_context.branch,
            diff_assistant_version=diff_context.assistant_version,
            diff_history_version=diff_history_version,
            diff_url=diff_url,
            diff_link=f"""<a href="{diff_url}" target="_blank">查看diff结果</a>""",
            diff_text=diff_text,
        )
        return diff_result

    @classmethod
    def build_from_orchestrator(
        cls, context, diff_context, diff_history_version, diff_url, diff_text
    ):
        diff_result = DiffResult(
            name=context.orchest_type,
            branch=context.branch,
            assistant_version=context.name,
            cur_history_version=get_latest_commit_id(context.store_root()),
            diff_name=diff_context.orchest_type,
            diff_branch=diff_context.branch,
            diff_assistant_version=diff_context.name,
            diff_history_version=diff_history_version,
            diff_url=diff_url,
            diff_link=f"""<a href="{diff_url}" target="_blank">查看diff结果</a>""",
            diff_text=diff_text,
        )
        return diff_result
