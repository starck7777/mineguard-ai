import os
os.environ['MINEGUARD_DATABASE_URL']='sqlite:///:memory:'
from fastapi.testclient import TestClient
from backend.app.main import app, classify

def payload(seq=1,battery=80):
    return {'node_id':'NODE-01','timestamp':'2026-08-26T12:00:00Z','sequence_id':seq,'source_type':'real','displacement_mm':-4.6,'tilt_x_deg':1.3,'tilt_y_deg':.7,'vibration_rms':.18,'vibration_peak':.62,'soil_moisture_percent':37.5,'soil_pressure':12.4,'rainfall_mm':0,'temperature_c':31.2,'humidity_percent':64,'battery_voltage':3.91,'battery_percentage':battery,'rssi':-81,'snr':7.4}

def test_health():
    with TestClient(app) as c: assert c.get('/health').json()['database']=='healthy'
def test_invalid_battery():
    with TestClient(app) as c: assert c.post('/api/telemetry',json=payload(battery=-1)).status_code==422
def test_duplicate_packet():
    with TestClient(app) as c:
        assert c.post('/api/telemetry',json=payload(101)).json()['duplicate'] is False
        assert c.post('/api/telemetry',json=payload(101)).json()['duplicate'] is True
def test_hysteresis():
    assert classify(62,'observation')=='observation'
    assert classify(65,'observation')=='warning'
def test_public_privacy():
    with TestClient(app) as c:
        body=c.get('/api/public/status').json(); assert 'rssi' not in body and 'battery' not in body

def test_module_analytics_contracts():
    with TestClient(app) as c:
        summary=c.get('/api/v1/mines/demo/module-summary')
        assert summary.status_code==200 and summary.json()['total_modules']==4
        risk=c.get('/api/v1/nodes/NODE-01/sensor-risk')
        assert risk.status_code==200 and len(risk.json()['sensors'])==14
        displacement=next(x for x in risk.json()['sensors'] if x['sensor']=='displacement_mm')
        assert {'risk_score','risk_level','threshold','explanation'} <= displacement.keys()
        matrix=c.get('/api/v1/sensor-risk-matrix?page_size=100')
        assert matrix.status_code==200 and matrix.json()['total']==56
        assert c.get('/api/v1/sensor-risk-matrix?format=csv').headers['content-type'].startswith('text/csv')

def test_sector_coverage_and_placement_security():
    with TestClient(app) as c:
        sectors=c.get('/api/v1/mines/demo/sectors').json(); assert len(sectors)>=4
        landmarks=c.get('/api/v1/mines/demo/landmarks').json(); assert landmarks['total']>=6
        placement=c.get('/api/v1/devices/NODE-01/placement').json()
        assert placement['nearest_landmark']['name'] and placement['landmark_distance_m']>0
        coverage=c.get(f"/api/v1/sectors/{sectors[0]['id']}/coverage").json()
        assert round(coverage['covered_percent']+coverage['uncovered_percent'],1)==100
        assert c.put('/api/v1/devices/NODE-01/placement',json={}).status_code in (403,422)
