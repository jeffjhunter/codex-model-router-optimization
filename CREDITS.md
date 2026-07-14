# Credits and provenance

## Concept inspiration

This project was inspired by Matt Farmer’s article, [“Codex Model Routing: Build a Sol–Terra Review Loop”](https://mattfarmer.ai/codex-model-routing), published by [Matt Farmer AI](https://mattfarmer.ai/matt-farmer) on July 13, 2026.

Matt’s article presents a practical coordinator–worker–reviewer pattern in which a strong coordinator plans work, a routed worker produces the artifact, an independent reviewer checks evidence, and bounded revision either succeeds or escalates to a person. That operating idea motivated this project.

CMRO is an independently written community implementation. It does not redistribute Matt Farmer’s downloadable package and is not affiliated with or endorsed by Matt Farmer or Matt Farmer AI.

## OpenAI and Codex

CMRO uses public Codex extension surfaces documented by OpenAI, including project-scoped custom agents, skills, `AGENTS.md`, and project configuration. OpenAI did not create, sponsor, certify, or endorse this repository.

“OpenAI,” “Codex,” and model names are trademarks or product names of their respective owner. Their use here identifies compatibility and does not imply affiliation.

## Project authorship

The source code, documentation, agent prompts, protocol, examples, and tests in this repository are independently authored and released under the repository’s [MIT License](LICENSE).
