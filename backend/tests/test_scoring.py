import math
from datetime import timedelta
import pytest
from app.scoring import default_settings, probability, compute, parse_iso
from app.schemas import SnapshotIn
from app.seed import validate_snapshot

NOW = parse_iso('2026-10-23T18:00:00.000Z')


def model_result(snapshot, settings=None):
    data = validate_snapshot(SnapshotIn.model_validate(snapshot))
    return compute(data['accounts'], data['services'], data['transactions'], settings or default_settings(), NOW, NOW)


@pytest.mark.parametrize('midpoint', [10000., -10000., 1.7976931348623157e308, -1.7976931348623157e308])
@pytest.mark.parametrize('steepness', [12., 5e-324])
def test_finite_probability(midpoint, steepness):
    settings = default_settings()
    settings['probability'].update(midpoint=midpoint, steepness=steepness)
    for score in (0., 50., 100.):
        value = probability(score, settings)
        assert math.isfinite(value)
        assert settings['probability']['floor'] <= value <= settings['probability']['ceiling']


@pytest.mark.parametrize('weight', [1e308, 5e-324, 1.])
def test_weight_scale(full_snapshot, weight):
    settings = default_settings()
    settings['weights'] = dict.fromkeys(settings['weights'], weight)
    result = model_result(full_snapshot, settings)
    import json
    json.dumps(result, allow_nan=False)
    assert result['summary']['scoredCustomers'] > 0
    for customer in result['customers']:
        if customer['score'] is not None:
            assert 0 <= customer['score'] <= 100
            assert 0 <= customer['confidence'] <= 1


def test_control_75_551(full_snapshot):
    snapshot = {'accounts': [dict(full_snapshot['accounts'][0], id=1, email='control@example.test', balance=400,
                 withdrawBalance=0, totalReplenished=12000, bonusBalance=0, bonusState='locked')],
                'services': [dict(full_snapshot['services'][0], id=1, ownerId=1, status='active', paymentTerm='month',
                  autoProlong=False, price=990, createdAt=(NOW-timedelta(days=28)).isoformat(), expiresAt=(NOW+timedelta(days=2)).isoformat())],
                'transactions': [dict(full_snapshot['transactions'][0], id=1, serviceId=1, status='performed',
                   type='prolong', createdAt=(NOW-timedelta(days=28)).isoformat(), performedAt=(NOW-timedelta(days=28)).isoformat())]}
    customer = model_result(snapshot)['customers'][0]
    assert customer['score'] == 75
    assert customer['money']['expectedLossCents'] == 551
