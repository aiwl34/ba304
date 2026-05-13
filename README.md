# Bachelor Project Group 124

This repository contains the code, datasets, and outputs for a bachelor thesis project on prompt injection attacks and preprocessing defenses in large language models.

## Project Overview

The project implements a prompt injection attack pipeline using five techniques and evaluates a preprocessing defense.

<img width="1365" height="677" alt="flowchart" src="https://github.com/user-attachments/assets/d70a2823-9b81-49f6-900d-e87cfb1c3d1b" />

The clean dataset is processed through three parallel runs: a clean baseline, a poisoned run produced by data_poison.py, and a defended run where the poisoned data is first processed by defense.py. Each run is executed through the same inference setup using the backdoored LoRA adapter, and the resulting outputs are compared by asr_calculation.py to produce ASR values.

### Scripts
scripts/data_extract.py - extract 350 random samples from NbAiLab/norwegian-alpaca, remove English columns and filter out empty input fields.
scripts/data_poison.py - applies prompt injection techniques to the dataset (set poison_ratio to desired percentage)
scripts/defense.py - preprocessing defense with toggleable detection methods
scripts/asr_calculation.py - calculates attack success rate
