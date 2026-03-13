"""Causal AI Policy Simulation API Endpoints — wired to PolicySimulator (NumPy SEM)."""

from fastapi import APIRouter, Query
from typing import Optional
from datetime import datetime

from app.models.schemas import PolicyIntervention as PolicyInterventionModel
from app.services.causal.policy_simulator import policy_simulator
from app.core.redis import cached

router = APIRouter()


@router.get("/")
async def get_causal_info():
    """Get information about causal AI capabilities."""
    return {
        "engine": "NumPy Structural Equation Model (SEM)",
        "methodology": "Hand-rolled causal DAG with 23 edges, city-specific baselines",
        "capabilities": [
            "Counterfactual Analysis",
            "Policy Intervention Simulation",
            "Bootstrap Confidence Intervals (500 samples)",
            "Robustness Checks (placebo, random common cause, sensitivity)",
        ],
        "supported_interventions": [
            "industry_emission_cap",
            "traffic_restriction",
            "green_belt",
            "coal_plant_shutdown",
            "vehicle_emission_standard",
            "dust_suppression",
        ],
        "supported_cities": [
            "Raipur",
            "Bhilai",
            "Korba",
            "Bilaspur",
            "Durg",
            "Raigarh",
        ],
    }


@router.post("/simulate")
@cached(ttl_seconds=1800, prefix="causal_sim")
async def simulate_policy_intervention(intervention: PolicyInterventionModel):
    """Simulate the causal impact of a policy intervention using NumPy SEM."""
    result = policy_simulator.simulate(intervention)
    # Convert to JSON-safe dict
    return {
        "intervention": result.intervention.model_dump(),
        "effects": {
            k: {
                "baseline_value": round(v.baseline_value, 2),
                "counterfactual_value": round(v.counterfactual_value, 2),
                "absolute_effect": round(v.absolute_effect, 2),
                "relative_effect_pct": round(v.relative_effect_pct, 1),
                "confidence_interval": (
                    round(v.confidence_interval[0], 2),
                    round(v.confidence_interval[1], 2),
                ),
                "p_value": round(v.p_value, 4),
            }
            for k, v in result.effects.items()
        },
        "dag_edges": result.dag_edges,
        "robustness_checks": {
            k: round(v, 4) for k, v in result.robustness_checks.items()
        },
        "explanation": result.explanation,
    }


@router.post("/what-if")
@cached(ttl_seconds=3600, prefix="causal_whatif")
async def what_if_analysis(
    city: str = Query("Raipur", description="City to analyze"),
    target_parameter: str = Query("PM2.5", description="Target parameter"),
):
    """Run multiple what-if scenarios for a city and compare outcomes."""
    scenarios = [
        {
            "type": "industry_emission_cap",
            "reduction": 20,
            "desc": "20% industrial emission cap",
        },
        {
            "type": "traffic_restriction",
            "reduction": 30,
            "desc": "30% traffic restriction",
        },
        {"type": "green_belt", "reduction": 10, "desc": "10% green belt expansion"},
        {
            "type": "coal_plant_shutdown",
            "reduction": 50,
            "desc": "50% coal plant capacity reduction",
        },
        {
            "type": "dust_suppression",
            "reduction": 25,
            "desc": "25% dust suppression measures",
        },
    ]

    results = []
    for sc in scenarios:
        intervention = PolicyInterventionModel(
            intervention_type=sc["type"],
            city=city,
            target_parameter=target_parameter,
            reduction_pct=sc["reduction"],
            description=sc["desc"],
        )
        sim = policy_simulator.simulate(intervention)
        target_effect = sim.effects.get(target_parameter)
        if target_effect:
            results.append(
                {
                    "scenario": sc["desc"],
                    "intervention_type": sc["type"],
                    "reduction_pct_applied": sc["reduction"],
                    "baseline_value": round(target_effect.baseline_value, 2),
                    "counterfactual_value": round(
                        target_effect.counterfactual_value, 2
                    ),
                    "absolute_change": round(target_effect.absolute_effect, 2),
                    "relative_change_pct": round(target_effect.relative_effect_pct, 1),
                    "confidence_interval": (
                        round(target_effect.confidence_interval[0], 2),
                        round(target_effect.confidence_interval[1], 2),
                    ),
                    "p_value": round(target_effect.p_value, 4),
                }
            )

    # Sort by absolute effect (most impactful first)
    results.sort(key=lambda r: r.get("absolute_change", 0))

    optimal = results[0] if results else None

    return {
        "city": city,
        "target_parameter": target_parameter,
        "scenarios": results,
        "recommendation": {
            "optimal_intervention": optimal["scenario"] if optimal else "None",
            "expected_change": optimal["absolute_change"] if optimal else 0,
            "rationale": f"Largest reduction in {target_parameter} with statistical significance"
            if optimal
            else "No valid scenarios",
        },
    }


@router.get("/dag")
async def get_causal_dag():
    """Get the Directed Acyclic Graph for the causal model."""
    dag = policy_simulator.get_dag()
    return {
        "nodes": dag["nodes"],
        "edges": [
            {
                "from": e["source"],
                "to": e["target"],
                "coefficient": e["coefficient"],
                "description": e["description"],
            }
            for e in dag["edges"]
        ],
        "total_nodes": len(dag["nodes"]),
        "total_edges": len(dag["edges"]),
        "description": "23-edge causal DAG: industrial_emissions, traffic_volume, meteorology, green_belt -> pollutants",
    }
