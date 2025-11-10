#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

# Prompt for the detection/match scoring model
# Adapted from Eleuther's delphi package: https://github.com/EleutherAI/delphi/blob/main/delphi/scorers/classifier/prompts/detection_prompt.py
# Fixed tokenization anomalies and added semantic regex support

from typing import List
from prompts.methods import semantic_regex_prompt


SEMANTIC_REGEX_DESCRIPTION = semantic_regex_prompt.SEMANTIC_REGEX_DESCRIPTION

DETECTION_SYSTEM_PROMPT = """You are an intelligent and meticulous linguistics researcher.

You will be given a certain latent of text, such as "male pronouns" or "text with negative sentiment".

You will then be given several text examples. Your task is to determine which examples possess the latent.

For each example in turn, return 1 if the sentence is correctly labeled or 0 if the tokens are mislabeled. You must return your response in a valid Python list. Do not return anything else besides a Python list.
"""

DETECTION_SYSTEM_PROMPT_SR = f"""You are an intelligent and meticulous linguistics researcher.

You will be given a certain latent of text formatted as a Semantic Regex. {SEMANTIC_REGEX_DESCRIPTION}

You will then be given several text examples. Your task is to determine which examples possess the latent.

For each example in turn, return 1 if the sentence is correctly labeled or 0 if the tokens are mislabeled. You must return your response in a valid Python list. Do not return anything else besides a Python list.
"""

FUZZING_SYSTEM_PROMPT = """You are an intelligent and meticulous linguistics researcher.

You will be given a certain latent of text, such as "male pronouns" or "text with negative sentiment".

You will be given a few examples of text that contain this latent. Portions of the sentence which strongly represent this latent are between tokens << and >>.

Some examples might be mislabeled. Your task is to determine if every single token within << and >> is correctly labeled. Consider that all provided examples could be correct, none of the examples could be correct, or a mix. An example is only correct if every marked token is representative of the latent

For each example in turn, return 1 if the sentence is correctly labeled or 0 if the tokens are mislabeled. You must return your response in a valid Python list. Do not return anything else besides a Python list.
"""

FUZZING_SYSTEM_PROMPT_SR = f"""You are an intelligent and meticulous linguistics researcher.

You will be given a certain latent of text formatted as a Semantic Regex. {SEMANTIC_REGEX_DESCRIPTION}

You will be given a few examples of text that contain this latent. Portions of the sentence which strongly represent this latent are between tokens << and >>.

Some examples might be mislabeled. Your task is to determine if every single token within << and >> is correctly labeled. Consider that all provided examples could be correct, none of the examples could be correct, or a mix. An example is only correct if every marked token is representative of the latent

For each example in turn, return 1 if the sentence is correctly labeled or 0 if the tokens are mislabeled. You must return your response in a valid Python list. Do not return anything else besides a Python list.
"""

EXPLANATION_PREFIX = "Latent explanation:"
EXPLANATION_PREFIX_SR = "Semantic Regex explanation:"



# https://www.neuronpedia.org/gpt2-small/6-res-jb/6048
EXPLANATION_ONE = f"{EXPLANATION_PREFIX} Words related to American football positions, specifically the tight end position.\n"
EXPLANATION_ONE_SR = f"{EXPLANATION_PREFIX_SR} [:field American football position:]\n"
DETECTION_EXAMPLE_ONE = """
Test examples:

Example 0:<|endoftext|>Getty Images\n\nPatriots tight end Rob Gronkowski had his boss'
Example 1: names of months used in The Lord of the Rings:\n\n"...the
Example 2: Media Day 2015\n\nLSU defensive end Isaiah Washington (94) speaks to the
Example 3: shown, is generally not eligible for ads. For example, videos about recent tragedies,
Example 4: line, with the left side — namely tackle Byron Bell at tackle and guard Amini
"""
DETECTION_RESPONSE_ONE = "[1,0,1,0,1]" # This is different from the original. Example 2 should be a match and does activate the neuron.

FUZZING_EXAMPLE_ONE = """
Test examples:

Example 0:<|endoftext|>Getty Images\n\nPatriots<< tight end>> Rob Gronkowski had his boss'
Example 1: posted<|endoftext|>You should know this<< about>> offensive line coaches: they are large, demanding<< men>>
Example 2: Media Day 2015\n\nLSU<< defensive>> end Isaiah Washington (94) speaks<< to the>>
Example 3:<< running backs>>," he said. .. Defensive<< end>> Carroll Phillips is improving and his injury is
Example 4:<< line>>, with the left side — namely<< tackle>> Byron Bell at<< tackle>> and<< guard>> Amini
"""
FUZZING_RESPONSE_ONE = "[1,0,0,1,1]"



# https://www.neuronpedia.org/gpt2-small/6-res-jb/9396
EXPLANATION_TWO = f"{EXPLANATION_PREFIX} The word 'guys' in the phrase 'you guys'.\n"
EXPLANATION_TWO_SR = f'{EXPLANATION_PREFIX_SR} [:symbol you guys:]\n'
DETECTION_EXAMPLE_TWO = """
Test examples:

Example 0: enact an individual health insurance mandate?", Pelosi's response was to dismiss both
Example 1: birth control access<|endoftext|> but I assure you women in Kentucky aren't laughing as they struggle
Example 2: du Soleil Fall Protection Program with construction requirements that do not apply to theater settings because
Example 3: <|endoftext|> distasteful. Amidst the slime lurk bits of Schadenfre
Example 4: the<|endoftext|>ľI want to remind you all that 10 days ago (director Massimil
"""
DETECTION_RESPONSE_TWO = "[0,0,0,0,0]"

