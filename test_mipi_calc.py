import csv
import math

import pytest
from mipi_calc import calculate_metrics, process_batch, main


def test_reference_equation():
    age, ecog, ratio, wbc = 60, 2, 1.5, 10
    expected = .03535*age + .6978 + 1.367*math.log10(ratio) + .9393*math.log10(wbc*1000)
    result = calculate_metrics(age=age, ecog=ecog, ldh_ratio=ratio, wbc=wbc)
    assert result['score'] == pytest.approx(expected, abs=.00005)
    assert result['classification'] == 'High'


def test_simplified_cutoffs():
    r = calculate_metrics(age=70, ecog=2, wbc=15, ldh_ratio=1.5)
    assert r['simplified_score'] == 11
    assert r['simplified_classification'] == 'High'
    assert calculate_metrics(age=49, ecog=0, wbc=6.69, ldh_ratio=.669)['simplified_score'] == 0
    assert calculate_metrics(age=50, ecog=1, wbc=6.7, ldh_ratio=.67)['simplified_score'] == 3


def test_biological_and_units():
    base = calculate_metrics(age=60, ecog=0, ldh_ratio=1, wbc=10)
    result = calculate_metrics(age=60, ecog=0, ldh=250, ldh_uln=250, wbc=10, ki67=40)
    assert result['biological_score'] == pytest.approx(base['score'] + .02142*40, abs=.0001)
    assert result['ldh_ratio'] == 1


@pytest.mark.parametrize('kwargs', [
    {'age': float('nan'), 'ecog': 0, 'wbc': 10, 'ldh_ratio': 1},
    {'age': 61, 'ecog': 1.5, 'wbc': 10, 'ldh_ratio': 1},
    {'age': 61, 'ecog': 0, 'wbc': 0, 'ldh_ratio': 1},
    {'age': 61, 'ecog': 0, 'wbc': 10, 'ldh_ratio': 0},
    {'age': 61, 'ecog': 0, 'wbc': 10, 'ldh_ratio': 1, 'ki67': 101},
    {'age': 61, 'ecog': 0, 'wbc': 10, 'ldh_ratio': 1, 'ldh': 200},
    {'age': 61, 'ecog': 0, 'wbc': 10},
])
def test_invalid_inputs(kwargs):
    with pytest.raises(ValueError):
        calculate_metrics(**kwargs)


def test_batch_preserves_rows_and_indicates_bad_values(tmp_path):
    inp, out = tmp_path/'patients.csv', tmp_path/'result.csv'
    inp.write_text('Patient_ID,age,ecog,wbc,ldh_ratio,ki67\nP1,60,0,10,1,30\nP2,60,0,0,1,\n', encoding='utf-8')
    assert process_batch(str(inp), str(out)) == 2
    with out.open(newline='') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == 2
    assert rows[0]['error'] == ''
    assert rows[0]['classification']
    assert 'WBC' in rows[1]['error']
    assert rows[1]['score'] == ''


def test_no_overwrite(tmp_path):
    f = tmp_path/'input.csv'
    f.write_text('age,ecog,wbc,ldh_ratio\n60,0,10,1\n')
    with pytest.raises(ValueError):
        process_batch(str(f), str(f))


def test_cli(capsys):
    assert main(['single', '--age', '60', '--ecog', '0', '--ldh-ratio', '1', '--wbc', '10']) == 0
    assert 'simplified_score' in capsys.readouterr().out
