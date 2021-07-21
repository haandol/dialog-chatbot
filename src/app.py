import logging
from dm import DialogManager, Intent
from nlu import NLU


class Chatbot(object):
    def __init__(self, start_message: str):
        nlu = NLU(max_length=64)
        self.dm = DialogManager(nlu=nlu)
        self.start_message = start_message
        self.user_intents = {}
        self.user_slot_values = {}

    def _init_user_session(self, uid):
        self.user_intents[uid] = None
        self.user_slot_values[uid] = {}

    def start(self, uid):
        self._init_user_session(uid)
        return self.start_message

    def _get_user_intent(self, uid, text) -> Intent:
        intent = self.user_intents[uid]
        if intent:
            return intent

        score, intent = self.dm.classify_intent(text)
        if not intent:
            return '처리할 수 없는 메시지 입니다.'
        logging.info(score, intent.name)
        self.user_intents[uid] = intent
        return intent
 
    def chat(self, uid, text) -> str:
        intent = self._get_user_intent(uid, text)
        is_fulfilled, new_slot_values, prompt = self.dm.fulfill_intent(
            intent, self.user_slot_values[uid], text
        )
        self.user_slot_values[uid].update(new_slot_values)
        logging.info(text, new_slot_values, self.user_slot_values[uid])
        response = prompt.format(**self.user_slot_values[uid])
        if is_fulfilled:
            self._init_user_session(uid)
        logging.info(is_fulfilled, new_slot_values, prompt)
        return response


if __name__ == '__main__':
    bot = Chatbot(start_message='안녕하세요, 꽃팔이 챗봇입니다.')
    uid = 'dongkyl'
    print(bot.start(uid))
    print(bot.chat(uid, '꽃을 사고 싶어'))
    print(bot.chat(uid, '장미'))
    print(bot.chat(uid, '오늘'))
    print(bot.chat(uid, '지금'))