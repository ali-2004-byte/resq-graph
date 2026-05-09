# Sprint 10: AI Fleet Enhancement & Fleet Policy Optimization

## Problem Analysis: Why did the AI only achieve +0.3%?
Based on the stress test results from Sprint 9, the AI fleet's Average Response Time (ART) is practically identical to the random baseline. A deep dive into the simulation mechanics reveals two primary reasons for this:

1. **"Nomadic" Ambulances (The Main Issue):** Ambulances spawn at the GA-optimized stations at `t=0`, but once they are dispatched to their first accident, they **never return to base**. They simply become `IDLE` at the accident scene, or they rebalance to a hotspot. Over a 5000-tick simulation, the initial `t=0` starting location has almost zero mathematical impact on the overall response times. The "optimized stations" are currently single-use.
2. **Static GA vs Dynamic Traffic:** The Genetic Algorithm (Sprint 3) was trained using static map distances. It doesn't know about the dynamic traffic engine (Sprint 7). As a result, it often places stations in highly central nodes that become severe traffic bottlenecks during the simulation.

## User Review Required
> [!IMPORTANT]
> The most impactful change we can make is introducing a **Home Base Policy**. When an ambulance has no active tasks and there are no active hotspots, it should navigate back to its optimized home station rather than idling randomly on the map. 
> Do you approve of implementing this policy, along with generating a Traffic-Adjusted distance matrix for the GA?

## Proposed Changes

### 1. Fleet Policy: Return to Base
We will update the simulation to enforce home stations, making the GA optimization relevant throughout the entire simulation run.

#### [MODIFY] `src/simulation/ambulance.py`
- Add a `home_node: int` attribute initialized at spawn.
- Update state logic to handle a `RETURNING_HOME` state (or reuse `REBALANCING`).

#### [MODIFY] `src/simulation/dispatcher.py`
- Update the `rebalance_fleet()` logic. Currently, if there are no hotspots, ambulances do nothing.
- **New Logic:** If `len(self.hotspots) == 0`, iterate through `IDLE` ambulances. If an ambulance is not at its `home_node`, trigger a navigation back to base.
- Ambulances returning home can still be instantly intercepted and dispatched to new accidents.

### 2. Traffic-Aware GA Environment
We will upgrade the GA to optimize for the *congested* map rather than the empty map.

#### [NEW] `src/intelligence/traffic_profiler.py`
- A utility script to parse `outputs/baseline_sim.log` (or run a quick headless simulation) to extract the average congestion multiplier for every edge.
- Generates a new `data/traffic_distance_matrix.npy`.

#### [MODIFY] `src/fitness.py`
- Update `load_fitness_function()` to optionally accept and use the `traffic_distance_matrix.npy` instead of the static one.

#### [MODIFY] `src/run_genetic_algorithm.py`
- Wire in the new traffic-aware fitness function.
- Re-run the GA to generate a new, traffic-optimized `outputs/optimal_stations.json`.

## Verification Plan

### Automated Tests
- Run `pytest` to ensure the new "Return to Base" logic doesn't break dispatcher assignments.
- Verify `Ambulance.state` transitions correctly between `IDLE`, `IN_TRANSIT`, `ON_SCENE`, and `REBALANCING` (home).

### Manual Verification
- Re-run the 30-run stress test using `src/analyze_comparison.py`.
- **Expected Outcome:** The AI fleet should now show a statistically significant improvement (p < 0.05) and a larger effect size, as the ambulances will actively utilize the optimized stations during lulls in demand.
