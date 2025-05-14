import os
from multiprocessing import Process
from pathlib import Path


def fill_characters():
    result = {}

    for character_folder in os.scandir(WORK_DIR / 'characters'):
        if character_folder.is_dir():
            character_name = character_folder.name

            with open(WORK_DIR / f'characters/{character_folder.name}/answer_prompt.txt', 'r') as file:
                answer_prompt = file.read()

            with open(WORK_DIR / f'characters/{character_folder.name}/outreach_prompt.txt', 'r') as file:
                outreach_prompt = file.read()

            result[character_name] = {
                'answer_prompt': answer_prompt,
                'outreach_prompt': outreach_prompt
            }

    return result


WORK_DIR = Path(__file__).resolve().parent.parent
PROCESSES: dict[int, Process] = {}
CHARACTERS = fill_characters()
