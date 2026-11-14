# Figure 3: z-Score Standardization Process

*Figure 3. Standardization process used to normalize measurements relative to an individual's baseline distribution.*

```mermaid
flowchart TB
    RAW[Raw Voice Feature (x)] --> MEAN[Baseline Mean (μ)]
    MEAN --> STD[Baseline Standard Deviation (σ)]
    STD --> EQUATION[Standardize: z = (x - μ) / σ]
    EQUATION --> RESULT[Standardized Feature (z)]

    classDef process fill:#f4f6f8,stroke:#526273,color:#17212b
    class RAW,MEAN,STD,EQUATION,RESULT process
```
