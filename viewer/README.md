# Semantic Regex: Viewer

This package is an interactive viewer for the experiment's results. It's built as a standard SvelteKit project.

## Developing

Install dependencies with:

```bash
npm install
```

Next, you need to generate the data file that aggregates the results main results of the experiments.

```bash
uv run ./scripts/generate_static.py
```

This will generate a file named `artifacts_index.json` in `src/lib/assets/`.

Lastly, run the local viewer with:

```sh
npm run dev
```

## Building

To create a production build of the viewer:

```sh
npm run build
```

You can preview the production build with `npm run preview`.
