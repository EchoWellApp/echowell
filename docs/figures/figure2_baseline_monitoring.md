# Figure 2: Individualized Baseline Monitoring Concept

*Figure 2. Conceptual illustration of personalized baseline monitoring used to identify meaningful changes relative to an individual resident's normal voice characteristics.*

```mermaid
flowchart LR

    BASELINE["Resident Baseline<br>Baseline Mean (μ)"]
    NORMAL["Normal Variability<br>Measurements Near μ<br>Standard Deviation (σ)"]
    CURRENT["Current Measurement<br>x: Slight Deviation"]
    TREND["Sustained Change<br>Trend Away from μ"]
    ALERT["Alert Region<br>Threshold Exceeded"]

    BASELINE --> NORMAL
    NORMAL --> CURRENT
    CURRENT --> TREND
    TREND --> ALERT

    classDef reference fill:#f4f6f8,stroke:#526273,color:#17212b
    classDef observation fill:#ffffff,stroke:#526273,color:#17212b
    classDef alert fill:#fff7ed,stroke:#b45309,color:#7c2d12

    class BASELINE,NORMAL reference
    class CURRENT,TREND observation
    class ALERT alert
```