import io
import yaml
import logging
from typing import Any, Callable
from sklearn.metrics.pairwise import cosine_similarity
from .slot_types import date_type_validator, time_type_validator

BUILTIN_SLOT_TYPES = {
    'date': date_type_validator,
    'time': time_type_validator,
}


def default_validator(values: list) -> Callable:
    def validator(v: Any):
        if v in values:
            return v
        else:
            return None
    return validator


class SlotType(object):
    def __init__(self, name: str, validate: Callable[[Any], bool]):
        self.name = name
        self.validate = validate

    @staticmethod
    def load_slot_types(path: str) -> dict:
        slot_types = {}
        for config in yaml.load(io.open(path, 'r'), Loader=yaml.FullLoader)['slot_types']:
            name = config['name']
            values = config['values']
            slot_types[name] = SlotType(name, default_validator(values))
        # built-in slot types
        for k, v in BUILTIN_SLOT_TYPES.items():
            slot_types[k] = SlotType(k, v)
        return slot_types


class Slot(object):
    def __init__(self, name: str, prompt: str, slot_type: SlotType):
        self.name = name
        self.prompt = prompt
        self.slot_type = slot_type

    def validate(self, v: Any) -> Any:
        return self.slot_type.validate(v)

    @staticmethod
    def load_slots(slot_types: dict, path: str) -> dict:
        slots = {}
        for config in yaml.load(io.open(path, 'r'), Loader=yaml.FullLoader)['slots']:
            intent_name = config['name']
            slots[intent_name] = []
            for slot_value in config['values']:
                name = slot_value['name']
                slot_type = slot_value['type']
                prompt = slot_value['prompt']
                slots[intent_name].append(Slot(name, prompt, slot_types[slot_type]))
        return slots


class Intent(object):
    def __init__(self, name: str, utterances: list, tokens, slots: list, confirm_prompt: str):
        self.name = name
        self.utterances = utterances
        self.confirm_prompt = confirm_prompt
        self.slots = slots
        self.tokens = tokens

    def next_prompt(self, user_slot_value: dict, text: str) -> tuple[bool, dict, str]:
        is_fulfilled = False
        slot_value = user_slot_value.copy()
        for i, slot in enumerate(self.slots):
            if slot.name not in slot_value:
                valid_value = slot.validate(text)
                if valid_value:
                    slot_value.update({slot.name: valid_value})
                    if i < len(self.slots) - 1:
                        return is_fulfilled, slot_value, self.slots[i+1].prompt
                else:
                    logging.warn(f'Invalid value for slot [{slot.name}]: {slot_value}, {text}')
                    return is_fulfilled, slot_value, slot.prompt
        else:
            is_fulfilled = True
        return is_fulfilled, slot_value, self.confirm_prompt

    def is_completed(self) -> bool:
        return all([slot.is_completed() for slot in self.slots])

    def similarity_score(self, tokens: list) -> float: 
        return max([
            cosine_similarity(tokens, intent_tokens)[0][0]
            for intent_tokens in self.tokens
        ])
 

    @staticmethod
    def load_intents(slots, path: str, tokenizer: Callable[[str], list]) -> list:
        intents = []
        for config in yaml.load(io.open(path, 'r'), Loader=yaml.FullLoader)['intents']:
            logging.info(config)
            name = config['name']
            utterances = config['utterances']
            confirm_prompt = config['confirm_prompt']

            tokens = [tokenizer(utterance) for utterance in utterances]
            intent = Intent(name, utterances=utterances, tokens=tokens,
                            slots=slots[name], confirm_prompt=confirm_prompt)
            intents.append(intent)
        return intents