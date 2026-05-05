import pytest
from src.simulation.event_spawner import EventSpawner, Accident

@pytest.fixture
def node_positions():
    return {
        1: {"x": 100, "y": 100},
        2: {"x": 200, "y": 200}
    }

def test_poisson_distribution(node_positions):
    lambda_rate = 0.5
    spawner = EventSpawner(lambda_rate=lambda_rate, node_positions=node_positions, rng_seed=42)
    
    ticks = 10000
    total_spawned = 0
    zero_ticks = 0
    
    for tick in range(ticks):
        accidents = spawner.spawn(tick)
        total_spawned += len(accidents)
        if len(accidents) == 0:
            zero_ticks += 1
            
    mean_spawned = total_spawned / ticks
    # Should be close to lambda_rate (0.5)
    assert 0.45 < mean_spawned < 0.55
    
    # Check that zero_ticks is around e^(-0.5) * 10000 = 6065
    assert 5800 < zero_ticks < 6300

def test_accident_attributes(node_positions):
    spawner = EventSpawner(lambda_rate=1.0, node_positions=node_positions, rng_seed=42)
    accidents = spawner.spawn(current_tick=10)
    
    if accidents:
        acc = accidents[0]
        assert acc.timestamp == 10
        assert acc.priority in [1, 2, 3]
        assert acc.location in [1, 2]
        assert isinstance(acc.pixel_pos, tuple)

def test_set_lambda(node_positions):
    spawner = EventSpawner(lambda_rate=0.0, node_positions=node_positions, rng_seed=42)
    # Should spawn 0
    accidents = spawner.spawn(0)
    assert len(accidents) == 0
    
    spawner.set_lambda(10.0)
    # Very likely to spawn > 0
    accidents = spawner.spawn(1)
    assert len(accidents) > 0
