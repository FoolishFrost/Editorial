import pytest
import os
import tempfile
from mode_ignore_subsystem import ModeIgnoreSubsystem


def test_mode_ignores_basic_filtering() -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        subsystem = ModeIgnoreSubsystem(settings_dir=temp_dir)
        
        # Initially, ignores should be empty lists/sets
        assert subsystem.ignores["cliches"] == set()
        assert subsystem.ignores["weak_modifiers"] == set()
        
        # Test add_ignore and case-insensitivity
        subsystem.add_ignore("cliches", "Cold As Ice")
        assert "cold as ice" in subsystem.ignores["cliches"]
        
        # Test save and reload
        subsystem2 = ModeIgnoreSubsystem(settings_dir=temp_dir)
        assert "cold as ice" in subsystem2.ignores["cliches"]
        
        # Test filtering hits
        content = "She was cold as ice but very happy."
        # Hits: [(8, 19, "cliche_hit"), (24, 28, "weak_modifiers_hit")]
        hits = [(8, 19, "cliche_hit"), (24, 28, "weak_modifiers_hit")]
        
        # Filter for cliches: "cold as ice" (span 8 to 19) is ignored
        filtered_cliches = subsystem.filter_hits("cliches", content, hits)
        assert len(filtered_cliches) == 1
        assert filtered_cliches[0] == (24, 28, "weak_modifiers_hit")
        
        # Filter for weak modifiers: nothing is ignored yet
        filtered_weak = subsystem.filter_hits("weak_modifiers", content, hits)
        assert len(filtered_weak) == 2
        
        # Add weak modifier ignore
        subsystem.add_ignore("weak_modifiers", "very")
        filtered_weak_after = subsystem.filter_hits("weak_modifiers", content, hits)
        assert len(filtered_weak_after) == 1
        assert filtered_weak_after[0] == (8, 19, "cliche_hit")
        
        # Test remove_ignore
        subsystem.remove_ignore("cliches", "cold as ice")
        assert "cold as ice" not in subsystem.ignores["cliches"]
        
        subsystem3 = ModeIgnoreSubsystem(settings_dir=temp_dir)
        assert "cold as ice" not in subsystem3.ignores["cliches"]
