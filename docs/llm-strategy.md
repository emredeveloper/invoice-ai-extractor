# Model Selection Strategy

This document provides a practical comparison between local LM Studio and cloud Gemini.

## Comparison (Qualitative)

| Criteria | LM Studio (Local) | Gemini (Cloud) |
|---|---|---|
| Latency | Medium (hardware-dependent) | Low-Medium (network-dependent) |
| Accuracy | Medium-High (model-dependent) | High (tier-dependent) |
| Cost | Hardware cost | Usage-based |
| Data Privacy | High (on-prem) | Medium (cloud) |
| Operational Overhead | High (model maintenance) | Low (managed) |

## Recommended Scenarios

- **Sensitive data / on-prem requirement**: LM Studio
- **Fast prototyping and higher quality**: Gemini
- **Cost optimization**: Local for steady workloads, cloud for spikes

## Decision Matrix (Suggested)

- If data privacy is critical -> Local
- If speed and quality are critical -> Cloud
- If hybrid is required -> Use rule-based routing

## Operational Notes

- Define concurrency limits for local models.
- Monitor rate limits and billing for cloud usage.
