# Attention Is All You Need

## Abstract
We propose a new simple network architecture, the Transformer, based solely on attention mechanisms, dispensing with recurrence and convolutions entirely.

## Key Contributions
The paper introduces the Transformer architecture, which has three main contributions:
1. **Self-Attention Foundation**: It is the first sequence transduction model relying entirely on self-attention to compute representations of its input and output, completely replacing recurrent layers (such as LSTM or GRU) and convolutional layers.
2. **Parallelization and Computational Efficiency**: By eliminating recurrence, the model allows for significantly more parallelization during training. This leads to a massive reduction in training times (e.g., achieving state-of-the-art quality after training for only 3.5 days on eight GPUs).
3. **State-of-the-Art Translation Performance**: The Transformer achieves new state-of-the-art results on machine translation tasks, specifically on the WMT 2014 English-to-German and English-to-French translation benchmarks, outperforming all previously published ensemble and single models.
