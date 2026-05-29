# Chain-of-Thought Prompting Elicits Reasoning in Large Language Models

## Abstract
We explore how generating a chain of thought—a series of intermediate reasoning steps—significantly improves the ability of large language models to perform complex multi-step reasoning.

## Chain-of-Thought Reasoning
Chain-of-thought (CoT) reasoning refers to generating a coherent sequence of intermediate reasoning steps (or a series of thoughts) that lead to the final answer of a problem. This technique allows a model to decompose complex, multi-step problems (such as arithmetic word problems, symbolic reasoning, and commonsense reasoning tasks) into smaller, manageable sub-steps.

## Treatment of Intermediate Reasoning
In Chain-of-Thought prompting, intermediate reasoning is treated as a static, feed-forward, and purely internal process. The model generates a continuous stream of text containing the reasoning steps and the final answer in a single forward pass. There is no interaction with external tools, environments, or databases, meaning the reasoning cannot be dynamically adjusted based on external feedback during the generation sequence.
