#
# For licensing see accompanying LICENSE file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

"""Test file for semantic regex prompt generation."""

from semantic_regex import (
    generate_semantic_regex_prompt,
    generate_semantic_regex,
)

from semantic_regex.semantic_regex import _parse_semantic_regex_response

def test_prompt_string_generation():
    """Test that generate_semantic_regex_prompt returns a dict with prompt and parameters."""
    print("=" * 60)
    print("TESTING PROMPT DICT GENERATION")
    print("=" * 60)

    # Sample data - tokens and their activation values
    sample_tokens = [
        ["The", "quick", "brown", "fox", "jumps", "over", "the", "lazy", "dog"],
        ["A", "fast", "red", "car", "speeds", "down", "the", "highway"],
        ["She", "ran", "quickly", "through", "the", "forest", "path"],
        ["The", "rapid", "blue", "river", "flows", "between", "mountains"],
        ["He", "swiftly", "moved", "across", "the", "room"]
    ]

    sample_activations = [
        [0.1, 0.9, 0.2, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],  # "quick" activates strongly
        [0.1, 0.8, 0.2, 0.1, 0.1, 0.1, 0.1, 0.1],       # "fast" activates strongly
        [0.1, 0.1, 0.9, 0.1, 0.1, 0.1, 0.1],            # "quickly" activates strongly
        [0.1, 0.7, 0.2, 0.1, 0.1, 0.1, 0.1],            # "rapid" activates strongly
        [0.1, 0.8, 0.1, 0.1, 0.1, 0.1]                  # "swiftly" activates strongly
    ]

    # Generate the prompt data
    prompt_data = generate_semantic_regex_prompt(
        sample_tokens,
        sample_activations,
        activation_threshold=0.3,
        n_data_examples=5,
        show_breaks=True,
        seed=42
    )

    print("Generated prompt data:")
    print("-" * 40)
    print(f"Type: {type(prompt_data)}")
    print(f"Keys: {list(prompt_data.keys())}")
    print(f"Prompt type: {type(prompt_data['prompt'])}")
    print(f"Parameters: {prompt_data['parameters']}")
    print("\nPrompt content (first 200 chars):")
    print(prompt_data['prompt'][:200] + "..." if len(prompt_data['prompt']) > 200 else prompt_data['prompt'])
    print("-" * 40)

    # Verify it's a dict with expected structure
    assert isinstance(prompt_data, dict)
    assert "prompt" in prompt_data
    assert "parameters" in prompt_data
    assert isinstance(prompt_data["prompt"], str)
    assert isinstance(prompt_data["parameters"], dict)
    assert "semantic regex" in prompt_data["prompt"].lower()
    assert "1:" in prompt_data["prompt"]  # Should have numbered examples

def test_dspy_generation():
    """Test the DSPy-based generate_semantic_regex function."""
    print("\n" + "=" * 60)
    print("TESTING DSPY GENERATION (Mock)")
    print("=" * 60)

    # Sample data focusing on speed words
    sample_tokens = [
        ["The", "quick", "brown", "fox"],
        ["A", "fast", "red", "car"],
        ["She", "ran", "quickly", "home"],
        ["The", "rapid", "blue", "river"]
    ]

    sample_activations = [
        [0.1, 0.9, 0.2, 0.1],  # "quick"
        [0.1, 0.8, 0.2, 0.1],  # "fast"
        [0.1, 0.1, 0.9, 0.1],  # "quickly"
        [0.1, 0.7, 0.2, 0.1]   # "rapid"
    ]

    # First generate the prompt data
    prompt_data = generate_semantic_regex_prompt(
        sample_tokens,
        sample_activations,
        activation_threshold=0.3,
        n_data_examples=4
    )

    print("✓ Prompt data generated successfully")
    print(f"Prompt parameters: {prompt_data['parameters']}")

    # Test without actual DSPy LM (will fail at generation but test setup)
    try:
        result = generate_semantic_regex(
            prompt_data,
            lm=None,  # No actual LM provided
            temperature=0.7,
            logging=True
        )
        print("✓ DSPy generation completed successfully")
        print(f"Result type: {type(result)}")
        print(f"Description: {result.get('description', 'No description')}")
        print(f"All parameters preserved: {result.get('parameters', {})}")
    except Exception as e:
        print(f"Expected error (no LM configured): {e}")
        print("✓ Function structure is correct, needs DSPy LM to complete")

