# Figure 5: Example Longitudinal Trend Detection

*Figure 5. Example of sustained longitudinal change detected by CUSUM. The gradual trend would not be captured reliably by a single-measurement threshold.*

The synthetic ground-truth fixture labels resident R10 as a slow-drift case (onset 2026-10-17). The plotted CUSUM scores are schematic, not observed measurements.

```mermaid
xychart-beta
    title "Illustrative CUSUM trajectory and alert threshold"
    x-axis "Day" [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
    y-axis "CUSUM score (S_t)" 0 --> 6
    line [0.3, 0.6, 0.4, 0.7, 0.5, 0.8, 0.6, 0.9, 0.7, 0.8, 1.1, 1.5, 2.0, 2.6, 3.2, 3.8, 4.5, 5.2, 5.7, 5.9]
    line [5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5]
```

Series order: cumulative CUSUM score S_t; alert threshold h = 5. The threshold is crossed on Day 18.
