from .conftest import login


def test_summary_is_business_readable(client):
    login(client)
    c6 = client.get('/api/v1/customers/6').json()
    assert c6['summary'].startswith('service-0006:')
    assert 'Услуг под риском' not in c6['summary']
    assert 'prolong_wait' not in c6['summary']
    assert 'ограничения' not in c6['summary']
    assert 'баллов до' not in c6['summary']

    c5 = client.get('/api/v1/customers/5').json()
    assert 'prolong_wait' not in c5['summary']
    assert 'минимум' not in c5['summary']
    assert 'Статус' not in c5['summary']


def test_snapshot_has_three_timestamps(client):
    login(client)
    before = client.get('/api/v1/analytics/summary').json()
    assert before['asOf'] and before['sourceUpdatedAt'] and before['updatedAt']
    snapshot = client.get('/api/v1/source/snapshot').json()
    snapshot['accounts'][0]['balance'] += 1
    response = client.put('/api/v1/source/snapshot', json=snapshot)
    after = response.json()['summary']
    assert after['asOf'] == before['asOf']
    assert after['sourceUpdatedAt'] >= before['sourceUpdatedAt']
    assert after['updatedAt'] >= before['updatedAt']


def test_feature_help_metadata(client):
    login(client)
    features = client.get('/api/v1/model/settings').json()['features']
    assert features
    for feature in features:
        assert feature['zero']
        assert feature['one']
