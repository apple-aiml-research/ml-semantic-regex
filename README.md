# Semantic Regexes

Semantic regexes are an automated interpretability method that describe LLM features using a structured language. Semantic regexes provide accurate, concise, and consistent feature descriptions that help humans build mental models of feature activations.

This repo contains a package to generate your own semantic regexes, pre-computed semantic regexes and evaluation scores, and an interactive [viewer](https://apple.github.io/ml-semantic-regex) to explore results.

<!-- ![Overview of Semantic Regex](img/teaser.png) -->

This code accompanies the research paper:

**Semantic Regexes: Auto-Interpreting LLM Features with a Structured Language**\
[Angie Boggust](https://angieboggust.com), [Donghao Ren](https://donghaoren.org), [Yannick Assogba](https://clome.info), [Dominik Moritz](https://www.domoritz.de), [Arvind Satyanarayan](https://arvindsatya.com), [Fred Hohman](https://fredhohman.com)\
arXiv, 2025.\
[Paper](https://arxiv.org/abs/2510.06378), [GitHub](https://github.com/apple/ml-semantic-regex), [Python package](https://pypi.org/project/semantic-regex), [Viewer](https://apple.github.io/ml-semantic-regex)

## Repo Structure

* [`experiments`](experiments): the code to replicable the experimental results from the paper.
* [`semantic-regex`](semantic-regex): a lightweight Python package to generate semantic regexes.
* [`viewer`](viewer): a web-based viewer to browse experimental results from the paper.

## Contributing

When making contributions, refer to the [`CONTRIBUTING`](CONTRIBUTING.md) guidelines and read the [`CODE OF CONDUCT`](CODE_OF_CONDUCT.md).

## BibTeX

To cite our paper, please use:

```bibtex
@article{boggust2025semantic,
    title={{Semantic Regexes: Auto-Interpreting LLM Features with a Structured Language}},
    author={Boggust, Arvind and Ren, Donghao and Assogba, Yannick and Moritz, Dominik, and Satyanarayan, Arvind and Hohman, Fred},
    journal={arXiv preprint arXiv:2510.06378},
    year={2025}
}
```

## License

This code is released under the [`LICENSE`](LICENSE) terms.

