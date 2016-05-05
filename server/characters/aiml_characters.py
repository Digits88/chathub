import os
import yaml
import logging
from character import AIMLCharacter

CWD = os.path.dirname(os.path.realpath(__file__))

logger = logging.getLogger('hr.chathub.characters.aiml_characters')

def load_aiml_character(character_yaml):
    def abs_path(p):
        if p.startswith('/'):
            return p
        if p.startswith('~'):
            return os.path.expanduser(p)
        return os.path.join(root_dir, p)

    with open(character_yaml) as f:
        spec = yaml.load(f)
        try:
            root_dir = os.path.dirname(os.path.realpath(character_yaml))
            character = AIMLCharacter(spec['id'], spec['name'])
            if 'property_file' in spec:
                character.set_property_file(abs_path(spec['property_file']))
            if 'level' in spec:
                character.level = int(spec['level'])
            if 'aiml' in spec:
                aiml_files = [abs_path(f) for f in spec['aiml']]
                character.load_aiml_files(character.kernel, aiml_files)
            if 'weight' in spec:
                character.weight = float(spec['weight'])
        except KeyError as ex:
            logger.error(ex)

    return character

characters = []

for yaml_file in os.listdir(CWD):
    if yaml_file.endswith('.yaml'):
        characters.append(load_aiml_character(os.path.join(CWD, yaml_file)))
