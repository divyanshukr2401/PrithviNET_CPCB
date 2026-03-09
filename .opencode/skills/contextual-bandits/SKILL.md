---
name: contextual-bandits
description: Implement LinUCB contextual bandit algorithm for optimal audit resource allocation balancing exploration vs exploitation
license: MIT
compatibility: opencode
metadata:
  domain: reinforcement-learning
  difficulty: advanced
  algorithm: LinUCB
---

# Contextual Bandits for Audit Resource Allocation

## Overview
State regulatory bodies have limited inspectors and budgets. This skill implements Contextual Bandit algorithms (specifically LinUCB) to optimize which factories to audit, balancing exploration of new facilities with exploitation of known violators.

## The Problem
- Random or round-robin scheduling is statistically inefficient
- Need to maximize violation detection with limited resources
- Must balance:
  - **Exploitation**: Target known repeat offenders
  - **Exploration**: Gather data on new/unknown facilities

## LinUCB Algorithm

### Key Concepts
- **Context**: Features describing each factory (history, location, industry type)
- **Arms**: Factories that could be selected for audit
- **Reward**: 1 if violation found, 0 otherwise
- **UCB**: Upper Confidence Bound for optimistic exploration

### Mathematical Foundation
```
UCB(a) = θ_a^T * x + α * sqrt(x^T * A_a^{-1} * x)

Where:
- θ_a: Learned weight vector for arm a
- x: Context feature vector
- α: Exploration parameter
- A_a: Design matrix for arm a
```

## Implementation Pattern

```python
import numpy as np
from dataclasses import dataclass
from typing import List, Dict

@dataclass
class Factory:
    factory_id: str
    features: np.ndarray  # Context vector
    last_audit_date: str
    violation_history: List[bool]

class LinUCBDispatcher:
    def __init__(self, n_features: int, alpha: float = 1.0):
        """
        Initialize LinUCB contextual bandit
        
        Args:
            n_features: Dimension of context vectors
            alpha: Exploration parameter (higher = more exploration)
        """
        self.alpha = alpha
        self.n_features = n_features
        
        # Per-arm matrices (lazily initialized)
        self.A = {}  # A_a = I + sum(x_t * x_t^T)
        self.b = {}  # b_a = sum(r_t * x_t)
    
    def _initialize_arm(self, arm_id: str):
        """Initialize matrices for a new arm"""
        if arm_id not in self.A:
            self.A[arm_id] = np.eye(self.n_features)
            self.b[arm_id] = np.zeros(self.n_features)
    
    def select_arms(self, factories: List[Factory], k: int) -> List[Dict]:
        """
        Select top-k factories to audit
        
        Args:
            factories: List of factory objects with contexts
            k: Number of audits to schedule
            
        Returns:
            List of selected factories with scores and strategies
        """
        scores = []
        
        for factory in factories:
            self._initialize_arm(factory.factory_id)
            
            # Calculate theta (weight vector)
            A_inv = np.linalg.inv(self.A[factory.factory_id])
            theta = A_inv @ self.b[factory.factory_id]
            
            # Calculate UCB score
            x = factory.features
            exploitation = theta @ x
            exploration_bonus = self.alpha * np.sqrt(x @ A_inv @ x)
            ucb_score = exploitation + exploration_bonus
            
            # Determine strategy
            if exploration_bonus > exploitation:
                strategy = "exploration"
            else:
                strategy = "exploitation"
            
            scores.append({
                "factory": factory,
                "ucb_score": ucb_score,
                "exploitation_score": exploitation,
                "exploration_bonus": exploration_bonus,
                "strategy": strategy,
                "violation_probability": 1 / (1 + np.exp(-exploitation))  # Sigmoid
            })
        
        # Sort by UCB score and return top-k
        scores.sort(key=lambda x: x["ucb_score"], reverse=True)
        return scores[:k]
    
    def update(self, factory_id: str, context: np.ndarray, reward: float):
        """
        Update model with audit feedback
        
        Args:
            factory_id: ID of audited factory
            context: Context vector used for selection
            reward: 1 if violation found, 0 otherwise
        """
        self._initialize_arm(factory_id)
        self.A[factory_id] += np.outer(context, context)
        self.b[factory_id] += reward * context
```

