from characters import CHARACTERS
import json
import logging
import requests
from collections import defaultdict
import random
import os
import sys
import datetime as dt
reload(sys)
sys.setdefaultencoding('utf-8')
import atexit

SUCCESS=0
WRONG_CHARACTER_NAME=1
NO_PATTERN_MATCH=2

useSOLR = True
SESSION_TIMEOUT=300
CWD = os.path.dirname(os.path.realpath(__file__))

logger = logging.getLogger('hr.chathub.server.chatbot')

def get_character(id, create=False):
    for character in CHARACTERS:
        if character.id == id:
            return character

def is_local_character(character):
    return True

def get_characters_by_name(name, local=True):
    characters = [c for c in CHARACTERS if c.name == name]
    if local:
        characters = [c for c in characters if is_local_character(c)]
    return characters

def list_character(id=None):
    if id is not None:
        responding_characters = get_responding_characters(id)
        return [(c.id, c.weight) for c in responding_characters]
    else:
        return [(c.id, c.weight) for c in CHARACTERS]

def set_weights(id, weights):
    try:
        weights = [float(w.strip()) for w in weights.split(',')]
    except Exception:
        return False, "Wrong weight format"
    responding_characters = get_responding_characters(id)
    if len(weights) != len(responding_characters):
        return False, "Number of weights doesn't match number of tiers {}".format(weights)
    for c, weight in zip(responding_characters, weights):
        c.weight = weight
    return True, "Weights are updated"

def update_character(id, csv_version=None):
    character = get_character(id)
    if not character:
        return False, "Character {} is not found".format(id)
    if not is_local_character(character):
        try:
            character.load_csv_files(csv_version)
        except Exception as ex:
            logger.error(ex)
            return False, "Update {} failed\n{}".format(id, ex)
        return True, "{} is updated".format(id)
    else:
        return False, "Character {} doesn't support update".format(id)
    return False

def load_sheet_keys(id, sheet_keys):
    character = get_character(id, True)
    if not character:
        return False, "Character {} is not found".format(id)
    if not sheet_keys:
        return False, "No sheet key is set"
    if not is_local_character(character):
        return character.load_sheet_keys(sheet_keys)
    else:
        return False, "Character doesn't support sheet keys"
    return False, "Unknown error"

def commit_character(id):
    character = get_character(id)
    if not character:
        return False, "Character {} is not found".format(id)
    if not is_local_character(character):
        return character.commit()
    else:
        return False, "Character {} doesn't support committing".format(character)

from response_cache import ResponseCache
response_caches = dict() # session -> response cache dict
MAX_CHAT_TRIES = 5
def _ask_characters(characters, question, lang, session):
    global response_caches
    chat_tries = 0
    if session not in response_caches:
        response_caches[session] = ResponseCache()
    cache = response_caches.get(session)

    weights = [c.weight for c in characters]
    _question = question.lower().strip()
    _question = ' '.join(_question.split()) # remove consecutive spaces
    num_tier = len(characters)
    while chat_tries < MAX_CHAT_TRIES:
        chat_tries += 1
        _responses = [c.respond(_question, lang, session) for c in characters]
        for r in _responses:
            assert isinstance(r, dict), "Response must be a dict"
        answers = [r.get('text', '') for r in _responses]

        # Each tier has weight*100% chance to be selected.
        # If the chance goes to the last tier, it will be selected anyway.
        for idx, answer in enumerate(answers):
            if not answer:
                continue
            if random.random()<weights[idx]:
                if cache.check(_question, answer):
                    cache.add(_question, answer)
                    return _responses[idx]

    c = get_character('sophia_pickup')
    if c is not None:
        chat_tries = 0
        while chat_tries < MAX_CHAT_TRIES:
            chat_tries += 1
            if random.random() > 0.7:
                _response = c.respond('early random pickup', lang, session)
                _response['state'] = 'early random pickup'
            else:
                _response = c.respond('mid random pickup', lang, session)
                _response['state'] = 'mid random pickup'
            answer = _response.get('text', '')
            if cache.check(_question, answer):
                cache.add(_question, answer)
                return _response

    _response = {}
    answer = "Sorry, I can't answer that"
    _response['text'] = answer
    _response['botid'] = "dummy"
    _response['botname'] = "dummy"
    cache.add(_question, answer)
    return _response

def get_responding_characters(id):
    character = get_character(id)
    if not character:
        return []
    botname = character.name

    # current character > local character with the same name > solr > generic
    responding_characters = get_characters_by_name(botname, local=True)
    if character in responding_characters:
        responding_characters.remove(character)
    responding_characters = sorted(responding_characters, key=lambda x: x.level)
    responding_characters.insert(0, character)

    if useSOLR:
        solr_character = get_character('solr_bot')
        if solr_character:
            responding_characters.append(solr_character)
        else:
            logger.warn("Solr character is not found")

    generic = get_character('generic')
    if generic:
        generic.set_properties(character.get_properties())
        responding_characters.append(generic)
    else:
        logger.warn("Generic character is not found")

    return responding_characters

def ask(id, question, lang, session=None):
    """
    return (response dict, return code)
    """
    global response_caches

    # Reset cache
    cache = response_caches.get(session)
    if cache is not None:
        if question and question.lower().strip() in ['hi', 'hello']:
            logger.info("Cache is cleaned by hi")
            cache.clean()
        if cache.last_time and (dt.datetime.now()-cache.last_time)>dt.timedelta(seconds=SESSION_TIMEOUT):
            logger.info("Cache is cleaned by timer")
            cache.clean()

    response = {'text': '', 'emotion': '', 'botid': '', 'botname': ''}

    responding_characters = get_responding_characters(id)
    if not responding_characters:
        return response, WRONG_CHARACTER_NAME

    logger.info("Responding characters {}".format(responding_characters))
    _response = _ask_characters(responding_characters, question, lang, session)

    for c in responding_characters:
        try:
            c.check_reset_topic(session)
        except Exception:
            continue

    if _response is not None:
        response.update(_response)
        logger.info("Ask {}, response {}".format(question, response))
        return response, SUCCESS
    else:
        return response, NO_PATTERN_MATCH

def dump_history():
    global response_caches
    for session, cache in response_caches.iteritems():
        dirname = os.path.expanduser('~/.hr/chatbot/history')
        if not os.path.isdir(dirname):
            os.makedirs(dirname)
        fname = os.path.join(dirname, '{}.csv'.format(session))
        cache.dump(fname)
atexit.register(dump_history)

if __name__ == '__main__':
    for character in CHARACTERS:
        print ask(character.id, 'what is your name')

