#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

# Prompt variables for semantic regex description generation

SEMANTIC_REGEX_DESCRIPTION = """A Semantic Regex is a structured pattern composed of:
* [:symbol X:] - matches an exact phrase X (e.g., [:symbol running:] matches "I am<< running>>" and "<< running>> faster").
* [:lexeme X:] - matches a phrase X and its syntactic variants (e.g., [:lexeme run:] matches "she<< ran>>", "it's<< running>> quickly").
* [:field X:] - matches a phrase X and its semantic variants (e.g., [:field run:] matches "out for a << jog>>" and "<< sprint>> for gold").
X can be a subword (e.g., ing), word (e.g., running), or phrase (e.g., running tempo).
These components can be combined to match more complex patterns:
* S1 S2 - matches a sequence where S1 is followed by S2 (e.g., [:symbol run:] [:lexeme fast:] matches "I<< run fast>>" and "they<< run faster>>").
* S1|S2 - matches either S1 or S2 (e.g., [:symbol run:]|[:symbol walk:] matches "I<< run>>" and "I<< walk>>").
* S? - matches S or nothing (e.g., [:lexeme run:] [:symbol very:]? [:symbol fast:] matches "I am<< running fast>>" and "I<< run very fast>>").
* @{:context C:}(S) - matches S that only activates in the context C (e.g., @{:context political:}([:lexeme run:]) matches "she<< ran>> for office" and "<<running>> for govenor" but not "I<< run>> marathons").
"""

SYSTEM = """
You are interpreting the role of LLM features. Your task it to describe patterns across activating text examples.

Input:
You will be given a list of text examples.
Activating phrases in each example are highlighted between delimiters like<< this and that>>.

Output:
You will output a **Semantic Regex** that describes patterns across the text examples.
{{SEMANTIC_REGEX_DESCRIPTION}}

Instructions:
1. Look at the text examples to identify patterns that occur across **all** examples.
2. First, look for patterns within the << >> delimiters.
    1. If you find an exact phrase, use a [:symbol X:].
    2. If you find a phrase and its syntactic variants, use a [:lexeme X:].
    3. If you find a phrase and its semantic variants, use a [:field X:].
    4. Create a Semantic Regex (S) with the fewest components that precisely describes the pattern.
3. Next, look for patterns in the examples' topics.
    1. If all examples are related to the same topic (C) AND the topic is not redundant with the current Semantic Regex (S), use a @{:context C:}(S) modifier.
4. Output the simplest and most concise Semantic Regex that precisely describes the patterns across all examples.
5. Do not includer the delimiters tokens (<< >>) in your Semantic Regex.
6. Output a short explanation followed by "SR: " and then the Semantic Regex
"""

SYSTEM = SYSTEM.replace("{{SEMANTIC_REGEX_DESCRIPTION}}", SEMANTIC_REGEX_DESCRIPTION)

# gpt2-small 8-res_mid_128k-oai 1638
EXAMPLE_1_INPUT = """
1: ax=[figg.add_subplot(2,1,k+)<< for>> k in xrange(2)]
2: p = 0<< for>> q in qlist: pprev = p
3: << for>> lam, prob in suite.Items():
"""
EXAMPLE_1_EXPLANATION = """The phrase 'for' activates only in the context of coding. SR: """
EXAMPLE_1_OUTPUT = """ @{:context coding:}([:symbol for:])"""


# gpt-2-small
EXAMPLE_2_INPUT = """
1: extradition legislation<< prohibits an individual from being sent back>>
2: << whether Israel can lift the collective protection of asylum seekers>>
3: << called on Dutch>> authorities<< to do more to protect human rights>> workers
"""
EXAMPLE_2_EXPLANATION = """The activating phrases and their surrounding phrases are all related to human rights legislation. SR: """
EXAMPLE_2_OUTPUT = """[:field human rights legislation:]"""

# gpt-2-small
EXAMPLE_3_INPUT = """
1: off the markets - 2<< times the size>> of India's
2: needed to meet demand - seven times<< the existing>> number
3: That's about three times<< the>> rate seen in Hawaii
"""
EXAMPLE_3_EXPLANATION = """The symbol 'the' activates when it is between a numerical multiplier and an amount of something. SR: """
EXAMPLE_3_OUTPUT = """[:field number:] [:symbol times the] [:field amount:]"""


# gpt-2-small 11-res-jb 12636
EXAMPLE_4_INPUT = """
1: sentenced to<< 30 years in>> prison
2: to<< ten months>> in prison suspended for<< 3 years>>
3: << 1 month>> behind bars but was ordered to
"""
EXAMPLE_4_EXPLANATION = """The activating phrases are durations of prison sentences. SR: """
EXAMPLE_4_OUTPUT = """@{:context prison sentences}([:field duration:])"""


def prompt():
    messages = [{"role": "system", "content": SYSTEM}]
    for i in range(1, 5):
        example_input = globals()[f"EXAMPLE_{i}_INPUT"]
        example_explanation = globals()[f"EXAMPLE_{i}_EXPLANATION"]
        example_output = globals()[f"EXAMPLE_{i}_OUTPUT"]
        messages.append({"role": "user", "content": example_input})
        messages.append({"role": "assistant", "content": example_explanation + example_output})
    return messages