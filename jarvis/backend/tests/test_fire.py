"""Ручные сверки FIRE-расчётов (Definition of Done: числа проверены руками)."""
import pytest

from app.analytics import fire


def test_fire_target_4pct():
    # $2000/мес → $24k/год → при SWR 4% нужно $600k
    assert fire.fire_target(2000, 0.04) == 600_000


def test_passive_income():
    # $600k * 4% / 12 = $2000/мес
    assert fire.passive_income_monthly(600_000, 0.04) == pytest.approx(2000)


def test_progress_halfway():
    assert fire.progress(300_000, 2000, 0.04) == pytest.approx(0.5)


def test_months_to_target_zero_when_reached():
    assert fire.months_to_target(600_000, 0, 0.05, 600_000) == 0


def test_months_to_target_no_growth():
    # без доходности: 12000 цель, 1000/мес → ровно 12 месяцев
    assert fire.months_to_target(0, 1000, 0.0, 12_000) == 12


def test_months_to_target_with_growth_faster():
    # с доходностью цель достигается не позже, чем без неё
    m_growth = fire.months_to_target(100_000, 1000, 0.08, 300_000)
    m_flat = fire.months_to_target(100_000, 1000, 0.0, 300_000)
    assert m_growth is not None and m_flat is not None
    assert m_growth < m_flat


def test_unreachable_returns_none():
    assert fire.months_to_target(0, 0, 0.0, 1_000_000) is None


def test_real_rate_fisher():
    # 6% номинал / 3% инфляция → 2.9126% реальных (уравнение Фишера)
    assert fire.real_rate(0.06, 0.03) == pytest.approx(0.0291262, abs=1e-6)
    assert fire.real_rate(0.06, 0.0) == pytest.approx(0.06)


def test_inflation_lengthens_path():
    # при инфляции путь к цели в сегодняшних деньгах дольше
    m_no_infl = fire.months_to_target(100_000, 1000, 0.06, 300_000, inflation=0.0)
    m_infl = fire.months_to_target(100_000, 1000, 0.06, 300_000, inflation=0.03)
    assert m_no_infl is not None and m_infl is not None
    assert m_infl > m_no_infl


def test_zero_nominal_with_inflation_still_reaches_by_contributions():
    # реальная ставка отрицательная, но взносы дотягивают
    m = fire.months_to_target(0, 1000, 0.0, 12_000, inflation=0.03)
    assert m is not None and m >= 12


def test_summary_structure():
    expenses = {"rent": 1200, "food": 500, "clothing": 100,
                "utilities_subscriptions": 150, "daily_free": 250}
    s = fire.summary(50_000, expenses, 0.04, 800, inflation=0.03)
    assert s["monthly_expenses"] == 2200
    assert s["target_capital"] == pytest.approx(2200 * 12 / 0.04)
    assert 0 < s["progress"] < 1
    assert s["scenarios"]
    assert s["inflation"] == 0.03
    assert s["base_real_return"] == pytest.approx(fire.real_rate(0.06, 0.03))