FUZZING_EXAMPLE_TWO = """
Test examples:

Example 0: if you are<< comfortable>> with it. You<< guys>> support me in many other ways already and
Example 1: birth control access<|endoftext|> but I assure you<< women>> in Kentucky aren't laughing as they struggle
Example 2:'s gig! I hope you guys<< LOVE>> her, and<< please>> be nice,
Example 3:American, told<< Hannity>> that "you<< guys>> are playing the race card."
Example 4:<< the>><|endoftext|>ľI want to<< remind>> you all that 10 days ago (director Massimil
"""
FUZZING_RESPONSE_TWO = "[0,0,0,0,0]"

# https://www.neuronpedia.org/gpt2-small/8-res-jb/12654
EXPLANATION_THREE = f"""{EXPLANATION_PREFIX} "of" before words that start with a capital letter.\n"""
EXPLANATION_THREE_SR = f'{EXPLANATION_PREFIX_SR} [:symbol of:] [:field Capitalized Word:]\n'
DETECTION_EXAMPLE_THREE = """
Test examples:

Example 0: climate, Tomblin's Chief of Staff Charlie Lorensen said.\n
Example 1: no wonderworking relics, no true Body and Blood of Christ, no true Baptism
Example 2: Deborah Sathe, Head of Talent Development and Production at Film London,
Example 3: It has been devised by Director of Public Prosecutions (DPP)
Example 4: and fair investigation not even include the Director of Athletics? Â· Finally, we believe the
"""
DETECTION_RESPONSE_THREE = "[1,1,1,1,1]"

FUZZING_EXAMPLE_THREE = """
Test examples:

Example 0: climate, Tomblin's Chief Chief<< of>> Staff Charlie Lorensen said.\n
Example 1: no wonderworking relics, no true Body and Blood<< of>> Christ, no true Baptism
Example 2: Deborah Sathe, Head<< of>> Talent Development and Production at Film London,
Example 3: It has been devised by Director<< of>> Public Prosecutions (DPP)
Example 4: and fair investigation not even include the Director<< of>> Athletics? Â· Finally, we believe the
"""
FUZZING_RESPONSE_THREE = "[1,1,1,1,1]"


EXPLANATIONS = [EXPLANATION_ONE, EXPLANATION_TWO, EXPLANATION_THREE]
EXPLANATIONS_SR = [EXPLANATION_ONE_SR, EXPLANATION_TWO_SR, EXPLANATION_THREE_SR]
DETECTION_FEW_SHOT_EXAMPLES = [DETECTION_EXAMPLE_ONE, DETECTION_EXAMPLE_TWO, DETECTION_EXAMPLE_THREE]
DETECTION_RESPONSES = [DETECTION_RESPONSE_ONE, DETECTION_RESPONSE_TWO, DETECTION_RESPONSE_THREE]
FUZZING_FEW_SHOT_EXAMPLES = [FUZZING_EXAMPLE_ONE, FUZZING_EXAMPLE_TWO, FUZZING_EXAMPLE_THREE]
FUZZING_RESPONSES = [FUZZING_RESPONSE_ONE, FUZZING_RESPONSE_TWO, FUZZING_RESPONSE_THREE]


GENERATION_PROMPT = """{explanation_prefix} {explanation}

Text examples:

{examples}
"""

def detection_prompt(examples: List[str], explanation: str, is_semantic_regex: bool) -> List[dict]:
    if is_semantic_regex:
        system_prompt = DETECTION_SYSTEM_PROMPT_SR
        few_shot_explanations = EXPLANATIONS_SR
        explanation_prefix = EXPLANATION_PREFIX_SR
    else:
        system_prompt = DETECTION_SYSTEM_PROMPT
        few_shot_explanations = EXPLANATIONS
        explanation_prefix = EXPLANATION_PREFIX

    messages = [{"role": "system", "content": system_prompt}]
    for i in range(len(DETECTION_FEW_SHOT_EXAMPLES)):
        few_shot_example = few_shot_explanations[i] + DETECTION_FEW_SHOT_EXAMPLES[i]
        messages.append({"role": "user", "content": few_shot_example})
        messages.append({"role": "assistant", "content": DETECTION_RESPONSES[i]})

    formatted_examples = '\n'.join([f"Example {i+1}: {ex.strip()}" for i, ex in enumerate(examples)])
    generation_prompt = GENERATION_PROMPT.format(
        explanation=explanation, examples=formatted_examples, explanation_prefix=explanation_prefix
    )
    messages.append({"role": "user", "content": generation_prompt})

    return messages


def fuzzing_prompt(examples: List[str], explanation: str, is_semantic_regex: bool) -> List[dict]:
    if is_semantic_regex:
        system_prompt = FUZZING_SYSTEM_PROMPT_SR
        few_shot_explanations = EXPLANATIONS_SR
        explanation_prefix = EXPLANATION_PREFIX_SR
    else:
        system_prompt = FUZZING_SYSTEM_PROMPT
        few_shot_explanations = EXPLANATIONS
        explanation_prefix = EXPLANATION_PREFIX

    messages = [{"role": "system", "content": system_prompt}]
    for i in range(len(FUZZING_FEW_SHOT_EXAMPLES)):
        few_shot_example = few_shot_explanations[i] + FUZZING_FEW_SHOT_EXAMPLES[i]
        messages.append({"role": "user", "content": few_shot_example})
        messages.append({"role": "assistant", "content": FUZZING_RESPONSES[i]})

    formatted_examples = '\n'.join([f"Example {i+1}: {ex.strip()}" for i, ex in enumerate(examples)])
    generation_prompt = GENERATION_PROMPT.format(
        explanation=explanation, examples=formatted_examples, explanation_prefix=explanation_prefix
    )
    messages.append({"role": "user", "content": generation_prompt})

    return messages