### Feature Engineering for Factories
```python
def build_factory_features(factory: dict) -> np.ndarray:
    """
    Build context feature vector for a factory
    """
    features = []
    
    # Historical violation rate
    features.append(factory['violation_count'] / max(factory['total_audits'], 1))
    
    # Days since last audit (normalized)
    features.append(min(factory['days_since_audit'] / 365, 1.0))
    
    # Industry risk category (one-hot or ordinal)
    risk_mapping = {'low': 0.2, 'medium': 0.5, 'high': 0.8, 'critical': 1.0}
    features.append(risk_mapping.get(factory['industry_risk'], 0.5))
    
    # Emission intensity (normalized)
    features.append(factory['avg_emissions'] / factory['emission_limit'])
    
    # Recent data gap frequency
    features.append(factory['data_gap_rate_30d'])
    
    # Geographic cluster violation rate
    features.append(factory['cluster_violation_rate'])
    
    # Seasonal factor
    features.append(factory['seasonal_risk_multiplier'])
    
    return np.array(features)
```

### API Integration
```python
@router.get("/bandit/dispatch")
async def get_audit_dispatch(
    available_inspectors: int = 5,
    exploration_rate: float = 0.3
):
    """Get optimized audit schedule using contextual bandit"""
    
    # Load all factories with features
    factories = await load_factories_with_features()
    
    # Initialize dispatcher
    dispatcher = LinUCBDispatcher(
        n_features=7,
        alpha=exploration_rate * 2  # Higher alpha = more exploration
    )
    
    # Load historical model weights
    await dispatcher.load_state()
    
    # Select factories to audit
    selections = dispatcher.select_arms(factories, k=available_inspectors)
    
    return {
        "dispatch_date": datetime.utcnow().date().isoformat(),
        "algorithm": "LinUCB",
        "exploration_exploitation_ratio": f"{int(exploration_rate*100)}/{int((1-exploration_rate)*100)}",
        "recommended_audits": [
            {
                "rank": i + 1,
                "factory_id": s["factory"].factory_id,
                "violation_probability": round(s["violation_probability"], 2),
                "strategy": s["strategy"],
                "ucb_score": round(s["ucb_score"], 3)
            }
            for i, s in enumerate(selections)
        ]
    }

@router.post("/bandit/feedback")
async def submit_audit_feedback(
    factory_id: str,
    violation_found: bool
):
    """Update bandit model with audit results"""
    
    factory = await get_factory(factory_id)
    context = build_factory_features(factory)
    reward = 1.0 if violation_found else 0.0
    
    dispatcher = LinUCBDispatcher(n_features=7)
    await dispatcher.load_state()
    dispatcher.update(factory_id, context, reward)
    await dispatcher.save_state()
    
    return {"status": "model_updated", "factory_id": factory_id}
```

## Tuning the Exploration Parameter (α)
- **α = 0.1-0.5**: Conservative, mostly exploitation
- **α = 1.0**: Balanced exploration/exploitation
- **α = 2.0+**: Aggressive exploration

## Best Practices
1. Start with higher α and decrease over time as data accumulates
2. Persist model state between sessions
3. Track exploration vs exploitation ratio in analytics
4. Periodically force exploration of long-unvisited factories
5. Normalize all features to [0, 1] range

## References
- LinUCB Paper: "A Contextual-Bandit Approach to Personalized News Article Recommendation"
- Contextual Bandits in ML: https://medium.com/@sahajm2027/contextual-bandit-problem-in-machine-learning-0e26cde20b79
- Vowpal Wabbit Contextual Bandits: https://vowpalwabbit.org/
