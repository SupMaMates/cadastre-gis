"""
Unit tests for Econometrics, Inequality, Demographics, and Land Fragmentation.
"""

import numpy as np
import pandas as pd
import pytest

from cadastre_gis.analytics.demographics import is_entity_name, parse_balkan_name
from cadastre_gis.analytics.fragmentation import effective_owners
from cadastre_gis.analytics.inequality import gini, hhi, lorenz_curve, palma_ratio, top_share
from cadastre_gis.analytics.land_use import categorize_usage, extract_land_class


def test_gini_coefficient():
    """Test Gini calculation under various equality conditions."""
    # Absolute equality
    assert gini(np.array([100, 100, 100, 100])) == 0.0
    assert gini(np.array([])) == 0.0
    assert gini(np.array([0, 0, 0])) == 0.0

    # Extreme inequality: 1 person owns 1,000, 99 people own 0
    unequal = np.array([0] * 99 + [1000])
    g = gini(unequal)
    assert g > 0.95


def test_theil_and_hhi():
    """Test Theil entropy and HHI indices."""
    equal_shares = np.array([0.25, 0.25, 0.25, 0.25])
    assert pytest.approx(hhi(equal_shares), abs=0.001) == 0.25

    monopoly = np.array([1.0])
    assert hhi(monopoly) == 1.0


def test_top_share_and_palma():
    """Test top percentile shares and Palma ratio."""
    wealth = pd.Series([10, 20, 30, 40, 50, 60, 70, 80, 90, 1000])
    # Top 10% (1 person with 1000 out of 1450)
    assert top_share(wealth, 0.10) > 0.65
    assert palma_ratio(wealth) > 5.0


def test_lorenz_curve():
    """Test Lorenz curve coordinate generation."""
    wealth = np.array([10, 20, 30, 40, 100])
    points = lorenz_curve(wealth, n_points=11)
    assert len(points) == 11
    assert points[0]["p"] == 0.0
    assert points[0]["l"] == 0.0
    assert points[-1]["p"] == 100.0
    assert points[-1]["l"] == 100.0


def test_effective_owners():
    """Test Laakso-Taagepera effective number of owners."""
    # Single sole owner
    assert effective_owners([1.0]) == 1.0
    # Two equal 50% owners
    assert effective_owners([0.5, 0.5]) == 2.0
    # Four equal 25% owners
    assert effective_owners([0.25, 0.25, 0.25, 0.25]) == 4.0
    # Unbalanced: one dominant 90% owner and two 5% owners
    assert 1.0 < effective_owners([0.9, 0.05, 0.05]) < 1.3


def test_balkan_name_parser():
    """Test parsing surname, patronym (father), first name, and gender."""
    # Male person with father name in parentheses
    sur, fath, first, gend = parse_balkan_name("Мутавчић (Живана) Ратко")
    assert sur == "Мутавчић"
    assert fath == "Живана"
    assert first == "Ратко"
    assert gend == "Male"

    # Female person
    sur, fath, first, gend = parse_balkan_name("Ђокановић (Славка) Марија")
    assert sur == "Ђокановић"
    assert fath == "Славка"
    assert first == "Марија"
    assert gend == "Female"

    # Legal entity
    sur, fath, first, gend = parse_balkan_name("ОПШТИНА ДОЊИ ЖАБАР")
    assert gend == "Entity"
    assert is_entity_name("РЕПУБЛИКА СРПСКА") is True
    assert is_entity_name("*ГОЛД - МГ* Д.О.О.") is True


def test_land_use_classification():
    """Test land class extraction and category classification."""
    assert extract_land_class("Њива 3. класе") == 3
    assert extract_land_class("Шума 4. класе") == 4
    assert extract_land_class("Двориште") is None

    assert categorize_usage("Њива 2. класе") == "agriculture"
    assert categorize_usage("Стамбени објекат") == "residential"
    assert categorize_usage("Двориште") == "yard"
    assert categorize_usage("Шума") == "forest"
    assert categorize_usage("Канал") == "infrastructure"