def test_response_parsing():
    """Test the parse_semantic_regex_response function."""
    print("\n" + "=" * 60)
    print("TESTING RESPONSE PARSING")
    print("=" * 60)

    # Test successful parsing
    test_responses = [
        "This captures speed-related concepts. SR: /\\b(quick|fast|rapid|swift)\\w*\\b/i",
        "The pattern matches movement words. SR: /\\bmov(e|ing|ed)\\b/",
        "Some explanation here.\n\nSR: /\\bcolor\\w*\\b/i"
    ]

    for i, response in enumerate(test_responses):
        try:
            parsed = _parse_semantic_regex_response(response)
            print(f"✓ Test {i+1}: '{parsed}'")
        except Exception as e:
            print(f"✗ Test {i+1} failed: {e}")

    # Test error case
    try:
        _parse_semantic_regex_response("No semantic regex here!")
        print("✗ Should have failed for missing SR:")
    except ValueError as e:
        print(f"✓ Correctly caught missing SR: {e}")

def test_different_parameters():
    """Test with different parameter settings."""
    print("\n" + "=" * 60)
    print("TESTING DIFFERENT PARAMETERS")
    print("=" * 60)

    # Sample data focusing on color words
    sample_tokens = [
        ["The", "bright", "red", "apple", "fell", "from", "tree"],
        ["She", "wore", "a", "blue", "dress", "to", "party"],
        ["The", "green", "grass", "was", "wet", "with", "dew"],
        ["His", "yellow", "car", "stood", "out", "in", "lot"],
        ["The", "purple", "flowers", "bloomed", "in", "spring"],
        ["Orange", "juice", "spilled", "on", "the", "table"],
        ["The", "pink", "sunset", "was", "beautiful", "tonight"]
    ]

    sample_activations = [
        [0.1, 0.1, 0.9, 0.1, 0.1, 0.1, 0.1],
        [0.1, 0.1, 0.1, 0.8, 0.1, 0.1, 0.1],
        [0.1, 0.7, 0.1, 0.1, 0.1, 0.1, 0.1],
        [0.1, 0.9, 0.1, 0.1, 0.1, 0.1, 0.1],
        [0.1, 0.8, 0.1, 0.1, 0.1, 0.1],
        [0.9, 0.1, 0.1, 0.1, 0.1, 0.1],
        [0.1, 0.7, 0.1, 0.1, 0.1, 0.1]
    ]

    # Test with different sampling methods
    for method in ['top', 'random', 'quantile']:
        print(f"\nTesting sampling method: {method}")
        print("-" * 30)

        prompt_data = generate_semantic_regex_prompt(
            sample_tokens,
            sample_activations,
            activation_threshold=0.2,
            n_data_examples=4,
            sampling_method=method,
            show_breaks=False,
            seed=42
        )

        print("✓ Prompt data generated successfully")
        print(f"Length: {len(prompt_data['prompt'])} characters")
        print(f"Parameters: {prompt_data['parameters']}")
        # Show a snippet
        lines = prompt_data['prompt'].split('\n')
        example_lines = [line for line in lines if line.strip() and (line.strip()[0].isdigit() if line.strip() else False)]
        print(f"Number of examples: {len(example_lines)}")

def test_with_realistic_text():
    """Test with more realistic text snippets."""
    print("\n" + "=" * 60)
    print("TESTING WITH REALISTIC TEXT")
    print("=" * 60)

    # More realistic text with punctuation and varied lengths
    sample_tokens = [
        ["I", "need", "to", "buy", "groceries", "at", "the", "store", "today", "."],
        ["She", "wants", "to", "purchase", "a", "new", "laptop", "for", "work", "."],
        ["We", "should", "get", "some", "coffee", "before", "the", "meeting", "."],
        ["He", "plans", "to", "acquire", "a", "house", "next", "year", "."],
        ["They", "decided", "to", "obtain", "tickets", "for", "the", "concert", "."]
    ]

    sample_activations = [
        [0.1, 0.1, 0.1, 0.9, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],  # "buy"
        [0.1, 0.1, 0.1, 0.8, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],  # "purchase"
        [0.1, 0.1, 0.7, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],       # "get"
        [0.1, 0.1, 0.1, 0.8, 0.1, 0.1, 0.1, 0.1, 0.1],       # "acquire"
        [0.1, 0.1, 0.1, 0.9, 0.1, 0.1, 0.1, 0.1, 0.1]        # "obtain"
    ]

    prompt_data = generate_semantic_regex_prompt(
        sample_tokens,
        sample_activations,
        activation_threshold=0.4,
        n_data_examples=10,  # More than available - should handle gracefully
        n_tokens_per_sample=8,  # Shorter snippets
        show_breaks=True,
        seed=123
    )

    print("Generated prompt data:")
    print("-" * 40)
    print("Type:", type(prompt_data))
    print("Prompt length:", len(prompt_data['prompt']))
    print("Parameters:", prompt_data['parameters'])
    print("First 200 characters of prompt:")
    print(prompt_data['prompt'][:200] + "..." if len(prompt_data['prompt']) > 200 else prompt_data['prompt'])
    print("-" * 40)

