This is a premature question-answering platform. The goal is to provide a ROS independent, scalable, platform-independent QA.

## Install Dependencies

```shell
[sudo] pip install Flask
[sudo] apt-get install python-yaml
```

## Run Server
```shell
cd server
python run.py [port]
```

The default port is 8001.

## Load Characters
The default path of the characters is the current characters directory.
But you can overwrite it by setting the environment variable `HR_CHARACTER_PATH`. For example

`$ HR_CHARACTER_PATH=/path/to/characters1,/path/to/characters2 python run.py`

### How is the Character Loaded
It loads every python module except `__init__.py` in every character path in `HR_CHARACTER_PATH`, and finds the global `characters` in this module.
Then it appends the characters to its character list `CHARACTERS`. See `characters/__init__.py`

## Docker

### Run Docker Server

```shell
./run-server.sh
```

### Build Docker Image

```shell
./build-docker-image.sh
```


## Define a Character
### Define an AIML character

```python
from character import AIMLCharacter
# id is an unique global string that refers to this character. name is the character name.
character = AIMLCharacter(id, name)
character.load_aiml_files([file1, file2])
character.set_property_file(abc.properties) # Set the key,value properties.
```

Once it's done, you need to put this object to global variable `characters` so the server can find and load it.

There is a convienent way to load the definition from yaml file.

The yaml file format is like this. The path is relative to the yaml file itself.
```yaml
id:
    sophia
name:
    sophia
property_file:
    sophia.properties
aiml:
    - ../../futurist_aiml/agians.aiml
    - ../../futurist_aiml/aiexistsans.aiml
    - ...
```
### Define a third party character
For example, if you want to integrate third party chatbot. What you can do is

1. Create a sub-class that inherits `Character` class.
2. Implement `respond` method. The return value is a dict that has these keys `response`, `botid`, `botname`.

Here is a dummy example.
```python
from character import Character
class DummyCharacter(Character):
  def respond(self, question, session=None):
    ret['response'] = "Hi there"
    ret['botid'] = self.id
    ret['botname'] = self.name
    return ret

characters = [DummyCharacter('34g634', 'dummy')]
```
Then you can put this module to the character path so when the server is started, the character can be found and loaded.

## Client for testing
There is a client for testing purpose. It's `client.py`.

Run `$ python client.py`, then you can ask questions and get the answers.

```
$ python client.py
[me]: help

Documented commands (type help <topic>):
========================================
select conn  help  list  q

[me]: list
[sophia]
generic
[me]: select han
Set chatbot to han
[me]: what is your name
quant_han[by han]: I'm called Han.
```

## Chatbot Server API

### List characters

```
GET /v1/chatbots
params: Auth
```

```
For example
http://host:port/v1/chatbots?Auth=AAAAB3NzaC

{"response": ["sophia", "pkd", "han", "generic"], "ret": 0}
```

### Chat

```
GET /v1/chat
params: botid, question, session, Auth
```

```
For example
http://host:port/v1/chat?question=hello&botid=sophia&session=0&Auth=AAAAB3NzaC

{"response": {"emotion": "", "text": "Hi. What seems to be your problem ?",
"botid": "sophia", "botname": "sophia"}, "ret": 0}
```
