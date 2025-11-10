#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

# Prompt variables for eleuther_acts-top-20
# Taken from: https://github.com/EleutherAI/delphi/blob/main/delphi/explainers/default/prompts.py

SYSTEM = """You are a meticulous AI researcher conducting an important investigation into patterns found in language. Your task is to analyze text and provide an explanation that thoroughly encapsulates possible patterns found in it.
Guidelines:

You will be given a list of text examples on which special words are selected and between delimiters like <<this>>. If a sequence of consecutive tokens all are important, the entire sequence of tokens will be contained between delimiters <<just like this>>.

- Try to produce a concise final description. Simply describe the text latents that are common in the examples, and what patterns you found.
- If the examples are uninformative, you don't need to mention them. Don't focus on giving examples of important tokens, but try to summarize the patterns found in the examples.
- Do not mention the marker tokens (<< >>) in your explanation.
- Do not make lists of possible explanations. Keep your explanations short and concise.
- The last line of your response must be the formatted explanation, using [EXPLANATION]:
"""

EXAMPLE_1 = """
Example 1:  and he was <<over the moon>> to find
Example 2:  we'll be laughing <<till the cows come home>>! Pro
Example 3:  thought Scotland was boring, but really there's more <<than meets the eye>>! I'd
"""

EXAMPLE_1_EXPLANATION = """
[EXPLANATION]: Common idioms in text conveying positive sentiment.
"""

EXAMPLE_2 = """
Example 1:  a river is wide but the ocean is wid<<er>>. The ocean
Example 2:  every year you get tall<<er>>," she
Example 3:  the hole was small<<er>> but deep<<er>> than the
"""

EXAMPLE_2_EXPLANATION = """
[EXPLANATION]: The token "er" at the end of a comparative adjective describing size.
"""

EXAMPLE_3 = """
Example 1:  something happening inside my <<house>>", he
Example 2:  presumably was always contained in <<a box>>", according
Example 3:  people were coming into the <<smoking area>>".

However he
Example 4:  Patrick: "why are you getting in the << way?>>" Later,
"""

EXAMPLE_3_EXPLANATION = """
[EXPLANATION]: Nouns representing a distinct objects that contains something, sometimes preciding a quotation mark.
"""

EXAMPLES = [
    EXAMPLE_1,
    EXAMPLE_2,
    EXAMPLE_3,
]

EXAMPLE_EXPLANATIONS = [
    EXAMPLE_1_EXPLANATION,
    EXAMPLE_2_EXPLANATION,
    EXAMPLE_3_EXPLANATION,
]