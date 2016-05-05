import os
import sys
import aiml
import logging

logger = logging.getLogger('hr.chathub.server.character')

class Character(object):
    def __init__(self, id, name, level=99):
        self.id = id
        self.name = name
        self.level = level
        self.properties = {}
        self.weight = 1 # How likely its response is used. [0-1]

    def get_properties(self):
        return self.properties

    def set_properties(self, props):
        self.properties.update(props)

    def respond(self, question, lang, session=None):
        raise NotImplementedError

    def __repr__(self):
        return "<Character id: {}, name: {}, level: {}>".format(
            self.id, self.name, self.level)

class AIMLCharacter(Character):

    def __init__(self, id, name, level=99):
        super(AIMLCharacter, self).__init__(id, name, level)
        self.kernel = aiml.Kernel()
        self.aiml_files = []
        self.kernel.verbose(False)
        self.current_topic = ''
        self.counter = 0
        self.N = 10 # How many times of reponse on the same topic

    def load_aiml_files(self, kernel, aiml_files):
        for f in aiml_files:
            if '*' not in f and not os.path.isfile(f):
                logger.warn("[{}] {} is not found".format(self.id, f))
            errors = kernel.learn(f)
            if errors:
                raise Exception("Load {} error\n{}".format(
                    os.path.basename(f), errors[0][1]))
            logger.info("[{}] Load {}".format(self.id, f))
            if f not in self.aiml_files:
                self.aiml_files.append(f)

    def set_property_file(self, propname):
        try:
            with open(propname) as f:
                for line in f:
                    parts = line.split('=')
                    key = parts[0].strip()
                    value = parts[1].strip()
                    self.kernel.setBotPredicate(key, value)
                    self.properties[key] = value
                logger.info("[{}] Set properties file {}".format(self.id, propname))
        except Exception:
            logger.error("Couldn't open {}".format(propname))

    def set_properties(self, props):
        super(AIMLCharacter, self).set_properties(props)
        for key, value in self.properties.iteritems():
            self.kernel.setBotPredicate(key, value)

    def check_reset_topic(self, session):
        """If it's on the same topic for N round, then reset the topic"""
        topic = self.kernel.getPredicate('topic', session).strip()
        if not topic:
            return
        if topic == self.current_topic:
            self.counter += 1
        else:
            self.counter = 0
            self.current_topic = topic
            logger.info('Topic is changed to {}, reset counter'.format(topic))
        if self.counter >= self.N:
            self.counter = 0
            self.current_topic = ''
            self.kernel.setPredicate('topic', '')
            logger.info("Topic is reset")

    def respond(self, question, lang, session):
        ret = {}
        if lang != 'en':
            ret['text'] = ''
        else:
            ret['text'] = self.kernel.respond(question, session)
        ret['emotion'] = self.kernel.getPredicate('emotion', session)
        ret['botid'] = self.id
        ret['botname'] = self.name
        return ret

