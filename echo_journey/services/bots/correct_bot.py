from echo_journey.data.whole_context import WholeContext

class CorrectBot():
    def __init__(self):
        self.context = WholeContext.generate_context_by_yaml("echo_journey/services/bots/meta/correct.yaml", "correct_bot")
        
    async def get_correct_result(self, expected_messages, messages):
        format_dict = self.format_correct_bot_input(expected_messages, messages)
        user_msg = self.context.cur_visible_assistant.content.user_prompt_prefix.format(**format_dict)
        self.context.add_user_msg_to_cur({"role": "user", "content": user_msg})
        result =  await self.context.execute()
        suggestions = ""
        for suggestion in result["suggestion_list"]:
            if not suggestion or suggestion == "null":
                continue
            else:
                suggestions += suggestion + "\n"
        return suggestions, int(result["score"])
    
    def format_correct_bot_input(self, expected_messages, messages):
        format_dict = {}
        expected_sentence = ""
        for expected_message in expected_messages:
            expected_sentence += expected_message.word
            expected_sentence += expected_message.initial_consonant
            expected_sentence += expected_message.vowels
            expected_sentence += str(expected_message.tone)
            
        sentence = ""
        for message in messages:
            sentence += message.word
            sentence += message.initial_consonant
            sentence += message.vowels
            sentence += str(message.tone)
        format_dict["expected_sentence"] = expected_sentence
        format_dict["sentence"] = sentence
        return format_dict