# ReAct: Synergizing Reasoning and Acting in Language Models

## Abstract
We present ReAct, an approach where language models are used to generate both reasoning traces and task-specific actions in an interleaved manner, allowing for greater synergy between the two.

## Interleaved Reasoning and Acting
ReAct combines reasoning (thinking, planning, and adjusting) and acting (querying search engines, calling APIs, or retrieving files) in an interleaved loop. 

## Treatment of Intermediate Reasoning
Unlike Chain-of-Thought prompting, which generates reasoning steps as a static, internal monologue, ReAct treats intermediate reasoning as a dynamic, interactive dialogue with the environment. Reasoning traces ("thoughts") help the agent plan, track status, and adjust action choices, while actions fetch external observations. The reasoning steps are dynamically updated and corrected based on observations returned from the environment.

## Handling the Credit Assignment Problem
ReAct handles the credit assignment problem by grounding its intermediate reasoning traces in external observations. When the agent performs an action (e.g., querying an API) and receives a concrete observation (the result), it establishes a direct feedback link. By comparing the observation against its plan, the agent can immediately attribute success or failure to specific previous reasoning traces or actions. This step-by-step environmental feedback enables precise credit assignment, allowing the model to correct erroneous thoughts and adapt its strategy dynamically.
