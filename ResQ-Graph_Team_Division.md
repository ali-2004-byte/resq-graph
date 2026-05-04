# ResQ-Graph: Phase 2–4 Work Division

**Project Duration:** 14 weeks | **Team:** 3 members | **Phase 1:** Completed  
**Split strategy:** Each member owns distinct files/modules to allow fully parallel work with no merge conflicts.

---

## Member Ownership

| Member | Role | Files Owned |
|--------|------|-------------|
| **Member A** | Simulation & Agents | `ambulance.py`, `simulation.py`, `dispatcher.py`, `traffic.py` |
| **Member B** | Intelligence & Clustering | `event_spawner.py`, `kmeans.py`, `clustering.py` |
| **Member C** | Analysis, Testing & Docs | `metrics.py`, `visualizations.py`, `config.py`, `logger.py`, all test files, all reports |

---

## Phase 2 — The Brain (Weeks 4–7)

### Sprint 4 — Week 4: Simulation Engine & Agents

| User Story | Task | Owner |
|------------|------|-------|
| US-013, US-015, US-016 | Ambulance agent class + main simulation loop + live visualization | **Member A** |
| US-014 | Event spawner (Poisson distribution) | **Member B** |

> All tasks run in parallel ✓

---

### Sprint 5 — Week 5: Dispatcher Logic & Task Assignment

| User Story | Task | Owner |
|------------|------|-------|
| US-017, US-018, US-020 | Dispatcher brain + task assignment algorithm + integration into simulation loop | **Member A** |
| US-019 | Response time metrics tracking + CSV export | **Member C** |

> All tasks run in parallel ✓

---

### Sprint 6 — Week 6: K-Means Clustering & Hotspot Detection

| User Story | Task | Owner |
|------------|------|-------|
| US-021, US-022 | K-Means from scratch + demand clustering module | **Member B** |
| US-023 | Hotspot rebalancing integration into dispatcher | **Member A** |
| US-024 | Hotspot live visualization overlay | **Member C** |

> All tasks run in parallel ✓  
> ⚠️ **Coordination point:** Agree on the `get_hotspots()` function signature at sprint start before splitting off. Suggested interface: input → `list[(node_id, timestamp)]`, output → `list[node_id]` (centroids).

---

### Sprint 7 — Week 7: Traffic Dynamics & Realism

| User Story | Task | Owner |
|------------|------|-------|
| US-025, US-026 | Traffic congestion model + ambulance re-routing | **Member A** |
| US-027, US-028 | Config file (YAML/JSON) + comprehensive logging system | **Member C** |

> All tasks run in parallel ✓

---

## Phase 3 — The Pulse (Weeks 8–12)

### Sprint 8 — Week 8: Baseline Comparison

| User Story | Task | Owner |
|------------|------|-------|
| US-029, US-030, US-032 | Random station generator + baseline simulation runs + reproducibility seed | **Member A** |
| US-031 | Baseline documentation + visualizations + markdown report | **Member C** |

> All tasks run in parallel ✓

---

### Sprint 9 — Week 9: AI-Optimised Fleet & Comparison

| User Story | Task | Owner |
|------------|------|-------|
| US-033 | AI-optimised fleet simulation runs (load GA stations from Phase 1) | **Member A** |
| US-034 | Statistical comparison + t-test significance analysis | **Member B** |
| US-035, US-036 | Comparison visualizations + results summary document | **Member C** |

> All tasks run in parallel ✓

---

### Sprint 10 — Week 10: Sensitivity Analysis

| User Story | Task | Owner |
|------------|------|-------|
| US-037, US-038 | Lambda (λ) sensitivity sweep + fleet size sensitivity sweep | **Member A** |
| US-039 | K-Means sensitivity (k parameter + update frequency) | **Member B** |
| US-040 | Sensitivity analysis report + visualizations | **Member C** |

> All tasks run in parallel ✓

---

### Sprint 11 — Week 11: Integration Testing & Edge Cases

| User Story | Task | Owner |
|------------|------|-------|
| US-041 (partial), US-042 | Unit tests for A*, dispatcher, simulation loop + integration tests | **Member A** |
| US-041 (partial), US-043 | Unit tests for GA, K-Means + edge case handling | **Member B** |
| US-044 | Regression test suite (10+ scenarios) | **Member C** |

> All tasks run in parallel ✓

---

### Sprint 12 — Week 12: Performance Optimisation & Scaling

| User Story | Task | Owner |
|------------|------|-------|
| US-045, US-046, US-048 | Profile codebase + optimise A* + enable 10,000+ tick scaling | **Member A** |
| US-047 | Optimise K-Means convergence (numpy vectorisation + early stopping) | **Member B** |

> All tasks run in parallel ✓

---

## Phase 4 — The Polish (Weeks 13–14)

### Sprint 13 — Week 13: Documentation & Code Quality

| User Story | Task | Owner |
|------------|------|-------|
| US-049 (partial) | Docstrings for simulation, dispatcher, agents modules | **Member A** |
| US-049 (partial), US-051 | Docstrings for GA, K-Means modules + PEP 8 refactoring | **Member B** |
| US-050, US-052 | Architecture documentation + user guide | **Member C** |

> All tasks run in parallel ✓

---

### Sprint 14 — Week 14: Final Report & Presentation

| User Story | Task | Owner |
|------------|------|-------|
| US-053 (partial) | Final report — technical sections + results compilation | **Member A** |
| US-055 | Live demo script + pre-recorded video backup | **Member B** |
| US-054, US-056 | Presentation slides + final review & submission package | **Member C** |

> All tasks run in parallel ✓

---

## Summary

| Member | Est. Points | Focus |
|--------|-------------|-------|
| **Member A** | ~62 pts | Core simulation engine, dispatcher, traffic, sensitivity runners, A* optimisation |
| **Member B** | ~50 pts | Event spawner, K-Means, statistical analysis, K-Means optimisation, demo script |
| **Member C** | ~57 pts | Metrics, visualizations, config/logging, all tests, all reports, docs, slides |

---

## Coordination Notes

- **Sprint 6 interface agreement:** Before splitting off, agree on the `get_hotspots()` signature between Members A and B.
- **Config/logger (Member C):** These are read-only utilities. Members A and B consume them — no conflict.
- **Test files (Member C):** Members A and B write code; Member C writes the tests against agreed interfaces. Keeps test files out of feature branches.
- **Final report (Sprint 14):** Member A writes technical content, Member C assembles, formats, and submits.
