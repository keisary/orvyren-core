# https://github.com/microsoft/graphrag

# microsoft/graphrag
URL: https://github.com/microsoft/graphrag

# microsoft/graphrag

A modular graph-based Retrieval-Augmented Generation (RAG) system

- Stars: 36324
- Forks: 3847
- Watchers: 36324
- Open issues: 58
- License: MIT License
- Homepage: https://microsoft.github.io/graphrag/
- Default branch: main
- Created: 2024-03-27T17:57:52Z

## Languages

- Dockerfile
- HTML
- Jinja
- Jupyter Notebook
- Python
- Shell
- TypeScript

## Topics

- gpt
- gpt-4
- gpt4
- graphrag
- llm
- llms
- rag

## Top Contributors

- AlonsoGuevara (144 contributions)
- natoverse (106 contributions)
- dworthen (44 contributions)
- dependabot[bot] (35 contributions)
- jgbradley1 (27 contributions)
- dayesouza (27 contributions)
- gaudyb (19 contributions)
- KennyZhang1 (11 contributions)
- darthtrevino (10 contributions)
- Copilot (9 contributions)

---

## README

# GraphRAG

> [!WARNING]
> GraphRAG is a research project that explores the functional use of graphs to form a targeted context for question answering. Since our first release in July 2024 the capabilities of frontier models have changed dramatically, and our portfolio of research projects has diversified to match. This project is largely in maintenance mode, and won't be accepting new PRs or implementing new features. We'll perform bug fixes and dependency updates as appropriate, particularly to address CVEs as they arise.

ð Microsoft Research Blog Post 
ð Read the docs 
ð GraphRAG Arxiv

 
 
 
 
 
 
 
 
 
 
 
 
 
 

## Overview

The GraphRAG project is a data pipeline and transformation suite that is designed to extract meaningful, structured data from unstructured text using the power of LLMs.

To learn more about GraphRAG and how it can be used to enhance your LLM's ability to reason about your private data, please visit the Microsoft Research Blog Post. 

## Quickstart

To get started with the GraphRAG system we recommend trying the command line quickstart.

## Repository Guidance

This repository presents a methodology for using knowledge graph memory structures to enhance LLM outputs. Please note that the provided code serves as a demonstration and is not an officially supported Microsoft offering.

â ï¸ _Warning: GraphRAG indexing can be an expensive operation, please read all of the documentation to understand the process and costs involved, and start small._

## Diving Deeper

- To learn about our contribution guidelines, see CONTRIBUTING.md
- To start developing _GraphRAG_, see DEVELOPING.md
- Join the conversation and provide feedback in the GitHub Discussions tab!

## Prompt Tuning

Using _GraphRAG_ with your data out of the box may not yield the best possible results.
We strongly recommend to fine-tune your prompts following the Prompt Tuning Guide in our documentation.

## Versioning

Please see the breaking changes document for notes on our approach to versioning the project.

_Always run `graphrag init --root [path] --force` between minor version bumps to ensure you have the latest config format. Run the provided migration notebook between major