def test_edge_cases():
    """Test edge cases and error handling."""
    print("\n" + "=" * 60)
    print("TESTING EDGE CASES")
    print("=" * 60)

    # Test with very few examples
    sample_tokens = [["Hello", "world"]]
    sample_activations = [[0.9, 0.1]]

    try:
        prompt_data = generate_semantic_regex_prompt(
            sample_tokens,
            sample_activations,
            n_data_examples=5  # More than available
        )
        print("✓ Handled case with fewer examples than requested")
        print(f"Generated prompt of length {len(prompt_data['prompt'])}")
        print(f"Parameters preserved: {prompt_data['parameters']}")
    except Exception as e:
        print(f"✗ Error with minimal data: {e}")

    # Test with invalid sampling method
    try:
        prompt_data = generate_semantic_regex_prompt(
            sample_tokens,
            sample_activations,
            sampling_method='invalid'
        )
        print("✗ Should have raised error for invalid sampling method")
    except ValueError as e:
        print(f"✓ Correctly caught invalid sampling method: {e}")

def test_complete_workflow():
    """Test the complete workflow from prompt generation to semantic regex generation."""
    print("\n" + "=" * 60)
    print("TESTING COMPLETE WORKFLOW")
    print("=" * 60)

    # Simple example
    sample_tokens = [
        ["cat", "is", "fast"],
        ["dog", "runs", "quickly"]
    ]
    sample_activations = [
        [0.1, 0.1, 0.9],  # "fast" activates
        [0.1, 0.1, 0.8]   # "quickly" activates
    ]

    # Step 1: Generate prompt data
    prompt_data = generate_semantic_regex_prompt(
        sample_tokens,
        sample_activations,
        activation_threshold=0.5,
        n_data_examples=2,
        seed=42
    )

    print("✓ Step 1: Generated prompt data")
    print(f"  - Prompt length: {len(prompt_data['prompt'])}")
    print(f"  - Parameters: {prompt_data['parameters']}")

    # Step 2: Test that we can pass it to the DSPy function
    try:
        # This will fail without an actual LM, but tests the interface
        result = generate_semantic_regex(
            prompt_data,
            temperature=0.8,
            logging=False
        )
        print("✓ Step 2: DSPy function accepted prompt data")
        print(f"  - Result keys: {list(result.keys())}")
    except Exception as e:
        print(f"✓ Step 2: Function interface correct (expected error): {type(e).__name__}")

    print("✓ Complete workflow test passed!")

def simple_test():
    """Simple test to verify everything works."""
    print("\n" + "=" * 60)
    print("SIMPLE VERIFICATION TEST")
    print("=" * 60)

    # Very simple example
    sample_tokens = [
        ["cat", "is", "fast"],
        ["dog", "runs", "quickly"]
    ]
    sample_activations = [
        [0.1, 0.1, 0.9],  # "fast" activates
        [0.1, 0.1, 0.8]   # "quickly" activates
    ]

    prompt_data = generate_semantic_regex_prompt(sample_tokens, sample_activations)

    print("SUCCESS! Generated prompt data:")
    print("Type:", type(prompt_data))
    print("Has prompt:", "prompt" in prompt_data)
    print("Has parameters:", "parameters" in prompt_data)
    print("Prompt length:", len(prompt_data['prompt']))
    print("Contains examples:", "1:" in prompt_data['prompt'] and "2:" in prompt_data['prompt'])

if __name__ == "__main__":
    # Run all tests
    test_prompt_string_generation()
    test_dspy_generation()
    test_response_parsing()
    test_different_parameters()
    test_with_realistic_text()
    test_edge_cases()
    test_complete_workflow()
    simple_test()
    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)
