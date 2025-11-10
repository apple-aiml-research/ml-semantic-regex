#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

# Data generation prompts for FADE evaluations
# Adapted from: https://github.com/brunibrun/FADE/blob/f929405e2350bd9a8098fd29a828bb497f085e09/fade/default_config.yaml#L41

from prompts.methods import semantic_regex_prompt



SEMANTIC_REGEX_DESCRIPTION = semantic_regex_prompt.SEMANTIC_REGEX_DESCRIPTION
SEMANTIC_REGEX_DESCRIPTION = SEMANTIC_REGEX_DESCRIPTION.replace('<<', '').replace('>>', '')


GENERATION_NATURAL_LANGUAGE_SYSTEM = """You are tasked with building a database of sequences that best represent a specific concept.
To create this, you will generate sequences that vary in style, tone, context, length, and structure, while maintaining a clear connection to the concept.
The concept does not need to be explicitly stated in each sequence, but each should relate meaningfully to it. Be creative and explore different ways to express the concept.

Here are examples of how different concepts might be expressed:

Concept: "German language" — Sequences might include German phrases, or sentences.
Concept: "Start of a Java Function" — Sequences might include Java code snippets defining a function.
Concept: "Irony" — Sequences might include ironic statements or expressions.

Provide your sequences as strings in a Python List format.

Example: ["This is a first example sequence.", "Second example sequence but it is much longer also there are somy typos in it. wjo told you that I can type?"]

Output only the Python List object, without any additional comments, symbols, or extraneous content."""



GENERATION_SEMANTIC_REGEX_SYSTEM = f"""You are tasked with building a database of sequences that best represent a specific concept.
To create this, you will generate sequences that vary in style, tone, context, length, and structure, while maintaining a clear connection to the concept.

The concept will be expressed as a Semantic Regex. {SEMANTIC_REGEX_DESCRIPTION}
Be creative and explore different ways to express the concept, while faithfully expressing the semantic regex.

Here are examples of how different concepts might be expressed:

Concept: "[:topic German Language:]" — Sequences might include German phrases, or sentences.
Concept: "@{{Java}}(functions)" — Sequences might include Java code snippets defining a function.
Concept: "[:lexeme irony:]" — Sequences that include the string 'irony', 'ironic', 'ironically', etc.

Provide your sequences as strings in a Python List format.

Example: ["This is a first example sequence.", "Second example sequence but it is much longer also there are somy typos in it. wjo told you that I can type?"]

Output only the Python List object, without any additional comments, symbols, or extraneous content."""



RATING_NATURAL_LANGUAGE_SYSTEM = """You are tasked with building a database of sequences that best represent a specific concept.
To create this, you will review a dataset of varying sequences and rate each one according to how much the concept is expressed.

For each sequence, assign a rating based on this scale:

0: The concept is not expressed.
1: The concept is vaguely or partially expressed.
2: The concept is clearly and unambiguously present.

Use conservative ratings. If uncertain, choose a lower rating to avoid including irrelevant sequences in your database.
If no sequence expresses the concept, rate all sequences as 0.

Each sequence is identified by a unique ID. Provide your ratings as a Python dictionary with sequence IDs as keys and their ratings as values.

Example Output: {{"14": 0, "15": 2, "20": 1, "27": 0}}

Output only the dictionary - no additional text, comments, or symbols."""



RATING_SEMANTIC_REGEX_SYSTEM = f"""You are tasked with building a database of sequences that best represent a specific concept.
To create this, you will review a dataset of varying sequences and rate each one according to how much the concept is expressed.

The concept will be written as a Semantic Regex. {SEMANTIC_REGEX_DESCRIPTION}

For each sequence, assign a rating based on this scale:

0: The concept is not expressed.
1: The concept is vaguely or partially expressed.
2: The concept is clearly and unambiguously present.

Use conservative ratings. If uncertain, choose a lower rating to avoid including irrelevant sequences in your database.
If no sequence expresses the concept, rate all sequences as 0.

Each sequence is identified by a unique ID. Provide your ratings as a Python dictionary with sequence IDs as keys and their ratings as values.

Example Output: {{"14": 0, "15": 2, "20": 1, "27": 0}}

Output only the dictionary - no additional text, comments, or symbols."""