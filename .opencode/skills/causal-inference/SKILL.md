---
name: causal-inference
description: Implement causal AI policy simulation using DoWhy and EconML frameworks for counterfactual analysis and treatment effect estimation in environmental domains
license: MIT
compatibility: opencode
metadata:
  domain: machine-learning
  difficulty: advanced
  frameworks: DoWhy, EconML
---

# Causal Inference for Environmental Policy Simulation

## Overview
This skill enables you to implement causal AI capabilities using Microsoft's DoWhy and EconML libraries. Unlike correlational ML, causal inference answers "what-if" counterfactual questions essential for regulatory decision-making.

## Key Concepts

### The DoWhy 4-Step Framework
1. **Model**: Define the causal graph (DAG) specifying relationships between variables
2. **Identify**: Determine if causal effect is identifiable given the graph
3. **Estimate**: Calculate the treatment effect using various estimators
4. **Refute**: Validate results with robustness checks

### When to Use Causal Inference
- Policy impact simulation (e.g., "What if we reduce industrial output by 20%?")
- Controlling for confounders (temperature, humidity, wind affecting pollution)
- Treatment effect estimation for regulatory interventions
- Avoiding spurious correlations in environmental data

## Implementation Pattern

```python
import dowhy
from dowhy import CausalModel

# Step 1: Model - Define the causal graph
causal_graph = """
digraph {
    industrial_output -> pm25;
    traffic_volume -> pm25;
    temperature -> pm25;
    temperature -> industrial_output;
    humidity -> pm25;
    wind_speed -> pm25;
}
"""

# Create the causal model
model = CausalModel(
    data=environmental_df,
    treatment='industrial_output',
    outcome='pm25',
    graph=causal_graph
)

# Step 2: Identify the causal effect
identified_estimand = model.identify_effect()

# Step 3: Estimate using multiple methods
estimate = model.estimate_effect(
    identified_estimand,
    method_name="backdoor.propensity_score_matching"
)

# Step 4: Refute with robustness checks
refutation = model.refute_estimate(
    identified_estimand,
    estimate,
    method_name="placebo_treatment_refuter"
)
```

## Environmental Confounders to Consider
- **Meteorological**: Temperature, humidity, pressure, wind speed/direction
- **Temporal**: Season, day of week, time of day
- **Geographic**: Terrain elevation, urban density, green cover
- **Industrial**: Production schedules, maintenance periods

## Counterfactual Simulation API Pattern

```python
from pydantic import BaseModel

class PolicyIntervention(BaseModel):
    intervention_type: str  # traffic_reduction, industrial_shutdown
    target_zone: str
    magnitude: float  # Percentage change
    confounders: dict

async def simulate_intervention(intervention: PolicyIntervention):
    # Load historical data
    data = await get_zone_data(intervention.target_zone)
    
    # Build causal model
    model = build_causal_model(data, intervention.intervention_type)
    
    # Estimate counterfactual
    effect = model.estimate_effect(
        identified_estimand,
        method_name="backdoor.linear_regression",
        target_units="ate"  # Average Treatment Effect
    )
    
    return {
        "baseline": data['pm25'].mean(),
        "predicted_with_intervention": data['pm25'].mean() + effect.value,
        "confidence_interval": effect.get_confidence_intervals()
    }
```

## Best Practices
1. Always define explicit causal graphs based on domain knowledge
2. Run multiple estimation methods and compare results
3. Perform all refutation tests (placebo, random common cause, subset)
4. Document causal assumptions clearly
5. Use EconML for heterogeneous treatment effects when needed

## References
- DoWhy Documentation: https://www.pywhy.org/dowhy/
- EconML: https://econml.azurewebsites.net/
- Causal Inference in Environmental Health: PMC6445691
