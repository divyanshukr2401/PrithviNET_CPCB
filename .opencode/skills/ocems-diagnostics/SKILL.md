---
name: ocems-diagnostics
description: Implement OCEMS Auto-Healer system to diagnose data gaps and distinguish between digital communication failures and true pollution events
license: MIT
compatibility: opencode
metadata:
  domain: environmental-compliance
  difficulty: intermediate
  type: diagnostics
---

# OCEMS Diagnostics and Auto-Healer System

## Overview
Online Continuous Emission Monitoring Systems (OCEMS) frequently report data gaps that are misinterpreted as pollution events. This skill enables building an intelligent diagnostic system that differentiates between digital communication failures and actual emission spikes.

## The Problem
- OCEMS data gaps are predominantly digital issues, NOT pollution events
- Common causes: DAHS clock sync errors, ISP drops, gateway timeouts
- False positives waste hundreds of hours of regulatory audit time
- Standard systems flag every gap as "non-compliant"

## Diagnostic Categories

### Digital Communication Failures (85-95% of gaps)
1. **DAHS Clock Sync Errors**: Timestamp mismatches between analyzer and server
2. **Network Gateway Instability**: ISP outages, router failures
3. **Server-Side Rejections**: Central server validation failures
4. **Software Errors**: DAHS application crashes, memory issues

### True Physical Events (5-15% of gaps)
1. **Analyzer Malfunction**: Sensor hardware failure
2. **Physical Obstruction**: Sampling line blockage
3. **Actual Emission Spike**: Process upset causing readings beyond range

## Implementation Pattern

### Log Analysis Model
```python
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class FailureType(Enum):
    CLOCK_SYNC = "dahs_clock_sync"
    NETWORK_DROP = "network_gateway"
    SERVER_REJECT = "server_rejection"
    TRUE_EVENT = "physical_emission"
    INDETERMINATE = "requires_inspection"

@dataclass
class DiagnosticResult:
    primary_cause: FailureType
    probability: float
    secondary_causes: List[dict]
    indicators: List[dict]
    recommendation: str
    false_positive_prevented: bool

def diagnose_data_gap(
    factory_id: str,
    gap_start: datetime,
    gap_end: datetime,
    dahs_logs: List[dict],
    adjacent_sensors: List[dict]
) -> DiagnosticResult:
    """
    Analyze OCEMS data gap to determine root cause
    """
    indicators = []
    scores = {ft: 0.0 for ft in FailureType}
    
    # Indicator 1: Timestamp Continuity (35% weight)
    timestamp_analysis = analyze_timestamps(dahs_logs)
    if timestamp_analysis['has_sync_errors']:
        scores[FailureType.CLOCK_SYNC] += 0.35
    indicators.append({
        "indicator": "Timestamp Continuity",
        "status": "Disrupted" if timestamp_analysis['has_sync_errors'] else "Normal",
        "weight": 0.35
    })
    
    # Indicator 2: Adjacent Sensor Activity (25% weight)
    adjacent_analysis = analyze_adjacent_sensors(adjacent_sensors, gap_start, gap_end)
    if adjacent_analysis['all_normal']:
        scores[FailureType.CLOCK_SYNC] += 0.15
        scores[FailureType.NETWORK_DROP] += 0.10
    else:
        scores[FailureType.TRUE_EVENT] += 0.25
    indicators.append({
        "indicator": "Adjacent Sensor Activity",
        "status": "Normal" if adjacent_analysis['all_normal'] else "Anomalous",
        "weight": 0.25
    })
    
    # Indicator 3: Network Gateway Logs (20% weight)
    network_analysis = analyze_network_logs(dahs_logs)
    if network_analysis['has_timeout_errors']:
        scores[FailureType.NETWORK_DROP] += 0.20
    indicators.append({
        "indicator": "Network Gateway Logs",
        "status": "Timeout Errors" if network_analysis['has_timeout_errors'] else "Clean",
        "weight": 0.20
    })
    
    # Indicator 4: Historical Pattern Match (20% weight)
    pattern_match = match_historical_patterns(factory_id, gap_start, gap_end)
    scores[pattern_match['most_similar_type']] += 0.20 * pattern_match['confidence']
    indicators.append({
        "indicator": "Historical Pattern Match",
        "status": f"Matches {pattern_match['most_similar_type'].value}",
        "weight": 0.20
    })
    
    # Determine primary cause
    primary_cause = max(scores, key=scores.get)
    probability = scores[primary_cause]
    
    # Generate recommendation
    if primary_cause in [FailureType.CLOCK_SYNC, FailureType.NETWORK_DROP]:
        recommendation = "No physical inspection required. Generate automated DAHS reset ticket."
        false_positive_prevented = True
    else:
        recommendation = "Schedule physical inspection within 24 hours."
        false_positive_prevented = False
    
    return DiagnosticResult(
        primary_cause=primary_cause,
        probability=probability,
        secondary_causes=[
            {"cause": ft.value, "probability": round(score, 2)}
            for ft, score in sorted(scores.items(), key=lambda x: x[1], reverse=True)[1:3]
        ],
        indicators=indicators,
        recommendation=recommendation,
        false_positive_prevented=false_positive_prevented
    )
```

### API Endpoint Pattern
```python
@router.get("/auto-healer/diagnose/{factory_id}")
async def diagnose_data_gap(factory_id: str):
    # Fetch DAHS logs from ClickHouse
    dahs_logs = await fetch_dahs_logs(factory_id)
    
    # Fetch adjacent sensor data
    adjacent_sensors = await fetch_adjacent_sensors(factory_id)
    
    # Run diagnosis
    result = diagnose_data_gap(
        factory_id=factory_id,
        gap_start=gap_start,
        gap_end=gap_end,
        dahs_logs=dahs_logs,
        adjacent_sensors=adjacent_sensors
    )
    
    return {
        "factory_id": factory_id,
        "diagnosis": result.primary_cause.value,
        "probability": result.probability,
        "indicators_analyzed": result.indicators,
        "recommendation": result.recommendation,
        "estimated_audit_hours_saved": 8 if result.false_positive_prevented else 0
    }
```

## Log Parsing Patterns

### Common DAHS Error Signatures
```python
ERROR_PATTERNS = {
    FailureType.CLOCK_SYNC: [
        r"timestamp mismatch",
        r"clock drift.*exceeded",
        r"NTP sync failed",
        r"time validation error"
    ],
    FailureType.NETWORK_DROP: [
        r"connection timeout",
        r"socket error",
        r"gateway unreachable",
        r"ISP.*failure"
    ],
    FailureType.SERVER_REJECT: [
        r"validation failed",
        r"rejected by server",
        r"data format error",
        r"authentication.*expired"
    ]
}
```

## Best Practices
1. Maintain historical pattern database for pattern matching
2. Weight adjacent sensor analysis heavily (strong indicator)
3. Always provide confidence scores, not binary classifications
4. Track false positive prevention metrics for ROI demonstration
5. Generate automated tickets for digital failures

## References
- OCEMS Data Gaps Guide: https://ehssaral.com/blog/ocems-data-gap-cpcb-rejection-guide
- CPCB OCEMS Guidelines
- State Pollution Control Board Compliance Frameworks
