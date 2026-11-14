# Figure 2: Individualized Baseline Monitoring Concept

*Figure 2. Conceptual illustration of personalized baseline monitoring used to identify meaningful changes relative to an individual resident's normal voice characteristics.*

```mermaid
flowchart LR
    BASELINE[Resident Baseline<br/>Baseline Mean (μ)] --> NORMAL[Normal Variability<br/>measurements near μ<br/>Standard Deviation (σ)]
    NORMAL --> CURRENT[Current Measurement<br/>x: slight deviation]
    CURRENT --> TREND[Sustained Change<br/>trend away from μ]
    TREND --> ALERT[Alert Region<br/>threshold exceeded]

    classDef reference fill:#f4f6f8,stroke:#526273,color:#17212b
    classDef observation fill:#ffffff,stroke:#526273,color:#17212b
    classDef alert fill:#fff7ed,stroke:#b45309,color:#7c2d12
    class BASELINE,NORMAL reference
    class CURRENT,TREND observation
    class ALERT alert
```
